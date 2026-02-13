"""
Feedback Learning System
Analyzes user feedback to improve job matching over time
"""

from typing import List, Dict, Optional
from datetime import datetime
import json


class FeedbackLearner:
    """Learns from user feedback to improve job matching"""
    
    def __init__(self, db):
        """
        Initialize feedback learner
        
        Args:
            db: JobDatabase instance
        """
        self.db = db
    
    def analyze_user_preferences(self, user_email: str) -> Dict:
        """
        Analyze user's feedback history to extract preferences
        
        Args:
            user_email: User email
            
        Returns:
            Dictionary with learned preferences
        """
        feedback_history = self.db.get_user_feedback(user_email, limit=100)
        
        if not feedback_history:
            return {
                'has_feedback': False,
                'total_feedback': 0,
                'preferences_summary': 'No feedback yet',
                'key_preferences': {'valued_aspects': [], 'dealbreakers': []}
            }
        
        # Categorize feedback
        agreed = [fb for fb in feedback_history if fb['feedback_type'] == 'agree']
        
        # Analyze patterns
        preferences = {
            'has_feedback': True,
            'total_feedback': len(feedback_history),
            'agreement_rate': len(agreed) / len(feedback_history) * 100 if feedback_history else 0,
            'liked_job_examples': self._extract_job_examples([fb for fb in agreed if fb['match_score_original'] >= 70], limit=3),
            'scoring_calibration': self._analyze_score_calibration(feedback_history),
            'key_preferences': {'valued_aspects': [], 'dealbreakers': []} # Will be populated by AI or fallback
        }
        
        return preferences

    def _extract_job_examples(self, feedback_list: List[Dict], limit: int = 3) -> List[Dict]:
        """Extract job examples from feedback"""
        examples = []
        
        for fb in feedback_list[:limit]:
            examples.append({
                'title': fb.get('job_title', 'Unknown'),
                'company': fb.get('job_company', 'Unknown'),
                'location': fb.get('job_location', 'Unknown'),
                'score': fb.get('match_score_original', 0),
                'alignments': fb.get('key_alignments', []),
                'gaps': fb.get('potential_gaps', []),
                'feedback_reason': fb.get('feedback_reason')
            })
        
        return examples

    def _analyze_score_calibration(self, feedback_history: List[Dict]) -> Dict:
        """Analyze if Claude's scores are calibrated with user's expectations"""
        calibration = {
            'avg_original_score': 0,
            'avg_user_score': 0,
            'score_bias': 0,  # Positive = Claude scores too high, Negative = too low
            'needs_calibration': False
        }
        
        scores_with_user_input = [
            fb for fb in feedback_history 
            if fb.get('match_score_user') is not None
        ]
        
        if not scores_with_user_input:
            return calibration
        
        original_scores = [fb['match_score_original'] for fb in scores_with_user_input]
        user_scores = [fb['match_score_user'] for fb in scores_with_user_input]
        
        calibration['avg_original_score'] = sum(original_scores) / len(original_scores)
        calibration['avg_user_score'] = sum(user_scores) / len(user_scores)
        calibration['score_bias'] = calibration['avg_original_score'] - calibration['avg_user_score']
        
        # If bias is > 10 points, calibration is needed
        calibration['needs_calibration'] = abs(calibration['score_bias']) > 10
        
        return calibration

    def analyze_user_preferences_ai(self, user_email: str) -> Dict:
        """
        Use Gemini to analyze feedback history and extract structured preferences.
        Returns a dict with instructions, valued_aspects, and dealbreakers.
        """
        feedback_history = self.db.get_user_feedback(user_email, limit=30)
        
        if not feedback_history:
            return {"instructions": "", "valued_aspects": [], "dealbreakers": []}
        
        # Format feedback for the AI
        feedback_summary = []
        for fb in feedback_history:
            item = f"Job: {fb.get('title')} at {fb.get('company')}\n"
            item += f"Claude Score: {fb['match_score_original']}\n"
            item += f"User Feedback: {fb['feedback_type']}"
            if fb.get('match_score_user'):
                item += f" (User Score: {fb['match_score_user']})"
            if fb.get('feedback_reason'):
                item += f"\nReason: {fb['feedback_reason']}"
            
            # Include what Claude liked/disliked for context
            if fb.get('key_alignments'):
                item += f"\nClaude Alignments: {fb['key_alignments']}"
            if fb.get('potential_gaps'):
                item += f"\nClaude Gaps: {fb['potential_gaps']}"
            
            feedback_summary.append(item)
        
        history_text = "\n---\n".join(feedback_summary)
        
        prompt = f"""You are an expert career coach analyzing a user's job feedback history.

Your task is to synthesize this feedback into a structured JSON profile. 
Focus on identifying what the user TRULY values vs. what they consider dealbreakers. 

CRITICAL: Do NOT flag a technology (like AI, Python, or Leadership) as a 'dealbreaker' just because it appeared in a negative feedback item. 
Only flag it as a dealbreaker if the user EXPLICITLY complained about it. If the AI said 'Missing AI experience' and the user rated it low, the dealbreaker is 'Inaccurate skill assessment' or 'Low seniority', NOT 'AI'.

FEEDBACK HISTORY:
{history_text}

Output format:
{{
  "instructions": "A concise list of 5-8 bullet points for an AI matching engine.",
  "valued_aspects": ["keyword1", "keyword2", ...],
  "dealbreakers": ["keyword1", "keyword2", ...]
}}

Example valued_aspects: ["High Seniority", "Leadership", "Automotive Domain", "Remote Work"]
Example dealbreakers: ["Heavy Travel", "Junior Roles", "Pure Individual Contributor", "Onsite Only"]

Output ONLY the JSON."""

        try:
            import os
            import google.generativeai as genai
            gemini_key = os.getenv('GOOGLE_GEMINI_API_KEY')
            if not gemini_key:
                return {"instructions": "", "valued_aspects": [], "dealbreakers": []}
            
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(response_mime_type="application/json")
            )
            
            import json
            return json.loads(response.text.strip())
        except Exception as e:
            print(f"Error in AI preference analysis: {e}")
            return {"instructions": "", "valued_aspects": [], "dealbreakers": []}

    def generate_learning_context(self, user_email: str) -> str:
        """
        Generate a context string to include in Claude prompts
        """
        # Get AI-synthesized structured data
        ai_data = self.analyze_user_preferences_ai(user_email)
        ai_instructions = ai_data.get('instructions', '')
        
        prefs = self.analyze_user_preferences(user_email)
        
        if not prefs['has_feedback']:
            return ""
        
        context_parts = [
            "\n## USER PREFERENCE LEARNING",
            f"Based on {prefs['total_feedback']} previous feedback items, here are specific instructions for scoring jobs for this user:",
        ]
        
        if ai_instructions:
            context_parts.append("\n### Personalized Scoring Instructions:")
            context_parts.append(ai_instructions)
        
        # Add calibration guidance
        calibration = prefs['scoring_calibration']
        if calibration['needs_calibration']:
            if calibration['score_bias'] > 0:
                context_parts.append(
                    f"\n### Scoring Calibration: User finds your scores ~{int(calibration['score_bias'])} points too high. "
                    "Be more conservative/strict in your scoring."
                )
            else:
                context_parts.append(
                    f"\n### Scoring Calibration: User finds your scores ~{abs(int(calibration['score_bias']))} points too low. "
                    "Be more generous/lenient in your scoring."
                )
        
        context_parts.append(
            "\n### Final Instruction: Apply the above patterns and instructions to the current job analysis.\n"
        )
        
        return '\n'.join(context_parts)
    
    def get_preference_summary(self, user_email: str) -> str:
        """
        Get a human-readable summary of learned preferences
        
        Args:
            user_email: User email
            
        Returns:
            Formatted summary string
        """
        prefs = self.analyze_user_preferences(user_email)
        
        if not prefs['has_feedback']:
            return "No feedback collected yet. Start rating job matches to help the system learn your preferences!"
        
        summary_parts = [
            f"Learning from {prefs['total_feedback']} feedback items",
            f"Agreement rate: {prefs['agreement_rate']:.1f}%"
        ]
        
        key_prefs = prefs['key_preferences']
        if key_prefs['valued_aspects']:
            summary_parts.append(f"You value: {', '.join(key_prefs['valued_aspects'][:3])}")
        
        if key_prefs['dealbreakers']:
            summary_parts.append(f"You avoid: {', '.join(key_prefs['dealbreakers'][:3])}")
        
        return " | ".join(summary_parts)


def test_learner():
    """Test the feedback learner"""
    from database.operations import JobDatabase
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    db_path = os.getenv('DATABASE_PATH', 'data/jobs.db')
    db = JobDatabase(db_path)
    
    learner = FeedbackLearner(db)
    
    # Analyze preferences
    prefs = learner.analyze_user_preferences('default@localhost')
    
    print("User Preferences Analysis:")
    print("=" * 60)
    print(json.dumps(prefs, indent=2))
    
    print("\n\nLearning Context for Claude:")
    print("=" * 60)
    print(learner.generate_learning_context('default@localhost'))
    
    print("\n\nPreference Summary:")
    print("=" * 60)
    print(learner.get_preference_summary('default@localhost'))


if __name__ == '__main__':
    test_learner()
