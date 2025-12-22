#!/bin/bash
# Run Job Monitor tests with cost-effective settings

echo "========================================"
echo "Job Monitor Test Suite"
echo "========================================"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "ERROR: pytest not found. Installing..."
    pip install pytest pytest-cov
fi

# Check environment variables
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL not set"
    exit 1
fi

echo "Running tests..."
echo ""

# Run database tests first (no API costs)
echo "1. Database Operations Tests (no API calls)"
echo "-------------------------------------------"
pytest tests/test_database_operations.py -v --tb=short
DB_EXIT=$?

echo ""
echo "2. Full Workflow Tests (LIMITED API calls)"
echo "-------------------------------------------"
echo "⚠️  This will make actual API calls (estimated cost: ~$0.02)"
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    pytest tests/test_full_workflow.py -v --tb=short -s
    WORKFLOW_EXIT=$?
else
    echo "Skipped workflow tests"
    WORKFLOW_EXIT=0
fi

echo ""
echo "========================================"
echo "Test Summary"
echo "========================================"

if [ $DB_EXIT -eq 0 ]; then
    echo "✓ Database tests: PASSED"
else
    echo "✗ Database tests: FAILED"
fi

if [ $WORKFLOW_EXIT -eq 0 ]; then
    echo "✓ Workflow tests: PASSED"
else
    echo "✗ Workflow tests: FAILED (or skipped)"
fi

echo ""

# Exit with error if any test failed
if [ $DB_EXIT -ne 0 ] || [ $WORKFLOW_EXIT -ne 0 ]; then
    exit 1
fi

exit 0
