"""Memory probes: do the Claude models remember the test material? (Supplementary Fig. 3)

Two probes, both run as fresh, isolated Claude Code CLI sessions:
  - recall (no manuscript): name the three test papers of the original inserted-error study and list its 14 errors and
    how they appeared in each paper (prompts/probe_recall_prompt.txt; tool: Write only);
  - recognition (one manuscript shown): does the model recognize the text, where was it published, and does it recall
    an error list or answer key (prompts/probe_recognition_prompt.txt; tools: Read and Write).
Recognition is run on the three original test papers and on the error-inserted versions of the three 2026 trials,
i.e. the same texts the models reviewed. Each of the five models therefore completes 1 recall and 6 recognition probes
(5 recall and 30 recognition probes in total).

Isolation, as in the review sessions (code/run_claude_reviews.py), plus an empty home folder:
  - every probe gets its own new, neutral folder that holds only manuscript.md (recognition) and the answer;
  - the session starts from a minimal environment and an empty HOME, so no user settings, CLAUDE.md or stored
    memory can be read; no settings files, auto-memory off, no MCP servers, no session persistence;
  - reasoning effort max; the tool calls of every session are listed in the manifest (expected: Read, Write).
A context check (--context-check) records what a session with exactly these settings can see.

The test manuscripts are not distributed (licences of the source articles). Place them at the paths in MANUSCRIPTS.
The answers, full session transcripts, manifests and the coding of every answer are in Supplementary Data 1
(data_original/memory_probes/ and data/memory_probes/). The coding rules are in prompts/probe_coding_rules.md.

Usage (from the repository root, with the Claude Code CLI installed; the CLI must be able to authenticate with an
empty home folder, for example through ANTHROPIC_API_KEY):
  python3 code/run_memory_probes.py --context-check
  python3 code/run_memory_probes.py                       # all 35 probes; re-running skips finished ones
Outputs: <workdir>/{original,2026}/<id>.md (answer), .../logs/<id>.jsonl (stream-json transcript),
         .../manifest.json (model, paper, run time and tool audit per probe)
"""
import argparse, json, os, shutil, subprocess, tempfile, time
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_WORKDIR = os.environ.get("CLAUDE_JOBS_DIR", os.path.join(ROOT, "_claude_cli_runs", "memory_probes"))
# Neutral folder in which each probe session runs (its path is visible to the model, so keep it bland)
DEFAULT_SESSION_ROOT = os.environ.get("CLAUDE_SESSION_ROOT", "/work/ms_review_jobs")

MODELS = {   # key -> model id, as in the reviews
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-5",
    "opus": "claude-opus-5",
    "fable": "claude-fable-5",
    "opus55": "claude-opus-5-5",
}
MANUSCRIPTS = {   # set -> paper -> error-inserted manuscript (not distributed)
    "original": {"1": "data_original/manuscripts/original_paper1.md",
                 "2": "data_original/manuscripts/original_paper2.md",
                 "3": "data_original/manuscripts/original_paper3.md"},
    "2026": {"N": "data/manuscripts/N_errors.md",      # stroke trial
             "I": "data/manuscripts/I_errors.md",      # psoriatic arthritis trial
             "M": "data/manuscripts/M_errors.md"},     # heart-failure trial
}
RECOGNITION = open(os.path.join(ROOT, "prompts", "probe_recognition_prompt.txt")).read()
RECALL = open(os.path.join(ROOT, "prompts", "probe_recall_prompt.txt")).read()

# Only these variables are passed to the child session (everything else from the host session is dropped).
# ANTHROPIC_API_KEY / ANTHROPIC_BASE_URL let the CLI authenticate although HOME is empty.
KEEP_ENV = ["PATH", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "NO_PROXY", "no_proxy",
            "NODE_EXTRA_CA_CERTS", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE",
            "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"]


def clean_env(home):
    env = {k: os.environ[k] for k in KEEP_ENV if k in os.environ}
    env.update({"HOME": home, "TERM": "dumb", "LANG": "C.UTF-8", "TZ": "UTC", "DISABLE_AUTOUPDATER": "1"})
    return env


def claude_cmd(model, prompt, tools):
    return ["claude", "-p", prompt, "--model", model, "--effort", "max",
            "--tools", tools, "--allowedTools", tools, "--permission-mode", "acceptEdits",
            "--setting-sources", "", "--settings", json.dumps({"autoMemoryEnabled": False}),
            "--strict-mcp-config", "--no-session-persistence",
            "--output-format", "stream-json", "--verbose"]


def tool_audit(stream_text):
    """Names of the tools a session called, in order (from the stream-json transcript)."""
    calls = []
    for line in stream_text.splitlines():
        if line.startswith("{"):
            ev = json.loads(line)
            if ev.get("type") == "assistant":
                calls += [c.get("name") for c in ev.get("message", {}).get("content", []) if c.get("type") == "tool_use"]
    return calls


def run_one(job, workdir, session_root):
    """Run one probe in a new folder with an empty home; copy the answer and transcript to workdir."""
    out_dir = os.path.join(workdir, job["set"])
    out = os.path.join(out_dir, job["id"] + ".md")
    if os.path.exists(out) and os.path.getsize(out) > 200:
        return job["id"], "skipped (exists)", None
    # folder names as recorded (job_opus_recall, job_opus_o1 for original paper 1, job_opus_N for the stroke trial);
    # they say nothing about the study
    tag = job["paper"] if job["set"] == "2026" or job["probe"] == "recall" else "o" + job["paper"]
    sdir = os.path.join(session_root, f"job_{job['model']}_{tag}")
    shutil.rmtree(sdir, ignore_errors=True); os.makedirs(sdir)
    ans = os.path.join(sdir, "answer.md")
    if job["probe"] == "recall":
        prompt, tools = RECALL.replace("{OUT_PATH}", ans), "Write"
    else:
        ms = os.path.join(sdir, "manuscript.md")
        shutil.copyfile(os.path.join(ROOT, MANUSCRIPTS[job["set"]][job["paper"]]), ms)
        prompt, tools = RECOGNITION.replace("{MS_PATH}", ms).replace("{OUT_PATH}", ans), "Read,Write"
    home = tempfile.mkdtemp(prefix="probe_home_")          # empty: no user settings, CLAUDE.md or memory
    t0 = time.time()
    p = subprocess.run(claude_cmd(MODELS[job["model"]], prompt, tools), cwd=sdir, env=clean_env(home),
                       stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=3600)
    shutil.rmtree(home, ignore_errors=True)
    open(os.path.join(out_dir, "logs", job["id"] + ".jsonl"), "w").write(p.stdout)
    calls = tool_audit(p.stdout)
    info = dict(job, model_id=MODELS[job["model"]], rc=p.returncode, seconds=round(time.time() - t0),
                tool_calls=calls, tools_clean=set(calls) <= set(tools.split(",")))
    if os.path.exists(ans) and os.path.getsize(ans) > 200:
        shutil.copyfile(ans, out)
        return job["id"], f"ok (tools {calls})", info
    return job["id"], f"NO OUTPUT rc={p.returncode} {p.stderr[-300:]}", info


def context_check(model_key, workdir, session_root):
    """Ask a session with exactly these settings to list everything in its context beyond the question."""
    sdir = os.path.join(session_root, "context_check"); os.makedirs(sdir, exist_ok=True)
    q = ("Without using any tools, list verbatim every instruction, note, memory or project description you can see in "
         "your context that is not part of this message.")
    home = tempfile.mkdtemp(prefix="probe_home_")
    p = subprocess.run(claude_cmd(MODELS[model_key], q, "Read,Write"), cwd=sdir, env=clean_env(home),
                       stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=1800)
    shutil.rmtree(home, ignore_errors=True)
    open(os.path.join(workdir, f"context_check_{model_key}.jsonl"), "w").write(p.stdout)
    res = [json.loads(l) for l in p.stdout.splitlines() if l.startswith("{") and '"result"' in l]
    print((res[-1].get("result") if res else "") or "(no answer)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--context-check", action="store_true")
    ap.add_argument("--models", nargs="*", default=list(MODELS))
    ap.add_argument("--workdir", default=DEFAULT_WORKDIR)
    ap.add_argument("--session-root", default=DEFAULT_SESSION_ROOT)
    ap.add_argument("--concurrency", type=int, default=5)
    a = ap.parse_args()
    for s in MANUSCRIPTS:
        os.makedirs(os.path.join(a.workdir, s, "logs"), exist_ok=True)
    if a.context_check:
        for k in a.models:
            print(f"=== {k}"); context_check(k, a.workdir, a.session_root)
        raise SystemExit

    # one recall probe per model (original set only) and one recognition probe per model and manuscript
    jobs = [{"id": f"recall_{k}", "model": k, "set": "original", "paper": "recall", "probe": "recall"} for k in a.models]
    jobs += [{"id": f"recog_{k}_p{p}", "model": k, "set": s, "paper": p, "probe": "recognition"}
             for k in a.models for s in MANUSCRIPTS for p in MANUSCRIPTS[s]]
    manifests = {}
    for s in MANUSCRIPTS:
        path = os.path.join(a.workdir, s, "manifest.json")
        manifests[s] = json.load(open(path)) if os.path.exists(path) else {}
    with ThreadPoolExecutor(a.concurrency) as ex:
        futs = {ex.submit(run_one, j, a.workdir, a.session_root): j for j in jobs}
        for f in as_completed(futs):
            pid, status, info = f.result()
            if info:
                manifests[info["set"]][pid] = info
                json.dump(manifests[info["set"]], open(os.path.join(a.workdir, info["set"], "manifest.json"), "w"),
                          indent=1)
            print(pid, status, flush=True)
