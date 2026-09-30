"""Describe paired prediction disagreements and family-correlated uncertainty."""

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from triage_bench.evaluate import quantile  # noqa: E402


def compare(snapshot,left,right):
    keys=snapshot['cases'];runs=snapshot['runs']
    leftrows={r['id']:r for r in runs[left]['predictions']}
    rightrows={r['id']:r for r in runs[right]['predictions']}
    families=defaultdict(list);cases=[];counts=defaultdict(int)
    for key in keys:
        def correct(rows):
            row=rows.get(key['id'],{})
            return row.get('status')=='ok' and all(row['predictions'].get(f) in accepted for f,accepted in key['accepted_answers'].items())
        lc,rc=correct(leftrows),correct(rightrows)
        counts['both_correct' if lc and rc else 'left_only_correct' if lc else 'right_only_correct' if rc else 'both_wrong']+=1
        families[key['incident_family_id']].append(int(lc)-int(rc))
        cases.append({'id':key['id'],'family':key['incident_family_id'],'left_correct':lc,'right_correct':rc,
                      'left_predictions':leftrows.get(key['id'],{}).get('predictions'),
                      'right_predictions':rightrows.get(key['id'],{}).get('predictions')})
    groups=list(families.values());rng=random.Random(17);boot=[]
    for _ in range(5000):
        sampled=[rng.choice(groups) for _ in groups]
        boot.append(sum(sum(g) for g in sampled)/sum(len(g) for g in sampled))
    wins,losses=counts['left_only_correct'],counts['right_only_correct'];n=wins+losses
    exact=min(1,2*sum(math.comb(n,k) for k in range(min(wins,losses)+1))/2**n) if n else 1
    return {'left':left,'right':right,'records':len(keys),'families':len(groups),'counts':dict(counts),
            'left_minus_right_agreement':sum(sum(g) for g in groups)/len(keys),
            'family_bootstrap_95_percent_interval':[quantile(boot,.025),quantile(boot,.975)],
            'incident_mcnemar_exact_two_sided_p':exact,
            'limitations':'Descriptive development comparison; model selection used this cohort. Synthetic correlated families are not independently validated. Incident p value assumes independence and is not evidence of production equivalence.',
            'cases':cases}


def analyze(directory,output):
    directory=Path(directory);output=Path(output)
    if output.exists():raise FileExistsError(output)
    result={}
    for cohort in ('old-development','new-development','combined-development'):
        snapshot=json.loads((directory/(cohort+'.evidence.json')).read_text())
        pairs=[('expanded-structured','previous-head'),('expanded-structured','expanded-text-only'),
               ('expanded-structured','finetuned-17'),('expanded-structured','finetuned-29'),
               ('expanded-structured','luna-classifier')]
        result[cohort]=[compare(snapshot,left,right) for left,right in pairs if left in snapshot['runs'] and right in snapshot['runs']]
    output.write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();analyze(a.evidence_dir,a.output)
