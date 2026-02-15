"""
QUICK START GUIDE - Insurance Form Determination System
========================================================

This guide shows you how to use the insurance form system step by step.
"""

from datetime import datetime, timedelta
from insurance_forms import (
    InsuranceRegistry, FormType, FormRequirement, FormSubmission,
    ClaimFormState
)
from form_determination_workflow import run_form_determination_workflow


# ============================================================================
# EXAMPLE 1: Simple Claim Determination
# ============================================================================

print("=" * 70)
print("EXAMPLE 1: Simple Individual Claim (Clalit)")
print("=" * 70)
print()

# User data
user_data = {
    'username': 'john_doe',
    'email': 'john@example.com',
    'phone': '+972-50-1234567',
    'family_members_count': 0,  # Individual claim
    'insurance_companies': 'clalit'
}

# Run the form determination workflow
result = run_form_determination_workflow(
    claim_id='claim_001_john',
    user_id='user_001',
    user_data=user_data,
    insurance_company='clalit',
    claim_amount=250.0,
    claim_description='Doctor visit and lab tests'
)

print("RESULTS:")
print(f"  Claim ID: {result['claim_id']}")
print(f"  Next Step: {result['next_step']}")
print(f"  Recommendation: {result['recommendation'][:100]}...")
print()

print("Required Forms:")
for i, form in enumerate(result['required_forms'], 1):
    print(f"  {i}. {form['form_type']}")
    print(f"     Required: {form['required']}")
    print(f"     Notes: {form['notes']}")
print()

print("Pending Forms (need to submit):")
for form in result['pending_forms']:
    print(f"  - {form['form_type']}")
print()

print("Actions to Take:")
for action in result['actions']:
    priority = action.get('priority', 'NORMAL')
    print(f"  [{priority}] {action['action']}")
    if 'form_type' in action:
        print(f"      Form: {action['form_type']}")
print()
print()


# ============================================================================
# EXAMPLE 2: Complex Family Claim
# ============================================================================

print("=" * 70)
print("EXAMPLE 2: Family Claim (Multiple members)")
print("=" * 70)
print()

# Family claim with multiple members
family_user_data = {
    'username': 'sarah_smith',
    'email': 'sarah@example.com',
    'phone': '+972-50-2345678',
    'family_members_count': 2,  # Claiming for 2 additional family members
    'family_members': 'David Smith, Rebecca Smith',
    'insurance_companies': 'clalit'
}

# Higher claim amount triggers additional requirements
result = run_form_determination_workflow(
    claim_id='claim_002_sarah',
    user_id='user_002',
    user_data=family_user_data,
    insurance_company='clalit',
    claim_amount=750.0,  # Triggers medical report requirement
    claim_description='Hospitalization costs for family members'
)

print("RESULTS:")
print(f"  Claim ID: {result['claim_id']}")
print(f"  Next Step: {result['next_step']}")
print(f"  Required Forms: {len(result['required_forms'])}")
print()

print("Required Forms (with notes):")
for form in result['required_forms']:
    print(f"  ✓ {form['form_type']}")
    print(f"    {form['notes']}")
print()

print("Analysis:")
for key, value in result['analysis'].items():
    if key == 'requirements':
        print(f"  Insurance: {value['insurance_company']}")
        print(f"  Contact: {value['contact_email']}")
        print(f"  Processing time: {value['processing_days']} days")
    elif key == 'compliance':
        print(f"  User Compliance: {value['compliance_score']}/{value['max_score']} ({value['percentage']}%)")
print()
print()


# ============================================================================
# EXAMPLE 3: Tracking Form Submissions
# ============================================================================

print("=" * 70)
print("EXAMPLE 3: Tracking Form Submissions")
print("=" * 70)
print()

# Create a form state with some submitted forms
form_state = ClaimFormState(
    claim_id='claim_003_tracking',
    insurance_company='clalit',
    user_data={
        'username': 'test_user',
        'email': 'test@example.com'
    },
    claim_amount=300.0
)

# Add some requirements
form_state.required_forms = [
    FormRequirement(FormType.RECEIPT, required=True),
    FormRequirement(FormType.CLAIM_FORM, required=True),
    FormRequirement(FormType.ID_VERIFICATION, required=True),
    FormRequirement(FormType.MEDICAL_REPORT, required=False, optional=True),
]

# Simulate submissions
form_state.submitted_forms[FormType.RECEIPT] = FormSubmission(
    form_type=FormType.RECEIPT,
    submitted_at=datetime.utcnow() - timedelta(days=2),
    submitted_file_url='https://storage.example.com/receipt_001.pdf',
    file_size_bytes=245000,
    status='received',
    response_received_at=datetime.utcnow() - timedelta(days=1),
    valid_until=datetime.utcnow() + timedelta(days=90)
)

form_state.submitted_forms[FormType.CLAIM_FORM] = FormSubmission(
    form_type=FormType.CLAIM_FORM,
    submitted_at=datetime.utcnow() - timedelta(days=1),
    submitted_file_url='https://storage.example.com/claim_form_001.pdf',
    file_size_bytes=156000,
    status='received',
    response_received_at=datetime.utcnow(),
    valid_until=datetime.utcnow() + timedelta(days=30)
)

print("FORM TRACKING STATUS:")
print()

print("Required Forms:")
for form in form_state.required_forms:
    status = "SUBMITTED" if form.form_type in form_state.submitted_forms else "PENDING"
    required = "(Required)" if form.required else "(Optional)"
    print(f"  [{status}] {form.form_type.value} {required}")
print()

print("Submitted Forms Details:")
for form_type, submission in form_state.submitted_forms.items():
    days_left = submission.days_until_expiry()
    print(f"  Form: {form_type.value}")
    print(f"    Status: {submission.status}")
    print(f"    Submitted: {submission.submitted_at.strftime('%Y-%m-%d %H:%M')}")
    print(f"    Accepted: {submission.response_received_at.strftime('%Y-%m-%d %H:%M') if submission.response_received_at else 'Pending'}")
    print(f"    Valid for: {days_left} more days")
    print()

print("Pending Forms:")
pending = form_state.get_pending_forms()
if pending:
    for form in pending:
        print(f"  ✗ {form.form_type.value} (Required: {form.required})")
else:
    print("  None - All forms submitted!")
print()

print("Expiring Soon (within 7 days):")
expiring = form_state.get_expiring_forms(days_threshold=7)
if expiring:
    for form in expiring:
        print(f"  ⚠ {form.form_type.value} - {form.days_until_expiry()} days left")
else:
    print("  None")
print()
print()


# ============================================================================
# EXAMPLE 4: Different Insurance Companies
# ============================================================================

print("=" * 70)
print("EXAMPLE 4: Comparing Insurance Companies")
print("=" * 70)
print()

companies = ['clalit', 'maccabi']

for company_name in companies:
    print(f"Insurance Company: {company_name.upper()}")
    print("-" * 40)
    
    company = InsuranceRegistry.get_company(company_name)
    
    print(f"  Name: {company.name}")
    print(f"  Country: {company.country}")
    print(f"  Email: {company.email}")
    print(f"  Processing time: {company.claim_processing_days} days")
    print()
    
    # Get base requirements
    base_forms = company.get_form_requirements()
    print(f"  Base Requirements ({len(base_forms)} forms):")
    for form in base_forms:
        req_text = "(REQUIRED)" if form.required else "(Optional)"
        print(f"    - {form.form_type.value} {req_text}")
    print()
    
    # Check conditional requirements
    test_user = {'username': 'test', 'email': 'test@test.com'}
    conditional_forms = company.get_conditional_requirements(test_user, 600.0)
    if conditional_forms:
        print(f"  Conditional Requirements (for amount=600):")
        for form in conditional_forms:
            print(f"    + {form.form_type.value}")
    print()
print()


# ============================================================================
# EXAMPLE 5: Eligibility Checking
# ============================================================================

print("=" * 70)
print("EXAMPLE 5: User Eligibility Checking")
print("=" * 70)
print()

# Test different user scenarios
scenarios = [
    {
        'name': 'Complete Profile',
        'user_data': {
            'username': 'john_doe',
            'email': 'john@example.com',
            'phone': '+972-50-1234567',
            'id_number': '123456789'
        }
    },
    {
        'name': 'Incomplete Profile',
        'user_data': {
            'username': 'jane_doe',
            'email': 'jane@example.com'
            # Missing phone and ID
        }
    }
]

company = InsuranceRegistry.get_company('clalit')

for scenario in scenarios:
    print(f"Scenario: {scenario['name']}")
    
    eligibility = company.validate_user_eligibility(scenario['user_data'])
    
    status = "✓ ELIGIBLE" if eligibility['eligible'] else "✗ NOT ELIGIBLE"
    print(f"  Status: {status}")
    print(f"  Reason: {eligibility['reason']}")
    if eligibility['restrictions']:
        print(f"  Restrictions:")
        for restriction in eligibility['restrictions']:
            print(f"    - {restriction}")
    print()
print()


# ============================================================================
# EXAMPLE 6: Form Validity and Renewal
# ============================================================================

print("=" * 70)
print("EXAMPLE 6: Form Validity and Renewal Management")
print("=" * 70)
print()

# Create forms with different validity periods
submission_old = FormSubmission(
    form_type=FormType.MEDICAL_REPORT,
    submitted_at=datetime.utcnow() - timedelta(days=180),
    status='accepted',
    # Expires in 180 days from submission
    valid_until=datetime.utcnow() - timedelta(days=5)  # Already expired!
)

submission_good = FormSubmission(
    form_type=FormType.RECEIPT,
    submitted_at=datetime.utcnow() - timedelta(days=30),
    status='accepted',
    valid_until=datetime.utcnow() + timedelta(days=150)
)

submission_expiring = FormSubmission(
    form_type=FormType.CLAIM_FORM,
    submitted_at=datetime.utcnow() - timedelta(days=170),
    status='accepted',
    valid_until=datetime.utcnow() + timedelta(days=5)  # Expires in 5 days
)

submissions = [
    ('Expired Form', submission_old),
    ('Valid Form', submission_good),
    ('Expiring Soon', submission_expiring)
]

for name, submission in submissions:
    print(f"{name}: {submission.form_type.value}")
    print(f"  Submitted: {submission.submitted_at.strftime('%Y-%m-%d')}")
    print(f"  Valid until: {submission.valid_until.strftime('%Y-%m-%d')}")
    print(f"  Currently valid: {submission.is_still_valid()}")
    print(f"  Days remaining: {submission.days_until_expiry()}")
    print()
print()


# ============================================================================
# EXAMPLE 7: Available Insurance Companies
# ============================================================================

print("=" * 70)
print("EXAMPLE 7: Available Insurance Companies")
print("=" * 70)
print()

available = InsuranceRegistry.list_companies()
print(f"Currently registered insurance companies: {len(available)}")
for company in available:
    print(f"  - {company}")
print()

print("To add a new insurance company:")
print("  1. Create a class that extends InsuranceCompany")
print("  2. Implement required methods (get_form_requirements, etc.)")
print("  3. Register with: InsuranceRegistry.register_company('name', YourClass)")
print()
print()


# ============================================================================
# EXAMPLE 8: Form State Serialization
# ============================================================================

print("=" * 70)
print("EXAMPLE 8: Serializing Form State for Database")
print("=" * 70)
print()

# Create a form state
form_state = ClaimFormState(
    claim_id='claim_example',
    insurance_company='clalit',
    user_data={'username': 'test', 'email': 'test@test.com'},
    claim_amount=500.0
)

form_state.required_forms = [
    FormRequirement(FormType.RECEIPT, required=True),
    FormRequirement(FormType.CLAIM_FORM, required=True),
]

form_state.submitted_forms[FormType.RECEIPT] = FormSubmission(
    form_type=FormType.RECEIPT,
    submitted_at=datetime.utcnow(),
    status='received'
)

form_state.next_action = 'submit_forms'

# Serialize to dict (for database storage)
state_dict = form_state.to_dict()

print("Serialized Form State (JSON-ready):")
import json
print(json.dumps(state_dict, indent=2, ensure_ascii=False, default=str))
print()

print("Dict keys available for database:")
for key in state_dict.keys():
    print(f"  - {key}")
print()
print()


print("=" * 70)
print("END OF QUICK START GUIDE")
print("=" * 70)
print()
print("Next Steps:")
print("  1. Read INSURANCE_FORMS_ARCHITECTURE.md for full design")
print("  2. Review forms_integration.py for database integration")
print("  3. Implement the database models in models.py")
print("  4. Create API endpoints using FormManagementService")
print("  5. Test with test_insurance_forms.py")
