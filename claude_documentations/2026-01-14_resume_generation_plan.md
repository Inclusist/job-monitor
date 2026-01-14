# Interactive Resume Generation Feature - Implementation Plan

**Date:** January 14, 2026
**Status:** 📋 Planning Phase
**Feature Type:** New Feature
**Estimated Effort:** ~20 hours

---

## Overview

Implementation of an interactive resume generation feature that allows users to:
1. Select missing competencies/skills from job requirements
2. Provide evidence for their claimed abilities
3. Generate tailored, ATS-optimized resumes using Claude AI
4. Download resumes in PDF and HTML formats

This feature bridges the gap between job requirements and user capabilities by letting users proactively demonstrate skills that weren't detected in their original CV parsing.

---

## User Problem Statement

**Current State:**
- Users see job matches with competency/skills alignments
- Missing competencies/skills are shown in gray (non-interactive)
- No way to claim abilities that weren't auto-detected from CV
- No tailored resume generation based on job requirements

**Pain Points:**
1. Users know they have certain skills but they weren't detected in CV parsing
2. Need to manually create tailored resumes for each application
3. Difficult to know which experiences to emphasize for specific jobs
4. No structured way to connect job requirements to their experiences

**Desired State:**
- Interactive UI where users can claim missing competencies/skills
- Structured evidence collection for each claim
- AI-generated tailored resumes that incorporate both detected and claimed abilities
- Professional, downloadable resumes optimized for each job

---

## Feature Workflow

### Step 1: Interactive Selection (Job Detail Page)

**Current Display:**
- Green boxes = Matched competencies/skills
- Gray boxes = Missing competencies/skills (not clickable)

**New Behavior:**
```
┌─────────────────────────────────────────────────┐
│ Competency Alignment                            │
├─────────────────────────────────────────────────┤
│ [✓ Project Management    ] ← Green (matched)   │
│ [  Agile Methodology     ] ← Gray (clickable)   │
│ [  Stakeholder Management] ← Gray (clickable)   │
│                                                 │
│ After user clicks:                              │
│ [✓ Agile Methodology ✓ User Selected]          │
│                       ↑ Light green background  │
└─────────────────────────────────────────────────┘
```

**User Actions:**
- Click gray box → turns light green + "✓ User Selected" badge
- Click again → deselects (back to gray)
- "Generate Resume" button shows count: "Generate Resume (3 additions)"

### Step 2: Evidence Collection Modal

**Triggered when:** User clicks "Generate Resume" with selections

**Multi-page flow:**
```
┌──────────────────────────────────────────────────┐
│ Provide Evidence: "Agile Methodology"           │
│ Step 1 of 3                                      │
├──────────────────────────────────────────────────┤
│                                                  │
│ Which roles demonstrated this?                   │
│ [x] Senior Software Engineer - Acme Corp         │
│     (2020-2023)                                  │
│ [ ] Software Developer - TechStart Inc           │
│     (2018-2020)                                  │
│ [x] Freelance Developer - Self-employed          │
│     (2017-2018)                                  │
│                                                  │
│ Describe how you demonstrated this:              │
│ ┌──────────────────────────────────────────────┐ │
│ │ Led daily standups, sprint planning, and    │ │
│ │ retrospectives for 5-person team. Managed   │ │
│ │ product backlog and coordinated with PO.    │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│          [Skip]        [Save & Continue]         │
└──────────────────────────────────────────────────┘
```

**Validation:**
- At least one work experience must be selected
- Evidence description required (minimum 20 characters)
- User can skip any item (removes it from generation)

### Step 3: Resume Generation

**Claude processes:**
- User's complete CV profile
- Job description and requirements
- Existing matched competencies/skills
- Newly claimed competencies/skills with evidence
- Selected work experiences

**Claude generates:**
- Professional HTML resume
- Optimized section ordering (most relevant first)
- Integrated evidence as professional bullet points
- Keyword-optimized for ATS systems
- Emphasis on matched requirements

### Step 4: Preview & Download

**Resume preview modal:**
```
┌────────────────────────────────────────────────┐
│ Your Tailored Resume                           │
│                                                │
│ ┌────────────────────────────────────────────┐ │
│ │  [Rendered professional resume]            │ │
│ │                                            │ │
│ │  John Doe                                  │ │
│ │  Senior Software Engineer                  │ │
│ │                                            │ │
│ │  EXPERIENCE                                │ │
│ │  • Led agile sprint planning... [NEW]     │ │
│ │  • Built scalable APIs...                 │ │
│ └────────────────────────────────────────────┘ │
│                                                │
│  [Download PDF] [Download HTML] [Close]        │
└────────────────────────────────────────────────┘
```

**Download options:**
- PDF (WeasyPrint) - production-ready
- HTML - editable by user

---

## Technical Architecture

### 1. Database Schema Changes

#### New Columns in `cv_profiles` Table

```sql
ALTER TABLE cv_profiles
ADD COLUMN user_claimed_competencies JSONB DEFAULT '{}',
ADD COLUMN user_claimed_skills JSONB DEFAULT '{}';
```

**Data Structure:**
```json
{
  "Agile Methodology": {
    "work_experience_ids": [1, 3],
    "evidence": "Led daily standups and sprint planning for 5-person team. Managed product backlog and coordinated with PO.",
    "added_at": "2026-01-14T10:30:00Z"
  },
  "Machine Learning": {
    "work_experience_ids": [2],
    "evidence": "Built and deployed ML models for customer segmentation using scikit-learn and TensorFlow.",
    "added_at": "2026-01-14T11:00:00Z"
  }
}
```

**Why JSONB?**
- Flexible structure (easy to add fields later)
- Efficient querying (can query specific competencies)
- Indexed for performance
- Native PostgreSQL support

#### New Table: `user_generated_resumes`

```sql
CREATE TABLE user_generated_resumes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    resume_html TEXT NOT NULL,
    resume_pdf_path TEXT,
    selections_used JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_user_job_resume UNIQUE(user_id, job_id)
);

CREATE INDEX idx_user_resumes ON user_generated_resumes(user_id, job_id);
CREATE INDEX idx_resume_created ON user_generated_resumes(created_at DESC);
```

**Purpose:**
- Store generated resumes for future reference
- Allow users to regenerate or view previous versions
- Track which competencies/skills were included
- Enable analytics on resume generation patterns

### 2. Backend Components

#### A. Database Operations Module

**New file:** `src/database/postgres_resume_operations.py`

```python
class PostgresResumeOperations:
    """Handle resume-related database operations"""

    def __init__(self, connection_pool):
        self.pool = connection_pool

    def save_user_claimed_competencies(self, user_id, competency_name,
                                       work_exp_ids, evidence):
        """Save user's claimed competency with evidence"""
        # Updates cv_profiles.user_claimed_competencies JSONB
        pass

    def save_user_claimed_skills(self, user_id, skill_name,
                                 work_exp_ids, evidence):
        """Save user's claimed skill with evidence"""
        # Updates cv_profiles.user_claimed_skills JSONB
        pass

    def get_user_claimed_data(self, user_id):
        """Get all user's claimed competencies and skills"""
        # Returns: {
        #   'competencies': {...},
        #   'skills': {...}
        # }
        pass

    def save_generated_resume(self, user_id, job_id, html,
                             pdf_path, selections):
        """Save generated resume to database"""
        # Upsert to user_generated_resumes table
        pass

    def get_user_resumes(self, user_id, job_id=None):
        """Get user's generated resumes"""
        # If job_id provided, get specific resume
        # Otherwise get all user's resumes
        pass

    def delete_resume(self, resume_id, user_id):
        """Delete a generated resume"""
        pass
```

**Key Implementation Notes:**
- Use JSONB update operations for atomic updates
- Handle merge logic (don't overwrite existing claims)
- Include timestamp tracking
- Proper error handling for constraint violations

#### B. Resume Generator Module

**New file:** `src/resume/resume_generator.py`

```python
from anthropic import Anthropic
from weasyprint import HTML
import os

class ResumeGenerator:
    """Generate tailored resumes using Claude AI"""

    def __init__(self, anthropic_api_key):
        self.client = Anthropic(api_key=anthropic_api_key)
        self.model = "claude-3-5-sonnet-20241022"

    def generate_resume_html(self, user_profile, job, claimed_data):
        """
        Generate tailored resume HTML using Claude

        Args:
            user_profile: User's CV profile dict
            job: Job details dict
            claimed_data: {
                'competencies': {...},
                'skills': {...}
            }

        Returns:
            str: Professional HTML resume
        """
        prompt = self._build_prompt(user_profile, job, claimed_data)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def html_to_pdf(self, html_content, output_path):
        """
        Convert HTML to PDF using WeasyPrint

        Args:
            html_content: HTML string
            output_path: Where to save PDF
        """
        HTML(string=html_content).write_pdf(output_path)

    def _build_prompt(self, user_profile, job, claimed_data):
        """Build comprehensive Claude prompt"""

        # Format claimed evidence
        claimed_section = self._format_claimed_evidence(claimed_data)

        prompt = f"""You are a professional resume writer. Generate a tailored, ATS-optimized resume.

USER'S PROFILE:
- Name: {user_profile.get('name', 'Professional')}
- Email: {user_profile.get('email')}
- Phone: {user_profile.get('phone')}
- Target Role: {user_profile.get('extracted_role')}
- Seniority: {user_profile.get('derived_seniority')}

WORK EXPERIENCE:
{self._format_work_experience(user_profile.get('work_experience', []))}

EDUCATION:
{self._format_education(user_profile.get('education', []))}

TECHNICAL SKILLS:
{', '.join(user_profile.get('technical_skills', []))}

COMPETENCIES (Auto-detected):
{', '.join(user_profile.get('competencies', []))}

{claimed_section}

JOB DETAILS:
- Title: {job['title']}
- Company: {job['company']}
- Location: {job.get('location', 'Not specified')}

JOB DESCRIPTION:
{job.get('description', '')}

REQUIRED COMPETENCIES:
{', '.join(job.get('ai_competencies', []))}

REQUIRED SKILLS:
{', '.join(job.get('ai_key_skills', []))}

TASK:
Generate a professional, ATS-optimized resume tailored for this specific job.

REQUIREMENTS:
1. **Integrate User-Claimed Competencies**: For each user-claimed competency/skill, incorporate their evidence as professional resume bullet points in the relevant work experience section. Rewrite their evidence to be concise, achievement-focused, and keyword-rich.

2. **Optimize for Job Requirements**: Ensure all matched and user-claimed competencies/skills are prominently featured. Use exact keywords from job requirements where appropriate.

3. **Professional Structure**:
   - Contact information header
   - Professional summary (2-3 sentences highlighting key strengths aligned with job)
   - Work experience (most recent first, emphasize relevant roles)
   - Education
   - Skills section (technical skills, competencies)
   - Optional: Certifications, Languages if relevant

4. **Experience Bullets**:
   - Start with strong action verbs
   - Quantify achievements where possible
   - Highlight impact and results
   - 3-5 bullets per role, most relevant roles get more detail
   - Mark newly added bullets with [NEW] suffix

5. **ATS Optimization**:
   - Use standard section headers
   - Include keywords naturally
   - Clean, parseable formatting
   - No tables, columns, or graphics

6. **Formatting**:
   - Use semantic HTML: <h1> for name, <h2> for sections, <ul> for bullets
   - Professional, modern CSS styling (embedded in <style> tag)
   - Clean, readable font (Arial, Helvetica, or similar)
   - Appropriate spacing and margins
   - Print-friendly (fits on 1-2 pages when converted to PDF)

OUTPUT:
Return ONLY the complete HTML document (including <!DOCTYPE html>, <html>, <head>, <style>, <body> tags). Do not include any markdown formatting or code fences.
"""
        return prompt

    def _format_claimed_evidence(self, claimed_data):
        """Format user-claimed competencies/skills for prompt"""
        if not claimed_data:
            return ""

        sections = []

        if claimed_data.get('competencies'):
            comp_list = []
            for name, details in claimed_data['competencies'].items():
                comp_list.append(
                    f"- {name}: {details['evidence']} "
                    f"(shown in work experience IDs: {details['work_experience_ids']})"
                )
            sections.append("USER-CLAIMED COMPETENCIES (with evidence):\n" +
                          "\n".join(comp_list))

        if claimed_data.get('skills'):
            skill_list = []
            for name, details in claimed_data['skills'].items():
                skill_list.append(
                    f"- {name}: {details['evidence']} "
                    f"(shown in work experience IDs: {details['work_experience_ids']})"
                )
            sections.append("USER-CLAIMED SKILLS (with evidence):\n" +
                          "\n".join(skill_list))

        return "\n\n".join(sections)

    def _format_work_experience(self, experiences):
        """Format work experience for prompt"""
        if not experiences:
            return "No work experience recorded"

        formatted = []
        for i, exp in enumerate(experiences, 1):
            formatted.append(
                f"{i}. {exp.get('title', 'Position')} at {exp.get('company', 'Company')} "
                f"({exp.get('start_date', '')} - {exp.get('end_date', 'Present')})\n"
                f"   {exp.get('description', '')}"
            )
        return "\n\n".join(formatted)

    def _format_education(self, education_list):
        """Format education for prompt"""
        if not education_list:
            return "No education recorded"

        formatted = []
        for edu in education_list:
            formatted.append(
                f"- {edu.get('degree', 'Degree')} in {edu.get('field', 'Field')} "
                f"from {edu.get('institution', 'Institution')} "
                f"({edu.get('graduation_year', '')})"
            )
        return "\n".join(formatted)
```

**Cost Estimation:**
- Input: ~2,000 tokens (profile + job + evidence)
- Output: ~2,000 tokens (full resume)
- Total: ~4,000 tokens per generation
- Cost: ~$0.12 per resume (Claude 3.5 Sonnet pricing)

**WeasyPrint Choice:**
- Pure Python (no external dependencies)
- Excellent CSS3 support (Flexbox, Grid)
- Actively maintained
- Professional PDF output quality
- Easy to install: `pip install weasyprint`

### 3. API Endpoints

**Location:** `app.py`

#### A. Save Competency Evidence

```python
@app.route('/api/save-competency-evidence', methods=['POST'])
@login_required
def save_competency_evidence():
    """
    Save user's claimed competencies/skills with evidence

    Request Body:
    {
        "selections": [
            {
                "name": "Agile Methodology",
                "type": "competency",
                "work_experience_ids": [1, 3],
                "evidence": "Led daily standups..."
            },
            {
                "name": "Python",
                "type": "skill",
                "work_experience_ids": [2],
                "evidence": "Built data pipeline..."
            }
        ]
    }

    Returns:
    {
        "success": true,
        "message": "Evidence saved for 2 items"
    }
    """
    user_id = get_user_id()
    data = request.json

    try:
        selections = data.get('selections', [])

        for item in selections:
            if item['type'] == 'competency':
                resume_ops.save_user_claimed_competencies(
                    user_id,
                    item['name'],
                    item['work_experience_ids'],
                    item['evidence']
                )
            else:  # skill
                resume_ops.save_user_claimed_skills(
                    user_id,
                    item['name'],
                    item['work_experience_ids'],
                    item['evidence']
                )

        return jsonify({
            'success': True,
            'message': f'Evidence saved for {len(selections)} items'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

#### B. Generate Resume

```python
@app.route('/api/generate-resume/<int:job_id>', methods=['POST'])
@login_required
def generate_resume(job_id):
    """
    Generate tailored resume for a specific job

    Returns:
    {
        "success": true,
        "resume_id": 123,
        "resume_html": "<html>...</html>",
        "pdf_url": "/download/resume/123"
    }
    """
    user_id = get_user_id()

    try:
        # Get user profile
        profile = cv_manager.get_primary_profile(user_id)
        if not profile:
            return jsonify({
                'success': False,
                'error': 'No CV profile found'
            }), 400

        # Get job details
        job = job_db.get_job_by_id(job_id)
        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404

        # Get user's claimed competencies/skills
        claimed_data = resume_ops.get_user_claimed_data(user_id)

        # Generate resume HTML
        generator = ResumeGenerator(os.getenv('ANTHROPIC_API_KEY'))
        resume_html = generator.generate_resume_html(
            profile,
            job,
            claimed_data
        )

        # Save to PDF
        pdf_filename = f"resume_{user_id}_{job_id}_{int(time.time())}.pdf"
        pdf_path = os.path.join('static', 'resumes', pdf_filename)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        generator.html_to_pdf(resume_html, pdf_path)

        # Save to database
        resume_id = resume_ops.save_generated_resume(
            user_id,
            job_id,
            resume_html,
            pdf_path,
            claimed_data
        )

        return jsonify({
            'success': True,
            'resume_id': resume_id,
            'resume_html': resume_html,
            'pdf_url': f'/download/resume/{resume_id}'
        })

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

#### C. Download Resume

```python
@app.route('/download/resume/<int:resume_id>')
@login_required
def download_resume(resume_id):
    """
    Download generated resume PDF

    Security: Verify user owns this resume
    """
    user_id = get_user_id()

    try:
        resume = resume_ops.get_user_resumes(user_id)
        resume = [r for r in resume if r['id'] == resume_id]

        if not resume:
            flash('Resume not found', 'error')
            return redirect(url_for('jobs'))

        resume = resume[0]
        pdf_path = resume['resume_pdf_path']

        if not os.path.exists(pdf_path):
            flash('Resume file not found', 'error')
            return redirect(url_for('jobs'))

        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"resume_{resume['job_id']}.pdf"
        )

    except Exception as e:
        flash(f'Error downloading resume: {str(e)}', 'error')
        return redirect(url_for('jobs'))
```

### 4. Frontend Implementation

#### A. Job Detail Page Updates (jobs.html)

**JavaScript State Management:**

```javascript
// Track user selections
const selectedItems = {
    competencies: new Set(),
    skills: new Set()
};

// Track evidence for each selected item
const evidenceData = new Map();

function toggleSelection(type, name, element) {
    if (selectedItems[type].has(name)) {
        // Deselect
        selectedItems[type].delete(name);
        evidenceData.delete(`${type}:${name}`);
        element.classList.remove('user-selected');
        element.querySelector('.user-selected-badge').style.display = 'none';
    } else {
        // Select
        selectedItems[type].add(name);
        element.classList.add('user-selected');
        element.querySelector('.user-selected-badge').style.display = 'inline';
    }

    updateGenerateButton();
}

function updateGenerateButton() {
    const totalSelected =
        selectedItems.competencies.size +
        selectedItems.skills.size;

    const btn = document.getElementById('generateResumeBtn');
    const countSpan = document.getElementById('additionCount');

    if (totalSelected > 0) {
        btn.disabled = false;
        countSpan.textContent = ` (${totalSelected} additions)`;
        countSpan.style.display = 'inline';
    } else {
        btn.disabled = true;
        countSpan.style.display = 'none';
    }
}

function openEvidenceModal() {
    // Collect all selected items
    const allSelections = [
        ...Array.from(selectedItems.competencies).map(name => ({
            name, type: 'competency'
        })),
        ...Array.from(selectedItems.skills).map(name => ({
            name, type: 'skill'
        }))
    ];

    if (allSelections.length === 0) {
        alert('Please select at least one competency or skill');
        return;
    }

    // Start evidence collection flow
    showEvidenceModal(allSelections, 0);
}
```

**HTML Changes:**

```html
<!-- Update competency/skill boxes to be clickable -->
{% for competency in job.ai_competencies %}
    {% set matched = competency in competency_mappings|map(attribute='job_requirement')|list %}
    <div class="competency-box
                {% if matched %}matched{% else %}missing clickable{% endif %}"
         {% if not matched %}
         onclick="toggleSelection('competencies', '{{ competency }}', this)"
         {% endif %}>
        {{ competency }}
        {% if not matched %}
        <span class="user-selected-badge" style="display:none;">
            ✓ User Selected
        </span>
        {% endif %}
    </div>
{% endfor %}

<!-- Add Generate Resume button -->
<div style="margin-top: 2rem;">
    <button id="generateResumeBtn"
            class="btn btn-primary"
            onclick="openEvidenceModal()"
            disabled>
        📄 Generate Tailored Resume
        <span id="additionCount" style="display:none;"></span>
    </button>
</div>
```

**CSS Additions:**

```css
.competency-box.clickable {
    cursor: pointer;
    transition: all 0.2s ease;
}

.competency-box.clickable:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.competency-box.user-selected {
    background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
    border-color: #28a745;
}

.user-selected-badge {
    font-size: 0.75rem;
    color: #28a745;
    font-weight: 600;
    margin-left: 0.5rem;
}
```

#### B. Evidence Collection Modal

**HTML Structure:**

```html
<!-- Evidence Collection Modal -->
<div id="evidenceModal" class="modal" style="display:none;">
    <div class="modal-overlay" onclick="closeEvidenceModal()"></div>
    <div class="modal-content" style="max-width: 600px;">
        <div class="modal-header">
            <h3>Provide Evidence: <span id="currentItemName"></span></h3>
            <button class="close-btn" onclick="closeEvidenceModal()">×</button>
        </div>

        <div class="progress-indicator">
            Step <span id="currentStep">1</span> of <span id="totalSteps">5</span>
        </div>

        <form id="evidenceForm" onsubmit="saveEvidence(event)">
            <div class="form-group">
                <label class="form-label">
                    Which roles demonstrated this? (Select all that apply)
                </label>
                <div id="workExperienceCheckboxes" class="checkbox-group">
                    <!-- Dynamically populated -->
                </div>
                <div id="experienceError" class="error-message" style="display:none;">
                    Please select at least one role
                </div>
            </div>

            <div class="form-group">
                <label class="form-label">
                    Describe how you demonstrated this:
                    <span class="hint">Be specific. Include tools, metrics, or impact if possible.</span>
                </label>
                <textarea
                    id="evidenceText"
                    class="form-control"
                    rows="4"
                    placeholder="Example: Led sprint planning and retrospectives for 5-person agile team. Managed backlog prioritization using Jira, resulting in 30% faster delivery cycles."
                    required
                    minlength="20"></textarea>
                <div class="char-count">
                    <span id="charCount">0</span> / 500 characters
                </div>
            </div>

            <div class="modal-footer">
                <button type="button"
                        class="btn btn-secondary"
                        onclick="skipCurrentItem()">
                    Skip This Item
                </button>
                <button type="submit" class="btn btn-primary">
                    Save & Continue
                </button>
            </div>
        </form>
    </div>
</div>
```

**JavaScript Logic:**

```javascript
let currentSelections = [];
let currentIndex = 0;
let collectedEvidence = [];

function showEvidenceModal(selections, startIndex) {
    currentSelections = selections;
    currentIndex = startIndex;

    if (currentIndex >= selections.length) {
        // All done, proceed to generation
        generateResume();
        return;
    }

    const item = selections[currentIndex];

    // Update modal
    document.getElementById('currentItemName').textContent = item.name;
    document.getElementById('currentStep').textContent = currentIndex + 1;
    document.getElementById('totalSteps').textContent = selections.length;

    // Populate work experience checkboxes
    populateWorkExperience();

    // Clear previous input
    document.getElementById('evidenceText').value = '';
    document.getElementById('charCount').textContent = '0';

    // Show modal
    document.getElementById('evidenceModal').style.display = 'flex';
}

function populateWorkExperience() {
    // Fetch user's work experience from profile
    // For now, use global variable or make API call
    const workExperiences = userWorkExperience; // Set on page load

    const container = document.getElementById('workExperienceCheckboxes');
    container.innerHTML = '';

    workExperiences.forEach((exp, index) => {
        const checkbox = document.createElement('div');
        checkbox.className = 'checkbox-item';
        checkbox.innerHTML = `
            <label>
                <input type="checkbox"
                       name="work_exp"
                       value="${exp.id || index}">
                <span class="checkbox-label">
                    <strong>${exp.title}</strong> at ${exp.company}
                    <br>
                    <small>${exp.start_date} - ${exp.end_date || 'Present'}</small>
                </span>
            </label>
        `;
        container.appendChild(checkbox);
    });
}

function saveEvidence(event) {
    event.preventDefault();

    // Validate work experience selection
    const checkboxes = document.querySelectorAll('input[name="work_exp"]:checked');
    if (checkboxes.length === 0) {
        document.getElementById('experienceError').style.display = 'block';
        return;
    }
    document.getElementById('experienceError').style.display = 'none';

    // Get selected work experience IDs
    const workExpIds = Array.from(checkboxes).map(cb => parseInt(cb.value));

    // Get evidence text
    const evidence = document.getElementById('evidenceText').value.trim();

    // Save to collection
    const item = currentSelections[currentIndex];
    collectedEvidence.push({
        name: item.name,
        type: item.type,
        work_experience_ids: workExpIds,
        evidence: evidence
    });

    // Move to next item
    currentIndex++;
    showEvidenceModal(currentSelections, currentIndex);
}

function skipCurrentItem() {
    // Remove from selected items
    const item = currentSelections[currentIndex];
    selectedItems[item.type].delete(item.name);

    // Move to next
    currentIndex++;
    showEvidenceModal(currentSelections, currentIndex);
}

function closeEvidenceModal() {
    document.getElementById('evidenceModal').style.display = 'none';
    collectedEvidence = [];
    currentSelections = [];
    currentIndex = 0;
}

// Character counter
document.getElementById('evidenceText')?.addEventListener('input', function(e) {
    const count = e.target.value.length;
    document.getElementById('charCount').textContent = count;

    if (count > 500) {
        e.target.value = e.target.value.substring(0, 500);
        document.getElementById('charCount').textContent = '500';
    }
});
```

#### C. Resume Preview Modal

**HTML:**

```html
<!-- Resume Preview Modal -->
<div id="resumePreviewModal" class="modal" style="display:none;">
    <div class="modal-overlay"></div>
    <div class="modal-content large" style="max-width: 900px;">
        <div class="modal-header">
            <h2>Your Tailored Resume</h2>
            <button class="close-btn" onclick="closeResumePreview()">×</button>
        </div>

        <div id="resumeGenerating" class="loading-state">
            <div class="spinner"></div>
            <p>Generating your tailored resume...</p>
            <small>This may take 10-15 seconds</small>
        </div>

        <div id="resumeContent" style="display:none;">
            <div id="resumePreview" class="resume-container">
                <!-- Rendered resume HTML inserted here -->
            </div>

            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="closeResumePreview()">
                    Close
                </button>
                <button class="btn btn-success" onclick="downloadResume('html')">
                    📄 Download HTML
                </button>
                <button class="btn btn-primary" onclick="downloadResume('pdf')">
                    📥 Download PDF
                </button>
            </div>
        </div>
    </div>
</div>
```

**JavaScript:**

```javascript
async function generateResume() {
    // Close evidence modal
    closeEvidenceModal();

    // Show preview modal in loading state
    document.getElementById('resumePreviewModal').style.display = 'flex';
    document.getElementById('resumeGenerating').style.display = 'block';
    document.getElementById('resumeContent').style.display = 'none';

    try {
        // Save evidence first
        await fetch('/api/save-competency-evidence', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                selections: collectedEvidence
            })
        });

        // Generate resume
        const jobId = currentJobId; // Set on page load
        const response = await fetch(`/api/generate-resume/${jobId}`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            // Show resume
            document.getElementById('resumePreview').innerHTML = data.resume_html;
            document.getElementById('resumeGenerating').style.display = 'none';
            document.getElementById('resumeContent').style.display = 'block';

            // Store resume ID for download
            currentResumeId = data.resume_id;
        } else {
            alert('Error generating resume: ' + data.error);
            closeResumePreview();
        }

    } catch (error) {
        alert('Error generating resume: ' + error.message);
        closeResumePreview();
    }
}

function closeResumePreview() {
    document.getElementById('resumePreviewModal').style.display = 'none';
}

function downloadResume(format) {
    if (format === 'pdf') {
        window.location.href = `/download/resume/${currentResumeId}`;
    } else if (format === 'html') {
        const html = document.getElementById('resumePreview').innerHTML;
        const blob = new Blob([html], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `resume_job_${currentJobId}.html`;
        a.click();
        URL.revokeObjectURL(url);
    }
}
```

---

## Integration with Matching System

### Update Matching Logic

**Goal:** Include user-claimed competencies/skills in future job matching

**File:** `src/matching/matcher.py`

**Changes needed:**

```python
def get_user_competencies_for_matching(self, user_id):
    """Get combined competencies for matching"""
    profile = self.cv_manager.get_primary_profile(user_id)

    # Original parsed competencies
    parsed_competencies = profile.get('competencies', [])
    parsed_skills = profile.get('technical_skills', [])

    # User-claimed competencies/skills
    claimed_competencies = profile.get('user_claimed_competencies', {})
    claimed_skills = profile.get('user_claimed_skills', {})

    # Combine
    all_competencies = parsed_competencies + list(claimed_competencies.keys())
    all_skills = parsed_skills + list(claimed_skills.keys())

    return {
        'competencies': {
            'parsed': parsed_competencies,
            'claimed': list(claimed_competencies.keys()),
            'all': all_competencies
        },
        'skills': {
            'parsed': parsed_skills,
            'claimed': list(claimed_skills.keys()),
            'all': all_skills
        }
    }
```

**Display in UI:**

Update competency alignment display to show source:

```html
<div class="competency-box matched">
    Project Management
    <span class="source-badge">CV</span>
</div>

<div class="competency-box matched user-claimed">
    Agile Methodology
    <span class="source-badge">User Claimed</span>
</div>
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1) - 8 hours

**Tasks:**
1. Database migration script (30 min)
   - Add columns to cv_profiles
   - Create user_generated_resumes table
   - Test migration on staging

2. Backend database operations (2 hours)
   - Implement PostgresResumeOperations class
   - Test JSONB operations
   - Add error handling

3. Resume generator scaffold (1 hour)
   - Create ResumeGenerator class structure
   - Test WeasyPrint installation
   - Create sample HTML template

4. Prompt engineering (3 hours)
   - Draft comprehensive Claude prompt
   - Test with sample data
   - Iterate on output quality
   - Optimize token usage

5. API endpoint stubs (1.5 hours)
   - Create route handlers
   - Add basic validation
   - Test error handling

**Deliverables:**
- ✅ Database schema updated
- ✅ Backend classes implemented
- ✅ Claude prompt finalized
- ✅ API endpoints functional

### Phase 2: Frontend Interactivity (Week 2) - 6 hours

**Tasks:**
1. Make gray boxes clickable (1 hour)
   - Update HTML templates
   - Add click handlers
   - Implement selection state

2. Generate Resume button (30 min)
   - Add button to job detail page
   - Wire up to JavaScript
   - Add state management

3. Evidence collection modal (3 hours)
   - Create modal HTML structure
   - Implement multi-step flow
   - Add work experience population
   - Form validation

4. Resume preview modal (1.5 hours)
   - Create preview modal
   - Add loading states
   - Implement download buttons

**Deliverables:**
- ✅ Interactive UI functional
- ✅ Evidence collection working
- ✅ Resume preview displays correctly

### Phase 3: Integration & Polish (Week 3) - 6 hours

**Tasks:**
1. End-to-end testing (2 hours)
   - Test full user flow
   - Fix bugs and edge cases
   - Test on different browsers

2. PDF generation (1 hour)
   - Finalize WeasyPrint styling
   - Test PDF output quality
   - Optimize for printing

3. Matching integration (1.5 hours)
   - Update matcher to use claimed data
   - Update UI to show source badges
   - Test matching with claimed competencies

4. Performance optimization (1 hour)
   - Add caching where appropriate
   - Optimize database queries
   - Test with large datasets

5. Documentation (30 min)
   - Update README
   - Add inline code comments
   - Document API endpoints

**Deliverables:**
- ✅ Feature fully functional
- ✅ Integrated with matching
- ✅ Production-ready

---

## Testing Plan

### Unit Tests

**Database Operations:**
- [ ] Save claimed competency
- [ ] Save claimed skill
- [ ] Get claimed data for user
- [ ] Save generated resume
- [ ] Get user resumes
- [ ] Handle duplicate claims
- [ ] Handle missing user

**Resume Generator:**
- [ ] Generate HTML from profile
- [ ] Format claimed evidence correctly
- [ ] Handle missing fields gracefully
- [ ] HTML to PDF conversion
- [ ] Validate HTML structure

**API Endpoints:**
- [ ] Save evidence with valid data
- [ ] Save evidence with invalid data
- [ ] Generate resume for valid job
- [ ] Generate resume for missing job
- [ ] Download resume with auth
- [ ] Download resume without auth

### Integration Tests

- [ ] Full user flow (select → evidence → generate → download)
- [ ] Multiple competencies selection
- [ ] Skip functionality works
- [ ] Evidence persists across sessions
- [ ] Generated resume includes claimed items
- [ ] PDF download works
- [ ] HTML download works
- [ ] Matching uses claimed competencies

### Manual Testing Scenarios

**Scenario 1: First-time user**
1. User views job detail page
2. Sees gray boxes for missing competencies
3. Clicks 3 gray boxes (turn green)
4. Clicks "Generate Resume (3 additions)"
5. Modal opens asking for evidence
6. Fills evidence for all 3
7. Resume generates successfully
8. Downloads PDF

**Scenario 2: Partial evidence**
1. User selects 5 missing items
2. Fills evidence for 3
3. Skips 2
4. Resume generates with only 3 additions

**Scenario 3: Return user**
1. User previously claimed competencies
2. Views different job
3. Previously claimed items show as "matched"
4. Can claim new items for new job

### Edge Cases

- [ ] User selects items but closes modal → selections cleared
- [ ] User provides very short evidence (<20 chars) → validation error
- [ ] User provides very long evidence (>500 chars) → truncated
- [ ] No work experience in profile → show message
- [ ] Job missing competencies field → handle gracefully
- [ ] Claude API error → show user-friendly message
- [ ] PDF generation fails → fallback to HTML only
- [ ] Resume too long (>2 pages) → warning to user

---

## Deployment Checklist

### Pre-deployment

- [ ] Run database migration script
- [ ] Test on staging environment
- [ ] Verify all API endpoints work
- [ ] Check WeasyPrint dependencies installed
- [ ] Verify ANTHROPIC_API_KEY is set
- [ ] Test PDF generation on Railway
- [ ] Create `static/resumes/` directory
- [ ] Set proper file permissions
- [ ] Add `.gitignore` entry for generated PDFs

### Dependencies

**Python packages to add to requirements.txt:**
```
weasyprint==60.2
```

**System dependencies (for Railway):**
```
# Dockerfile or nixpacks.toml
# WeasyPrint requires:
- cairo
- pango
- gdk-pixbuf
```

**Railway Build Configuration:**
```toml
# nixpacks.toml
[phases.setup]
aptPkgs = ['cairo', 'pango1.0', 'gdk-pixbuf-2.0']
```

### Post-deployment

- [ ] Test resume generation in production
- [ ] Verify PDF downloads work
- [ ] Check file storage and cleanup
- [ ] Monitor Claude API usage/costs
- [ ] Check error logs for issues
- [ ] Verify matching uses claimed data

### Monitoring

**Metrics to track:**
- Resume generation requests per day
- Average generation time
- Claude API costs
- PDF file storage usage
- User adoption rate
- Error rates by endpoint

---

## Cost Analysis

### Claude API Costs

**Per Resume:**
- Input: ~2,000 tokens (profile + job + evidence)
- Output: ~2,000 tokens (full HTML resume)
- Total: ~4,000 tokens
- Cost: ~$0.12 per resume (Claude 3.5 Sonnet)

**Monthly Estimates:**
- 100 users × 5 resumes each = 500 resumes
- 500 × $0.12 = $60/month
- With growth to 1,000 users: $600/month

**Optimization opportunities:**
- Cache resume templates
- Use Claude 3.5 Haiku for simpler resumes ($0.01 per resume)
- Batch generation for multiple jobs

### Storage Costs

**PDF Storage:**
- Average PDF size: ~200 KB
- 1,000 resumes = 200 MB
- Railway includes generous storage
- Implement cleanup: delete resumes older than 30 days

### Total Monthly Cost Estimate

- Claude API: $60-$600 (depending on usage)
- Storage: Negligible (< $1)
- **Total: $60-$600/month**

---

## Future Enhancements (Phase 2+)

### Short-term (1-3 months)

1. **Multiple Resume Templates**
   - Modern design
   - Traditional/conservative
   - ATS-optimized (minimal styling)
   - Academic/research focused

2. **Resume Editing**
   - Let users edit generated resume before download
   - WYSIWYG editor integration
   - Save custom edits

3. **Bulk Generation**
   - Generate resumes for top 10 jobs at once
   - Queue system for processing
   - Email notification when ready

4. **Resume Analytics**
   - Track which resumes got interviews
   - A/B test different phrasings
   - Suggest improvements based on feedback

### Medium-term (3-6 months)

5. **AI Resume Optimization**
   - Analyze job description for keywords
   - Suggest missing keywords to add
   - ATS compatibility score
   - Readability score

6. **Version History**
   - Save multiple versions per job
   - Compare versions side-by-side
   - Revert to previous version

7. **Custom Sections**
   - Let users add custom sections
   - Projects portfolio
   - Publications
   - Volunteer work

8. **LinkedIn Integration**
   - Import profile from LinkedIn
   - Keep resume in sync
   - Export to LinkedIn

### Long-term (6+ months)

9. **Resume Builder UI**
   - Drag-and-drop section reordering
   - Live preview
   - Real-time AI suggestions
   - Template customization

10. **Multi-language Support**
    - Generate resumes in multiple languages
    - Translate claimed evidence
    - Localized formatting

11. **Video Resume**
    - Script generation for video introduction
    - Talking points based on resume
    - Recording guidance

12. **Resume Coaching**
    - AI review of user's evidence
    - Suggestions for improvement
    - Industry-specific tips
    - Mock interview questions

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Claude API failures | Medium | High | Implement retry logic, fallback to cached templates |
| WeasyPrint rendering issues | Low | Medium | Test extensively, provide HTML fallback |
| PDF generation slowness | Medium | Medium | Generate async with progress indicator |
| Storage fills up quickly | Low | Medium | Implement 30-day cleanup, compress PDFs |
| User claims false competencies | High | Low | Evidence required, disclaimer shown |

### UX Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Evidence collection too tedious | Medium | High | Allow bulk skip, save progress |
| Generated resume quality poor | Low | High | Extensive prompt engineering, user feedback |
| Resume doesn't match expectations | Medium | Medium | Show preview before download, allow regeneration |
| Users don't understand feature | Medium | Medium | Add tutorial, tooltips, example evidence |

### Business Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| High Claude API costs | Medium | Medium | Monitor usage, set per-user limits |
| Users abuse free resume generation | Low | Low | Rate limiting (5 per day) |
| Legal issues with resume content | Low | High | Disclaimer that user is responsible for accuracy |

---

## Success Metrics

### Adoption Metrics

- **Week 1:** 10% of active users try feature
- **Month 1:** 30% adoption rate
- **Month 3:** 50% adoption rate

### Usage Metrics

- Average resumes generated per user: 3-5
- Average selections per resume: 2-3 competencies
- Evidence completion rate: >80%
- Download rate: >90% after generation

### Quality Metrics

- User satisfaction (survey): >4.0/5.0
- Resume regeneration rate: <20% (low = good quality)
- Feature-related support tickets: <5% of total
- User-reported errors: <2% of generations

### Business Metrics

- Conversion rate (free → paid): +5% improvement
- User retention: +10% improvement
- Time to first application: -30% reduction
- Interview callback rate: Track and compare

---

## Documentation Updates Needed

1. **README.md**
   - Add resume generation to features list
   - Include screenshots
   - Document dependencies

2. **API Documentation**
   - Document new endpoints
   - Request/response examples
   - Error codes

3. **User Guide**
   - How to claim competencies
   - Tips for writing evidence
   - Resume customization options

4. **Developer Guide**
   - Database schema
   - Claude prompt structure
   - How to add new resume templates

---

## Related Features

### Existing Features to Update

1. **Cover Letter Generation**
   - Reuse claimed competencies
   - Consistent evidence between resume and cover letter
   - Cross-link: "Generate matching resume"

2. **Job Matching**
   - Include claimed competencies in matching algorithm
   - Show "claimed" badge in match results
   - Prioritize jobs where user has claimed relevant skills

3. **User Profile**
   - Show list of all claimed competencies
   - Allow editing evidence
   - Show which jobs each claim was used for

### New Features Enabled

1. **Application Tracking**
   - Track which resume was sent for each application
   - Monitor which versions get responses
   - Optimize based on success rate

2. **Skills Gap Analysis**
   - Show most commonly missing competencies
   - Suggest courses or certifications
   - Track progress as user claims more skills

3. **Portfolio Integration**
   - Link evidence to portfolio projects
   - Include project screenshots in resume
   - Generate project descriptions

---

## Conclusion

This feature represents a significant value-add for Inclusist users:

**Value Proposition:**
- Saves users 1-2 hours per job application
- Increases application quality and interview callbacks
- Provides structured framework for self-assessment
- Leverages AI to optimize resume for each job

**Technical Feasibility:**
- Builds on existing infrastructure
- Well-defined scope and implementation plan
- Manageable complexity
- Clear success metrics

**Next Steps:**
1. Review and approve this implementation plan
2. Create database migration scripts
3. Begin Phase 1 implementation
4. Regular check-ins at end of each phase

**Estimated Timeline:**
- Phase 1: Week 1 (8 hours)
- Phase 2: Week 2 (6 hours)
- Phase 3: Week 3 (6 hours)
- **Total: 20 hours over 3 weeks**

Ready to proceed with implementation when approved.

---

## Appendix: Sample Resume Output

### Input Data

**User Profile:**
- Name: John Doe
- Role: Senior Software Engineer
- Experience: 8 years

**Job:**
- Title: Lead Software Engineer
- Company: TechCorp
- Required: Agile, Python, Team Leadership

**Claimed:**
- Agile Methodology: "Led sprint planning for 5-person team"
- Python: "Built data pipelines processing 1M records/day"

### Generated Resume (Abbreviated)

```html
<!DOCTYPE html>
<html>
<head>
    <style>
        /* Professional styling */
        body { font-family: Arial; }
        h1 { color: #2c3e50; }
        .section { margin: 20px 0; }
        .bullet { margin: 5px 0; }
    </style>
</head>
<body>
    <header>
        <h1>John Doe</h1>
        <p>Senior Software Engineer | john@email.com</p>
    </header>

    <section class="professional-summary">
        <h2>Professional Summary</h2>
        <p>Accomplished Senior Software Engineer with 8 years of
        experience in agile development and Python-based systems...</p>
    </section>

    <section class="experience">
        <h2>Professional Experience</h2>

        <div class="job">
            <h3>Senior Software Engineer - Acme Corp</h3>
            <p>2020-2023</p>
            <ul>
                <li>Led sprint planning and agile ceremonies for
                5-person cross-functional team [NEW]</li>
                <li>Built high-performance data pipelines using Python,
                processing 1M+ records daily [NEW]</li>
                <li>Architected microservices infrastructure...</li>
            </ul>
        </div>
    </section>

    <section class="skills">
        <h2>Technical Skills</h2>
        <p>Python, JavaScript, React, Node.js, Agile Methodology,
        Team Leadership, System Architecture</p>
    </section>
</body>
</html>
```

**[NEW] markers indicate bullets generated from user-claimed evidence**

---

**Document Version:** 1.0
**Last Updated:** January 14, 2026
**Author:** Claude (via User Planning Session)
**Status:** Ready for Implementation
