"""
Skill and Competency Normalizer

Resolves three categories of duplication in AI-extracted job terms:
  1. Case variation:     Javascript  -> JavaScript
  2. Semantic aliases:   Communication Skills -> Communication
  3. German->English:    Teamarbeit  -> Teamwork

Pipeline order (matters for chaining):
  German -> DB map -> Alias -> Casing
  e.g. "Kommunikationsfähigkeit" -> German  -> "Communication Skills"
                                 -> DB map  -> "Communication"   (if populated)
                                 -> Alias   -> "Communication"   (static fallback)

The DB map is checked before the static aliases so that embedding-derived
canonicals (which may be more specific) take priority.  It is backed by the
skill_canonical_map Postgres table and refreshed in-process every 5 minutes.

Usage:
    from analysis.skill_normalizer import normalize_term, normalize_and_deduplicate
"""

import os
import time
from typing import List


# ---------------------------------------------------------------------------
# 1. GERMAN -> ENGLISH MAP
#    Keys: lowercase German term (both umlaut and oe-spelled variants).
#    Values: English form (may need a second pass through SEMANTIC_ALIASES).
# ---------------------------------------------------------------------------
GERMAN_TO_ENGLISH = {
    # Core soft skills
    "teamarbeit":                "Teamwork",
    "teamfähigkeit":             "Teamwork",
    "teamfaehigkeit":            "Teamwork",
    "kommunikation":             "Communication",
    "kommunikationsfähigkeit":   "Communication Skills",
    "kommunikationsfaehigkeit":  "Communication Skills",
    "führung":                   "Leadership",
    "führungskräfte":            "Leadership",
    "fuehrung":                  "Leadership",
    "fuehrungskraefte":          "Leadership",
    "problemlösung":             "Problem Solving",
    "problemloesung":            "Problem Solving",
    "analytisches denken":       "Analytical Thinking",
    "kritisches denken":         "Critical Thinking",
    "zeitmanagement":            "Time Management",
    "selbstständigkeit":         "Independence",
    "selbststaendigkeit":        "Independence",
    "verantwortungsbewusstsein": "Responsibility",
    "kundenorientierung":        "Customer Orientation",
    "flexibilität":              "Flexibility",
    "flexibilitaet":             "Flexibility",
    "kreativität":               "Creativity",
    "kreativitaet":              "Creativity",
    "konfliktlösung":            "Conflict Resolution",
    "konfliktloesung":           "Conflict Resolution",
    "strategisches denken":      "Strategic Thinking",
    "entscheidungsfähigkeit":    "Decision Making",
    "entscheidungsfaehigkeit":   "Decision Making",
    "zusammenarbeit":            "Collaboration",
    "organisationsfähigkeit":    "Organizational Skills",
    "organisationsfaehigkeit":   "Organizational Skills",
    "präsentation":              "Presentation",
    "praesentation":             "Presentation",
    "verhandlungsfähigkeit":     "Negotiation",
    "verhandlungsfaehigkeit":    "Negotiation",
    "adaptationsfähigkeit":      "Adaptability",
    "adaptationsfaehigkeit":     "Adaptability",
    "mentoring":                 "Mentoring",
    "coaching":                  "Coaching",

    # Technical / project terms
    "projektmanagement":         "Project Management",
    "risikomanagement":          "Risk Management",
    "qualitätssicherung":        "Quality Assurance",
    "qualitaetssicherung":       "Quality Assurance",
    "datenanalyse":              "Data Analysis",
    "maschinelles lernen":       "Machine Learning",
    "künstliche intelligenz":    "Artificial Intelligence",
    "kuenstliche intelligenz":   "Artificial Intelligence",
    "cloud-computing":           "Cloud Computing",
    "agile methodiken":          "Agile Methodologies",
    "scrum":                     "Scrum",
    "devops":                    "DevOps",

    # Common single-word German terms
    "erfahrung":                 "Experience",
    "kenntnisse":                "Knowledge",
    "fähigkeiten":               "Skills",
    "faehigkeiten":              "Skills",
}

# ---------------------------------------------------------------------------
# 2. SEMANTIC ALIAS MAP
#    Keys: lowercase input variant.  Values: canonical display form.
#    Alias values are already in final canonical form — normalize_term()
#    returns them immediately without further passes.
# ---------------------------------------------------------------------------
SEMANTIC_ALIASES = {
    # --- Communication family ---
    "communication skills":      "Communication",
    "communication":             "Communication",
    "verbal communication":      "Communication",
    "written communication":     "Communication",

    # --- React family ---
    "reactjs":                   "React",
    "react.js":                  "React",
    "react":                     "React",

    # --- Node family ---
    "nodejs":                    "Node.js",
    "node.js":                   "Node.js",
    "node":                      "Node.js",

    # --- JavaScript / TypeScript ---
    "javascript":                "JavaScript",
    "typescript":                "TypeScript",

    # --- PostgreSQL family ---
    "postgresql":                "PostgreSQL",
    "postgres":                  "PostgreSQL",

    # --- Cloud providers ---
    "aws":                       "AWS",
    "amazon web services":       "AWS",
    "azure":                     "Azure",
    "microsoft azure":           "Azure",
    "gcp":                       "GCP",
    "google cloud platform":     "GCP",
    "google cloud":              "GCP",

    # --- Containers / orchestration ---
    "docker":                    "Docker",
    "kubernetes":                "Kubernetes",
    "k8s":                       "Kubernetes",

    # --- Databases ---
    "mongodb":                   "MongoDB",
    "mysql":                     "MySQL",
    "redis":                     "Redis",
    "sql":                       "SQL",

    # --- APIs ---
    "restful":                   "RESTful APIs",
    "rest api":                  "RESTful APIs",
    "rest apis":                 "RESTful APIs",
    "restful apis":              "RESTful APIs",
    "graphql":                   "GraphQL",

    # --- Frontend frameworks ---
    "vue":                       "Vue.js",
    "vue.js":                    "Vue.js",
    "vuejs":                     "Vue.js",
    "angular":                   "Angular",
    "angularjs":                 "Angular",
    "next.js":                   "Next.js",
    "nextjs":                    "Next.js",

    # --- Backend frameworks ---
    "django":                    "Django",
    "flask":                     "Flask",
    "spring":                    "Spring",
    "spring boot":               "Spring Boot",
    "springboot":                "Spring Boot",

    # --- ML / Data ---
    "tensorflow":                "TensorFlow",
    "pytorch":                   "PyTorch",
    "scikit-learn":              "Scikit-learn",
    "sklearn":                   "Scikit-learn",
    "pandas":                    "Pandas",
    "numpy":                     "NumPy",
    "machine learning":          "Machine Learning",
    "ml":                        "Machine Learning",
    "artificial intelligence":   "Artificial Intelligence",
    "data science":              "Data Science",
    "data engineering":          "Data Engineering",
    "data analysis":             "Data Analysis",
    "data analytics":            "Data Analysis",
    "natural language processing": "NLP",
    "nlp":                       "NLP",
    "deep learning":             "Deep Learning",
    "computer vision":           "Computer Vision",

    # --- DevOps / CI ---
    "ci/cd":                     "CI/CD",
    "cicd":                      "CI/CD",
    "devops":                    "DevOps",
    "terraform":                 "Terraform",
    "linux":                     "Linux",
    "git":                       "Git",
    "github":                    "GitHub",
    "gitlab":                    "GitLab",

    # --- Methodologies ---
    "agile":                     "Agile",
    "scrum":                     "Scrum",

    # --- Management / roles ---
    "project management":        "Project Management",
    "project mgmt":              "Project Management",
    "product management":        "Product Management",
    "leadership":                "Leadership",
    "team leadership":           "Leadership",
    "technical leadership":      "Technical Leadership",
    "teamwork":                  "Teamwork",
    "team collaboration":        "Teamwork",
    "cross-functional collaboration": "Cross-Functional Collaboration",
    "cross-functional communication": "Cross-Functional Collaboration",
    "quality assurance":         "Quality Assurance",
    "qa":                        "Quality Assurance",

    # --- Design ---
    "ux design":                 "UX Design",
    "ui design":                 "UI Design",
    "ui/ux design":              "UX Design",
    "user experience":           "UX Design",

    # --- Languages ---
    "python":                    "Python",
    "java":                      "Java",
    "c#":                        "C#",
    "csharp":                    "C#",
    "c++":                       "C++",
    "cpp":                       "C++",
}

# ---------------------------------------------------------------------------
# 3. CANONICAL CASING MAP
#    Last-pass fallback. Only fires for terms NOT already in SEMANTIC_ALIASES.
#    Fixes casing on terms that slip through (e.g. all-lowercase variants
#    not explicitly listed above).
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# DB MAP CACHE
#    Module-level cache of skill_canonical_map.  Refreshed every _DB_MAP_TTL
#    seconds.  Falls back silently if the table does not exist yet or the DB
#    is unreachable — the static maps still work in that case.
# ---------------------------------------------------------------------------
_db_map_cache: dict = {}          # variant (lowercase) -> canonical (display)
_db_map_loaded_at: float = 0.0
_DB_MAP_TTL: int = 300            # seconds


def _load_db_map():
    """Reload _db_map_cache from Postgres if the TTL has expired."""
    global _db_map_cache, _db_map_loaded_at
    now = time.time()
    if _db_map_loaded_at > 0 and (now - _db_map_loaded_at) < _DB_MAP_TTL:
        return  # still fresh
    db_url = os.getenv('DATABASE_URL', '')
    if not db_url.startswith('postgres'):
        return  # no Postgres available — static maps only
    try:
        import psycopg2
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT variant, canonical FROM skill_canonical_map")
        _db_map_cache = {row[0]: row[1] for row in cur.fetchall()}
        cur.close()
        conn.close()
        _db_map_loaded_at = time.time()
    except Exception:
        pass  # table may not exist yet — static maps still work


CANONICAL_CASING = {
    "javascript":      "JavaScript",
    "typescript":      "TypeScript",
    "postgresql":      "PostgreSQL",
    "mongodb":         "MongoDB",
    "graphql":         "GraphQL",
    "nodejs":          "Node.js",
    "node.js":         "Node.js",
    "reactjs":         "React",
    "react.js":        "React",
    "vue.js":          "Vue.js",
    "next.js":         "Next.js",
    "scikit-learn":    "Scikit-learn",
    "tensorflow":      "TensorFlow",
    "pytorch":         "PyTorch",
    "pandas":          "Pandas",
    "numpy":           "NumPy",
    "github":          "GitHub",
    "gitlab":          "GitLab",
    "ci/cd":           "CI/CD",
    "devops":          "DevOps",
    "aws":             "AWS",
    "azure":           "Azure",
    "gcp":             "GCP",
    "nlp":             "NLP",
    "qa":              "Quality Assurance",
    "mysql":           "MySQL",
    "redis":           "Redis",
    "kubernetes":      "Kubernetes",
    "k8s":             "Kubernetes",
    "c#":              "C#",
    "c++":             "C++",
}


def normalize_term(term: str) -> str:
    """
    Normalize a single competency or skill term.

    Pipeline (order matters):
        1. Strip whitespace.
        2. German->English lookup (lowercased). If hit, continue with English value.
        3. DB map lookup (cached, TTL 300 s). If hit, return immediately.
        4. Semantic-alias lookup (lowercased). If hit, return immediately —
           alias values are already in canonical form.
        5. Canonical-casing lookup (lowercased). If hit, return casing value.
        6. Otherwise return the original stripped term unchanged.

    Args:
        term: Raw competency or skill string (e.g. "Javascript", "Teamarbeit")

    Returns:
        Normalized canonical string (e.g. "JavaScript", "Teamwork")
    """
    if not term or not term.strip():
        return term

    stripped = term.strip()
    lower = stripped.lower()

    # Pass 1: German -> English (static)
    if lower in GERMAN_TO_ENGLISH:
        stripped = GERMAN_TO_ENGLISH[lower]
        lower = stripped.lower()

    # Pass 2: DB map (cached, refreshed every _DB_MAP_TTL seconds)
    _load_db_map()
    if lower in _db_map_cache:
        return _db_map_cache[lower]

    # Pass 3: Semantic alias (static fallback)
    if lower in SEMANTIC_ALIASES:
        return SEMANTIC_ALIASES[lower]

    # Pass 4: Canonical casing (static fallback)
    if lower in CANONICAL_CASING:
        return CANONICAL_CASING[lower]

    # No map hit — return stripped original
    return stripped


def normalize_and_deduplicate(terms: List[str]) -> List[str]:
    """
    Normalize every term in the list, then deduplicate while preserving
    the order of first occurrence.

    Example:
        ["Communication Skills", "Teamarbeit", "Communication", "Teamwork"]
        -> ["Communication", "Teamwork"]

    Args:
        terms: List of raw competency/skill strings

    Returns:
        Deduplicated list in first-occurrence order, each term normalized
    """
    seen = set()
    result = []
    for term in terms:
        normalized = normalize_term(term)
        key = normalized.lower()
        if key not in seen:
            seen.add(key)
            result.append(normalized)
    return result
