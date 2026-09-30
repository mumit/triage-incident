"""Generate paired synthetic teacher-training material with provisional references."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from triage_bench import teacher_scenarios  # noqa: E402
from triage_bench.dataset import write_jsonl  # noqa: E402
from triage_bench.encoder import CLASSES, FIELDS  # noqa: E402
from triage_bench.llm_review import sha  # noqa: E402
from triage_bench.policy import priority  # noqa: E402


def build(output):
    inputs, labels, families = [], [], []
    catalog = []
    for line in teacher_scenarios.DOMAIN_PAIRS.strip().splitlines():
        family, domain, positive, negative = line.split('|')
        catalog.append((family, domain, positive, negative, 'domain_support'))
    for text, kind in [(teacher_scenarios.CHANGE_PAIRS, 'change_scope'), (teacher_scenarios.RECOVERY_PAIRS, 'recovery')]:
        for line in text.strip().splitlines():
            family, positive, negative = line.split('|')
            catalog.append((family, 'noc', positive, negative, kind))
    for family, domain, first, second, kind in catalog:
        pair = 'TT-' + hashlib.sha256(family.encode()).hexdigest()[:10]
        for variant, detail in enumerate((first, second)):
            status = 'degraded' if kind=='domain_support' else ('outage' if kind=='change_scope' else 'unknown')
            if kind!='domain_support' and variant==1:
                status = 'none'
            count = None if status=='unknown' else (0 if status=='none' else (4 if kind=='change_scope' else 2))
            edges = [['S0', 'A0'], ['S1', 'A1']]
            note = 'Documented distinct access paths; this excerpt does not establish absence of shared services.'
            if family=='transport_dependency_membership':
                detail = 'Two sites have degraded service. Current power checks pass. ' + detail.replace('The alarmed uplink', 'Uplink U7')
                edges = [['S0', 'A0'], ['S1', 'A1'], ['A0', 'U7' if variant==0 else 'U8'], ['A1', 'U7' if variant==0 else 'U9']]
                note = 'Complete upstream dependencies for these two affected sites; every upstream link is listed.'
            elif kind=='domain_support':
                detail = 'Two sites have degraded service with partial availability. ' + detail
                if domain=='ran':
                    detail += ' Independent current DC supply and upstream transport checks pass.'
                elif domain=='power':
                    detail += ' Independent current upstream transport checks pass.'
                elif domain=='transport':
                    detail += ' Independent current power and radio checks pass.'
                else:
                    detail += ' Independent current radio, power, and upstream transport checks pass.'
                if variant==1:
                    detail += ' No other current independent fault-domain evidence is available.'
            change = {'status':'unknown','detail':'No relevant change activity has been independently established at decision time.'}
            if kind=='change_scope':
                change = {'status':'in_progress','scope':['S0','S1'],
                          'started_at':'2026-05-02T09:40:00Z','ended_at':'2026-05-02T10:20:00Z',
                          'detail':'Actual implementation scope is unverified.' if variant==0 else 'Independent work logs confirm actual scope matches approved scope.'}
            packet = {'decision_timestamp':'2026-05-02T10:00:00Z',
                      'observations':[{'detail':detail,'source':'Fictional independent operations checks','observed_at':'2026-05-02T10:00:00Z'}],
                      'service_impact':{'status':status,'affected_sites':count,'basis':'Current independent service checks' if status!='unknown' else 'Not independently verified'},
                      'topology':{'edges':edges,'note':note}, 'change_record':change}
            category = (next(i for i, triple in enumerate(CLASSES) if triple[0]==domain) if variant==0 else 4) if kind=='domain_support' else ((5 if kind=='change_scope' else 4) if variant==0 else 6)
            answers = dict(zip(FIELDS,CLASSES[category]));answers['priority']=priority(packet['service_impact'])
            record_id = pair + ('-a' if variant==0 else '-b')
            inputs.append({'id':record_id,'input':packet,'policy_version':'northstar-1.0'})
            labels.append({'id':record_id,'split':'teacher_training_draft','incident_family_id':family,'pair_id':pair,
                           'labels':answers,'accepted_answers':{key:[value] for key,value in answers.items()},
                           'review_status':'provisional AI-authored reference; no teacher or specialist review yet'})
        families.append({'incident_family_id':family,'pair_id':pair,'mechanism':kind,
                         'related_development_themes':'Positive/negative evidence, scope or recovery; conceptually related to development interventions. Mechanism overlap has not been independently adjudicated.'})
    output = Path(output)
    output.mkdir(parents=True,exist_ok=False)
    write_jsonl(output/'train.inputs.jsonl',inputs);write_jsonl(output/'reference.labels.jsonl',labels)
    (output/'families.json').write_text(json.dumps(families,indent=2)+'\n')
    manifest = {'use':'AI-authored training development material; not a holdout','records':len(inputs),'families':len(families),'pairs':len(families),
                'catalog_sha256':sha(teacher_scenarios.__file__),'generator_sha256':sha(__file__),
                'sha256':{name:sha(output/name) for name in ('train.inputs.jsonl','reference.labels.jsonl','families.json')}}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(build(args.output_dir),indent=2))


if __name__=='__main__':
    main()
