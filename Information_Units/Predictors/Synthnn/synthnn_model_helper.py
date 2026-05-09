"""Wrapper for SynthNN model with caching and mock capability."""

import sys
from pathlib import Path
from typing import List, Dict
import numpy as np


class SynthnnModelHelper:
    """Wrapper for SynthNN model with caching."""
    
    MODEL_CACHE_DIR = Path(__file__).parent / 'models'
    MODEL_FILE = 'synthnn_model.pt'
    
    def __init__(self, logger=None):
        """
        Initialize SynthNN model helper.
        
        Args:
            logger: Optional logger for warnings/errors
        """
        self.logger = logger
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """
        Load SynthNN model weights from cache.
        
        Adds the SynthNN module to Python path and verifies model files exist.
        """
        try:
            # Add SynthNN module to path
            synthnn_module_path = str(self.MODEL_CACHE_DIR / 'SynthNN')
            if synthnn_module_path not in sys.path:
                sys.path.insert(0, synthnn_module_path)
            
            # Verify model files exist
            model_dir = self.MODEL_CACHE_DIR / 'Paper_final_model'
            required_files = ['W1_30M_synth_v3_semi14112.txt', 
                            'b1_30M_synth_v3_semi14112.txt',
                            'b2_30M_synth_v3_semi14112.txt',
                            'b3_30M_synth_v3_semi14112.txt',
                            'F1_30M_synth_v3_semi14112.txt',
                            'F2_30M_synth_v3_semi14112.txt',
                            'F3_30M_synth_v3_semi14112.txt']
            
            for file in required_files:
                if not (model_dir / file).exists():
                    raise FileNotFoundError(f"Missing model file: {file}")
            
            # Model files verified - actual loading happens at prediction time
            self.model = str(model_dir) + '/'  # Store path to model directory
            
            if self.logger:
                self.logger.log(
                    f"SynthNN model loaded from {model_dir}",
                    'info'
                )
                
        except Exception as e:
            if self.logger:
                self.logger.log(
                    f"Failed to load SynthNN model: {str(e)}. "
                    "Ensure TensorFlow is installed and model files are present.",
                    'error'
                )
            raise
    
    def predict_batch(self, compositions: List[str]) -> Dict[str, float]:
        """
        Batch prediction for multiple compositions.
        
        Args:
            compositions (List[str]): List of composition strings (e.g., ['Al2O3', 'FeO', ...])
            
        Returns:
            Dict[str, float]: Composition → synthesizability score mapping
                            Returns float scores 0.0-1.0 indicating synthesizability likelihood
                            
        Example:
            >>> predictions = model_helper.predict_batch(['Al2O3', 'FeO'])
            >>> predictions
            {'Al2O3': 0.92, 'FeO': 0.31}
        """
        return self._predict(compositions)
    
    def _predict(self, compositions: List[str]) -> Dict[str, float]:
        """
        Call the integrated SynthNN model.
        
        Uses the official SynthNN model from:
        https://github.com/antoniuk1/SynthNN
        
        Args:
            compositions (List[str]): Normalized composition strings
            
        Returns:
            Dict[str, float]: Composition → synthesizability score mapping (0.0-1.0)
        """
        try:
            # Import SynthNN utilities
            from utils import get_features
            import tensorflow as tf
            import os
            
            if self.model is None:
                raise RuntimeError("Model not loaded. Call _load_model() first.")
            
            # Prepare input
            data_input = np.array(compositions)
            
            # Get features using SynthNN's feature extraction
            x_input = get_features(data_input)
            
            # Load model weights
            saved_model_dir = self.model
            
            def find_all(name, path):
                result = []
                for files in os.listdir(path):
                    if files.startswith(name):
                        result.append(os.path.join(files))
                return result
            
            W1_filename = find_all('W1', saved_model_dir)
            b1_filename = find_all('b1', saved_model_dir)
            b2_filename = find_all('b2', saved_model_dir)
            b3_filename = find_all('b3', saved_model_dir)
            F1_filename = find_all('F1', saved_model_dir)
            F2_filename = find_all('F2', saved_model_dir)
            F3_filename = find_all('F3', saved_model_dir)
            
            if len(W1_filename) > 1:
                raise ValueError("Multiple model weight files found")
            
            W1_loaded = np.loadtxt(saved_model_dir + W1_filename[0])
            b1_loaded = np.loadtxt(saved_model_dir + b1_filename[0])
            b2_loaded = np.loadtxt(saved_model_dir + b2_filename[0])
            b3_loaded = np.loadtxt(saved_model_dir + b3_filename[0])
            b3_loaded = np.reshape(b3_loaded, [2])
            
            M = np.shape(W1_loaded)[1]
            no_h1 = np.shape(b1_loaded)[0]
            no_h2 = np.shape(b2_loaded)[0]
            
            F1_loaded = np.loadtxt(saved_model_dir + F1_filename[0])
            F2_loaded = np.loadtxt(saved_model_dir + F2_filename[0])
            F3_loaded = np.loadtxt(saved_model_dir + F3_filename[0])
            F3_loaded = np.reshape(F3_loaded, [no_h2, 2])
            
            # Set up model architecture
            y_input = np.zeros((len(data_input), 2))
            tf.compat.v1.disable_eager_execution()
            x = tf.compat.v1.placeholder(tf.float32, shape=[None, x_input.shape[1]])
            y_ = tf.compat.v1.placeholder(tf.float32, shape=[None, 2])
            W1 = tf.compat.v1.placeholder(tf.float32, shape=[x_input.shape[1], M])
            F1 = tf.compat.v1.placeholder(tf.float32, shape=[M, no_h1])
            F2 = tf.compat.v1.placeholder(tf.float32, shape=[no_h1, no_h2])
            F3 = tf.compat.v1.placeholder(tf.float32, shape=[no_h2, 2])
            b1 = tf.compat.v1.placeholder(tf.float32, shape=[no_h1])
            b2 = tf.compat.v1.placeholder(tf.float32, shape=[no_h2])
            b3 = tf.compat.v1.placeholder(tf.float32, shape=[2])
            
            sess = tf.compat.v1.InteractiveSession()
            z0_raw = tf.multiply(tf.expand_dims(x, 2), tf.expand_dims(W1, 0))
            tempmean, var = tf.nn.moments(x=z0_raw, axes=[1])
            z0 = tf.concat([tf.reduce_sum(input_tensor=z0_raw, axis=1)], 1)
            z1 = tf.add(tf.matmul(z0, F1), b1)
            a1 = tf.tanh(z1)
            z2 = tf.add(tf.matmul(a1, F2), b2)
            a2 = tf.tanh(z2)
            z3 = tf.add(tf.matmul(a2, F3), b3)
            a3 = tf.nn.softmax(z3)
            clipped_y = tf.clip_by_value(a3, 1e-10, 1.0)
            
            sess.run(tf.compat.v1.initialize_all_variables())
            preds = a3.eval(feed_dict={
                x: x_input, 
                y_: y_input,
                W1: W1_loaded,
                F1: F1_loaded,
                F2: F2_loaded,
                F3: F3_loaded,
                b1: b1_loaded,
                b2: b2_loaded,
                b3: b3_loaded
            })
            sess.close()
            
            # preds[:,0] contains synthesizability scores (probability of being synthesizable)
            scores = preds[:, 0]
            
            # Create result dictionary
            results = {}
            for i, comp in enumerate(compositions):
                results[comp] = float(scores[i])
            
            if self.logger:
                self.logger.log(
                    f"SynthNN predictions completed for {len(compositions)} compositions",
                    'info'
                )
            
            return results
            
        except Exception as e:
            if self.logger:
                self.logger.log(
                    f"SynthNN prediction failed: {str(e)}",
                    'error'
                )
            # Return None for all compositions to trigger error handling
            return {comp: None for comp in compositions}
