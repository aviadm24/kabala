"""
LangGraph Workflow for Dynamic Form Determination
==================================================

This module implements a LangGraph agent that:
1. Analyzes user profile and claim details
2. Determines which forms are required
3. Tracks form submissions and responses
4. Processes incoming emails to identify issues
5. Recommends next steps (submit, wait, fix, etc.)

The workflow uses LLM reasoning to handle edge cases and understand
incoming insurance company responses.
"""

from typing import Dict, List, Any, Optional, Tuple, TypedDict, Annotated
from datetime import datetime
import json
import logging

from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from insurance_forms import (
    InsuranceRegistry, ClaimFormState, FormSubmission, FormType,
    FormRequirement, InsuranceCompany
)

logger = logging.getLogger(__name__)


# ============================================================================
# STATE DEFINITION
# ============================================================================

class FormDeterminationState(TypedDict):
    """LangGraph state for form determination workflow"""
    
    # Initial inputs
    claim_id: str
    user_id: str
    user_data: Dict[str, Any]
    insurance_company_name: str
    claim_amount: float
    claim_description: str
    
    # Insurance company instance
    insurance_company: InsuranceCompany
    
    # Form state
    form_state: ClaimFormState
    
    # Message history for LLM reasoning
    messages: List[BaseMessage]
    
    # Analysis results
    analysis_results: Dict[str, Any]
    
    # Actions to take
    actions: List[Dict[str, Any]]
    
    # Final recommendation
    next_step: str  # "submit_forms", "wait_for_response", "fix_issues", "more_info_needed"
    recommendation: str


# ============================================================================
# TOOLS FOR THE AGENT
# ============================================================================

@tool
def get_insurance_requirements(insurance_company_name: str, user_data: Dict[str, Any], claim_amount: float) -> Dict[str, Any]:
    """
    Get the form requirements for an insurance company based on user profile.
    
    Args:
        insurance_company_name: Name of the insurance company
        user_data: User profile information
        claim_amount: Amount being claimed
    
    Returns:
        Dictionary with required forms and conditions
    """
    try:
        company = InsuranceRegistry.get_company(insurance_company_name)
        
        # Validate eligibility
        eligibility = company.validate_user_eligibility(user_data)
        if not eligibility['eligible']:
            return {
                'eligible': False,
                'reason': eligibility['reason'],
                'forms': []
            }
        
        # Get base requirements
        base_forms = company.get_form_requirements()
        
        # Get conditional requirements
        conditional_forms = company.get_conditional_requirements(user_data, claim_amount)
        
        all_forms = base_forms + conditional_forms
        
        return {
            'eligible': True,
            'insurance_company': company.name,
            'contact_email': company.email,
            'processing_days': company.claim_processing_days,
            'required_forms': [
                {
                    'form_type': f.form_type.value,
                    'required': f.required,
                    'optional': f.optional,
                    'max_age_days': f.max_age_days,
                    'requires_original': f.requires_original,
                    'notes': f.notes,
                    'reason': f.condition if f.condition else 'Standard requirement'
                }
                for f in all_forms
            ],
            'num_forms_required': len([f for f in all_forms if f.required])
        }
    except Exception as e:
        return {
            'eligible': False,
            'reason': f'Error retrieving requirements: {str(e)}',
            'forms': []
        }


@tool
def check_form_status(form_state: Dict[str, Any], form_type: str) -> Dict[str, Any]:
    """
    Check the submission status of a specific form.
    
    Args:
        form_state: Current form state
        form_type: The form type to check
    
    Returns:
        Status information for the form
    """
    submitted_forms = form_state.get('submitted_forms', {})
    
    if form_type in submitted_forms:
        form_info = submitted_forms[form_type]
        return {
            'form_type': form_type,
            'status': form_info['status'],
            'submitted': True,
            'submitted_at': form_info['submitted_at'],
            'valid_until': form_info['valid_until'],
            'issues': form_info.get('issues', [])
        }
    else:
        return {
            'form_type': form_type,
            'status': 'not_submitted',
            'submitted': False,
            'reason': 'Form not yet submitted'
        }


@tool
def analyze_insurance_email(email_body: str, insurance_company_name: str) -> Dict[str, Any]:
    """
    Parse and analyze incoming email from insurance company to determine status and next steps.
    
    Args:
        email_body: The email body text
        insurance_company_name: Which insurance company sent the email
    
    Returns:
        Analysis of the email including status, missing forms, issues
    """
    try:
        company = InsuranceRegistry.get_company(insurance_company_name)
        result = company.parse_response_email(email_body)
        
        return {
            'email_status': result['status'],  # approved, rejected, needs_info, pending
            'missing_forms': result['missing_forms'],
            'issues_identified': result['issues'],
            'next_steps': result['next_steps'],
            'raw_analysis': result
        }
    except Exception as e:
        return {
            'error': str(e),
            'email_status': 'unknown',
            'missing_forms': [],
            'issues_identified': [f'Could not parse email: {str(e)}'],
            'next_steps': 'Manual review required'
        }


@tool
def get_user_compliance_score(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze user data completeness to predict claim success rate.
    
    Returns scoring on:
    - Profile completeness (email, phone, ID, etc.)
    - Documentation organization
    - Historical claim patterns
    """
    score = 0
    missing_fields = []
    
    required_fields = ['email', 'username']
    for field in required_fields:
        if user_data.get(field):
            score += 10
        else:
            missing_fields.append(field)
    
    # Family data
    if user_data.get('family_members') or user_data.get('family_members_count', 0) > 0:
        score += 5
    
    # Insurance info
    if user_data.get('insurance_companies'):
        score += 10
    
    # Phone
    if user_data.get('phone'):
        score += 5
    
    return {
        'compliance_score': score,
        'max_score': 50,
        'percentage': round((score / 50) * 100, 1),
        'missing_fields': missing_fields,
        'recommendation': 'Good - proceed with claim' if score >= 30 else 'Low - collect more info first'
    }


# ============================================================================
# WORKFLOW NODES
# ============================================================================

def initialize_form_state(state: FormDeterminationState) -> FormDeterminationState:
    """Initialize the form determination workflow"""
    logger.info(f"Initializing form state for claim {state['claim_id']}")
    
    # Get insurance company instance
    state['insurance_company'] = InsuranceRegistry.get_company(state['insurance_company_name'])
    
    # Initialize form state
    state['form_state'] = ClaimFormState(
        claim_id=state['claim_id'],
        insurance_company=state['insurance_company_name'],
        user_data=state['user_data'],
        claim_amount=state['claim_amount']
    )
    
    # Initialize messages
    state['messages'] = [
        HumanMessage(content=f"""
You are managing a health insurance claim for {state['claim_amount']} from {state['insurance_company_name']}.

User Information:
- Username: {state['user_data'].get('username')}
- Email: {state['user_data'].get('email')}
- Phone: {state['user_data'].get('phone')}
- Family Members: {state['user_data'].get('family_members_count', 0)}
- Insurance Companies: {state['user_data'].get('insurance_companies')}

Claim Details:
- Amount: {state['claim_amount']}
- Description: {state['claim_description']}

Your task:
1. Determine all forms required for this claim
2. Analyze user eligibility
3. Identify any potential issues
4. Create a submission plan

Start by getting the insurance company requirements.
        """)
    ]
    
    state['analysis_results'] = {}
    state['actions'] = []
    
    return state


def determine_required_forms(state: FormDeterminationState) -> FormDeterminationState:
    """Use LLM to analyze requirements and create extraction plan"""
    logger.info(f"Determining required forms for {state['insurance_company_name']}")
    
    # Get requirements using tool
    requirements = get_insurance_requirements(
        state['insurance_company_name'],
        state['user_data'],
        state['claim_amount']
    )
    
    state['analysis_results']['requirements'] = requirements
    
    if not requirements['eligible']:
        state['messages'].append(AIMessage(content=f"""
The user is not eligible for this insurance company reimbursement:
{requirements['reason']}

Cannot proceed with claim processing.
        """))
        return state
    
    # Update form state with requirements
    required_forms = []
    for form_req in requirements['required_forms']:
        req = FormRequirement(
            form_type=FormType(form_req['form_type']),
            required=form_req['required'],
            optional=form_req['optional'],
            max_age_days=form_req['max_age_days'],
            requires_original=form_req['requires_original'],
            notes=form_req['notes']
        )
        required_forms.append(req)
    
    state['form_state'].required_forms = required_forms
    
    state['messages'].append(AIMessage(content=f"""
Insurance Requirements Retrieved:
- Insurance Company: {requirements['insurance_company']}
- Contact: {requirements['contact_email']}
- Processing Time: {requirements['processing_days']} days
- Required Forms: {requirements['num_forms_required']}

Required forms:
{json.dumps(requirements['required_forms'], indent=2, ensure_ascii=False)}
    """))
    
    return state


def analyze_user_readiness(state: FormDeterminationState) -> FormDeterminationState:
    """Analyze if user profile has necessary information"""
    logger.info("Analyzing user readiness")
    
    compliance = get_user_compliance_score(state['user_data'])
    state['analysis_results']['compliance'] = compliance
    
    state['messages'].append(AIMessage(content=f"""
User Profile Analysis:
- Compliance Score: {compliance['compliance_score']}/{compliance['max_score']} ({compliance['percentage']}%)
- Missing Fields: {', '.join(compliance['missing_fields']) if compliance['missing_fields'] else 'None'}
- Recommendation: {compliance['recommendation']}
    """))
    
    return state


def check_form_validity(state: FormDeterminationState) -> FormDeterminationState:
    """Check expiration dates and validity of already submitted forms"""
    logger.info("Checking submitted form validity")
    
    if not state['form_state'].submitted_forms:
        state['messages'].append(AIMessage(content="No forms have been submitted yet."))
        return state
    
    expiring_forms = state['form_state'].get_expiring_forms(days_threshold=7)
    rejected_forms = state['form_state'].get_rejected_forms()
    
    issues = []
    if expiring_forms:
        issues.append(f"{len(expiring_forms)} forms expiring within 7 days")
    if rejected_forms:
        issues.append(f"{len(rejected_forms)} forms were rejected")
    
    state['analysis_results']['form_validity'] = {
        'expiring_count': len(expiring_forms),
        'rejected_count': len(rejected_forms),
        'issues': issues
    }
    
    return state


def create_submission_plan(state: FormDeterminationState) -> FormDeterminationState:
    """Create action plan for what needs to be done"""
    logger.info("Creating submission plan")
    
    pending_forms = state['form_state'].get_pending_forms()
    rejected_forms = state['form_state'].get_rejected_forms()
    
    actions = []
    
    # Determine next action
    if rejected_forms:
        state['next_step'] = "fix_issues"
        for form in rejected_forms:
            actions.append({
                'action': 'fix_form',
                'form_type': form.form_type.value,
                'reason': form.issues_found,
                'priority': 'HIGH'
            })
        state['recommendation'] = f"User needs to fix {len(rejected_forms)} rejected form(s)"
    
    elif pending_forms:
        state['next_step'] = "submit_forms"
        for form in pending_forms:
            actions.append({
                'action': 'collect_and_submit',
                'form_type': form.form_type.value,
                'priority': 'HIGH' if form.required else 'LOW'
            })
        state['recommendation'] = f"Ready to submit {len(pending_forms)} form(s)"
    
    elif state['form_state'].submitted_forms and not state['form_state'].all_accepted:
        state['next_step'] = "wait_for_response"
        state['recommendation'] = "All forms submitted. Waiting for insurance company response."
        actions.append({
            'action': 'monitor_email',
            'priority': 'HIGH',
            'check_frequency': 'daily'
        })
    
    else:
        state['next_step'] = "claim_processing"
        state['recommendation'] = "Claim is being processed by insurance company."
    
    state['actions'] = actions
    
    state['messages'].append(AIMessage(content=f"""
Submission Plan:
Next Step: {state['next_step']}
Recommendation: {state['recommendation']}

Actions to Take:
{json.dumps(actions, indent=2, ensure_ascii=False)}
    """))
    
    return state


def format_final_recommendation(state: FormDeterminationState) -> FormDeterminationState:
    """Create final summary and recommendation"""
    logger.info("Formatting final recommendation")
    
    summary = f"""
=== CLAIM FORM DETERMINATION SUMMARY ===

Claim ID: {state['claim_id']}
Insurance Company: {state['insurance_company_name']}
Claim Amount: {state['claim_amount']}

REQUIRED FORMS: {len(state['form_state'].required_forms)}
- {len([f for f in state['form_state'].required_forms if f.required])} mandatory
- {len([f for f in state['form_state'].required_forms if f.optional])} optional

SUBMITTED: {len(state['form_state'].submitted_forms)}
PENDING: {len(state['form_state'].get_pending_forms())}

NEXT STEP: {state['next_step']}
RECOMMENDATION: {state['recommendation']}

ACTIONS:
"""
    for action in state['actions']:
        summary += f"\n- {action['action']}: {action.get('form_type', '')} (Priority: {action['priority']})"
    
    # Potential Issues
    if state['analysis_results'].get('form_validity', {}).get('issues'):
        summary += f"\n\nPOTENTIAL ISSUES:\n"
        for issue in state['analysis_results']['form_validity']['issues']:
            summary += f"- {issue}\n"
    
    state['recommendation'] = summary
    
    return state


# ============================================================================
# WORKFLOW ROUTING
# ============================================================================

def should_analyze_compliance(state: FormDeterminationState) -> bool:
    """Determine if we should check user compliance"""
    # Always check
    return True


def should_check_validity(state: FormDeterminationState) -> bool:
    """Only check if forms have been submitted"""
    return len(state['form_state'].submitted_forms) > 0


def route_based_on_state(state: FormDeterminationState) -> str:
    """Route to appropriate node based on current state"""
    # Simple routing - can be enhanced
    return "end"


# ============================================================================
# BUILD THE WORKFLOW GRAPH
# ============================================================================

def build_form_determination_graph():
    """Construct the LangGraph workflow"""
    
    workflow = StateGraph(FormDeterminationState)
    
    # Add nodes
    workflow.add_node("initialize", initialize_form_state)
    workflow.add_node("determine_forms", determine_required_forms)
    workflow.add_node("analyze_compliance", analyze_user_readiness)
    workflow.add_node("check_validity", check_form_validity)
    workflow.add_node("create_plan", create_submission_plan)
    workflow.add_node("format_recommendation", format_final_recommendation)
    
    # Define edges
    workflow.add_edge(START, "initialize")
    workflow.add_edge("initialize", "determine_forms")
    workflow.add_edge("determine_forms", "analyze_compliance")
    workflow.add_edge("analyze_compliance", "check_validity")
    workflow.add_edge("check_validity", "create_plan")
    workflow.add_edge("create_plan", "format_recommendation")
    workflow.add_edge("format_recommendation", END)
    
    # Compile
    return workflow.compile()


# ============================================================================
# WORKFLOW EXECUTION
# ============================================================================

def run_form_determination_workflow(
    claim_id: str,
    user_id: str,
    user_data: Dict[str, Any],
    insurance_company: str,
    claim_amount: float,
    claim_description: str = "",
    form_state: Optional[ClaimFormState] = None
) -> Dict[str, Any]:
    """
    Execute the form determination workflow.
    
    Args:
        claim_id: Unique claim identifier
        user_id: User identifier
        user_data: User profile data
        insurance_company: Insurance company name
        claim_amount: Amount being claimed
        claim_description: Description of the claim
        form_state: Optional existing form state to resume from
    
    Returns:
        Dict with workflow results including recommendations
    """
    
    graph = build_form_determination_graph()
    
    initial_state = {
        'claim_id': claim_id,
        'user_id': user_id,
        'user_data': user_data,
        'insurance_company_name': insurance_company,
        'claim_amount': claim_amount,
        'claim_description': claim_description,
        'insurance_company': None,
        'form_state': form_state,
        'messages': [],
        'analysis_results': {},
        'actions': [],
        'next_step': 'initializing',
        'recommendation': ''
    }
    
    # Run the workflow
    result = graph.invoke(initial_state)
    
    return {
        'claim_id': result['claim_id'],
        'next_step': result['next_step'],
        'recommendation': result['recommendation'],
        'form_state': result['form_state'].to_dict(),
        'required_forms': [
            {
                'form_type': f.form_type.value,
                'required': f.required,
                'notes': f.notes
            }
            for f in result['form_state'].required_forms
        ],
        'pending_forms': [
            {
                'form_type': f.form_type.value,
                'required': f.required,
                'notes': f.notes
            }
            for f in result['form_state'].get_pending_forms()
        ],
        'actions': result['actions'],
        'analysis': result['analysis_results']
    }


if __name__ == "__main__":
    # Example usage
    user_data = {
        'username': 'aviad_moshe',
        'email': 'aviad@example.com',
        'phone': '+972-123-456789',
        'family_members_count': 2,
        'insurance_companies': 'clalit'
    }
    
    result = run_form_determination_workflow(
        claim_id='claim_001',
        user_id='user_001',
        user_data=user_data,
        insurance_company='clalit',
        claim_amount=350.0,
        claim_description='Doctor visit and lab tests'
    )
    
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
