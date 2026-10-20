"""Run blind reviews with a Claude model as fresh, independent Claude Code CLI sessions (one session per review).

This follows Option A of CLEAN_RERUN_INSTRUCTIONS.md, so no project note can reach the reviewer:
  - every review gets its own new, neutral folder containing only manuscript.md (and, afterwards, review.md);
  - the session starts from a minimal environment (only PATH, HOME, proxy and certificate variables), so no
    host-session, project or account variables are passed on;
  - no settings files, no CLAUDE.md, auto-memory switched off, no MCP servers, no session persistence;
  - tools limited to Read and Write; reasoning effort max;
  - the prompt is the same reviewer template as the earlier Claude runs (prompts/reviewer_prompt_original.txt for the
    original test papers, prompts/reviewer_prompt.txt for the 2026 trials and their clean versions).
A context probe (--probe) records what a session with exactly these settings can see, as evidence for the audit.

Usage (from the repo root, with the Claude Code CLI installed and logged in):
  python3 code/run_claude_reviews.py --probe
  python3 code/run_claude_reviews.py --exp 1 --model claude-opus-5-5 --key opus55 --reps 4 --concurrency 4
  python3 code/run_claude_reviews.py --exp 2 --model claude-opus-5-5 --key opus55 --reps 4 --controls --concurrency 4
Outputs: <workdir>/exp{N}/out/<id>.md (review), <workdir>/exp{N}/logs/<id>.jsonl (full stream-json transcript incl.
tool calls and usage), <workdir>/exp{N}/manifest.json with a per-session tool audit. Re-running skips finished jobs.
"""
import argparse, json, os, random, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_WORKDIR = os.environ.get("CLAUDE_JOBS_DIR", os.path.join(ROOT, "_claude_cli_runs"))
# Neutral folder in which each review session runs (its path is visible to the reviewer, so keep it bland)
DEFAULT_SESSION_ROOT = os.environ.get("CLAUDE_SESSION_ROOT", "/work/ms_review_jobs")

SOURCES = {
    1: {1: "data_original/manuscripts/original_paper1.md", 2: "data_original/manuscripts/original_paper2.md", 3: "data_original/manuscripts/original_paper3.md"},
    2: {1: "data/manuscripts/N_errors.md", 2: "data/manuscripts/I_errors.md", 3: "data/manuscripts/M_errors.md"},
}
CLEAN2 = {1: "data/manuscripts/N_clean.md", 2: "data/manuscripts/I_clean.md", 3: "data/manuscripts/M_clean.md"}
TEMPLATES = {1: "prompts/reviewer_prompt_original.txt", 2: "prompts/reviewer_prompt.txt"}
PREFIX = {1: "xoreview", 2: "xreview"}          # x = fresh-session Claude Code CLI run
CTL_PREFIX = "xcontrol"

# Only these variables are passed to the child session (everything else from the host session is dropped)
KEEP_ENV = ["HOME", "PATH", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "NO_PROXY", "no_proxy",
            "NODE_EXTRA_CA_CERTS", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "NODE_OPTIONS"]


def clean_env():
    env = {k: os.environ[k] for k in KEEP_ENV if k in os.environ}
    env.update({"TERM": "dumb", "LANG": "C.UTF-8", "TZ": "UTC", "DISABLE_AUTOUPDATER": "1"})
    return env


def claude_cmd(model, effort, prompt, tools="Read,Write"):
    return ["claude", "-p", prompt, "--model", model, "--effort", effort,
            "--tools", tools, "--allowedTools", tools, "--permission-mode", "acceptEdits",
            "--setting-sources", "", "--settings", json.dumps({"autoMemoryEnabled": False}),
            "--strict-mcp-config", "--no-session-persistence",
            "--output-format", "stream-json", "--verbose"]


def build_jobs(exp, key, model, reps, controls, workdir, seed=55):
    d = os.path.join(workdir, f"exp{exp}")
    for sub in ("out", "logs"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    mpath = os.path.join(d, "manifest.json")
    jobs = json.load(open(mpath)) if os.path.exists(mpath) else []
    have = {(j["model"], j["paper"], j["rep"], j["kind"]) for j in jobs}
    new = []
    for p in (1, 2, 3):
        for r in range(1, reps + 1):
            if (key, p, r, "review") not in have:
                new.append({"paper": p, "model": key, "rep": r, "kind": "review"})
        if exp == 2 and controls and (key, p, 1, "control") not in have:
            new.append({"paper": p, "model": key, "rep": 1, "kind": "control"})
    random.Random(seed + len(jobs)).shuffle(new)
    n_rev = sum(1 for j in jobs if j["kind"] == "review"); n_ctl = sum(1 for j in jobs if j["kind"] == "control")
    for j in new:
        if j["kind"] == "review":
            n_rev += 1; j["id"] = f"{PREFIX[exp]}_{n_rev:03d}"
        else:
            n_ctl += 1; j["id"] = f"{CTL_PREFIX}_{n_ctl:02d}"
        j["model_id"] = model; j["effort"] = "max"; j["harness"] = "claude_code_cli_fresh"
    jobs += new
    json.dump(jobs, open(mpath, "w"), indent=1)
    return d, jobs


def audit_transcript(lines, ms_path, out_path):
    """Return (tool calls, clean?, final result record) from a stream-json transcript."""
    calls, result = [], None
    for ln in lines:
        try:
            ev = json.loads(ln)
        except ValueError:
            continue
        if ev.get("type") == "assistant":
            for c in ev.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    calls.append({"name": c.get("name"), "input": {k: (v if k != "content" else f"<{len(v)} chars>") for k, v in c.get("input", {}).items()}})
        elif ev.get("type") == "result":
            result = ev
    ok_calls = all((c["name"] == "Read" and c["input"].get("file_path") == ms_path) or
                   (c["name"] == "Write" and c["input"].get("file_path") == out_path) for c in calls)
    return calls, ok_calls, result


def run_job(d, job, exp, session_root, timeout_min):
    out = os.path.join(d, "out", job["id"] + ".md")
    log = os.path.join(d, "logs", job["id"] + ".jsonl")
    if os.path.exists(out) and os.path.getsize(out) > 500:
        return job["id"], "skipped (exists)", 0, None
    # fresh neutral folder per session: only the manuscript, under a neutral name
    sdir = os.path.join(session_root, f"s{random.randrange(10**6):06d}")
    while os.path.exists(sdir):
        sdir = os.path.join(session_root, f"s{random.randrange(10**6):06d}")
    os.makedirs(sdir)
    ms_path, out_path = os.path.join(sdir, "manuscript.md"), os.path.join(sdir, "review.md")
    src = SOURCES[exp][job["paper"]] if job["kind"] == "review" else CLEAN2[job["paper"]]
    shutil.copyfile(os.path.join(ROOT, src), ms_path)
    prompt = open(os.path.join(ROOT, TEMPLATES[exp])).read().replace("{MS_PATH}", ms_path).replace("{OUT_PATH}", out_path).rstrip("\n")
    t0 = time.time()
    try:
        p = subprocess.run(claude_cmd(job["model_id"], "max", prompt), cwd=sdir, env=clean_env(), stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=timeout_min * 60)
        stdout, rc = p.stdout, p.returncode
    except subprocess.TimeoutExpired as e:
        stdout, rc = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or ""), "timeout"
    open(log, "w").write(stdout)
    calls, clean, res = audit_transcript(stdout.splitlines(), ms_path, out_path)
    info = {"session_dir": sdir, "returncode": rc, "tool_calls": calls, "tool_use_clean": clean,
            "cost_usd_list": (res or {}).get("total_cost_usd"), "duration_s": round(time.time() - t0),
            "usage": (res or {}).get("usage"), "final_message": ((res or {}).get("result") or "")[:200]}
    if os.path.exists(out_path) and os.path.getsize(out_path) > 500:
        shutil.copyfile(out_path, out)
        return job["id"], f"ok ({os.path.getsize(out)} bytes, ${info['cost_usd_list'] or 0:.2f}, tools clean={clean})", time.time() - t0, info
    return job["id"], f"NO OUTPUT (rc={rc})", time.time() - t0, info


def probe(model, session_root, workdir):
    """Record what a session with the review settings can see (no tools used)."""
    sdir = os.path.join(session_root, "probe"); os.makedirs(sdir, exist_ok=True)
    q = ("Without using any tools, list verbatim every instruction, note, memory or project description you can see in "
         "your context that is not part of this message.")
    p = subprocess.run(claude_cmd(model, "max", q), cwd=sdir, env=clean_env(), stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=3600)
    os.makedirs(workdir, exist_ok=True)
    fp = os.path.join(workdir, f"context_probe_{model}.jsonl"); open(fp, "w").write(p.stdout)
    res = [json.loads(l) for l in p.stdout.splitlines() if l.startswith("{") and '"type":"result"' in l.replace(" ", "")]
    text = (res[-1].get("result") if res else "") or ""
    flags = [w for w in ("peer review", "Schroter", "BMJ", "inserted", "error", "P1_", "Dropbox", "project") if w.lower() in text.lower()]
    print(f"probe written to {fp}; {len(text)} chars; words found: {flags or 'none'}")
    return text


def integrate(exp, workdir):
    """Copy finished reviews into data_original/ (exp 1) or data/ (exp 2), extend the manifests, save the audit."""
    d = os.path.join(workdir, f"exp{exp}")
    jobs = json.load(open(os.path.join(d, "manifest.json")))
    base = os.path.join(ROOT, "data_original" if exp == 1 else "data")
    man_path = os.path.join(base, "manifest.json"); manifest = json.load(open(man_path)); have = {j["id"] for j in manifest}
    cman_path = os.path.join(base, "control_manifest.json") if exp == 2 else None
    cmanifest = json.load(open(cman_path)) if cman_path else None; chave = {j["id"] for j in cmanifest} if cmanifest else set()
    audit_path = os.path.join(base, "claude_cli_audit.json")
    audit = json.load(open(audit_path)) if os.path.exists(audit_path) else {}
    n_ok = n_missing = 0
    for j in jobs:
        src = os.path.join(d, "out", j["id"] + ".md")
        if not (os.path.exists(src) and os.path.getsize(src) > 500):
            n_missing += 1; continue
        n_ok += 1
        entry = {"paper": j["paper"], "model": j["model"], "rep": j["rep"], "id": j["id"], "harness": j["harness"],
                 "model_id": j["model_id"], "effort": j["effort"]}
        if j["kind"] == "review":
            shutil.copyfile(src, os.path.join(base, "reviews", j["id"] + ".md"))
            if j["id"] not in have: manifest.append(entry); have.add(j["id"])
        else:
            shutil.copyfile(src, os.path.join(base, "controls", "reviews", j["id"] + ".md"))
            e2 = {k: entry[k] for k in ("id", "paper", "model", "harness", "model_id", "effort")}
            if j["id"] not in chave: cmanifest.append(e2); chave.add(j["id"])
        a = j.get("audit", {})
        audit[j["id"]] = {"tool_use_clean": a.get("tool_use_clean"), "tool_calls": a.get("tool_calls"),
                          "cost_usd_list": a.get("cost_usd_list"), "duration_s": a.get("duration_s"),
                          "usage": a.get("usage"), "context_reference": None}
    json.dump(manifest, open(man_path, "w"), indent=1)
    if cmanifest is not None: json.dump(cmanifest, open(cman_path, "w"), indent=1)
    json.dump(audit, open(audit_path, "w"), indent=1)
    print(f"exp {exp}: {n_ok} reviews integrated, {n_missing} missing; audit entries: {len(audit)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", type=int, choices=(1, 2))
    ap.add_argument("--model", default="claude-opus-5-5", help="Claude model ID")
    ap.add_argument("--key", default="opus55", help="model key used in the manifests")
    ap.add_argument("--reps", type=int, default=4)
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--timeout-min", type=int, default=45)
    ap.add_argument("--workdir", default=DEFAULT_WORKDIR)
    ap.add_argument("--session-root", default=DEFAULT_SESSION_ROOT)
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--integrate", action="store_true", help="copy finished reviews into data/ or data_original/")
    a = ap.parse_args()
    if a.integrate:
        integrate(a.exp, a.workdir); return
    os.makedirs(a.session_root, exist_ok=True)
    if a.probe:
        probe(a.model, a.session_root, a.workdir); return
    if not a.exp:
        sys.exit("--exp is required")
    d, jobs = build_jobs(a.exp, a.key, a.model, a.reps, a.controls, a.workdir)
    todo = [j for j in jobs if j["model"] == a.key]
    print(f"{len(todo)} jobs in {d}; model {a.model}; dry-run={a.dry_run}", flush=True)
    if a.dry_run:
        return
    mpath = os.path.join(d, "manifest.json")
    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        futs = {ex.submit(run_job, d, j, a.exp, a.session_root, a.timeout_min): j for j in todo}
        for f in as_completed(futs):
            jid, status, dt, info = f.result()
            if info:
                futs[f]["audit"] = info
                json.dump(jobs, open(mpath, "w"), indent=1)       # save audit as each job finishes
            print(f"{time.strftime('%H:%M:%S')} {jid} p{futs[f]['paper']} {futs[f]['kind']} {status} {dt/60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
