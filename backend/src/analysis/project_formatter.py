"""
Project Formatter
Converts casual project descriptions into professional structured bullet points
"""

from anthropic import Anthropic
from typing import Dict, Optional
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import logging

logger = logging.getLogger(__name__)


class ProjectFormatter:
    """Format project descriptions using Gemini/Claude AI"""

    def __init__(self, anthropic_api_key: str, gemini_api_key: Optional[str] = None):
        """
        Initialize project formatter

        Args:
            anthropic_api_key: Anthropic API key (Claude - fallback)
            gemini_api_key: Google Gemini API key (primary, optional)
        """
        # Claude client (fallback)
        self.client = Anthropic(api_key=anthropic_api_key)
        self.model = "claude-3-5-haiku-20241022"

        # Gemini client (primary)
        self.gemini_model = None
        if gemini_api_key:
            genai.configure(api_key=gemini_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')

    def format_project(self, casual_text: str) -> Dict[str, str]:
        """
        Convert casual project description to professional bullet-point format

        Args:
            casual_text: User's casual description of the project

        Returns:
            Dictionary with formatted_text and metadata
        """
        if not casual_text or len(casual_text.strip()) < 10:
            return {'error': 'Project description too short'}

        prompt = self._build_prompt(casual_text)

        formatted_text = None
        api_used = None

        try:
            # TRY GEMINI FIRST
            if self.gemini_model:
                try:
                    formatted_text = self._format_with_gemini(prompt)
                    api_used = 'gemini'
                    logger.info("Project formatted with Gemini")
                except Exception as gemini_error:
                    logger.warning(f"Gemini failed, falling back to Claude: {gemini_error}")

            # FALLBACK TO CLAUDE
            if formatted_text is None:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=500,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                formatted_text = response.content[0].text.strip()
                api_used = 'claude'
                logger.info(f"Project formatted with Claude (fallback: {self.gemini_model is not None})")

            return {
                'formatted_text': formatted_text,
                'api_used': api_used
            }

        except Exception as e:
            logger.error(f"Both APIs failed: {e}")
            return {
                'error': f"Failed to format project: {str(e)}"
            }

    def _format_with_gemini(self, prompt: str) -> str:
        """
        Format project using Gemini API

        Args:
            prompt: Complete prompt string

        Returns:
            str: Formatted project text

        Raises:
            Exception: If Gemini API call fails
        """
        if not self.gemini_model:
            raise ValueError("Gemini not configured")

        # gemini-2.5-flash thinking tokens count against max_output_tokens.
        # Thinking alone typically uses 1000-1500 tokens, so the budget must
        # be high enough to cover both thinking and visible output.
        response = self.gemini_model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=8192,
                temperature=0.7,
                top_p=0.9,
            )
        )

        # Validate response
        if not response or not response.text:
            raise ValueError("Gemini returned empty response")

        formatted = response.text.strip()

        if len(formatted) < 20:
            raise ValueError("Gemini returned response too short")

        return formatted

    def _build_prompt(self, casual_text: str) -> str:
        """Build AI prompt for formatting casual project text"""

        prompt = f"""Convert this casual project description into professional resume bullet points.

INPUT: {casual_text}

FORMAT:
Project Name (title case, no bold)
• Brief description of what you built
• Technologies used (list the tools/languages)
• Impact or achievement if mentioned

RULES:
- Use plain text only, no markdown
- Use bullet points (•)
- 2-4 bullets maximum
- Professional language with action verbs
- Complete all bullet points

Example:
Inclusist Job Matching Platform
• Developed AI-powered application for automated job matching
• Technologies: Python, Flask, TensorFlow, PostgreSQL
• Achieved 85% match accuracy through semantic analysis

Now format the input above:"""

        return prompt


def test_formatter():
    """Test the project formatter"""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    gemini_key = os.getenv('GOOGLE_GEMINI_API_KEY')

    if not anthropic_key:
        print("Error: ANTHROPIC_API_KEY not found")
        return

    formatter = ProjectFormatter(anthropic_key, gemini_api_key=gemini_key)

    print("=" * 60)
    print("Testing Project Formatter")
    print("=" * 60)

    # Test cases
    test_cases = [
        "working on inclusist, a job matching app using ai and python. helps people find relevant jobs automatically",
        "built a weather dashboard with react and nodejs. shows real time weather data from openweathermap api",
        "creating an e-commerce site for selling books online. using django, stripe for payments, postgres database"
    ]

    for i, casual_text in enumerate(test_cases, 1):
        print(f"\n📝 Test Case {i}:")
        print(f"Input: {casual_text}")
        print("-" * 60)

        result = formatter.format_project(casual_text)

        if 'error' in result:
            print(f"Error: {result['error']}")
        else:
            print(f"API Used: {result['api_used']}")
            print(f"\nFormatted Output:\n{result['formatted_text']}")

        print("\n" + "=" * 60)


if __name__ == "__main__":
    test_formatter()
