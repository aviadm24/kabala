"""
Unit tests for core application functions.
"""

import pytest
from datetime import datetime
import re
from main import safe_public_id, sign_cookie_value, verify_cookie_value, get_verified_cookies
from fastapi import Request


@pytest.mark.unit
class TestSafePublicId:
    """Test safe_public_id function."""
    
    def test_safe_public_id_basic(self):
        """Test basic safe_public_id creation."""
        result = safe_public_id("Receipt", "2025-01-15")
        assert result == "Receipt_2025-01-15"
    
    def test_safe_public_id_with_spaces(self):
        """Test safe_public_id with spaces in name."""
        result = safe_public_id("My Receipt", "2025-01-15")
        assert result == "My_Receipt_2025-01-15"
        assert " " not in result
    
    def test_safe_public_id_with_special_chars(self):
        """Test safe_public_id removes special characters."""
        result = safe_public_id("Receipt@#$", "2025-01-15")
        assert result == "Receipt_2025-01-15"
        assert not re.search(r'[^A-Za-z0-9_\-]', result)
    
    def test_safe_public_id_max_length(self):
        """Test safe_public_id respects max length."""
        long_name = "A" * 300
        result = safe_public_id(long_name, "2025-01-15")
        assert len(result) <= 200
    
    def test_safe_public_id_hyphen_preserved(self):
        """Test safe_public_id preserves hyphens."""
        result = safe_public_id("Receipt-001", "2025-01-15")
        assert "Receipt-001" in result


@pytest.mark.unit
class TestCookieSigning:
    """Test cookie signing/verification functions."""
    
    def test_sign_and_verify_cookie(self):
        """Test signing and verifying a cookie value."""
        original = "test_user_123"
        signed = sign_cookie_value(original)
        
        # Signed value should be different from original
        assert signed != original
        
        # Should verify correctly
        verified = verify_cookie_value(signed)
        assert verified == original
    
    def test_verify_invalid_signature(self):
        """Test that invalid signature returns None."""
        result = verify_cookie_value("invalid_signature")
        assert result is None
    
    def test_verify_tampered_cookie(self):
        """Test that tampered cookie returns None."""
        original = "test_user_123"
        signed = sign_cookie_value(original)
        
        # Tamper with the cookie
        tampered = signed[:-5] + "XXXXX"
        
        result = verify_cookie_value(tampered)
        assert result is None
    
    def test_sign_empty_value(self):
        """Test signing an empty value."""
        signed = sign_cookie_value("")
        verified = verify_cookie_value(signed)
        assert verified == ""


@pytest.mark.unit
class TestGetVerifiedCookies:
    """Test get_verified_cookies function."""
    
    def test_get_verified_cookies_valid(self, auth_cookies):
        """Test getting valid verified cookies."""
        # Mock request with cookies
        from unittest.mock import Mock
        
        request = Mock(spec=Request)
        request.cookies = {
            "user_id": auth_cookies["user_id"],
            "username": auth_cookies["username"]
        }
        
        user_id, username = get_verified_cookies(request)
        
        assert user_id == "1"
        assert username == "testuser"
    
    def test_get_verified_cookies_missing(self):
        """Test getting cookies when they're missing."""
        from unittest.mock import Mock
        
        request = Mock(spec=Request)
        request.cookies = {}
        
        user_id, username = get_verified_cookies(request)
        
        assert user_id is None
        assert username is None
    
    def test_get_verified_cookies_invalid(self):
        """Test getting cookies with invalid signatures."""
        from unittest.mock import Mock
        
        request = Mock(spec=Request)
        request.cookies = {
            "user_id": "invalid_signature",
            "username": "invalid_signature"
        }
        
        user_id, username = get_verified_cookies(request)
        
        assert user_id is None
        assert username is None
    
    def test_get_verified_cookies_partial(self, auth_cookies):
        """Test getting cookies when only one is valid."""
        from unittest.mock import Mock
        
        request = Mock(spec=Request)
        request.cookies = {
            "user_id": auth_cookies["user_id"],
            "username": "invalid_signature"
        }
        
        user_id, username = get_verified_cookies(request)
        
        assert user_id == "1"
        assert username is None


@pytest.mark.unit
class TestModels:
    """Test database models."""
    
    def test_user_creation(self, db_session):
        """Test creating a user."""
        from models import User
        
        user = User(
            username="newuser",
            email="new@example.com",
            phone="9876543210",
            created_at="2025-01-01"
        )
        db_session.add(user)
        db_session.commit()
        
        # Verify it was created
        retrieved = db_session.query(User).filter_by(username="newuser").first()
        assert retrieved is not None
        assert retrieved.email == "new@example.com"
    
    def test_receipt_creation(self, db_session, sample_user):
        """Test creating a receipt."""
        from models import Receipt
        
        receipt = Receipt(
            public_id="test_receipt_002",
            user_id=sample_user.user_id,
            username=sample_user.username,
            name="New Receipt",
            date="2025-01-02",
            created_at="2025-01-02"
        )
        db_session.add(receipt)
        db_session.commit()
        
        # Verify it was created and linked
        retrieved = db_session.query(Receipt).filter_by(public_id="test_receipt_002").first()
        assert retrieved is not None
        assert retrieved.user_id == sample_user.user_id
    
    def test_user_receipt_relationship(self, db_session, sample_user, sample_receipt):
        """Test user-receipt relationship."""
        # Refresh to load relationship
        db_session.refresh(sample_user)
        
        assert len(sample_user.receipts) > 0
        assert sample_receipt in sample_user.receipts


@pytest.mark.unit
class TestEnvironmentVariables:
    """Test environment variable handling."""
    
    def test_cloudinary_config(self):
        """Test Cloudinary configuration."""
        import os
        from main import cloudinary
        
        # Cloudinary should be configured (even if with None values)
        assert cloudinary is not None


@pytest.mark.unit
class TestStringFormatting:
    """Test string formatting utilities."""
    
    def test_safe_public_id_unicode(self):
        """Test safe_public_id with unicode characters."""
        result = safe_public_id("Réceipt_ñ", "2025-01-15")
        # Should handle unicode by removing non-ASCII
        assert len(result) > 0
        assert not any(ord(c) > 127 for c in result if c not in "2025-01-15_-")
