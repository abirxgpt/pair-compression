# PAIR Project — CLAUDE.md
# Updated after Session 0 Audit (2026-06-23)
# Author: Abir Gupta | Goal: arXiv-ready first-author paper

---

## WHAT THIS PROJECT IS

PAIR (Perceptual Adaptive Importance-Guided ROI Compression) is an image
compression research paper + codebase. The goal is to get it arXiv-ready
and strong enough to list on a resume and target IEEE Signal Processing Letters.

The paper is an HONEST NEGATIVE RESULT paper — framed as:
"We rigorously investigated why explicit perceptual importance mapping
cannot beat classical codecs — and here is the precise reason why,
with implications for learned compression design."

---

## AUDIT FINDINGS SUMMARY (do not re-audit, trust these)

### What works and must NOT be touched:
- pawc/importance_map.py — solid, all tests pass
- pawc/metrics.py — solid, PSNR/SSIM/MS-SSIM all correct
- pawc/wavelet_transform.py — solid, adaptive basis selection works
- pawc/quantization.py — structure fine (one test fails but not critical)
- pawc/huffman_coder.py — works
- pawc/binary_codec.py — works
- pawc/entropy_coding.py — works
- pawc/config.py — works
- kodak_dataset/ — all 24 images present
- kodak_results/benchmark_results.json — 216 results (24 × 3 × 3), correct
- pair_results/benchmark_results.json — 72 results (24 × 3), correct
- kodak_results/charts/ — 8 figures including rd_curve_psnr.pdf (publication quality)
- paper/figures/algorithm_flowchart.pdf — TikZ flowchart, already in paper
- paper/PAIR_paper.tex — IEEEtran format, ~6 pages, mostly complete

### CRITICAL BUG (the whole point of Session 1):
- pawc/pair_codec.py and pawc/jpeg2000_backend.py use Pillow J2K
- The importance map is reduced to ONE scalar (effective_quality) via weighted average
- Pillow applies this scalar GLOBALLY — zero per-region effect
- Evidence: all 24 PAIR Q70 files are ~42,100 ± 100 bytes regardless of content
- glymur 0.14.6 IS installed but completely unused
- Fix: rewrite encoder using glymur.Jp2k with tile-based OR precinct-based quality

### Broken modules (Session 2, lower priority):
- simple_pawc_v2.py — imports adaptive_wavelet.py which doesn't exist
- pawc_v2_codec.py — same broken import + _decompress_block() returns zeros
- These are not used by the paper experiments, fix but don't prioritize

### Paper issues (Session 3):
- \ref{fig:rd_curve} exists in paper but NO matching \label — shows "??"
- rd_curve_psnr.pdf EXISTS in kodak_results/charts/ but NOT copied to paper/figures/
- Author affiliation: "Department of Electronics and Communication" — WRONG dept
- Email: 22cs04@ecajmer.ac.in — must change to abir.guptaaa@gmail.com
- Abstract claims "4.43 dB below JPEG" — actual gap at Q70 is ~1.66 dB — MISLEADING
- Paper numbers slightly off (33.32 claimed vs 33.22 actual) — update to exact
- "[repository to be added]" — must add GitHub URL before arXiv
- No std deviations in any table
- No importance map visualizations
- comparison_results.pdf in paper/figures/ is NOT referenced in paper (add or delete)

---

## EXACT ACTUAL BENCHMARK NUMBERS (use these in paper, not paper's claimed values)

### Q70 Results (mean across 24 Kodak images):
| Codec | PSNR  | SSIM  | MS-SSIM | BPP  |
|-------|-------|-------|---------|------|
| PAIR  | 33.22 | 0.815 | —       | 0.857|
| JPEG  | 34.88 | 0.923 | —       | 1.21 |
| WebP  | 35.09 | —     | —       | 0.88 |

Note: compute MS-SSIM and std dev fresh from JSON in Session 3.
The JSON has per-image data — aggregate it properly.

---

## REPOSITORY STRUCTURE (current state)

```
image_compression_algorithm/
├── CLAUDE.md                    ← THIS FILE (keep updated)
├── AUDIT_REPORT.md              ← Session 0 output, keep for reference
├── pawc/                        ← main package
│   ├── pair_codec.py            ← NEEDS REWRITE (Session 1)
│   ├── jpeg2000_backend.py      ← NEEDS REWRITE (Session 1)
│   ├── importance_map.py        ← DO NOT TOUCH
│   ├── metrics.py               ← DO NOT TOUCH
│   ├── wavelet_transform.py     ← DO NOT TOUCH
│   ├── quantization.py          ← DO NOT TOUCH
│   ├── huffman_coder.py         ← DO NOT TOUCH
│   ├── binary_codec.py          ← DO NOT TOUCH
│   ├── entropy_coding.py        ← DO NOT TOUCH
│   ├── config.py                ← DO NOT TOUCH
│   ├── simple_pawc_v2.py        ← fix imports (Session 2, low priority)
│   ├── pawc_v2_codec.py         ← fix imports + decompress (Session 2)
│   └── core.py                  ← mostly OK, file expansion bug is known
├── kodak_dataset/               ← 24 images, DO NOT TOUCH
├── kodak_results/
│   ├── benchmark_results.json   ← DO NOT RECOMPUTE
│   └── charts/                  ← ALL FIGURES EXIST HERE, publication quality
│       ├── rd_curve_psnr.pdf    ← COPY THIS TO paper/figures/
│       ├── rd_curve_ssim.pdf    ← COPY THIS TO paper/figures/
│       ├── comparison_psnr.png  ← use in paper
│       ├── comparison_ssim.png  ← use in paper
│       ├── comparison_bpp.png   ← use in paper
│       └── kodak_table.tex      ← base for paper table, update with std dev
├── pair_results/
│   ├── benchmark_results.json   ← DO NOT RECOMPUTE (unless glymur fix changes numbers)
│   └── 72 × .jp2 files         ← compressed outputs
├── paper/
│   ├── PAIR_paper.tex           ← MAIN PAPER — edit in Session 3
│   ├── PAWC_paper.tex           ← OLD VERSION — ignore
│   ├── PAWC_paper_revised.tex   ← OLD VERSION — ignore
│   └── figures/
│       ├── algorithm_flowchart.pdf  ← in paper, keep
│       ├── algorithm_flowchart.png  ← in paper, keep
│       ├── comparison_results.pdf   ← NOT in paper — add or delete (Session 3)
│       └── comparison_results.png   ← NOT in paper — add or delete (Session 3)
├── tests/                       ← 16/18 passing
├── benchmark.py                 ← DO NOT RERUN unless necessary
├── kodak_benchmark.py           ← DO NOT RERUN unless necessary
├── kodak_benchmark_pair.py      ← DO NOT RERUN (will rerun after glymur fix)
├── analyze_pair_results.py      ← useful for extracting std dev from JSON
└── generate_charts.py           ← useful for regenerating figures
```

---

## SESSION ROADMAP

### Session 1 — FIX THE ROI IMPLEMENTATION (most important)
Goal: Make PAIR actually do what the paper claims.
Files to change: pawc/pair_codec.py, pawc/jpeg2000_backend.py
Validation: After fix, Q70 file sizes should VARY by image content (not all ~42,100 bytes)

### Session 2 — FIX BROKEN CODE + ADD TESTS
Goal: Clean codebase, all 18 tests pass
Files: pawc/adaptive_wavelet.py (create), pawc_v2_codec.py, simple_pawc_v2.py
New tests: tests/test_pair_codec.py, tests/test_metrics.py

### Session 3 — FINALIZE PAPER
Goal: Zero "??" references, correct numbers, all figures included
Files: paper/PAIR_paper.tex, paper/figures/, generate new importance map viz

### Session 4 — POLISH + ARXIV PREP
Goal: arXiv submission package ready
Files: git init, README.md update, requirements.txt verify, final PDF

---

## LANGUAGE & LIBRARIES

Python 3.12 (already installed)
Use ONLY these for new code — already in environment:
- numpy, scipy, Pillow, opencv-python, PyWavelets
- glymur 0.14.6 (USE THIS for Session 1 — it's there, just unused)
- matplotlib, pandas, scikit-image, seaborn
- pytest for tests

DO NOT install new packages unless absolutely necessary.
DO NOT use openjpeg Python bindings (not installed).

---

## GLYMUR IMPLEMENTATION NOTES (critical for Session 1)

glymur 0.14.6 is available. Use it like this:

```python
import glymur
import numpy as np

# Basic JPEG 2000 encoding with quality layers
jp2 = glymur.Jp2k(output_path, data=image_array,
                   cratios=[compression_ratio])

# With multiple quality layers (better approach):
jp2 = glymur.Jp2k(output_path, data=image_array,
                   cratios=[high_ratio, mid_ratio, low_ratio])

# Tile-based approach (recommended for ROI simulation):
# Encode high-importance regions with lower compression ratio (higher quality)
# Encode low-importance regions with higher compression ratio (lower quality)
# Reconstruct by tiling
```

The tile-based approach is the REALISTIC approach for this project.
True Maxshift ROI requires OpenJPEG C API — too complex. Use tiles.

Tile-based strategy:
1. Generate importance map I(x,y)
2. Divide image into NxN tiles (e.g., 64x64)
3. For each tile, compute mean importance
4. Assign compression ratio: high importance → low ratio (better quality)
5. Encode each tile separately with glymur at its assigned ratio
6. Store tile map + compressed tiles in output file

Expected result: file sizes VARY by image content. High-detail images get
more bits in salient regions. This is genuinely more sophisticated than the
current approach.

---

## PAPER REFRAMING (the new story — use this voice in all writing)

DO NOT write: "PAIR underperforms JPEG"
DO write: "Our analysis reveals that JPEG 2000's wavelet decomposition
inherently concentrates energy in perceptually important frequency bands,
making explicit importance-map overlays largely redundant — a finding
consistent with the mathematical relationship between wavelet basis functions
and the human contrast sensitivity function."

The contribution is the INVESTIGATION, not the system. We proved something
rigorously. That has value.

---

## PAPER WRITING RULES

- IEEEtran conference format (already set)
- Every table value must match exact JSON output — no rounding beyond 2 decimal places
- Every figure must have \label and be referenced with \ref before it appears
- No "??" allowed in final compiled PDF
- Author: Abir Gupta
- Affiliation: Independent Researcher, Bengaluru, India
- Email: abir.guptaaa@gmail.com
- Repository: https://github.com/abirxgpt/pair-compression (set this up Session 4)

---

## DO NOT DO THESE THINGS

- Do NOT rerun the full Kodak benchmark (takes hours, data already exists)
- Do NOT modify importance_map.py, metrics.py, wavelet_transform.py
- Do NOT use PAWC_paper.tex or PAWC_paper_revised.tex (outdated)
- Do NOT install new Python packages
- Do NOT change the existing test files (except to add new ones)
- Do NOT use the student email (22cs04@ecajmer.ac.in) in any paper version

---

## CLAUDE CODE COMMANDS TO USE

/plan     → before any implementation block over 30 lines
/compact  → when context >70% full (long sessions)
/rewind   → if something breaks (revert code, keep conversation)
/context  → check how full the window is
