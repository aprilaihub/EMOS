"""
Diagnostic script to check mob_n features
"""

from pathlib import Path
from Information_Units.Predictors.Gbfs.GbfsPredictor import GbfsPredictor

print("Checking mob_n features...")
try:
    predictor = GbfsPredictor("test", property_name="mob_n")
    print(f"\nmob_n predictor loaded successfully")
    print(f"Total features: {len(predictor.feature_list)}")
    print(f"\nFirst 20 features:")
    for i, feat in enumerate(predictor.feature_list[:20]):
        print(f"  {i+1:3}. {feat}")
    
    print(f"\nFeatures containing 'avg':")
    avg_features = [f for f in predictor.feature_list if 'avg' in f.lower()]
    for feat in avg_features:
        print(f"  - {feat}")
    
    print(f"\nLast 20 features:")
    for i, feat in enumerate(predictor.feature_list[-20:], len(predictor.feature_list)-19):
        print(f"  {i:3}. {feat}")
        
except Exception as e:
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc()
