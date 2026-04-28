// DOM elements
const operatingArea = document.getElementById('operatingArea');
const featureView = document.getElementById('featureView');
const llmView = document.getElementById('llmView');
const featureButtons = document.querySelectorAll('.feature-btn');
const iuFeatureButtons = document.querySelectorAll('.iu-feature-btn');
const llmButton = document.getElementById('llmBtn');
const closeChat = document.getElementById('closeChat');
const closeFeature = document.getElementById('closeFeature');
const chatInput = document.getElementById('chatInput');
const sendMessage = document.getElementById('sendMessage');
const chatMessages = document.getElementById('chatMessages');

const iuFeatureModules = {
    database: {
        alexandria: {
            className: 'AlexandriaIUFeature',
            file: './Features/IU_Features/Databases/AlexandriaIUFeature.js',
            id: 1007,
        },
        cod: {
            className: 'CodIUFeature',
            file: './Features/IU_Features/Databases/CodIUFeature.js',
            id: 1008,
        },
        materialsproject: {
            className: 'MaterialsprojectIUFeature',
            file: './Features/IU_Features/Databases/MaterialsprojectIUFeature.js',
            id: 1009,
        },
        mathub3d: {
            className: 'Mathub3dIUFeature',
            file: './Features/IU_Features/Databases/Mathub3dIUFeature.js',
            id: 1010,
        },
        jarvisdft: {
            className: 'JarvisdftIUFeature',
            file: './Features/IU_Features/Databases/JarvisdftIUFeature.js',
            id: 1011,
        },
        aflow: {
            className: 'AflowIUFeature',
            file: './Features/IU_Features/Databases/AflowIUFeature.js',
            id: 1012,
        },
    },
    generator: {
        mattergen_dft_band_gap: {
            className: 'MattergenDftBandGapIUFeature',
            file: './Features/IU_Features/Generators/MattergenDftBandGapIUFeature.js',
            id: 1110,
        },
        mattergen_base_model: {
            className: 'MattergenBaseModelIUFeature',
            file: './Features/IU_Features/Generators/MattergenBaseModelIUFeature.js',
            id: 1111,
        },
        mattergen_mp_20_base: {
            className: 'MattergenMp20BaseIUFeature',
            file: './Features/IU_Features/Generators/MattergenMp20BaseIUFeature.js',
            id: 1112,
        },
        mattergen_chemical_system: {
            className: 'MattergenChemicalSystemIUFeature',
            file: './Features/IU_Features/Generators/MattergenChemicalSystemIUFeature.js',
            id: 1113,
        },
        mattergen_chemical_system_stability: {
            className: 'MattergenChemicalSystemStabilityIUFeature',
            file: './Features/IU_Features/Generators/MattergenChemicalSystemStabilityIUFeature.js',
            id: 1114,
        },
        mattergen_magnetic_density: {
            className: 'MattergenMagneticDensityIUFeature',
            file: './Features/IU_Features/Generators/MattergenMagneticDensityIUFeature.js',
            id: 1115,
        },
        mattergen_magnetic_density_hhi: {
            className: 'MattergenMagneticDensityHhiIUFeature',
            file: './Features/IU_Features/Generators/MattergenMagneticDensityHhiIUFeature.js',
            id: 1116,
        },
        mattergen_bulk_modulus: {
            className: 'MattergenBulkModulusIUFeature',
            file: './Features/IU_Features/Generators/MattergenBulkModulusIUFeature.js',
            id: 1117,
        },
        mattergen_space_group: {
            className: 'MattergenSpaceGroupIUFeature',
            file: './Features/IU_Features/Generators/MattergenSpaceGroupIUFeature.js',
            id: 1118,
        },
    },
    predictor: {
        mattersim: {
            className: 'MattersimIUFeature',
            file: './Features/IU_Features/Predictors/MattersimIUFeature.js',
            id: 2001,
        },
        synthnn: {
            className: 'SynthnnIUFeature',
            file: './Features/IU_Features/Predictors/SynthnnIUFeature.js',
            id: 2002,
        },
        gbfs: {
            className: 'GbfsIUFeature',
            file: './Features/IU_Features/Predictors/GbfsIUFeature.js',
            id: 2005,
        },
        gbfs_2d: {
            className: 'Gbfs2dIUFeature',
            file: './Features/IU_Features/Predictors/Gbfs2dIUFeature.js',
            id: 2006,
        },
    }
};

// Feature class mapping for dynamic loading
const featureClasses = {
    1: 'DatabaseExtractorFeature',
    2: 'StabilityConsensusAnalysisFeature',
    3: 'AmdScreeningFeature',
    4: 'MosfetEvaluatorFeature',
};

// Feature file paths for dynamic loading (relative paths for GitHub Pages compatibility)
const featureFiles = {
    1: './Features/Materials_Exploration/DatabaseExtractor/DatabaseExtractor.js',
    2: './Features/Materials_Exploration/StabilityConsensusAnalysis/StabilityConsensusAnalysis.js',
    3: './Features/Materials_Exploration/AmdScreening/AmdScreening.js',
    4: './Features/Electronics_Application/MosfetEvaluator/MosfetEvaluator.js',
};

// Global feature instances storage
window.features = {};
let currentFeatureInstance = null;

// Resolve backend url for finding scripts
async function resolveBackendBaseUrl() {
    const meta = document.querySelector('meta[name="emos-backend"]');
    if (meta?.content) return meta.content.replace(/\/$/, '');
    if (window.EMOS_BACKEND_BASE_URL) return String(window.EMOS_BACKEND_BASE_URL).replace(/\/$/, '');

    const { protocol, hostname, port } = window.location;
    const devStaticPorts = new Set(['5500', '8000', '8080', '5173']);
    const devBackend = `${protocol}//${hostname}:5001`;

    // Skip same-origin probe on common dev ports to avoid 404 noise
    if (port && devStaticPorts.has(port)) {
        try {
            const res = await fetch(`${devBackend}/api/health`);
            if (res.ok) return devBackend;
        } catch (_) { /* ignore */ }
        return devBackend;
    }

    // Try same-origin when proxied
    try {
        const res = await fetch('/api/health');
        if (res.ok) return window.location.origin;
    } catch (_) { /* ignore */ }

    return devBackend;
}


// Functions
async function showFeatureView(featureNumber, featureName, featureDesc) {
    // Hide other views
    operatingArea.classList.add('hidden');
    llmView.classList.add('hidden');
    
    // Show feature view
    featureView.classList.remove('hidden');
    
    // Load and initialize the specific feature module
    await loadFeatureModule(parseInt(featureNumber), featureName, featureDesc);
    
    // Add visual feedback to the clicked button
    featureButtons.forEach(btn => btn.style.transform = 'scale(1)');
    const clickedButton = document.querySelector(`[data-feature="${featureNumber}"]`);
    if (clickedButton) {
        clickedButton.style.transform = 'scale(0.95)';
        setTimeout(() => {
            clickedButton.style.transform = 'scale(1)';
        }, 150);
    }
}

async function showIUFeatureView(iuType, iuId, iuName, iuDesc) {
    const iuModule = iuFeatureModules?.[iuType]?.[iuId];

    // Hide other views and show feature panel area
    operatingArea.classList.add('hidden');
    llmView.classList.add('hidden');
    featureView.classList.remove('hidden');

    if (!iuModule) {
        featureView.innerHTML = createGenericFeatureView(`${iuName} IU Feature`, iuDesc || 'No IU feature module found.');
        return;
    }

    try {
        if (!window.BaseFeature) {
            await loadScript('./Features/BaseFeature.js');
        }

        if (!window[iuModule.className]) {
            await loadScript(iuModule.file);
        }

        const IUFeatureClass = window[iuModule.className];
        const iuFeatureId = iuModule.id;

        currentFeatureInstance = new IUFeatureClass(iuFeatureId, {
            iuType,
            iuId,
            iuName,
            iuDesc,
        });
        window.features[iuFeatureId] = currentFeatureInstance;

        featureView.innerHTML = currentFeatureInstance.createFeatureHTML();

        if (typeof currentFeatureInstance.initializeUI === 'function') {
            await currentFeatureInstance.initializeUI();
        }
    } catch (error) {
        console.error('Error loading IU feature module:', error);
        featureView.innerHTML = createGenericFeatureView(`${iuName} IU Feature`, iuDesc || 'Failed to load IU feature module.');
    }
}

// Load and initialize a feature module
async function loadFeatureModule(featureId, featureName, featureDesc) {
    try {
        console.log(`Loading feature ${featureId}: ${featureName}`);
        
        // Check if we need to load the BaseFeature first
        if (!window.BaseFeature) {
            console.log('Loading BaseFeature...');
            await loadScript('./Features/BaseFeature.js');
        }
        
        // Load the specific feature if available
        if (featureFiles[featureId] && featureClasses[featureId]) {
            console.log(`Feature file: ${featureFiles[featureId]}`);
            console.log(`Feature class: ${featureClasses[featureId]}`);
            
            // Check if the feature class is already loaded
            if (!window[featureClasses[featureId]]) {
                console.log(`Loading feature script: ${featureFiles[featureId]}`);
                try {
                    await loadScript(featureFiles[featureId]);
                    console.log(`Successfully loaded: ${featureFiles[featureId]}`);
                } catch (scriptError) {
                    console.error(`Failed to load script: ${featureFiles[featureId]}`, scriptError);
                    throw scriptError;
                }
            }
            
            // Create feature instance and initialize
            const FeatureClass = window[featureClasses[featureId]];
            console.log(`Feature class found:`, FeatureClass);
            
            currentFeatureInstance = new FeatureClass(featureId);
            window.features[featureId] = currentFeatureInstance;

            // Ensure modular property mappings are loaded before building UI
            // (the cache is shared, so this is a no-op after the first load)
            if (typeof _loadPropertyMappings === 'function') {
                await _loadPropertyMappings();
            }
            
            // Replace the feature view content with the specific feature's interface
            featureView.innerHTML = currentFeatureInstance.createFeatureHTML();
            console.log('Feature HTML created successfully');
            
        } else {
            // Fallback to generic processing view for features not yet implemented
            console.log(`Feature ${featureId} not implemented, using fallback`);
            featureView.innerHTML = createGenericFeatureView(featureName, featureDesc);
        }
    } catch (error) {
        console.error('Error loading feature module:', error);
        featureView.innerHTML = createGenericFeatureView(featureName, featureDesc);
    }
}

// Helper function to load scripts dynamically
function loadScript(src) {
    return new Promise((resolve, reject) => {
        // Prevent duplicate <script> tags for the same URL
        if (document.querySelector(`script[src="${src}"]`)) {
            resolve();
            return;
        }
        const script = document.createElement('script');
        script.src = src;
        script.onload = () => {
            console.log(`${src} loaded successfully`);
            resolve();
        };
        script.onerror = () => {
            console.error(`Failed to load ${src}`);
            reject(new Error(`Failed to load ${src}`));
        };
        document.head.appendChild(script);
    });
}
// Expose globally so other scripts can dynamically load modules
window.loadScript = loadScript;

// Create generic feature view for fallback
function createGenericFeatureView(featureName, featureDesc) {
    return `
        <div class="feature-header">
            <div class="feature-title-section">
                <h3><span id="featureTitle">${featureName}</span> Processing</h3>
                <p class="feature-subtitle" id="featureSubtitle">${featureDesc}</p>
            </div>
            <button class="close-feature" id="closeFeature">×</button>
        </div>
        <div class="process-section">
            <h3>Inputs</h3>
            <div class="process-content" id="inputsContent">
                <p>Configure your input parameters for ${featureName}</p>
                <div class="input-controls">
                    <label>Parameter 1: <input type="text" placeholder="Enter value"></label>
                    <label>Parameter 2: <input type="text" placeholder="Enter value"></label>
                    <label>Parameter 3: <input type="text" placeholder="Enter value"></label>
                </div>
            </div>
        </div>
        
        <div class="process-section">
            <h3>Processing</h3>
            <div class="process-content" id="processingContent">
                <p>Processing ${featureName}...</p>
                <div class="progress-bar">
                    <div class="progress-fill"></div>
                </div>
                <button class="process-btn" onclick="startGenericProcessing()">Start Processing</button>
            </div>
        </div>
        
        <div class="process-section">
            <h3>Outputs</h3>
            <div class="process-content" id="outputsContent">
                <p>Results for ${featureName}</p>
                <div class="output-display">
                    <div class="output-item">
                        <strong>Result 1:</strong> <span>Pending...</span>
                    </div>
                    <div class="output-item">
                        <strong>Result 2:</strong> <span>Pending...</span>
                    </div>
                    <div class="output-item">
                        <strong>Result 3:</strong> <span>Pending...</span>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Generic processing function for fallback features
function startGenericProcessing() {
    const progressFill = document.querySelector('.progress-fill');
    const processBtn = document.querySelector('.process-btn');
    const outputItems = document.querySelectorAll('.output-item span');
    
    // Disable button and show processing
    processBtn.disabled = true;
    processBtn.textContent = 'Processing...';
    
    // Animate progress bar
    progressFill.style.width = '100%';
    
    // Simulate processing time and update outputs
    setTimeout(() => {
        outputItems[0].textContent = 'Analysis complete - 98.5% accuracy';
        setTimeout(() => {
            outputItems[1].textContent = 'Processing finished successfully';
            setTimeout(() => {
                outputItems[2].textContent = 'Results generated and saved';
                
                // Re-enable button
                processBtn.disabled = false;
                processBtn.textContent = 'Start Processing';
                
                // Reset progress for next use
                setTimeout(() => {
                    progressFill.style.width = '0%';
                }, 1000);
            }, 800);
        }, 600);
    }, 2000);
}

function showLLMView() {
    // Hide other views
    operatingArea.classList.add('hidden');
    featureView.classList.add('hidden');
    
    // Show LLM view
    llmView.classList.remove('hidden');
    
    // Focus on chat input
    setTimeout(() => {
        chatInput.focus();
    }, 100);
    
    // Add visual feedback to LLM button
    llmButton.style.transform = 'scale(0.95)';
    setTimeout(() => {
        llmButton.style.transform = 'scale(1)';
    }, 150);
}

function showWelcomeView() {
    // Hide other views
    featureView.classList.add('hidden');
    llmView.classList.add('hidden');
    
    // Show operating area
    operatingArea.classList.remove('hidden');
    
    // Clear chat history when closing LLM view
    clearChatHistory();
    
    // Clean up current feature instance
    if (currentFeatureInstance) {
        if (typeof currentFeatureInstance.destroy === 'function') {
            currentFeatureInstance.destroy();
        }
        currentFeatureInstance = null;
    }
}

function clearChatHistory() {
    // Reset chat messages to initial state with welcome and beta notice
    if (chatMessages) {
        chatMessages.innerHTML = `
            <div class="message bot-message">
                <div class="message-content">
                    Hello! I'm the EMOS Assistant. How can I help you with electronics materials science today?
                </div>
            </div>
            <div class="message system-message">
                <div class="message-content">
                    <span class="beta-icon">⚠️</span> <strong>Beta Notice:</strong> This LLM feature is currently in development. Responses are simulated and may not reflect actual AI capabilities. Full LLM integration coming soon!
                </div>
            </div>
        `;
    }
}

// Chat functionality
function sendChatMessage() {
    const message = chatInput.value.trim();
    if (!message) return;
    
    // Add user message
    addMessage(message, 'user');
    
    // Clear input
    chatInput.value = '';
    
    // Simulate bot response
    setTimeout(() => {
        const botResponse = generateBotResponse(message);
        addMessage(botResponse, 'bot');
    }, 1000);
}

function addMessage(content, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}-message`;
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.textContent = content;
    
    messageDiv.appendChild(messageContent);
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}



function generateBotResponse(userMessage) {
    const responses = [
        "That's an interesting question about materials science! Let me help you with that.",
        "Based on your query, I can provide insights into material properties and behavior.",
        "Materials science involves understanding structure-property relationships. What specific aspect interests you?",
        "I can assist with crystallography, thermodynamics, mechanical properties, and more. What would you like to explore?",
        "Great question! In materials science, we often consider processing-structure-property-performance relationships.",
        "I'm here to help with your materials research. Could you provide more details about what you're working on?",
        "Materials engineering combines physics, chemistry, and engineering principles. What's your specific application?",
        "From nanomaterials to bulk properties, I can discuss various scales of material behavior. What interests you most?"
    ];
    
    // Simple keyword-based responses
    const lowerMessage = userMessage.toLowerCase();
    
    if (lowerMessage.includes('crystal') || lowerMessage.includes('structure')) {
        return "Crystal structures are fundamental to understanding material properties. Different crystal systems (cubic, tetragonal, orthorhombic, etc.) lead to different physical and mechanical properties.";
    } else if (lowerMessage.includes('mechanical') || lowerMessage.includes('strength')) {
        return "Mechanical properties like tensile strength, yield strength, and fracture toughness are crucial for engineering applications. These depend on microstructure, defects, and processing history.";
    } else if (lowerMessage.includes('thermal') || lowerMessage.includes('temperature')) {
        return "Thermal properties such as thermal conductivity, expansion coefficient, and specific heat are important for high-temperature applications and thermal management.";
    } else if (lowerMessage.includes('database')) {
        return "Materials databases are invaluable for research and design. They contain property data, phase diagrams, and processing information for thousands of materials.";
    } else if (lowerMessage.includes('predict') || lowerMessage.includes('model')) {
        return "Predictive modeling in materials science uses computational methods like DFT, molecular dynamics, and machine learning to predict material properties before synthesis.";
    } else {
        return responses[Math.floor(Math.random() * responses.length)];
    }
}

function startProcessing() {
    const progressFill = document.querySelector('.progress-fill');
    const processBtn = document.querySelector('.process-btn');
    const outputItems = document.querySelectorAll('.output-item span');
    
    // Disable button and show processing
    processBtn.disabled = true;
    processBtn.textContent = 'Processing...';
    
    // Animate progress bar
    progressFill.style.width = '100%';
    
    // Simulate processing time and update outputs
    setTimeout(() => {
        outputItems[0].textContent = 'Analysis complete - 98.5% accuracy';
        setTimeout(() => {
            outputItems[1].textContent = 'Material properties calculated';
            setTimeout(() => {
                outputItems[2].textContent = 'Optimization recommendations generated';
                
                // Re-enable button
                processBtn.disabled = false;
                processBtn.textContent = 'Start Processing';
                
                // Reset progress for next use
                setTimeout(() => {
                    progressFill.style.width = '0%';
                }, 1000);
            }, 800);
        }, 600);
    }, 2000);
}

function resetProcessing() {
    const progressFill = document.querySelector('.progress-fill');
    const processBtn = document.querySelector('.process-btn');
    const outputItems = document.querySelectorAll('.output-item span');
    
    // Reset progress bar
    progressFill.style.width = '0%';
    
    // Reset button
    processBtn.disabled = false;
    processBtn.textContent = 'Start Processing';
    
    // Reset outputs
    outputItems.forEach(item => {
        item.textContent = 'Pending...';
    });
}

// Initialize application
document.addEventListener('DOMContentLoaded', async () => {
    // Load BaseFeature class first
    const baseFeatureScript = document.createElement('script');
    baseFeatureScript.src = '/Features/BaseFeature.js';
    baseFeatureScript.onload = function() {
        console.log('BaseFeature loaded successfully');
    };
    document.head.appendChild(baseFeatureScript);


    // Resolve backend URL once and reuse
    const BACKEND_BASE_URL = await resolveBackendBaseUrl();
    window.BACKEND_BASE_URL = BACKEND_BASE_URL; // optional exposure for debugging
    console.log('Backend base URL:', BACKEND_BASE_URL);

    //Generator selection functionality
    const checkboxes = document.querySelectorAll("input[type='checkbox']");

    checkboxes.forEach(checkbox => {
        checkbox.addEventListener("change", async function() {
            const ui_type = this.getAttribute("ui-type");
            const className = this.value; // use value attribute
            const active = this.checked;

            // Always log the local change first
            console.log(`${ui_type} ${className} ${active ? 'checked' : 'unchecked'} locally`);

            try {
                const res = await fetch(`${BACKEND_BASE_URL}/api/process/toggle_IU`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ class_name: className, class_type: ui_type, active })
                });
                const data = await res.json();

                if (!res.ok) {
                    console.warn(`Backend response not OK for ${className}: ${data?.message || data?.error || "Unknown error"}`);
                    return;
                }

                console.log(`Backend success: ${data.message}`);
            } catch (err) {
                console.warn(`Backend unavailable for ${className}:`, err.message);
            }
        });
    });
    
    // Feature button functionality - SINGLE EVENT LISTENER
    featureButtons.forEach(button => {
        button.addEventListener('click', function() {
            const featureNumber = this.getAttribute('data-feature');
            const featureName = this.getAttribute('data-feature-name');
            const featureDesc = this.getAttribute('data-feature-desc');
            
            showFeatureView(featureNumber, featureName, featureDesc);
        });
    });

    // IU feature button functionality (phase 1: Alexandria)
    iuFeatureButtons.forEach(button => {
        button.addEventListener('click', async function() {
            const iuId = this.getAttribute('data-iu-feature');
            const iuType = this.getAttribute('data-iu-type');
            const iuName = this.getAttribute('data-iu-name');
            const iuDesc = this.getAttribute('data-iu-desc');
            await showIUFeatureView(iuType, iuId, iuName, iuDesc);
        });
    });

    // LLM button functionality
    if (llmButton) {
        llmButton.addEventListener('click', showLLMView);
    }

    // Close feature functionality
    document.addEventListener('click', (e) => {
        if (e.target.id === 'closeFeature' || e.target.classList.contains('close-feature')) {
            showWelcomeView();
        }
    });

    // Close chat functionality
    if (closeChat) {
        closeChat.addEventListener('click', showWelcomeView);
    }

    // Chat functionality
    if (sendMessage) {
        sendMessage.addEventListener('click', sendChatMessage);
    }
    
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendChatMessage();
            }
        });
    }

    // Process button functionality - Only for fallback/generic features
    document.addEventListener('click', (e) => {
        // Only handle process buttons that don't have a specific onclick handler
        if (e.target.classList.contains('process-btn') && !e.target.onclick) {
            startProcessing();
        }
    });

    // Add hover effects to sections
    const sections = document.querySelectorAll('.control-section');
    sections.forEach(section => {
        section.addEventListener('mouseenter', () => {
            section.style.transform = 'translateY(-2px)';
            section.style.transition = 'transform 0.3s ease';
        });
        
        section.addEventListener('mouseleave', () => {
            section.style.transform = 'translateY(0)';
        });
    });
    
    // Initialize with welcome view
    showWelcomeView();
});
