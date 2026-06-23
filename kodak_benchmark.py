"""
Kodak Lossless True Color Image Suite Benchmark

Downloads and benchmarks PAWC compression on the standard Kodak dataset (24 images).
This is the de facto standard benchmark for image compression research.
"""

import os
import urllib.request
from pathlib import Path
import numpy as np
from PIL import Image
import json
import time
from typing import Dict, List

from pawc import compress_file, decompress_file, CompressionConfig
from pawc.metrics import calculate_psnr, calculate_ssim, calculate_ms_ssim


# Kodak dataset URLs (hosted on various mirrors)
KODAK_BASE_URL = "http://r0k.us/graphics/kodak/kodak/"
KODAK_IMAGES = [f"kodim{i:02d}.png" for i in range(1, 25)]  # kodim01.png to kodim24.png


def download_kodak_dataset(output_dir: Path):
    """Download the Kodak dataset if not already present."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Downloading Kodak Lossless True Color Image Suite...")
    print("(24 images, 768×512 pixels each, standard benchmark dataset)")
    print()
    
    for i, img_name in enumerate(KODAK_IMAGES, 1):
        img_path = output_dir / img_name
        
        if img_path.exists():
            print(f"[{i}/24] {img_name} - already exists")
            continue
        
        url = KODAK_BASE_URL + img_name
        print(f"[{i}/24] Downloading {img_name}...", end=" ")
        
        try:
            urllib.request.urlretrieve(url, img_path)
            print("✓")
        except Exception as e:
            print(f"✗ Error: {e}")
            # Try alternate URL
            alt_url = f"https://r0k.us/graphics/kodak/kodak/{img_name}"
            try:
                print(f"      Trying alternate URL...", end=" ")
                urllib.request.urlretrieve(alt_url, img_path)
                print("✓")
            except Exception as e2:
                print(f"✗ Failed: {e2}")
    
    print(f"\nDataset ready in: {output_dir}")


def compress_jpeg(input_path: Path, output_path: Path, quality: int) -> Dict:
    """Compress image using JPEG."""
    img = Image.open(input_path)
    
    start_time = time.time()
    img.save(output_path, 'JPEG', quality=quality, optimize=True)
    compress_time = time.time() - start_time
    
    compressed_size = output_path.stat().st_size
    
    # Load for quality measurement
    compressed_img = np.array(Image.open(output_path))
    original_img = np.array(img)
    
    return {
        'size': compressed_size,
        'time': compress_time,
        'compressed_img': compressed_img,
        'original_img': original_img
    }


def compress_webp(input_path: Path, output_path: Path, quality: int) -> Dict:
    """Compress image using WebP."""
    img = Image.open(input_path)
    
    start_time = time.time()
    img.save(output_path, 'WEBP', quality=quality, method=6)
    compress_time = time.time() - start_time
    
    compressed_size = output_path.stat().st_size
    
    # Load for quality measurement
    compressed_img = np.array(Image.open(output_path))
    original_img = np.array(img)
    
    return {
        'size': compressed_size,
        'time': compress_time,
        'compressed_img': compressed_img,
        'original_img': original_img
    }


def compress_pawc(input_path: Path, output_path: Path, quality: int) -> Dict:
    """Compress image using PAWC."""
    original_img = np.array(Image.open(input_path))
    
    config = CompressionConfig(quality=quality)
    
    start_time = time.time()
    stats = compress_file(str(input_path), str(output_path), config)
    compress_time = time.time() - start_time
    
    # Decompress for quality measurement
    decompressed_path = output_path.with_suffix('.png')
    compressed_img = decompress_file(str(output_path), str(decompressed_path))
    
    # Clean up decompressed file
    decompressed_path.unlink()
    
    return {
        'size': stats['compressed_size'],
        'time': compress_time,
        'compressed_img': compressed_img,
        'original_img': original_img
    }


def benchmark_single_image(image_path: Path, output_dir: Path, quality: int):
    """Benchmark all codecs on a single image at given quality."""
    image_name = image_path.stem
    results = {'image': image_name, 'quality': quality}
    
    original_size = image_path.stat().st_size
    results['original_size'] = original_size
    
    print(f"\n  Testing {image_name} (quality {quality}):")
    
    # PAWC
    print(f"    PAWC...", end=" ", flush=True)
    try:
        pawc_output = output_dir / f"{image_name}_q{quality}_pawc.pawc"
        pawc_result = compress_pawc(image_path, pawc_output, quality)
        
        psnr = calculate_psnr(pawc_result['original_img'], pawc_result['compressed_img'])
        ssim = calculate_ssim(pawc_result['original_img'], pawc_result['compressed_img'])
        ms_ssim = calculate_ms_ssim(pawc_result['original_img'], pawc_result['compressed_img'])
        bpp = (pawc_result['size'] * 8) / (768 * 512)
        ratio = original_size / pawc_result['size']
        
        results['pawc'] = {
            'size': pawc_result['size'],
            'time': pawc_result['time'],
            'psnr': psnr,
            'ssim': ssim,
            'ms_ssim': ms_ssim,
            'bpp': bpp,
            'ratio': ratio
        }
        print(f"✓ ({pawc_result['size']:,} bytes, {psnr:.2f} dB)")
    except Exception as e:
        print(f"✗ Error: {e}")
        results['pawc'] = None
    
    # JPEG
    print(f"    JPEG...", end=" ", flush=True)
    try:
        jpeg_output = output_dir / f"{image_name}_q{quality}_jpeg.jpg"
        jpeg_result = compress_jpeg(image_path, jpeg_output, quality)
        
        psnr = calculate_psnr(jpeg_result['original_img'], jpeg_result['compressed_img'])
        ssim = calculate_ssim(jpeg_result['original_img'], jpeg_result['compressed_img'])
        ms_ssim = calculate_ms_ssim(jpeg_result['original_img'], jpeg_result['compressed_img'])
        bpp = (jpeg_result['size'] * 8) / (768 * 512)
        ratio = original_size / jpeg_result['size']
        
        results['jpeg'] = {
            'size': jpeg_result['size'],
            'time': jpeg_result['time'],
            'psnr': psnr,
            'ssim': ssim,
            'ms_ssim': ms_ssim,
            'bpp': bpp,
            'ratio': ratio
        }
        print(f"✓ ({jpeg_result['size']:,} bytes, {psnr:.2f} dB)")
    except Exception as e:
        print(f"✗ Error: {e}")
        results['jpeg'] = None
    
    # WebP
    print(f"    WebP...", end=" ", flush=True)
    try:
        webp_output = output_dir / f"{image_name}_q{quality}_webp.webp"
        webp_result = compress_webp(image_path, webp_output, quality)
        
        psnr = calculate_psnr(webp_result['original_img'], webp_result['compressed_img'])
        ssim = calculate_ssim(webp_result['original_img'], webp_result['compressed_img'])
        ms_ssim = calculate_ms_ssim(webp_result['original_img'], webp_result['compressed_img'])
        bpp = (webp_result['size'] * 8) / (768 * 512)
        ratio = original_size / webp_result['size']
        
        results['webp'] = {
            'size': webp_result['size'],
            'time': webp_result['time'],
            'psnr': psnr,
            'ssim': ssim,
            'ms_ssim': ms_ssim,
            'bpp': bpp,
            'ratio': ratio
        }
        print(f"✓ ({webp_result['size']:,} bytes, {psnr:.2f} dB)")
    except Exception as e:
        print(f"✗ Error: {e}")
        results['webp'] = None
    
    return results


def run_kodak_benchmark(qualities: List[int] = [70, 85, 95]):
    """Run full Kodak benchmark."""
    # Setup directories
    dataset_dir = Path("kodak_dataset")
    output_dir = Path("kodak_results")
    output_dir.mkdir(exist_ok=True)
    
    # Download dataset if needed
    download_kodak_dataset(dataset_dir)
    
    # Get all Kodak images
    images = sorted(dataset_dir.glob("kodim*.png"))
    
    if len(images) == 0:
        print("ERROR: No Kodak images found!")
        return
    
    print(f"\n{'='*80}")
    print(f"KODAK BENCHMARK - {len(images)} images × {len(qualities)} quality levels")
    print(f"{'='*80}")
    
    all_results = []
    
    for quality in qualities:
        print(f"\n{'='*80}")
        print(f"Quality Level: {quality}")
        print(f"{'='*80}")
        
        for img_path in images:
            result = benchmark_single_image(img_path, output_dir, quality)
            all_results.append(result)
    
    # Save results to JSON
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


def print_summary(results: List[Dict], qualities: List[int]):
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
        
        for codec in ['pawc', 'jpeg', 'webp']:
            codec_results = [r[codec] for r in quality_results if r[codec] is not None]
            
            if not codec_results:
                continue
            
            avg_psnr = np.mean([r['psnr'] for r in codec_results])
            avg_ssim = np.mean([r['ssim'] for r in codec_results])
            avg_ms_ssim = np.mean([r['ms_ssim'] for r in codec_results])
            avg_bpp = np.mean([r['bpp'] for r in codec_results])
            avg_ratio = np.mean([r['ratio'] for r in codec_results])
            avg_time = np.mean([r['time'] for r in codec_results])
            
            print(f"\n  {codec.upper():5s} | "
                  f"PSNR: {avg_psnr:5.2f} dB | "
                  f"SSIM: {avg_ssim:.4f} | "
                  f"MS-SSIM: {avg_ms_ssim:.4f} | "
                  f"BPP: {avg_bpp:.3f} | "
                  f"Ratio: {avg_ratio:.2f}:1 | "
                  f"Time: {avg_time:.2f}s")
    
    print("\n" + "="*100)


if __name__ == '__main__':
    # Run benchmark at three quality levels
    run_kodak_benchmark(qualities=[70, 85, 95])
