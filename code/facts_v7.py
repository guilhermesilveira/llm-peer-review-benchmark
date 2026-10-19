"""Every number quoted in the text of manuscript v7 that is not already a field of results.json / results_v2.json.

Reads data/results.json, data_original/results.json, data/results_v2.json and the judge outputs; writes
data/facts_v7.json and prints a readable summary. Run after analyze.py, analyze_original.py and analyze_v2.py:
  python3 code/facts_v7.py
"""
import json, os, glob, collections, statistics as st
import numpy as np
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ERR = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "m1", "m2", "m3", "m4", "m5"]
ORIG7 = ["haiku", "sonnet", "opus", "fable", "gpt54mini", "gpt54", "gpt55"]
NEW8 = ["opus55", "gpt61sol", "gpt6luna", "gemini38fl", "kimik3", "dsv4pro", "qwen38_27b", "gptoss120b"]
ALL = ORIG7 + NEW8
OPEN = ["kimik3", "dsv4pro", "qwen38_27b", "gptoss120b"]
HUMAN_TOTAL = 3.29

R2 = json.load(open(os.path.join(ROOT, "data", "results.json")))
R1 = json.load(open(os.path.join(ROOT, "data_original", "results.json")))
V2 = json.load(open(os.path.join(ROOT, "data", "results_v2.json")))


def agreement(pairs):
    exact = np.mean([a == b for a, b in pairs])
    a1 = np.array([a >= 0.5 for a, b in pairs]); b1 = np.array([b >= 0.5 for a, b in pairs])
    po = np.mean(a1 == b1); pa, pb = a1.mean(), b1.mean(); pe = pa * pb + (1 - pa) * (1 - pb)
    return {"n_pairs": len(pairs), "exact": round(100 * exact, 1), "kappa": round((po - pe) / (1 - pe), 3)}


def judge_pairs(base, jdir, ids):
    pairs = []
    for rid in ids:
        f1, f2 = os.path.join(base, jdir, f"{rid}__J1.json"), os.path.join(base, jdir, f"{rid}__J2.json")
        if not (os.path.exists(f1) and os.path.exists(f2)):
            continue
        s1 = {s["id"]: float(s["score"]) for s in json.load(open(f1))["scores"]}
        s2 = {s["id"]: float(s["score"]) for s in json.load(open(f2))["scores"]}
        pairs += [(s1[e], s2[e]) for e in ERR]
    return pairs


F = {}
for tag, R, base in (("orig", R1, os.path.join(ROOT, "data_original")), ("y2026", R2, os.path.join(ROOT, "data"))):
    rows = R["rows"]; S = R["summary"]
    ids_all = [r["id"] for r in rows]
    ids_new = [r["id"] for r in rows if r["model"] in NEW8]
    ids_old = [r["id"] for r in rows if r["model"] in ORIG7]
    f = {"agreement_all": agreement(judge_pairs(base, "judgements", ids_all)),
         "agreement_orig7": agreement(judge_pairs(base, "judgements", ids_old)),
         "agreement_new8": agreement(judge_pairs(base, "judgements", ids_new))}
    per = {}
    for m in ALL:
        R_ = [r for r in rows if r["model"] == m]
        tot = [sum(r["scores"].values()) for r in R_]
        recs = collections.Counter(r["rec"] for r in R_)
        per[m] = {"n": len(R_), "total_mean": round(st.mean(tot), 2), "total_min": min(tot), "total_max": max(tot),
                  "n_ge13": sum(t >= 13 for t in tot), "n_le_human": sum(t <= HUMAN_TOTAL for t in tot),
                  "words": round(st.mean(r["words"] for r in R_)),
                  "recs": dict(recs),
                  "by_paper_total": {p: round(st.mean(sum(r["scores"].values()) for r in R_ if r["paper"] == p), 2) for p in (1, 2, 3)},
                  "by_paper_major": {p: round(st.mean(sum(v for k, v in r["scores"].items() if k[0] == "M") for r in R_ if r["paper"] == p), 2) for p in (1, 2, 3)},
                  "per_error_pct": {e: round(S[m]["per_error_pct"][e], 1) for e in ERR}}
    f["per_model"] = per
    allt = [(sum(r["scores"].values()), r["model"], r["id"]) for r in rows]
    f["n_reviews"] = len(rows)
    f["n_reviews_le_human"] = sum(t <= HUMAN_TOTAL for t, _, _ in allt)
    f["lowest_review"] = min(allt)
    # length vs detection across model means and within models (2026 trials in the manuscript; both sets here)
    mw = [per[m]["words"] for m in ALL]; mt = [per[m]["total_mean"] for m in ALL]
    rho, p = stats.spearmanr(mw, mt)
    f["length_rho_15_models"] = {"rho": round(rho, 2), "p": round(p, 3)}
    rho7, p7 = stats.spearmanr([per[m]["words"] for m in ORIG7], [per[m]["total_mean"] for m in ORIG7])
    f["length_rho_orig7"] = {"rho": round(rho7, 2), "p": round(p7, 3)}
    within = {}
    for m in ALL:
        R_ = [r for r in rows if r["model"] == m]
        r_, p_ = stats.spearmanr([r["words"] for r in R_], [sum(r["scores"].values()) for r in R_])
        within[m] = {"rho": None if np.isnan(r_) else round(r_, 2), "p": None if np.isnan(p_) else round(p_, 3)}
    f["length_within"] = within
    F[tag] = f

# unmodified manuscripts (2026 trials only)
crow = R2["control_rows"]
ctl = {}
for m in ALL:
    C = [r for r in crow if r["model"] == m]
    ctl[m] = {"n": len(C), "total_mean": round(st.mean(sum(r["scores"].values()) for r in C), 2),
              "credited_items": sum(v >= 0.5 for r in C for v in r["scores"].values()),
              "recs": dict(collections.Counter(r["rec"] for r in C))}
items = collections.Counter(); full = partial = 0; per_model_items = collections.defaultdict(int)
for r in crow:
    for e, v in r["scores"].items():
        if v >= 0.5:
            items[e] += 1; per_model_items[r["model"]] += 1
            if v >= 1: full += 1
            else: partial += 1
F["controls"] = {"per_model": ctl, "n_reviews": len(crow), "credited_total": sum(items.values()),
                 "item_observations": 14 * len(crow), "full": full, "partial": partial,
                 "credited_by_item": dict(items.most_common()),
                 "never_credited": [e for e in ERR if items[e] == 0],
                 "recs_all": dict(collections.Counter(r["rec"] for r in crow)),
                 "credited_orig7": sum(per_model_items[m] for m in ORIG7), "credited_new8": sum(per_model_items[m] for m in NEW8),
                 "credits_by_item_orig7": dict(collections.Counter(e for r in crow if r["model"] in ORIG7 for e, v in r["scores"].items() if v >= 0.5)),
                 "credits_by_item_new8": dict(collections.Counter(e for r in crow if r["model"] in NEW8 for e, v in r["scores"].items() if v >= 0.5))}

# sensitivity / specificity table from the clustered analysis
F["sens_spec"] = {m: {"sens_orig": V2["exp1"][m]["sens_all"], "sens_orig_ci": V2["exp1"][m]["sens_all_ci"],
                      "sens_2026": V2["exp2"][m]["sens_all"], "sens_2026_ci": V2["exp2"][m]["sens_all_ci"],
                      "spec_2026": V2["exp2"][m]["spec_all"], "spec_2026_ci": V2["exp2"][m]["spec_all_ci"]} for m in ALL}
F["pairwise"] = V2["pairwise_clustered"]

json.dump(F, open(os.path.join(ROOT, "data", "facts_v7.json"), "w"), indent=1)

# ---------------------------------------------------------------- readable summary
for tag in ("orig", "y2026"):
    f = F[tag]
    print(f"\n=== {tag}: agreement all {f['agreement_all']}, new8 {f['agreement_new8']}")
    print(f"reviews {f['n_reviews']}, at or below human mean: {f['n_reviews_le_human']}, lowest {f['lowest_review']}")
    print(f"length rho 15 models {f['length_rho_15_models']}, orig7 {f['length_rho_orig7']}")
    for m in sorted(ALL, key=lambda m: f["per_model"][m]["total_mean"]):
        p = f["per_model"][m]
        print(f"  {m:11s} tot {p['total_mean']:5.2f} [{p['total_min']:.2f}-{p['total_max']:.2f}] ge13 {p['n_ge13']:2d} words {p['words']:5d} recs {p['recs']} byPaperMajor {p['by_paper_major']}")
print("\n=== controls", {k: v for k, v in F["controls"].items() if k != "per_model"})
for m in ALL:
    print("  ", m, F["controls"]["per_model"][m], F["sens_spec"][m]["spec_2026"])
