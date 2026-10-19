"""Aggregate blinded judge scores into the statistics reported in the manuscript.

Inputs (relative to the project root):
  data/manifest.json                blinded review id -> paper / model / replicate
  data/judgements/review_XXX__J{1,2}.json   two blinded judges per review (Schroter 1 / 0.5 / 0 scheme)
  data/control_manifest.json, data/controls/judgements/   same for the clean-manuscript controls
  data/reviews/*.md                 the reviews themselves (used only for word counts)
Outputs:
  data/results.json                 all aggregates used by make_figures.py and the manuscript
  data/results_summary.md           human-readable tables
Run:  python code/analyze.py
"""
import json, os, glob, statistics as st, math, random
from collections import defaultdict, Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")
ERR_IDS = ["M1","M2","M3","M4","M5","M6","M7","M8","M9","m1","m2","m3","m4","m5"]
ERR_NAMES = {
 "M1":"Poor justification for the study","M2":"Biased randomisation procedure","M3":"No sample size calculation",
 "M4":"Reliability/validity of outcome measures unknown","M5":"Not analysed by intention to treat","M6":"Poor response rate",
 "M7":"Unjustified conclusions","M8":"Abstract vs results discrepancy","M9":"Inconsistent denominators",
 "m1":"No ethics committee approval","m2":"No explanation of non-randomised cases / flow","m3":"Text vs table inconsistency",
 "m4":"Word reversal (wrong interpretation)","m5":"Hawthorne effect not considered"}
MODELS = ["haiku","sonnet","opus","fable","gpt54mini","gpt54","gpt55",   # models with no rows are skipped
          # added 30 Sep 2026: newer closed models and open-weight models
          "opus55","gpt61sol","gpt6luna","gemini38fl","kimik3","dsv4pro","qwen38_27b","gptoss120b"]
MODEL_LABEL = {"haiku":"Haiku 4.5","sonnet":"Sonnet 5","opus":"Opus 5","fable":"Fable 5",
               "gpt54mini":"GPT-5.4 mini","gpt54":"GPT-5.4","gpt55":"GPT-5.5",
               "opus55":"Opus 5.5","gpt61sol":"GPT-6.1 Sol","gpt6luna":"GPT-6 Luna","gemini38fl":"Gemini 3.8 Flash",
               "kimik3":"Kimi K3","dsv4pro":"DeepSeek V4 Pro","qwen38_27b":"Qwen3.8-27B","gptoss120b":"gpt-oss-120b"}
def present(summ): return [m for m in MODELS if m in summ]
# Schroter et al. 2008, Table 5: % of control-group (untrained) reviewers identifying each error, papers 1-3
# 15 Oct 2026: m4 paper 3 corrected from 10 to 7 (10 is the face-to-face group's value for paper 1; flagged by Xavier)
HUMAN_PER_ERROR = {
 "M1":[31,22,30],"M2":[49,46,48],"M3":[21,22,25],"M4":[13,15,45],"M5":[22,9,34],"M6":[34,43,46],
 "M7":[43,36,44],"M8":[23,20,33],"M9":[38,40,17],"m1":[18,25,33],"m2":[50,30,56],"m3":[5,12,4],"m4":[13,9,7],"m5":[21,2,3]}
HUMAN_MEAN_MAJOR = [2.58, 2.71, 3.05]   # of 9 (all reviewer groups, papers 1-3, Schroter 2008 abstract/results)
HUMAN_MEAN_MINOR = [0.91, 0.85, 1.09]   # of 5

def load(manifest_file, judge_dir, review_dir):
    manifest = {j["id"]: j for j in json.load(open(os.path.join(D, manifest_file)))}
    rows = []
    for rid, job in manifest.items():
        per = {}
        for jf in sorted(glob.glob(os.path.join(D, judge_dir, f"{rid}__J*.json"))):
            d = json.load(open(jf))
            per[os.path.basename(jf).split("__")[1].split(".")[0]] = {
                "scores": {s["id"]: float(s["score"]) for s in d["scores"]}, "rec": d.get("recommendation","unclear")}
        if not per: continue
        mean_scores = {e: st.mean([p["scores"].get(e,0) for p in per.values()]) for e in ERR_IDS}
        rf = os.path.join(D, review_dir, f"{rid}.md")
        words = len(open(rf).read().split()) if os.path.exists(rf) else None
        rows.append({"id": rid, **job, "judges": per, "scores": mean_scores,
                     "rec": Counter(p["rec"] for p in per.values()).most_common(1)[0][0], "words": words})
    return rows

def boot_ci(vals, n=5000, seed=1):
    rnd = random.Random(seed); m = len(vals)
    bs = sorted(st.mean(rnd.choices(vals, k=m)) for _ in range(n))
    return bs[int(0.025*n)], bs[int(0.975*n)]

def summarise(rows):
    out = {}
    for m in MODELS:
        R = [r for r in rows if r["model"]==m]
        if not R: continue
        maj = [sum(r["scores"][e] for e in ERR_IDS if e[0]=="M") for r in R]
        mino = [sum(r["scores"][e] for e in ERR_IDS if e[0]=="m") for r in R]
        tot = [a+b for a,b in zip(maj,mino)]
        out[m] = {"n": len(R), "major_mean": st.mean(maj), "major_ci": boot_ci(maj), "minor_mean": st.mean(mino), "minor_ci": boot_ci(mino),
                  "total_mean": st.mean(tot), "totals": tot, "majors": maj, "minors": mino,
                  "major_pct": 100*st.mean(maj)/9, "minor_pct": 100*st.mean(mino)/5,
                  "per_error_pct": {e: 100*st.mean([r["scores"][e] for r in R]) for e in ERR_IDS},
                  "per_error_full_pct": {e: 100*st.mean([1 if r["scores"][e]>=0.75 else 0 for r in R]) for e in ERR_IDS},
                  "recommendations": dict(Counter(r["rec"] for r in R)),
                  "words_mean": st.mean([r["words"] for r in R if r["words"]]),
                  "by_paper": {p: {"major": st.mean([sum(r["scores"][e] for e in ERR_IDS if e[0]=="M") for r in R if r["paper"]==p]),
                                   "minor": st.mean([sum(r["scores"][e] for e in ERR_IDS if e[0]=="m") for r in R if r["paper"]==p]),
                                   "n": len([r for r in R if r["paper"]==p])} for p in (1,2,3)}}
    out["human"] = {"major_mean": st.mean(HUMAN_MEAN_MAJOR), "minor_mean": st.mean(HUMAN_MEAN_MINOR),
                    "major_pct": 100*st.mean(HUMAN_MEAN_MAJOR)/9, "minor_pct": 100*st.mean(HUMAN_MEAN_MINOR)/5,
                    "per_error_pct": {e: st.mean(v) for e,v in HUMAN_PER_ERROR.items()},
                    "by_paper": {1:{"major":2.58,"minor":0.91},2:{"major":2.71,"minor":0.85},3:{"major":3.05,"minor":1.09}}}
    return out

def agreement(rows):
    pairs = []
    for r in rows:
        js = list(r["judges"].values())
        if len(js) >= 2:
            for e in ERR_IDS: pairs.append((js[0]["scores"].get(e,0), js[1]["scores"].get(e,0)))
    exact = st.mean([a==b for a,b in pairs]); a1=[a>=0.5 for a,b in pairs]; b1=[b>=0.5 for a,b in pairs]
    po = st.mean([x==y for x,y in zip(a1,b1)]); pa=st.mean(a1); pb=st.mean(b1); pe=pa*pb+(1-pa)*(1-pb)
    conf = Counter((a,b) for a,b in pairs)
    return {"n_pairs": len(pairs), "exact_agreement": exact, "binary_agreement": po, "kappa_binary": (po-pe)/(1-pe),
            "confusion": {f"{a}|{b}": n for (a,b),n in conf.items()}}

def mann_whitney_p(x, y):
    """Two-sided exact-ish Mann-Whitney U via normal approximation with tie correction (small samples)."""
    allv = sorted([(v,0) for v in x]+[(v,1) for v in y]); n1,n2=len(x),len(y)
    # ranks with ties
    ranks = {}; i=0
    while i < len(allv):
        j=i
        while j+1 < len(allv) and allv[j+1][0]==allv[i][0]: j+=1
        r=(i+j)/2+1
        for k in range(i,j+1): ranks[k]=r
        i=j+1
    R1 = sum(ranks[k] for k,(v,g) in enumerate(allv) if g==0)
    U1 = R1 - n1*(n1+1)/2; U = min(U1, n1*n2-U1)
    ties = Counter(v for v,_ in allv); N=n1+n2
    tie_term = sum(t**3-t for t in ties.values())/(N*(N-1)) if N>1 else 0
    sigma = math.sqrt(n1*n2/12*((N+1)-tie_term)); mu=n1*n2/2
    if sigma==0: return 1.0
    z = (abs(U-mu)-0.5)/sigma
    return math.erfc(z/math.sqrt(2))

if __name__ == "__main__":
    rows = load("manifest.json", "judgements", "reviews")
    ctrl = load("control_manifest.json", os.path.join("controls","judgements"), os.path.join("controls","reviews"))
    summ = summarise(rows); agr = agreement(rows)
    csumm = summarise(ctrl) if ctrl else {}
    # pairwise tests on per-review totals
    tests = {}; PM = present(summ)
    for a in PM:
        for b in PM:
            if a<b: tests[f"{a}_vs_{b}"] = mann_whitney_p(summ[a]["totals"], summ[b]["totals"])
    res = {"summary": summ, "agreement": agr, "controls": csumm, "tests_total_mannwhitney_p": tests,
           "rows": [{k:v for k,v in r.items() if k!="judges"} for r in rows],
           "control_rows": [{k:v for k,v in r.items() if k!="judges"} for r in ctrl]}
    json.dump(res, open(os.path.join(D,"results.json"),"w"), indent=1)
    L = []
    L.append("# Results summary (generated by code/analyze.py)\n")
    L.append(f"Judge agreement: {agr['n_pairs']} paired judgements; exact agreement {100*agr['exact_agreement']:.1f}%; binary agreement {100*agr['binary_agreement']:.1f}%; Cohen's kappa {agr['kappa_binary']:.3f}\n")
    L.append("| Group | n reviews | Major (of 9), mean [95% CI] | % | Minor (of 5), mean [95% CI] | % | Mean words |\n|---|---|---|---|---|---|---|")
    L.append(f"| BMJ reviewers 2008 (Schroter) | 607 x 3 papers | {summ['human']['major_mean']:.2f} | {summ['human']['major_pct']:.0f} | {summ['human']['minor_mean']:.2f} | {summ['human']['minor_pct']:.0f} | - |")
    for m in PM:
        s=summ[m]; L.append(f"| {MODEL_LABEL[m]} | {s['n']} | {s['major_mean']:.2f} [{s['major_ci'][0]:.2f}, {s['major_ci'][1]:.2f}] | {s['major_pct']:.0f} | {s['minor_mean']:.2f} [{s['minor_ci'][0]:.2f}, {s['minor_ci'][1]:.2f}] | {s['minor_pct']:.0f} | {s['words_mean']:.0f} |")
    L.append("\n## Per-error detection (% of reviews; mean of the two judges' 0/0.5/1 scores)\n")
    L.append("| Error | Humans (control group, Schroter Table 5) | " + " | ".join(MODEL_LABEL[m] for m in PM) + " |\n|---|---|" + "---|"*len(PM))
    for e in ERR_IDS:
        L.append(f"| {e} {ERR_NAMES[e]} | {summ['human']['per_error_pct'][e]:.0f} | " + " | ".join(f"{summ[m]['per_error_pct'][e]:.0f}" for m in PM) + " |")
    L.append("\n## Recommendations\n")
    for m in PM: L.append(f"- {MODEL_LABEL[m]}: {summ[m]['recommendations']}")
    L.append("\n## Pairwise Mann-Whitney (per-review total of 14), two-sided p\n")
    for k,v in tests.items(): L.append(f"- {k}: p = {v:.4g}")
    if csumm:
        L.append("\n## Clean-manuscript controls (credited 'detections' of absent errors)\n")
        L.append("| Model | n | Major credited (of 9) | Minor credited (of 5) | Recommendations |\n|---|---|---|---|---|")
        for m in PM:
            if m in csumm: L.append(f"| {MODEL_LABEL[m]} | {csumm[m]['n']} | {csumm[m]['major_mean']:.2f} | {csumm[m]['minor_mean']:.2f} | {csumm[m]['recommendations']} |")
    open(os.path.join(D,"results_summary.md"),"w").write("\n".join(L)+"\n")
    print("\n".join(L))
