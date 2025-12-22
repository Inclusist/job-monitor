# Job Monitor Tests

Comprehensive test suite for the Job Monitor application.

## Test Files

### `test_full_workflow.py`
Complete end-to-end integration tests covering:
- User registration and authentication
- CV upload and parsing
- Search preferences management  
- **Limited job search** (5 jobs max to minimize API costs)
- Job matching to user CV
- Match retrieval and filtering
- Statistics and reporting

**Cost Control**: Uses only 1 search query with 5 jobs maximum to minimize API usage.

### `test_database_operations.py`
Database-specific tests without external API calls:
- PostgreSQL CV operations (CRUD)
- PostgreSQL job operations (CRUD)
- User job matching
- Method parity checks (SQLite vs PostgreSQL)
- Data integrity validation

## Running Tests

### All Tests
```bash
pytest tests/ -v
```

### Specific Test File
```bash
pytest tests/test_database_operations.py -v
```

### Specific Test Class
```bash
pytest tests/test_full_workflow.py::TestWorkflowIntegration -v
```

### Specific Test
```bash
pytest tests/test_full_workflow.py::TestWorkflowIntegration::test_02_cv_upload -v
```

### With Output
```bash
pytest tests/ -v -s
```

### Skip API-dependent tests
```bash
pytest tests/ -v -m "not api"
```

## Cost-Effective Testing

The test suite is designed to minimize costs:

1. **Limited API Calls**: Job search limited to 1 query, 5 jobs
2. **Haiku Model**: Uses `claude-3-5-haiku-20241022` for cost efficiency
3. **Database Tests**: Most tests use only database operations
4. **Reusable Fixtures**: Users and CVs created once per test class

**Estimated Cost per Full Test Run**:
- JSearch API: ~1 call = minimal cost
- Anthropic API: ~5 analyses with Haiku = $0.01-0.02

## Requirements

```bash
pip install pytest pytest-cov
```

## Environment Variables

Required in `.env`:
```
DATABASE_URL=postgresql://...
ANTHROPIC_API_KEY=sk-ant-...
JSEARCH_API_KEY=...
```

## Test Coverage

Run with coverage report:
```bash
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

## Continuous Integration

Tests can be run in CI/CD pipelines. For cost control in CI:

```bash
# Skip expensive API tests
pytest tests/test_database_operations.py -v

# Or use environment flag
SKIP_API_TESTS=1 pytest tests/ -v
```

## Test Data Cleanup

Tests automatically clean up after themselves:
- Test users are archived (not deleted to preserve data integrity)
- Test CVs are set to 'archived' status
- Jobs remain in database for audit purposes

Manual cleanup if needed:
```bash
python scripts/cleanup_test_data.py
```
