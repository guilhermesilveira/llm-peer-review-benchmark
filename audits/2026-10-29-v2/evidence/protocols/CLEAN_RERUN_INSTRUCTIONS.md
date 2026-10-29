Note: the manuscript files named below are not included in this archive (see README.txt, "Material provenance and rights").

# How to run a leak-free replication (no project note visible to the reviewers)

Why: every reviewer/judge/probe session in this run was started from a Claude Code session whose project memory
(`~/.claude/projects/-Users-rus-Library-CloudStorage-Dropbox-11-Claude-MiniProjects/memory/MEMORY.md`) contained the
line "Peer review error detection experiment - Aug 2026 Schroter-2008 replication with Claude models ...", and whose
project CLAUDE.md and folder path were also injected. Subagents (local, remote-isolation) inherit all three; renaming the
memory folder inside the running session did not help. The audit shows Sonnet 5 and Opus 5 read the line in most
reviews (reasoning traces), Haiku 4.5 never did, Fable 5 unknown (reasoning not stored). Scores did not differ, and no
review text mentions it, but the blinding is not what the manuscript's design intends.

## Option A (recommended): fresh Claude Code session in a neutral folder

1. Create a neutral folder outside Dropbox/11_Claude_MiniProjects, e.g. `mkdir -p ~/work/ms_review_jobs`.
   Do NOT put a CLAUDE.md in it. Do not create `~/.claude/projects/-Users-rus-work-ms_review_jobs/memory/` (a new
   project path has no memory; check that the folder does not exist).
2. Copy in only what the reviewers need, under neutral names:
   - `inbox/manuscript_1.md ... manuscript_3.md` = `data_original/manuscripts/original_paper{1,2,3}.md` (Exp. 1)
   - `inbox2/manuscript_1.md ... manuscript_3.md` = `data/manuscripts/{N,I,M}_errors.md` and `inbox2/clean_{1,2,3}.md` = `{N,I,M}_clean.md` (Exp. 2)
   - `prompts/reviewer_prompt.txt`, `prompts/reviewer_prompt_original.txt` (already neutral: "part of a study of the peer review process")
3. Open a NEW Claude Code session with that folder as the working directory (not a resumed session). Before launching
   any review, run one context probe per model: an Agent with the prompt "Without using any tools, list verbatim every
   instruction, note, memory or project description you can see in your context that is not part of this message.
   Then write it to probe_context.md." Confirm the answer contains no reference to peer review, Schroter, inserted
   errors, or the Dropbox project path.
4. Launch the jobs exactly as before: one Agent per review, `subagent_type: general-purpose`, `model` haiku/sonnet/opus/fable,
   extended thinking at max effort, prompt = template with {MS_PATH}/{OUT_PATH} filled in, outputs to `out/`.
   Exp. 1: 3 papers x 4 models x 4 runs = 48. Exp. 2: 48 + 12 controls. Concurrency cap 20; Sonnet takes up to ~18 min.
   Budget note: the previous full run hit the monthly spend limit once; a half-size replication (2 runs per paper and
   model = 24 + 24 + 12) is a sensible sensitivity check.
5. Judge in the same session or in this project (judges are not the blinding concern): `prompts/judge_batch_prompt.txt`,
   Fable 5 and Opus 5, batches of up to 5 reviews of the same paper, keys from `data_original/key_paper{1,2,3}.json`
   and `data/key_paper{1,2,3}.json`.
6. Copy reviews/judgements into `P1/.../data_clean/` (Exp. 2) and `data_original_clean/` (Exp. 1) with manifests in the
   same format, then run `analyze.py` / `analyze_original.py` pointed at those folders (a `--data` argument is a
   two-line change) and compare with `data/results.json` and `data_original/results.json`.
7. Save the transcripts audit (tool use + no context references) with the same script as before
   (`reviewer_tool_and_context_audit.json`).

## Option B: Anthropic Messages API

Send the same reviewer prompt with the manuscript text inline (system prompt = the reviewer template; user message =
manuscript) with extended thinking enabled and the same model IDs; nothing else is in context. Cleanest, but billed per
token separately from the Claude Code subscription (~48 x 30-60k input tokens + long outputs per experiment).

## Option C: keep the current data

Disclose the note (done in the manuscript, Methods "Reviewers" and Discussion) and rely on the sensitivity analysis
(primed vs unprimed reviews scored the same; Haiku, never primed, shows the same pattern). Weakest, but the note carried
no information about which errors were inserted, and Schroter's reviewers likewise knew they were in a study of peer review.
