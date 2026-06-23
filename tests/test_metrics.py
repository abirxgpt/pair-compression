"""Tests for image quality metrics (metrics.py)."""
import numpy as np
from pawc.metrics import calculate_psnr, calculate_ssim, calculate_ms_ssim


def test_psnr_identical_images():
    """PSNR on identical images should be inf or very high."""
    img = np.ones((100, 100, 3), dtype=np.uint8) * 128
    psnr = calculate_psnr(img, img)
    assert psnr == float("inf") or psnr > 100, f"PSNR = {psnr}"


def test_psnr_range():
    """Small noise should produce PSNR in reasonable range."""
    img = np.ones((100, 100, 3), dtype=np.uint8) * 128
    rng = np.random.RandomState(42)
    noise = rng.randint(-10, 11, size=img.shape).astype(np.int16)
    noisy = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    psnr = calculate_psnr(img, noisy)
    assert 20 < psnr < 50, f"PSNR out of range: {psnr:.2f}"


def test_ssim_identical_images():
    """SSIM on identical images should be near 1.0."""
    img = np.ones((100, 100, 3), dtype=np.uint8) * 128
    ssim = calculate_ssim(img, img)
    assert ssim > 0.99, f"SSIM = {ssim:.4f}"


def test_ms_ssim_identical_images():
    """MS-SSIM on identical images should be near 1.0."""
    img = np.ones((128, 128, 3), dtype=np.uint8) * 128
    ms_ssim = calculate_ms_ssim(img, img)
    assert ms_ssim > 0.99, f"MS-SSIM = {ms_ssim:.4f}"


def test_ssim_range():
    """SSIM on noisy images should be in sane range."""
    img = np.ones((100, 100, 3), dtype=np.uint8) * 128
    rng = np.random.RandomState(42)
    noise = rng.randint(-30, 31, size=img.shape).astype(np.int16)
    noisy = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    ssim = calculate_ssim(img, noisy)
    assert 0.1 < ssim < 0.95, f"SSIM out of range: {ssim:.4f}"
