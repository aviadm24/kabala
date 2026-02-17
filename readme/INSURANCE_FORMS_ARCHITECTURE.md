"""
INSURANCE FORM DETERMINATION SYSTEM - ARCHITECTURE GUIDE
=========================================================

This document explains the architecture and design of the insurance form 
determination system that uses LangGraph to manage the complexity of 
insurance claims.

## PROBLEM STATEMENT

Insurance companies don't just require a receipt to reimburse claims.
They typically require:

1. MULTIPLE FORMS beyond the receipt:
   - Claim form (insurance company's own form)
   - Medical reports or lab results
   - Proof of payment (bank/credit card statement)
   - ID verification
   - Policy copy or coverage verification
   - Specialist authorization letters
   - Family member consent forms
   - Pre-approval documentation

2. COMPLEX CONDITIONAL LOGIC:
   - Different forms for different claim amounts
   - Different forms for family members vs. individual
   - Different forms for different medical specialties
   - Validation dates and expiration windows
   - Translation requirements for multi-language support

3. ONGOING MONITORING:
   - Insurance companies respond via email
   - Need to parse responses to understand rejections
   - Need to track form validity expiration
   - Need to handle resubmissions and renewal

4. USER CHALLENGES:
   - Users don't know what forms to submit
   - Forms need to be renewed periodically
   - Different companies have different requirements
   - No centralized tracking of what's needed vs. submitted

## SOLUTION ARCHITECTURE

### 1. INSURANCE COMPANY CLASSES

Each insurance company is represented as a class that defines:
- What forms are required
- What forms are conditionally required
- How to validate eligibility
- How to parse their response emails
- What language and format to submit in

```
InsuranceCompany (Abstract Base)
├── KlalitInsurance
│   ├── get_form_requirements() → List[FormRequirement]
│   ├── validate_user_eligibility() → Dict
│   ├── get_conditional_requirements() → List[FormRequirement]
│   └── parse_response_email() → Dict
│
└── MeccabiInsurance
    ├── get_form_requirements() → List[FormRequirement]
    ├── validate_user_eligibility() → Dict
    ├── get_conditional_requirements() → List[FormRequirement]
    └── parse_response_email() → Dict
```

This design allows:
- Easy addition of new insurance companies
- Company-specific business logic encapsulated
- Reusable form type definitions
- Extensible for future requirements

### 2. FORM REQUIREMENT SYSTEM

Each form requirement includes:
- Form type (RECEIPT, CLAIM_FORM, MEDICAL_REPORT, etc.)
- Whether it's required or optional
- Validation rules (max age, original copy required, etc.)
- Conditional triggers
- User-facing notes

```
FormRequirement
├── form_type: FormType enum
├── required: bool
├── max_age_days: int (180 days, etc.)
├── requires_original: bool
├── requires_certified_copy: bool
├── condition: str (e.g., "if_amount_exceeds_1000")
├── condition_fn: callable
└── notes: str
```

### 3. LANGGRAPH WORKFLOW

The LangGraph workflow is the intelligent engine that:

1. **Analyzes User & Insurance Company**
   - Gets user profile information
   - Retrieves insurance company's form requirements
   - Evaluates conditional requirements

2. **Creates Form Submission Plan**
   - Determines which forms are actually needed
   - Prioritizes required vs. optional forms
   - Checks current submission status
   - Identifies potential issues

3. **Routes to Appropriate State**
   - If forms not submitted → "submit_forms" action
   - If forms submitted → "wait_for_response" action
   - If rejected → "fix_issues" action
   - If expiring → "renew_forms" action

4. **Synthesizes Recommendations**
   - Provides step-by-step guidance to user
   - Explains why each form is needed
   - Estimates timeline to completion

WORKFLOW GRAPH:
```
START
 │
 ├─→ initialize
 │    └─→ Load user data, create form state
 │
 ├─→ determine_required_forms
 │    └─→ Get insurance company requirements
 │    └─→ Evaluate eligibility
 │    └─→ Apply conditional logic
 │
 ├─→ analyze_user_readiness
 │    └─→ Check profile completeness
 │    └─→ Score compliance
 │    └─→ Identify missing information
 │
 ├─→ check_form_validity
 │    └─→ Check expiration dates
 │    └─→ Find rejected forms
 │    └─→ Calculate renewal dates
 │
 ├─→ create_submission_plan
 │    └─→ Route based on current state
 │    └─→ Generate action list
 │    └─→ Set next step
 │
 ├─→ format_final_recommendation
 │    └─→ Summarize findings
 │    └─→ Create user-facing recommendation
 │
 └─→ END
```

### 4. CLAIMFORMSTATE TRACKER

This data structure tracks:
- All required forms for a claim
- Which forms have been submitted
- Status of each submission (pending, accepted, rejected, expired)
- Validity dates and renewal requirements
- Next recommended action

```
ClaimFormState
├── claim_id: str
├── insurance_company: str
├── user_data: Dict
├── claim_amount: float
├── required_forms: List[FormRequirement]
├── submitted_forms: Dict[FormType, FormSubmission]
├── all_submitted: bool
├── all_accepted: bool
├── last_agent_analysis: Dict
└── next_action: str
```

This state is:
- Persistent (stored in database as JSON)
- Resumable (can reload and continue)
- Traceable (full audit trail)
- Queryable (can filter, sort, search)

### 5. DATABASE INTEGRATION

Three new tables:

**ClaimFormTracking**
- Links Claim to form tracking state
- Stores serialized ClaimFormState
- Indexes for quick querying (all_submitted, all_accepted, current_step)

**FormSubmissionRecord**
- Audit trail of each form submission
- Tracks file URLs, sizes, hashes
- Response tracking (accepted/rejected)
- Renewal dates

**Email Processing**
- Incoming emails parsed by insurance company's parse_response_email()
- Messages analyzed by LLM to extract key information
- Status updates trigger workflow re-analysis

### 6. WORKFLOW INTEGRATION POINTS

**Point 1: When Claim is Created**
```
User submits claim with:
- Insurance company
- Receipt
- Claim amount

System:
1. Creates Claim record
2. Creates ClaimFormTracking record
3. Runs form_determination_workflow
4. Returns list of required forms
5. Notifies user via API/UI
```

**Point 2: When Form is Submitted**
```
User uploads form:
- Form type
- File

System:
1. Stores FormSubmissionRecord
2. Updates ClaimFormState
3. Re-runs workflow to check if ready to submit to insurance
4. Returns next action
```

**Point 3: When Email Arrives**
```
Insurance company responds:
- Email body
- From: insurance company email

System:
1. ClaimEmail record created
2. Insurance company's parse_response_email() analyzes email
3. LLM optionally enhances analysis
4. Updates form submission statuses
5. Re-runs workflow
6. Determines if more info needed
```

**Point 4: Periodic Monitoring**
```
Daily/Weekly background tasks:
- Check for forms expiring within 7 days
- Re-run form determination for open claims
- Monitor claim status
- Send user notifications
```

## FLOW DIAGRAMS

### USER JOURNEY

```
User Creates Claim
       │
       ├─→ System: Create Claim record
       │
       └─→ System: Analyze Form Requirements
              │
              ├─→ Get Insurance Company rules
              ├─→ Evaluate user eligibility
              ├─→ Apply conditional logic
              └─→ Create form checklist
                     │
                     └─→ Return to User:
                        "You need these forms:
                        1. Receipt (have)
                        2. Claim Form (need)
                        3. Medical Report (optional)"

User Uploads Forms
       │
       └─→ System: Track Submission
              │
              ├─→ Store form metadata
              ├─→ Update tracking state
              └─→ Check if ready to submit

User Submits to Insurance
       │
       └─→ System: Compose Email
              │
              ├─→ Use insurance company template
              ├─→ Attach all forms
              ├─→ Send in correct language
              └─→ Record in email log

Insurance Responds
       │
       └─→ System: Analyze Response
              │
              ├─→ Parse email for key info
              ├─→ Extract form status
              ├─→ Identify missing items
              └─→ Update tracking
                     │
                     ├─→ If approved: Mark complete
                     ├─→ If rejected: Request fixes
                     └─→ If needs info: Flag issues

User Fixes Issues
       │
       └─→ Re-submit Forms
              │
              └─→ Repeat Until Approved
```

### LANGGRAPH DECISION TREE

```
Has user submitted all required forms?
├─ NO
│  ├─→ Output: "submit_forms"
│  └─→ Action: List pending forms
│
├─ YES
│  ├─→ Have all forms been accepted?
│  │   ├─ NO
│  │   │  ├─→ Were any rejected?
│  │   │  │   ├─ YES
│  │   │  │   │  ├─→ Output: "fix_issues"
│  │   │  │   │  └─→ Action: List rejected forms + reasons
│  │   │  │   │
│  │   │  │   └─ NO
│  │   │  │      ├─→ Output: "wait_for_response"
│  │   │  │      └─→ Action: Monitor for email response
│  │   │  │
│  │   │  └─→ Any forms expiring soon?
│  │   │      ├─ YES
│  │   │      │  ├─→ Output: "renew_forms"
│  │   │      │  └─→ Action: Resubmit expiring forms
│  │   │      │
│  │   │      └─ NO
│  │   │         └─→ Continue monitoring
│  │   │
│  │   └─ YES
│  │      ├─→ Output: "claim_processing"
│  │      └─→ Action: Await final decision/payment
```

## EXAMPLE SCENARIOS

### Scenario 1: Simple Claim

```
User: Student, had doctor visit, amount 150 NIS
Insurance: Clalit

Form determination:
- Required: Receipt, Claim Form, ID Verification, Proof of Payment
- Optional: Medical Report
- Conditional: None (amount too small)
- Eligibility: ✓ Valid Clalit member

Action: "submit_forms"
Recommendation: "Submit 4 forms for approval"
```

### Scenario 2: Complex Family Claim

```
User: Parent, claiming for 3 family members
Insurance: Clalit
Amount: 1500 NIS

Form determination:
- Required: Receipt, Claim Form, ID Verification, Proof of Payment
- Conditional (added):
  - Medical Report (amount > 500)
  - 3x Authorization Letters (family members)
  - Family Relationship Verification
- Eligibility: ✓ Valid Clalit member

Action: "submit_forms"
Recommendation: "Submit 8 forms including family authorizations"
```

### Scenario 3: Rejected Claim

```
User: Previous claim rejection
Insurance: Maccabi

System receives email: "Missing medical specialist authorization"

Form determination:
- Previous status: Rejected "missing_specialist_auth"
- New conditional forms: Add Specialist Authorization form
- Re-evaluate: ✓ Now complete

Action: "fix_issues"
Recommendation: "Add missing specialist authorization form and resubmit"
```

## CODE ORGANIZATION

```
insurance_forms.py
├─ FormType enum (RECEIPT, CLAIM_FORM, MEDICAL_REPORT, etc.)
├─ FormRequirement class
├─ FormSubmission class
├─ ClaimFormState class
├─ InsuranceCompany base class
├─ KlalitInsurance (subclass)
├─ MeccabiInsurance (subclass)
└─ InsuranceRegistry

form_determination_workflow.py
├─ FormDeterminationState (LangGraph state)
├─ initialize_form_state()
├─ determine_required_forms()
├─ analyze_user_readiness()
├─ check_form_validity()
├─ create_submission_plan()
├─ format_final_recommendation()
├─ build_form_determination_graph()
└─ run_form_determination_workflow()

forms_integration.py
├─ FormManagementService
│  ├─ create_claim_with_forms()
│  ├─ submit_form()
│  ├─ process_incoming_email()
│  ├─ check_expiring_forms()
│  └─ re_run_form_determination()
└─ Example API routes and background tasks

models.py (additions)
├─ ClaimFormTracking table
└─ FormSubmissionRecord table
```

## EXTENSION POINTS

### 1. Adding a New Insurance Company

```python
# Create new class
class MaHpInsurance(InsuranceCompany):
    name = "Mah"
    country = "Israel"
    
    def get_form_requirements(self) -> List[FormRequirement]:
        return [
            FormRequirement(FormType.RECEIPT, required=True),
            # ... add requirements specific to Mah
        ]
    
    def parse_response_email(self, email_body: str) -> Dict:
        # Add Mah-specific parsing logic
        ...

# Register it
InsuranceRegistry.register_company('mah', MaHpInsurance)
```

### 2. Adding Complex Conditional Logic

```python
def complex_conditional_fn(user_data: Dict, claim_amount: float) -> bool:
    # Check if user has complex scenario
    has_family = user_data.get('family_members_count', 0) > 0
    is_high_amount = claim_amount > 1000
    has_specialist = user_data.get('saw_specialist', False)
    
    return has_family or (is_high_amount and has_specialist)

requirement = FormRequirement(
    form_type=FormType.SPECIALIST_REPORT,
    required=False,
    condition_fn=complex_conditional_fn,
    notes="Required if family claim or specialist visit over 1000"
)
```

### 3. Custom Email Parsing

```python
def advanced_email_analysis(email_body: str) -> Dict:
    # Use LLM to deeply analyze email
    from langchain.chat_models import ChatOpenAI
    
    llm = ChatOpenAI(model="gpt-4")
    analysis = llm.invoke([
        HumanMessage(f"Analyze insurance response: {email_body}")
    ])
    
    return {
        'status': extract_status(analysis),
        'missing_forms': extract_forms(analysis),
        'issues': extract_issues(analysis)
    }
```

## TESTING STRATEGY

1. **Unit Tests**
   - Test each InsuranceCompany class
   - Test FormRequirement evaluation
   - Test FormSubmission validity checking

2. **Workflow Tests**
   - Test workflow with various user scenarios
   - Test conditional logic paths
   - Test form determination accuracy

3. **Integration Tests**
   - Test full claim creation flow
   - Test form submission tracking
   - Test email response processing

4. **Scenario Tests**
   - Simple claims
   - Complex family claims
   - Rejection and resubmission flows
   - Form expiration and renewal

## PERFORMANCE CONSIDERATIONS

1. **JSON Serialization**: Form state is stored as JSON in database
   - Fast serialization/deserialization
   - Human-readable in database
   - Easy to migrate/export

2. **Indexing**: ClaimFormTracking table has indexes on:
   - all_submitted (find claims ready to submit)
   - all_accepted (find completed claims)
   - current_step (filter by workflow state)

3. **Caching**: Can cache insurance company instances
   - InsuranceRegistry maintains class cache
   - Configuration immutable after registration

4. **Async Processing**: Background tasks for
   - Email monitoring
   - Form expiration checking
   - Workflow re-analysis

## SECURITY CONSIDERATIONS

1. **Input Validation**
   - Validate file uploads (type, size)
   - Sanitize email body before LLM processing
   - Validate form types against FormType enum

2. **Data Privacy**
   - Forms contain sensitive user data
   - Store on secure file storage (S3, etc.)
   - Audit trail in FormSubmissionRecord
   - Don't log email bodies containing PII

3. **Access Control**
   - Users can only see/modify their own claims
   - Insurance company email parsing is deterministic
   - Admin access to bulk operations

## FUTURE ENHANCEMENTS

1. **Multi-language Support**
   - Insurance company responses in various languages
   - Auto-translate requirement notes
   - User preference for submission language

2. **Document Intelligence**
   - OCR to verify form completeness
   - Auto-extract key info from uploaded documents
   - Validation that documents match requirements

3. **Predictive Analytics**
   - Historical approval rates by insurance company
   - Estimate claim success probability
   - Recommend optimizations

4. **Legal/Compliance**
   - Regulatory requirement tracking
   - Automatic form updates when regulations change
   - Audit trail for legal review

5. **Mobile Integration**
   - Mobile-optimized form submission UI
   - Camera integration for document capture
   - Offline-first document handling
"""

print(__doc__)
