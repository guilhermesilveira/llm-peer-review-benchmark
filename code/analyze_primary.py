"""Primary analyses for the 15-model peer-review benchmark.

Reads the historical and 2026 review manifests, original-judge scores and control scores.
Calculates mean scores, sensitivity, specificity, manuscript-clustered bootstrap intervals
and within-manuscript permutation comparisons. The human comparator is the untrained
control group of Schroter et al. (2008), weighted by the number of reviews per paper.

Writes data/results_v2.json, using the filename supplied in Supplementary Data 1.
Run from the repository root: python code/analyze_primary.py
"""

import json, os, re, collections
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RNG = np.random.default_rng(20260824)
NBOOT = 10000

MAJOR = [f"M{i}" for i in range(1, 10)]
MINOR = [f"m{i}" for i in range(1, 6)]
ITEMS = MAJOR + MINOR

MODELS = ["haiku", "sonnet", "opus", "fable", "gpt54mini", "gpt54", "gpt55"]
LABEL = {"haiku": "Haiku 4.5", "sonnet": "Sonnet 5", "opus": "Opus 5", "fable": "Fable 5",
         "gpt54mini": "GPT-5.4 mini", "gpt54": "GPT-5.4", "gpt55": "GPT-5.5"}
ANTHROPIC = {"haiku", "sonnet", "opus", "fable"}

# Preserve the archived two-pass random seeds and draw order so confidence intervals
# and permutation results reproduce the recorded analysis of all 15 models.
MODELS_NEW = ["opus55", "gpt61sol", "gpt6luna", "gemini38fl", "kimik3", "dsv4pro", "qwen38_27b", "gptoss120b"]
LABEL.update({"opus55": "Opus 5.5", "gpt61sol": "GPT-6.1 Sol", "gpt6luna": "GPT-6 Luna",
              "gemini38fl": "Gemini 3.8 Flash", "kimik3": "Kimi K3", "dsv4pro": "DeepSeek V4 Pro",
              "qwen38_27b": "Qwen3.8-27B", "gptoss120b": "gpt-oss-120b"})

# Schroter et al. 2008, untrained control group only (Table 4).
# Reconstructed against the published combined means; all three papers reconcile.
HUMAN_CONTROL = {
    1: {"n": 173, "major": 2.38, "minor": 0.99},
    2: {"n": 162, "major": 2.13, "minor": 0.71},
    3: {"n": 156, "major": 2.71, "minor": 0.96},
}


# ---------------------------------------------------------------- loading

def load_scores(judge_dir, ids):
    """review_id -> {item: mean judge score}. Also returns per-judge for agreement."""
    mean_scores, per_judge = {}, {}
    for rid in ids:
        js = {}
        for j in ("J1", "J2"):
            p = os.path.join(judge_dir, f"{rid}__{j}.json")
            if not os.path.exists(p):
                continue
            d = json.load(open(p))
            js[j] = {s["id"]: float(s["score"]) for s in d["scores"]}
        if not js:
            continue
        per_judge[rid] = js
        mean_scores[rid] = {
            it: float(np.mean([js[j].get(it, 0.0) for j in js])) for it in ITEMS
        }
    return mean_scores, per_judge


def load_experiment(base, judge_sub, manifest_name):
    man = json.load(open(os.path.join(base, manifest_name)))
    ids = [m["id"] for m in man]
    scores, per_judge = load_scores(os.path.join(base, judge_sub), ids)
    meta = {m["id"]: m for m in man}
    return man, meta, scores, per_judge


# ---------------------------------------------------------------- bootstrap

def cluster_boot(values_by_paper, stat=np.mean, nboot=NBOOT):
    """
    Resample papers with replacement, then reps within each sampled paper.
    values_by_paper: {paper -> array of per-review values}
    Returns (point estimate, lo, hi).
    """
    papers = sorted(values_by_paper)
    allv = np.concatenate([values_by_paper[p] for p in papers])
    point = float(stat(allv))
    out = np.empty(nboot)
    for b in range(nboot):
        pick = RNG.choice(papers, size=len(papers), replace=True)
        draws = []
        for p in pick:
            v = values_by_paper[p]
            draws.append(RNG.choice(v, size=len(v), replace=True))
        out[b] = stat(np.concatenate(draws))
    return point, float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def review_boot(values, stat=np.mean, nboot=NBOOT):
    """Old scheme: resample reviews as if independent. For side-by-side comparison."""
    values = np.asarray(values, float)
    out = np.array([stat(RNG.choice(values, size=len(values), replace=True))
                    for _ in range(nboot)])
    return float(stat(values)), float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


# ---------------------------------------------------------------- metrics

def per_review_totals(scores, meta, model, items):
    """{paper -> array of per-review summed scores over `items`}"""
    by_paper = collections.defaultdict(list)
    for rid, m in meta.items():
        if m["model"] != model or rid not in scores:
            continue
        by_paper[m["paper"]].append(sum(scores[rid][i] for i in items))
    return {p: np.array(v, float) for p, v in by_paper.items()}


def item_detection(scores, meta, model, items, thresh=0.5):
    """
    Item-level binary detection, grouped by paper.
    Each review contributes len(items) observations.
    {paper -> array of 0/1}
    """
    by_paper = collections.defaultdict(list)
    for rid, m in meta.items():
        if m["model"] != model or rid not in scores:
            continue
        by_paper[m["paper"]].extend(
            [1.0 if scores[rid][i] >= thresh else 0.0 for i in items]
        )
    return {p: np.array(v, float) for p, v in by_paper.items()}


def count_points(text):
    """
    Distinct numbered points in a review. Counts lines that open a numbered or
    bulleted item at the start of a line, which is how both harnesses format
    major/minor points under the BMJ guidance.
    """
    n = 0
    for line in text.splitlines():
        s = line.strip()
        if re.match(r"^(\d{1,2}[\.\)]\s+|[-*]\s+\*\*|\*\*\d{1,2}[\.\)])", s):
            n += 1
    return n




# ---------------------------------------------------------------- pairwise

def clustered_perm(A, B, nperm=20000):
    """
    Model-vs-model contrast, permuting model labels WITHIN paper.
    This conditions on manuscript, so it removes between-paper variance from the
    contrast. Note this is a different question from the clustered CI above:
    the CI asks how well an absolute rate generalises to a NEW manuscript,
    the permutation asks whether two models differ on THESE manuscripts.
    """
    papers = sorted(set(A) & set(B))
    obs = (np.mean(np.concatenate([A[p] for p in papers]))
           - np.mean(np.concatenate([B[p] for p in papers])))
    cnt = 0
    for _ in range(nperm):
        da, db = [], []
        for p in papers:
            pool = RNG.permutation(np.concatenate([A[p], B[p]]))
            da.append(pool[:len(A[p])]); db.append(pool[len(A[p]):])
        d = np.mean(np.concatenate(da)) - np.mean(np.concatenate(db))
        if abs(d) >= abs(obs) - 1e-12:
            cnt += 1
    return float(obs), cnt / nperm


PAIRS = [("haiku", "sonnet"), ("sonnet", "opus"), ("sonnet", "fable"),
         ("opus", "fable"), ("gpt54mini", "sonnet"), ("haiku", "gpt54mini"),
         ("gpt54", "gpt55"), ("gpt55", "opus"), ("gpt55", "sonnet")]

# Contrasts involving the added models (second pass)
NEW_PAIRS = [("opus", "opus55"), ("opus55", "fable"), ("gpt55", "gpt61sol"), ("gpt61sol", "opus55"),
             ("gpt6luna", "gpt54mini"), ("gemini38fl", "gpt61sol"), ("kimik3", "gpt61sol"), ("kimik3", "dsv4pro"),
             ("dsv4pro", "qwen38_27b"), ("gptoss120b", "haiku"), ("kimik3", "opus55")]


# ---------------------------------------------------------------- main

def run(models, pairs, priming=True):
    out = {}

    for expname, base, judge_sub, rev_sub, ctl_base in [
        ("exp2", os.path.join(ROOT, "data"), "judgements", "reviews",
         os.path.join(ROOT, "data", "controls")),
        ("exp1", os.path.join(ROOT, "data_original"), "judgements", "reviews", None),
    ]:
        man, meta, scores, per_judge = load_experiment(base, judge_sub, "manifest.json")

        # controls
        cmeta, cscores = {}, {}
        if ctl_base:
            cman = json.load(open(os.path.join(base, "control_manifest.json")))
            cids = [m["id"] for m in cman]
            cscores, _ = load_scores(os.path.join(ctl_base, "judgements"), cids)
            cmeta = {m["id"]: m for m in cman}

        rows = {}
        for mod in models:
            r = {"model": LABEL[mod]}

            # --- per-review totals, old vs clustered CI
            for tag, items, denom in [("major", MAJOR, 9), ("minor", MINOR, 5),
                                      ("total", ITEMS, 14)]:
                bp = per_review_totals(scores, meta, mod, items)
                if not bp:
                    continue
                pt, lo, hi = cluster_boot(bp)
                flat = np.concatenate([bp[p] for p in sorted(bp)])
                _, rlo, rhi = review_boot(flat)
                r[f"{tag}_mean"] = round(pt, 2)
                r[f"{tag}_ci_clustered"] = [round(lo, 2), round(hi, 2)]
                r[f"{tag}_ci_by_review"] = [round(rlo, 2), round(rhi, 2)]
                r[f"{tag}_ci_width_clustered"] = round(hi - lo, 2)
                r[f"{tag}_ci_width_by_review"] = round(rhi - rlo, 2)

            # --- sensitivity (item level, error-seeded)
            for tag, items in [("major", MAJOR), ("minor", MINOR), ("all", ITEMS)]:
                bp = item_detection(scores, meta, mod, items)
                if not bp:
                    continue
                pt, lo, hi = cluster_boot(bp)
                r[f"sens_{tag}"] = round(100 * pt, 1)
                r[f"sens_{tag}_ci"] = [round(100 * lo, 1), round(100 * hi, 1)]
                r[f"sens_{tag}_n_obs"] = int(sum(len(v) for v in bp.values()))

            # --- specificity (item level, clean controls)
            if cscores:
                for tag, items in [("major", MAJOR), ("minor", MINOR), ("all", ITEMS)]:
                    bp = item_detection(cscores, cmeta, mod, items)
                    if not bp:
                        continue
                    # specificity = 1 - false alarm rate
                    bp_spec = {p: 1.0 - v for p, v in bp.items()}
                    pt, lo, hi = cluster_boot(bp_spec)
                    r[f"spec_{tag}"] = round(100 * pt, 1)
                    r[f"spec_{tag}_ci"] = [round(100 * lo, 1), round(100 * hi, 1)]
                    r[f"spec_{tag}_n_obs"] = int(sum(len(v) for v in bp.values()))

            # --- criticism volume
            vols = []
            for rid, m in meta.items():
                if m["model"] != mod:
                    continue
                p = os.path.join(base, rev_sub, f"{rid}.md")
                if os.path.exists(p):
                    t = open(p, encoding="utf-8", errors="replace").read()
                    vols.append((count_points(t), len(t.split())))
            if vols:
                pts = np.array([v[0] for v in vols], float)
                wds = np.array([v[1] for v in vols], float)
                r["points_per_review"] = round(float(pts.mean()), 1)
                r["words_per_review"] = int(wds.mean())
                caught = r.get("total_mean", np.nan)
                r["points_per_caught_error"] = (
                    round(float(pts.mean()) / caught, 2) if caught and caught == caught else None
                )
            rows[mod] = r

        out[expname] = rows

        # pairwise contrasts, permuted within paper
        tot_by_paper = {m: per_review_totals(scores, meta, m, ITEMS) for m in MODELS + MODELS_NEW}
        pw = {}
        for a, b in pairs:
            if not tot_by_paper.get(a) or not tot_by_paper.get(b):
                continue
            d, p = clustered_perm(tot_by_paper[a], tot_by_paper[b])
            pw[f"{a}_vs_{b}"] = {"diff_of_14": round(d, 2), "perm_p": round(p, 4),
                                 "significant_0.05": bool(p < 0.05)}
        out.setdefault("pairwise_clustered", {})[expname] = pw

        # ---- priming check (Anthropic harness only; the audit tracks it there)
        aud_p = os.path.join(base, "reviewer_tool_and_context_audit.json")
        if priming and os.path.exists(aud_p):
            aud = json.load(open(aud_p))
            revaud = aud.get("experiment2_reviews") or aud.get("experiment1_reviews") or {}
            prime = {}
            for mod in sorted(ANTHROPIC):
                hit, miss = [], []
                for rid, m in meta.items():
                    if m["model"] != mod or rid not in scores or rid not in revaud:
                        continue
                    tot = sum(scores[rid][i] for i in ITEMS)
                    (hit if revaud[rid].get("referenced_experiment_context") else miss).append(tot)
                if hit and miss:
                    prime[LABEL[mod]] = {
                        "n_referenced": len(hit),
                        "n_not": len(miss),
                        "mean_referenced": round(float(np.mean(hit)), 2),
                        "mean_not": round(float(np.mean(miss)), 2),
                        "diff": round(float(np.mean(hit) - np.mean(miss)), 2),
                    }
                elif hit or miss:
                    prime[LABEL[mod]] = {
                        "n_referenced": len(hit), "n_not": len(miss),
                        "mean_referenced": round(float(np.mean(hit)), 2) if hit else None,
                        "mean_not": round(float(np.mean(miss)), 2) if miss else None,
                        "diff": None,
                    }
            # pooled, centred within model so model identity cannot drive it
            dh, dm = [], []
            for mod in sorted(ANTHROPIC):          # sorted: set order varies between runs
                vals = {}
                for rid, m in meta.items():
                    if m["model"] != mod or rid not in scores or rid not in revaud:
                        continue
                    vals[rid] = (sum(scores[rid][i] for i in ITEMS),
                                 bool(revaud[rid].get("referenced_experiment_context")))
                if not vals:
                    continue
                mu = np.mean([v[0] for v in vals.values()])
                for tot, flag in vals.values():
                    (dh if flag else dm).append(tot - mu)
            if dh and dm:
                obs = float(np.mean(dh) - np.mean(dm))
                pool = np.array(dh + dm)
                nh = len(dh)
                perm = np.array([
                    (lambda s: s[:nh].mean() - s[nh:].mean())(RNG.permutation(pool))
                    for _ in range(20000)
                ])
                prime["_pooled_within_model_centred"] = {
                    "n_referenced": len(dh), "n_not": len(dm),
                    "diff_errors_of_14": round(obs, 2),
                    "perm_p_two_sided": round(float(np.mean(np.abs(perm) >= abs(obs))), 4),
                }
            out.setdefault("priming", {})[expname] = prime
    return out


def main():
    global RNG
    RNG = np.random.default_rng(20260824)          # first pass: original seven models, original seed
    out = run(MODELS, PAIRS, priming=True)
    RNG = np.random.default_rng(20260930)          # second pass: added models, own seed
    new = run(MODELS_NEW, NEW_PAIRS, priming=False)
    for expname in ("exp2", "exp1"):
        out[expname].update(new[expname])
        out["pairwise_clustered"][expname].update(new["pairwise_clustered"][expname])

    # ---- corrected human comparator
    n = sum(v["n"] for v in HUMAN_CONTROL.values())
    out["human_untrained_control"] = {
        "per_paper": HUMAN_CONTROL,
        "major_weighted": round(sum(v["major"] * v["n"] for v in HUMAN_CONTROL.values()) / n, 2),
        "minor_weighted": round(sum(v["minor"] * v["n"] for v in HUMAN_CONTROL.values()) / n, 2),
        "major_unweighted": round(np.mean([v["major"] for v in HUMAN_CONTROL.values()]), 2),
        "minor_unweighted": round(np.mean([v["minor"] for v in HUMAN_CONTROL.values()]), 2),
        "note": ("Untrained control-group reviews from Schroter et al. (2008), Table 4; "
                 "the manuscript uses review-weighted major- and minor-error means."),
    }

    with open(os.path.join(ROOT, "data", "results_v2.json"), "w") as f:
        json.dump(out, f, indent=1)
    return out


if __name__ == "__main__":
    res = main()
    print(json.dumps(res.get("human_untrained_control"), indent=1))
    print("\nwrote data/results_v2.json")
