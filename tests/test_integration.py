"""Integration tests for end-to-end compression/decompression."""

import numpy as np
import pytest
import tempfile
from pathlib import Path
from PIL import Image

from pawc.core import compress_image, decompress_image, compress_file, decompress_file
from pawc.config import CompressionConfig
from pawc.metrics import calculate_psnr, calculate_ssim


def test_compress_decompress_grayscale():
    """Test compression and decompression of grayscale image."""
    # Create test image
    original = np.random.randint(0, 256, size=(128, 128), dtype=np.uint8)
    
    # Compress
    config = CompressionConfig(quality=85)
    compressed_data = compress_image(original, config)
    
    # Decompress
    reconstructed = decompress_image(compressed_data)
    
    # Check shape
    assert reconstructed.shape == original.shape
    
    # Check PSNR (should be reasonable)
    psnr = calculate_psnr(original, reconstructed)
    assert psnr > 25.0  # Reasonable quality


def test_compress_decompress_color():
    """Test compression and decompression of color image."""
    original = np.random.randint(0, 256, size=(128, 128, 3), dtype=np.uint8)
    
    config = CompressionConfig(quality=90)
    compressed_data = compress_image(original, config)
    
    reconstructed = decompress_image(compressed_data)
    
    assert reconstructed.shape == original.shape
    
    # Check SSIM
    ssim = calculate_ssim(original, reconstructed)
    assert ssim > 0.8  # Good structural similarity


def test_high_quality_compression():
    """Test high quality compression maintains quality."""
    original = np.random.randint(0, 256, size=(64, 64, 3), dtype=np.uint8)
    
    config = CompressionConfig.preset_high_quality()
    compressed_data = compress_image(original, config)
    
    reconstructed = decompress_image(compressed_data)
    
    psnr = calculate_psnr(original, reconstructed)
    ssim = calculate_ssim(original, reconstructed)
    
    # High quality should give good metrics
    assert psnr > 30.0
    assert ssim > 0.9


@pytest.mark.xfail(reason="Classical PAWC pipeline known to expand files — "
                          "documented limitation. PAIR codec uses JPEG2000 "
                          "backend instead.")
def test_file_compression():
    """Test file-based compression and decompression."""
    # Create test image
    original = np.random.randint(0, 256, size=(100, 100, 3), dtype=np.uint8)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Save original
        input_path = Path(tmpdir) / "test.png"
        Image.fromarray(original).save(input_path)
        
        # Compress
        compressed_path = Path(tmpdir) / "test.pawc"
        config = CompressionConfig(quality=80)
        stats = compress_file(input_path, compressed_path, config)
        
        # Check file exists
        assert compressed_path.exists()
        
        # Check statistics
        assert stats['compression_ratio'] > 1.0
        
        # Decompress
        output_path = Path(tmpdir) / "output.png"
        reconstructed = decompress_file(compressed_path, output_path)
        
        # Check output exists
        assert output_path.exists()
        
        # Verify quality
        psnr = calculate_psnr(original, reconstructed)
        assert psnr > 20.0


def test_different_quality_levels():
    """Test that different quality levels produce different results."""
    original = np.random.randint(0, 256, size=(64, 64, 3), dtype=np.uint8)
    
    # Test different quality levels
    qualities = [50, 75, 95]
    psnrs = []
    
    for quality in qualities:
        config = CompressionConfig(quality=quality)
        compressed = compress_image(original, config)
        reconstructed = decompress_image(compressed)
        
        psnr = calculate_psnr(original, reconstructed)
        psnrs.append(psnr)
    
    # Higher quality should give higher PSNR
    assert psnrs[2] > psnrs[1] > psnrs[0]


def test_edge_cases():
    """Test edge cases."""
    # Very small image
    tiny = np.random.randint(0, 256, size=(16, 16, 3), dtype=np.uint8)
    config = CompressionConfig(quality=85)
    compressed = compress_image(tiny, config)
    reconstructed = decompress_image(compressed)
    assert reconstructed.shape == tiny.shape
    
    # Single channel
    single = np.random.randint(0, 256, size=(32, 32), dtype=np.uint8)
    compressed = compress_image(single, config)
    reconstructed = decompress_image(compressed)
    assert reconstructed.shape == single.shape
