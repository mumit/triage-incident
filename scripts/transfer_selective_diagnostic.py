"""Development-only selective automation using uncalibrated disposition scores."""

import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def analyze(evidence,output):
    evidence=Path(evidence);output=Path(output)
    if output.exists():raise FileExistsError(output)
    snapshot=json.loads(evidence.read_text());keys={k['id']:k for k in snapshot['cases']}
    results={}
    for name,run in snapshot['runs'].items():
        rows=run['predictions']
        if not all('disposition_probabilities' in r for r in rows):continue
        outcomes=[]
        for row in rows:
            probabilities=row['disposition_probabilities'];key=keys[row['id']]
            correct=row['status']=='ok' and all(row['predictions'].get(f) in choices for f,choices in key['accepted_answers'].items())
            outcomes.append((max(probabilities),correct))
        curve=[]
        for threshold in (0,.5,.6,.7,.8,.9,.95,.99):
            accepted=[ok for score,ok in outcomes if score>=threshold]
            curve.append({'threshold':threshold,'accepted':len(accepted),'coverage':len(accepted)/len(keys),
                          'errors':sum(not ok for ok in accepted),'agreement':sum(accepted)/len(accepted) if accepted else None})
        results[name]=curve
    result={'use':'Inspected development diagnostic only; no threshold is promoted',
            'limitations':'Maximum softmax score is uncalibrated. Selecting a threshold on these same errors is optimistic. Evidence insufficiency is a label, not confidence. No operational error guarantee.',
            'source_evidence':str(evidence),'curves':results}
    output.write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();analyze(a.evidence,a.output)
