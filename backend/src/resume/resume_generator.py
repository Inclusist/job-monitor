"""
Resume Generator using Claude AI

Generates tailored, ATS-optimized resumes based on:
- User's CV profile
- Job requirements
- User-claimed competencies/skills with evidence
"""
from anthropic import Anthropic
from typing import Dict, List, Any, Optional
import json
import re
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import logging

logger = logging.getLogger(__name__)


class ResumeGenerator:
    """Generate tailored resumes using Claude AI"""

    def __init__(self, anthropic_api_key: str, gemini_api_key: Optional[str] = None):
        """
        Initialize resume generator

        Args:
            anthropic_api_key: Anthropic API key (Claude - fallback)
            gemini_api_key: Google Gemini API key (primary, optional)
        """
        # Claude client (fallback)
        self.client = Anthropic(api_key=anthropic_api_key)
        self.model = "claude-haiku-4-5-20251001"  # Use Haiku (faster and cheaper, still high quality)

        # Gemini client (primary)
        self.gemini_model = None
        if gemini_api_key:
            genai.configure(api_key=gemini_api_key)
            # Use system instruction to enforce strict output format
            system_instruction = (
                "You are an expert resume writer. "
                "You MUST return ONLY valid HTML. "
                "Do NOT include any introduction, conversational filler, or markdown code fences. "
                "Start your response immediately with <!DOCTYPE html> and end with </html>."
            )
            self.gemini_model = genai.GenerativeModel(
                model_name='gemini-2.5-flash',
                system_instruction=system_instruction
            )

    def generate_resume_html(self, user_profile: Dict, job: Dict,
                            claimed_data: Optional[Dict] = None,
                            user_info: Optional[Dict] = None,
                            instructions: str = '',
                            language: str = 'english') -> str:
        """
        Generate tailored resume HTML using Claude

        Args:
            user_profile: User's CV profile dict
            job: Job details dict
            claimed_data: Dict with 'competencies' and 'skills' keys (optional)
            user_info: Dict with 'name', 'email', 'phone' keys for resume header (optional)
            instructions: Optional user instructions to guide generation
            language: 'english' or 'german' (default: 'english')

        Returns:
            str: Professional HTML resume
        """
        prompt = self._build_prompt(user_profile, job, claimed_data, user_info, instructions, language)

        html_content = None
        api_used = None

        try:
            # TRY GEMINI FIRST
            if self.gemini_model:
                try:
                    html_content = self._generate_with_gemini(prompt)
                    api_used = 'gemini'
                    logger.info(f"Resume generated with Gemini | Job: {job.get('id')} | Length: {len(html_content)}")
                except Exception as gemini_error:
                    logger.warning(f"Gemini failed, falling back to Claude: {gemini_error}")

            # FALLBACK TO CLAUDE
            if html_content is None:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=8192,  # Increased for longer resumes
                    temperature=0.7,  # Slightly creative but professional
                    messages=[{"role": "user", "content": prompt}]
                )
                html_content = response.content[0].text
                api_used = 'claude'
                logger.info(f"Resume generated with Claude (fallback: {self.gemini_model is not None})")

            # Robust extraction of HTML content (strips markdown fences and preambles)
            if html_content:
                # Find start of HTML
                start_idx = html_content.find('<!DOCTYPE html>')
                if start_idx == -1:
                    start_idx = html_content.find('<html')
                
                # Find end of HTML
                end_idx = html_content.rfind('</html>')
                if end_idx != -1:
                    end_idx += 7 # Length of </html>
                
                if start_idx != -1 and end_idx != -1:
                    html_content = html_content[start_idx:end_idx]
                elif start_idx != -1:
                    html_content = html_content[start_idx:]

            # Convert markdown formatting to HTML for both APIs
            html_content = self._convert_markdown_to_html(html_content)

            # Log API usage for analytics
            logger.info(f"Resume generation complete | API: {api_used}")
            return html_content.strip()

        except Exception as e:
            logger.error(f"Both APIs failed for resume generation: {e}")
            raise

    def _generate_with_gemini(self, prompt: str) -> str:
        """
        Generate resume HTML using Gemini API

        Args:
            prompt: Complete prompt string

        Returns:
            str: Generated HTML content

        Raises:
            Exception: If Gemini API call fails or returns invalid HTML
        """
        if not self.gemini_model:
            raise ValueError("Gemini not configured")

        response = self.gemini_model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=8192,  # Match Claude's limit
                temperature=0.7,
                top_p=0.9,
            )
        )

        # Validate response
        if not response.text:
            raise ValueError("Gemini returned empty response")

        html_content = response.text.strip()

        # Validate HTML structure presence (extraction happens in main function)
        if '<!DOCTYPE html>' not in html_content or '</html>' not in html_content:
            # Check for <html tag as fallback
            if '<html' not in html_content:
                raise ValueError("Gemini did not return valid HTML")

        return html_content

    def _convert_markdown_to_html(self, text: str) -> str:
        """
        Convert common markdown syntax to HTML tags

        Args:
            text: Text potentially containing markdown

        Returns:
            str: Text with markdown converted to HTML
        """
        # Convert **bold** to <strong>bold</strong>
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)

        # Convert *italic* to <em>italic</em> (but not if already in <strong>)
        text = re.sub(r'(?<!</strong>)\*([^*]+?)\*(?!<strong>)', r'<em>\1</em>', text)

        return text

    def _build_prompt(self, user_profile: Dict, job: Dict,
                     claimed_data: Optional[Dict] = None,
                     user_info: Optional[Dict] = None,
                     instructions: str = '',
                     language: str = 'english') -> str:
        """
        Build comprehensive Claude prompt

        Args:
            user_profile: User's CV profile
            job: Job details
            claimed_data: User-claimed competencies/skills
            user_info: User contact information (name, email, phone)
            instructions: Optional user instructions to guide generation
            language: 'english' or 'german'

        Returns:
            str: Complete prompt for Claude
        """
        # Format claimed evidence if provided
        claimed_section = ""
        if claimed_data and (claimed_data.get('competencies') or claimed_data.get('skills')):
            claimed_section = self._format_claimed_evidence(
                claimed_data.get('competencies', {}),
                claimed_data.get('skills', {}),
                user_profile.get('work_experience', [])
            )

        # Format work experience
        work_exp_section = self._format_work_experience(
            user_profile.get('work_experience', [])
        )

        # Format education
        education_section = self._format_education(
            user_profile.get('education', [])
        )

        # Format projects
        projects_section = self._format_projects(
            user_profile.get('projects', [])
        )

        # Use user_info if provided, otherwise fall back to profile
        contact_name = user_info.get('name') if user_info else user_profile.get('name', 'Professional')
        contact_email = user_info.get('email') if user_info else user_profile.get('email', 'email@example.com')
        contact_phone = user_info.get('phone') if user_info else user_profile.get('phone', '')

        # Build the prompt
        prompt = f"""You are an expert resume writer specializing in creating ATS-optimized, professional resumes tailored to specific job opportunities.

## LANGUAGE REQUIREMENT - READ THIS FIRST

{self._get_language_instructions(language)}

## USER'S PROFILE

**Name:** {contact_name}
**Contact Information for Resume Header:**
- Email: {contact_email}
- Phone: {contact_phone if contact_phone else 'Not provided'}

**Location:** {user_profile.get('location', '')}

**Career Information:**
- Target Role: {user_profile.get('extracted_role', 'Professional')}
- Seniority Level: {user_profile.get('derived_seniority', 'Mid-level')}
- Total Experience: {user_profile.get('total_years_experience', 'Multiple')} years

**Core Competencies (Auto-detected from CV):**
{self._format_list(user_profile.get('competencies', [])[:15])}

**Technical Skills:**
{self._format_list(user_profile.get('technical_skills', [])[:20])}

**Soft Skills:**
{self._format_list(user_profile.get('soft_skills', [])[:10])}

{work_exp_section}

{education_section}
{projects_section}
**Certifications:**
{self._format_list(user_profile.get('certifications', []))}

**Languages:**
{self._format_list(user_profile.get('languages', []))}

{claimed_section}

---

## TARGET JOB

**Position:** {job.get('title', 'Position')}
**Company:** {job.get('company', 'Company')}
**Location:** {job.get('location', 'Location')}

**Job Description:**
{job.get('description', 'No description provided')[:2000]}

**Required Competencies:**
{self._format_list(job.get('ai_competencies', []))}

**Required Skills:**
{self._format_list(job.get('ai_key_skills', []))}

---
{"## USER INSTRUCTIONS" + chr(10) + chr(10) + instructions + chr(10) + chr(10) + "Follow these instructions carefully when writing the resume." + chr(10) + chr(10) + "---" + chr(10) if instructions else ""}
## YOUR TASK

Generate a professional, ATS-optimized resume tailored specifically for this job opportunity.

**IMPORTANT:** Do NOT ask clarifying questions. Generate the resume immediately using the information provided. If any information is missing, use reasonable placeholders or omit those sections. The user needs a complete HTML resume document right now.

**REMINDER:** Remember to write the resume in {"GERMAN (Deutsch)" if language == "german" else "ENGLISH"} as specified at the top of this prompt!

## REQUIREMENTS

### 1. Content Strategy
- **Match Keywords:** Use exact keywords from the job description naturally throughout the resume
- **Emphasize Relevance:** Prioritize the most relevant experiences and skills for this specific role
- **Quantify Achievements:** Include metrics, numbers, and measurable outcomes where possible
- **User-Claimed Skills:** Integrate user-claimed competencies/skills seamlessly into relevant experience sections
- **Professional Tone:** Maintain a confident, achievement-focused tone

### 2. Structure
Use this standard, ATS-friendly structure:

1. **Header** - MUST be formatted as:
   - Candidate's name in large, bold text (e.g., 24-28pt font)
   - Below the name, on separate lines: Email | Phone (if provided)
   - Example format:
     ```
     JOHN DOE
     john.doe@example.com | +1 (555) 123-4567
     ```
   - Use ONLY the contact information provided - do NOT make up or invent contact details
2. **Professional Summary** - 3-4 sentences highlighting key qualifications aligned with the job
3. **Core Competencies** - 8-12 key competencies/skills as a bullet list
4. **Professional Experience** - Include ALL work experiences provided, no exceptions. List most recent first. Each role should have 3-5 achievement-focused bullet points.
5. **Education** - Degree, institution, year
6. **Projects** (if provided) - Include ALL projects listed, maintaining the bullet-point structure provided
7. **Additional Sections** (if applicable) - Certifications, Languages, Technical Skills

### 3. Experience Bullet Points
For each work experience:
- Start with strong action verbs (Led, Developed, Implemented, Drove, etc.)
- Include measurable outcomes when available
- Highlight achievements over responsibilities
- **User-Claimed Evidence:** When incorporating user-claimed competencies/skills, rewrite their evidence as professional, achievement-focused resume bullets
- Ensure bullets align with job requirements
- **IMPORTANT:** All text must be in black color - do not use blue, red, or any other colors

### 4. ATS Optimization
- Use standard section headers (no fancy titles)
- Include relevant keywords naturally
- Use standard formatting (no tables, text boxes, or graphics)
- Use common fonts and simple styling
- Ensure text is parseable by ATS systems

### 5. HTML Formatting
Return ONLY valid HTML with the following structure:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume - [Name]</title>
    <style>
        /* Professional, print-friendly CSS */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Arial', 'Helvetica', sans-serif;
            font-size: 11pt;
            line-height: 1.4;
            color: #333;
            max-width: 8.5in;
            margin: 0 auto;
            padding: 0.5in;
        }}
        h1 {{
            font-size: 24pt;
            color: #1a1a1a;
            margin-bottom: 0.2in;
            text-align: center;
        }}
        .contact {{
            text-align: center;
            margin-bottom: 0.3in;
            font-size: 10pt;
            color: #555;
        }}
        h2 {{
            font-size: 14pt;
            color: #1a1a1a;
            border-bottom: 2px solid #333;
            margin-top: 0.25in;
            margin-bottom: 0.15in;
            padding-bottom: 0.05in;
            text-transform: uppercase;
            letter-spacing: 0.5pt;
        }}
        .summary {{
            margin-bottom: 0.2in;
            text-align: justify;
        }}
        .competencies {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.1in;
            margin-bottom: 0.2in;
        }}
        .competency-item {{
            font-size: 10pt;
            padding: 0.05in;
        }}
        .job {{
            margin-bottom: 0.2in;
        }}
        .job-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.05in;
        }}
        .job-title {{
            font-weight: bold;
            font-size: 11pt;
        }}
        .company {{
            font-style: italic;
        }}
        .dates {{
            color: #555;
            font-size: 10pt;
        }}
        ul {{
            margin-left: 0.25in;
            margin-bottom: 0.1in;
        }}
        li {{
            margin-bottom: 0.08in;
        }}
        .new-item {{
            color: #0066cc;
            font-weight: 600;
        }}
        .education-item {{
            margin-bottom: 0.1in;
        }}
        .skills-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.05in;
            font-size: 10pt;
        }}
        @media print {{
            body {{ padding: 0.3in; }}
        }}
    </style>
</head>
<body>
    <!-- Header with name and contact -->
    <!-- Professional Summary section -->
    <!-- Core Competencies section -->
    <!-- Professional Experience section -->
    <!-- Education section -->
    <!-- Additional sections as needed -->
</body>
</html>
```

### 6. Critical Instructions - READ CAREFULLY

**YOU MUST FOLLOW THESE RULES EXACTLY:**

1. **Your ENTIRE response must be ONLY the HTML document**
2. **Start IMMEDIATELY with `<!DOCTYPE html>`** - no introduction, no explanation
3. **Do NOT include markdown code fences** (no ```html or ```)
4. **Do NOT explain what you're doing** - just output the HTML
5. **Do NOT ask "Would you like me to..." or any questions** - JUST GENERATE IT
6. **The first characters of your response MUST be:** `<!DOCTYPE html>`
7. **The last characters of your response MUST be:** `</html>`
8. **Nothing before `<!DOCTYPE html>`, nothing after `</html>`**

Additional requirements:
- Include ALL work experiences from the user's profile - DO NOT SKIP ANY, regardless of how many there are
- Ensure the resume is professional length (2-3 pages is perfectly acceptable when including all work experiences)
- All content must be factual and based on the provided profile
- If information is missing, use reasonable defaults or omit the section
- Make it visually clean and professional with ALL TEXT IN BLACK COLOR (no blue, red, or colored text)
- Optimize for both human readers and ATS systems

**FINAL LANGUAGE REMINDER:** Write the entire resume in {"GERMAN (Deutsch) - use German section headers, German action verbs, German descriptions" if language == "german" else "ENGLISH"}!

**BEGIN YOUR RESPONSE NOW WITH `<!DOCTYPE html>` AND NOTHING ELSE:**"""

        return prompt

    def _get_language_instructions(self, language: str) -> str:
        """Get language-specific instructions for resume generation"""
        if language == 'german':
            return """**CRITICAL: WRITE THE ENTIRE RESUME IN GERMAN (Deutsch).**

*** ABSOLUTELY MANDATORY - THIS IS THE #1 REQUIREMENT ***
*** ALL CONTENT MUST BE IN GERMAN - NOT ENGLISH ***

YOU MUST:
- Write EVERYTHING in German (Deutsch) - no English except technical terms
- ALL section headers MUST be in German
- ALL job descriptions MUST be in German
- ALL bullet points MUST be in German
- ALL summaries MUST be in German

REQUIRED GERMAN SECTION HEADERS:
- "BERUFSERFAHRUNG" (not "Professional Experience")
- "AUSBILDUNG" (not "Education")
- "KERNKOMPETENZEN" (not "Core Competencies")
- "BERUFLICHES PROFIL" or "ZUSAMMENFASSUNG" (not "Professional Summary")
- "PROJEKTE" (not "Projects")
- "ZERTIFIZIERUNGEN" (not "Certifications")
- "SPRACHEN" (not "Languages")
- "TECHNISCHE FÄHIGKEITEN" (not "Technical Skills")

GERMAN ACTION VERBS (start every bullet point with these):
- "Leitete" (not "Led")
- "Entwickelte" (not "Developed")
- "Implementierte" (not "Implemented")
- "Verwaltete" (not "Managed")
- "Koordinierte" (not "Coordinated")
- "Optimierte" (not "Optimized")
- "Analysierte" (not "Analyzed")

GERMAN DATE FORMATS:
- "Januar 2020 - Dezember 2023" (NOT "January 2020 - December 2023")
- Months: Januar, Februar, März, April, Mai, Juni, Juli, August, September, Oktober, November, Dezember

EXCEPTIONS (keep in English):
- Technical terms: "Machine Learning", "API", "DevOps", "Python", "JavaScript"
- Company names and brand names
- Software/tool names

**REMEMBER: IF YOU WRITE ANYTHING IN ENGLISH (except technical terms), YOU HAVE FAILED THE TASK.**"""
        else:  # Default to English
            return """**Write the resume in ENGLISH.**

Language Requirements:
- ALL content must be in professional business English
- Use standard American/British English conventions
- Action verbs: "Led", "Developed", "Implemented", "Managed", etc.
- Date formats: "January 2020 - December 2023" or "2020 - 2023"
- Standard English section headers as specified above"""

    def _format_claimed_evidence(self, claimed_competencies: Dict,
                                 claimed_skills: Dict,
                                 work_experiences: List[Dict]) -> str:
        """
        Format user-claimed competencies/skills for prompt

        Args:
            claimed_competencies: Dict of claimed competencies
            claimed_skills: Dict of claimed skills
            work_experiences: List of work experience dicts for reference

        Returns:
            str: Formatted section for prompt
        """
        if not claimed_competencies and not claimed_skills:
            return ""

        sections = []

        # Create work experience ID to title mapping
        work_exp_map = {}
        for i, exp in enumerate(work_experiences):
            work_exp_map[i] = f"{exp.get('title', 'Position')} at {exp.get('company', 'Company')}"

        if claimed_competencies:
            comp_list = ["**USER-CLAIMED COMPETENCIES (with evidence to incorporate):**"]
            comp_list.append("")
            for name, details in claimed_competencies.items():
                exp_ids = details.get('work_experience_ids', [])
                exp_titles = [work_exp_map.get(exp_id, f"Experience #{exp_id}") for exp_id in exp_ids]

                comp_list.append(f"**{name}:**")
                comp_list.append(f"- Evidence: {details.get('evidence', 'No evidence provided')}")
                comp_list.append(f"- Demonstrated in: {', '.join(exp_titles) if exp_titles else 'Not specified'}")
                comp_list.append("")

            sections.append("\n".join(comp_list))

        if claimed_skills:
            skill_list = ["**USER-CLAIMED SKILLS (with evidence to incorporate):**"]
            skill_list.append("")
            for name, details in claimed_skills.items():
                exp_ids = details.get('work_experience_ids', [])
                exp_titles = [work_exp_map.get(exp_id, f"Experience #{exp_id}") for exp_id in exp_ids]

                skill_list.append(f"**{name}:**")
                skill_list.append(f"- Evidence: {details.get('evidence', 'No evidence provided')}")
                skill_list.append(f"- Demonstrated in: {', '.join(exp_titles) if exp_titles else 'Not specified'}")
                skill_list.append("")

            sections.append("\n".join(skill_list))

        if sections:
            result = "\n---\n\n## USER-CLAIMED ADDITIONS\n\n"
            result += "The user has claimed the following competencies/skills that were not auto-detected. "
            result += "You MUST incorporate their evidence as professional resume bullets in the relevant experience sections. "
            result += "Rewrite their evidence to be concise, achievement-focused, and keyword-rich. "
            result += "Blend them naturally with existing bullets - do NOT mark them or use different colors.\n\n"
            result += "\n\n".join(sections)
            return result

        return ""

    def _format_work_experience(self, experiences: List[Dict]) -> str:
        """
        Format work experience for prompt

        Args:
            experiences: List of work experience dicts

        Returns:
            str: Formatted work experience section
        """
        if not experiences:
            return "**Work Experience:**\nNo work experience recorded"

        formatted = ["**Work Experience:**", ""]
        for i, exp in enumerate(experiences):
            title = exp.get('title', 'Position')
            company = exp.get('company', 'Company')
            start = exp.get('start_date', '')
            end = exp.get('end_date', 'Present')
            description = exp.get('description', '')

            formatted.append(f"{i + 1}. **{title}** at **{company}**")
            formatted.append(f"   {start} - {end}")

            if description:
                # Split description into bullet points if it contains line breaks
                if '\n' in description:
                    desc_lines = [line.strip() for line in description.split('\n') if line.strip()]
                    formatted.append("   Key responsibilities/achievements:")
                    for line in desc_lines[:5]:  # Limit to 5 bullets
                        formatted.append(f"   - {line}")
                else:
                    formatted.append(f"   {description}")

            formatted.append("")

        return "\n".join(formatted)

    def _format_education(self, education_list: List[Dict]) -> str:
        """
        Format education for prompt

        Args:
            education_list: List of education dicts

        Returns:
            str: Formatted education section
        """
        if not education_list:
            return "**Education:**\nNo education recorded"

        formatted = ["**Education:**", ""]
        for edu in education_list:
            degree = edu.get('degree', 'Degree')
            field = edu.get('field', 'Field of Study')
            institution = edu.get('institution', 'Institution')
            year = edu.get('graduation_year', '')

            formatted.append(f"- {degree} in {field}")
            formatted.append(f"  {institution}, {year}")
            formatted.append("")

        return "\n".join(formatted)

    def _format_list(self, items: List) -> str:
        """
        Format a simple list of items

        Args:
            items: List of strings or dicts

        Returns:
            str: Formatted list
        """
        if not items:
            return "Not specified"

        formatted_items = []
        for item in items:
            if isinstance(item, dict):
                # If it's a dict, try to get a name or description
                formatted_items.append(item.get('name', item.get('description', str(item))))
            else:
                formatted_items.append(str(item))

        return ", ".join(formatted_items[:10])  # Limit to 10 items

    def _format_projects(self, projects: List[str]) -> str:
        """
        Format projects for resume prompt

        Args:
            projects: List of formatted project text blocks

        Returns:
            str: Formatted projects section for prompt
        """
        if not projects or len(projects) == 0:
            return ""

        formatted = "\n\nPROJECTS:\n"
        for i, project in enumerate(projects, 1):
            formatted += f"\n{i}. {project}\n"

        return formatted

    def html_to_pdf(self, html_content: str, output_path: str) -> None:
        """
        Convert HTML to PDF using WeasyPrint

        Args:
            html_content: HTML string
            output_path: Path where PDF should be saved

        Raises:
            ImportError: If WeasyPrint is not installed
            Exception: If PDF generation fails
        """
        try:
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration
        except ImportError:
            raise ImportError(
                "WeasyPrint is not installed. "
                "Install it with: pip install weasyprint"
            )

        try:
            # Create font configuration for better rendering
            font_config = FontConfiguration()

            # Generate PDF
            HTML(string=html_content).write_pdf(
                output_path,
                font_config=font_config
            )

        except Exception as e:
            print(f"Error generating PDF: {e}")
            raise

    def estimate_cost(self, user_profile: Dict, job: Dict,
                     claimed_data: Optional[Dict] = None) -> Dict[str, float]:
        """
        Estimate the cost of generating a resume

        Args:
            user_profile: User's CV profile
            job: Job details
            claimed_data: User-claimed data

        Returns:
            Dict with estimated tokens and cost
        """
        # Build prompt to estimate tokens
        prompt = self._build_prompt(user_profile, job, claimed_data)

        # Rough estimation: 1 token ≈ 4 characters
        input_tokens = len(prompt) / 4
        output_tokens = 2000  # Estimated output size

        # Claude 3.5 Sonnet pricing (as of Jan 2026)
        # Input: $3 per million tokens
        # Output: $15 per million tokens
        input_cost = (input_tokens / 1_000_000) * 3
        output_cost = (output_tokens / 1_000_000) * 15
        total_cost = input_cost + output_cost

        return {
            'estimated_input_tokens': int(input_tokens),
            'estimated_output_tokens': output_tokens,
            'estimated_input_cost': input_cost,
            'estimated_output_cost': output_cost,
            'estimated_total_cost': total_cost
        }
