# Independent technical audit of the v2 peer-review benchmark

**Date:** 29 October 2026. **Study:** [medRxiv 10.64898/2026.10.25.26366455v2](https://www.medrxiv.org/content/10.64898/2026.10.25.26366455v2), posted 28 October 2026. **Upstream code:** [`b05dbde6374c4bdafa1dfc4b5e4b4819f032bc4a`](https://github.com/rustlab1/llm-peer-review-benchmark/tree/b05dbde6374c4bdafa1dfc4b5e4b4819f032bc4a).

This audit identifies two seeded-item scoring conflicts with explicit answer-key exclusions, three control-review scoring artifacts, retained exposure to experiment-identifying context in part of the primary dataset, and a code defect that drops the historical context-reference analysis. It also examines the statistical scope of the three-manuscript model comparison and the interpretation of the control endpoint.

The calculations use the released data only and make no new model calls. All 120 independently reconstructed combined point estimates match the archived values to floating-point precision. The case review is targeted: it establishes the examples below, without estimating the prevalence of grading errors or their total impact on rankings. Preparation and case interpretation were assisted by OpenAI Codex; see [attribution and scope](ATTRIBUTION.md).

**1. Seeded-item detections conflict with explicit rubric exclusions**

The supplementary scoring methods, pp. 5-6, say that the manuscript-specific key defines the statements required for any score above zero and examples that fail those criteria. The statistical methods, p. 6, count an item as detected when the mean of the two judges reaches 0.5.

Two complete released reviews contain no qualifying alternative passage:

| Trial and reviewer | Target | Review content | Explicit exclusion | Recorded outcome |
| --- | --- | --- | --- | --- |
| P38, GPT-5.4, `ereview_0843` | M1: inadequate study justification | Calls the introduction brief and asks for a more balanced, concise literature review. | Generic introduction-length or reference comments without identifying missing study context or justification. | Both judges award 0.5; the item counts as detected. |
| P18, GPT-5.4-mini, `ereview_0689` | M3: absent sample-size calculation | Asks why 141 patients were enrolled despite a target of 124 and whether the power calculation was updated. | Over-enrollment criticism without recognizing the missing sample-size justification. | Both judges award 0.5; the item counts as detected. |

For P38, the review discusses uncertainty about the primary factorial comparison elsewhere, but does not identify the missing introductory rationale specified by M1. For P18, its question presupposes a calculation and asks about an update; it does not identify that no calculation is reported. J1's explanation itself acknowledges that the cited over-enrollment criticism is insufficient under the key.

**Evidence:** P38 [full review](evidence/further_trials/reviews/ereview_0843.md#L168), [key](evidence/further_trials/trials/P38/key.json#L10), [J1](evidence/further_trials/judgements/ereview_0843__J1.json#L5), [J2](evidence/further_trials/judgements/ereview_0843__J2.json#L5); P18 [full review](evidence/further_trials/reviews/ereview_0689.md#L14), [key](evidence/further_trials/trials/P18/key.json#L26), [J1](evidence/further_trials/judgements/ereview_0689__J1.json#L15), [J2](evidence/further_trials/judgements/ereview_0689__J2.json#L15).

These are local, concordant grading inconsistencies. Correcting either item to zero changes that model's 58-trial major-error mean by 0.00862 points and its sensitivity by 0.123 percentage points. Those corrections alone do not explain the reported performance gap. They establish that inter-judge agreement cannot substitute for validity checks against the stated rubric.

**Suggested correction:** independently adjudicate these cases and audit a blinded sample of all credited items, including partial-credit items. Report the resulting label-error rate and corrected metrics.

**2. Control reviews receive reversal-item credit based on a seeded-text assumption**

In trial P33, the serious-adverse-event proportions are 15.1% with DNL343 and 11.5% with shared placebo. The [control change log](evidence/further_trials/trials/P33/changes.md#L31) records a correctly directed comparison: the first proportion is higher. The planted m4 error instead reverses that direction; see the [answer key](evidence/further_trials/trials/P33/key.json).

Control review `econtrol_0749` correctly reports these proportions and questions the abstract's reassuring safety summary. It does not allege the targeted reversed comparison. Nevertheless, J1's evidence explains its award by assuming that a reversed sentence exists in the manuscript. Both judges give 0.5, making m4 a flagged control item. The documented control sentence has the correct direction.

The same target-item credit occurs in `econtrol_0744` and `econtrol_0764`. These three P33 reviews are all three m4 control flags across the released primary and additional-trial data.

**Evidence:** [Sol review](evidence/further_trials/reviews/econtrol_0749.md#L77), [J1's interpretation](evidence/further_trials/judgements/econtrol_0749__J1.json#L65), [J2](evidence/further_trials/judgements/econtrol_0749__J2.json); [GPT-5.4-mini review](evidence/further_trials/reviews/econtrol_0744.md), [GPT-6 Luna review](evidence/further_trials/reviews/econtrol_0764.md). Both judge files for every case are included under `evidence/further_trials/judgements/`.

The [judge prompt](evidence/further_trials/prompts/judge_prompt.txt) describes a manuscript with inserted errors and supplies the seeded key plus the review. The [runner](../../code/further_trials/ext_runner.py#L441) applies this interface to controls too. The judge does not receive the actual control manuscript to check its assumption.

These flags are scoring artifacts; they do not demonstrate that the reviewing models falsely alleged a reversed sentence. Removing these three flags raises pooled item-level nonflagging by approximately 0.0304 percentage points, leaving its one-decimal rounding unchanged.

**Suggested correction:** supply condition-appropriate manuscript evidence or control-specific criteria, distinguish the exact planted error from a broader topical concern, and independently adjudicate control labels before interpreting them as reviewer false alarms.

**3. Experiment-identifying context was visible to some primary reviewers**

The supplementary reviewer methods, p. 5, disclose that a one-line project description was visible to Haiku 4.5, Sonnet 5, Opus 5 and Fable 5. The archived [clean-rerun protocol](evidence/protocols/CLEAN_RERUN_INSTRUCTIONS.md#L5) gives more consequential detail: inherited project context identified an error-detection experiment and its relationship to the Schroter benchmark. It also describes inherited project-file and directory context.

The retained current audit records mark references to this experimental context in:

| Primary component audited | Records | Positive context-reference flags |
| --- | ---: | ---: |
| Historical seeded manuscripts, four original Claude models | 48 | 16 |
| Three 2026 seeded manuscripts, same models | 48 | 18 |
| Three 2026 controls, same models | 12 | 3 |

The corresponding IDs remain in the primary manifests and scoring data. The [historical audit](evidence/data_original/reviewer_tool_and_context_audit.json) and [2026 audit](evidence/data/reviewer_tool_and_context_audit.json) are reproduced unchanged. These are the study's audit records; the full original reviewer-session transcripts are not publicly included, which limits independent inspection of the recorded exposure.

Knowing the identity of a published planted-error benchmark can cue retrieval of its error categories and change review strategy. The observational comparison of reviews that reference the context with those that do not reference it does not isolate the effect of exposure: both groups had access to the context, and absence of a reference does not establish absence of influence. Fable's reasoning was not stored, further limiting interpretation of its unflagged records.

This finding concerns the original four-model primary component. It does not extend to the 55 additional API-reviewed trials or to the separately isolated Opus 5.5 sessions. No numerical effect of the exposure has been established.

**Suggested correction:** rerun the affected primary components with experiment-identifying context removed and compare scores using the same adjudication procedure.

**4. The historical context-reference analysis is silently omitted by a parser defect**

At [the audited code's parser](../../code/analyze_primary.py#L278), the analysis obtains review records only from nested `experiment2_reviews` or `experiment1_reviews` keys. The historical audit file instead contains a flat dictionary keyed by review ID.

Therefore the file's 48 records, including 16 positive flags, yield an empty record set to that parser. The saved primary `data/results_v2.json` consequently contains an empty historical priming-analysis object. The [verifier](verify_audit.py) reproduces both the zero-row parser result and the positive flags that the file actually contains.

This defect affects the historical context-reference check, not the main score calculations.

**Suggested correction:** accept the flat historical audit structure, require nonempty coverage where audit records are expected, and regenerate the historical context-reference analysis. A small format fix does not by itself establish that exposure had no effect.

**5. Statistical inference must distinguish repeated generations from new manuscripts**

The paper, p. 7, reports that GPT-6.1 Sol scored 0.81 fewer total points than Opus 5.5 on the three new manuscripts, with P = 0.0002. Recalculation from the raw J1/J2 scores gives:

| Manuscript | Sol mean, out of 14 | Opus 5.5 mean, out of 14 | Sol minus Opus |
| --- | ---: | ---: | ---: |
| Stroke | 12.0000 | 13.1250 | -1.1250 |
| Arthritis | 12.5625 | 13.0000 | -0.4375 |
| Heart failure | 11.8750 | 12.7500 | -0.8750 |

The mean difference is -0.8125. Exhaustive enumeration of individual-review label assignments within each fixed manuscript gives 50 extreme assignments out of 343,000, or P = 0.0001457726. Whole-manuscript paired label flips give P = 0.25; the released trial-level Monte Carlo output gives approximately 0.2443. The [primary code](../../code/analyze_primary.py#L150) explicitly describes the first test as conditional on these manuscripts.

The two tests target different uncertainty. The small generation-level P supports repeatability of the difference on those three manuscripts. It does not supply the same evidence for an advantage across new manuscripts. The whole-trial test is a separate inferential calculation, not a replacement P-value for the fixed-manuscript question.

Opus 5.5's advertised 99% major-error score also comes from this three-manuscript subset; it was not evaluated on the 55 additional trials. Repeated generations increase information about output variability without supplying additional independent clinical manuscripts.

**Suggested correction:** clearly label fixed-manuscript comparisons, present trial-level uncertainty for generalization claims, and compare the leading models on a larger common manuscript set.

**6. The control endpoint does not establish the correctness of review criticisms**

The pooled calculation is 1,737 flagged categories among 9,856 target-item observations, giving 82.3762% nonflagging. It is an item-level endpoint. Direct recalculation additionally gives:

- 675 of 704 control reviews (95.8807%) flag at least one of the 14 target categories.
- The mean is 2.4673 flagged target categories per control review.
- GPT-6.1 Sol flags unsupported conclusions in 55 of 58 controls (94.8276%).

These flags are not independently established false accusations. Some controls retain genuine limitations, and some labels can arise from scoring artifacts such as finding 2. Criticisms outside the 14 target categories are not adjudicated by this endpoint. Thus it does not measure review-level factual precision or author/editor burden from incorrect criticisms. The authors acknowledge that control comments can be justified; the endpoint should be interpreted within that limitation.

**Suggested correction:** adjudicate whether each criticism is correct against the actual manuscript, report precision across all substantive criticisms, and separately report the proportion of reviews containing an incorrect criticism.

**7. The added manuscript count provides limited diversity of diagnostic challenges**

All 55 included additional-trial M5 keys explicitly describe an intention-to-treat analysis as not performed. All 55 M4 keys describe a developed, study-specific or in-house measurement instrument. The verifier normalizes typographic hyphens before counting these phrases.

The trial set varies clinical context, but repeatedly presents conspicuous cues for the same predefined fault mechanisms. This supports a benchmark of those constructed checks. It supplies limited evidence about subtle, undisclosed analytical errors or broader scientific judgment. The absence of human reviews of the 2026 manuscripts also prevents a contemporary same-manuscript human-versus-model comparison.

**Suggested correction:** add independently validated errors with varied severity and explicitness, include naturally occurring defects, and obtain contemporary human reviews of the same manuscripts under comparable conditions.

**Reproduction and bounded conclusions**

Follow the [reproduction instructions](README.md). [Saved results](audit_results.json) contain exact permutation results, local grading evidence, control counts, parser behavior and cue counts. [Point-estimate checks](point_estimate_checks.csv) provide the 120-value comparison. [Provenance](provenance.json) records the preprint version, upstream commit and source archive hash.

The strongest demonstrated implementation issues are the specific rubric conflicts, the three control reversal labels and the dropped historical context analysis. The retained experiment-identifying context is a documented design concern. Their combined effect on rankings or the human-model performance gap remains unquantified. Re-scoring and clean reruns are needed to establish that effect.
