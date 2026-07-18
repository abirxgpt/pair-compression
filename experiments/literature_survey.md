# Literature Survey: Importance/Saliency-Guided Compression — What Baselines Did They Use?

Purpose: document which controls the prior literature ran, to substantiate the
paper's claim that the uniform-allocation / sanity-check controls are missing.

Columns:
- **Importance model**: how the "important regions" are computed
- **Codec**: base compression engine
- **Primary metric**: what they measured to claim success
- **Same-codec uniform baseline at matched rate?**: the control our paper runs
- **Random/inverted-map sanity control?**: the ablation our paper runs

| # | Paper | Importance model | Codec | Primary metric | Uniform ctrl? | Sanity ctrl? |
|---|-------|------------------|-------|----------------|:---:|:---:|
| 1 | Ouerhani et al. 2001, "Adaptive color image compression based on visual attention" (ICIAP) | Itti-Koch saliency | Custom DCT | Subjective + ROI quality | No | No |
| 2 | Christopoulos et al. 2000, "The JPEG2000 still image coding system" (TCE) | Manual ROI mask | JPEG 2000 Maxshift | ROI PSNR | N/A (manual ROI) | No |
| 3 | Ebrahimi & Lee 2002-05, foveated / perceptual JPEG 2000 line | Foveation model | JPEG 2000 | Weighted PSNR | No | No |
| 4 | Guo & Zhang 2010, "A novel multiresolution spatiotemporal saliency detection…" (TIP) | Phase spectrum saliency | Custom multiresolution | Subjective + compression ratio | No | No |
| 5 | Li, Itti et al. 2011, "Visual attention guided bit allocation in video compression" (IVC) | Itti attention model | H.264 | Eye-tracking-weighted PSNR, subjective | Partial (std encoder at matched rate, weighted metric) | No |
| 6 | Barua et al. 2015, "Saliency guided wavelet compression" (Rice) | GBVS-style saliency | Wavelet/SPIHT-style | Low-bitrate ROI quality, detection accuracy | No | No |
| 7 | Cai et al. 2017, "Closed-form optimization on saliency-guided image compression" (TMM) | Learned/graph saliency | JPEG | ROI vs non-ROI distortion trade-off | No | No |
| 8 | Prakash et al. 2017, "MS-ROI: semantic obstruction of JPEG" | CNN multi-structure saliency | JPEG | Subjective, per-region quality | No | No |
| 9 | Zünd et al. 2013, "Content-aware compression using saliency-driven image retargeting" | Saliency + retargeting | JPEG | Subjective | No | No |
| 10 | Zhang et al. 2021, "Attention-guided image compression by deep reconstruction of compressive sensed saliency skeleton" (CVPR) | Learned saliency skeleton | Learned codec | RD + subjective | No (different-architecture baselines) | No |
| 11 | Kaur et al. 2020, "Regional bit allocation with visual attention and distortion sensitivity" (MTAP) | Attention + sensitivity maps | HEVC | Subjective scores | Partial (std encoder, subjective metric) | No |
| 12 | ROI-based deep compression w/ Swin (2023, arXiv 2305.07783) | Learned ROI | Learned transformer codec | ROI-weighted RD | No (architecture comparisons) | No |

## Summary statistics for the paper

- 12/12 surveyed papers: **none** run a random- or inverted-map sanity control.
- 10/12: no same-codec uniform-allocation control at matched bitrate on global fidelity;
  the 2 partial cases (Li 2011, Kaur 2020) compare against a standard encoder but
  evaluate exclusively on attention-weighted or subjective metrics, never reporting
  the global-fidelity cost.
- 0/12 papers using multi-component importance fusion ablate the individual components.

## Honest caveats (must appear in the paper)

- The literature's strongest claims are about SUBJECTIVE / attention-weighted quality,
  not global PSNR. Our region-wise PSNR analysis (inside the top-15% importance mask)
  is the closest objective proxy for their claim, and our LPIPS numbers address
  perceptual quality. We cannot refute subjective studies we did not replicate.
- Video codecs (H.264/HEVC rows) have different rate-control machinery than JPEG 2000;
  those rows are included to document evaluation practice, not as direct comparisons.

Sources (search-verified):
- https://www.ece.rice.edu/~av21/Documents/2015/SaliencyCompression.pdf
- http://www.buaamc2.net/pdf/TMM2017closedform.pdf
- http://ilab.usc.edu/publications/doc/Li_etal11ivc.pdf
- https://openaccess.thecvf.com/content/CVPR2021/papers/Zhang_Attention-Guided_Image_Compression_by_Deep_Reconstruction_of_Compressive_Sensed_Saliency_CVPR_2021_paper.pdf
- https://link.springer.com/article/10.1007/s11042-020-08686-z
- https://arxiv.org/pdf/2305.07783
- https://www.researchgate.net/publication/223001586_Region_of_interest_coding_in_JPEG_2000
