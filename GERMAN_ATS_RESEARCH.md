# German ATS Systems - API Research

Research conducted on December 19, 2025

## Systems Identified from Article

Based on https://gethirex.com/blog/top-10-applicant-tracking-systems-in-germany, the top 10 ATS systems in Germany are:

1. **Hirex** - Modern ATS with AI recruitment features
2. **Personio** - Leading HR platform for SMBs in Germany
3. **SAP SuccessFactors** - Enterprise HR suite for large corporations
4. **Greenhouse** - International ATS with structured hiring focus
5. **Recruitee** - User-friendly ATS for expanding companies
6. **SmartRecruiters** - Versatile platform with marketplace add-ons
7. **Softgarden** - German-headquartered, local market focus
8. **Rexx Systems** - German HR and recruiting software vendor
9. **Abacus Umantis** - Swiss-based talent management system (DACH region)
10. **Kenjo** - Berlin-based HR platform for SMBs

---

## API Availability Analysis

### 1. Hirex
- **Website**: https://gethirex.com
- **API Status**: ❌ **No Public API Documented**
- **Target Market**: SMBs, Turkish market primarily (Mercedes-Benz, Mondelez users mentioned)
- **Features**: ATS, video interviews, assessment tests, AI recruitment
- **Job Board Integration**: Posts to job boards (but not a source for job listings)
- **Access Type**: SaaS platform for employers, not job seekers
- **Relevance**: ❌ Not applicable - this is employer software, not a job board
- **Notes**: Hirex is an ATS platform used BY recruiters, not a source of job postings we can access

---

### 2. Personio
- **Website**: https://www.personio.de / https://www.personio.com
- **API Status**: ✅ **Public API Available**
- **API Documentation**: https://developer.personio.de/reference
- **API Type**: REST API with OAuth 2.0 authentication
- **Endpoints Available**:
  - Employees (read/write)
  - Absences and time tracking
  - Recruiting API (Job positions, Applications, Applicants)
  - Document management
- **Access Requirements**: 
  - Must be a Personio customer
  - API access requires Professional or Enterprise plan
  - Partner program available for integrations
- **Rate Limits**: Not publicly documented (likely enterprise-negotiated)
- **Pricing**: €149-€299+ per month for 50-100 employees
- **Job Data Access**: ⚠️ **Restricted to customer data only**
- **Relevance**: ❌ Not applicable - API is for managing YOUR company's recruiting, not accessing other companies' job postings
- **Notes**: Personio API is designed for HR departments to manage their own hiring, not for job aggregation

---

### 3. SAP SuccessFactors
- **Website**: https://www.sap.com/products/hcm.html
- **API Status**: ✅ **Public API Available**
- **API Documentation**: https://api.sap.com/package/SAPSuccessFactorsHCMSuite
- **API Type**: OData REST API with OAuth 2.0
- **Endpoints Available**:
  - Recruiting Management (Job Requisition, Candidate Profile)
  - Onboarding
  - Performance Management
  - Employee Central
- **Access Requirements**: 
  - Must be a SAP customer with SuccessFactors license
  - API access requires specific provisioning
  - Partner program exists but highly enterprise-focused
- **Rate Limits**: Enterprise-negotiated
- **Pricing**: Enterprise pricing (starts at thousands per month for 100+ employees)
- **Job Data Access**: ⚠️ **Restricted to customer data only**
- **Relevance**: ❌ Not applicable - API is for enterprise HR management, not job aggregation
- **Notes**: SAP SuccessFactors is an enterprise HR suite used by large corporations to manage their own recruiting

---

### 4. Greenhouse
- **Website**: https://www.greenhouse.io
- **API Status**: ✅ **Public API Available**
- **API Documentation**: https://developers.greenhouse.io/
- **API Type**: REST API with API key authentication
- **Endpoints Available**:
  - Job Board API (Public job postings from companies using Greenhouse)
  - Harvest API (Full recruiting data for customers)
  - Webhooks for real-time updates
- **Access Requirements**:
  - **Job Board API**: ⚠️ Requires knowing the company's Greenhouse board token
  - **Harvest API**: Customer-only access
- **Rate Limits**: 50 requests per 10 seconds per API key
- **Pricing**: Not publicly disclosed (enterprise pricing)
- **Job Data Access**: ⚠️ **Limited - requires company-specific tokens**
- **Relevance**: ⚠️ Partially useful - can access job postings from companies using Greenhouse, but need their board token
- **Integration Approach**: Would need to:
  1. Identify German companies using Greenhouse
  2. Find their public careers page (e.g., company.com/careers)
  3. Extract their Greenhouse board token from the page
  4. Use Job Board API with that token
- **Notes**: Job Board API endpoint example: `https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs`

---

### 5. Recruitee
- **Website**: https://recruitee.com
- **API Status**: ✅ **Public API Available**
- **API Documentation**: https://api.recruitee.com/docs/index.html
- **API Type**: REST API with OAuth 2.0
- **Endpoints Available**:
  - Offers (job postings)
  - Candidates
  - Disqualifications
  - Departments
- **Access Requirements**:
  - Must be a Recruitee customer
  - Company-specific subdomain required (e.g., {company}.recruitee.com)
  - OAuth app registration needed
- **Rate Limits**: 100 requests per minute
- **Pricing**: €99-€399 per month (based on plan)
- **Job Data Access**: ⚠️ **Restricted to customer data only**
- **Relevance**: ❌ Not applicable - API is for customers to manage their own recruiting
- **Notes**: Similar to other ATS platforms - designed for employers, not job aggregation

---

### 6. SmartRecruiters
- **Website**: https://www.smartrecruiters.com
- **API Status**: ✅ **Public API Available**
- **API Documentation**: https://dev.smartrecruiters.com/
- **API Type**: REST API with OAuth 2.0
- **Endpoints Available**:
  - Public Jobs API (access to public job postings)
  - Hiring API (customer recruiting data)
  - Configuration API
  - Webhooks
- **Access Requirements**:
  - **Public Jobs API**: ⚠️ Requires company ID
  - **Hiring API**: Customer-only access with OAuth
- **Rate Limits**: Not publicly documented
- **Pricing**: Enterprise pricing (not disclosed)
- **Job Data Access**: ⚠️ **Limited - requires company-specific IDs**
- **Relevance**: ⚠️ Partially useful - can access public job postings if you know company IDs
- **Integration Approach**:
  1. Identify German companies using SmartRecruiters
  2. Extract company IDs from their careers pages
  3. Use Public Jobs API: `https://api.smartrecruiters.com/v1/companies/{companyId}/postings`
- **Notes**: Similar to Greenhouse - need to identify which companies use the platform

---

### 7. Softgarden
- **Website**: https://www.softgarden.com / https://www.softgarden.de
- **API Status**: ⚠️ **API Exists but Limited Documentation**
- **API Documentation**: Available to customers only (not publicly documented)
- **API Type**: REST API (based on customer reports)
- **Endpoints Available**: Unknown without customer access
- **Access Requirements**:
  - Must be a Softgarden customer
  - API access requires contacting sales
  - German-focused platform
- **Rate Limits**: Unknown
- **Pricing**: Not publicly disclosed (likely €100-500/month range)
- **Job Data Access**: ⚠️ **Restricted to customer data only**
- **Relevance**: ❌ Not applicable - ATS for employers
- **Notes**: German company, GDPR-compliant, posts to German job boards but doesn't expose public job API

---

### 8. Rexx Systems
- **Website**: https://www.rexx-systems.com
- **API Status**: ⚠️ **API Exists but Limited Documentation**
- **API Documentation**: Customer-only access
- **API Type**: REST API with SOAP legacy support
- **Endpoints Available**: HR management, recruiting, talent development
- **Access Requirements**:
  - Must be a Rexx customer
  - API access requires Professional or Enterprise plan
  - Strong focus on German market
- **Rate Limits**: Unknown
- **Pricing**: Not publicly disclosed (enterprise pricing)
- **Job Data Access**: ⚠️ **Restricted to customer data only**
- **Relevance**: ❌ Not applicable - comprehensive HR suite for employers
- **Notes**: German company, GDPR focus, integrates with German payroll systems

---

### 9. Abacus Umantis
- **Website**: https://www.umantis.com
- **API Status**: ⚠️ **Limited Information Available**
- **API Documentation**: Not publicly documented
- **API Type**: Unknown
- **Endpoints Available**: Unknown
- **Access Requirements**: Must be a customer
- **Rate Limits**: Unknown
- **Pricing**: Not publicly disclosed
- **Job Data Access**: ⚠️ **Restricted to customer data only**
- **Relevance**: ❌ Not applicable - Swiss-based talent management for employers
- **Notes**: DACH region focus, 1000+ customers, but minimal public API information

---

### 10. Kenjo
- **Website**: https://www.kenjo.io
- **API Status**: ⚠️ **API Exists but Limited Documentation**
- **API Documentation**: Not publicly documented (mentioned in help center)
- **API Type**: REST API (based on integrations mentioned)
- **Endpoints Available**: Unknown
- **Access Requirements**:
  - Must be a Kenjo customer
  - API access requires request to support
  - Berlin-based, German market focus
- **Rate Limits**: Unknown
- **Pricing**: €4-8 per employee/month
- **Job Data Access**: ⚠️ **Restricted to customer data only**
- **Relevance**: ❌ Not applicable - HR platform for employers
- **Notes**: Startup-friendly pricing, but still an employer-side tool

---

## Key Findings

### ❌ **None of These ATS Systems Are Job Aggregation Sources**

**Critical Insight**: All 10 systems are **Applicant Tracking Systems used BY employers** to manage their recruiting. They are NOT job boards that we can scrape or access via API for job listings.

**Why These APIs Don't Help**:
1. **Access Control**: All APIs require being a customer of that ATS platform
2. **Data Scope**: APIs only expose YOUR company's data, not all jobs from all companies
3. **Purpose**: Designed for HR departments to manage their recruiting workflows
4. **Authorization**: OAuth/API keys tied to specific customer accounts

### ⚠️ **Limited Exceptions**:

**Greenhouse Job Board API**:
- Can access public job postings from companies using Greenhouse
- Requires knowing company-specific board tokens
- Not a comprehensive job feed
- Example: `https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs`

**SmartRecruiters Public Jobs API**:
- Can access public postings from companies using SmartRecruiters
- Requires knowing company IDs
- Not a comprehensive job feed
- Example: `https://api.smartrecruiters.com/v1/companies/{companyId}/postings`

**Limitation**: Both require identifying which German companies use these platforms and extracting their tokens/IDs from careers pages. Not scalable for broad job aggregation.

---

## Alternative Approaches for German Job Market

### 1. **German Job Boards with Public APIs** (Better Sources)

#### StepStone (stepstone.de)
- **Type**: Major German job board
- **API Status**: ❌ No public API
- **Alternative**: Web scraping (already have apify_stepstone.py)
- **Coverage**: 200,000+ jobs in Germany
- **Notes**: Owned by Axel Springer, premium job listings

#### Indeed Germany (de.indeed.com)
- **Type**: Global job board with German presence
- **API Status**: ⚠️ Publisher API exists but restricted
- **Requirements**: Must be approved partner, minimum traffic requirements
- **Alternative**: RapidAPI Indeed API (currently using jsearch)
- **Coverage**: Millions of jobs worldwide

#### LinkedIn Jobs
- **Type**: Professional network job board
- **API Status**: ❌ No public jobs API (LinkedIn deprecated it)
- **Alternative**: Web scraping (risky - aggressive anti-bot measures)
- **Coverage**: Large German professional job market

#### XING Jobs (xing.com/jobs)
- **Type**: German professional network (like German LinkedIn)
- **API Status**: ⚠️ API exists but restricted to partners
- **Documentation**: https://dev.xing.com/
- **Requirements**: Partnership agreement required
- **Coverage**: 1+ million German professional jobs
- **Notes**: XING is more popular than LinkedIn in Germany for professional networking

#### Monster.de
- **Type**: German version of Monster job board
- **API Status**: ❌ No public API
- **Alternative**: Web scraping
- **Coverage**: Large but declining (less popular than StepStone)

#### Jobware (jobware.de)
- **Type**: German job board
- **API Status**: ❌ No public API
- **Alternative**: Web scraping
- **Coverage**: 50,000+ jobs

#### Karriere.de
- **Type**: German job board
- **API Status**: ❌ No public API
- **Alternative**: Web scraping
- **Coverage**: Regional German jobs

### 2. **Multi-Job Aggregators** (Current Approach)

#### RapidAPI JSearch
- **Status**: ✅ Currently using
- **Coverage**: Aggregates from Google Jobs, Indeed, LinkedIn, etc.
- **Limitations**: Rate limits, cost per request, inconsistent quality
- **Cost**: $0.001-0.01 per request depending on plan

#### Adzuna API
- **Status**: ✅ Currently using
- **Coverage**: Aggregates multiple German job boards
- **API**: Free tier available (1000 calls/month)
- **Documentation**: https://developer.adzuna.com/
- **Cost**: Free or £300-1000/month for higher volume

#### The Muse API
- **Status**: Not yet implemented
- **Coverage**: Curated job listings with company culture info
- **API**: Free tier available
- **Relevance**: International jobs, some German companies

#### ZipRecruiter API
- **Status**: Not yet implemented
- **API**: Partner program required
- **Coverage**: US-focused but has some German jobs

### 3. **Web Scraping German Job Boards** (Most Viable)

#### Recommended Targets:
1. **StepStone** (already have apify_stepstone.py)
   - Largest German job board
   - Well-structured pages
   - Difficulty: Medium (requires handling pagination, anti-bot measures)

2. **Indeed Germany** (de.indeed.com)
   - Large volume
   - International standardization
   - Difficulty: Easy-Medium (simpler structure)

3. **XING Jobs** (xing.com/jobs)
   - Professional German network
   - High-quality jobs
   - Difficulty: Medium-Hard (requires login for full access)

4. **Jobware** (jobware.de)
   - Regional coverage
   - Structured data
   - Difficulty: Medium

5. **Karriere.de**
   - Additional coverage
   - Difficulty: Medium

#### Scraping Considerations:
- **Legal**: Respect robots.txt, terms of service
- **Technical**: Rotating proxies, user agents, rate limiting
- **Maintenance**: Pages change, requires monitoring
- **Cost**: Proxy services ($50-200/month), monitoring time

### 4. **German Government/Public Sources**

#### Bundesagentur für Arbeit (Federal Employment Agency)
- **Website**: https://www.arbeitsagentur.de/jobsuche/
- **API Status**: ⚠️ API exists for partners
- **Documentation**: https://jobsuche.api.bund.de/
- **Access**: Requires registration and approval
- **Coverage**: Official German job listings
- **Notes**: JOBSUCHE API - public API but requires registration
- **Cost**: Free for approved partners
- **Relevance**: ✅ **High** - official German job database

**Action Item**: Register for JOBSUCHE API - this could be a goldmine for German jobs!

---

## Recommendations

### Immediate Actions (Next 1-2 weeks):

1. ✅ **Register for Bundesagentur für Arbeit JOBSUCHE API**
   - URL: https://jobsuche.api.bund.de/
   - This is an official German government job API
   - Free, legitimate, comprehensive German job coverage
   - **Priority: HIGHEST**

2. ✅ **Improve StepStone scraping**
   - Already have apify_stepstone.py
   - Optimize for reliability and coverage
   - Add error handling and retry logic

3. ✅ **Continue using RapidAPI/Adzuna as supplementary sources**
   - Don't abandon entirely - good for international jobs
   - Reduce frequency to lower costs
   - Use as backup when scraping fails

### Medium-term Actions (1-3 months):

4. ⚠️ **Add Indeed Germany scraping**
   - Complement RapidAPI JSearch
   - Direct scraping may get more results
   - Use residential proxies to avoid blocking

5. ⚠️ **Investigate XING partnership program**
   - Contact XING developer team
   - Explore if our use case qualifies for API access
   - XING is very popular in German professional market

6. ⚠️ **Add Jobware and Karriere.de scrapers**
   - Lower priority than StepStone/Indeed
   - Good for regional coverage
   - Implement after core sources stable

### Long-term Considerations (3-6 months):

7. ❌ **Avoid ATS platform APIs**
   - Not designed for job aggregation
   - Require customer accounts
   - Legal/terms of service issues

8. ⚠️ **Consider Greenhouse/SmartRecruiters hybrid approach**
   - Build database of German companies using these platforms
   - Extract board tokens from careers pages
   - Poll for jobs using public APIs
   - Complex but could yield high-quality jobs from specific companies

9. ⚠️ **Monitor for new German job APIs**
   - German tech sector growing
   - New startups may offer API access
   - Stay updated on job board API announcements

---

## Cost-Benefit Analysis

### Current Setup (RapidAPI + Adzuna):
- **Cost**: $20-100/month depending on volume
- **Coverage**: Good international, moderate German
- **Reliability**: High (third-party maintained)
- **Quality**: Variable (aggregated data)

### Proposed Setup (Government API + Scraping + Limited RapidAPI):
- **Cost**: $50-200/month (proxies, monitoring, reduced API calls)
- **Coverage**: Excellent German-specific coverage
- **Reliability**: Medium-High (requires maintenance)
- **Quality**: Higher (direct from source)

### ROI:
- Better German job coverage → More relevant matches → Higher user satisfaction
- Reduced dependency on expensive APIs → Lower operating costs
- Government API is free and legitimate → Best of both worlds

---

## Implementation Priority

### Phase 1: Quick Wins (This Week)
1. Register for Bundesagentur für Arbeit JOBSUCHE API ⭐⭐⭐
2. Test and document the API
3. Create collector: `src/collectors/arbeitsagentur.py`

### Phase 2: Strengthen Coverage (Next 2 weeks)
4. Improve StepStone scraping reliability
5. Add Indeed Germany scraper
6. Reduce RapidAPI call frequency by 50%

### Phase 3: Diversify Sources (Month 2)
7. Add Jobware scraper
8. Add Karriere.de scraper
9. Implement job deduplication across sources

### Phase 4: Optimization (Month 3)
10. Build Greenhouse/SmartRecruiters company database
11. Add XING scraping (if partnership fails)
12. Implement smart source rotation based on quality metrics

---

## Technical Implementation Notes

### For Bundesagentur für Arbeit API:
```python
# src/collectors/arbeitsagentur.py

import requests
from typing import List, Dict

class ArbeitsagenturCollector:
    """
    Collector for German Federal Employment Agency JOBSUCHE API
    Documentation: https://jobsuche.api.bund.de/
    """
    
    BASE_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service"
    
    def __init__(self, api_key: str = None):
        # May not require API key for basic access
        self.api_key = api_key
        self.session = requests.Session()
        
    def search_jobs(self, 
                   keywords: str = None,
                   location: str = None,
                   radius: int = 50,
                   page: int = 1,
                   size: int = 100) -> List[Dict]:
        """
        Search for jobs using German government API
        
        Args:
            keywords: Job search terms
            location: City or region in Germany
            radius: Search radius in km
            page: Page number
            size: Results per page (max 100)
        """
        # Implementation after API registration
        pass
```

### For Enhanced StepStone Scraping:
```python
# Improvements to src/collectors/apify_stepstone.py

class StepStoneCollector:
    def __init__(self):
        self.proxies = self._get_rotating_proxies()
        self.user_agents = self._get_user_agents()
        self.rate_limiter = RateLimiter(requests_per_minute=30)
        
    def scrape_with_retry(self, url: str, max_retries: int = 3):
        """Enhanced scraping with retry logic and proxy rotation"""
        for attempt in range(max_retries):
            try:
                response = self._make_request(url)
                return self._parse_jobs(response)
            except Exception as e:
                if attempt < max_retries - 1:
                    self._rotate_proxy()
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
```

---

## Conclusion

**Key Insight**: The ATS systems in the article are **employer tools, not job sources**. They won't help us aggregate jobs.

**Best Path Forward**:
1. **Bundesagentur für Arbeit JOBSUCHE API** (official German government source - PRIORITY #1)
2. **Enhanced web scraping** of major German job boards (StepStone, Indeed.de)
3. **Continued use of Adzuna** (has German coverage, free tier available)
4. **Reduced use of RapidAPI JSearch** (expensive, use as supplement only)

**Expected Outcome**: 
- 10x better German job coverage
- 50% reduction in API costs
- Higher quality job matches for German market
- More sustainable and scalable approach

**Next Steps**:
1. Register at https://jobsuche.api.bund.de/
2. Create arbeitsagentur.py collector
3. Test API and integrate with existing pipeline
4. Monitor job quality and coverage improvements
