# AI Learning System - How It Works

## Overview
The Job Monitor uses Claude AI to analyze jobs and score them based on your CV. Over time, Claude learns from your feedback to improve future recommendations.

## The Learning Flow

```
1. You rate a job (Accurate/Too High/Too Low/Poor Match)
   └─> Optional: Provide your own score (0-100)
   └─> Optional: Explain your reason

2. System stores feedback with job details
   └─> Original Claude score
   └─> Your feedback type & score
   └─> Your written reason
   └─> Job description, alignments, gaps

3. FeedbackLearner analyzes all your feedback
   └─> Groups: Jobs you liked vs disliked
   └─> Extracts: Common skills, industries, deal-breakers
   └─> Calculates: Score calibration bias

4. Learning context generated
   └─> Examples of jobs you liked (with your reasons)
   └─> Examples of jobs you disliked (with your reasons)
   └─> Extracted preferences (what you value)
   └─> Deal-breakers (what you avoid)
   └─> Score adjustment guidance

5. Claude analyzes new jobs WITH your learning context
   └─> Sees your CV
   └─> Sees your past preferences
   └─> Adjusts scoring based on what you've taught it
```

## What Claude Learns

### From "👍 Accurate" Feedback
When you agree with high scores (85+):
- These job characteristics are valuable to you
- This company type appeals to you
- This role level is appropriate
- These skills/technologies interest you

### From "📉 Score Too High" Feedback
When Claude overestimates a job:
- Learns what you DON'T value
- Identifies your deal-breakers
- Adjusts expectations downward
- Recognizes misalignments you care about

**Example:** You rate a 82-score job as "too high" with reason: "Too much consulting work, I prefer product companies"
→ Claude learns: *Consulting roles should score lower, product companies preferred*

### From "📈 Score Too Low" Feedback  
When Claude underestimates a job:
- Learns what you DO value (even if not obvious in CV)
- Identifies hidden preferences
- Adjusts expectations upward
- Recognizes opportunities you see

**Example:** You rate a 68-score remote job as "too low" with score 85, reason: "Remote work is very important to me"
→ Claude learns: *Remote roles deserve +17 point boost, user highly values flexibility*

### From "👎 Poor Match" Feedback
When a job is completely wrong:
- Strong negative signal
- These characteristics to avoid
- This type of role doesn't fit
- Major misalignment identified

**Example:** Job score 75, you rate "poor match" with reason: "No leadership responsibilities, I need to manage a team"
→ Claude learns: *Individual contributor roles are deal-breakers, must emphasize team management*

## Score Calibration

The system tracks score differences to calibrate Claude's judgment:

**Scenario 1: Claude too optimistic**
- You give 10 jobs "too high" feedback
- Average: Claude scores 78, you say 65
- **Bias: +13 points**
- Future jobs: Claude instructed to be ~13 points more conservative

**Scenario 2: Claude too pessimistic**
- You give 10 jobs "too low" feedback  
- Average: Claude scores 62, you say 78
- **Bias: -16 points**
- Future jobs: Claude instructed to be ~16 points more generous

## Pattern Extraction

### Keyword Analysis
From your feedback reasons, the system extracts themes:
- "remote work is important" → *values: remote*
- "too much travel" → *dealbreaker: travel*
- "not enough ML work" → *values: machine learning*
- "great automotive company" → *values: automotive*

### Alignment Learning
From jobs you liked:
- Common skills in "key alignments"
- Company sizes/types
- Technologies mentioned
- Role characteristics

From jobs you disliked:
- Common issues in "potential gaps"
- Problematic requirements
- Red flags you identify

## Why Your Reasons Matter

**Without reason:**
```
Job: "Senior Data Scientist at Agency X" (Score: 78)
Feedback: 📉 Too High
Your Score: 55

Claude learns: "This job type should score lower"
```

**With detailed reason:**
```
Job: "Senior Data Scientist at Agency X" (Score: 78)
Feedback: 📉 Too High  
Your Score: 55
Reason: "Agency work means juggling multiple clients with no deep technical work. 
         I need to build production ML systems, not just consulting reports."

Claude learns: 
- Agency/consulting roles are deal-breakers
- User values "production ML systems" and "deep technical work"
- Multiple clients = negative signal
- Report-writing focus = dealbreaker
→ Future agency jobs will score 20+ points lower
→ Future production ML roles will score higher
```

## The Learning Context in Action

When Claude analyzes a new "Head of ML Engineering at Tesla" job, it sees:

```
## USER PREFERENCE LEARNING
Based on 23 feedback items:

### Jobs User Found Highly Relevant:
- Head of Data Science at BMW (92) - "Perfect automotive focus"
- ML Engineering Manager at Bosch (88) - "Love the production ML emphasis"
- Principal ML Engineer at Volkswagen (90) - "Senior role + automotive"

### Jobs User Found Less Relevant:
- Data Scientist at McKinsey (75) - "Too much consulting, not technical"
- Senior Analyst at Agency (68) - "Client juggling, no depth"
- ML Engineer at Startup (72) - "Too junior, need leadership role"

### User Values: automotive, leadership, production ML, engineering depth
### User Concerns: consulting, agencies, client juggling, junior roles

### Scoring Guidance: Be 8 points more conservative than usual.

### Instructions: This Tesla role is automotive + engineering leadership + 
production ML = HIGH match. Avoid consulting red flags. Score confidently high.
```

**Result:** Claude scores this 95 (vs 85 without learning) because it matches ALL your learned preferences!

## Tips for Better Learning

1. **Be specific**: "Not interested" → "Location requires daily office presence, I need remote flexibility"

2. **Quantify when possible**: Instead of "too junior", say "Need to manage 5+ people, this is individual contributor"

3. **Mention alternatives**: "Prefer X over Y" → "Would rather see product companies than consulting firms"

4. **Explain surprises**: "I know my CV says X, but actually I want Y because..."

5. **Rate consistently**: 20+ ratings = Good learning | 50+ ratings = Excellent learning

## Technical Details

**Storage:** SQLite `job_feedback` table with full job details and your feedback

**Analysis:** Python `FeedbackLearner` class extracts patterns using keyword matching and statistical analysis

**Integration:** Learning context injected into Claude's system prompt before each job analysis

**Privacy:** All learning is local to your database, never shared

## View Your Learning

Visit the **🧠 Learning Insights** page to see:
- What Claude has learned about your preferences
- Score calibration status  
- Examples of jobs you liked/disliked
- The exact learning context Claude sees
- Your complete feedback history

The more you use it, the smarter it gets! 🚀
