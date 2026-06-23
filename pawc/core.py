"""
Core compression/decompression pipeline for PAWC algorithm.

This module orchestrates the entire compression process.
"""

import numpy as np
from PIL import Image
import os
from typing import Optional, Union
from pathlib import Path

from .config import CompressionConfig
from .importance_map import ImportanceMapGenerator
from .wavelet_transform import AdaptiveWaveletTransform
from .quantization import ImportanceWeightedQuantizer
from .binary_codec import EfficientBinaryCodec


def compress_image(image: np.ndarray, 
                  config: Optional[CompressionConfig] = None) -> dict:
    """
    Compress an image using the PAWC algorithm.
    
    Args:
        image: Input image as numpy array (H, W, C) in range [0, 255]
        config: Compression configuration (uses defaults if None)
    
    Returns:
        Dictionary containing compressed data
    """
    if config is None:
        config = CompressionConfig()
    
    # Validate input
    if image.dtype != np.uint8 and (image.min() < 0 or image.max() > 255):
        raise ValueError("Input image must be in range [0, 255]")
    
    # Store original dimensions
    original_shape = image.shape
    height, width = original_shape[0], original_shape[1]
    channels = original_shape[2] if len(original_shape) == 3 else 1
    
    # Convert to float
    image_float = image.astype(np.float32)
    
    print(f"[PAWC] Compressing image: {width}x{height}, {channels} channels, quality={config.quality}")
    
    # Step 1: Generate perceptual importance map
    print("[PAWC] Step 1/4: Generating perceptual importance map...")
    importance_generator = ImportanceMapGenerator(
        edge_weight=config.edge_weight,
        texture_weight=config.texture_weight,
        saliency_weight=config.saliency_weight
    )
    importance_map = importance_generator.generate(image_float)
    
    # Step 2: Apply adaptive wavelet transform
    print("[PAWC] Step 2/4: Applying adaptive wavelet transform...")
    wavelet_transform = AdaptiveWaveletTransform(
        block_size=config.block_size,
        max_level=config.max_wavelet_level,
        wavelet_bases=config.wavelet_bases
    )
    wavelet_blocks = wavelet_transform.forward(image_float, importance_map)
    
    # Step 3: Quantize coefficients
    print("[PAWC] Step 3/4: Quantizing wavelet coefficients...")
    quantizer = ImportanceWeightedQuantizer(
        base_q=config.base_quantization,
        adaptation_strength=config.adaptation_strength,
        use_ml_optimizer=config.use_ml_quantization
    )
    
    quantized_blocks = []
    for block in wavelet_blocks:
        quantized_coeffs, metadata = quantizer.quantize_coeffs(
            block.coeffs,
            importance_map,
            block.position,
            config.block_size
        )
        
        # Store quantized block info (now with INTEGER coefficients)
        quantized_blocks.append({
            'quantized_coeffs': quantized_coeffs,  # List of int16 arrays
            'quant_metadata': metadata,  # Includes q_steps
            'wavelet': block.wavelet,
            'level': block.level,
            'position': block.position,
            'shape': block.shape
        })
    
    # Step 4: Prepare compressed data structure
    print("[PAWC] Step 4/4: Packaging compressed data...")
    compressed_data = {
        'height': height,
        'width': width,
        'channels': channels,
        'quality': config.quality,
        'blocks': quantized_blocks,
        'config': {
            'block_size': config.block_size,
            'max_level': config.max_wavelet_level,
            'base_q': config.base_quantization
        }
    }
    
    print(f"[PAWC] Compression complete! {len(quantized_blocks)} blocks processed.")
    
    return compressed_data


def decompress_image(compressed_data: dict) -> np.ndarray:
    """
    Decompress image from PAWC compressed data.
    
    Args:
        compressed_data: Compressed data dictionary
    
    Returns:
        Reconstructed image as numpy array (H, W, C) in range [0, 255]
    """
    height = compressed_data['height']
    width = compressed_data['width']
    channels = compressed_data['channels']
    
    print(f"[PAWC] Decompressing image: {width}x{height}, {channels} channels")
    
    # Reconstruct wavelet blocks with dequantization
    from .wavelet_transform import WaveletBlock
    from .quantization import ImportanceWeightedQuantizer
    
    blocks = []
    for block_data in compressed_data['blocks']:
        # Dequantize integer coefficients back to float
        quantized_coeffs = block_data['quantized_coeffs']
        q_steps = block_data['quant_metadata']['q_steps']
        
        # Dequantize each subband
        float_coeffs = []
        for i, (coeffs, q_step) in enumerate(zip(quantized_coeffs, q_steps)):
            if isinstance(coeffs, list):
                # Tuple of details
                dequant_details = tuple(
                    ImportanceWeightedQuantizer._dequantize_from_int(c, q_step) 
                    for c in coeffs
                )
                float_coeffs.append(dequant_details)
            else:
                # Single array
                float_coeffs.append(
                    ImportanceWeightedQuantizer._dequantize_from_int(coeffs, q_step)
                )
        
        blocks.append(WaveletBlock(
            coeffs=tuple(float_coeffs),
            wavelet=block_data['wavelet'],
            level=block_data['level'],
            position=block_data['position'],
            shape=block_data['shape']
        ))
    
    # Inverse wavelet transform
    print("[PAWC] Applying inverse wavelet transform...")
    wavelet_transform = AdaptiveWaveletTransform(
        block_size=compressed_data['config']['block_size'],
        max_level=compressed_data['config']['max_level']
    )
    
    output_shape = (height, width, channels) if channels > 1 else (height, width)
    reconstructed = wavelet_transform.inverse(blocks, output_shape)
    
    # Clip to valid range and convert to uint8
    reconstructed = np.clip(reconstructed, 0, 255).astype(np.uint8)
    
    print("[PAWC] Decompression complete!")
    
    return reconstructed


def compress_file(input_path: Union[str, Path],
                 output_path: Union[str, Path],
                 config: Optional[CompressionConfig] = None) -> dict:
    """
    Compress an image file.
    
    Args:
        input_path: Path to input image
        output_path: Path to output compressed file (.pawc extension)
        config: Compression configuration
    
    Returns:
        Dictionary with compression statistics
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Load image
    print(f"[PAWC] Loading image: {input_path}")
    image = Image.open(input_path)
    image_array = np.array(image)
    
    # Compress
    compressed_data = compress_image(image_array, config)
    
    # Write to file using efficient binary codec
    print(f"[PAWC] Writing compressed file: {output_path}")
    codec = EfficientBinaryCodec()
    codec.write_file(str(output_path), compressed_data)
    
    # Calculate statistics
    original_size = input_path.stat().st_size
    compressed_size = output_path.stat().st_size
    compression_ratio = original_size / compressed_size
    
    stats = {
        'original_size': original_size,
        'compressed_size': compressed_size,
        'compression_ratio': compression_ratio,
        'space_savings': (1 - 1/compression_ratio) * 100
    }
    
    print(f"[PAWC] Compression Statistics:")
    print(f"  Original size: {original_size:,} bytes")
    print(f"  Compressed size: {compressed_size:,} bytes")
    print(f"  Compression ratio: {compression_ratio:.2f}:1")
    print(f"  Space savings: {stats['space_savings']:.1f}%")
    
    return stats


def decompress_file(input_path: Union[str, Path],
                   output_path: Union[str, Path]) -> np.ndarray:
    """
    Decompress a PAWC compressed file.
    
    Args:
        input_path: Path to compressed file (.pawc)
        output_path: Path to output image
    
    Returns:
        Reconstructed image array
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Read compressed data using efficient binary codec
    print(f"[PAWC] Reading compressed file: {input_path}")
    codec = EfficientBinaryCodec()
    compressed_data = codec.read_file(str(input_path))
    
    # Decompress
    reconstructed = decompress_image(compressed_data)
    
    # Save image
    print(f"[PAWC] Saving decompressed image: {output_path}")
    image = Image.fromarray(reconstructed)
    image.save(output_path)
    
    return reconstructed
