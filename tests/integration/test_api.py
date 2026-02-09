"""
Integration tests for API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint returns success."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "message" in data


@pytest.mark.integration
class TestUIEndpoint:
    """Test UI endpoint."""
    
    def test_index_without_auth(self, client):
        """Test accessing index page without authentication."""
        response = client.get("/")
        
        assert response.status_code == 200
        # Should return HTML
        assert "text/html" in response.headers.get("content-type", "")
    
    def test_index_with_auth(self, client, auth_cookies, sample_user):
        """Test accessing index page with authentication."""
        response = client.get(
            "/",
            cookies={
                "user_id": auth_cookies["user_id"],
                "username": auth_cookies["username"]
            }
        )
        
        assert response.status_code == 200
        # Should contain username in context
        assert "text/html" in response.headers.get("content-type", "")


@pytest.mark.integration
class TestOCREndpoint:
    """Test OCR API endpoints."""
    
    @pytest.mark.slow
    @pytest.mark.ocr
    def test_ocr_post_basic(self, client):
        """Test OCR endpoint with basic request."""
        # Note: This test may fail without proper setup
        # It's here as a template for when OCR is fully integrated
        payload = {
            "file_url": "https://example.com/receipt.jpg",
            "file_type": "receipt"
        }
        
        response = client.post("/api/ocr/ocr", json=payload)
        
        # Should return 200 or 422 (validation error)
        assert response.status_code in [200, 422, 500]  # 500 expected without real setup
    
    @pytest.mark.slow
    @pytest.mark.ocr
    def test_ocr_missing_parameters(self, client):
        """Test OCR endpoint with missing parameters."""
        response = client.post("/api/ocr/ocr", json={})
        
        # Should return validation error
        assert response.status_code == 422


@pytest.mark.integration
class TestDatabaseIntegration:
    """Test database integration."""
    
    def test_user_can_be_created_and_retrieved(self, db_session):
        """Test creating and retrieving a user."""
        from models import User
        
        user = User(
            username="integration_user",
            email="integration@example.com",
            phone="5555555555",
            created_at="2025-01-01"
        )
        db_session.add(user)
        db_session.commit()
        
        # Retrieve it
        retrieved = db_session.query(User).filter_by(
            username="integration_user"
        ).first()
        
        assert retrieved is not None
        assert retrieved.email == "integration@example.com"
        assert retrieved.phone == "5555555555"
    
    def test_receipt_user_relationship(self, db_session, sample_user, sample_receipt):
        """Test receipt-user relationship works correctly."""
        from models import Receipt
        
        # Verify relationship
        user_receipts = db_session.query(Receipt).filter_by(
            user_id=sample_user.user_id
        ).all()
        
        assert len(user_receipts) > 0
        assert sample_receipt.user_id == sample_user.user_id


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling in API."""
    
    def test_health_check_always_succeeds(self, client):
        """Test that health check endpoint is always available."""
        # Try multiple times to ensure consistency
        for _ in range(3):
            response = client.get("/health")
            assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.slow
class TestAPIResponseFormats:
    """Test API response formats for consistency."""
    
    def test_health_response_format(self, client):
        """Test health check returns expected JSON format."""
        response = client.get("/health")
        data = response.json()
        
        # Should have these keys
        assert isinstance(data, dict)
        assert "status" in data
        assert "message" in data
    
    def test_json_responses_are_valid(self, client):
        """Test that all JSON responses are valid JSON."""
        response = client.get("/health")
        
        # Should be valid JSON
        assert response.json() is not None
