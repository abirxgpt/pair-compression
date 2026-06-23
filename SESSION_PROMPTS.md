# PAIR Project — Session Prompts
# Based on Session 0 Audit findings (2026-06-23)
# Use one session prompt per Claude Code session

---

# SESSION 1: FIX THE ROI IMPLEMENTATION
# This is the most critical session. The paper's central claim doesn't exist in code.
# Paste everything below as your first message.

---

Read CLAUDE.md fully before doing anything.

We are in Session 1. The audit found the single most critical bug:
pawc/pair_codec.py reduces the importance map to ONE scalar and applies it
globally. Pillow J2K has zero per-region effect. All PAIR Q70 files are
~42,100 bytes regardless of image content. This proves the ROI does nothing.

glymur 0.14.6 is installed and unused. We fix this now.

/plan

Before writing any code, plan the following:

PART A — Read existing code first (do not skip this):
1. Read pawc/pair_codec.py completely — understand the full encode/decode flow
2. Read pawc/jpeg2000_backend.py completely — understand what it currently does
3. Read pawc/importance_map.py — understand what compute_importance_map() returns
   (shape, value range, what edge/texture/saliency components look like)
4. Read pawc/config.py — understand CompressionConfig structure
5. Run this to confirm the bug:
   python -c "
   import os, glob
   files = sorted(glob.glob('pair_results/*_q70.jp2'))[:5]
   for f in files:
       print(f'{os.path.basename(f)}: {os.path.getsize(f):,} bytes')
   "
   All sizes should be ~42,100. Confirm and report.

PART B — Design the fix:
We implement TILE-BASED quality allocation using glymur. Here is the spec:

Class: GlymurROIEncoder in pawc/jpeg2000_backend.py (new class, do not delete old one)

Method: encode(image_array, importance_map, base_quality, output_path)
  - image_array: numpy array HxWx3, uint8
  - importance_map: numpy array HxW, float32, range [0,1]
  - base_quality: int 70/85/95
  - output_path: string, .jp2

Algorithm:
  Step 1: Divide image into 64x64 tiles (handle edge tiles with padding)
  Step 2: For each tile (i,j):
    - Extract tile from image_array
    - Extract tile from importance_map
    - Compute tile_importance = mean of importance_map tile
  Step 3: Convert base_quality to base compression ratio:
    quality_to_ratio = {70: 20, 85: 10, 95: 4}
    base_ratio = quality_to_ratio[base_quality]
  Step 4: Assign per-tile compression ratio:
    if tile_importance > 0.7:   cratio = max(2, base_ratio // 3)   # high quality
    elif tile_importance > 0.4: cratio = base_ratio                 # medium quality
    else:                       cratio = min(60, base_ratio * 2)    # low quality
  Step 5: Encode each tile with glymur:
    import glymur, io
    tile_jp2_bytes = encode_tile_to_bytes(tile_array, cratio)
  Step 6: Pack everything into a custom container:
    - Header: image shape, tile size, number of tiles
    - Tile map: list of (row, col, importance, cratio, byte_offset, byte_length)
    - Tile data: concatenated JP2 bytes
  Step 7: Save to output_path as .jp2 (use a wrapper JP2 or custom binary format)

Method: decode(input_path) → numpy array HxWx3
  - Read header and tile map
  - Decode each tile with glymur
  - Reconstruct full image from tiles

IMPORTANT: keep the old Pillow-based encoder intact as PillowROIEncoder.
We are ADDING glymur, not replacing the old code. This preserves reproducibility.

PART C — Update pair_codec.py:
  - Add import for GlymurROIEncoder
  - Add parameter use_glymur=True to PAIRCodec.__init__()
  - When use_glymur=True: use GlymurROIEncoder
  - When use_glymur=False: use old PillowROIEncoder (preserve existing behavior)

PART D — Validate the fix:
After implementing, run this validation:

  python -c "
  import sys
  sys.path.insert(0, '.')
  from pawc.pair_codec import PAIRCodec
  import numpy as np
  from PIL import Image
  import os

  codec = PAIRCodec(use_glymur=True)

  # Test on 3 different images
  test_images = [
      'kodak_dataset/kodim07.png',  # animal (high texture)
      'kodim15.png' if os.path.exists('kodim15.png') else 'kodak_dataset/kodim15.png',  # indoor
      'kodak_dataset/kodim01.png',  # outdoor
  ]

  for img_path in test_images:
      if not os.path.exists(img_path):
          continue
      img = np.array(Image.open(img_path).convert('RGB'))
      out_path = f'test_glymur_{os.path.basename(img_path)}.jp2'
      codec.encode(img, out_path, quality=70)
      size = os.path.getsize(out_path)
      decoded = codec.decode(out_path)
      print(f'{os.path.basename(img_path)}: {size:,} bytes, decoded shape: {decoded.shape}')
      os.remove(out_path)
  "

SUCCESS criteria:
  - Three files with DIFFERENT sizes (not all ~42,100)
  - Size difference between images should be at least 3,000 bytes
  - Decoded shape should be (512, 768, 3) or (768, 512, 3)
  - No exceptions thrown

If sizes still all match → the tile importance assignment is not working, debug Step 4.

PART E — Re-run PAIR benchmark with glymur encoder:
  ONLY after validation passes. Run on ALL 24 Kodak images:

  python -c "
  import sys, json, os, time
  sys.path.insert(0, '.')
  from pawc.pair_codec import PAIRCodec
  from pawc.metrics import calculate_psnr, calculate_ssim
  import numpy as np
  from PIL import Image
  from tqdm import tqdm

  codec = PAIRCodec(use_glymur=True)
  results = []

  for img_num in tqdm(range(1, 25), desc='Kodak PAIR glymur'):
      img_path = f'kodak_dataset/kodim{img_num:02d}.png'
      img = np.array(Image.open(img_path).convert('RGB'))

      for quality in [70, 85, 95]:
          out_path = f'pair_results_glymur/kodim{img_num:02d}_q{quality}.jp2'
          os.makedirs('pair_results_glymur', exist_ok=True)

          start = time.time()
          codec.encode(img, out_path, quality=quality)
          encode_time = time.time() - start

          filesize = os.path.getsize(out_path)
          bpp = (filesize * 8) / (img.shape[0] * img.shape[1])

          decoded = codec.decode(out_path)
          psnr = calculate_psnr(img, decoded)
          ssim = calculate_ssim(img, decoded)

          results.append({
              'image': f'kodim{img_num:02d}',
              'quality': quality,
              'psnr': round(psnr, 4),
              'ssim': round(ssim, 4),
              'bpp': round(bpp, 4),
              'filesize': filesize,
              'encode_time': round(encode_time, 3)
          })

  with open('pair_results_glymur/benchmark_results.json', 'w') as f:
      json.dump(results, f, indent=2)

  # Print summary
  import statistics
  for q in [70, 85, 95]:
      q_results = [r for r in results if r['quality'] == q]
      psnrs = [r['psnr'] for r in q_results]
      ssims = [r['ssim'] for r in q_results]
      bpps = [r['bpp'] for r in q_results]
      print(f'Q{q}: PSNR={statistics.mean(psnrs):.2f}±{statistics.stdev(psnrs):.2f}, '
            f'SSIM={statistics.mean(ssims):.3f}±{statistics.stdev(ssims):.3f}, '
            f'BPP={statistics.mean(bpps):.3f}±{statistics.stdev(bpps):.3f}')
  "

Save output. These are the NEW benchmark numbers for the paper.
Compare: did glymur PAIR improve over Pillow PAIR?
Paper will report BOTH (Pillow baseline + glymur improved version).

Session 1 is done when:
  ✅ GlymurROIEncoder implemented in jpeg2000_backend.py
  ✅ PAIRCodec accepts use_glymur=True parameter
  ✅ Validation shows varying file sizes across images
  ✅ Full 24-image benchmark run saved to pair_results_glymur/

---

# SESSION 2: FIX BROKEN CODE + TESTS
# Paste everything below as your first message for Session 2.

---

Read CLAUDE.md fully. We are in Session 2.

Session 1 is done. glymur encoder works and new benchmark exists.
Now we clean up broken code and make all 18 tests pass.

/plan

TASK 1 — Fix broken imports (15 minutes):
Read simple_pawc_v2.py and pawc_v2_codec.py.
Both import: from .adaptive_wavelet import AdaptiveWaveletTransform
But adaptive_wavelet.py does not exist.

Create pawc/adaptive_wavelet.py as a STUB that makes imports work:
  - Define class AdaptiveWaveletTransform
  - In __init__: store config
  - In forward(image): call existing WaveletTransform from wavelet_transform.py
  - In inverse(coeffs): call existing inverse from wavelet_transform.py
  - Add docstring: "Stub adapter — delegates to WaveletTransform"

This is the minimum to fix the import. Don't over-engineer it.

TASK 2 — Fix _decompress_block() in pawc_v2_codec.py:
Current line 383: return np.zeros((self.BLOCK_SIZE, self.BLOCK_SIZE), dtype=np.float32)
This is a placeholder. Read the surrounding code to understand what it should return.
Implement a basic inverse quantization + inverse wavelet for the block.
If the full implementation is too complex, at minimum make it NOT return all zeros
(return the mean value of the block coefficients instead).

TASK 3 — Fix the 2 failing tests:

Read tests/test_integration.py and tests/test_quantization.py to find:
- test_file_compression (fails because old PAWC expands files)
- test_importance_weighted_quantization (fails because importance has no effect)

For test_file_compression:
  Option A: Fix core.py pipeline to actually compress (hard, risky)
  Option B: Mark test as xfail with honest reason:
    @pytest.mark.xfail(reason="Classical PAWC pipeline known to expand files — "
                       "documented limitation. PAIR codec uses JPEG2000 backend instead.")
  Use Option B. It's honest and doesn't break things.

For test_importance_weighted_quantization:
  Read the test. If it tests that high-importance regions have MORE coefficients
  (less zeros), and that's legitimately not working: use xfail with reason.
  If it's a test design issue (wrong assertion): fix the assertion to match actual behavior.

TASK 4 — Add missing tests:

Create tests/test_pair_codec.py:
  - test_glymur_encoder_produces_valid_file()
      encode kodak_dataset/kodim01.png at Q70 with GlymurROIEncoder
      assert output file exists and size > 0
      assert file size varies (encode 2 different images, sizes differ)

  - test_glymur_encoder_roundtrip()
      encode then decode kodim01.png
      assert decoded.shape == original.shape
      assert PSNR(original, decoded) > 25  # basic sanity check

  - test_pillow_encoder_still_works()
      encode with use_glymur=False
      assert output file exists

Create tests/test_metrics.py:
  - test_psnr_identical_images()
      img = np.ones((100,100,3), dtype=np.uint8) * 128
      assert calculate_psnr(img, img) == float('inf') or > 100

  - test_psnr_range()
      noisy = img + np.random.randint(-10, 10, img.shape).astype(np.uint8)
      psnr = calculate_psnr(img, noisy)
      assert 20 < psnr < 50  # reasonable range for small noise

  - test_ssim_identical_images()
      assert calculate_ssim(img, img) > 0.99

Run after each task:
  python -m pytest tests/ -v 2>&1

Target: 18/18 pass (or 16/18 with 2 marked xfail — that's also acceptable)

Session 2 is done when:
  ✅ No ImportError anywhere in pawc/
  ✅ python -c "import pawc" runs clean
  ✅ pytest tests/ shows 0 failures (xfail is OK, failure is not)
  ✅ tests/test_pair_codec.py and tests/test_metrics.py both exist and pass

---

# SESSION 3: FINALIZE PAPER
# Paste everything below as your first message for Session 3.

---

Read CLAUDE.md fully. We are in Session 3.

Sessions 1 and 2 are done. Now we make the paper arXiv-ready.
Main file: paper/PAIR_paper.tex

/plan

TASK 1 — Load all benchmark data and compute final numbers:

Run this to get exact numbers for the paper:
  python -c "
  import json, statistics

  # Load original PAIR (Pillow)
  with open('pair_results/benchmark_results.json') as f:
      pair_data = json.load(f)

  # Load baselines
  with open('kodak_results/benchmark_results.json') as f:
      baseline_data = json.load(f)

  # Load new glymur PAIR
  import os
  glymur_data = None
  if os.path.exists('pair_results_glymur/benchmark_results.json'):
      with open('pair_results_glymur/benchmark_results.json') as f:
          glymur_data = json.load(f)

  def summarize(data, codec_filter=None, quality=70):
      if codec_filter:
          rows = [r for r in data if r.get('codec') == codec_filter and r['quality'] == quality]
      else:
          rows = [r for r in data if r['quality'] == quality]
      if not rows:
          return None
      psnrs = [r['psnr'] for r in rows]
      ssims = [r.get('ssim', 0) for r in rows]
      bpps = [r['bpp'] for r in rows]
      return {
          'psnr': f'{statistics.mean(psnrs):.2f} ± {statistics.stdev(psnrs):.2f}',
          'ssim': f'{statistics.mean(ssims):.3f} ± {statistics.stdev(ssims):.3f}',
          'bpp':  f'{statistics.mean(bpps):.3f} ± {statistics.stdev(bpps):.3f}',
          'n': len(rows)
      }

  for q in [70, 85, 95]:
      print(f'\n=== Q{q} ===')
      print('PAIR (Pillow):', summarize(pair_data, quality=q))
      if glymur_data:
          print('PAIR (glymur):', summarize(glymur_data, quality=q))
      for codec in ['jpeg', 'webp']:
          print(f'{codec.upper()}:', summarize(baseline_data, codec_filter=codec, quality=q))
  "

Copy the output — these are the EXACT numbers that go into all paper tables.
Save this output to results_summary.txt in the project root.

TASK 2 — Fix paper/PAIR_paper.tex — do these in order:

2a. Update author block:
  FROM: Department of Electronics and Communication, Engineering College Ajmer
  TO:   Independent Researcher, Ajmer, India
  FROM: 22cs04@ecajmer.ac.in
  TO:   abir.guptaaa@gmail.com

2b. Fix the "Figure ??" — add rd_curve figure properly:
  - Copy: kodak_results/charts/rd_curve_psnr.pdf → paper/figures/rd_curve.pdf
  - Copy: kodak_results/charts/rd_curve_ssim.pdf → paper/figures/rd_curve_ssim.pdf
  - In PAIR_paper.tex, find the section referencing \ref{fig:rd_curve}
  - Replace the placeholder text with actual figure inclusion:
    \begin{figure}[t]
    \centering
    \includegraphics[width=\columnwidth]{figures/rd_curve.pdf}
    \caption{Rate-distortion performance on Kodak dataset at quality levels 70, 85, 95.
    PAIR achieves competitive bitrates (0.857 BPP at Q70) while JPEG maintains
    superior PSNR, consistent with our analysis of wavelet-based implicit perceptual
    optimization.}
    \label{fig:rd_curve}
    \end{figure}

2c. Update Table I with exact numbers + std deviations:
  Use the values from TASK 1 output.
  Format: 33.22 ± 1.84 (replace all single values with mean ± std)
  Add footnote: "† Paired t-test (PAIR vs JPEG): compute and insert p-value"

2d. Fix abstract — the "4.43 dB" claim:
  Find what "4.43 dB" refers to in the paper. If it's across all quality levels,
  compute the actual average gap and use that.
  If it was just wrong, replace with: "PAIR remains 1.66 dB below JPEG at Q70,
  with the gap widening to X.XX dB at Q95"

2e. If glymur benchmark shows improvement over Pillow:
  Add a new row to Table I: "PAIR (glymur ROI)" with the new numbers
  Add text in Section III-E: "We subsequently implemented true tile-based ROI
  encoding using OpenJPEG via glymur, achieving [X] improvement in PSNR while
  maintaining [Y] BPP."

2f. Update "[repository to be added]":
  Replace with: https://github.com/abirxgpt/pair-compression

2g. Add importance map visualization figure:
  Generate this figure with Python first:
  
  python -c "
  import sys
  sys.path.insert(0, '.')
  import numpy as np
  import matplotlib.pyplot as plt
  import matplotlib.gridspec as gridspec
  from PIL import Image
  from pawc.importance_map import compute_importance_map

  fig = plt.figure(figsize=(10, 6))
  gs = gridspec.GridSpec(2, 5, figure=fig, wspace=0.05, hspace=0.1)

  test_images = [
      ('kodak_dataset/kodim07.png', 'Textured'),
      ('kodak_dataset/kodim15.png', 'Indoor'),
  ]

  labels = ['Original', 'Edge', 'Texture', 'Saliency', 'Fused']
  cmaps = [None, 'hot', 'viridis', 'plasma', 'RdYlGn']

  for row, (img_path, title) in enumerate(test_images):
      img = np.array(Image.open(img_path).convert('RGB'))
      gray = np.array(Image.open(img_path).convert('L'))
      
      imp_map, components = compute_importance_map(img, return_components=True)
      # if return_components not supported, call separately
      
      panels = [img, components.get('edge', gray), components.get('texture', gray),
                components.get('saliency', gray), imp_map]
      
      for col, (panel, label, cmap) in enumerate(zip(panels, labels, cmaps)):
          ax = fig.add_subplot(gs[row, col])
          if cmap:
              ax.imshow(panel, cmap=cmap, vmin=0, vmax=1)
          else:
              ax.imshow(panel)
          ax.axis('off')
          if row == 0:
              ax.set_title(label, fontsize=9, fontweight='bold')
          if col == 0:
              ax.set_ylabel(title, fontsize=9, rotation=90, labelpad=5)

  plt.savefig('paper/figures/importance_maps.pdf', bbox_inches='tight', dpi=300)
  plt.savefig('paper/figures/importance_maps.png', bbox_inches='tight', dpi=300)
  print('Saved importance_maps.pdf')
  "
  
  If compute_importance_map does not accept return_components=True, read
  pawc/importance_map.py and call the individual component functions directly.
  
  After generating, add figure to paper:
  \begin{figure}[t]
  \centering
  \includegraphics[width=\columnwidth]{figures/importance_maps.pdf}
  \caption{Multi-component importance maps for two Kodak images. From left:
  original, edge strength (Canny), texture complexity (FFT energy), visual
  saliency (spectral residual), and fused importance map.}
  \label{fig:importance_maps}
  \end{figure}
  Reference it in Section III-B with \ref{fig:importance_maps}.

TASK 3 — Compile and verify:
  cd paper
  pdflatex PAIR_paper.tex
  bibtex PAIR_paper
  pdflatex PAIR_paper.tex
  pdflatex PAIR_paper.tex

Check output for:
  - Any remaining "??" → fix before proceeding
  - Page count (should be 6-8 pages)
  - All figures rendered (not blank boxes)

If pdflatex is not installed on Windows, note this and provide Overleaf instructions:
  "Upload paper/ folder to Overleaf, set compiler to pdflatex, compile."

Session 3 is done when:
  ✅ results_summary.txt contains exact mean ± std for all codecs at all quality levels
  ✅ Abstract has correct dB gap numbers
  ✅ Author is "Independent Researcher" with gmail
  ✅ rd_curve figure is in paper with proper \label and \ref
  ✅ importance_maps figure generated and included
  ✅ All table values match JSON exactly
  ✅ "[repository to be added]" replaced with GitHub URL
  ✅ Zero "??" when compiled (or list the remaining ones for manual fix)

---

# SESSION 4: POLISH + ARXIV PREP
# Paste everything below as your first message for Session 4.

---

Read CLAUDE.md fully. We are in Session 4 — the last session.

Sessions 1-3 are done. Paper compiles clean. Now we prepare the arXiv package.

/plan

TASK 1 — Git initialize and first commit:
  cd C:\Users\abirg\.gemini\antigravity\scratch\image_compression_algorithm
  git init
  git add CLAUDE.md README.md requirements.txt pyproject.toml setup.py
  git add pawc/ tests/ paper/ kodak_results/charts/ pair_results/benchmark_results.json
  git add pair_results_glymur/benchmark_results.json (if exists)
  git add analyze_pair_results.py generate_charts.py benchmark.py
  git add AUDIT_REPORT.md KODAK_ANALYSIS.md OPTIMIZATION_SUMMARY.md
  git add .gitignore
  git commit -m "Initial commit: PAIR compression paper codebase"

Do NOT git add:
  - kodak_dataset/ (copyright)
  - kodak_results/*.jpg, *.webp, *.pawc (large binary outputs)
  - pair_results/*.jp2 (large binaries)
  - pair_results_glymur/*.jp2 (large binaries)
  - testing_images/ (personal photos)
  - __pycache__/ (already in .gitignore)
  - *.pawc, *.pwc2 (test artifacts)

TASK 2 — Update .gitignore to exclude the above permanently:
Add to .gitignore:
  kodak_dataset/
  kodak_results/*.jpg
  kodak_results/*.webp
  pair_results/*.jp2
  pair_results_glymur/*.jp2
  testing_images/
  *.pawc
  *.pwc2
  test_output/
  seminar_report_docs/

TASK 3 — Update README.md completely:
Write a professional README with:

  # PAIR: Perceptual Adaptive Importance-Guided ROI Compression
  
  [![arXiv](https://img.shields.io/badge/arXiv-XXXX.XXXXX-b31b1b.svg)](https://arxiv.org/abs/XXXX.XXXXX)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
  [![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
  
  **Authors:** Abir Gupta (Independent Researcher)
  
  One paragraph: what PAIR is, what we found, why it matters.
  
  ## Key Results
  Table: PAIR vs JPEG vs WebP on Kodak at Q70 (mean ± std)
  
  ## Quick Start
  pip install -r requirements.txt
  python -c "from pawc.pair_codec import PAIRCodec; print('OK')"
  
  ## Reproduce Results
  See REPRODUCE.md
  
  ## Citation
  BibTeX block (fill arXiv ID after upload)
  
  ## Project Structure
  Brief description of each folder

TASK 4 — Create REPRODUCE.md:
Exact steps to reproduce every number in the paper:
  1. Install dependencies
  2. Download Kodak dataset (script provided)
  3. Run: python kodak_benchmark_pair.py
  4. Run: python generate_charts.py
  5. Expected output: results matching paper Table I

TASK 5 — Verify requirements.txt is complete and exact:
  python -c "
  import pkg_resources
  needed = ['numpy', 'scipy', 'Pillow', 'opencv-python', 'PyWavelets',
            'glymur', 'matplotlib', 'pandas', 'scikit-image', 'seaborn', 'tqdm']
  for pkg in needed:
      try:
          version = pkg_resources.get_distribution(pkg).version
          print(f'{pkg}=={version}')
      except:
          print(f'MISSING: {pkg}')
  "
  Update requirements.txt with exact pinned versions from above output.

TASK 6 — Final arXiv checklist (go through every item):

  [ ] paper/PAIR_paper.tex compiles with zero warnings on references
  [ ] Zero "??" in compiled PDF
  [ ] Abstract under 1960 characters: python -c "print(len('PASTE ABSTRACT HERE'))"
  [ ] Author: Abir Gupta, Independent Researcher, abir.guptaaa@gmail.com
  [ ] GitHub repo URL in paper (not "[repository to be added]")
  [ ] All figures have both \label and \ref
  [ ] rd_curve figure included and renders
  [ ] importance_maps figure included and renders
  [ ] All table numbers match JSON (spot check 3 values)
  [ ] Bibliography: all 10 references have proper format
  [ ] Page count: 6-8 pages
  [ ] File size: final PDF under 10MB

TASK 7 — Create arXiv source package:
  In paper/ directory, create pair_arxiv.zip containing:
  - PAIR_paper.tex
  - IEEEtran.cls (download if not present)
  - references.bib (or whatever .bib file is referenced)
  - figures/ folder (all PDFs used in paper)

  Command:
  cd paper
  zip -r pair_arxiv.zip PAIR_paper.tex *.bib *.cls figures/

TASK 8 — Write the arXiv metadata (save to paper/ARXIV_METADATA.txt):

  Title: PAIR: Perceptual Adaptive Importance-Guided ROI Compression — 
         An Empirical Analysis
  
  Authors: Abir Gupta
  
  Abstract: [use the updated abstract from Session 3]
  
  Primary category: cs.CV
  Cross-list: eess.IV
  
  Comments: 6 pages, 3 figures, 2 tables. 
            Code: https://github.com/abirxgpt/pair-compression
  
  MSC classes: (leave blank)
  ACM classes: I.4.2

TASK 9 — Push to GitHub:
  Create repo at https://github.com/new
    Name: pair-compression
    Description: PAIR: Perceptual Adaptive Importance-Guided ROI Compression
    Public: YES
    License: MIT (already in repo)
    Topics: image-compression jpeg2000 perceptual-coding computer-vision

  Then push:
  git remote add origin https://github.com/abirxgpt/pair-compression.git
  git branch -M main
  git push -u origin main

Session 4 is done when:
  ✅ git repository initialized with proper .gitignore
  ✅ README.md is professional and complete
  ✅ requirements.txt has pinned versions
  ✅ REPRODUCE.md exists
  ✅ paper/pair_arxiv.zip is ready for upload
  ✅ paper/ARXIV_METADATA.txt has all submission info
  ✅ GitHub repo is public and accessible
  ✅ arXiv checklist: all items checked

After Session 4, upload pair_arxiv.zip to https://arxiv.org/submit
Fill metadata from ARXIV_METADATA.txt
Submit. Done.

---

## RESUME LINE (add after arXiv ID is assigned)

First Author — PAIR: Perceptual Adaptive Importance-Guided ROI Compression
arXiv:XXXX.XXXXX [cs.CV] · Rigorous empirical analysis of explicit perceptual
importance mapping vs classical codecs on Kodak dataset · Tile-based OpenJPEG
ROI implementation · Python codebase with full reproducibility

