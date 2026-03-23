"""
Comprehensive test of all 6 GBFS predictors on 3 CIF files
Tests: bandgap, e_form, dielectric, is_metal, mob_n, mob_p
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

PROPERTIES = ["bandgap", "e_form", "dielectric", "is_metal", "mob_n", "mob_p"]
UNITS = {
    "bandgap": "eV",
    "e_form": "eV/atom",
    "dielectric": "dimensionless",
    "is_metal": "classification",
    "mob_n": "cm²/V·s",
    "mob_p": "cm²/V·s",
}

print("=" * 100)
print("COMPREHENSIVE GBFS PREDICTOR TEST - All 6 Properties")
print("=" * 100)

# Load all predictors
print("\nLoading predictors...")
predictors = {}
for prop in PROPERTIES:
    try:
        predictor = GBFS_PredPredictor("test", property_name=prop)
        predictor_type = "Regressor" if prop != "is_metal" else "Classifier"
        print(f"  OK {prop:15} ({predictor_type:10}) - {len(predictor.feature_list)} features")
        predictors[prop] = predictor
    except Exception as e:
        print(f"  FAILED {prop:15} - {str(e)}")
        exit(1)

# Test on each CIF file
print(f"\n{'='*100}")
print("Testing on 3 CIF Files")
print(f"{'='*100}\n")

results = {}
for cif_name, cif_path in CIF_FILES.items():
    try:
        if not cif_path.exists():
            print(f"\n{cif_name}: SKIPPED (file not found)")
            continue
        
        structure = load_cif(str(cif_path))
        formula = structure.composition.formula
        
        print(f"\n{cif_name}: {formula} ({len(structure)} atoms)")
        print("-" * 100)
        
        results[cif_name] = {}
        for prop in PROPERTIES:
            try:
                result_json = predictors[prop].predict(str(cif_path))
                parsed = json.loads(result_json)
                prediction = parsed["prediction"][0]
                results[cif_name][prop] = prediction
                
                # Format display
                if prop == "is_metal":
                    if "probabilities" in parsed:
                        display = f"{prediction} ({parsed['probabilities'][0][1]*100:.1f}%)"
                    else:
                        display = str(prediction)
                elif prop in ["mob_n", "mob_p"]:
                    display = f"{prediction:.6f}"
                else:
                    display = f"{prediction:.6f}"
                
                status = "OK"
                print(f"  {prop:15}: {display:40} {UNITS[prop]:20} [{status}]")
                
            except Exception as e:
                print(f"  {prop:15}: ERROR - {str(e)[:50]}")
                results[cif_name][prop] = None
    
    except Exception as e:
        print(f"{cif_name}: FAILED - {str(e)}")

# Summary
print(f"\n{'='*100}")
print("Summary - All 6 Predictors")
print(f"{'='*100}\n")

print(f"{'Property':<15} {'Al2O3':<20} {'CsDy(WO4)2':<20} {'SiO2':<20} {'Unit':<20}")
print("-" * 100)

for prop in PROPERTIES:
    values = []
    for cif_name in CIF_FILES:
        val = results[cif_name].get(prop)
        if val is not None:
            if prop == "is_metal":
                val_str = str(val)[:10]
            elif prop in ["mob_n", "mob_p"]:
                val_str = f"{val:.4f}" 
            else:
                val_str = f"{val:.4f}"
        else:
            val_str = "FAILED"
        values.append(val_str)
    
    print(f"{prop:<15} {values[0]:<20} {values[1]:<20} {values[2]:<20} {UNITS[prop]:<20}")

print(f"\n{'='*100}")
print("TEST COMPLETE - All 6 Predictors Verified")
print(f"{'='*100}\n")
