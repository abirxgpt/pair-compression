"""Generate the master rate-distortion figure for the paper."""
import json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import statistics, os

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# --- LEFT: PSNR vs BPP ---
# Vanilla J2K
vj2k = json.load(open('experiments/vanilla_j2k/results.json'))
cratios = sorted(set(r['cratio'] for r in vj2k))
vj2k_x = [statistics.mean([r['bpp'] for r in vj2k if r['cratio']==c]) for c in cratios]
vj2k_y = [statistics.mean([r['psnr'] for r in vj2k if r['cratio']==c]) for c in cratios]
ax1.plot(vj2k_x, vj2k_y, 's-', label='JPEG 2000 (vanilla)', color='brown', linewidth=2)

# PAIR Pillow
pp = json.load(open('pair_results/benchmark_results.json'))
pp_x = [statistics.mean([r['bpp'] for r in pp if r['quality']==q]) for q in [70,85,95]]
pp_y = [statistics.mean([r['psnr'] for r in pp if r['quality']==q]) for q in [70,85,95]]
ax1.plot(pp_x, pp_y, 'o-', label='PAIR (Pillow)', color='blue', linewidth=2)

# PAIR glymur
pg = json.load(open('pair_results_glymur/benchmark_results.json'))
pg_x = [statistics.mean([r['bpp'] for r in pg if r['quality']==q]) for q in [70,85,95]]
pg_y = [statistics.mean([r['psnr'] for r in pg if r['quality']==q]) for q in [70,85,95]]
ax1.plot(pg_x, pg_y, 'D-', label='PAIR (glymur tile-ROI)', color='green', linewidth=2)

# JPEG extended
if os.path.exists('experiments/extended_baselines.json'):
    eb = json.load(open('experiments/extended_baselines.json'))
    jpeg_qs = sorted(set(r['quality'] for r in eb['jpeg']))
    jpeg_x = [statistics.mean([r['bpp'] for r in eb['jpeg'] if r['quality']==q]) for q in jpeg_qs]
    jpeg_y = [statistics.mean([r['psnr'] for r in eb['jpeg'] if r['quality']==q]) for q in jpeg_qs]
    ax1.plot(jpeg_x, jpeg_y, '^-', label='JPEG', color='red', linewidth=2)

    webp_x = [statistics.mean([r['bpp'] for r in eb['webp'] if r['quality']==q]) for q in jpeg_qs]
    webp_y = [statistics.mean([r['psnr'] for r in eb['webp'] if r['quality']==q]) for q in jpeg_qs]
    ax1.plot(webp_x, webp_y, 'v-', label='WebP', color='purple', linewidth=2)
else:
    # Fallback: use kodak_results
    kb = json.load(open('kodak_results/benchmark_results.json'))
    jpeg_qs = sorted(set(r['quality'] for r in kb))
    jpeg_x = [statistics.mean([r['jpeg']['bpp'] for r in kb if r['quality']==q]) for q in jpeg_qs]
    jpeg_y = [statistics.mean([r['jpeg']['psnr'] for r in kb if r['quality']==q]) for q in jpeg_qs]
    ax1.plot(jpeg_x, jpeg_y, '^-', label='JPEG', color='red', linewidth=2)

    webp_x = [statistics.mean([r['webp']['bpp'] for r in kb if r['quality']==q]) for q in jpeg_qs]
    webp_y = [statistics.mean([r['webp']['psnr'] for r in kb if r['quality']==q]) for q in jpeg_qs]
    ax1.plot(webp_x, webp_y, 'v-', label='WebP', color='purple', linewidth=2)

ax1.set_xlabel('Bits Per Pixel (BPP)', fontsize=12)
ax1.set_ylabel('PSNR (dB)', fontsize=12)
ax1.set_title('Rate-Distortion (PSNR)', fontsize=14, fontweight='bold')
ax1.legend(fontsize=8)
ax1.grid(True, alpha=0.3)

# --- RIGHT: SSIM vs BPP ---
vj2k_sy = [statistics.mean([r['ssim'] for r in vj2k if r['cratio']==c]) for c in cratios]
ax2.plot(vj2k_x, vj2k_sy, 's-', label='JPEG 2000 (vanilla)', color='brown', linewidth=2)

pp_sy = [statistics.mean([r['ssim'] for r in pp if r['quality']==q]) for q in [70,85,95]]
ax2.plot(pp_x, pp_sy, 'o-', label='PAIR (Pillow)', color='blue', linewidth=2)

pg_sy = [statistics.mean([r['ssim'] for r in pg if r['quality']==q]) for q in [70,85,95]]
ax2.plot(pg_x, pg_sy, 'D-', label='PAIR (glymur tile-ROI)', color='green', linewidth=2)

if os.path.exists('experiments/extended_baselines.json'):
    for codec, marker, color, label in [('jpeg','^-','red','JPEG'),('webp','v-','purple','WebP')]:
        pts = eb[codec]
        qs = sorted(set(r['quality'] for r in pts))
        sx = [statistics.mean([r['bpp'] for r in pts if r['quality']==q]) for q in qs]
        sy = [statistics.mean([r['ssim'] for r in pts if r['quality']==q]) for q in qs]
        ax2.plot(sx, sy, marker, label=label, color=color, linewidth=2)
else:
    for codec, marker, color, label in [('jpeg','^-','red','JPEG'),('webp','v-','purple','WebP')]:
        sx = [statistics.mean([r[codec]['bpp'] for r in kb if r['quality']==q]) for q in jpeg_qs]
        sy = [statistics.mean([r[codec]['ssim'] for r in kb if r['quality']==q]) for q in jpeg_qs]
        ax2.plot(sx, sy, marker, label=label, color=color, linewidth=2)

ax2.set_xlabel('Bits Per Pixel (BPP)', fontsize=12)
ax2.set_ylabel('SSIM', fontsize=12)
ax2.set_title('Rate-Distortion (SSIM)', fontsize=14, fontweight='bold')
ax2.legend(fontsize=8)
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('paper/figures_new/master_rd.pdf', dpi=300, bbox_inches='tight')
plt.savefig('paper/figures_new/master_rd.png', dpi=300, bbox_inches='tight')
print('Saved master RD figure')
