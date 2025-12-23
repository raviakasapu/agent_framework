#!/bin/bash
# Restructure repo for GitHub distribution
# Run from: ai_agent_framework_repo/

set -e

echo "🔄 Restructuring repository for GitHub distribution..."

# 1. Move package files to root
echo "📦 Moving package source to root..."
cp -r agent-framework-pypi/src .
cp agent-framework-pypi/pyproject.toml .
cp agent-framework-pypi/LICENSE .

# Backup existing README, then copy package README
[ -f README.md ] && mv README.md README_old.md
cp agent-framework-pypi/README.md .

# 2. Reorganize docs
echo "📚 Reorganizing documentation..."
mkdir -p docs_source
mv docs/sphinx/source docs_source/
mv docs/sphinx/Makefile docs_source/

# 3. Build docs to /docs for GitHub Pages
echo "🏗️  Building documentation..."
if command -v sphinx-build &> /dev/null; then
    cd docs_source
    sphinx-build -b html source ../docs 2>/dev/null || echo "⚠️  Sphinx build had warnings (check output)"
    cd ..
else
    echo "⚠️  sphinx-build not found. Install with: pip install sphinx sphinx-rtd-theme myst-parser"
    echo "   Then run: cd docs_source && sphinx-build -b html source ../docs"
fi

# 4. Create .nojekyll for GitHub Pages
touch docs/.nojekyll

# 5. Clean up old directories (optional - comment out to keep)
echo "🧹 Cleaning up..."
# rm -rf agent-framework-pypi/  # Uncomment to remove old dir
# rm -rf docs/sphinx/           # Uncomment to remove old sphinx dir

echo ""
echo "✅ Restructuring complete!"
echo ""
echo "New structure:"
echo "  src/agent_framework/    - Package source"
echo "  docs/                   - Built HTML (GitHub Pages)"
echo "  docs_source/source/     - Sphinx source files"
echo "  .github/workflows/      - CI/CD workflows"
echo ""
echo "Next steps:"
echo "  1. Review changes: git status"
echo "  2. Commit: git add . && git commit -m 'Restructure for GitHub distribution'"
echo "  3. Push to GitHub: git push origin main"
echo "  4. Enable GitHub Pages: Settings → Pages → Branch: main, Folder: /docs"
echo ""
echo "Install package with:"
echo "  pip install git+https://github.com/raviakasapu/agent_framework.git"

