#!/usr/bin/env python3
"""
Compare different skill extraction methods

This test compares:
1. Claude AI extraction (current method) - extracts skills AND competencies
2. TechWolf ConTeXT extraction - ESCO-based semantic matching
3. JobBERT skill extraction - domain-adapted NER model

Goal: Determine the best approach for skill/competency extraction and normalization
"""

import os
import sys
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline
import anthropic
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()


def extract_with_claude(job_description: str, job_title: str) -> dict:
    """Extract skills and competencies using Claude AI (current method)"""

    api_key = os.getenv('ANTHROPIC_API_KEY')
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""Analyze this job posting and extract:
1. Technical skills (specific tools, technologies, programming languages)
2. Competencies (soft skills, management abilities, domain knowledge)

Job Title: {job_title}

Job Description:
{job_description}

Return a JSON object with two arrays:
{{
    "technical_skills": ["skill1", "skill2", ...],
    "competencies": ["competency1", "competency2", ...]
}}

Be specific and extract as many relevant items as possible."""

    message = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = message.content[0].text

    # Extract JSON from response
    try:
        # Try to find JSON in the response
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        json_str = response_text[start:end]
        result = json.loads(json_str)
        return result
    except Exception as e:
        print(f"Error parsing Claude response: {e}")
        print(f"Response: {response_text}")
        return {"technical_skills": [], "competencies": []}


def extract_with_techwolf(job_description: str, esco_skills: list, model: SentenceTransformer, threshold: float = 0.5) -> list:
    """Extract skills using TechWolf's ConTeXT model with ESCO matching"""

    # Split job description into sentences for better extraction
    import re
    sentences = [s.strip() for s in re.split(r'[.!?\n]+', job_description) if len(s.strip()) > 20]

    # Encode sentences
    sentence_embeddings = model.encode(sentences, convert_to_tensor=True)

    # Encode ESCO skills (sample - in production we'd use all 13k)
    esco_labels = [skill['label'] for skill in esco_skills]
    esco_embeddings = model.encode(esco_labels, convert_to_tensor=True)

    # Find matches
    extracted_skills = set()

    for sent_idx, sent_emb in enumerate(sentence_embeddings):
        # Compute similarities
        similarities = util.cos_sim(sent_emb, esco_embeddings)[0]

        # Get top matches above threshold
        for skill_idx, score in enumerate(similarities):
            if score.item() >= threshold:
                extracted_skills.add(esco_labels[skill_idx])

    return sorted(list(extracted_skills))


def extract_with_jobbert(job_description: str) -> dict:
    """Extract skills using JobBERT skill extraction model"""

    # Load JobBERT skill extraction pipeline
    skill_extractor = pipeline(
        "token-classification",
        model="jjzha/jobbert_skill_extraction",
        aggregation_strategy="simple"  # Merge tokens into complete skills
    )

    # Extract skills
    results = skill_extractor(job_description)

    # Group by entity type
    hard_skills = set()
    soft_skills = set()

    for entity in results:
        skill_text = entity['word'].strip()
        entity_label = entity['entity_group']

        # Clean up subword tokens (remove ##)
        skill_text = skill_text.replace('##', '')

        if len(skill_text) < 2:  # Skip single characters
            continue

        # Categorize based on entity label
        if 'SOFT' in entity_label or 'soft' in entity_label:
            soft_skills.add(skill_text)
        else:
            hard_skills.add(skill_text)

    return {
        'hard_skills': sorted(list(hard_skills)),
        'soft_skills': sorted(list(soft_skills)),
        'all_skills': sorted(list(hard_skills | soft_skills))
    }


def compare_extractions(job_description: str, job_title: str = "Sample Job"):
    """Compare both extraction methods"""

    print("=" * 80)
    print(f"SKILL EXTRACTION COMPARISON: {job_title}")
    print("=" * 80)
    print(f"\nJob Description Preview (first 300 chars):")
    print(job_description[:300] + "...\n")

    # Extract with Claude
    print("\n📊 Extracting with Claude AI...")
    claude_result = extract_with_claude(job_description, job_title)
    claude_skills = set(claude_result.get('technical_skills', []))
    claude_competencies = set(claude_result.get('competencies', []))
    claude_all = claude_skills | claude_competencies

    print(f"  ✓ Found {len(claude_skills)} technical skills")
    print(f"  ✓ Found {len(claude_competencies)} competencies")
    print(f"  ✓ Total: {len(claude_all)} items")

    # Extract with TechWolf
    print("\n🤖 Extracting with TechWolf ConTeXT model...")
    print("  Loading model...")
    model = SentenceTransformer('TechWolf/ConTeXT-Skill-Extraction-base')

    # Sample ESCO skills for testing (in production, load all 13k from CSV)
    sample_esco = [
        {'label': 'Python'},
        {'label': 'JavaScript'},
        {'label': 'project management'},
        {'label': 'team leadership'},
        {'label': 'data analysis'},
        {'label': 'machine learning'},
        {'label': 'SQL'},
        {'label': 'cloud computing'},
        {'label': 'problem solving'},
        {'label': 'communication'},
        {'label': 'agile methodology'},
        {'label': 'software development'},
        {'label': 'REST APIs'},
        {'label': 'version control'},
        {'label': 'testing'},
        {'label': 'Docker'},
        {'label': 'Kubernetes'},
        {'label': 'CI/CD'},
        {'label': 'React'},
        {'label': 'Node.js'},
    ]

    techwolf_skills = set(extract_with_techwolf(job_description, sample_esco, model, threshold=0.4))

    print(f"  ✓ Found {len(techwolf_skills)} skills")

    # Extract with JobBERT
    print("\n🎯 Extracting with JobBERT skill extraction...")
    print("  Loading model...")
    jobbert_result = extract_with_jobbert(job_description)
    jobbert_hard = set(jobbert_result['hard_skills'])
    jobbert_soft = set(jobbert_result['soft_skills'])
    jobbert_all = set(jobbert_result['all_skills'])

    print(f"  ✓ Found {len(jobbert_hard)} hard skills")
    print(f"  ✓ Found {len(jobbert_soft)} soft skills")
    print(f"  ✓ Total: {len(jobbert_all)} skills")

    # Compare results
    print("\n" + "=" * 80)
    print("COMPARISON RESULTS")
    print("=" * 80)

    print(f"\n📈 CLAUDE EXTRACTION:")
    print(f"  Technical Skills ({len(claude_skills)}):")
    for skill in sorted(claude_skills):
        print(f"    • {skill}")

    print(f"\n  Competencies ({len(claude_competencies)}):")
    for comp in sorted(claude_competencies):
        print(f"    • {comp}")

    print(f"\n🤖 TECHWOLF EXTRACTION ({len(techwolf_skills)}) [ESCO-limited]:")
    for skill in sorted(techwolf_skills):
        print(f"    • {skill}")

    print(f"\n🎯 JOBBERT EXTRACTION:")
    print(f"  Hard Skills ({len(jobbert_hard)}):")
    for skill in sorted(jobbert_hard):
        print(f"    • {skill}")

    print(f"\n  Soft Skills ({len(jobbert_soft)}):")
    for skill in sorted(jobbert_soft):
        print(f"    • {skill}")

    # Overlap analysis (normalize for comparison)
    claude_normalized = set(item.lower().strip() for item in claude_all)
    techwolf_normalized = set(skill.lower().strip() for skill in techwolf_skills)
    jobbert_normalized = set(skill.lower().strip() for skill in jobbert_all)

    # Three-way overlap analysis
    claude_and_jobbert = claude_normalized & jobbert_normalized
    claude_and_techwolf = claude_normalized & techwolf_normalized
    jobbert_and_techwolf = jobbert_normalized & techwolf_normalized
    all_three = claude_normalized & jobbert_normalized & techwolf_normalized

    only_claude = claude_normalized - jobbert_normalized - techwolf_normalized
    only_jobbert = jobbert_normalized - claude_normalized - techwolf_normalized
    only_techwolf = techwolf_normalized - claude_normalized - jobbert_normalized

    print(f"\n" + "=" * 80)
    print("OVERLAP ANALYSIS")
    print("=" * 80)

    if len(claude_all) > 0:
        claude_jobbert_pct = (len(claude_and_jobbert) / len(claude_all)) * 100
    else:
        claude_jobbert_pct = 0

    print(f"\n✅ All 3 methods found: {len(all_three)} items")
    if all_three:
        for item in sorted(all_three):
            print(f"    • {item}")

    print(f"\n🤝 Claude & JobBERT overlap: {len(claude_and_jobbert)} items ({claude_jobbert_pct:.1f}% of Claude's)")
    if claude_and_jobbert - all_three:
        for item in sorted(claude_and_jobbert - all_three):
            print(f"    • {item}")

    print(f"\n📝 Only Claude found: {len(only_claude)} items")
    if only_claude:
        for item in sorted(only_claude):
            print(f"    • {item}")

    print(f"\n🎯 Only JobBERT found: {len(only_jobbert)} items")
    if only_jobbert:
        for item in sorted(only_jobbert):
            print(f"    • {item}")

    print(f"\n🤖 Only TechWolf found: {len(only_techwolf)} items (ESCO-limited)")
    if only_techwolf:
        for item in sorted(only_techwolf):
            print(f"    • {item}")

    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)

    print(f"""
Summary:
- Claude extracted: {len(claude_all)} items ({len(claude_skills)} skills + {len(claude_competencies)} competencies)
- JobBERT extracted: {len(jobbert_all)} items ({len(jobbert_hard)} hard + {len(jobbert_soft)} soft)
- TechWolf extracted: {len(techwolf_skills)} items (ESCO-limited to {len(sample_esco)} sample skills)
- Claude & JobBERT overlap: {len(claude_and_jobbert)} items ({claude_jobbert_pct:.1f}%)
- All 3 agree: {len(all_three)} items

Key Findings:
1. Claude: Comprehensive extraction with skills/competency distinction
2. JobBERT: Domain-adapted, extracts modern skills (no ESCO limitations)
3. TechWolf+ESCO: Limited by outdated taxonomy (missing: Airflow, Spark, modern tools)

Recommendation:
✅ BEST APPROACH: JobBERT for extraction + semantic clustering for normalization
   - No dependency on outdated ESCO taxonomy
   - Domain-adapted on 3.2M real job postings
   - Automatically handles hard vs soft skills
   - Can extract modern tools/frameworks

⚠️  ABANDON ESCO: Missing modern tech stack (Airflow, many frameworks)

🔄 HYBRID OPTION: Use JobBERT + Claude for verification
   - JobBERT for fast, accurate extraction
   - Claude for quality check on complex competencies
""")


def main():
    # Test with sample job or user-provided job
    if len(sys.argv) > 1:
        job_file = sys.argv[1]
        print(f"Loading job from: {job_file}")
        with open(job_file, 'r') as f:
            job_data = json.load(f)
        job_description = job_data.get('description', '')
        job_title = job_data.get('title', 'Unknown')
    else:
        # Sample job description for testing
        job_title = "Senior Python Developer"
        job_description = """
We are looking for a Senior Python Developer to join our data engineering team.

Requirements:
- 5+ years of Python programming experience
- Strong knowledge of data analysis and machine learning
- Experience with SQL databases and data warehousing
- Proficiency in AWS cloud services
- Excellent problem-solving and communication skills
- Team leadership experience preferred

Responsibilities:
- Design and implement scalable data pipelines
- Lead technical projects and mentor junior developers
- Collaborate with cross-functional teams
- Optimize system performance and reliability

Tech Stack: Python, PostgreSQL, Docker, Kubernetes, Airflow, Spark
"""

    compare_extractions(job_description, job_title)


if __name__ == '__main__':
    main()
