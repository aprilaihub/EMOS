"""
Comprehensive test of all 4 GBFS predictors on 3 CIF files
"""

import json
import numpy as np
from pathlib import Path
from tabulate import tabulate

from Information_Units.Predictors.GBFS_Pred.GBFS_PredPredictor import GBFS_PredPredictor, load_cif

# Setup paths
FIXTURES_DIR = Path(__file__).parent / "tests" / "fixtures" / "cif_files"
CIF_FILES = {
    "Al2O3": FIXTURES_DIR / "Al2O3.cif",
    "CsDy(WO4)2": FIXTURES_DIR / "CsDy(WO4)2.cif",
    "SiO2": FIXTURES_DIR / "SiO2.cif",
}

PROPERTIES = ["bandgap", "e_form", "dielectric", "is_metal"]
UNITS = {
    "bandgap": "eV",
    "e_form": "eV/atom",
    "dielectric": "dimensionless",
    "is_metal": "classification"
}

def format_prediction(result_json, property_name):
    """Parse JSON result and format prediction with units."""
    try:
        parsed = json.loads(result_json)
        prediction = parsed["prediction"][0]
        
        # For classifier, also show probabilities if available
        if property_name == "is_metal":
            if "probabilities" in parsed:
                probs = parsed["probabilities"][0]
                return f"{prediction} ({probs[1]*100:.1f}% confidence)"
            return str(prediction)
        else:
            return f"{prediction:.6f}"
    except Exception as e:
        return f"ERROR: {str(e)}"

def test_all_predictors():
    """Test all predictors on all CIF files."""
    print("=" * 100)
    print("GBFS PREDICTOR COMPREHENSIVE TEST")
    print("=" * 100)
    
    # Verify CIF files exist
    print("\nChecking CIF files...")
    missing_files = []
    for name, path in CIF_FILES.items():
        if path.exists():
            print(f"  OK {name:20} {path}")
        else:
            print(f"  MISSING {name:20} NOT FOUND: {path}")
            missing_files.append(name)
    
    if missing_files:
        print(f"\nWarning: Missing CIF files: {', '.join(missing_files)}")
        return False
    
    # Load predictors
    print("\nLoading predictors...")
    predictors = {}
    for prop in PROPERTIES:
        try:
            predictor = GBFS_PredPredictor("test", property_name=prop)
            predictor_type = "Regressor" if prop != "is_metal" else "Classifier"
            print(f"  OK {prop:15} ({predictor_type:10}) - {len(predictor.feature_list)} features")
            predictors[prop] = predictor
        except Exception as e:
            print(f"  FAILED {prop:15} FAILED: {str(e)}")
            return False
    
    # Run predictions
    print("\nRunning predictions...\n")
    
    results = {}
    for cif_name, cif_path in CIF_FILES.items():
        print(f"\n{'='*100}")
        print(f"Testing on: {cif_name}")
        print(f"{'='*100}")
        
        # Load structure info
        try:
            structure = load_cif(str(cif_path))
            formula = structure.composition.formula
            print(f"Formula: {formula}")
            print(f"Atoms: {len(structure)}")
        except Exception as e:
            print(f"Error loading structure: {e}")
            continue
        
        results[cif_name] = {}
        
        # Test each predictor
        table_data = []
        for prop in PROPERTIES:
            try:
                predictor = predictors[prop]
                result_json = predictor.predict(str(cif_path))
                
                # Extract prediction value
                parsed = json.loads(result_json)
                prediction = parsed["prediction"][0]
                
                # Store as string for classifiers, value for regressors
                if prop == "is_metal":
                    results[cif_name][prop] = str(prediction)
                else:
                    results[cif_name][prop] = prediction
                
                # Format for display
                if prop == "is_metal":
                    if "probabilities" in parsed:
                        probs = parsed["probabilities"][0]
                        display = f"{prediction} ({probs[1]*100:.1f}% confidence)"
                    else:
                        display = str(prediction)
                else:
                    display = f"{prediction:.6f}"
                
                unit = UNITS[prop]
                table_data.append([prop, display, unit, "OK"])
                
            except Exception as e:
                table_data.append([prop, f"ERROR: {str(e)[:40]}", UNITS[prop], "FAILED"])
                results[cif_name][prop] = None
        
        # Print table
        print(tabulate(
            table_data,
            headers=["Property", "Prediction", "Unit", "Status"],
            tablefmt="grid",
            stralign="left"
        ))
    
    # Summary statistics
    print(f"\n{'='*100}")
    print("SUMMARY STATISTICS")
    print(f"{'='*100}\n")
    
    summary_table = []
    for prop in PROPERTIES:
        values = [results[cif][prop] for cif in CIF_FILES if results[cif].get(prop) is not None]
        if values:
            if prop == "is_metal":
                summary_table.append([prop, f"N/A (Classification)", f"N/A", f"{len(values)}/3"])
            else:
                mean_val = np.mean(values)
                min_val = np.min(values)
                max_val = np.max(values)
                summary_table.append([
                    prop,
                    f"{mean_val:.6f}",
                    f"[{min_val:.6f}, {max_val:.6f}]",
                    f"{len(values)}/3"
                ])
        else:
            summary_table.append([prop, "FAILED", "---", "0/3"])
    
    print(tabulate(
        summary_table,
        headers=["Property", "Mean", "Range", "Successful"],
        tablefmt="grid"
    ))
    
    # Detailed results by CIF
    print(f"\n{'='*100}")
    print("DETAILED RESULTS TABLE")
    print(f"{'='*100}\n")
    
    for cif_name in CIF_FILES:
        print(f"\n{cif_name}:")
        for prop in PROPERTIES:
            value = results[cif_name].get(prop)
            if value is not None:
                print(f"  {prop:15}: {value}")
            else:
                print(f"  {prop:15}: FAILED")
    
    # Export results to JSON
    output_file = Path(__file__).parent / "PREDICTOR_TEST_RESULTS.json"
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": str(Path(__file__).stat().st_mtime),
            "cif_files": list(CIF_FILES.keys()),
            "properties": PROPERTIES,
            "results": results,
            "units": UNITS
        }, f, indent=2, default=str)
    
    print(f"\n{'='*100}")
    print(f"COMPLETED: Results exported to: {output_file}")
    print(f"{'='*100}\n")
    
    return True


if __name__ == "__main__":
    success = test_all_predictors()
    exit(0 if success else 1)
