"""
PAWC v2: Importance-Weighted JPEG 2000 Encoder

This module integrates JPEG 2000 compression with PAWC's perceptual importance mapping.
Instead of custom wavelets, we use JPEG 2000's optimized codec but guide quality allocation
based on our multi-component importance framework.
"""

import numpy as np
from PIL import Image
from pathlib import Path
from typing import Tuple, Optional
import io
import struct
import os

from .importance_map import ImportanceMapGenerator
from .config import CompressionConfig


class ImportanceWeightedJPEG2000:
    """
    JPEG 2000 encoder with importance-weighted quality allocation.
    
    Novel contribution: Instead of uniform JPEG 2000 quality, we:
    1. Generate perceptual importance map (edge + texture + saliency)
    2. Create importance-based quality tiers
    3. Encode regions at different quality levels
    4. Produce superior perceptual quality for same file size
    """
    
    def __init__(self, config: Optional[CompressionConfig] = None):
        """Initialize encoder with configuration."""
        self.config = config or CompressionConfig()
        self.importance_gen = ImportanceMapGenerator(
            edge_weight=self.config.edge_weight,
            texture_weight=self.config.texture_weight,
            saliency_weight=self.config.saliency_weight
        )
    
    def compress(self, image: np.ndarray, quality: int = 85) -> Tuple[bytes, dict]:
        """
        Compress image using importance-weighted JPEG 2000.
        
        Args:
            image: Input image (H×W×C numpy array)
            quality: Base quality level (1-100)
        
        Returns:
            (compressed_bytes, metadata)
        """
        height, width = image.shape[:2]
        channels = image.shape[2] if len(image.shape) == 3 else 1
        
        # Step 1: Generate importance map
        importance_map = self.importance_gen.generate(image)
        
        # Step 2: Create quality map based on importance
        # High importance → high quality
        # Low importance → lower quality (saves bits!)
        quality_map = self._importance_to_quality_map(importance_map, quality)
        
        # Step 3: Divide image into importance regions
        regions = self._segment_by_importance(importance_map)
        
        # Step 4: Encode using adaptive quality
        if len(regions) > 1:
            # Multi-tier encoding
            compressed = self._encode_multi_tier(image, regions, quality_map, quality)
        else:
            # Fallback to standard JPEG 2000
            compressed = self._encode_standard(image, quality)
        
        metadata = {
            'width': width,
            'height': height,
            'channels': channels,
            'quality': quality,
            'codec': 'jpeg2000_importance_weighted',
            'regions': len(regions)
        }
        
        return compressed, metadata
    
    def decompress(self, compressed_data: bytes) -> np.ndarray:
        """
        Decompress JPEG 2000 image.
        
        Args:
            compressed_data: Compressed bytes
        
        Returns:
            Decompressed image array
        """
        # JPEG 2000 decompression is standard
        img = Image.open(io.BytesIO(compressed_data))
        return np.array(img)
    
    def _importance_to_quality_map(self, importance_map: np.ndarray, base_quality: int) -> np.ndarray:
        """
        Convert importance map to quality allocation map.
        
        High importance regions get quality boost, low importance get reduction.
        """
        # Map importance [0,1] to quality adjustment [-30, +10]
        # This creates significant bitrate savings on unimportant regions
        quality_adjustment = -30 + 40 * importance_map
        
        quality_map = np.clip(base_quality + quality_adjustment, 10, 100)
        
        return quality_map.astype(np.uint8)
    
    def _segment_by_importance(self, importance_map: np.ndarray, num_tiers: int = 3) -> list:
        """
        Segment image into importance tiers.
        
        Returns list of (threshold_min, threshold_max, quality_level) tuples.
        """
        # Divide importance into tiers
        # Tier 1 (High): top 20% importance
        # Tier 2 (Med): middle 50%
        # Tier 3 (Low): bottom 30%
        
        p80 = np.percentile(importance_map, 80)
        p30 = np.percentile(importance_map, 30)
        
        return [
            {'name': 'high', 'min': p80, 'max': 1.0},
            {'name': 'medium', 'min': p30, 'max': p80},
            {'name': 'low', 'min': 0.0, 'max': p30}
        ]
    
    def _encode_multi_tier(self, image: np.ndarray, regions: list, 
                          quality_map: np.ndarray, base_quality: int) -> bytes:
        """
        Encode image with multi-tier quality (EXPERIMENTAL).
        
        For now, we use a simpler approach: average quality based on importance.
        Advanced ROI coding with JPEG 2000 would require more complex integration.
        """
        # Calculate weighted average quality
        # High importance regions contribute more to quality decision
        importance = quality_map / 100.0
        effective_quality = int(np.average(quality_map, weights=importance))
        
        # Encode with effective quality
        return self._encode_standard(image, effective_quality)
    
    def _encode_standard(self, image: np.ndarray, quality: int) -> bytes:
        """
        Standard JPEG 2000 encoding.
        
        Args:
            image: Input image array
            quality: Quality level (1-100)
        
        Returns:
            Compressed JPEG 2000 bytes
        """
        # Convert numpy array to PIL Image
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)
        
        pil_img = Image.fromarray(image)
        
        # Save to JPEG 2000 format
        buffer = io.BytesIO()
        
        # JPEG 2000 parameters
        # quality_mode: 'rates' (bits per pixel) or 'dB' (PSNR target)
        # quality_layers: [target] where target depends on quality parameter
        
        # Map quality (1-100) to JPEG 2000 compression ratio
        # Quality 100 → ratio 5:1, Quality 50 → ratio 20:1, Quality 1 → ratio 100:1
        compression_ratio = max(5, 105 - quality)
        
        pil_img.save(
            buffer,
            format='JPEG2000',
            quality_mode='rates',
            quality_layers=[compression_ratio],
            irreversible=True,  # Lossy (faster)
            progression='RPCL'  # Resolution-Position-Component-Layer
        )
        
        return buffer.getvalue()


def compress_file_j2k(input_path: str, output_path: str, config: Optional[CompressionConfig] = None) -> dict:
    """
    Compress image file using importance-weighted JPEG 2000.
    
    Args:
        input_path: Input image path
        output_path: Output .jp2 or .j2k file path
        config: Compression configuration
    
    Returns:
        Compression statistics dictionary
    """
    config = config or CompressionConfig()
    encoder = ImportanceWeightedJPEG2000(config)
    
    # Load image
    image = np.array(Image.open(input_path))
    original_size = Path(input_path).stat().st_size
    
    # Compress
    compressed_data, metadata = encoder.compress(image, config.quality)
    
    # Save
    with open(output_path, 'wb') as f:
        f.write(compressed_data)
    
    compressed_size = len(compressed_data)
    
    return {
        'original_size': original_size,
        'compressed_size': compressed_size,
        'compression_ratio': original_size / compressed_size,
        'metadata': metadata
    }


def decompress_file_j2k(input_path: str, output_path: str) -> np.ndarray:
    """
    Decompress JPEG 2000 file.
    
    Args:
        input_path: Input .jp2 or .j2k file
        output_path: Output image path
    
    Returns:
        Decompressed image array
    """
    encoder = ImportanceWeightedJPEG2000()
    
    with open(input_path, 'rb') as f:
        compressed_data = f.read()
    
    image = encoder.decompress(compressed_data)
    
    # Save decompressed image
    Image.fromarray(image).save(output_path)

    return image


class GlymurROIEncoder:
    """
    Tile-based ROI encoder using glymur (OpenJPEG) for per-tile quality allocation.

    Unlike the Pillow-based approach which reduces the importance map to a single
    scalar, this encoder divides the image into tiles and encodes each tile at a
    different compression ratio based on its perceptual importance. High-importance
    tiles receive lower compression ratios (higher quality), while low-importance
    tiles are compressed more aggressively.

    Container format (custom binary, NOT valid JP2):
        MAGIC:     4 bytes  b'PAIR'
        VERSION:   4 bytes  uint32 (1)
        IMG_W:     4 bytes  uint32
        IMG_H:     4 bytes  uint32
        CHANNELS:  4 bytes  uint32 (3)
        TILE_SIZE: 4 bytes  uint32 (64)
        NUM_TILES: 4 bytes  uint32
        [NUM_TILES tile entries]:
            row:      4 bytes  uint32
            col:      4 bytes  uint32
            tile_w:   4 bytes  uint32
            tile_h:   4 bytes  uint32
            imp_mean: 4 bytes  float32
            cratio:   4 bytes  float32
            offset:   4 bytes  uint32 (absolute from file start)
            length:   4 bytes  uint32
        [TILE_DATA]: concatenated JP2 bytes
    """

    TILE_SIZE = 64
    MAGIC = b'PAIR'
    VERSION = 1

    QUALITY_TO_BASE_RATIO = {70: 20, 85: 10, 95: 4}

    def __init__(self, tile_size: int = 64):
        self.tile_size = tile_size

    def encode(self, image_array: np.ndarray, importance_map: np.ndarray,
               base_quality: int, output_path: str) -> dict:
        """
        Encode image with tile-based importance-weighted quality allocation.

        Args:
            image_array: Input image HxWx3, uint8
            importance_map: Perceptual importance HxW, float32 in [0, 1]
            base_quality: Base quality level (70, 85, 95)
            output_path: Output file path (.jp2 or custom extension)

        Returns:
            Metadata dict with tile statistics
        """
        import glymur
        import tempfile

        h, w = image_array.shape[:2]
        channels = image_array.shape[2] if image_array.ndim == 3 else 1
        ts = self.tile_size

        # Pad to multiple of tile_size
        pad_h = (ts - h % ts) % ts
        pad_w = (ts - w % ts) % ts

        if pad_h > 0 or pad_w > 0:
            if image_array.ndim == 3:
                image_padded = np.pad(image_array, ((0, pad_h), (0, pad_w), (0, 0)),
                                      mode='reflect')
            else:
                image_padded = np.pad(image_array, ((0, pad_h), (0, pad_w)),
                                      mode='reflect')
            imp_padded = np.pad(importance_map, ((0, pad_h), (0, pad_w)),
                               mode='reflect')
        else:
            image_padded = image_array
            imp_padded = importance_map

        padded_h, padded_w = image_padded.shape[:2]

        # Map base quality to base compression ratio
        base_ratio = self.QUALITY_TO_BASE_RATIO.get(base_quality, 20)

        # Thresholds tuned from per-tile importance statistics:
        #   - Low-activity images: tile_imp peaks ~0.37, mean ~0.13
        #   - High-activity images: tile_imp peaks ~0.47, mean ~0.34
        HI_THRESH = 0.30   # top tiles in diverse images
        MED_THRESH = 0.15  # separates flat backgrounds from textured regions

        # Process tiles: compute importance + cratio, encode each
        tile_entries = []
        tile_jp2_list = []

        for row in range(0, padded_h, ts):
            for col in range(0, padded_w, ts):
                tile_img = image_padded[row:row+ts, col:col+ts]
                tile_imp = imp_padded[row:row+ts, col:col+ts]

                mean_imp = float(np.mean(tile_imp))

                # Assign per-tile compression ratio
                if mean_imp > HI_THRESH:
                    cratio = max(2, base_ratio // 2)     # high quality (gentler)
                elif mean_imp > MED_THRESH:
                    cratio = base_ratio                   # medium quality
                else:
                    cratio = min(60, base_ratio * 3)      # low quality (less aggressive)

                th, tw = tile_img.shape[0], tile_img.shape[1]

                # Create a unique temp path (don't pre-create file)
                tmp_path = os.path.join(
                    tempfile.gettempdir(),
                    f'pair_tile_{row}_{col}_{np.random.randint(0, 999999)}.jp2')

                try:
                    jp2 = glymur.Jp2k(tmp_path, data=tile_img, cratios=[cratio])
                    with open(tmp_path, 'rb') as f:
                        jp2_bytes = f.read()
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

                tile_entries.append({
                    'row': row, 'col': col,
                    'tile_w': tw, 'tile_h': th,
                    'imp_mean': mean_imp,
                    'cratio': cratio,
                    'length': len(jp2_bytes),
                    'data': jp2_bytes
                })
                tile_jp2_list.append(jp2_bytes)

        # Write container
        header_size = 4 + 4 + 4 + 4 + 4 + 4 + 4  # 28 bytes
        tile_entry_size = 4 + 4 + 4 + 4 + 4 + 4 + 4 + 4  # 32 bytes per tile
        tile_map_size = len(tile_entries) * tile_entry_size

        data_start = header_size + tile_map_size

        with open(output_path, 'wb') as f:
            # Header
            f.write(self.MAGIC)
            f.write(struct.pack('<I', self.VERSION))
            f.write(struct.pack('<I', w))       # original width
            f.write(struct.pack('<I', h))       # original height
            f.write(struct.pack('<I', channels))
            f.write(struct.pack('<I', ts))
            f.write(struct.pack('<I', len(tile_entries)))

            # Compute absolute offsets and write tile map
            current_offset = data_start
            for entry in tile_entries:
                offset = current_offset
                length = entry['length']
                f.write(struct.pack('<IIIIffII',
                    entry['row'], entry['col'],
                    entry['tile_w'], entry['tile_h'],
                    entry['imp_mean'], entry['cratio'],
                    offset, length))
                current_offset += length

            # Write all tile data
            for entry in tile_entries:
                f.write(entry['data'])

        # Build metadata
        importances = [e['imp_mean'] for e in tile_entries]
        cratios = [e['cratio'] for e in tile_entries]
        sizes = [e['length'] for e in tile_entries]

        metadata = {
            'width': w, 'height': h, 'channels': channels,
            'tile_size': ts, 'num_tiles': len(tile_entries),
            'base_quality': base_quality, 'base_ratio': base_ratio,
            'imp_mean': float(np.mean(importances)),
            'imp_std': float(np.std(importances)),
            'cratio_mean': float(np.mean(cratios)),
            'cratio_std': float(np.std(cratios)),
            'tile_bytes_mean': float(np.mean(sizes)),
            'tile_bytes_total': int(np.sum(sizes)),
            'compressed_size': int(np.sum(sizes)) + data_start,
            'high_tiles': sum(1 for e in tile_entries if e['imp_mean'] > HI_THRESH),
            'med_tiles': sum(1 for e in tile_entries if MED_THRESH < e['imp_mean'] <= HI_THRESH),
            'low_tiles': sum(1 for e in tile_entries if e['imp_mean'] <= MED_THRESH),
        }

        return metadata

    def decode(self, input_path: str) -> np.ndarray:
        """
        Decode a PAIR tile-container file back to an image array.

        Args:
            input_path: Path to the encoded file

        Returns:
            Reconstructed image as HxWx3 uint8 numpy array
        """
        import glymur
        import tempfile

        with open(input_path, 'rb') as f:
            # Read header
            magic = f.read(4)
            if magic != self.MAGIC:
                raise ValueError(f"Invalid PAIR file: bad magic {magic}")

            version = struct.unpack('<I', f.read(4))[0]
            if version != self.VERSION:
                raise ValueError(f"Unsupported PAIR version: {version}")

            img_w = struct.unpack('<I', f.read(4))[0]
            img_h = struct.unpack('<I', f.read(4))[0]
            channels = struct.unpack('<I', f.read(4))[0]
            tile_size = struct.unpack('<I', f.read(4))[0]
            num_tiles = struct.unpack('<I', f.read(4))[0]

            # Read tile map
            tile_entries = []
            for _ in range(num_tiles):
                row, col, tw, th = struct.unpack('<IIII', f.read(16))
                imp_mean, cratio = struct.unpack('<ff', f.read(8))
                offset, length = struct.unpack('<II', f.read(8))
                tile_entries.append({
                    'row': row, 'col': col, 'tile_w': tw, 'tile_h': th,
                    'imp_mean': imp_mean, 'cratio': cratio,
                    'offset': offset, 'length': length
                })

            # Read tile data and decode
            # Compute padded dimensions
            pad_h = (tile_size - img_h % tile_size) % tile_size
            pad_w = (tile_size - img_w % tile_size) % tile_size
            padded_h = img_h + pad_h
            padded_w = img_w + pad_w

            if channels == 3:
                reconstructed = np.zeros((padded_h, padded_w, 3), dtype=np.uint8)
            else:
                reconstructed = np.zeros((padded_h, padded_w), dtype=np.uint8)

            for entry in tile_entries:
                row, col = entry['row'], entry['col']
                tw, th = entry['tile_w'], entry['tile_h']
                length = entry['length']

                # Read JP2 bytes
                f.seek(entry['offset'])
                jp2_bytes = f.read(length)

                # Write to temp file for glymur decode
                tmp = tempfile.NamedTemporaryFile(suffix='.jp2', delete=False)
                tmp_path = tmp.name
                tmp.write(jp2_bytes)
                tmp.close()

                try:
                    jp2 = glymur.Jp2k(tmp_path)
                    tile = jp2[:]
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

                # Place tile
                if channels == 3:
                    reconstructed[row:row+th, col:col+tw, :] = tile[:th, :tw, :]
                else:
                    reconstructed[row:row+th, col:col+tw] = tile[:th, :tw]

            # Crop padding
            if channels == 3:
                reconstructed = reconstructed[:img_h, :img_w, :]
            else:
                reconstructed = reconstructed[:img_h, :img_w]

        return reconstructed
