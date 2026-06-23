"""
Stub adapter — delegates to pywt for wavelet transforms.

Provides AdaptiveWaveletTransform with the API expected by
simple_pawc_v2.py and pawc_v2_codec.py.
"""

import numpy as np
import pywt
from typing import Tuple


class AdaptiveWaveletTransform:
    """
    Adaptive wavelet transform with select/transform/inverse_transform API.

    Selects wavelet basis based on block variance: smooth blocks use 'haar',
    detailed blocks use 'db4'.
    """

    AVAILABLE_WAVELETS = ['haar', 'db4', 'bior4.4']

    def __init__(self):
        pass

    def select_wavelet(self, block: np.ndarray,
                       block_importance: float) -> str:
        """
        Select wavelet basis based on block variance.

        Args:
            block: 2D image block
            block_importance: Mean importance of the block

        Returns:
            Wavelet name string ('haar', 'db4', or 'bior4.4')
        """
        variance = np.var(block)

        if variance < 100:
            return 'haar'
        elif variance < 1000:
            return 'bior4.4'
        else:
            return 'db4'

    def transform(self, block: np.ndarray, wavelet: str,
                  level: int = 2) -> list:
        """
        Apply wavelet transform to a block.

        Args:
            block: 2D image block
            wavelet: Wavelet name
            level: Decomposition level

        Returns:
            List of wavelet coefficients from pywt.wavedec2
        """
        return pywt.wavedec2(block, wavelet, level=level)

    def inverse_transform(self, coeffs: list,
                          wavelet: str) -> np.ndarray:
        """
        Apply inverse wavelet transform.

        Args:
            coeffs: Wavelet coefficients from pywt.wavedec2
            wavelet: Wavelet name used for forward transform

        Returns:
            Reconstructed 2D array
        """
        return pywt.waverec2(coeffs, wavelet)
