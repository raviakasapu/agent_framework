# Building Sphinx Documentation

## Quick Start

```bash
# From sdk/docs/sphinx directory
make html

# View the docs
open build/html/index.html
```

## Requirements

The Sphinx documentation requires the following packages (already in `sdk/requirements.txt`):

- sphinx
- sphinx-rtd-theme (Read the Docs theme)
- myst-parser (for Markdown support)

## Build Commands

### HTML (Recommended)
```bash
make html
```

### Clean Build
```bash
make clean
make html
```

### Other Formats
```bash
make latexpdf  # PDF via LaTeX
make epub      # EPUB ebook
make man       # Man pages
```

## Serving Locally

### Option 1: Simple HTTP Server
```bash
cd build/html
python -m http.server 8000
# Visit http://localhost:8000
```

### Option 2: Via docs_server
```bash
# From sdk/ directory
AGENT_DOCS_DIR=docs/sphinx/build/html uvicorn docs_server.main:app --reload --port 8000
# Visit http://localhost:8000/reference
```

## Documentation Structure

```
docs/sphinx/
├── source/              # Source files
│   ├── index.rst       # Main index
│   ├── conf.py         # Sphinx configuration
│   ├── guides/         # User guides
│   ├── tutorials/      # Step-by-step tutorials
│   ├── api/            # API reference (auto-generated)
│   └── powerbi/        # Domain-specific docs
│
├── build/              # Generated output
│   └── html/           # HTML documentation
│
├── Makefile            # Build automation (Unix)
└── make.bat            # Build automation (Windows)
```

## Updating Documentation

### Add a New Guide

1. Create `.rst` file in `source/guides/`
2. Add to `source/guides/index.rst` toctree
3. Rebuild: `make html`

### Add API Documentation

API docs are auto-generated from Python docstrings using `automodule`.

To document a new module:

1. Edit `source/api/index.rst`
2. Add:
   ```rst
   .. automodule:: your.module.path
      :members:
      :undoc-members:
      :show-inheritance:
   ```
3. Rebuild: `make html`

### Update Existing Content

1. Edit the `.rst` or `.md` file
2. Rebuild: `make html`
3. Refresh browser

## Troubleshooting

### "No module named 'framework'"

Ensure you're in the `sdk/` directory when building, or add to `sys.path` in `conf.py`.

### Build Warnings

Common warnings and fixes:

**"document isn't included in any toctree"**
- Add the document to a toctree in index.rst or parent file

**"undefined label"**
- Check cross-reference syntax: `:doc:`path/to/file``

**"Duplicate explicit target name"**
- Ensure section titles are unique within a file

### Clean Build

If you see stale content:

```bash
make clean
make html
```

## Customization

### Theme

Edit `source/conf.py`:

```python
html_theme = 'sphinx_rtd_theme'  # Read the Docs theme
# or
html_theme = 'alabaster'  # Default theme
```

### Logo and Favicon

```python
html_logo = '_static/logo.png'
html_favicon = '_static/favicon.ico'
```

### Syntax Highlighting

```python
pygments_style = 'sphinx'  # Code highlighting style
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Build Docs

on: [push]

jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: cd docs/sphinx && make html
      - uses: actions/upload-artifact@v2
        with:
          name: documentation
          path: docs/sphinx/build/html
```

## Publishing

### GitHub Pages

```bash
# Build docs
make html

# Copy to gh-pages branch
cp -r build/html/* /path/to/gh-pages/

# Commit and push
cd /path/to/gh-pages/
git add .
git commit -m "Update documentation"
git push origin gh-pages
```

### Read the Docs

1. Connect your repository to readthedocs.org
2. Configure build settings
3. Docs auto-build on push

## See Also

- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [reStructuredText Primer](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html)
- [MyST Parser](https://myst-parser.readthedocs.io/) (Markdown support)

