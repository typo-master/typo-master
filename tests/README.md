# Typo Master Backend Testing Framework

This testing framework provides comprehensive coverage for the Typo Master backend API, including unit tests, regression tests, and security tests.

## Quick Start

```bash
# Run all tests
python run_tests.py all

# Run specific test categories
python run_tests.py unit
python run_tests.py regression
python run_tests.py security

# Run with coverage and HTML report
python run_tests.py all --coverage --html-report

# Run in parallel
python run_tests.py all --parallel
```

## Test Categories

### Unit Tests (`tests/unit/`)

Fast, isolated tests that validate individual components:

- `test_storage.py` - MySQLStorage unit tests
- `test_main_api.py` - FastAPI endpoint tests

Run with: `python run_tests.py unit`

### Regression Tests (`tests/regression/`)

Tests that ensure API contracts remain stable:

- `test_api_contracts.py` - API response structure validation
- `test_critical_workflows.py` - End-to-end workflow tests
- `test_database_schema.py` - Database compatibility tests

Run with: `python run_tests.py regression`

### Security Tests (`tests/security/`)

Tests for security vulnerabilities:

- `test_sql_injection.py` - SQL injection tests
- `test_input_validation.py` - Input validation tests
- `test_authz.py` - Authorization tests
- `test_data_exposure.py` - Data exposure tests
- `test_security_headers.py` - Security headers tests

Run with: `python run_tests.py security`

## Directory Structure

```
tests/
├── conftest.py              # Root pytest configuration
├── README.md                # This file
├── unit/                    # Unit tests
│   ├── conftest.py
│   ├── base_test.py
│   ├── test_storage.py
│   ├── test_main_api.py
│   └── utils/
│       └── mocks.py
├── regression/              # Regression tests
│   ├── conftest.py
│   ├── test_api_contracts.py
│   ├── test_critical_workflows.py
│   ├── test_database_schema.py
│   ├── baselines/           # Expected response baselines
│   └── utils/
│       ├── snapshot.py
│       └── comparator.py
├── security/                # Security tests
│   ├── conftest.py
│   ├── test_sql_injection.py
│   ├── test_input_validation.py
│   ├── test_authz.py
│   ├── test_data_exposure.py
│   ├── test_security_headers.py
│   └── scanners/
│       └── injection.py
├── runners/                 # Test orchestration
│   ├── orchestrator.py
│   └── reporter.py
├── scripts/                 # Helper scripts
│   ├── setup_test_env.sh
│   └── cleanup_test_env.sh
└── reports/                 # Test reports (generated)
    ├── htmlcov/
    ├── junit.xml
    └── coverage.xml
```

## Configuration

### pytest.ini

Test markers and configuration are defined in `pytest.ini`:

- `unit` - Unit tests
- `regression` - Regression tests
- `security` - Security tests
- `critical` - Critical tests (must pass)
- `slow` - Slow tests (may be skipped)
- `integration` - Integration tests

### Environment Variables

Some tests require environment variables:

```bash
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=password
export MYSQL_DATABASE=typomaster_test
```

## Running Tests

### Run all tests

```bash
python run_tests.py all
```

### Run with options

```bash
# With coverage
python run_tests.py unit --coverage

# With HTML report
python run_tests.py all --html-report

# Parallel execution
python run_tests.py all --parallel

# Fail fast (stop on first failure)
python run_tests.py all --fail-fast

# Verbose output
python run_tests.py all --verbose

# Combined
python run_tests.py all --parallel --coverage --html-report
```

### Run specific test files

```bash
pytest tests/unit/test_storage.py -v
pytest tests/security/test_sql_injection.py -v
pytest tests/regression/test_api_contracts.py -v
```

### Run by marker

```bash
pytest -m unit
pytest -m regression
pytest -m security
pytest -m critical
pytest -m "not slow"
```

## CI/CD Integration

GitHub Actions workflow is configured in `.github/workflows/regression-tests.yml`:

- Runs on push to main/develop
- Runs on pull requests
- Runs daily at 2 AM UTC
- Tests on Python 3.10, 3.11, 3.12
- Includes security scanning with Bandit

## Adding New Tests

### Unit Tests

1. Create test file in `tests/unit/`
2. Import from `base_test.py` if needed
3. Use markers: `@pytest.mark.unit`
4. Mock external dependencies

Example:

```python
import pytest
from tests.unit.base_test import BaseUnitTest

@pytest.mark.unit
class TestNewFeature(BaseUnitTest):
    def test_something(self):
        # Test code
        pass
```

### Regression Tests

1. Create test file in `tests/regression/`
2. Use markers: `@pytest.mark.regression`
3. May include `@pytest.mark.critical` for critical paths
4. Focus on API contract stability

### Security Tests

1. Create test file in `tests/security/`
2. Use markers: `@pytest.mark.security`
3. Test both positive and negative cases
4. Document security implications

## Baseline Management

Regression tests compare responses against baselines:

```python
# To update baselines after intentional changes:
# 1. Run tests with --snapshot-update (if implemented)
# 2. Or manually update files in tests/regression/baselines/
```

## Troubleshooting

### Tests fail due to missing database

Some tests require a MySQL database. Set environment variables or skip database tests:

```bash
pytest -m "not database"
```

### Permission errors

Ensure scripts are executable:

```bash
chmod +x tests/scripts/*.sh
```

### Import errors

Ensure you're running from the project root:

```bash
cd /Users/cc11001100/github/typo-master/typo-master
python run_tests.py unit
```

## Contributing

When adding new features:

1. Add unit tests for new code
2. Add regression tests if API changes
3. Add security tests for security-sensitive code
4. Update baselines if API contracts change intentionally
5. Ensure all critical tests pass
