"""Generate ablation RD figure once Phase 2 completes."""
import json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np, statistics, os

if not os.path.exists('experiments/ablation/all_results.json'):
    print('Waiting for Phase 2 to finish...')
    exit(1)

data = json.load(open('experiments/ablation/all_results.json'))
fig, ax = plt.subplots(figsize=(8, 5))

colors = {
    'default': '#2196F3', 'edge_only': '#FF9800', 'texture_only': '#4CAF50',
    'saliency_only': '#9C27B0', 'equal': '#607D8B', 'uniform': '#000000',
    'random': '#f44336', 'inverted': '#795548'
}

for name, results in data.items():
    bpp = np.mean([r['bpp'] for r in results])
    psnr = np.mean([r['psnr'] for r in results])
    bpp_std = np.std([r['bpp'] for r in results])
    psnr_std = np.std([r['psnr'] for r in results])
    ax.errorbar(bpp, psnr, xerr=bpp_std, yerr=psnr_std,
                fmt='o', color=colors.get(name, 'gray'), label=name,
                markersize=10, capsize=5, markeredgewidth=1.5)

ax.set_xlabel('Bits Per Pixel (BPP)', fontsize=12)
ax.set_ylabel('PSNR (dB)', fontsize=12)
ax.set_title('Ablation: Importance Map Variants on Kodak (Q70, n=24)', fontsize=14)
ax.legend(fontsize=9, ncol=2)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('paper/figures_new/ablation_rd.pdf', dpi=300, bbox_inches='tight')
plt.savefig('paper/figures_new/ablation_rd.png', dpi=300, bbox_inches='tight')
print('Saved ablation figure')
