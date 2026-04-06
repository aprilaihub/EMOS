# AMD (Average Minimum Distance) Predictor

Crystal structure similarity comparison using geometric descriptors.

## Overview

The AMD Predictor uses the **average-minimum-distance** package to compare crystal structures and determine their similarity based on geometric properties. It computes both:

- **PDD/EMD** (Pointwise Distance Distribution / Earth Mover's Distance) - compares full atomic environment distributions
- **AMD** (Average Minimum Distance) - simplified vector-based comparison metric

## Features

- Compares two or more crystal structures from CIF files
- Uses geometric descriptors independent of unit cell representation
- Returns similarity metrics as JSON dictionaries
- Configurable k parameter (neighborhood size) for descriptor calculation
- Multiple distance metric options (chebyshev, euclidean, etc.)
- Handles multiple crystals per CIF file
- Deterministic and reproducible results

## Installation

The AMD predictor requires the `average-minimum-distance` package:

```bash
pip install average-minimum-distance
```

This is already specified in `requirements.txt`.

## Usage

### Basic Usage

```python
from Information_Units.Predictors.AMD.AMDPredictor import AMDPredictor

# Create predictor
predictor = AMDPredictor(predictor_name="my_amd", k=100, metric="chebyshev")

# Compare two structures
inputs = {'cif_paths': ['structure1.cif', 'structure2.cif']}
result_json = predictor.predict(inputs)

# Parse result
import json
result = json.loads(result_json)
```

### Advanced Usage

```python
# Get results as dictionary instead of JSON
result = predictor.predict_numpy(inputs)

# Access similarity information
for comparison in result['pairwise_distances']:
    print(f"PDD/EMD distance: {comparison['pdd_emd_distance']}")
    print(f"AMD distance: {comparison['amd_distance']}")
    print(f"Identical? {comparison['identical']}")
    print(f"Very similar? {comparison['very_similar']}")
```

## Parameters

- `k` (int): Number of neighboring atoms to consider in PDD/AMD calculation. Default: 100
  - Smaller k: Looks at local environment only
  - Larger k: Captures broader structural features
  - Recommendation: Use k≥100 for most applications, or higher than number of atoms in unit cell

- `metric` (str): Distance metric for AMD comparison. Default: "chebyshev"
  - "chebyshev" (L-infinity): Maximum coordinate distance
  - "euclidean": Euclidean distance  
  - Other scipy.spatial.distance metrics supported

## Input Formats

The predictor accepts flexible input formats:

```python
# Format 1: String path (needs at least 2 files via list wrapping)
inputs = ['/path/to/file1.cif', '/path/to/file2.cif']

# Format 2: Dictionary with cif_paths
inputs = {'cif_paths': ['/path/to/file1.cif', '/path/to/file2.cif']}

# Format 3: Dictionary with cif_path1 and cif_path2
inputs = {'cif_path1': '/path/to/file1.cif', 'cif_path2': '/path/to/file2.cif'}

# Format 4: Nested input_data
inputs = {'input_data': {'cif_paths': ['/path/to/file1.cif', '/path/to/file2.cif']}}
```

**Important**: At least 2 CIF files (or 2 crystal structures across files) are required for comparison.

## Output Format

### Successful Prediction

```json
{
  "pairwise_distances": [
    {
      "crystal_1_index": 0,
      "crystal_2_index": 1,
      "crystal_1_file": "file1.cif",
      "crystal_2_file": "file2.cif",
      "pdd_emd_distance": 0.15,
      "amd_distance": 0.08,
      "identical": false,
      "very_similar": false,
      "similar": true
    }
  ],
  "crystal_info": [
    {
      "name": "Al2O3",
      "n_atoms": 10,
      "n_asym": 2,
      "composition": "Al4O6"
    },
    {
      "name": "SiO2",
      "n_atoms": 12,
      "n_asym": 2,
      "composition": "Si4O8"
    }
  ],
  "parameters": {
    "k": 100,
    "metric": "chebyshev",
    "n_crystals": 2,
    "n_files": 2
  },
  "n_comparisons": 1
}
```

### Error Handling

```json
{
  "error": "No crystal structures found in file",
  "predictor": "my_amd",
  "status": "failed"
}
```

## Similarity Thresholds

The predictor sets similarity flags based on PDD/EMD distance:

- `identical`: pdd_emd_distance < 1e-6 (essentially 0)
- `very_similar`: pdd_emd_distance < 0.1
- `similar`: pdd_emd_distance < 0.5

For different crystal structures (different materials), expect:
- PDD/EMD distances: 0.1 - several units
- AMD distances: 0.01 - several units

## Interpretation

### Distance Meaning

- **Distance ≈ 0**: Identical or nearly identical crystals (same geometry)
- **Distance 0.01-0.1**: Very similar crystal structures
- **Distance 0.1-0.5**: Similar crystal types with some structural differences
- **Distance > 0.5**: Quite different crystal structures

### Why Two Metrics?

- **PDD/EMD**: More comprehensive, considers full neighbor shells. Slower computation.
- **AMD**: Simplified vector metric, faster comparison. Good for screening.

## Examples

### Compare identical structures
```python
inputs = {'cif_paths': ['Al2O3.cif', 'Al2O3.cif']}
result = json.loads(predictor.predict(inputs))
# Expected: pdd_emd_distance < 0.01, identical=True
```

### Compare different materials
```python
inputs = {'cif_paths': ['Al2O3.cif', 'SiO2.cif']}
result = json.loads(predictor.predict(inputs))
# Expected: pdd_emd_distance > 0.1, identical=False
```

### Compare ZnO wurtzite polymorphs
```python
# Real-world example: Two wurtzite ZnO structures with different lattice parameters
# mp-2133.cif: a=3.237 Å, c=5.222 Å (hexagonal)
# mp-1017539.cif: a=3.205 Å, c=5.517 Å (hexagonal)

inputs = {'cif_paths': ['mp-2133.cif', 'mp-1017539.cif']}
result = json.loads(predictor.predict(inputs))

# Output:
# pdd_emd_distance: 0.8078
# amd_distance: 0.8078
# identical: False
# very_similar: False
# similar: False

# Interpretation: Both are ZnO materials, but structural differences are significant
# (different lattice parameters) so they are correctly identified as not identical.
# This demonstrates the predictor can distinguish between structurally similar but
# non-identical materials of the same composition.
```

### Multiple structures in one file
```python
# If a CIF file contains multiple structures, they are all compared
inputs = {'cif_paths': ['multi_structure.cif', 'other.cif']}
# Result includes all pairwise comparisons
```

## Docker Deployment

The AMD predictor is containerized as a production-ready FastAPI service with full HTTP API support.

### Quick Start with Docker Compose

```bash
cd Information_Units/Predictors/AMD/docker
docker-compose build
docker-compose up
```

The API will be available at `http://localhost:8001`

### API Endpoints

- **POST /predict** - Compare crystal structures
- **GET /health** - Health check
- **GET /info** - Service information
- **GET /docs** - Interactive API documentation (Swagger UI)

### Example API Request

```bash
curl -X POST http://localhost:8001/predict \
  -H "Content-Type: application/json" \
  -d '{
    "cif_paths": ["structure1.cif", "structure2.cif"],
    "k": 100,
    "metric": "chebyshev"
  }'
```

### Python Client Example

```python
import requests

response = requests.post(
    "http://localhost:8001/predict",
    json={
        "cif_paths": ["structure1.cif", "structure2.cif"],
        "k": 100
    }
)

result = response.json()
for comparison in result["pairwise_distances"]:
    print(f"Distance: {comparison['pdd_emd_distance']:.4f}")
```

For comprehensive Docker documentation, see [docker/DOCKER.md](docker/DOCKER.md).

## Testing

Unit tests (35 tests):
```bash
pytest tests/unit/test_amd_behaviour.py -v
```

Integration tests (25 tests):
```bash
pytest tests/integration/test_amd_sanity.py -v
```

Test coverage includes:
- Initialization and configuration
- CIF file handling and validation
- Distance calculation accuracy
- Multiple input formats
- Error handling
- Deterministic behavior
- Parameter sensitivity

## References

- **Package**: [average-minimum-distance on GitHub](https://github.com/dwiddo/average-minimum-distance)
- **Documentation**: [average-minimum-distance ReadTheDocs](https://average-minimum-distance.readthedocs.io)
- **Papers**:
  - Average minimum distances of periodic point sets (MATCH 2022)
  - Resolving the data ambiguity for periodic crystals (NeurIPS 2022)

## Troubleshooting

### "module 'amd' has no attribute..."
- Ensure `average-minimum-distance` is installed: `pip install average-minimum-distance --upgrade`
- Restart Python kernel if upgrading

### "No crystal structures found in CIF file"
- Check that the CIF file is valid and contains complete structure information
- Ensure the file is not corrupted or empty

### Very similar structures have distance > 0.1
- Try increasing k parameter to capture more atomic shells
- Different cell choices for the same crystal can appear more different with small k

### Comparison takes a long time
- Reduce k parameter (smaller neighborhood) to speed up calculation
- Use AMD_pdist instead of full pairwise if many structures

## Integration with EMOS Platform

The AMD predictor is registered in the PredictorFactory as:
```python
from Information_Units.Predictors.PredictorFactory import predictor_factory
amd_class = predictor_factory['amd']
predictor = amd_class(predictor_name="amd_analysis", k=100)
```
