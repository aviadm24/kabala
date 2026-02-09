#!/bin/bash
# Quick setup script for test suite
# Usage: bash setup_tests.sh

set -e

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_BIN="$PROJECT_DIR/venv/bin"

echo "🧪 Test Suite Setup"
echo "===================="
echo ""

# Check if venv exists
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "❌ Virtual environment not found at $PROJECT_DIR/venv"
    echo "Please create it first with: python3 -m venv venv"
    exit 1
fi

echo "✅ Virtual environment found"
echo "📦 Installing test dependencies..."

# Install test dependencies
"$VENV_BIN/python" -m pip install --quiet -q pytest>=7.0 pytest-cov>=4.0 pytest-timeout>=2.1 pytest-asyncio>=0.20 httpx>=0.24 sqlalchemy>=2.0 pytest-mock>=3.10

echo "✅ Dependencies installed"
echo ""
echo "🚀 Ready to run tests!"
echo ""
echo "Quick commands:"
echo "  $VENV_BIN/python -m pytest tests                    # Run all tests"
echo "  $VENV_BIN/python -m pytest tests -m unit           # Unit tests only"
echo "  $VENV_BIN/python -m pytest tests -m integration    # Integration tests"
echo "  $VENV_BIN/python -m pytest tests -m regression     # Regression tests"
echo "  $VENV_BIN/python -m pytest tests -v                # Verbose output"
echo "  $VENV_BIN/python -m pytest tests --cov             # With coverage"
echo ""
echo "Or use the test runner:"
echo "  $VENV_BIN/python run_tests.py"
echo "  $VENV_BIN/python run_tests.py --unit"
echo "  $VENV_BIN/python run_tests.py --coverage"
