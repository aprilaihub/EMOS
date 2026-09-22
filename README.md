# EMOS - Electronic Materials Ontology System

🌐 **Live Site**: https://aprilaihub.github.io/EMOS

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="frontend/images/logo_name_dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="frontend/images/logo_name.svg">
  <img src="frontend/images/logo_name.svg" width="600" height="200" alt="EMOS - Electronic Materials Ontology System">
</picture>

## PROJECT OVERVIEW

EMOS is an open-source platform for electronics materials science research. Access integrated databases, AI-powered analysis, and computational tools for materials exploration and electronic device design.

## QUICK START

### Prerequisites
- Python 3.10-3.12 (Python 3.11 recommended)
- Docker + Docker Compose plugin (for container-backed model services)
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Installation

```bash
git clone https://github.com/aprilaihub/EMOS.git
cd EMOS
bash setup/setup.sh          # macOS/Linux
# or
setup\setup.bat              # Windows
```

Then activate the virtual environment:
- macOS/Linux: `source emos_env/bin/activate`
- Windows: `emos_env\Scripts\activate.bat`

The setup script automatically installs all libraries from `requirements.txt`. See [setup/README.md](setup/README.md) for more details or manual setup instructions.

### Run Locally (Baseline Reproducible Path)

1) Start container services (build images first):

```bash
docker compose up -d --build
```

2) Start backend:

```bash
python backend/app.py
# Runs on http://localhost:5001
```

3) Build and open the local frontend preview:

```bash
rm -rf _site
mkdir _site
cp -r frontend/. _site/
cp -r Features Information_Units backend devtools docs _site/
python -m http.server 8000 --directory _site
```

Then open http://localhost:8000 in your browser. This assembles the same flat
site layout used by the GitHub Pages deployment.

### Standard Local Commands

```bash
bash setup/setup.sh
source emos_env/bin/activate
docker compose up -d --build
python backend/app.py
pytest tests/unit/test_backend_readiness_and_lambda.py tests/unit/test_node_editor_sse_parser.py -q
pytest -m "network" -q
python -m http.server 8000 --directory _site
```

> **Note**: Backend default local port is `5001`.

### Quick Troubleshooting

- Re-run setup with `bash setup/setup.sh` and re-activate `source emos_env/bin/activate`.
- If port `5001` is busy, run backend with `PORT=5002 python backend/app.py`.
- If containers are stale, run `docker compose down` then `docker compose up -d --build`.

## PROJECT STRUCTURE

```
EMOS/
├── frontend/                     # Static web application
│   ├── index.html                # Main application interface
│   ├── script.js                 # JavaScript functionality & feature loading
│   ├── styles.css                # Application styling
│   └── images/                   # Frontend graphics and logos
├── requirements.txt              # Python dependencies
│
├── Features/                     # Feature implementations
│   ├── Materials_Exploration/   # Materials science features
│   ├── Electronics_Application/ # Electronics application tools
│   └── FeatureFactory.py        # Feature loader and manager
│
├── Information_Units/           # Data sources & computational tools
│   ├── Databases/               # Material property databases
│   ├── Generators/              # Material generation tools
│   └── Predictors/              # Property prediction models
│
├── backend/                     # Flask backend server
│   └── app.py                   # Flask API routes
│
├── docs/                        # Markdown documentation
│   ├── index.md                 # Documentation introduction
│   ├── information-units/       # IU pages
│   ├── features/                # Feature pages
│   └── tutorials/               # Contribution tutorials
│
├── devtools/                    # Development tools
│   └── source_data.json             # Component definitions
│
```

## TECHNOLOGY STACK

- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Backend**: Python, Flask
- **Architecture**: Modular component-based structure
- **Documentation**: Markdown files shown in `frontend/documentation.html`
- **UI/UX**: Responsive design with glassmorphism effects

## NEXT STEPS

- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add features and information units
- **Documentation**: Open [frontend/documentation.html](frontend/documentation.html) or read the [Markdown documentation](docs/index.md)
- **GitHub**: https://github.com/aprilaihub/EMOS

## LICENSE

Licensed under the Apache License 2.0 - see [LICENSE](LICENSE) for details.
