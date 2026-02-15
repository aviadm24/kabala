"""
LangGraph workflow for insurance claim email processing.

This module defines the workflow for:
1. Generating claim documents and emails
2. Sending emails to insurance companies
3. Processing inbound responses
4. Making claims decisions

The workflow integrates with the email loop closure system.
"""

from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ClaimWorkflowState(TypedDict):
    """State representation for claim email workflow"""
    
    # Claim identity
    claim_id: int
    claim_public_id: str
    user_id: int
    
    # Email information
    insurance_company: str
    insurance_contact_email: str
    user_email: Optional[str]
    
    # Email content (outbound)
    email_subject: Optional[str]
    email_html: Optional[str]
    email_text: Optional[str]
    
    # Email sending
    outbound_message_id: Optional[str]
    email_sent_at: Optional[datetime]
    
    # Inbound response handling
    inbound_message_id: Optional[str]
    inbound_sender: Optional[str]
    inbound_subject: Optional[str]
    inbound_body_text: Optional[str]
    inbound_body_html: Optional[str]
    inbound_received_at: Optional[datetime]
    inbound_attachments: Optional[List[Dict[str, Any]]]
    
    # AI processing results
    response_intent: Optional[str]  # e.g., "APPROVED", "REJECTED", "MORE_INFO_NEEDED"
    response_confidence: Optional[float]
    response_summary: Optional[str]
    action_required: Optional[str]
    
    # Status
    claim_status: str
    workflow_stage: str  # "pending_send", "awaiting_response", "processing_response", etc.
    errors: List[str]
    metadata: Dict[str, Any]
