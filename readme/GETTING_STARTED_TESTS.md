# 🚀 Email Testing - Quick Start Checklist

Complete this checklist to start testing the email loop closure feature.

## ✅ Phase 1: Setup (5 minutes)

- [ ] **Get Resend API Key**
  - Go to: https://resend.com/api-keys
  - Create new key or copy existing
  - Copy the key (starts with `re_`)

- [ ] **Prepare Your Email**
  - Use an email you can access (Gmail, etc.)
  - You'll receive test emails here
  - Example: `your-email@gmail.com`

- [ ] **Create Test Configuration**
  ```bash
  cp .env.test.example .env.test
  ```

- [ ] **Edit .env.test**
  ```bash
  nano .env.test  # or open in VS Code
  ```
  
  Update these fields:
  ```dotenv
  RESEND_API_KEY=re_your_actual_key_here
  TEST_EMAIL_RECIPIENT=your-email@gmail.com
  EMAIL_TEST_MODE=true
  ```

- [ ] **Save and Close**

## ✅ Phase 2: Verify Installation (5 minutes)

- [ ] **Install Test Dependencies**
  ```bash
  pip install pytest pytest-asyncio requests
  ```

- [ ] **Verify Pytest Works**
  ```bash
  pytest --version
  ```
  
  Should output: `pytest X.X.X ...`

- [ ] **Check Configuration Loaded**
  ```bash
  python -c "from tests.config import get_config; c = get_config(); print(c)"
  ```
  
  Should show your config with email settings

## ✅ Phase 3: Run Basic Test (2 minutes)

- [ ] **Run Simple Unit Test**
  ```bash
  pytest tests/unit/test_email_service.py::TestResendClient::test_client_initialization -v
  ```
  
  Should pass ✓

- [ ] **Run Claim Creation Test**
  ```bash
  pytest tests/integration/test_claims.py::TestClaimsAPI::test_create_claim_success -v
  ```
  
  Should pass ✓

## ✅ Phase 4: Test Email Sending (5 minutes)

- [ ] **Run Email Sending Test**
  ```bash
  pytest tests/integration/test_claims.py::TestClaimsAPI::test_send_claim_email_success -v
  ```

- [ ] **Check Your Email Inbox**
  - Look for email from: `onboarding@resend.dev`
  - Subject should be: `[TO: claims@testinsurance.com] [CC: ...] Test Subject`
  - This means test mode is redirecting correctly!

## ✅ Phase 5: Run All Tests (3 minutes)

Choose one method:

### Method A: Using Test Runner Script
```bash
./run_email_tests.sh all
```

### Method B: Using Pytest
```bash
pytest tests/ -v --tb=short
```

### Method C: By Category
```bash
pytest tests/unit/ -v                    # Unit tests only
pytest tests/integration/test_claims.py  # Claims API only
pytest tests/integration/test_webhooks.py # Webhooks only
pytest tests/integration/test_e2e_workflow.py # End-to-end only
```

Expected output:
```
tests/unit/test_email_service.py::... PASSED
tests/integration/test_claims.py::... PASSED
tests/integration/test_webhooks.py::... PASSED
tests/integration/test_e2e_workflow.py::... PASSED

======================== 91 passed in 12.34s ========================
```

## ✅ Phase 6: Verify Email Loop (5 minutes)

- [ ] **Run End-to-End Test**
  ```bash
  pytest tests/integration/test_e2e_workflow.py::TestEmailLoopClosureE2E::test_complete_claim_workflow -v -s
  ```

- [ ] **Check Inbox Again**
  - Should receive another test email
  - Subject shows original recipient details
  - Proves the complete loop works!

## ✅ Phase 7: Run with Coverage (2 minutes)

- [ ] **Generate Coverage Report**
  ```bash
  pytest tests/ --cov=services --cov=api --cov=workflows --cov-report=html
  ```

- [ ] **View Coverage Report**
  ```bash
  open htmlcov/index.html  # macOS
  # or
  xdg-open htmlcov/index.html  # Linux
  # or
  start htmlcov/index.html  # Windows
  ```

- [ ] **Check Coverage Targets**
  - services/email_service.py: > 90%
  - api/claims.py: > 85%
  - api/webhooks.py: > 85%

## 🎯 Success Indicators

✅ **All tests pass**
```
======================== 91 passed in ~12s ========================
```

✅ **Email received in inbox**
- From: `onboarding@resend.dev`
- Subject: `[TO: claims@...] Claim...`

✅ **High coverage**
- services/: > 95%
- api/: > 88%
- workflows/: > 80%

## 🔧 Troubleshooting

### Issue: "RESEND_API_KEY not configured"

**Solution**:
```bash
# Edit .env.test and add:
RESEND_API_KEY=re_your_key_here

# Or set environment variable:
export RESEND_API_KEY=re_your_key_here
pytest tests/ -v
```

### Issue: "No emails received in inbox"

**Possible causes**:
1. TEST_EMAIL_RECIPIENT not set correctly
2. Check spam folder
3. Email might be delayed (up to 2 minutes)

**Solution**:
```bash
# Verify TEST_EMAIL_RECIPIENT is set
grep TEST_EMAIL_RECIPIENT .env.test

# Run with explicit email
TEST_EMAIL_RECIPIENT=your@email.com pytest tests/integration/test_e2e_workflow.py -v
```

### Issue: "Database error: tables not found"

**Solution**:
```bash
# Remove old test database and recreate
rm test.db
pytest tests/ -v
```

### Issue: "Tests pass but slow"

**Solution**:
- Skip slow tests: `pytest tests/ -m "not slow"`
- Run unit tests only: `pytest tests/unit/ -v`

## 📚 Documentation

For more details, see:
- `TEST_EMAIL_GUIDE.md` - Complete test documentation
- `EMAIL_TESTS_SUMMARY.md` - Implementation summary
- `.env.test.example` - Configuration reference

## 🚀 Next Steps After Testing

1. **Verify Domain** (Production only):
   - Get verified domain in Resend
   - Update EMAIL_DOMAIN
   - Update CLAIMS_FROM_EMAIL
   - Set EMAIL_TEST_MODE=false

2. **Setup Webhooks**:
   - Create webhook in Resend: `https://yourapp.com/webhooks/email-inbound`
   - Add webhook secret to .env

3. **Deploy**:
   - Run migrations: `alembic upgrade head`
   - Deploy code
   - Monitor email delivery

## ⏱️ Time Estimates

| Phase | Time | Critical |
|-------|------|----------|
| Setup | 5 min | ✓ |
| Verify Installation | 5 min | ✓ |
| Run Basic Test | 2 min | ✓ |
| Test Email | 5 min | ✓ |
| Run All Tests | 3 min | ✓ |
| Verify Email Loop | 5 min | ✓ |
| Coverage Report | 2 min | |
| **TOTAL** | **~25 min** | |

## 📋 Pre-Deployment Checklist

Before deploying to production:

- [ ] All 91 tests pass
- [ ] Email redirection works
- [ ] Coverage > 80% for email/claims code
- [ ] Verified domain configured in Resend
- [ ] Webhook endpoint configured
- [ ] Database migration applied
- [ ] Environment variables set correctly
- [ ] Error logging configured
- [ ] Monitoring alerts set up
- [ ] User notifications configured

## 🎉 Ready to Deploy!

Once this checklist is complete, you're ready to:

1. ✅ Deploy code to staging
2. ✅ Test with real Resend domain
3. ✅ Configure production webhook
4. ✅ Deploy to production
5. ✅ Monitor email delivery

---

**Quick Reference**:
```bash
# One-liner to run everything
export TEST_EMAIL_RECIPIENT=your@email.com && \
export RESEND_API_KEY=re_your_key && \
./run_email_tests.sh all
```

**Questions?** See `TEST_EMAIL_GUIDE.md` for detailed information.

**Status**: ✅ Ready for Testing  
**Last Updated**: February 13, 2026
