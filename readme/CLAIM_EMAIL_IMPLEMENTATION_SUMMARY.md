# Email Loop Closure Feature - Implementation Summary

## ✅ Completed Components

### 1. Database Models (`models.py`)
- **ClaimStatus**: Enum with states (DRAFT, READY_TO_SEND, SENT, AWAITING_RESPONSE, RESPONSE_RECEIVED, ACTION_REQUIRED, CLOSED)
- **EmailDirection**: Enum (OUTBOUND, INBOUND)
- **Claim**: Full model with public_id, reply_email, status tracking, timestamps
- **ClaimEmail**: Stores individual emails with headers, attachments metadata, raw data

### 2. Email Service (`services/email_service.py`)
- **ResendClient**: 
  - `send_email()`: Sends via Resend API with proper headers and Reply-To setting
  - `validate_webhook_signature()`: Validates inbound webhook authenticity
- **EmailTemplates**: 
  - `claim_submission_html()`: HTML email template
  - `claim_submission_text()`: Plain text fallback
- **ResendAPIError**: Custom exception for API errors

### 3. API Endpoints

#### Claims API (`api/claims.py`)
```
POST   /api/claims/create              Create new claim
GET    /api/claims/{claim_id}          Get claim details
GET    /api/claims                     List claims (with filtering)
POST   /api/claims/{claim_id}/send-email  Send email to insurance
PUT    /api/claims/{claim_id}/status   Update claim status
GET    /api/claims/{claim_id}/emails   Get all emails for claim
```

**Key Features:**
- Auto-generates unique public_id and reply_email
- CC'ing user email on outbound
- Tracks message IDs for both inbound/outbound
- Updates claim status automatically

#### Webhooks API (`api/webhooks.py`)
```
POST   /webhooks/email-inbound         Resend webhook for inbound emails
```

**Key Features:**
- Validates Resend webhook signature
- Extracts claim ID from email address (regex: `claim-{id}@`)
- Stores raw email with headers and attachments
- Updates claim status to RESPONSE_RECEIVED
- Prepared for async workflow triggering

### 4. LangGraph Workflows

#### State Model (`workflows/claim_state.py`)
- **ClaimWorkflowState**: Comprehensive state for tracking:
  - Claim identity (id, public_id, user info)
  - Email content (subject, html, text)
  - Inbound response (sender, subject, body, attachments)
  - AI processing results (intent, confidence, action)
  - Workflow status and errors

#### Nodes (`workflows/nodes.py`)
1. **generate_documents_node**: Prepares email content
2. **send_email_node**: Sends via Resend with proper headers
3. **process_inbound_response_node**: Extracts and structures inbound email
4. **parse_intent_node**: Uses simple heuristics (placeholder for LLM)
5. **decide_next_action_node**: Routes based on detected intent
6. **update_claim_status_node**: Updates database and notifies user

#### Workflow Graph (`workflows/builder.py`)
- **claim_workflow**: Outbound flow (generate → send)
- **inbound_workflow**: Inbound processing flow (process → parse → decide → update)

### 5. Database Migration
- Created migration: `3b81cc706962_add_claim_and_claimemail_tables.py`
- Creates both tables with proper indexes
- Supports both SQLite and PostgreSQL

### 6. Documentation (`CLAIM_EMAIL_SETUP.md`)
Complete setup guide including:
- Architecture overview
- Environment configuration
- Step-by-step Resend setup
- Database migration instructions
- Testing procedures
- Security guidelines
- Troubleshooting guide
- Code examples for all workflows

## 📁 File Structure

```
kabala/
├── models.py                          [Extended with Claim models]
├── main.py                            [Updated with router includes]
├── services/
│   ├── __init__.py
│   └── email_service.py               [Resend client, templates, webhooks]
├── api/
│   ├── claims.py                      [Claims CRUD and email endpoints]
│   └── webhooks.py                    [Inbound email webhook handler]
├── workflows/
│   ├── __init__.py
│   ├── claim_state.py                 [State TypedDict]
│   ├── nodes.py                       [Workflow nodes]
│   └── builder.py                     [Graph construction]
├── alembic/
│   └── versions/
│       └── 3b81cc706962_*.py          [Database migration]
└── CLAIM_EMAIL_SETUP.md               [Complete setup documentation]
```

## 🔑 Key Features Implemented

### Email Loop Closure
- ✅ Verified domain support (mail.yourapp.com)
- ✅ Unique reply addresses per claim (claim-{id}@mail.yourapp.com)
- ✅ Automatic inbound email capture via webhook
- ✅ Full email history tracking with headers/attachments

### Claim Management
- ✅ Create claims with insurance company details
- ✅ Status state machine (7 states with transitions)
- ✅ Public ID generation for email addresses
- ✅ Timestamp tracking (created, updated, last_inbound)

### Email Operations
- ✅ Send outbound emails with proper headers
- ✅ CC user on outbound emails (optional)
- ✅ Store message IDs for tracking
- ✅ Webhook signature validation
- ✅ Attachment metadata storage
- ✅ Raw header preservation for audit

### Workflow Processing
- ✅ LangGraph integration for automation
- ✅ Outbound email workflow
- ✅ Inbound response processing
- ✅ Intent parsing (APPROVED, REJECTED, MORE_INFO_NEEDED, UNCLEAR)
- ✅ Action decision making
- ✅ Status updates based on decisions
- ✅ Error handling and logging

## 🚀 Next Steps for Deployment

### Immediate
1. **Run Migration**
   ```bash
   cd /Users/aviadmoshe/Documents/code_projects/kabala
   alembic upgrade head
   ```

2. **Update .env**
   ```dotenv
   RESEND_API_KEY=re_your_key
   EMAIL_DOMAIN=mail.yourapp.com
   CLAIMS_FROM_EMAIL=claims@mail.yourapp.com
   RESEND_WEBHOOK_SECRET=whsec_your_secret
   ```

3. **Verify Imports**
   ```bash
   python -c "from models import Claim; from services.email_service import ResendClient; print('All imports OK')"
   ```

4. **Test API**
   ```bash
   python -m pytest tests/integration/test_claims.py -v
   ```

### Secondary
1. **Configure Resend Domain**
   - Follow Phase 2 in CLAIM_EMAIL_SETUP.md
   - Verify DNS records
   - Test domain with verification endpoint

2. **Set Up Webhook**
   - Create webhook in Resend dashboard
   - Point to `/webhooks/email-inbound`
   - Copy webhook secret to .env

3. **Enhance AI Processing**
   - Replace heuristic parsing with LLM calls
   - Integrate Claude or GPT for intent detection
   - Improve decision making logic

4. **Add User Notifications**
   - Email notifications when claim status changes
   - In-app notifications for new responses
   - Timeline/history view for users

5. **Security Hardening**
   - Implement HTML sanitization (bleach library)
   - Add rate limiting on webhook endpoint
   - Encrypt attachment storage
   - Add malware scanning for attachments

## ⚠️ Important Notes

### Environment Variables Required
```
RESEND_API_KEY          - From Resend dashboard
EMAIL_DOMAIN            - Your verified domain
CLAIMS_FROM_EMAIL       - From address (claims@domain)
RESEND_WEBHOOK_SECRET   - From webhook creation
```

### Database Requirements
- Support for DateTime columns
- Support for Enum types (or String fallback)
- ForeignKey constraints
- Cascading deletes on Claim → ClaimEmail

### API Security
- Webhook signature validation is implemented
- Add rate limiting to webhook endpoint
- Validate claim existence before processing
- Sanitize HTML in inbound emails
- Implement RBAC for claim access

### Workflow Considerations
- Outbound workflow is synchronous (email sent immediately)
- Inbound workflow should be triggered asynchronously (via background task)
- Parse intent node currently uses heuristics (replace with LLM)
- Implement async notification system for status changes

## 🧪 Quick Test

```bash
# 1. Create a claim
curl -X POST http://localhost:8000/api/claims/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "insurance_company": "Test Insurance",
    "insurance_contact_email": "test@insurance.com"
  }'

# Response will include:
# {
#   "id": 1,
#   "public_id": "abc12345",
#   "reply_email": "claim-abc12345@mail.yourapp.com",
#   "status": "DRAFT"
# }

# 2. Send claim email
curl -X POST http://localhost:8000/api/claims/1/send-email \
  -H "Content-Type: application/json" \
  -d '{
    "cc_user_email": true
  }'

# 3. List claims
curl http://localhost:8000/api/claims?user_id=1

# 4. Get claim details
curl http://localhost:8000/api/claims/1

# 5. View all emails for claim
curl http://localhost:8000/api/claims/1/emails
```

## 📊 Database Schema

### claims table
```sql
CREATE TABLE claims (
  id INTEGER PRIMARY KEY,
  public_id VARCHAR UNIQUE NOT NULL,
  user_id INTEGER FOREIGN KEY,
  reply_email VARCHAR UNIQUE NOT NULL,
  outbound_message_id VARCHAR,
  status VARCHAR NOT NULL,
  insurance_company VARCHAR,
  insurance_contact_email VARCHAR,
  created_at DATETIME,
  updated_at DATETIME,
  last_inbound_at DATETIME
);

CREATE INDEX ix_claims_public_id ON claims(public_id);
CREATE INDEX ix_claims_user_id ON claims(user_id);
CREATE INDEX ix_claims_status ON claims(status);
```

### claim_emails table
```sql
CREATE TABLE claim_emails (
  id INTEGER PRIMARY KEY,
  claim_id INTEGER FOREIGN KEY,
  direction VARCHAR NOT NULL,
  message_id VARCHAR,
  sender VARCHAR NOT NULL,
  recipient VARCHAR NOT NULL,
  subject VARCHAR,
  body_text TEXT,
  body_html TEXT,
  attachments_json TEXT,
  raw_headers_json TEXT,
  created_at DATETIME
);

CREATE INDEX ix_claim_emails_claim_id ON claim_emails(claim_id);
CREATE INDEX ix_claim_emails_direction ON claim_emails(direction);
CREATE INDEX ix_claim_emails_created_at ON claim_emails(created_at);
```

## 📝 Configuration Checklist

- [ ] Run database migration
- [ ] Add Resend API key to .env
- [ ] Configure email domain in .env
- [ ] Verify domain in Resend dashboard
- [ ] Add DNS records for domain
- [ ] Create webhook in Resend dashboard
- [ ] Add webhook secret to .env
- [ ] Test email sending with verification endpoint
- [ ] Test webhook with curl simulation
- [ ] Integrate with UI for claim creation
- [ ] Add user notification system
- [ ] Implement HTML sanitization
- [ ] Add rate limiting to webhook
- [ ] Set up monitoring/logging
- [ ] Enhance AI processing with LLM

---

**Implementation Date**: February 13, 2026  
**Implementation Status**: ✅ Complete - Ready for Testing  
**Next Phase**: Testing, Security Hardening, LLM Integration
