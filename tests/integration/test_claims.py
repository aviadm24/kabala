"""
Integration tests for claims API endpoints.

Tests cover:
- Claim creation
- Claim retrieval
- Claim listing with filtering
- Email sending workflow
- Status updates
- Email history retrieval
"""

import pytest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from models import Claim, ClaimStatus, ClaimEmail, EmailDirection


@pytest.mark.integration
class TestClaimsAPI:
    """Integration tests for claims API endpoints"""

    def test_create_claim_success(self, client, sample_user, db_session):
        """Test successful claim creation"""
        # Merge the user back into this session to avoid DetachedInstanceError
        user = db_session.merge(sample_user)
        user_id = user.user_id
        
        response = client.post(
            "/api/claims/create",
            json={
                "user_id": user_id,
                "insurance_company": "Test Insurance",
                "insurance_contact_email": "claims@testins.com",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "public_id" in data
        assert "reply_email" in data
        assert "status" in data
        
        # Verify data
        assert data["user_id"] == user_id
        assert data["insurance_company"] == "Test Insurance"
        assert data["insurance_contact_email"] == "claims@testins.com"
        assert data["status"] == "DRAFT"
        
        # Verify reply_email format
        assert data["reply_email"].startswith("claim-")
        # Domain depends on environment (resend.dev for test, mail.yourapp.com for prod)
        assert "@resend.dev" in data["reply_email"] or "@mail.yourapp.com" in data["reply_email"]
        
        # Verify claim was created in database
        claim = db_session.query(Claim).filter(
            Claim.id == data["id"]
        ).first()
        assert claim is not None
        assert claim.public_id == data["public_id"]

    def test_create_claim_user_not_found(self, client):
        """Test claim creation with invalid user"""
        response = client.post(
            "/api/claims/create",
            json={
                "user_id": 99999,
                "insurance_company": "Test Insurance",
                "insurance_contact_email": "claims@testins.com",
            }
        )
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    def test_get_claim_success(self, client, sample_claim):
        """Test retrieving claim details"""
        response = client.get(f"/api/claims/{sample_claim.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == sample_claim.id
        assert data["public_id"] == sample_claim.public_id
        assert data["user_id"] == sample_claim.user_id
        assert data["insurance_company"] == sample_claim.insurance_company

    def test_get_claim_not_found(self, client):
        """Test retrieving non-existent claim"""
        response = client.get("/api/claims/99999")
        
        assert response.status_code == 404
        assert "Claim not found" in response.json()["detail"]

    def test_list_claims_all(self, client, sample_user, db_session):
        """Test listing all claims"""
        # Create multiple claims
        claim1 = Claim(
            public_id="abc12345",
            user_id=sample_user.user_id,
            reply_email="claim-abc12345@mail.yourapp.com",
            status=ClaimStatus.DRAFT,
            insurance_company="Insurance A",
            insurance_contact_email="claims@a.com",
        )
        claim2 = Claim(
            public_id="def67890",
            user_id=sample_user.user_id,
            reply_email="claim-def67890@mail.yourapp.com",
            status=ClaimStatus.AWAITING_RESPONSE,
            insurance_company="Insurance B",
            insurance_contact_email="claims@b.com",
        )
        db_session.add(claim1)
        db_session.add(claim2)
        db_session.commit()
        
        response = client.get("/api/claims")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) >= 2

    def test_list_claims_filter_by_user(self, client, sample_user, db_session):
        """Test listing claims filtered by user"""
        # Create another user and their claim
        from models import User
        other_user = User(
            username="otheruser",
            email="other@example.com",
            created_at="2025-01-01"
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)
        
        # Create claims for both users
        claim1 = Claim(
            public_id="user1_claim",
            user_id=sample_user.user_id,
            reply_email="claim-user1@mail.yourapp.com",
            status=ClaimStatus.DRAFT,
            insurance_company="Insurance A",
            insurance_contact_email="claims@a.com",
        )
        claim2 = Claim(
            public_id="user2_claim",
            user_id=other_user.user_id,
            reply_email="claim-user2@mail.yourapp.com",
            status=ClaimStatus.DRAFT,
            insurance_company="Insurance B",
            insurance_contact_email="claims@b.com",
        )
        db_session.add(claim1)
        db_session.add(claim2)
        db_session.commit()
        
        # Query for specific user
        response = client.get(f"/api/claims?user_id={sample_user.user_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned claims should be for the specified user
        for claim in data:
            assert claim["user_id"] == sample_user.user_id

    def test_list_claims_filter_by_status(self, client, sample_user, db_session):
        """Test listing claims filtered by status"""
        # Create claims with different statuses
        claim1 = Claim(
            public_id="claim_draft",
            user_id=sample_user.user_id,
            reply_email="claim-draft@mail.yourapp.com",
            status=ClaimStatus.DRAFT,
            insurance_company="Insurance",
            insurance_contact_email="claims@ins.com",
        )
        claim2 = Claim(
            public_id="claim_sent",
            user_id=sample_user.user_id,
            reply_email="claim-sent@mail.yourapp.com",
            status=ClaimStatus.AWAITING_RESPONSE,
            insurance_company="Insurance",
            insurance_contact_email="claims@ins.com",
        )
        db_session.add(claim1)
        db_session.add(claim2)
        db_session.commit()
        
        # Query for specific status
        response = client.get(f"/api/claims?status={ClaimStatus.DRAFT.value}")
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned claims should have the specified status
        for claim in data:
            assert claim["status"] == ClaimStatus.DRAFT.value

    @patch("api.claims.ResendClient.send_email")
    def test_send_claim_email_success(self, mock_send, client, sample_claim, sample_user):
        """Test successful email sending"""
        mock_send.return_value = {"id": "msg_test_123"}
        
        response = client.post(
            f"/api/claims/{sample_claim.id}/send-email",
            json={
                "claim_id": sample_claim.id,
                "subject": "Test Subject",
                "cc_user_email": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response
        assert data["direction"] == "OUTBOUND"
        assert data["message_id"] == "msg_test_123"
        assert data["claim_id"] == sample_claim.id
        
        # Verify send_email was called
        mock_send.assert_called_once()

    @patch("api.claims.ResendClient.send_email")
    def test_send_claim_email_updates_status(self, mock_send, client, sample_claim, db_session):
        """Test that sending email updates claim status"""
        mock_send.return_value = {"id": "msg_123"}
        
        claim = db_session.merge(sample_claim)
        
        response = client.post(
            f"/api/claims/{claim.id}/send-email",
            json={"claim_id": claim.id, "cc_user_email": False}
        )
        
        assert response.status_code == 200
        
        # Refresh claim from database by re-querying
        updated_claim = db_session.query(Claim).filter(Claim.id == claim.id).first()
        
        # Verify status was updated
        assert updated_claim.status == ClaimStatus.AWAITING_RESPONSE
        assert updated_claim.outbound_message_id == "msg_123"

    @patch("api.claims.ResendClient.send_email")
    def test_send_claim_email_creates_record(self, mock_send, client, sample_claim, db_session):
        """Test that sending email creates ClaimEmail record"""
        mock_send.return_value = {"id": "msg_abc"}
        
        response = client.post(
            f"/api/claims/{sample_claim.id}/send-email",
            json={"claim_id": sample_claim.id}
        )
        
        assert response.status_code == 200
        
        # Verify ClaimEmail record exists
        email = db_session.query(ClaimEmail).filter(
            ClaimEmail.claim_id == sample_claim.id,
            ClaimEmail.direction == EmailDirection.OUTBOUND
        ).first()
        
        assert email is not None
        assert email.message_id == "msg_abc"
        assert email.direction == EmailDirection.OUTBOUND

    def test_send_claim_email_not_found(self, client):
        """Test sending email for non-existent claim"""
        response = client.post(
            "/api/claims/99999/send-email",
            json={"claim_id": 99999}
        )
        
        assert response.status_code == 404
        assert "Claim not found" in response.json()["detail"]

    def test_update_claim_status_success(self, client, sample_claim, db_session):
        """Test updating claim status"""
        new_status = ClaimStatus.RESPONSE_RECEIVED.value
        
        claim = db_session.merge(sample_claim)
        
        response = client.put(
            f"/api/claims/{claim.id}/status",
            params={"new_status": new_status}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == new_status
        
        # Verify database was updated by re-querying
        updated_claim = db_session.query(Claim).filter(Claim.id == claim.id).first()
        assert updated_claim.status == ClaimStatus.RESPONSE_RECEIVED

    def test_update_claim_status_invalid(self, client, sample_claim):
        """Test updating with invalid status"""
        response = client.put(
            f"/api/claims/{sample_claim.id}/status",
            params={"new_status": "INVALID_STATUS"}
        )
        
        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]

    def test_update_claim_status_not_found(self, client):
        """Test updating status for non-existent claim"""
        response = client.put(
            "/api/claims/99999/status",
            params={"new_status": "DRAFT"}
        )
        
        assert response.status_code == 404
        assert "Claim not found" in response.json()["detail"]

    def test_get_claim_emails_all(self, client, sample_claim, sample_outbound_email, sample_inbound_email):
        """Test retrieving all emails for a claim"""
        response = client.get(f"/api/claims/{sample_claim.id}/emails")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) >= 2
        directions = [email["direction"] for email in data]
        assert EmailDirection.OUTBOUND.value in directions
        assert EmailDirection.INBOUND.value in directions

    def test_get_claim_emails_filter_outbound(self, client, sample_claim, sample_outbound_email, sample_inbound_email):
        """Test filtering emails by direction (outbound)"""
        response = client.get(
            f"/api/claims/{sample_claim.id}/emails?direction={EmailDirection.OUTBOUND.value}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned emails should be outbound
        for email in data:
            assert email["direction"] == EmailDirection.OUTBOUND.value

    def test_get_claim_emails_filter_inbound(self, client, sample_claim, sample_outbound_email, sample_inbound_email):
        """Test filtering emails by direction (inbound)"""
        response = client.get(
            f"/api/claims/{sample_claim.id}/emails?direction={EmailDirection.INBOUND.value}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned emails should be inbound
        for email in data:
            assert email["direction"] == EmailDirection.INBOUND.value

    def test_get_claim_emails_not_found(self, client):
        """Test retrieving emails for non-existent claim"""
        response = client.get("/api/claims/99999/emails")
        
        assert response.status_code == 404
        assert "Claim not found" in response.json()["detail"]
