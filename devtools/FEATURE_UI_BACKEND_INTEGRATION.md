# Feature UI & Backend Integration Guide

## Overview
This document explains how feature contributions are seamlessly integrated across the entire EMOS stack: metadata → templates → factory → UI → backend.

---

## Complete Integration Flow

```
metadata.json
    ↓
contribution_tool.py
    ↓
├─ Feature Templates (Python + JS)
├─ FeatureFactory.py
├─ index.html (UI Buttons)
├─ script.js (JS Mappings)
    ↓
Backend (app.py)
    ↓
User Interface (Live)
```

---

## 1. Feature Addition Workflow

### Step 1: Update metadata.json
Add new feature entry to the appropriate category:

```json
{
  "features": {
    "materials_exploration": [
      {
        "id": 17,
        "name": "New Feature",
        "display_name": "New Feature",
        "description": "Feature description",
        "folder_path": "Features/Materials_Exploration/NewFeature",
        "class_name": "NewFeatureFeature",
        "file_name": "NewFeatureFeature.py",
        "js_file_name": "NewFeature.js",
        "inputs": [...],
        "outputs": [...]
      }
    ]
  }
}
```

### Step 2: Run Contribution Tool
```bash
python devtools/contribution_tool.py
```

### Step 3: Tool Actions (Automatic)

**A. Creates Feature Templates:**
```
Features/Materials_Exploration/NewFeature/
├── README.md                    # Documentation with inputs/outputs
├── __init__.py                  # Python init file
├── NewFeatureFeature.py        # Backend class (extends BaseFeature)
└── NewFeature.js               # Frontend class (extends BaseFeature)
```

**B. Updates FeatureFactory.py:**
```python
# Adds import
from Features.Materials_Exploration.NewFeature.NewFeatureFeature import NewFeatureFeature

# Adds factory entry
feature_factory = {
    "17": NewFeatureFeature,
    # ... existing features
}
```

**C. Updates index.html (UI Buttons):**
```html
<!-- Materials Exploration Subsection -->
<div class="feature-grid">
    <!-- Existing buttons ... -->
    <button class="feature-btn" 
            data-feature="17" 
            data-feature-name="New Feature" 
            data-feature-desc="Feature description">
        New Feature
    </button>
</div>
```

**D. Updates script.js (Mappings):**
```javascript
// Feature class mapping
const featureClasses = {
    17: 'NewFeatureFeature',
    // ... existing mappings
};

// Feature file paths
const featureFiles = {
    17: './Features/Materials_Exploration/NewFeature/NewFeature.js',
    // ... existing mappings
};
```

---

## 2. Backend Integration

### Feature Python Template (Auto-generated)

```python
from Features.BaseFeature import BaseFeature
from Information_Units.Generators.GeneratorFactory import generator_factory
from Information_Units.Databases.DatabaseFactory import database_factory
from Information_Units.Predictors.PredictorFactory import predictor_factory


class NewFeatureFeature(BaseFeature):
    def __init__(self, logger=None):
        super().__init__("New Feature", logger)
    
    def info(self):
        return "New Feature: Feature description"
    
    def extract_inputs(self, input_data):
        """Extract inputs from frontend request"""
        return {
            'input1': input_data.get('input1', ''),
            'input2': input_data.get('input2', ''),
            # ... from metadata inputs
        }
    
    def process_feature(self, inputs):
        """Core processing logic"""
        if self.logger:
            self.logger.log('Initializing New Feature...', 'info')
        
        # Process information units
        self._process_information_units(inputs)
        
        if self.logger:
            self.logger.log('New Feature processing completed', 'info')
        
        return {
            'status': 'completed',
            'message': 'New Feature executed successfully'
        }
    
    def format_outputs(self, results):
        """Format results for frontend"""
        return {
            'output1': 'placeholder text value',
            'output2': 'placeholder text value',
            # ... from metadata outputs
        }
    
    def _process_information_units(self, inputs):
        """Integrate with databases, generators, predictors"""
        # Full implementation with logging & error handling
        # ... (auto-generated from template)
```

### Backend Endpoint (Existing in app.py)

```python
@app.route('/api/process/<int:feature_id>', methods=['POST'])
def process_feature(feature_id):
    """Process feature request - works with all features automatically"""
    try:
        data = request.json
        logger.clear_logs()
        
        # Create feature instance from factory
        feature = create_feature(str(feature_id), logger)
        
        # Execute feature workflow
        outputs = feature.process(data)
        
        return jsonify({
            'success': True,
            'outputs': outputs,
            'logs': logger.get_logs()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'logs': logger.get_logs()
        }), 500
```

**Key Points:**
- ✅ No backend code changes needed for new features
- ✅ Factory pattern automatically routes requests
- ✅ Logging integrated automatically
- ✅ Error handling unified

---

## 3. Frontend Integration

### Feature JavaScript Template (Auto-generated)

```javascript
// New Feature Feature
class NewFeatureFeature extends BaseFeature {
    constructor() {
        super(1, 'New Feature', 'Feature description');
    }

    createInputsHTML() {
        return `
            <p>Configure input parameters for New Feature</p>
            <div class="input-controls">
                ${this.createTextInput(`input1_${this.featureId}`, 'Input 1', 'Enter value')}
                ${this.createTextInput(`input2_${this.featureId}`, 'Input 2', 'Enter value')}
                <!-- ... from metadata inputs -->
            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <p>New Feature results and outputs</p>
            <div class="output-display" id="outputDisplay_${this.featureId}">
                <div class="output-item">
                    <strong>Output 1:</strong> <span id="output1_${this.featureId}">Pending...</span>
                </div>
                <!-- ... from metadata outputs -->
            </div>
        `;
    }

    async processFeature() {
        // Calls backend automatically via inherited method
        return {
            output1: 'Output 1 - placeholder',
            output2: 'Output 2 - placeholder',
            // ... from metadata outputs
        };
    }
}
```

### Frontend Loading (Existing in script.js)

```javascript
// When user clicks button (data-feature="17"):
async function loadFeatureModule(featureId, featureName, featureDesc) {
    // 1. Load BaseFeature.js (if not loaded)
    if (!window.BaseFeature) {
        await loadScript('./Features/BaseFeature.js');
    }
    
    // 2. Load feature-specific JS from featureFiles mapping
    const filePath = featureFiles[featureId];
    await loadScript(filePath);
    
    // 3. Create instance from featureClasses mapping
    const FeatureClass = window[featureClasses[featureId]];
    currentFeatureInstance = new FeatureClass();
    
    // 4. Render UI
    featureView.innerHTML = currentFeatureInstance.createFeatureHTML();
}
```

**Key Points:**
- ✅ No frontend code changes needed for new features
- ✅ Dynamic loading based on metadata
- ✅ UI automatically generated from inputs/outputs
- ✅ BaseFeature provides standard interaction patterns

---

## 4. UI Components Updated

### A. Feature Buttons (index.html)
**Materials Exploration Section:**
```html
<div class="feature-subsection">
    <h3>Materials Exploration</h3>
    <div class="feature-container">
        <div class="feature-grid">
            <!-- Auto-generated from metadata -->
            <button class="feature-btn" 
                    data-feature="1" 
                    data-feature-name="Material Search" 
                    data-feature-desc="...">
                Material Search
            </button>
            <!-- ... all materials_exploration features -->
        </div>
    </div>
</div>
```

**Electronics Application Section:**
```html
<div class="feature-subsection">
    <h3>Electronics Application</h3>
    <div class="feature-container">
        <div class="feature-grid">
            <!-- Auto-generated from metadata -->
            <button class="feature-btn" 
                    data-feature="9" 
                    data-feature-name="Device Synthesizability" 
                    data-feature-desc="...">
                Device Synthesizability
            </button>
            <!-- ... all electronics_application features -->
        </div>
    </div>
</div>
```

### B. Script Mappings (script.js)

**Feature Classes Mapping:**
```javascript
const featureClasses = {
    1: 'MaterialSearchFeature',
    2: 'MaterialGenerationFeature',
    // ... auto-generated from metadata
    17: 'NewFeatureFeature'
};
```

**Feature Files Mapping:**
```javascript
const featureFiles = {
    1: './Features/Materials_Exploration/MaterialSearch/MaterialSearch.js',
    2: './Features/Materials_Exploration/MaterialGeneration/MaterialGeneration.js',
    // ... auto-generated from metadata
    17: './Features/Materials_Exploration/NewFeature/NewFeature.js'
};
```

---

## 5. Inputs & Outputs System

### Metadata-Driven UI Generation

**Input Types Supported:**
- `text` → Text input field
- `number` → Number input with min/max/step
- `select` → Dropdown with options
- `checkbox` → Boolean toggle
- `file` → File upload

**Example Metadata Input:**
```json
{
  "name": "propertyType",
  "display_name": "Property Type",
  "type": "select",
  "required": false,
  "options": [
    {"value": "mechanical", "text": "Mechanical Properties"},
    {"value": "thermal", "text": "Thermal Properties"}
  ],
  "default": "",
  "description": "Type of material property"
}
```

**Generated JavaScript:**
```javascript
${this.createSelectInput(
    `propertyType_${this.featureId}`, 
    'Property Type', 
    [
        {value: 'mechanical', text: 'Mechanical Properties'},
        {value: 'thermal', text: 'Thermal Properties'}
    ]
)}
```

**Generated Python:**
```python
def extract_inputs(self, input_data):
    return {
        'propertyType': input_data.get('propertyType', ''),
        # ... other inputs
    }
```

### Output Types Supported:
- `text` → Text display
- `table` → Tabular data
- `link` → Downloadable link
- Custom types can be added

---

## 6. Feature Removal Workflow

### Step 1: Remove from metadata.json
Delete the feature entry from the appropriate category array.

### Step 2: Run Contribution Tool
```bash
python devtools/contribution_tool.py
```

### Step 3: Tool Actions (Automatic)

**A. Removes Feature Folder:**
```
Features/Materials_Exploration/OldFeature/ → DELETED
```

**B. Updates FeatureFactory.py:**
- Removes import statement
- Removes factory entry

**C. Updates index.html:**
- Removes button from feature grid

**D. Updates script.js:**
- Removes from featureClasses mapping
- Removes from featureFiles mapping

---

## 7. Backend Connectivity Verification

### Health Check:
```bash
curl http://localhost:5001/api/health
# Response: {"status": "ok"}
```

### Feature Info:
```bash
curl http://localhost:5001/api/features/info
# Returns all available features and their details
```

### Feature Processing:
```bash
curl -X POST http://localhost:5001/api/process/17 \
  -H "Content-Type: application/json" \
  -d '{"input1": "value1", "input2": "value2"}'
  
# Response:
{
  "success": true,
  "outputs": {
    "output1": "result1",
    "output2": "result2"
  },
  "logs": [...]
}
```

---

## 8. Best Practices

### ✅ DO:
1. **Always use metadata.json** as single source of truth
2. **Run contribution tool** for all additions/removals
3. **Test backend endpoint** after adding features
4. **Verify UI buttons** appear correctly
5. **Check browser console** for loading errors
6. **Use meaningful IDs** (sequential numbers)
7. **Include comprehensive inputs/outputs** in metadata

### ❌ DON'T:
1. **Manually edit** index.html feature buttons
2. **Manually edit** script.js mappings
3. **Skip** the contribution tool
4. **Make multiple changes** at once
5. **Forget** to update metadata when removing features
6. **Use duplicate IDs** for features

---

## 9. Troubleshooting

### Feature Button Not Appearing:
1. Check metadata.json has correct entry
2. Verify contribution tool ran successfully
3. Clear browser cache and reload
4. Check browser console for errors

### Feature Not Loading:
1. Check featureClasses mapping in script.js
2. Verify featureFiles path is correct
3. Check if JS file exists at specified path
4. Open browser DevTools → Network → look for 404s

### Backend Not Processing:
1. Verify FeatureFactory.py has correct import
2. Check factory_factory dict has entry
3. Test `/api/features/info` endpoint
4. Check backend logs for errors

### Inputs/Outputs Not Showing:
1. Verify metadata has inputs/outputs arrays
2. Check generated JS createInputsHTML() method
3. Inspect browser DOM for missing elements
4. Verify BaseFeature.js helper methods work

---

## 10. Summary

The contribution tool provides **end-to-end integration**:

✅ **Metadata** → Single source of truth  
✅ **Templates** → Auto-generated Python & JavaScript  
✅ **Factory** → Automatic backend routing  
✅ **UI Buttons** → Dynamic generation from metadata  
✅ **Script Mappings** → Class & file path synchronization  
✅ **Backend** → Zero-code feature addition support  
✅ **Frontend** → Dynamic loading & rendering  

**Result:** Add/remove features with **zero manual UI or backend code changes** - just update metadata.json and run the tool!
