"""
Semantic Matcher for Competency and Skill Matching

Uses sentence-transformers to compute semantic similarity between
job requirements and user profile, enabling matching beyond exact keywords.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class SemanticMatcher:
    """
    Singleton class for semantic similarity matching using sentence-transformers.
    
    Uses paraphrase-multilingual-MiniLM-L12-v2 for multilingual support,
    consistent with existing semantic filtering in filter_jobs.py.
    """
    
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the model (lazy loading on first use)"""
        if self._model is None:
            self._load_model()
    
    def _load_model(self):
        """Load the sentence transformer model"""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading semantic similarity model...")
            self._model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            logger.info("✓ Semantic model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load semantic model: {e}")
            self._model = None
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two text strings.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        if not self._model:
            return 0.0
        
        try:
            embeddings = self._model.encode([text1, text2])
            # Compute cosine similarity
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
            return float(similarity)
        except Exception as e:
            logger.error(f"Error computing similarity: {e}")
            return 0.0
    
    def match_competencies(
        self, 
        job_competencies: List[str], 
        user_competencies: List[str],
        user_skills: List[str] = None,
        threshold: float = 0.45
    ) -> Dict[str, bool]:
        """
        Match job competencies against user competencies and skills.
        
        Args:
            job_competencies: List of job competency requirements
            user_competencies: List of user competencies from CV
            user_skills: Optional list of user technical skills (often overlaps)
            threshold: Minimum similarity score to consider a match (default 0.45)
            
        Returns:
            Dict mapping each job competency to boolean (matched or not)
        """
        if not self._model or not job_competencies:
            return {comp: False for comp in job_competencies}
        
        # Combine user competencies and skills for broader matching
        user_terms = list(user_competencies) if user_competencies else []
        if user_skills:
            user_terms.extend(user_skills)
        
        if not user_terms:
            return {comp: False for comp in job_competencies}
        
        try:
            # Encode all texts in batches for efficiency
            job_embeddings = self._model.encode(job_competencies)
            user_embeddings = self._model.encode(user_terms)
            
            matches = {}
            for idx, job_comp in enumerate(job_competencies):
                # Find best matching user term
                max_similarity = 0.0
                for user_emb in user_embeddings:
                    similarity = np.dot(job_embeddings[idx], user_emb) / (
                        np.linalg.norm(job_embeddings[idx]) * np.linalg.norm(user_emb)
                    )
                    max_similarity = max(max_similarity, similarity)
                
                matches[job_comp] = max_similarity >= threshold
                
                # Log high-confidence matches for debugging
                if max_similarity >= threshold:
                    logger.debug(f"Semantic match: '{job_comp}' (similarity: {max_similarity:.3f})")
            
            return matches
            
        except Exception as e:
            logger.error(f"Error in match_competencies: {e}")
            return {comp: False for comp in job_competencies}
    
    def match_skills(
        self,
        job_skills: List[str],
        user_skills: List[str],
        threshold: float = 0.50
    ) -> Dict[str, bool]:
        """
        Match job skills against user skills.
        
        Args:
            job_skills: List of required technical skills
            user_skills: List of user's technical skills
            threshold: Minimum similarity score (default 0.50, higher for skills)
            
        Returns:
            Dict mapping each job skill to boolean (matched or not)
        """
        if not self._model or not job_skills or not user_skills:
            return {skill: False for skill in job_skills}
        
        try:
            # Encode skills
            job_embeddings = self._model.encode(job_skills)
            user_embeddings = self._model.encode(user_skills)
            
            matches = {}
            for idx, job_skill in enumerate(job_skills):
                # Find best matching user skill
                max_similarity = 0.0
                for user_emb in user_embeddings:
                    similarity = np.dot(job_embeddings[idx], user_emb) / (
                        np.linalg.norm(job_embeddings[idx]) * np.linalg.norm(user_emb)
                    )
                    max_similarity = max(max_similarity, similarity)
                
                matches[job_skill] = max_similarity >= threshold
                
                # Log matches
                if max_similarity >= threshold:
                    logger.debug(f"Semantic skill match: '{job_skill}' (similarity: {max_similarity:.3f})")
            
            return matches
            
        except Exception as e:
            logger.error(f"Error in match_skills: {e}")
            return {skill: False for skill in job_skills}


# Singleton instance
_semantic_matcher = None


def get_semantic_matcher() -> SemanticMatcher:
    """Get or create the singleton SemanticMatcher instance"""
    global _semantic_matcher
    if _semantic_matcher is None:
        _semantic_matcher = SemanticMatcher()
    return _semantic_matcher
