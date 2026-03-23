import traceback
from Information_Units.Predictors.GBFS_Pred.GBFS_PredPredictor import GBFS_PredPredictor

print('Testing Error Handling\n' + '=' * 80)

# Test 1: Invalid property
print('\n1. Invalid property name:')
try:
    predictor = GBFS_PredPredictor(
        predictor_name='test',
        property_name='invalid_property'
    )
except ValueError as e:
    print(f'✓ Caught ValueError: {str(e)}')
except Exception as e:
    print(f'✗ Unexpected error: {type(e).__name__}: {str(e)}')

# Test 2: Valid property
print('\n2. Valid property (bandgap):')
try:
    predictor = GBFS_PredPredictor(
        predictor_name='test',
        property_name='bandgap'
    )
    print(f'✓ Successfully initialized with {len(predictor.feature_list)} features')
except Exception as e:
    print(f'✗ Error: {str(e)}')

# Test 3: All supported properties
print('\n3. All supported properties:')
for prop in ['bandgap', 'e_form', 'dielectric', 'is_metal']:
    try:
        predictor = GBFS_PredPredictor(
            predictor_name='test',
            property_name=prop
        )
        print(f'✓ {prop:15} - {len(predictor.feature_list)} features')
    except Exception as e:
        print(f'✗ {prop:15} - {str(e)}')

print('\n' + '=' * 80)
print('Error handling test complete')
