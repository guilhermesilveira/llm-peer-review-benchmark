"""Compare the primary and alternative binary detection rules.

The primary rule requires the mean of Fable 5 and Opus 5 scores to be at least 0.5.
The alternative counts detection if either judge awards at least 0.5. Also reconstructs
human detection rates from the untrained group in Schroter et al. (2008), Table 5.

Writes data/checks_v17.json, using the archived filename.
Run: python code/check_detection_rules.py
"""
import json, os, sys
import numpy as np
from scipy.stats import spearmanr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aggregate_scores as A          # HUMAN_PER_ERROR (corrected m4)
import analyze_primary as V       # data loading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N = [173, 162, 156]          # untrained control reviews, papers 1-3 (Schroter 2008, Table 4)
ITEMS = V.ITEMS
MODELS = V.MODELS + V.MODELS_NEW
out = {}

# ---- 1. human detection rates
H = A.HUMAN_PER_ERROR
out["human_m4_unweighted"] = float(np.mean(H["m4"]))
out["human_m4_weighted"] = float(np.dot(H["m4"], N) / sum(N))
out["human_binary_weighted_all14"] = float(sum(np.dot(H[e], N) for e in ITEMS) / (14 * sum(N)))
out["human_binary_unweighted_all14"] = float(np.mean([np.mean(H[e]) for e in ITEMS]))

# ---- 2/3. models, both rules
def load(base, sub, manifest):
    man = json.load(open(os.path.join(base, manifest)))
    ids = [m["id"] for m in man]
    _, per = V.load_scores(os.path.join(base, sub), ids)
    return {m["id"]: m for m in man}, per

def detected(js, item, rule):
    s = [js[j].get(item, 0.0) for j in js]
    return (np.mean(s) >= 0.5) if rule == "mean" else (max(s) >= 0.5)

meta2, per2 = load(os.path.join(ROOT, "data"), "judgements", "manifest.json")
meta1, per1 = load(os.path.join(ROOT, "data_original"), "judgements", "manifest.json")
cmeta, cper = load(os.path.join(ROOT, "data"), os.path.join("controls", "judgements"), "control_manifest.json")

for rule in ("mean", "either"):
    r = {}
    for tag, meta, per in (("sens_2026", meta2, per2), ("sens_2004", meta1, per1), ("flag_controls", cmeta, cper)):
        r[tag] = {}
        for mod in MODELS:
            vals = [detected(per[rid], it, rule) for rid, m in meta.items() if m["model"] == mod and rid in per for it in ITEMS]
            r[tag][mod] = 100 * float(np.mean(vals))
    flags = sum(detected(cper[rid], it, rule) for rid in cmeta if rid in cper for it in ITEMS)
    r["control_flags"] = int(flags); r["control_items"] = 14 * len([rid for rid in cmeta if rid in cper])
    sens = [r["sens_2026"][m] for m in MODELS]; spec = [100 - r["flag_controls"][m] for m in MODELS]
    rho, p = spearmanr(sens, spec)
    rng = np.random.default_rng(17); perm = [spearmanr(sens, rng.permutation(spec))[0] for _ in range(20000)]
    r["rho_sens_spec_2026"] = float(rho); r["p_scipy"] = float(p)
    r["p_perm"] = float(np.mean(np.abs(perm) >= abs(rho) - 1e-12))
    for k in ("sens_2026", "sens_2004", "flag_controls"):
        v = r[k]; r[k + "_range"] = [min(v.values()), max(v.values()), min(v, key=v.get), max(v, key=v.get)]
    out[rule] = r

json.dump(out, open(os.path.join(ROOT, "data", "checks_v17.json"), "w"), indent=1)
for k in ("human_m4_unweighted", "human_m4_weighted", "human_binary_weighted_all14", "human_binary_unweighted_all14"):
    print(k, round(out[k], 2))
for rule in ("mean", "either"):
    r = out[rule]
    print(f"[{rule}] control flags {r['control_flags']}/{r['control_items']}; rho {r['rho_sens_spec_2026']:.3f} "
          f"P scipy {r['p_scipy']:.4f} perm {r['p_perm']:.4f}")
    for k in ("sens_2026", "sens_2004", "flag_controls"):
        lo, hi, mlo, mhi = r[k + "_range"]; print(f"   {k}: {lo:.1f} ({mlo}) to {hi:.1f} ({mhi})")
    print("   flags by model:", {m: round(v, 1) for m, v in r["flag_controls"].items()})
