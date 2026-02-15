"""
Insurance Company Form Management System
========================================

This module defines insurance company classes with their specific form requirements,
and provides a LangGraph-based workflow to dynamically determine which forms are
needed for a successful claim submission.

Architecture:
- InsuranceCompany: Base class defining form requirements and validation rules
- FormType: Enum of supported form types and their metadata
- FormRequirement: Specification of a form including validation rules
- ClaimFormState: Tracks form status, expiration, and submission state
- FormDeterminationWorkflow: LangGraph agent to determine needed forms

Usage:
    1. Register insurance companies with their form requirements
    2. Create a claim with an insurance company
    3. Run the form determination workflow with user data
    4. Track form submissions and responses
    5. Monitor for issues via incoming mail
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import json


# ============================================================================
# FORM TYPE DEFINITIONS
# ============================================================================

class FormType(str, Enum):
    """Standard forms required by insurance companies"""
    # Medical/Health Forms
    MEDICAL_REPORT = "medical_report"
    LAB_RESULTS = "lab_results"
    PHARMACY_RECEIPT = "pharmacy_receipt"
    HOSPITALIZATION_DOCUMENT = "hospitalization_document"
    DOCTOR_NOTE = "doctor_note"
    
    # Administrative Forms
    CLAIM_FORM = "claim_form"  # Insurance company's claim form
    RECEIPT = "receipt"  # Original receipt/invoice
    ID_VERIFICATION = "id_verification"
    PROOF_OF_PAYMENT = "proof_of_payment"
    BANK_STATEMENT = "bank_statement"
    
    # Policy/Insurance Forms
    POLICY_COPY = "policy_copy"
    COVERAGE_VERIFICATION = "coverage_verification"
    
    # Special Cases
    AUTHORIZATION_LETTER = "authorization_letter"  # For family members
    MINOR_CONSENT = "minor_consent"  # For minors
    SPOUSE_CONSENT = "spouse_consent"  # For spouse claims
    PRE_APPROVAL = "pre_approval"  # If pre-approval was obtained


@dataclass
class FormRequirement:
    """Specification of a required form with validation rules"""
    form_type: FormType
    required: bool = True
    optional: bool = False
    
    # Validation rules
    max_age_days: Optional[int] = None  # Max age of document (180 days, etc.)
    requires_original: bool = False
    requires_certified_copy: bool = False
    requires_translation: bool = False  # If multiple languages in user profile
    
    # Conditional requirements
    condition: Optional[str] = None  # e.g., "if_amount_exceeds_1000", "if_family_members_count > 2"
    condition_fn: Optional[callable] = None  # Function to evaluate condition
    
    # Notes for user
    notes: str = ""
    
    def is_applicable(self, user_data: Dict[str, Any], claim_amount: float = 0) -> bool:
        """Check if this form is required based on user data and claim"""
        if not self.required and self.optional:
            return False
        
        # Check conditional requirements if provided
        if self.condition_fn:
            try:
                return self.condition_fn(user_data, claim_amount)
            except Exception:
                return True  # Default to required if condition fails
        
        return True


@dataclass
class FormSubmission:
    """Track the submission status of a form"""
    form_type: FormType
    submitted_at: Optional[datetime] = None
    submitted_file_url: Optional[str] = None
    file_size_bytes: Optional[int] = None
    
    # Response tracking
    status: str = "pending"  # pending, received, rejected, expired
    response_received_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    issues_found: List[str] = field(default_factory=list)
    
    # Expiration tracking
    valid_until: Optional[datetime] = None
    is_expired: bool = False
    renewal_required_at: Optional[datetime] = None
    
    def is_still_valid(self) -> bool:
        """Check if document is still within valid date range"""
        if not self.valid_until:
            return True
        return datetime.utcnow() < self.valid_until
    
    def days_until_expiry(self) -> Optional[int]:
        """Return days until form expires"""
        if not self.valid_until:
            return None
        delta = self.valid_until - datetime.utcnow()
        return max(0, delta.days)


# ============================================================================
# INSURANCE COMPANY DEFINITIONS
# ============================================================================

class InsuranceCompany(ABC):
    """
    Base class for insurance company form requirements.
    Each insurance company subclass defines what forms are needed
    for a successful claim.
    """
    
    name: str
    country: str
    email: str
    website: str
    phone: str
    claim_processing_days: int = 30
    
    # Form requirements for this insurance company
    base_requirements: List[FormRequirement] = []
    
    def __init__(self):
        """Initialize with standard form requirements"""
        self.form_requirements = self.get_form_requirements()
    
    @abstractmethod
    def get_form_requirements(self) -> List[FormRequirement]:
        """Return list of forms required by this insurance company"""
        pass
    
    @abstractmethod
    def validate_user_eligibility(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate if user is eligible and return eligibility info.
        Return dict with:
        - eligible: bool
        - reason: str
        - restrictions: List[str]
        """
        pass
    
    @abstractmethod
    def get_conditional_requirements(self, user_data: Dict[str, Any], claim_amount: float) -> List[FormRequirement]:
        """
        Return additional forms needed based on user profile and claim amount.
        This is where complex logic lives - e.g., family counting, amount thresholds, etc.
        """
        pass
    
    @abstractmethod
    def parse_response_email(self, email_body: str) -> Dict[str, Any]:
        """
        Parse incoming email from insurance company to extract:
        - status: approved/rejected/needs_info
        - missing_forms: List[FormType]
        - issues: List[str]
        - next_steps: str
        """
        pass
    
    @abstractmethod
    def get_submission_email_template(self, forms_submitted: List[FormSubmission]) -> Dict[str, str]:
        """
        Return the email template for submitting forms to this insurance company.
        Should include what to write and in what language.
        """
        pass


class KlalitInsurance(InsuranceCompany):
    """Clalit Health Services (Israel)"""
    name = "Clalit"
    country = "Israel"
    email = "claims@clalit.co.il"
    website = "https://www.clalit.co.il"
    phone = "+972-2-6797777"
    claim_processing_days = 30
    
    def get_form_requirements(self) -> List[FormRequirement]:
        """Clalit standard form requirements"""
        return [
            FormRequirement(
                form_type=FormType.RECEIPT,
                required=True,
                notes="Original receipt with date, amount, and provider details"
            ),
            FormRequirement(
                form_type=FormType.CLAIM_FORM,
                required=True,
                notes="Clalit's claim form (טופס תביעה)"
            ),
            FormRequirement(
                form_type=FormType.ID_VERIFICATION,
                required=True,
                notes="ID or passport copy"
            ),
            FormRequirement(
                form_type=FormType.MEDICAL_REPORT,
                required=False,
                optional=True,
                notes="Required for amounts over 500 NIS or for complex care"
            ),
            FormRequirement(
                form_type=FormType.PROOF_OF_PAYMENT,
                required=True,
                notes="Bank statement or credit card statement showing payment"
            ),
        ]
    
    def validate_user_eligibility(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if user is eligible for Clalit reimbursement"""
        required_fields = ['email', 'id_number']
        missing = [f for f in required_fields if not user_data.get(f)]
        
        return {
            'eligible': len(missing) == 0,
            'reason': 'Valid Clalit member' if len(missing) == 0 else f'Missing: {", ".join(missing)}',
            'restrictions': []
        }
    
    def get_conditional_requirements(self, user_data: Dict[str, Any], claim_amount: float) -> List[FormRequirement]:
        """Additional forms based on claim amount and user profile"""
        extra_forms = []
        
        # High amount claims require medical justification
        if claim_amount > 500:
            extra_forms.append(FormRequirement(
                form_type=FormType.MEDICAL_REPORT,
                required=True,
                notes="Mandatory for claims over 500 NIS"
            ))
        
        # Family member claims
        if user_data.get('family_members_count', 0) > 0:
            extra_forms.append(FormRequirement(
                form_type=FormType.AUTHORIZATION_LETTER,
                required=True,
                notes="Authorization letter from family member for dependent claims"
            ))
        
        return extra_forms
    
    def parse_response_email(self, email_body: str) -> Dict[str, Any]:
        """Parse Clalit's response email"""
        result = {
            'status': 'pending',
            'missing_forms': [],
            'issues': [],
            'next_steps': '',
            'raw_body': email_body
        }
        
        # Simple keyword matching (can be enhanced with LLM)
        email_lower = email_body.lower()
        
        if 'אושר' in email_body or 'approved' in email_lower:
            result['status'] = 'approved'
        elif 'דחוי' in email_body or 'rejected' in email_lower:
            result['status'] = 'rejected'
        elif 'דרוש' in email_body or 'required' in email_lower or 'missing' in email_lower:
            result['status'] = 'needs_info'
        
        # Look for missing documents
        if 'form' in email_lower or 'טופס' in email_body:
            result['missing_forms'].append(FormType.CLAIM_FORM)
        if 'medical' in email_lower or 'רפואי' in email_body:
            result['missing_forms'].append(FormType.MEDICAL_REPORT)
        if 'receipt' in email_lower or 'קבלה' in email_body:
            result['missing_forms'].append(FormType.RECEIPT)
        
        return result
    
    def get_submission_email_template(self, forms_submitted: List[FormSubmission]) -> Dict[str, str]:
        """Email template for Clalit submission"""
        hebrew_body = """
        שלום,
        
        אני מגיש בזאת תביעה לתשלום הוצאות רפואיות.
        
        המסמכים המצורפים כוללים:
        """
        
        for form in forms_submitted:
            hebrew_body += f"\n- {form.form_type.value}"
        
        hebrew_body += """
        
        בברכה,
        המבקש
        """
        
        return {
            'subject': "תביעה על הוצאות רפואיות",
            'body_he': hebrew_body,
            'body_en': "Medical expense claim submission",
            'recipient': self.email,
            'language': 'he'
        }


class MeccabiInsurance(InsuranceCompany):
    """Maccabi Health Services (Israel)"""
    name = "Maccabi"
    country = "Israel"
    email = "claims@maccabi.co.il"
    website = "https://www.maccabi.co.il"
    phone = "+972-3-6923000"
    claim_processing_days = 30
    
    def get_form_requirements(self) -> List[FormRequirement]:
        return [
            FormRequirement(
                form_type=FormType.RECEIPT,
                required=True,
                notes="Original receipt"
            ),
            FormRequirement(
                form_type=FormType.CLAIM_FORM,
                required=True,
                notes="Maccabi's official claim form"
            ),
            FormRequirement(
                form_type=FormType.ID_VERIFICATION,
                required=True,
            ),
            FormRequirement(
                form_type=FormType.PROOF_OF_PAYMENT,
                required=True,
            ),
        ]
    
    def validate_user_eligibility(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'eligible': bool(user_data.get('email')),
            'reason': 'Valid Maccabi member',
            'restrictions': []
        }
    
    def get_conditional_requirements(self, user_data: Dict[str, Any], claim_amount: float) -> List[FormRequirement]:
        extra_forms = []
        if claim_amount > 1000:
            extra_forms.append(FormRequirement(
                form_type=FormType.MEDICAL_REPORT,
                required=True,
                notes="Required for large claims"
            ))
        return extra_forms
    
    def parse_response_email(self, email_body: str) -> Dict[str, Any]:
        return {
            'status': 'pending',
            'missing_forms': [],
            'issues': [],
            'next_steps': '',
            'raw_body': email_body
        }
    
    def get_submission_email_template(self, forms_submitted: List[FormSubmission]) -> Dict[str, str]:
        return {
            'subject': "Medical expense claim",
            'body_en': "Please find attached my claim for medical expenses",
            'recipient': self.email,
            'language': 'en'
        }


# ============================================================================
# INSURANCE COMPANY REGISTRY
# ============================================================================

class InsuranceRegistry:
    """Registry of all supported insurance companies"""
    
    _companies: Dict[str, type] = {
        'clalit': KlalitInsurance,
        'maccabi': MeccabiInsurance,
        # Add more insurance companies here
    }
    
    @classmethod
    def get_company(cls, company_name: str) -> InsuranceCompany:
        """Get an insurance company instance by name"""
        company_class = cls._companies.get(company_name.lower())
        if not company_class:
            raise ValueError(f"Unknown insurance company: {company_name}")
        return company_class()
    
    @classmethod
    def register_company(cls, name: str, company_class: type):
        """Register a new insurance company"""
        cls._companies[name.lower()] = company_class
    
    @classmethod
    def list_companies(cls) -> List[str]:
        """List all available insurance companies"""
        return list(cls._companies.keys())


# ============================================================================
# CLAIM FORM STATE TRACKING
# ============================================================================

@dataclass
class ClaimFormState:
    """Track all forms needed and their submission status for a claim"""
    claim_id: str
    insurance_company: str
    user_data: Dict[str, Any]
    claim_amount: float
    
    # Form tracking
    required_forms: List[FormRequirement] = field(default_factory=list)
    submitted_forms: Dict[FormType, FormSubmission] = field(default_factory=dict)
    
    # State
    all_submitted: bool = False
    all_accepted: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    # LangGraph state
    last_agent_analysis: Optional[Dict[str, Any]] = None
    next_action: Optional[str] = None  # "submit_forms", "wait_response", "fix_forms", etc.
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict for database storage"""
        return {
            'claim_id': self.claim_id,
            'insurance_company': self.insurance_company,
            'user_data': self.user_data,
            'claim_amount': self.claim_amount,
            'required_forms': [
                {
                    'form_type': f.form_type.value,
                    'required': f.required,
                    'optional': f.optional,
                    'notes': f.notes
                }
                for f in self.required_forms
            ],
            'submitted_forms': {
                k.value: {
                    'form_type': k.value,
                    'submitted_at': v.submitted_at.isoformat() if v.submitted_at else None,
                    'status': v.status,
                    'valid_until': v.valid_until.isoformat() if v.valid_until else None,
                    'issues': v.issues_found
                }
                for k, v in self.submitted_forms.items()
            },
            'all_submitted': self.all_submitted,
            'all_accepted': self.all_accepted,
            'next_action': self.next_action,
        }
    
    def get_pending_forms(self) -> List[FormRequirement]:
        """Get forms that still need to be submitted"""
        submitted_types = set(self.submitted_forms.keys())
        return [f for f in self.required_forms if f.form_type not in submitted_types]
    
    def get_rejected_forms(self) -> List[FormSubmission]:
        """Get forms that were rejected"""
        return [f for f in self.submitted_forms.values() if f.status == 'rejected']
    
    def get_expiring_forms(self, days_threshold: int = 7) -> List[FormSubmission]:
        """Get forms expiring within threshold days"""
        expiring = []
        for form in self.submitted_forms.values():
            days_left = form.days_until_expiry()
            if days_left and days_left <= days_threshold:
                expiring.append(form)
        return expiring


# ============================================================================
# DATABASE INTEGRATION
# ============================================================================

# These would be added to models.py:
"""
from sqlalchemy import Column, String, JSON, Boolean, DateTime
from sqlalchemy.orm import relationship

class ClaimFormTracking(Base):
    __tablename__ = "claim_form_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), unique=True, nullable=False)
    insurance_company = Column(String, nullable=False)
    
    # Form state as JSON
    form_state_json = Column(Text, nullable=False)  # Serialized ClaimFormState
    
    # Summary fields (for querying)
    all_submitted = Column(Boolean, default=False)
    all_accepted = Column(Boolean, default=False)
    next_action = Column(String)  # "submit", "wait", "fix", etc.
    
    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    claim = relationship("Claim", backref="form_tracking")
    
    def get_state(self) -> ClaimFormState:
        return ClaimFormState(**json.loads(self.form_state_json))
    
    def update_state(self, state: ClaimFormState):
        self.form_state_json = json.dumps(state.to_dict())
        self.all_submitted = state.all_submitted
        self.all_accepted = state.all_accepted
        self.next_action = state.next_action
        self.updated_at = datetime.utcnow()
"""


if __name__ == "__main__":
    # Example usage
    clalit = InsuranceRegistry.get_company('clalit')
    
    user_data = {
        'username': 'john_doe',
        'email': 'john@example.com',
        'family_members_count': 2,
        'id_number': '123456789'
    }
    
    claim_amount = 250.0
    
    # Get requirements
    base_forms = clalit.get_form_requirements()
    conditional_forms = clalit.get_conditional_requirements(user_data, claim_amount)
    
    print(f"Insurance: {clalit.name}")
    print(f"\nBase forms required ({len(base_forms)}):")
    for form in base_forms:
        print(f"  - {form.form_type.value}: {form.notes}")
    
    print(f"\nConditional forms ({len(conditional_forms)}):")
    for form in conditional_forms:
        print(f"  - {form.form_type.value}: {form.notes}")
