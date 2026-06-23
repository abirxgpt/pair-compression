# Reproducing PAIR Results

This guide reproduces every number in the PAIR paper (Table I and Table II).

## Prerequisites

- Python 3.12+
- ~2 GB free disk space (Kodak dataset + outputs)
- Windows, macOS, or Linux

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

Verify:

```bash
python -c "import glymur; print(glymur.version.version)"
# Should print: 0.14.6

python -c "from pawc.pair_codec import PAIRCodec; print('OK')"
# Should print: OK
```

**glymur OpenJPEG setup (REQUIRED for tile-ROI):** glymur needs the OpenJPEG C
library. Create `~/.config/glymur/glymurrc` (Linux/macOS) or
`%USERPROFILE%\glymur\glymurrc` (Windows) containing:

```ini
[library]
openjp2 = /path/to/openjp2.dll
```

On Windows with Anaconda: `C:\Users\...\anaconda3\Library\bin\openjp2.dll`

## Step 2: Download Kodak Dataset

```bash
python -c "
import urllib.request, os
os.makedirs('kodak_dataset', exist_ok=True)
base = 'http://r0k.us/graphics/kodak/kodak/'
for i in range(1, 25):
    name = f'kodim{i:02d}.png'
    url = base + name
    path = f'kodak_dataset/{name}'
    if not os.path.exists(path):
        urllib.request.urlretrieve(url, path)
        print(f'Downloaded {name}')
print('Done')
"
```

Verify: `ls kodak_dataset/` should show 24 files (kodim01.png through kodim24.png).

## Step 3: Run PAIR (Pillow) Benchmark

```bash
python kodak_benchmark_pair.py
```

This produces `pair_results/benchmark_results.json` with 72 entries (24 images ×
3 quality levels). Expected runtime: ~10 minutes.

Verify:

```bash
python -c "
import json, statistics
data = json.load(open('pair_results/benchmark_results.json'))
q70 = [r for r in data if r['quality'] == 70]
psnr = statistics.mean([r['psnr'] for r in q70])
bpp = statistics.mean([r['bpp'] for r in q70])
print(f'PAIR Q70: PSNR={psnr:.2f}, BPP={bpp:.3f}')
# Expected: PSNR=33.22, BPP=0.857
"
```

## Step 4: Run Baseline (JPEG, WebP) Benchmark

```bash
python kodak_benchmark.py
```

Produces `kodak_results/benchmark_results.json`. Expected runtime: ~5 minutes.

## Step 5: Run PAIR (glymur tile-ROI) Benchmark

```bash
python -c "
import sys, json, os, time, statistics
sys.path.insert(0, '.')
from pawc.pair_codec import PAIRCodec
from pawc.metrics import calculate_psnr, calculate_ssim
import numpy as np
from PIL import Image

codec = PAIRCodec(use_glymur=True)
os.makedirs('pair_results_glymur', exist_ok=True)
results = []

for i in range(1, 25):
    img_path = f'kodak_dataset/kodim{i:02d}.png'
    img = np.array(Image.open(img_path).convert('RGB'))
    for q in [70, 85, 95]:
        out = f'pair_results_glymur/kodim{i:02d}_q{q}.jp2'
        compressed, meta = codec.compress(img, quality=q, output_path=out)
        sz = os.path.getsize(out)
        bpp = (sz * 8) / (img.shape[0] * img.shape[1])
        dec = codec.decompress(compressed, input_path=out)
        results.append({
            'image': f'kodim{i:02d}', 'quality': q,
            'psnr': round(calculate_psnr(img, dec), 4),
            'ssim': round(calculate_ssim(img, dec), 4),
            'bpp': round(bpp, 4), 'filesize': sz
        })

with open('pair_results_glymur/benchmark_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print('Done')
"
```

Expected runtime: ~60 minutes (72 encodings × ~50 seconds each).

## Step 6: Generate Charts

```bash
python generate_charts.py
```

Produces `kodak_results/charts/rd_curve_psnr.pdf`, `rd_curve_ssim.pdf`,
and comparison bar charts.

## Step 7: Compute Final Numbers

```bash
python analyze_pair_results.py
```

This prints mean ± std values matching Table I and Table II in the paper.

## Expected Paper Tables

### Table I: Q70 Results

| Codec | PSNR | SSIM | BPP |
|-------|------|------|-----|
| PAIR (Pillow) | 33.22 ± 2.42 | 0.815 ± 0.090 | 0.857 ± 0.001 |
| PAIR (glymur) | 31.30 ± 0.84 | 0.812 ± 0.061 | 1.266 ± 0.449 |
| JPEG | 34.88 ± 1.61 | 0.923 ± 0.013 | 1.213 ± 0.376 |
| WebP | 35.09 ± 1.13 | 0.924 ± 0.016 | 0.877 ± 0.415 |

### Table II: Multi-Quality

| Codec | Q | PSNR | SSIM | BPP |
|-------|---|------|------|-----|
| PAIR | 70 | 33.22 ± 2.42 | 0.815 ± 0.090 | 0.857 ± 0.001 |
| PAIR | 85 | 35.02 ± 3.20 | 0.882 ± 0.065 | 1.599 ± 0.001 |
| PAIR | 95 | 36.87 ± 3.77 | 0.921 ± 0.045 | 2.398 ± 0.002 |
| JPEG | 70 | 34.88 ± 1.61 | 0.923 ± 0.013 | 1.213 ± 0.376 |
| JPEG | 85 | 36.82 ± 1.53 | 0.950 ± 0.009 | 1.836 ± 0.523 |
| JPEG | 95 | 40.79 ± 1.08 | 0.976 ± 0.006 | 3.306 ± 0.743 |

## Troubleshooting

- **glymur ImportError**: Ensure OpenJPEG ≥ 2.4.0 is installed and glymurrc
  points to the correct DLL/shared library.
- **Kodak download fails**: The r0k.us mirror may be slow. Try the alternate
  URL `https://r0k.us/graphics/kodak/kodak/`.
- **Pillow JPEG 2000 unavailable**: Ensure Pillow is built with JPEG 2000
  support (`python -c "from PIL import features; print(features.check('jpeg2000'))"`).
