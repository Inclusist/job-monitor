#!/usr/bin/env python3
"""
Test script to compare English-only vs Multilingual embedding models

This script demonstrates the difference between:
- all-MiniLM-L6-v2 (current, English-focused)
- paraphrase-multilingual-MiniLM-L12-v2 (multilingual)

Run: python tests/test_multilingual_models.py
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from sentence_transformers import SentenceTransformer


# ============================================================================
# TEST DATA - Realistic CV and Job Descriptions
# ============================================================================

CV_TEXT_ENGLISH = """
Senior Data Scientist with 8 years of experience in machine learning and artificial intelligence.

Skills:
- Python, R, SQL
- Machine Learning (scikit-learn, TensorFlow, PyTorch)
- Deep Learning and Neural Networks
- Natural Language Processing
- Data visualization (matplotlib, seaborn, plotly)
- Big Data (Spark, Hadoop)
- Cloud platforms (AWS, Azure)

Experience:
- Led ML projects for customer segmentation and churn prediction
- Developed recommendation systems using collaborative filtering
- Built NLP models for sentiment analysis
- Managed data science teams of 5+ engineers
- Published research in computer vision

Looking for senior data scientist or machine learning engineer roles in Germany.
"""

# German job postings (from Arbeitsagentur/StepStone)
GERMAN_JOBS = [
    {
        "title": "Senior Datenwissenschaftler (m/w/d)",
        "description": """
        Wir suchen einen erfahrenen Datenwissenschaftler für unser Team in Berlin.

        Ihre Aufgaben:
        - Entwicklung von Machine-Learning-Modellen
        - Arbeit mit großen Datenmengen (Big Data)
        - Zusammenarbeit mit Software-Ingenieuren
        - Leitung von KI-Projekten

        Anforderungen:
        - Mindestens 5 Jahre Erfahrung in Data Science
        - Expertise in Python, R und SQL
        - Erfahrung mit TensorFlow oder PyTorch
        - Kenntnisse in Deep Learning
        - Teamführungserfahrung von Vorteil

        Wir bieten ein innovatives Arbeitsumfeld und Weiterbildungsmöglichkeiten.
        """
    },
    {
        "title": "Machine Learning Engineer",
        "description": """
        Für unser KI-Team in München suchen wir einen Machine Learning Engineer.

        Was Sie erwartet:
        - Entwicklung und Optimierung von ML-Algorithmen
        - Arbeit mit neuronalen Netzen
        - Deployment von ML-Modellen in der Cloud (AWS/Azure)
        - Code-Reviews und Best Practices

        Ihr Profil:
        - Studium in Informatik, Mathematik oder verwandtem Bereich
        - Sehr gute Python-Kenntnisse
        - Erfahrung mit scikit-learn, TensorFlow
        - Kenntnisse in Natural Language Processing erwünscht
        - Deutsch oder Englisch fließend
        """
    },
    {
        "title": "Data Analyst",
        "description": """
        Unser Business Intelligence Team sucht Verstärkung.

        Ihre Tätigkeiten:
        - Datenanalyse und Reporting
        - Erstellung von Dashboards
        - SQL-Abfragen optimieren
        - Zusammenarbeit mit Fachabteilungen

        Was wir erwarten:
        - Erfahrung mit SQL und Excel
        - Grundkenntnisse in Python oder R
        - Visualisierungstools (Tableau, Power BI)
        - Analytisches Denkvermögen
        """
    }
]

# English job postings (for comparison)
ENGLISH_JOBS = [
    {
        "title": "Senior Data Scientist",
        "description": """
        We are looking for an experienced Data Scientist to join our team in Berlin.

        Responsibilities:
        - Develop machine learning models
        - Work with large datasets (Big Data)
        - Collaborate with software engineers
        - Lead AI projects

        Requirements:
        - At least 5 years of experience in Data Science
        - Expertise in Python, R, and SQL
        - Experience with TensorFlow or PyTorch
        - Knowledge of Deep Learning
        - Team leadership experience preferred

        We offer an innovative work environment and training opportunities.
        """
    },
    {
        "title": "Machine Learning Engineer",
        "description": """
        Our AI team in Munich is looking for a Machine Learning Engineer.

        What to expect:
        - Development and optimization of ML algorithms
        - Work with neural networks
        - Deployment of ML models to the cloud (AWS/Azure)
        - Code reviews and best practices

        Your profile:
        - Degree in Computer Science, Mathematics, or related field
        - Strong Python skills
        - Experience with scikit-learn, TensorFlow
        - Knowledge of Natural Language Processing desired
        - Fluent in German or English
        """
    },
    {
        "title": "Data Analyst",
        "description": """
        Our Business Intelligence team is looking for support.

        Your activities:
        - Data analysis and reporting
        - Creation of dashboards
        - Optimize SQL queries
        - Collaboration with departments

        What we expect:
        - Experience with SQL and Excel
        - Basic knowledge of Python or R
        - Visualization tools (Tableau, Power BI)
        - Analytical thinking
        """
    }
]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def calculate_similarity(embedding1, embedding2):
    """Calculate cosine similarity between two embeddings"""
    return np.dot(embedding1, embedding2) / (
        np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
    )


def format_percentage(value):
    """Format similarity as percentage with color"""
    pct = value * 100
    if pct >= 70:
        color = '🟢'
    elif pct >= 50:
        color = '🟡'
    else:
        color = '🔴'
    return f"{color} {pct:5.1f}%"


# ============================================================================
# MAIN TEST
# ============================================================================

def main():
    print("\n" + "="*80)
    print("MULTILINGUAL EMBEDDING MODEL COMPARISON")
    print("="*80)
    print("\nThis test compares:")
    print("  1. all-MiniLM-L6-v2 (Current - English-focused)")
    print("  2. paraphrase-multilingual-MiniLM-L12-v2 (Multilingual)")
    print("\n" + "="*80 + "\n")

    # ========================================================================
    # LOAD MODELS
    # ========================================================================

    print("📥 Loading models...\n")

    print("  [1/2] Loading English-only model (all-MiniLM-L6-v2)...")
    start = time.time()
    model_english = SentenceTransformer('all-MiniLM-L6-v2')
    time_english_load = time.time() - start
    print(f"        ✅ Loaded in {time_english_load:.2f}s")

    print("\n  [2/2] Loading Multilingual model (paraphrase-multilingual-MiniLM-L12-v2)...")
    print("        ⚠️  First run will download ~420MB (one-time, cached afterwards)")
    start = time.time()
    model_multilingual = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    time_multilingual_load = time.time() - start
    print(f"        ✅ Loaded in {time_multilingual_load:.2f}s")

    print("\n" + "="*80)
    print("ENCODING CV")
    print("="*80 + "\n")

    # Encode CV with both models
    print("CV Text (English):")
    print(CV_TEXT_ENGLISH[:200] + "...\n")

    print("Encoding with English model...")
    start = time.time()
    cv_embedding_english = model_english.encode(CV_TEXT_ENGLISH, show_progress_bar=False)
    time_cv_english = time.time() - start
    print(f"  ✅ Encoded in {time_cv_english*1000:.0f}ms")

    print("Encoding with Multilingual model...")
    start = time.time()
    cv_embedding_multilingual = model_multilingual.encode(CV_TEXT_ENGLISH, show_progress_bar=False)
    time_cv_multilingual = time.time() - start
    print(f"  ✅ Encoded in {time_cv_multilingual*1000:.0f}ms")

    # ========================================================================
    # TEST 1: GERMAN JOBS (Critical test)
    # ========================================================================

    print("\n" + "="*80)
    print("TEST 1: MATCHING ENGLISH CV WITH GERMAN JOB POSTINGS")
    print("="*80)
    print("\n⚠️  This is the CRITICAL test - most Arbeitsagentur jobs are in German!")
    print()

    results_german = []

    for idx, job in enumerate(GERMAN_JOBS, 1):
        print(f"\n[Job {idx}] {job['title']}")
        print("-" * 80)
        print(job['description'][:150] + "...\n")

        job_text = f"{job['title']} {job['description']}"

        # Encode with English model
        start = time.time()
        job_embedding_english = model_english.encode(job_text, show_progress_bar=False)
        time_job_english = time.time() - start
        similarity_english = calculate_similarity(cv_embedding_english, job_embedding_english)

        # Encode with Multilingual model
        start = time.time()
        job_embedding_multilingual = model_multilingual.encode(job_text, show_progress_bar=False)
        time_job_multilingual = time.time() - start
        similarity_multilingual = calculate_similarity(cv_embedding_multilingual, job_embedding_multilingual)

        print(f"English Model:      {format_percentage(similarity_english)} similarity")
        print(f"Multilingual Model: {format_percentage(similarity_multilingual)} similarity")
        print(f"Improvement:        {format_percentage(similarity_multilingual - similarity_english)} ({((similarity_multilingual/similarity_english - 1) * 100):.0f}% better)")

        # Threshold check (30% for current system)
        threshold = 0.30
        passes_english = "✅ PASS" if similarity_english >= threshold else "❌ FILTERED OUT"
        passes_multilingual = "✅ PASS" if similarity_multilingual >= threshold else "❌ FILTERED OUT"

        print(f"\nAt 30% threshold:")
        print(f"  English Model:      {passes_english}")
        print(f"  Multilingual Model: {passes_multilingual}")

        results_german.append({
            'job': job['title'],
            'english': similarity_english,
            'multilingual': similarity_multilingual
        })

    # ========================================================================
    # TEST 2: ENGLISH JOBS (Baseline test)
    # ========================================================================

    print("\n" + "="*80)
    print("TEST 2: MATCHING ENGLISH CV WITH ENGLISH JOB POSTINGS")
    print("="*80)
    print("\n📊 Baseline test - both models should perform well here")
    print()

    results_english = []

    for idx, job in enumerate(ENGLISH_JOBS, 1):
        print(f"\n[Job {idx}] {job['title']}")
        print("-" * 80)

        job_text = f"{job['title']} {job['description']}"

        # Encode with English model
        job_embedding_english = model_english.encode(job_text, show_progress_bar=False)
        similarity_english = calculate_similarity(cv_embedding_english, job_embedding_english)

        # Encode with Multilingual model
        job_embedding_multilingual = model_multilingual.encode(job_text, show_progress_bar=False)
        similarity_multilingual = calculate_similarity(cv_embedding_multilingual, job_embedding_multilingual)

        print(f"English Model:      {format_percentage(similarity_english)} similarity")
        print(f"Multilingual Model: {format_percentage(similarity_multilingual)} similarity")

        if similarity_english > similarity_multilingual:
            diff = similarity_english - similarity_multilingual
            print(f"Difference:         English model {format_percentage(diff)} better")
        else:
            diff = similarity_multilingual - similarity_english
            print(f"Difference:         Multilingual model {format_percentage(diff)} better")

        results_english.append({
            'job': job['title'],
            'english': similarity_english,
            'multilingual': similarity_multilingual
        })

    # ========================================================================
    # PERFORMANCE SUMMARY
    # ========================================================================

    print("\n" + "="*80)
    print("PERFORMANCE COMPARISON")
    print("="*80 + "\n")

    print(f"Model Loading Time:")
    print(f"  English Model:      {time_english_load:.2f}s")
    print(f"  Multilingual Model: {time_multilingual_load:.2f}s")

    print(f"\nCV Encoding Time:")
    print(f"  English Model:      {time_cv_english*1000:.0f}ms")
    print(f"  Multilingual Model: {time_cv_multilingual*1000:.0f}ms")
    print(f"  Slowdown:           {((time_cv_multilingual/time_cv_english - 1) * 100):.0f}%")

    print(f"\nModel Size:")
    print(f"  English Model:      ~80 MB")
    print(f"  Multilingual Model: ~420 MB (5.2x larger)")

    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================

    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80 + "\n")

    # German jobs analysis
    german_english_avg = np.mean([r['english'] for r in results_german])
    german_multilingual_avg = np.mean([r['multilingual'] for r in results_german])

    german_english_passed = sum(1 for r in results_german if r['english'] >= 0.30)
    german_multilingual_passed = sum(1 for r in results_german if r['multilingual'] >= 0.30)

    print("📊 GERMAN JOBS (English CV → German job postings):")
    print(f"   English Model avg:      {format_percentage(german_english_avg)}")
    print(f"   Multilingual Model avg: {format_percentage(german_multilingual_avg)}")
    print(f"   Improvement:            +{((german_multilingual_avg/german_english_avg - 1) * 100):.0f}%")
    print(f"\n   Jobs passing 30% threshold:")
    print(f"   English Model:      {german_english_passed}/{len(GERMAN_JOBS)} jobs ({german_english_passed/len(GERMAN_JOBS)*100:.0f}%)")
    print(f"   Multilingual Model: {german_multilingual_passed}/{len(GERMAN_JOBS)} jobs ({german_multilingual_passed/len(GERMAN_JOBS)*100:.0f}%)")

    # English jobs analysis
    english_english_avg = np.mean([r['english'] for r in results_english])
    english_multilingual_avg = np.mean([r['multilingual'] for r in results_english])

    print(f"\n📊 ENGLISH JOBS (English CV → English job postings):")
    print(f"   English Model avg:      {format_percentage(english_english_avg)}")
    print(f"   Multilingual Model avg: {format_percentage(english_multilingual_avg)}")

    if english_english_avg > english_multilingual_avg:
        diff_pct = ((english_english_avg - english_multilingual_avg) / english_english_avg * 100)
        print(f"   Quality loss:           -{diff_pct:.1f}% (acceptable)")
    else:
        print(f"   Quality:                Equal or better")

    # ========================================================================
    # RECOMMENDATION
    # ========================================================================

    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80 + "\n")

    if german_multilingual_passed > german_english_passed:
        print("✅ STRONG RECOMMENDATION: Switch to Multilingual Model")
        print("\n   Reasons:")
        print(f"   1. {german_multilingual_passed - german_english_passed} more German jobs matched")
        print(f"   2. {((german_multilingual_avg/german_english_avg - 1) * 100):.0f}% better similarity for German jobs")
        print(f"   3. Minimal quality loss for English jobs ({abs(english_english_avg - english_multilingual_avg)*100:.1f}%)")
        print(f"   4. Performance penalty acceptable (~{((time_cv_multilingual/time_cv_english - 1) * 100):.0f}% slower)")

        if german_multilingual_passed == len(GERMAN_JOBS) and german_english_passed < len(GERMAN_JOBS):
            print(f"\n   🎯 CRITICAL: English model MISSES relevant German jobs!")
            print(f"      This is a {((len(GERMAN_JOBS) - german_english_passed) / len(GERMAN_JOBS) * 100):.0f}% job loss rate!")
    else:
        print("ℹ️  Both models perform similarly")
        print("   Consider sticking with English model if most jobs are in English")

    print("\n" + "="*80)
    print("\nTest complete! Review the results above to make your decision.")
    print("\nTo implement the change:")
    print("  Edit: scripts/filter_jobs.py, line 39")
    print("  Change: 'all-MiniLM-L6-v2' → 'paraphrase-multilingual-MiniLM-L12-v2'")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
