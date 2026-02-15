"""
Integration tests for webhook handlers.

Tests cover:
- Inbound email webhook processing
- Webhook signature validation
- Claim ID extraction from email address
- Email storage
- Claim status updates
- Error handling
"""

import pytest
import json
import hmac
import hashlib
from datetime import datetime
from unittest.mock import patch, MagicMock
from models import Claim, ClaimEmail, ClaimStatus, EmailDirection


@pytest.mark.integration
class TestEmailWebhooks:
    """Integration tests for email webhooks"""

    @staticmethod
    def generate_webhook_signature(body: str, secret: str = "test_secret") -> str:
        """Generate a valid webhook signature"""
        timestamp = "1234567890"
        signed_content = f"{timestamp}.{body}"
        expected_hash = hmac.new(
            secret.encode(),
            signed_content.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"t={timestamp},v1={expected_hash}"

    def test_inbound_email_webhook_success(self, client, sample_claim, db_session):
        """Test successful inbound email processing"""
        payload = {
            "type": "email_received",
            "created_at": "2024-01-01T12:00:00Z",
            "data": {
                "from_addr": "claims@testinsurance.com",
                "to_addr": f"claim-{sample_claim.public_id}@mail.yourapp.com",
                "subject": "Re: Claim Submission",
                "text": "Your claim has been approved.",
                "html": "<p>Your claim has been approved.</p>",
                "headers": {"Message-ID": "test_msg_id"},
                "message_id": "msg_inbound_123",
            }
        }
        
        body = json.dumps(payload)
        signature = self.generate_webhook_signature(body, "test_secret")
        
        with patch("api.webhooks.ResendClient.validate_webhook_signature", return_value=True):
            response = client.post(
                "/webhooks/email-inbound",
                content=body,
                headers={
                    "x-resend-signature": signature,
                    "Content-Type": "application/json"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response
        assert data["status"] == "success"
        assert data["claim_id"] == sample_claim.id
        assert data["claim_public_id"] == sample_claim.public_id

    def test_inbound_email_webhook_creates_record(self, client, sample_claim, db_session):
        """Test that webhook creates ClaimEmail record"""
        payload = {
            "type": "email_received",
            "created_at": "2024-01-01T12:00:00Z",
            "data": {
                "from_addr": "claims@testinsurance.com",
                "to_addr": f"claim-{sample_claim.public_id}@mail.yourapp.com",
                "subject": "Re: Claim Submission",
                "text": "Your claim has been approved.",
                "html": "<p>Your claim has been approved.</p>",
                "headers": {"Message-ID": "test_id"},
                "message_id": "msg_inbound_456",
            }
        }
        
        body = json.dumps(payload)
        signature = self.generate_webhook_signature(body, "test_secret")
        
        with patch("api.webhooks.ResendClient.validate_webhook_signature", return_value=True):
            response = client.post(
                "/webhooks/email-inbound",
                content=body,
                headers={
                    "x-resend-signature": signature,
                    "Content-Type": "application/json"
                }
            )
        
        assert response.status_code == 200
        
        # Verify ClaimEmail record was created
        email = db_session.query(ClaimEmail).filter(
            ClaimEmail.claim_id == sample_claim.id,
            ClaimEmail.direction == EmailDirection.INBOUND
        ).first()
        
        assert email is not None
        assert email.sender == "claims@testinsurance.com"
        assert email.subject == "Re: Claim Submission"
        assert email.body_text == "Your claim has been approved."

    def test_inbound_email_webhook_updates_claim_status(self, client, sample_claim, db_session):
        """Test that webhook updates claim status"""
        # Set claim to AWAITING_RESPONSE first
        sample_claim.status = ClaimStatus.AWAITING_RESPONSE
        db_session.commit()
        
        payload = {
            "type": "email_received",
            "created_at": "2024-01-01T12:00:00Z",
            "data": {
                "from_addr": "claims@testinsurance.com",
                "to_addr": f"claim-{sample_claim.public_id}@mail.yourapp.com",
                "subject": "Re: Claim",
                "text": "Response text",
                "html": "<p>Response</p>",
                "headers": {},
                "message_id": "msg_789",
            }
        }
        
        body = json.dumps(payload)
        signature = self.generate_webhook_signature(body, "test_secret")
        
        with patch("api.webhooks.ResendClient.validate_webhook_signature", return_value=True):
            response = client.post(
                "/webhooks/email-inbound",
                content=body,
                headers={
                    "x-resend-signature": signature,
                    "Content-Type": "application/json"
                }
            )
        
        assert response.status_code == 200
        
        # Verify status was updated by re-querying
        updated_claim = db_session.query(Claim).filter(Claim.id == sample_claim.id).first()
        assert updated_claim.status == ClaimStatus.RESPONSE_RECEIVED
        assert updated_claim.last_inbound_at is not None

    def test_inbound_email_webhook_invalid_signature(self, client, sample_claim):
        """Test webhook rejects invalid signature"""
        payload = {
            "type": "email_received",
            "data": {}
        }
        
        body = json.dumps(payload)
        
        with patch("api.webhooks.ResendClient.validate_webhook_signature", return_value=False):
            response = client.post(
                "/webhooks/email-inbound",
                content=body,
                headers={
                    "x-resend-signature": "invalid_signature",
                    "Content-Type": "application/json"
                }
            )
        
        assert response.status_code == 401

    def test_inbound_email_webhook_claim_not_found(self, client):
        """Test webhook with non-existent claim ID"""
        payload = {
            "type": "email_received",
            "created_at": "2024-01-01T12:00:00Z",
            "data": {
                "from_addr": "claims@testinsurance.com",
                "to_addr": "claim-nonexistent@mail.yourapp.com",
                "subject": "Re: Claim",
                "text": "Response",
                "html": "<p>Response</p>",
                "headers": {},
                "message_id": "msg_999",
            }
        }
        
        body = json.dumps(payload)
        signature = self.generate_webhook_signature(body, "test_secret")
        
        with patch("api.webhooks.ResendClient.validate_webhook_signature", return_value=True):
            response = client.post(
                "/webhooks/email-inbound",
                content=body,
                headers={
                    "x-resend-signature": signature,
                    "Content-Type": "application/json"
                }
            )
        
        # Should still return 200 but with error status
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"

    def test_inbound_email_webhook_with_attachments(self, client, sample_claim, db_session):
        """Test webhook processing with attachments"""
        payload = {
            "type": "email_received",
            "created_at": "2024-01-01T12:00:00Z",
            "data": {
                "from_addr": "claims@testinsurance.com",
                "to_addr": f"claim-{sample_claim.public_id}@mail.yourapp.com",
                "subject": "Re: Claim with Approval Letter",
                "text": "Attached is approval.",
                "html": "<p>Attached is approval.</p>",
                "headers": {},
                "message_id": "msg_attach_123",
                "attachments": [
                    {
                        "filename": "approval.pdf",
                        "size": 102400,
                        "content_type": "application/pdf"
                    },
                    {
                        "filename": "receipt.jpg",
                        "size": 51200,
                        "content_type": "image/jpeg"
                    }
                ]
            }
        }
        
        body = json.dumps(payload)
        signature = self.generate_webhook_signature(body, "test_secret")
        
        with patch("api.webhooks.ResendClient.validate_webhook_signature", return_value=True):
            response = client.post(
                "/webhooks/email-inbound",
                content=body,
                headers={
                    "x-resend-signature": signature,
                    "Content-Type": "application/json"
                }
            )
        
        assert response.status_code == 200
        
        # Verify attachments were stored
        email = db_session.query(ClaimEmail).filter(
            ClaimEmail.claim_id == sample_claim.id
        ).first()
        
        assert email is not None
        assert email.attachments_json is not None
        
        attachments = json.loads(email.attachments_json)
        assert len(attachments) == 2
        assert attachments[0]["filename"] == "approval.pdf"
        assert attachments[1]["filename"] == "receipt.jpg"

    def test_inbound_email_webhook_ignores_other_events(self, client):
        """Test webhook ignores non-email_received events"""
        payload = {
            "type": "email_sent",  # Different event type
            "created_at": "2024-01-01T12:00:00Z",
            "data": {}
        }
        
        body = json.dumps(payload)
        signature = self.generate_webhook_signature(body, "test_secret")
        
        with patch("api.webhooks.ResendClient.validate_webhook_signature", return_value=True):
            response = client.post(
                "/webhooks/email-inbound",
                content=body,
                headers={
                    "x-resend-signature": signature,
                    "Content-Type": "application/json"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"

    def test_inbound_email_webhook_invalid_json(self, client):
        """Test webhook with invalid JSON payload"""
        body = "invalid json {{"
        
        with patch("api.webhooks.ResendClient.validate_webhook_signature", return_value=True):
            response = client.post(
                "/webhooks/email-inbound",
                content=body,
                headers={
                    "x-resend-signature": "t=123,v1=abc",
                    "Content-Type": "application/json"
                }
            )
        
        assert response.status_code == 400
        assert "Invalid JSON payload" in response.json()["detail"]

    def test_inbound_email_webhook_malformed_recipient(self, client):
        """Test webhook with malformed recipient address"""
        payload = {
            "type": "email_received",
            "created_at": "2024-01-01T12:00:00Z",
            "data": {
                "from_addr": "claims@testinsurance.com",
                "to_addr": "notaclaim@mail.yourapp.com",  # Wrong format
                "subject": "Re: Claim",
                "text": "Response",
                "html": "<p>Response</p>",
                "headers": {},
            }
        }
        
        body = json.dumps(payload)
        signature = self.generate_webhook_signature(body, "test_secret")
        
        with patch("api.webhooks.ResendClient.validate_webhook_signature", return_value=True):
            response = client.post(
                "/webhooks/email-inbound",
                content=body,
                headers={
                    "x-resend-signature": signature,
                    "Content-Type": "application/json"
                }
            )
        
        # Should still return success but error status
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "Could not extract claim ID" in data["message"]


@pytest.mark.unit
class TestEmailAddressParsing:
    """Unit tests for claim ID extraction from email addresses"""

    def test_extract_claim_id_success(self):
        """Test extracting claim ID from valid email address"""
        from api.webhooks import extract_claim_id_from_email
        
        claim_id = extract_claim_id_from_email("claim-abc12345@mail.yourapp.com")
        assert claim_id == "abc12345"

    def test_extract_claim_id_alphanumeric(self):
        """Test extracting alphanumeric claim IDs"""
        from api.webhooks import extract_claim_id_from_email
        
        claim_id = extract_claim_id_from_email("claim-Test123ABC@mail.yourapp.com")
        assert claim_id == "Test123ABC"

    def test_extract_claim_id_short(self):
        """Test extracting short claim ID"""
        from api.webhooks import extract_claim_id_from_email
        
        claim_id = extract_claim_id_from_email("claim-abc@mail.yourapp.com")
        assert claim_id == "abc"

    def test_extract_claim_id_long(self):
        """Test extracting long claim ID"""
        from api.webhooks import extract_claim_id_from_email
        
        claim_id = extract_claim_id_from_email("claim-verylongclaim1234567890@mail.yourapp.com")
        assert claim_id == "verylongclaim1234567890"

    def test_extract_claim_id_invalid_format(self):
        """Test extraction fails for invalid format"""
        from api.webhooks import extract_claim_id_from_email
        
        claim_id = extract_claim_id_from_email("notaclaim@mail.yourapp.com")
        assert claim_id == ""

    def test_extract_claim_id_no_hyphen(self):
        """Test extraction fails without hyphen"""
        from api.webhooks import extract_claim_id_from_email
        
        claim_id = extract_claim_id_from_email("claimabc12345@mail.yourapp.com")
        assert claim_id == ""

    def test_extract_claim_id_empty(self):
        """Test extraction with empty string"""
        from api.webhooks import extract_claim_id_from_email
        
        claim_id = extract_claim_id_from_email("")
        assert claim_id == ""
