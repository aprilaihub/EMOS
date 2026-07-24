/* ============================================================
   EMOS Form Page — data model
   Units (19), features (4), mock candidates, onboarding.
   ============================================================ */

const UNITS = {
  database: {
    label: "Databases",
    items: [
      { id: "cod",              name: "COD",              desc: "Crystallography Open Database: open-access collection of experimentally determined crystal structures." },
      { id: "materialsproject", name: "MaterialsProject", desc: "The Materials Project: DFT-computed properties for over 150,000 inorganic compounds." },
      { id: "alexandria",       name: "Alexandria",       desc: "Alexandria: large-scale DFT database of two-dimensional and three-dimensional materials." },
      { id: "mathub3d",         name: "Mathub3d",         desc: "Materials Cloud 3D: curated set of 3D crystal structures with computed electronic properties." },
      { id: "jarvisdft",        name: "JarvisDFT",        desc: "JARVIS-DFT: NIST database of DFT-calculated properties optimised for electronic applications." },
      { id: "aflow",            name: "AFLOW",            desc: "AFLOW: automatic high-throughput database of ab initio computed materials properties." },
    ],
  },
  generator: {
    label: "Generators",
    items: [
      { id: "mg_base",        name: "MatterGen: Base Model",               desc: "Unconditioned MatterGen: generates novel crystal structures with no property constraints." },
      { id: "mg_mp20",        name: "MatterGen: MP-20 Base",               desc: "MatterGen trained on MP-20 dataset: targeted generation of stable inorganic crystals." },
      { id: "mg_chem",        name: "MatterGen: Chemical System",          desc: "Generates structures conditioned on a specific chemical system (e.g. Ga-N)." },
      { id: "mg_chem_stab",   name: "MatterGen: Chemical System + Stability", desc: "Chemical system generation with added stability conditioning for lower hull energy." },
      { id: "mg_bandgap",     name: "MatterGen: DFT Band Gap",             desc: "Generates structures targeting a specified DFT band gap value." },
      { id: "mg_magdens",     name: "MatterGen: Magnetic Density",         desc: "Generates structures conditioned on target magnetic density." },
      { id: "mg_magdens_hhi", name: "MatterGen: Magnetic Density + HHI",   desc: "Magnetic density generation with Herfindahl-Hirschman Index constraint for elemental abundance." },
      { id: "mg_bulk",        name: "MatterGen: Bulk Modulus",             desc: "Generates structures conditioned on a target bulk modulus (stiffness)." },
      { id: "mg_spacegroup",  name: "MatterGen: Space Group",              desc: "Generates structures constrained to a specific crystallographic space group." },
    ],
  },
  predictor: {
    label: "Predictors",
    items: [
      { id: "mattersim", name: "MatterSim", desc: "MatterSim: universal ML potential for fast prediction of energy, forces, and stability across materials." },
      { id: "synthnn",   name: "SynthNN",   desc: "SynthNN: neural network predictor for synthesisability score of a proposed crystal structure." },
      { id: "gbfs",      name: "GBFS",      desc: "GBFS: graph-based feature screening for rapid property prediction and candidate ranking." },
      { id: "gbfs_2d",   name: "GBFS-2D",   desc: "GBFS-2D: variant of GBFS optimised for two-dimensional layered materials." },
    ],
  },
};

/* ============================================================
   Unit panels — the "Open" drawer for an individual IU.
   COD is fully specified (worked example). Every other unit
   falls back to DEFAULT_UNIT_PANEL, keyed by category, so the
   drawer shell is real for all 19 without inventing 19 schemas.
   ============================================================ */
const UNIT_PANELS = {
  cod: {
    title: "COD",
    subtitle: "Crystallography Open Database: open-access collection of crystal structures",
    kind: "database",
    inputs: [
      { id: "batchSize",    label: "Batch size",          type: "number", value: 25, placeholder: "25" },
      { id: "composition",  label: "Target compositions", type: "text",   placeholder: "e.g. Fe2O3, GaN" },
      { id: "elements",     label: "Elements",            type: "text",   placeholder: "e.g. Ga, N" },
      { id: "formula",      label: "Formula description", type: "text",   placeholder: "e.g. binary oxide", advanced: true },
      { id: "codId",        label: "COD entry ID",        type: "text",   placeholder: "Optional",          advanced: true },
      { id: "nelements",    label: "Number of elements",  type: "number", placeholder: "e.g. 2",            advanced: true },
      { id: "nperiodic",    label: "Periodic dimensions", type: "select", options: ["Any", "0", "1", "2", "3"], advanced: true },
      { id: "type",         label: "Structure type",      type: "select", options: ["Any", "Mineral", "Synthetic", "Theoretical"], advanced: true },
    ],
    outputLabel: "Retrieved dataset",
  },
};

const DEFAULT_UNIT_PANEL = {
  database: {
    inputs: [
      { id: "batchSize",   label: "Batch size",          type: "number", value: 25 },
      { id: "composition", label: "Target compositions", type: "text", placeholder: "e.g. Fe2O3" },
      { id: "elements",    label: "Elements",            type: "text", placeholder: "e.g. Ga, N" },
    ],
    outputLabel: "Retrieved dataset",
  },
  generator: {
    inputs: [
      { id: "samples",     label: "Samples to generate", type: "number", value: 64 },
      { id: "targetProp",  label: "Target property",     type: "text", placeholder: "e.g. band gap" },
    ],
    outputLabel: "Generated structures (CIF)",
  },
  predictor: {
    inputs: [
      { id: "batchSize",   label: "Batch size",          type: "number", value: 32 },
      { id: "property",    label: "Property",            type: "select", options: ["All", "Band gap", "Formation energy", "Stability"] },
    ],
    outputLabel: "Prediction result",
  },
};

// active stage: which pipeline stage a feature lights up
const FEATURES = [
  {
    id: "db_extract",
    name: "Database Extractor",
    ready: "Ready", readyClass: "ready",
    uses: "database",
    stage: "SOURCE",
    eyebrow: "Feature · uses selection",
    desc: "Pull crystal structures and their computed properties from the databases you have selected, then rank them by stability.",
    params: [
      { kind: "slider", id: "maxResults", label: "Max batch size / database", unit: "structures", min: 50, max: 1000, step: 50, value: 100 },
      { kind: "slider", id: "bandgapMin", label: "Band gap minimum", unit: "eV", min: 0, max: 6, step: 0.1, value: 0.8 },
      { kind: "slider", id: "ehullMax",   label: "Energy above hull max", unit: "eV/atom", min: 0, max: 0.5, step: 0.01, value: 0.10 },
      { kind: "text",   id: "elements",   label: "Required elements", placeholder: "e.g. Ga, N" },
    ],
    advanced: [
      { kind: "select", id: "sortBy", label: "Sort by", options: ["Stability", "Band gap", "Formation energy"] },
      { kind: "select", id: "spaceGroup", label: "Crystal system", options: ["Any", "Cubic", "Hexagonal", "Tetragonal", "Orthorhombic"] },
    ],
  },
  {
    id: "stability",
    name: "Stability Consensus",
    ready: "Ready", readyClass: "ready",
    uses: "predictor",
    stage: "SCREEN",
    eyebrow: "Feature · uses selection",
    desc: "Aggregate stability verdicts across the ML predictors you have selected to reach a consensus energy above hull for each candidate.",
    params: [
      { kind: "slider", id: "ensemble", label: "Ensemble members", unit: "models", min: 1, max: 4, step: 1, value: 3 },
      { kind: "slider", id: "agree",    label: "Agreement threshold", unit: "%", min: 50, max: 100, step: 5, value: 75 },
    ],
    advanced: [
      { kind: "select", id: "relax", label: "Relaxation", options: ["None", "Light", "Full"] },
    ],
  },
  {
    id: "amd",
    name: "AMD Screening",
    ready: "Beta", readyClass: "beta",
    uses: "predictor",
    stage: "SCREEN",
    eyebrow: "Feature · uses selection",
    desc: "Screen uploaded CIF structures with average minimum distance fingerprints to flag near-duplicate and outlier candidates.",
    params: [
      { kind: "slider", id: "kNeighbours", label: "k neighbours", unit: "", min: 1, max: 50, step: 1, value: 12 },
      { kind: "slider", id: "cutoff",      label: "Distance cutoff", unit: "Å", min: 1, max: 12, step: 0.5, value: 6 },
    ],
    advanced: [
      { kind: "select", id: "metric", label: "Distance metric", options: ["Chebyshev", "Euclidean", "Manhattan"] },
    ],
  },
  {
    id: "mosfet",
    name: "MOSFET Evaluator",
    ready: "Experimental", readyClass: "exp",
    uses: null,
    stage: "EVALUATE",
    eyebrow: "Feature · device level",
    desc: "Run a 2D Poisson and drift-diffusion solver to estimate device-level figures of merit for a candidate channel material.",
    params: [
      { kind: "slider", id: "gateV",   label: "Gate voltage", unit: "V", min: 0, max: 3, step: 0.1, value: 1.2 },
      { kind: "slider", id: "channelL", label: "Channel length", unit: "nm", min: 5, max: 100, step: 5, value: 20 },
      { kind: "slider", id: "doping",  label: "Doping density", unit: "1e18 cm⁻³", min: 0.1, max: 10, step: 0.1, value: 2.0 },
    ],
    advanced: [
      { kind: "select", id: "temp", label: "Temperature", options: ["300 K", "77 K", "400 K"] },
    ],
  },
];

// mock candidate structures (band gap eV as the lead property)
const CANDIDATES = [
  { id: "mp-1234",  formula: "Ga2O3",  el: "Ga", val: 4.80, err: 0.18, lo: 4.4, hi: 5.2, ef: -2.91, source: "MaterialsProject", stability: "stable" },
  { id: "cod-7781", formula: "GaN",    el: "Ga", val: 3.42, err: 0.09, lo: 3.2, hi: 3.6, ef: -1.62, source: "COD",             stability: "stable" },
  { id: "afl-5520", formula: "ZnO",    el: "Zn", val: 3.30, err: 0.21, lo: 2.9, hi: 3.7, ef: -1.71, source: "AFLOW",           stability: "stable" },
  { id: "alx-3098", formula: "In2O3",  el: "In", val: 2.90, err: 0.15, lo: 2.6, hi: 3.2, ef: -2.10, source: "Alexandria",      stability: "marginal" },
  { id: "jvd-4412", formula: "SnO2",   el: "Sn", val: 3.60, err: 0.12, lo: 3.3, hi: 3.9, ef: -2.44, source: "JarvisDFT",       stability: "stable" },
  { id: "mp-8841",  formula: "Fe2O3",  el: "Fe", val: 2.20, err: 0.28, lo: 1.7, hi: 2.7, ef: -1.49, source: "MaterialsProject", stability: "marginal" },
  { id: "mh3-2210", formula: "MoS2",   el: "Mo", val: 1.80, err: 0.10, lo: 1.6, hi: 2.0, ef: -1.05, source: "Mathub3d",        stability: "stable" },
  { id: "cod-9930", formula: "WSe2",   el: "W",  val: 1.62, err: 0.14, lo: 1.4, hi: 1.9, ef: -0.88, source: "COD",             stability: "marginal" },
  { id: "afl-1177", formula: "CdTe",   el: "Cd", val: 1.50, err: 0.07, lo: 1.4, hi: 1.6, ef: -0.74, source: "AFLOW",           stability: "stable" },
  { id: "alx-6654", formula: "Bi2Te3", el: "Bi", val: 0.30, err: 0.06, lo: 0.2, hi: 0.4, ef: -0.52, source: "Alexandria",      stability: "unstable" },
];

// element colors for the crystal legend / viewer (CPK-ish)
const ELEMENT_COLORS = {
  Ga: "#E06633", N: "#3050F8", O: "#FF0D0D", Zn: "#7D80B0", In: "#A67573",
  Sn: "#668080", Fe: "#E06633", Mo: "#54B5B5", S: "#FFFF30", W: "#2194D6",
  Se: "#FFA100", Cd: "#FFD98F", Bi: "#9E4FB5", Te: "#D47A00",
};

// onboarding (4 steps); preview is rendered live HTML
const ONBOARDING = [
  {
    title: "Select units by clicking them",
    desc: "Click any database, generator or predictor row to add it to your pipeline; click again to remove it. The dot turns red when a unit is selected, and the pipeline strip at the top fills in live.",
    preview: `<div style="display:flex;align-items:center;gap:10px;padding:8px 12px;background:var(--surface-selected);border-radius:var(--radius-card);width:230px;">
      <span class="dot database dot-on"></span>
      <span style="font-size:13px;font-weight:500;flex:1;text-align:left;">COD</span>
      <span style="font-size:11px;color:var(--text-secondary);border:1px solid var(--border-medium);border-radius:var(--radius-control);padding:1px 8px;">Open</span></div>`,
  },
  {
    title: "Open a feature to run a workflow",
    desc: "Features combine your selected units into one run. Selected databases are queried together; tune parameters on the left, launch on the right, and follow the live log.",
    preview: `<button class="btn btn-primary btn-lg" style="width:230px;">▶ Run Database Extractor</button>`,
  },
  {
    title: "Explore, pin and annotate results",
    desc: "Sort ranked candidates in the table, inspect real 3D crystal structures, pin favourites and leave notes for your team. Predictions always show their uncertainty.",
    preview: `<div style="display:flex;gap:8px;align-items:center;">
      <span class="pill stable">Stable</span><span class="pill marginal">Marginal</span><span class="pill unstable">Unstable</span></div>`,
  },
  {
    title: "Build custom pipelines in the Node Editor",
    desc: "Switch to the Node Editor tab to drag units onto a canvas and wire them into fully custom pipelines, no separate page, and your work can be saved and reloaded.",
    preview: `<div style="display:flex;align-items:center;gap:10px;">
      <span style="padding:7px 12px;background:var(--white);border:1px solid var(--border-medium);border-top:3px solid var(--cat-database);border-radius:var(--radius-card);font-size:12px;font-weight:600;">COD</span>
      <span style="color:var(--text-muted);font-size:15px;">→</span>
      <span style="padding:7px 12px;background:var(--white);border:1px solid var(--border-medium);border-top:3px solid var(--cat-predictor);border-radius:var(--radius-card);font-size:12px;font-weight:600;">MatterSim</span></div>`,
  },
  {
    title: "Help is one click away",
    desc: "Click the ? beside any unit or feature for a plain-English description, open the Documentation page from the nav bar, or ask the assistant in the bottom corner at any time.",
    preview: `<div style="display:flex;align-items:center;gap:16px;">
      <span style="width:22px;height:22px;border-radius:50%;border:1px solid var(--border-medium);display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:var(--text-secondary);">?</span>
      <span style="width:36px;height:36px;border-radius:50%;background:var(--accent);display:inline-flex;align-items:center;justify-content:center;color:#fff;">
        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="8" width="16" height="11" rx="3"/><path d="M12 8V4"/><circle cx="12" cy="3" r="1.2" fill="currentColor" stroke="none"/><circle cx="9" cy="13" r="1.1" fill="currentColor" stroke="none"/><circle cx="15" cy="13" r="1.1" fill="currentColor" stroke="none"/><path d="M2 12v3M22 12v3"/></svg>
      </span></div>`,
  },
];

/* ============================================================
   Feature importance (Citrine "why" panel) — per feature.
   Each entry: which input drove the prediction, relative weight,
   and direction (+ raises the score, - lowers it).
   ============================================================ */
const DRIVERS = {
  db_extract: [
    { name: "Energy above hull", weight: 0.34, dir: "-" },
    { name: "Band gap minimum",  weight: 0.27, dir: "+" },
    { name: "Source coverage",   weight: 0.19, dir: "+" },
    { name: "Required elements", weight: 0.12, dir: "+" },
    { name: "Crystal system",    weight: 0.08, dir: "+" },
  ],
  stability: [
    { name: "MatterSim e-hull",   weight: 0.41, dir: "-" },
    { name: "Model agreement",    weight: 0.28, dir: "+" },
    { name: "SynthNN synthesis",  weight: 0.18, dir: "+" },
    { name: "Ensemble members",   weight: 0.13, dir: "+" },
  ],
  amd: [
    { name: "Min interatomic dist", weight: 0.38, dir: "+" },
    { name: "k neighbours",         weight: 0.26, dir: "+" },
    { name: "Distance cutoff",      weight: 0.21, dir: "-" },
    { name: "Fingerprint overlap",  weight: 0.15, dir: "-" },
  ],
  mosfet: [
    { name: "Carrier mobility",  weight: 0.36, dir: "+" },
    { name: "Gate voltage",      weight: 0.24, dir: "+" },
    { name: "Channel length",    weight: 0.22, dir: "-" },
    { name: "Doping density",    weight: 0.18, dir: "+" },
  ],
};
