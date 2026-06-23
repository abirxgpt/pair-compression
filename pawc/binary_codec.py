"""
Efficient binary codec for PAWC compression.

This module implements proper integer quantization and compact binary serialization
to achieve actual compression instead of expansion.
"""

import numpy as np
import struct
from typing import Tuple, List, Dict, Any
import io


class IntegerQuantizer:
    """
    Converts float coefficients to compact integer representation.
    
    This is critical for compression - float32 → int16 gives 50% size reduction
    plus enables much better entropy coding.
    """
    
    @staticmethod
    def quantize_to_integers(coeffs: np.ndarray, q_step: float) -> Tuple[np.ndarray, Dict]:
        """
        Quantize float coefficients to int16.
        
        Args:
            coeffs: Float coefficients
            q_step: Quantization step size
        
        Returns:
            (quantized_int16, metadata)
        """
        # Quantize to integers
        int_coeffs = np.round(coeffs / q_step).astype(np.int16)
        
        # Store metadata for dequantization
        metadata = {
            'q_step': q_step,
            'shape': coeffs.shape,
            'dtype': 'int16'
        }
        
        return int_coeffs, metadata
    
    @staticmethod
    def dequantize_from_integers(int_coeffs: np.ndarray, q_step: float) -> np.ndarray:
        """
        Dequantize int16 back to float.
        
        Args:
            int_coeffs: Integer coefficients
            q_step: Quantization step size
        
        Returns:
            Float coefficients
        """
        return int_coeffs.astype(np.float32) * q_step
    
    @staticmethod
    def quantize_wavelet_block(coeffs: Tuple, q_steps: List[float]) -> Tuple[List[np.ndarray], List[Dict]]:
        """
        Quantize all subbands in a wavelet block.
        
        Args:
            coeffs: Wavelet coefficients tuple from pywt.wavedec2
            q_steps: Quantization step for each subband
        
        Returns:
            (list of int16 arrays, list of metadata)
        """
        quantized_subbands = []
        metadata_list = []
        
        for i, (coeff, q_step) in enumerate(zip(coeffs, q_steps)):
            if isinstance(coeff, tuple):
                # Detail coefficients (LH, HL, HH)
                quantized_details = []
                detail_metadata = []
                
                for detail in coeff:
                    q_detail, meta = IntegerQuantizer.quantize_to_integers(detail, q_step)
                    quantized_details.append(q_detail)
                    detail_metadata.append(meta)
                
                quantized_subbands.append(quantized_details)
                metadata_list.append({'type': 'tuple', 'details': detail_metadata})
            else:
                # Approximation coefficients (LL)
                q_coeff, meta = IntegerQuantizer.quantize_to_integers(coeff, q_step)
                quantized_subbands.append(q_coeff)
                metadata_list.append(meta)
        
        return quantized_subbands, metadata_list


class EfficientBinaryCodec:
    """
    Compact binary format for PAWC files.
    
    Uses struct packing + bz2 compression instead of pickle.
    Expected: 30-100x size reduction.
    """
    
    MAGIC = b'PAWC'
    VERSION = 2  # Version 2 with efficient encoding
    
    def __init__(self):
        """Initialize codec."""
        pass
    
    def encode_block(self, block_data: Dict) -> bytes:
        """
        Encode a single block to binary.
        
        Format:
        - Position: 2× uint16 (4 bytes)
        - Wavelet: uint8 (1 byte) - encoded as index
        - Level: uint8 (1 byte)
        - Num subbands: uint8 (1 byte)
        - For each subband:
            - Shape: 2× uint16 (4 bytes)
            - Q_step: float32 (4 bytes)
            - Data length: uint32 (4 bytes)
            - Int16 coefficients (compressed)
        """
        buf = io.BytesIO()
        
        # Position
        pos_i, pos_j = block_data['position']
        buf.write(struct.pack('<HH', pos_i, pos_j))
        
        # Wavelet type (encode as index)
        wavelet_map = {'haar': 0, 'db4': 1, 'bior4.4': 2}
        wavelet_idx = wavelet_map.get(block_data['wavelet'], 0)
        buf.write(struct.pack('<B', wavelet_idx))
        
        # Level
        buf.write(struct.pack('<B', block_data['level']))
        
        # Shape (block shape)
        if 'shape' in block_data and block_data['shape'] is not None:
            h, w = block_data['shape']
        else:
            # Default to block size from first coeff
            h, w = block_data['quantized_coeffs'][0].shape if not isinstance(block_data['quantized_coeffs'][0], list) else block_data['quantized_coeffs'][0][0].shape
        buf.write(struct.pack('<HH', h, w))
        
        # Encode quantized coefficients
        quantized_coeffs = block_data['quantized_coeffs']
        metadata = block_data['quant_metadata']
        q_steps = metadata['q_steps']
        
        # Number of subbands
        buf.write(struct.pack('<B', len(quantized_coeffs)))
        
        for i, (coeffs, q_step) in enumerate(zip(quantized_coeffs, q_steps)):
            if isinstance(coeffs, list):
                # List of detail subbands - mark as list
                buf.write(struct.pack('<B', 1))  # 1 = list
                buf.write(struct.pack('<B', len(coeffs)))  # number of elements in list
                for detail_coeffs in coeffs:
                    meta_dict = {'q_step': q_step, 'shape': detail_coeffs.shape}
                    self._encode_subband(buf, detail_coeffs, meta_dict)
            else:
                # Single array
                buf.write(struct.pack('<B', 0))  # 0 = single array
                meta_dict = {'q_step': q_step, 'shape': coeffs.shape}
                self._encode_subband(buf, coeffs, meta_dict)
        
        return buf.getvalue()
    
    def _encode_subband(self, buf: io.BytesIO, coeffs: np.ndarray, meta: Dict):
        """Encode a single subband."""
        # Shape
        h, w = coeffs.shape
        buf.write(struct.pack('<HH', h, w))
        
        # Q step
        buf.write(struct.pack('<f', meta['q_step']))
        
        # Compress coefficients with bz2
        import bz2
        
        # Flatten to 1D for better compression
        flat_coeffs = coeffs.flatten()
        
        # Convert to bytes
        coeff_bytes = flat_coeffs.tobytes()
        
        # Compress
        compressed = bz2.compress(coeff_bytes, compresslevel=9)
        
        # Write length and data
        buf.write(struct.pack('<I', len(compressed)))
        buf.write(compressed)
    
    def decode_block(self, data: bytes) -> Dict:
        """
        Decode block from binary.
        
        Returns:
            Block dictionary
        """
        buf = io.BytesIO(data)
        
        # Position
        pos_i, pos_j = struct.unpack('<HH', buf.read(4))
        
        # Wavelet
        wavelet_idx = struct.unpack('<B', buf.read(1))[0]
        wavelet_map = {0: 'haar', 1: 'db4', 2: 'bior4.4'}
        wavelet = wavelet_map[wavelet_idx]
        
        # Level
        level = struct.unpack('<B', buf.read(1))[0]
        
        # Shape
        shape_h, shape_w = struct.unpack('<HH', buf.read(4))
        shape = (shape_h, shape_w)
        
        # Number of subbands
        num_subbands = struct.unpack('<B', buf.read(1))[0]
        
        # Decode subbands
        quantized_coeffs = []
        q_steps = []
        
        for _ in range(num_subbands):
            # Read type flag
            type_flag = struct.unpack('<B', buf.read(1))[0]
            
            if type_flag == 1:
                # List of arrays
                num_in_list = struct.unpack('<B', buf.read(1))[0]
                list_arrays = []
                q_step_value = None
                for _ in range(num_in_list):
                    coeffs, meta = self._decode_subband(buf)
                    list_arrays.append(coeffs)
                    q_step_value = meta['q_step']  # All subbands use same q_step
                quantized_coeffs.append(list_arrays)
                q_steps.append(q_step_value)
            else:
                # Single array
                coeffs, meta = self._decode_subband(buf)
                quantized_coeffs.append(coeffs)
                q_steps.append(meta['q_step'])
        
        return {
            'position': (pos_i, pos_j),
            'wavelet': wavelet,
            'level': level,
            'shape': shape,
            'quantized_coeffs': quantized_coeffs,
            'quant_metadata': {'q_steps': q_steps}
        }
    
    def _decode_subband(self, buf: io.BytesIO) -> Tuple[np.ndarray, Dict]:
        """Decode a single subband."""
        # Shape
        h, w = struct.unpack('<HH', buf.read(4))
        
        # Q step
        q_step = struct.unpack('<f', buf.read(4))[0]
        
        # Compressed data
        compressed_len = struct.unpack('<I', buf.read(4))[0]
        compressed = buf.read(compressed_len)
        
        # Decompress
        import bz2
        coeff_bytes = bz2.decompress(compressed)
        
        # Convert back to array
        flat_coeffs = np.frombuffer(coeff_bytes, dtype=np.int16)
        coeffs = flat_coeffs.reshape(h, w)
        
        metadata = {
            'q_step': q_step,
            'shape': (h, w)
        }
        
        return coeffs, metadata
    
    def write_file(self, filename: str, compressed_data: Dict):
        """
        Write compressed data to file in efficient binary format.
        
        Args:
            filename: Output file path
            compressed_data: Dictionary with all compression data
        """
        with open(filename, 'wb') as f:
            # Header
            f.write(self.MAGIC)
            f.write(struct.pack('<I', self.VERSION))
            
            # Image dimensions
            f.write(struct.pack('<III',
                              compressed_data['height'],
                              compressed_data['width'],
                              compressed_data['channels']))
            
            # Compression config
            config = compressed_data['config']
            f.write(struct.pack('<BBBf',
                              compressed_data['quality'],
                              config['block_size'],
                              config['max_level'],
                              config['base_q']))
            
            # Number of blocks
            blocks = compressed_data['blocks']
            f.write(struct.pack('<I', len(blocks)))
            
            # Encode each block
            for block in blocks:
                block_bytes = self.encode_block(block)
                # Write block length then data
                f.write(struct.pack('<I', len(block_bytes)))
                f.write(block_bytes)
    
    def read_file(self, filename: str) -> Dict:
        """
        Read compressed data from file.
        
        Args:
            filename: Input file path
        
        Returns:
            Dictionary with decompression data
        """
        with open(filename, 'rb') as f:
            # Verify magic
            magic = f.read(4)
            if magic != self.MAGIC:
                raise ValueError(f"Invalid file format. Expected {self.MAGIC}, got {magic}")
            
            # Version
            version = struct.unpack('<I', f.read(4))[0]
            if version != self.VERSION:
                # Try old version
                raise ValueError(f"Unsupported version: {version}. Please regenerate compressed files.")
            
            # Image dimensions
            height, width, channels = struct.unpack('<III', f.read(12))
            
            # Config
            quality, block_size, max_level, base_q = struct.unpack('<BBBf', f.read(7))
            
            # Number of blocks
            num_blocks = struct.unpack('<I', f.read(4))[0]
            
            # Decode blocks
            blocks = []
            for _ in range(num_blocks):
                block_len = struct.unpack('<I', f.read(4))[0]
                block_bytes = f.read(block_len)
                block = self.decode_block(block_bytes)
                blocks.append(block)
            
            return {
                'height': height,
                'width': width,
                'channels': channels,
                'quality': quality,
                'blocks': blocks,
                'config': {
                    'block_size': block_size,
                    'max_level': max_level,
                    'base_q': base_q
                }
            }


def test_codec():
    """Quick test of the codec."""
    # Test integer quantization
    coeffs = np.random.randn(64, 64).astype(np.float32) * 100
    q_step = 5.0
    
    int_coeffs, meta = IntegerQuantizer.quantize_to_integers(coeffs, q_step)
    reconstructed = IntegerQuantizer.dequantize_from_integers(int_coeffs, q_step)
    
    error = np.abs(coeffs - reconstructed).max()
    print(f"Max quantization error: {error:.2f} (should be ≈ {q_step/2})")
    
    # Test binary codec
    block_data = {
        'position': (0, 0),
        'wavelet': 'haar',
        'level': 2,
        'quantized_coeffs': [int_coeffs],
        'quant_metadata': [meta]
    }
    
    codec = EfficientBinaryCodec()
    encoded = codec.encode_block(block_data)
    decoded = codec.decode_block(encoded)
    
    print(f"Original coeffs size: {coeffs.nbytes} bytes")
    print(f"Encoded block size: {len(encoded)} bytes")
    print(f"Compression: {coeffs.nbytes / len(encoded):.2f}x")


if __name__ == '__main__':
    test_codec()
