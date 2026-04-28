from Features.BaseFeature import BaseFeature
from Information_Units.Generators.GeneratorFactory import generator_factory
from Information_Units.Databases.DatabaseFactory import database_factory
from Information_Units.Predictors.PredictorFactory import predictor_factory


class MosfetEvaluatorFeature(BaseFeature):
    def __init__(self, logger=None):
        super().__init__("MOSFET evaluator", logger)
    
    def info(self):
        return "MOSFET evaluator: Evaluate MOSFET performance from uploaded CIF files and simulation parameters"
    
    def extract_inputs(self, input_data):
        return {
            'cifFiles': input_data.get('cifFiles', ''),
            'deviceType': input_data.get('deviceType', 'nmos'),
            'channelLengthNm': input_data.get('channelLength(nm)', '45'),
            'channelWidthNm': input_data.get('channelWidth(nm)', '1000'),
            'oxideThicknessNm': input_data.get('oxideThickness(nm)', '1.5'),
            'supplyVoltageVdd': input_data.get('supplyVoltageVdd(v)', '1.0'),
            'gateWorkFunctionEv': input_data.get('gateWorkFunction(ev)', '4.5'),
            'sourceDrainDopingCm3': input_data.get('source/drainDoping(cm^-3)', '1e+20'),
            'temperatureK': input_data.get('temperature(k)', '300'),
            'drainVoltageVd': input_data.get('drainVoltageVd(v)', '1.0'),
            'gateVoltageSweepStartV': input_data.get('gateSweepStart(v)', '0.0'),
            'gateVoltageSweepStopV': input_data.get('gateSweepStop(v)', '1.5'),
            'gateVoltageSweepStepV': input_data.get('gateSweepStep(v)', '0.05'),
            'validateBandGap': input_data.get('validateBandGapFromCif', 'True'),
            'validateElectronMobility': input_data.get('validateElectronMobilityFromCif', 'True'),
            'validateHoleMobility': input_data.get('validateHoleMobilityFromCif', 'True'),
            'validateDielectricConstant': input_data.get('validateDielectricConstantFromCif', 'True'),
            'feature_input': input_data.get('featureInput', ''),
            'active_databases': input_data.get('active_databases', []),
            'active_generators': input_data.get('active_generators', []),
            'active_predictors': input_data.get('active_predictors', []),
        }
    
    def process_feature(self, inputs):
        if self.logger:
            self.logger.log('Initializing MOSFET evaluator...', 'info')
        
        # Process information units (databases, generators, predictors)
        self._process_information_units(inputs)
        
        if self.logger:
            self.logger.log('MOSFET evaluator processing completed', 'info')
        
        return {
            'status': 'completed',
            'message': 'MOSFET evaluator feature executed successfully'
        }
    
    def format_outputs(self, results):
        return {
            'downloadResultsJson': 'placeholder link value',
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
