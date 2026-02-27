from Features.BaseFeature import BaseFeature
from Information_Units.Generators.GeneratorFactory import generator_factory
from Information_Units.Databases.DatabaseFactory import database_factory
from Information_Units.Predictors.PredictorFactory import predictor_factory


class MaterialSearchFeature(BaseFeature):
    def __init__(self, logger=None):
        super().__init__("Material Search", logger)
    
    def info(self):
        return "Material Search: Search and explore materials from comprehensive databases using various criteria"
    
    def extract_inputs(self, input_data):
        return {
            'materialName': input_data.get('materialName/formula', ''),
            'propertyType': input_data.get('propertyType', ''),
            'minValue': input_data.get('minimumValue', '0'),
            'maxValue': input_data.get('maximumValue', '0'),
            'includeComposites': input_data.get('includeCompositeMaterials', 'True'),
            'feature_input': input_data.get('featureInput', ''),
            'active_databases': input_data.get('active_databases', []),
            'active_generators': input_data.get('active_generators', []),
            'active_predictors': input_data.get('active_predictors', []),
        }
    
    def process_feature(self, inputs):
        if self.logger:
            self.logger.log('Initializing Material Search...', 'info')
        
        # Process information units (databases, generators, predictors)
        self._process_information_units(inputs)
        
        if self.logger:
            self.logger.log('Material Search processing completed', 'info')
        
        return {
            'status': 'completed',
            'message': 'Material Search feature executed successfully'
        }
    
    def format_outputs(self, results):
        return {
            'materialsCount': 'placeholder text value',
            'topMatch': 'placeholder text value',
            'propertyRange': 'placeholder text value',
            'downloadLink': 'placeholder link value',
        }
    
    def _process_information_units(self, inputs):
        """Process active databases, generators, and predictors with proper logging"""
        # Process databases
        active_databases = inputs.get('active_databases', [])
        if not active_databases:
            if self.logger:
                self.logger.log('No active databases found.', 'warning')
        else:
            if self.logger:
                database_names = ', '.join(db["name"] for db in active_databases)
                self.logger.log(f'Active databases ({len(active_databases)}): {database_names}', 'info')
            
            for dtbs in active_databases:
                db_key = dtbs['value']
                if db_key in database_factory:
                    db_instance = database_factory[db_key](db_key, self.logger)
                    if self.logger:
                        self.logger.log(db_instance.info(), 'info')
        
        # Process generators
        active_generators = inputs.get('active_generators', [])
        if not active_generators:
            if self.logger:
                self.logger.log('No active generators found.', 'warning')
        else:
            if self.logger:
                generator_names = ', '.join(gen["name"] for gen in active_generators)
                self.logger.log(f'Active generators ({len(active_generators)}): {generator_names}', 'info')
            
            for gnrtr in active_generators:
                gen_key = gnrtr['value']
                if gen_key in generator_factory:
                    gen_instance = generator_factory[gen_key](gen_key, self.logger)
                    if self.logger:
                        self.logger.log(gen_instance.info(), 'info')
        
        # Process predictors
        active_predictors = inputs.get('active_predictors', [])
        if not active_predictors:
            if self.logger:
                self.logger.log('No active predictors found.', 'warning')
        else:
            if self.logger:
                predictor_names = ', '.join(pred["name"] for pred in active_predictors)
                self.logger.log(f'Active predictors ({len(active_predictors)}): {predictor_names}', 'info')
            
            for prdctr in active_predictors:
                pred_key = prdctr['value']
                if pred_key in predictor_factory:
                    pred_instance = predictor_factory[pred_key](pred_key, self.logger)
                    if self.logger:
                        self.logger.log(pred_instance.info(), 'info')
