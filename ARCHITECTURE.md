# Test Suite Architecture

## Overview

This test suite is designed to be **dynamic, flexible, and maintainable**. It supports:

- ✅ **Unit Tests**: Test individual functions in isolation
- ✅ **Integration Tests**: Test API endpoints and database interactions  
- ✅ **Regression Tests**: Ensure core functionality doesn't break
- ✅ **Environment Configuration**: Test local, staging, or production
- ✅ **Future React Frontend**: Easy to add React component tests later
- ✅ **Easy to Run**: Simple commands for different test scenarios

## Architecture

```
┌─────────────────────────────────────────────┐
│         Test Runner (run_tests.py)          │
│  • Easy CLI interface                        │
│  • Environment selection                     │
│  • Test type filtering                       │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│      Test Configuration (config.py)         │
│  • Environment handling                      │
│  • Database configuration                    │
│  • Feature flags                             │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│    Pytest Fixtures (conftest.py)            │
│  • Database sessions                         │
│  • Test client                               │
│  • Sample data fixtures                      │
│  • Authentication cookies                    │
└────────────────┬────────────────────────────┘
                 │
        ┌────────┴────────┬──────────────┐
        ▼                 ▼              ▼
    ┌────────┐     ┌────────────┐  ┌───────────┐
    │  Unit  │     │Integration │  │Regression │
    │ Tests  │     │   Tests    │  │  Tests    │
    └────────┘     └────────────┘  └───────────┘
        │                 │              │
        ▼                 ▼              ▼
    ┌────────────────────────────────────────┐
    │        Pytest Markers                   │
    │  @pytest.mark.unit                     │
    │  @pytest.mark.integration              │
    │  @pytest.mark.regression               │
    │  @pytest.mark.slow                     │
    │  @pytest.mark.ocr                      │
    │  @pytest.mark.cloudinary               │
    └────────────────────────────────────────┘
```

## Test Organization

### Unit Tests (`tests/unit/`)
**Purpose**: Test individual functions in isolation

**What's Tested**:
- Cookie signing/verification
- String formatting utilities (safe_public_id)
- Database model creation
- Environment configuration loading

**When to Add Tests**: When writing utility functions or business logic

**Example**:
```python
@pytest.mark.unit
class TestSafePublicId:
    def test_safe_public_id_basic(self):
        result = safe_public_id("Receipt", "2025-01-15")
        assert result == "Receipt_2025-01-15"
```

### Integration Tests (`tests/integration/`)
**Purpose**: Test API endpoints and database interactions

**What's Tested**:
- Health check endpoint
- UI endpoints
- OCR API endpoints
- User/Receipt CRUD operations
- Database relationships

**When to Add Tests**: When adding new API endpoints or database operations

**Example**:
```python
@pytest.mark.integration
class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
```

### Regression Tests (`tests/regression/`)
**Purpose**: Ensure core functionality doesn't break with new changes

**What's Tested**:
- Health endpoint always available
- User creation never fails
- Receipt creation never fails
- Authentication always works
- Data integrity constraints
- Configuration loading

**When to Add Tests**: When fixing bugs or making breaking changes

**Example**:
```python
@pytest.mark.regression
class TestCoreRegressions:
    def test_health_endpoint_never_fails(self, client):
        response = client.get("/health")
        assert response.status_code == 200
```

## Configuration System

### Environment Variables (`config.py`)

The test configuration system automatically loads and manages:

```python
# Environment selection
TEST_ENV=local|staging|production

# Database configuration
TEST_DB_TYPE=sqlite|postgresql
TEST_DATABASE_URL=...

# API configuration
TEST_API_URL=http://localhost:8000

# Feature flags
TEST_RUN_SLOW=true|false
TEST_RUN_OCR=true|false
TEST_USE_CLOUDINARY=true|false
```

### How It Works

1. `run_tests.py` parses CLI arguments (--local, --staging, --production)
2. Environment variables are set based on CLI args and `.env.test` file
3. `config.py` loads environment variables and creates `TestConfig` object
4. `conftest.py` uses `TestConfig` to set up fixtures
5. Tests access config via `test_config` fixture

## Fixtures

### Core Fixtures

**`test_config`**: Get test configuration
```python
def test_something(self, test_config):
    assert test_config.environment.value == "local"
```

**`db_session`**: Fresh database session for each test
```python
def test_create_user(self, db_session):
    user = User(username="test", email="test@example.com")
    db_session.add(user)
    db_session.commit()
```

**`client`**: Test API client with mocked database
```python
def test_endpoint(self, client):
    response = client.get("/health")
    assert response.status_code == 200
```

### Data Fixtures

**`sample_user`**: Pre-created test user
```python
def test_with_user(self, db_session, sample_user):
    assert sample_user.username == "testuser"
```

**`sample_receipt`**: Pre-created test receipt linked to sample_user
```python
def test_with_receipt(self, db_session, sample_receipt, sample_user):
    assert sample_receipt.user_id == sample_user.user_id
```

**`auth_cookies`**: Signed authentication cookies
```python
def test_auth(self, client, auth_cookies):
    response = client.get("/", cookies=auth_cookies)
    assert response.status_code == 200
```

## Usage Patterns

### Pattern 1: Quick Local Testing

Before committing:
```bash
python run_tests.py --regression --unit --integration
```

### Pattern 2: Focused Testing

While developing a feature:
```bash
# Run only related tests
python run_tests.py --integration -v

# Run specific test
pytest tests/integration/test_api.py::TestOCREndpoint -v
```

### Pattern 3: Remote Testing

Testing against staging before deploy:
```bash
# Set up staging environment
TEST_ENV=staging python run_tests.py --regression

# Or with custom config
python run_tests.py --staging --regression
```

### Pattern 4: CI/CD Integration

In your CI/CD pipeline:
```bash
python run_tests.py --coverage
```

## Future: React Frontend Integration

When adding React frontend, the architecture scales naturally:

```
tests/
├── backend/           # Existing tests
│   ├── unit/
│   ├── integration/
│   └── regression/
├── frontend/          # New React tests
│   ├── components/    # Jest + React Testing Library
│   ├── pages/
│   └── utils/
├── e2e/              # End-to-end tests
│   └── user_flows/   # Selenium/Playwright
└── conftest.py       # Shared configuration
```

### Adding React Component Tests

1. **Install test tools**:
   ```bash
   npm install --save-dev @testing-library/react @testing-library/jest-dom jest
   ```

2. **Create test files** in `tests/frontend/`:
   ```javascript
   // tests/frontend/components/ReceiptUpload.test.js
   import { render, screen } from '@testing-library/react';
   import ReceiptUpload from '../../../src/components/ReceiptUpload';
   
   test('renders upload button', () => {
     render(<ReceiptUpload />);
     expect(screen.getByRole('button')).toBeInTheDocument();
   });
   ```

3. **Run all tests**:
   ```bash
   # Backend tests
   python run_tests.py
   
   # Frontend tests
   npm test
   ```

## Key Features

### 1. Dynamic Configuration
- Load from environment variables
- Support local, staging, production
- Easy to switch between environments
- No hardcoded values

### 2. Flexible Execution
- Run all tests
- Run by type (unit/integration/regression)
- Skip slow tests by default
- Easy to include optional test suites

### 3. Easy to Understand
- Clear test names
- Well-organized directories
- Comprehensive fixtures
- Good documentation

### 4. Easy to Extend
- Add new test files to appropriate directory
- Use existing fixtures
- Follow naming conventions
- Add markers as needed

### 5. Future-Proof
- React frontend compatible
- Can add E2E tests
- Configurable for any environment
- Scales with application

## Best Practices

1. **Keep tests focused**: One assertion per test when possible
2. **Use fixtures**: Leverage provided fixtures for DRY code
3. **Descriptive names**: Test names should describe what's being tested
4. **Test edge cases**: Include tests for error conditions
5. **Keep tests fast**: Mock external services
6. **Isolate tests**: Each test should be independent
7. **Use markers**: Organize tests with appropriate markers

## Performance

- Unit tests: < 1 second
- Integration tests: < 5 seconds
- Regression tests: < 10 seconds
- All tests: ~20-30 seconds

## Debugging

```bash
# Verbose output
python run_tests.py -v

# Show print statements
python run_tests.py -s

# Stop on first failure
python run_tests.py -x

# Full traceback
python run_tests.py --tb=long

# Specific test with debugger
pytest tests/unit/test_core.py::TestClass::test_method --pdb
```

## Next Steps

1. ✅ Install test dependencies: `pip install -r requirements-test.txt`
2. ✅ Create `.env.test` from template: `cp .env.test.template .env.test`
3. ✅ Run tests: `python run_tests.py`
4. ✅ Check coverage: `python run_tests.py --coverage`
5. ✅ Read detailed docs: `tests/README.md`
6. ✅ Add tests for new features
7. ✅ Set up CI/CD integration
8. ✅ Add React frontend tests when ready

For more details, see:
- [TESTING.md](TESTING.md) - Quick start guide
- [tests/README.md](tests/README.md) - Comprehensive documentation
- [.env.test.template](.env.test.template) - Configuration template
