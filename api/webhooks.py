"""
Webhook handlers for inbound emails from Resend.

This module handles:
- Inbound email webhook validation
- Parsing claim ID from reply-to address
- Storing inbound emails
- Updating claim status
- Triggering workflow continuation (async)
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import json
import logging
import re

from database import SessionLocal
from models import Claim, ClaimEmail, ClaimStatus, EmailDirection
from services.email_service import ResendClient
from depts import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/webhooks",
    tags=["webhooks"],
)


# ============================================================================
# Webhook handlers
# ============================================================================


@router.post("/email-inbound")
async def handle_inbound_email(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handle inbound emails from Resend webhook.
    
    Resend sends inbound emails that arrive at configured inbound domains
    to this endpoint. We need to:
    
    1. Validate the webhook signature
    2. Extract claim ID from recipient address (claim-{public_id}@...)
    3. Find the claim in database
    4. Store the inbound email
    5. Update claim status to RESPONSE_RECEIVED
    6. Trigger workflow continuation (async)
    
    Webhook payload structure (from Resend docs):
    {
        "type": "email_received",
        "created_at": "2024-01-01T12:00:00Z",
        "data": {
            "from_addr": "insurance@example.com",
            "to_addr": "claim-abc12345@mail.yourapp.com",
            "subject": "Re: Claim Submission",
            "text": "...",
            "html": "...",
            "reply_to": "...",
            "cc": [...],
            "bcc": [...],
            "raw_email": "...",
            "headers": {...},
            "attachments": [...]
        }
    }
    """
    # Get raw body for signature validation
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8")

    # Get signature header
    signature = request.headers.get("x-resend-signature", "")

    # Validate webhook signature
    client = ResendClient()
    if not client.validate_webhook_signature(signature, body_str):
        logger.warning("Invalid webhook signature received")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    try:
        payload = json.loads(body_str)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse webhook payload: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Handle email_received event
    if payload.get("type") != "email_received":
        logger.info(f"Ignoring webhook event type: {payload.get('type')}")
        return {"status": "ignored", "type": payload.get("type")}

    try:
        data = payload.get("data", {})

        # Extract claim ID from recipient address
        to_addr = data.get("to_addr", "")
        claim_public_id = extract_claim_id_from_email(to_addr)

        if not claim_public_id:
            logger.warning(f"Could not extract claim ID from recipient: {to_addr}")
            # Still acknowledge receipt, but don't process
            return {
                "status": "error",
                "message": "Could not extract claim ID from recipient address",
            }

        # Find claim
        claim = (
            db.query(Claim)
            .filter(Claim.public_id == claim_public_id)
            .first()
        )

        if not claim:
            logger.warning(f"Claim not found: {claim_public_id}")
            # Acknowledge but don't process - claim may have been deleted
            return {
                "status": "error",
                "message": f"Claim not found: {claim_public_id}",
            }

        # Store inbound email
        claim_email = ClaimEmail(
            claim_id=claim.id,
            direction=EmailDirection.INBOUND,
            message_id=data.get("message_id"),
            sender=data.get("from_addr", ""),
            recipient=to_addr,
            subject=data.get("subject", ""),
            body_text=data.get("text", ""),
            body_html=data.get("html", ""),
            raw_headers_json=json.dumps(data.get("headers", {})),
        )

        # Store attachments if any
        if data.get("attachments"):
            attachments_metadata = [
                {
                    "filename": att.get("filename"),
                    "size": att.get("size"),
                    "content_type": att.get("content_type"),
                }
                for att in data.get("attachments", [])
            ]
            claim_email.attachments_json = json.dumps(attachments_metadata)

        # Update claim status and timestamp
        claim.status = ClaimStatus.RESPONSE_RECEIVED
        claim.last_inbound_at = datetime.utcnow()
        claim.updated_at = datetime.utcnow()

        db.add(claim_email)
        db.commit()
        db.refresh(claim_email)

        logger.info(
            f"Stored inbound email for claim {claim.public_id} "
            f"from {data.get('from_addr')}"
        )

        # TODO: Trigger workflow continuation asynchronously
        # This would integrate with LangGraph to continue the workflow
        # await trigger_claim_workflow_continuation(claim_id=claim.id, db=db)

        return {
            "status": "success",
            "claim_id": claim.id,
            "claim_public_id": claim.public_id,
            "email_id": claim_email.id,
        }

    except Exception as e:
        logger.error(f"Error processing inbound email webhook: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# Helper functions
# ============================================================================


def extract_claim_id_from_email(email_address: str) -> str:
    """
    Extract claim public ID from email address.
    
    Expected format: claim-{public_id}@{domain}
    Example: claim-abc12345@mail.yourapp.com
    
    Args:
        email_address: The email address to parse
        
    Returns:
        The public_id part, or empty string if not found
    """
    # Match pattern: claim-{alphanumeric}@
    match = re.match(r"claim-([a-zA-Z0-9]+)@", email_address)
    if match:
        return match.group(1)
    return ""
