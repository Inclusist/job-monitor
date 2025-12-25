# Future Questions & Decisions

This document tracks open questions and potential improvements for future consideration.

---

## 1. Should JSearch API Fetching Be Triggered When Keywords Change?

**Current Behavior:**
- JSearch live fetching only triggers for **first-time users** (when `existing_matches` is empty)
- When users change their keywords, the system:
  - Re-matches against existing database jobs with new keyword boosting
  - Does NOT fetch new jobs from JSearch API

**Question:**
Should we add logic to re-trigger JSearch when a user updates their search keywords?

**Considerations:**
- **Pro:** Fresh jobs relevant to new keywords
- **Pro:** Better matches for users pivoting their search
- **Con:** Additional API costs (JSearch is paid)
- **Con:** Potential performance impact (30-60s for fetching)
- **Con:** May fetch duplicates if keywords overlap

**Possible Solutions:**
1. Track `preferences_updated` timestamp and re-fetch if keywords changed significantly
2. Add a manual "Refresh Jobs" button for users to trigger on-demand
3. Track which keywords were used for each job fetch, only fetch for new keywords
4. Periodic background refresh (e.g., once per week) regardless of keyword changes

**Decision:** TBD

---

## 2. Should Semantic Matching Threshold Be Raised from 30%?

**Current Behavior:**
- Semantic matches ≥30% are saved to database
- Claude analysis only runs on matches ≥70%
- UI filter defaults to showing 70+ but users can lower it to see 30-69% matches

**Question:**
Should we raise the minimum semantic threshold from 30% to 50% or 60%?

**Current Rationale for 30%:**
1. **User flexibility:** Users can filter UI to see medium-quality matches (30-69%)
2. **Cost savings:** Only spend Claude API credits on high-confidence jobs (≥70%)
3. **Useful data:** Even 30-69% matches show semantic score and matched keywords
4. **Future options:** Database has matches ready if we want to re-analyze or lower threshold

**Arguments for Raising Threshold:**
- **Pro:** Fewer low-quality matches in database
- **Pro:** Faster matching (fewer jobs to save)
- **Pro:** Less database storage
- **Con:** May miss edge cases that could be relevant
- **Con:** Less flexibility for users to explore broader matches

**Data Points:**
- Test with user 87: 2,162 jobs → 1,681 matches at 30% threshold
- Of those, only 8 were ≥70% (0.5%)
- Range 30-69%: 1,673 matches (99.5%)

**Options:**
1. Keep at 30% (maximum flexibility)
2. Raise to 50% (reduce storage by ~50-70%)
3. Raise to 60% (more aggressive filtering)
4. Make it configurable per user

**Decision:** TBD

---

## 3. Other Questions to Consider

- Should we add database indexes for faster querying? (user_id + job_id composite index)
- Should we implement job de-duplication across sources?
- Should we add a "Re-analyze with Claude" button for specific jobs?
- Should we implement periodic background job refresh (e.g., weekly)?
- Should we track which searches returned 0 results and adjust strategy?

---

**Last Updated:** 2025-12-25
