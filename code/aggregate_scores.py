"""Prepare descriptive scores and figure inputs for the 2026 reviews and controls.

Reads data/manifest.json, data/control_manifest.json, original-judge outputs and reviews.
Writes data/results.json. Primary inference is performed by analyze_primary.py.
Run: python code/aggregate_scores.py
"""
import json
import os
import statistics as st
from collections import Counter

from analyze_primary import HUMAN_CONTROL

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")
ERR_IDS = [f"M{i}" for i in range(1, 10)] + [f"m{i}" for i in range(1, 6)]
MODELS = ["haiku", "sonnet", "opus", "fable", "gpt54mini", "gpt54", "gpt55",
          "opus55", "gpt61sol", "gpt6luna", "gemini38fl", "kimik3", "dsv4pro", "qwen38_27b", "gptoss120b"]
MODEL_LABEL = {"haiku": "Haiku 4.5", "sonnet": "Sonnet 5", "opus": "Opus 5", "fable": "Fable 5",
               "gpt54mini": "GPT-5.4 mini", "gpt54": "GPT-5.4", "gpt55": "GPT-5.5",
               "opus55": "Opus 5.5", "gpt61sol": "GPT-6.1 Sol", "gpt6luna": "GPT-6 Luna",
               "gemini38fl": "Gemini 3.8 Flash", "kimik3": "Kimi K3", "dsv4pro": "DeepSeek V4 Pro",
               "qwen38_27b": "Qwen3.8-27B", "gptoss120b": "gpt-oss-120b"}
# Schroter et al. (2008), Table 5, untrained control group, papers 1–3.
HUMAN_PER_ERROR = {
    "M1": [31, 22, 30], "M2": [49, 46, 48], "M3": [21, 22, 25], "M4": [13, 15, 45],
    "M5": [22, 9, 34], "M6": [34, 43, 46], "M7": [43, 36, 44], "M8": [23, 20, 33],
    "M9": [38, 40, 17], "m1": [18, 25, 33], "m2": [50, 30, 56], "m3": [5, 12, 4],
    "m4": [13, 9, 7], "m5": [21, 2, 3],
}


def present(summary):
    return [model for model in MODELS if model in summary]


def load(manifest_file, judge_dir, review_dir, base=D):
    manifest = json.load(open(os.path.join(base, manifest_file)))
    rows = []
    for job in manifest:
        rid = job["id"]
        per = {}
        for judge in ("J1", "J2"):
            record = json.load(open(os.path.join(base, judge_dir, f"{rid}__{judge}.json")))
            per[judge] = {"scores": {s["id"]: float(s["score"]) for s in record["scores"]},
                          "rec": record.get("recommendation", "unclear")}
        mean_scores = {error: st.mean(per[judge]["scores"][error] for judge in ("J1", "J2"))
                       for error in ERR_IDS}
        words = len(open(os.path.join(base, review_dir, f"{rid}.md")).read().split())
        rows.append({"id": rid, **job, "judges": per, "scores": mean_scores,
                     "rec": Counter(p["rec"] for p in per.values()).most_common(1)[0][0], "words": words})
    return rows


def summarise(rows):
    out = {}
    for model in MODELS:
        reviews = [r for r in rows if r["model"] == model]
        if not reviews:
            continue
        major = [sum(r["scores"][e] for e in ERR_IDS[:9]) for r in reviews]
        minor = [sum(r["scores"][e] for e in ERR_IDS[9:]) for r in reviews]
        totals = [a + b for a, b in zip(major, minor)]
        out[model] = {
            "n": len(reviews), "major_mean": st.mean(major), "minor_mean": st.mean(minor),
            "total_mean": st.mean(totals), "totals": totals, "majors": major, "minors": minor,
            "major_pct": 100 * st.mean(major) / 9, "minor_pct": 100 * st.mean(minor) / 5,
            "per_error_pct": {e: 100 * st.mean(r["scores"][e] for r in reviews) for e in ERR_IDS},
            "recommendations": dict(Counter(r["rec"] for r in reviews)),
            "words_mean": st.mean(r["words"] for r in reviews),
            "by_paper": {p: {"major": st.mean(sum(r["scores"][e] for e in ERR_IDS[:9])
                                               for r in reviews if r["paper"] == p),
                              "minor": st.mean(sum(r["scores"][e] for e in ERR_IDS[9:])
                                               for r in reviews if r["paper"] == p),
                              "n": sum(r["paper"] == p for r in reviews)} for p in (1, 2, 3)},
        }
    count = sum(v["n"] for v in HUMAN_CONTROL.values())
    major = sum(v["n"] * v["major"] for v in HUMAN_CONTROL.values()) / count
    minor = sum(v["n"] * v["minor"] for v in HUMAN_CONTROL.values()) / count
    out["human"] = {"cohort": "untrained control group", "n": count,
                    "major_mean": major, "minor_mean": minor,
                    "major_pct": 100 * major / 9, "minor_pct": 100 * minor / 5,
                    "per_error_pct": {e: st.mean(v) for e, v in HUMAN_PER_ERROR.items()},
                    "by_paper": HUMAN_CONTROL}
    return out


def agreement(rows):
    pairs = [(r["judges"]["J1"]["scores"][e], r["judges"]["J2"]["scores"][e])
             for r in rows for e in ERR_IDS]
    exact = st.mean(a == b for a, b in pairs)
    aa = [a >= 0.5 for a, _ in pairs]
    bb = [b >= 0.5 for _, b in pairs]
    observed = st.mean(a == b for a, b in zip(aa, bb))
    pa, pb = st.mean(aa), st.mean(bb)
    expected = pa * pb + (1 - pa) * (1 - pb)
    confusion = Counter(pairs)
    return {"n_pairs": len(pairs), "exact_agreement": exact, "binary_agreement": observed,
            "kappa_binary": (observed - expected) / (1 - expected),
            "confusion": {f"{a}|{b}": n for (a, b), n in confusion.items()}}


if __name__ == "__main__":
    rows = load("manifest.json", "judgements", "reviews")
    controls = load("control_manifest.json", "controls/judgements", "controls/reviews")
    result = {"summary": summarise(rows), "agreement": agreement(rows), "controls": summarise(controls),
              "rows": [{k: v for k, v in r.items() if k != "judges"} for r in rows],
              "control_rows": [{k: v for k, v in r.items() if k != "judges"} for r in controls]}
    with open(os.path.join(D, "results.json"), "w") as handle:
        json.dump(result, handle, indent=1)
    print(f"Prepared {len(rows)} error-seeded reviews and {len(controls)} control reviews.")
