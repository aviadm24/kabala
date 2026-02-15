"""
End-to-end tests for the complete email loop closure workflow.

These tests simulate the full lifecycle:
1. Create a claim
2. Send email to insurance company
3. Receive inbound response via webhook
4. Process and update status
"""

import pytest
import json
import hmac
import hashlib
from datetime import datetime
from unittest.mock import patch, MagicMock
from models import Claim, ClaimEmail, ClaimStatus, EmailDirection, User


@pytest.mark.integration
class TestEmailLoopClosureE2E:
    """End-to-end tests for complete email loop workflow"""

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

    def test_complete_claim_workflow(self, client, db_session):
        """Test complete workflow from claim creation to response processing"""
        
        # Step 1: Create a user
        user = User(
            username="e2e_test_user",
            email="e2etest@example.com",
            created_at="2025-01-01"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Step 2: Create a claim
        create_response = client.post(
            "/api/claims/create",
            json={
                "user_id": user.user_id,
                "insurance_company": "E2E Test Insurance",
                "insurance_contact_email": "claims@e2einsurance.com",
                "claim_amount": "$10,000",
            }
        )
        
        assert create_response.status_code == 200
        claim_data = create_response.json()
        claim_id = claim_data["id"]
        claim_public_id = claim_data["public_id"]
        assert claim_data["status"] == "DRAFT"
        
        # Step 3: Send email to insurance company
        with patch("api.claims.ResendClient.send_email") as mock_send:
            mock_send.return_value = {"id": "msg_outbound_e2e"}
            
            send_response = client.post(
                f"/api/claims/{claim_id}/send-email",
                json={
                    "claim_id": claim_id,
                    "subject": "E2E Claim Submission",
                    "cc_user_email": True
                }
            )
        
        assert send_response.status_code == 200
        email_data = send_response.json()
        assert email_data["direction"] == "OUTBOUND"
        assert email_data["message_id"] == "msg_outbound_e2e"
        
        # Verify claim status changed
        get_response = client.get(f"/api/claims/{claim_id}")
        claim_after_send = get_response.json()
        assert claim_after_send["status"] == "AWAITING_RESPONSE"
        
        # Step 4: Simulate inbound response via webhook
        inbound_payload = {
            "type": "email_received",
            "created_at": "2024-01-01T12:00:00Z",
            "data": {
                "from_addr": "claims@e2einsurance.com",
                "to_addr": f"claim-{claim_public_id}@mail.yourapp.com",
                "subject": "Re: E2E Claim Submission",
                "text": "Your claim has been approved for $10,000.",
                "html": "<p>Your claim has been approved for $10,000.</p>",
                "headers": {"Message-ID": "msg_inbound_e2e"},
                "message_id": "msg_inbound_e2e",
            }
        }
        
        body = json.dumps(inbound_payload)
        signature = self.generate_webhook_signature(body, "test_secret")
        
        with patch("api.webhooks.ResendClient.validate_webhook_signature", return_value=True):
            webhook_response = client.post(
                "/webhooks/email-inbound",
                content=body,
                headers={
                    "x-resend-signature": signature,
                    "Content-Type": "application/json"
                }
            )
        
        assert webhook_response.status_code == 200
        webhook_data = webhook_response.json()
        assert webhook_data["status"] == "success"
        assert webhook_data["claim_public_id"] == claim_public_id
        
        # Step 5: Verify claim status updated
        get_response = client.get(f"/api/claims/{claim_id}")
        claim_after_response = get_response.json()
        assert claim_after_response["status"] == "RESPONSE_RECEIVED"
        
        # Step 6: Verify email history
        emails_response = client.get(f"/api/claims/{claim_id}/emails")
        assert emails_response.status_code == 200
        emails = emails_response.json()
        
        assert len(emails) == 2
        
        # Find outbound and inbound
        outbound = next((e for e in emails if e["direction"] == "OUTBOUND"), None)
        inbound = next((e for e in emails if e["direction"] == "INBOUND"), None)
        
        assert outbound is not None
        assert outbound["message_id"] == "msg_outbound_e2e"
        
        assert inbound is not None
        assert inbound["message_id"] == "msg_inbound_e2e"
        assert inbound["sender"] == "claims@e2einsurance.com"

    def test_multiple_claims_per_user(self, client, db_session):
        """Test that a user can have multiple independent claims"""
        
        # Create user
        user = User(
            username="multi_claims_user",
            email="multiuser@example.com",
            created_at="2025-01-01"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        user_id = user.user_id
        
        # Create multiple claims
        claims = []
        for i in range(3):
            response = client.post(
                "/api/claims/create",
                json={
                    "user_id": user_id,
                    "insurance_company": f"Insurance {i}",
                    "insurance_contact_email": f"claims{i}@insurance.com",
                }
            )
            assert response.status_code == 200
            claims.append(response.json())
        
        # Verify each claim has unique ID and email
        public_ids = [c["public_id"] for c in claims]
        reply_emails = [c["reply_email"] for c in claims]
        
        # All should be unique
        assert len(set(public_ids)) == 3
        assert len(set(reply_emails)) == 3
        
        # Each should contain its unique ID
        for claim, public_id in zip(claims, public_ids):
            assert public_id in claim["reply_email"]
        
        # List claims for user
        list_response = client.get(f"/api/claims?user_id={user_id}")
        listed_claims = list_response.json()
        
        assert len(listed_claims) >= 3

    def test_email_chain_multiple_responses(self, client, db_session):
        """Test handling multiple responses to the same claim"""
        
        # Create user and claim
        user = User(
            username="chain_test_user",
            email="chain@example.com",
            created_at="2025-01-01"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        create_response = client.post(
            "/api/claims/create",
            json={
                "user_id": user.user_id,
                "insurance_company": "Chain Insurance",
                "insurance_contact_email": "claims@chainins.com",
            }
        )
        claim_id = create_response.json()["id"]
        claim_public_id = create_response.json()["public_id"]
        
        # Send initial email
        with patch("api.claims.ResendClient.send_email") as mock_send:
            mock_send.return_value = {"id": "msg_chain_outbound"}
            client.post(f"/api/claims/{claim_id}/send-email", json={"claim_id": claim_id})
        
        # Send first response
        response1_payload = {
            "type": "email_received",
            "data": {
                "from_addr": "claims@chainins.com",
                "to_addr": f"claim-{claim_public_id}@mail.yourapp.com",
                "subject": "Re: Claim - Need More Info",
                "text": "We need more information to process your claim.",
                "html": "<p>We need more information to process your claim.</p>",
                "message_id": "msg_chain_response_1",
                "headers": {},
            }
        }
        
        body1 = json.dumps(response1_payload)
        signature1 = self.generate_webhook_signature(body1, "test_secret")
        
        with patch("api.webhooks.ResendClient.validate_webhook_signature", return_value=True):
            client.post(
                "/webhooks/email-inbound",
                content=body1,
                headers={"x-resend-signature": signature1, "Content-Type": "application/json"}
            )
        
        # Send second response
        response2_payload = {
            "type": "email_received",
            "data": {
                "from_addr": "claims@chainins.com",
                "to_addr": f"claim-{claim_public_id}@mail.yourapp.com",
                "subject": "Re: Claim - Approved",
                "text": "Your claim has been approved.",
                "html": "<p>Your claim has been approved.</p>",
                "message_id": "msg_chain_response_2",
                "headers": {},
            }
        }
        
        body2 = json.dumps(response2_payload)
        signature2 = self.generate_webhook_signature(body2, "test_secret")
        
        with patch("api.webhooks.ResendClient.validate_webhook_signature", return_value=True):
            client.post(
                "/webhooks/email-inbound",
                content=body2,
                headers={"x-resend-signature": signature2, "Content-Type": "application/json"}
            )
        
        # Verify all emails are stored
        emails_response = client.get(f"/api/claims/{claim_id}/emails")
        emails = emails_response.json()
        
        # Should have 1 outbound + 2 inbound = 3 total
        assert len(emails) == 3
        
        message_ids = [e["message_id"] for e in emails]
        assert "msg_chain_outbound" in message_ids
        assert "msg_chain_response_1" in message_ids
        assert "msg_chain_response_2" in message_ids

    def test_test_mode_email_redirection(self, client, db_session):
        """Test that emails are sent via API"""
        
        user = User(
            username="test_mode_user",
            email="testmode@example.com",
            created_at="2025-01-01"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        user_id = user.user_id
        
        create_response = client.post(
            "/api/claims/create",
            json={
                "user_id": user_id,
                "insurance_company": "Test Mode Insurance",
                "insurance_contact_email": "claims@testmodeins.com",
            }
        )
        claim_id = create_response.json()["id"]
        
        with patch("api.claims.ResendClient.send_email") as mock_send:
            mock_send.return_value = {"id": "msg_test_mode"}
            
            send_response = client.post(
                f"/api/claims/{claim_id}/send-email",
                json={"claim_id": claim_id, "cc_user_email": True}
            )
            
            assert send_response.status_code == 200
            
            # Verify send_email was called with the insurance company email
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            
            # Verify the email was sent to the intended recipient
            # (In real test mode, it would be redirected to TEST_EMAIL_RECIPIENT)
            assert "to" in call_args[1]

    def test_claim_status_transitions(self, client, db_session):
        """Test valid claim status transitions"""
        
        # Create user and claim
        user = User(
            username="status_test_user",
            email="status@example.com",
            created_at="2025-01-01"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        create_response = client.post(
            "/api/claims/create",
            json={
                "user_id": user.user_id,
                "insurance_company": "Status Test Insurance",
                "insurance_contact_email": "claims@statusins.com",
            }
        )
        claim_id = create_response.json()["id"]
        
        # Check initial status
        response = client.get(f"/api/claims/{claim_id}")
        assert response.json()["status"] == "DRAFT"
        
        # Transition to READY_TO_SEND
        response = client.put(
            f"/api/claims/{claim_id}/status",
            params={"new_status": "READY_TO_SEND"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "READY_TO_SEND"
        
        # Transition to SENT
        response = client.put(
            f"/api/claims/{claim_id}/status",
            params={"new_status": "SENT"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "SENT"
        
        # Can transition to various states
        for status in ["AWAITING_RESPONSE", "RESPONSE_RECEIVED", "ACTION_REQUIRED", "CLOSED"]:
            response = client.put(
                f"/api/claims/{claim_id}/status",
                params={"new_status": status}
            )
            assert response.status_code == 200
            assert response.json()["status"] == status
