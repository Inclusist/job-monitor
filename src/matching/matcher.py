"""
Background job matching with semantic filtering and Claude analysis
"""
import os
import time
import importlib.util
from pathlib import Path
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.database.postgres_operations import PostgresDatabase
from src.database.postgres_cv_operations import PostgresCVManager
from src.analysis.claude_analyzer import ClaudeJobAnalyzer


def run_background_matching(user_id: int, matching_status: Dict) -> None:
    """
    Run complete job matching pipeline for a user in background
    
    Args:
        user_id: User ID to match jobs for
        matching_status: Shared dictionary to update with progress
    """
    try:
        # Initialize status
        matching_status[user_id] = {
            'status': 'running',
            'stage': 'initializing',
            'progress': 0,
            'message': 'Starting job matching...',
            'matches_found': 0,
            'jobs_analyzed': 0
        }
        
        # Initialize databases
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            matching_status[user_id] = {
                'status': 'error',
                'stage': 'error',
                'progress': 0,
                'message': '❌ Database connection not configured.',
                'matches_found': 0,
                'jobs_analyzed': 0
            }
            return
        
        job_db_inst = PostgresDatabase(db_url)
        cv_manager_inst = PostgresCVManager(job_db_inst.connection_pool)
        
        # Get user's primary CV and profile
        primary_cv = cv_manager_inst.get_primary_cv(user_id)
        if not primary_cv:
            matching_status[user_id] = {
                'status': 'error',
                'stage': 'error',
                'progress': 0,
                'message': '❌ No primary CV found. Please upload a CV first.',
                'matches_found': 0,
                'jobs_analyzed': 0
            }
            return
        
        profile = cv_manager_inst.get_cv_profile(primary_cv['id'], include_full_text=False)
        if not profile:
            matching_status[user_id] = {
                'status': 'error',
                'stage': 'error',
                'progress': 0,
                'message': '❌ CV profile not found. Please re-upload your CV.',
                'matches_found': 0,
                'jobs_analyzed': 0
            }
            return
        
        print(f"\n{'='*60}")
        print(f"Background Job Matching - User {user_id}")
        print(f"{'='*60}\n")
        
        # Load filter_jobs module dynamically
        matching_status[user_id].update({
            'stage': 'loading_model',
            'progress': 10,
            'message': 'Loading AI models...'
        })
        
        print("📥 Loading sentence transformer model...")
        t_model_start = time.time()
        scripts_dir = Path(__file__).parent.parent.parent / 'scripts'
        filter_jobs_path = scripts_dir / 'filter_jobs.py'
        
        spec = importlib.util.spec_from_file_location("filter_module", filter_jobs_path)
        filter_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(filter_module)
        
        # Load semantic model
        model = filter_module.load_sentence_transformer()
        t_model = time.time() - t_model_start
        print(f"✅ Model loaded ({t_model:.2f}s)")
        
        # Build CV embedding
        t_cv_start = time.time()
        cv_text = filter_module.build_cv_text(profile)
        cv_embedding = model.encode(cv_text, show_progress_bar=False)
        t_cv = time.time() - t_cv_start
        print(f"✅ CV embedding created ({t_cv:.2f}s)")
        
        # Check if user has any existing matches
        existing_matches = job_db_inst.get_user_job_matches(user_id, min_semantic_score=0, limit=1)
        
        # If no matches yet, fetch initial jobs from JSearch
        if not existing_matches:
            matching_status[user_id].update({
                'stage': 'initial_fetch',
                'progress': 15,
                'message': 'First time setup: Fetching initial jobs from JSearch...'
            })
            print("\n🔍 First time user - fetching initial jobs from JSearch...")
            
            try:
                from src.collectors.jsearch import JSearchCollector
                from src.collectors.arbeitsagentur import ArbeitsagenturCollector
                
                # Get user preferences for search
                user = cv_manager_inst.get_user_by_id(user_id)
                preferences = user.get('preferences', {})
                keywords = preferences.get('search_keywords', [])
                # Check both possible location keys for backward compatibility
                locations = preferences.get('search_locations', preferences.get('preferred_locations', []))
                
                # Build search query from CV if no preferences set
                if not keywords:
                    keywords = [profile.get('expertise_summary', '').split()[0]] if profile.get('expertise_summary') else ['software engineer']
                if not locations:
                    locations = ['Germany']
                
                # Initialize collectors
                jsearch_key = os.environ.get('JSEARCH_API_KEY')
                jsearch = JSearchCollector(jsearch_key) if jsearch_key else None
                arbeitsagentur = ArbeitsagenturCollector()  # Always available (free, no key needed)
                
                if jsearch or arbeitsagentur:
                    # PROGRESSIVE FETCHING: Use ALL keywords, process in small batches
                    # This allows results to appear progressively instead of waiting 30+ minutes
                    batch_size = 2  # Process 2-3 keywords at a time
                    keyword_batches = [keywords[i:i+batch_size] for i in range(0, len(keywords), batch_size)]
                    
                    # Calculate total searches (JSearch + Arbeitsagentur for German locations)
                    jsearch_searches = len(keyword_batches) * len(locations) if jsearch else 0
                    # Arbeitsagentur only for German locations
                    german_locations = [loc for loc in locations if any(term in loc.lower() for term in ['germany', 'deutschland', 'berlin', 'munich', 'hamburg', 'remote'])]
                    ba_searches = len(keyword_batches) * len(german_locations) if arbeitsagentur and german_locations else 0
                    total_searches = jsearch_searches + ba_searches
                    
                    print(f"  📊 Progressive search: {len(keywords)} keywords in {len(keyword_batches)} batches × {len(locations)} locations")
                    if jsearch and arbeitsagentur and german_locations:
                        print(f"  🌍 JSearch: {jsearch_searches} searches (international)")
                        print(f"  🇩🇪 Arbeitsagentur: {ba_searches} searches (German locations)")
                    print(f"  ⏱️  Estimated time: ~{total_searches * 3 / 60:.1f} minutes ({total_searches} API calls)")
                    print(f"  💡 Results will stream in as each search completes\n")
                    
                    def fetch_batch_jsearch(batch_keywords, location, batch_idx):
                        """Fetch jobs from JSearch for a batch of keywords (progressive results)"""
                        if not batch_keywords or not jsearch:
                            return 0
                        
                        combined_query = " OR ".join(batch_keywords) if len(batch_keywords) > 1 else batch_keywords[0]
                        batch_name = f"Batch {batch_idx+1}/{len(keyword_batches)}"
                        
                        # Determine country code from location
                        country_code = None
                        if location:
                            loc_lower = location.lower()
                            # German-speaking countries
                            if 'germany' in loc_lower or 'deutschland' in loc_lower or any(city in loc_lower for city in ['berlin', 'munich', 'hamburg', 'cologne', 'frankfurt']):
                                country_code = 'de'
                            elif 'austria' in loc_lower or 'österreich' in loc_lower or any(city in loc_lower for city in ['vienna', 'wien', 'salzburg']):
                                country_code = 'at'
                            elif 'switzerland' in loc_lower or 'schweiz' in loc_lower or any(city in loc_lower for city in ['zurich', 'geneva', 'basel']):
                                country_code = 'ch'
                            # Other European countries
                            elif 'france' in loc_lower or any(city in loc_lower for city in ['paris', 'lyon', 'marseille']):
                                country_code = 'fr'
                            elif 'uk' in loc_lower or 'united kingdom' in loc_lower or 'england' in loc_lower or any(city in loc_lower for city in ['london', 'manchester', 'birmingham']):
                                country_code = 'gb'
                            elif 'spain' in loc_lower or 'españa' in loc_lower or any(city in loc_lower for city in ['madrid', 'barcelona', 'valencia']):
                                country_code = 'es'
                            elif 'netherlands' in loc_lower or 'holland' in loc_lower or any(city in loc_lower for city in ['amsterdam', 'rotterdam', 'utrecht']):
                                country_code = 'nl'
                            elif 'italy' in loc_lower or 'italia' in loc_lower or any(city in loc_lower for city in ['rome', 'milan', 'florence']):
                                country_code = 'it'
                            elif 'belgium' in loc_lower or 'belgique' in loc_lower or any(city in loc_lower for city in ['brussels', 'antwerp', 'bruges']):
                                country_code = 'be'
                            elif 'portugal' in loc_lower or any(city in loc_lower for city in ['lisbon', 'porto']):
                                country_code = 'pt'
                            # North America (default to US if nothing else matches)
                            elif 'canada' in loc_lower or any(city in loc_lower for city in ['toronto', 'vancouver', 'montreal']):
                                country_code = 'ca'
                            elif 'usa' in loc_lower or 'united states' in loc_lower or 'america' in loc_lower:
                                country_code = 'us'
                        
                        print(f"  🔍 [JSearch] {batch_name} - {location} ({country_code}): {combined_query[:45]}...")
                        t_start = time.time()
                        
                        try:
                            # Fetch from JSearch API (5 pages = ~50 results per batch)
                            jobs = jsearch.search_jobs(
                                query=combined_query,
                                location=location,
                                num_pages=5,
                                date_posted="week",
                                country=country_code
                            )
                            
                            # Add to database immediately
                            new_jobs = 0
                            for job in jobs:
                                if job_db_inst.add_job(job):
                                    new_jobs += 1
                            
                            elapsed = time.time() - t_start
                            print(f"  ✓ [JSearch] {batch_name} done: {len(jobs)} jobs ({new_jobs} new) in {elapsed:.1f}s")
                            return new_jobs
                            
                        except Exception as e:
                            print(f"  ⚠️  [JSearch] {batch_name} error: {e}")
                            return 0
                    
                    def fetch_batch_arbeitsagentur(batch_keywords, location, batch_idx):
                        """Fetch jobs from Arbeitsagentur for a batch of keywords (German jobs only)"""
                        if not batch_keywords or not arbeitsagentur:
                            return 0
                        
                        # Only fetch from Arbeitsagentur for German locations
                        is_german = any(term in location.lower() for term in ['germany', 'deutschland', 'berlin', 'munich', 'hamburg', 'remote'])
                        if not is_german:
                            return 0
                        
                        batch_name = f"Batch {batch_idx+1}/{len(keyword_batches)}"
                        
                        # Arbeitsagentur API handles both German and English keywords well
                        # It searches in job descriptions which often contain English terms
                        combined_query = " OR ".join(batch_keywords) if len(batch_keywords) > 1 else batch_keywords[0]
                        
                        # Extract city from location string
                        city = location.split(',')[0].strip() if ',' in location else location.strip()
                        if city.lower() == 'remote work':
                            city = None  # Remote jobs - search nationwide
                        
                        print(f"  🔍 [BA] {batch_name} - {location}: {combined_query[:45]}...")
                        t_start = time.time()
                        
                        try:
                            # Fetch from Arbeitsagentur API
                            result = arbeitsagentur.search_jobs(
                                keywords=combined_query,
                                location=city,
                                radius_km=50,
                                days_since_posted=7,  # Last week
                                page_size=50  # Fetch up to 50 jobs per search
                            )
                            
                            jobs = result.get('jobs', [])
                            
                            # Add to database immediately
                            new_jobs = 0
                            for job in jobs:
                                if job_db_inst.add_job(job):
                                    new_jobs += 1
                            
                            elapsed = time.time() - t_start
                            print(f"  ✓ [BA] {batch_name} done: {len(jobs)} jobs ({new_jobs} new) in {elapsed:.1f}s")
                            return new_jobs
                            
                        except Exception as e:
                            print(f"  ⚠️  [BA] {batch_name} error: {e}")
                            return 0
                    
                    # Progressive fetching with concurrent workers
                    total_new = 0
                    completed = 0
                    t_fetch_start = time.time()
                    
                    with ThreadPoolExecutor(max_workers=4) as executor:
                        # Submit all fetch tasks (both JSearch and Arbeitsagentur)
                        futures = {}
                        
                        # Submit JSearch tasks
                        if jsearch:
                            for batch_idx, batch_keywords in enumerate(keyword_batches):
                                for location in locations:
                                    future = executor.submit(fetch_batch_jsearch, batch_keywords, location, batch_idx)
                                    futures[future] = ('jsearch', batch_idx, location)
                        
                        # Submit Arbeitsagentur tasks for German locations
                        if arbeitsagentur and german_locations:
                            for batch_idx, batch_keywords in enumerate(keyword_batches):
                                for location in german_locations:
                                    future = executor.submit(fetch_batch_arbeitsagentur, batch_keywords, location, batch_idx)
                                    futures[future] = ('arbeitsagentur', batch_idx, location)
                        
                        # Process results as they complete (progressive!)
                        for future in as_completed(futures):
                            new_jobs = future.result()
                            total_new += new_jobs
                            completed += 1
                            
                            # Update progress for UI
                            progress = 15 + int((completed / total_searches) * 10)  # 15-25%
                            matching_status[user_id].update({
                                'progress': progress,
                                'message': f'Fetching jobs: {completed}/{total_searches} searches done ({total_new} new jobs)...'
                            })
                    
                    t_fetch = time.time() - t_fetch_start
                    print(f"\n✓ All searches complete: {total_new} new jobs in {t_fetch:.1f}s ({t_fetch/60:.1f} min)")
                    print(f"  📊 Processed {len(keywords)} keywords across {total_searches} searches")
                    
                    if t_fetch > 120:
                        print(f"  💡 {t_fetch/60:.1f} minutes for {len(keywords)} keywords - results appeared progressively!")
                else:
                    print("⚠️  No job collectors available, will use existing jobs only")
                    
            except Exception as e:
                print(f"⚠️  Error fetching initial jobs: {e}")
                # Continue with existing jobs if fetch fails
        
        # Get unfiltered jobs
        matching_status[user_id].update({
            'stage': 'fetching_jobs',
            'progress': 20,
            'message': 'Fetching jobs to analyze...'
        })
        
        t_query_start = time.time()
        jobs_to_filter = job_db_inst.get_unfiltered_jobs_for_user(user_id)
        t_query = time.time() - t_query_start
        print(f"Found {len(jobs_to_filter)} jobs to filter (query: {t_query:.2f}s)")
        
        if not jobs_to_filter:
            print("✓ No new jobs to filter")
            matching_status[user_id] = {
                'status': 'completed',
                'stage': 'done',
                'progress': 100,
                'message': 'No new jobs to filter',
                'matches_found': 0,
                'jobs_analyzed': 0
            }
            return
        
        # Get user preferences for keyword boosting
        user = cv_manager_inst.get_user_by_id(user_id)
        preferences = user.get('preferences', {})
        config_keywords = preferences.get('search_keywords', [])
        
        # Filter jobs with semantic similarity
        matching_status[user_id].update({
            'stage': 'semantic_filtering',
            'progress': 30,
            'message': f'Analyzing {len(jobs_to_filter)} jobs with semantic similarity...',
            'total_jobs': len(jobs_to_filter)
        })
        
        matches = []
        max_score = 0
        
        # Timing breakdown
        t_semantic_start = time.time()
        t_encode_total = 0
        t_similarity_total = 0
        t_keyword_total = 0
        
        for idx, job in enumerate(jobs_to_filter):
            job_text = filter_module.build_job_text(job)
            
            t_encode = time.time()
            job_embedding = model.encode(job_text, show_progress_bar=False)
            t_encode_total += time.time() - t_encode
            
            t_sim = time.time()
            similarity = filter_module.calculate_similarity(cv_embedding, job_embedding)
            t_similarity_total += time.time() - t_sim
            
            t_kw = time.time()
            boosted_score, matched_keywords = filter_module.apply_keyword_boosts(
                similarity, job, config_keywords
            )
            t_keyword_total += time.time() - t_kw
            
            # Track max score for debugging
            if boosted_score > max_score:
                max_score = boosted_score
            
            if boosted_score >= 0.30:  # 30% threshold (temporarily lowered for testing)
                matches.append({
                    'job': job,
                    'score': int(boosted_score * 100),
                    'matched_keywords': matched_keywords
                })
            
            # Update progress during filtering
            if (idx + 1) % 10 == 0 or idx == len(jobs_to_filter) - 1:
                progress = 30 + int((idx + 1) / len(jobs_to_filter) * 20)  # 30-50%
                matching_status[user_id].update({
                    'progress': progress,
                    'message': f'Filtered {idx + 1}/{len(jobs_to_filter)} jobs, {len(matches)} matches so far...'
                })
        
        t_semantic_total = time.time() - t_semantic_start
        print(f"\n⏱️  SEMANTIC FILTERING:")
        print(f"  Total: {t_semantic_total:.2f}s ({t_semantic_total/60:.2f} min)")
        print(f"  Encoding: {t_encode_total:.2f}s ({t_encode_total/len(jobs_to_filter)*1000:.0f}ms/job)")
        print(f"  Similarity: {t_similarity_total:.2f}s")
        print(f"  Keyword boost: {t_keyword_total:.2f}s")
        print(f"✓ Found {len(matches)} matches above 30% threshold (max: {max_score:.3f})")
        
        # Save semantic matches to database (batch insert for performance)
        matching_status[user_id].update({
            'stage': 'saving_matches',
            'progress': 55,
            'message': f'Saving {len(matches)} matches to database...',
            'matches_found': len(matches)
        })
        
        # Prepare batch data
        batch_matches = []
        for match in matches:
            job = match['job']
            match_reasoning = f"Matched keywords: {', '.join(match['matched_keywords'][:5])}" if match['matched_keywords'] else "Semantic similarity"
            batch_matches.append({
                'user_id': user_id,
                'job_id': job['id'],
                'semantic_score': match['score'],
                'match_reasoning': match_reasoning
            })
        
        # Batch insert all matches at once (much faster than individual inserts)
        t_save_start = time.time()
        saved_count = job_db_inst.add_user_job_matches_batch(batch_matches)
        cv_manager_inst.update_filter_run_time(user_id)
        t_save = time.time() - t_save_start
        print(f"✓ Saved {saved_count} semantic matches in {t_save:.2f}s")
        
        # Step 2: Claude analysis on high-scoring matches (>= 70%)
        high_score_matches = [m for m in matches if m['score'] >= 70]
        
        # Initialize Claude analyzer
        try:
            api_key = os.environ.get('ANTHROPIC_API_KEY')
            if api_key:
                analyzer = ClaudeJobAnalyzer(api_key=api_key, db=job_db_inst, user_email=user.get('email', 'unknown'))
            else:
                print("⚠️  No ANTHROPIC_API_KEY found, skipping Claude analysis")
                analyzer = None
        except Exception as e:
            print(f"⚠️  Could not initialize Claude analyzer: {e}")
            analyzer = None
        
        jobs_analyzed = 0
        if high_score_matches and analyzer:
            print(f"\n🤖 Running Claude analysis on {len(high_score_matches)} high-scoring jobs...")
            
            # Set the profile once for all analyses
            analyzer.set_profile(profile)
            
            matching_status[user_id].update({
                'stage': 'claude_analysis',
                'progress': 60,
                'message': f'Running AI analysis on {len(high_score_matches)} high-scoring matches...'
            })

            # Collect all Claude analyses first, then batch update
            claude_batch_updates = []

            for idx, match in enumerate(high_score_matches):  # Analyze all high-scoring matches
                job = match['job']
                
                try:
                    # Analyze with Claude
                    analysis = analyzer.analyze_job(job)
                    
                    if analysis and 'match_score' in analysis:
                        # Convert lists to strings for database storage
                        key_alignments = analysis.get('key_alignments', [])
                        potential_gaps = analysis.get('potential_gaps', [])
                        
                        # Handle both list of strings and list of dicts
                        if key_alignments and isinstance(key_alignments[0], dict):
                            key_alignments = [str(item) for item in key_alignments]
                        if potential_gaps and isinstance(potential_gaps[0], dict):
                            potential_gaps = [str(item) for item in potential_gaps]
                        
                        # Add to batch
                        claude_batch_updates.append({
                            'user_id': user_id,
                            'job_id': job['id'],
                            'claude_score': analysis['match_score'],
                            'priority': analysis.get('priority', 'medium'),
                            'match_reasoning': analysis.get('reasoning', ''),
                            'key_alignments': key_alignments,
                            'potential_gaps': potential_gaps
                        })
                        
                        print(f"  ✓ {job.get('title', 'Unknown')[:50]} - Claude: {analysis['match_score']}%")
                        jobs_analyzed += 1
                        
                        # Update progress
                        progress = 60 + int((idx + 1) / min(len(high_score_matches), 20) * 30)  # 60-90%
                        matching_status[user_id].update({
                            'progress': progress,
                            'message': f'AI analyzed {idx + 1}/{min(len(high_score_matches), 20)} jobs...',
                            'jobs_analyzed': jobs_analyzed
                        })
                    
                except Exception as e:
                    print(f"  ⚠ Error analyzing job {job['id']}: {e}")
                    continue
            
            # Batch update all Claude analyses at once (much faster than individual updates)
            if claude_batch_updates:
                matching_status[user_id].update({
                    'progress': 92,
                    'message': f'Saving {len(claude_batch_updates)} AI analyses to database...'
                })
                updated_count = job_db_inst.add_user_job_matches_batch(claude_batch_updates)
                print(f"✓ Saved {updated_count} Claude analyses to database")
            
            print(f"✓ Claude analysis complete")
        
        # Mark as completed
        matching_status[user_id] = {
            'status': 'completed',
            'stage': 'done',
            'progress': 100,
            'message': f'✅ Matching complete! Found {len(matches)} matches, analyzed {jobs_analyzed} with AI',
            'matches_found': len(matches),
            'jobs_analyzed': jobs_analyzed
        }
        
        print(f"\n{'='*60}")
        print(f"✅ Background job matching complete for user {user_id}")
        print(f"   Semantic matches: {len(matches)}")
        print(f"   Claude analyzed: {jobs_analyzed}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error in background matching: {e}")
        import traceback
        traceback.print_exc()
        
        # Mark as error
        matching_status[user_id] = {
            'status': 'error',
            'stage': 'error',
            'progress': 0,
            'message': f'❌ Error: {str(e)}',
            'matches_found': 0,
            'jobs_analyzed': 0
        }
