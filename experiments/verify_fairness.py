"""Verify whether the ablation comparison is bitrate-fair, and decompose
the loss into (tiling penalty) + (importance misallocation penalty) by
comparing every variant against the vanilla J2K RD curve at its own BPP."""
import json, statistics
import numpy as np

abl = json.load(open('experiments/ablation/all_results.json'))
vj2k = json.load(open('experiments/vanilla_j2k/results.json'))

# Build vanilla J2K anchor curve (mean BPP, mean PSNR per cratio), skip cr=2 (inf PSNR)
crats = [c for c in sorted(set(r['cratio'] for r in vj2k)) if c > 2]
curve = []
for c in crats:
    pts = [r for r in vj2k if r['cratio'] == c]
    curve.append((statistics.mean([r['bpp'] for r in pts]),
                  statistics.mean([r['psnr'] for r in pts])))
curve.sort()
xs = [p[0] for p in curve]
ys = [p[1] for p in curve]

def vanilla_psnr_at(bpp):
    return float(np.interp(bpp, xs, ys))

print('Vanilla J2K anchor curve:')
for x, y in curve:
    print(f'  BPP={x:.3f}  PSNR={y:.2f}')

print('\n=== ABLATION VARIANTS vs VANILLA ANCHOR AT MATCHED BPP ===')
print(f'{"Variant":<15} {"PSNR":>7} {"BPP":>7} {"Vanilla@BPP":>12} {"Gap":>7}')
uniform_bpp = statistics.mean([r['bpp'] for r in abl['uniform']])
for name in ['default','edge_only','texture_only','saliency_only','equal',
             'inverted','random','uniform']:
    r = abl[name]
    p = statistics.mean([x['psnr'] for x in r])
    b = statistics.mean([x['bpp'] for x in r])
    v = vanilla_psnr_at(b)
    print(f'{name:<15} {p:>7.2f} {b:>7.3f} {v:>12.2f} {p-v:>+7.2f}')

print('\n=== KEY QUESTION: is the ablation bitrate-fair? ===')
d_bpp = statistics.mean([r['bpp'] for r in abl['default']])
u_bpp = uniform_bpp
print(f'default BPP = {d_bpp:.3f}')
print(f'uniform BPP = {u_bpp:.3f}')
print(f'Ratio: uniform uses {u_bpp/d_bpp:.2f}x the bits of default!')
print('The -5.47 dB "delta vs uniform" compares variants at DIFFERENT bitrates.')

print('\n=== DECOMPOSITION (at matched BPP vs vanilla anchor) ===')
u_psnr = statistics.mean([x['psnr'] for x in abl['uniform']])
d_psnr = statistics.mean([x['psnr'] for x in abl['default']])
tiling_penalty = u_psnr - vanilla_psnr_at(u_bpp)
default_total = d_psnr - vanilla_psnr_at(d_bpp)
print(f'Tiling penalty alone (uniform tiles vs vanilla @ {u_bpp:.2f} BPP): {tiling_penalty:+.2f} dB')
print(f'Default total gap (vs vanilla @ {d_bpp:.2f} BPP):                 {default_total:+.2f} dB')
print(f'Marginal cost attributable to importance-driven allocation:      {default_total - tiling_penalty:+.2f} dB')

# Why did uniform end up at cratio 10?
print('\n=== WHY uniform BPP is so high ===')
print('Encoder thresholds: imp>0.30 -> cr=base/2=10 | imp>0.15 -> cr=20 | else cr=60')
print('Uniform map = 0.5 everywhere -> EVERY tile lands in the >0.30 branch -> cr=10')
print('So "uniform" actually encodes at cratio 10, not the intended base 20.')
print('Same for random (tile means ~0.5) and inverted (means ~0.6-0.9): all cr=10.')
print('That is why uniform/random/inverted are byte-identical in BPP and PSNR.')
