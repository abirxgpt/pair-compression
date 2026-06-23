"""
Benchmark PAIR on full Kodak dataset (24 images).
"""

import os
from pathlib import Path
import numpy as np
from PIL import Image
import json
import time

from pawc.pair_codec import compress_file_pair, decompress_file_pair  
from pawc.metrics import calculate_psnr, calculate_ssim, calculate_ms_ssim
from pawc.config import CompressionConfig


def benchmark_pair_on_kodak(qualities=[70, 85, 95]):
    """Run PAIR benchmark on Kodak dataset."""
    dataset_dir = Path("kodak_dataset")
    output_dir = Path("pair_results")
    output_dir.mkdir(exist_ok=True)
    
    # Get all Kodak images
    images = sorted(dataset_dir.glob("kodim*.png"))
    
    if len(images) == 0:
        print("ERROR: No Kodak images found!")
        return
    
    print("="*80)
    print(f"PAIR KODAK BENCHMARK - {len(images)} images × {len(qualities)} quality levels")
    print("="*80)
    
    all_results = []
    
    for quality in qualities:
        print(f"\n{'='*80}")
        print(f"Quality Level: {quality}")
        print(f"{'='*80}")
        
        for img_path in images:
            print(f"\n  Testing {img_path.name} (quality {quality}):")
            print(f"    PAIR...", end=" ", flush=True)
            
            original_img = np.array(Image.open(img_path))
            original_size = img_path.stat().st_size
            
            try:
                # Compress
                output_path = output_dir / f"{img_path.stem}_q{quality}.jp2"
                config = CompressionConfig(quality=quality)
                
                start_time = time.time()
                stats = compress_file_pair(str(img_path), str(output_path), config)
                compress_time = time.time() - start_time
                
                # Decompress
                dec_path = output_dir / f"{img_path.stem}_q{quality}_dec.png"
                decompressed_img = decompress_file_pair(str(output_path), str(dec_path))
                
                # Metrics
                psnr = calculate_psnr(original_img, decompressed_img)
                ssim = calculate_ssim(original_img, decompressed_img)
                ms_ssim = calculate_ms_ssim(original_img, decompressed_img)
                
                compressed_size = stats['compressed_size']
                ratio = stats['compression_ratio']
                bpp = (compressed_size * 8) / (768 * 512)
                
                result = {
                    'image': img_path.stem,
                    'quality': quality,
                    'original_size': original_size,
                    'compressed_size': compressed_size,
                    'ratio': ratio,
                    'bpp': bpp,
                    'psnr': psnr,
                    'ssim': ssim,
                    'ms_ssim': ms_ssim,
                    'time': compress_time,
                    'tier_distribution': stats['metadata']['tier_distribution']
                }
                
                all_results.append(result)
                
                print(f"✓ ({compressed_size:,} bytes, {psnr:.2f} dB, {ssim:.4f} SSIM)")
                
                # Clean up decompressed file
                dec_path.unlink()
                
            except Exception as e:
                print(f"✗ Error: {e}")
    
    # Save results
    results_file = output_dir / "benchmark_results.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n{'='*80}")
    print("BENCHMARK COMPLETE!")
    print(f"Results saved to: {results_file}")
    print(f"{'='*80}")
    
    # Print summary
    print_summary(all_results, qualities)
    
    return all_results


def print_summary(results, qualities):
    """Print summary statistics."""
    print("\n" + "="*100)
    print("SUMMARY STATISTICS")
    print("="*100)
    
    for quality in qualities:
        print(f"\n{'─'*100}")
        print(f"Quality {quality}")
        print(f"{'─'*100}")
        
        # Filter results for this quality
        quality_results = [r for r in results if r['quality'] == quality]
        
        if not quality_results:
            continue
        
        avg_psnr = np.mean([r['psnr'] for r in quality_results])
        avg_ssim = np.mean([r['ssim'] for r in quality_results])
        avg_ms_ssim = np.mean([r['ms_ssim'] for r in quality_results])
        avg_bpp = np.mean([r['bpp'] for r in quality_results])
        avg_ratio = np.mean([r['ratio'] for r in quality_results])
        avg_time = np.mean([r['time'] for r in quality_results])
        
        print(f"\n  PAIR | "
              f"PSNR: {avg_psnr:5.2f} dB | "
              f"SSIM: {avg_ssim:.4f} | "
              f"MS-SSIM: {avg_ms_ssim:.4f} | "
              f"BPP: {avg_bpp:.3f} | "
              f"Ratio: {avg_ratio:.2f}:1 | "
              f"Time: {avg_time:.2f}s")
        
        # Compare with baselines
        baseline_jpeg = {70: (34.91, 0.923, 1.19), 85: (37.52, 0.950, 1.77), 95: (40.84, 0.974, 2.88)}
        baseline_webp = {70: (35.14, 0.923, 0.86), 85: (40.58, 0.977, 1.47), 95: (44.01, 0.989, 2.48)}
        
        if quality in baseline_jpeg:
            jpeg_psnr, jpeg_ssim, jpeg_bpp = baseline_jpeg[quality]
            print(f"  JPEG | PSNR: {jpeg_psnr:5.2f} dB | SSIM: {jpeg_ssim:.4f} | BPP: {jpeg_bpp:.3f}")
            print(f"  Δ    | PSNR: {avg_psnr - jpeg_psnr:+5.2f} dB | SSIM: {avg_ssim - jpeg_ssim:+.4f} | BPP: {avg_bpp - jpeg_bpp:+.3f}")
    
    print("\n" + "="*100)


if __name__ == '__main__':
    # Run benchmark
    benchmark_pair_on_kodak(qualities=[70, 85, 95])
