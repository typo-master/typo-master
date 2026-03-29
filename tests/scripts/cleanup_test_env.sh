#!/bin/bash
# Test environment cleanup script

set -e

echo "Cleaning up test environment..."

# Remove test artifacts
rm -rf tests/reports/
rm -rf .pytest_cache/
rm -rf __pycache__/

# Clean up Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

echo "Test environment cleanup complete!"
