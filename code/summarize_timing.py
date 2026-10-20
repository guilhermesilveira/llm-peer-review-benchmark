"""Summarise the timing run (data/timing_run/): one fresh Claude Code session per original Anthropic model and
error-seeded 2026 manuscript, run with code/run_claude_reviews.py (same prompt and settings as the reviews, effort max).
Cost (list price), duration and tokens are read from the final 'result' record of each session transcript
(data/timing_run/exp2/logs/<id>.jsonl). Writes data/timing_run/timing_summary.json.
Run: python3 code/summarize_timing.py
"""
import json, os, statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data", "timing_run", "exp2")
man = json.load(open(os.path.join(D, "manifest.json")))
out = {}
for model in ("haiku", "sonnet", "opus", "fable"):
    recs = []
    for j in (x for x in man if x["model"] == model):
        res = [json.loads(l) for l in open(os.path.join(D, "logs", j["id"] + ".jsonl")) if l.startswith("{")]
        res = [r for r in res if r.get("type") == "result"][-1]
        u = res["usage"]
        words = len(open(os.path.join(D, "out", j["id"] + ".md")).read().split())
        recs.append({"id": j["id"], "paper": j["paper"], "cost": res["total_cost_usd"], "minutes": res["duration_ms"] / 60000,
                     "input_tokens": u["input_tokens"] + u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0),
                     "output_tokens": u["output_tokens"],
                     "reasoning_tokens": (u.get("output_tokens_details") or {}).get("thinking_tokens", 0), "words": words})
    out[model] = {"n": len(recs), "model_id": man[[x["model"] for x in man].index(model)]["model_id"],
                  "cost_mean": st.mean(r["cost"] for r in recs), "cost_min": min(r["cost"] for r in recs), "cost_max": max(r["cost"] for r in recs),
                  "min_mean": st.mean(r["minutes"] for r in recs), "min_min": min(r["minutes"] for r in recs), "min_max": max(r["minutes"] for r in recs),
                  "input_tokens_mean": st.mean(r["input_tokens"] for r in recs), "output_tokens_mean": st.mean(r["output_tokens"] for r in recs),
                  "reasoning_tokens_mean": st.mean(r["reasoning_tokens"] for r in recs), "words_mean": st.mean(r["words"] for r in recs),
                  "sessions": recs}
json.dump(out, open(os.path.join(ROOT, "data", "timing_run", "timing_summary.json"), "w"), indent=1)
for m, v in out.items():
    print(f"{m:7s} n={v['n']} {v['min_mean']:.1f} min ({v['min_min']:.1f}-{v['min_max']:.1f}) ${v['cost_mean']:.2f} ({v['cost_min']:.2f}-{v['cost_max']:.2f}) "
          f"in {v['input_tokens_mean']/1000:.0f}k out {v['output_tokens_mean']/1000:.1f}k (reas {v['reasoning_tokens_mean']/1000:.1f}k) words {v['words_mean']:.0f}")
