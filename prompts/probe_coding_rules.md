# Coding rules for the memory-probe answers (Supplementary Fig. 3)

The answers of Haiku 4.5, Sonnet 5, Fable 5, Opus 5 and Opus 5.5 to the recall and recognition probes
(`code/run_memory_probes.py`) were coded with the rules below. The answers, session transcripts and codes are in
Supplementary Data 1 (`data_original/memory_probes/` for the original test papers, `data/memory_probes/` for the
2026 trials).

Code only what an answer says. Count something as knowledge only when the model presents it as memory or prior
knowledge, at any stated confidence. Do not count items the model labels a guess, a generic reconstruction, an
inference from reading the text, or something it cannot separate from reading the text. Do not count facts the
model reads off the manuscript in front of it.

## Ground truth

Source publications of the original test papers:
- paper 1: van Walraven, C., Laupacis, A., Seth, R. & Wells, G. Dictated versus database-generated discharge
  summaries: a randomized clinical trial. *CMAJ* 1999;160:319-326.
- paper 2: source not identified.
- paper 3: Drury, M. et al. Patients with cancer holding their own records: a randomised controlled trial.
  *Br. J. Gen. Pract.* 2000;50:105-110.

The 14 error types of the original study (published in its reports): M1 poor justification for the study;
M2 biased randomization or allocation; M3 no sample-size calculation; M4 unknown reliability or validity of the
outcome measure; M5 failure to analyse by intention to treat; M6 poor response rate or loss to follow-up;
M7 unjustified conclusions; M8 discrepancy between abstract and results; M9 inconsistent denominators; m1 no ethics
approval; m2 no explanation of ineligible participants or non-enrolment; m3 inconsistency between text and tables;
m4 a comparison reported the wrong way round; m5 Hawthorne effect not considered.

Source trials of the 2026 manuscripts: stroke trial, Inoue et al., *JAMA Neurol.* 2026; psoriatic arthritis trial,
Ogdie et al., *Arthritis Rheumatol.* 2026; heart-failure trial, Pandey et al., *Nat. Med.* 2026. The error-inserted
versions were made for this study and never published.

## Measures (figure columns)

Recognition probes (one manuscript shown), counted per manuscript (of 3):
- **Recognized the source trial**: the model names the published trial the manuscript was made from (trial name,
  first author, or a description that identifies the correct trial), offered as memory.
- **Recalled result values**: the model states from memory a numerical result of the source trial. A remembered
  conclusion or direction of effect without values is noted but not counted.
- **Named the published paper**: the model gives, as memory, the correct journal and the correct year of the source
  publication.
- **Recalled where errors were inserted**: the model says it remembers, from the test paper itself or an answer key,
  a specific error inserted into this manuscript. Errors found by reading the text do not count. Original test
  papers only; not applicable to the 2026 manuscripts.
- **Recalled an answer key**: the model says it remembers an answer key or error list for this manuscript. Original
  test papers only; not applicable to the 2026 manuscripts.

Recall probe (no manuscript), original study only:
- **Named the test papers** (of 3): test papers the model names correctly (topic, title or source trial).
- **Recalled the error types** (of 14): official error types the model lists as remembered. Items labelled a
  generic reconstruction or a guess are excluded; a combined item counts for each official type it names.
