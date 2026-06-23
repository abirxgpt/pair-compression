"""
PAWC - Perceptual Adaptive Wavelet Compression

A novel image compression algorithm combining perceptual importance modeling,
adaptive wavelet transforms, and ML-based quantization.
"""

__version__ = "0.1.0"
__author__ = "PAWC Development Team"

from .core import compress_image, decompress_image, compress_file, decompress_file
from .config import CompressionConfig
from .metrics import calculate_psnr, calculate_ssim, calculate_ms_ssim

__all__ = [
    "compress_image",
    "decompress_image", 
    "compress_file",
    "decompress_file",
    "CompressionConfig",
    "calculate_psnr",
    "calculate_ssim",
    "calculate_ms_ssim",
]
