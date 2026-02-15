from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
from enum import Enum


class ClaimStatus(str, Enum):
    """Claim status state machine"""
    DRAFT = "DRAFT"
    READY_TO_SEND = "READY_TO_SEND"
    SENT = "SENT"
    AWAITING_RESPONSE = "AWAITING_RESPONSE"
    RESPONSE_RECEIVED = "RESPONSE_RECEIVED"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    CLOSED = "CLOSED"


class EmailDirection(str, Enum):
    """Email direction: inbound or outbound"""
    OUTBOUND = "OUTBOUND"
    INBOUND = "INBOUND"

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    phone = Column(String)
    email = Column(String)
    family_members = Column(Text)
    insurance_companies = Column(Text)
    created_at = Column(String)

    receipts = relationship("Receipt", back_populates="user")
    claims = relationship("Claim", back_populates="user")


class Receipt(Base):
    __tablename__ = "receipts"

    public_id = Column(String, primary_key=True)
    resource_type = Column(String)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    username = Column(String)
    name = Column(String)
    date = Column(String)
    sent_to_insurance = Column(String)
    refund_details = Column(Text)
    insurance_company = Column(String)
    account_username = Column(String)
    family_count = Column(Integer)
    family_names = Column(Text)
    how_work = Column(Text)
    secure_url = Column(String)
    created_at = Column(String)

    user = relationship("User", back_populates="receipts")


class Claim(Base):
    """Insurance claim with email loop closure"""
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    
    # Email loop fields
    reply_email = Column(String, nullable=False, index=True)  # claim-{public_id}@mail.yourapp.com
    outbound_message_id = Column(String, nullable=True)  # Resend message ID for tracking
    
    # Claim metadata
    status = Column(SQLEnum(ClaimStatus), default=ClaimStatus.DRAFT, index=True)
    insurance_company = Column(String)
    insurance_contact_email = Column(String)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_inbound_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="claims")
    emails = relationship("ClaimEmail", back_populates="claim", cascade="all, delete-orphan")


class ClaimEmail(Base):
    """Inbound and outbound emails for a claim"""
    __tablename__ = "claim_emails"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False, index=True)
    
    # Email metadata
    direction = Column(SQLEnum(EmailDirection), nullable=False, index=True)
    message_id = Column(String, nullable=True, index=True)  # Resend message ID or email Message-ID header
    
    # Email content
    sender = Column(String, nullable=False)
    recipient = Column(String, nullable=False)
    subject = Column(String)
    body_text = Column(Text)
    body_html = Column(Text)
    
    # Attachments and headers
    attachments_json = Column(Text, nullable=True)  # JSON list of attachment metadata
    raw_headers_json = Column(Text, nullable=True)  # JSON of raw email headers
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    claim = relationship("Claim", back_populates="emails")

