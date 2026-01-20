# EMOS - Electronics Materials Operating System

🌐 **Live Site**: https://aprilaihub.github.io/EMOS

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="images/logo_name_dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="images/logo_name.svg">
  <img src="images/logo_name.svg" width="600" height="200" alt="EMOS - Electronics Materials Operating System">
</picture>

A modern open-source and community-based web-based platform for electronics materials science research and analysis, featuring an intuitive interface for materials exploration, AI-powered analysis, and integrated computational tools for electronic device design pipelines.

## 🚀 Features

### Materials Exploration
- **Material Search**: Search and explore materials from comprehensive databases using various criteria
- **Material Generation**: Generate new material compositions using AI-powered algorithms and predictive models
- **Database Extractor**: Extract and analyze specific material properties and data from integrated databases
- **Material Characterization**: Advanced materials analysis and characterization tools for comprehensive evaluation
- **DFT Calculation**: Density Functional Theory calculations for electronic structure analysis
- **Crystallographic Analysis**: Crystal structure analysis and symmetry determination tools
- **Quantum Mechanics**: Quantum mechanical calculations for electronic and optical properties
- **Tensor Analysis**: Tensor calculus and analysis for material property tensors

### Electronics Applications
- **Device Synthesizability**: Evaluate feasibility and methods for synthesizing electronic devices from selected materials
- **Interface Calculation**: Calculate and analyze interfaces between different materials in electronic applications
- **Property Prediction**: Electronic property prediction and optimization for semiconductor applications
- **Band Structure**: Band structure calculations and electronic transport property analysis
- **Thermal Management**: Thermal management analysis for electronic device performance optimization
- **Reliability Assessment**: Reliability assessment and failure analysis for electronic materials
- **Process Integration**: Process integration workflows for electronic device manufacturing
- **Advanced Characterization**: Advanced characterization techniques for electronic materials evaluation

### AI Assistant
- **LLM Integration**: Built-in AI assistant for materials science queries
- **Interactive Chat**: Real-time assistance with materials research
- **Knowledge Base**: Access to comprehensive materials science information

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
├── README.md                     # Project documentation
├── images/                       # Graphics and logos
└── Features/                     # Modular feature implementations
    ├── BaseFeature.js           # Foundation class for all features
    ├── Materials_Exploration/    # 8 materials science features
    └── Electronics_Application/  # 8 electronics-focused features
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
   pip install flask flask-cors numpy scipy matplotlib pandas
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

### AI Assistant

- Click "LLM for EMOS" to open the chat interface
- Ask questions about materials science, properties, or applications
- Get contextual help and guidance for using EMOS features

## 🎨 Interface Features

- **Responsive Design**: Adapts to different screen sizes
- **Modern Aesthetics**: Glassmorphism effects and smooth animations
- **Interactive Elements**: Hover effects and visual feedback
- **Progress Tracking**: Real-time processing status indicators
- **Modal Views**: Focused interfaces for specific tasks

## 🔧 Development

### Architecture Overview

EMOS uses a modular architecture with dynamic feature loading:

- **BaseFeature Class**: Foundation class providing common functionality for all features
- **Feature Inheritance**: Each feature extends BaseFeature with specialized implementations
- **Dynamic Loading**: Features are loaded on-demand using ES6 modules
- **Consistent Interface**: All features provide standardized input/output interfaces

### Feature Development

Each feature is a self-contained module with:

```javascript
class YourFeature extends BaseFeature {
    constructor() {
        super(id, 'Feature Name', 'Description');
    }
    
    createInputsHTML() {
        // Custom input interface
    }
    
    createOutputsHTML() {
        // Custom output interface  
    }
    
    async processFeature() {
        // Feature-specific logic
    }
    
    updateOutputs(results) {
        // Update UI with results
    }
}
```

### File Organization
- `index.html`: Main HTML structure with dynamic content areas
- `script.js`: Application logic, feature loading, and AI responses
- `styles.css`: Complete styling including responsive design and animations
- `Features/BaseFeature.js`: Base class with common utilities
- `Features/*/`: Individual feature implementations

### Key JavaScript Functions
- `loadFeatureModule()`: Dynamically loads and initializes features
- `showFeatureView()`: Displays feature-specific interface
- `showLLMView()`: Opens AI assistant chat
- `createGenericFeatureView()`: Fallback UI for error handling

### Styling Architecture
- CSS Grid and Flexbox for layout
- CSS custom properties for theming
- Modular component styles
- Responsive breakpoints

## 🤝 Contributing

We welcome contributions to EMOS! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**: Implement your feature or fix
4. **Commit changes**: `git commit -m 'Add amazing feature'`
5. **Push to branch**: `git push origin feature/amazing-feature`
6. **Open a Pull Request**: Describe your changes and their benefits

### Development Guidelines
- Follow existing code style and structure
- Extend BaseFeature class for new features
- Use descriptive names (max 3 words) for features
- Implement error handling and fallback mechanisms
- Test functionality across different browsers
- Ensure responsive design compatibility
- Document new features or changes

### Adding New Features

1. **Create Feature Directory**: `Features/Category/Feature_Name/`
2. **Implement Feature Class**: Extend BaseFeature with custom methods
3. **Update Mappings**: Add to `featureClasses` and `featureFiles` in script.js
4. **Add UI Button**: Include in index.html with proper data attributes
5. **Test Integration**: Verify loading and functionality

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**EMOS** - Advancing electronics materials science through intelligent software solutions.
