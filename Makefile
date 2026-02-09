#!/bin/bash
# Makefile for common test tasks
# Usage: make test, make test-unit, etc.

.PHONY: test test-unit test-integration test-regression test-all test-coverage test-verbose test-local test-staging clean

# Default - run core tests
test:
	python run_tests.py --unit --integration --regression

# Unit tests only
test-unit:
	python run_tests.py --unit

# Integration tests only
test-integration:
	python run_tests.py --integration

# Regression tests only
test-regression:
	python run_tests.py --regression

# All tests including slow ones
test-all:
	python run_tests.py --unit --integration --regression --slow

# With coverage
test-coverage:
	python run_tests.py --unit --integration --regression --coverage

# Verbose output
test-verbose:
	python run_tests.py --unit --integration --regression -v

# Test locally
test-local:
	TEST_ENV=local python run_tests.py --unit --integration --regression

# Test staging
test-staging:
	TEST_ENV=staging python run_tests.py --regression

# Quick smoke test
test-smoke:
	python run_tests.py --unit

# Clean test artifacts
clean:
	rm -f test.db
	rm -rf .pytest_cache
	rm -rf htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Install test dependencies
install-test:
	pip install -r requirements-test.txt

# Run a specific test
test-one:
	@echo "Usage: make test-one FILE=tests/unit/test_core.py::TestClass::test_method"
	pytest $(FILE)

help:
	@echo "Available targets:"
	@echo "  make test              - Run unit, integration, and regression tests"
	@echo "  make test-unit         - Run unit tests only"
	@echo "  make test-integration  - Run integration tests only"
	@echo "  make test-regression   - Run regression tests only"
	@echo "  make test-all          - Run all tests including slow tests"
	@echo "  make test-coverage     - Run tests with coverage report"
	@echo "  make test-verbose      - Run tests with verbose output"
	@echo "  make test-local        - Run tests against local environment"
	@echo "  make test-staging      - Run tests against staging environment"
	@echo "  make test-smoke        - Quick smoke test"
	@echo "  make clean             - Clean test artifacts"
	@echo "  make install-test      - Install test dependencies"
	@echo "  make test-one FILE=... - Run a specific test"
