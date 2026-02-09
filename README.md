# EMOS - Electronics Materials Operating System

🌐 **Live Site**: https://aprilaihub.github.io/EMOS

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="images/logo_name_dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="images/logo_name.svg">
  <img src="images/logo_name.svg" width="600" height="200" alt="EMOS - Electronics Materials Operating System">
</picture>

A modern open-source and community-based web-based platform for electronics materials science research and analysis, featuring an intuitive interface for materials exploration, AI-powered analysis, and integrated computational tools for electronic device design pipelines.


## 🛠️ Technology Stack

- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Architecture**: Modular component-based structure with dynamic feature loading
- **UI/UX**: Modern responsive design with glassmorphism effects
- **Icons**: SVG graphics for scalable interface elements
- **Feature System**: BaseFeature class with inheritance for specialized implementations

## 📁 Project Structure

```
EMOS/
├── index.html                    # Main application interface
├── script.js                     # Core JavaScript functionality & dynamic loading
├── styles.css                    # Application styling
├── requirements.txt              # Python dependencies
│
├── Features/                     # Feature implementations (extend BaseFeature)
│   ├── BaseFeature.py           # Base class for Python features
│   ├── BaseFeature.js           # Base class for JS features
│   ├── FeatureFactory.py        # Feature loader and manager
│   ├── Materials_Exploration/   # Materials science features
│   │   ├── MaterialSearch/
│   │   ├── DftCalculation/
│   │   └── ...
│   └── Electronics_Application/ # Electronics-focused features
│       ├── PropertyPrediction/
│       ├── BandStructure/
│       └── ...
│
├── Information_Units/           # Data sources & computational tools
│   ├── Databases/               # Material property databases
│   │   ├── BaseDatabase.py
│   │   ├── DatabaseFactory.py
│   │   ├── Materialsproject/
│   │   ├── Jarvis/
│   │   └── ...
│   ├── Generators/              # Material generation tools
│   │   ├── BaseGenerator.py
│   │   ├── GeneratorFactory.py
│   │   ├── Imatgen/
│   │   ├── Matgan/
│   │   └── ...
│   └── Predictors/              # Property prediction models
│       ├── BasePredictor.py
│       ├── PredictorFactory.py
│       ├── M3gnet/
│       ├── Deepmd/
│       └── ...
│
├── backend/                     # Flask backend server
│   └── app.py                   # Flask application & API routes
│
├── docs/                        # Documentation (Sphinx)
│   ├── conf.py
│   ├── index.rst
│   └── _build/                  # Generated HTML documentation
│
├── devtools/                   # Development tools & contribution utilities
│   ├── core_metadata.json
│   └── core_utilities.py
│
└── images/                      # Graphics, logos, team photos
```

## 🎯 Getting Started

### Prerequisites
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Local web server (optional, for development)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/EMOS.git
   cd EMOS
   ```

2. **Install Python dependencies** (for backend features)
   ```bash
   python -m pip install -r requirements.txt
   ```

## 🏃‍♂️ Running the Application

EMOS consists of two components that work together:

### Frontend (Website)

The frontend can be run in several ways:

#### Option 1: Direct File Access
- Simply open `index.html` directly in your web browser
- Navigate to: `file:///path/to/EMOS/index.html`

#### Option 2: Local Development Server (Recommended)
Using a local server prevents CORS issues and provides better development experience:

```bash
# Using Python 3
python -m http.server 8000

# Using Python 2 (if Python 3 not available)
python -m SimpleHTTPServer 8000

# Using Node.js (if you have it installed)
npx serve .

# Using PHP (if you have it installed)
php -S localhost:8000
```

Then access the application at: `http://localhost:8000`

### Backend (Flask Server)

For full functionality including advanced calculations and processing, you need to run the Flask backend:

1. **Navigate to the backend directory**
   ```bash
   cd backend
   ```

2. **Run the Flask server**
   ```bash
   python app.py
   ```
   
   Or with explicit Flask command:
   ```bash
   flask run
   ```

3. **Verify server is running**
   The Flask server will start on `http://localhost:5000` by default.
   You should see output similar to:
   ```
   * Running on http://127.0.0.1:5000
   * Debug mode: on
   ```

### Complete Setup (Frontend + Backend)

For the full EMOS experience with all features enabled:

1. **Terminal 1 - Start Flask Backend**
   ```bash
   cd EMOS/backend
   python app.py
   ```

2. **Terminal 2 - Start Frontend Server**
   ```bash
   cd EMOS
   python -m http.server 8000
   ```

3. **Access the application**
   - Frontend: `http://localhost:8000`
   - Backend API: `http://localhost:5000`

### Troubleshooting

- **CORS Issues**: Use a local server instead of opening the HTML file directly
- **Flask Import Errors**: Ensure all Python dependencies are installed: `pip install flask flask-cors`
- **Port Conflicts**: If ports 8000 or 5000 are in use, specify different ports:
  ```bash
  python -m http.server 3000  # Frontend on port 3000
  flask run --port 5001       # Backend on port 5001
  ```

3. **Access the application**
   - Frontend: `http://localhost:8000` (or your chosen port)
   - Backend API: `http://localhost:5000` (or your chosen port)

## 🖥️ Usage

### Main Interface

The EMOS interface is divided into two main panels:

#### Left Panel - Controls
- **Information Units**: Configure databases, generators, and predictors
- **Features**: Access materials exploration and electronics application tools
- **LLM**: Interact with the AI assistant

#### Right Panel - Operating Area
- **Welcome Screen**: Starting point with navigation guidance
- **Feature Processing**: Input parameters, processing controls, and results display
- **Chat Interface**: AI assistant interaction area

### Workflow

1. **Select Information Units**: Choose relevant databases and computational tools
2. **Choose Feature**: Click on any feature button to access specific functionality
3. **Configure Inputs**: Set parameters for your analysis or calculation
4. **Process**: Execute the selected feature with your parameters
5. **Review Results**: Analyze outputs and export data as needed

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**EMOS** - Advancing electronics materials science through intelligent software solutions.
