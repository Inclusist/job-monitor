"""
CV Analyzer - Uses Claude AI to parse CV text into structured profile data
"""

import json
from typing import Dict, Any
from anthropic import Anthropic


class CVAnalyzer:
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        """
        Initialize CV Analyzer with Claude API

        Args:
            api_key: Anthropic API key
            model: Claude model to use (Sonnet for better structured extraction)
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def analyze_cv(self, cv_text: str, user_email: str) -> Dict[str, Any]:
        """
        Parse CV text into structured profile data

        Args:
            cv_text: Extracted text from CV
            user_email: User's email for logging

        Returns:
            Dictionary with structured profile data
        """
        if not cv_text or len(cv_text.strip()) < 50:
            return self._get_default_profile("CV text too short or empty")

        try:
            prompt = self._create_parsing_prompt(cv_text)

            response = self.client.messages.create(
                model=self.model,
                max_tokens=2500,  # Increased for new fields
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = response.content[0].text
            profile = self._parse_response(response_text)

            # Add metadata
            profile['parsing_model'] = self.model
            profile['parsing_cost'] = self._estimate_cost(cv_text, response_text)
            profile['full_text'] = cv_text

            return profile

        except Exception as e:
            print(f"Error analyzing CV for {user_email}: {e}")
            return self._get_default_profile(f"Error during analysis: {str(e)}")

    def _create_parsing_prompt(self, cv_text: str) -> str:
        """
        Create detailed prompt for CV parsing

        Args:
            cv_text: CV text to parse

        Returns:
            Prompt string
        """
        # Truncate if too long (keep first 8000 chars)
        if len(cv_text) > 8000:
            cv_text = cv_text[:8000] + "\n...[truncated]"

        prompt = f"""You are an expert Executive Recruiter and Technical Hiring Manager.
Your goal is not just to "parse" this CV, but to "understand" the candidate's core value proposition, seniority, and potential.

CV TEXT:
{cv_text}

Analyze the CV and extract structured data in JSON format.
You MUST infer "Abstract" fields that might not be explicitly written, based on the depth of their experience.

Output JSON structure:
{{
  "technical_skills": ["skill1", "skill2", ...],
  "soft_skills": ["skill1", ...],
  "languages": [
    {{"language": "English", "level": "C1"}},
    {{"language": "German", "level": "B2"}}
  ],
  
  "semantic_summary": "A rich, executive-style bio (3-4 sentences). Synthesize their KEY value. Mention their seniority (e.g. 'Senior Leader'), the SCALE of systems they worked on (e.g. 'High-traffic distributed systems'), their primary DOMAIN focus, and their LEADERSHIP style.",
  
  "derived_seniority": "Junior|Mid|Senior|Staff|Principal|Head of|CTO",
  "extracted_role": "The best canonical job title for them (e.g. 'Staff Backend Engineer')",
  
  "domain_expertise": ["Fintech", "AdTech", "Health", "E-commerce", "B2B SaaS", ...],
  
  "competencies": [
    {{"name": "Strategic Leadership", "evidence": "Led the pivot to..."}},
    {{"name": "Hiring & Team Building", "evidence": "Recruited 2 data teams..."}}
  ],
  
  "search_keywords_abstract": "A space-separated string of 10-15 keywords that best describe what this person SHOULD be found for (including synonyms). e.g. 'Python Backend Distributed-Systems Tech-Lead System-Design'",

  "work_experience": [
    {{
      "title": "Job Title",
      "company": "Company Name",
      "duration": "2020-2023",
      "description": "Brief description of role",
      "key_achievements": ["achievement1", "achievement2", ...]
    }}
  ],
  "total_years_experience": 10.5,
  "leadership_experience": ["Led team of 8 engineers", ...],
  "education": [
    {{
      "degree": "M.Sc. Computer Science",
      "institution": "University Name",
      "year": "2015",
      "honors": "summa cum laude"
    }}
  ],
  "highest_degree": "Master",
  "expertise_summary": "<2-3 sentence summary - kept for backward compatibility>",
  "career_highlights": ["highlight1", ...],
  "industries": ["Industry1", ...],
  "certifications": [],
  "current_location": "City, Country",
  "preferred_work_locations": ["Location1", ...],
  "desired_job_titles": ["Title1", ...],
  "work_arrangement_preference": "remote/hybrid/onsite/flexible"
}}

GUIDELINES for Abstract Fields:
1. semantic_summary: Do NOT just list skills. Tell a story. "A seasoned engineering leader with 10+ years in Fintech..."
2. derived_seniority: Look at their scope. Did they lead teams? Did they own architecture? Ignore "inflated" titles, look at responsibility.
3. domain_expertise: Infer this from the companies they worked at.
4. competencies: This is CRITICAL. Look at their entire Work Experience.
   - Extract a COMPREHENSIVE list of 6-10 distinct competencies.
   - Ensure a balance of "Technical Leadership" (e.g. Architecture, Code Quality, Tech Stack Strategy), "Strategic Leadership" (e.g. Roadmap, Hiring), and "People Management" (e.g. Mentoring, Conflicts).
   - Valid examples: "Technical Leadership", "System Architecture", "Cloud Strategy", "Hiring & Team Building", "Stakeholder Management", "Budgeting", "Product Strategy".
   - For "evidence", paste the specific bullet point that proves it.
5. search_keywords_abstract: This will be used for vector matching. Include terms that imply their level and niche.

Respond ONLY with valid JSON, no additional text."""

        return prompt

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse and validate Claude's JSON response

        Args:
            response_text: Raw response from Claude

        Returns:
            Parsed profile dictionary
        """
        try:
            # Extract JSON from response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1

            if start == -1 or end == 0:
                raise ValueError("No JSON found in response")

            json_str = response_text[start:end]
            profile = json.loads(json_str)

            # Validate required fields exist
            required_fields = [
                'technical_skills', 'work_experience', 'education',
                'expertise_summary', 'total_years_experience'
            ]

            for field in required_fields:
                if field not in profile:
                    profile[field] = [] if field != 'total_years_experience' and field != 'expertise_summary' else None

            # Ensure proper types
            if not isinstance(profile.get('technical_skills'), list):
                profile['technical_skills'] = []
            if not isinstance(profile.get('soft_skills'), list):
                profile['soft_skills'] = []
            if not isinstance(profile.get('languages'), list):
                profile['languages'] = []
            if not isinstance(profile.get('work_experience'), list):
                profile['work_experience'] = []
            if not isinstance(profile.get('education'), list):
                profile['education'] = []

            # Default values for optional fields
            profile.setdefault('certifications', [])
            profile.setdefault('leadership_experience', [])
            profile.setdefault('career_highlights', [])
            profile.setdefault('industries', [])
            profile.setdefault('highest_degree', None)
            profile.setdefault('expertise_summary', '')

            # Default values for new fields
            profile.setdefault('current_location', None)
            profile.setdefault('preferred_work_locations', [])
            profile.setdefault('desired_job_titles', [])
            profile.setdefault('work_arrangement_preference', 'flexible')
            
            # Default values for new Abstract fields
            profile.setdefault('semantic_summary', profile.get('expertise_summary', ''))
            profile.setdefault('derived_seniority', 'Mid')
            profile.setdefault('domain_expertise', [])
            profile.setdefault('competencies', [])
            profile.setdefault('extracted_role', 'Software Engineer')
            profile.setdefault('search_keywords_abstract', '')

            return profile

        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Response text: {response_text[:500]}...")
            return self._get_default_profile("Failed to parse JSON response")

        except Exception as e:
            print(f"Error parsing response: {e}")
            return self._get_default_profile(f"Parsing error: {str(e)}")

    def _get_default_profile(self, reason: str) -> Dict[str, Any]:
        """
        Return a default profile structure when parsing fails

        Args:
            reason: Reason for failure

        Returns:
            Default profile dictionary
        """
        return {
            'technical_skills': [],
            'soft_skills': [],
            'languages': [],
            'certifications': [],
            'work_experience': [],
            'total_years_experience': 0,
            'leadership_experience': [],
            'education': [],
            'highest_degree': None,
            'expertise_summary': f'CV parsing incomplete: {reason}',
            'career_highlights': [],
            'industries': [],
            'current_location': None,
            'preferred_work_locations': [],
            'desired_job_titles': [],
            'work_arrangement_preference': 'flexible',
            'parsing_model': self.model,
            'parsing_cost': 0.0,
            'full_text': ''
        }

    def _estimate_cost(self, input_text: str, output_text: str) -> float:
        """
        Estimate Claude API cost for CV parsing

        Args:
            input_text: Input text sent to Claude
            output_text: Output received from Claude

        Returns:
            Estimated cost in USD
        """
        # Rough token estimation (1 token ≈ 4 characters)
        input_tokens = len(input_text) / 4
        output_tokens = len(output_text) / 4

        # Haiku pricing (as of Dec 2024)
        # Input: $0.25 per million tokens
        # Output: $1.25 per million tokens
        input_cost = (input_tokens / 1_000_000) * 0.25
        output_cost = (output_tokens / 1_000_000) * 1.25

        return round(input_cost + output_cost, 4)

    @staticmethod
    def estimate_parsing_cost(text_length: int, model: str = "claude-3-haiku-20240307") -> float:
        """
        Estimate cost before parsing

        Args:
            text_length: Length of CV text in characters
            model: Claude model being used

        Returns:
            Estimated cost in USD
        """
        # Rough estimates
        input_tokens = text_length / 4
        output_tokens = 1000  # Expected structured output size (increased for new fields)

        # Haiku pricing
        input_cost = (input_tokens / 1_000_000) * 0.25
        output_cost = (output_tokens / 1_000_000) * 1.25

        return round(input_cost + output_cost, 4)


if __name__ == "__main__":
    # Test the CV analyzer
    print("Testing CVAnalyzer...")

    # Sample CV text
    sample_cv = """
John Doe
Senior Software Engineer
john.doe@email.com | +1-234-567-8900 | San Francisco, CA

PROFESSIONAL SUMMARY
Experienced software engineer with 8+ years in full-stack development, specializing in Python,
React, and cloud architecture. Led teams of up to 10 engineers in building scalable web applications.

WORK EXPERIENCE

Senior Software Engineer | Tech Corp | 2020-Present
- Led development of microservices architecture serving 1M+ users
- Managed team of 6 engineers, conducted code reviews and mentoring
- Reduced system latency by 40% through optimization initiatives
- Technologies: Python, Django, React, PostgreSQL, AWS, Docker

Software Engineer | StartupXYZ | 2018-2020
- Developed RESTful APIs and frontend features
- Implemented CI/CD pipeline reducing deployment time by 60%
- Technologies: Node.js, Express, MongoDB, React

Junior Developer | WebCo | 2015-2018
- Built responsive web applications using modern JavaScript frameworks
- Collaborated with design team on UI/UX improvements

EDUCATION
M.S. Computer Science | Stanford University | 2015
B.S. Computer Engineering | UC Berkeley | 2013

SKILLS
Programming: Python, JavaScript, TypeScript, SQL, Go
Frameworks: Django, React, Node.js, Express
Cloud & DevOps: AWS, Docker, Kubernetes, CI/CD, Jenkins
Databases: PostgreSQL, MongoDB, Redis
Other: Agile, Scrum, Team Leadership, System Design

LANGUAGES
English (Native)
Spanish (Fluent - C1)
Mandarin (Conversational - B1)

CERTIFICATIONS
AWS Certified Solutions Architect - Professional (2022)
Certified Kubernetes Administrator (2021)
"""

    # Note: This test requires a valid Anthropic API key
    # Uncomment and provide key to test
    # import os
    # api_key = os.getenv('ANTHROPIC_API_KEY')
    # if api_key:
    #     analyzer = CVAnalyzer(api_key)
    #     profile = analyzer.analyze_cv(sample_cv, "test@example.com")
    #     print(json.dumps(profile, indent=2))
    # else:
    #     print("Set ANTHROPIC_API_KEY environment variable to test")

    # Test cost estimation
    estimated_cost = CVAnalyzer.estimate_parsing_cost(len(sample_cv))
    print(f"Estimated parsing cost: ${estimated_cost:.4f}")

    print("\nCVAnalyzer structure test completed!")
