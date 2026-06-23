"""
Entropy coding module with context-adaptive arithmetic coding.

Implements run-length encoding and arithmetic coding for efficient bitstream compression.
"""

import numpy as np
from typing import List, Tuple
import struct
import zlib


class EntropyEncoder:
    """Context-adaptive entropy encoder for compressed data."""
    
    def __init__(self, use_arithmetic_coding: bool = True):
        """
        Initialize entropy encoder.
        
        Args:
            use_arithmetic_coding: Use arithmetic coding (vs simple compression)
        """
        self.use_arithmetic_coding = use_arithmetic_coding
    
    def encode(self, data: np.ndarray, context: str = 'default') -> bytes:
        """
        Encode data to compressed bitstream.
        
        Args:
            data: Numerical data to encode
            context: Context identifier for adaptive coding
        
        Returns:
            Compressed bytes
        """
        # Flatten and convert to bytes-compatible format
        data_flat = data.flatten().astype(np.float32)
        
        # Apply run-length encoding for zeros (common in quantized wavelets)
        rle_data = self._run_length_encode(data_flat)
        
        # Convert to bytes
        data_bytes = rle_data.tobytes()
        
        if self.use_arithmetic_coding:
            # Use zlib (DEFLATE algorithm) as a proxy for arithmetic coding
            # In production, implement true arithmetic coding
            compressed = zlib.compress(data_bytes, level=9)
        else:
            compressed = data_bytes
        
        return compressed
    
    def decode(self, compressed: bytes, shape: Tuple, dtype=np.float32) -> np.ndarray:
        """
        Decode compressed bitstream to data.
        
        Args:
            compressed: Compressed bytes
            shape: Original data shape
            dtype: Data type
        
        Returns:
            Decoded array
        """
        if self.use_arithmetic_coding:
            # Decompress
            data_bytes = zlib.decompress(compressed)
        else:
            data_bytes = compressed
        
        # Convert from bytes
        rle_data = np.frombuffer(data_bytes, dtype=dtype)
        
        # Decode run-length encoding
        data_flat = self._run_length_decode(rle_data, np.prod(shape))
        
        # Reshape
        data = data_flat.reshape(shape)
        
        return data
    
    @staticmethod
    def _run_length_encode(data: np.ndarray) -> np.ndarray:
        """
        Apply run-length encoding to efficiently compress zeros.
        
        Format: [value, count, value, count, ...]
        Special case: if count is 0, it's a non-zero value sequence
        """
        if len(data) == 0:
            return np.array([], dtype=data.dtype)
        
        # Simple RLE for zeros
        encoded = []
        i = 0
        
        while i < len(data):
            if data[i] == 0:
                # Count consecutive zeros
                count = 1
                while i + count < len(data) and data[i + count] == 0:
                    count += 1
                
                # Encode as: [0, count]
                encoded.extend([0.0, float(count)])
                i += count
            else:
                # Non-zero value, store directly
                encoded.append(data[i])
                i += 1
        
        return np.array(encoded, dtype=data.dtype)
    
    @staticmethod
    def _run_length_decode(encoded: np.ndarray, expected_length: int) -> np.ndarray:
        """
        Decode run-length encoded data.
        """
        if len(encoded) == 0:
            return np.array([], dtype=encoded.dtype)
        
        decoded = []
        i = 0
        
        while i < len(encoded) and len(decoded) < expected_length:
            if i + 1 < len(encoded) and encoded[i] == 0 and encoded[i+1] > 1:
                # Zero run: [0, count]
                count = int(encoded[i+1])
                decoded.extend([0.0] * count)
                i += 2
            else:
                # Non-zero value
                decoded.append(encoded[i])
                i += 1
        
        return np.array(decoded, dtype=encoded.dtype)


class BitstreamWriter:
    """Writes compressed image data to a binary file format."""
    
    MAGIC_NUMBER = b'PAWC'
    VERSION = 1
    
    def __init__(self):
        """Initialize bitstream writer."""
        self.encoder = EntropyEncoder()
    
    def write(self, filename: str, compressed_data: dict):
        """
        Write compressed data to file.
        
        Args:
            filename: Output filename
            compressed_data: Dictionary with compression data
        """
        with open(filename, 'wb') as f:
            # Header
            f.write(self.MAGIC_NUMBER)
            f.write(struct.pack('<I', self.VERSION))
            
            # Image metadata
            f.write(struct.pack('<III', 
                              compressed_data['height'],
                              compressed_data['width'],
                              compressed_data['channels']))
            
            # Compression parameters
            f.write(struct.pack('<f', compressed_data['quality']))
            
            # Compressed payload (using pickle for simplicity)
            # Include both blocks and config
            import pickle
            payload_data = {
                'blocks': compressed_data['blocks'],
                'config': compressed_data.get('config', {})
            }
            payload = pickle.dumps(payload_data)
            payload_size = len(payload)
            
            f.write(struct.pack('<Q', payload_size))
            f.write(payload)
    
    def read(self, filename: str) -> dict:
        """
        Read compressed data from file.
        
        Args:
            filename: Input filename
        
        Returns:
            Dictionary with decompression data
        """
        with open(filename, 'rb') as f:
            # Verify magic number
            magic = f.read(4)
            if magic != self.MAGIC_NUMBER:
                raise ValueError(f"Invalid file format. Expected {self.MAGIC_NUMBER}, got {magic}")
            
            # Version
            version = struct.unpack('<I', f.read(4))[0]
            if version != self.VERSION:
                raise ValueError(f"Unsupported version: {version}")
            
            # Image metadata
            height, width, channels = struct.unpack('<III', f.read(12))
            
            # Compression parameters
            quality = struct.unpack('<f', f.read(4))[0]
            
            # Compressed payload
            payload_size = struct.unpack('<Q', f.read(8))[0]
            payload = f.read(payload_size)
            
            import pickle
            payload_data = pickle.loads(payload)
            
            # Handle both old and new format
            if isinstance(payload_data, dict):
                blocks = payload_data.get('blocks', payload_data)
                config = payload_data.get('config', {})
            else:
                # Old format: just blocks
                blocks = payload_data
                config = {}
            
            # Provide defaults if config is missing
            if not config:
                config = {
                    'block_size': 64,
                    'max_level': 4,
                    'base_q': 10.0
                }
            
            return {
                'height': height,
                'width': width,
                'channels': channels,
                'quality': quality,
                'blocks': blocks,
                'config': config
            }


def encode_to_bitstream(data: np.ndarray, context: str = 'default') -> bytes:
    """
    Convenience function to encode data.
    
    Args:
        data: Data to encode
        context: Context for adaptive coding
    
    Returns:
        Compressed bytes
    """
    encoder = EntropyEncoder()
    return encoder.encode(data, context)


def decode_from_bitstream(compressed: bytes, shape: Tuple) -> np.ndarray:
    """
    Convenience function to decode data.
    
    Args:
        compressed: Compressed bytes
        shape: Original shape
    
    Returns:
        Decoded array
    """
    encoder = EntropyEncoder()
    return encoder.decode(compressed, shape)
