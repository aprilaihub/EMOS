# Documentation Framework

EMOS uses [Sphinx](https://www.sphinx-doc.org/) with the Read the Docs theme to generate comprehensive documentation from reStructuredText and Markdown files.

## Quick Overview

- **Framework**: Sphinx
- **Theme**: Read the Docs (sphinx_rtd_theme)
- **Format Support**: Markdown (via MyST Parser) and reStructuredText
- **Output**: HTML documentation (generated in `_build/html/`)

## Project Structure

```
docs/
├── conf.py                      # Sphinx configuration
├── index.rst                    # Main documentation index
├── introduction.md              # Getting started
├── overview.md                  # Platform overview
├── quickstart.md                # Quick start guide
├── information_units/           # Information units documentation
├── features/                    # Features documentation
├── user_guide/                  # User tutorials and examples
├── reference/                   # API reference and troubleshooting
└── _build/                      # Generated HTML documentation
    └── html/                    # Output folder (do not commit)
```

## Building Documentation

### Prerequisites
- Python 3.8+
- Sphinx: `pip install sphinx sphinx-rtd-theme myst-parser`

### Build Command

```bash
cd docs
sphinx-build -b html . _build/html
```

This generates HTML documentation in `docs/_build/html/`. Open `index.html` in your browser to view.

### Clean Build

To rebuild from scratch (removes old build):

```bash
cd docs
rm -rf _build
sphinx-build -b html . _build/html
```

## Writing Documentation

### File Formats

**Markdown files** (.md):
- Use for content-heavy sections (getting started, guides)
- Easier to read and write
- Example: `introduction.md`, `quickstart.md`

**reStructuredText files** (.rst):
- Use for index and structured references
- Better for cross-referencing
- Example: `index.rst`, `conf.py`

### Adding New Pages

1. Create a `.md` or `.rst` file in the appropriate folder
2. Add a reference to it in `index.rst` within the `toctree` directive:

```rst
.. toctree::
   :maxdepth: 2
   
   your_new_page
```

3. Rebuild documentation

## Documentation Organization

The documentation is organized into these main sections:

- **Getting Started**: Introduction, overview, quick start
- **Information Units**: Databases, generators, predictors
- **Features**: Materials exploration, electronics applications
- **User Guide**: Tutorials, examples, best practices
- **Reference**: API documentation, troubleshooting

## Automatic Deployment

Documentation is automatically built and deployed to GitHub Pages when you push to the `master` branch. See the GitHub Actions workflow (`.github/workflows/deploy-site.yml`) for details.

## Common Tasks

### View Documentation Locally

```bash
cd /home/soe/EMOS
python -m http.server 8000
# Visit http://localhost:8000/docs/_build/html/
```

### Check for Sphinx Warnings

```bash
cd docs
sphinx-build -W -b html . _build/html
# -W treats warnings as errors (useful for CI/CD)
```

### Update Theme Settings

Edit `conf.py` to customize theme, extensions, or output format. Common settings:
- `html_theme`: Current theme (sphinx_rtd_theme)
- `extensions`: Add parsing/formatting extensions
- `html_theme_options`: Customize appearance

## Useful Resources

- [Sphinx Documentation](https://www.sphinx-doc.org/en/master/)
- [MyST Parser Guide](https://myst-parser.readthedocs.io/)
- [Read the Docs Theme](https://sphinx-rtd-theme.readthedocs.io/)
