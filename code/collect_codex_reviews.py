"""Copy the Codex (OpenAI model) reviews into the data folders, extend the manifests, and build a tool-use audit
from the Codex event logs.

  python code/collect_codex_reviews.py --exp 1   -> data_original/reviews/goreview_XXX.md, data_original/manifest.json (+entries),
                                                  data_original/codex_tool_audit.json
  python code/collect_codex_reviews.py --exp 2   -> data/reviews/greview_XXX.md, data/controls/reviews/gcontrol_XX.md,
                                                  data/manifest.json, data/control_manifest.json, data/codex_tool_audit.json
Model keys used in the manifests: gpt-5.5 -> gpt55, gpt-5.4 -> gpt54, gpt-5.4-mini -> gpt54mini (labels in aggregate_scores.py).
Safe to re-run: existing manifest entries are not duplicated; review files are overwritten from the job folder.
"""
import argparse, json, os, shutil, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_WORKDIR = os.environ.get("CODEX_JOBS_DIR", "/private/tmp/claude-501/-Users-rus-Library-CloudStorage-Dropbox-11-Claude-MiniProjects/3c672df1-92b4-4bf5-beb7-9cd60cdb83a9/scratchpad/rj")
KEY = {"gpt-5.5": "gpt55", "gpt-5.4": "gpt54", "gpt-5.4-mini": "gpt54mini", "gpt-5.3-codex": "gpt53codex", "gpt-5.2": "gpt52"}

def audit_log(path, ms_path, out_path):
    cmds, files, msgs = [], [], []
    if os.path.exists(path):
        for line in open(path):
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("type") != "item.completed":
                continue
            it = d.get("item", {})
            t = it.get("type")
            if t == "command_execution":
                cmds.append(it.get("command", ""))
            elif t == "file_change":
                files.extend([c.get("path", "") for c in it.get("changes", [])])
            elif t == "agent_message":
                msgs.append((it.get("text") or "")[:200])
    def ok_cmd(c):
        c2 = re.sub(r"^/bin/(zsh|bash|sh)\s+-l?c\s+", "", c.strip()).strip().strip("'\"").strip()
        reads_ms = ms_path in c2 and re.match(r"^(cat|sed|head|tail|nl|wc|less|grep)\b", c2) is not None
        writes_out = out_path in c2 and ("cat >" in c2 or "cat <<" in c2 or "tee " in c2 or "printf" in c2 or "echo" in c2 or "python" in c2)
        mk_out = re.match(r"^mkdir -p\s+'?(out|" + re.escape(os.path.dirname(out_path)) + r")/?'?$", c2) is not None
        ls_ok = c2 in ("ls", "pwd", "ls -la", "ls -l") or (c2.startswith("ls") and (os.path.dirname(out_path) in c2 or os.path.dirname(ms_path) in c2))
        return reads_ms or writes_out or mk_out or ls_ok   # bare ls/pwd in the empty work folder are harmless orientation commands
    suspicious = [c for c in cmds if not ok_cmd(c)]
    other_files = [f for f in files if os.path.abspath(f) != os.path.abspath(out_path) and out_path not in f]
    return {"n_commands": len(cmds), "commands": cmds, "file_changes": files, "final_messages": msgs[-2:],
            "suspicious_commands": suspicious, "other_file_changes": other_files,
            "tool_use_clean": not suspicious and not other_files}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--exp", type=int, required=True, choices=(1, 2)); ap.add_argument("--workdir", default=DEFAULT_WORKDIR)
    a = ap.parse_args()
    d = os.path.join(a.workdir, f"exp{a.exp}")
    jobs = json.load(open(os.path.join(d, "manifest.json")))
    if a.exp == 1:
        dest_rev = os.path.join(ROOT, "data_original", "reviews"); man_path = os.path.join(ROOT, "data_original", "manifest.json")
        cman_path = None; dest_ctl = None; audit_path = os.path.join(ROOT, "data_original", "codex_tool_audit.json")
    else:
        dest_rev = os.path.join(ROOT, "data", "reviews"); man_path = os.path.join(ROOT, "data", "manifest.json")
        dest_ctl = os.path.join(ROOT, "data", "controls", "reviews"); cman_path = os.path.join(ROOT, "data", "control_manifest.json")
        audit_path = os.path.join(ROOT, "data", "codex_tool_audit.json")
    manifest = json.load(open(man_path)); have = {j["id"] for j in manifest}
    cmanifest = json.load(open(cman_path)) if cman_path else None; chave = {j["id"] for j in cmanifest} if cmanifest else set()
    audit = json.load(open(audit_path)) if os.path.exists(audit_path) else {}
    n_ok = n_missing = 0
    for j in jobs:
        src = os.path.join(d, "out", j["id"] + ".md")
        if not (os.path.exists(src) and os.path.getsize(src) > 500):
            n_missing += 1; continue
        n_ok += 1
        ms = os.path.join(d, "inbox", ("manuscript" if j["kind"] == "review" else "clean") + f"_{j['paper']}.md")
        entry = {"paper": j["paper"], "model": KEY[j["model"]], "rep": j["rep"], "id": j["id"], "harness": "codex", "model_id": j["model"], "effort": j["effort"]}
        if j["kind"] == "review":
            shutil.copyfile(src, os.path.join(dest_rev, j["id"] + ".md"))
            if j["id"] not in have: manifest.append(entry); have.add(j["id"])
        else:
            shutil.copyfile(src, os.path.join(dest_ctl, j["id"] + ".md"))
            if j["id"] not in chave: cmanifest.append({"id": j["id"], "paper": j["paper"], "model": KEY[j["model"]], "harness": "codex", "model_id": j["model"], "effort": j["effort"]}); chave.add(j["id"])
        audit[j["id"]] = audit_log(os.path.join(d, "logs", j["id"] + ".jsonl"), ms, src)
    json.dump(manifest, open(man_path, "w"), indent=1)
    if cmanifest is not None: json.dump(cmanifest, open(cman_path, "w"), indent=1)
    json.dump(audit, open(audit_path, "w"), indent=1)
    unclean = [k for k, v in audit.items() if not v["tool_use_clean"]]
    print(f"exp {a.exp}: {n_ok} reviews integrated, {n_missing} missing; audit: {len(audit)} entries, not clean: {unclean}")

if __name__ == "__main__":
    main()
