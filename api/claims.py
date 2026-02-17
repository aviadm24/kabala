"""
API endpoints for claim management and email operations.

Provides endpoints for:
- Creating and managing claims
- Sending claim emails to insurance companies  
- Attaching documents to claims
- Managing claim statuses
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Form, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid
import json
import logging
import requests
import base64
    
from database import SessionLocal
from models import Claim, ClaimEmail, ClaimStatus, EmailDirection, User, Receipt
from services.email_service import ResendClient, EmailTemplates, ResendAPIError
from depts import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/claims",
    tags=["claims"],
)


# ============================================================================
# Pydantic models for request/response
# ============================================================================

from pydantic import BaseModel


class ClaimCreate(BaseModel):
    """Request to create a new claim"""

    user_id: int
    insurance_company: str
    insurance_contact_email: str
    claim_amount: Optional[str] = None
    document_summary: Optional[str] = None


class ClaimResponse(BaseModel):
    """Response with claim details"""

    id: int
    public_id: str
    user_id: int
    reply_email: str
    status: str
    insurance_company: str
    insurance_contact_email: str
    created_at: datetime
    updated_at: datetime
    last_inbound_at: Optional[datetime]

    class Config:
        from_attributes = True


class SendClaimEmailRequest(BaseModel):
    """Request to send a claim email"""

    claim_id: int
    receipt_public_id: Optional[str] = None
    subject: Optional[str] = None
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    cc_user_email: bool = True


class ClaimEmailResponse(BaseModel):
    """Response from email operation"""

    id: int
    claim_id: int
    direction: str
    message_id: Optional[str]
    sender: str
    recipient: str
    subject: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Helper functions
# ============================================================================


def generate_public_id() -> str:
    """Generate a short unique ID for claims (for email addresses)"""
    # Generate 8 character alphanumeric ID
    return str(uuid.uuid4()).replace("-", "")[:8]


def generate_reply_email(public_id: str, domain: str = None) -> str:
    """Generate claim-specific reply email address"""
    from services.email_service import EMAIL_DOMAIN

    if not domain:
        domain = EMAIL_DOMAIN
    return f"claim-{public_id}@{domain}"


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/create", response_model=ClaimResponse)
def create_claim(
    claim_data: ClaimCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new insurance claim.
    
    This creates a claim record and generates a unique reply email address
    for the email loop closure system.
    """
    # Verify user exists
    user = db.query(User).filter(User.user_id == claim_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Generate public ID and reply email
    public_id = generate_public_id()
    reply_email = generate_reply_email(public_id)

    # Create claim
    claim = Claim(
        public_id=public_id,
        user_id=claim_data.user_id,
        reply_email=reply_email,
        status=ClaimStatus.DRAFT,
        insurance_company=claim_data.insurance_company,
        insurance_contact_email=claim_data.insurance_contact_email,
    )

    db.add(claim)
    db.commit()
    db.refresh(claim)

    logger.info(f"Created claim {claim.public_id} for user {claim_data.user_id}")

    return claim


@router.get("/{claim_id}", response_model=ClaimResponse)
def get_claim(claim_id: int, db: Session = Depends(get_db)):
    """Retrieve claim details"""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


@router.get("", response_model=List[ClaimResponse])
def list_claims(
    user_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    List claims with optional filtering.
    
    Query parameters:
    - user_id: Filter by user
    - status: Filter by claim status
    """
    query = db.query(Claim)

    if user_id:
        query = query.filter(Claim.user_id == user_id)

    if status:
        query = query.filter(Claim.status == status)

    return query.order_by(Claim.created_at.desc()).all()


@router.post("/{claim_id}/send-email", response_model=ClaimEmailResponse)
def send_claim_email(
    claim_id: int,
    request_data: SendClaimEmailRequest,
    db: Session = Depends(get_db),
):
    """
    Send an email to the insurance company for this claim.
    
    This endpoint:
    1. Generates the email content
    2. Sends via Resend API with Reply-To set to the claim's unique reply email
    3. Stores the message ID for tracking
    4. Updates claim status to AWAITING_RESPONSE
    """
    # Get claim
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Get user for CC
    user = db.query(User).filter(User.user_id == claim.user_id).first()

    # Generate email content
    from services.email_service import CLAIMS_FROM_EMAIL

    subject = request_data.subject or f"Insurance Claim Submission - {claim.public_id}"
    
    # Use provided body or generate from template
    if request_data.body_html:
        body_html = request_data.body_html
    else:
        body_html = EmailTemplates.claim_submission_html(
            claim_id=claim.public_id,
            insurance_company=claim.insurance_company,
        )

    if request_data.body_text:
        body_text = request_data.body_text
    else:
        body_text = EmailTemplates.claim_submission_text(
            claim_id=claim.public_id,
            insurance_company=claim.insurance_company,
        )

    # Prepare email parameters
    cc_list = [user.email] if (request_data.cc_user_email and user.email) else None
    
    # Get image URL from database
    image_url = None
    if request_data.receipt_public_id:
        receipt = db.query(Receipt).filter(Receipt.public_id == request_data.receipt_public_id).first()
        if receipt:
            image_url = receipt.secure_url

    # 1. Download image if URL exists
    encoded_file = None
    if image_url:
        try:
            response = requests.get(image_url)
            response.raise_for_status()
            encoded_file = base64.b64encode(response.content).decode("utf-8")
        except Exception as e:
            logger.warning(f"Failed to download image from {image_url}: {str(e)}")

    # 2. Convert to base64
    try:
        # Send email via Resend
        client = ResendClient()
        
        # Build attachments if image exists
        attachments = []
        if encoded_file:
            attachments = [
                {
                    "filename": "receipt.jpg",
                    "content": encoded_file,
                }
            ]
        
        response = client.send_email(
            to=claim.insurance_contact_email,
            subject=subject,
            html=body_html,
            text=body_text,
            cc=cc_list,
            reply_to=claim.reply_email,
            from_email=CLAIMS_FROM_EMAIL,
            attachments=attachments,
        )

        message_id = response.get("id")

        # Store outbound email record
        claim_email = ClaimEmail(
            claim_id=claim.id,
            direction=EmailDirection.OUTBOUND,
            message_id=message_id,
            sender=CLAIMS_FROM_EMAIL,
            recipient=claim.insurance_contact_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )

        # Update claim
        claim.outbound_message_id = message_id
        claim.status = ClaimStatus.AWAITING_RESPONSE
        claim.updated_at = datetime.utcnow()

        db.add(claim_email)
        db.commit()
        db.refresh(claim_email)

        logger.info(
            f"Sent email for claim {claim.public_id}, "
            f"Message ID: {message_id}"
        )

        return claim_email

    except ResendAPIError as e:
        logger.error(f"Failed to send email for claim {claim_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


@router.put("/{claim_id}/status")
def update_claim_status(
    claim_id: int,
    new_status: str,
    db: Session = Depends(get_db),
):
    """Update claim status"""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    # Validate status
    try:
        claim.status = ClaimStatus(new_status)
    except ValueError:
        valid_statuses = [s.value for s in ClaimStatus]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )

    claim.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(claim)

    logger.info(f"Updated claim {claim.public_id} status to {new_status}")

    return {"id": claim.id, "status": claim.status}


@router.get("/{claim_id}/emails", response_model=List[ClaimEmailResponse])
def get_claim_emails(
    claim_id: int,
    direction: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Retrieve all emails for a claim.
    
    Query parameters:
    - direction: Filter by INBOUND or OUTBOUND
    """
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    query = db.query(ClaimEmail).filter(ClaimEmail.claim_id == claim_id)

    if direction:
        query = query.filter(ClaimEmail.direction == direction)

    return query.order_by(ClaimEmail.created_at.desc()).all()
