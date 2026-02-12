"""
Search Parameter Suggester
Uses Claude AI to suggest relevant job search parameters based on user's CV
"""

import json
from anthropic import Anthropic
from typing import Dict, List


class SearchSuggester:
    """Suggests job search parameters based on CV profile"""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-20241022"):
        """
        Initialize search suggester
        
        Args:
            api_key: Anthropic API key
            model: Claude model to use
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model
    
    def suggest_search_parameters(self, cv_profile: Dict) -> Dict[str, List[str]]:
        """
        Analyze CV and suggest relevant job search parameters
        
        Args:
            cv_profile: Parsed CV profile dictionary
            
        Returns:
            Dictionary with suggested job_titles and locations
        """
        
        # Extract key info from CV
        expertise = cv_profile.get('expertise_summary', '')
        skills = cv_profile.get('skills', {})
        experience = cv_profile.get('work_experience', [])
        current_location = cv_profile.get('location', '')
        
        # Build context for Claude
        context = f"""
Expertise: {expertise}

Technical Skills: {', '.join(skills.get('technical', [])[:10])}

Recent Experience:
"""
        
        for exp in experience[:3]:
            context += f"- {exp.get('title', '')} at {exp.get('company', '')}\n"
        
        prompt = f"""Based on this professional profile, suggest relevant job search parameters.

{context}

Current Location: {current_location}

Please suggest:
1. Job titles that match this person's expertise and experience level (10-15 titles)
2. Locations where they should search (include current location, major tech hubs in their region, and remote options)

Consider:
- Their seniority level (junior/mid/senior/lead/head/director)
- Their domain expertise
- Career progression opportunities
- Both specific and broader job titles
- Include German job titles if relevant

Return your response as a JSON object with this structure:
{{
  "job_titles": ["Title 1", "Title 2", ...],
  "locations": ["Location 1", "Location 2", ...],
  "reasoning": "Brief explanation of suggestions"
}}
"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            content = response.content[0].text
            
            # Try to parse JSON from response
            # Claude might wrap JSON in markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            suggestions = json.loads(content)
            
            return {
                'job_titles': suggestions.get('job_titles', []),
                'locations': suggestions.get('locations', []),
                'reasoning': suggestions.get('reasoning', '')
            }
            
        except Exception as e:
            print(f"Error getting suggestions: {e}")
            # Return fallback suggestions
            return {
                'job_titles': [
                    'Data Scientist',
                    'Senior Data Scientist',
                    'Machine Learning Engineer',
                    'AI Engineer',
                    'Data Engineer'
                ],
                'locations': [
                    'Berlin, Germany',
                    'Munich, Germany',
                    'Hamburg, Germany',
                    'Remote, Germany'
                ],
                'reasoning': 'Default suggestions (AI suggestion failed)'
            }


def test_suggester():
    """Test the search suggester"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not found")
        return
    
    # Mock CV profile
    mock_profile = {
        'expertise_summary': 'Senior Data Scientist with 8+ years of experience in machine learning, deep learning, and AI. Expertise in Python, TensorFlow, and cloud platforms.',
        'skills': {
            'technical': ['Python', 'TensorFlow', 'PyTorch', 'SQL', 'AWS', 'Docker', 'Kubernetes', 'Machine Learning', 'Deep Learning', 'NLP'],
            'soft': ['Leadership', 'Communication', 'Problem Solving']
        },
        'work_experience': [
            {'title': 'Senior Data Scientist', 'company': 'Tech Corp', 'duration': '2020-Present'},
            {'title': 'Data Scientist', 'company': 'StartupCo', 'duration': '2017-2020'},
            {'title': 'Data Analyst', 'company': 'BigCorp', 'duration': '2015-2017'}
        ],
        'location': 'Berlin, Germany'
    }
    
    suggester = SearchSuggester(api_key)
    
    print("Getting search suggestions based on CV profile...")
    print("=" * 60)
    
    suggestions = suggester.suggest_search_parameters(mock_profile)
    
    print("\n📋 SUGGESTED JOB TITLES:")
    for i, title in enumerate(suggestions['job_titles'], 1):
        print(f"  {i}. {title}")
    
    print("\n🌍 SUGGESTED LOCATIONS:")
    for i, location in enumerate(suggestions['locations'], 1):
        print(f"  {i}. {location}")
    
    print(f"\n💡 REASONING:")
    print(f"  {suggestions['reasoning']}")


if __name__ == "__main__":
    test_suggester()
