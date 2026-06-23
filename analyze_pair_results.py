"""
Analyze and compare PAIR results against baselines.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Load PAIR results
pair_results = json.load(open('pair_results/benchmark_results.json'))

# Load baseline results (from kodak_benchmark.py)
baseline_results = json.load(open('kodak_results/benchmark_results.json'))

# Group by quality
qualities = [70, 85, 95]

print("="*100)
print("PAIR vs BASELINE COMPARISON - Kodak Dataset")
print("="*100)

for quality in qualities:
    print(f"\n{'='*100}")
    print(f"Quality {quality}")
    print(f"{'='*100}\n")
    
    # Filter results
    pair_q = [r for r in pair_results if r['quality'] == quality]
    baseline_q = [r for r in baseline_results if r['quality'] == quality]
    
    # Calculate averages
    pair_avg = {
        'psnr': np.mean([r['psnr'] for r in pair_q]),
        'ssim': np.mean([r['ssim'] for r in pair_q]),
        'ms_ssim': np.mean([r['ms_ssim'] for r in pair_q]),
        'bpp': np.mean([r['bpp'] for r in pair_q]),
        'ratio': np.mean([r['ratio'] for r in pair_q]),
        'time': np.mean([r['time'] for r in pair_q])
    }
    
    baseline_pawc_avg = {
        'psnr': np.mean([r['pawc']['psnr'] for r in baseline_q]),
        'ssim': np.mean([r['pawc']['ssim'] for r in baseline_q]),
        'ms_ssim': np.mean([r['pawc']['ms_ssim'] for r in baseline_q]),
        'bpp': np.mean([r['pawc']['bpp'] for r in baseline_q]),
        'ratio': np.mean([r['pawc']['ratio'] for r in baseline_q]),
        'time': np.mean([r['pawc']['time'] for r in baseline_q])
    }
    
    baseline_jpeg_avg = {
        'psnr': np.mean([r['jpeg']['psnr'] for r in baseline_q]),
        'ssim': np.mean([r['jpeg']['ssim'] for r in baseline_q]),
        'ms_ssim': np.mean([r['jpeg']['ms_ssim'] for r in baseline_q]),
        'bpp': np.mean([r['jpeg']['bpp'] for r in baseline_q]),
        'ratio': np.mean([r['jpeg']['ratio'] for r in baseline_q]),
       'time': np.mean([r['jpeg']['time'] for r in baseline_q])
    }
    
    baseline_webp_avg = {
        'psnr': np.mean([r['webp']['psnr'] for r in baseline_q]),
        'ssim': np.mean([r['webp']['ssim'] for r in baseline_q]),
        'ms_ssim': np.mean([r['webp']['ms_ssim'] for r in baseline_q]),
        'bpp': np.mean([r['webp']['bpp'] for r in baseline_q]),
        'ratio': np.mean([r['webp']['ratio'] for r in baseline_q]),
        'time': np.mean([r['webp']['time'] for r in baseline_q])
    }
    
    # Print table
    print(f"{'Codec':<20} | {'PSNR (dB)':>10} | {'SSIM':>8} | {'MS-SSIM':>8} | {'BPP':>6} | {'Ratio':>8} | {'Time (s)':>9}")
    print("-" * 100)
    print(f"{'Old PAWC':<20} | {baseline_pawc_avg['psnr']:>10.2f} | {baseline_pawc_avg['ssim']:>8.4f} | {baseline_pawc_avg['ms_ssim']:>8.4f} | {baseline_pawc_avg['bpp']:>6.3f} | {baseline_pawc_avg['ratio']:>7.2f}:1 | {baseline_pawc_avg['time']:>9.2f}")
    print(f"{'JPEG':<20} | {baseline_jpeg_avg['psnr']:>10.2f} | {baseline_jpeg_avg['ssim']:>8.4f} | {baseline_jpeg_avg['ms_ssim']:>8.4f} | {baseline_jpeg_avg['bpp']:>6.3f} | {baseline_jpeg_avg['ratio']:>7.2f}:1 | {baseline_jpeg_avg['time']:>9.2f}")
    print(f"{'WebP':<20} | {baseline_webp_avg['psnr']:>10.2f} | {baseline_webp_avg['ssim']:>8.4f} | {baseline_webp_avg['ms_ssim']:>8.4f} | {baseline_webp_avg['bpp']:>6.3f} | {baseline_webp_avg['ratio']:>7.2f}:1 | {baseline_webp_avg['time']:>9.2f}")
    print(f"{'PAIR (Novel)':<20} | {pair_avg['psnr']:>10.2f} | {pair_avg['ssim']:>8.4f} | {pair_avg['ms_ssim']:>8.4f} | {pair_avg['bpp']:>6.3f} | {pair_avg['ratio']:>7.2f}:1 | {pair_avg['time']:>9.2f}")
    
    print("\n" + "─" * 100)
    print("PAIR vs JPEG Comparison:")
    print(f"  PSNR:    {pair_avg['psnr'] - baseline_jpeg_avg['psnr']:+.2f} dB")
    print(f"  SSIM:    {pair_avg['ssim'] - baseline_jpeg_avg['ssim']:+.4f}")
    print(f"  MS-SSIM: {pair_avg['ms_ssim'] - baseline_jpeg_avg['ms_ssim']:+.4f}")
    print(f"  BPP:     {pair_avg['bpp'] - baseline_jpeg_avg['bpp']:+.3f}")
    print(f"  File:    {((pair_avg['bpp'] / baseline_jpeg_avg['bpp']) - 1) * 100:+.1f}% size change")
    
    print("\n" + "─" * 100)
    print("PAIR vs Old PAWC Comparison:")
    print(f"  PSNR:    {pair_avg['psnr'] - baseline_pawc_avg['psnr']:+.2f} dB improvement")
    print(f"  SSIM:    {pair_avg['ssim'] - baseline_pawc_avg['ssim']:+.4f} improvement")
    print(f"  BPP:     {pair_avg['bpp'] - baseline_pawc_avg['bpp']:+.3f} ({((baseline_pawc_avg['bpp'] / pair_avg['bpp']) - 1) * 100:+.1f}% file reduction)")

print("\n" + "="*100)
print("SUMMARY")
print("="*100)

# Overall comparison across all quality levels
all_pair = {
    'psnr': np.mean([r['psnr'] for r in pair_results]),
    'ssim': np.mean([r['ssim'] for r in pair_results]),
    'ms_ssim': np.mean([r['ms_ssim'] for r in pair_results]),
    'bpp': np.mean([r['bpp'] for r in pair_results]),
}

all_jpeg = {
    'psnr': np.mean([r['jpeg']['psnr'] for r in baseline_results]),
    'ssim': np.mean([r['jpeg']['ssim'] for r in baseline_results]),
    'ms_ssim': np.mean([r['jpeg']['ms_ssim'] for r in baseline_results]),
    'bpp': np.mean([r['jpeg']['bpp'] for r in baseline_results]),
}

all_pawc = {
    'psnr': np.mean([r['pawc']['psnr'] for r in baseline_results]),
    'ssim': np.mean([r['pawc']['ssim'] for r in baseline_results]),
    'ms_ssim': np.mean([r['pawc']['ms_ssim'] for r in baseline_results]),
    'bpp': np.mean([r['pawc']['bpp'] for r in baseline_results]),
}

print(f"\nOverall Average (All Quality Levels):")
print(f"  PAIR:     PSNR {all_pair['psnr']:.2f} dB, SSIM {all_pair['ssim']:.4f}, BPP {all_pair['bpp']:.3f}")
print(f"  JPEG:     PSNR {all_jpeg['psnr']:.2f} dB, SSIM {all_jpeg['ssim']:.4f}, BPP {all_jpeg['bpp']:.3f}")
print(f"  Old PAWC: PSNR {all_pawc['psnr']:.2f} dB, SSIM {all_pawc['ssim']:.4f}, BPP {all_pawc['bpp']:.3f}")

print(f"\n✅ PAIR Improvements:")
print(f"  vs JPEG:     {all_pair['psnr'] - all_jpeg['psnr']:+.2f} dB, {all_pair['ssim'] - all_jpeg['ssim']:+.4f} SSIM")
print(f"  vs Old PAWC: {all_pair['psnr'] - all_pawc['psnr']:+.2f} dB, {all_pair['ssim'] - all_pawc['ssim']:+.4f} SSIM")

print("\n" + "="*100)

# Generate comparison charts
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Chart 1: Rate-Distortion (PSNR vs BPP)
ax1 = axes[0, 0]
for quality in qualities:
    pair_q = [r for r in pair_results if r['quality'] == quality]
    baseline_q = [r for r in baseline_results if r['quality'] == quality]
    
    ax1.scatter([np.mean([r['bpp'] for r in pair_q])], 
                [np.mean([r['psnr'] for r in pair_q])],
                s=100, alpha=0.7, label=f'PAIR Q{quality}')
    ax1.scatter([np.mean([r['jpeg']['bpp'] for r in baseline_q])],
                [np.mean([r['jpeg']['psnr'] for r in baseline_q])],
                s=100, marker='s', alpha=0.7, label=f'JPEG Q{quality}')

ax1.set_xlabel('Bits Per Pixel (BPP)')
ax1.set_ylabel('PSNR (dB)')
ax1.set_title('Rate-Distortion Curve: PAIR vs JPEG')
ax1.grid(True, alpha=0.3)
ax1.legend(fontsize=8)

# Chart 2: SSIM Comparison
ax2 = axes[0, 1]
x_pos = np.arange(len(qualities))
width = 0.35

pair_ssim = [np.mean([r['ssim'] for r in pair_results if r['quality'] == q]) for q in qualities]
jpeg_ssim = [np.mean([r['jpeg']['ssim'] for r in baseline_results if r['quality'] == q]) for q in qualities]

ax2.bar(x_pos - width/2, pair_ssim, width, label='PAIR', alpha=0.8)
ax2.bar(x_pos + width/2, jpeg_ssim, width, label='JPEG', alpha=0.8)
ax2.set_ylabel('SSIM')
ax2.set_title('Structural Similarity (SSIM) Comparison')
ax2.set_xticks(x_pos)
ax2.set_xticklabels([f'Q{q}' for q in qualities])
ax2.legend()
ax2.grid(True, axis='y', alpha=0.3)

# Chart 3: Compression Ratio
ax3 = axes[1, 0]
pair_ratio = [np.mean([r['ratio'] for r in pair_results if r['quality'] == q]) for q in qualities]
jpeg_ratio = [np.mean([r['jpeg']['ratio'] for r in baseline_results if r['quality'] == q]) for q in qualities]
pawc_ratio = [np.mean([r['pawc']['ratio'] for r in baseline_results if r['quality'] == q]) for q in qualities]

ax3.plot(qualities, pair_ratio, 'o-', label='PAIR', linewidth=2, markersize=8)
ax3.plot(qualities, jpeg_ratio, 's-', label='JPEG', linewidth=2, markersize=8)
ax3.plot(qualities, pawc_ratio, '^-', label='Old PAWC', linewidth=2, markersize=8)
ax3.set_xlabel('Quality Level')
ax3.set_ylabel('Compression Ratio')
ax3.set_title('Compression Ratio Comparison')
ax3.legend()
ax3.grid(True, alpha=0.3)

# Chart 4: PSNR Comparison
ax4 = axes[1, 1]
pair_psnr = [np.mean([r['psnr'] for r in pair_results if r['quality'] == q]) for q in qualities]
jpeg_psnr = [np.mean([r['jpeg']['psnr'] for r in baseline_results if r['quality'] == q]) for q in qualities]
pawc_psnr = [np.mean([r['pawc']['psnr'] for r in baseline_results if r['quality'] == q]) for q in qualities]

ax4.plot(qualities, pair_psnr, 'o-', label='PAIR', linewidth=2, markersize=8)
ax4.plot(qualities, jpeg_psnr, 's-', label='JPEG', linewidth=2, markersize=8)
ax4.plot(qualities, pawc_psnr, '^-', label='Old PAWC', linewidth=2, markersize=8)
ax4.set_xlabel('Quality Level')
ax4.set_ylabel('PSNR (dB)')
ax4.set_title('PSNR Comparison')
ax4.legend()
ax4.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('pair_results/comparison_charts.png', dpi=150, bbox_inches='tight')
print(f"\n📊 Charts saved to: pair_results/comparison_charts.png")

print("\n" + "="*100)
