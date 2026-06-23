"""
Generate publication-quality charts and tables from Kodak benchmark results.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import List, Dict


def load_results(results_file: Path) -> List[Dict]:
    """Load benchmark results from JSON."""
    with open(results_file, 'r') as f:
        return json.load(f)


def generate_rate_distortion_curves(results: List[Dict], output_dir: Path):
    """Generate rate-distortion curves (PSNR vs BPP)."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Group by codec
    for codec in ['pawc', 'jpeg', 'webp']:
        codec_results = []
        for r in results:
            if r.get(codec):
                codec_results.append(r[codec])
        
        if not codec_results:
            continue
        
        # Sort by BPP
        codec_results.sort(key=lambda x: x['bpp'])
        
        bpp = [r['bpp'] for r in codec_results]
        psnr = [r['psnr'] for r in codec_results]
        
        # Plot with markers
        markers = {'pawc': 'o', 'jpeg': 's', 'webp': '^'}
        colors = {'pawc': 'blue', 'jpeg': 'red', 'webp': 'green'}
        
        ax.plot(bpp, psnr, 
                marker=markers[codec], 
                color=colors[codec],
                label=codec.upper(),
                linewidth=2,
                markersize=8,
                alpha=0.7)
    
    ax.set_xlabel('Bits Per Pixel (BPP)', fontsize=12)
    ax.set_ylabel('PSNR (dB)', fontsize=12)
    ax.set_title('Rate-Distortion Performance (Kodak Dataset)', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'rd_curve_psnr.png', dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'rd_curve_psnr.pdf', bbox_inches='tight')
    print(f"✓ Saved rate-distortion curve (PSNR)")
    plt.close()
    
    # SSIM version
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for codec in ['pawc', 'jpeg', 'webp']:
        codec_results = []
        for r in results:
            if r.get(codec):
                codec_results.append(r[codec])
        
        if not codec_results:
            continue
        
        codec_results.sort(key=lambda x: x['bpp'])
        
        bpp = [r['bpp'] for r in codec_results]
        ssim = [r['ssim'] for r in codec_results]
        
        markers = {'pawc': 'o', 'jpeg': 's', 'webp': '^'}
        colors = {'pawc': 'blue', 'jpeg': 'red', 'webp': 'green'}
        
        ax.plot(bpp, ssim,
                marker=markers[codec],
                color=colors[codec],
                label=codec.upper(),
                linewidth=2,
                markersize=8,
                alpha=0.7)
    
    ax.set_xlabel('Bits Per Pixel (BPP)', fontsize=12)
    ax.set_ylabel('SSIM', fontsize=12)
    ax.set_title('Rate-Distortion Performance - SSIM (Kodak Dataset)', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'rd_curve_ssim.png', dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / 'rd_curve_ssim.pdf', bbox_inches='tight')
    print(f"✓ Saved rate-distortion curve (SSIM)")
    plt.close()


def generate_comparison_bars(results: List[Dict], output_dir: Path):
    """Generate bar charts comparing codecs at each quality level."""
    qualities = sorted(set(r['quality'] for r in results))
    
    for metric in ['psnr', 'ssim', 'bpp']:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        x = np.arange(len(qualities))
        width = 0.25
        
        for i, codec in enumerate(['pawc', 'jpeg', 'webp']):
            values = []
            for q in qualities:
                q_results = [r[codec][metric] for r in results 
                           if r['quality'] == q and r.get(codec)]
                if q_results:
                    values.append(np.mean(q_results))
                else:
                    values.append(0)
            
            colors = {'pawc': 'blue', 'jpeg': 'red', 'webp': 'green'}
            ax.bar(x + i*width, values, width, 
                  label=codec.upper(), 
                  color=colors[codec],
                  alpha=0.8)
        
        ax.set_xlabel('Quality Level', fontsize=12)
        ylabel = {'psnr': 'PSNR (dB)', 'ssim': 'SSIM', 'bpp': 'Bits Per Pixel'}[metric]
        ax.set_ylabel(ylabel, fontsize=12)
        title = f'{metric.upper()} Comparison (Kodak Dataset Average)'
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xticks(x + width)
        ax.set_xticklabels([f'Q{q}' for q in qualities])
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(output_dir / f'comparison_{metric}.png', dpi=300, bbox_inches='tight')
        print(f"✓ Saved {metric.upper()} comparison chart")
        plt.close()


def generate_latex_table(results: List[Dict], output_file: Path):
    """Generate LaTeX table for paper."""
    qualities = sorted(set(r['quality'] for r in results))
    
    latex = []
    latex.append("\\begin{table}[htbp]")
    latex.append("\\caption{Compression Performance on Kodak Dataset (24 images, 768×512)}")
    latex.append("\\begin{center}")
    latex.append("\\begin{tabular}{ccccccc}")
    latex.append("\\toprule")
    latex.append("\\textbf{Codec} & \\textbf{Quality} & \\textbf{BPP} & \\textbf{PSNR (dB)} & \\textbf{SSIM} & \\textbf{MS-SSIM} & \\textbf{Ratio} \\\\")
    latex.append("\\midrule")
    
    for codec in ['pawc', 'jpeg', 'webp']:
        first_row = True
        for q in qualities:
            q_results = [r[codec] for r in results 
                        if r['quality'] == q and r.get(codec)]
            
            if not q_results:
                continue
            
            avg_bpp = np.mean([r['bpp'] for r in q_results])
            avg_psnr = np.mean([r['psnr'] for r in q_results])
            avg_ssim = np.mean([r['ssim'] for r in q_results])
            avg_ms_ssim = np.mean([r['ms_ssim'] for r in q_results])
            avg_ratio = np.mean([r['ratio'] for r in q_results])
            
            codec_name = codec.upper() if first_row else ""
            latex.append(f"{codec_name} & {q} & {avg_bpp:.3f} & {avg_psnr:.2f} & {avg_ssim:.4f} & {avg_ms_ssim:.4f} & {avg_ratio:.2f}:1 \\\\")
            first_row = False
        
        if codec != 'webp':
            latex.append("\\midrule")
    
    latex.append("\\bottomrule")
    latex.append("\\end{tabular}")
    latex.append("\\label{tab:kodak_results}")
    latex.append("\\end{center}")
    latex.append("\\end{table}")
    
    with open(output_file, 'w') as f:
        f.write('\n'.join(latex))
    
    print(f"✓ Saved LaTeX table to {output_file}")
    
    # Also print to console
    print("\n" + "="*100)
    print("LATEX TABLE FOR PAPER")
    print("="*100)
    print('\n'.join(latex))
    print("="*100)


def main():
    """Generate all charts and tables."""
    results_file = Path("kodak_results/benchmark_results.json")
    output_dir = Path("kodak_results/charts")
    output_dir.mkdir(exist_ok=True)
    
    if not results_file.exists():
        print(f"ERROR: Results file not found: {results_file}")
        print("Please run kodak_benchmark.py first!")
        return
    
    print("Loading benchmark results...")
    results = load_results(results_file)
    print(f"Loaded {len(results)} result entries")
    
    print("\nGenerating charts...")
    generate_rate_distortion_curves(results, output_dir)
    generate_comparison_bars(results, output_dir)
    
    print("\nGenerating LaTeX table...")
    latex_file = output_dir / "kodak_table.tex"
    generate_latex_table(results, latex_file)
    
    print(f"\n{'='*100}")
    print("ALL CHARTS AND TABLES GENERATED!")
    print(f"Output directory: {output_dir}")
    print(f"{'='*100}")
    print("\nGenerated files:")
    print("  - rd_curve_psnr.png/pdf (for paper)")
    print("  - rd_curve_ssim.png/pdf")
    print("  - comparison_psnr.png")
    print("  - comparison_ssim.png")
    print("  - comparison_bpp.png")
    print("  - kodak_table.tex (copy into paper)")


if __name__ == '__main__':
    main()
