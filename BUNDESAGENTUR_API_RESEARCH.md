# Bundesagentur für Arbeit JOBSUCHE API Research

## Overview
The German Federal Employment Agency (Bundesagentur für Arbeit) operates Germany's largest job database. While there's no official public API, the community has documented the working endpoints through the **bundesAPI** project.

---

## 1. Base URL and Endpoints

### Base URL
```
https://rest.arbeitsagentur.de/jobboerse/jobsuche-service
```

### Available Endpoints

#### 1.1 Job Search (PC Version)
```
GET /pc/v4/jobs
```
Main endpoint for job search with filtering capabilities.

#### 1.2 Job Search (App Version)
```
GET /pc/v4/app/jobs
```
Mobile app version of job search with identical parameters.

#### 1.3 Employer Logo
```
GET /ed/v1/arbeitgeberlogo/{hashID}
```
Retrieves company logo as PNG image.

---

## 2. Authentication

### Method: API Key (Header-based)

**Authentication Type:** Static API Key  
**No registration required** - Public access using a fixed client ID

#### Header Required:
```
X-API-Key: jobboerse-jobsuche
```

#### Implementation:
```python
headers = {
    'X-API-Key': 'jobboerse-jobsuche',
    'User-Agent': 'Jobsuche/2.9.2 (de.arbeitsagentur.jobboerse; build:1077; iOS 15.1.0) Alamofire/5.4.4'
}
```

**Note:** The User-Agent is optional but recommended to mimic the official app.

---

## 3. Request Parameters

All parameters are **optional** query parameters for GET requests:

### Core Search Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `was` | string | Job title free-text search | `"Python Developer"` |
| `wo` | string | Location free-text search | `"Berlin"` |
| `berufsfeld` | string | Professional field search | `"Informatik"` |

### Pagination Parameters

| Parameter | Type | Description | Default | Example |
|-----------|------|-------------|---------|---------|
| `page` | integer | Results page (starting from 1) | 1 | `1` |
| `size` | integer | Number of results per page | 25 | `50`, `100` |

### Filtering Parameters

| Parameter | Type | Values | Description |
|-----------|------|--------|-------------|
| `angebotsart` | integer | `1`, `2`, `4`, `34` | Job type: 1=Employment, 2=Self-employment, 4=Training/Dual Study, 34=Internship/Trainee |
| `befristung` | integer | `1`, `2` | Contract: 1=Temporary, 2=Permanent (semicolon-separated: `1;2`) |
| `arbeitszeit` | string | `vz`, `tz`, `snw`, `ho`, `mj` | Work time: vz=Full-time, tz=Part-time, snw=Shift/Night/Weekend, ho=Remote/Home Office, mj=Mini-job (semicolon-separated: `vz;tz`) |
| `umkreis` | integer | 0-200 | Radius in kilometers from `wo` location | `25`, `200` |
| `veroeffentlichtseit` | integer | 0-100 | Days since job posting (0-100 days) | `7`, `30` |

### Boolean Filters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `zeitarbeit` | boolean | `true` | Include temporary agency jobs |
| `pav` | boolean | `true` | Include private employment agency jobs |
| `behinderung` | boolean | `false` | Jobs suitable for disabled persons |
| `corona` | boolean | `false` | Only COVID-19 related jobs |

### Additional Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `arbeitgeber` | string | Filter by employer name (URL encoded) | `"Deutsche%20Bahn%20AG"` |

---

## 4. Response Format

### Content-Type
```
application/json
```

### Response Structure

```json
{
  "stellenangebote": [
    {
      "refnr": "10000-1234567890-S",
      "titel": "Senior Python Developer",
      "arbeitgeber": "Tech Company GmbH",
      "arbeitsort": {
        "ort": "Berlin",
        "plz": "10115",
        "land": "Deutschland",
        "koordinaten": {
          "lat": 52.5200,
          "lon": 13.4050
        }
      },
      "beruf": "Softwareentwickler/in",
      "arbeitszeitmodelle": ["VOLLZEIT"],
      "veroeffentlicht": "2025-12-19T10:00:00+01:00",
      "aktuelleVeroeffentlichungsdatum": "2025-12-19T10:00:00+01:00",
      "eintrittsdatum": "2026-01-15",
      "befristung": "UNBEFRISTET",
      "arbeitsort_plz": "10115",
      "arbeitsort_ort": "Berlin"
    }
  ],
  "maxErgebnisse": 1000,
  "facetten": {
    "berufsfeld": [...],
    "arbeitszeit": [...],
    "angebotsart": [...]
  }
}
```

### Key Response Fields

- **stellenangebote**: Array of job postings
  - `refnr`: Unique job reference number
  - `titel`: Job title
  - `arbeitgeber`: Employer name
  - `arbeitsort`: Location details (city, ZIP, coordinates)
  - `beruf`: Profession category
  - `arbeitszeitmodelle`: Work time models (array)
  - `veroeffentlicht`: Publication date (ISO 8601)
  - `befristung`: Contract type (BEFRISTET/UNBEFRISTET)
  
- **maxErgebnisse**: Maximum number of results available
- **facetten**: Available filters/facets for refining search

---

## 5. Rate Limits

⚠️ **No official rate limit documentation found**

### Best Practices:
- Implement reasonable delays between requests (1-2 seconds recommended)
- Use pagination instead of large `size` values
- Cache results when possible
- Monitor for HTTP 429 (Too Many Requests) responses
- The API appears to be publicly accessible without strict rate limiting

### Recommended Implementation:
```python
import time
import requests

def rate_limited_request(url, headers, params):
    response = requests.get(url, headers=headers, params=params)
    time.sleep(1)  # 1 second delay between requests
    return response
```

---

## 6. Example API Calls

### Example 1: Basic Job Search (Python)

```python
import requests

# Configuration
BASE_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service"
API_KEY = "jobboerse-jobsuche"

# Headers
headers = {
    'X-API-Key': API_KEY,
    'User-Agent': 'Jobsuche/2.9.2 (de.arbeitsagentur.jobboerse; build:1077; iOS 15.1.0) Alamofire/5.4.4'
}

# Search for Python jobs in Berlin
params = {
    'was': 'Python Developer',
    'wo': 'Berlin',
    'umkreis': 25,
    'angebotsart': 1,  # Employment
    'arbeitszeit': 'vz;ho',  # Full-time and Remote
    'page': 1,
    'size': 50,
    'veroeffentlichtseit': 30  # Last 30 days
}

# Make request
response = requests.get(
    f"{BASE_URL}/pc/v4/jobs",
    headers=headers,
    params=params
)

# Parse response
if response.status_code == 200:
    data = response.json()
    jobs = data.get('stellenangebote', [])
    
    print(f"Found {len(jobs)} jobs")
    for job in jobs[:5]:
        print(f"- {job['titel']} at {job.get('arbeitgeber', 'N/A')}")
        print(f"  Location: {job['arbeitsort']['ort']}")
        print(f"  Ref: {job['refnr']}\n")
else:
    print(f"Error: {response.status_code}")
```

### Example 2: Using the Python Client Library

```python
from deutschland import jobsuche
from deutschland.jobsuche.api import default_api

# Configure API
configuration = jobsuche.Configuration(
    host = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service"
)
configuration.api_key['APIKeyHeaders'] = 'jobboerse-jobsuche'

# Create API client
with jobsuche.ApiClient(configuration) as api_client:
    api_instance = default_api.DefaultApi(api_client)
    
    # Search parameters
    try:
        api_response = api_instance.pc_v4_jobs_get(
            was="Python Developer",
            wo="Berlin",
            umkreis=25,
            angebotsart=1,
            arbeitszeit="vz;ho",
            page=1,
            size=50,
            veroeffentlichtseit=30
        )
        
        jobs = api_response.stellenangebote
        print(f"Found {len(jobs)} jobs")
        
    except jobsuche.ApiException as e:
        print(f"Exception: {e}")
```

### Example 3: Simple Search Function

```python
import requests

def search_jobs(what, where, radius=25, job_type=1):
    """
    Search for jobs using the Bundesagentur API
    
    Args:
        what (str): Job title or keywords
        where (str): Location (city name)
        radius (int): Search radius in km (default: 25)
        job_type (int): 1=Employment, 2=Self-employment, 4=Training, 34=Internship
        
    Returns:
        dict: JSON response with job listings
    """
    url = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
    
    headers = {
        'X-API-Key': 'jobboerse-jobsuche',
        'User-Agent': 'Mozilla/5.0'
    }
    
    params = {
        'was': what,
        'wo': where,
        'umkreis': radius,
        'angebotsart': job_type,
        'page': 1,
        'size': 100,
        'pav': False  # Exclude private agencies
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching jobs: {e}")
        return None

# Usage
results = search_jobs("Software Engineer", "München", radius=50)
if results and 'stellenangebote' in results:
    print(f"Total jobs: {len(results['stellenangebote'])}")
```

### Example 4: cURL Command

```bash
curl -m 60 \
  -H "X-API-Key: jobboerse-jobsuche" \
  'https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs?angebotsart=1&wo=Berlin&umkreis=200&arbeitszeit=ho;mj&page=1&size=25&pav=false'
```

### Example 5: R Language

```r
library(httr)
library(jsonlite)

clientId <- "jobboerse-jobsuche"
url <- "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"

# Add parameters
url_with_params <- paste0(url, "?angebotsart=1&wo=Berlin&was=Entwickler&size=50")

# Make request
data_request <- GET(
  url = url_with_params,
  add_headers("X-API-Key" = clientId),
  config = config(connecttimeout = 60)
)

# Parse response
data <- content(data_request)
jobs <- data$stellenangebote

print(paste("Found", length(jobs), "jobs"))
```

---

## 7. Integration Examples

### Example 6: Collector Class for Job Monitor

```python
import requests
import time
from typing import List, Dict, Optional

class BundesagenturCollector:
    """
    Collector for German Federal Employment Agency jobs
    """
    
    BASE_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service"
    API_KEY = "jobboerse-jobsuche"
    
    def __init__(self):
        self.headers = {
            'X-API-Key': self.API_KEY,
            'User-Agent': 'Mozilla/5.0'
        }
        
    def search(
        self,
        keywords: str,
        location: str,
        radius_km: int = 50,
        max_results: int = 100,
        days_since_posted: int = 30,
        remote_only: bool = False
    ) -> List[Dict]:
        """
        Search for jobs
        
        Args:
            keywords: Job title or search terms
            location: City or region name
            radius_km: Search radius in kilometers
            max_results: Maximum number of results to return
            days_since_posted: Only show jobs posted within N days
            remote_only: Only return remote/home office jobs
            
        Returns:
            List of job dictionaries
        """
        params = {
            'was': keywords,
            'wo': location,
            'umkreis': radius_km,
            'angebotsart': 1,  # Employment only
            'size': min(max_results, 100),  # API max is 100
            'veroeffentlichtseit': days_since_posted,
            'pav': False  # Exclude private agencies
        }
        
        if remote_only:
            params['arbeitszeit'] = 'ho'  # Home office
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/pc/v4/jobs",
                headers=self.headers,
                params=params,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            jobs = data.get('stellenangebote', [])
            
            # Rate limiting
            time.sleep(1)
            
            return self._normalize_jobs(jobs)
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching jobs from Bundesagentur: {e}")
            return []
    
    def _normalize_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """
        Normalize job data to standard format
        """
        normalized = []
        
        for job in jobs:
            try:
                normalized_job = {
                    'source': 'bundesagentur',
                    'external_id': job.get('refnr'),
                    'title': job.get('titel', ''),
                    'company': job.get('arbeitgeber', 'Unknown'),
                    'location': job.get('arbeitsort', {}).get('ort', ''),
                    'posted_date': job.get('aktuelleVeroeffentlichungsdatum', ''),
                    'url': f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{job.get('refnr', '')}",
                    'description': job.get('beruf', ''),
                    'contract_type': job.get('befristung', ''),
                    'work_time': ','.join(job.get('arbeitszeitmodelle', [])),
                    'raw_data': job
                }
                normalized.append(normalized_job)
            except Exception as e:
                print(f"Error normalizing job: {e}")
                continue
        
        return normalized
    
    def search_multiple_locations(
        self,
        keywords: str,
        locations: List[str],
        **kwargs
    ) -> List[Dict]:
        """
        Search across multiple locations
        """
        all_jobs = []
        
        for location in locations:
            print(f"Searching in {location}...")
            jobs = self.search(keywords, location, **kwargs)
            all_jobs.extend(jobs)
            time.sleep(2)  # Rate limiting between locations
        
        # Remove duplicates by external_id
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            job_id = job['external_id']
            if job_id not in seen:
                seen.add(job_id)
                unique_jobs.append(job)
        
        return unique_jobs

# Usage example
if __name__ == "__main__":
    collector = BundesagenturCollector()
    
    # Search for jobs
    jobs = collector.search(
        keywords="Python Developer",
        location="Berlin",
        radius_km=50,
        max_results=50,
        remote_only=True
    )
    
    print(f"Found {len(jobs)} jobs")
    for job in jobs[:5]:
        print(f"- {job['title']} at {job['company']}")
```

---

## 8. Important Notes

### Limitations

1. **Unofficial API**: This is not an officially supported API by the Bundesagentur für Arbeit
2. **No OAuth**: Simple static API key authentication
3. **No Documentation on Rate Limits**: Use responsibly to avoid getting blocked
4. **German Language**: Results and parameters are primarily in German
5. **Pagination Limit**: Maximum 100 results per page

### Best Practices

1. **Always include User-Agent header** to identify your application
2. **Implement retry logic** for failed requests
3. **Cache results** to minimize API calls
4. **Use appropriate delays** between requests (1-2 seconds)
5. **Handle errors gracefully** - API may be unavailable
6. **Respect the data** - this is a public service

### Data Usage

- The data is publicly accessible but respect the source
- Attribute the source when using the data
- Do not overload the API with excessive requests
- Consider storing results locally to reduce API calls

---

## 9. Additional Resources

- **GitHub Repository**: https://github.com/bundesAPI/jobsuche-api
- **API Documentation**: https://jobsuche.api.bund.dev/
- **OpenAPI Spec**: https://jobsuche.api.bund.dev/openapi.yaml
- **Python Client**: Available via `deutschland` package
  ```bash
  pip install deutschland[jobsuche]
  ```

### Community Projects

- bundesAPI Python Client: Auto-generated client library
- Multiple examples in Python, R, and other languages
- Active community with 114+ stars on GitHub

---

## 10. Response Example (Full)

```json
{
  "stellenangebote": [
    {
      "refnr": "10000-1234567890-S",
      "beruf": "Fachinformatiker/in - Anwendungsentwicklung",
      "titel": "Senior Python Developer (m/w/d)",
      "arbeitgeber": "Tech Company GmbH",
      "arbeitgeberHashId": "VK2qoXBe0s-UAdH_qxLDRrZrY5iY8a1PJt3MjJCXsdo=",
      "arbeitsort": {
        "strasse": "Hauptstraße 123",
        "plz": "10115",
        "ort": "Berlin",
        "land": "Deutschland",
        "koordinaten": {
          "lat": 52.5200,
          "lon": 13.4050
        }
      },
      "arbeitsort_plz": "10115",
      "arbeitsort_ort": "Berlin",
      "arbeitszeitmodelle": ["VOLLZEIT", "HEIM_TELEARBEIT"],
      "angebotsart": "ARBEIT",
      "befristung": "UNBEFRISTET",
      "veroeffentlicht": "2025-12-19T10:00:00+01:00",
      "aktuelleVeroeffentlichungsdatum": "2025-12-19T10:00:00+01:00",
      "modifikationsTimestamp": "2025-12-19T10:00:00+01:00",
      "eintrittsdatum": "2026-01-15",
      "branche": "Information und Kommunikation"
    }
  ],
  "maxErgebnisse": 1000,
  "page": {
    "number": 1,
    "size": 50,
    "totalElements": 1000,
    "totalPages": 20
  },
  "facetten": {
    "berufsfeld": [
      {
        "bezeichnung": "Informatik, IT",
        "anzahl": 856
      }
    ],
    "arbeitszeit": [
      {
        "bezeichnung": "Vollzeit",
        "code": "vz",
        "anzahl": 920
      },
      {
        "bezeichnung": "Teilzeit",
        "code": "tz",
        "anzahl": 80
      }
    ]
  }
}
```

---

## Summary

The Bundesagentur für Arbeit JOBSUCHE API provides access to Germany's largest job database through:

✅ **Simple API Key Authentication** (no registration needed)  
✅ **RESTful JSON API** with comprehensive filtering  
✅ **No apparent rate limits** (but use responsibly)  
✅ **Active community support** via bundesAPI project  
✅ **Python client library** available  
✅ **Free and public access**  

⚠️ **Considerations:**
- Unofficial/undocumented API
- Primarily German language
- No official support or SLA
- Rate limits unknown - implement safeguards

**Recommended for production use** with proper error handling and rate limiting.
