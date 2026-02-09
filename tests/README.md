# Test Suite Documentation

This directory contains a comprehensive, dynamic test suite for the Receipt Uploader application. It's designed to be:

- **Dynamic**: Works with future React frontend without changes
- **Flexible**: Easy to configure for local, staging, and production testing
- **Organized**: Separated into unit, integration, and regression tests
- **Easy to Use**: Simple commands to run tests and check for regressions

## Directory Structure

```
tests/
├── __init__.py              # Tests package marker
├── config.py                # Test configuration management
├── conftest.py              # Pytest fixtures and configuration
├── unit/                    # Unit tests
│   ├── __init__.py
│   └── test_core.py         # Core function tests
├── integration/             # Integration tests
│   ├── __init__.py
│   └── test_api.py          # API endpoint tests
├── regression/              # Regression tests
│   ├── __init__.py
│   └── test_regressions.py  # Regression test suite
└── fixtures/                # Test data and fixtures (for future use)
```

## Quick Start

### Installation

1. Install test dependencies:
   ```bash
   pip install pytest pytest-cov pytest-timeout httpx
   ```

2. (Optional) Install coverage tools:
   ```bash
   pip install coverage pytest-cov
   ```

### Running Tests

#### Simple Usage

Run all tests:
```bash
python run_tests.py
```

Run only unit tests:
```bash
python run_tests.py --unit
```

Run only integration tests:
```bash
python run_tests.py --integration
```

Run only regression tests (checks for breaking changes):
```bash
python run_tests.py --regression
```

#### With Options

Include slow tests:
```bash
python run_tests.py --slow
```

Include OCR tests (requires proper setup):
```bash
python run_tests.py --ocr
```

Include Cloudinary tests:
```bash
python run_tests.py --cloudinary
```

Verbose output:
```bash
python run_tests.py -v
```

Generate coverage report:
```bash
python run_tests.py --coverage
```

#### Environment Configuration

Test against different environments:

```bash
# Local (default)
python run_tests.py --local --unit

# Staging
python run_tests.py --staging --regression

# Production (be careful!)
python run_tests.py --production --regression
```

#### Combined Examples

Run unit and integration tests with verbose output:
```bash
python run_tests.py --unit --integration -v
```

Run all tests including slow and OCR tests against staging:
```bash
python run_tests.py --staging --slow --ocr
```

Generate coverage report for regression tests:
```bash
python run_tests.py --regression --coverage
```

### Direct Pytest Usage

You can also run pytest directly:

```bash
# Run all tests
pytest tests

# Run specific test file
pytest tests/unit/test_core.py

# Run specific test class
pytest tests/unit/test_core.py::TestSafePublicId

# Run specific test
pytest tests/unit/test_core.py::TestSafePublicId::test_safe_public_id_basic

# With markers
pytest -m unit
pytest -m "unit or integration"
pytest -m "regression and not slow"

# With verbose and warnings
pytest -vv --tb=long

# Stop on first failure
pytest -x

# Show print statements
pytest -s
```

## Configuration

### Environment Variables

Create a `.env.test` file in the project root to configure test behavior:

```bash
# Test environment: local, staging, production
TEST_ENV=local

# Database configuration
TEST_DB_TYPE=sqlite  # or postgresql
TEST_DATABASE_URL=sqlite:///./test.db

# API configuration
TEST_API_URL=http://localhost:8000

# Feature flags
TEST_RUN_SLOW=false              # Run slow tests
TEST_RUN_OCR=false               # Run OCR tests
TEST_USE_CLOUDINARY=false        # Use Cloudinary
TEST_LOG_LEVEL=INFO

# Cloudinary (if needed)
CLOUDINARY_URL=cloudinary://...
```

### Remote Testing

For testing against staging or production:

```bash
# .env.test (staging)
TEST_ENV=staging
TEST_API_URL=https://staging-api.example.com
TEST_DATABASE_URL=postgresql://user:pass@staging-db.example.com/kabala_test

# .env.test (production)
TEST_ENV=production
TEST_API_URL=https://api.example.com
TEST_DATABASE_URL=postgresql://user:pass@prod-db.example.com/kabala_test
```

## Test Categories

### Unit Tests (`tests/unit/`)
Test individual functions in isolation:
- Cookie signing/verification
- String formatting utilities
- Database model creation
- Configuration loading

**Run with:** `python run_tests.py --unit`

### Integration Tests (`tests/integration/`)
Test API endpoints and database interactions:
- Health check endpoint
- UI endpoints
- OCR endpoints
- Database CRUD operations

**Run with:** `python run_tests.py --integration`

### Regression Tests (`tests/regression/`)
Ensure core functionality doesn't break:
- Health endpoint reliability
- User/Receipt creation
- Authentication
- Data integrity
- Configuration handling

**Run with:** `python run_tests.py --regression`

## Markers

Tests can be marked with markers for selective execution:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.regression` - Regression tests
- `@pytest.mark.slow` - Slow tests (skipped by default)
- `@pytest.mark.ocr` - OCR-related tests (skipped by default)
- `@pytest.mark.cloudinary` - Cloudinary-related tests (skipped if disabled)
- `@pytest.mark.production` - Production-only tests

## Fixtures

The test suite provides several useful fixtures:

```python
@pytest.fixture
def db_session:
    """Fresh database session for each test."""
    
@pytest.fixture
def client:
    """Test client with mocked dependencies."""
    
@pytest.fixture
def sample_user:
    """Sample user created in test database."""
    
@pytest.fixture
def sample_receipt:
    """Sample receipt linked to sample_user."""
    
@pytest.fixture
def auth_cookies:
    """Signed authentication cookies."""
    
@pytest.fixture
def test_config:
    """Test configuration object."""
```

## Future: React Frontend Testing

The test suite is designed to work with a future React frontend:

1. **Separate Frontend Tests**: Add `tests/frontend/` directory for React component tests
2. **E2E Tests**: Add `tests/e2e/` for end-to-end testing with Selenium/Playwright
3. **API Tests**: Existing integration tests remain unchanged
4. **Shared Fixtures**: `conftest.py` provides shared fixtures for all test types

Example structure after React addition:
```
tests/
├── backend/
│   ├── unit/
│   ├── integration/
│   └── regression/
├── frontend/
│   ├── components/
│   ├── pages/
│   └── utils/
├── e2e/
│   └── user_flows/
└── conftest.py
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.10
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests
        run: python run_tests.py --coverage
      
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

### Pre-commit Hook

Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
python run_tests.py --regression --unit --integration || exit 1
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

## Debugging Tests

### Verbose Output
```bash
pytest -vv tests/unit/test_core.py
```

### Show Print Statements
```bash
pytest -s tests/unit/test_core.py
```

### Stop on First Failure
```bash
pytest -x tests/
```

### Show Local Variables on Failure
```bash
pytest -l tests/
```

### Run with Debugger
```bash
pytest --pdb tests/unit/test_core.py
```

### Full Traceback
```bash
pytest --tb=long tests/
```

## Adding New Tests

### 1. Choose Test Type
- **Unit**: Individual function - add to `tests/unit/test_*.py`
- **Integration**: API/Database - add to `tests/integration/test_*.py`
- **Regression**: Breaking changes - add to `tests/regression/test_*.py`

### 2. Create Test File
```python
import pytest

@pytest.mark.unit  # or integration/regression
class TestMyFeature:
    """Test my feature."""
    
    def test_something(self, db_session, client):
        """Test something."""
        # Arrange
        expected = "expected_value"
        
        # Act
        result = my_function()
        
        # Assert
        assert result == expected
```

### 3. Run New Test
```bash
python run_tests.py --unit -v
```

## Best Practices

1. **Arrange-Act-Assert**: Structure tests with clear sections
2. **One assertion per test**: When possible, keep tests focused
3. **Use fixtures**: Leverage provided fixtures for DRY code
4. **Descriptive names**: Use clear test names that describe what's being tested
5. **Test edge cases**: Include tests for error conditions and edge cases
6. **Keep tests fast**: Use mocks for external services
7. **Isolate tests**: Each test should be independent
8. **Document complex tests**: Add comments for non-obvious test logic

## Troubleshooting

### Tests fail with "module not found"
```bash
# Ensure venv is activated
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov
```

### Database errors
```bash
# Reset test database
rm test.db

# Run tests again
python run_tests.py --unit
```

### Cloudinary tests failing
```bash
# Run without Cloudinary tests
python run_tests.py --unit --integration
```

### Fixture not found
Ensure `conftest.py` is in the `tests/` directory and fixtures are defined.

## Coverage Reports

Generate and view coverage:

```bash
# Generate HTML coverage report
python run_tests.py --coverage

# Open the report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## Performance

- **Unit tests**: < 1 second
- **Integration tests**: < 5 seconds
- **Regression tests**: < 10 seconds
- **All tests**: ~20-30 seconds

To speed up test runs:
- Skip slow tests: default behavior
- Skip OCR tests: default behavior
- Use `pytest -x` to stop on first failure
- Run specific test file: `pytest tests/unit/test_core.py`

## Support

For issues or improvements:
1. Check existing tests for patterns
2. Review conftest.py for available fixtures
3. Check test configuration in config.py
4. Refer to pytest documentation: https://docs.pytest.org/
