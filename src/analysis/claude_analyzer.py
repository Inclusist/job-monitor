"""
Claude API integration for analyzing job matches
Uses Anthropic's Claude API to score and analyze job postings
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from anthropic import Anthropic
import time

logger = logging.getLogger(__name__)


class ClaudeJobAnalyzer:
    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-20241022", 
                 db=None, user_email: str = 'default@localhost'):
        """
        Initialize Claude analyzer
        
        Args:
            api_key: Anthropic API key
            model: Model to use (haiku for cost efficiency, sonnet for better quality)
            db: JobDatabase instance for feedback learning (optional)
            user_email: User email for personalized learning
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.profile = None
        self.db = db
        self.user_email = user_email
        self.learning_context = None
        
        # Initialize feedback learner if database is provided
        if db:
            from src.analysis.feedback_learner import FeedbackLearner
            self.learner = FeedbackLearner(db)
            self.learning_context = self.learner.generate_learning_context(user_email)
        else:
            self.learner = None
    
    def set_profile(self, profile: Dict[str, Any]):
        """Set user profile for analysis (from config.yaml)"""
        self.profile = profile

    def set_profile_from_cv(self, cv_profile: Dict[str, Any]):
        """
        Set profile from parsed CV data

        Converts CV profile structure to format expected by job analyzer

        Args:
            cv_profile: CV profile dictionary from database
        """
        # Transform CV profile to analyzer profile format
        self.profile = {
            'name': cv_profile.get('name', 'User'),
            'current_role': self._extract_current_role(cv_profile),
            'location': cv_profile.get('location', ''),
            'key_experience': self._format_key_experience(cv_profile),
            'technical_skills': cv_profile.get('technical_skills', []),
            'soft_skills': cv_profile.get('soft_skills', []),
            'languages': self._format_languages_simple(cv_profile.get('languages', [])),
            'work_experience': cv_profile.get('work_experience', []),
            'total_years_experience': cv_profile.get('total_years_experience', 0),
            'leadership_experience': cv_profile.get('leadership_experience', []),
            'education': cv_profile.get('education', []),
            'expertise_summary': cv_profile.get('expertise_summary', ''),
            'career_highlights': cv_profile.get('career_highlights', []),
            'industries': cv_profile.get('industries', []),
            'preferences': [],  # Can be added from user preferences
            # New AI-enhanced fields from CV
            'work_arrangement_preference': cv_profile.get('work_arrangement_preference', 'flexible'),
            'desired_job_titles': cv_profile.get('desired_job_titles', []),
            'current_location': cv_profile.get('current_location', ''),
            'preferred_work_locations': cv_profile.get('preferred_work_locations', [])
        }

    def _extract_current_role(self, cv_profile: Dict) -> str:
        """Extract current role from work experience"""
        work_exp = cv_profile.get('work_experience', [])
        if work_exp:
            # Assume first entry is most recent
            return work_exp[0].get('title', 'Professional')
        return 'Professional'

    def _format_key_experience(self, cv_profile: Dict) -> list:
        """Format key experience points from CV profile"""
        key_exp = []

        # Add years of experience
        years = cv_profile.get('total_years_experience', 0)
        if years > 0:
            key_exp.append(f"{years}+ years of professional experience")

        # Add leadership experience
        leadership = cv_profile.get('leadership_experience', [])
        if leadership:
            key_exp.extend(leadership[:3])  # Top 3

        # Add career highlights
        highlights = cv_profile.get('career_highlights', [])
        if highlights:
            key_exp.extend(highlights[:2])  # Top 2

        return key_exp

    def _format_languages_simple(self, languages: list) -> list:
        """Format languages for simple display"""
        if not languages:
            return []

        result = []
        for lang in languages:
            if isinstance(lang, dict):
                level = lang.get('level', '')
                result.append(f"{lang.get('language')} ({level})" if level else lang.get('language'))
            else:
                result.append(str(lang))

        return result
    
    def analyze_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single job posting against user profile
        
        Args:
            job: Job dictionary with title, company, description, etc.
            
        Returns:
            Analysis dictionary with match_score, priority, reasoning, etc.
        """
        if not self.profile:
            raise ValueError("Profile not set. Call set_profile() first.")
        
        prompt = self._create_analysis_prompt(job)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract text from response
            response_text = response.content[0].text
            
            # Parse JSON response
            analysis = self._parse_response(response_text)
            
            return analysis
            
        except Exception as e:
            print(f"Error analyzing job: {e}")
            return {
                'match_score': 0,
                'priority': 'low',
                'key_alignments': [],
                'potential_gaps': [],
                'reasoning': f'Error during analysis: {str(e)}'
            }
    
    def analyze_batch(self, jobs: list) -> list:
        """
        Analyze multiple jobs in batch
        Note: For now, we'll do sequential calls. Can optimize later.
        
        Args:
            jobs: List of job dictionaries
            
        Returns:
            List of jobs with analysis added
        """
        analyzed_jobs = []
        
        for i, job in enumerate(jobs):
            print(f"Analyzing job {i+1}/{len(jobs)}: {job.get('title')} at {job.get('company')}")
            
            analysis = self.analyze_job(job)
            job.update(analysis)
            analyzed_jobs.append(job)
            
            # Small delay to avoid rate limiting
            if i < len(jobs) - 1:
                time.sleep(0.5)
        
        return analyzed_jobs
    
    def _create_analysis_prompt(self, job: Dict[str, Any]) -> str:
        """Create the enhanced analysis prompt for Claude using rich AI metadata"""

        # Helper to safely format list items
        def format_list_item(item):
            if isinstance(item, dict):
                # Handle dict items (e.g., languages with level)
                if 'language' in item and 'level' in item:
                    return f"{item['language']} ({item['level']})"
                return str(item)
            return str(item)

        # Format key experience
        key_exp = self.profile.get('key_experience', []) or []
        key_exp_str = chr(10).join(f'- {format_list_item(exp)}' for exp in key_exp) if key_exp else '- Not specified'

        # Format technical skills
        tech_skills = self.profile.get('technical_skills', []) or []
        tech_skills_str = ', '.join(format_list_item(s) for s in tech_skills) if tech_skills else 'Not specified'

        # Format languages
        languages = self.profile.get('languages', []) or []
        languages_str = ', '.join(format_list_item(lang) for lang in languages) if languages else 'Not specified'

        # Format preferences
        prefs = self.profile.get('preferences', []) or []
        prefs_str = chr(10).join(f'- {format_list_item(pref)}' for pref in prefs) if prefs else '- Not specified'

        # Format work arrangement preference
        work_arrangement = self.profile.get('work_arrangement_preference', 'flexible')

        # Format preferred locations
        preferred_locs = self.profile.get('preferred_work_locations', []) or []
        preferred_locs_str = ', '.join(str(loc) for loc in preferred_locs) if preferred_locs else 'Not specified'

        # Get user's experience and industries for matching
        user_years = self.profile.get('total_years_experience', 0)
        user_industries = self.profile.get('industries', []) or []
        user_industries_str = ', '.join(user_industries) if user_industries else 'Not specified'

        profile_summary = f"""
**Candidate Profile:**
- Name: {self.profile.get('name')}
- Current Role: {self.profile.get('current_role')}
- Total Experience: {user_years} years
- Location: {self.profile.get('location')}
- Work Arrangement Preference: {work_arrangement}
- Preferred Work Locations: {preferred_locs_str}
- Industry Background: {user_industries_str}

**Key Experience:**
{key_exp_str}

**Technical Skills:**
{tech_skills_str}

**Languages:**
{languages_str}

**Preferences:**
{prefs_str}
"""

        # Extract rich AI metadata from job (all available fields)
        ai_key_skills = job.get('ai_key_skills', []) or []
        ai_keywords = job.get('ai_keywords', []) or []
        ai_core_responsibilities = job.get('ai_core_responsibilities', '')
        ai_requirements_summary = job.get('ai_requirements_summary', '')
        ai_experience_level = job.get('ai_experience_level', 'Not specified')
        ai_taxonomies_a = job.get('ai_taxonomies_a', []) or []
        ai_work_arrangement = job.get('ai_work_arrangement', 'Not specified')
        ai_employment_type = job.get('ai_employment_type', []) or []
        ai_benefits = job.get('ai_benefits', []) or []

        # Handle employment_type - could be string or array
        if isinstance(ai_employment_type, list):
            employment_type_str = ', '.join([str(et) for et in ai_employment_type if et]) if ai_employment_type else 'Not specified'
        else:
            employment_type_str = str(ai_employment_type) if ai_employment_type else 'Not specified'

        # Pre-calculate skill matches
        user_skills_set = set(skill.lower().strip() for skill in tech_skills if skill)
        job_skills_set = set(skill.lower().strip() for skill in ai_key_skills if skill)

        matching_skills = user_skills_set & job_skills_set
        missing_skills = job_skills_set - user_skills_set
        extra_skills = user_skills_set - job_skills_set

        # Calculate skill match percentage
        if job_skills_set:
            skill_match_pct = len(matching_skills) / len(job_skills_set) * 100
        else:
            skill_match_pct = 0

        # Format skill analysis
        matching_skills_str = ', '.join(sorted(matching_skills)) if matching_skills else 'None'
        missing_skills_str = ', '.join(sorted(missing_skills)[:10]) if missing_skills else 'None'
        extra_skills_str = ', '.join(sorted(extra_skills)[:10]) if extra_skills else 'None'

        # Industry match check
        job_industries_set = set(ind.lower().strip() for ind in ai_taxonomies_a if ind)
        user_industries_set = set(ind.lower().strip() for ind in user_industries if ind)
        matching_industries = user_industries_set & job_industries_set
        industry_match = 'Yes' if matching_industries else 'No'

        # Format job metadata sections
        job_skills_str = ', '.join(ai_key_skills[:15]) if ai_key_skills else 'Not specified'
        job_keywords_str = ', '.join(ai_keywords[:12]) if ai_keywords else 'Not specified'
        job_industries_str = ', '.join(ai_taxonomies_a) if ai_taxonomies_a else 'Not specified'
        job_benefits_str = ', '.join(ai_benefits[:8]) if ai_benefits else 'Not specified'

        job_details = f"""
**Job Posting:**
- Title: {job.get('title')}
- Company: {job.get('company')}
- Location: {job.get('location')}
- Posted: {job.get('posted_date', 'Unknown')}
- Salary: {job.get('salary', 'Not specified')}

**AI-Extracted Job Requirements:**
- Required Skills: {job_skills_str}
- Experience Level: {ai_experience_level}
- Industries: {job_industries_str}
- Keywords: {job_keywords_str}
- Work Arrangement: {ai_work_arrangement}
- Employment Type: {employment_type_str}
- Benefits: {job_benefits_str}

**Core Responsibilities (AI Summary):**
{ai_core_responsibilities or 'Not available'}

**Requirements Summary (AI Summary):**
{ai_requirements_summary or 'Not available'}

**PRE-CALCULATED MATCH ANALYSIS:**
- Skill Match: {skill_match_pct:.1f}% ({len(matching_skills)}/{len(job_skills_set)} required skills)
- Matching Skills: {matching_skills_str}
- Missing Skills: {missing_skills_str}
- Additional Skills (Candidate): {extra_skills_str}
- Industry Match: {industry_match}
- Experience Match: User has {user_years} years, Job requires {ai_experience_level}
"""

        # Add learning context if available
        learning_section = ""
        if self.learning_context:
            learning_section = self.learning_context

        prompt = f"""You are an expert career advisor. Analyze this job posting against the candidate's profile using the PRE-CALCULATED MATCH ANALYSIS provided.

{profile_summary}

{job_details}

{learning_section}

**Analysis Task:**
Evaluate this job opportunity and provide your assessment in the following JSON format:

{{
  "match_score": <number 0-100>,
  "priority": "<high|medium|low>",
  "key_alignments": ["<alignment 1>", "<alignment 2>", ...],
  "potential_gaps": ["<gap 1>", "<gap 2>", ...],
  "reasoning": "<2-3 sentence summary explaining the match score and priority>"
}}

**Enhanced Scoring Guidelines (Use Pre-Calculated Data):**

**Base Score (Skills + Experience):**
- Skill Match ≥80%: Start at 85-90
- Skill Match 60-79%: Start at 75-84
- Skill Match 40-59%: Start at 60-74
- Skill Match 20-39%: Start at 45-59
- Skill Match <20%: Start at 30-44

**Adjustments:**
- Experience match (within 1-2 years of requirement): +5 points
- Experience mismatch (too junior by 3+ years): -10 points
- Experience mismatch (too senior by 5+ years): -5 points
- Industry match: +5 points
- Work arrangement match: +5 points
- Work arrangement mismatch: -10 to -15 points
- Location match: +3 points
- Benefits/compensation attractive: +2-5 points

**Final Score Ranges:**
- 90-100: Exceptional match (80%+ skill match, experience aligned, industry match)
- 80-89: Strong match (60-79% skills or strong compensating factors)
- 70-79: Good match (40-59% skills or acceptable gaps)
- 60-69: Moderate match (stretch opportunity, significant learning required)
- Below 60: Weak match (fundamental gaps)

**Priority Guidelines:**
- High: Score 85+, strong alignment with career goals, good location/company
- Medium: Score 70-84, decent fit with some reservations
- Low: Score below 70, significant gaps or misalignment

**Key Alignment Examples:**
- "Strong skill overlap: Python, SQL, Machine Learning"
- "Experience level matches: 5 years required, candidate has 6 years"
- "Industry alignment: Both in Technology/Finance"
- "Work arrangement compatible: Remote preference, Remote job"

**Potential Gap Examples:**
- "Missing required skills: AWS, Kubernetes, Docker"
- "Experience gap: Requires 8+ years, candidate has 3 years"
- "No industry experience in Healthcare (job requirement)"
- "Work arrangement mismatch: Onsite required, candidate prefers remote"

**Critical Notes:**
1. **USE the pre-calculated data** - don't recalculate skill matches from scratch
2. **Work arrangement compatibility is critical** - a mismatch should lower score by 10-15 points
3. **Focus on gaps that matter** - missing "nice-to-have" skills ≠ dealbreaker
4. **Be realistic** - most jobs won't be 90+ matches, that's okay

Respond ONLY with valid JSON, no additional text.
"""
        
        return prompt
    
    def _calculate_priority(self, score: int) -> str:
        """
        Calculate priority based on match score
        
        Args:
            score: Match score (0-100)
            
        Returns:
            Priority level: 'high', 'medium', or 'low'
        """
        if score >= 85:
            return 'high'
        elif score >= 70:
            return 'medium'
        else:
            return 'low'
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude's JSON response"""
        try:
            # Try to find JSON in the response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            
            if start != -1 and end != 0:
                json_str = response_text[start:end]
                analysis = json.loads(json_str)
                
                # Validate required fields
                required_fields = ['match_score', 'priority', 'key_alignments', 
                                 'potential_gaps', 'reasoning']
                
                for field in required_fields:
                    if field not in analysis:
                        analysis[field] = [] if field in ['key_alignments', 'potential_gaps'] else ''
                
                # FIX: Validate priority matches the score guidelines
                # Sometimes Claude returns incorrect priority despite clear guidelines
                score = analysis.get('match_score', 0)
                correct_priority = self._calculate_priority(score)
                
                if analysis.get('priority') != correct_priority:
                    logger.warning(
                        f"Priority mismatch: Claude returned '{analysis.get('priority')}' "
                        f"for score {score}, correcting to '{correct_priority}'"
                    )
                    analysis['priority'] = correct_priority
                
                return analysis
            else:
                raise ValueError("No JSON found in response")
                
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Response text: {response_text}")
            
            # Return default low-score analysis
            return {
                'match_score': 50,
                'priority': 'low',
                'key_alignments': [],
                'potential_gaps': ['Unable to analyze'],
                'reasoning': 'Analysis failed due to parsing error'
            }


def test_analyzer():
    """Test function"""
    from dotenv import load_dotenv
    import yaml
    
    load_dotenv()
    
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize analyzer
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set in .env file")
        return
    
    analyzer = ClaudeJobAnalyzer(api_key)
    analyzer.set_profile(config['profile'])
    
    # Test job
    test_job = {
        'title': 'Head of AI - Driving Innovation',
        'company': 'Volkswagen Group Innovation',
        'location': 'Wolfsburg, Germany',
        'posted_date': '2024-12-15',
        'description': """
        We are looking for a visionary leader with proven expertise in AI.
        Lead a group of AI developers driving innovation across domains.
        Strong track record of leading AI teams and projects required.
        Experience in automotive industry preferred.
        Deep expertise in machine learning, deep learning, and generative AI.
        German B2 and English C1 required.
        """
    }
    
    print("Testing Claude analyzer...")
    analysis = analyzer.analyze_job(test_job)
    
    print("\nAnalysis Result:")
    print(f"Match Score: {analysis['match_score']}")
    print(f"Priority: {analysis['priority']}")
    print(f"Key Alignments: {analysis['key_alignments']}")
    print(f"Potential Gaps: {analysis['potential_gaps']}")
    print(f"Reasoning: {analysis['reasoning']}")


if __name__ == "__main__":
    test_analyzer()
