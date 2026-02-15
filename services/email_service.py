"""
Email service for sending and managing claim emails via Resend.

This module handles:
- Outbound email sending via Resend API
- Email loop closure with verified domains
- Webhook signature validation
- Message ID tracking for replies
- Test mode support with Resend test domain
"""

import os
import json
import logging
import hmac
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Resend API configuration
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
RESEND_API_URL = "https://api.resend.com"

# Email domain configuration
# For development/testing, use Resend's test domain
# For production, use a verified domain
EMAIL_DOMAIN = os.environ.get("EMAIL_DOMAIN", "resend.dev")  # Default to Resend test domain
CLAIMS_FROM_EMAIL = os.environ.get("CLAIMS_FROM_EMAIL", f"onboarding@{EMAIL_DOMAIN}")
WEBHOOK_SECRET = os.environ.get("RESEND_WEBHOOK_SECRET", "")

# Test/Preview mode configuration
TEST_MODE = os.environ.get("EMAIL_TEST_MODE", "true").lower() == "true"
TEST_EMAIL_RECIPIENT = os.environ.get("TEST_EMAIL_RECIPIENT", None)  # Where test emails are sent

if not RESEND_API_KEY:
    logger.warning("RESEND_API_KEY not configured - email functionality disabled")


class ResendClient:
    """Client for Resend API operations"""

    def __init__(self, api_key: str = RESEND_API_KEY):
        self.api_key = api_key
        self.base_url = RESEND_API_URL

    def send_email(
        self,
        to: str,
        subject: str,
        html: str,
        text: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        from_email: str = CLAIMS_FROM_EMAIL,
    ) -> Dict[str, Any]:
        """
        Send an email via Resend API.
        
        Args:
            to: Recipient email address
            subject: Email subject
            html: Email body (HTML)
            text: Email body (plain text fallback)
            cc: List of CC recipients
            bcc: List of BCC recipients
            reply_to: Reply-To address (for email loop closure)
            attachments: List of attachment objects
            from_email: From address (must be verified domain)
            
        Returns:
            Response dict with message_id and other metadata
            
        Raises:
            ResendAPIError: If API call fails
        """
        if not self.api_key:
            raise ResendAPIError("RESEND_API_KEY not configured")

        # In test mode, redirect to test recipient if configured
        actual_to = to
        actual_cc = cc
        actual_bcc = bcc
        
        if TEST_MODE and TEST_EMAIL_RECIPIENT:
            logger.info(
                f"[TEST MODE] Original recipient: {to}, "
                f"redirecting to: {TEST_EMAIL_RECIPIENT}"
            )
            actual_to = TEST_EMAIL_RECIPIENT
            # Include original recipients in subject for visibility
            subject = f"[TO: {to}] {subject}"
            if cc:
                subject = f"[CC: {', '.join(cc)}] {subject}"
            # Clear CC/BCC in test mode to avoid sending to real recipients
            actual_cc = None
            actual_bcc = None

        payload = {
            "from": from_email,
            "to": actual_to,
            "subject": subject,
            "html": html,
        }

        if text:
            payload["text"] = text
        if actual_cc:
            payload["cc"] = actual_cc
        if actual_bcc:
            payload["bcc"] = actual_bcc
        if reply_to:
            payload["reply_to"] = reply_to
        if attachments:
            payload["attachments"] = attachments

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                f"{self.base_url}/emails",
                json=payload,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Email sent successfully. Message ID: {result.get('id')}")
            return result
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to send email: {str(e)}"
            if hasattr(e, "response") and e.response is not None:
                error_msg += f" - {e.response.text}"
            logger.error(error_msg)
            raise ResendAPIError(error_msg)

    def validate_webhook_signature(self, signature: str, body: str) -> bool:
        """
        Validate Resend webhook signature.
        
        Args:
            signature: The x-resend-signature header value
            body: The raw request body
            
        Returns:
            True if signature is valid, False otherwise
            
        Note:
            Signature format: t={timestamp},v1={hash}
        """
        if not WEBHOOK_SECRET:
            logger.warning("RESEND_WEBHOOK_SECRET not configured - skipping validation")
            return True

        try:
            # Parse signature header: "t=timestamp,v1=hash"
            parts = signature.split(",")
            timestamp = None
            received_hash = None

            for part in parts:
                if part.startswith("t="):
                    timestamp = part[2:]
                elif part.startswith("v1="):
                    received_hash = part[3:]

            if not timestamp or not received_hash:
                logger.error("Invalid signature format")
                return False

            # Create signed content: {timestamp}.{body}
            signed_content = f"{timestamp}.{body}"

            # Calculate HMAC-SHA256
            expected_hash = hmac.new(
                WEBHOOK_SECRET.encode(),
                signed_content.encode(),
                hashlib.sha256,
            ).hexdigest()

            # Constant-time comparison
            is_valid = hmac.compare_digest(expected_hash, received_hash)

            if not is_valid:
                logger.warning("Webhook signature validation failed")

            return is_valid

        except Exception as e:
            logger.error(f"Error validating webhook signature: {str(e)}")
            return False


class EmailTemplates:
    """Email templates for claim communications"""

    @staticmethod
    def claim_submission_html(
        claim_id: str,
        insurance_company: str,
        claim_amount: Optional[str] = None,
        document_summary: Optional[str] = None,
    ) -> str:
        """Generate HTML for claim submission email"""
        return f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2>Claim Submission</h2>
    
    <p>Dear {insurance_company},</p>
    
    <p>We are submitting a claims request for your review and processing.</p>
    
    <p><strong>Claim Details:</strong></p>
    <ul>
        <li>Claim ID: <code>{claim_id}</code></li>
        <li>Insurance Company: {insurance_company}</li>
        {f'<li>Claim Amount: {claim_amount}</li>' if claim_amount else ''}
    </ul>
    
    {f'<p><strong>Document Summary:</strong></p><p>{document_summary}</p>' if document_summary else ''}
    
    <p>Please review the attached documents and respond to this email with your decision or any additional information needed.</p>
    
    <p>Best regards,<br/>
    Claims Automation System</p>
    
    <hr style="margin-top: 40px; border: none; border-top: 1px solid #ccc;">
    <p style="font-size: 12px; color: #666;">
        This is an automated email from the claims processing system.
        Your reply will be automatically attached to this claim in our system.
    </p>
</body>
</html>
"""

    @staticmethod
    def claim_submission_text(
        claim_id: str,
        insurance_company: str,
        claim_amount: Optional[str] = None,
    ) -> str:
        """Generate plain text version of claim submission email"""
        return f"""
Claim Submission

Dear {insurance_company},

We are submitting a claims request for your review and processing.

Claim Details:
- Claim ID: {claim_id}
- Insurance Company: {insurance_company}
{f'- Claim Amount: {claim_amount}' if claim_amount else ''}

Please review the attached documents and respond to this email with your decision or any additional information needed.

Best regards,
Claims Automation System

---
This is an automated email from the claims processing system.
Your reply will be automatically attached to this claim in our system.
"""


class ResendAPIError(Exception):
    """Exception raised for Resend API errors"""

    pass
