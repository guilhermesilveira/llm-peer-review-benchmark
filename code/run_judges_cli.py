"""Run the judge sessions written by make_judge_batches.py in parallel, as fresh Claude Code CLI sessions.

Same judges and instructions as run_judges_claude_cli.sh (J1 = Fable 5, J2 = Opus 5; sessions may only Read and Write).
The instruction text of the batch file is given in the prompt itself: since mid-2026 the one-line prompt "Read <batch file>
and follow it exactly." trips Fable 5's cyber safeguard, and Claude Code then silently continues the session with another
model (claude-opus-4-8). Any session in which such a model fallback occurs is rejected: its outputs are moved to
<judge dir>/rejected_fallback/ and the batch is reported as FALLBACK. Differences: sessions run concurrently, start from a minimal
environment with no settings, memory or MCP servers (as in run_claude_cli.py), and every output is checked to be valid
JSON with the 14 scores in the key's order. Batches whose outputs all exist and are valid are skipped.

Usage:  python3 code/run_judges_cli.py <judge dir> [<judge dir> ...] --concurrency 8
"""
import argparse, glob, json, os, re, subprocess, time
from concurrent.futures import ThreadPoolExecutor, as_completed

MODELS = {"J1": os.environ.get("J1_MODEL", "claude-fable-5"), "J2": os.environ.get("J2_MODEL", "claude-opus-5")}
KEEP_ENV = ["HOME", "PATH", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "NO_PROXY", "no_proxy",
            "NODE_EXTRA_CA_CERTS", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "NODE_OPTIONS"]


def clean_env():
    env = {k: os.environ[k] for k in KEEP_ENV if k in os.environ}
    env.update({"TERM": "dumb", "LANG": "C.UTF-8", "TZ": "UTC", "DISABLE_AUTOUPDATER": "1"})
    return env


def targets(batch_file):
    """(key path, [(review path, output path), ...]) named in a batch instruction file."""
    txt = open(batch_file).read()
    key = re.search(r"Answer key \(JSON[^)]*\): (\S+)", txt).group(1)
    pairs = re.findall(r"- Review \d+: (\S+) -> write scores to (\S+)", txt)
    return key, pairs


def valid(out_path, key_path):
    try:
        d = json.load(open(out_path))
        ids = [e["id"] for e in json.load(open(key_path))["errors"]]
        return [s["id"] for s in d["scores"]] == ids and all(s["score"] in (0, 0.5, 1) for s in d["scores"])
    except Exception:
        return False


def run(batch_file, timeout_min):
    judge = "J1" if batch_file.endswith("_J1.txt") else "J2"
    key, pairs = targets(batch_file)
    if all(valid(o, key) for _, o in pairs):
        return batch_file, "skipped (done)", 0
    t0 = time.time()
    cmd = ["claude", "-p", open(batch_file).read(), "--model", MODELS[judge],
           "--tools", "Read,Write", "--allowedTools", "Read,Write", "--permission-mode", "acceptEdits",
           "--setting-sources", "", "--settings", json.dumps({"autoMemoryEnabled": False}),
           "--strict-mcp-config", "--no-session-persistence", "--max-turns", "30",
           "--output-format", "stream-json", "--verbose"]
    try:
        p = subprocess.run(cmd, cwd=os.path.dirname(batch_file), env=clean_env(), stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=timeout_min * 60)
        out = p.stdout
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
    open(batch_file[:-4] + ".jsonl", "w").write(out)
    fallback = [json.loads(l) for l in out.splitlines() if '"model_refusal_fallback"' in l]
    served = set()
    for l in out.splitlines():
        if l.startswith("{") and '"type":"assistant"' in l.replace(" ", ""):
            served.add(json.loads(l).get("message", {}).get("model"))
    if fallback or (served - {MODELS[judge]}):
        qdir = os.path.join(os.path.dirname(batch_file), "rejected_fallback"); os.makedirs(qdir, exist_ok=True)
        for _, o in pairs:
            if os.path.exists(o):
                os.replace(o, os.path.join(qdir, os.path.basename(o)))
        return batch_file, f"FALLBACK (served by {sorted(x for x in served if x)})", time.time() - t0
    n_ok = sum(valid(o, key) for _, o in pairs)
    return batch_file, f"{n_ok}/{len(pairs)} valid", time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--timeout-min", type=int, default=40)
    a = ap.parse_args()
    files = sorted(f for d in a.dirs for f in glob.glob(os.path.join(d, "batch_*_J[12].txt")))
    print(f"{len(files)} judge sessions", flush=True)
    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        futs = [ex.submit(run, f, a.timeout_min) for f in files]
        for f in as_completed(futs):
            bf, status, dt = f.result()
            print(f"{time.strftime('%H:%M:%S')} {bf} {status} {dt/60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
