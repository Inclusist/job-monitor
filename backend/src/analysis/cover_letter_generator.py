"""
Cover Letter Generator
Uses Claude AI to generate personalized cover letters based on CV and job details
"""

from anthropic import Anthropic
from typing import Dict, Optional
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import logging

logger = logging.getLogger(__name__)


class CoverLetterGenerator:
    """Generates personalized cover letters using Claude AI"""
    
    STYLES = {
        'professional': {
            'name': 'Professional & Formal',
            'description': 'Traditional business tone, structured format',
            'best_for': 'Corporate roles, finance, consulting, traditional industries'
        },
        'technical': {
            'name': 'Technical & Detailed',
            'description': 'Emphasizes technical skills and methodologies',
            'best_for': 'Engineering, data science, DevOps roles'
        },
        'results': {
            'name': 'Results-Oriented',
            'description': 'Focus on achievements and measurable impact',
            'best_for': 'Sales, marketing, growth roles, target-driven positions'
        },
        'conversational': {
            'name': 'Modern & Conversational',
            'description': 'Friendly yet professional, shows personality',
            'best_for': 'Startups, tech companies, creative agencies'
        },
        'enthusiastic': {
            'name': 'Enthusiastic & Passionate',
            'description': 'Shows genuine excitement and cultural fit',
            'best_for': 'Mission-driven companies, startups'
        },
        'executive': {
            'name': 'Executive & Strategic',
            'description': 'High-level thinking, leadership perspective',
            'best_for': 'Senior/leadership positions, C-suite roles'
        }
    }
    
    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-20241022",
                 gemini_api_key: Optional[str] = None):
        """
        Initialize cover letter generator

        Args:
            api_key: Anthropic API key (Claude - fallback)
            model: Claude model to use
            gemini_api_key: Google Gemini API key (primary, optional)
        """
        # Claude client (fallback)
        self.client = Anthropic(api_key=api_key)
        self.model = model

        # Gemini client (primary)
        self.gemini_model = None
        if gemini_api_key:
            genai.configure(api_key=gemini_api_key)
            # Use system instruction to enforce strict output format
            system_instruction = (
                "You are an expert cover letter writer. "
                "You MUST return ONLY the cover letter text itself. "
                "Do NOT include any introduction, conversational filler (like 'Here is the cover letter'), "
                "markdown code fences, or post-generation comments. "
                "The response should start with the greeting and end with the applicant's name."
            )
            self.gemini_model = genai.GenerativeModel(
                model_name='gemini-2.5-flash',
                system_instruction=system_instruction
            )
    
    def generate_cover_letter(
        self,
        cv_profile: Dict,
        job: Dict,
        style: str = 'professional',
        language: str = 'english',
        instructions: str = ''
    ) -> Dict[str, str]:
        """
        Generate a personalized cover letter

        Args:
            cv_profile: User's parsed CV profile
            job: Job details dictionary
            style: Cover letter style (professional, technical, results, etc.)
            language: 'english' or 'german'
            instructions: Optional user instructions to guide generation

        Returns:
            Dictionary with cover_letter text and metadata
        """

        if style not in self.STYLES:
            style = 'professional'

        style_info = self.STYLES[style]

        # Build prompt based on style and language
        prompt = self._build_prompt(
            cv_profile=cv_profile,
            job=job,
            style=style,
            style_info=style_info,
            language=language,
            instructions=instructions
        )

        api_used = None
        cover_letter = None

        try:
            # TRY GEMINI FIRST
            if self.gemini_model:
                try:
                    cover_letter = self._generate_with_gemini(prompt)
                    api_used = 'gemini'
                    logger.info(f"Cover letter generated with Gemini | Style: {style} | Language: {language}")
                except Exception as gemini_error:
                    logger.warning(f"Gemini failed, falling back to Claude: {gemini_error}")

            # FALLBACK TO CLAUDE
            if cover_letter is None:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4000,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                cover_letter = response.content[0].text.strip()
                api_used = 'claude'
                logger.info(f"Cover letter generated with Claude (fallback: {self.gemini_model is not None})")

            # Clean up any conversational filler or code fences
            if cover_letter:
                # Remove common markdown code fences
                if cover_letter.startswith('```'):
                    lines = cover_letter.split('\n')
                    if lines[0].startswith('```'):
                        lines = lines[1:]
                    if lines and lines[-1].startswith('```'):
                        lines = lines[:-1]
                    cover_letter = '\n'.join(lines).strip()
                
                # Remove common preambles
                preambles = [
                    "Here's the cover letter:",
                    "Here is the cover letter:",
                    "Sure, here's a cover letter",
                    "Sure, here is a cover letter",
                    "I have generated a cover letter",
                    "Based on the information provided",
                ]
                for preamble in preambles:
                    if cover_letter.lower().startswith(preamble.lower()):
                        cover_letter = cover_letter[len(preamble):].strip()
                        # Remove leading colon if present
                        if cover_letter.startswith(':'):
                            cover_letter = cover_letter[1:].strip()
                        break

            return {
                'cover_letter': cover_letter,
                'style': style_info['name'],
                'language': language.capitalize(),
                'job_title': job.get('title'),
                'company': job.get('company'),
                'api_used': api_used
            }

        except Exception as e:
            logger.error(f"Both APIs failed: {e}")
            return {
                'error': f"Failed to generate cover letter: {str(e)}",
                'style': style_info['name'],
                'language': language.capitalize()
            }

    def _generate_with_gemini(self, prompt: str) -> str:
        """
        Generate cover letter using Gemini API

        Args:
            prompt: Complete prompt string

        Returns:
            str: Generated cover letter text

        Raises:
            Exception: If Gemini API call fails
        """
        if not self.gemini_model:
            raise ValueError("Gemini not configured")

        response = self.gemini_model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=4000,
                temperature=0.7,
                top_p=0.9,
            )
        )

        # Validate response
        if not response.text or len(response.text.strip()) < 100:
            raise ValueError("Gemini returned empty/invalid response")

        return response.text.strip()

    def _build_prompt(
        self,
        cv_profile: Dict,
        job: Dict,
        style: str,
        style_info: Dict,
        language: str,
        instructions: str = ''
    ) -> str:
        """Build the prompt for Claude based on style and language"""
        
        # Extract key info
        expertise = cv_profile.get('expertise_summary', '')
        technical_skills = cv_profile.get('technical_skills', [])
        soft_skills = cv_profile.get('soft_skills', [])
        experience = cv_profile.get('work_experience', [])[:3]
        education = cv_profile.get('education', [])[:2]
        projects = cv_profile.get('projects', [])
        name = cv_profile.get('name', 'Applicant')
        
        job_title = job.get('title', '')
        company = job.get('company', '')
        description = job.get('description', '')
        location = job.get('location', '')
        
        # Language-specific instructions
        if language == 'german':
            lang_instruction = f"""
Write the cover letter in GERMAN (Deutsch).
Use formal German business language: "Sie" form, proper formal greetings and closings.
Structure: "Sehr geehrte Damen und Herren," or "Sehr geehrte/r [Name]," (if hiring manager known)
Closing: "Mit freundlichen Grüßen," followed by the applicant's name: {name}
"""
        else:
            lang_instruction = f"""
Write the cover letter in ENGLISH.
Use professional business English.
Greeting: "Dear Hiring Manager," or "Dear [Name]," (if known)
Closing: "Sincerely," or "Best regards," followed by the applicant's name: {name}
"""

        # Style-specific instructions
        style_instructions = {
            'professional': """
- Use formal, traditional business language
- Clear structure: opening, 2-3 body paragraphs, closing
- Emphasize qualifications and fit
- Professional tone throughout
- Traditional sign-off with the applicant's name
""",
            'technical': """
- Emphasize specific technologies, tools, and methodologies
- Include technical achievements and metrics
- Reference relevant technical skills from the job description
- Show deep technical understanding
- Use industry-specific terminology appropriately
- Professional sign-off with the applicant's name
""",
            'results': """
- Lead with quantifiable achievements
- Include specific metrics and impact (%, $, growth numbers)
- Use action verbs: "achieved," "increased," "delivered"
- Focus on business outcomes and ROI
- Demonstrate track record of success
- Professional sign-off with the applicant's name
""",
            'conversational': """
- Warm, approachable tone while maintaining professionalism
- Show personality and cultural fit
- Use "I'm excited about" rather than "I am writing to express interest"
- More natural, less formal language
- Show enthusiasm genuinely
- Friendly but professional sign-off with the applicant's name
""",
            'enthusiastic': """
- Express genuine excitement about the role and company
- Show passion for the mission/product/industry
- Explain WHY you want THIS job at THIS company
- Connect personal values to company values
- Energetic but professional tone
- Passionate sign-off with the applicant's name
""",
            'executive': """
- Strategic, high-level perspective
- Focus on leadership, vision, and business impact
- Mention team building, organizational change, strategic initiatives
- Demonstrate executive presence
- Less detail on technical execution, more on strategic direction
- Executive sign-off with the applicant's name
"""
        }
        
        style_guide = style_instructions.get(style, style_instructions['professional'])
        
        prompt = f"""Generate a compelling cover letter for this job application.

**CRITICAL INSTRUCTION:** Do NOT include any preamble, introduction, or conversational filler like "Here is the cover letter:". Start your response IMMEDIATELY with the greeting (e.g., "Dear Hiring Manager,"). Do NOT use markdown code fences.

CANDIDATE PROFILE:
Name: {name}
Expertise: {expertise}

Key Technical Skills: {', '.join(technical_skills[:8])}
Key Soft Skills: {', '.join(soft_skills[:5])}

Recent Experience:
"""
        
        for exp in experience:
            if isinstance(exp, dict):
                prompt += f"- {exp.get('title', '')} at {exp.get('company', '')} ({exp.get('duration', '')})\n"
            else:
                prompt += f"- {exp}\n"
        
        prompt += f"""
Education:
"""
        for edu in education:
            if isinstance(edu, dict):
                prompt += f"- {edu.get('degree', '')} in {edu.get('field', '')} from {edu.get('institution', '')}\n"
            else:
                prompt += f"- {edu}\n"

        # Add projects section if available
        if projects:
            prompt += f"""
Projects:
"""
            for proj in projects:
                if isinstance(proj, dict):
                    proj_name = proj.get('name', '')
                    proj_desc = proj.get('description', '')
                    proj_url = proj.get('url', '')
                    prompt += f"- {proj_name}"
                    if proj_url:
                        prompt += f" ({proj_url})"
                    if proj_desc:
                        prompt += f": {proj_desc}"
                    prompt += "\n"
                else:
                    prompt += f"- {proj}\n"

        prompt += f"""

JOB DETAILS:
Position: {job_title}
Company: {company}
Location: {location}

Job Description:
{description[:1000]}

STYLE: {style_info['name']}
{style_guide}

LANGUAGE:
{lang_instruction}

{"USER INSTRUCTIONS:" + chr(10) + instructions + chr(10) + "Follow these instructions carefully when writing the cover letter." + chr(10) if instructions else ""}REQUIREMENTS:
1. Address the specific requirements mentioned in the job description
2. Highlight relevant experience and skills that match this role
3. Keep it to 3-4 paragraphs (250-350 words)
4. Include proper greeting and closing
5. Make it personal and compelling
6. Do NOT make up information not in the candidate profile
7. Use the applicant's name: {name}

Generate the cover letter now:
"""
        
        return prompt


def test_generator():
    """Test the cover letter generator"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not found")
        return
    
    # Mock data
    mock_cv = {
        'name': 'John Doe',
        'expertise_summary': 'Senior Data Scientist with 8+ years experience in ML and AI',
        'skills': {
            'technical': ['Python', 'TensorFlow', 'PyTorch', 'SQL', 'AWS', 'Docker'],
            'soft': ['Leadership', 'Communication', 'Problem Solving']
        },
        'work_experience': [
            {'title': 'Senior Data Scientist', 'company': 'Tech Corp', 'duration': '2020-Present'},
            {'title': 'Data Scientist', 'company': 'StartupCo', 'duration': '2017-2020'}
        ],
        'education': [
            {'degree': 'M.Sc.', 'field': 'Computer Science', 'institution': 'TU Berlin'}
        ]
    }
    
    mock_job = {
        'title': 'Head of Data Science',
        'company': 'Volkswagen AG',
        'location': 'Wolfsburg, Germany',
        'description': 'We are seeking an experienced Head of Data Science to lead our AI initiatives...'
    }
    
    generator = CoverLetterGenerator(api_key)
    
    print("=" * 60)
    print("Testing Cover Letter Generator")
    print("=" * 60)
    
    # Test English Professional
    print("\n📝 Style: Professional & Formal (English)")
    print("-" * 60)
    result = generator.generate_cover_letter(mock_cv, mock_job, style='professional', language='english')
    if 'error' in result:
        print(f"Error: {result['error']}")
    else:
        print(result['cover_letter'])
    
    print("\n" + "=" * 60)
    
    # Test German Technical
    print("\n📝 Style: Technical & Detailed (German)")
    print("-" * 60)
    result = generator.generate_cover_letter(mock_cv, mock_job, style='technical', language='german')
    if 'error' in result:
        print(f"Error: {result['error']}")
    else:
        print(result['cover_letter'])


if __name__ == "__main__":
    test_generator()
