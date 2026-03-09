/**
 * 
 * Adding a new generator's UI only requires:
 *
 * Create Information_Units/Generators/Foo/FooInputs.js with a class that has render(), attachListeners(), and collectValues().
 * Add one entry to GENERATOR_INPUTS_REGISTRY in BaseFeature.js.
 * 
 * MattergenInputs.js
 * ==================
 * Defines the dynamic input UI for the MatterGen generator.
 *
 * When MatterGen is selected as a generator in a Feature, this module provides:
 *   1.  An <h4> title "MatterGen"
 *   2.  A dropdown of pretrained model names (from _MODEL_PROPERTIES_MAP keys,
 *       plus the two unconditional base models)
 *   3.  Dynamic property fields that appear/disappear based on the selected
 *       model — field types are derived from property_mappings.json
 *
 * Usage from a Feature's createInputsHTML():
 *   const mg = new MattergenInputs(this.featureId);
 *   return mg.render();
 *
 * Then, after the HTML is in the DOM, call:
 *   mg.attachListeners();
 *
 * To collect the values for a backend request:
 *   const payload = mg.collectValues();
 */

// ── Model → required-property list ──────────────────────────────────
// Mirrors _MODEL_PROPERTIES_MAP from MattergenGenerator.py.
// Base models have an empty property list (unconditional generation).
const MATTERGEN_MODEL_PROPERTIES_MAP = {
    demo:                                [],
    mattergen_base:                      [],
    mp_20_base:                          [],
    chemical_system:                     ["chemical_system"],
    chemical_system_energy_above_hull:   ["chemical_system", "energy_above_hull"],
    dft_band_gap:                        ["dft_band_gap"],
    dft_mag_density:                     ["dft_mag_density"],
    dft_mag_density_hhi_score:           ["dft_mag_density", "hhi_score"],
    ml_bulk_modulus:                     ["ml_bulk_modulus"],
    space_group:                         ["space_group"],
};

// ── Property metadata (sourced from property_mappings.json) ─────────
// Only the properties that MatterGen actually uses are listed here.
const MATTERGEN_PROPERTY_META = {
    chemical_system: {
        label:       "Chemical System",
        type:        "string",
        placeholder: "e.g. Si-O  or  Li-Fe-P-O",
        description: "Participating atom types separated with '-'",
    },
    energy_above_hull: {
        label:       "Energy Above Hull",
        type:        "float",
        unit:        "eV/atom",
        min:         0,
        step:        0.01,
        description: "Distance from the convex hull",
    },
    dft_band_gap: {
        label:       "DFT Band Gap",
        type:        "float",
        unit:        "eV",
        min:         0,
        step:        0.1,
        description: "Direct electronic band gap",
    },
    dft_mag_density: {
        label:       "Magnetic Density",
        type:        "float",
        unit:        "T",
        step:        0.1,
        description: "DFT magnetic density",
    },
    hhi_score: {
        label:       "HHI Score",
        type:        "float",
        min:         0,
        step:        0.01,
        description: "Herfindahl–Hirschman Index score",
    },
    ml_bulk_modulus: {
        label:       "Bulk Modulus",
        type:        "float",
        unit:        "GPa",
        min:         0,
        step:        1,
        description: "ML-predicted bulk modulus",
    },
    space_group: {
        label:       "Space Group Number",
        type:        "integer",
        min:         1,
        max:         230,
        step:        1,
        description: "International space-group number (1–230)",
    },
};

// ── Helper: human-readable model labels ─────────────────────────────
function _modelDisplayName(key) {
    const MAP = {
        demo:                                "⚙ Demo (fake response for debugging)",
        mattergen_base:                      "MatterGen Base (unconditional)",
        mp_20_base:                          "MP-20 Base (unconditional)",
        chemical_system:                     "Chemical System",
        chemical_system_energy_above_hull:   "Chemical System + Energy Above Hull",
        dft_band_gap:                        "DFT Band Gap",
        dft_mag_density:                     "Magnetic Density",
        dft_mag_density_hhi_score:           "Magnetic Density + HHI Score",
        ml_bulk_modulus:                     "Bulk Modulus (ML)",
        space_group:                         "Space Group",
    };
    return MAP[key] || key;
}

// =====================================================================
//  MattergenInputs class
// =====================================================================
class MattergenInputs {
    /**
     * @param {string|number} featureId – the owning Feature's id, used to
     *     namespace all DOM element ids so multiple features can coexist.
     */
    constructor(featureId) {
        this.fid = featureId;
        this._selectId    = `mattergen_model_${this.fid}`;
        this._propsContId = `mattergen_props_${this.fid}`;
        this._batchSizeId = `mattergen_batch_size_${this.fid}`;
        this._numBatchesId = `mattergen_num_batches_${this.fid}`;
    }

    // ── Render ───────────────────────────────────────────────────────
    /**
     * Return the full HTML string for the MatterGen input section.
     * After injecting this into the DOM, call `attachListeners()`.
     */
    render() {
        const modelOptions = Object.keys(MATTERGEN_MODEL_PROPERTIES_MAP)
            .map(k => `<option value="${k}">${_modelDisplayName(k)}</option>`)
            .join("\n");

        return `
            <div class="mattergen-inputs" id="mattergen_section_${this.fid}">
                <h4>MatterGen</h4>

                <label>Pretrained Model:
                    <select id="${this._selectId}">
                        ${modelOptions}
                    </select>
                </label>

                <!-- common generation parameters -->
                <label>Batch Size:
                    <input type="number" id="${this._batchSizeId}" value="10" min="1" max="1000" step="1">
                </label>
                <label>Number of Batches:
                    <input type="number" id="${this._numBatchesId}" value="1" min="1" max="100" step="1">
                </label>

                <!-- dynamic property fields (filled by JS on model change) -->
                <div id="${this._propsContId}" class="mattergen-property-fields"></div>
            </div>
        `;
    }

    // ── Dynamic field rendering ──────────────────────────────────────
    /** Build the HTML for the property fields required by `modelKey`. */
    _renderPropertyFields(modelKey) {
        const props = MATTERGEN_MODEL_PROPERTIES_MAP[modelKey] || [];
        if (props.length === 0) {
            return `<p class="mattergen-hint"><em>This model generates structures unconditionally — no property targets needed.</em></p>`;
        }

        return props.map(propKey => {
            const meta = MATTERGEN_PROPERTY_META[propKey];
            if (!meta) return `<!-- unknown property: ${propKey} -->`;

            const inputId = `mattergen_prop_${propKey}_${this.fid}`;
            const unitStr = meta.unit ? ` (${meta.unit})` : "";
            const labelText = `${meta.label}${unitStr}`;

            if (meta.type === "string") {
                return `
                    <label>${labelText}:
                        <input type="text" id="${inputId}"
                               placeholder="${meta.placeholder || ""}"
                               title="${meta.description || ""}">
                    </label>`;
            }

            // integer or float → number input
            const step = meta.step ?? (meta.type === "integer" ? 1 : "any");
            const min  = meta.min  != null ? `min="${meta.min}"` : "";
            const max  = meta.max  != null ? `max="${meta.max}"` : "";
            return `
                <label>${labelText}:
                    <input type="number" id="${inputId}"
                           step="${step}" ${min} ${max}
                           title="${meta.description || ""}">
                </label>`;
        }).join("\n");
    }

    // ── Event binding ────────────────────────────────────────────────
    /**
     * Attach the change-listener to the model dropdown so the property
     * fields update automatically.  Call this **once** after injecting
     * the HTML returned by `render()` into the DOM.
     */
    attachListeners() {
        const select = document.getElementById(this._selectId);
        if (!select) return;

        const container = document.getElementById(this._propsContId);

        // Initial render for the default selection
        container.innerHTML = this._renderPropertyFields(select.value);

        // Re-render on change
        select.addEventListener("change", () => {
            container.innerHTML = this._renderPropertyFields(select.value);
        });
    }

    // ── Collect values ───────────────────────────────────────────────
    /**
     * Read the current values from the DOM and return an object ready to
     * be merged into the payload sent to the backend.
     *
     * @returns {{
     *   pretrained_name: string,
     *   batch_size: number,
     *   num_batches: number,
     *   properties_to_condition_on: Object
     * }}
     */
    collectValues() {
        const select = document.getElementById(this._selectId);
        const modelKey = select ? select.value : "mattergen_base";

        const batchSizeEl  = document.getElementById(this._batchSizeId);
        const numBatchesEl = document.getElementById(this._numBatchesId);

        const payload = {
            pretrained_name: modelKey,
            batch_size:  parseInt(batchSizeEl?.value || "10", 10),
            num_batches: parseInt(numBatchesEl?.value || "1", 10),
            properties_to_condition_on: {},
        };

        const props = MATTERGEN_MODEL_PROPERTIES_MAP[modelKey] || [];
        for (const propKey of props) {
            const el = document.getElementById(`mattergen_prop_${propKey}_${this.fid}`);
            if (!el || el.value === "") continue;

            const meta = MATTERGEN_PROPERTY_META[propKey];
            if (meta && meta.type === "integer") {
                payload.properties_to_condition_on[propKey] = parseInt(el.value, 10);
            } else if (meta && meta.type === "float") {
                payload.properties_to_condition_on[propKey] = parseFloat(el.value);
            } else {
                payload.properties_to_condition_on[propKey] = el.value;
            }
        }

        return payload;
    }
}

// Export for browser & module contexts
if (typeof window !== "undefined") {
    window.MattergenInputs = MattergenInputs;
    // Also expose the constants so other code can inspect them
    window.MATTERGEN_MODEL_PROPERTIES_MAP = MATTERGEN_MODEL_PROPERTIES_MAP;
    window.MATTERGEN_PROPERTY_META        = MATTERGEN_PROPERTY_META;
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = { MattergenInputs, MATTERGEN_MODEL_PROPERTIES_MAP, MATTERGEN_PROPERTY_META };
}
