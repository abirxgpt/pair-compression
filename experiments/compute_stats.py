"""Compute statistical tests for the paper."""
import json, numpy as np
from scipy import stats

print('='*60)
print('HEADLINE: Vanilla J2K vs PAIR at matched BPP')
print('='*60)

# Load vanilla J2K at cr=30 (closest BPP to PAIR Q70's 0.857)
vj2k = json.load(open('experiments/vanilla_j2k/results.json'))
pair = json.load(open('pair_results/benchmark_results.json'))

vj2k_30 = [r['psnr'] for r in vj2k if r['cratio'] == 30]
pair_70 = [r['psnr'] for r in pair if r['quality'] == 70]

vj2k_bpp = np.mean([r['bpp'] for r in vj2k if r['cratio'] == 30])
pair_bpp = np.mean([r['bpp'] for r in pair if r['quality'] == 70])

print(f'Vanilla J2K (cr=30): PSNR={np.mean(vj2k_30):.2f} +/- {np.std(vj2k_30):.2f}, BPP={vj2k_bpp:.3f}')
print(f'PAIR Pillow (Q70):   PSNR={np.mean(pair_70):.2f} +/- {np.std(pair_70):.2f}, BPP={pair_bpp:.3f}')

t_stat, p_value = stats.ttest_ind(vj2k_30, pair_70)
diff = np.mean(vj2k_30) - np.mean(pair_70)
pooled_std = np.sqrt((np.std(vj2k_30)**2 + np.std(pair_70)**2) / 2)
d = diff / pooled_std

print(f'\nt({len(vj2k_30)+len(pair_70)-2}) = {t_stat:.3f}, p = {p_value:.6f}, d = {d:.3f}')
print(f'Vanilla J2K beats PAIR by {diff:+.2f} dB at {vj2k_bpp/pair_bpp-1:+.1%} lower BPP')

# Also check if ablation results exist yet
import os
if os.path.exists('experiments/ablation/all_results.json'):
    print('\n' + '='*60)
    print('ABLATION: All variants vs uniform')
    print('='*60)
    data = json.load(open('experiments/ablation/all_results.json'))
    uniform_psnr = [r['psnr'] for r in data['uniform']]
    for name in data:
        if name == 'uniform':
            continue
        v_psnr = [r['psnr'] for r in data[name]]
        t, p = stats.ttest_rel(v_psnr, uniform_psnr)
        d_arr = np.array(v_psnr) - np.array(uniform_psnr)
        d_val = np.mean(d_arr) / np.std(d_arr, ddof=1)
        sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'ns'
        print(f'{name:<20}: delta_PSNR={np.mean(d_arr):+.3f}, d={d_val:+.3f}, p={p:.4f} {sig}')
else:
    print('\nAblation data not yet available. Will re-run after Phase 2 completes.')

print('\nDone.')
