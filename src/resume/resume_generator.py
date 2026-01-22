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


class ResumeGenerator:
    """Generate tailored resumes using Claude AI"""

    def __init__(self, anthropic_api_key: str):
        """
        Initialize resume generator

        Args:
            anthropic_api_key: Anthropic API key
        """
        self.client = Anthropic(api_key=anthropic_api_key)
        self.model = "claude-3-5-haiku-20241022"  # Use Haiku (faster and cheaper, still high quality)

    def generate_resume_html(self, user_profile: Dict, job: Dict,
                            claimed_data: Optional[Dict] = None,
                            user_info: Optional[Dict] = None) -> str:
        """
        Generate tailored resume HTML using Claude

        Args:
            user_profile: User's CV profile dict
            job: Job details dict
            claimed_data: Dict with 'competencies' and 'skills' keys (optional)
            user_info: Dict with 'name', 'email', 'phone' keys for resume header (optional)

        Returns:
            str: Professional HTML resume
        """
        prompt = self._build_prompt(user_profile, job, claimed_data, user_info)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8192,  # Increased for longer resumes
                temperature=0.7,  # Slightly creative but professional
                messages=[{"role": "user", "content": prompt}]
            )

            html_content = response.content[0].text

            # Clean up any markdown code fences if Claude included them
            if html_content.startswith('```html'):
                html_content = html_content.split('```html\n', 1)[1]
                html_content = html_content.rsplit('```', 1)[0]
            elif html_content.startswith('```'):
                html_content = html_content.split('```\n', 1)[1]
                html_content = html_content.rsplit('```', 1)[0]

            # Remove any preamble text before <!DOCTYPE html>
            # Claude sometimes adds commentary before the actual HTML
            if '<!DOCTYPE html>' in html_content:
                html_content = '<!DOCTYPE html>' + html_content.split('<!DOCTYPE html>', 1)[1]
            elif '<html' in html_content.lower():
                # If no DOCTYPE but has <html> tag, extract from there
                import re
                match = re.search(r'<html[^>]*>', html_content, re.IGNORECASE)
                if match:
                    html_content = html_content[match.start():]

            # Remove any text after the closing </html> tag
            if '</html>' in html_content.lower():
                html_content = html_content[:html_content.lower().rfind('</html>') + 7]

            return html_content.strip()

        except Exception as e:
            print(f"Error generating resume: {e}")
            raise

    def _build_prompt(self, user_profile: Dict, job: Dict,
                     claimed_data: Optional[Dict] = None,
                     user_info: Optional[Dict] = None) -> str:
        """
        Build comprehensive Claude prompt

        Args:
            user_profile: User's CV profile
            job: Job details
            claimed_data: User-claimed competencies/skills
            user_info: User contact information (name, email, phone)

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

        # Use user_info if provided, otherwise fall back to profile
        contact_name = user_info.get('name') if user_info else user_profile.get('name', 'Professional')
        contact_email = user_info.get('email') if user_info else user_profile.get('email', 'email@example.com')
        contact_phone = user_info.get('phone') if user_info else user_profile.get('phone', '')

        # Build the prompt
        prompt = f"""You are an expert resume writer specializing in creating ATS-optimized, professional resumes tailored to specific job opportunities.

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

## YOUR TASK

Generate a professional, ATS-optimized resume tailored specifically for this job opportunity.

**IMPORTANT:** Do NOT ask clarifying questions. Generate the resume immediately using the information provided. If any information is missing, use reasonable placeholders or omit those sections. The user needs a complete HTML resume document right now.

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
6. **Additional Sections** (if applicable) - Certifications, Languages, Technical Skills

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

**BEGIN YOUR RESPONSE NOW WITH `<!DOCTYPE html>` AND NOTHING ELSE:**"""

        return prompt

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
