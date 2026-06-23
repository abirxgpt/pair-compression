"""Tests for PAIR codec (pair_codec.py) — glymur and pillow backends."""
import os
import pytest
import numpy as np
from PIL import Image

from pawc.pair_codec import PAIRCodec
from pawc.metrics import calculate_psnr


KODAK_DIR = "kodak_dataset"
KODAK_01 = os.path.join(KODAK_DIR, "kodim01.png")
KODAK_15 = os.path.join(KODAK_DIR, "kodim15.png")

requires_kodak = pytest.mark.skipif(
    not os.path.exists(KODAK_01),
    reason="Kodak dataset not found. Download to kodak_dataset/ first."
)


@requires_kodak
def test_glymur_encoder_produces_valid_file():
    """Encode with glymur: files exist, have different sizes."""
    img1 = np.array(Image.open(KODAK_01).convert("RGB"))
    img2 = np.array(Image.open(KODAK_15).convert("RGB"))
    codec = PAIRCodec(use_glymur=True)

    out1 = "_test_glymur_kodim01.jp2"
    out2 = "_test_glymur_kodim15.jp2"

    try:
        compressed1, meta1 = codec.compress(img1, quality=70, output_path=out1)
        assert os.path.exists(out1)
        size1 = os.path.getsize(out1)
        assert size1 > 0

        compressed2, meta2 = codec.compress(img2, quality=70, output_path=out2)
        assert os.path.exists(out2)
        size2 = os.path.getsize(out2)
        assert size2 > 0

        # Different images should produce different sizes
        assert size1 != size2, (
            f"Expected different sizes, got {size1} and {size2}"
        )
    finally:
        for p in [out1, out2]:
            if os.path.exists(p):
                os.remove(p)


@requires_kodak
def test_glymur_encoder_roundtrip():
    """Encode then decode — shape match and reasonable PSNR."""
    img = np.array(Image.open(KODAK_01).convert("RGB"))
    codec = PAIRCodec(use_glymur=True)
    out = "_test_roundtrip.jp2"

    try:
        compressed, meta = codec.compress(img, quality=70, output_path=out)
        decoded = codec.decompress(compressed, input_path=out)

        assert decoded.shape == img.shape, (
            f"Shape mismatch: {decoded.shape} vs {img.shape}"
        )
        psnr = calculate_psnr(img, decoded)
        assert psnr > 25, f"PSNR too low: {psnr:.2f} dB"
    finally:
        if os.path.exists(out):
            os.remove(out)


@requires_kodak
def test_pillow_encoder_still_works():
    """Old Pillow backend still functional with use_glymur=False."""
    img = np.array(Image.open(KODAK_01).convert("RGB"))
    codec = PAIRCodec(use_glymur=False)

    # Pillow path returns compressed bytes directly (no file output)
    compressed, meta = codec.compress(img, quality=70)
    assert compressed is not None
    assert len(compressed) > 0
    assert meta["codec"] == "PAIR"

    # Decode should also work
    decoded = codec.decompress(compressed)
    assert decoded.shape == img.shape
