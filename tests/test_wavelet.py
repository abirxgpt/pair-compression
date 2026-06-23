"""Tests for adaptive wavelet transform."""

import numpy as np
import pytest
from pawc.wavelet_transform import AdaptiveWaveletTransform, apply_adaptive_wavelet


def test_forward_transform():
    """Test forward wavelet transform."""
    image = np.random.rand(128, 128).astype(np.float32) * 255
    
    transform = AdaptiveWaveletTransform(block_size=64, max_level=3)
    blocks = transform.forward(image)
    
    # Should have multiple blocks
    assert len(blocks) > 0
    
    # Each block should have coefficients
    for block in blocks:
        assert block.coeffs is not None
        assert block.wavelet in ('haar', 'db4', 'bior4.4')
        assert 1 <= block.level <= 3


def test_inverse_transform():
    """Test inverse wavelet transform."""
    image = np.random.rand(64, 64).astype(np.float32) * 255
    
    transform = AdaptiveWaveletTransform(block_size=64, max_level=2)
    
    # Forward
    blocks = transform.forward(image)
    
    # Inverse
    reconstructed = transform.inverse(blocks, image.shape)
    
    # Check shape
    assert reconstructed.shape == image.shape
    
    # Check reconstruction quality (should be very close)
    mse = np.mean((image - reconstructed) ** 2)
    assert mse < 1.0  # Low error


def test_color_image_transform():
    """Test transform on color images."""
    image = np.random.rand(64, 64, 3).astype(np.float32) * 255
    
    transform = AdaptiveWaveletTransform(block_size=32, max_level=2)
    blocks = transform.forward(image)
    
    # Should have blocks for each channel
    assert len(blocks) > 3
    
    # Inverse
    reconstructed = transform.inverse(blocks, image.shape)
    
    assert reconstructed.shape == image.shape


def test_with_importance_map():
    """Test adaptive selection with importance map."""
    image = np.random.rand(64, 64).astype(np.float32) * 255
    importance_map = np.random.rand(64, 64).astype(np.float32)
    
    transform = AdaptiveWaveletTransform(block_size=64, max_level=3)
    blocks = transform.forward(image, importance_map)
    
    assert len(blocks) > 0
    
    # With importance map, levels might vary
    levels = [block.level for block in blocks]
    assert min(levels) >= 1
    assert max(levels) <= 3
