#!/usr/bin/env bash
# Score the open-weight model reviews with the same two blinded judges as before (J1 = Fable 5, J2 = Opus 5),
# launched as independent, non-interactive Claude Code sessions that may only Read the instruction file, the key and
# the reviews, and Write the JSON outputs. This reproduces the original judge procedure exactly.
#
# Usage (from the repo root, with the Claude Code CLI installed and logged in):
#   python3 code/make_judge_batches.py --exp 1 --prefix woreview_ --workdir _open_model_runs
#   python3 code/make_judge_batches.py --exp 2 --prefix wreview_ --ctl-prefix wcontrol_ --workdir _open_model_runs
#   bash code/run_judges_claude_cli.sh _open_model_runs/judge/exp1
#   bash code/run_judges_claude_cli.sh _open_model_runs/judge/exp2
# Each batch file is run once; rerunning skips batches whose outputs all exist.
set -u
JD="$1"
J1_MODEL="${J1_MODEL:-claude-fable-5}"
J2_MODEL="${J2_MODEL:-claude-opus-5}"
for f in "$JD"/batch_*_J1.txt "$JD"/batch_*_J2.txt; do
  case "$f" in *_J1.txt) M="$J1_MODEL";; *) M="$J2_MODEL";; esac
  # skip if every output path named in the instruction file already exists
  missing=0
  for o in $(grep -o 'write scores to [^ ]*' "$f" | awk '{print $4}'); do [ -s "$o" ] || missing=1; done
  if [ "$missing" = 0 ]; then echo "skip $(basename "$f")"; continue; fi
  echo "$(date +%H:%M:%S) $(basename "$f") -> $M"
  claude -p "Read $f and follow it exactly." --model "$M" --allowedTools "Read,Write" --max-turns 30 > "${f%.txt}.log" 2>&1
done
echo done
