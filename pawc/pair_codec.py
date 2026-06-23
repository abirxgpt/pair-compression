"""
PAIR: Perceptual Adaptive Importance-guided ROI Compression

Novel algorithm combining multi-component perceptual importance maps
with JPEG 2000's Region of Interest (ROI) coding for competitive performance.
"""

import numpy as np
from PIL import Image
from pathlib import Path
from typing import Tuple, Optional
import io
import os
import tempfile

from pawc.importance_map import ImportanceMapGenerator
from pawc.jpeg2000_backend import GlymurROIEncoder
from pawc.config import CompressionConfig


class PAIRCodec:
    """
    PAIR: Perceptual Adaptive Importance-guided ROI compression.
    
    Key Innovation: Multi-component importance maps (edge + texture + saliency)
    are used to automatically generate ROI masks for JPEG 2000 encoding,
    allocating quality based on perceptual importance.
    """
    
    def __init__(self, config: Optional[CompressionConfig] = None,
                 use_glymur: bool = True):
        """
        Initialize PAIR codec.

        Args:
            config: Compression configuration
            use_glymur: If True, use tile-based glymur/OpenJPEG ROI encoder.
                        If False, use old Pillow global-quality encoder.
        """
        self.config = config or CompressionConfig()
        self.use_glymur = use_glymur
        self.importance_gen = ImportanceMapGenerator(
            edge_weight=self.config.edge_weight,
            texture_weight=self.config.texture_weight,
            saliency_weight=self.config.saliency_weight
        )
        if use_glymur:
            self.glymur_encoder = GlymurROIEncoder(tile_size=64)
    
    def _generate_roi_tiers(self, importance_map: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Convert continuous importance map to 3-tier ROI masks.
        
        Args:
            importance_map: Continuous importance values [0, 1]
        
        Returns:
            (high_roi, med_roi, low_roi) binary masks
        """
        # OPTIMIZED: Adjusted tier percentiles for better quality distribution
        # High tier: top 15% importance (more selective)
        p_high = np.percentile(importance_map, 85)
        # Medium tier: 40th-85th percentile (wider middle range)
        p_med = np.percentile(importance_map, 40)
        
        high_roi = importance_map > p_high
        med_roi = (importance_map > p_med) & ~high_roi
        low_roi = ~(high_roi | med_roi)
        
        return high_roi, med_roi, low_roi
    
    def _encode_pillow_roi(self, image: np.ndarray, high_roi: np.ndarray, 
                           med_roi: np.ndarray, quality: int) -> bytes:
        """
        Encode with ROI using Pillow's JPEG 2000 (simpler approach).
        
        Since glymur's Maxshift ROI is complex, we use a simpler tiling approach:
        - Encode full image at base quality
        - Overlay high-quality tiles for important regions
        """
        height, width = image.shape[:2]
        
        # OPTIMIZED: More aggressive quality boosting for important regions
        base_quality = quality
        high_quality = min(100, base_quality + 20)  # Stronger boost for salient regions
        low_quality = max(15, base_quality - 15)    # Less aggressive reduction for background
        
        # Create quality map
        quality_map = np.full((height, width), base_quality, dtype=np.uint8)
        quality_map[high_roi] = high_quality
        quality_map[med_roi] = base_quality
        quality_map[~(high_roi | med_roi)] = low_quality  # Low ROI is everything else
        
        # For now, use average quality (weighted by importance)
        # More sophisticated: use quality map for rate control
        importance_weights = np.zeros_like(quality_map, dtype=float)
        importance_weights[high_roi] = 4.0  # OPTIMIZED: Stronger weighting for salient regions
        importance_weights[med_roi] = 1.5    # Medium bump
        importance_weights[~(high_roi | med_roi)] = 0.3  # Aggressive compression for background
        
        effective_quality = int(np.average(quality_map, weights=importance_weights))
        
        # Encode with JPEG 2000
        pil_img = Image.fromarray(image)
        buffer = io.BytesIO()
        
        # Map quality (1-100) to compression ratio
        # Quality 100 → ratio 5:1, Quality 50 → ratio 20:1
        compression_ratio = max(5, 105 - effective_quality)
        
        pil_img.save(
            buffer,
            format='JPEG2000',
            quality_mode='rates',
            quality_layers=[compression_ratio],
            irreversible=True,
            progression='RPCL'
        )
        
        return buffer.getvalue()
    
    def compress(self, image: np.ndarray, quality: int = 85,
                 output_path: Optional[str] = None) -> Tuple[bytes, dict]:
        """
        Compress image using PAIR algorithm.

        Args:
            image: Input image (HxWxC numpy array)
            quality: Base quality level (1-100)
            output_path: Optional output path (used by glymur path)

        Returns:
            (compressed_bytes, metadata)
        """
        height, width = image.shape[:2]
        channels = image.shape[2] if len(image.shape) == 3 else 1

        # Step 1: Generate perceptual importance map (NOVEL CONTRIBUTION)
        importance_map = self.importance_gen.generate(image)

        # Step 2: Encode based on backend
        if self.use_glymur:
            import tempfile
            # Glymur path: tile-based per-region quality
            if output_path:
                out_path = output_path
                cleanup_out = False
            else:
                tmp = tempfile.NamedTemporaryFile(suffix='.jp2', delete=False)
                out_path = tmp.name
                tmp.close()
                cleanup_out = True

            try:
                enc_metadata = self.glymur_encoder.encode(
                    image, importance_map, quality, out_path)
                with open(out_path, 'rb') as f:
                    compressed_data = f.read()
            finally:
                if cleanup_out and os.path.exists(out_path):
                    os.unlink(out_path)

            metadata = {
                'width': width, 'height': height, 'channels': channels,
                'quality': quality,
                'codec': 'PAIR-glymur',
                'backend': 'glymur-tile-roi',
                'tile_stats': {
                    'num_tiles': enc_metadata['num_tiles'],
                    'high_tiles': enc_metadata['high_tiles'],
                    'med_tiles': enc_metadata['med_tiles'],
                    'low_tiles': enc_metadata['low_tiles'],
                    'mean_cratio': enc_metadata['cratio_mean'],
                },
                'importance_stats': {
                    'mean': enc_metadata['imp_mean'],
                    'std': enc_metadata['imp_std'],
                },
                'compressed_size': enc_metadata['compressed_size'],
            }
        else:
            # Old Pillow path: global quality averaging
            high_roi, med_roi, low_roi = self._generate_roi_tiers(importance_map)
            compressed_data = self._encode_pillow_roi(image, high_roi, med_roi, quality)

            total_pixels = height * width
            high_percent = (np.sum(high_roi) / total_pixels) * 100
            med_percent = (np.sum(med_roi) / total_pixels) * 100
            low_percent = (np.sum(low_roi) / total_pixels) * 100

            metadata = {
                'width': width, 'height': height, 'channels': channels,
                'quality': quality,
                'codec': 'PAIR',
                'backend': 'pillow-global',
                'tier_distribution': {
                    'high': f'{high_percent:.1f}%',
                    'medium': f'{med_percent:.1f}%',
                    'low': f'{low_percent:.1f}%'
                },
                'importance_stats': {
                    'mean': float(np.mean(importance_map)),
                    'std': float(np.std(importance_map)),
                    'min': float(np.min(importance_map)),
                    'max': float(np.max(importance_map))
                }
            }

        return compressed_data, metadata
    
    def decompress(self, compressed_data: bytes,
                   input_path: Optional[str] = None) -> np.ndarray:
        """
        Decompress PAIR-compressed image.

        Args:
            compressed_data: Compressed bytes (Pillow path) or raw file bytes
            input_path: Path to compressed file (needed for glymur path since
                        glymur reads tile JP2 data from file offsets)

        Returns:
            Decompressed image array
        """
        # Detect format: glymur PAIR container starts with b'PAIR'
        if compressed_data[:4] == b'PAIR':
            # Glymur tile-based container
            if input_path and os.path.exists(input_path):
                return self.glymur_encoder.decode(input_path)
            else:
                # Write bytes to temp file for decode
                tmp = tempfile.NamedTemporaryFile(suffix='.jp2', delete=False)
                try:
                    tmp.write(compressed_data)
                    tmp.close()
                    return self.glymur_encoder.decode(tmp.name)
                finally:
                    if os.path.exists(tmp.name):
                        os.unlink(tmp.name)
        else:
            # Old Pillow JP2 path
            img = Image.open(io.BytesIO(compressed_data))
            return np.array(img)


def compress_file_pair(input_path: str, output_path: str, 
                       config: Optional[CompressionConfig] = None) -> dict:
    """
    Compress image file using PAIR algorithm.
    
    Args:
        input_path: Input image path
        output_path: Output .jp2 file path
        config: Compression configuration
    
    Returns:
        Compression statistics dictionary
    """
    config = config or CompressionConfig()
    codec = PAIRCodec(config)
    
    # Load image
    image = np.array(Image.open(input_path))
    original_size = Path(input_path).stat().st_size
    
    # Compress
    compressed_data, metadata = codec.compress(image, config.quality,
                                                output_path=output_path)
    
    # Save
    with open(output_path, 'wb') as f:
        f.write(compressed_data)
    
    compressed_size = len(compressed_data)
    
    print(f"[PAIR] Compression complete:")
    print(f"  Original: {original_size:,} bytes")
    print(f"  Compressed: {compressed_size:,} bytes")
    print(f"  Ratio: {original_size/compressed_size:.2f}:1")
    print(f"  Tier distribution: {metadata['tier_distribution']}")
    
    return {
        'original_size': original_size,
        'compressed_size': compressed_size,
        'compression_ratio': original_size / compressed_size,
        'metadata': metadata
    }


def decompress_file_pair(input_path: str, output_path: str) -> np.ndarray:
    """
    Decompress PAIR file.
    
    Args:
        input_path: Input .jp2 file
        output_path: Output image path
    
    Returns:
        Decompressed image array
    """
    codec = PAIRCodec()
    
    with open(input_path, 'rb') as f:
        compressed_data = f.read()
    
    image = codec.decompress(compressed_data, input_path=input_path)
    
    # Save decompressed image
    Image.fromarray(image).save(output_path)
    
    return image
