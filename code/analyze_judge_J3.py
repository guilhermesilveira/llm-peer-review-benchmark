"""Robustness of the results to the choice of judge and to the wording of the judge instructions.

Compares the third judge (J3, Kimi K3 through OpenRouter, code/run_judge_open.py) with the two Claude judges
(J1 Fable 5, J2 Opus 5) and recomputes the main results with J3 alone and with the mean of all three judges.
Agreement uses the same definitions as facts_v7.py (exact agreement on 1 / 0.5 / 0; Cohen's kappa for score >= 0.5).

Usage: python3 code/analyze_judge_J3.py   ->  _judge_runs_J3/J3_results.json and prints a summary
"""
import json, os, random, statistics as st
import numpy as np
from scipy.stats import spearmanr, pearsonr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.join(ROOT, "additional_judges/kimi_k3")
ERR = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "m1", "m2", "m3", "m4", "m5"]
MAJ, MIN = ERR[:9], ERR[9:]
HUMAN_TOTAL = 3.29
ANTHROPIC = {"haiku", "sonnet", "opus", "fable", "opus55"}
LABEL = {"haiku": "Haiku 4.5", "sonnet": "Sonnet 5", "opus": "Opus 5", "fable": "Fable 5", "opus55": "Opus 5.5",
         "gpt54mini": "GPT-5.4 mini", "gpt54": "GPT-5.4", "gpt55": "GPT-5.5", "gpt61sol": "GPT-6.1 Sol",
         "gpt6luna": "GPT-6 Luna", "gemini38fl": "Gemini 3.8 Flash", "kimik3": "Kimi K3", "dsv4pro": "DeepSeek V4 Pro",
         "qwen38_27b": "Qwen3.8-27B", "gptoss120b": "gpt-oss-120b"}

R1 = json.load(open(os.path.join(ROOT, "data_original", "results.json")))
R2 = json.load(open(os.path.join(ROOT, "data", "results.json")))
SETS = {"2004": (R1["rows"], "data_original/judgements"), "2026": (R2["rows"], "data/judgements"),
        "control": (R2["control_rows"], "data/controls/judgements")}


def load(path):
    return {s["id"]: float(s["score"]) for s in json.load(open(path))["scores"]}


def collect(prompt="main"):
    """rows per set with J1, J2, J3 item scores (only reviews that J3 has scored)."""
    out = {}
    for name, (rows, jdir) in SETS.items():
        L = []
        for r in rows:
            f3 = os.path.join(RUN, f"kimik3_{prompt}", "judgements", f"{r['id']}__J3.json")
            if not os.path.exists(f3):
                continue
            L.append({"id": r["id"], "model": r["model"], "paper": r["paper"],
                      "J1": load(os.path.join(ROOT, jdir, f"{r['id']}__J1.json")),
                      "J2": load(os.path.join(ROOT, jdir, f"{r['id']}__J2.json")),
                      "J3": load(f3), "J12": r["scores"]})
        out[name] = L
    return out


def agreement(pairs):
    exact = np.mean([a == b for a, b in pairs])
    a1 = np.array([a >= 0.5 for a, b in pairs]); b1 = np.array([b >= 0.5 for a, b in pairs])
    po = np.mean(a1 == b1); pa, pb = a1.mean(), b1.mean(); pe = pa * pb + (1 - pa) * (1 - pb)
    return {"n_pairs": len(pairs), "exact": round(100 * exact, 1), "binary": round(100 * po, 1),
            "kappa": round((po - pe) / (1 - pe), 3)}


def pairs(L, a, b, items=ERR):
    return [(r[a][e], r[b][e]) for r in L for e in items]


def scores_with(r, judges):
    return {e: st.mean(r[j][e] for j in judges) for e in ERR}


def model_metrics(D, judges):
    """Per model: mean summed score, sensitivity (2026, 2004) and specificity, as in the paper (detected = mean >= 0.5)."""
    res = {}
    for m in LABEL:
        out = {}
        for name in ("2004", "2026"):
            R = [scores_with(r, judges) for r in D[name] if r["model"] == m]
            if not R:
                continue
            out[f"total_{name}"] = round(st.mean(sum(s.values()) for s in R), 2)
            out[f"major_{name}"] = round(st.mean(sum(s[e] for e in MAJ) for s in R), 2)
            out[f"sens_{name}"] = round(100 * np.mean([s[e] >= 0.5 for s in R for e in ERR]), 1)
            out[f"min_total_{name}"] = min(sum(s.values()) for s in R)
        C = [scores_with(r, judges) for r in D["control"] if r["model"] == m]
        if C:
            out["spec"] = round(100 * (1 - np.mean([s[e] >= 0.5 for s in C for e in ERR])), 1)
        res[m] = out
    return res


def perm_test(D, name, judges, a, b, n=20000, seed=1):
    """Difference in mean summed score between models a and b, labels shuffled within manuscript (as in the paper)."""
    rng = random.Random(seed)
    R = [(r["paper"], r["model"], sum(scores_with(r, judges).values())) for r in D[name] if r["model"] in (a, b)]
    def diff(rows):
        A = [t for p, m, t in rows if m == a]; B = [t for p, m, t in rows if m == b]
        return st.mean(A) - st.mean(B)
    obs = diff(R); hits = 0
    by_p = {}
    for p, m, t in R:
        by_p.setdefault(p, []).append((m, t))
    for _ in range(n):
        rows = []
        for p, L in by_p.items():
            labels = [m for m, t in L]; rng.shuffle(labels)
            rows += [(p, lab, t) for lab, (m, t) in zip(labels, L)]
        if abs(diff(rows)) >= abs(obs) - 1e-12:
            hits += 1
    return round(obs, 2), round((hits + 1) / (n + 1), 4)


def main():
    D = collect("main")
    n = {k: len(v) for k, v in D.items()}
    res = {"n_scored": n}
    # 1. agreement
    ag = {}
    for name, L in D.items():
        ag[name] = {"J1_J2": agreement(pairs(L, "J1", "J2")), "J3_J1": agreement(pairs(L, "J3", "J1")),
                    "J3_J2": agreement(pairs(L, "J3", "J2"))}
        t12 = [sum(r["J12"].values()) for r in L]; t3 = [sum(r["J3"].values()) for r in L]
        ag[name]["total_J3_minus_J12_mean"] = round(st.mean(np.array(t3) - np.array(t12)), 2)
        ag[name]["total_pearson_r"] = round(pearsonr(t12, t3)[0], 3) if len(L) > 2 else None
    res["agreement"] = ag
    # per-item agreement (2026 + 2004 error-seeded) and direction
    L = D["2004"] + D["2026"]
    res["per_item"] = {e: {"exact_J3_vs_J12mean_ge05": round(100 * np.mean([(r["J3"][e] >= 0.5) == (r["J12"][e] >= 0.5) for r in L]), 1),
                           "J3_minus_J12": round(st.mean(r["J3"][e] - r["J12"][e] for r in L), 3)} for e in ERR}
    # 2. self-preference checks: J3 - J12 by reviewing model
    sp = {}
    for m in LABEL:
        Lm = [r for r in D["2004"] + D["2026"] if r["model"] == m]
        if Lm:
            sp[m] = round(st.mean(sum(r["J3"].values()) - sum(r["J12"].values()) for r in Lm), 2)
    res["J3_minus_J12_by_model"] = sp
    anth = [v for m, v in sp.items() if m in ANTHROPIC]; other = [v for m, v in sp.items() if m not in ANTHROPIC]
    res["J3_minus_J12_anthropic_vs_other"] = {"anthropic": round(st.mean(anth), 2), "other": round(st.mean(other), 2)}
    # 3. main results under each judge set
    variants = {"J1J2 (paper)": ["J1", "J2"], "J3 alone": ["J3"], "J1J2J3": ["J1", "J2", "J3"]}
    mm = {k: model_metrics(D, v) for k, v in variants.items()}
    res["model_metrics"] = mm
    summ = {}
    base = mm["J1J2 (paper)"]
    for k, M in mm.items():
        ms = [m for m in LABEL if "sens_2026" in M[m] and "spec" in M[m]]
        rho, p = spearmanr([M[m]["sens_2026"] for m in ms], [M[m]["spec"] for m in ms])
        r26, _ = spearmanr([base[m]["total_2026"] for m in ms], [M[m]["total_2026"] for m in ms])
        r04, _ = spearmanr([base[m]["total_2004"] for m in ms], [M[m]["total_2004"] for m in ms])
        summ[k] = {"sens_spec_rho": round(rho, 2), "sens_spec_P": round(p, 4),
                   "rank_rho_vs_paper_2026": round(r26, 3), "rank_rho_vs_paper_2004": round(r04, 3),
                   "sens_2026_range": [min(M[m]["sens_2026"] for m in ms), max(M[m]["sens_2026"] for m in ms)],
                   "spec_range": [min(M[m]["spec"] for m in ms), max(M[m]["spec"] for m in ms)],
                   "lowest_review_total_2004": min(M[m]["min_total_2004"] for m in ms),
                   "lowest_review_total_2026": min(M[m]["min_total_2026"] for m in ms),
                   "top3_2026": sorted(ms, key=lambda m: -M[m]["total_2026"])[:3],
                   "top_open_2026": max(["kimik3", "dsv4pro", "qwen38_27b", "gptoss120b"], key=lambda m: M[m]["total_2026"])}
    res["summary_by_judge_set"] = summ
    # 4. key contrasts under J3 alone
    con = {}
    for name in ("2004", "2026"):
        for a, b in [("opus55", "opus"), ("opus55", "fable"), ("opus", "fable"), ("gpt61sol", "gpt55"),
                     ("opus55", "gpt61sol"), ("sonnet", "haiku"), ("gpt61sol", "kimik3")]:
            con[f"{name} {a} vs {b}"] = {"J1J2": perm_test(D, name, ["J1", "J2"], a, b, n=5000),
                                        "J3": perm_test(D, name, ["J3"], a, b, n=5000)}
    res["contrasts"] = con
    # 5. reworded prompt (J3 only), compared with J3 main on the same reviews
    Dr = collect("reworded")
    Lr = [r for name in Dr for r in Dr[name]]
    main_by_id = {r["id"]: r for name in D for r in D[name]}
    both = [(r, main_by_id[r["id"]]) for r in Lr if r["id"] in main_by_id]
    if both:
        prs = [(a["J3"][e], b["J3"][e]) for a, b in both for e in ERR]
        res["reworded"] = {"n_reviews": len(both), "agreement_reworded_vs_main": agreement(prs),
                           "agreement_reworded_vs_J1": agreement([(a["J3"][e], a["J1"][e]) for a, b in both for e in ERR]),
                           "total_reworded_minus_main": round(st.mean(sum(a["J3"].values()) - sum(b["J3"].values()) for a, b in both), 2),
                           "controls_credited_main": sum(b["J3"][e] >= 0.5 for a, b in both if "control" in a["id"] for e in ERR),
                           "controls_credited_reworded": sum(a["J3"][e] >= 0.5 for a, b in both if "control" in a["id"] for e in ERR)}
    json.dump(res, open(os.path.join(RUN, "J3_results.json"), "w"), indent=1)
    # printout
    print("n scored", n)
    for name, a in ag.items():
        print(name, a)
    print("per-model J3 - J12 (summed score):", sp)
    print("anthropic vs other:", res["J3_minus_J12_anthropic_vs_other"])
    for k, s in summ.items():
        print(k, s)
    print(f"\n{'model':16s} " + " | ".join(f"{k[:12]:>12s} sens26 spec  tot26" for k in mm))
    for m in sorted(LABEL, key=lambda m: base[m].get("total_2026", 0)):
        print(f"{LABEL[m]:16s} " + " | ".join(f"{mm[k][m].get('sens_2026', float('nan')):12.1f} {mm[k][m].get('spec', float('nan')):5.1f} {mm[k][m].get('total_2026', float('nan')):6.2f}" for k in mm))
    for k, v in con.items():
        print(k, v)
    print("reworded:", res.get("reworded"))
    print("per item:", res["per_item"])


if __name__ == "__main__":
    main()
