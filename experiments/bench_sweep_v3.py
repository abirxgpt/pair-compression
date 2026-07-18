"""
Sweep v3 — the corrected, bitrate-fair experiment suite.

Fixes the v2 flaws:
  F1: matched-BPP comparison via per-variant RD curves (4 base ratios each)
  F2: region-wise PSNR (inside top-15% importance mask vs bottom-40%)
      -> tests the literature's ACTUAL claim (foreground quality)
  F4: multi-bitrate robustness (base ratios 8/16/30/50)
  F6: LPIPS perceptual metric on every decode

Variants:
  - default / edge_only / texture_only / saliency_only / equal: content-driven
  - uniform: constant map 0.2 -> middle threshold branch -> EVERY tile at
    cratio=base (fixes the v2 bug where uniform=0.5 hit the high branch)
  - vanilla: single-pass glymur encode, no tiling (the true anchor)

Usage:  py experiments/bench_sweep_v3.py [--smoke]
"""
import sys, json, os, time
sys.path.insert(0, '.')
import numpy as np
from PIL import Image
import glymur
import torch
import lpips as lpips_lib

from pawc.importance_map import ImportanceMapGenerator
from pawc.jpeg2000_backend import GlymurROIEncoder
from pawc.metrics import calculate_psnr, calculate_ssim

SMOKE = '--smoke' in sys.argv

VARIANTS = {
    'default':       (0.4, 0.3, 0.3),
    'edge_only':     (1.0, 0.0, 0.0),
    'texture_only':  (0.0, 1.0, 0.0),
    'saliency_only': (0.0, 0.0, 1.0),
    'equal':         (0.333, 0.333, 0.334),
    'uniform':       None,   # constant 0.2 -> all tiles at cratio=base
}
BASE_RATIOS = [8, 16, 30, 50]
IMAGES = range(1, 3) if SMOKE else range(1, 25)
if SMOKE:
    VARIANTS = {k: VARIANTS[k] for k in ['default', 'uniform']}
    BASE_RATIOS = [16]

OUT_DIR = 'experiments/sweep_v3'
os.makedirs(OUT_DIR, exist_ok=True)
RESULTS_PATH = os.path.join(OUT_DIR, 'results.json')

encoder = GlymurROIEncoder(tile_size=64)
lpips_fn = lpips_lib.LPIPS(net='alex')

def to_lpips_tensor(arr):
    return torch.from_numpy(arr.copy()).permute(2, 0, 1).unsqueeze(0).float() / 127.5 - 1.0

def masked_psnr(orig, dec, mask):
    o = orig.astype(np.float64)[mask]
    d = dec.astype(np.float64)[mask]
    mse = np.mean((o - d) ** 2)
    if mse == 0:
        return float('inf')
    return 10 * np.log10(255.0 ** 2 / mse)

results = []
t_start = time.time()
total_units = IMAGES.stop - IMAGES.start
done_imgs = 0

for img_num in IMAGES:
    img_path = f'kodak_dataset/kodim{img_num:02d}.png'
    img = np.array(Image.open(img_path).convert('RGB'))
    h, w = img.shape[:2]

    # Generate importance maps once per variant (cached across ratios)
    maps = {}
    for vname, weights in VARIANTS.items():
        if vname == 'uniform':
            maps[vname] = np.full((h, w), 0.2, dtype=np.float32)
        else:
            gen = ImportanceMapGenerator(*weights)
            maps[vname] = gen.generate(img)

    # Region masks come from the DEFAULT map (same mask for every variant,
    # so region comparisons are apples-to-apples)
    dmap = maps.get('default')
    if dmap is None:  # smoke mode fallback
        dmap = ImportanceMapGenerator(0.4, 0.3, 0.3).generate(img)
    hi_thresh = np.percentile(dmap, 85)
    lo_thresh = np.percentile(dmap, 40)
    mask_high = dmap > hi_thresh          # top 15% most important pixels
    mask_low = dmap <= lo_thresh          # bottom 40%
    orig_lpips_t = to_lpips_tensor(img)

    for base in BASE_RATIOS:
        # --- tiled variants ---
        for vname in VARIANTS:
            out = os.path.join(OUT_DIR, f'_tmp_{vname}.jp2')
            meta = encoder.encode(img, maps[vname], base_quality=70,
                                  output_path=out, base_ratio=base)
            filesize = os.path.getsize(out)
            bpp = filesize * 8 / (h * w)
            dec = encoder.decode(out)
            os.remove(out)

            row = {
                'image': f'kodim{img_num:02d}', 'variant': vname, 'base_ratio': base,
                'psnr': round(calculate_psnr(img, dec), 4),
                'ssim': round(calculate_ssim(img, dec), 4),
                'psnr_high': round(masked_psnr(img, dec, mask_high), 4),
                'psnr_low': round(masked_psnr(img, dec, mask_low), 4),
                'lpips': round(lpips_fn(orig_lpips_t, to_lpips_tensor(dec)).item(), 5),
                'bpp': round(bpp, 4), 'filesize': filesize,
            }
            results.append(row)
            print(f"kodim{img_num:02d} {vname:<13} base={base:>2}: "
                  f"PSNR={row['psnr']:.2f} hi={row['psnr_high']:.2f} "
                  f"lo={row['psnr_low']:.2f} LPIPS={row['lpips']:.4f} BPP={row['bpp']:.3f}",
                  flush=True)

        # --- vanilla single-pass anchor at the same cratio ---
        out = os.path.join(OUT_DIR, '_tmp_vanilla.jp2')
        glymur.Jp2k(out, data=img, cratios=[base])
        filesize = os.path.getsize(out)
        bpp = filesize * 8 / (h * w)
        dec = glymur.Jp2k(out)[:]
        os.remove(out)
        row = {
            'image': f'kodim{img_num:02d}', 'variant': 'vanilla', 'base_ratio': base,
            'psnr': round(calculate_psnr(img, dec), 4),
            'ssim': round(calculate_ssim(img, dec), 4),
            'psnr_high': round(masked_psnr(img, dec, mask_high), 4),
            'psnr_low': round(masked_psnr(img, dec, mask_low), 4),
            'lpips': round(lpips_fn(orig_lpips_t, to_lpips_tensor(dec)).item(), 5),
            'bpp': round(bpp, 4), 'filesize': filesize,
        }
        results.append(row)
        print(f"kodim{img_num:02d} {'vanilla':<13} cr  ={base:>2}: "
              f"PSNR={row['psnr']:.2f} hi={row['psnr_high']:.2f} "
              f"lo={row['psnr_low']:.2f} LPIPS={row['lpips']:.4f} BPP={row['bpp']:.3f}",
              flush=True)

    # incremental save after every image
    with open(RESULTS_PATH, 'w') as f:
        json.dump(results, f, indent=1)
    done_imgs += 1
    elapsed = time.time() - t_start
    eta = elapsed / done_imgs * (total_units - done_imgs)
    print(f'--- image {done_imgs}/{total_units} done, elapsed {elapsed/60:.1f}m, ETA {eta/60:.1f}m ---',
          flush=True)

print(f'\nDONE. {len(results)} rows -> {RESULTS_PATH}')
