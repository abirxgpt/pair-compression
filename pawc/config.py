"""
Configuration module for PAWC compression algorithm.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class CompressionConfig:
    """Configuration parameters for PAWC compression."""
    
    # Quality parameter (1-100, higher = better quality)
    quality: int = 85
    
    # Perceptual importance map weights
    edge_weight: float = 0.4  # α - edge strength weight
    texture_weight: float = 0.3  # β - texture complexity weight
    saliency_weight: float = 0.3  # γ - visual saliency weight
    
    # Wavelet transform parameters
    block_size: int = 16  # OPTIMIZED: Reduced from 64 for better compression
    max_wavelet_level: int = 3  # Reduced from 4 to match smaller blocks
    wavelet_bases: Tuple[str, ...] = ('haar', 'db4', 'bior4.4')  # Available wavelets
    
    # Quantization parameters
    base_quantization: float = None  # Auto-calculated from quality if None
    adaptation_strength: float = 0.5  # OPTIMIZED: Reduced from 2.0 to minimize importance effect
    
    # ML quantization optimizer
    use_ml_quantization: bool = True  # Enable/disable ML optimizer
    
    # Entropy coding
    use_arithmetic_coding: bool = True  # Use arithmetic vs. Huffman coding
    
    # Performance
    n_jobs: int = -1  # Number of parallel jobs (-1 = all CPUs)
    
    def __post_init__(self):
        """Validate and auto-calculate parameters."""
        if not 1 <= self.quality <= 100:
            raise ValueError("Quality must be between 1 and 100")
        
        # Auto-calculate base quantization from quality
        if self.base_quantization is None:
            # OPTIMIZED: Less aggressive quantization
            # Quality 100 → Q=2, Quality 90 → Q=12, Quality 70 → Q=32, Quality 50 → Q=52
            self.base_quantization = max(2, 102 - self.quality)
        
        # Validate weights sum to 1.0 (approximately)
        weight_sum = self.edge_weight + self.texture_weight + self.saliency_weight
        if not 0.99 <= weight_sum <= 1.01:
            # Normalize weights
            self.edge_weight /= weight_sum
            self.texture_weight /= weight_sum
            self.saliency_weight /= weight_sum
    
    @classmethod
    def preset_high_quality(cls) -> 'CompressionConfig':
        """High quality preset (quality=95)."""
        return cls(quality=95)
    
    @classmethod
    def preset_balanced(cls) -> 'CompressionConfig':
        """Balanced preset (quality=85)."""
        return cls(quality=85)
    
    @classmethod
    def preset_high_compression(cls) -> 'CompressionConfig':
        """High compression preset (quality=70)."""
        return cls(quality=70)
