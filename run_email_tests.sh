#!/bin/bash

# Email Loop Closure - Test Runner Script
# This script helps run the email/claim tests with proper configuration

set -e

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║ $1${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
}

print_step() {
    echo -e "${YELLOW}→ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if .env.test exists
if [ ! -f ".env.test" ]; then
    echo ""
    print_header "Setup: Create Test Configuration"
    print_step "Creating .env.test from template..."
    
    if [ ! -f ".env.test.example" ]; then
        print_error ".env.test.example not found"
        exit 1
    fi
    
    cp ".env.test.example" ".env.test"
    print_info "Created .env.test - please configure with your email:"
    print_info "  1. Edit .env.test"
    print_info "  2. Set TEST_EMAIL_RECIPIENT to your email address"
    print_info "  3. Set RESEND_API_KEY if you have one"
    echo ""
    read -p "Press enter to continue after editing .env.test..."
fi

# Load environment
echo ""
print_header "Configuration"
set -a
source .env.test
set +a

print_success "Loaded test configuration"
print_info "Database: $TEST_DB_TYPE ($TEST_DATABASE_URL)"
print_info "Test Email Recipient: ${TEST_EMAIL_RECIPIENT:-'[Not configured]'}"
print_info "Email Test Mode: ${EMAIL_TEST_MODE:-'true'}"

# Check for RESEND_API_KEY
if [ -z "$RESEND_API_KEY" ]; then
    print_error "RESEND_API_KEY not configured in .env.test"
    echo ""
    print_info "To get API key:"
    print_info "  1. Visit https://resend.com/api-keys"
    print_info "  2. Create or copy API key"
    print_info "  3. Add to .env.test: RESEND_API_KEY=re_your_key"
    echo ""
else
    print_success "RESEND_API_KEY configured"
fi

# Run tests based on argument
test_type="${1:-all}"

run_unit_tests() {
    echo ""
    print_header "Unit Tests: Email Service"
    pytest tests/unit/test_email_service.py -v --tb=short
}

run_claims_tests() {
    echo ""
    print_header "Integration Tests: Claims API"
    pytest tests/integration/test_claims.py -v --tb=short
}

run_webhook_tests() {
    echo ""
    print_header "Integration Tests: Webhooks"
    pytest tests/integration/test_webhooks.py -v --tb=short
}

run_e2e_tests() {
    echo ""
    print_header "End-to-End Tests: Complete Workflow"
    pytest tests/integration/test_e2e_workflow.py -v --tb=short
}

run_all_tests() {
    run_unit_tests
    run_claims_tests
    run_webhook_tests
    run_e2e_tests
}

# Execute based on type
case "$test_type" in
    unit)
        run_unit_tests
        ;;
    claims)
        run_claims_tests
        ;;
    webhooks)
        run_webhook_tests
        ;;
    e2e)
        run_e2e_tests
        ;;
    all)
        run_all_tests
        ;;
    *)
        print_header "Email Loop Closure - Test Runner"
        echo ""
        echo "Usage: ./run_email_tests.sh [test_type]"
        echo ""
        echo "Test types:"
        echo "  unit       Run email service unit tests"
        echo "  claims     Run claims API integration tests"
        echo "  webhooks   Run webhook integration tests"
        echo "  e2e        Run end-to-end workflow tests"
        echo "  all        Run all tests (default)"
        echo ""
        echo "Examples:"
        echo "  ./run_email_tests.sh              # Run all tests"
        echo "  ./run_email_tests.sh unit         # Run unit tests only"
        echo "  ./run_email_tests.sh e2e          # Run end-to-end tests"
        echo ""
        ;;
esac

# Summary
echo ""
if [ $? -eq 0 ]; then
    print_success "All tests passed!"
else
    print_error "Some tests failed"
    exit 1
fi
