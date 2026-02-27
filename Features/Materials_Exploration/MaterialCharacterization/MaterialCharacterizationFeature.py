from Features.BaseFeature import BaseFeature
from Information_Units.Generators.GeneratorFactory import generator_factory
from Information_Units.Databases.DatabaseFactory import database_factory
from Information_Units.Predictors.PredictorFactory import predictor_factory


class MaterialCharacterizationFeature(BaseFeature):
    def __init__(self, logger=None):
        super().__init__("Material Characterization", logger)
    
    def info(self):
        return "Material Characterization: Advanced materials analysis and characterization tools for comprehensive evaluation"
    
    def extract_inputs(self, input_data):
        return {
            'materialFormula': input_data.get('materialFormula', ''),
            'analysisType': input_data.get('analysisType', 'basic'),
            'threshold': input_data.get('thresholdValue', '50'),
            'exportResults': input_data.get('exportResults', 'True'),
            'feature_input': input_data.get('featureInput', ''),
            'active_databases': input_data.get('active_databases', []),
            'active_generators': input_data.get('active_generators', []),
            'active_predictors': input_data.get('active_predictors', []),
        }
    
    def process_feature(self, inputs):
        if self.logger:
            self.logger.log('Initializing Material Characterization...', 'info')
        
        # Process information units (databases, generators, predictors)
        self._process_information_units(inputs)
        
        if self.logger:
            self.logger.log('Material Characterization processing completed', 'info')
        
        return {
            'status': 'completed',
            'message': 'Material Characterization feature executed successfully'
        }
    
    def format_outputs(self, results):
        return {
            'analysisStatus': 'placeholder text value',
            'materialProperties': 'placeholder text value',
            'reportGeneration': 'placeholder text value',
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
