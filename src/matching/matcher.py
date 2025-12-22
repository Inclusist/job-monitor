"""
Background job matching with semantic filtering and Claude analysis
"""
import os
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
        
        scripts_dir = Path(__file__).parent.parent.parent / 'scripts'
        filter_jobs_path = scripts_dir / 'filter_jobs.py'
        
        spec = importlib.util.spec_from_file_location("filter_module", filter_jobs_path)
        filter_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(filter_module)
        
        # Load semantic model
        model = filter_module.load_sentence_transformer()
        
        # Build CV embedding
        cv_text = filter_module.build_cv_text(profile)
        cv_embedding = model.encode(cv_text, show_progress_bar=False)
        
        # Check if user has any existing matches
        existing_matches = job_db_inst.get_user_job_matches(user_id, min_score=0, limit=1)
        
        # If no matches yet, fetch initial jobs from JSearch
        if not existing_matches:
            matching_status[user_id].update({
                'stage': 'initial_fetch',
                'progress': 15,
                'message': 'First time setup: Fetching initial jobs from JSearch...'
            })
            print("\n🔍 First time user - fetching initial jobs from JSearch...")
            
            try:
                from collectors.jsearch import JSearchCollector
                
                # Get user preferences for search
                user = cv_manager_inst.get_user_by_id(user_id)
                preferences = user.get('preferences', {})
                keywords = preferences.get('search_keywords', [])
                locations = preferences.get('preferred_locations', [])
                
                # Build search query from CV if no preferences set
                if not keywords:
                    keywords = [profile.get('expertise_summary', '').split()[0]] if profile.get('expertise_summary') else ['software engineer']
                if not locations:
                    locations = ['Germany']
                
                # Initialize JSearch collector
                jsearch_key = os.environ.get('JSEARCH_API_KEY')
                if jsearch_key:
                    jsearch = JSearchCollector(jsearch_key)
                    
                    # Prioritize keywords: user preferences are already in priority order
                    # Split into 2 batches for concurrent calls
                    mid_point = max(1, len(keywords) // 2)
                    batch1_keywords = keywords[:mid_point]
                    batch2_keywords = keywords[mid_point:] if len(keywords) > mid_point else []
                    
                    def fetch_batch(batch_keywords, location, batch_num):
                        """Fetch jobs for a batch of keywords in a location"""
                        if not batch_keywords:
                            return []
                        
                        combined_query = " OR ".join(batch_keywords) if len(batch_keywords) > 1 else batch_keywords[0]
                        print(f"  🔍 Batch {batch_num} in {location}: {combined_query}")
                        
                        # Request 100 results per batch per location (max 200 per location)
                        jobs = jsearch.search_jobs(
                            query=combined_query,
                            location=location,
                            results_wanted=100,
                            hours_old=72  # Last 3 days
                        )
                        return jobs
                    
                    # Fetch jobs concurrently across all batches and locations
                    total_fetched = 0
                    locations_limited = locations[:2]  # Limit to 2 locations
                    
                    with ThreadPoolExecutor(max_workers=4) as executor:
                        matching_status[user_id].update({
                            'message': f'Fetching jobs concurrently (2 batches × {len(locations_limited)} locations)...'
                        })
                        
                        # Submit all fetch tasks
                        futures = []
                        for location in locations_limited:
                            futures.append(executor.submit(fetch_batch, batch1_keywords, location, 1))
                            if batch2_keywords:
                                futures.append(executor.submit(fetch_batch, batch2_keywords, location, 2))
                        
                        # Collect results as they complete
                        for future in as_completed(futures):
                            try:
                                jobs = future.result()
                                # Add jobs to database
                                for job in jobs:
                                    job_db_inst.add_job(job)
                                    total_fetched += 1
                                print(f"  ✓ Fetched {len(jobs)} jobs from batch")
                            except Exception as e:
                                print(f"  ⚠️  Batch fetch error: {e}")
                    
                    print(f"✓ Fetched {total_fetched} initial jobs from JSearch")
                    print(f"  📊 Keyword batches: Batch 1: {', '.join(batch1_keywords)}")
                    if batch2_keywords:
                        print(f"  📊 Keyword batches: Batch 2: {', '.join(batch2_keywords)}")
                else:
                    print("⚠️  No JSEARCH_API_KEY found, will use existing jobs only")
                    
            except Exception as e:
                print(f"⚠️  Error fetching initial jobs: {e}")
                # Continue with existing jobs if fetch fails
        
        # Get unfiltered jobs
        matching_status[user_id].update({
            'stage': 'fetching_jobs',
            'progress': 20,
            'message': 'Fetching jobs to analyze...'
        })
        
        jobs_to_filter = job_db_inst.get_unfiltered_jobs_for_user(user_id)
        print(f"Found {len(jobs_to_filter)} jobs to filter")
        
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
        for idx, job in enumerate(jobs_to_filter):
            job_text = filter_module.build_job_text(job)
            job_embedding = model.encode(job_text, show_progress_bar=False)
            
            similarity = filter_module.calculate_similarity(cv_embedding, job_embedding)
            boosted_score, matched_keywords = filter_module.apply_keyword_boosts(
                similarity, job, config_keywords
            )
            
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
        
        print(f"✓ Found {len(matches)} matches above 30% threshold (max score: {max_score:.3f})")
        
        # Save semantic matches to database
        matching_status[user_id].update({
            'stage': 'saving_matches',
            'progress': 55,
            'message': f'Saving {len(matches)} matches to database...',
            'matches_found': len(matches)
        })
        
        for match in matches:
            job = match['job']
            match_reasoning = f"Matched keywords: {', '.join(match['matched_keywords'][:5])}" if match['matched_keywords'] else "Semantic similarity"
            job_db_inst.add_user_job_match(
                user_id=user_id,
                job_id=job['id'],
                semantic_score=match['score'],
                match_reasoning=match_reasoning
            )
        
        cv_manager_inst.update_filter_run_time(user_id)
        print(f"✓ Saved {len(matches)} semantic matches to database")
        
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
                'message': f'Running AI analysis on {min(len(high_score_matches), 20)} top matches...'
            })
            
            for idx, match in enumerate(high_score_matches[:20]):  # Limit to top 20
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
                        
                        job_db_inst.add_user_job_match(
                            user_id=user_id,
                            job_id=job['id'],
                            claude_score=analysis['match_score'],
                            priority=analysis.get('priority', 'medium'),
                            match_reasoning=analysis.get('reasoning', ''),
                            key_alignments=key_alignments,
                            potential_gaps=potential_gaps
                        )
                        print(f"  ✓ {job.get('title', 'Unknown')[:50]} - Claude: {analysis['match_score']}%")
                        jobs_analyzed += 1
                        
                        # Update progress
                        progress = 60 + int((idx + 1) / min(len(high_score_matches), 20) * 35)
                        matching_status[user_id].update({
                            'progress': progress,
                            'message': f'AI analyzed {idx + 1}/{min(len(high_score_matches), 20)} jobs...',
                            'jobs_analyzed': jobs_analyzed
                        })
                    
                except Exception as e:
                    print(f"  ⚠ Error analyzing job {job['id']}: {e}")
                    continue
            
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
