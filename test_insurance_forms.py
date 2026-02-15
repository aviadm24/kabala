"""
Insurance Forms System - Testing & Validation
==============================================

Test utilities and validation functions for the insurance forms system.
Run these tests to verify the system is working correctly.
"""

import unittest
from datetime import datetime, timedelta
import json

from insurance_forms import (
    FormType, FormRequirement, FormSubmission, ClaimFormState,
    InsuranceRegistry, KlalitInsurance, MeccabiInsurance
)
from form_determination_workflow import (
    run_form_determination_workflow, get_insurance_requirements,
    check_form_status, analyze_insurance_email, get_user_compliance_score
)


class TestInsuranceCompanies(unittest.TestCase):
    """Test insurance company class definitions"""
    
    def test_clalit_registered(self):
        """Clalit should be registered in the registry"""
        company = InsuranceRegistry.get_company('clalit')
        self.assertEqual(company.name, "Clalit")
        self.assertEqual(company.country, "Israel")
        self.assertIsNotNone(company.email)
    
    def test_maccabi_registered(self):
        """Maccabi should be registered in the registry"""
        company = InsuranceRegistry.get_company('maccabi')
        self.assertEqual(company.name, "Maccabi")
        self.assertEqual(company.country, "Israel")
        self.assertIsNotNone(company.email)
    
    def test_clalit_has_form_requirements(self):
        """Clalit should have form requirements"""
        company = InsuranceRegistry.get_company('clalit')
        forms = company.get_form_requirements()
        self.assertGreater(len(forms), 0)
        self.assertTrue(any(f.form_type == FormType.RECEIPT for f in forms))
    
    def test_clalit_validate_eligibility(self):
        """Clalit should validate user eligibility"""
        company = InsuranceRegistry.get_company('clalit')
        
        # Valid user
        valid_user = {'email': 'test@test.com', 'id_number': '123456789'}
        result = company.validate_user_eligibility(valid_user)
        self.assertTrue(result['eligible'])
        
        # Invalid user (missing email)
        invalid_user = {'id_number': '123456789'}
        result = company.validate_user_eligibility(invalid_user)
        self.assertFalse(result['eligible'])
    
    def test_clalit_conditional_requirements(self):
        """Clalit should provide conditional requirements based on amount"""
        company = InsuranceRegistry.get_company('clalit')
        user_data = {'email': 'test@test.com'}
        
        # Low amount
        forms_low = company.get_conditional_requirements(user_data, 100)
        self.assertEqual(len(forms_low), 0)
        
        # High amount (should require medical report)
        forms_high = company.get_conditional_requirements(user_data, 600)
        self.assertGreater(len(forms_high), 0)
        self.assertTrue(any(f.form_type == FormType.MEDICAL_REPORT for f in forms_high))
    
    def test_clalit_family_requirements(self):
        """Clalit should require additional forms for family claims"""
        company = InsuranceRegistry.get_company('clalit')
        
        user_data_family = {
            'email': 'test@test.com',
            'family_members_count': 2
        }
        
        forms = company.get_conditional_requirements(user_data_family, 200)
        # Should have authorization letter requirement
        self.assertTrue(any(f.form_type == FormType.AUTHORIZATION_LETTER for f in forms))


class TestFormRequirements(unittest.TestCase):
    """Test form requirement specification"""
    
    def test_form_requirement_basic(self):
        """Form requirement should store basic info"""
        req = FormRequirement(
            form_type=FormType.RECEIPT,
            required=True,
            notes="Original receipt"
        )
        self.assertEqual(req.form_type, FormType.RECEIPT)
        self.assertTrue(req.required)
        self.assertFalse(req.optional)
    
    def test_form_requirement_is_applicable_required(self):
        """Required forms should always be applicable"""
        req = FormRequirement(FormType.RECEIPT, required=True)
        self.assertTrue(req.is_applicable({}, 0))
    
    def test_form_requirement_is_applicable_optional(self):
        """Optional forms should not be applicable by default"""
        req = FormRequirement(FormType.RECEIPT, optional=True)
        self.assertFalse(req.is_applicable({}, 0))
    
    def test_form_requirement_with_condition(self):
        """Form requirement should evaluate conditions"""
        def amount_threshold(user_data, claim_amount):
            return claim_amount > 500
        
        req = FormRequirement(
            form_type=FormType.MEDICAL_REPORT,
            condition_fn=amount_threshold
        )
        
        self.assertFalse(req.is_applicable({}, 300))
        self.assertTrue(req.is_applicable({}, 600))


class TestFormSubmission(unittest.TestCase):
    """Test form submission tracking"""
    
    def test_form_submission_valid(self):
        """Form submission should validate when within valid period"""
        submission = FormSubmission(
            form_type=FormType.RECEIPT,
            submitted_at=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=90)
        )
        self.assertTrue(submission.is_still_valid())
    
    def test_form_submission_expired(self):
        """Form submission should be invalid when expired"""
        submission = FormSubmission(
            form_type=FormType.RECEIPT,
            submitted_at=datetime.utcnow() - timedelta(days=100),
            valid_until=datetime.utcnow() - timedelta(days=10)
        )
        self.assertFalse(submission.is_still_valid())
    
    def test_form_submission_days_until_expiry(self):
        """Should calculate days until expiry correctly"""
        submission = FormSubmission(
            form_type=FormType.RECEIPT,
            submitted_at=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=30)
        )
        days_left = submission.days_until_expiry()
        self.assertIsNotNone(days_left)
        self.assertEqual(days_left, 30)
    
    def test_form_submission_status_tracking(self):
        """Should track form submission status"""
        submission = FormSubmission(
            form_type=FormType.RECEIPT,
            submitted_at=datetime.utcnow(),
            status='submitted'
        )
        self.assertEqual(submission.status, 'submitted')
        
        # Update status
        submission.response_received_at = datetime.utcnow()
        submission.status = 'accepted'
        self.assertEqual(submission.status, 'accepted')


class TestClaimFormState(unittest.TestCase):
    """Test claim form state management"""
    
    def test_claim_form_state_creation(self):
        """ClaimFormState should initialize properly"""
        state = ClaimFormState(
            claim_id='test_001',
            insurance_company='clalit',
            user_data={'email': 'test@test.com'},
            claim_amount=300.0
        )
        self.assertEqual(state.claim_id, 'test_001')
        self.assertEqual(state.insurance_company, 'clalit')
        self.assertEqual(state.claim_amount, 300.0)
    
    def test_pending_forms(self):
        """Should correctly identify pending forms"""
        state = ClaimFormState(
            claim_id='test_001',
            insurance_company='clalit',
            user_data={},
            claim_amount=300.0
        )
        
        # Add requirements
        state.required_forms = [
            FormRequirement(FormType.RECEIPT, required=True),
            FormRequirement(FormType.CLAIM_FORM, required=True),
        ]
        
        # Submit one
        state.submitted_forms[FormType.RECEIPT] = FormSubmission(
            form_type=FormType.RECEIPT,
            submitted_at=datetime.utcnow()
        )
        
        # Check pending
        pending = state.get_pending_forms()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].form_type, FormType.CLAIM_FORM)
    
    def test_expiring_forms(self):
        """Should identify expiring forms"""
        state = ClaimFormState(
            claim_id='test_001',
            insurance_company='clalit',
            user_data={},
            claim_amount=300.0
        )
        
        # Add submissions
        state.submitted_forms[FormType.RECEIPT] = FormSubmission(
            form_type=FormType.RECEIPT,
            submitted_at=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=5)  # Expiring soon
        )
        
        state.submitted_forms[FormType.CLAIM_FORM] = FormSubmission(
            form_type=FormType.CLAIM_FORM,
            submitted_at=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=100)  # Good
        )
        
        # Check expiring (within 7 days)
        expiring = state.get_expiring_forms(days_threshold=7)
        self.assertEqual(len(expiring), 1)
        self.assertEqual(expiring[0].form_type, FormType.RECEIPT)
    
    def test_form_state_serialization(self):
        """Form state should serialize to dict for database"""
        state = ClaimFormState(
            claim_id='test_001',
            insurance_company='clalit',
            user_data={'email': 'test@test.com'},
            claim_amount=300.0
        )
        
        state.required_forms = [
            FormRequirement(FormType.RECEIPT, required=True)
        ]
        
        # Serialize
        state_dict = state.to_dict()
        
        # Verify structure
        self.assertEqual(state_dict['claim_id'], 'test_001')
        self.assertEqual(state_dict['insurance_company'], 'clalit')
        self.assertIn('required_forms', state_dict)
        self.assertIn('submitted_forms', state_dict)
        
        # Should be JSON serializable
        json_str = json.dumps(state_dict, default=str)
        self.assertIsInstance(json_str, str)


class TestFormDeterminationWorkflow(unittest.TestCase):
    """Test LangGraph workflow"""
    
    def test_workflow_simple_claim(self):
        """Workflow should handle simple claim"""
        result = run_form_determination_workflow(
            claim_id='test_001',
            user_id='user_001',
            user_data={
                'username': 'test_user',
                'email': 'test@test.com',
                'family_members_count': 0
            },
            insurance_company='clalit',
            claim_amount=200.0,
            claim_description='Doctor visit'
        )
        
        self.assertEqual(result['claim_id'], 'test_001')
        self.assertIn('next_step', result)
        self.assertIn('required_forms', result)
        self.assertGreater(len(result['required_forms']), 0)
    
    def test_workflow_family_claim(self):
        """Workflow should handle family claim"""
        result = run_form_determination_workflow(
            claim_id='test_002',
            user_id='user_002',
            user_data={
                'username': 'test_user',
                'email': 'test@test.com',
                'family_members_count': 2
            },
            insurance_company='clalit',
            claim_amount=500.0,
            claim_description='Family claim'
        )
        
        num_forms = len(result['required_forms'])
        # Family claims should have more forms
        self.assertGreater(num_forms, 1)
    
    def test_workflow_high_amount_claim(self):
        """Workflow should identify additional forms for high amounts"""
        result_low = run_form_determination_workflow(
            claim_id='test_003a',
            user_id='user_003',
            user_data={
                'username': 'test_user',
                'email': 'test@test.com',
                'family_members_count': 0
            },
            insurance_company='clalit',
            claim_amount=100.0
        )
        
        result_high = run_form_determination_workflow(
            claim_id='test_003b',
            user_id='user_003',
            user_data={
                'username': 'test_user',
                'email': 'test@test.com',
                'family_members_count': 0
            },
            insurance_company='clalit',
            claim_amount=600.0  # High amount
        )
        
        # High amount should require more forms
        self.assertGreater(
            len(result_high['required_forms']),
            len(result_low['required_forms'])
        )
    
    def test_workflow_next_steps(self):
        """Workflow should recommend appropriate next steps"""
        result = run_form_determination_workflow(
            claim_id='test_004',
            user_id='user_004',
            user_data={
                'username': 'test_user',
                'email': 'test@test.com'
            },
            insurance_company='clalit',
            claim_amount=300.0
        )
        
        # Should always have a next step
        self.assertIsNotNone(result['next_step'])
        self.assertIn(result['next_step'], [
            'submit_forms',
            'wait_for_response',
            'fix_issues',
            'claim_processing'
        ])


class TestInsuranceRegistry(unittest.TestCase):
    """Test insurance company registry"""
    
    def test_list_companies(self):
        """Registry should list available companies"""
        companies = InsuranceRegistry.list_companies()
        self.assertGreater(len(companies), 0)
        self.assertIn('clalit', companies)
    
    def test_get_nonexistent_company(self):
        """Registry should raise error for unknown company"""
        with self.assertRaises(ValueError):
            InsuranceRegistry.get_company('nonexistent')


class IntegrationTest(unittest.TestCase):
    """End-to-end integration tests"""
    
    def test_complete_claim_workflow(self):
        """Test complete workflow from claim to recommendation"""
        # 1. Run form determination
        result = run_form_determination_workflow(
            claim_id='integration_001',
            user_id='user_123',
            user_data={
                'username': 'john_doe',
                'email': 'john@example.com',
                'phone': '+1-555-0000',
                'family_members_count': 0
            },
            insurance_company='clalit',
            claim_amount=350.0,
            claim_description='Doctor visit and lab tests'
        )
        
        # 2. Verify we got a proper result
        self.assertIsNotNone(result)
        self.assertEqual(result['claim_id'], 'integration_001')
        self.assertGreater(len(result['required_forms']), 0)
        
        # 3. Simulate form submission
        form_state = result.get('form_state', {})
        self.assertIsNotNone(form_state)
        
        # 4. Verify we can serialize
        self.assertIsInstance(form_state, dict)
        json_str = json.dumps(form_state, default=str)
        self.assertIsInstance(json_str, str)
    
    def test_form_state_lifecycle(self):
        """Test complete form state lifecycle"""
        # 1. Create state
        state = ClaimFormState(
            claim_id='lifecycle_001',
            insurance_company='clalit',
            user_data={'email': 'test@test.com'},
            claim_amount=300.0
        )
        
        # 2. Add requirements
        state.required_forms = [
            FormRequirement(FormType.RECEIPT, required=True),
            FormRequirement(FormType.CLAIM_FORM, required=True),
        ]
        
        # 3. Submit first form
        state.submitted_forms[FormType.RECEIPT] = FormSubmission(
            form_type=FormType.RECEIPT,
            submitted_at=datetime.utcnow(),
            status='submitted'
        )
        
        # 4. Verify state
        self.assertEqual(len(state.get_pending_forms()), 1)
        
        # 5. Mark as accepted
        state.submitted_forms[FormType.RECEIPT].status = 'accepted'
        
        # 6. Submit second form
        state.submitted_forms[FormType.CLAIM_FORM] = FormSubmission(
            form_type=FormType.CLAIM_FORM,
            submitted_at=datetime.utcnow(),
            status='submitted'
        )
        
        # 7. Verify all submitted
        self.assertEqual(len(state.get_pending_forms()), 0)
        
        # 8. Serialize
        state_dict = state.to_dict()
        self.assertEqual(len(state_dict['submitted_forms']), 2)


def run_all_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestInsuranceCompanies))
    suite.addTests(loader.loadTestsFromTestCase(TestFormRequirements))
    suite.addTests(loader.loadTestsFromTestCase(TestFormSubmission))
    suite.addTests(loader.loadTestsFromTestCase(TestClaimFormState))
    suite.addTests(loader.loadTestsFromTestCase(TestFormDeterminationWorkflow))
    suite.addTests(loader.loadTestsFromTestCase(TestInsuranceRegistry))
    suite.addTests(loader.loadTestsFromTestCase(IntegrationTest))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    print("=" * 70)
    print("INSURANCE FORMS SYSTEM - TEST SUITE")
    print("=" * 70)
    print()
    
    result = run_all_tests()
    
    print()
    print("=" * 70)
    if result.wasSuccessful():
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
        print(f"  Failures: {len(result.failures)}")
        print(f"  Errors: {len(result.errors)}")
    print("=" * 70)
