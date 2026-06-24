"""7-way ablation: test every importance map variant on Kodak Q70."""
import sys, json, os, statistics
sys.path.insert(0, '.')
import numpy as np
from PIL import Image
from pawc.importance_map import ImportanceMapGenerator
from pawc.jpeg2000_backend import GlymurROIEncoder
from pawc.metrics import calculate_psnr, calculate_ssim, calculate_ms_ssim

VARIANTS = {
    'edge_only':     (1.0, 0.0, 0.0),
    'texture_only':  (0.0, 1.0, 0.0),
    'saliency_only': (0.0, 0.0, 1.0),
    'equal':         (0.333, 0.333, 0.334),
    'default':       (0.4, 0.3, 0.3),
    'random':        'random',
    'uniform':       'uniform',
    'inverted':      'inverted',
}

os.makedirs('experiments/ablation', exist_ok=True)
encoder = GlymurROIEncoder(tile_size=64)
all_results = {}

for variant_name, weights in VARIANTS.items():
    print(f'\n{"="*60}')
    print(f'ABLATION: {variant_name}')
    print(f'{"="*60}')

    if variant_name == 'random':
        gen = None
    elif variant_name == 'uniform':
        gen = None
    elif variant_name == 'inverted':
        gen = ImportanceMapGenerator(0.4, 0.3, 0.3)
    else:
        gen = ImportanceMapGenerator(*weights)

    results = []
    for img_num in range(1, 25):
        img_path = f'kodak_dataset/kodim{img_num:02d}.png'
        img = np.array(Image.open(img_path).convert('RGB'))

        if variant_name == 'random':
            imp = np.random.rand(img.shape[0], img.shape[1]).astype(np.float32)
        elif variant_name == 'uniform':
            imp = np.ones((img.shape[0], img.shape[1]), dtype=np.float32) * 0.5
        elif variant_name == 'inverted':
            imp = 1.0 - gen.generate(img)
        else:
            imp = gen.generate(img)

        out = f'experiments/ablation/{variant_name}_kodim{img_num:02d}.jp2'
        meta = encoder.encode(img, imp, base_quality=70, output_path=out)
        filesize = os.path.getsize(out)
        bpp = (filesize * 8) / (img.shape[0] * img.shape[1])

        decoded = encoder.decode(out)
        psnr = calculate_psnr(img, decoded)
        ssim = calculate_ssim(img, decoded)
        ms_ssim = calculate_ms_ssim(img, decoded)

        results.append({
            'image': f'kodim{img_num:02d}',
            'psnr': round(psnr, 4), 'ssim': round(ssim, 4),
            'ms_ssim': round(ms_ssim, 4), 'bpp': round(bpp, 4),
            'filesize': filesize
        })
        print(f'  kodim{img_num:02d}: {filesize:,}B, PSNR={psnr:.2f}, SSIM={ssim:.4f}')

    all_results[variant_name] = results

    psnr_mean = statistics.mean([r['psnr'] for r in results])
    psnr_std = statistics.stdev([r['psnr'] for r in results])
    bpp_mean = statistics.mean([r['bpp'] for r in results])
    print(f'  MEAN: PSNR={psnr_mean:.2f}+/-{psnr_std:.2f}, BPP={bpp_mean:.3f}')

with open('experiments/ablation/all_results.json', 'w') as f:
    json.dump(all_results, f, indent=2)

print('\n\n' + '='*70)
print('ABLATION SUMMARY - Kodak Q70 (mean +/- std, n=24)')
print('='*70)
print(f'{"Variant":<20} {"PSNR":>12} {"SSIM":>10} {"BPP":>10}')
print('-'*52)
for name in VARIANTS:
    r = all_results[name]
    p = statistics.mean([x['psnr'] for x in r])
    ps = statistics.stdev([x['psnr'] for x in r])
    s = statistics.mean([x['ssim'] for x in r])
    b = statistics.mean([x['bpp'] for x in r])
    print(f'{name:<20} {p:>6.2f}+/-{ps:.2f} {s:>6.3f} {b:>6.3f}')
