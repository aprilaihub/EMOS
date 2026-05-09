# Database Extractor Input Case Studies

Practical example input payloads for electronics-focused database extraction workflows.

All examples below are informed by the current database property mappings in
`Information_Units/property_mappings/sources/databases/*.json`.

## 1. Wide-Bandgap Materials for Power Electronics

Use this when screening wide-bandgap candidates across AFLOW and JARVIS with strict compatibility.

```json
{
  "batchSize": 100,
  "retrievalMode": "strict",
  "targetCompositions": "Ga-N,Si-C,Al-N",
  "queryValues": {
    "band_gap": [2.5, 5.5],
    "density": [2.0, 8.0],
    "bulk_modulus": [100, 350],
    "nelements": [2, 3]
  },
  "active_databases": [
    { "value": "aflow", "name": "AFLOW" },
    { "value": "jarvisdft", "name": "JARVIS-DFT" }
  ]
}
```

## 2. Low Effective-Mass Semiconductors for High-Mobility Transistors

Use this when searching channel materials with effective-mass filters (JARVIS supports these directly).

```json
{
  "batchSize": 80,
  "retrievalMode": "strict",
  "targetCompositions": "In-Ga-As,Ga-As,In-P",
  "queryValues": {
    "band_gap": [0.8, 2.2],
    "avg_elec_mass": [0.05, 0.5],
    "avg_hole_mass": [0.05, 0.8],
    "hull_distance": [0.0, 0.1]
  },
  "active_databases": [
    { "value": "jarvisdft", "name": "JARVIS-DFT" }
  ]
}
```

## 3. Thermally Robust Substrate and Packaging Materials

Use this for broad thermal and mechanical screening where databases may not share all keys.

```json
{
  "batchSize": 120,
  "retrievalMode": "lenient",
  "targetCompositions": "Al-N,Si-C,Be-O,Al2O3",
  "queryValues": {
    "thermal_conductivity_300_k": [50, 500],
    "bulk_modulus": [120, 400],
    "band_gap": [3.0, 8.0],
    "density": [2.0, 7.0]
  },
  "active_databases": [
    { "value": "aflow", "name": "AFLOW" },
    { "value": "jarvisdft", "name": "JARVIS-DFT" },
    { "value": "mathub3d", "name": "MatHub3D" }
  ]
}
```

## 4. 2D Electronic Materials for Ultrathin Devices

Use this when targeting 2D-like semiconducting candidates with strict shared filters.

```json
{
  "batchSize": 60,
  "retrievalMode": "strict",
  "targetCompositions": "Mo-S,W-S,Mo-Se,W-Se",
  "queryValues": {
    "band_gap": [1.0, 2.5],
    "density": [3.0, 9.0],
    "bulk_modulus": [20, 250],
    "nelements": [2, 3]
  },
  "active_databases": [
    { "value": "jarvisdft", "name": "JARVIS-DFT" },
    { "value": "mathub3d", "name": "MatHub3D" }
  ]
}
```

## 5. High-k Dielectric Candidates for Gate Oxides

Use this for dielectric-related exploration with one strict-safe core and one advanced database-specific key.

```json
{
  "batchSize": 90,
  "retrievalMode": "lenient",
  "targetCompositions": "Hf-O,Zr-O,La-Al-O",
  "queryValues": {
    "band_gap": [4.0, 9.0],
    "density": [4.0, 12.0],
    "epsx": [5, 60]
  },
  "active_databases": [
    { "value": "jarvisdft", "name": "JARVIS-DFT" },
    { "value": "aflow", "name": "AFLOW" },
    { "value": "alexandria", "name": "Alexandria" }
  ]
}
```

## Quick Usage Guidance

- Start with `lenient` mode for broad exploration.
- Switch to `strict` mode for cleaner cross-database comparison where all filters must be queryable.
- Keep `batchSize` moderate first (for example 50-100), then increase once filters are validated.
- If strict mode skips databases, reduce filters to the intersection of retrievable keys for that database set.
