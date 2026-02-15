"""
LangGraph workflow nodes for claim processing.

Each node represents a step in the claim processing workflow:
- Document generation
- Email sending
- Response waiting
- Response processing
- Decision making
"""

from typing import Any
from datetime import datetime
import logging
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Claim, ClaimEmail, ClaimStatus
from workflows.claim_state import ClaimWorkflowState
from services.email_service import ResendClient, EmailTemplates

logger = logging.getLogger(__name__)


def generate_documents_node(state: ClaimWorkflowState) -> ClaimWorkflowState:
    """
    Generate claim documents (PDF, summary, etc.)
    
    In a real implementation, this would:
    1. Fetch claim receipts/documents
    2. Generate formatted PDFs
    3. Create document summary
    4. Store generated files
    
    For now, this is a placeholder that prepares email content.
    """
    logger.info(f"[GenerateDocuments] Processing claim {state['claim_public_id']}")
    
    # Get the claim from database
    db = SessionLocal()
    try:
        claim = db.query(Claim).filter(
            Claim.public_id == state['claim_public_id']
        ).first()
        
        if not claim:
            state['errors'].append(f"Claim not found: {state['claim_public_id']}")
            return state
        
        # Generate email content using templates
        state['email_subject'] = f"Insurance Claim Submission - {state['claim_public_id']}"
        
        state['email_html'] = EmailTemplates.claim_submission_html(
            claim_id=claim.public_id,
            insurance_company=claim.insurance_company,
        )
        
        state['email_text'] = EmailTemplates.claim_submission_text(
            claim_id=claim.public_id,
            insurance_company=claim.insurance_company,
        )
        
        state['workflow_stage'] = "documents_generated"
        logger.info(f"[GenerateDocuments] Completed for claim {state['claim_public_id']}")
        
    finally:
        db.close()
    
    return state


def send_email_node(state: ClaimWorkflowState) -> ClaimWorkflowState:
    """
    Send email to insurance company via Resend.
    
    This node:
    1. Formats email with proper headers
    2. Sends via Resend with reply-to set to claim's unique email
    3. Stores message ID
    4. Updates claim status
    """
    logger.info(f"[SendEmail] Sending for claim {state['claim_public_id']}")
    
    # Validate prerequisites
    if not state['email_html'] or not state['email_subject']:
        state['errors'].append("Email content not prepared")
        return state
    
    db = SessionLocal()
    try:
        claim = db.query(Claim).filter(
            Claim.public_id == state['claim_public_id']
        ).first()
        
        if not claim:
            state['errors'].append(f"Claim not found: {state['claim_public_id']}")
            return state
        
        # Prepare CC list
        cc_list = [state['user_email']] if state['user_email'] else []
        
        # Send via Resend
        client = ResendClient()
        response = client.send_email(
            to=state['insurance_contact_email'],
            subject=state['email_subject'],
            html=state['email_html'],
            text=state['email_text'],
            cc=cc_list if cc_list else None,
            reply_to=claim.reply_email,
        )
        
        message_id = response.get("id")
        state['outbound_message_id'] = message_id
        state['email_sent_at'] = datetime.utcnow()
        
        # Update claim in database
        claim.outbound_message_id = message_id
        claim.status = ClaimStatus.AWAITING_RESPONSE
        claim.updated_at = datetime.utcnow()
        
        db.commit()
        state['claim_status'] = ClaimStatus.AWAITING_RESPONSE.value
        state['workflow_stage'] = "email_sent"
        
        logger.info(
            f"[SendEmail] Sent for claim {state['claim_public_id']}, "
            f"Message ID: {message_id}"
        )
        
    except Exception as e:
        state['errors'].append(f"Failed to send email: {str(e)}")
        logger.error(f"[SendEmail] Error: {str(e)}", exc_info=True)
    finally:
        db.close()
    
    return state


def process_inbound_response_node(state: ClaimWorkflowState) -> ClaimWorkflowState:
    """
    Process inbound email response.
    
    This node extracts and structures information from the inbound email:
    1. Parse sender and subject
    2. Extract key content
    3. Handle attachments
    4. Flag for AI processing
    """
    logger.info(f"[ProcessInboundResponse] Processing for claim {state['claim_public_id']}")
    
    if not state['inbound_message_id']:
        state['errors'].append("No inbound message to process")
        return state
    
    db = SessionLocal()
    try:
        claim = db.query(Claim).filter(
            Claim.public_id == state['claim_public_id']
        ).first()
        
        if not claim:
            state['errors'].append(f"Claim not found: {state['claim_public_id']}")
            return state
        
        # Get the inbound email record
        email = db.query(ClaimEmail).filter(
            ClaimEmail.message_id == state['inbound_message_id']
        ).first()
        
        if not email:
            state['errors'].append(f"Inbound email not found: {state['inbound_message_id']}")
            return state
        
        # Extract structured data
        state['inbound_sender'] = email.sender
        state['inbound_subject'] = email.subject
        state['inbound_body_text'] = email.body_text
        state['inbound_body_html'] = email.body_html
        state['inbound_received_at'] = email.created_at
        
        state['workflow_stage'] = "inbound_processed"
        logger.info(f"[ProcessInboundResponse] Processed for claim {state['claim_public_id']}")
        
    except Exception as e:
        state['errors'].append(f"Failed to process inbound response: {str(e)}")
        logger.error(f"[ProcessInboundResponse] Error: {str(e)}", exc_info=True)
    finally:
        db.close()
    
    return state


def parse_intent_node(state: ClaimWorkflowState) -> ClaimWorkflowState:
    """
    Use AI/LLM to parse the insurance company's response.
    
    This node would typically use Claude or another LLM to:
    1. Determine intent (APPROVED, REJECTED, MORE_INFO_NEEDED, etc.)
    2. Extract key information
    3. Generate confidence score
    4. Summarize response
    
    This is a placeholder - integrate with your LLM provider.
    """
    logger.info(f"[ParseIntent] Analyzing response for claim {state['claim_public_id']}")
    
    if not state['inbound_body_text']:
        state['errors'].append("No inbound body text to analyze")
        return state
    
    # TODO: Integrate with LLM
    # For now, use simple heuristics
    text = state['inbound_body_text'].lower()
    
    if any(word in text for word in ['approve', 'approved', 'accept']):
        state['response_intent'] = "APPROVED"
        state['response_confidence'] = 0.85
    elif any(word in text for word in ['reject', 'rejected', 'deny', 'denied']):
        state['response_intent'] = "REJECTED"
        state['response_confidence'] = 0.85
    elif any(word in text for word in ['more info', 'additional', 'required']):
        state['response_intent'] = "MORE_INFO_NEEDED"
        state['response_confidence'] = 0.80
    else:
        state['response_intent'] = "UNCLEAR"
        state['response_confidence'] = 0.50
    
    state['response_summary'] = f"Intent: {state['response_intent']} (confidence: {state['response_confidence']})"
    state['workflow_stage'] = "intent_parsed"
    
    logger.info(
        f"[ParseIntent] Parsed intent: {state['response_intent']} "
        f"(confidence: {state['response_confidence']})"
    )
    
    return state


def decide_next_action_node(state: ClaimWorkflowState) -> ClaimWorkflowState:
    """
    Determine the next action based on the response.
    
    Routes to appropriate next steps:
    - APPROVED: Mark claim as closed, notify user
    - REJECTED: Escalate for review, notify user
    - MORE_INFO_NEEDED: Prepare response with additional info
    - UNCLEAR: Route to human review
    """
    logger.info(f"[DecideNextAction] For claim {state['claim_public_id']}")
    
    if not state['response_intent']:
        state['errors'].append("No response intent determined")
        state['action_required'] = "ESCALATE_HUMAN_REVIEW"
        return state
    
    intent = state['response_intent']
    
    if intent == "APPROVED":
        state['action_required'] = "CLOSE_CLAIM"
        state['claim_status'] = ClaimStatus.CLOSED.value
    elif intent == "REJECTED":
        state['action_required'] = "ESCALATE_HUMAN_REVIEW"
        state['claim_status'] = ClaimStatus.ACTION_REQUIRED.value
    elif intent == "MORE_INFO_NEEDED":
        state['action_required'] = "PREPARE_RESPONSE"
        state['claim_status'] = ClaimStatus.ACTION_REQUIRED.value
    else:
        state['action_required'] = "ESCALATE_HUMAN_REVIEW"
        state['claim_status'] = ClaimStatus.ACTION_REQUIRED.value
    
    state['workflow_stage'] = "action_decided"
    logger.info(f"[DecideNextAction] Decision: {state['action_required']}")
    
    return state


def update_claim_status_node(state: ClaimWorkflowState) -> ClaimWorkflowState:
    """
    Update claim status in database and notify user.
    
    This is an async node that would trigger:
    1. Database update
    2. User notifications (email, in-app)
    3. Event logging
    """
    logger.info(f"[UpdateClaimStatus] For claim {state['claim_public_id']}")
    
    db = SessionLocal()
    try:
        claim = db.query(Claim).filter(
            Claim.public_id == state['claim_public_id']
        ).first()
        
        if not claim:
            state['errors'].append(f"Claim not found: {state['claim_public_id']}")
            return state
        
        # Update status
        try:
            claim.status = ClaimStatus(state['claim_status'])
            claim.updated_at = datetime.utcnow()
            db.commit()
            logger.info(f"[UpdateClaimStatus] Updated claim {state['claim_public_id']} to {state['claim_status']}")
        except ValueError:
            state['errors'].append(f"Invalid status: {state['claim_status']}")
        
        state['workflow_stage'] = "completed"
        
        # TODO: Send user notification
        # notify_user(claim, state['action_required'], state['response_summary'])
        
    except Exception as e:
        state['errors'].append(f"Failed to update claim status: {str(e)}")
        logger.error(f"[UpdateClaimStatus] Error: {str(e)}", exc_info=True)
    finally:
        db.close()
    
    return state
