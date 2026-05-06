import warnings
warnings.filterwarnings('ignore')
from pathlib import Path
import json
import joblib

bandgap_dir = Path('Information_Units/Predictors/Gbfs')

print('=' * 80)
print('Feature Diagnostics')
print('=' * 80)

for prop in ['bandgap', 'e_form', 'dielectric', 'is_metal']:
    features_path = bandgap_dir / prop / f'{prop}_features.pkl'
    features_data = joblib.load(features_path)
    
    if isinstance(features_data, __import__('pandas').DataFrame):
        feature_list = features_data['feature'].tolist()
    else:
        try:
            feature_list = list(features_data)
        except:
            feature_list = features_data.tolist() if hasattr(features_data, 'tolist') else list(features_data)
    
    base_features = [f for f in feature_list if '/' not in f]
    eng_features = [f for f in feature_list if '/' in f]
    
    print(f'\n{prop.upper()}')
    print(f'{"-" * 80}')
    print(f'Total features: {len(feature_list)}')
    print(f'Base features: {len(base_features)}')
    print(f'Engineered features: {len(eng_features)}')
    
    if eng_features:
        print(f'\nEngineered features:')
        for ef in eng_features:
            print(f'  - {ef}')
    
    # Check for special features
    special_props = ['LUMO', 'HOMO', 'gap', 'energy', 'electronic', 'ionic']
    special = [f for f in base_features if any(sp.lower() in f.lower() for sp in special_props)]
    if special:
        print(f'\nSpecial/Computed features:')
        for s in special[:10]:  # Show first 10
            print(f'  - {s}')
        if len(special) > 10:
            print(f'  ... and {len(special) - 10} more')
