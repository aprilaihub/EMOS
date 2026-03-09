from Features.BaseFeature import BaseFeature
from Information_Units.Generators.GeneratorFactory import generator_factory, generator_registry
from Information_Units.Databases.DatabaseFactory import database_factory
from Information_Units.Predictors.PredictorFactory import predictor_factory


class MaterialGenerationFeature(BaseFeature):
    def __init__(self, logger=None):
        super().__init__("Material Generation", logger)
    
    def info(self):
        return "Material Generation: Generate new material compositions using AI-powered algorithms and predictive models"
    
    def extract_inputs(self, input_data):
        return {
            'active_databases': input_data.get('active_databases', []),
            'active_generators': input_data.get('active_generators', []),
            'active_predictors': input_data.get('active_predictors', []),
            'generator_inputs': input_data.get('generator_inputs', {}),
        }
    
    def process_feature(self, inputs):
        if self.logger:
            self.logger.log('Initializing Material Generation...', 'info')

        # ── Collect results from all active generators ────────────────
        generator_inputs = inputs.get('generator_inputs', {})
        all_generation_results = {}

        active_generators = inputs.get('active_generators', [])
        if not active_generators:
            if self.logger:
                self.logger.log('No active generators selected.', 'warning')
        else:
            if self.logger:
                names = ', '.join(g['name'] for g in active_generators)
                self.logger.log(f'Active generators ({len(active_generators)}): {names}', 'info')

        for gen_info in active_generators:
            gen_key = gen_info['value']

            # Check if the generator is in the registry (instantiated)
            if gen_key in generator_registry:
                gen_instance = generator_registry[gen_key]
            elif gen_key in generator_factory:
                gen_instance = generator_factory[gen_key](gen_key, self.logger)
            else:
                if self.logger:
                    self.logger.log(f'Generator "{gen_key}" not found in factory — skipping.', 'warning')
                continue

            # Get the per-generator inputs collected by the JS ___Inputs class
            gen_params = generator_inputs.get(gen_key, {})

            if self.logger:
                self.logger.log(f'Calling {gen_key}.generate() with params: {gen_params}', 'info')

            try:
                result = gen_instance.generate(gen_params)
                all_generation_results[gen_key] = result

                status = result.get('status', 'unknown')
                n_structs = result.get('num_structures', 0)
                if self.logger:
                    self.logger.log(
                        f'{gen_key}: status={status}, {n_structs} structure(s) returned.', 'info'
                    )

                # Forward any debug_logs from the container
                for dl in result.get('debug_logs', []):
                    if self.logger:
                        self.logger.log(f'  [{gen_key}] {dl}', 'info')

            except Exception as exc:
                if self.logger:
                    self.logger.log(f'{gen_key}.generate() failed: {exc}', 'error')
                all_generation_results[gen_key] = {
                    'status': 'error',
                    'message': str(exc),
                }

        if self.logger:
            self.logger.log('Material Generation processing completed.', 'info')
        
        return {
            'status': 'completed',
            'generation_results': all_generation_results,
        }
    
    def format_outputs(self, results):
        """Return the raw generation results so the JS front-end can
        render them (structure dropdown, CIF viewer, etc.)."""
        return results
