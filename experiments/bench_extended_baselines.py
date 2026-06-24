"""Extended JPEG and WebP benchmarks for smooth RD curves."""
import sys, json, os, statistics
sys.path.insert(0, '.')
import numpy as np
from PIL import Image
import io
from pawc.metrics import calculate_psnr, calculate_ssim

QUALITIES = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
results = {'jpeg': [], 'webp': []}

for img_num in range(1, 25):
    img_path = f'kodak_dataset/kodim{img_num:02d}.png'
    img = np.array(Image.open(img_path).convert('RGB'))

    for q in QUALITIES:
        # JPEG
        buf = io.BytesIO()
        Image.fromarray(img).save(buf, 'JPEG', quality=q)
        jpeg_bytes = buf.getvalue()
        jpeg_bpp = (len(jpeg_bytes) * 8) / (img.shape[0] * img.shape[1])
        jpeg_decoded = np.array(Image.open(io.BytesIO(jpeg_bytes)))
        jpeg_psnr = calculate_psnr(img, jpeg_decoded)
        jpeg_ssim = calculate_ssim(img, jpeg_decoded)
        results['jpeg'].append({
            'image': f'kodim{img_num:02d}', 'quality': q,
            'psnr': jpeg_psnr, 'ssim': jpeg_ssim, 'bpp': jpeg_bpp
        })

        # WebP
        buf = io.BytesIO()
        Image.fromarray(img).save(buf, 'WEBP', quality=q)
        webp_bytes = buf.getvalue()
        webp_bpp = (len(webp_bytes) * 8) / (img.shape[0] * img.shape[1])
        webp_decoded = np.array(Image.open(io.BytesIO(webp_bytes)))
        webp_psnr = calculate_psnr(img, webp_decoded)
        webp_ssim = calculate_ssim(img, webp_decoded)
        results['webp'].append({
            'image': f'kodim{img_num:02d}', 'quality': q,
            'psnr': webp_psnr, 'ssim': webp_ssim, 'bpp': webp_bpp
        })

        print(f'kodim{img_num:02d} Q{q:>3}: JPEG={jpeg_psnr:.1f}dB/{jpeg_bpp:.3f}bpp  WebP={webp_psnr:.1f}dB/{webp_bpp:.3f}bpp')

with open('experiments/extended_baselines.json', 'w') as f:
    json.dump(results, f, indent=2)

for codec in ['jpeg', 'webp']:
    print(f'\n{codec.upper()} RD POINTS:')
    for q in QUALITIES:
        pts = [r for r in results[codec] if r['quality'] == q]
        psnr = statistics.mean([r['psnr'] for r in pts])
        bpp = statistics.mean([r['bpp'] for r in pts])
        print(f'  Q{q:>3}: PSNR={psnr:.2f}, BPP={bpp:.3f}')
