"""
Background job matching with semantic filtering and Claude analysis
"""
import os
import time
import importlib.util
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.database.postgres_operations import PostgresDatabase
from src.database.postgres_cv_operations import PostgresCVManager
from src.analysis.claude_analyzer import ClaudeJobAnalyzer


def split_into_date_chunks(jobs: list, chunk_days: int = 3) -> List[Tuple[str, list]]:
    """Split jobs into chunks by discovered_date, newest first.

    Returns list of (chunk_label, jobs_list) tuples.
    Jobs without a discovered_date go into a final 'undated' chunk.
    """
    if not jobs:
        return []

    with_dates = []
    without_dates = []

    for job in jobs:
        d = job.get('discovered_date')
        if d:
            if isinstance(d, str):
                d = datetime.fromisoformat(d)
            with_dates.append((job, d))
        else:
            without_dates.append(job)

    if not with_dates:
        return [('all jobs', jobs)]

    # Find date range
    newest = max(d for _, d in with_dates)
    oldest = min(d for _, d in with_dates)

    # Build chunks from newest to oldest
    chunks = []
    chunk_end = newest + timedelta(days=1)  # inclusive of newest day

    while chunk_end > oldest:
        chunk_start = chunk_end - timedelta(days=chunk_days)
        chunk_jobs = [j for j, d in with_dates if chunk_start <= d < chunk_end]
        if chunk_jobs:
            label = f"{chunk_start.strftime('%b %d')} - {(chunk_end - timedelta(days=1)).strftime('%b %d')}"
            chunks.append((label, chunk_jobs))
        chunk_end = chunk_start

    if without_dates:
        chunks.append(('undated', without_dates))

    return chunks


def generate_news_snippets(profile: dict, num_snippets: int = 10) -> list:
    """Generate job-related news/tips using Gemini, personalized to user's field."""
    try:
        gemini_key = os.getenv('GOOGLE_GEMINI_API_KEY') if os.getenv('ENABLE_GEMINI') == 'true' else None
        if not gemini_key:
            return []

        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-2.5-flash')

        expertise = profile.get('expertise_summary', 'professional')
        industries = ', '.join(profile.get('industries', [])) or 'technology'

        prompt = f"""Generate {num_snippets} short, interesting snippets (2-3 sentences each) for a job seeker in {industries} with expertise in: {expertise}.

Mix of:
- Current job market trends and insights
- Practical career tips and advice
- Industry news and developments
- Interview and application tips

Each snippet should be self-contained, informative, and encouraging. Return as a JSON array of strings.
No markdown formatting in the snippets themselves."""

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=2048,
                temperature=0.9,
            )
        )

        import json
        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith('```'):
            text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        return json.loads(text)
    except Exception as e:
        print(f"⚠️  Could not generate news snippets: {e}")
        return []


def run_background_matching(user_id: int, matching_status: Dict, latest_day_only: bool = False) -> None:
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

        # Generate news snippets for display during matching
        snippets = generate_news_snippets(profile)
        if snippets:
            matching_status[user_id]['news_snippets'] = snippets

        # Check if user has any existing matches
        existing_matches = job_db_inst.get_user_job_matches(user_id, min_semantic_score=0, limit=1)
        
        # No longer fetching initial jobs from API here.
        # Database is now expected to have sufficient historical data.
        print("🔍 Checking existing jobs in database...")
        
        # Get user preferences for location filtering
        user = cv_manager_inst.get_user_by_id(user_id)
        preferences = user.get('preferences', {})
        preferred_locs = preferences.get('search_locations', preferences.get('preferred_locations', []))
        config_keywords = preferences.get('search_keywords', [])

        # Get unfiltered jobs with SQL-based location/work filtering
        matching_status[user_id].update({
            'stage': 'fetching_jobs',
            'progress': 20,
            'message': 'Fetching jobs with location filters...'
        })

        t_query_start = time.time()
        jobs_to_filter = job_db_inst.get_unfiltered_jobs_for_user(
            user_id=user_id,
            user_cities=preferred_locs if preferred_locs else None,
            latest_day_only=latest_day_only
        )
        t_query = time.time() - t_query_start

        if preferred_locs:
            print(f"Found {len(jobs_to_filter)} jobs matching location filter: {preferred_locs} (query: {t_query:.2f}s)")
        else:
            print(f"Found {len(jobs_to_filter)} jobs (no location filter, query: {t_query:.2f}s)")

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

        # ✅ Location/work filtering done by SQL - jobs_to_filter already filtered!

        import json
        import numpy as np

        # Split jobs into date-based chunks (newest first) for progressive results
        chunks = split_into_date_chunks(jobs_to_filter, chunk_days=3)
        total_job_count = len(jobs_to_filter)

        print(f"\n📦 Split {total_job_count} jobs into {len(chunks)} date chunks:")
        for label, chunk_jobs in chunks:
            print(f"   {label}: {len(chunk_jobs)} jobs")

        # Initialize Claude analyzer once (shared across chunks)
        try:
            api_key = os.environ.get('ANTHROPIC_API_KEY')
            if api_key:
                analyzer = ClaudeJobAnalyzer(api_key=api_key, db=job_db_inst, user_email=user.get('email', 'unknown'))
                analyzer.set_profile_from_cv(profile)
            else:
                print("⚠️  No ANTHROPIC_API_KEY found, skipping Claude analysis")
                analyzer = None
        except Exception as e:
            print(f"⚠️  Could not initialize Claude analyzer: {e}")
            analyzer = None

        total_matches = []
        total_analyzed = 0
        jobs_processed = 0
        chunks_completed = 0

        # Progress range: 20-90% split equally across chunks
        progress_start = 20
        progress_end = 90
        progress_per_chunk = (progress_end - progress_start) / max(len(chunks), 1)

        for chunk_idx, (chunk_label, chunk_jobs) in enumerate(chunks):
            chunk_progress_base = progress_start + chunk_idx * progress_per_chunk

            matching_status[user_id].update({
                'stage': 'semantic_filtering',
                'progress': int(chunk_progress_base),
                'message': f'Chunk {chunk_idx+1}/{len(chunks)} ({chunk_label}): filtering {len(chunk_jobs)} jobs...',
                'total_jobs': total_job_count,
                'current_chunk': chunk_idx + 1,
                'total_chunks': len(chunks),
            })

            print(f"\n⚡ CHUNK {chunk_idx+1}/{len(chunks)} ({chunk_label}): {len(chunk_jobs)} jobs")

            # --- Load/encode embeddings for this chunk ---
            chunk_embeddings = {}
            chunk_needing_encoding = []

            for job in chunk_jobs:
                if job.get('embedding_jobbert_title'):
                    try:
                        embedding_json = job['embedding_jobbert_title']
                        if isinstance(embedding_json, str):
                            embedding_data = json.loads(embedding_json)
                        else:
                            embedding_data = embedding_json
                        chunk_embeddings[job['id']] = np.array(embedding_data)
                    except Exception as e:
                        print(f"  ⚠️  Failed to load embedding for job {job['id']}: {e}")
                        chunk_needing_encoding.append(job)
                else:
                    chunk_needing_encoding.append(job)

            if chunk_needing_encoding:
                for job in chunk_needing_encoding:
                    job_text = filter_module.build_job_text(job)
                    job_embedding = model.encode(job_text, show_progress_bar=False)
                    chunk_embeddings[job['id']] = job_embedding

            # --- Semantic filtering for this chunk ---
            chunk_matches = []
            for idx, job in enumerate(chunk_jobs):
                job_embedding = chunk_embeddings.get(job['id'])
                if job_embedding is None:
                    continue

                similarity = filter_module.calculate_similarity(cv_embedding, job_embedding)
                boosted_score, matched_keywords = filter_module.apply_keyword_boosts(
                    similarity, job, config_keywords
                )

                if boosted_score >= 0.30:
                    chunk_matches.append({
                        'job': job,
                        'score': int(boosted_score * 100),
                        'matched_keywords': matched_keywords
                    })

                # Update progress within chunk (first half of chunk's range = semantic)
                if (idx + 1) % 10 == 0 or idx == len(chunk_jobs) - 1:
                    semantic_progress = chunk_progress_base + (idx + 1) / len(chunk_jobs) * (progress_per_chunk * 0.4)
                    jobs_processed_so_far = jobs_processed + idx + 1
                    matching_status[user_id].update({
                        'progress': int(semantic_progress),
                        'message': f'Chunk {chunk_idx+1}/{len(chunks)}: filtered {idx+1}/{len(chunk_jobs)} jobs, {len(chunk_matches)} matches...',
                        'matches_found': len(total_matches) + len(chunk_matches),
                    })

            jobs_processed += len(chunk_jobs)
            print(f"  ✓ Semantic: {len(chunk_matches)} matches from {len(chunk_jobs)} jobs")

            # --- Save this chunk's semantic matches ---
            if chunk_matches:
                batch_matches = []
                for match in chunk_matches:
                    job = match['job']
                    match_reasoning = f"Matched keywords: {', '.join(match['matched_keywords'][:5])}" if match['matched_keywords'] else "Semantic similarity"
                    batch_matches.append({
                        'user_id': user_id,
                        'job_id': job['id'],
                        'semantic_score': match['score'],
                        'match_reasoning': match_reasoning
                    })
                saved_count = job_db_inst.add_user_job_matches_batch(batch_matches)
                print(f"  ✓ Saved {saved_count} semantic matches")

            # --- Claude analysis for this chunk's high-scoring matches ---
            chunk_analyzed = 0
            high_score = [m for m in chunk_matches if m['score'] >= 50]

            if high_score and analyzer:
                claude_progress_base = chunk_progress_base + progress_per_chunk * 0.4
                matching_status[user_id].update({
                    'stage': 'claude_analysis',
                    'progress': int(claude_progress_base),
                    'message': f'Chunk {chunk_idx+1}/{len(chunks)}: AI analyzing {len(high_score)} high-scoring matches...',
                })

                jobs_to_analyze = [match['job'] for match in high_score]

                try:
                    analyzed_jobs = analyzer.analyze_batch(jobs_to_analyze)
                except Exception as batch_error:
                    print(f"  ⚠️  Batch analysis failed for chunk: {batch_error}")
                    analyzed_jobs = []

                if analyzed_jobs:
                    # Process batch results
                    claude_batch_updates = []
                    for idx, job in enumerate(analyzed_jobs):
                        if 'match_score' in job:
                            key_alignments = job.get('key_alignments', [])
                            potential_gaps = job.get('potential_gaps', [])

                            if key_alignments and isinstance(key_alignments[0], dict):
                                key_alignments = [str(item) for item in key_alignments]
                            if potential_gaps and isinstance(potential_gaps[0], dict):
                                potential_gaps = [str(item) for item in potential_gaps]

                            claude_batch_updates.append({
                                'user_id': user_id,
                                'job_id': job['id'],
                                'claude_score': job['match_score'],
                                'priority': job.get('priority', 'medium'),
                                'match_reasoning': job.get('reasoning', ''),
                                'key_alignments': key_alignments,
                                'potential_gaps': potential_gaps,
                                'competency_mappings': job.get('competency_mappings', []),
                                'skill_mappings': job.get('skill_mappings', [])
                            })
                            chunk_analyzed += 1

                            # Update progress within Claude analysis portion
                            claude_progress = claude_progress_base + (idx + 1) / len(analyzed_jobs) * (progress_per_chunk * 0.6)
                            matching_status[user_id].update({
                                'progress': int(claude_progress),
                                'message': f'Chunk {chunk_idx+1}/{len(chunks)}: AI analyzed {idx+1}/{len(analyzed_jobs)} jobs...',
                                'jobs_analyzed': total_analyzed + chunk_analyzed,
                            })

                    # Save Claude results
                    if claude_batch_updates:
                        job_db_inst.add_user_job_matches_batch(claude_batch_updates)
                        print(f"  ✓ Saved {len(claude_batch_updates)} Claude analyses")

                    # Save competencies/skills
                    jobs_to_update_competencies = []
                    for job in analyzed_jobs:
                        if job.get('ai_competencies') or job.get('ai_key_skills'):
                            jobs_to_update_competencies.append({
                                'job_id': job['id'],
                                'ai_competencies': job.get('ai_competencies', []),
                                'ai_key_skills': job.get('ai_key_skills', [])
                            })
                    if jobs_to_update_competencies:
                        job_db_inst.update_jobs_competencies_batch(jobs_to_update_competencies)

            # --- Signal frontend: chunk completed (use counter, not boolean) ---
            total_matches.extend(chunk_matches)
            total_analyzed += chunk_analyzed
            chunks_completed += 1

            matching_status[user_id].update({
                'matches_found': len(total_matches),
                'jobs_analyzed': total_analyzed,
                'chunks_completed': chunks_completed,
            })
            print(f"  ✓ Chunk {chunk_idx+1}/{len(chunks)} complete ({len(chunk_matches)} matches, {chunk_analyzed} analyzed)")

        # All chunks done — update filter run time ONCE
        cv_manager_inst.update_filter_run_time(user_id)

        # Mark as completed
        matching_status[user_id] = {
            'status': 'completed',
            'stage': 'done',
            'progress': 100,
            'message': f'✅ Matching complete! Found {len(total_matches)} matches, analyzed {total_analyzed} with AI',
            'matches_found': len(total_matches),
            'jobs_analyzed': total_analyzed
        }

        print(f"\n{'='*60}")
        print(f"✅ Background job matching complete for user {user_id}")
        print(f"   Semantic matches: {len(total_matches)}")
        print(f"   Claude analyzed: {total_analyzed}")
        print(f"   Chunks processed: {len(chunks)}")
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
