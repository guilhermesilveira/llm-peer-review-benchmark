"""Answer keys for Experiment 1: the ORIGINAL Schroter test papers (BMJ 2004 data supplement, files schs1-3.pdf).
The 'name' and 'definition' fields are the official descriptions of the 14 deliberate errors (schs4.pdf);
the 'instantiation' fields are the official per-paper list of errors (schs5.pdf), lightly reformatted.
Writes data_original/keys.json and data_original/key_paper{1,2,3}.json.
Paper 1 = discharge summaries (database vs dictation); paper 2 = computer-generated health record vs booklet;
paper 3 = patient-held records in cancer care.
"""
import json, os
D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_original")
os.makedirs(D, exist_ok=True)

RULES = ("Schroter et al. 2004/2008 strict marking scheme. Score 1 = the review contains a clear statement that identifies THIS "
         "specific error AND explains why it is a problem (or what is missing). Score 0.5 = the review shows some evidence of "
         "having noticed the problem but the statement is vague, incomplete, or does not explain the issue (e.g. asks a related "
         "question without stating the error). Score 0 = not mentioned, or only a generic remark that would apply to any paper. "
         "Do NOT give credit for a comment about a different, merely related, weakness. Judge each error independently. "
         "Ignore how many other (non-listed) problems the review raises. The 'definition' field is the official BMJ description "
         "of what counted as detection in the original study; apply it.")

# Official definitions (schs4.pdf, "Descriptions of 14 deliberate errors")
DEF = {
 "M1": ("Poor justification for conducting the study",
        "A statement that the authors failed to put their study into context by providing relevant information from previous studies and justifying why there was a need for a new study."),
 "M2": ("Biased randomisation procedure",
        "A statement that the randomisation method (e.g. randomisation by family name or day of the week) was inadequate and could result in systematic bias."),
 "M3": ("No sample size calculation reported",
        "A statement that a sample size calculation had not been reported."),
 "M4": ("Unknown reliability and validity of the outcome measures",
        "A statement that there was insufficient information about the measurement properties (i.e. reliability and validity) of the outcome measures used e.g. quality of life questionnaires. A simple statement that the instruments were not referenced was not counted as this did not comment on the unknown measurement properties of the instruments."),
 "M5": ("Failure to analyse the data on an intention-to-treat basis",
        "A statement that the authors were incorrect in their assumptions that intention-to-treat analysis was inappropriate."),
 "M6": ("Poor response rate",
        "A statement that the response rate was low."),
 "M7": ("Unjustified conclusions",
        "A statement that the authors made inappropriate conclusions beyond their findings by inappropriately generalising their results to other areas of care which were not under study."),
 "M8": ("Discrepancy between data reported in the abstract and results",
        "A statement that there were discrepancies between the data reported in the main text of the paper and that reported in the abstract."),
 "M9": ("Inconsistent denominator",
        "A statement that the number of patients / cases reported in the papers are inconsistent and difficult to follow."),
 "m1": ("No ethics committee approval",
        "A statement that there was no indication that the study had been approved by an ethics committee."),
 "m2": ("No explanations for ineligible or non-randomized cases",
        "A statement that the flow of participants through each stage of the study was not clear and that the authors failed to provide explanations for ineligible or non-randomized cases."),
 "m3": ("Inconsistency between data reported in main text and tables",
        "A statement that there were discrepancies between figures reported in the main text and those reported in the tables."),
 "m4": ("Failure to spot word reversal in text leading to wrong interpretation of results",
        "A statement that the words in the text describing the findings reported in a table were inverted leading to the wrong interpretation."),
 "m5": ("Hawthorne effect",
        "A statement that the authors failed to report a possible Hawthorne effect i.e. that participants were aware that they were in a study and may have behaved differently from usual."),
}

# Official per-paper instantiations (schs5.pdf, "List of deliberate errors in papers reviewed"), plus what does not suffice
NOT_ENOUGH = {
 "M1": "Only saying the introduction is short or asking for more references, without pointing to missing context/justification.",
 "M2": "Only asking for more detail on randomisation, or only noting baseline imbalance, without stating that the method is inadequate/biased.",
 "M3": "Only saying the sample is small.",
 "M4": "A simple statement that the instruments were not referenced (explicitly excluded in the original study); generic remarks about self-report.",
 "M5": "Merely noting incomplete data or non-response without stating that intention-to-treat analysis should have been done / that the authors' dismissal of it is wrong.",
 "M6": "Generic remarks about missing data without stating that the response rate is low.",
 "M7": "Only saying 'demonstrates' should be 'suggests' or generic hedging advice unrelated to over-generalisation.",
 "M8": "Generic advice to check the abstract.",
 "M9": "Only asking for a CONSORT diagram (that is m2).",
 "m1": "Generic remark that ethics should be considered.",
 "m2": "Only noting an arithmetic inconsistency (that is M9).",
 "m3": "Generic advice to check numbers.",
 "m4": "",
 "m5": "Only saying that blinding was impossible / the study was open, without linking awareness of being studied to changed behaviour.",
}

INST = {
 1: {  # Are discharge summaries produced from databases better than those dictated from medical records?
  "M1": "Little justification for the need of the study [Introduction].",
  "M2": "Randomisation procedure sub-optimal: 'Admissions were randomised by the investigators, according to the first letter of their family name' [Methods].",
  "M3": "No sample size justification / calculation [Methods].",
  "M4": "Unknown reliability and validity of the GP assessment form (100-mm visual analogue ratings of quality, completeness, organisation, timeliness) [Methods].",
  "M5": "Intention-to-treat analysis would have been appropriate, not 'inappropriate' as the Discussion claims ('intention-to-treat analysis was not possible for the summary assessment, though such an analysis would have been inappropriate') [Discussion].",
  "M6": "Poor response rate for the GP assessments of summaries (151 / 302 = 50%) [Results].",
  "M7": "Generalisability of results unfounded: results are based on one teaching hospital with general medical patients, but the conclusions state that the use of computer databases to create hospital discharge summaries should be implemented widely / results are 'generalisable to all hospital discharges' [Abstract & Discussion].",
  "M8": "70.6% in the Abstract versus 79.6% in the Results for summary generation within 4 weeks; the Abstract states no difference in assessments of timeliness, but the Results say GPs gave higher timeliness ratings to database summaries; the Abstract reports figures for completeness, organisation and quality that are not reported in the Results section.",
  "M9": "Inconsistency throughout the paper about the number of discharge summaries (293, or 299, or 302, etc.).",
  "m1": "No explicit ethics approval [Methods].",
  "m2": "No explanation for ineligible or non-randomised patients [Figure 1, Results]: n = 17 admitted but not eligible for randomisation; n = 54 eligible for randomisation but not randomised.",
  "m3": "Inconsistency between text and tables: Results should state 14 not 15 items with a significant difference between groups as in Table 2; Results should state 10 not 7 items were more commonly cited in the database summaries as in Table 2.",
  "m4": "Wrong interpretation: database-generated summaries were shorter, not longer (57.3 v 64.8 lines) [Results, Discussion].",
  "m5": "No mention of a possible Hawthorne effect (on dictated summaries): junior doctors / participants may have behaved differently because they knew they were taking part in a study [Discussion].",
 },
 2: {  # Personalised computer-generated health record vs booklet, recruitment to health checks
  "M1": "Little justification for the need of the study [Introduction].",
  "M2": "Randomisation procedure sub-optimal: patients 'were randomly allocated, on the basis of their family name, to one of four groups' [Methods].",
  "M3": "No sample size justification / calculation [Methods].",
  "M4": "Unknown reliability and validity of the questionnaire (attitudes, knowledge and behaviour) [Methods].",
  "M5": "Intention-to-treat analysis should have been conducted; the investigators state 'we confined our analyses to the 414 patients who responded to the initial questionnaires as the non-responders were almost certainly not interested in having a health check' [Discussion].",
  "M6": "Poor response rate (414 / 850 = 49%) [Abstract].",
  "M7": "Generalisability of results unfounded: results are based on health promotion in one general practice, but the conclusions state the CHR and booklet should be used in other areas of primary care such as chronic disease [Abstract, Discussion].",
  "M8": "414/850 = 49% response rate in the Abstract and 551/850 = 65% in the Results.",
  "M9": "Inconsistency throughout the paper about the number of respondents (551 or 414?; Tables 1 and 4 have different denominators).",
  "m1": "No explicit ethics approval [Methods].",
  "m2": "No explanation for ineligible or non-randomised patients [Figure 1, Results]: 299 eligible patients who did not complete the questionnaire are not accounted for; 551 responses to the baseline questionnaire but subgroups sum to n = 414 (137 patients unaccounted for).",
  "m3": "Inconsistency between text and tables: Results state 62% liked more information about their health, Table 3 states 52%; Results state 58-67% used the media, Table 2 states 54-67%.",
  "m4": "Wrong interpretation: in the Discussion it should say the CHR was significantly associated with attending the health check, not the CHR + booklet (the Results section interprets the table correctly) [Discussion].",
  "m5": "No mention of a possible Hawthorne effect: patients may have behaved differently from usual because they knew they were taking part in a study [Discussion].",
 },
 3: {  # Patients with cancer holding their own records
  "M1": "Little justification for the need of the study [Introduction].",
  "M2": "Randomisation procedure sub-optimal: patients were randomised to intervention or control 'dependent on the day of the week' [Methods].",
  "M3": "No sample size justification / calculation [Methods].",
  "M4": "Unknown reliability and validity of the instrument measuring quality of life and/or of the 7-item questionnaire about satisfaction and communication [Methods].",
  "M5": "Intention-to-treat analysis would have been appropriate; the Discussion argues that analysis on the basis of intention to treat was not appropriate [Discussion].",
  "M6": "Poor response rate (450 / 850 = 53%) [Results].",
  "M7": "Generalisability of results unfounded: results are based only on a sample of radiotherapy patients, possibly from one provider, but the conclusions state that such an innovation should not be pursued in providing hospital-based care [Abstract, Discussion].",
  "M8": "Response rate reported as 450/574 = 78% in the Abstract and 450/850 = 53% in the Results.",
  "M9": "The figures in Table 1 sum to n = 325 not n = 425 for the record-holder (RH) and normal-care (NC) groups; the figures in Table 2 sum to n = 206 not n = 178 for the RH group and to n = 244 not n = 272 for the NC group.",
  "m1": "No explicit ethics approval [Methods].",
  "m2": "No explanation for ineligible or non-randomised patients [Figure 1, Results]: 446 (1296 - 850) eligible patients were not randomised; why were only n = 574 questionnaires sent at 3 months instead of n = 850?",
  "m3": "Inconsistency between text and tables: Results state there are 8 symptoms, Table 3 lists 6 symptoms.",
  "m4": "Wrong interpretation: the RH group suffered significantly less, not more, from nausea and vomiting and constipation (see Table 3) [Results].",
  "m5": "No mention of a possible Hawthorne effect: patients may have behaved differently because they knew they were taking part in a study [Discussion].",
 },
}
TITLES = {1: "Are discharge summaries produced from databases better than those dictated from medical records? (original Schroter test paper 1)",
          2: "The effect of a personalised computer-generated health record compared with a standard explanatory booklet on recruitment to health checks in general practice (original Schroter test paper 2)",
          3: "The effect of patients with cancer holding their own records on communication and quality of life (original Schroter test paper 3)"}

def key(p):
    errs = []
    for eid in ["M1","M2","M3","M4","M5","M6","M7","M8","M9","m1","m2","m3","m4","m5"]:
        name, definition = DEF[eid]
        errs.append({"id": eid, "class": "major" if eid[0]=="M" else "minor", "name": name,
                     "definition_official": definition,
                     "instantiation": INST[p][eid],
                     "detected_if": definition + " Here specifically: " + INST[p][eid],
                     "not_enough": NOT_ENOUGH[eid]})
    return {"scoring_rules": RULES, "paper_title": TITLES[p], "errors": errs}

allk = {"scoring_rules": RULES, "source": "Schroter et al. BMJ 2004;328:673, data supplement files schs4.pdf (descriptions) and schs5.pdf (list per paper)",
        "papers": {str(p): key(p) for p in (1,2,3)}}
json.dump(allk, open(os.path.join(D, "keys.json"), "w"), indent=1, ensure_ascii=False)
for p in (1,2,3):
    json.dump(key(p), open(os.path.join(D, f"key_paper{p}.json"), "w"), indent=1, ensure_ascii=False)
print("keys written to", D)
