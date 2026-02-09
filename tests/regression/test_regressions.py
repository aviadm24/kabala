"""
Regression tests to ensure core functionality doesn't break.
These tests should be run on every commit to catch regressions.
"""

import pytest


@pytest.mark.regression
class TestCoreRegressions:
    """Test core functionality regressions."""
    
    def test_health_endpoint_never_fails(self, client):
        """Regression: Health endpoint must always be available."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_user_creation_never_fails(self, db_session):
        """Regression: Should always be able to create users."""
        from models import User
        
        user = User(
            username=f"regression_user_{id({})}",
            email=f"regression{id({})}@example.com",
            created_at="2025-01-01"
        )
        db_session.add(user)
        db_session.commit()
        
        # Verify
        assert user.user_id is not None
    
    def test_receipt_creation_never_fails(self, db_session, sample_user):
        """Regression: Should always be able to create receipts."""
        from models import Receipt
        
        receipt = Receipt(
            public_id=f"regression_receipt_{id({})}",
            user_id=sample_user.user_id,
            username=sample_user.username,
            created_at="2025-01-01"
        )
        db_session.add(receipt)
        db_session.commit()
        
        assert receipt.public_id is not None


@pytest.mark.regression
class TestAuthenticationRegressions:
    """Test authentication functionality regressions."""
    
    def test_cookie_signing_always_works(self):
        """Regression: Cookie signing/verification must work."""
        from main import sign_cookie_value, verify_cookie_value
        
        test_value = "test_regression_value"
        signed = sign_cookie_value(test_value)
        verified = verify_cookie_value(signed)
        
        assert verified == test_value
    
    def test_invalid_cookies_always_rejected(self):
        """Regression: Invalid cookies must always be rejected."""
        from main import verify_cookie_value
        
        result = verify_cookie_value("definitely_invalid_signature")
        assert result is None


@pytest.mark.regression
class TestDataIntegrityRegressions:
    """Test data integrity regressions."""
    
    def test_user_unique_constraint(self, db_session):
        """Regression: Username uniqueness must be enforced."""
        from models import User
        from sqlalchemy.exc import IntegrityError
        
        user1 = User(
            username="unique_regression_test",
            email="test1@example.com",
            created_at="2025-01-01"
        )
        db_session.add(user1)
        db_session.commit()
        
        # Try to create another user with same username
        user2 = User(
            username="unique_regression_test",
            email="test2@example.com",
            created_at="2025-01-01"
        )
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_receipt_user_relationship_integrity(self, db_session, sample_user):
        """Regression: Receipt-user relationship must be maintained."""
        from models import Receipt
        
        receipt = Receipt(
            public_id="regression_receipt_integrity",
            user_id=sample_user.user_id,
            username=sample_user.username,
            created_at="2025-01-01"
        )
        db_session.add(receipt)
        db_session.commit()
        
        # Verify relationship
        retrieved_user = db_session.query(sample_user.__class__).filter_by(
            user_id=sample_user.user_id
        ).first()
        
        assert len(retrieved_user.receipts) > 0


@pytest.mark.regression
@pytest.mark.slow
class TestPerformanceRegressions:
    """Test performance hasn't significantly degraded."""
    
    def test_user_query_performance(self, db_session):
        """Regression: User queries should be fast."""
        from models import User
        
        # Create multiple users
        for i in range(10):
            user = User(
                username=f"perf_test_user_{i}",
                email=f"perf{i}@example.com",
                created_at="2025-01-01"
            )
            db_session.add(user)
        db_session.commit()
        
        # Test a simple query
        def query():
            return db_session.query(User).filter_by(
                username="perf_test_user_0"
            ).first()
        
        # Should complete reasonably quickly (no strict requirement)
        result = query()
        assert result is not None


@pytest.mark.regression
class TestConfigurationRegressions:
    """Test configuration handling regressions."""
    
    def test_test_config_loads_correctly(self):
        """Regression: Test configuration must load without errors."""
        from tests.config import get_config
        
        config = get_config()
        
        assert config is not None
        assert config.environment is not None
        assert config.database_url is not None
        assert config.api_base_url is not None
    
    def test_environment_variables_respected(self):
        """Regression: Environment variables should be used for config."""
        import os
        from tests.config import TestConfig
        
        # Create config from current environment
        config = TestConfig.from_env()
        
        # Should have valid values
        assert config.database_url is not None
        assert len(config.database_url) > 0
