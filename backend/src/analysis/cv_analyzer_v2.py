
import json
from typing import Dict, Any
from anthropic import Anthropic
from src.analysis.cv_analyzer import CVAnalyzer

class CVAnalyzerV2(CVAnalyzer):
    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-20241022"):
        super().__init__(api_key, model)

    def _create_parsing_prompt(self, cv_text: str) -> str:
        """
        Create enhanced prompt for abstract meaning and semantic summary extraction
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
  "languages": [{{"language": "English", "level": "C1"}}],
  
  "semantic_summary": "A rich, executive-style bio (3-4 sentences). Synthesize their KEY value. Mention their seniority (e.g. 'Senior Leader'), the SCALE of systems they worked on (e.g. 'High-traffic distributed systems'), their primary DOMAIN focus, and their LEADERSHIP style.",
  
  "derived_seniority": "Junior|Mid|Senior|Staff|Principal|Head of|CTO",
  "extracted_role": "The best canonical job title for them (e.g. 'Staff Backend Engineer')",
  
  "domain_expertise": ["Fintech", "AdTech", "Health", "E-commerce", "B2B SaaS", ...],
  
  "search_keywords_abstract": "A space-separated string of 10-15 keywords that best describe what this person SHOULD be found for (including synonyms). e.g. 'Python Backend Distributed-Systems Tech-Lead System-Design'",

  "work_experience": [
    {{
      "title": "Job Title",
      "company": "Company Name",
      "duration": "2020-2023",
      "description": "Brief description",
      "key_achievements": ["achievement1", ...]
    }}
  ],
  "education": [],
  "total_years_experience": 10.5,
  "current_location": "City, Country",
  "preferred_work_locations": ["City, Country"],
  "desired_job_titles": ["Title1", "Title2"]
}}

GUIDELINES for Abstract Fields:
1. semantic_summary: Do NOT just list skills. Tell a story. "A seasoned engineering leader with 10+ years in Fintech, specializing in low-latency trading systems..."
2. derived_seniority: Look at their scope. Did they lead teams? Did they own architecture? Ignore "inflated" titles, look at responsibility.
3. domain_expertise: Infer this from the companies they worked at.
4. search_keywords_abstract: This will be used for vector matching. Include terms that imply their level and niche (e.g. "Scalability", "Mentoring", "Architecture" rather than just "Python").

Respond ONLY with valid JSON."""
        return prompt

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse response and ensure enhancements are present
        """
        profile = super()._parse_response(response_text)
        
        # Ensure new fields exist even if model missed them (unlikely with Sonnet)
        profile.setdefault('semantic_summary', profile.get('expertise_summary', ''))
        profile.setdefault('derived_seniority', 'Mid')
        profile.setdefault('domain_expertise', [])
        profile.setdefault('extracted_role', 'Software Engineer')
        profile.setdefault('search_keywords_abstract', '')
        
        return profile
