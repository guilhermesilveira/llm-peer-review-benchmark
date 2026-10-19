"""Write judge instruction files for the (Codex/GPT) reviews that have no judgements yet.

Judges: J1 = Fable 5, J2 = Opus 5 (same as the Claude runs). Reviews of the same paper are grouped in batches of up to
four; the instruction file is the batch judge prompt with the FILES section filled in (paths inside the repository).
Each judge session is then launched with a two-line prompt: "Read <instruction file> and follow it exactly."

  python code/make_judge_batches.py --exp 1            -> judge files for data_original (goreview_*)
  python code/make_judge_batches.py --exp 2            -> judge files for data (greview_*) and controls (gcontrol_*)
Output: <workdir>/judge/exp{N}/batch_<k>_J{1,2}.txt and a listing printed to stdout.
"""
import argparse, glob, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_WORKDIR = os.environ.get("CODEX_JOBS_DIR", "/private/tmp/claude-501/-Users-rus-Library-CloudStorage-Dropbox-11-Claude-MiniProjects/3c672df1-92b4-4bf5-beb7-9cd60cdb83a9/scratchpad/rj")
WORDS = {1: "ONE", 2: "TWO", 3: "THREE", 4: "FOUR"}
TEMPLATE = open(os.path.join(ROOT, "prompts", "judge_batch_prompt.txt")).read()

def files_block(n, key, revs, outs):
    lines = [f"- Answer key (JSON; contains the scoring rules and the 14 errors with what counts as detection): {key}"]
    for i in range(n):
        lines.append(f"- Review {i+1}: {revs[i]} -> write scores to {outs[i]}")
    return "\n".join(lines)

def make(template, n, key, revs, outs):
    head, rest = template.split("FILES:\n", 1)
    _, tail = rest.split("\n\nPROCESS RULES:", 1)
    head = head.replace("FOUR written peer reviews", f"{WORDS[n]} written peer review{'s' if n > 1 else ''}")
    tail = tail.replace("the four reviews", f"the {WORDS[n].lower()} review{'s' if n > 1 else ''}").replace("When all four output files are written", f"When all {WORDS[n].lower()} output file{'s are' if n > 1 else ' is'} written")
    if n == 1:
        tail = tail.replace("Score each review independently of the others. ", "")
        head = head.replace("Score each review independently of the others. ", "")
    return head + "FILES:\n" + files_block(n, key, revs, outs) + "\n\nPROCESS RULES:" + tail

def batches_for(manifest_path, review_dir, judge_dir, key_dir, only_prefix):
    man = json.load(open(manifest_path))
    todo = [j for j in man if j["id"].startswith(only_prefix)
            and not (os.path.exists(os.path.join(judge_dir, j["id"] + "__J1.json")) and os.path.exists(os.path.join(judge_dir, j["id"] + "__J2.json")))]
    out = []
    for p in (1, 2, 3):
        ids = sorted(j["id"] for j in todo if j["paper"] == p and os.path.exists(os.path.join(review_dir, j["id"] + ".md")))
        for k in range(0, len(ids), 4):
            chunk = ids[k:k + 4]
            out.append({"paper": p, "ids": chunk, "key": os.path.join(key_dir, f"key_paper{p}.json"),
                        "revs": [os.path.join(review_dir, i + ".md") for i in chunk],
                        "outs_j1": [os.path.join(judge_dir, i + "__J1.json") for i in chunk],
                        "outs_j2": [os.path.join(judge_dir, i + "__J2.json") for i in chunk]})
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--exp", type=int, required=True, choices=(1, 2)); ap.add_argument("--workdir", default=DEFAULT_WORKDIR)
    ap.add_argument("--prefix", help="review id prefix to score (default goreview_ for exp 1, greview_ for exp 2)")
    ap.add_argument("--ctl-prefix", default="gcontrol_", help="control id prefix (exp 2)")
    a = ap.parse_args()
    rev_prefix = a.prefix or ("goreview_" if a.exp == 1 else "greview_")
    jd = os.path.join(a.workdir, "judge", f"exp{a.exp}"); os.makedirs(jd, exist_ok=True)
    if a.exp == 1:
        D = os.path.join(ROOT, "data_original")
        groups = [batches_for(os.path.join(D, "manifest.json"), os.path.join(D, "reviews"), os.path.join(D, "judgements"), D, rev_prefix)]
    else:
        D = os.path.join(ROOT, "data")
        groups = [batches_for(os.path.join(D, "manifest.json"), os.path.join(D, "reviews"), os.path.join(D, "judgements"), D, rev_prefix),
                  batches_for(os.path.join(D, "control_manifest.json"), os.path.join(D, "controls", "reviews"), os.path.join(D, "controls", "judgements"), D, a.ctl_prefix)]
    k = 0; listing = []
    for g in groups:
        for b in g:
            k += 1
            for jn, outs in (("J1", b["outs_j1"]), ("J2", b["outs_j2"])):
                txt = make(TEMPLATE, len(b["ids"]), b["key"], b["revs"], outs)
                fp = os.path.join(jd, f"batch_{k:02d}_{jn}.txt"); open(fp, "w").write(txt)
                listing.append({"batch": k, "judge": jn, "paper": b["paper"], "ids": b["ids"], "file": fp})
    json.dump(listing, open(os.path.join(jd, "listing.json"), "w"), indent=1)
    for l in listing:
        print(f"batch {l['batch']:02d} {l['judge']} paper {l['paper']} n={len(l['ids'])} -> {l['file']}")
    print(f"{len(listing)} judge sessions ({k} batches x 2 judges)")

if __name__ == "__main__":
    main()
