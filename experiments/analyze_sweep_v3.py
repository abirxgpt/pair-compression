"""
Analyze sweep v3: bitrate-fair comparisons via per-image vanilla anchoring.

For every (image, variant, ratio) row, interpolate THAT image's own vanilla
RD curve at the row's BPP, and report the gap. Paired t-tests on per-image
gaps. Outputs global-PSNR, region-PSNR (high/low), and LPIPS analyses,
plus the RD figure for the paper.
"""
import json, statistics, os
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

rows = json.load(open('experiments/sweep_v3/results.json'))
variants = sorted(set(r['variant'] for r in rows) - {'vanilla'})
ratios = sorted(set(r['base_ratio'] for r in rows))
images = sorted(set(r['image'] for r in rows))

# Per-image vanilla anchor curves (BPP -> metric) for interpolation
def build_anchor(img, metric):
    pts = sorted([(r['bpp'], r[metric]) for r in rows
                  if r['image'] == img and r['variant'] == 'vanilla'
                  and np.isfinite(r[metric])])
    return [p[0] for p in pts], [p[1] for p in pts]

def anchor_at(img, metric, bpp):
    xs, ys = build_anchor(img, metric)
    return float(np.interp(bpp, xs, ys))

def gaps_for(variant, ratio, metric):
    """Per-image gap: variant metric minus vanilla metric at the SAME BPP."""
    out = []
    for img in images:
        r = next((x for x in rows if x['image'] == img and
                  x['variant'] == variant and x['base_ratio'] == ratio), None)
        if r is None or not np.isfinite(r[metric]):
            continue
        out.append(r[metric] - anchor_at(img, metric, r['bpp']))
    return np.array(out)

def report(metric, better='higher'):
    print(f'\n{"="*78}')
    print(f'{metric.upper()} — gap vs per-image vanilla anchor at matched BPP '
          f'({"higher" if better=="higher" else "lower"} is better)')
    print(f'{"="*78}')
    print(f'{"variant":<15}' + ''.join(f'{"r"+str(rt):>15}' for rt in ratios))
    table = {}
    for v in variants:
        cells = []
        for rt in ratios:
            g = gaps_for(v, rt, metric)
            t, p = stats.ttest_1samp(g, 0.0)
            sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'ns'
            cells.append(f'{np.mean(g):+.2f}{sig:<3}')
            table.setdefault(v, {})[rt] = {
                'mean_gap': float(np.mean(g)), 'std': float(np.std(g, ddof=1)),
                't': float(t), 'p': float(p),
                'd': float(np.mean(g) / np.std(g, ddof=1))}
        print(f'{v:<15}' + ''.join(f'{c:>15}' for c in cells))
    return table

summary = {
    'global_psnr': report('psnr'),
    'psnr_high_region': report('psnr_high'),
    'psnr_low_region': report('psnr_low'),
    'lpips': report('lpips', better='lower'),
    'ssim': report('ssim'),
}

# THE headline question: does importance help WHERE IT CLAIMS TO?
print(f'\n{"="*78}')
print('HEADLINE: default vs uniform, matched-anchor gaps in HIGH-importance regions')
print(f'{"="*78}')
for rt in ratios:
    gd = gaps_for('default', rt, 'psnr_high')
    gu = gaps_for('uniform', rt, 'psnr_high')
    t, p = stats.ttest_rel(gd, gu)
    print(f'ratio {rt:>2}: default {np.mean(gd):+.2f} vs uniform {np.mean(gu):+.2f} '
          f'-> delta {np.mean(gd-gu):+.2f} dB (p={p:.4f})')

# Mean BPP per variant/ratio (to show fairness)
print(f'\nBPP by variant/ratio:')
print(f'{"variant":<15}' + ''.join(f'{"r"+str(rt):>10}' for rt in ratios))
for v in variants + ['vanilla']:
    cells = []
    for rt in ratios:
        b = [r['bpp'] for r in rows if r['variant'] == v and r['base_ratio'] == rt]
        cells.append(f'{statistics.mean(b):.3f}' if b else '--')
    print(f'{v:<15}' + ''.join(f'{c:>10}' for c in cells))

with open('experiments/sweep_v3/analysis.json', 'w') as f:
    json.dump(summary, f, indent=1)

# ---- RD figure: global PSNR (left) and high-region PSNR (right) ----
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
styles = {'vanilla': ('k-s', 'JPEG 2000 (single-pass)'),
          'uniform': ('0.5', 'Uniform tiles'),
          'default': ('b-o', 'Default (0.4,0.3,0.3)'),
          'edge_only': ('-^', 'Edge-only'),
          'texture_only': ('-v', 'Texture-only'),
          'saliency_only': ('-<', 'Saliency-only'),
          'equal': ('->', 'Equal weights')}
for metric, ax, ylabel in [('psnr', ax1, 'PSNR (dB)'),
                           ('psnr_high', ax2, 'PSNR in top-15% importance region (dB)')]:
    for v in ['vanilla', 'uniform', 'default', 'edge_only', 'texture_only',
              'saliency_only', 'equal']:
        xs_, ys_ = [], []
        for rt in ratios:
            sel = [r for r in rows if r['variant'] == v and r['base_ratio'] == rt
                   and np.isfinite(r[metric])]
            if sel:
                xs_.append(statistics.mean([r['bpp'] for r in sel]))
                ys_.append(statistics.mean([r[metric] for r in sel]))
        style, label = styles[v]
        if v == 'uniform':
            ax.plot(xs_, ys_, 'D--', color='0.4', label=label, linewidth=2)
        else:
            ax.plot(xs_, ys_, style, label=label, linewidth=2)
    ax.set_xlabel('Bits Per Pixel (BPP)', fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
ax1.set_title('Global fidelity', fontsize=13, fontweight='bold')
ax2.set_title('Fidelity where importance maps claim to help', fontsize=13, fontweight='bold')
plt.tight_layout()
os.makedirs('paper/figures_new', exist_ok=True)
plt.savefig('paper/figures_new/sweep_rd.pdf', dpi=300, bbox_inches='tight')
plt.savefig('paper/figures_new/sweep_rd.png', dpi=300, bbox_inches='tight')
print('\nSaved paper/figures_new/sweep_rd.pdf and analysis.json')
