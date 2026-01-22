"""
ESCO Skill Mapper

Maps extracted skills/competencies to standardized ESCO taxonomy using semantic matching.
This ensures consistent skill identification across jobs and CVs.
"""

from typing import List, Dict, Optional, Tuple
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from sentence_transformers import SentenceTransformer, util
import numpy as np


class ESCOSkillMapper:
    """
    Maps free-text skills to standardized ESCO skills using semantic similarity
    """

    def __init__(self, connection_pool: SimpleConnectionPool, model_name: str = 'TechWolf/JobBERT-v3'):
        """
        Initialize ESCO skill mapper

        Args:
            connection_pool: PostgreSQL connection pool
            model_name: Sentence transformer model to use
        """
        self.pool = connection_pool
        self.model = SentenceTransformer(model_name)
        self._esco_cache = None
        self._esco_embeddings = None

    def load_esco_skills(self) -> Tuple[List[Dict], np.ndarray]:
        """
        Load ESCO skills from database and compute embeddings (cached)

        Returns:
            Tuple of (skills_list, embeddings_array)
        """
        if self._esco_cache is not None and self._esco_embeddings is not None:
            return self._esco_cache, self._esco_embeddings

        print("📚 Loading ESCO skills from database...")

        conn = self.pool.getconn()
        try:
            cur = conn.cursor()

            # Load all ESCO skills
            cur.execute("""
                SELECT uri, preferred_label, alt_labels, description, skill_type
                FROM esco_skills
                ORDER BY preferred_label
            """)

            rows = cur.fetchall()

            if not rows:
                raise ValueError("No ESCO skills found in database. Run setup_esco_database.py first.")

            skills = []
            texts_to_encode = []

            for row in rows:
                uri, preferred_label, alt_labels, description, skill_type = row

                skill = {
                    'uri': uri,
                    'preferred_label': preferred_label,
                    'alt_labels': alt_labels or [],
                    'description': description or '',
                    'skill_type': skill_type or ''
                }

                skills.append(skill)

                # Combine labels for encoding (primary + alternatives)
                text = preferred_label
                if alt_labels:
                    text += ' | ' + ' | '.join(alt_labels[:3])  # Limit alt labels

                texts_to_encode.append(text)

            print(f"  ✓ Loaded {len(skills)} ESCO skills")
            print(f"  🔢 Computing embeddings...")

            # Encode all ESCO skills
            embeddings = self.model.encode(texts_to_encode, convert_to_tensor=True, show_progress_bar=True)

            # Cache for future use
            self._esco_cache = skills
            self._esco_embeddings = embeddings

            print(f"  ✓ Ready for mapping")

            return skills, embeddings

        finally:
            self.pool.putconn(conn)

    def map_skill(self, extracted_skill: str, threshold: float = 0.6, top_k: int = 5,
                  prefer_type: Optional[str] = None) -> Optional[Dict]:
        """
        Map an extracted skill/competence to the most similar ESCO item

        Args:
            extracted_skill: Free-text skill or competence to map
            threshold: Minimum similarity score (0-1)
            top_k: Number of top candidates to consider
            prefer_type: Prefer 'skill' or 'competence' matches (None for both)

        Returns:
            Dict with ESCO mapping or None if no good match
            {
                'esco_uri': str,
                'esco_label': str,
                'esco_type': str,  # 'skill', 'competence', 'knowledge'
                'confidence': float,
                'extracted_text': str,
                'alternatives': List[Dict]  # Top alternatives
            }
        """
        if not extracted_skill or not extracted_skill.strip():
            return None

        # Check cache first
        cached = self._get_cached_mapping(extracted_skill)
        if cached:
            return cached

        # Load ESCO skills
        esco_skills, esco_embeddings = self.load_esco_skills()

        # Encode the extracted skill
        query_embedding = self.model.encode(extracted_skill, convert_to_tensor=True)

        # Compute similarities
        similarities = util.cos_sim(query_embedding, esco_embeddings)[0]

        # Get top K matches (get more if we need to filter by type)
        search_k = top_k * 3 if prefer_type else top_k
        top_indices = similarities.argsort(descending=True)[:search_k]

        results = []
        for idx in top_indices:
            idx = idx.item()
            score = similarities[idx].item()

            if score < threshold:
                continue

            skill_type = esco_skills[idx]['skill_type']

            # Filter by type if specified
            if prefer_type:
                if prefer_type.lower() not in skill_type.lower():
                    continue

            results.append({
                'esco_uri': esco_skills[idx]['uri'],
                'esco_label': esco_skills[idx]['preferred_label'],
                'esco_alt_labels': esco_skills[idx]['alt_labels'],
                'esco_description': esco_skills[idx]['description'],
                'esco_type': skill_type,
                'confidence': score
            })

            # Stop if we have enough results
            if len(results) >= top_k:
                break

        if not results:
            return None

        # Best match
        best_match = results[0]

        # Cache the mapping
        self._save_mapping(extracted_skill, best_match['esco_uri'], best_match['confidence'])

        return {
            'esco_uri': best_match['esco_uri'],
            'esco_label': best_match['esco_label'],
            'esco_alt_labels': best_match['esco_alt_labels'],
            'esco_description': best_match['esco_description'],
            'esco_type': best_match['esco_type'],
            'confidence': best_match['confidence'],
            'extracted_text': extracted_skill,
            'alternatives': results[1:]  # Other top matches
        }

    def map_skills_batch(self, extracted_skills: List[str], threshold: float = 0.6) -> List[Optional[Dict]]:
        """
        Map multiple skills in batch (more efficient)

        Args:
            extracted_skills: List of skills to map
            threshold: Minimum similarity score

        Returns:
            List of mapping dicts (or None for unmapped skills)
        """
        if not extracted_skills:
            return []

        # Load ESCO skills
        esco_skills, esco_embeddings = self.load_esco_skills()

        # Check cache for all skills
        results = []
        uncached_skills = []
        uncached_indices = []

        for i, skill in enumerate(extracted_skills):
            cached = self._get_cached_mapping(skill)
            if cached:
                results.append(cached)
            else:
                results.append(None)  # Placeholder
                uncached_skills.append(skill)
                uncached_indices.append(i)

        if not uncached_skills:
            return results

        # Encode uncached skills in batch
        print(f"  Mapping {len(uncached_skills)} skills to ESCO...")
        query_embeddings = self.model.encode(uncached_skills, convert_to_tensor=True)

        # Compute similarities for all queries
        similarities = util.cos_sim(query_embeddings, esco_embeddings)

        # Process each uncached skill
        for idx, skill in enumerate(uncached_skills):
            skill_similarities = similarities[idx]

            # Get best match
            best_idx = skill_similarities.argmax().item()
            best_score = skill_similarities[best_idx].item()

            if best_score >= threshold:
                mapping = {
                    'esco_uri': esco_skills[best_idx]['uri'],
                    'esco_label': esco_skills[best_idx]['preferred_label'],
                    'esco_alt_labels': esco_skills[best_idx]['alt_labels'],
                    'esco_description': esco_skills[best_idx]['description'],
                    'esco_type': esco_skills[best_idx]['skill_type'],
                    'confidence': best_score,
                    'extracted_text': skill
                }

                # Cache the mapping
                self._save_mapping(skill, mapping['esco_uri'], mapping['confidence'])

                # Update results
                original_idx = uncached_indices[idx]
                results[original_idx] = mapping

        return results

    def _get_cached_mapping(self, extracted_skill: str) -> Optional[Dict]:
        """Get cached mapping from database"""
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()

            cur.execute("""
                SELECT sm.esco_uri, sm.confidence, es.preferred_label, es.alt_labels, es.description, es.skill_type
                FROM skill_mappings sm
                JOIN esco_skills es ON sm.esco_uri = es.uri
                WHERE sm.extracted_text = %s
                ORDER BY sm.confidence DESC
                LIMIT 1
            """, (extracted_skill,))

            row = cur.fetchone()

            if not row:
                return None

            return {
                'esco_uri': row[0],
                'confidence': row[1],
                'esco_label': row[2],
                'esco_alt_labels': row[3] or [],
                'esco_description': row[4] or '',
                'esco_type': row[5] or '',
                'extracted_text': extracted_skill,
                'from_cache': True
            }

        finally:
            self.pool.putconn(conn)

    def _save_mapping(self, extracted_skill: str, esco_uri: str, confidence: float, source: str = 'auto'):
        """Save mapping to database for future use"""
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO skill_mappings (extracted_text, esco_uri, confidence, source)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (extracted_text, esco_uri) DO UPDATE SET
                    confidence = EXCLUDED.confidence,
                    created_at = CURRENT_TIMESTAMP
            """, (extracted_skill, esco_uri, confidence, source))

            conn.commit()

        except Exception as e:
            conn.rollback()
            print(f"Warning: Could not cache skill mapping: {e}")

        finally:
            self.pool.putconn(conn)

    def map_competence(self, extracted_competence: str, threshold: float = 0.6, top_k: int = 5) -> Optional[Dict]:
        """
        Map extracted competence to ESCO competence (convenience method)

        Args:
            extracted_competence: Free-text competence to map
            threshold: Minimum similarity score (0-1)
            top_k: Number of top candidates to consider

        Returns:
            Dict with ESCO mapping or None if no good match
        """
        return self.map_skill(extracted_competence, threshold=threshold, top_k=top_k, prefer_type='competence')

    def map_technical_skill(self, extracted_skill: str, threshold: float = 0.6, top_k: int = 5) -> Optional[Dict]:
        """
        Map extracted technical skill to ESCO skill (convenience method)

        Args:
            extracted_skill: Free-text skill to map
            threshold: Minimum similarity score (0-1)
            top_k: Number of top candidates to consider

        Returns:
            Dict with ESCO mapping or None if no good match
        """
        return self.map_skill(extracted_skill, threshold=threshold, top_k=top_k, prefer_type='skill')

    def search_esco_skills(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search ESCO skills by text query

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching ESCO skills
        """
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()

            # Use PostgreSQL full-text search
            cur.execute("""
                SELECT uri, preferred_label, alt_labels, description, skill_type,
                       ts_rank(search_vector, plainto_tsquery('english', %s)) as rank
                FROM esco_skills
                WHERE search_vector @@ plainto_tsquery('english', %s)
                ORDER BY rank DESC
                LIMIT %s
            """, (query, query, limit))

            rows = cur.fetchall()

            results = []
            for row in rows:
                results.append({
                    'uri': row[0],
                    'preferred_label': row[1],
                    'alt_labels': row[2] or [],
                    'description': row[3] or '',
                    'skill_type': row[4] or '',
                    'rank': row[5]
                })

            return results

        finally:
            self.pool.putconn(conn)


def test_mapper():
    """Test the ESCO skill mapper"""
    import os
    from dotenv import load_dotenv
    from psycopg2.pool import SimpleConnectionPool

    load_dotenv()

    DATABASE_URL = os.getenv('DATABASE_URL')
    pool = SimpleConnectionPool(1, 5, DATABASE_URL)

    mapper = ESCOSkillMapper(pool)

    # Test skills and competences separately
    test_skills = [
        "Python programming",
        "Machine learning",
        "Data analysis",
        "SQL databases",
        "Cloud computing"
    ]

    test_competences = [
        "Project management",
        "Team leadership",
        "Agile methodology",
        "Strategic thinking",
        "Communication skills"
    ]

    print("\n" + "=" * 70)
    print("Testing ESCO Skill & Competence Mapper")
    print("=" * 70)

    print("\n📝 Mapping technical skills:\n")
    for skill in test_skills[:3]:
        result = mapper.map_technical_skill(skill, threshold=0.5)
        if result:
            print(f"  '{skill}' → '{result['esco_label']}' (confidence: {result['confidence']:.2f})")
            print(f"    Type: {result['esco_type']}")
            print(f"    URI: {result['esco_uri']}")
            if result.get('alternatives'):
                print(f"    Alternatives: {len(result['alternatives'])} other matches")
        else:
            print(f"  '{skill}' → No match found")
        print()

    print("\n💼 Mapping competences:\n")
    for competence in test_competences[:3]:
        result = mapper.map_competence(competence, threshold=0.5)
        if result:
            print(f"  '{competence}' → '{result['esco_label']}' (confidence: {result['confidence']:.2f})")
            print(f"    Type: {result['esco_type']}")
            print(f"    URI: {result['esco_uri']}")
            if result.get('alternatives'):
                print(f"    Alternatives: {len(result['alternatives'])} other matches")
        else:
            print(f"  '{competence}' → No match found")
        print()

    # Test batch mapping
    print("\n📦 Batch mapping (mixed skills & competences):\n")
    all_items = test_skills[3:] + test_competences[3:]
    results = mapper.map_skills_batch(all_items, threshold=0.5)
    for item, result in zip(all_items, results):
        if result:
            print(f"  '{item}' → '{result['esco_label']}' [{result['esco_type']}] ({result['confidence']:.2f})")
        else:
            print(f"  '{item}' → No match")

    pool.closeall()


if __name__ == '__main__':
    test_mapper()
