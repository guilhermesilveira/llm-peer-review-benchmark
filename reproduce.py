"""Reproduce principal summaries from archived item scores without model calls."""
from pathlib import Path
import csv,json,itertools,argparse
import numpy as np
from scipy.stats import spearmanr

BASE=Path(__file__).resolve().parent
OUT=BASE/'results';OUT.mkdir(exist_ok=True)
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--scores', type=Path, required=True, help='validation/all_judge_item_scores.csv from Supplementary Data 1')
args=parser.parse_args()
rows=list(csv.DictReader(args.scores.open()))
judges=['Fable_5','Opus_5','Kimi_K3','GPT_6_1_Sol','Jev_1_13_0','Microsoft_Decision_1']
for r in rows:
    for k in judges+['primary_mean_score','primary_detected','either_judge_detected']:r[k]=float(r[k])
models=sorted(set(r['reviewer_model'] for r in rows))
summary=[]
for tag in ['2004','2026_seeded','2026_controls']:
    for m in models:
        rs=[r for r in rows if r['dataset']==tag and r['reviewer_model']==m];ids=set(r['review_id'] for r in rs)
        totals=[sum(r['primary_mean_score'] for r in rs if r['review_id']==rid) for rid in ids]
        major=[sum(r['primary_mean_score'] for r in rs if r['review_id']==rid and r['error_id'].startswith('M')) for rid in ids]
        minor=[sum(r['primary_mean_score'] for r in rs if r['review_id']==rid and r['error_id'].startswith('m')) for rid in ids]
        primary=100*np.mean([r['primary_detected'] for r in rs]);either=100*np.mean([r['either_judge_detected'] for r in rs])
        summary.append({'dataset':tag,'reviewer_model':m,'reviews':len(ids),'major_score_mean':float(np.mean(major)),'minor_score_mean':float(np.mean(minor)),'total_score_mean':float(np.mean(totals)),'primary_detection_percent':float(primary),'either_judge_detection_percent':float(either),'primary_nonflagging_percent':float(100-primary) if tag=='2026_controls' else None,'minimum_review_score':min(totals)})
def write_csv(path,rs):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
write_csv(OUT/'per_model_results.csv',summary)
agreements=[]
for tag in ['2004','2026_seeded','2026_controls']:
    rs=[r for r in rows if r['dataset']==tag]
    for a,b in itertools.combinations(judges,2):
        aa=np.array([r[a] for r in rs]);bb=np.array([r[b] for r in rs]);x=aa>=.5;y=bb>=.5
        po=np.mean(x==y);pe=x.mean()*y.mean()+(1-x.mean())*(1-y.mean())
        agreements.append({'dataset':tag,'judge_a':a,'judge_b':b,'items':len(rs),'exact_agreement_percent':100*float(np.mean(aa==bb)),'binary_cohens_kappa':float((po-pe)/(1-pe))})
write_csv(OUT/'judge_agreement.csv',agreements)
report={'reviews_by_dataset':{tag:len(set(r['review_id'] for r in rows if r['dataset']==tag)) for tag in ['2004','2026_seeded','2026_controls']}}
for label,key in [('primary','primary_detected'),('either_judge','either_judge_detected')]:
    sens=[100*np.mean([r[key] for r in rows if r['dataset']=='2026_seeded' and r['reviewer_model']==m]) for m in models]
    spec=[100*(1-np.mean([r[key] for r in rows if r['dataset']=='2026_controls' and r['reviewer_model']==m])) for m in models]
    rho,p=spearmanr(sens,spec)
    report[label]={'control_flags':int(sum(r[key] for r in rows if r['dataset']=='2026_controls')),'sensitivity_specificity_rho':float(rho),'p_scipy':float(p)}
report['all_seeded_reviews_above_historical_human_mean']=all(r['minimum_review_score']>3.29 for r in summary if r['dataset']!='2026_controls')
assert report['reviews_by_dataset']=={'2004':180,'2026_seeded':180,'2026_controls':45}
assert report['primary']['control_flags']==107
assert report['either_judge']['control_flags']==145
assert report['all_seeded_reviews_above_historical_human_mean']
(OUT/'summary.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
