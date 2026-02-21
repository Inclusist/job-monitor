"""
Job Extractor Utility

Fetches job posting URLs and extracts structured data using Claude AI.
"""
import os
import re
import requests
from bs4 import BeautifulSoup
from anthropic import Anthropic
from typing import Optional, Tuple, Dict
import json


def fetch_url_content(url: str, timeout: int = 10) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch raw HTML from a URL.

    Args:
        url: Job posting URL
        timeout: Request timeout in seconds

    Returns:
        tuple: (html_content, error_message)
               If successful: (html, None)
               If failed: (None, error_message)
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; JobMonitor/1.0)'
        }

        response = requests.get(url, headers=headers, timeout=timeout)

        if response.status_code != 200:
            return None, f"HTTP {response.status_code}: {response.reason}"

        html = response.text

        # Validate content length
        if len(html) < 500:
            return None, "Page content too short - likely an error or login page"

        return html, None

    except requests.exceptions.Timeout:
        return None, "Request timeout - the site took too long to respond"
    except requests.exceptions.ConnectionError:
        return None, "Connection failed - could not reach the site"
    except requests.exceptions.RequestException as e:
        return None, f"Request failed: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"


def extract_text_from_html(html: str) -> str:
    """
    Extract clean text from HTML using BeautifulSoup.

    Args:
        html: Raw HTML content

    Returns:
        str: Extracted text (newlines preserved, scripts/styles removed)
    """
    soup = BeautifulSoup(html, 'lxml')

    # Remove unwanted tags
    for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
        tag.decompose()

    # Extract text with newlines
    text = soup.get_text(separator='\n', strip=True)

    # Collapse multiple newlines to max 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def extract_job_data(text: str, api_key: Optional[str] = None) -> Dict[str, Optional[str]]:
    """
    Parse job posting text and extract structured data using Claude.

    Args:
        text: Job posting text (from URL fetch or user paste)
        api_key: Anthropic API key (if None, reads from env)

    Returns:
        dict: {
            'title': str,
            'company': str,
            'location': str,
            'description': str,
            'salary': str or None
        }

    Raises:
        ValueError: If extraction fails or required fields missing
    """
    if not api_key:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("No Anthropic API key provided")

    client = Anthropic(api_key=api_key)

    # Truncate text if too long (max ~8000 chars for context window)
    if len(text) > 8000:
        text = text[:8000] + "...(truncated)"

    prompt = f"""Extract structured job information from this job posting text.

Return ONLY a JSON object with these exact keys (no markdown, no code fences):
- title: The job title/position
- company: The company/organization name
- location: The job location (city, country, or "Remote")
- description: The full job description text
- salary: The salary/compensation (if mentioned, otherwise null)

Job Posting Text:
{text}

Return the JSON now:"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            temperature=0.3,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        result_text = response.content[0].text.strip()

        # Remove markdown code fences if present
        if result_text.startswith('```json'):
            result_text = result_text.split('```json\n', 1)[1].rsplit('```', 1)[0]
        elif result_text.startswith('```'):
            result_text = result_text.split('```\n', 1)[1].rsplit('```', 1)[0]

        # Parse JSON
        job_data = json.loads(result_text)

        # Validate required fields
        if not job_data.get('title'):
            raise ValueError("Missing job title")
        if not job_data.get('company'):
            raise ValueError("Missing company name")
        if not job_data.get('description'):
            raise ValueError("Missing job description")

        # Ensure all expected keys exist
        return {
            'title': job_data.get('title', '').strip(),
            'company': job_data.get('company', '').strip(),
            'location': job_data.get('location', '').strip() or 'Not specified',
            'description': job_data.get('description', '').strip(),
            'salary': job_data.get('salary')
        }

    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse Claude response as JSON: {e}")
    except Exception as e:
        raise ValueError(f"Job data extraction failed: {e}")
