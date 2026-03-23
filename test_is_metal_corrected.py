"""
Test is_metal predictor with corrected scaler on 3 CIF files
"""

import json
from pathlib import Path
from Information_Units.Predictors.GBFS_Pred.GBFS_PredPredictor import GBFS_PredPredictor, load_cif

# Setup paths
FIXTURES_DIR = Path(__file__).parent / "tests" / "fixtures" / "cif_files"
CIF_FILES = {
    "Al2O3": FIXTURES_DIR / "Al2O3.cif",
    "CsDy(WO4)2": FIXTURES_DIR / "CsDy(WO4)2.cif",
    "SiO2": FIXTURES_DIR / "SiO2.cif",
}

print("=" * 80)
print("Testing is_metal Predictor with Corrected Scaler")
print("=" * 80)

# Load is_metal predictor
print("\nLoading is_metal predictor...")
try:
    metal_predictor = GBFS_PredPredictor("test", property_name="is_metal")
    print(f"OK - Loaded with {len(metal_predictor.feature_list)} features")
    print(f"Model type: {type(metal_predictor.model).__name__}")
    print(f"Scaler type: {type(metal_predictor.scaler).__name__}")
except Exception as e:
    print(f"FAILED - {str(e)}")
    exit(1)

# Test on each CIF file
print(f"\n{'='*80}")
print("Testing on CIF Files")
print(f"{'='*80}\n")

for cif_name, cif_path in CIF_FILES.items():
    try:
        # Verify file exists
        if not cif_path.exists():
            print(f"\n{cif_name}: SKIPPED (file not found)")
            continue
        
        # Load structure info
        structure = load_cif(str(cif_path))
        formula = structure.composition.formula
        
        # Make prediction
        result_json = metal_predictor.predict(str(cif_path))
        parsed = json.loads(result_json)
        
        prediction = parsed["prediction"][0]
        probs = parsed.get("probabilities", [[0, 1]])[0]
        
        print(f"\n{cif_name}:")
        print(f"  Formula: {formula}")
        print(f"  Atoms: {len(structure)}")
        print(f"  Prediction: {prediction}")
        print(f"  Probabilities: Not Metal={probs[0]:.4f}, Metal={probs[1]:.4f}")
        print(f"  Confidence: {max(probs)*100:.1f}%")
        print(f"  Status: OK")
        
    except Exception as e:
        print(f"\n{cif_name}: FAILED")
        print(f"  Error: {str(e)}")

print(f"\n{'='*80}")
print("Testing Complete")
print(f"{'='*80}\n")
