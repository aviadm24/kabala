# 📋 Complete Test Suite - Setup & Usage Guide

## What You Got

A **production-ready, dynamic test suite** with:

✅ **Unit Tests** - Test individual functions  
✅ **Integration Tests** - Test API endpoints  
✅ **Regression Tests** - Catch breaking changes  
✅ **Easy Configuration** - Local/staging/production  
✅ **Future-Ready** - Works with React frontend  
✅ **Simple to Run** - Single command testing  

## 📂 File Structure

```
your-project/
├── tests/                          # All tests here
│   ├── __init__.py
│   ├── config.py                   # Configuration management
│   ├── conftest.py                 # Pytest setup & fixtures
│   ├── README.md                   # Full documentation
│   │
│   ├── unit/                       # Unit tests (fast)
│   │   ├── __init__.py
│   │   └── test_core.py            # Core functions
│   │
│   ├── integration/                # Integration tests
│   │   ├── __init__.py
│   │   └── test_api.py             # API endpoints
│   │
│   ├── regression/                 # Regression tests
│   │   ├── __init__.py
│   │   └── test_regressions.py     # Core features
│   │
│   └── fixtures/                   # Test data (future)
│
├── run_tests.py                    # Easy test runner
├── pytest.ini                      # Pytest configuration
├── requirements-test.txt           # Test dependencies
├── .env.test.template              # Configuration template
├── TESTING.md                      # Quick start guide
├── ARCHITECTURE.md                 # Architecture overview
└── Makefile                        # Make shortcuts (optional)
```

## 🚀 Quick Start (5 minutes)

### Step 1: Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### Step 2: Create Configuration (Optional)

```bash
# Copy template
cp .env.test.template .env.test

# Edit if needed (usually not necessary for local testing)
# nano .env.test
```

### Step 3: Run Tests

```bash
# Run all tests
python run_tests.py

# That's it! You should see results.
```

## 📊 Common Commands

| Command | Purpose | Speed |
|---------|---------|-------|
| `python run_tests.py` | All tests | ~30s |
| `python run_tests.py --unit` | Unit tests only | <1s |
| `python run_tests.py --integration` | API tests | ~5s |
| `python run_tests.py --regression` | Breaking changes | ~10s |
| `python run_tests.py --unit --integration` | Unit + Integration | ~5s |
| `python run_tests.py -v` | Verbose output | ~30s |
| `python run_tests.py --coverage` | Coverage report | ~35s |

## 🎯 Use Cases

### Before Committing

Ensure you haven't broken anything:

```bash
python run_tests.py --regression --unit --integration
```

✅ **Result**: Green means safe to commit!

### While Developing

Run only related tests:

```bash
# Test the API I'm working on
python run_tests.py --integration -v

# Or run one specific test
pytest tests/integration/test_api.py::TestHealthEndpoint -v
```

### Testing Against Staging

Before deploying to production:

```bash
python run_tests.py --staging --regression
```

### Quick Smoke Test

Ultra-fast sanity check:

```bash
python run_tests.py --unit
```

### Generate Coverage Report

See which code is tested:

```bash
python run_tests.py --coverage
open htmlcov/index.html
```

## 🔧 Advanced Configuration

### Testing Different Environments

Edit `.env.test`:

```bash
# Local (default)
TEST_ENV=local
TEST_API_URL=http://localhost:8000
TEST_DATABASE_URL=sqlite:///./test.db

# Staging
TEST_ENV=staging
TEST_API_URL=https://staging.example.com
TEST_DATABASE_URL=postgresql://user:pass@staging-db/test

# Production
TEST_ENV=production
TEST_API_URL=https://api.example.com
TEST_DATABASE_URL=postgresql://user:pass@prod-db/test
```

### Including Optional Tests

```bash
# Include slow tests
python run_tests.py --slow

# Include OCR tests
python run_tests.py --ocr

# Include all
python run_tests.py --slow --ocr
```

### Custom pytest Arguments

```bash
# Pass any pytest argument
python run_tests.py --unit -s -v

# Stop on first failure
python run_tests.py -x

# Run specific test
pytest tests/unit/test_core.py::TestClass::test_method
```

## 📈 Test Organization

### Unit Tests (Speed: <1 second)
Testing individual functions:
- Cookie signing ✓
- String formatting ✓
- Database models ✓
- Configuration ✓

**Add tests here for**: Utility functions, business logic

### Integration Tests (Speed: ~5 seconds)
Testing API endpoints and database:
- Health check endpoint ✓
- UI endpoints ✓
- OCR endpoints ✓
- Database CRUD operations ✓

**Add tests here for**: New API endpoints, database operations

### Regression Tests (Speed: ~10 seconds)
Ensuring nothing breaks:
- Health always available ✓
- User creation never fails ✓
- Receipt creation never fails ✓
- Authentication always works ✓
- Data integrity ✓

**Add tests here for**: Bug fixes, critical paths

## 🔍 Debugging

### Test Failed? Here's How to Debug

```bash
# See what failed with details
python run_tests.py -v

# See print statements in tests
python run_tests.py -s

# See full traceback
python run_tests.py --tb=long

# Stop on first failure
python run_tests.py -x

# Run specific failing test
pytest tests/unit/test_core.py::TestClass::test_name --pdb
```

### Common Issues

**"ModuleNotFoundError: No module named pytest"**
```bash
pip install -r requirements-test.txt
```

**"Database locked"**
```bash
rm test.db
python run_tests.py
```

**"Connection refused"**
```bash
# Make sure app is running
python -m uvicorn main:app --reload
```

## 🎨 With Make (Optional)

Use convenient Make shortcuts:

```bash
make test              # Default tests
make test-unit         # Unit only
make test-integration  # Integration only
make test-regression   # Regression only
make test-coverage     # With coverage
make test-verbose      # Verbose output
make clean             # Clean up test files
```

## 🚀 Future: React Frontend

When you add React, just create:

```
tests/
├── backend/           # Existing tests (unchanged)
│   ├── unit/
│   ├── integration/
│   └── regression/
├── frontend/          # New React tests
│   ├── components/
│   └── pages/
└── e2e/              # End-to-end tests
```

No restructuring needed! The configuration system is ready.

## 📚 Documentation

- **[tests/README.md](tests/README.md)** - Complete testing guide (70+ pages)
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical architecture
- **[TESTING.md](TESTING.md)** - Quick reference
- **[.env.test.template](.env.test.template)** - Configuration options

## ✨ Key Features

### 1. Easy to Run
```bash
python run_tests.py
```
That's it. No complex setup.

### 2. Easy to Configure
- Environment variables
- `.env.test` file
- CLI arguments
- All optional for local testing

### 3. Easy to Extend
Add new tests:
```python
# In tests/unit/, tests/integration/, or tests/regression/

@pytest.mark.unit
def test_my_feature():
    # Your test here
    assert True
```

### 4. Easy to Debug
```bash
python run_tests.py -v -s --tb=long
```

### 5. Future-Proof
- React frontend ready
- E2E test support
- CI/CD integration
- Multiple environment support

## 📞 Help

**Quick questions?** Check [TESTING.md](TESTING.md)

**Need details?** Read [tests/README.md](tests/README.md)

**Architecture questions?** See [ARCHITECTURE.md](ARCHITECTURE.md)

## ✅ You're Ready!

1. ✅ Installed pytest
2. ✅ Created test suite
3. ✅ Ready to run tests

**Try it now:**
```bash
python run_tests.py
```

See green checkmarks? Congratulations! Your test suite is working. 🎉

---

**Pro Tips:**
- Run `python run_tests.py --regression` before every commit
- Use `python run_tests.py --unit` for quick feedback while coding
- Run `python run_tests.py --coverage` to see test coverage
- Add tests when you find bugs (test-driven debugging)
