To the Editor and Authors,

This manuscript addresses a clinically important question: whether repeated-dose IV magnesium and adjunct nebulized budesonide can improve outcomes for children with severe acute asthma in the emergency setting. The combination of repeated higher-dose magnesium with serum magnesium measurements is somewhat novel, and if studied rigorously could matter to pediatric emergency clinicians and policy makers.

However, I have major concerns about the internal validity, analysis, and reporting of this trial. The most serious problems are: (1) the allocation method was predictable and does not meet usual standards for randomized allocation concealment; (2) the primary efficacy analysis was per-protocol only, with no intention-to-treat analysis; (3) the prespecified primary comparison is unclear in what appears to be a 2×2 factorial design; (4) there are multiple internal inconsistencies in the reported numbers; and (5) the conclusions substantially overstate the data, especially given a neutral primary outcome. As submitted, I do not think the paper provides reliable evidence that either intervention improves clinically meaningful outcomes.

## Major points

### 1. Allocation method is predictable and risks major bias
The manuscript states:

> “Allocation was determined by the enrolling physician from the date of presentation and the hospital record number: patients presenting on odd-numbered calendar dates were assigned to high dose magnesium and those presenting on even-numbered dates to standard dose magnesium, and patients whose hospital record number ended in an odd digit were assigned to nebulized budesonide and those whose number ended in an even digit to nebulized placebo.”

This is not adequate randomization with concealed allocation. It is a predictable assignment scheme. The enrolling physician knew treatment allocation at the point of enrollment, and potentially even before consent was sought. That opens the door to selection bias. It also raises doubts about the claim that the study was “blinded,” because the enrolling physician necessarily knew both allocations.

Related issues that need clarification:
- Were the physicians determining “medical readiness for discharge” blinded to allocation?
- Could the same child be enrolled more than once over this 2015–2020 period? This is especially important because hospital record number parity would then assign the same budesonide/placebo status on repeat visits.
- If multiple children were enrolled on the same calendar day, then magnesium assignment was effectively clustered by day. This clustering is not reflected in the analysis.

At minimum, the study should be described as quasi-randomized rather than randomized. This is a fundamental design limitation.

### 2. The primary analysis should not be per-protocol only
The authors state:

> “All efficacy and safety analyses were performed in the per-protocol population… An intention-to-treat analysis was not performed…”

This is a major problem. In randomized trials, the primary efficacy analysis should ordinarily be intention-to-treat. Excluding randomized participants because they received additional therapy or had protocol deviations is especially problematic in acute severe asthma, because those deviations are likely related to prognosis and treatment response. Excluding such patients can materially bias efficacy estimates.

Here, 166 were randomized, 7 were “not included in the analysis,” and 14 more were excluded for major protocol deviations, leaving 139 in the per-protocol set. That means about 16% of randomized patients were excluded from efficacy analyses. This is too many to ignore, and the reasons are highly likely to be informative.

The manuscript needs:
- A CONSORT flow diagram with correct arithmetic and reasons for all exclusions.
- Exact reasons for the 7 randomized patients not included in analysis.
- Exact reasons for the 14 major protocol deviations, by treatment arm.
- An intention-to-treat primary analysis, with per-protocol only as sensitivity.
- Safety analyses on all treated patients, not the per-protocol population.

### 3. The prespecified primary comparison is unclear, and the factorial design is not handled appropriately
The manuscript reads as a 2×2 factorial trial, but the analytic plan is inconsistent across sections.

- The abstract and introduction frame the study as 4 groups.
- The Methods say the accelerated failure time analysis compared “combined high-dose magnesium versus standard dose” and “combined budesonide versus nebulized placebo groups.”
- The Results first emphasize the 4-group comparison, then describe the combined magnesium analysis as “exploratory.”
- The Discussion and Conclusions focus on claims about magnesium efficacy despite a neutral primary time-to-discharge result.

This needs to be clarified against the registered protocol:
- What was the prespecified primary hypothesis?
- Was this a factorial trial designed to estimate main effects of magnesium and budesonide?
- Was an interaction between magnesium and budesonide tested?
- Why are the combined analyses described as “exploratory” if the Methods imply they were planned?

For a factorial trial, the main effects should be estimated in a model including both interventions, and interaction should be assessed. The present presentation does not allow the reader to determine whether the observed findings are prespecified, post hoc, or robust.

Also, the sample size section is inadequate. The paper states that 218 patients were planned, but gives no assumptions (effect size, variance, power, alpha, inflation for attrition, whether powered for main effects or interaction). That needs to be reported.

### 4. There are multiple internal inconsistencies that undermine confidence in the data
Several numerical inconsistencies are serious enough that I cannot currently be confident in the results as presented.

Examples:
- Participant flow does not add up:  
  > “414… assessed… 254 were not randomized… 166 were randomized”  
  But 414 − 254 = 160, not 166.
- The key 12-hour discharge finding differs between Abstract and Results:
  - Abstract: **46/71 (64.8%)** vs **26/68 (38.2%)**, **p = 0.002**, ARR 26.6%
  - Results text: **40/71 (56.3%)** vs **26/68 (38.2%)**, **p = 0.033**, ARR 18.1%
  This is a major discrepancy in the central efficacy claim.
- In the Results text for budesonide:
  > “the mean asthma severity score at 4 and 8 h was higher in the combined budesonide groups than in the placebo groups (5.0 vs 5.9… 3.9 vs 4.6…)”
  
  Numerically, those values are lower, not higher.
- The text says:
  > “Boys made up… 60.7% of the standard dose magnesium with placebo group”
  
  but Table 1 shows **29/41 = 70.7%**.
- Table 3 reports a “ratio of geometric means” of **1.1 (0.9 to 1.2)** for both the magnesium and budesonide comparisons, which seems inconsistent with the reported geometric means (e.g., 13.3 h vs 13.8 h for magnesium). These numbers need checking.
- Safety reports “Two of the **77** patients in the high dose magnesium groups…” but elsewhere high-dose numbers are 78 randomized, 71 per-protocol. The denominator 77 needs explanation.

Before the scientific claims can be evaluated, the manuscript needs a full data audit and correction of all internal inconsistencies.

### 5. The primary outcome and secondary severity-score analyses are not robustly handled
The primary outcome was “time to medical readiness for discharge,” but patients were assessed:

> “at least every 6 h by a paediatrician”

This raises several issues:
- Was the event time known exactly, or only within intervals?
- If only assessed every 6 hours, why is a sub-hour difference in geometric mean time (13.3 vs 13.8 h) clinically or statistically meaningful?
- How was interval censoring handled in the time-to-event analysis?
- How was the one PICU admission handled in the primary analysis?

The outcome itself also depends partly on subjective clinical judgement (“minimal or absent wheezing, crackles, or chest retractions”), and the asthma severity score used both for eligibility and secondary outcomes was “developed by the investigators for this trial.” The full scoring system, validation status, training of raters, and inter-rater reliability are not provided. This is a substantial limitation.

For the repeated severity-score outcomes, the analysis is particularly problematic:
- Patients discharged earlier are absent from later time points, so missingness is informative.
- Means at 12 and especially 24 hours are therefore based on progressively selected subsets of sicker children.
- Table 2 gives a 24-hour mean score of **6.7** in the high-dose magnesium + budesonide group, which is difficult to interpret without knowing how many children remained under observation at 24 hours.
- The manuscript does not report the number of patients contributing data at each time point.

Simple between-group comparisons of mean scores at each time point are not adequate. These outcomes need either a mixed-effects/repeated-measures approach with appropriate handling of post-discharge missingness, or at least a much more cautious descriptive presentation with denominators at each time point.

Baseline imbalance is also relevant: the combined budesonide groups start with a lower baseline severity score than placebo groups (**8.9 vs 9.3**, Table 3, p=0.08). Any score analyses should adjust for baseline severity.

### 6. The conclusions are not supported by the data
The paper’s conclusions are much too strong for the results shown.

The primary outcome is essentially negative:
- Four-group comparison: **p = 0.718** (Figure 2 text) / Table 2 shows **p = 1.0**
- Combined magnesium comparison: geometric mean **13.3 h vs 13.8 h**, **p = 0.3**
- Combined budesonide comparison: geometric mean **13.8 h vs 13.3 h**, **p = 0.6**

Yet the Abstract and Discussion conclude that repeated high-dose magnesium “shortens the time to medical readiness for discharge.” That is not supported by the reported primary analysis.

The recommendation:

> “High-dose magnesium with nebulized budesonide should replace standard-dose magnesium as the routine emergency department treatment for all children with acute asthma, including those with moderate exacerbations.”

is far beyond what these data can support. Reasons include:
- neutral primary endpoint
- single-center study
- predictable, non-concealed allocation
- per-protocol analysis only
- early stopping
- severe exacerbations studied, not moderate ones
- mostly very young children
- local short-stay unit discharge process
- post hoc/emphasized secondary findings only

Likewise, the conclusion that budesonide reduces “the need for further care after discharge” is not supported. Revisit/readmission outcomes were not statistically significant, follow-up was incomplete, and revisits were numerically higher in the budesonide groups (**8/43 vs 5/44** in Table 3).

This manuscript needs a complete re-write of the Abstract, Discussion, and Conclusions to reflect a negative/uncertain efficacy trial with limited short-term safety observations.

### 7. Important methodological details are missing or inconsistent
Several key methods are insufficiently described:

- **IV infusion duration** is not stated for either magnesium infusion. This is critical for both efficacy and safety.
- **Blinding of nebulized budesonide vs saline placebo** is not explained. Budesonide suspension may not be visually identical to saline; how was masking maintained?
- Timing is inconsistent:
  - Methods: second infusion given **3 h later**
  - Discussion: “following **4 h later** with a standard dose”
  - Discussion also says levels were measured “**1 h after the second dose**,” whereas Methods say **5 h after the first infusion**, which may or may not correspond.
- The timing of budesonide administration is unclear. The manuscript says budesonide was prepared to deliver **1 mg every 20 min for 3 doses**, but later says bronchodilators were given at 0, 20, and 40 min and this was “followed by” study drug over 20 min. Please clarify the exact sequence.
- What treatment, if any, was given before randomization/enrollment?
- Ethics committee approval is not stated. That must be included.
- The requirement for chest radiography and viral PCR for all enrolled children requires justification, including whether these procedures delayed treatment.

### 8. Safety conclusions should be much more cautious
The short-term safety data are reassuring but limited. The manuscript should not state broadly that “high-dose magnesium was safe” without qualification.

Points needing attention:
- Safety should be reported in all treated patients, not only the per-protocol population.
- Adverse event definitions and ascertainment need to be specified.
- The sample is small and underpowered for uncommon adverse events.
- Average 5-hour magnesium levels in the high-dose groups were **1.52–1.56 mmol/L**, below the **2.0 mmol/L** threshold discussed by the authors as relevant for smooth muscle relaxation. Thus the intervention as delivered may not have achieved the purported target exposure.
- Please report how many patients exceeded 2.0 mmol/L at any time, and any renal function or other laboratory safety data if collected.

## Minor points

1. Please provide the full investigator-developed asthma severity score, including item weights and scoring anchors, either in the main text or supplement.
2. Table 2 should report the number of patients assessed at each time point (4, 8, 12, 24 h).
3. The prespecified secondary outcome “proportion of patients discharged within 12, 24, 36, and 48 h” should be fully presented in the manuscript, not selectively discussed.
4. Use consistent terminology: “medical readiness for discharge” versus “discharged.”
5. Replace “p = 0.00” with “p < 0.001.”
6. Specify which statistical tests were used for 4-group comparisons in Table 2.
7. The statement that “There were no clinically important baseline differences” should be softened; small but potentially relevant imbalances exist in baseline severity and viral positivity.
8. Clarify exactly what counted as a “major protocol deviation.”
9. The title includes “pilot,” but the manuscript is written as a definitive efficacy study. Either the paper should be reframed as pilot/feasibility/safety work, or the “pilot” label reconsidered.
10. I cannot fully assess the references because they were omitted from the review copy; however, the introduction is quite brief and the discussion repetitive. The literature review should be more balanced and concise in the final version.

## Recommendation

**Reject.**

The clinical question is worthwhile, but the current manuscript has fundamental design and analysis problems—most importantly predictable allocation without adequate concealment, exclusive per-protocol analysis, unclear primary analytic strategy, numerous reporting inconsistencies, and major overinterpretation of a neutral primary result. These issues substantially limit the scientific reliability of the work for a general medical journal.
