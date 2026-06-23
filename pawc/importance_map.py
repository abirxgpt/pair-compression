"""
Perceptual Importance Map (PIM) generation module.

Combines edge detection, texture analysis, and visual saliency to identify
perceptually important regions in an image.
"""

import numpy as np
from scipy import ndimage
from scipy.fft import fft2, ifft2, fftshift
import cv2
from typing import Tuple


class ImportanceMapGenerator:
    """Generates perceptual importance maps for images."""
    
    def __init__(self, edge_weight: float = 0.4, 
                 texture_weight: float = 0.3,
                 saliency_weight: float = 0.3):
        """
        Initialize the importance map generator.
        
        Args:
            edge_weight: Weight for edge component (α)
            texture_weight: Weight for texture component (β)
            saliency_weight: Weight for saliency component (γ)
        """
        self.alpha = edge_weight
        self.beta = texture_weight
        self.gamma = saliency_weight
    
    def generate(self, image: np.ndarray) -> np.ndarray:
        """
        Generate perceptual importance map for an image.
        
        Args:
            image: Input image (H, W, C) in range [0, 255]
        
        Returns:
            Importance map (H, W) in range [0, 1]
        """
        # Convert to grayscale for analysis
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_RGB2GRAY)
        else:
            gray = image.astype(np.uint8)
        
        # Compute three components
        edge_map = self._compute_edge_strength(gray)
        texture_map = self._compute_texture_complexity(gray)
        saliency_map = self._compute_visual_saliency(gray)
        
        # Combine with weights
        importance_map = (
            self.alpha * edge_map +
            self.beta * texture_map +
            self.gamma * saliency_map
        )
        
        # Normalize to [0, 1]
        importance_map = self._normalize(importance_map)
        
        return importance_map
    
    def _compute_edge_strength(self, gray: np.ndarray) -> np.ndarray:
        """
        Compute edge strength using Canny edge detection.
        
        Args:
            gray: Grayscale image
        
        Returns:
            Normalized edge strength map
        """
        # Apply Canny edge detection
        edges = cv2.Canny(gray, threshold1=50, threshold2=150)
        
        # Apply Gaussian blur to create smooth edge strength map
        edge_strength = cv2.GaussianBlur(edges.astype(np.float32), (9, 9), 2.0)
        
        return self._normalize(edge_strength)
    
    def _compute_texture_complexity(self, gray: np.ndarray, 
                                   window_size: int = 32) -> np.ndarray:
        """
        Compute texture complexity using local FFT energy.
        
        Args:
            gray: Grayscale image
            window_size: Size of local analysis window
        
        Returns:
            Normalized texture complexity map
        """
        h, w = gray.shape
        complexity_map = np.zeros_like(gray, dtype=np.float32)
        
        # Pad image for windowing
        pad = window_size // 2
        padded = np.pad(gray, pad, mode='reflect')
        
        # Sliding window FFT analysis
        for i in range(h):
            for j in range(w):
                # Extract local window
                window = padded[i:i+window_size, j:j+window_size]
                
                # Compute FFT energy (excluding DC component)
                fft_mag = np.abs(fft2(window))
                fft_mag[0, 0] = 0  # Remove DC
                
                # High-frequency energy indicates texture complexity
                complexity_map[i, j] = np.sum(fft_mag ** 2)
        
        return self._normalize(complexity_map)
    
    def _compute_visual_saliency(self, gray: np.ndarray) -> np.ndarray:
        """
        Compute visual saliency using spectral residual method.
        
        Based on: "Saliency Detection: A Spectral Residual Approach" (Hou & Zhang, 2007)
        
        Args:
            gray: Grayscale image
        
        Returns:
            Normalized saliency map
        """
        # Convert to float
        img_float = gray.astype(np.float32)
        
        # Compute FFT
        img_fft = fft2(img_float)
        
        # Compute amplitude and phase
        amplitude = np.abs(img_fft)
        phase = np.angle(img_fft)
        
        # Compute log amplitude spectrum
        log_amplitude = np.log(amplitude + 1e-8)
        
        # Compute spectral residual
        # (deviation from average spectrum)
        log_amplitude_avg = cv2.GaussianBlur(log_amplitude, (3, 3), 1.0)
        spectral_residual = log_amplitude - log_amplitude_avg
        
        # Reconstruct saliency map
        saliency_fft = np.exp(spectral_residual + 1j * phase)
        saliency_map = np.abs(ifft2(saliency_fft)) ** 2
        
        # Apply Gaussian smoothing
        saliency_map = cv2.GaussianBlur(saliency_map, (9, 9), 2.5)
        
        return self._normalize(saliency_map)
    
    @staticmethod
    def _normalize(arr: np.ndarray) -> np.ndarray:
        """Normalize array to [0, 1] range."""
        arr_min = arr.min()
        arr_max = arr.max()
        
        if arr_max - arr_min < 1e-8:
            return np.zeros_like(arr)
        
        return (arr - arr_min) / (arr_max - arr_min)


def generate_importance_map(image: np.ndarray,
                           edge_weight: float = 0.4,
                           texture_weight: float = 0.3,
                           saliency_weight: float = 0.3) -> np.ndarray:
    """
    Convenience function to generate importance map.
    
    Args:
        image: Input image (H, W, C) in range [0, 255]
        edge_weight: Weight for edge component
        texture_weight: Weight for texture component
        saliency_weight: Weight for saliency component
    
    Returns:
        Importance map (H, W) in range [0, 1]
    """
    generator = ImportanceMapGenerator(edge_weight, texture_weight, saliency_weight)
    return generator.generate(image)
