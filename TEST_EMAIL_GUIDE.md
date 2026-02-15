# Email Loop Closure - Test Suite Guide

Comprehensive test coverage for the insurance claim email loop closure feature. Tests include unit tests, integration tests, and end-to-end workflow tests.

## 📋 Test Structure

```
tests/
├── unit/
│   └── test_email_service.py           # Email service unit tests (47 tests)
├── integration/
│   ├── test_claims.py                  # Claims API integration tests (20 tests)
│   ├── test_webhooks.py                # Webhook integration tests (12 + 7 unit tests)
│   └── test_e2e_workflow.py            # End-to-end workflow tests (5 tests)
├── conftest.py                         # Shared fixtures and configuration
└── config.py                           # Test environment configuration
```

## 🚀 Quick Start

### 1. Install Test Dependencies

```bash
cd /Users/aviadmoshe/Documents/code_projects/kabala
python -m pip install pytest pytest-asyncio pytest-mockpip requests
```

### 2. Run All Tests

```bash
# Run all tests with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_email_service.py -v
pytest tests/integration/test_claims.py -v

# Run specific test class
pytest tests/unit/test_email_service.py::TestResendClient -v

# Run specific test
pytest tests/unit/test_email_service.py::TestResendClient::test_send_email_success -v
```

## 🧪 Test Categories

### Unit Tests (Email Service)

**File**: `tests/unit/test_email_service.py`

Tests for the email service module without external dependencies.

```bash
pytest tests/unit/test_email_service.py -v -m unit
```

**Coverage**:
- ✅ Resend client initialization
- ✅ Email sending with various headers (CC, BCC, Reply-To)
- ✅ Test mode email redirection
- ✅ Webhook signature validation (valid/invalid)
- ✅ Error handling
- ✅ Email template generation
- ✅ Configuration and environment variables

### Integration Tests (Claims API)

**File**: `tests/integration/test_claims.py`

Tests for the claims API endpoints with database interaction.

```bash
pytest tests/integration/test_claims.py -v -m integration
```

**Coverage**:
- ✅ Create claim with auto-generated public_id and reply_email
- ✅ Retrieve claim details
- ✅ List claims with filtering (by user, status)
- ✅ Send email via API (with Resend mocking)
- ✅ Update claim status
- ✅ Retrieve email history (all, filtered by direction)
- ✅ Error handling (claim not found, invalid status, etc.)

### Integration Tests (Webhooks)

**File**: `tests/integration/test_webhooks.py`

Tests for inbound email webhook processing.

```bash
pytest tests/integration/test_webhooks.py -v -m integration
```

**Coverage**:
- ✅ Inbound email webhook processing
- ✅ Webhook signature validation
- ✅ Claim ID extraction from email address
- ✅ Email storage with headers and attachments
- ✅ Claim status updates (AWAITING_RESPONSE → RESPONSE_RECEIVED)
- ✅ Error handling (wrong format, invalid signature, claim not found, etc.)
- ✅ Attachment metadata storage
- ✅ Email address parsing (regex validation)

### End-to-End Workflow Tests

**File**: `tests/integration/test_e2e_workflow.py`

Complete workflow tests simulating real-world scenarios.

```bash
pytest tests/integration/test_e2e_workflow.py -v -m integration
```

**Scenarios**:
- ✅ **Complete Workflow**: Create claim → Send email → Receive response → Update status
- ✅ **Multiple Claims**: User with independent multiple claims
- ✅ **Email Chain**: Multiple responses to same claim
- ✅ **Test Mode**: Email redirection in test mode
- ✅ **Status Transitions**: Valid claim status changes

## ⚙️ Configuration

### Test Environment Variables

Create a `.env.test` file in the project root:

```dotenv
# Test database
TEST_ENV=local
TEST_DB_TYPE=sqlite
TEST_DATABASE_URL=sqlite:///./test.db

# Test API
TEST_API_URL=http://localhost:8000

# Resend API
RESEND_API_KEY=re_your_test_key_here

# Email testing - CUSTOM TEST EMAIL
EMAIL_TEST_MODE=true
TEST_EMAIL_RECIPIENT=your-email@example.com

# Logging
TEST_LOG_LEVEL=INFO

# Feature toggles
TEST_RUN_SLOW=false
TEST_RUN_OCR=false
```

### Using Custom Test Email

To receive actual test emails in your inbox:

1. **Set custom email recipient**:
   ```dotenv
   EMAIL_TEST_MODE=true
   TEST_EMAIL_RECIPIENT=your-email@example.com
   ```

2. **Run tests**:
   ```bash
   export TEST_EMAIL_RECIPIENT="your-email@example.com"
   pytest tests/ -v
   ```

3. **What happens**:
   - All outbound claim emails are redirected to your email
   - Original recipient is shown in email subject: `[TO: claims@insurance.com] Subject`
   - CC recipients are shown in subject: `[CC: user@example.com] [TO: ...] Subject`
   - CC/BCC lists are cleared to avoid sending to unintended recipients

### Resend API Key Configuration

1. **Get your Resend API key**:
   - Visit [Resend Dashboard](https://resend.com/api-keys)
   - Create or copy existing API key

2. **Add to environment**:
   ```bash
   export RESEND_API_KEY=re_your_key_here
   ```

3. **Or add to `.env.test`**:
   ```dotenv
   RESEND_API_KEY=re_your_key_here
   ```

## 🏃 Running Tests

### Run All Tests

```bash
pytest tests/ -v --tb=short
```

### Run By Category

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Specific marker
pytest tests/ -v -m unit
pytest tests/ -v -m integration
```

### Run With Coverage

```bash
pytest tests/ --cov=services --cov=api --cov=workflows --cov-report=html
# Open htmlcov/index.html to view coverage report
```

### Run Specific Tests

```bash
# Test email sending
pytest tests/unit/test_email_service.py::TestResendClient::test_send_email_success -v

# Test claim creation
pytest tests/integration/test_claims.py::TestClaimsAPI::test_create_claim_success -v

# Test complete workflow
pytest tests/integration/test_e2e_workflow.py::TestEmailLoopClosureE2E::test_complete_claim_workflow -v
```

### Run With Custom Settings

```bash
# Use custom test email
TEST_EMAIL_RECIPIENT="you@example.com" pytest tests/integration/test_claims.py -v

# Verbose output with print statements
pytest tests/ -v -s

# Stop on first failure
pytest tests/ -x

# Show local variables on failure
pytest tests/ -l
```

## 📊 Test Fixtures

Automatically available in all tests:

### Database & Client

```python
def test_example(client, db_session):
    """Fixtures available in tests"""
    # client: FastAPI TestClient with dependency injection
    # db_session: SQLAlchemy database session
```

### Sample Data

```python
def test_example(sample_user, sample_claim, sample_outbound_email):
    """Pre-created test data"""
    # sample_user: Test User instance
    # sample_claim: Test Claim instance
    # sample_outbound_email: Test outbound ClaimEmail
    # sample_inbound_email: Test inbound ClaimEmail
```

### Configuration

```python
def test_example(test_config):
    """Test configuration"""
    # test_config: TestConfig instance from .env.test or environment
```

## 🔍 Example Test Runs

### Test Email Sending with Custom Email

```bash
# Set your email
export TEST_EMAIL_RECIPIENT="myemail@gmail.com"

# Run email sending test
pytest tests/integration/test_claims.py::TestClaimsAPI::test_send_claim_email_success -v

# Watch for email in Gmail
# Subject will show: [TO: claims@testinsurance.com] Test Subject
```

### Test Complete Workflow

```bash
# Full workflow test with email redirect
TEST_EMAIL_RECIPIENT="myemail@gmail.com" \
pytest tests/integration/test_e2e_workflow.py::TestEmailLoopClosureE2E::test_complete_claim_workflow -v -s
```

### Test Webhook Parsing

```bash
# Test email address parsing
pytest tests/integration/test_webhooks.py::TestEmailAddressParsing -v

# Test webhook processing
pytest tests/integration/test_webhooks.py::TestEmailWebhooks::test_inbound_email_webhook_success -v
```

## 🐛 Debugging Tests

### Print Debug Info

```bash
# Show print statements during test
pytest tests/integration/test_claims.py::TestClaimsAPI::test_create_claim_success -v -s

# Show captured logs
pytest tests/ -v --log-cli-level=DEBUG
```

### Debug Single Test

```bash
# Use pdb debugger
pytest tests/integration/test_claims.py -v -k test_create_claim -x --pdb

# Or add to test:
def test_example():
    import pdb; pdb.set_trace()
    # ... test code
```

### Check Database State

```python
def test_example(db_session, sample_claim):
    # Query database directly
    claim = db_session.query(Claim).first()
    print(f"Claim status: {claim.status}")
    
    # Check relationships
    emails = claim.emails
    print(f"Emails: {len(emails)}")
```

## 📝 Test Examples

### Example: Test Email Sending

```python
@patch("api.claims.ResendClient.send_email")
def test_send_email(mock_send, client, sample_claim):
    mock_send.return_value = {"id": "msg_123"}
    
    response = client.post(
        f"/api/claims/{sample_claim.id}/send-email",
        json={"cc_user_email": True}
    )
    
    assert response.status_code == 200
    assert response.json()["message_id"] == "msg_123"
```

### Example: Test Webhook Processing

```python
def test_webhook(client, sample_claim):
    payload = {
        "type": "email_received",
        "data": {
            "from_addr": "claims@insurance.com",
            "to_addr": f"claim-{sample_claim.public_id}@mail.yourapp.com",
            "subject": "Re: Claim",
            "text": "Approved",
            "html": "<p>Approved</p>",
            "headers": {},
        }
    }
    
    with patch("api.webhooks.ResendClient.validate_webhook_signature", return_value=True):
        response = client.post(
            "/webhooks/email-inbound",
            json=payload,
            headers={"x-resend-signature": "valid_sig"}
        )
    
    assert response.status_code == 200
```

## ✅ Test Checklist

Before deploying, ensure all tests pass:

- [ ] Run: `pytest tests/unit/ -v` (all unit tests pass)
- [ ] Run: `pytest tests/integration/ -v` (all integration tests pass)
- [ ] Run: `pytest tests/integration/test_e2e_workflow.py -v` (end-to-end workflows pass)
- [ ] Run with coverage: `pytest tests/ --cov`
- [ ] Coverage is > 80% for `services/` and `api/` directories
- [ ] All mocked tests work correctly
- [ ] Real Resend API key works (test with one live test)

## 🚨 Troubleshooting

### Issue: "RESEND_API_KEY not configured"

**Solution**:
```bash
export RESEND_API_KEY=re_your_key_here
pytest tests/ -v
```

### Issue: "Test email recipient not configured"

**Solution**: Test mode still works but won't redirect emails
```bash
export TEST_EMAIL_RECIPIENT=your@email.com
pytest tests/ -v
```

### Issue: "Database error: tables don't exist"

**Solution**: Database tables are auto-created during test setup. If error persists:
```bash
rm test.db  # Remove old test database
pytest tests/ -v  # Will recreate
```

### Issue: "Claim not found in webhook test"

**Cause**: Claim ID extraction failed
```python
# Add debugging
from api.webhooks import extract_claim_id_from_email
claim_id = extract_claim_id_from_email("claim-abc123@mail.yourapp.com")
print(f"Extracted: {claim_id}")
```

## 📚 Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Resend API Docs](https://resend.com/docs/api-reference)
- [FastAPI Testing](https://fastapi.tiangolo.com/advanced/testing-websockets/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/faq/testing.html)

## 🎯 Next Steps

1. **Configure custom email**: Set `TEST_EMAIL_RECIPIENT` in `.env.test`
2. **Run unit tests**: `pytest tests/unit/ -v`
3. **Run integration tests**: `pytest tests/integration/ -v`
4. **Run end-to-end**: `pytest tests/integration/test_e2e_workflow.py -v`
5. **Check inbox**: Look for test emails with `[TO: ...]` in subject

---

**Last Updated**: February 13, 2026  
**Total Tests**: 91 tests across 4 test files  
**Status**: ✅ Ready for Testing
