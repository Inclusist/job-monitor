#!/usr/bin/env python3
"""
One-time enrichment of skill_canonical_map

Populates the table in two phases:
    A. Static seeding  – every entry from the three lookup maps in
       skill_normalizer.py is resolved through the full pipeline and
       inserted with confidence=1.0, source='static'.
    B. Embedding clustering – all unique terms extracted from jobs
       (ai_competencies + ai_key_skills) that are NOT already in the
       map are clustered via cosine similarity using
       paraphrase-multilingual-MiniLM-L12-v2.  The most-frequent term
       in each cluster becomes the canonical.

Usage:
    python scripts/enrich_canonical_map.py
    python scripts/enrich_canonical_map.py --threshold 0.80
    python scripts/enrich_canonical_map.py --dry-run            # print plan, no writes
"""
import os
import sys
import argparse
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import execute_values
import numpy as np

from src.analysis.skill_normalizer import (
    GERMAN_TO_ENGLISH,
    SEMANTIC_ALIASES,
    CANONICAL_CASING,
    normalize_term,
)


# ---------------------------------------------------------------------------
# Phase A – Static seeding
# ---------------------------------------------------------------------------
def _build_static_pairs():
    """
    Flatten all three static maps into (variant_lower, canonical) pairs.
    German entries are resolved through the full normalize_term() pipeline
    so that chained aliases (e.g. kommunikationsfähigkeit → Communication
    Skills → Communication) produce the final canonical.
    """
    pairs = {}

    # SEMANTIC_ALIASES – values are already canonical
    for variant, canonical in SEMANTIC_ALIASES.items():
        pairs[variant.lower().strip()] = canonical

    # CANONICAL_CASING – values are already canonical
    for variant, canonical in CANONICAL_CASING.items():
        pairs[variant.lower().strip()] = canonical

    # GERMAN_TO_ENGLISH – resolve English value through alias/casing
    for variant, english in GERMAN_TO_ENGLISH.items():
        canonical = normalize_term(english)  # resolves alias chain
        pairs[variant.lower().strip()] = canonical

    return pairs


def _seed_static(cursor, pairs, dry_run):
    """INSERT static pairs with ON CONFLICT DO NOTHING"""
    if dry_run:
        print(f"   [dry-run] Would insert {len(pairs)} static entries")
        return len(pairs)

    rows = [(v, c, 1.0, 'static') for v, c in pairs.items()]
    execute_values(
        cursor,
        """
        INSERT INTO skill_canonical_map (variant, canonical, confidence, source)
        VALUES %s
        ON CONFLICT (variant) DO NOTHING
        """,
        rows,
    )
    return len(rows)


# ---------------------------------------------------------------------------
# Phase B – Collect terms from DB
# ---------------------------------------------------------------------------
_TERM_QUERY = """
SELECT term, COUNT(*) as freq
FROM (
    SELECT unnest(ai_competencies) as term FROM jobs WHERE ai_competencies IS NOT NULL
    UNION ALL
    SELECT unnest(ai_key_skills)   as term FROM jobs WHERE ai_key_skills   IS NOT NULL
) sub
WHERE term IS NOT NULL AND term != ''
GROUP BY term
ORDER BY freq DESC
"""


def _collect_terms(cursor):
    """
    Returns list of (term_original_casing, frequency) sorted by freq DESC.
    """
    cursor.execute(_TERM_QUERY)
    return cursor.fetchall()  # [(term, freq), ...]


def _load_existing_variants(cursor):
    """Set of variant keys already in the map"""
    cursor.execute("SELECT variant FROM skill_canonical_map")
    return {row[0] for row in cursor.fetchall()}


# ---------------------------------------------------------------------------
# Phase B – Embedding + clustering
# ---------------------------------------------------------------------------
def _load_model():
    from sentence_transformers import SentenceTransformer
    print("   Loading paraphrase-multilingual-MiniLM-L12-v2...")
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device='cpu')
    print("   Model loaded")
    return model


def _unit_normalize(vectors: np.ndarray) -> np.ndarray:
    """L2-normalize rows in place, return view"""
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def _cluster_greedy(embeddings: np.ndarray, threshold: float):
    """
    Greedy frequency-ordered clustering.

    embeddings: unit-normalized, rows ordered by frequency DESC.
    Returns: list of (canonical_idx, [(member_idx, similarity), ...])
    """
    n = embeddings.shape[0]
    assigned = {}  # idx -> canonical_idx

    # Pre-compute full similarity matrix (N x N) — for 14K terms this is
    # ~1.5 GB float64; use float32 to halve it.  For very large N we could
    # do row-by-row, but 14K x 14K float32 = 784 MB which is fine.
    # If N > 30_000 fall back to row-by-row to stay under 2 GB.
    if n <= 30_000:
        sim_matrix = (embeddings @ embeddings.T).astype(np.float32)
    else:
        sim_matrix = None  # will compute row-by-row

    clusters = []  # [(canonical_idx, [(member_idx, sim), ...])]

    for i in range(n):
        if i in assigned:
            continue
        # i is the most-frequent unassigned term → becomes canonical
        assigned[i] = i
        members = []

        if sim_matrix is not None:
            sims = sim_matrix[i]
        else:
            sims = (embeddings @ embeddings[i]).astype(np.float32)

        for j in range(i + 1, n):
            if j in assigned:
                continue
            if sims[j] >= threshold:
                assigned[j] = i
                members.append((j, float(sims[j])))

        clusters.append((i, members))

    return clusters


def _run_embedding_phase(cursor, unmapped_terms, threshold, dry_run):
    """
    unmapped_terms: list of (original_cased_term, frequency) — already filtered.
    Returns number of rows written.
    """
    if not unmapped_terms:
        print("   No unmapped terms to cluster")
        return 0

    model = _load_model()

    terms_cased = [t[0] for t in unmapped_terms]  # original casing
    terms_lower = [t.lower().strip() for t in terms_cased]

    print(f"   Encoding {len(terms_cased)} terms...")
    t0 = time.time()
    raw_embeddings = model.encode(terms_cased, show_progress_bar=False, convert_to_numpy=True)
    embeddings = _unit_normalize(raw_embeddings.astype(np.float32))
    print(f"   Encoded in {time.time() - t0:.1f}s")

    print(f"   Clustering (threshold={threshold})...")
    t0 = time.time()
    clusters = _cluster_greedy(embeddings, threshold)
    print(f"   Clustered in {time.time() - t0:.1f}s")

    # Summarize
    n_clusters = len(clusters)
    n_mapped = sum(len(members) for _, members in clusters)
    n_new_canonicals = n_clusters  # each cluster head is a new canonical
    print(f"   Clusters: {n_clusters}  |  Terms mapped to existing canonical: {n_mapped}")

    if dry_run:
        print(f"   [dry-run] Would insert {n_clusters + n_mapped} embedding rows")
        # Print a sample
        for ci, (head, members) in enumerate(clusters[:10]):
            canonical_display = terms_cased[head]
            if members:
                sample = [(terms_cased[m], f"{s:.3f}") for m, s in members[:3]]
                print(f"      {canonical_display} <- {sample}")
        if len(clusters) > 10:
            print(f"      ... and {len(clusters) - 10} more clusters")
        return 0

    # Build rows for INSERT
    rows = []
    for head_idx, members in clusters:
        canonical_display = terms_cased[head_idx]
        # Head maps to itself (confidence = 1.0 since it IS the canonical)
        rows.append((terms_lower[head_idx], canonical_display, 1.0, 'embedding'))
        # Members map to the head
        for member_idx, sim in members:
            rows.append((terms_lower[member_idx], canonical_display, sim, 'embedding'))

    execute_values(
        cursor,
        """
        INSERT INTO skill_canonical_map (variant, canonical, confidence, source)
        VALUES %s
        ON CONFLICT (variant) DO NOTHING
        """,
        rows,
    )
    return len(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='Enrich skill_canonical_map')
    parser.add_argument('--threshold', type=float, default=0.75,
                        help='Cosine similarity threshold for clustering (default 0.75)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print plan without writing to DB')
    args = parser.parse_args()

    print("=" * 70)
    print("ENRICH CANONICAL SKILL MAP")
    print("=" * 70)
    print(f"Threshold: {args.threshold}  |  Dry-run: {args.dry_run}")
    print()

    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    conn.autocommit = False
    cursor = conn.cursor()

    try:
        # --- Phase A: Static seeding ---
        print("Phase A: Static seeding")
        static_pairs = _build_static_pairs()
        print(f"   Built {len(static_pairs)} static (variant, canonical) pairs")
        static_inserted = _seed_static(cursor, static_pairs, args.dry_run)
        if not args.dry_run:
            conn.commit()
            print(f"   Inserted {static_inserted} static rows (ON CONFLICT DO NOTHING)")
        print()

        # --- Phase B: Collect + filter + cluster ---
        print("Phase B: Embedding-based clustering")
        all_terms = _collect_terms(cursor)
        print(f"   Unique terms in jobs: {len(all_terms)}")

        existing_variants = _load_existing_variants(cursor)
        print(f"   Already mapped (from static or prior run): {len(existing_variants)}")

        # Filter: keep only terms whose lowercased form is not yet mapped
        unmapped = [(term, freq) for term, freq in all_terms
                    if term.lower().strip() not in existing_variants]
        print(f"   Unmapped terms to cluster: {len(unmapped)}")
        print()

        if unmapped:
            embedding_rows = _run_embedding_phase(
                cursor, unmapped, args.threshold, args.dry_run
            )
            if not args.dry_run:
                conn.commit()
                print(f"   Committed {embedding_rows} embedding rows")
        print()

        # --- Summary ---
        if not args.dry_run:
            cursor.execute(
                "SELECT source, COUNT(*) FROM skill_canonical_map GROUP BY source ORDER BY source"
            )
            print("Final map contents:")
            for source, count in cursor.fetchall():
                print(f"   {source}: {count}")
            cursor.execute("SELECT COUNT(DISTINCT canonical) FROM skill_canonical_map")
            print(f"   Distinct canonicals: {cursor.fetchone()[0]}")

        print()
        print("=" * 70)
        print("DONE")
        print("=" * 70)

    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
