"""
Cover Letter Generator
Uses Claude AI to generate personalized cover letters based on CV and job details
"""

from anthropic import Anthropic
from typing import Dict, Optional


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
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        """
        Initialize cover letter generator
        
        Args:
            api_key: Anthropic API key
            model: Claude model to use
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model
    
    def generate_cover_letter(
        self,
        cv_profile: Dict,
        job: Dict,
        style: str = 'professional',
        language: str = 'english',
        claimed_data: Optional[Dict] = None
    ) -> Dict[str, str]:
        """
        Generate a personalized cover letter

        Args:
            cv_profile: User's parsed CV profile
            job: Job details dictionary
            style: Cover letter style (professional, technical, results, etc.)
            language: 'english' or 'german'
            claimed_data: Dict with 'competencies' and 'skills' keys containing user claims with evidence

        Returns:
            Dictionary with cover_letter text and metadata
        """

        if style not in self.STYLES:
            style = 'professional'

        style_info = self.STYLES[style]

        # Build context from CV
        expertise = cv_profile.get('expertise_summary', '')
        skills = cv_profile.get('skills', {})
        experience = cv_profile.get('work_experience', [])[:3]
        education = cv_profile.get('education', [])[:2]

        # Build prompt based on style and language
        prompt = self._build_prompt(
            cv_profile=cv_profile,
            job=job,
            style=style,
            style_info=style_info,
            language=language,
            claimed_data=claimed_data
        )
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            cover_letter = response.content[0].text.strip()
            
            return {
                'cover_letter': cover_letter,
                'style': style_info['name'],
                'language': language.capitalize(),
                'job_title': job.get('title'),
                'company': job.get('company')
            }
            
        except Exception as e:
            return {
                'error': f"Failed to generate cover letter: {str(e)}",
                'style': style_info['name'],
                'language': language.capitalize()
            }
    
    def _build_prompt(
        self,
        cv_profile: Dict,
        job: Dict,
        style: str,
        style_info: Dict,
        language: str,
        claimed_data: Optional[Dict] = None
    ) -> str:
        """Build the prompt for Claude based on style and language"""

        # Extract key info
        expertise = cv_profile.get('expertise_summary', '')
        skills = cv_profile.get('skills', {})
        experience = cv_profile.get('work_experience', [])[:3]
        education = cv_profile.get('education', [])[:2]
        name = cv_profile.get('name', 'Applicant')
        
        job_title = job.get('title', '')
        company = job.get('company', '')
        description = job.get('description', '')
        location = job.get('location', '')
        
        # Language-specific instructions
        if language == 'german':
            lang_instruction = """
Write the cover letter in GERMAN (Deutsch).
Use formal German business language: "Sie" form, proper formal greetings and closings.
Structure: "Sehr geehrte Damen und Herren," or "Sehr geehrte/r [Name]," (if hiring manager known)
Closing: "Mit freundlichen Grüßen"
"""
        else:
            lang_instruction = """
Write the cover letter in ENGLISH.
Use professional business English.
Greeting: "Dear Hiring Manager," or "Dear [Name]," (if known)
Closing: "Sincerely," or "Best regards,"
"""
        
        # Style-specific instructions
        style_instructions = {
            'professional': """
- Use formal, traditional business language
- Clear structure: opening, 2-3 body paragraphs, closing
- Emphasize qualifications and fit
- Professional tone throughout
- Traditional sign-off
""",
            'technical': """
- Emphasize specific technologies, tools, and methodologies
- Include technical achievements and metrics
- Reference relevant technical skills from the job description
- Show deep technical understanding
- Use industry-specific terminology appropriately
""",
            'results': """
- Lead with quantifiable achievements
- Include specific metrics and impact (%, $, growth numbers)
- Use action verbs: "achieved," "increased," "delivered"
- Focus on business outcomes and ROI
- Demonstrate track record of success
""",
            'conversational': """
- Warm, approachable tone while maintaining professionalism
- Show personality and cultural fit
- Use "I'm excited about" rather than "I am writing to express interest"
- More natural, less formal language
- Show enthusiasm genuinely
""",
            'enthusiastic': """
- Express genuine excitement about the role and company
- Show passion for the mission/product/industry
- Explain WHY you want THIS job at THIS company
- Connect personal values to company values
- Energetic but professional tone
""",
            'executive': """
- Strategic, high-level perspective
- Focus on leadership, vision, and business impact
- Mention team building, organizational change, strategic initiatives
- Demonstrate executive presence
- Less detail on technical execution, more on strategic direction
"""
        }
        
        style_guide = style_instructions.get(style, style_instructions['professional'])
        
        prompt = f"""Generate a compelling cover letter for this job application.

CANDIDATE PROFILE:
Name: {name}
Expertise: {expertise}

Key Technical Skills: {', '.join(skills.get('technical', [])[:8])}
Key Soft Skills: {', '.join(skills.get('soft', [])[:5])}

Recent Experience:
"""
        
        for exp in experience:
            prompt += f"- {exp.get('title', '')} at {exp.get('company', '')} ({exp.get('duration', '')})\n"

        prompt += f"""
Education:
"""
        for edu in education:
            prompt += f"- {edu.get('degree', '')} in {edu.get('field', '')} from {edu.get('institution', '')}\n"

        # Add claimed competencies and skills with evidence
        if claimed_data and (claimed_data.get('competencies') or claimed_data.get('skills')):
            prompt += f"""

CLAIMED COMPETENCIES & SKILLS WITH EVIDENCE:
The candidate has provided specific evidence for the following competencies and skills.
Use these as strong selling points in the cover letter - they have concrete examples backing them.
"""

            claimed_competencies = claimed_data.get('competencies', {})
            if claimed_competencies:
                prompt += "\nCompetencies (with evidence):\n"
                for comp_name, comp_data in list(claimed_competencies.items())[:8]:  # Limit to top 8
                    evidence = comp_data.get('evidence', '')
                    if evidence:
                        # Truncate evidence to keep prompt concise
                        evidence_short = evidence[:150] + "..." if len(evidence) > 150 else evidence
                        prompt += f"- {comp_name}: {evidence_short}\n"
                    else:
                        prompt += f"- {comp_name}\n"

            claimed_skills = claimed_data.get('skills', {})
            if claimed_skills:
                prompt += "\nTechnical Skills (with evidence):\n"
                for skill_name, skill_data in list(claimed_skills.items())[:10]:  # Limit to top 10
                    evidence = skill_data.get('evidence', '')
                    if evidence:
                        # Truncate evidence to keep prompt concise
                        evidence_short = evidence[:150] + "..." if len(evidence) > 150 else evidence
                        prompt += f"- {skill_name}: {evidence_short}\n"
                    else:
                        prompt += f"- {skill_name}\n"

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

REQUIREMENTS:
1. Address the specific requirements mentioned in the job description
2. Highlight relevant experience and skills that match this role
3. PRIORITIZE the claimed competencies and skills with evidence - these are the candidate's strongest selling points
4. When mentioning claimed competencies/skills, you can subtly reference the evidence (e.g., "demonstrated through..." or "proven experience in...")
5. Keep it to 3-4 paragraphs (250-350 words)
6. Include proper greeting and closing
7. Make it personal and compelling
8. Do NOT make up information not in the candidate profile
9. Use the applicant's name: {name}

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
