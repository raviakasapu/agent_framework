#!/bin/bash
# Script to build and publish the agentic-framework package to PyPI

set -e

echo "=== Building agentic-framework package ==="

# Clean previous builds
rm -rf dist/ build/ *.egg-info src/*.egg-info

# Install build tools if needed
pip install --upgrade build twine

# Build the package
python -m build --sdist --wheel

echo ""
echo "=== Build complete ==="
echo "Packages created in dist/:"
ls -la dist/

echo ""
echo "=== To publish to PyPI ==="
echo ""
echo "1. Test on TestPyPI first (recommended):"
echo "   twine upload --repository testpypi dist/*"
echo ""
echo "2. Then publish to PyPI:"
echo "   twine upload dist/*"
echo ""
echo "Note: You'll need a PyPI account and API token."
echo "Set up ~/.pypirc or use: twine upload --username __token__ --password <your-token> dist/*"

