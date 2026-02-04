// Interface Calculation Feature
class InterfaceCalculationFeature extends BaseFeature {
    constructor(featureId) {
        super(featureId, 'Interface Calculation', 'Calculate and analyze interfaces between different materials in electronic applications');
    }

    createInputsHTML() {
        return `
            <p>Configure interface calculation parameters</p>
            <div class="input-controls">
                ${this.createTextInput(`material1_${this.featureId}`, 'Material 1', 'e.g., Si, GaAs, AlN', true)}
                ${this.createTextInput(`material2_${this.featureId}`, 'Material 2', 'e.g., SiO2, Al2O3, HfO2', true)}
                ${this.createSelectInput(`interfaceType_${this.featureId}`, 'Interface Type', [
                    { value: 'coherent', text: 'Coherent Interface' },
                    { value: 'semicoherent', text: 'Semi-coherent Interface' },
                    { value: 'incoherent', text: 'Incoherent Interface' },
                    { value: 'grain_boundary', text: 'Grain Boundary' }
                ])}
                ${this.createSelectInput(`calculationMethod_${this.featureId}`, 'Calculation Method', [
                    { value: 'dft', text: 'DFT (First Principles)' },
                    { value: 'classical_md', text: 'Classical Molecular Dynamics' },
                    { value: 'tight_binding', text: 'Tight Binding' },
                    { value: 'empirical', text: 'Empirical Models' }
                ])}
                ${this.createNumberInput(`supercellSize_${this.featureId}`, 'Supercell Size (atoms)', '50', '1000', '10')}
                ${this.createCheckboxInput(`includeStrain_${this.featureId}`, 'Include Strain Effects', true)}
                ${this.createCheckboxInput(`calculateBandOffset_${this.featureId}`, 'Calculate Band Offset', true)}
            </div>
        `;
    }

    createOutputsHTML() {
        return `
            <p>Interface calculation results and properties</p>
            <div class="output-display" id="outputDisplay_${this.featureId}">
                <div class="output-item">
                    <strong>Interface Energy:</strong> <span id="interfaceEnergy_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Band Offset:</strong> <span id="bandOffset_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Lattice Mismatch:</strong> <span id="latticeMismatch_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Interface States:</strong> <span id="interfaceStates_${this.featureId}">Pending...</span>
                </div>
                <div class="output-item">
                    <strong>Charge Transfer:</strong> <span id="chargeTransfer_${this.featureId}">Pending...</span>
                </div>
            </div>
        `;
    }

    async processFeature() {
        // Simple fixed results for interface calculation
        return {
            interfaceEnergy: '1.247 J/m²',
            bandOffset: '1.85 eV',
            latticeMismatch: '2.3%',
            interfaceStates: '3.24e12 states/cm²',
            chargeTransfer: '0.285 e⁻'
        };
    }

    updateOutputs(results = null) {
        const finalResults = results || this.results;
        
        document.getElementById(`interfaceEnergy_${this.featureId}`).textContent = finalResults.interfaceEnergy;
        document.getElementById(`bandOffset_${this.featureId}`).textContent = finalResults.bandOffset;
        document.getElementById(`latticeMismatch_${this.featureId}`).textContent = finalResults.latticeMismatch;
        document.getElementById(`interfaceStates_${this.featureId}`).textContent = finalResults.interfaceStates;
        document.getElementById(`chargeTransfer_${this.featureId}`).textContent = finalResults.chargeTransfer;
    }
}

window.InterfaceCalculationFeature = InterfaceCalculationFeature;
