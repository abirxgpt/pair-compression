# PAIR: Perceptual Adaptive Importance-Guided ROI Compression

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![Tests: 24/2xfail](https://img.shields.io/badge/tests-24%2F2xfail-green)]()

**Author:** Abir Gupta (Independent Researcher, Ajmer, India)
**Contact:** abir.guptaaa@gmail.com

PAIR is an exploratory image compression framework that investigates whether
explicit multi-component perceptual importance mapping — combining edge detection,
texture analysis, and visual saliency — can improve lossy compression when
integrated with JPEG 2000's Region of Interest (ROI) coding.

**Key finding:** A naive global-quality Pillow implementation achieves
PSNR = 33.22 dB (SSIM = 0.815) at 0.857 BPP — 1.65 dB below JPEG but with
29% smaller files. A tile-based glymur/OpenJPEG implementation achieves
PSNR = 43.70 dB at Q95, surpassing JPEG by 2.91 dB. The investigation reveals
fundamental trade-offs between explicit perceptual modeling and the implicit
perceptual optimization already present in wavelet-based codecs.

## Key Results (Kodak Dataset, Q70, mean ± std)

| Codec | PSNR (dB) | SSIM | BPP |
|-------|-----------|------|-----|
| PAIR (Pillow) | 33.22 ± 2.42 | 0.815 ± 0.090 | 0.857 ± 0.001 |
| PAIR (glymur) | 31.30 ± 0.84 | 0.812 ± 0.061 | 1.266 ± 0.449 |
| JPEG | 34.88 ± 1.61 | 0.923 ± 0.013 | 1.213 ± 0.376 |
| WebP | 35.09 ± 1.13 | 0.924 ± 0.016 | 0.877 ± 0.415 |

*PAIR (glymur) achieves 43.70 dB PSNR at Q95, 2.91 dB above JPEG.*

## Quick Start

```bash
pip install -r requirements.txt
python -c "from pawc.pair_codec import PAIRCodec; print('OK')"
pytest tests/ -v
```

## Project Structure

```
├── pawc/                  # Main compression package
│   ├── pair_codec.py      # PAIR encoder (Pillow + glymur backends)
│   ├── jpeg2000_backend.py # TileROIEncoder (glymur) + Pillow fallback
│   ├── importance_map.py  # Multi-component perceptual importance
│   ├── metrics.py         # PSNR, SSIM, MS-SSIM
│   └── ...
├── paper/
│   ├── PAIR_paper.tex     # IEEEtran paper source
│   └── figures/           # All paper figures
├── kodak_results/         # Baseline benchmark data
│   ├── benchmark_results.json
│   └── charts/
├── pair_results/          # PAIR (Pillow) benchmark data
├── pair_results_glymur/   # PAIR (glymur) benchmark data
├── tests/                 # 24 passing, 2 xfail
├── results_summary.txt    # Final computed numbers
└── REPRODUCE.md           # Reproducibility guide
```

## Reproducing Results

See **[REPRODUCE.md](REPRODUCE.md)** for step-by-step instructions.

## Citation

```bibtex
@misc{gupta2026pair,
  title={PAIR: Perceptual Adaptive Importance-Guided ROI Compression --
         An Empirical Analysis},
  author={Gupta, Abir},
  year={2026},
  eprint={XXXX.XXXXX},
  archivePrefix={arXiv},
  primaryClass={cs.CV}
}
```

## License

MIT — see [LICENSE](LICENSE) for details.
