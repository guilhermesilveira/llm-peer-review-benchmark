# LLM peer review benchmark

Code and prompts for **Large language models detect methodological errors that human peer review misses in clinical trials**.

Dominikus Brian and Xavier Isidro Pereira Hernández contributed equally. The other authors are Hao Yin, Jeffrey Koury and Ruslan Rust. The preprint is being prepared for submission.

The benchmark tests 15 models on three historical trial manuscripts and three trials published in 2026. It includes 180 reviews of historical manuscripts, 180 reviews of error-seeded 2026 manuscripts and 45 control reviews. This repository contains the code and prompts for the current manuscript. Study data are distributed separately with the manuscript.

## Reproduce the results

Use Python 3.10 or later and the score file from Supplementary Data 1:

```bash
python -m pip install -r requirements.txt
python reproduce.py --scores /path/to/Supplementary_Data_1/validation/all_judge_item_scores.csv
```

This writes per-model results, judge agreement and correlations to `results/`, using saved scores without calling model APIs.

The primary analysis averages the scores of Fable 5 and Opus 5. Binary detection requires their mean to be at least 0.5. The historical human comparator uses the untrained control group. Flags on control manuscripts may be valid criticisms, and judge agreement does not establish accuracy against human labels.

## Generate the figures

Copy `data/`, `data_original/` and `additional_judges/` from Supplementary Data 1 into the repository root, then run:

```bash
python code/make_figures.py
python code/make_judge_figure.py
```

The figures are written to `figures/` as PNG and PDF files.

| Manuscript figure | Content | Script |
| --- | --- | --- |
| Figure 1 | Study design and historical manuscripts | `make_figures.py` |
| Figure 2 | 2026 manuscripts and control reviews | `make_figures.py` |
| Supplementary Figure 1 | Judge agreement and instruction checks | `make_judge_figure.py` |
| Supplementary Figure 2 | Scores by manuscript | `make_figures.py` |
| Supplementary Figure 3 | Memory probes | `make_figures.py` |
| Supplementary Figure 4 | Cost and review length | `make_figures.py` |

See the [code guide](code/README.md) for statistical analyses, validation, study-material scripts and session runners. The recorded prompts are in [`prompts/`](prompts/).

## License and citation

Code is MIT licensed. See [LICENSE](LICENSE) and [CITATION.cff](CITATION.cff). The test manuscripts are not included because of the licences of the source articles.
