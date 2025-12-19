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
                'preferences_summary': 'No feedback yet'
            }
        
        # Categorize feedback
        agreed = []
        disagreed = []
        too_high_scores = []
        too_low_scores = []
        
        for fb in feedback_history:
            if fb['feedback_type'] == 'agree':
                agreed.append(fb)
            elif fb['feedback_type'] == 'disagree':
                disagreed.append(fb)
            elif fb['feedback_type'] == 'too_high':
                too_high_scores.append(fb)
            elif fb['feedback_type'] == 'too_low':
                too_low_scores.append(fb)
        
        # Extract patterns from jobs user liked (agreed with high scores)
        liked_jobs = [fb for fb in agreed if fb['match_score_original'] >= 70]
        
        # Extract patterns from jobs user disliked (disagreed or too_high on low scores)
        disliked_jobs = disagreed + too_high_scores
        
        # Analyze patterns
        preferences = {
            'has_feedback': True,
            'total_feedback': len(feedback_history),
            'agreement_rate': len(agreed) / len(feedback_history) * 100 if feedback_history else 0,
            'liked_job_examples': self._extract_job_examples(liked_jobs, limit=3),
            'disliked_job_examples': self._extract_job_examples(disliked_jobs, limit=3),
            'key_preferences': self._extract_key_preferences(liked_jobs, disliked_jobs),
            'scoring_calibration': self._analyze_score_calibration(feedback_history)
        }
        
        return preferences
    
    def _extract_job_examples(self, feedback_list: List[Dict], limit: int = 3) -> List[Dict]:
        """Extract job examples from feedback"""
        examples = []
        
        for fb in feedback_list[:limit]:
            examples.append({
                'title': fb['job_title'],
                'company': fb['job_company'],
                'location': fb['job_location'],
                'score': fb['match_score_original'],
                'alignments': fb['key_alignments'],
                'gaps': fb['potential_gaps'],
                'feedback_reason': fb.get('feedback_reason')
            })
        
        return examples
    
    def _extract_key_preferences(self, liked: List[Dict], disliked: List[Dict]) -> Dict:
        """Extract key preferences from liked/disliked jobs"""
        preferences = {
            'valued_aspects': [],
            'dealbreakers': [],
            'location_preferences': {},
            'company_types': {}
        }
        
        # Analyze liked jobs for valued aspects
        if liked:
            # Extract common keywords from alignments
            all_alignments = []
            for fb in liked:
                if fb.get('key_alignments'):
                    all_alignments.append(fb['key_alignments'])
            
            if all_alignments:
                preferences['valued_aspects'] = self._find_common_themes(all_alignments)
        
        # Analyze disliked jobs for dealbreakers
        if disliked:
            all_gaps = []
            for fb in disliked:
                if fb.get('potential_gaps'):
                    all_gaps.append(fb['potential_gaps'])
                if fb.get('feedback_reason'):
                    all_gaps.append(fb['feedback_reason'])
            
            if all_gaps:
                preferences['dealbreakers'] = self._find_common_themes(all_gaps)
        
        return preferences
    
    def _find_common_themes(self, text_list: List[str]) -> List[str]:
        """Find common themes in a list of text descriptions"""
        # Simple keyword extraction (could be enhanced with NLP)
        common_keywords = [
            'leadership', 'management', 'technical', 'strategy', 'team',
            'machine learning', 'AI', 'data science', 'python', 'remote',
            'senior', 'head', 'director', 'automotive', 'startup',
            'enterprise', 'research', 'production', 'deployment'
        ]
        
        found_themes = []
        combined_text = ' '.join(text_list).lower()
        
        for keyword in common_keywords:
            if keyword.lower() in combined_text:
                found_themes.append(keyword)
        
        return found_themes[:5]  # Top 5 themes
    
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
    
    def generate_learning_context(self, user_email: str) -> str:
        """
        Generate a context string to include in Claude prompts
        This helps Claude learn from user feedback
        
        Args:
            user_email: User email
            
        Returns:
            Formatted string to include in analysis prompts
        """
        prefs = self.analyze_user_preferences(user_email)
        
        if not prefs['has_feedback']:
            return ""
        
        context_parts = [
            "\n## USER PREFERENCE LEARNING",
            f"Based on {prefs['total_feedback']} previous feedback items:",
        ]
        
        # Add liked job examples
        if prefs['liked_job_examples']:
            context_parts.append("\n### Jobs User Found Highly Relevant:")
            for job in prefs['liked_job_examples']:
                context_parts.append(
                    f"- {job['title']} at {job['company']} (score: {job['score']})"
                )
                if job.get('feedback_reason'):
                    context_parts.append(f"  Reason: {job['feedback_reason']}")
        
        # Add disliked job examples
        if prefs['disliked_job_examples']:
            context_parts.append("\n### Jobs User Found Less Relevant:")
            for job in prefs['disliked_job_examples']:
                context_parts.append(
                    f"- {job['title']} at {job['company']} (score: {job['score']})"
                )
                if job.get('feedback_reason'):
                    context_parts.append(f"  Reason: {job['feedback_reason']}")
        
        # Add key preferences
        key_prefs = prefs['key_preferences']
        if key_prefs['valued_aspects']:
            context_parts.append("\n### User Values:")
            context_parts.append(f"- {', '.join(key_prefs['valued_aspects'])}")
        
        if key_prefs['dealbreakers']:
            context_parts.append("\n### User Concerns:")
            context_parts.append(f"- {', '.join(key_prefs['dealbreakers'])}")
        
        # Add calibration guidance
        calibration = prefs['scoring_calibration']
        if calibration['needs_calibration']:
            if calibration['score_bias'] > 0:
                context_parts.append(
                    f"\n### Scoring Guidance: User finds your scores ~{int(calibration['score_bias'])} points too high. "
                    "Be more conservative in scoring."
                )
            else:
                context_parts.append(
                    f"\n### Scoring Guidance: User finds your scores ~{abs(int(calibration['score_bias']))} points too low. "
                    "Be more generous in scoring."
                )
        
        context_parts.append(
            "\n### Instructions: Use these preferences to improve match scoring. "
            "Give higher scores to jobs similar to what the user liked, "
            "and lower scores to jobs with characteristics they found problematic.\n"
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
