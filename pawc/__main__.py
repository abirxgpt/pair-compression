"""
Command-line interface for PAWC compression.

Usage:
    python -m pawc compress input.jpg output.pawc --quality 85
    python -m pawc decompress input.pawc output.jpg
"""

import argparse
import sys
from pathlib import Path

from .core import compress_file, decompress_file
from .config import CompressionConfig
from .metrics import calculate_psnr, calculate_ssim, calculate_ms_ssim
from PIL import Image
import numpy as np


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='PAWC - Perceptual Adaptive Wavelet Compression',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Compress an image:
    python -m pawc compress input.jpg output.pawc --quality 85
  
  Decompress an image:
    python -m pawc decompress input.pawc output.jpg
  
  Compress with quality comparison:
    python -m pawc compress input.jpg output.pawc --quality 90 --compare
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Compress command
    compress_parser = subparsers.add_parser('compress', help='Compress an image')
    compress_parser.add_argument('input', type=str, help='Input image file')
    compress_parser.add_argument('output', type=str, help='Output compressed file (.pawc)')
    compress_parser.add_argument('--quality', type=int, default=85,
                                help='Compression quality (1-100, default: 85)')
    compress_parser.add_argument('--preset', type=str, choices=['high', 'balanced', 'fast'],
                                help='Use quality preset')
    compress_parser.add_argument('--compare', action='store_true',
                                help='Compare with original after compression')
    
    # Decompress command
    decompress_parser = subparsers.add_parser('decompress', help='Decompress an image')
    decompress_parser.add_argument('input', type=str, help='Input compressed file (.pawc)')
    decompress_parser.add_argument('output', type=str, help='Output image file')
    
    # Parse arguments
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == 'compress':
            compress_command(args)
        elif args.command == 'decompress':
            decompress_command(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def compress_command(args):
    """Handle compress command."""
    # Create configuration
    if args.preset:
        if args.preset == 'high':
            config = CompressionConfig.preset_high_quality()
        elif args.preset == 'balanced':
            config = CompressionConfig.preset_balanced()
        elif args.preset == 'fast':
            config = CompressionConfig.preset_high_compression()
    else:
        config = CompressionConfig(quality=args.quality)
    
    # Compress
    stats = compress_file(args.input, args.output, config)
    
    # Compare if requested
    if args.compare:
        print("\n[PAWC] Computing quality metrics...")
        
        # Load original
        original = np.array(Image.open(args.input))
        
        # Decompress to compare
        from .core import decompress_file
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            reconstructed = decompress_file(args.output, tmp_path)
            
            # Calculate metrics
            psnr = calculate_psnr(original, reconstructed)
            ssim = calculate_ssim(original, reconstructed)
            ms_ssim = calculate_ms_ssim(original, reconstructed)
            
            print(f"\n[PAWC] Quality Metrics:")
            print(f"  PSNR: {psnr:.2f} dB")
            print(f"  SSIM: {ssim:.4f}")
            print(f"  MS-SSIM: {ms_ssim:.4f}")
        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)


def decompress_command(args):
    """Handle decompress command."""
    decompress_file(args.input, args.output)
    print(f"[PAWC] Successfully decompressed to: {args.output}")


if __name__ == '__main__':
    main()
