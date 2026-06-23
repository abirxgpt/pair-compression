"""
Huffman Coding Implementation for PAWC v2

Standard Huffman entropy coder for wavelet coefficients.
"""

import heapq
from collections import Counter, defaultdict
from typing import Dict, Tuple, List
import struct
import numpy as np


class HuffmanNode:
    """Node in Huffman tree."""
    
    def __init__(self, symbol=None, freq=0, left=None, right=None):
        self.symbol = symbol
        self.freq = freq
        self.left = left
        self.right = right
    
    def __lt__(self, other):
        return self.freq < other.freq


class HuffmanCoder:
    """
    Huffman entropy coder for integer sequences.
    
    Implements canonical Huffman coding for efficient compression
    of quantized wavelet coefficients.
    """
    
    def __init__(self):
        self.codebook = {}
        self.decode_tree = None
        self.symbol_lengths = {}
    
    def build_codebook(self, data: np.ndarray) -> Dict[int, str]:
        """
        Build Huffman codebook from symbol frequencies.
        
        Args:
            data: Integer array of symbols
        
        Returns:
            Dictionary mapping symbols to binary codes
        """
        # Count frequencies
        frequencies = Counter(data.flatten())
        
        if len(frequencies) == 0:
            return {}
        
        if len(frequencies) == 1:
            # Single symbol - use 1-bit code
            symbol = list(frequencies.keys())[0]
            self.codebook = {symbol: '0'}
            self.symbol_lengths = {symbol: 1}
            return self.codebook
        
        # Build Huffman tree
        heap = [HuffmanNode(symbol=sym, freq=freq) 
                for sym, freq in frequencies.items()]
        heapq.heapify(heap)
        
        while len(heap) > 1:
            left = heapq.heappop(heap)
            right = heapq.heappop(heap)
            
            merged = HuffmanNode(
                freq=left.freq + right.freq,
                left=left,
                right=right
            )
            heapq.heappush(heap, merged)
        
        # Generate codes
        root = heap[0]
        self.decode_tree = root
        self.codebook = {}
        self.symbol_lengths = {}
        self._generate_codes(root, '')
        
        return self.codebook
    
    def _generate_codes(self, node: HuffmanNode, code: str):
        """Recursively generate Huffman codes."""
        if node.symbol is not None:
            # Leaf node
            self.codebook[node.symbol] = code if code else '0'
            self.symbol_lengths[node.symbol] = len(code) if code else 1
        else:
            if node.left:
                self._generate_codes(node.left, code + '0')
            if node.right:
                self._generate_codes(node.right, code + '1')
    
    def encode(self, data: np.ndarray) -> Tuple[bytes, Dict]:
        """
        Encode data using Huffman coding.
        
        Args:
            data: Integer array to encode
        
        Returns:
            (encoded_bytes, metadata) tuple
        """
        if len(self.codebook) == 0:
            self.build_codebook(data)
        
        # Convert data to bit string
        flat_data = data.flatten()
        bit_string = ''.join(self.codebook[symbol] for symbol in flat_data)
        
        # Pad to byte boundary
        padding = (8 - len(bit_string) % 8) % 8
        bit_string += '0' * padding
        
        # Convert to bytes
        encoded_bytes = int(bit_string, 2).to_bytes(
            (len(bit_string) + 7) // 8, byteorder='big'
        )
        
        # Create metadata with codebook
        metadata = {
            'codebook': self.codebook,
            'symbol_lengths': self.symbol_lengths,
            'original_shape': data.shape,
            'padding': padding,
            'num_symbols': len(flat_data)
        }
        
        return encoded_bytes, metadata
    
    def decode(self, encoded_bytes: bytes, metadata: Dict) -> np.ndarray:
        """
        Decode Huffman-encoded data.
        
        Args:
            encoded_bytes: Encoded byte string
            metadata: Encoding metadata including codebook
        
        Returns:
            Decoded integer array
        """
        # Rebuild codebook
        self.codebook = metadata['codebook']
        self.symbol_lengths = metadata['symbol_lengths']
        
        # Rebuild decode tree
        self._rebuild_decode_tree()
        
        # Convert bytes to bit string
        bit_string = bin(int.from_bytes(encoded_bytes, byteorder='big'))[2:]
        bit_string = bit_string.zfill(len(encoded_bytes) * 8)
        
        # Remove padding
        if metadata['padding'] > 0:
            bit_string = bit_string[:-metadata['padding']]
        
        # Decode symbols
        decoded = []
        current_code = ''
        reverse_codebook = {v: k for k, v in self.codebook.items()}
        
        for bit in bit_string:
            current_code += bit
            if current_code in reverse_codebook:
                decoded.append(reverse_codebook[current_code])
                current_code = ''
                
                if len(decoded) >= metadata['num_symbols']:
                    break
        
        # Reshape
        decoded_array = np.array(decoded, dtype=np.int16)
        return decoded_array.reshape(metadata['original_shape'])
    
    def _rebuild_decode_tree(self):
        """Rebuild decode tree from codebook."""
        self.decode_tree = HuffmanNode()
        
        for symbol, code in self.codebook.items():
            node = self.decode_tree
            for bit in code[:-1]:
                if bit == '0':
                    if node.left is None:
                        node.left = HuffmanNode()
                    node = node.left
                else:
                    if node.right is None:
                        node.right = HuffmanNode()
                    node = node.right
            
            # Last bit
            if code[-1] == '0':
                node.left = HuffmanNode(symbol=symbol)
            else:
                node.right = HuffmanNode(symbol=symbol)
    
    def get_compression_stats(self, data: np.ndarray) -> Dict:
        """
        Calculate compression statistics.
        
        Args:
            data: Original data
        
        Returns:
            Statistics dictionary
        """
        if len(self.codebook) == 0:
            self.build_codebook(data)
        
        # Calculate average code length
        frequencies = Counter(data.flatten())
        total_symbols = sum(frequencies.values())
        
        avg_length = sum(
            frequencies[sym] * len(self.codebook[sym]) 
            for sym in frequencies
        ) / total_symbols
        
        # Theoretical entropy
        entropy = -sum(
            (freq / total_symbols) * np.log2(freq / total_symbols)
            for freq in frequencies.values()
        )
        
        return {
            'num_symbols': len(self.codebook),
            'avg_code_length': avg_length,
            'entropy': entropy,
            'efficiency': entropy / avg_length if avg_length > 0 else 0
        }


def zigzag_indices(size: int) -> List[Tuple[int, int]]:
    """
    Generate zig-zag scan indices for a square block.
    
    Args:
        size: Block dimension (must be square)
    
    Returns:
        List of (row, col) tuples in zig-zag order
    """
    indices = []
    
    for diagonal in range(2 * size - 1):
        if diagonal % 2 == 0:
            # Even diagonal: go up-right
            row = min(diagonal, size - 1)
            col = diagonal - row
            
            while row >= 0 and col < size:
                indices.append((row, col))
                row -= 1
                col += 1
        else:
            # Odd diagonal: go down-left
            col = min(diagonal, size - 1)
            row = diagonal - col
            
            while col >= 0 and row < size:
                indices.append((row, col))
                row += 1
                col -= 1
    
    return indices


def zigzag_scan(block: np.ndarray) -> np.ndarray:
    """
    Apply zig-zag scanning to coefficient block.
    
    Args:
        block: 2D coefficient array
    
    Returns:
        1D array in zig-zag order
    """
    if block.shape[0] != block.shape[1]:
        raise ValueError("Block must be square for zig-zag scanning")
    
    size = block.shape[0]
    indices = zigzag_indices(size)
    
    return np.array([block[i, j] for i, j in indices])


def inverse_zigzag_scan(coeffs: np.ndarray, size: int) -> np.ndarray:
    """
    Reconstruct 2D block from zig-zag scanned coefficients.
    
    Args:
        coeffs: 1D array of coefficients
        size: Block dimension
    
    Returns:
        2D coefficient block
    """
    block = np.zeros((size, size), dtype=coeffs.dtype)
    indices = zigzag_indices(size)
    
    for k, (i, j) in enumerate(indices):
        if k < len(coeffs):
            block[i, j] = coeffs[k]
    
    return block


def run_length_encode(data: np.ndarray) -> List[Tuple[int, int]]:
    """
    Run-length encode a 1D array.
    
    Args:
        data: 1D array (typically from zig-zag scan)
    
    Returns:
        List of (value, run_length) tuples
    """
    if len(data) == 0:
        return []
    
    encoded = []
    current_value = data[0]
    current_run = 1
    
    for value in data[1:]:
        if value == current_value and current_run < 255:
            current_run += 1
        else:
            encoded.append((int(current_value), current_run))
            current_value = value
            current_run = 1
    
    # Add last run
    encoded.append((int(current_value), current_run))
    
    return encoded


def run_length_decode(encoded: List[Tuple[int, int]]) -> np.ndarray:
    """
    Decode run-length encoded data.
    
    Args:
        encoded: List of (value, run_length) tuples
    
    Returns:
        Decoded 1D array
    """
    decoded = []
    for value, run_length in encoded:
        decoded.extend([value] * run_length)
    
    return np.array(decoded, dtype=np.int16)
