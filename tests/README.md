# Job Monitor Test Suite

Comprehensive test suite with cost-effective API usage controls using pytest markers.

## Test Files

### Database Tests (`test_database_operations.py`)
- **Tests**: 11 | **Cost**: $0 (no API calls)
- PostgreSQL CRUD operations (users, CVs, profiles, jobs, matches)
- `pytest tests/test_database_operations.py -v`

### Error Handling (`test_error_handling.py`)
- **Tests**: 14 | **Cost**: $0
- Input validation and error scenarios
- `pytest tests/test_error_handling.py -v`

### Integration (`test_integration.py`)
- **Tests**: 2 | **Cost**: $0 (uses mock data)
- End-to-end user journey validation
- `pytest tests/test_integration.py -v`

### API Collectors (`test_api_collectors.py`) ⚡ NEW
- **Tests**: 17 | **Cost**: Variable (see markers below)
- Live API testing: JSearch, ActiveJobs, Bundesagentur für Arbeit
- Uses pytest markers for flexible cost control
- `pytest -m quick -v` (recommended for daily use)

### Full Workflow (`test_full_workflow.py`)
- **Tests**: 1 | **Cost**: ~$0.02
- Complete workflow with Claude analysis (5 jobs max, Haiku model)
- `pytest tests/test_full_workflow.py -v`

## Pytest Markers (Cost Control)

Tests are categorized with markers for flexible execution:

```bash
# Quick smoke tests - 3 tests, ~60 jobs, $0.002
pytest -m quick -v

# All API tests - 17 tests, ~700 jobs, $0.01  
pytest -m api -v

# Skip expensive tests - 14 tests, ~300 jobs, $0.008
pytest -m "api and not expensive" -v

# Integration test - all 3 APIs, ~135 jobs, $0.003
pytest -m integration -v

# Database only - no API costs
pytest -m database -v
```

## Recommended Workflows

**Daily Development** (quick validation):
```bash
pytest -m quick -v  # 3 seconds, $0.002
```

**Before Committing** (recommended):
```bash
pytest -m "not expensive" -v  # 30 seconds, ~$0.01
# Or just database + error tests:
pytest tests/test_database_operations.py tests/test_error_handling.py tests/test_integration.py -v
```

**Pre-Deployment / Weekly** (full validation):
```bash
pytest -v  # Full suite, 60 seconds, ~$0.03
```

## API-Specific Testing

```bash
# Test individual APIs
pytest tests/test_api_collectors.py::TestArbeitsagenturCollector -v  # FREE, no key needed
pytest tests/test_api_collectors.py::TestJSearchCollector -v         # RapidAPI
pytest tests/test_api_collectors.py::TestActiveJobsCollector -v      # RapidAPI
```

## Environment Variables

Required in `.env`:
```bash
# For JSearch & ActiveJobs (RapidAPI) 
export RAPIDAPI_KEY="your_rapidapi_key"

# Bundesagentur für Arbeit needs no key (always works)

# For full workflow test
DATABASE_URL=postgresql://...
ANTHROPIC_API_KEY=sk-ant-...
```

Tests automatically skip if `RAPIDAPI_KEY` is not set.

## Cost Breakdown

| Test Suite | Tests | Jobs | API Calls | Cost |
|------------|-------|------|-----------|------|
| Database Operations | 11 | 0 | 0 | $0 |
| Error Handling | 14 | 0 | 0 | $0 |
| Integration (mock) | 2 | 0 | 0 | $0 |
| API Quick (`-m quick`) | 3 | ~60 | 3 | ~$0.002 |
| API Standard (`-m "api and not expensive"`) | 14 | ~300 | 15 | ~$0.008 |
| API Full (`-m api`) | 17 | ~700 | 18 | ~$0.01 |
| Full Workflow | 1 | 5 | 6 | ~$0.02 |
| **TOTAL (all tests)** | **48** | **~765** | **24** | **~$0.03** |
```
DATABASE_URL=postgresql://...
ANTHROPIC_API_KEY=sk-ant-...
JSEARCH_API_KEY=...
```

## Pytest Configuration

See [pytest.ini](../pytest.ini) for marker definitions:
- `quick`: Minimal API calls for smoke testing
- `api`: All API-dependent tests  
- `expensive`: High-usage tests (multiple pages)
- `integration`: Multi-system integration tests
- `database`: Database-only tests

## Test Coverage

Run with coverage report:
```bash
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

## Continuous Integration

For CI/CD pipelines (cost control):
```bash
# Recommended: Quick tests only
pytest -m quick -v

# Or skip all external APIs
pytest -m "not api" -v

# Full suite (weekly)
pytest -v
```

## Test Data Cleanup

Remove test data from database:
```bash
python scripts/cleanup_test_data.py
```

Or use the test runner:
```bash
./run_tests.sh
```
