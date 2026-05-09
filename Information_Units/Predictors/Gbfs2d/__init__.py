"""
Initialize placeholder model files for Gbfs-2d predictor.
This creates dummy models that can be replaced with real trained models.
"""

import os
import joblib
import numpy as np
from sklearn.preprocessing import StandardScaler
from lightgbm import LGBMRegressor, LGBMClassifier

def create_placeholder_models():
    """Create placeholder model files for bandgap, is_metal, and is_stable properties."""
    
    base_dir = os.path.dirname(__file__)
    properties = {
        'bandgap': {
            'type': 'regression',
            'n_features': 117,  # Example number of features
            'model_class': LGBMRegressor
        },
        'is_metal': {
            'type': 'classifier',
            'n_features': 117,
            'model_class': LGBMClassifier
        },
        'is_stable': {
            'type': 'classifier',
            'n_features': 117,
            'model_class': LGBMClassifier
        }
    }
    
    for prop, config in properties.items():
        prop_dir = os.path.join(base_dir, f"{prop}_2d")
        os.makedirs(prop_dir, exist_ok=True)
        
        n_features = config['n_features']
        
        # Create feature list with _2d suffix
        features = [f"feature_{i}" for i in range(n_features)]
        features_path = os.path.join(prop_dir, f"{prop}_2d_features.pkl")
        joblib.dump(features, features_path)
        print(f"Created {features_path}")
        
        # Create dummy scaler
        scaler = StandardScaler()
        # Fit with dummy data
        dummy_data = np.random.randn(10, n_features)
        scaler.fit(dummy_data)
        scaler_path = os.path.join(prop_dir, f"{prop}_2d_scaler.pkl")
        joblib.dump(scaler, scaler_path)
        print(f"Created {scaler_path}")
        
        # Create dummy model
        if config['type'] == 'regression':
            model = LGBMRegressor(n_estimators=10, random_state=42, verbose=-1)
            # Fit with dummy data
            dummy_y = np.random.randn(10)
        else:  # classifier
            model = LGBMClassifier(n_estimators=10, random_state=42, verbose=-1)
            # Fit with dummy data
            dummy_y = np.random.randint(0, 2, 10)
        
        model.fit(dummy_data, dummy_y)
        model_path = os.path.join(prop_dir, f"{prop}_2d_model.pkl")
        joblib.dump(model, model_path)
        print(f"Created {model_path}")
    
    print("\nPlaceholder models created successfully!")
    print("These are dummy models for testing. Replace with real trained models.")

if __name__ == "__main__":
    create_placeholder_models()
