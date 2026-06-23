"""
Quality metrics for image compression evaluation.

Implements PSNR, SSIM, and MS-SSIM metrics.
"""

import numpy as np
from scipy import signal
from scipy.ndimage import gaussian_filter
from typing import Tuple


def calculate_psnr(original: np.ndarray, compressed: np.ndarray, 
                  max_value: float = 255.0) -> float:
    """
    Calculate Peak Signal-to-Noise Ratio (PSNR).
    
    Args:
        original: Original image
        compressed: Compressed/reconstructed image
        max_value: Maximum possible pixel value
    
    Returns:
        PSNR in dB
    """
    mse = np.mean((original - compressed) ** 2)
    
    if mse == 0:
        return float('inf')
    
    psnr = 20 * np.log10(max_value / np.sqrt(mse))
    return psnr


def calculate_ssim(original: np.ndarray, compressed: np.ndarray,
                  max_value: float = 255.0,
                  window_size: int = 11,
                  k1: float = 0.01,
                  k2: float = 0.03) -> float:
    """
    Calculate Structural Similarity Index (SSIM).
    
    Based on: "Image Quality Assessment: From Error Visibility to Structural Similarity"
    (Wang et al., 2004)
    
    Args:
        original: Original image
        compressed: Compressed/reconstructed image
        max_value: Maximum possible pixel value
        window_size: Size of Gaussian window
        k1, k2: Stability constants
    
    Returns:
        SSIM value in range [-1, 1], closer to 1 is better
    """
    # Convert to float
    img1 = original.astype(np.float64)
    img2 = compressed.astype(np.float64)
    
    # Handle multi-channel images
    if len(img1.shape) == 3:
        ssim_channels = []
        for c in range(img1.shape[2]):
            ssim_c = _ssim_single_channel(
                img1[:, :, c], img2[:, :, c],
                max_value, window_size, k1, k2
            )
            ssim_channels.append(ssim_c)
        return np.mean(ssim_channels)
    else:
        return _ssim_single_channel(img1, img2, max_value, window_size, k1, k2)


def _ssim_single_channel(img1: np.ndarray, img2: np.ndarray,
                        max_value: float, window_size: int,
                        k1: float, k2: float) -> float:
    """Calculate SSIM for a single channel."""
    # Constants
    c1 = (k1 * max_value) ** 2
    c2 = (k2 * max_value) ** 2
    
    # Gaussian window
    sigma = 1.5
    window = _gaussian_window(window_size, sigma)
    
    # Normalize window
    window = window / np.sum(window)
    
    # Compute local statistics using convolution
    mu1 = signal.correlate2d(img1, window, mode='valid')
    mu2 = signal.correlate2d(img2, window, mode='valid')
    
    mu1_sq = mu1 ** 2
    mu2_sq = mu2 ** 2
    mu1_mu2 = mu1 * mu2
    
    sigma1_sq = signal.correlate2d(img1 ** 2, window, mode='valid') - mu1_sq
    sigma2_sq = signal.correlate2d(img2 ** 2, window, mode='valid') - mu2_sq
    sigma12 = signal.correlate2d(img1 * img2, window, mode='valid') - mu1_mu2
    
    # SSIM formula
    ssim_map = ((2 * mu1_mu2 + c1) * (2 * sigma12 + c2)) / \
               ((mu1_sq + mu2_sq + c1) * (sigma1_sq + sigma2_sq + c2))
    
    return np.mean(ssim_map)


def calculate_ms_ssim(original: np.ndarray, compressed: np.ndarray,
                     max_value: float = 255.0,
                     weights: Tuple[float, ...] = (0.0448, 0.2856, 0.3001, 0.2363, 0.1333)) -> float:
    """
    Calculate Multi-Scale Structural Similarity Index (MS-SSIM).
    
    Based on: "Multi-scale structural similarity for image quality assessment"
    (Wang et al., 2003)
    
    Args:
        original: Original image
        compressed: Compressed/reconstructed image
        max_value: Maximum possible pixel value
        weights: Weights for each scale
    
    Returns:
        MS-SSIM value in range [0, 1]
    """
    # Convert to float
    img1 = original.astype(np.float64)
    img2 = compressed.astype(np.float64)
    
    # Handle multi-channel images
    if len(img1.shape) == 3:
        msssim_channels = []
        for c in range(img1.shape[2]):
            msssim_c = _ms_ssim_single_channel(
                img1[:, :, c], img2[:, :, c],
                max_value, weights
            )
            msssim_channels.append(msssim_c)
        return np.mean(msssim_channels)
    else:
        return _ms_ssim_single_channel(img1, img2, max_value, weights)


def _ms_ssim_single_channel(img1: np.ndarray, img2: np.ndarray,
                           max_value: float,
                           weights: Tuple[float, ...]) -> float:
    """Calculate MS-SSIM for a single channel."""
    levels = len(weights)
    mssim = []
    mcs = []
    
    for i in range(levels):
        ssim_val, cs_val = _ssim_with_contrast(img1, img2, max_value)
        mssim.append(ssim_val)
        mcs.append(cs_val)
        
        # Downsample for next level
        if i < levels - 1:
            img1 = _downsample(img1)
            img2 = _downsample(img2)
            
            # Check if images are too small
            if img1.shape[0] < 11 or img1.shape[1] < 11:
                break
    
    # Compute weighted product
    ms_ssim_value = np.prod([mcs[i] ** weights[i] for i in range(len(mcs) - 1)]) * \
                   (mssim[-1] ** weights[len(mcs) - 1])
    
    return ms_ssim_value


def _ssim_with_contrast(img1: np.ndarray, img2: np.ndarray, 
                       max_value: float) -> Tuple[float, float]:
    """Calculate SSIM and contrast comparison separately."""
    window_size = 11
    k1, k2 = 0.01, 0.03
    c1 = (k1 * max_value) ** 2
    c2 = (k2 * max_value) ** 2
    
    sigma = 1.5
    window = _gaussian_window(window_size, sigma)
    window = window / np.sum(window)
    
    mu1 = signal.correlate2d(img1, window, mode='valid')
    mu2 = signal.correlate2d(img2, window, mode='valid')
    
    mu1_sq = mu1 ** 2
    mu2_sq = mu2 ** 2
    mu1_mu2 = mu1 * mu2
    
    sigma1_sq = signal.correlate2d(img1 ** 2, window, mode='valid') - mu1_sq
    sigma2_sq = signal.correlate2d(img2 ** 2, window, mode='valid') - mu2_sq
    sigma12 = signal.correlate2d(img1 * img2, window, mode='valid') - mu1_mu2
    
    # Luminance comparison
    l = (2 * mu1_mu2 + c1) / (mu1_sq + mu2_sq + c1)
    
    # Contrast comparison
    cs = (2 * sigma12 + c2) / (sigma1_sq + sigma2_sq + c2)
    
    # SSIM
    ssim_val = np.mean(l * cs)
    cs_val = np.mean(cs)
    
    return ssim_val, cs_val


def _gaussian_window(size: int, sigma: float) -> np.ndarray:
    """Create 2D Gaussian window."""
    coords = np.arange(size) - (size - 1) / 2
    g = np.exp(-(coords ** 2) / (2 * sigma ** 2))
    g = g / g.sum()
    
    # 2D window
    window = np.outer(g, g)
    return window


def _downsample(img: np.ndarray) -> np.ndarray:
    """Downsample image by factor of 2 using Gaussian filtering."""
    # Apply Gaussian filter
    filtered = gaussian_filter(img, sigma=1.0)
    
    # Subsample
    downsampled = filtered[::2, ::2]
    
    return downsampled


def calculate_compression_ratio(original_size: int, compressed_size: int) -> float:
    """
    Calculate compression ratio.
    
    Args:
        original_size: Size of original file/data in bytes
        compressed_size: Size of compressed file/data in bytes
    
    Returns:
        Compression ratio (original/compressed)
    """
    return original_size / compressed_size


def calculate_bpp(compressed_size: int, width: int, height: int) -> float:
    """
    Calculate bits per pixel.
    
    Args:
        compressed_size: Size of compressed data in bytes
        width: Image width
        height: Image height
    
    Returns:
        Bits per pixel
    """
    total_bits = compressed_size * 8
    total_pixels = width * height
    
    return total_bits / total_pixels
