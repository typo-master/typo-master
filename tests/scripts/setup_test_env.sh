#!/bin/bash
# Test environment setup script

set -e

echo "Setting up test environment..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Install dependencies if needed
if ! python3 -c "import pytest" 2>/dev/null; then
    echo "Installing pytest..."
    pip install pytest pytest-asyncio pytest-cov pytest-mock
fi

# Create reports directory
mkdir -p tests/reports/htmlcov
mkdir -p tests/reports/xml

echo "Test environment setup complete!"
echo ""
echo "Run tests with:"
echo "  python run_tests.py unit"
echo "  python run_tests.py regression"
echo "  python run_tests.py security"
echo "  python run_tests.py all"
