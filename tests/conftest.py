"""
Pytest configuration and shared fixtures.
"""

import os
import sys
import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
TESTS_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(TESTS_ROOT))

# Load environment variables from test .env file if it exists
TEST_ENV_FILE = PROJECT_ROOT / ".env.test"
if TEST_ENV_FILE.exists():
    load_dotenv(TEST_ENV_FILE)
else:
    load_dotenv()

from tests.config import get_config
from database import Base
from models import User, Receipt, Claim, ClaimEmail, ClaimStatus, EmailDirection
from depts import get_db
from main import app


@pytest.fixture(scope="session")
def test_config():
    """Get test configuration."""
    return get_config()


@pytest.fixture(scope="session")
def test_db_engine(test_config):
    """Create test database engine."""
    engine = create_engine(
        test_config.database_url,
        connect_args={"check_same_thread": False} if test_config.database_type.value == "sqlite" else {}
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup: drop all tables after tests
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_db_engine):
    """Create a fresh database session for each test."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = SessionLocal()
    
    yield session
    
    # Cleanup after test
    session.rollback()
    session.close()


@pytest.fixture
def client(db_session):
    """Create a test client with dependency override."""
    from fastapi.testclient import TestClient
    
    # Override the get_db dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    yield client
    
    # Clear overrides after test
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    user = User(
        username=f"testuser_{unique_id}",
        email=f"test_{unique_id}@example.com",
        phone="1234567890",
        family_members="Alice,Bob",
        insurance_companies="CompanyA,CompanyB",
        created_at="2025-01-01"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_receipt(db_session, sample_user):
    """Create a sample receipt for testing."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    receipt = Receipt(
        public_id=f"test_receipt_{unique_id}",
        resource_type="image",
        user_id=sample_user.user_id,
        username=sample_user.username,
        name="Test Receipt",
        date="2025-01-01",
        sent_to_insurance="no",
        insurance_company="CompanyA",
        account_username="testaccount",
        family_count=2,
        family_names="Alice,Bob",
        secure_url="https://example.com/image.jpg",
        created_at="2025-01-01"
    )
    db_session.add(receipt)
    db_session.commit()
    db_session.refresh(receipt)
    return receipt


@pytest.fixture
def sample_claim(db_session, sample_user):
    """Create a sample claim for testing."""
    import uuid
    from datetime import datetime
    unique_id = str(uuid.uuid4())[:8]
    claim = Claim(
        public_id=unique_id,
        user_id=sample_user.user_id,
        reply_email=f"claim-{unique_id}@mail.yourapp.com",
        status=ClaimStatus.DRAFT,
        insurance_company="Test Insurance Co",
        insurance_contact_email="claims@testinsurance.com",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(claim)
    db_session.commit()
    db_session.refresh(claim)
    return claim


@pytest.fixture
def sample_outbound_email(db_session, sample_claim):
    """Create a sample outbound email for testing."""
    import uuid
    from datetime import datetime
    unique_msg_id = f"msg_{str(uuid.uuid4())[:12]}"
    email = ClaimEmail(
        claim_id=sample_claim.id,
        direction=EmailDirection.OUTBOUND,
        message_id=unique_msg_id,
        sender="onboarding@resend.dev",
        recipient="claims@testinsurance.com",
        subject=f"Insurance Claim Submission - {sample_claim.public_id}",
        body_text="This is a test claim...",
        body_html="<p>This is a test claim...</p>",
        created_at=datetime.utcnow(),
    )
    db_session.add(email)
    db_session.commit()
    db_session.refresh(email)
    return email


@pytest.fixture
def sample_inbound_email(db_session, sample_claim):
    """Create a sample inbound email for testing."""
    import uuid
    from datetime import datetime
    import json
    unique_msg_id = f"msg_{str(uuid.uuid4())[:12]}"
    email = ClaimEmail(
        claim_id=sample_claim.id,
        direction=EmailDirection.INBOUND,
        message_id=unique_msg_id,
        sender="claims@testinsurance.com",
        recipient=sample_claim.reply_email,
        subject="Re: Insurance Claim Submission",
        body_text="Your claim has been approved.",
        body_html="<p>Your claim has been approved.</p>",
        raw_headers_json=json.dumps({"Message-ID": unique_msg_id, "From": "claims@testinsurance.com"}),
        created_at=datetime.utcnow(),
    )
    db_session.add(email)
    db_session.commit()
    db_session.refresh(email)
    return email


@pytest.fixture
def auth_cookies():
    """Generate signed auth cookies for testing."""
    from itsdangerous import URLSafeTimedSerializer
    SECRET_KEY = os.environ.get('SECRET_KEY', 'test-secret-key')
    serializer = URLSafeTimedSerializer(SECRET_KEY, salt='cookie-signer')
    
    user_id = "1"
    username = "testuser"
    
    return {
        "user_id": serializer.dumps(user_id),
        "username": serializer.dumps(username)
    }


# Pytest markers for test categorization
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "regression: mark test as a regression test")
    config.addinivalue_line("markers", "slow: mark test as slow")
    config.addinivalue_line("markers", "ocr: mark test as OCR-related")
    config.addinivalue_line("markers", "cloudinary: mark test as Cloudinary-related")
    config.addinivalue_line("markers", "production: mark test as production-only")


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on markers and config."""
    test_config = get_config()
    
    for item in items:
        # Skip slow tests if not explicitly requested
        if "slow" in item.keywords and not test_config.run_slow_tests:
            item.add_marker(pytest.mark.skip(reason="Slow tests disabled"))
        
        # Skip OCR tests if not explicitly requested
        if "ocr" in item.keywords and not test_config.run_ocr_tests:
            item.add_marker(pytest.mark.skip(reason="OCR tests disabled"))
        
        # Skip production tests if not in production
        if "production" in item.keywords and not test_config.is_production():
            item.add_marker(pytest.mark.skip(reason="Production tests only"))
        
        # Skip Cloudinary tests if not enabled
        if "cloudinary" in item.keywords and not test_config.use_cloudinary:
            item.add_marker(pytest.mark.skip(reason="Cloudinary tests disabled"))
