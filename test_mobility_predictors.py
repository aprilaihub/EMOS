"""
Test mob_n (electron mobility) and mob_p (hole mobility) predictors
with log10 inverse transformation on 3 CIF files
"""

import json
import math
from pathlib import Path
from Information_Units.Predictors.GBFS_Pred.GBFS_PredPredictor import GBFS_PredPredictor, load_cif

# Setup paths
FIXTURES_DIR = Path(__file__).parent / "tests" / "fixtures" / "cif_files"
CIF_FILES = {
    "Al2O3": FIXTURES_DIR / "Al2O3.cif",
    "CsDy(WO4)2": FIXTURES_DIR / "CsDy(WO4)2.cif",
    "SiO2": FIXTURES_DIR / "SiO2.cif",
}

MOBILITY_PROPERTIES = ["mob_n", "mob_p"]
UNITS = {
    "mob_n": "cm²/V·s",
    "mob_p": "cm²/V·s",
}

print("=" * 90)
print("Testing Mobility Predictors with Log10 Inverse Transformation")
print("=" * 90)

# Load mobility predictors
print("\nLoading mobility predictors...")
predictors = {}
for prop in MOBILITY_PROPERTIES:
    try:
        predictor = GBFS_PredPredictor("test", property_name=prop)
        print(f"  OK {prop:10} - {len(predictor.feature_list)} features, "
              f"Model: {type(predictor.model).__name__}, "
              f"Scaler: {type(predictor.scaler).__name__}")
        predictors[prop] = predictor
    except Exception as e:
        print(f"  FAILED {prop:10} - {str(e)}")
        exit(1)

# Test on each CIF file
print(f"\n{'='*90}")
print("Testing on CIF Files with Log10 Inverse Transformation")
print(f"{'='*90}\n")

results = {}
for cif_name, cif_path in CIF_FILES.items():
    try:
        # Verify file exists
        if not cif_path.exists():
            print(f"\n{cif_name}: SKIPPED (file not found)")
            continue
        
        # Load structure info
        structure = load_cif(str(cif_path))
        formula = structure.composition.formula
        
        print(f"\n{cif_name}:")
        print(f"  Formula: {formula}")
        print(f"  Atoms: {len(structure)}")
        
        results[cif_name] = {}
        
        # Test each mobility predictor
        for prop in MOBILITY_PROPERTIES:
            try:
                result_json = predictors[prop].predict(str(cif_path))
                parsed = json.loads(result_json)
                
                # Extract prediction (already inverse log10 transformed)
                mobility_value = parsed["prediction"][0]
                results[cif_name][prop] = mobility_value
                
                unit = UNITS[prop]
                
                # Format scientific notation for mobility values
                if mobility_value >= 1e6 or (mobility_value > 0 and mobility_value < 0.001):
                    display = f"{mobility_value:.3e}"
                else:
                    display = f"{mobility_value:.6f}"
                
                status = "OK"
                print(f"  {prop:10}: {display:20} {unit:15} [{status}]")
                
            except Exception as e:
                print(f"  {prop:10}: ERROR - {str(e)[:50]}")
                results[cif_name][prop] = None
    
    except Exception as e:
        print(f"{cif_name}: FAILED - {str(e)}")

# Summary statistics
print(f"\n{'='*90}")
print("Summary Statistics (after log10 inverse transformation)")
print(f"{'='*90}\n")

summary_data = []
for prop in MOBILITY_PROPERTIES:
    values = [results[cif][prop] for cif in CIF_FILES 
              if results[cif].get(prop) is not None]
    
    if values:
        min_val = min(values)
        max_val = max(values)
        mean_val = sum(values) / len(values)
        
        if max_val >= 1e6 or (max_val > 0 and min_val < 0.001):
            min_str = f"{min_val:.3e}"
            max_str = f"{max_val:.3e}"
            mean_str = f"{mean_val:.3e}"
        else:
            min_str = f"{min_val:.6f}"
            max_str = f"{max_val:.6f}"
            mean_str = f"{mean_val:.6f}"
        
        summary_data.append([
            prop,
            mean_str,
            f"[{min_str}, {max_str}]",
            f"{len(values)}/3",
            UNITS[prop]
        ])
    else:
        summary_data.append([prop, "FAILED", "---", "0/3", UNITS[prop]])

print("Property    Mean                  Range                           Success    Unit")
print("-" * 90)
for row in summary_data:
    print(f"{row[0]:10} {row[1]:20} {row[2]:30} {row[3]:10} {row[4]}")

# Detailed results
print(f"\n{'='*90}")
print("Detailed Results (Actual Mobility Values - after log10 inverse transformation)")
print(f"{'='*90}\n")

for cif_name in CIF_FILES:
    print(f"{cif_name}:")
    for prop in MOBILITY_PROPERTIES:
        value = results[cif_name].get(prop)
        if value is not None:
            if value >= 1e6 or (value > 0 and value < 0.001):
                display = f"{value:.3e}"
            else:
                display = f"{value:.6f}"
            print(f"  {prop:10}: {display:20} {UNITS[prop]}")
        else:
            print(f"  {prop:10}: FAILED")
    print()

print(f"{'='*90}")
print("Test Complete")
print(f"{'='*90}\n")
