"""Export teacher labels after blind review, with family-level exclusion and audit."""

import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from triage_bench.dataset import read_jsonl,write_jsonl  # noqa: E402
from triage_bench.encoder import CLASSES,FIELDS  # noqa: E402
from triage_bench.llm_review import policy_issues,public_packet,sha,verify_evidence  # noqa: E402


def build(inputs,labels,primary_evidence,audit_evidence,audit_inputs,audit_labels,output):
    primary=verify_evidence(primary_evidence,inputs,labels)
    audit=verify_evidence(audit_evidence,audit_inputs,audit_labels)
    if primary['metadata']['requested_model']==audit['metadata']['requested_model']:
        raise ValueError('Audit must use a different model')
    records=read_jsonl(inputs);references=read_jsonl(labels)
    packetmap={r['id']:r for r in records};keymap={k['id']:k for k in references}
    first={r['id']:r for r in primary['reviews']};second={r['id']:r for r in audit['reviews']}
    for r in read_jsonl(audit_inputs):
        if r!=packetmap.get(r['id']):
            raise ValueError('Audit facts differ from primary inputs')
    if {r['id'] for r in read_jsonl(audit_inputs)}!=set(second):
        raise ValueError('Audit response coverage differs')
    cases=[];rejected_families=set()
    for r in records:
        record_id=r['id'];reasons=[]
        reviews=[first.get(record_id)]+([second[record_id]] if record_id in second else [])
        for review in reviews:
            if not review or review['status']!='ok':
                reasons.append('failed or missing review');continue
            if review['review']['input_issues'] or review['review']['unresolved_questions']:
                reasons.append('unresolved labelability issue')
            reasons.extend(policy_issues(review['predictions'],public_packet(r)))
        if record_id in second and all(review and review['status']=='ok' for review in reviews):
            if reviews[0]['predictions']!=reviews[1]['predictions']:
                reasons.append('teacher/audit decision disagreement')
            if reviews[0]['resolved_model']==reviews[1]['resolved_model']:
                reasons.append('same resolved model')
        family=keymap[record_id]['incident_family_id']
        if reasons:
            rejected_families.add(family)
        cases.append({'id':record_id,'incident_family_id':family,'pair_id':keymap[record_id]['pair_id'],
                      'reasons':reasons,'audit_reviewed':record_id in second})
    accepted=[case['id'] for case in cases if case['incident_family_id'] not in rejected_families]
    accepted_set=set(accepted)
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    write_jsonl(output/'train.inputs.jsonl',[r for r in records if r['id'] in accepted_set])
    keys=[]
    for r in records:
        record_id=r['id']
        if record_id not in accepted_set:
            continue
        answers=first[record_id]['predictions']
        keys.append({'id':record_id,'incident_family_id':keymap[record_id]['incident_family_id'],
                     'pair_id':keymap[record_id]['pair_id'],'split':'teacher_training',
                     'labels':answers,'accepted_answers':{field:[value] for field,value in answers.items()},
                     'review_status':'LLM teacher label; independent model audit on selected families; no specialist review',
                     'teacher_model':first[record_id]['resolved_model'],
                     'audit_model':second[record_id]['resolved_model'] if record_id in second else None})
    write_jsonl(output/'train.labels.jsonl',keys)
    (output/'decisions.json').write_text(json.dumps(cases,indent=2)+'\n')
    manifest={'use':'teacher-reviewed synthetic training material; not independent ground truth',
              'source_records':len(records),'accepted_records':len(keys),
              'accepted_families':len({key['incident_family_id'] for key in keys}),
              'rejected_families':sorted(rejected_families),'audit_records':len(second),
              'dispositions':len({tuple(key['labels'][field] for field in FIELDS) for key in keys}),
              'primary_evidence_sha256':sha(primary_evidence),'audit_evidence_sha256':sha(audit_evidence),
              'source_input_sha256':sha(inputs),'exporter_sha256':sha(__file__),
              'sha256':{name:sha(output/name) for name in ('train.inputs.jsonl','train.labels.jsonl','decisions.json')}}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','labels','primary-evidence','audit-evidence','audit-inputs','audit-labels','output-dir'):
        parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args()
    print(json.dumps(build(a.inputs,a.labels,a.primary_evidence,a.audit_evidence,a.audit_inputs,a.audit_labels,a.output_dir),indent=2))


if __name__=='__main__':
    main()
