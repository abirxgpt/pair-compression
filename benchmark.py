"""
Comprehensive benchmarking script for PAWC compression.

Compares PAWC against JPEG, PNG, and WebP codecs.
"""

import numpy as np
from PIL import Image
import tempfile
from pathlib import Path
import time
import argparse
from typing import Dict, List
import json

from pawc.core import compress_file, decompress_file
from pawc.config import CompressionConfig
from pawc.metrics import (
    calculate_psnr, 
    calculate_ssim, 
    calculate_ms_ssim,
    calculate_compression_ratio,
    calculate_bpp
)


class CodecBenchmark:
    """Benchmarks codecs on a set of test images."""
    
    def __init__(self, output_dir: Path):
        """
        Initialize benchmark.
        
        Args:
            output_dir: Directory to store compressed files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = []
    
    def generate_test_images(self, sizes=[(256, 256), (512, 512), (1024, 1024)]) -> List[Path]:
        """Generate synthetic test images."""
        test_images = []
        
        for idx, (h, w) in enumerate(sizes):
            # Create diverse test images
            images = {
                f'random_{h}x{w}': np.random.randint(0, 256, size=(h, w, 3), dtype=np.uint8),
                f'gradient_{h}x{w}': self._create_gradient(h, w),
                f'texture_{h}x{w}': self._create_texture(h, w),
            }
            
            for name, img_array in images.items():
                path = self.output_dir / f'{name}.png'
                Image.fromarray(img_array).save(path)
                test_images.append(path)
        
        return test_images
    
    @staticmethod
    def _create_gradient(h: int, w: int) -> np.ndarray:
        """Create gradient test image."""
        x = np.linspace(0, 255, w)
        y = np.linspace(0, 255, h)
        xv, yv = np.meshgrid(x, y)
        
        r = xv.astype(np.uint8)
        g = yv.astype(np.uint8)
        b = ((xv + yv) / 2).astype(np.uint8)
        
        return np.stack([r, g, b], axis=-1)
    
    @staticmethod
    def _create_texture(h: int, w: int) -> np.ndarray:
        """Create textured test image."""
        # High-frequency pattern
        freq = 10
        x = np.linspace(0, freq * np.pi, w)
        y = np.linspace(0, freq * np.pi, h)
        xv, yv = np.meshgrid(x, y)
        
        texture = (np.sin(xv) * np.cos(yv) * 127 + 128).astype(np.uint8)
        
        return np.stack([texture, texture, texture], axis=-1)
    
    def benchmark_pawc(self, image_path: Path, quality: int) -> Dict:
        """Benchmark PAWC codec."""
        # Load original
        original = np.array(Image.open(image_path))
        original_size = image_path.stat().st_size
        
        # Compress
        compressed_path = self.output_dir / f'{image_path.stem}_pawc_q{quality}.pawc'
        
        config = CompressionConfig(quality=quality)
        
        start_time = time.time()
        compress_file(image_path, compressed_path, config)
        compress_time = time.time() - start_time
        
        # Decompress
        output_path = self.output_dir / f'{image_path.stem}_pawc_q{quality}_dec.png'
        
        start_time = time.time()
        reconstructed = decompress_file(compressed_path, output_path)
        decompress_time = time.time() - start_time
        
        # Metrics
        compressed_size = compressed_path.stat().st_size
        
        return {
            'codec': 'PAWC',
            'quality': quality,
            'original_size': original_size,
            'compressed_size': compressed_size,
            'compression_ratio': calculate_compression_ratio(original_size, compressed_size),
            'bpp': calculate_bpp(compressed_size, original.shape[1], original.shape[0]),
            'psnr': calculate_psnr(original, reconstructed),
            'ssim': calculate_ssim(original, reconstructed),
            'ms_ssim': calculate_ms_ssim(original, reconstructed),
            'compress_time': compress_time,
            'decompress_time': decompress_time
        }
    
    def benchmark_jpeg(self, image_path: Path, quality: int) -> Dict:
        """Benchmark JPEG codec."""
        original = np.array(Image.open(image_path))
        original_size = image_path.stat().st_size
        
        # Compress
        compressed_path = self.output_dir / f'{image_path.stem}_jpeg_q{quality}.jpg'
        
        img = Image.open(image_path)
        start_time = time.time()
        img.save(compressed_path, 'JPEG', quality=quality, optimize=True)
        compress_time = time.time() - start_time
        
        # Decompress (load)
        start_time = time.time()
        reconstructed = np.array(Image.open(compressed_path))
        decompress_time = time.time() - start_time
        
        compressed_size = compressed_path.stat().st_size
        
        return {
            'codec': 'JPEG',
            'quality': quality,
            'original_size': original_size,
            'compressed_size': compressed_size,
            'compression_ratio': calculate_compression_ratio(original_size, compressed_size),
            'bpp': calculate_bpp(compressed_size, original.shape[1], original.shape[0]),
            'psnr': calculate_psnr(original, reconstructed),
            'ssim': calculate_ssim(original, reconstructed),
            'ms_ssim': calculate_ms_ssim(original, reconstructed),
            'compress_time': compress_time,
            'decompress_time': decompress_time
        }
    
    def benchmark_webp(self, image_path: Path, quality: int) -> Dict:
        """Benchmark WebP codec."""
        original = np.array(Image.open(image_path))
        original_size = image_path.stat().st_size
        
        # Compress
        compressed_path = self.output_dir / f'{image_path.stem}_webp_q{quality}.webp'
        
        img = Image.open(image_path)
        start_time = time.time()
        img.save(compressed_path, 'WEBP', quality=quality)
        compress_time = time.time() - start_time
        
        # Decompress
        start_time = time.time()
        reconstructed = np.array(Image.open(compressed_path))
        decompress_time = time.time() - start_time
        
        compressed_size = compressed_path.stat().st_size
        
        return {
            'codec': 'WebP',
            'quality': quality,
            'original_size': original_size,
            'compressed_size': compressed_size,
            'compression_ratio': calculate_compression_ratio(original_size, compressed_size),
            'bpp': calculate_bpp(compressed_size, original.shape[1], original.shape[0]),
            'psnr': calculate_psnr(original, reconstructed),
            'ssim': calculate_ssim(original, reconstructed),
            'ms_ssim': calculate_ms_ssim(original, reconstructed),
            'compress_time': compress_time,
            'decompress_time': decompress_time
        }
    
    def benchmark_png(self, image_path: Path) -> Dict:
        """Benchmark PNG codec (lossless)."""
        original = np.array(Image.open(image_path))
        original_size = image_path.stat().st_size
        
        # Compress
        compressed_path = self.output_dir / f'{image_path.stem}_png.png'
        
        img = Image.open(image_path)
        start_time = time.time()
        img.save(compressed_path, 'PNG', optimize=True)
        compress_time = time.time() - start_time
        
        # Decompress
        start_time = time.time()
        reconstructed = np.array(Image.open(compressed_path))
        decompress_time = time.time() - start_time
        
        compressed_size = compressed_path.stat().st_size
        
        return {
            'codec': 'PNG',
            'quality': 100,  # Lossless
            'original_size': original_size,
            'compressed_size': compressed_size,
            'compression_ratio': calculate_compression_ratio(original_size, compressed_size),
            'bpp': calculate_bpp(compressed_size, original.shape[1], original.shape[0]),
            'psnr': float('inf'),  # Perfect reconstruction
            'ssim': 1.0,
            'ms_ssim': 1.0,
            'compress_time': compress_time,
            'decompress_time': decompress_time
        }
    
    def run_benchmark(self, test_images: List[Path], qualities: List[int] = [75, 85, 95]):
        """Run comprehensive benchmark."""
        print(f"[Benchmark] Running benchmarks on {len(test_images)} images with qualities {qualities}")
        
        for image_path in test_images:
            print(f"\n[Benchmark] Processing: {image_path.name}")
            
            for quality in qualities:
                # PAWC
                try:
                    result = self.benchmark_pawc(image_path, quality)
                    result['image'] = image_path.name
                    self.results.append(result)
                    print(f"  PAWC Q{quality}: {result['psnr']:.2f} dB, {result['compression_ratio']:.2f}:1")
                except Exception as e:
                    print(f"  PAWC Q{quality} failed: {e}")
                
                # JPEG
                try:
                    result = self.benchmark_jpeg(image_path, quality)
                    result['image'] = image_path.name
                    self.results.append(result)
                    print(f"  JPEG Q{quality}: {result['psnr']:.2f} dB, {result['compression_ratio']:.2f}:1")
                except Exception as e:
                    print(f"  JPEG Q{quality} failed: {e}")
                
                # WebP
                try:
                    result = self.benchmark_webp(image_path, quality)
                    result['image'] = image_path.name
                    self.results.append(result)
                    print(f"  WebP Q{quality}: {result['psnr']:.2f} dB, {result['compression_ratio']:.2f}:1")
                except Exception as e:
                    print(f"  WebP Q{quality} failed: {e}")
            
            # PNG (once per image)
            try:
                result = self.benchmark_png(image_path)
                result['image'] = image_path.name
                self.results.append(result)
                print(f"  PNG: Lossless, {result['compression_ratio']:.2f}:1")
            except Exception as e:
                print(f"  PNG failed: {e}")
    
    def save_results(self, filename: str = 'benchmark_results.json'):
        """Save benchmark results to JSON."""
        output_path = self.output_dir / filename
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n[Benchmark] Results saved to: {output_path}")
    
    def print_summary(self):
        """Print summary statistics."""
        import pandas as pd
        
        df = pd.DataFrame(self.results)
        
        print("\n" + "="*80)
        print("BENCHMARK SUMMARY")
        print("="*80)
        
        for codec in ['PAWC', 'JPEG', 'WebP', 'PNG']:
            codec_data = df[df['codec'] == codec]
            if len(codec_data) == 0:
                continue
            
            print(f"\n{codec}:")
            print(f"  Avg PSNR: {codec_data['psnr'].replace([np.inf], np.nan).mean():.2f} dB")
            print(f"  Avg SSIM: {codec_data['ssim'].mean():.4f}")
            print(f"  Avg MS-SSIM: {codec_data['ms_ssim'].mean():.4f}")
            print(f"  Avg Compression Ratio: {codec_data['compression_ratio'].mean():.2f}:1")
            print(f"  Avg BPP: {codec_data['bpp'].mean():.4f}")


def main():
    """Main benchmark entry point."""
    parser = argparse.ArgumentParser(description='Benchmark PAWC against other codecs')
    parser.add_argument('--output-dir', type=str, default='benchmark_output',
                       help='Output directory for results')
    parser.add_argument('--qualities', type=int, nargs='+', default=[75, 85, 95],
                       help='Quality levels to test')
    parser.add_argument('--images', type=str, nargs='+',
                       help='Paths to test images (generates synthetic if not provided)')
    
    args = parser.parse_args()
    
    # Create benchmark
    benchmark = CodecBenchmark(Path(args.output_dir))
    
    # Get test images
    if args.images:
        test_images = [Path(img) for img in args.images]
    else:
        print("[Benchmark] Generating synthetic test images...")
        test_images = benchmark.generate_test_images()
    
    # Run benchmark
    benchmark.run_benchmark(test_images, args.qualities)
    
    # Save and display results
    benchmark.save_results()
    
    try:
        benchmark.print_summary()
    except ImportError:
        print("\n[Benchmark] Install pandas for summary statistics: pip install pandas")


if __name__ == '__main__':
    main()
