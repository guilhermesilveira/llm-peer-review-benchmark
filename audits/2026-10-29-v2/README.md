# Reproduce the independent v2 audit

Read the [report](REPORT.md), [attribution](ATTRIBUTION.md), and [source provenance](provenance.json).

1. Download [Supplementary Data 1](https://www.medrxiv.org/content/medrxiv/early/2026/10/28/2026.10.25.26366455.1/DC2/embed/media-2.zip?download=true) from the [v2 supplementary-material page](https://www.medrxiv.org/content/10.64898/2026.10.25.26366455v2.supplementary-material).
2. Compare the archive's SHA-256 with `source_zip_sha256` in `provenance.json`, then extract its `Supplementary_Data_1` directory.
3. From this repository's root, run:

```bash
python3 audits/2026-10-29-v2/verify_audit.py /path/to/Supplementary_Data_1 audits/2026-10-29-v2/audit_results.json
```

The verifier uses only the Python standard library. It reads saved reviews, scores, keys and audits; it makes no model or network calls. It reconstructs the 58-trial aggregation, checks 120 archived point estimates, enumerates the three-manuscript permutation tests exactly, counts control-category flags, reproduces the historical audit-parser behavior and reports the saved scores in five inspected review cases. The saved output can be inspected without downloading the full archive.

The code checks recorded facts and arithmetic. Interpreting a review against its item-specific rubric requires reading the full review and key; those selected source files and both judge outputs are included under `evidence/`. Their original archive paths and hashes appear in [evidence_manifest.csv](evidence_manifest.csv).

The source case files are unchanged. The full modified manuscripts and the full data archive are not redistributed. The report's limitations and attribution apply to the results here.
