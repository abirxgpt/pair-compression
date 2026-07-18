"""Qualitative figure: original vs vanilla vs uniform tiles vs default tiles.
Zoomed crop chosen to straddle tile boundaries so seams are visible."""
import sys, os
sys.path.insert(0, '.')
import numpy as np
from PIL import Image
import glymur
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pawc.importance_map import ImportanceMapGenerator
from pawc.jpeg2000_backend import GlymurROIEncoder
from pawc.metrics import calculate_psnr

IMG = 'kodak_dataset/kodim05.png'   # motorcycles: strong salient foreground
BASE = 30                            # ~0.8-0.9 BPP operating point
CROP = (slice(192, 384), slice(256, 512))  # 192x256 crop spanning tile borders

img = np.array(Image.open(IMG).convert('RGB'))
h, w = img.shape[:2]
enc = GlymurROIEncoder(tile_size=64)
gen = ImportanceMapGenerator(0.4, 0.3, 0.3)
imp = gen.generate(img)

panels = [('Original', img, None)]

# vanilla single-pass
glymur.Jp2k('_q_v.jp2', data=img, cratios=[BASE])
dv = glymur.Jp2k('_q_v.jp2')[:]
bppv = os.path.getsize('_q_v.jp2') * 8 / (h * w); os.remove('_q_v.jp2')
panels.append((f'JPEG 2000 single-pass\n{bppv:.2f} BPP, {calculate_psnr(img, dv):.1f} dB', dv, None))

# uniform tiles (constant 0.2 -> all tiles at cratio=BASE)
u = np.full((h, w), 0.2, dtype=np.float32)
enc.encode(img, u, 70, '_q_u.jp2', base_ratio=BASE)
du = enc.decode('_q_u.jp2')
bppu = os.path.getsize('_q_u.jp2') * 8 / (h * w); os.remove('_q_u.jp2')
panels.append((f'Uniform tiles\n{bppu:.2f} BPP, {calculate_psnr(img, du):.1f} dB', du, None))

# default importance tiles
enc.encode(img, imp, 70, '_q_d.jp2', base_ratio=BASE)
dd = enc.decode('_q_d.jp2')
bppd = os.path.getsize('_q_d.jp2') * 8 / (h * w); os.remove('_q_d.jp2')
panels.append((f'Importance tiles (default)\n{bppd:.2f} BPP, {calculate_psnr(img, dd):.1f} dB', dd, None))

fig, axes = plt.subplots(2, 4, figsize=(14, 7),
                         gridspec_kw={'height_ratios': [2, 1.6]})
for i, (title, arr, _) in enumerate(panels):
    axes[0, i].imshow(arr)
    axes[0, i].set_title(title, fontsize=9)
    axes[0, i].axis('off')
    # crop with tile grid hint
    axes[1, i].imshow(arr[CROP])
    axes[1, i].axis('off')
    axes[1, i].set_title('crop (192$\\times$256)', fontsize=8)

plt.suptitle('kodim05 at matched base ratio (cr=30): tile seams and background degradation '
             'introduced by importance-guided tiling', fontsize=11, fontweight='bold')
plt.tight_layout()
plt.savefig('paper/figures_new/qualitative.pdf', dpi=300, bbox_inches='tight')
plt.savefig('paper/figures_new/qualitative.png', dpi=200, bbox_inches='tight')
print(f'Saved qualitative figure. BPP: vanilla={bppv:.3f} uniform={bppu:.3f} default={bppd:.3f}')
