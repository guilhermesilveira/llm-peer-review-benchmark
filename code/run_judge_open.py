"""Third judge (J3) through OpenRouter: score every review against the answer key with an open-weight model.

Same task as the two Claude judges (J1 Fable 5, J2 Opus 5): one review, the paper's answer key, the 1 / 0.5 / 0 scheme,
JSON output with a verbatim quote per score. Differences forced by the API: the key and the review are placed inside the
prompt (prompts/judge_prompt_api_inline.txt) instead of being read from files, and each request scores one review.
The judge is blind to the reviewing model (reviews carry neutral ids only).

A second prompt (prompts/judge_prompt_api_inline_reworded.txt) states the same rules in different words; it is run on a
fixed subset to test how much the scores depend on the wording of the judge instructions.

Usage (repo root; needs OPENROUTER_API_KEY in the environment or in .env):
  python3 code/run_judge_open.py --prompt main --concurrency 8           # all 405 reviews
  python3 code/run_judge_open.py --prompt reworded --concurrency 8       # 90-review subset
  python3 code/run_judge_open.py --prompt main --limit 5                 # pilot
Outputs: _judge_runs_J3/<judge>_<prompt>/judgements/<id>__J3.json, .../logs/<id>.json (full API response with usage
and cost), .../manifest.json. Re-running skips finished jobs. Nothing in data/ is changed.
"""
import argparse, json, os, re, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_URL = "https://openrouter.ai/api/v1/chat/completions"
JUDGES = {  # key -> (OpenRouter model id, reasoning effort, provider routing)
    "kimik3": ("moonshotai/kimi-k3", "high", {"order": ["moonshotai"], "allow_fallbacks": False}),
}
PROMPTS = {"main": "prompts/judge_prompt_api_inline.txt", "reworded": "prompts/judge_prompt_api_inline_reworded.txt"}
IDS = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "m1", "m2", "m3", "m4", "m5"]


def load_key():
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"]
    for line in open(os.path.join(ROOT, ".env")):
        if line.strip().startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("OPENROUTER_API_KEY not found")


def all_jobs():
    """Every scored review: (id, set, paper, review path, key path), from the results files."""
    jobs = []
    r1 = json.load(open(os.path.join(ROOT, "data_original", "results.json")))
    r2 = json.load(open(os.path.join(ROOT, "data", "results.json")))
    for r in r1["rows"]:
        jobs.append({"id": r["id"], "set": "2004", "paper": r["paper"], "model": r["model"], "rep": r.get("rep"),
                     "review": f"data_original/reviews/{r['id']}.md", "key": f"data_original/key_paper{r['paper']}.json"})
    for r in r2["rows"]:
        jobs.append({"id": r["id"], "set": "2026", "paper": r["paper"], "model": r["model"], "rep": r.get("rep"),
                     "review": f"data/reviews/{r['id']}.md", "key": f"data/key_paper{r['paper']}.json"})
    for r in r2["control_rows"]:
        jobs.append({"id": r["id"], "set": "control", "paper": r["paper"], "model": r["model"], "rep": 1,
                     "review": f"data/controls/reviews/{r['id']}.md", "key": f"data/key_paper{r['paper']}.json"})
    return jobs


def subset(jobs):
    """Reworded-prompt subset: one error-seeded 2026 review per model and paper (lowest rep) plus all 45 controls."""
    pick = {}
    for j in jobs:
        if j["set"] == "2026":
            k = (j["model"], j["paper"])
            if k not in pick or j["rep"] < pick[k]["rep"]:
                pick[k] = j
    return sorted(pick.values(), key=lambda j: j["id"]) + [j for j in jobs if j["set"] == "control"]


def call_api(key, model_id, effort, provider, prompt, max_tokens=32000, tries=4):
    body = {"model": model_id, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens,
            "reasoning": {"effort": effort}, "provider": provider, "usage": {"include": True}}
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode(), method="POST", headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/ruslanrust", "X-Title": "inserted-error replication judge"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=1200) as r:
                resp = json.load(r)
            if "choices" not in resp:                      # errors can come back as HTTP 200
                raise RuntimeError(json.dumps(resp)[:300])
            return resp
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:300]
            if e.code in (408, 429, 500, 502, 503, 504) and attempt < tries - 1:
                time.sleep(20 * (attempt + 1)); continue
            raise RuntimeError(f"HTTP {e.code}: {msg}")
        except Exception:
            if attempt < tries - 1:
                time.sleep(20 * (attempt + 1)); continue
            raise


def parse(text):
    """The JSON object in the reply, checked for 14 ids in order and scores in {0, 0.5, 1}."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    a, b = t.find("{"), t.rfind("}")
    obj = json.loads(t[a:b + 1])
    ids = [s["id"] for s in obj["scores"]]
    if ids != IDS:
        raise ValueError(f"ids {ids}")
    for s in obj["scores"]:
        s["score"] = float(s["score"])
        if s["score"] not in (0.0, 0.5, 1.0):
            raise ValueError(f"score {s['score']}")
    return obj


def run_job(job, template, judge, d, key):
    out = os.path.join(d, "judgements", f"{job['id']}__J3.json")
    log = os.path.join(d, "logs", f"{job['id']}.json")
    if os.path.exists(out):
        return job["id"], "skip", 0.0
    prompt = (template.replace("{KEY_JSON}", open(os.path.join(ROOT, job["key"])).read().strip())
                      .replace("{REVIEW_TEXT}", open(os.path.join(ROOT, job["review"])).read().strip()))
    model_id, effort, provider = JUDGES[judge]
    cost, last_err = 0.0, None
    for attempt in range(2):                               # one retry if the reply is not valid JSON
        t0 = time.time()
        resp = call_api(key, model_id, effort, provider, prompt)
        usage = resp.get("usage") or {}
        cost += float(usage.get("cost") or 0)
        text = resp["choices"][0]["message"].get("content") or ""
        json.dump({"id": job["id"], "attempt": attempt + 1, "seconds": round(time.time() - t0, 1),
                   "served_by": resp.get("provider"), "model": resp.get("model"), "usage": usage, "response": resp},
                  open(log if attempt == 0 else log.replace(".json", f"_try{attempt + 1}.json"), "w"), indent=1)
        try:
            obj = parse(text)
            obj["_meta"] = {"judge": judge, "model_id": model_id, "served_by": resp.get("provider"), "prompt": template_name}
            json.dump(obj, open(out, "w"), indent=1, ensure_ascii=False)
            return job["id"], "ok", cost
        except Exception as e:
            last_err = e
    return job["id"], f"invalid: {last_err}", cost


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", default="kimik3", choices=list(JUDGES))
    ap.add_argument("--prompt", default="main", choices=list(PROMPTS))
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0, help="pilot: only the first N jobs")
    args = ap.parse_args()
    template_name = args.prompt
    template = open(os.path.join(ROOT, PROMPTS[args.prompt])).read()
    jobs = all_jobs()
    if args.prompt == "reworded":
        jobs = subset(jobs)
    if args.limit:
        # pilot: a spread over sets and models
        jobs = sorted(jobs, key=lambda j: (j["set"] != "2026", j["model"], j["paper"]))[::max(1, len(jobs) // args.limit)][:args.limit]
    d = os.path.join(ROOT, "additional_judges/kimi_k3", f"{args.judge}_{args.prompt}")
    for sub in ("judgements", "logs"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    json.dump(jobs, open(os.path.join(d, "manifest.json" if not args.limit else "manifest_pilot.json"), "w"), indent=1)
    key = load_key()
    total, done, bad = 0.0, 0, []
    print(f"{len(jobs)} jobs, judge {args.judge}, prompt {args.prompt}", flush=True)
    with ThreadPoolExecutor(args.concurrency) as ex:
        futs = {ex.submit(run_job, j, template, args.judge, d, key): j for j in jobs}
        for f in as_completed(futs):
            try:
                jid, status, c = f.result()
            except Exception as e:
                jid, status, c = futs[f]["id"], f"error: {e}", 0.0
            total += c; done += 1
            if status not in ("ok", "skip"):
                bad.append((jid, status))
            print(f"[{done}/{len(jobs)}] {jid} {status} ${c:.4f} (total ${total:.2f})", flush=True)
    print(f"DONE {done} jobs, {len(bad)} failed, cost ${total:.2f}", flush=True)
    for b in bad:
        print("FAILED", *b, flush=True)
