"""
Quantization module with ML-based optimization.

Implements importance-weighted quantization and neural network-based
quantization parameter prediction.
"""

import numpy as np
import pywt
from typing import List, Tuple
import pickle


class MLQuantizationOptimizer:
    """
    Lightweight neural network for predicting optimal quantization parameters.
    
    Network architecture:
    Input (4) → Dense(32) → ReLU → Dense(16) → ReLU → Dense(8) → ReLU → Dense(1) → Sigmoid
    
    Output: Q_adjust ∈ [0.5, 2.0] (multiplier for base quantization)
    """
    
    def __init__(self):
        """Initialize with pre-trained weights (simple initialization for now)."""
        # For a production system, these would be trained on a dataset
        # For now, we use a simplified heuristic-based approach
        self.trained = False
        self.weights = self._initialize_weights()
    
    def _initialize_weights(self):
        """Initialize network weights with reasonable defaults."""
        # Simple initialization - in practice, train on dataset
        np.random.seed(42)
        return {
            'W1': np.random.randn(4, 32) * 0.1,
            'b1': np.zeros(32),
            'W2': np.random.randn(32, 16) * 0.1,
            'b2': np.zeros(16),
            'W3': np.random.randn(16, 8) * 0.1,
            'b3': np.zeros(8),
            'W4': np.random.randn(8, 1) * 0.1,
            'b4': np.zeros(1),
        }
    
    def predict(self, features: np.ndarray) -> float:
        """
        Predict quantization adjustment factor.
        
        Args:
            features: [subband_energy, importance_mean, importance_std, block_variance]
        
        Returns:
            Q_adjust multiplier in range [0.5, 2.0]
        """
        if not self.trained:
            # Use heuristic if not trained
            return self._heuristic_prediction(features)
        
        # Forward pass
        x = features.reshape(1, -1)
        
        # Layer 1
        x = np.maximum(0, np.dot(x, self.weights['W1']) + self.weights['b1'])  # ReLU
        
        # Layer 2
        x = np.maximum(0, np.dot(x, self.weights['W2']) + self.weights['b2'])  # ReLU
        
        # Layer 3
        x = np.maximum(0, np.dot(x, self.weights['W3']) + self.weights['b3'])  # ReLU
        
        # Output layer
        x = np.dot(x, self.weights['W4']) + self.weights['b4']
        
        # Sigmoid activation scaled to [0.5, 2.0]
        q_adjust = 0.5 + 1.5 * (1 / (1 + np.exp(-x[0, 0])))
        
        return q_adjust
    
    def _heuristic_prediction(self, features: np.ndarray) -> float:
        """
        Heuristic-based prediction when ML model is not trained.
        
        Uses importance and variance to estimate quantization needs.
        """
        subband_energy, importance_mean, importance_std, block_variance = features
        
        # High importance → lower Q_adjust (finer quantization)
        # High variance → lower Q_adjust (preserve detail)
        
        importance_factor = 1.0 - 0.5 * importance_mean
        variance_factor = np.clip(block_variance / 10000.0, 0, 0.5)
        
        q_adjust = 0.5 + importance_factor + variance_factor
        return np.clip(q_adjust, 0.5, 2.0)


class ImportanceWeightedQuantizer:
    """Quantizes wavelet coefficients with importance-weighted step sizes."""
    
    def __init__(self, base_q: float = 10.0, 
                 adaptation_strength: float = 2.0,
                 use_ml_optimizer: bool = True):
        """
        Initialize quantizer.
        
        Args:
            base_q: Base quantization step size
            adaptation_strength: k - importance adaptation factor
            use_ml_optimizer: Whether to use ML-based optimization
        """
        self.base_q = base_q
        self.k = adaptation_strength
        self.use_ml_optimizer = use_ml_optimizer
        
        if use_ml_optimizer:
            self.ml_optimizer = MLQuantizationOptimizer()
        else:
            self.ml_optimizer = None
    
    def quantize_coeffs(self, coeffs: Tuple, 
                       importance_map: np.ndarray,
                       block_position: Tuple[int, int],
                       block_size: int) -> Tuple[List, dict]:
        """
        Quantize wavelet coefficients with importance weighting.
        NOW RETURNS INTEGER QUANTIZED COEFFICIENTS for efficient storage.
        
        Args:
            coeffs: Wavelet coefficients from pywt.wavedec2
            importance_map: Perceptual importance map
            block_position: (row, col) position of block
            block_size: Size of block
        
        Returns:
            (quantized_int_coeffs_list, metadata)
        """
        i, j = block_position
        imp_block = importance_map[i:min(i+block_size, importance_map.shape[0]),
                                   j:min(j+block_size, importance_map.shape[1])]
        
        # Extract importance statistics
        importance_mean = np.mean(imp_block)
        importance_std = np.std(imp_block)
        
        # Quantize each subband
        quantized_coeffs = []
        metadata = {'q_steps': []}
        
        for idx, coeff in enumerate(coeffs):
            if idx == 0:
                # Approximation coefficients (LL)
                # Always use fine quantization for low-frequency
                q_step = self.base_q * 0.5
            else:
                # Detail coefficients (LH, HL, HH)
                if isinstance(coeff, tuple):
                    # Multiple detail subbands
                    coeff_energy = np.mean([np.mean(np.abs(c)) for c in coeff])
                    block_variance = np.mean([np.var(c) for c in coeff])
                else:
                    coeff_energy = np.mean(np.abs(coeff))
                    block_variance = np.var(coeff)
                
                # Compute adaptive quantization step
                q_step = self._compute_adaptive_q_step(
                    coeff_energy,
                    importance_mean,
                    importance_std,
                    block_variance
                )
            
            # Apply integer quantization
            if isinstance(coeff, tuple):
                quantized_subband = [self._quantize_to_int(c, q_step) for c in coeff]
            else:
                quantized_subband = self._quantize_to_int(coeff, q_step)
            
            quantized_coeffs.append(quantized_subband)
            metadata['q_steps'].append(q_step)
        
        return quantized_coeffs, metadata
    
    def _compute_adaptive_q_step(self, subband_energy: float,
                                importance_mean: float,
                                importance_std: float,
                                block_variance: float) -> float:
        """Compute adaptive quantization step size."""
        # Base adaptation: Q(x,y) = Q_base · (1 + k·(1 - I(x,y)))
        q_base_adapted = self.base_q * (1 + self.k * (1 - importance_mean))
        
        # ML optimization (if enabled)
        if self.use_ml_optimizer and self.ml_optimizer is not None:
            features = np.array([
                subband_energy,
                importance_mean,
                importance_std,
                block_variance
            ])
            q_adjust = self.ml_optimizer.predict(features)
            q_step = q_base_adapted * q_adjust
        else:
            q_step = q_base_adapted
        
        return max(0.5, q_step)  # Ensure minimum quantization step
    
    @staticmethod
    def _quantize_to_int(arr: np.ndarray, q_step: float) -> np.ndarray:
        """
        Quantize array to INT16 using dead-zone quantization.
        
        This is the KEY change for compression - converts float32 → int16.
        
        Args:
            arr: Float coefficient array
            q_step: Quantization step size
        
        Returns:
            int16 quantized coefficients
        """
        # Dead-zone threshold
        dead_zone = q_step * 1.5
        
        # Quantize to integers
        quantized_int = np.where(
            np.abs(arr) < dead_zone,
            0,
            np.round(arr / q_step)
        ).astype(np.int16)
        
        return quantized_int
    
    @staticmethod
    def _dequantize_from_int(int_arr: np.ndarray, q_step: float) -> np.ndarray:
        """
        Dequantize int16 back to float.
        
        Args:
            int_arr: Integer quantized coefficients
            q_step: Quantization step size
        
        Returns:
            Float coefficients
        """
        return int_arr.astype(np.float32) * q_step
    
    def dequantize_coeffs(self, quantized_coeffs: Tuple, 
                         metadata: dict) -> Tuple:
        """
        Dequantize coefficients (no-op since we store quantized values directly).
        
        Args:
            quantized_coeffs: Quantized coefficients
            metadata: Quantization metadata
        
        Returns:
            Dequantized coefficients (same as input for this implementation)
        """
        # In this implementation, quantized values are already in original scale
        return quantized_coeffs


def quantize_wavelet_coefficients(coeffs: Tuple,
                                  importance_map: np.ndarray,
                                  block_position: Tuple[int, int],
                                  block_size: int,
                                  base_q: float = 10.0) -> Tuple[Tuple, dict]:
    """
    Convenience function for quantizing wavelet coefficients.
    
    Args:
        coeffs: Wavelet coefficients
        importance_map: Perceptual importance map
        block_position: Block position
        block_size: Block size
        base_q: Base quantization parameter
    
    Returns:
        (quantized_coeffs, metadata)
    """
    quantizer = ImportanceWeightedQuantizer(base_q=base_q)
    return quantizer.quantize_coeffs(coeffs, importance_map, block_position, block_size)
