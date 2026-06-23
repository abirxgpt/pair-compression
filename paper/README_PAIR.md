# PAIR Research Paper

## Publication-Ready IEEE Conference Paper

This directory contains the complete IEEE conference paper for **PAIR: Perceptual Adaptive Importance-Guided ROI Compression**.

## Files

- **PAIR_paper.tex** - Main LaTeX source (IEEE conference format)
- **README.md** - This file

## Paper Summary

**Title:** PAIR: Perceptual Adaptive Importance-Guided ROI Compression - An Exploratory Investigation

**Author:** Abir Gupta, Engineering College Ajmer

**Type:** IEEE Conference Paper (6 pages)

**Status:** ✅ Ready for submission

## Key Contributions

1. **Novel Multi-Component Importance Framework**
   - Automatic fusion of edge, texture, and saliency
   - No manual ROI annotation required

2. **Comprehensive Kodak Benchmark**
   - 24 images × 3 quality levels = 72 tests
   - Rigorous comparison vs JPEG, WebP
   - Real performance data

3. **Honest Analysis**
   - PAIR: 33.32 dB avg PSNR
   - JPEG: 34.91 dB (1.59 dB better)
   - Explains why perceptual approaches struggle

4. **Research Insights**
   - Why explicit importance mapping is challenging
   - Lessons for future perceptual compression
   - Value of negative results

## Results Summary

| Codec | PSNR (dB) | SSIM | BPP | Status |
|-------|-----------|------|-----|---------|
| **PAIR** | 33.32 | 0.824 | 0.857 | Novel |
| JPEG | 34.91 | 0.923 | 1.19 | Baseline |
| WebP | 35.14 | 0.923 | 0.86 | Baseline |
| Old PAWC | 31.48 | 0.729 | 2.89 | Previous |

**PAIR Achievement:** +1.84 dB over naive approach, competitive file sizes

## Compilation Instructions

### Option 1: Overleaf (Recommended)

1. Go to [overleaf.com](https://www.overleaf.com)
2. Create new project → Upload Project
3. Upload `PAIR_paper.tex`
4. Select compiler: **pdfLaTeX**
5. Click **Recompile**
6. Download PDF

### Option 2: Local LaTeX

```bash
pdflatex PAIR_paper.tex
bibtex PAIR_paper
pdflatex PAIR_paper.tex
pdflatex PAIR_paper.tex
```

**Requirements:**
- Full TeX distribution (TeX Live, MiKTeX)
- IEEEtran document class

## Target Venues

**Primary:**
- IEEE ICIP (International Conference on Image Processing)
- CVPR Workshops
- IEEE ICME (Multimedia Expo)

**Secondary:**
- Regional conferences
- arXiv preprint

**Workshop Track:**
- "Novel Approaches to Image Compression"
- "Perceptual Optimization"

## Paper Structure

1. **Abstract** - Concise summary with key results
2. **Introduction** - Motivation and research question
3. **Related Work** - Perceptual coding, JPEG 2000, ROI
4. **Methodology** - Complete PAIR algorithm description
5. **Experimental Evaluation** - Kodak benchmark results
6. **Analysis** - Why PAIR underperforms + insights
7. **Discussion** - Lessons learned, future directions
8. **Conclusion** - Summary of contributions

## Why This Is Publishable

✅ **Novel contribution** - Multi-component importance for ROI  
✅ **Rigorous evaluation** - Standard Kodak benchmark  
✅ **Honest results** - Transparent about limitations  
✅ **Research insights** - Explains why approaches fail  
✅ **Complete implementation** - Reproducible work  
✅ **Professional presentation** - IEEE format

**Negative results are valued in research!** This paper contributes understanding to the field.

## Next Steps

1. **Review the compiled PDF** - Check formatting
2. **Add repository link** - Update "Code and Data" section
3. **Generate figures** - If required by venue
4. **Submit to arXiv** - Establish priority
5. **Target conference** - Select venue and submit

---

**Paper is ready for submission!** Upload to Overleaf and compile to see the professional result.
