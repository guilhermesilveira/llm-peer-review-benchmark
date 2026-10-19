"""Run the blind reviews with open-weight models through an OpenAI-compatible chat API (OpenRouter by default).

Same protocol as the Claude Code and Codex runs: one fresh, independent request per review, the BMJ-style reviewer
instructions, the manuscript under a neutral name, no tools of any kind (the API call has none, so the tool audit is
clean by construction), reasoning mode at its highest setting. The manuscript is placed inside the prompt, exactly as
in the Experiment 2 Codex runs (prompts/reviewer_prompt_api_inline.txt differs from reviewer_prompt_codex_inline.txt
only in asking for the review as the reply instead of as a file).

Usage (from the repo root; needs OPENROUTER_API_KEY in the environment or in a .env file at the repo root):
  python3 code/run_open_models.py --exp 1 --models kimik3 dsv4pro gptoss120b qwen38_27b --reps 4 --concurrency 4
  python3 code/run_open_models.py --exp 2 --models ... --reps 4 --controls --concurrency 4
  python3 code/run_open_models.py --integrate --exp 1     (copy reviews into data_original/, extend the manifest)
  python3 code/run_open_models.py --integrate --exp 2     (data/ and data/controls/, both manifests)
Outputs: <workdir>/exp{N}/out/<id>.md (review text), <workdir>/exp{N}/logs/<id>.json (full API response incl. usage
and, when the provider returns it, the reasoning trace), <workdir>/exp{N}/manifest.json. Re-running skips finished jobs.
"""
import argparse, json, os, random, shutil, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_WORKDIR = os.environ.get("OPEN_JOBS_DIR", os.path.join(ROOT, "_open_model_runs"))
API_URL = os.environ.get("OPEN_API_URL", "https://openrouter.ai/api/v1/chat/completions")

# manifest key -> (provider model id, reasoning effort, label)
MODELS = {
    "kimik3":     ("moonshotai/kimi-k3",           "high", "Kimi K3"),
    "dsv4pro":    ("deepseek/deepseek-v4-pro-0813", "high", "DeepSeek V4 Pro"),
    "glm53":      ("z-ai/glm-5.3",                 "high", "GLM-5.3"),
    "gptoss120b": ("openai/gpt-oss-120b",          "high", "gpt-oss-120b"),
    "qwen38_27b": ("qwen/qwen3.8-27b",             "high", "Qwen3.8-27B"),
    # Added 2026-09-30: newest closed models reachable through OpenRouter.
    # OpenAI models use "xhigh", the same effort as the earlier GPT-5.x runs in Codex.
    "gpt61sol":   ("openai/gpt-6.1-sol",           "xhigh", "GPT-6.1 Sol"),
    "gpt6luna":   ("openai/gpt-6-luna",            "xhigh", "GPT-6 Luna"),
    "gemini38fl": ("google/gemini-3.8-flash",      "high", "Gemini 3.8 Flash"),
}
# Provider routing. OpenRouter otherwise sends each request to the cheapest host, which for open-weight models is
# often a third-party, lower-precision (e.g. 4-bit) copy. Pin each open model to its developer's own endpoint (or a
# fixed full-precision host) so that every review of a model comes from the same weights; no fallback to other hosts.
DEFAULT_PROVIDER = {"allow_fallbacks": True}
PROVIDERS = {
    "kimik3":     {"order": ["moonshotai"], "allow_fallbacks": False},
    # DeepSeek's own endpoint is excluded by the account's no-training-on-prompts setting; FP8 is the model's
    # native precision, so use a fixed FP8 host instead
    "dsv4pro":    {"order": ["baidu"], "quantizations": ["fp8"], "allow_fallbacks": False},
    "qwen38_27b": {"order": ["alibaba"], "allow_fallbacks": False},
    "gptoss120b": {"order": ["deepinfra"], "quantizations": ["bf16"], "allow_fallbacks": False},
    "gpt61sol":   {"order": ["openai"], "allow_fallbacks": False},
    "gpt6luna":   {"order": ["openai"], "allow_fallbacks": False},
}
NOTES = {
    1: "this is a text-only version converted from a PDF. Tables, the flow diagram and the reference list are included as plain text; there are no other figures.",
    2: "this is a text-only version. The reference list and citation markers have been omitted for length. Tables are included in the text; figures and supplementary material are not included (figure legends are).",
}
SOURCES = {
    1: {1: "data_original/manuscripts/original_paper1.md", 2: "data_original/manuscripts/original_paper2.md", 3: "data_original/manuscripts/original_paper3.md"},
    2: {1: "data/manuscripts/N_errors.md", 2: "data/manuscripts/I_errors.md", 3: "data/manuscripts/M_errors.md"},
}
CLEAN2 = {1: "data/manuscripts/N_clean.md", 2: "data/manuscripts/I_clean.md", 3: "data/manuscripts/M_clean.md"}
PREFIX = {1: "woreview", 2: "wreview"}      # w = open-weight; mirrors oreview/review and goreview/greview
CTL_PREFIX = "wcontrol"


def load_key():
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"]
    env = os.path.join(ROOT, ".env")
    if os.path.exists(env):
        for line in open(env):
            line = line.strip()
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("OPENROUTER_API_KEY not found (environment or .env at the repo root)")


def build_jobs(exp, models, reps, controls, workdir, seed=23):
    d = os.path.join(workdir, f"exp{exp}")
    for sub in ("inbox", "out", "logs"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    for p, src in SOURCES[exp].items():
        shutil.copyfile(os.path.join(ROOT, src), os.path.join(d, "inbox", f"manuscript_{p}.md"))
    if exp == 2 and controls:
        for p, src in CLEAN2.items():
            shutil.copyfile(os.path.join(ROOT, src), os.path.join(d, "inbox", f"clean_{p}.md"))
    mpath = os.path.join(d, "manifest.json")
    jobs = json.load(open(mpath)) if os.path.exists(mpath) else []
    have = {(j["model"], j["paper"], j["rep"], j["kind"]) for j in jobs}
    new = []
    for m in models:
        for p in (1, 2, 3):
            for r in range(1, reps + 1):
                if (m, p, r, "review") not in have:
                    new.append({"paper": p, "model": m, "rep": r, "kind": "review"})
            if exp == 2 and controls and (m, p, 1, "control") not in have:
                new.append({"paper": p, "model": m, "rep": 1, "kind": "control"})
    random.Random(seed + len(jobs)).shuffle(new)
    n_rev = sum(1 for j in jobs if j["kind"] == "review"); n_ctl = sum(1 for j in jobs if j["kind"] == "control")
    for j in new:
        if j["kind"] == "review":
            n_rev += 1; j["id"] = f"{PREFIX[exp]}_{n_rev:03d}"
        else:
            n_ctl += 1; j["id"] = f"{CTL_PREFIX}_{n_ctl:02d}"
        j["model_id"], j["effort"], _ = MODELS[j["model"]]
    jobs += new
    json.dump(jobs, open(mpath, "w"), indent=1)
    return d, jobs


def call_api(key, model_id, effort, prompt, provider=None, max_tokens=64000, tries=4):
    # max_tokens covers reasoning + review; 64k leaves room for long reasoning at the highest effort
    body = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "reasoning": {"effort": effort},
        "provider": provider or DEFAULT_PROVIDER,
        "usage": {"include": True},          # ask OpenRouter to report the cost of each call
    }
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode(), method="POST", headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/ruslanrust", "X-Title": "inserted-error replication"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=1800) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:500]
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                time.sleep(20 * (attempt + 1)); continue
            raise RuntimeError(f"HTTP {e.code}: {msg}")
        except Exception as e:                       # timeouts, resets
            if attempt < tries - 1:
                time.sleep(20 * (attempt + 1)); continue
            raise


def run_job(d, job, exp, template, key):
    ms = os.path.join(d, "inbox", ("manuscript" if job["kind"] == "review" else "clean") + f"_{job['paper']}.md")
    out = os.path.join(d, "out", job["id"] + ".md")
    log = os.path.join(d, "logs", job["id"] + ".json")
    if os.path.exists(out) and os.path.getsize(out) > 500:
        return job["id"], "skipped (exists)", 0
    prompt = template.replace("{NOTES}", NOTES[exp]).replace("{MANUSCRIPT}", open(ms).read().rstrip("\n"))
    t0 = time.time()
    # Rate limits and provider hiccups can come back as HTTP 200 with an error inside the body; retry those
    # a few times. Failed attempts are kept as <id>.attempt<k>.json for the audit trail.
    for attempt in range(1, 5):
        try:
            resp = call_api(key, job["model_id"], job["effort"], prompt, provider=PROVIDERS.get(job["model"]))
        except Exception as e:
            return job["id"], f"FAILED {e}", time.time() - t0
        text = (resp.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        finish = (resp.get("choices") or [{}])[0].get("finish_reason")
        if finish == "stop" and len(text.strip()) >= 500:
            break
        json.dump(resp, open(log.replace(".json", f".attempt{attempt}.json"), "w"), indent=1)
        time.sleep(30 * attempt)
    json.dump(resp, open(log, "w"), indent=1)
    # keep only reviews that finished normally: a stream that ended in an error can hold a truncated review
    if finish != "stop" or len(text.strip()) < 500:
        return job["id"], f"NO OUTPUT (finish={finish}, {len(text)} chars)", time.time() - t0
    open(out, "w").write(text.strip() + "\n")
    return job["id"], f"ok (finish={finish}, {resp.get('usage', {}).get('completion_tokens', '?')} out tokens)", time.time() - t0


def integrate(exp, workdir):
    d = os.path.join(workdir, f"exp{exp}")
    jobs = json.load(open(os.path.join(d, "manifest.json")))
    if exp == 1:
        dest_rev = os.path.join(ROOT, "data_original", "reviews"); man_path = os.path.join(ROOT, "data_original", "manifest.json")
        dest_ctl = cman_path = None; audit_path = os.path.join(ROOT, "data_original", "open_model_api_audit.json")
    else:
        dest_rev = os.path.join(ROOT, "data", "reviews"); man_path = os.path.join(ROOT, "data", "manifest.json")
        dest_ctl = os.path.join(ROOT, "data", "controls", "reviews"); cman_path = os.path.join(ROOT, "data", "control_manifest.json")
        audit_path = os.path.join(ROOT, "data", "open_model_api_audit.json")
    manifest = json.load(open(man_path)); have = {j["id"] for j in manifest}
    cmanifest = json.load(open(cman_path)) if cman_path else None; chave = {j["id"] for j in cmanifest} if cmanifest else set()
    audit = json.load(open(audit_path)) if os.path.exists(audit_path) else {}
    n_ok = n_missing = 0
    for j in jobs:
        src = os.path.join(d, "out", j["id"] + ".md")
        if not (os.path.exists(src) and os.path.getsize(src) > 500):
            n_missing += 1; continue
        n_ok += 1
        resp = json.load(open(os.path.join(d, "logs", j["id"] + ".json")))
        ch = (resp.get("choices") or [{}])[0]
        entry = {"paper": j["paper"], "model": j["model"], "rep": j["rep"], "id": j["id"], "harness": "api_inline",
                 "provider": "openrouter", "model_id": j["model_id"], "effort": j["effort"]}
        if j["kind"] == "review":
            shutil.copyfile(src, os.path.join(dest_rev, j["id"] + ".md"))
            if j["id"] not in have: manifest.append(entry); have.add(j["id"])
        else:
            shutil.copyfile(src, os.path.join(dest_ctl, j["id"] + ".md"))
            e2 = {k: entry[k] for k in ("id", "paper", "model", "harness", "provider", "model_id", "effort")}
            if j["id"] not in chave: cmanifest.append(e2); chave.add(j["id"])
        audit[j["id"]] = {"tool_use_clean": True, "tools_available": False, "finish_reason": ch.get("finish_reason"),
                          "usage": resp.get("usage"), "served_by": resp.get("provider"),
                          "reasoning_returned": bool(ch.get("message", {}).get("reasoning")),
                          "context_reference": None}
    json.dump(manifest, open(man_path, "w"), indent=1)
    if cmanifest is not None: json.dump(cmanifest, open(cman_path, "w"), indent=1)
    json.dump(audit, open(audit_path, "w"), indent=1)
    print(f"exp {exp}: {n_ok} reviews integrated, {n_missing} missing; audit entries: {len(audit)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", type=int, required=True, choices=(1, 2))
    ap.add_argument("--models", nargs="+", default=list(MODELS), help="manifest keys: " + " ".join(MODELS))
    ap.add_argument("--reps", type=int, default=4)
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--workdir", default=DEFAULT_WORKDIR)
    ap.add_argument("--integrate", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    # optional filters, e.g. a pilot of one review per model: --paper 3 --rep 1 --kind review
    ap.add_argument("--paper", type=int, help="only run jobs for this paper (1-3)")
    ap.add_argument("--rep", type=int, help="only run jobs with this replicate number")
    ap.add_argument("--kind", choices=("review", "control"), help="only run reviews or only controls")
    a = ap.parse_args()
    if a.integrate:
        integrate(a.exp, a.workdir); return
    for m in a.models:
        if m not in MODELS: sys.exit(f"unknown model key {m}; known: {list(MODELS)}")
    d, jobs = build_jobs(a.exp, a.models, a.reps, a.controls, a.workdir)
    template = open(os.path.join(ROOT, "prompts", "reviewer_prompt_api_inline.txt")).read()
    todo = [j for j in jobs if j["model"] in a.models
            and (a.paper is None or j["paper"] == a.paper)
            and (a.rep is None or j["rep"] == a.rep)
            and (a.kind is None or j["kind"] == a.kind)]
    print(f"{len(todo)} jobs in {d}; models {a.models}; dry-run={a.dry_run}", flush=True)
    if a.dry_run: return
    key = load_key()
    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        futs = {ex.submit(run_job, d, j, a.exp, template, key): j for j in todo}
        for f in as_completed(futs):
            jid, status, dt = f.result()
            print(f"{time.strftime('%H:%M:%S')} {jid} {futs[f]['model']} p{futs[f]['paper']} {status} {dt/60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
