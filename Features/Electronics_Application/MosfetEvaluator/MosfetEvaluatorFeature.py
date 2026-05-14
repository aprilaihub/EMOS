from Features.BaseFeature import BaseFeature
from Information_Units.Generators.GeneratorFactory import generator_factory
from Information_Units.Databases.DatabaseFactory import database_factory
from Information_Units.Predictors.PredictorFactory import predictor_factory
from Features.Electronics_Application.MosfetEvaluator.pdd_solver_python.MosfetSolver import run as run_mosfet_solver
import json
import numpy as np
from datetime import datetime
from pathlib import Path


class MosfetEvaluatorFeature(BaseFeature):
    def __init__(self, logger=None):
        super().__init__("MOSFET evaluator", logger)
    
    def info(self):
        return "MOSFET evaluator: Evaluate MOSFET performance from uploaded CIF files and simulation parameters"
    
    def extract_inputs(self, input_data):
        return {
            'channelLengthNm': input_data.get('channelLengthNm', '14'),
            'sourceDrainLengthNm': input_data.get('sourceDrainLengthNm', '4'),
            'oxideThicknessNm': input_data.get('oxideThicknessNm', '1'),
            'channelThicknessNm': input_data.get('channelThicknessNm', '4'),
            'dxM': input_data.get('dxM', '5e-10'),
            'dyM': input_data.get('dyM', '5e-10'),
            'temperatureK': input_data.get('temperatureK', '300'),
            'gateWorkFunctionEv': input_data.get('gateWorkFunctionEv', '3.65'),
            'sdWorkFunctionEv': input_data.get('sdWorkFunctionEv', '0.0'),
            'channelDopingCm3': input_data.get('channelDopingCm3', '-1e15'),
            'sourceDrainDopingCm3': input_data.get('sourceDrainDopingCm3', '1e20'),
            'drainVoltageVd': input_data.get('drainVoltageVd', '0.7'),
            'gateVoltageSweepStartV': input_data.get('gateVoltageSweepStartV', '0.0'),
            'gateVoltageSweepStopV': input_data.get('gateVoltageSweepStopV', '0.7'),
            'numberOfGatePoints': input_data.get('numberOfGatePoints', '14'),
            'drainVoltageSweepStartV': input_data.get('drainVoltageSweepStartV', '0.0'),
            'drainVoltageSweepStopV': input_data.get('drainVoltageSweepStopV', '0.7'),
            'numberOfDrainPoints': input_data.get('numberOfDrainPoints', '13'),
            'channelNc': input_data.get('channelNc', '2.8e25'),
            'channelNv': input_data.get('channelNv', '1.04e25'),
            'channelEpsRel': input_data.get('channelEpsRel', '11.9'),
            'channelUn': input_data.get('channelUn', '0.1500'),
            'channelUp': input_data.get('channelUp', '0.0475'),
            'channelXiEv': input_data.get('channelXiEv', '4.05'),
            'channelEgEv': input_data.get('channelEgEv', '1.12'),
            'channelVsatN': input_data.get('channelVsatN', '2e5'),
            'channelVsatP': input_data.get('channelVsatP', '2e5'),
            'channelPowN': input_data.get('channelPowN', '2.0'),
            'channelPowP': input_data.get('channelPowP', '1.0'),
            'insulatorNc': input_data.get('insulatorNc', '1.0'),
            'insulatorNv': input_data.get('insulatorNv', '1.0'),
            'insulatorEpsRel': input_data.get('insulatorEpsRel', '3.9'),
            'insulatorUn': input_data.get('insulatorUn', '1e-3'),
            'insulatorUp': input_data.get('insulatorUp', '1e-3'),
            'insulatorXiEv': input_data.get('insulatorXiEv', '0.9'),
            'insulatorEgEv': input_data.get('insulatorEgEv', '9.0'),
            'insulatorVsatN': input_data.get('insulatorVsatN', '2e5'),
            'insulatorVsatP': input_data.get('insulatorVsatP', '2e5'),
            'insulatorPowN': input_data.get('insulatorPowN', '2.0'),
            'insulatorPowP': input_data.get('insulatorPowP', '1.0'),
            'active_databases': input_data.get('active_databases', []),
            'active_generators': input_data.get('active_generators', []),
            'active_predictors': input_data.get('active_predictors', []),
        }
    
    def process_feature(self, inputs):
        if self.logger:
            self.logger.log('Initializing MOSFET evaluator...', 'info')

        # Process information units (databases, generators, predictors)
        self._process_information_units(inputs)

        # ── Run the 2D PDD Python solver ──────────────────────────────────────
        if self.logger:
            self.logger.log('Launching Python 2D drift-diffusion solver...', 'info')

        Vgs_start = float(inputs.get('gateVoltageSweepStartV', 0.0))
        Vgs_stop = float(inputs.get('gateVoltageSweepStopV', 0.7))
        Nvg = max(2, int(float(inputs.get('numberOfGatePoints', 14))))

        Vds_start = float(inputs.get('drainVoltageSweepStartV', 0.0))
        Vds_stop = float(inputs.get('drainVoltageSweepStopV', inputs.get('drainVoltageVd', 0.7)))
        Nvd = max(2, int(float(inputs.get('numberOfDrainPoints', 13))))

        channel_material = {
            'Nc': float(inputs.get('channelNc', 2.8e25)),
            'Nv': float(inputs.get('channelNv', 1.04e25)),
            'ep': float(inputs.get('channelEpsRel', 11.9)),
            'un': float(inputs.get('channelUn', 0.1500)),
            'up': float(inputs.get('channelUp', 0.0475)),
            'xi': float(inputs.get('channelXiEv', 4.05)),
            'Eg': float(inputs.get('channelEgEv', 1.12)),
            'vsat_n': float(inputs.get('channelVsatN', 2e5)),
            'vsat_p': float(inputs.get('channelVsatP', 2e5)),
            'pow_n': float(inputs.get('channelPowN', 2.0)),
            'pow_p': float(inputs.get('channelPowP', 1.0)),
        }

        insulator_material = {
            'Nc': float(inputs.get('insulatorNc', 1.0)),
            'Nv': float(inputs.get('insulatorNv', 1.0)),
            'ep': float(inputs.get('insulatorEpsRel', 3.9)),
            'un': float(inputs.get('insulatorUn', 1e-3)),
            'up': float(inputs.get('insulatorUp', 1e-3)),
            'xi': float(inputs.get('insulatorXiEv', 0.9)),
            'Eg': float(inputs.get('insulatorEgEv', 9.0)),
            'vsat_n': float(inputs.get('insulatorVsatN', 2e5)),
            'vsat_p': float(inputs.get('insulatorVsatP', 2e5)),
            'pow_n': float(inputs.get('insulatorPowN', 2.0)),
            'pow_p': float(inputs.get('insulatorPowP', 1.0)),
        }

        try:
            solver_results = run_mosfet_solver(
                channel_length_m=float(inputs.get('channelLengthNm', 14)) * 1e-9,
                source_drain_length_m=float(inputs.get('sourceDrainLengthNm', 4)) * 1e-9,
                oxide_thickness_m=float(inputs.get('oxideThicknessNm', 1)) * 1e-9,
                channel_thickness_m=float(inputs.get('channelThicknessNm', 4)) * 1e-9,
                dx=float(inputs.get('dxM', 5e-10)),
                dy=float(inputs.get('dyM', 5e-10)),
                temperature_K=float(inputs.get('temperatureK', 300)),
                gate_work_function_eV=float(inputs.get('gateWorkFunctionEv', 3.65)),
                sd_work_function_eV=float(inputs.get('sdWorkFunctionEv', 0.0)),
                channel_doping_cm3=float(inputs.get('channelDopingCm3', -1e15)),
                sd_doping_cm3=float(inputs.get('sourceDrainDopingCm3', 1e20)),
                Vgs_start=Vgs_start,
                Vgs_stop=Vgs_stop,
                Nvg=Nvg,
                Vds_start=Vds_start,
                Vds_stop=Vds_stop,
                Nvd=Nvd,
                channel_material=channel_material,
                insulator_material=insulator_material,
            )
            if self.logger:
                self.logger.log('Python solver completed successfully.', 'info')
        except RuntimeError as exc:
            if self.logger:
                self.logger.log(f'Python solver error: {exc}', 'error')
            solver_results = None

        if self.logger:
            self.logger.log('MOSFET evaluator processing completed', 'info')

        return {
            'status': 'completed',
            'message': 'MOSFET evaluator feature executed successfully',
            'solver_results': solver_results,
        }
    
    def format_outputs(self, results):
        import tempfile
        import os
        
        solver = results.get('solver_results')
        if solver is None:
            return {'error': 'Solver did not produce results.'}
        
        # Extract arrays
        J_arr = np.asarray(solver['J'])  # shape: (Nvg, Nvd)
        Q_arr = np.asarray(solver['Q'])
        Vgs_arr = np.asarray(solver['Vgs'])
        Vds_arr = np.asarray(solver['Vds'])
        
        # Calculate key metrics
        mid_vgs_idx = len(Vgs_arr) // 2
        mid_vds_idx = len(Vds_arr) * 2 // 3
        id_on = float(J_arr[mid_vgs_idx, mid_vds_idx])
        
        off_vgs_idx = 0
        id_off = float(J_arr[off_vgs_idx, mid_vds_idx])
        
        mid_vds_ref_idx = len(Vds_arr) // 2
        j_ref_curve = J_arr[:, mid_vds_ref_idx]
        threshold_idx = np.argmin(np.abs(j_ref_curve - np.nanmean(j_ref_curve)))
        vth_approx = float(Vgs_arr[threshold_idx])
        
        key_metrics = {
            "Id_on_uA_per_um": id_on,
            "Id_off_uA_per_um": id_off,
            "Vth_approx_V": vth_approx,
            "Ion_Ioff_ratio": float(id_on / max(id_off, 1e-10)),
        }
        
        # Create full results dict for JSON
        full_results = {
            "timestamp": datetime.now().isoformat(),
            "device": {
                "channel_length_nm": 14,  # Can be extracted from inputs if needed
            },
            "bias_conditions": {
                "Vgs_range_V": [float(Vgs_arr.min()), float(Vgs_arr.max())],
                "Vds_range_V": [float(Vds_arr.min()), float(Vds_arr.max())],
            },
            "key_metrics": key_metrics,
            "full_data": {
                "Vgs": Vgs_arr.tolist(),
                "Vds": Vds_arr.tolist(),
                "J": J_arr.tolist(),
                "Q": Q_arr.tolist(),
            }
        }
        
        # Save to JSON file in temp directory
        output_dir = Path(tempfile.gettempdir()) / 'emos_mosfet_results'
        output_dir.mkdir(exist_ok=True)
        json_filename = f"mosfet_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        json_path = output_dir / json_filename
        
        with open(json_path, 'w') as f:
            json.dump(full_results, f, indent=2)
        
        return {
            'status': 'success',
            'key_metrics': key_metrics,
            'J_uA_per_um': J_arr.tolist(),
            'Vgs_V': Vgs_arr.tolist(),
            'Vds_V': Vds_arr.tolist(),
            'Q_C_per_m': Q_arr.tolist(),
            'json_filename': json_filename,
            'json_path': str(json_path),
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
