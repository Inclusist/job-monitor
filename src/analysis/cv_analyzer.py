"""
CV Analyzer - Uses Claude AI to parse CV text into structured profile data
"""

import json
from typing import Dict, Any
from anthropic import Anthropic


class CVAnalyzer:
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
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
                max_tokens=2000,
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

        prompt = f"""You are an expert CV/resume parser. Extract structured information from the following CV text.

CV TEXT:
{cv_text}

Extract the following information in JSON format:

{{
  "technical_skills": ["skill1", "skill2", ...],
  "soft_skills": ["skill1", "skill2", ...],
  "languages": [
    {{"language": "English", "level": "C1"}},
    {{"language": "German", "level": "B2"}}
  ],
  "certifications": ["cert1", "cert2", ...],
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
  "leadership_experience": ["Led team of 8 engineers", "Managed $2M budget", ...],
  "education": [
    {{
      "degree": "M.Sc. Computer Science",
      "institution": "University Name",
      "year": "2015",
      "honors": "summa cum laude"
    }}
  ],
  "highest_degree": "Master",
  "expertise_summary": "<2-3 sentence summary of key expertise and career focus>",
  "career_highlights": ["highlight1", "highlight2", ...],
  "industries": ["Industry1", "Industry2", ...]
}}

IMPORTANT EXTRACTION GUIDELINES:
- technical_skills: Extract ALL technical skills mentioned (programming languages, frameworks, tools, methodologies, platforms). Be comprehensive.
- soft_skills: Extract interpersonal and professional skills (leadership, communication, problem-solving, etc.)
- languages: Include all spoken/written languages with proficiency levels if mentioned (A1, A2, B1, B2, C1, C2, or descriptive like "fluent", "native")
- work_experience: List jobs in reverse chronological order. For each role, focus on concrete achievements and responsibilities.
- total_years_experience: Calculate by summing all work experience durations. Use decimals (e.g., 5.5 for 5 years 6 months)
- leadership_experience: Extract specific examples of leadership, management, or team coordination
- education: Include all degrees, certifications, and relevant coursework
- highest_degree: Choose from: "PhD", "Master", "Bachelor", "Associate", "High School", "Other"
- expertise_summary: Write a concise 2-3 sentence summary capturing the candidate's core expertise and career trajectory
- career_highlights: 3-5 most impressive achievements across entire career
- industries: List all industries the candidate has worked in

FORMATTING RULES:
- Be thorough but concise
- If information is not available in the CV, use empty arrays [] or null
- For total_years_experience, make your best estimate if exact dates aren't clear
- Ensure all JSON is valid and properly formatted
- Do not include explanatory text outside the JSON structure

Respond ONLY with valid JSON, no additional text or explanation."""

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

        # Sonnet 3.5 pricing (as of Dec 2024)
        # Input: $3 per million tokens
        # Output: $15 per million tokens
        input_cost = (input_tokens / 1_000_000) * 3.00
        output_cost = (output_tokens / 1_000_000) * 15.00

        return round(input_cost + output_cost, 4)

    @staticmethod
    def estimate_parsing_cost(text_length: int, model: str = "claude-3-5-sonnet-20241022") -> float:
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
        output_tokens = 800  # Expected structured output size

        # Sonnet pricing
        input_cost = (input_tokens / 1_000_000) * 3.00
        output_cost = (output_tokens / 1_000_000) * 15.00

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
