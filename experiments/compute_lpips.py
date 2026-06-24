"""Compute LPIPS on ablation variants for paper."""
import sys, json, numpy as np
sys.path.insert(0, '.')
import lpips, torch
from PIL import Image
from pawc.jpeg2000_backend import GlymurROIEncoder
from pawc.importance_map import ImportanceMapGenerator

loss_fn = lpips.LPIPS(net='alex')
encoder = GlymurROIEncoder()

VARIANTS = {
    'default':  (0.4, 0.3, 0.3),
    'uniform':  None,  # special = all 0.5
    'edge_only':(1.0, 0.0, 0.0),
}

results = {}
for var, weights in VARIANTS.items():
    print(f'LPIPS: {var}...')
    scores = []
    for img_num in range(1, 25):
        img_path = f'kodak_dataset/kodim{img_num:02d}.png'
        img = np.array(Image.open(img_path).convert('RGB'))

        if var == 'uniform':
            imp = np.ones((img.shape[0], img.shape[1]), dtype=np.float32) * 0.5
        else:
            gen = ImportanceMapGenerator(*weights)
            imp = gen.generate(img)

        jp2_path = f'experiments/ablation/{var}_kodim{img_num:02d}.jp2'
        decoded = encoder.decode(jp2_path)

        orig_t = torch.from_numpy(img).permute(2,0,1).unsqueeze(0).float() / 127.5 - 1.0
        dec_t = torch.from_numpy(decoded).permute(2,0,1).unsqueeze(0).float() / 127.5 - 1.0
        scores.append(loss_fn(orig_t, dec_t).item())

    results[var] = scores
    print(f'  LPIPS = {np.mean(scores):.4f} +/- {np.std(scores):.4f}')

with open('experiments/lpips_results.json', 'w') as f:
    json.dump(results, f, indent=2)

# Also compute for vanilla J2K at cr=30
print('LPIPS: vanilla J2K cr=30...')
vj2k_scores = []
for img_num in range(1, 25):
    img_path = f'kodak_dataset/kodim{img_num:02d}.png'
    img = np.array(Image.open(img_path).convert('RGB'))
    jp2_path = f'experiments/vanilla_j2k/kodim{img_num:02d}_cr30.jp2'
    import glymur
    decoded = glymur.Jp2k(jp2_path)[:]
    orig_t = torch.from_numpy(img).permute(2,0,1).unsqueeze(0).float() / 127.5 - 1.0
    dec_t = torch.from_numpy(decoded).permute(2,0,1).unsqueeze(0).float() / 127.5 - 1.0
    vj2k_scores.append(loss_fn(orig_t, dec_t).item())

results['vanilla_j2k_cr30'] = vj2k_scores
print(f'  LPIPS = {np.mean(vj2k_scores):.4f} +/- {np.std(vj2k_scores):.4f}')

with open('experiments/lpips_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print('\nDone. Results:')
for var, scores in results.items():
    print(f'  {var:<25}: LPIPS = {np.mean(scores):.4f} +/- {np.std(scores):.4f}')
