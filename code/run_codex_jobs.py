"""Run the blind reviews with OpenAI models through the Codex CLI (non-interactive `codex exec`).

Same protocol as the Claude runs: one fresh session per review, the BMJ-style reviewer prompt, the manuscript under a
neutral name in an otherwise empty working folder, output written to a file, no web/network (sandbox), no other files.
Differences that are unavoidable: Codex uses shell commands (cat / file write) instead of Read/Write tools, and its own
default system prompt (a coding-agent persona). `--ignore-user-config` keeps plugins, hooks and marketplaces of the desktop
app out of the session; `--ephemeral` persists nothing; `--ignore-rules` disables local exec policies.

Usage (from the repo root):
  python code/run_codex_jobs.py --exp 1 --models gpt-5.5:xhigh gpt-5.4:xhigh gpt-5.4-mini:high --reps 4 --concurrency 3
  python code/run_codex_jobs.py --exp 2 --models ... --reps 4 --controls --concurrency 3
  add --dry-run to only build the job folder and manifest.
Outputs go to <workdir>/exp{N}/out/<id>.md, event logs to <workdir>/exp{N}/logs/<id>.jsonl, manifest to <workdir>/exp{N}/manifest.json.
The workdir defaults to a neutral folder in the session scratchpad; pass --workdir to change it.
Re-running skips jobs whose output file exists (resume-safe).
--inline: put the manuscript text inside the prompt (sent via stdin) instead of a file the model has to cat. Needed for
manuscripts longer than about 10,000 tokens, because the Codex shell tool truncates command output at 10,000 tokens
(head and tail shown, middle omitted, with a warning). Experiment 2 was run this way; Experiment 1 files are shorter.
"""
import argparse, json, os, random, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODEX = os.environ.get("CODEX_BIN", "/Applications/Codex.app/Contents/Resources/codex")
DEFAULT_WORKDIR = os.environ.get("CODEX_JOBS_DIR", "/private/tmp/claude-501/-Users-rus-Library-CloudStorage-Dropbox-11-Claude-MiniProjects/3c672df1-92b4-4bf5-beb7-9cd60cdb83a9/scratchpad/rj")

NOTES = {
    1: "this is a text-only version converted from a PDF. Tables, the flow diagram and the reference list are included as plain text; there are no other figures.",
    2: "this is a text-only version. The reference list and citation markers have been omitted for length. Tables are included in the text; figures and supplementary material are not included (figure legends are).",
}
SOURCES = {  # experiment -> paper number -> manuscript file (error-seeded), and clean controls for experiment 2
    1: {1: "data_original/manuscripts/original_paper1.md", 2: "data_original/manuscripts/original_paper2.md", 3: "data_original/manuscripts/original_paper3.md"},
    2: {1: "data/manuscripts/N_errors.md", 2: "data/manuscripts/I_errors.md", 3: "data/manuscripts/M_errors.md"},
}
CLEAN2 = {1: "data/manuscripts/N_clean.md", 2: "data/manuscripts/I_clean.md", 3: "data/manuscripts/M_clean.md"}
PREFIX = {1: "goreview", 2: "greview"}

def build_jobs(exp, models, reps, controls, workdir, seed=11):
    d = os.path.join(workdir, f"exp{exp}")
    for sub in ("inbox", "out", "logs"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    for p, src in SOURCES[exp].items():
        shutil.copyfile(os.path.join(ROOT, src), os.path.join(d, "inbox", f"manuscript_{p}.md"))
    if exp == 2 and controls:
        for p, src in CLEAN2.items():
            shutil.copyfile(os.path.join(ROOT, src), os.path.join(d, "inbox", f"clean_{p}.md"))
    mpath = os.path.join(d, "manifest.json")
    if os.path.exists(mpath):
        return d, json.load(open(mpath))
    jobs = []
    for m, eff in models:
        for p in (1, 2, 3):
            for r in range(1, reps + 1):
                jobs.append({"paper": p, "model": m, "effort": eff, "rep": r, "kind": "review"})
            if exp == 2 and controls:
                jobs.append({"paper": p, "model": m, "effort": eff, "rep": 1, "kind": "control"})
    random.Random(seed).shuffle(jobs)
    n_rev = n_ctl = 0
    for j in jobs:
        if j["kind"] == "review":
            n_rev += 1; j["id"] = f"{PREFIX[exp]}_{n_rev:03d}"
        else:
            n_ctl += 1; j["id"] = f"gcontrol_{n_ctl:02d}"
    json.dump(jobs, open(mpath, "w"), indent=1)
    return d, jobs

def run_job(d, job, exp, template, inline=False):
    ms = os.path.join(d, "inbox", ("manuscript" if job["kind"] == "review" else "clean") + f"_{job['paper']}.md")
    out = os.path.join(d, "out", job["id"] + ".md")
    last = os.path.join(d, "out", job["id"] + ".last_message.txt")
    log = os.path.join(d, "logs", job["id"] + ".jsonl")
    if os.path.exists(out) and os.path.getsize(out) > 500:
        return job["id"], "skipped (exists)", 0
    if inline:
        prompt = template.replace("{OUT_PATH}", out).replace("{NOTES}", NOTES[exp]).replace("{MANUSCRIPT}", open(ms).read().rstrip("\n"))
    else:
        prompt = template.replace("{MS_PATH}", ms).replace("{OUT_PATH}", out).replace("{NOTES}", NOTES[exp])
    cmd = [CODEX, "exec", "--ignore-user-config", "--ignore-rules", "--ephemeral", "--skip-git-repo-check",
           "-s", "workspace-write", "-C", d, "-m", job["model"],
           "-c", f'model_reasoning_effort="{job["effort"]}"', "-c", 'web_search="disabled"',
           "--json", "-o", last, "-"]                      # prompt via stdin (long manuscripts)
    t0 = time.time()
    with open(log, "w") as lf:
        proc = subprocess.run(cmd, input=prompt, stdout=lf, stderr=subprocess.PIPE, text=True, cwd=d)
    dt = time.time() - t0
    status = "ok" if os.path.exists(out) and os.path.getsize(out) > 500 else f"NO OUTPUT (rc={proc.returncode}) {proc.stderr[-300:]}"
    if status != "ok" and os.path.exists(last) and os.path.getsize(last) > 500:
        shutil.copyfile(last, out); status = "ok (from last message)"
    return job["id"], status, dt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", type=int, required=True, choices=(1, 2))
    ap.add_argument("--models", nargs="+", required=True, help="model:effort, e.g. gpt-5.5:xhigh")
    ap.add_argument("--reps", type=int, default=4)
    ap.add_argument("--controls", action="store_true", help="also review the clean manuscripts once per model (experiment 2)")
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--workdir", default=DEFAULT_WORKDIR)
    ap.add_argument("--only", nargs="*", help="run only these job ids")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--inline", action="store_true", help="manuscript text inside the prompt (see module docstring)")
    a = ap.parse_args()
    models = [tuple(m.split(":")) if ":" in m else (m, "high") for m in a.models]
    d, jobs = build_jobs(a.exp, models, a.reps, a.controls, a.workdir)
    template = open(os.path.join(ROOT, "prompts", "reviewer_prompt_codex_inline.txt" if a.inline else "reviewer_prompt_codex.txt")).read()
    todo = [j for j in jobs if (not a.only or j["id"] in a.only)]
    print(f"{len(todo)} jobs in {d}; models {models}; dry-run={a.dry_run}")
    if a.dry_run:
        return
    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        futs = {ex.submit(run_job, d, j, a.exp, template, a.inline): j for j in todo}
        for f in as_completed(futs):
            jid, status, dt = f.result()
            print(f"{time.strftime('%H:%M:%S')} {jid} {futs[f]['model']} p{futs[f]['paper']} {status} {dt/60:.1f} min", flush=True)

if __name__ == "__main__":
    main()
