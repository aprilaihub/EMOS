# Stability Consensus Analysis

## Overview

The Stability Consensus Analysis feature queries multiple crystal structure databases and runs ML force-field predictors to evaluate the thermodynamic stability of a given crystal structure. Results are displayed with **✅ green ticks** (stable) and **❌ red crosses** (unstable) for each source, allowing users to interpret the multi-source consensus themselves.

## Architecture

### Input
- **CIF File**: Single crystal structure in CIF format
- **Databases**: Select which databases to query (Materials Project, Alexandria, COD, etc.)
- **Predictors**: Select which predictors to run (MatterSim, CHGNet)

### Processing Pipeline

```
1. Parse CIF file → Extract composition
   ↓
2. Query Databases (parallel)
   - Materials Project: energy_above_hull_r2scan < 0.05 eV/atom → ✅
   - Alexandria: hull_distance < 0.05 eV/atom → ✅
   ↓
3. Run Predictors (parallel)
   - MatterSim: relax structure, extract max force
   - CHGNet: relax structure, extract max force
   - Criterion: max_relaxed_force < 0.05 eV/Å → ✅
   ↓
4. Compute Consensus Summary
   - Count: X stable, Y unstable
   - Overall verdict: All agree / Mixed opinion
   ↓
5. Generate Downloadable JSON Report
```

### Output

**Results Table** with per-source assessments:

| Source | Stability | Raw Value | Threshold | Unit | Description |
|--------|-----------|-----------|-----------|------|-------------|
| Materials Project | ✅ Stable | 0.02 | 0.05 | eV/atom | Formation energy above convex hull |
| Alexandria | ✅ Stable | 0.01 | 0.05 | eV/atom | Distance to convex hull |
| MatterSim | ❌ Unstable | 0.08 | 0.05 | eV/Å | Maximum relaxed force |
| CHGNet | ❌ Unstable | 0.12 | 0.05 | eV/Å | Maximum relaxed force |

**Consensus Summary**:
- Overall Consensus: ⚠️ Mixed opinion: 2 stable, 2 unstable
- Downloadable JSON with full details

## Stability Thresholds

### Database Sources
- **Materials Project**: `energy_above_hull_r2scan < 0.05 eV/atom`
- **Alexandria**: `hull_distance < 0.05 eV/atom`
- Others: Similar hull-distance based criteria

### Predictor Sources (Local Minimum Evaluation)
- **MatterSim**: `max_relaxed_force < 0.05 eV/Å`
- **CHGNet**: `max_relaxed_force < 0.05 eV/Å`
- Rationale: Low forces after relaxation indicate a local minimum; high forces suggest an unstable/saddle-point configuration

## Implementation Details

### Backend (`StabilityConsensusAnalysisFeature.py`)
- **`process_feature()`**: Main orchestration pipeline
- **`_query_databases()`**: Query selected databases in sequence
- **`_evaluate_database_stability()`**: Convert hull distance to ✅/❌
- **`_run_predictors_parallel()`**: Execute predictors (ready for concurrent HTTP calls)
- **`_evaluate_predictor_stability()`**: Extract max force and evaluate threshold
- **`_compute_consensus_summary()`**: Aggregate votes across sources
- **`format_outputs()`**: Serialize results to JSON for download

### Frontend (`StabilityConsensusAnalysis.js`)
- **File upload**: Accept single CIF file with progress logging
- **Database/Predictor selection**: Checkboxes for source configuration
- **Results display**: Color-coded table (green rows = stable, red rows = unstable)
- **JSON download**: Download full report for external analysis

## Tests

### Unit Tests (`tests/unit/test_stability_consensus_analysis.py`)
- 20+ assertions covering:
  - Stability threshold evaluation (database & predictor)
  - Consensus summary computation
  - Error handling (missing metrics, no results, invalid CIF)
  - Input extraction and defaults

### Integration Tests (`tests/integration/test_stability_consensus_analysis.py`)
- Full pipeline orchestration
- Database query mocking
- Multi-source consensus aggregation
- Output formatting validation

## Running Tests

**Unit tests** (no external dependencies):
```bash
cd /mnt/c/Users/smishra2/Desktop/EMOS
conda run -n mattersim python -m pytest tests/unit/test_stability_consensus_analysis.py -v
```

**Integration tests** (optional; uses mocks):
```bash
conda run -n mattersim python -m pytest tests/integration/test_stability_consensus_analysis.py -v
```

## Future Enhancements

1. **Composition-based queries**: Accept "Li2O" string; extract matching structures from databases
2. **Parallel predictor execution**: Use `asyncio` or thread pool for concurrent HTTP calls to MatterSim + CHGNet
3. **Customizable thresholds**: UI sliders to adjust stability criteria per source
4. **Weighted consensus**: User-defined weights for each source (e.g., trust databases more than predictors)
5. **Batch processing**: Accept multiple CIF files for high-throughput screening
6. **Comparison mode**: Show how predictor energies compare to database hull distances

Analyze and aggregate stability consensus from uploaded CIF structures

## Overview

This feature provides stability consensus analysis functionality within the EMOS platform.

## Key Methods

- `info()`: Returns feature description and capabilities
- `extract_inputs(input_data)`: Extracts and validates input parameters
- `process_feature(inputs)`: Core feature processing logic
- `format_outputs(results)`: Formats results to expected output format


## Input Parameters

- **CIF Files**: Browse and upload one or more CIF files for stability consensus analysis

## Output Parameters

- **Download Results (JSON)**: Download JSON file containing stability consensus analysis results

## Usage

See the base class documentation for detailed usage instructions.

This feature exposes its compatible databases and predictors in its own input
panel and processes only those local selections.
