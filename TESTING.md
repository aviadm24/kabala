# Quick Start Guide for Test Suite

## 1. Setup (One time)

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Copy and configure test environment
cp .env.test.template .env.test

# Edit .env.test if needed (optional for local testing)
```

## 2. Run Tests

```bash
# All tests (quick - skips slow/ocr tests)
python run_tests.py

# Unit tests only (fastest)
python run_tests.py --unit

# Integration tests (tests API endpoints)
python run_tests.py --integration

# Regression tests (checks for breaking changes)
python run_tests.py --regression

# Everything with verbose output
python run_tests.py -v

# With coverage report
python run_tests.py --coverage
```

## 3. Before Committing

Run this to check you haven't broken anything:
```bash
python run_tests.py --regression --unit --integration
```

## 4. Testing Different Environments

```bash
# Local (default)
python run_tests.py --local

# Staging
TEST_ENV=staging python run_tests.py

# Production (careful!)
TEST_ENV=production python run_tests.py --regression
```

## 5. Debugging Failures

```bash
# See what failed with verbose output
python run_tests.py -v

# See print statements
python run_tests.py -s

# Stop on first failure
python run_tests.py -x

# Only run a specific test
pytest tests/unit/test_core.py::TestSafePublicId::test_safe_public_id_basic

# Full traceback
python run_tests.py --tb=long
```

## 6. Coverage Report

```bash
# Generate and open coverage report
python run_tests.py --coverage
open htmlcov/index.html
```

## Common Issues

**"ModuleNotFoundError: No module named 'pytest'"**
```bash
pip install -r requirements-test.txt
```

**"Database locked" errors**
```bash
rm test.db
python run_tests.py
```

**"FAILED tests/... - AssertionError"**
```bash
# Run that specific test with verbose output
pytest tests/path/to/test.py::TestClass::test_name -vv
```

## Next Steps

- Read [tests/README.md](tests/README.md) for complete documentation
- Add more tests as you develop new features
- Set up CI/CD to run tests automatically
- Configure testing for staging/production environments
