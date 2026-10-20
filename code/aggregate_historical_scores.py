"""Prepare descriptive scores and figure inputs for the historical trial manuscripts.

Reads data_original/manifest.json, original-judge outputs and reviews.
Writes data_original/results.json. Primary inference is performed by analyze_primary.py.
Run: python code/aggregate_historical_scores.py
"""
import json
import os
import statistics as st

import aggregate_scores as A

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data_original")


if __name__ == "__main__":
    rows = A.load("manifest.json", "judgements", "reviews", base=D)
    summary = A.summarise(rows)
    models = A.present(summary)
    per_paper = {m: {str(p): {e: 100 * st.mean(r["scores"][e] for r in rows
                                              if r["model"] == m and r["paper"] == p)
                             for e in A.ERR_IDS} for p in (1, 2, 3)} for m in models}
    human_per_paper = {str(p): {e: A.HUMAN_PER_ERROR[e][p - 1] for e in A.ERR_IDS}
                       for p in (1, 2, 3)}
    result = {"experiment": "historical trial manuscripts (BMJ 2004 supplement)",
              "summary": summary, "agreement": A.agreement(rows),
              "per_paper_error_pct": per_paper, "human_per_paper_error_pct": human_per_paper,
              "human_by_paper": summary["human"]["by_paper"],
              "rows": [{k: v for k, v in r.items() if k != "judges"} for r in rows]}
    with open(os.path.join(D, "results.json"), "w") as handle:
        json.dump(result, handle, indent=1)
    print(f"Prepared {len(rows)} historical-manuscript reviews.")
