# Code guide

All scripts in this folder support the current manuscript. Run commands from the repository root. The `data_original/` directory refers to the historical trial manuscripts used in the main experiment.

## Saved-data analyses

Copy `data/`, `data_original/` and `additional_judges/` from Supplementary Data 1 into the repository root. Archived JSON filenames are retained so the scripts can use the supplied files directly.

| Script | Purpose |
| --- | --- |
| `aggregate_scores.py` | Prepare descriptive summaries and figure inputs for the 2026 reviews and controls |
| `aggregate_historical_scores.py` | Prepare the corresponding inputs for the historical manuscripts |
| `analyze_primary.py` | Compute primary scores, sensitivity, specificity, manuscript-clustered intervals and permutation comparisons |
| `check_detection_rules.py` | Compare primary detection with the either-judge rule and reconstruct historical human detection rates |
| `summarize_results.py` | Summarize model scores, controls, agreement and review-length findings |
| `estimate_costs.py` | Recompute Supplementary Table 3 estimates from archived price and token inputs |
| `validate_submission.py` | Check review coverage, item scores and principal reported results |

To regenerate the analyses from the original judge outputs:

```bash
python code/aggregate_scores.py
python code/aggregate_historical_scores.py
python code/analyze_primary.py
python code/summarize_results.py
python code/check_detection_rules.py
python code/estimate_costs.py
python code/validate_submission.py
```

`analyze_primary.py` supplies the manuscript's confidence intervals and pairwise tests. Its two fixed random seeds preserve the recorded analysis of all 15 models. Pairwise P values are exploratory and unadjusted for multiple comparisons. The human comparator uses the untrained control group of Schroter et al. (2008), weighted by reviews per paper. Point scores and binary detection rates are distinct measures.

To also check Supplementary Table 2 against the Word supplement:

```bash
python code/validate_submission.py --supplement /path/to/Supplementary_information.docx
```

## Figures and timing

`make_figures.py` generates Figures 1–2 and Supplementary Figures 2–4. `make_judge_figure.py` generates Supplementary Figure 1. Their contents are listed in the main README.

`summarize_timing.py` reads the 12 separate timing sessions in `data/timing_run/`. To use `summarize_session_costs.py`, place `open_model_runs/` and `claude_code_runs_opus55/` from Supplementary Data 2 under `logs/`. Both scripts rebuild inputs used by `estimate_costs.py`.

## Study materials and session runners

These scripts document the collection procedure. Running model sessions requires the relevant command-line client or API credentials and incurs new model calls. Reproducing saved-data analyses does not require them.

The test manuscripts and the scripts that inserted the errors are not distributed, because of the licences of the source articles. Supplementary Table 1 and the change list in Supplementary Data 1 describe every edit; the scripts are available from the corresponding author on request.

| Script | Purpose |
| --- | --- |
| `build_2026_answer_keys.py` | Build the 2026 answer keys |
| `build_historical_answer_keys.py` | Build the historical answer keys from the official error descriptions |
| `prepare_judge_batches.py` | Prepare the original judges' blinded review batches |
| `run_claude_reviews.py` | Run Claude Code review sessions |
| `run_codex_reviews.py` | Run Codex review sessions |
| `collect_codex_reviews.py` | Extract Codex outputs and update review manifests |
| `run_api_reviews.py` | Run the seven API-accessed reviewer models |
| `run_claude_judges.py` | Run the two original Claude judges |
| `run_api_judge.py` | Run Kimi K3 with original or reworded scoring instructions |

## Recorded prompts and judge labels

Prompt files retain their recorded wording. Reviewer variants reflect the historical or 2026 manuscripts and the software environment. Judge variants cover individual reviews, batches, inline API requests and reworded instructions. Recall and recognition prompts are separate memory probes.

The combined score table names all six judges explicitly. J3 means Kimi K3 in the Kimi archive. In the separate decision-comparison archive, J3 means Jev, J4 means Microsoft Decision-1 and J5 means GPT-6.1 Sol. Supplementary Figure 1 compares the four judges that produced supporting text; the saved-score reproduction script also summarizes the two categorical decision models.
