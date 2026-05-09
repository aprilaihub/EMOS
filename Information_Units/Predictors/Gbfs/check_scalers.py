import joblib
from pathlib import Path

print('Scaler Diagnostics')
print('=' * 80)

for prop in ['bandgap', 'e_form', 'dielectric', 'is_metal']:
    scaler_path = Path('Information_Units/Predictors/Gbfs') / prop / f'{prop}_scaler.pkl'
    scaler = joblib.load(scaler_path)
    print(f'\n{prop}: {type(scaler).__name__}')
