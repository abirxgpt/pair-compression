"""
Adaptive Wavelet Transform module.

Implements block-wise wavelet basis selection and multi-resolution decomposition.
"""

import numpy as np
import pywt
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass


@dataclass
class WaveletBlock:
    """Information about a wavelet-transformed block."""
    coeffs: Tuple  # Wavelet coefficients
    wavelet: str  # Selected wavelet basis
    level: int  # Decomposition level
    position: Tuple[int, int]  # (row, col) position in image
    shape: Tuple[int, int]  # Block shape


class AdaptiveWaveletTransform:
    """Adaptive wavelet transform with block-wise basis selection."""
    
    def __init__(self, block_size: int = 64,
                 max_level: int = 4,
                 wavelet_bases: Tuple[str, ...] = ('haar', 'db4', 'bior4.4'),
                 lambda_rd: float = 0.1):
        """
        Initialize adaptive wavelet transform.
        
        Args:
            block_size: Size of blocks for adaptive selection
            max_level: Maximum wavelet decomposition level
            wavelet_bases: Available wavelet bases to choose from
            lambda_rd: Lagrangian multiplier for rate-distortion optimization
        """
        self.block_size = block_size
        self.max_level = max_level
        self.wavelet_bases = wavelet_bases
        self.lambda_rd = lambda_rd
    
    def forward(self, image: np.ndarray, 
                importance_map: Optional[np.ndarray] = None) -> List[WaveletBlock]:
        """
        Apply adaptive wavelet transform to image.
        
        Args:
            image: Input image (H, W) or (H, W, C)
            importance_map: Optional importance map for adaptive level selection
        
        Returns:
            List of WaveletBlock objects
        """
        # Handle color images by processing each channel
        if len(image.shape) == 3:
            blocks = []
            for c in range(image.shape[2]):
                channel_blocks = self._forward_channel(
                    image[:, :, c], 
                    importance_map,
                    channel_idx=c
                )
                blocks.extend(channel_blocks)
            return blocks
        else:
            return self._forward_channel(image, importance_map)
    
    def _forward_channel(self, channel: np.ndarray,
                        importance_map: Optional[np.ndarray] = None,
                        channel_idx: int = 0) -> List[WaveletBlock]:
        """Apply transform to a single channel."""
        h, w = channel.shape
        blocks = []
        
        # Pad to multiple of block_size
        pad_h = (self.block_size - h % self.block_size) % self.block_size
        pad_w = (self.block_size - w % self.block_size) % self.block_size
        
        if pad_h > 0 or pad_w > 0:
            channel = np.pad(channel, ((0, pad_h), (0, pad_w)), mode='reflect')
            if importance_map is not None:
                importance_map = np.pad(importance_map, 
                                       ((0, pad_h), (0, pad_w)), 
                                       mode='reflect')
        
        h_padded, w_padded = channel.shape
        
        # Process blocks
        for i in range(0, h_padded, self.block_size):
            for j in range(0, w_padded, self.block_size):
                block = channel[i:i+self.block_size, j:j+self.block_size]
                
                # Select optimal wavelet and level
                if importance_map is not None:
                    imp_block = importance_map[i:i+self.block_size, j:j+self.block_size]
                    avg_importance = np.mean(imp_block)
                else:
                    avg_importance = 0.5
                
                wavelet, level = self._select_wavelet_and_level(block, avg_importance)
                
                # Apply wavelet transform
                coeffs = pywt.wavedec2(block, wavelet, level=level)
                
                # Store block info
                blocks.append(WaveletBlock(
                    coeffs=coeffs,
                    wavelet=wavelet,
                    level=level,
                    position=(i, j),
                    shape=block.shape
                ))
        
        return blocks
    
    def _select_wavelet_and_level(self, block: np.ndarray, 
                                  importance: float) -> Tuple[str, int]:
        """
        Select optimal wavelet basis and decomposition level.
        
        Uses rate-distortion optimization:
        W* = argmin_W { E_block + λ·C_block }
        
        Args:
            block: Image block
            importance: Average importance of block
        
        Returns:
            (wavelet_name, decomposition_level)
        """
        best_wavelet = self.wavelet_bases[0]
        best_cost = float('inf')
        
        # Determine decomposition level based on importance
        # Higher importance → more detail preservation → higher level
        level = min(self.max_level, max(1, int(1 + importance * (self.max_level - 1))))
        
        # Try each wavelet basis
        for wavelet in self.wavelet_bases:
            try:
                # Transform
                coeffs = pywt.wavedec2(block, wavelet, level=level)
                
                # Reconstruct
                reconstructed = pywt.waverec2(coeffs, wavelet)
                
                # Handle size mismatch due to wavelet boundaries
                reconstructed = reconstructed[:block.shape[0], :block.shape[1]]
                
                # Compute reconstruction error
                error = np.mean((block - reconstructed) ** 2)
                
                # Compute coefficient entropy (complexity)
                coeffs_flat = np.concatenate([c.ravel() for c in pywt.coeffs_to_array(coeffs)[0]])
                entropy = self._compute_entropy(coeffs_flat)
                
                # Rate-distortion cost
                cost = error + self.lambda_rd * entropy
                
                if cost < best_cost:
                    best_cost = cost
                    best_wavelet = wavelet
            except:
                # Skip if wavelet fails for this block
                continue
        
        return best_wavelet, level
    
    @staticmethod
    def _compute_entropy(coeffs: np.ndarray, num_bins: int = 256) -> float:
        """Compute Shannon entropy of coefficients."""
        # Quantize to bins
        if len(coeffs) == 0:
            return 0.0
        
        hist, _ = np.histogram(coeffs, bins=num_bins)
        hist = hist[hist > 0]  # Remove zero bins
        
        # Normalize
        probs = hist / hist.sum()
        
        # Compute entropy
        entropy = -np.sum(probs * np.log2(probs + 1e-10))
        
        return entropy
    
    def inverse(self, blocks: List[WaveletBlock], 
                output_shape: Tuple[int, ...]) -> np.ndarray:
        """
        Reconstruct image from wavelet blocks.
        
        Args:
            blocks: List of WaveletBlock objects
            output_shape: Desired output shape (H, W) or (H, W, C)
        
        Returns:
            Reconstructed image
        """
        if len(output_shape) == 3:
            # Color image
            h, w, c = output_shape
            reconstructed = np.zeros((h, w, c), dtype=np.float32)
            
            # Group blocks by channel
            blocks_per_channel = len(blocks) // c
            
            for ch in range(c):
                channel_blocks = blocks[ch * blocks_per_channel:(ch + 1) * blocks_per_channel]
                reconstructed[:, :, ch] = self._inverse_channel(channel_blocks, (h, w))
        else:
            # Grayscale image
            reconstructed = self._inverse_channel(blocks, output_shape)
        
        return reconstructed
    
    def _inverse_channel(self, blocks: List[WaveletBlock],
                        output_shape: Tuple[int, int]) -> np.ndarray:
        """Reconstruct a single channel."""
        h, w = output_shape
        
        # Determine padded size
        pad_h = (self.block_size - h % self.block_size) % self.block_size
        pad_w = (self.block_size - w % self.block_size) % self.block_size
        h_padded = h + pad_h
        w_padded = w + pad_w
        
        # Initialize output
        channel = np.zeros((h_padded, w_padded), dtype=np.float32)
        
        # Reconstruct each block
        for block_info in blocks:
            i, j = block_info.position
            
            # Inverse wavelet transform
            reconstructed_block = pywt.waverec2(block_info.coeffs, block_info.wavelet)
            
            # Handle size mismatch
            reconstructed_block = reconstructed_block[:block_info.shape[0], 
                                                     :block_info.shape[1]]
            
            # Place in output
            channel[i:i+block_info.shape[0], j:j+block_info.shape[1]] = reconstructed_block
        
        # Remove padding
        return channel[:h, :w]


def apply_adaptive_wavelet(image: np.ndarray,
                          importance_map: Optional[np.ndarray] = None,
                          block_size: int = 64,
                          max_level: int = 4) -> List[WaveletBlock]:
    """
    Convenience function for adaptive wavelet transform.
    
    Args:
        image: Input image
        importance_map: Optional importance map
        block_size: Block size for adaptive selection
        max_level: Maximum decomposition level
    
    Returns:
        List of WaveletBlock objects
    """
    transform = AdaptiveWaveletTransform(block_size=block_size, max_level=max_level)
    return transform.forward(image, importance_map)
