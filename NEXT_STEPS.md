# Next Steps - Custom Job Matching Development

## Current Status

✅ **Infrastructure Complete**
- 3,800 jobs downloaded from Germany (last 7 days)
- Comprehensive AI metadata (99.4% coverage)
- All 50+ fields populated and indexed
- Error handling implemented and tested

## Phase 1: Analysis & Design (Recommended First Steps)

### 1.1 Analyze Current Matching Performance
**Goal:** Understand baseline to measure improvements against

**Tasks:**
- Run analysis on existing user_job_matches table
- Calculate distribution of semantic scores vs Claude scores
- Identify where Claude agrees/disagrees with semantic matching
- Measure false positives and false negatives (if user feedback available)

**SQL Queries:**
```sql
-- Score distribution
SELECT
    CASE
        WHEN semantic_score < 30 THEN '0-30%'
        WHEN semantic_score < 50 THEN '30-50%'
        WHEN semantic_score < 70 THEN '50-70%'
        WHEN semantic_score < 85 THEN '70-85%'
        ELSE '85-100%'
    END as score_range,
    COUNT(*) as jobs,
    AVG(claude_score) as avg_claude_score
FROM user_job_matches
WHERE user_id = 1
GROUP BY score_range
ORDER BY score_range;

-- Claude vs Semantic agreement
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN ABS(semantic_score - claude_score) < 10 THEN 1 ELSE 0 END) as close_agreement,
    SUM(CASE WHEN ABS(semantic_score - claude_score) >= 20 THEN 1 ELSE 0 END) as major_disagreement
FROM user_job_matches
WHERE claude_score IS NOT NULL;
```

### 1.2 Profile AI Metadata Quality
**Goal:** Understand which AI fields are most useful

**Tasks:**
- Analyze correlation between AI fields and match scores
- Identify most predictive features (skills, industries, experience level)
- Check data quality issues (missing values, inconsistencies)

**Script to create:**
```python
# scripts/analyze_ai_metadata.py
# - Calculate skill frequency vs match rate
# - Analyze industry distribution
# - Check experience level accuracy
```

### 1.3 User Profile Analysis
**Goal:** Extract structured data from user CV

**Tasks:**
- Parse user CV to extract:
  - Years of experience
  - Skills list (technical & soft skills)
  - Industry preferences
  - Previous job titles
  - Education level
- Create user profile table with structured fields
- Map user skills to job ai_key_skills

## Phase 2: Develop Custom Matching Algorithm

### 2.1 Skill-Based Matching
**Priority:** HIGH - Most objective matching criterion

**Algorithm:**
```python
def calculate_skill_match(user_skills, job_ai_key_skills):
    """
    Calculate skill overlap with weighted scoring

    Weights:
    - Exact match: 1.0
    - Related skill (from taxonomy): 0.7
    - Skill category match: 0.4
    """
    user_skills_set = set([s.lower() for s in user_skills])
    job_skills_set = set([s.lower() for s in job_ai_key_skills])

    exact_matches = user_skills_set & job_skills_set

    # Calculate match percentage
    if not job_skills_set:
        return 0

    match_score = len(exact_matches) / len(job_skills_set) * 100

    # Boost if user has MORE skills than required (overqualified)
    if len(user_skills_set) > len(job_skills_set):
        bonus = min(10, (len(user_skills_set) - len(job_skills_set)) * 2)
        match_score += bonus

    return min(match_score, 100)
```

### 2.2 Experience Level Matching
**Priority:** HIGH - Critical filter

**Algorithm:**
```python
def match_experience_level(user_years_experience, job_ai_experience_level):
    """
    Match user experience against job requirements

    Levels:
    - 0-2: Entry level
    - 2-5: Mid level
    - 5-10: Senior
    - 10+: Lead/Principal

    Rules:
    - Exact match: 100%
    - One level below: 80% (stretch opportunity)
    - One level above: 60% (may be overqualified)
    - Two+ levels mismatch: 0% (filter out)
    """
    level_map = {
        '0-2': 0,
        '2-5': 1,
        '5-10': 2,
        '10+': 3
    }

    user_level = (
        0 if user_years_experience < 2
        else 1 if user_years_experience < 5
        else 2 if user_years_experience < 10
        else 3
    )

    job_level = level_map.get(job_ai_experience_level, user_level)

    diff = abs(user_level - job_level)

    if diff == 0:
        return 100
    elif diff == 1:
        return 80 if job_level > user_level else 60
    else:
        return 0  # Filter out
```

### 2.3 Industry & Keywords Matching
**Priority:** MEDIUM - Helps with domain fit

**Algorithm:**
```python
def calculate_industry_match(user_industries, job_ai_taxonomies_a):
    """Simple industry overlap scoring"""
    if not job_ai_taxonomies_a:
        return 50  # Neutral if no industry tags

    user_set = set([i.lower() for i in user_industries])
    job_set = set([i.lower() for i in job_ai_taxonomies_a])

    overlap = user_set & job_set

    if overlap:
        return 100

    # Check for related industries (e.g., Technology & Engineering)
    related_pairs = {
        ('technology', 'engineering'),
        ('marketing', 'sales'),
        ('healthcare', 'social services'),
    }

    for user_ind in user_set:
        for job_ind in job_set:
            if (user_ind, job_ind) in related_pairs or (job_ind, user_ind) in related_pairs:
                return 70

    return 30  # Different industry = lower score
```

### 2.4 Work Arrangement Preference
**Priority:** HIGH - Hard requirement for many users

**Algorithm:**
```python
def filter_by_work_arrangement(jobs, user_preferences):
    """
    Filter jobs by work arrangement

    User preferences: ['Remote', 'Hybrid']
    Job values: 'Remote OK', 'Remote Solely', 'Hybrid', 'On-site'
    """
    preference_map = {
        'remote': ['Remote OK', 'Remote Solely'],
        'hybrid': ['Hybrid'],
        'onsite': ['On-site']
    }

    allowed_arrangements = []
    for pref in user_preferences:
        allowed_arrangements.extend(preference_map.get(pref.lower(), []))

    if not allowed_arrangements:
        return jobs  # No preference = accept all

    return [
        job for job in jobs
        if job.get('ai_work_arrangement') in allowed_arrangements
    ]
```

### 2.5 Combined Scoring Algorithm
**Priority:** HIGH - Brings everything together

```python
def calculate_custom_match_score(user_profile, job):
    """
    Multi-factor matching with configurable weights

    Default weights:
    - Skills: 40%
    - Experience level: 25%
    - Industry: 15%
    - Work arrangement: 10%
    - Semantic (CV-description): 10%
    """
    score = 0

    # 1. Skills (40%)
    skill_score = calculate_skill_match(
        user_profile['skills'],
        job.get('ai_key_skills', [])
    )
    score += skill_score * 0.40

    # 2. Experience level (25%)
    exp_score = match_experience_level(
        user_profile['years_experience'],
        job.get('ai_experience_level')
    )
    if exp_score == 0:
        return 0  # Hard filter - don't show mismatched levels
    score += exp_score * 0.25

    # 3. Industry (15%)
    industry_score = calculate_industry_match(
        user_profile['industries'],
        job.get('ai_taxonomies_a', [])
    )
    score += industry_score * 0.15

    # 4. Work arrangement (10%)
    arrangement = job.get('ai_work_arrangement')
    if arrangement and user_profile.get('work_arrangements'):
        if arrangement in user_profile['work_arrangements']:
            score += 10
        elif arrangement == 'On-site' and 'Remote' in user_profile['work_arrangements']:
            return 0  # Hard filter - user wants remote, job is onsite

    # 5. Semantic similarity (10%)
    # Use existing semantic matching on description
    semantic_score = calculate_semantic_similarity(
        user_profile['cv_text'],
        job.get('ai_core_responsibilities', '') + ' ' + job.get('ai_requirements_summary', '')
    )
    score += semantic_score * 0.10

    return min(score, 100)
```

## Phase 3: Implementation

### 3.1 Create User Profile Extraction
**File:** `src/matching/user_profile_extractor.py`

```python
class UserProfileExtractor:
    """Extract structured profile from user CV"""

    def extract_profile(self, cv_text):
        # Use existing semantic model or Claude to extract:
        # - Skills
        # - Years of experience
        # - Industries
        # - Education
        # - Preferences (work arrangement, salary)
        pass
```

### 3.2 Implement Custom Matcher
**File:** `src/matching/custom_matcher.py`

```python
class CustomJobMatcher:
    """Multi-factor job matching using AI metadata"""

    def match_jobs(self, user_id, jobs):
        # Get user profile
        user_profile = self.get_user_profile(user_id)

        # Apply hard filters
        filtered = self.apply_filters(jobs, user_profile)

        # Calculate scores
        scored = []
        for job in filtered:
            score = calculate_custom_match_score(user_profile, job)
            if score >= 30:  # Minimum threshold
                scored.append({
                    **job,
                    'custom_match_score': score
                })

        # Sort by score
        return sorted(scored, key=lambda x: x['custom_match_score'], reverse=True)
```

### 3.3 Integration with Existing System
**Approach:** Side-by-side comparison

- Keep existing semantic + Claude matching
- Add custom matching as separate column
- Display both scores to user
- Collect user feedback on which is more accurate
- Gradually shift to custom matching if it performs better

**UI Changes:**
```html
<div class="match-scores">
    <div>Semantic: {{ job.semantic_score }}%</div>
    <div>Claude: {{ job.claude_score }}%</div>
    <div>Custom AI: {{ job.custom_match_score }}%</div>
</div>
```

## Phase 4: Testing & Optimization

### 4.1 A/B Testing
- Split traffic: 50% see custom scores, 50% see semantic+Claude
- Track user engagement:
  - Which jobs do users view?
  - Which jobs do users apply to?
  - User feedback scores
- Measure accuracy improvements

### 4.2 Weight Tuning
- Experiment with different weight combinations
- Use user feedback to optimize weights
- Consider user-specific weights (preferences)

### 4.3 Performance Benchmarking
- Measure query speed (custom vs semantic)
- Optimize database queries with proper indexes
- Consider caching frequently accessed data

## Phase 5: Scale & Enhance

### 5.1 Expand Beyond Germany
- Download jobs from other countries
- Adapt for multi-country matching
- Handle location preferences

### 5.2 Real-time Updates
- Set up daily job downloads
- Incremental updates (only new/changed jobs)
- Archive old jobs (>30 days)

### 5.3 Advanced Features
- Salary range matching
- Company size/stage preferences
- Commute distance calculation
- Benefit matching
- Hiring manager insights

## Recommended Timeline

### Week 1: Analysis & Design
- Analyze current matching performance
- Profile AI metadata quality
- Design custom matching algorithm
- Create test plan

### Week 2: Core Implementation
- Extract user profile from CV
- Implement skill matching
- Implement experience level matching
- Build combined scoring function

### Week 3: Integration & Testing
- Integrate with existing system
- Side-by-side comparison UI
- Unit tests for matching logic
- Test with real user data

### Week 4: Optimization & Launch
- A/B testing setup
- Performance optimization
- User feedback collection
- Gradual rollout

## Success Metrics

1. **Accuracy Improvement**
   - Target: 20%+ increase in user satisfaction with matches
   - Measure: User feedback scores (thumbs up/down)

2. **Efficiency Gains**
   - Target: 50%+ reduction in Claude API costs
   - Method: Only send top 10% of matches to Claude for detailed analysis

3. **Coverage Increase**
   - Target: 100% of jobs have initial match score (vs current ~70%)
   - Current gap: Jobs without Claude analysis show "Matched keywords"

4. **Speed Improvement**
   - Target: <2 seconds for full matching pipeline
   - Current: ~5-10 seconds for semantic + Claude

## Risk Mitigation

1. **Risk:** Custom matching less accurate than Claude
   - **Mitigation:** Keep both systems, let user choose
   - **Fallback:** Revert to Claude if metrics decline

2. **Risk:** Skill extraction from CV is inaccurate
   - **Mitigation:** Allow user to manually edit profile
   - **Fallback:** Use Claude to verify extracted skills

3. **Risk:** AI metadata from API is incomplete
   - **Mitigation:** Fallback to semantic matching for missing fields
   - **Enhancement:** Build our own metadata extraction

## Next Immediate Actions

**Option A: Quick Win - Skill-based filtering (1-2 days)**
1. Extract top 10 skills from user CV manually
2. Filter jobs by skill overlap
3. Compare results with current matching
4. Show proof of concept

**Option B: Full Implementation (2-4 weeks)**
1. Follow Phase 1-3 above
2. Build comprehensive matching system
3. Integrate with UI for A/B testing

**Option C: Hybrid Approach (1 week)**
1. Use AI metadata for fast filtering (work arrangement, experience level)
2. Apply semantic matching to filtered set
3. Send only top 20% to Claude
4. Measure cost savings and accuracy

## Questions to Answer

1. **User preference:** Which jobs does the user actually apply to?
2. **Weight optimization:** What's the ideal mix of skills vs experience vs industry?
3. **Threshold tuning:** What's the minimum score that users find acceptable?
4. **Claude value:** When does Claude analysis add value over metadata matching?

---

**Recommendation:** Start with **Option C (Hybrid Approach)** for quick wins, then iterate toward full custom matching based on results.
