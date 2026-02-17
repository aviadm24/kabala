# Email Loop Closure Feature - Implementation Guide

## Overview

This guide covers the implementation of the **Claim Email Loop Closure** feature, which enables:

- Sending claim emails from a verified domain
- Unique inbound email addresses per claim  
- Automatic attachment of replies to claims
- Full email history tracking
- AI-driven response processing via LangGraph

## Architecture Components

### 1. **Database Models**

#### Claim
- `id`: Primary key
- `public_id`: Unique short ID (8 chars) used in email addresses
- `user_id`: Reference to user
- `reply_email`: Claim-specific email (claim-{public_id}@mail.yourapp.com)
- `status`: Current claim status (DRAFT, READY_TO_SEND, SENT, AWAITING_RESPONSE, RESPONSE_RECEIVED, ACTION_REQUIRED, CLOSED)
- `insurance_company`: Name of insurance company
- `insurance_contact_email`: Email to send claim to
- `outbound_message_id`: Resend message ID for outbound email
- `last_inbound_at`: Timestamp of last inbound email
- `created_at`, `updated_at`: Timestamps

#### ClaimEmail
- `id`: Primary key
- `claim_id`: Reference to Claim
- `direction`: OUTBOUND or INBOUND
- `message_id`: Resend message ID or email Message-ID header
- `sender`, `recipient`: Email addresses
- `subject`: Email subject
- `body_text`, `body_html`: Email content
- `attachments_json`: JSON metadata of attachments
- `raw_headers_json`: Raw email headers
- `created_at`: Timestamp

### 2. **Email Service**

Located in `services/email_service.py`:

**ResendClient** class:
- `send_email()`: Send email via Resend API with proper headers
- `validate_webhook_signature()`: Verify inbound webhook authenticity

**EmailTemplates** class:
- `claim_submission_html()`: Generate HTML email template
- `claim_submission_text()`: Generate plain text email template

### 3. **API Endpoints**

#### Claims Management (`api/claims.py`)

```
POST   /api/claims/create              Create new claim
GET    /api/claims/{claim_id}          Get claim details
GET    /api/claims                     List claims (with filtering)
POST   /api/claims/{claim_id}/send-email  Send email to insurance
PUT    /api/claims/{claim_id}/status   Update claim status
GET    /api/claims/{claim_id}/emails   Get all emails for claim
```

#### Webhooks (`api/webhooks.py`)

```
POST   /webhooks/email-inbound         Receive inbound email from Resend
```

### 4. **Workflow Engine (LangGraph)**

Located in `workflows/`:

**Outbound Flow:**
```
generateDocuments → sendEmail → [waiting for inbound webhook]
```

**Inbound Response Flow:**
```
processInbound → parseIntent → decideAction → updateStatus → END
```

## Setup Instructions

### Phase 1: Environment Configuration

Add these to your `.env` file:

```dotenv
# Resend API
RESEND_API_KEY=re_your_api_key_here

# Email domain configuration
# Update these after domain verification in Resend
EMAIL_DOMAIN=mail.yourapp.com
CLAIMS_FROM_EMAIL=claims@mail.yourapp.com

# Webhook security
# Get this from Resend dashboard after setting up webhook
RESEND_WEBHOOK_SECRET=whsec_your_secret_here
```

### Phase 2: Resend Dashboard Setup

#### Step 1: Add Sending Domain

1. Log in to [Resend Dashboard](https://resend.com)
2. Navigate to **Domains**
3. Click **Add Domain**
4. Enter: `mail.yourapp.com` (NOT the root domain)
5. Click **Add**

#### Step 2: Verify Domain via DNS

Resend will provide DNS records. Add these to your domain provider (Route53, Cloudflare, etc.):

**Example DNS Records:**

- **CNAME** for DKIM: `default._domainkey.mail.yourapp.com` → `mail.yourapp.com`
- **MX** record: `mail.yourapp.com` → `inbound.mx.resend.dev`
- **SPF** record: `v=spf1 include:sendingdomain.resend.dev ~all`

⚠️ **Important**: DNS changes can take 24-48 hours to propagate. Verify in Resend dashboard when ready.

#### Step 3: Set Up Inbound Email Routing

1. In Resend Dashboard, go to your verified domain
2. Click **Inbound Settings**
3. Configure a catch-all rule:
   - **From**: `*@mail.yourapp.com`
   - **Forward to webhooks**: Enable
   - **Webhook endpoint**: `https://yourapp.com/webhooks/email-inbound`
4. Click **Save**

#### Step 4: Create Webhook for Inbound Emails

1. Navigate to **Webhooks** section
2. Create new webhook:
   - **URL**: `https://yourapp.com/webhooks/email-inbound`
   - **Events**: Select "email_received"
3. Copy the **Webhook Secret**
4. Add to `.env`: `RESEND_WEBHOOK_SECRET=...`

#### Step 5: Test Domain Verification

```bash
python -c "
from services.email_service import ResendClient

client = ResendClient()
response = client.send_email(
    to='test@yourcompany.com',
    subject='Domain Verification Test',
    html='<p>This is a test email.</p>',
    from_email='claims@mail.yourapp.com'
)
print('Email sent:', response.get('id'))
"
```

### Phase 3: Database Migration

Run the migrations to create the Claim and ClaimEmail tables:

```bash
# Generate migration (optional - already created)
# alembic revision --autogenerate -m "Add Claim and ClaimEmail tables"

# Apply migration
alembic upgrade head
```

Verify tables were created:
```bash
# For SQLite
sqlite3 app.db ".tables"

# For PostgreSQL
psql $DATABASE_URL -c "\dt claims, claim_emails"
```

### Phase 4: Test the Feature

#### Test 1: Create a Claim

```bash
curl -X POST http://localhost:8000/api/claims/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "insurance_company": "Acme Insurance",
    "insurance_contact_email": "claims@acmeins.com",
    "claim_amount": "$5,000"
  }'
```

Response:
```json
{
  "id": 1,
  "public_id": "abc12345",
  "user_id": 1,
  "reply_email": "claim-abc12345@mail.yourapp.com",
  "status": "DRAFT",
  "created_at": "2024-01-01T12:00:00"
}
```

#### Test 2: Send Claim Email

```bash
curl -X POST http://localhost:8000/api/claims/1/send-email \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Our Claim Submission",
    "cc_user_email": true
  }'
```

Response:
```json
{
  "id": 1,
  "claim_id": 1,
  "direction": "OUTBOUND",
  "message_id": "msg_abc123",
  "sender": "claims@mail.yourapp.com",
  "recipient": "claims@acmeins.com",
  "subject": "Our Claim Submission",
  "created_at": "2024-01-01T12:00:00"
}
```

#### Test 3: Simulate Inbound Email

Send a reply to the claim email address. The webhook will automatically:
1. Parse the reply-to address
2. Extract claim ID
3. Store the email
4. Update claim status to RESPONSE_RECEIVED
5. Trigger workflow processing

### Phase 5: Workflow Integration

#### Outbound Email Workflow

```python
from workflows.builder import claim_workflow
from workflows.claim_state import ClaimWorkflowState
from datetime import datetime

# Initialize state
initial_state = ClaimWorkflowState(
    claim_id=1,
    claim_public_id="abc12345",
    user_id=1,
    insurance_company="Acme Insurance",
    insurance_contact_email="claims@acmeins.com",
    user_email="user@example.com",
    email_subject=None,
    email_html=None,
    email_text=None,
    outbound_message_id=None,
    email_sent_at=None,
    inbound_message_id=None,
    inbound_sender=None,
    inbound_subject=None,
    inbound_body_text=None,
    inbound_body_html=None,
    inbound_received_at=None,
    inbound_attachments=None,
    response_intent=None,
    response_confidence=None,
    response_summary=None,
    action_required=None,
    claim_status="DRAFT",
    workflow_stage="pending_send",
    errors=[],
    metadata={},
)

# Execute outbound workflow
result = claim_workflow.invoke(initial_state)
print("Email sent:", result.get("outbound_message_id"))
```

#### Inbound Response Workflow

When webhook receives inbound email:

```python
from workflows.builder import inbound_workflow

# Webhook populates these fields from the inbound email
state["inbound_message_id"] = "email_id_from_resend"
state["inbound_sender"] = "claims@acmeins.com"
state["inbound_subject"] = "Re: Our Claim Submission"
state["inbound_body_text"] = "Your claim has been approved..."

# Execute inbound workflow
result = inbound_workflow.invoke(state)
print("Intent:", result.get("response_intent"))
print("Status:", result.get("claim_status"))
```

## Security Considerations

### 1. Webhook Signature Validation

Always validate webhook signatures:

```python
from services.email_service import ResendClient

client = ResendClient()
signature = request.headers.get("x-resend-signature")
is_valid = client.validate_webhook_signature(signature, raw_body)

if not is_valid:
    raise HTTPException(status_code=401, detail="Invalid signature")
```

### 2. Claim ID Extraction

Validate extracted claim IDs exist in database:

```python
claim = db.query(Claim).filter(Claim.public_id == extracted_id).first()
if not claim:
    # Log and reject, don't process
    raise Exception(f"Claim not found: {extracted_id}")
```

### 3. Email Sanitization

Sanitize HTML in inbound emails before displaying:

```python
from bleach import clean

safe_html = clean(
    claim_email.body_html,
    tags=['p', 'div', 'br', 'strong', 'em', 'u'],
    strip=True
)
```

### 4. Attachment Handling

- Limit attachment size (e.g., 25MB max)
- Scan for malware (integrate with ClamAV or similar)
- Store attachments in secure location with access controls
- Never execute attachments

### 5. User Privacy

- Never log email passwords or credentials
- Encrypt sensitive claim data at rest
- Implement role-based access control (RBAC)
- Audit all claim access and modifications

## Monitoring and Debugging

### Check Email Sending Status

```bash
# In Resend dashboard, navigate to Activity
# Filter by "emails" tab
# Look for messages from claims@mail.yourapp.com
```

### Monitor Webhook Deliveries

```bash
# In Resend dashboard, go to Webhooks
# Click your webhook
# View recent deliveries and any failures
```

### Database Debugging

```python
# Check claim status
from database import SessionLocal
from models import Claim, ClaimEmail

db = SessionLocal()

claim = db.query(Claim).filter(Claim.public_id == "abc12345").first()
print(f"Status: {claim.status}")
print(f"Last inbound: {claim.last_inbound_at}")

# View all emails for claim
emails = db.query(ClaimEmail).filter(ClaimEmail.claim_id == claim.id).all()
for email in emails:
    print(f"{email.direction}: {email.sender} → {email.recipient}")
```

### View Logs

```bash
# Check application logs
tail -f logs/kabala.log | grep -E "(SendEmail|ProcessInbound|Webhook)"
```

## Common Issues and Troubleshooting

### Issue: "Email not sent"

**Causes:**
- Domain not verified in Resend
- Invalid RESEND_API_KEY
- Typo in email address

**Solution:**
1. Verify domain status in Resend dashboard (should show "Verified")
2. Check DNS propagation (use `dig` or online tools)
3. Validate API key in environment variables
4. Check email address syntax

### Issue: "Webhook not receiving emails"

**Causes:**
- Webhook URL incorrect in Resend
- Webhook secret not shared between Resend and app
- Inbound routing not enabled
- Server not publicly accessible

**Solution:**
1. Verify webhook URL in Resend dashboard settings
2. Test webhook with: `curl https://yourapp.com/webhooks/email-inbound`
3. Ensure server is publicly accessible (not localhost)
4. Check webhook logs in Resend dashboard

### Issue: "Claim not found from webhook"

**Causes:**
- Email sent to wrong address format
- Claim deleted before email arrived
- Public ID extraction failed

**Solution:**
1. Check email was sent to `claim-{public_id}@mail.yourapp.com`
2. Verify claim exists: `SELECT * FROM claims WHERE public_id = '...'`
3. Check webhook logs for extraction errors

### Issue: "High latency in email delivery"

**Solutions:**
- Resend typically delivers within seconds
- Check your server response time to webhooks
- Async process long-running tasks (attachment scanning, etc.)

## Next Steps

1. **Configure domain verification** (Phase 2)
2. **Run database migration** (Phase 3)
3. **Test with test cases** (Phase 4)
4. **Integrate with your UI** to create/send claims
5. **Add user notifications** when emails arrive/status changes
6. **Enhance AI processing** in `parse_intent_node` with LLM integration
7. **Implement attachment handling** and malware scanning
8. **Set up monitoring and alerting** for failed emails

## Additional Resources

- [Resend Documentation](https://resend.com/docs)
- [Resend API Reference](https://resend.com/docs/api-reference)
- [Resend Domain Verification](https://resend.com/docs/send-with-resend/domains)
- [Resend Webhooks](https://resend.com/docs/send-with-resend/webhooks)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Insurance Claims System                      │
└─────────────────────────────────────────────────────────────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
         ┌──────▼────────┐  ┌────▼──────────┐  ┌─▼───────────────┐
         │  API Endpoints │  │   Database   │  │ LangGraph       │
         ├────────────────┤  ├──────────────┤  │ Workflows       │
         │ POST /create   │  │ Claim        │  ├─────────────────┤
         │ POST /send-    │  │ ClaimEmail   │  │ generateDocs    │
         │   email        │  │ User         │  │ sendEmail       │
         │ GET /*         │  │ Receipt      │  │ processInbound  │
         │ PUT /status    │  └──────────────┘  │ parseIntent     │
         └────────────────┘                     │ decideAction    │
                │                               └─────────────────┘
                │
     ┌──────────┼──────────┐
     │          │          │
┌────▼────┐ ┌──▼──────┐ ┌─▼────────────┐
│ Resend   │ │ Webhook  │ │ Email        │
│ API      │ │ Handler  │ │ Service      │
├──────────┤ ├─────────┤ ├──────────────┤
│ send()   │ │validate  │ │ResendClient  │
│ webhook  │ │ signature│ │EmailTemplates│
└──────────┘ │ extract  │ └──────────────┘
             │ claim_id │
             │ store    │
             │ email    │
             └─────────┘
                │
     ┌──────────┴──────────┐
     ▼                     ▼
┌──────────────┐    ┌────────────────┐
│ Outbound     │    │ Inbound        │
│ Email        │    │ Email from     │
│ to Insurance │    │ Insurance Co.  │
└──────────────┘    └────────────────┘
```

---

**Last Updated**: February 13, 2026  
**Version**: 1.0  
**Status**: Implementation Complete
