# Compiling the PAIR Paper with Flowchart

The PAIR paper now includes a professional TikZ flowchart! Here's how to compile it:

## Option 1: Overleaf (Recommended - Easiest)

1. Go to [overleaf.com](https://www.overleaf.com)
2. Create a new project → "Upload Project"
3. Upload `PAIR_paper.tex`
4. Click **Recompile**
5. The flowchart will appear in your PDF!

## Option 2: Local LaTeX (If you have TeX installed)

```bash
cd paper
pdflatex PAIR_paper.tex
```

## What I Added

### Professional TikZ Flowchart

**Location:** In Section 3 (Methodology), right after "Algorithm Overview"

**Features:**
- ✅ Color-coded nodes (processes, data, components)
- ✅ Clear flow showing all 4 stages
- ✅ Annotations with technical details
- ✅ Professional IEEE-style formatting

**The flowchart shows:**

1. **Input** → RGB Image
2. **Stage 1:** Importance Map Generation
   - Edge Detection (Canny + Gaussian)
   - Texture Analysis (FFT energy)
   - Visual Saliency (Spectral residual)
   - Combined into unified importance map
3. **Stage 2:** ROI Tier Segmentation
   - High ROI (15%)
   - Medium ROI (45%)
   - Low ROI (40%)
4. **Stage 3:** Quality Allocation
   - High: Q_base + 20
   - Medium: Q_base
   - Low: Q_base - 15
   - Merged into effective quality
5. **Stage 4:** JPEG 2000 Encoding
6. **Output** → Compressed Data

## Visual Style

- **Blue boxes** = Processing steps
- **Green trapezoids** = Data/inputs/outputs
- **Orange boxes** = Sub-components
- **Purple circle** = Merge operation
- **Arrows** = Data flow

## Why This Helps

1. **Clarity:** Readers can see the entire algorithm at a glance
2. **Professional:** Standard in IEEE papers to show workflow
3. **Visual:** Much easier to understand than text alone
4. **Publishable:** Exactly what reviewers expect to see

## Paper is Complete!

Your PAIR paper now has:
- ✅ Professional text (6 pages)
- ✅ Real benchmark data tables
- ✅ Comprehensive TikZ flowchart
- ✅ Proper IEEE formatting
- ✅ Complete references

**Ready for submission!**
