"""Recalculate the v2 study audit from extracted Supplementary Data 1.

SPDX-License-Identifier: MIT

Usage: python3 verify_audit.py /path/to/Supplementary_Data_1 [output.json]
Uses only the Python standard library and saved data; makes no model or network calls.
Judgmental findings require reading the referenced full reviews and answer keys.
"""
import collections
import csv
import itertools
import json
import pathlib
import statistics
import sys

ROOT = pathlib.Path(sys.argv[1])
OUT = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path(__file__).with_name('audit_results.json')
ITEMS = [f'M{i}' for i in range(1, 10)] + [f'm{i}' for i in range(1, 6)]
ALIASES = {'haiku': 'haiku45', 'sonnet': 'sonnet5', 'opus': 'opus5', 'fable': 'fable5'}
ACTIVE = {'haiku45', 'sonnet5', 'gpt54mini', 'gpt54', 'gpt55', 'gpt61sol', 'gpt6luna',
          'gemini38fl', 'kimik3', 'gptoss120b', 'dsv4pro', 'qwen38_27b'}


def read(relative):
    return json.loads((ROOT / relative).read_text())


def scores(folder, rid):
    pairs = []
    for judge in ('J1', 'J2'):
        d = read(f'{folder}/{rid}__{judge}.json')
        by_id = {s['id']: float(s['score']) for s in d['scores']}
        pairs.append([by_id[i] for i in ITEMS])
    return [(a+b)/2 for a, b in zip(*pairs)]


trials = list(csv.DictReader((ROOT / 'further_trials/trials/trials.csv').open()))
included = {r['trial_id'] for r in trials if r['status'] == 'included'}
records = []
for manifest, folder, kind in [('manifest.json', 'judgements', 'review'),
                               ('control_manifest.json', 'controls/judgements', 'control')]:
    for row in read(f'data/{manifest}'):
        records.append({'id': row['id'], 'model': ALIASES.get(row['model'], row['model']),
                        'trial': f'original_{row["paper"]}', 'kind': kind,
                        'scores': scores(f'data/{folder}', row['id'])})

for row in read('further_trials/manifest.json'):
    if row['tid'] not in included or row['model'] not in ACTIVE:
        continue
    path = ROOT / 'further_trials/judgements' / f'{row["id"]}__J1.json'
    if not path.exists():
        continue
    records.append({'id': row['id'], 'model': row['model'], 'trial': row['tid'],
                    'kind': row['kind'], 'scores': scores('further_trials/judgements', row['id'])})

groups = collections.defaultdict(list)
for row in records:
    groups[(row['model'], row['kind'], row['trial'])].append(row['scores'])
collapsed = {}
for key, values in groups.items():
    collapsed[key] = {'scores': [statistics.mean(v) for v in zip(*values)],
                      'detected': [statistics.mean(v) for v in zip(*[[s >= .5 for s in v] for v in values])]}

reference = read('further_trials/results/results_fig2_combined.json')['models']
checks = []
for model in sorted(reference):
    for kind in ('review', 'control'):
        rows = [v for (m, k, t), v in collapsed.items() if m == model and k == kind]
        det = statistics.mean(statistics.mean(r['detected']) for r in rows)
        observed = {'major_mean': statistics.mean(sum(r['scores'][:9]) for r in rows),
                    'minor_mean': statistics.mean(sum(r['scores'][9:]) for r in rows),
                    'total_mean': statistics.mean(sum(r['scores']) for r in rows),
                    ('sens' if kind == 'review' else 'spec'): 100*(det if kind == 'review' else 1-det)}
        for metric, value in observed.items():
            checks.append({'model': model, 'kind': kind, 'metric': metric, 'recomputed': value,
                           'archived': reference[model][kind][metric],
                           'difference': value-reference[model][kind][metric]})

controls = [r for r in records if r['kind'] == 'control']
flag_counts = [sum(s >= .5 for s in r['scores']) for r in controls]


def exact_permutations(folder):
    by_model = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in read(f'{folder}/manifest.json'):
        if row['model'] in {'gpt61sol', 'opus55'}:
            by_model[row['model']][row['paper']].append(sum(scores(f'{folder}/judgements', row['id'])))
    distribution = collections.Counter({0: 1})
    observed = 0
    differences, means = [], []
    for trial in (1, 2, 3):
        a, b = by_model['gpt61sol'][trial], by_model['opus55'][trial]
        assert len(a) == len(b) == 4
        pool = [round(s*4) for s in a+b]
        within = collections.Counter(2*sum(c)-sum(pool) for c in itertools.combinations(pool, 4))
        convolved = collections.Counter()
        for x, n in distribution.items():
            for y, k in within.items():
                convolved[x+y] += n*k
        distribution = convolved
        observed += sum(pool[:4])-sum(pool[4:])
        difference = statistics.mean(a)-statistics.mean(b)
        differences.append(difference)
        means.append({'trial': trial, 'sol_mean_of_14': statistics.mean(a),
                      'opus55_mean_of_14': statistics.mean(b), 'sol_minus_opus55': difference})
    n = sum(distribution.values())
    extreme = sum(k for x, k in distribution.items() if abs(x) >= abs(observed))
    flips = [sum(a*b for a, b in zip(signs, differences)) for signs in itertools.product((-1, 1), repeat=3)]
    return {'trial_means': means, 'mean_difference': statistics.mean(differences),
            'review_label_exact_p': extreme/n, 'extreme_permutations': extreme, 'all_permutations': n,
            'trial_label_exact_p': sum(abs(x) >= abs(sum(differences))-1e-12 for x in flips)/len(flips)}


def case(rid, tid, item):
    key = next(s for s in read(f'further_trials/trials/{tid}/key.json')['errors'] if s['id'] == item)
    judgments = []
    for j in ('J1', 'J2'):
        d = read(f'further_trials/judgements/{rid}__{j}.json')
        s = next(s for s in d['scores'] if s['id'] == item)
        judgments.append({'judge': j, **s})
    return {'review_id': rid, 'trial': tid, 'item': item, 'key': key, 'judgments': judgments,
            'mean_score': statistics.mean(s['score'] for s in judgments),
            'review_path_in_archive': f'further_trials/reviews/{rid}.md'}


historical_audit = read('data_original/reviewer_tool_and_context_audit.json')
modern_audit = read('data/reviewer_tool_and_context_audit.json')
leak_counts = {'historical': sum(bool(v.get('referenced_experiment_context')) for v in historical_audit.values())}
for group, values in modern_audit.items():
    leak_counts[group] = sum(bool(v.get('referenced_experiment_context')) for v in values.values())

m4_controls = [r['id'] for r in controls if r['scores'][ITEMS.index('m4')] >= .5]
source_cues = {'included_further_trials': len(included), 'explicit_itt_not_performed': 0, 'custom_instrument_wording': 0}
for tid in included:
    key = {s['id']: s for s in read(f'further_trials/trials/{tid}/key.json')['errors']}
    hyphens = str.maketrans({c: '-' for c in '\u2010\u2011\u2012\u2013\u2014\u2212'})
    m5 = key['M5']['instantiation'].lower().translate(hyphens)
    m4 = key['M4']['instantiation'].lower().translate(hyphens)
    source_cues['explicit_itt_not_performed'] += ('intention-to-treat' in m5 and 'not performed' in m5)
    source_cues['custom_instrument_wording'] += any(s in m4 for s in ('developed', 'study-specific', 'in-house'))

result = {
    'scope': 'medRxiv DOI 10.64898/2026.10.25.26366455 version 2; saved data only',
    'point_estimate_checks': {'n': len(checks), 'max_abs_difference': max(abs(x['difference']) for x in checks)},
    'raw_modern_counts': dict(collections.Counter(r['kind'] for r in records)),
    'control_flags': {'n_reviews': len(controls), 'n_target_items': len(controls)*14,
                      'n_flags': sum(flag_counts), 'item_nonflagging_percent': 100*(1-sum(flag_counts)/(len(controls)*14)),
                      'reviews_with_any_flag': sum(bool(n) for n in flag_counts),
                      'reviews_with_any_flag_percent': 100*sum(bool(n) for n in flag_counts)/len(controls),
                      'mean_flags_per_review': statistics.mean(flag_counts), 'm4_flagged_ids': sorted(m4_controls)},
    'p_comparisons': {folder: exact_permutations(folder) for folder in ('data', 'data_original')},
    'seeded_key_exclusion_conflicts': [case('ereview_0843', 'P38', 'M1'), case('ereview_0689', 'P18', 'M3')],
    'control_reversal_cases': [case(rid, 'P33', 'm4') for rid in sorted(m4_controls)],
    'context_reference_flags': leak_counts,
    'historical_audit_parser': {'n_actual_audit_rows': len(historical_audit),
                               'n_rows_found_by_current_parser': len(historical_audit.get('experiment2_reviews') or historical_audit.get('experiment1_reviews') or {}),
                               'saved_primary_exp1_priming': read('data/results_v2.json')['priming']['exp1']},
    'explicit_fault_cues': source_cues,
    'qualification': 'Flagged control categories are not automatically false accusations; synthetic additions are disclosed. Local scoring errors do not establish their prevalence or reversal of main rankings.',
}
assert len(checks) == 120 and result['point_estimate_checks']['max_abs_difference'] < 1e-10
assert result['raw_modern_counts'] == {'review': 840, 'control': 704}
assert sorted(m4_controls) == ['econtrol_0744', 'econtrol_0749', 'econtrol_0764']
assert result['p_comparisons']['data']['trial_label_exact_p'] == .25
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(result, indent=2))
print(json.dumps({'saved': str(OUT), 'point_estimate_checks': result['point_estimate_checks'],
                  'control_flags': result['control_flags'], 'modern_exact_p': result['p_comparisons']['data'],
                  'context_reference_flags': leak_counts, 'explicit_fault_cues': source_cues}, indent=2))
