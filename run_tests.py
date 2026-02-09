#!/usr/bin/env python
"""
Test runner script with easy configuration.
Supports running different test suites locally and on remote servers.

Usage:
    python run_tests.py                          # Run all tests locally
    python run_tests.py --unit                   # Run only unit tests
    python run_tests.py --integration            # Run only integration tests
    python run_tests.py --regression             # Run only regression tests
    python run_tests.py --production             # Run tests against production
    python run_tests.py --slow                   # Include slow tests
    python run_tests.py --ocr                    # Include OCR tests
    python run_tests.py --local --unit --verbose # Run unit tests locally with verbose output
    python run_tests.py --staging --regression   # Run regression tests against staging
"""

import sys
import subprocess
import argparse
from pathlib import Path
from typing import List
import os

# Get project root
PROJECT_ROOT = Path(__file__).parent


class TestRunner:
    """Manages test execution with flexible configuration."""
    
    def __init__(self):
        self.pytest_args: List[str] = []
        self.markers: List[str] = []
        self.environment = "local"
        self.extra_args: List[str] = []
    
    def add_environment(self, env: str) -> None:
        """Set test environment (local, staging, production)."""
        valid_envs = ["local", "staging", "production"]
        if env not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        
        self.environment = env
        os.environ["TEST_ENV"] = env
    
    def add_test_type(self, test_type: str) -> None:
        """Add test type marker."""
        if test_type not in ["unit", "integration", "regression"]:
            raise ValueError("Test type must be unit, integration, or regression")
        self.markers.append(test_type)
    
    def add_optional_tests(self, test_type: str) -> None:
        """Add optional test types."""
        if test_type not in ["slow", "ocr", "cloudinary"]:
            raise ValueError("Optional test must be slow, ocr, or cloudinary")
        
        if test_type == "slow":
            os.environ["TEST_RUN_SLOW"] = "true"
        elif test_type == "ocr":
            os.environ["TEST_RUN_OCR"] = "true"
        elif test_type == "cloudinary":
            os.environ["TEST_USE_CLOUDINARY"] = "true"
    
    def add_verbose(self) -> None:
        """Add verbose output."""
        self.pytest_args.append("-vv")
    
    def add_coverage(self) -> None:
        """Add coverage reporting."""
        self.pytest_args.extend([
            "--cov=.",
            "--cov-report=html",
            "--cov-report=term-missing"
        ])
    
    def add_markers(self) -> None:
        """Add marker filters."""
        if self.markers:
            marker_expr = " or ".join(self.markers)
            self.pytest_args.extend(["-m", marker_expr])
    
    def add_extra_args(self, *args: str) -> None:
        """Add extra pytest arguments."""
        self.extra_args.extend(args)
    
    def build_command(self) -> List[str]:
        """Build the pytest command."""
        # Try to use venv python if available
        venv_python = PROJECT_ROOT / "venv" / "bin" / "python"
        if venv_python.exists():
            cmd = [str(venv_python), "-m", "pytest"]
        else:
            cmd = ["python", "-m", "pytest"]
        
        # Add test directory
        cmd.append("tests")
        
        # Add markers
        self.add_markers()
        
        # Add pytest args
        cmd.extend(self.pytest_args)
        
        # Add extra args
        cmd.extend(self.extra_args)
        
        return cmd
    
    def run(self) -> int:
        """Run pytest and return exit code."""
        cmd = self.build_command()
        
        print(f"🧪 Running tests in {self.environment} environment")
        print(f"📍 Test types: {', '.join(self.markers) if self.markers else 'all'}")
        print(f"🔧 Command: {' '.join(cmd)}\n")
        
        # Change to project root
        os.chdir(PROJECT_ROOT)
        
        # Run pytest
        result = subprocess.run(cmd)
        return result.returncode


def main():
    """Parse arguments and run tests."""
    parser = argparse.ArgumentParser(
        description="Dynamic test runner for Receipt Uploader application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Environment
    env_group = parser.add_argument_group("Environment")
    env_group.add_argument(
        "--local",
        action="store_const",
        const="local",
        dest="environment",
        default="local",
        help="Run tests locally (default)"
    )
    env_group.add_argument(
        "--staging",
        action="store_const",
        const="staging",
        dest="environment",
        help="Run tests against staging environment"
    )
    env_group.add_argument(
        "--production",
        action="store_const",
        const="production",
        dest="environment",
        help="Run tests against production environment"
    )
    
    # Test types
    test_group = parser.add_argument_group("Test Types")
    test_group.add_argument(
        "--unit",
        action="append_const",
        const="unit",
        dest="test_types",
        help="Run only unit tests"
    )
    test_group.add_argument(
        "--integration",
        action="append_const",
        const="integration",
        dest="test_types",
        help="Run only integration tests"
    )
    test_group.add_argument(
        "--regression",
        action="append_const",
        const="regression",
        dest="test_types",
        help="Run only regression tests"
    )
    
    # Optional tests
    opt_group = parser.add_argument_group("Optional Tests")
    opt_group.add_argument(
        "--slow",
        action="store_true",
        help="Include slow tests"
    )
    opt_group.add_argument(
        "--ocr",
        action="store_true",
        help="Include OCR tests"
    )
    opt_group.add_argument(
        "--cloudinary",
        action="store_true",
        help="Include Cloudinary tests"
    )
    
    # Output options
    out_group = parser.add_argument_group("Output Options")
    out_group.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    out_group.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    # Extra pytest arguments
    parser.add_argument(
        "pytest_args",
        nargs="*",
        help="Extra arguments to pass to pytest"
    )
    
    args = parser.parse_args()
    
    # Create runner
    runner = TestRunner()
    
    try:
        # Set environment
        runner.add_environment(args.environment)
        
        # Add test types
        if args.test_types:
            for test_type in args.test_types:
                runner.add_test_type(test_type)
        
        # Add optional tests
        if args.slow:
            runner.add_optional_tests("slow")
        if args.ocr:
            runner.add_optional_tests("ocr")
        if args.cloudinary:
            runner.add_optional_tests("cloudinary")
        
        # Add output options
        if args.verbose:
            runner.add_verbose()
        if args.coverage:
            runner.add_coverage()
        
        # Add extra arguments
        if args.pytest_args:
            runner.add_extra_args(*args.pytest_args)
        
        # Run tests
        exit_code = runner.run()
        
        print("\n" + "=" * 70)
        if exit_code == 0:
            print("✅ All tests passed!")
        else:
            print(f"❌ Tests failed with exit code {exit_code}")
        print("=" * 70)
        
        return exit_code
    
    except ValueError as e:
        parser.error(str(e))


if __name__ == "__main__":
    sys.exit(main())
