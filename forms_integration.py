"""
Integration Guide: Insurance Forms & LangGraph Workflow
========================================================

This guide explains how to integrate the insurance form determination system
into your existing codebase.

ARCHITECTURE OVERVIEW:
1. User submits a claim with receipt and insurance company details
2. Claim is created in database with status DRAFT
3. Form determination workflow is triggered (async)
4. LangGraph agent analyzes user profile and insurance requirements
5. FormTracking record created with required forms list
6. User receives notification of what forms are needed
7. User submits forms through UI
8. System monitors for insurance company responses via email
9. LLM analyzes responses to determine if forms were accepted
10. Claim status updated based on insurance company feedback

DATABASE SCHEMA CHANGES:
- Add ClaimFormTracking table to track form state
- Add FormSubmissionRecord table for audit trail

WORKFLOW INTEGRATION POINTS:
1. When Claim is created → run form determination
2. When email arrives → parse for form acceptance/rejection
3. When form uploaded → update form state
4. Periodic monitoring → check for expiring forms
"""

from datetime import datetime
from datetime import timedelta
import json
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
import asyncio
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Database Models (to be added to models.py)
# ============================================================================

# Note: These would be imported and added to models.py:

"""
# In models.py, add these imports:
from insurance_forms import ClaimFormState, FormType, FormSubmission

# Add these table definitions to models.py:

class ClaimFormTracking(Base):
    '''Track all forms required and submitted for a claim'''
    __tablename__ = "claim_form_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), unique=True, nullable=False, index=True)
    insurance_company = Column(String, nullable=False)
    
    # Form state (serialized JSON)
    form_state_json = Column(Text, nullable=False)
    
    # Summary fields for quick querying
    num_required_forms = Column(Integer, default=0)
    num_submitted_forms = Column(Integer, default=0)
    all_submitted = Column(Boolean, default=False, index=True)
    all_accepted = Column(Boolean, default=False, index=True)
    
    # Workflow status
    current_step = Column(String, default='initial')  # initial, determining, ready_to_submit, submitted, processing, completed
    next_action = Column(String)  # submit_forms, wait_for_response, fix_issues, claim_processing
    last_recommendation = Column(Text)
    
    # Tracking timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_analyzed_at = Column(DateTime, nullable=True)
    
    # Relationships
    claim = relationship("Claim", backref="form_tracking")
    form_submissions = relationship("FormSubmissionRecord", back_populates="tracking")
    
    def get_state(self) -> 'ClaimFormState':
        '''Deserialize form state from JSON'''
        from insurance_forms import ClaimFormState
        return ClaimFormState(**json.loads(self.form_state_json))
    
    def update_state(self, state: 'ClaimFormState'):
        '''Serialize and save form state'''
        self.form_state_json = json.dumps(state.to_dict())
        self.num_required_forms = len(state.required_forms)
        self.num_submitted_forms = len(state.submitted_forms)
        self.all_submitted = state.all_submitted
        self.all_accepted = state.all_accepted
        self.next_action = state.next_action
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        '''Convert to dictionary for API responses'''
        state = self.get_state()
        return {
            'claim_id': self.claim_id,
            'insurance_company': self.insurance_company,
            'current_step': self.current_step,
            'next_action': self.next_action,
            'num_required_forms': self.num_required_forms,
            'num_submitted_forms': self.num_submitted_forms,
            'all_submitted': self.all_submitted,
            'all_accepted': self.all_accepted,
            'required_forms': [
                {
                    'form_type': f.form_type.value,
                    'required': f.required,
                    'notes': f.notes
                }
                for f in state.required_forms
            ],
            'submitted_forms': list(state.submitted_forms.keys()),
            'last_recommendation': self.last_recommendation,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_analyzed_at': self.last_analyzed_at.isoformat() if self.last_analyzed_at else None
        }


class FormSubmissionRecord(Base):
    '''Audit trail for form submissions'''
    __tablename__ = "form_submission_records"
    
    id = Column(Integer, primary_key=True, index=True)
    tracking_id = Column(Integer, ForeignKey("claim_form_tracking.id"), nullable=False)
    
    # Form information
    form_type = Column(String, nullable=False, index=True)
    file_name = Column(String)
    file_url = Column(String)
    file_size_bytes = Column(Integer)
    file_sha256 = Column(String)  # For content verification
    
    # Submission tracking
    submitted_at = Column(DateTime, nullable=True, index=True)
    submitted_by = Column(String)  # email of submitter
    submission_attempt_num = Column(Integer, default=1)
    
    # Response tracking
    response_status = Column(String, default='pending')  # pending, accepted, rejected, expired
    response_received_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text)
    
    # Validity tracking
    valid_until = Column(DateTime, nullable=True)
    requires_renewal = Column(Boolean, default=False)
    renewal_submitted_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tracking = relationship("ClaimFormTracking", back_populates="form_submissions")
    
    def is_valid(self) -> bool:
        '''Check if form is still valid'''
        if not self.valid_until:
            return True
        return datetime.utcnow() < self.valid_until
    
    def days_until_expiry(self) -> Optional[int]:
        '''Days remaining before expiration'''
        if not self.valid_until:
            return None
        delta = self.valid_until - datetime.utcnow()
        return max(0, delta.days)
"""


# ============================================================================
# Service Layer: Form Management
# ============================================================================

class FormManagementService:
    """
    High-level service for managing insurance forms and claim submissions.
    This is the main interface your routes and business logic should use.
    """
    
    @staticmethod
    def create_claim_with_forms(
        db,
        user_id: int,
        insurance_company: str,
        claim_amount: float,
        claim_description: str,
        receipt_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new claim and immediately determine required forms.
        
        Args:
            db: Database session
            user_id: ID of the user
            insurance_company: Name of insurance company
            claim_amount: Amount being claimed
            claim_description: Description of what the claim is for
            receipt_id: Optional receipt ID to link
        
        Returns:
            Dict with claim info and initial form requirements
        """
        from form_determination_workflow import run_form_determination_workflow
        
        # Get user data
        # user = db.query(User).filter(User.user_id == user_id).first()
        # user_data = {...convert user to dict...}
        
        # For now, mock user data
        user_data = {
            'user_id': user_id,
            'email': 'example@example.com',
            'phone': '+1-555-0000',
            'family_members_count': 0,
            'insurance_companies': insurance_company
        }
        
        # Run form determination workflow
        workflow_result = run_form_determination_workflow(
            claim_id=f"claim_{user_id}_{int(datetime.utcnow().timestamp())}",
            user_id=user_id,
            user_data=user_data,
            insurance_company=insurance_company,
            claim_amount=claim_amount,
            claim_description=claim_description
        )
        
        return {
            'claim_id': workflow_result['claim_id'],
            'next_step': workflow_result['next_step'],
            'required_forms': workflow_result['required_forms'],
            'pending_forms': workflow_result['pending_forms'],
            'actions': workflow_result['actions'],
            'recommendation': workflow_result['recommendation']
        }
    
    @staticmethod
    def submit_form(
        db,
        claim_id: str,
        form_type: str,
        file_url: str,
        file_size: int
    ) -> Dict[str, Any]:
        """
        Record a form submission and update claim state.
        
        Args:
            db: Database session
            claim_id: The claim ID
            form_type: Type of form being submitted
            file_url: URL where file is stored
            file_size: Size of file in bytes
        
        Returns:
            Updated claim form state
        """
        # Get claim and tracking
        # claim = db.query(Claim).filter(Claim.public_id == claim_id).first()
        # tracking = db.query(ClaimFormTracking).filter(
        #     ClaimFormTracking.claim_id == claim.id
        # ).first()
        
        # Update form submission
        # state = tracking.get_state()
        # state.submitted_forms[FormType(form_type)] = FormSubmission(
        #     form_type=FormType(form_type),
        #     submitted_at=datetime.utcnow(),
        #     submitted_file_url=file_url,
        #     file_size_bytes=file_size,
        #     status='submitted'
        # )
        # tracking.update_state(state)
        
        # db.add(FormSubmissionRecord(...))
        # db.commit()
        
        return {
            'status': 'submitted',
            'form_type': form_type,
            'submitted_at': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    async def process_incoming_email(
        db,
        claim_id: str,
        email_body: str,
        email_from: str,
        email_subject: str
    ) -> Dict[str, Any]:
        """
        Process incoming email from insurance company and update claim status.
        
        Args:
            db: Database session
            claim_id: The claim ID
            email_body: Email body text
            email_from: Email sender
            email_subject: Email subject
        
        Returns:
            Analysis of email and any actions needed
        """
        from form_determination_workflow import analyze_insurance_email
        
        # Get tracking
        # tracking = db.query(ClaimFormTracking).filter_by(claim_id=claim_id).first()
        
        # Analyze email
        # analysis = analyze_insurance_email(email_body, tracking.insurance_company)
        
        # Update current step based on analysis
        # if analysis['email_status'] == 'approved':
        #     tracking.current_step = 'claim_processing'
        # elif analysis['email_status'] == 'needs_info':
        #     tracking.current_step = 'waiting_for_fixes'
        # elif analysis['email_status'] == 'rejected':
        #     tracking.current_step = 'fix_issues_needed'
        
        # db.commit()
        
        return {
            'claim_id': claim_id,
            'analysis': 'analysis',
            'next_action': 'fix_issues'
        }
    
    @staticmethod
    def check_expiring_forms(db) -> List[Dict[str, Any]]:
        """
        Find all forms expiring within 7 days and notify users.
        
        Returns:
            List of expiring forms
        """
        # Query all claims with expiring forms
        # Filter form submissions where valid_until < now + 7 days
        # Return list for notification
        
        return []
    
    @staticmethod
    def re_run_form_determination(
        db,
        claim_id: str
    ) -> Dict[str, Any]:
        """
        Re-run form determination (useful after fixing issues or adding new info).
        
        Returns:
            Updated form requirements
        """
        from form_determination_workflow import run_form_determination_workflow
        
        # Get existing claim and tracking
        # Re-run workflow with updated data
        # Update tracking record
        
        return {
            'claim_id': claim_id,
            'updated': True,
            'new_actions': []
        }


# ============================================================================
# API Routes Integration Examples
# ============================================================================

"""
Example routes to add to your main.py or routes file:

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/claims", tags=["claims"])

@router.post("/with-forms")
async def create_claim_with_forms(
    user_id: int,
    insurance_company: str,
    claim_amount: float,
    claim_description: str,
    db: Session = Depends(get_db)
):
    '''Create a claim and determine required forms'''
    result = FormManagementService.create_claim_with_forms(
        db, user_id, insurance_company, claim_amount, claim_description
    )
    return result


@router.post("/{claim_id}/forms/{form_type}/submit")
async def submit_form(
    claim_id: str,
    form_type: str,
    file_url: str,
    file_size: int,
    db: Session = Depends(get_db)
):
    '''Submit a form for a claim'''
    result = FormManagementService.submit_form(db, claim_id, form_type, file_url, file_size)
    return result


@router.get("/{claim_id}/forms/status")
async def get_form_status(
    claim_id: str,
    db: Session = Depends(get_db)
):
    '''Get current form submission status'''
    # tracking = db.query(ClaimFormTracking).filter_by(claim_id=claim_id).first()
    # return tracking.to_dict()
    pass


@router.get("/monitoring/expiring")
async def get_expiring_forms(
    db: Session = Depends(get_db)
):
    '''Get all forms expiring within 7 days'''
    return FormManagementService.check_expiring_forms(db)


@router.post("/{claim_id}/refresh")
async def refresh_form_determination(
    claim_id: str,
    db: Session = Depends(get_db)
):
    '''Re-run form determination for a claim'''
    return FormManagementService.re_run_form_determination(db, claim_id)
"""


# ============================================================================
# Background Tasks / Scheduled Jobs
# ============================================================================

"""
Example Celery tasks to add for background processing:

from celery import shared_task
from datetime import datetime, timedelta

@shared_task
def check_expiring_forms_task():
    '''Check for forms expiring within 7 days (run daily)'''
    db = SessionLocal()
    FormManagementService.check_expiring_forms(db)
    db.close()


@shared_task
def monitor_claim_emails_task(claim_id: str):
    '''Monitor for new emails on a claim (run periodic)'''
    # Get claim's email address
    # Check for new emails
    # Process any received emails
    pass


@shared_task
def recheck_form_prerequisites_task():
    '''Re-run form determination for all open claims (weekly)'''
    # Query all claims with status not in [CLOSED, COMPLETED]
    # Re-run form determination for each
    # Alert users if new forms needed
    pass
"""


# ============================================================================
# Testing Examples
# ============================================================================

def test_insurance_company_classes():
    """Test that insurance company classes work correctly"""
    from insurance_forms import InsuranceRegistry, FormType
    
    # Test Clalit
    clalit = InsuranceRegistry.get_company('clalit')
    assert clalit.name == "Clalit"
    
    forms = clalit.get_form_requirements()
    assert len(forms) > 0
    assert any(f.form_type == FormType.RECEIPT for f in forms)
    
    print("✓ Insurance company classes working")


def test_form_workflow():
    """Test the form determination workflow"""
    from form_determination_workflow import run_form_determination_workflow
    
    user_data = {
        'username': 'test_user',
        'email': 'test@example.com',
        'family_members_count': 0
    }
    
    result = run_form_determination_workflow(
        claim_id='test_claim_001',
        user_id=123,
        user_data=user_data,
        insurance_company='clalit',
        claim_amount=200.0,
        claim_description='Doctor visit'
    )
    
    assert result['claim_id'] == 'test_claim_001'
    assert len(result['required_forms']) > 0
    assert result['next_step'] in ['submit_forms', 'wait_for_response', 'fix_issues']
    
    print("✓ Form determination workflow working")


if __name__ == "__main__":
    print("Insurance Forms Integration Guide")
    print("=" * 50)
    print()
    print("Testing components...")
    test_insurance_company_classes()
    test_form_workflow()
    print()
    print("✓ All tests passed!")
