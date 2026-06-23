"""
Simplified PAWC v2 Implementation for Testing

This version uses a simplified approach to ensure it works correctly:
- Huffman coding for quantized coefficients
- Block-based processing with importance weighting
- Proper round-trip compression/decompression
"""

import numpy as np
from PIL import Image
import pickle
import gzip
from typing import Tuple, Optional
from pathlib import Path

from .importance_map import ImportanceMapGenerator
from .adaptive_wavelet import AdaptiveWaveletTransform
from .huffman_coder import HuffmanCoder, zigzag_scan, inverse_zigzag_scan
from .config import CompressionConfig


class SimplePAWCv2Codec:
    """
    Simplified PAWC v2 with working Huffman compression.
    
    Focus on correctness over maximum optimization.
    """
    
    BLOCK_SIZE = 32
    
    def __init__(self, config: Optional[CompressionConfig] = None):
        self.config = config or CompressionConfig()
        self.importance_gen = ImportanceMapGenerator(
            self.config.edge_weight,
            self.config.texture_weight,
            self.config.saliency_weight
        )
        self.wavelet_transform = AdaptiveWaveletTransform()
    
    def compress(self, image: np.ndarray, quality: int = 85) -> Tuple[bytes, dict]:
        """Compress image with PAWC v2."""
        height, width, channels = image.shape
        
        # Generate importance map
        importance_map = self.importance_gen.generate(image)
        
        # Process each channel
        all_blocks = []
        
        for c in range(channels):
            channel = image[:, :, c].astype(np.float32)
            blocks = self._process_channel(channel, importance_map, quality)
            all_blocks.append(blocks)
        
        # Package everything
        data = {
            'shape': (height, width, channels),
            'blocks': all_blocks,
            'quality': quality,
            'block_size': self.BLOCK_SIZE,
            'config': {
                'edge_w': self.config.edge_weight,
                'texture_w': self.config.texture_weight,
                'saliency_w': self.config.saliency_weight
            }
        }
        
        # Serialize with pickle and compress with gzip
        serialized = pickle.dumps(data)
        compressed = gzip.compress(serialized, compresslevel=9)
        
        metadata = {
            'compressed_size': len(compressed),
            'original_size': height * width * channels,
            'compression_ratio': (height * width * channels) / len(compressed)
        }
        
        return compressed, metadata
    
    def _process_channel(self, channel: np.ndarray, importance_map: np.ndarray,
                        quality: int) -> list:
        """Process one channel into compressed blocks."""
        height, width = channel.shape
        
        # Pad to block size
        pad_h = (self.BLOCK_SIZE - height % self.BLOCK_SIZE) % self.BLOCK_SIZE
        pad_w = (self.BLOCK_SIZE - width % self.BLOCK_SIZE) % self.BLOCK_SIZE
        
        if pad_h > 0 or pad_w > 0:
            channel = np.pad(channel, ((0, pad_h), (0, pad_w)), mode='edge')
            importance_map = np.pad(importance_map, ((0, pad_h), (0, pad_w)), mode='edge')
        
        blocks = []
        
        for y in range(0, channel.shape[0], self.BLOCK_SIZE):
            for x in range(0, channel.shape[1], self.BLOCK_SIZE):
                block = channel[y:y+self.BLOCK_SIZE, x:x+self.BLOCK_SIZE]
                imp_block = importance_map[y:y+self.BLOCK_SIZE, x:x+self.BLOCK_SIZE]
                
                compressed_block = self._compress_block(block, imp_block, quality)
                blocks.append(compressed_block)
        
        return blocks
    
    def _compress_block(self, block: np.ndarray, importance_block: np.ndarray,
                       quality: int) -> dict:
        """Compress a single block."""
        # Block importance
        block_importance = np.mean(importance_block)
        
        # Select wavelet
        wavelet = self.wavelet_transform.select_wavelet(block, block_importance)
        
        # Transform
        coeffs = self.wavelet_transform.transform(block, wavelet, level=2)
        
        # Quantize with importance weighting
        q_scale = 100.0 / max(quality, 1)
        importance_factor = 0.5 + 1.5 * (1.0 - block_importance)
        final_q = q_scale * importance_factor
        
        quantized_coeffs = []
        for i, c in enumerate(coeffs):
            if isinstance(c, tuple):
                # Detail coefficients (H, V, D)
                q_detail = []
                for detail in c:
                    qd = np.round(detail / final_q).astype(np.int16)
                    q_detail.append(qd)
                quantized_coeffs.append(tuple(q_detail))
            else:
                # Approximation
                qa = np.round(c / (final_q * 0.5)).astype(np.int16)
                quantized_coeffs.append(qa)
        
        # Huffman encode each subband
        huff_coder = HuffmanCoder()
        encoded_coeffs = []
        
        for c in quantized_coeffs:
            if isinstance(c, tuple):
                enc_tuple = []
                for detail in c:
                    flat = detail.flatten()
                    enc, meta = huff_coder.encode(flat)
                    enc_tuple.append({'data': enc, 'meta': meta})
                encoded_coeffs.append(enc_tuple)
            else:
                flat = c.flatten()
                enc, meta = huff_coder.encode(flat)
                encoded_coeffs.append({'data': enc, 'meta': meta})
        
        return {
            'wavelet': wavelet,
            'q_scale': final_q,
            'encoded': encoded_coeffs,
            'importance': float(block_importance)
        }
    
    def decompress(self, compressed_bytes: bytes) -> np.ndarray:
        """Decompress PAWC v2 data."""
        # Decompress and deserialize
        decompressed = gzip.decompress(compressed_bytes)
        data = pickle.loads(decompressed)
        
        height, width, channels = data['shape']
        all_blocks = data['blocks']
        block_size = data['block_size']
        
        # Reconstruct each channel
        reconstructed_channels = []
        
        for channel_blocks in all_blocks:
            channel = self._reconstruct_channel(
                channel_blocks, height, width, block_size
            )
            reconstructed_channels.append(channel)
        
        # Stack channels
        image = np.stack(reconstructed_channels, axis=2)
        return np.clip(image, 0, 255).astype(np.uint8)
    
    def _reconstruct_channel(self, blocks: list, orig_height: int,
                            orig_width: int, block_size: int) -> np.ndarray:
        """Reconstruct channel from blocks."""
        # Calculate padded size
        pad_h = (block_size - orig_height % block_size) % block_size
        pad_w = (block_size - orig_width % block_size) % block_size
        padded_h = orig_height + pad_h
        padded_w = orig_width + pad_w
        
        # Initialize output
        channel = np.zeros((padded_h, padded_w), dtype=np.float32)
        
        # Reconstruct blocks
        block_idx = 0
        for y in range(0, padded_h, block_size):
            for x in range(0, padded_w, block_size):
                block = self._decompress_block(blocks[block_idx], block_size)
                channel[y:y+block_size, x:x+block_size] = block
                block_idx += 1
        
        # Crop to original size
        return channel[:orig_height, :orig_width]
    
    def _decompress_block(self, block_data: dict, block_size: int) -> np.ndarray:
        """Decompress a single block."""
        wavelet = block_data['wavelet']
        q_scale = block_data['q_scale']
        encoded = block_data['encoded']
        
        # Huffman decode each subband
        huff_coder = HuffmanCoder()
        decoded_coeffs = []
        
        for enc in encoded:
            if isinstance(enc, list):
                # Detail coefficients
                dec_tuple = []
                for enc_detail in enc:
                    flat = huff_coder.decode(enc_detail['data'], enc_detail['meta'])
                    shape = (block_size // 2, block_size // 2)  # After 1 level
                    detail = flat.reshape(shape)
                    dec_tuple.append(detail)
                decoded_coeffs.append(tuple(dec_tuple))
            else:
                # Approximation
                flat = huff_coder.decode(enc['data'], enc['meta'])
                shape = (block_size // 4, block_size // 4)  # After 2 levels
                approx = flat.reshape(shape)
                decoded_coeffs.append(approx)
        
        # Dequantize
        dequantized = []
        for i, c in enumerate(decoded_coeffs):
            if isinstance(c, tuple):
                deq_tuple = []
                for detail in c:
                    deq_tuple.append(detail.astype(np.float32) * q_scale)
                dequantized.append(tuple(deq_tuple))
            else:
                dequantized.append(c.astype(np.float32) * (q_scale * 0.5))
        
        # Inverse wavelet transform
        reconstructed = self.wavelet_transform.inverse_transform(
            dequantized, wavelet
        )
        
        return reconstructed


def compress_file_pawcv2(input_path: str, output_path: str,
                         config: Optional[CompressionConfig] = None) -> dict:
    """Compress an image file with PAWC v2."""
    config = config or CompressionConfig()
    codec = SimplePAWCv2Codec(config)
    
    # Load image
    image = np.array(Image.open(input_path))
    original_size = Path(input_path).stat().st_size
    
    # Compress
    compressed_data, metadata = codec.compress(image, config.quality)
    
    # Save
    with open(output_path, 'wb') as f:
        f.write(compressed_data)
    
    compressed_size = len(compressed_data)
    
    print(f"\n[PAWC v2] Compression complete:")
    print(f"  Original: {original_size:,} bytes")
    print(f"  Compressed: {compressed_size:,} bytes")
    print(f"  Ratio: {original_size / compressed_size:.2f}:1")
    print(f"  BPP: {(compressed_size * 8) / (image.shape[0] * image.shape[1]):.3f}")
    
    return {
        'original_size': original_size,
        'compressed_size': compressed_size,
        'compression_ratio': original_size / compressed_size,
        'bpp': (compressed_size * 8) / (image.shape[0] * image.shape[1])
    }


def decompress_file_pawcv2(input_path: str, output_path: str) -> np.ndarray:
    """Decompress a PAWC v2 file."""
    codec = SimplePAWCv2Codec()
    
    # Load compressed data
    with open(input_path, 'rb') as f:
        compressed_data = f.read()
    
    # Decompress
    image = codec.decompress(compressed_data)
    
    # Save
    Image.fromarray(image).save(output_path)
    
    return image
