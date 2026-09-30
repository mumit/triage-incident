"""Generate 30 new training and 20 development paired synthetic families."""

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from triage_bench import transfer_scenarios as catalog  # noqa: E402
from triage_bench.dataset import write_jsonl  # noqa: E402
from triage_bench.encoder import CLASSES,FIELDS  # noqa: E402
from triage_bench.policy import priority  # noqa: E402
from triage_bench.teacher_encoder import sha  # noqa: E402


def packet(details,status='degraded',sites=2,change=None,edges=None,note=None):
    return {'decision_timestamp':'2026-06-12T14:00:00Z',
            'observations':[{'detail':detail,'source':'Fictional independent check '+str(i+1),
                             'observed_at':'2026-06-12T13:59:00Z'} for i,detail in enumerate(details)],
            'service_impact':{'status':status,'affected_sites':sites,'basis':'Independent service checks at decision time' if status!='unknown' else 'Independent checks not available'},
            'topology':{'edges':edges or [['S0','A0'],['S1','A1']],
                        'note':note or 'Distinct documented access paths; possible shared services are not completely mapped.'},
            'change_record':change or {'status':'unknown','detail':'No relevant change has been independently established.'}}


def build(output):
    rows=[]
    normal={'ran':'Independent power and upstream packet delivery checks pass.',
            'transport':'Independent site-supply and local radio checks pass.',
            'power':'Independent upstream transport checks pass.',
            'core':'Independent site-supply, local radio and upstream transport checks pass.'}
    for line in catalog.DOMAIN_PAIRS.strip().splitlines():
        split,family,domain,positive,negative=line.split('|')
        category=next(i for i,c in enumerate(CLASSES) if c[0]==domain)
        checks=[normal[domain],'Two sites retain partial availability but current independent service probes confirm degradation.']
        change=None
        if domain=='ran':
            change={'status':'completed','scope':['REMOTE-LAB'], 'ended_at':'2026-06-12T13:45:00Z',
                    'detail':'Approved resolver work in an isolated remote lab; independent logs verify no affected assets or service dependencies were touched.'}
        variants=[]
        for index,text in enumerate((positive,negative)):
            details=[text]+checks
            if index==1: details.append('No other independent current fault-domain diagnosis is available; the continuing degradation remains unexplained.')
            if len(rows)%2: details=details[1:]+details[:1]
            variants.append((packet(details,change=change),category if index==0 else 4))
        rows.append((split,family,'domain_support',variants))
    for line in catalog.CHANGE_PAIRS.strip().splitlines():
        split,family,work=line.split('|')
        base={'status':'in_progress','scope':['S0','S1'],'started_at':'2026-06-12T13:30:00Z'}
        unverified={**base,'detail':'Approved work: '+work+'. Actual touched assets are not yet verified; no actual end time is recorded.'}
        verified={**base,'detail':'Independent implementation logs verify only approved assets were touched. Planned work remains in progress; no actual end time is recorded.'}
        a=packet(['Approved work would '+work+'. Four sites S0 through S3 are unreachable.',
                  'The implementation asset list is unavailable. No current independent domain fault is established; timing alone cannot identify a cause.'],status='outage',sites=4,change=unverified)
        b=packet(['Approved work would '+work+'. Independent implementation logs confirm exactly that effect at S0 and S1.',
                  'Only planned service suspension is present. All other sites and services pass; no current unplanned impact exists.'],status='none',sites=0,change=verified)
        rows.append((split,family,'change_scope',[(a,5),(b,6)]))
    for line in catalog.RECOVERY_PAIRS.strip().splitlines():
        split,family,service=line.split('|')
        a=packet(['The '+service+' alarm is no longer active.',
                  'Independent end-to-end service results have not arrived. Alarm clearance alone does not verify recovery; no current domain diagnosis is available.'],status='unknown',sites=None)
        b=packet(['Independent '+service+' checks passed repeatedly throughout the completed required recovery interval.',
                  'End-to-end transactions and current service counters confirm normal operation; the inactive historical alarm has no current impact.'],status='none',sites=0)
        rows.append((split,family,'recovery',[(a,4),(b,6)]))
    # Four additional development mechanisms exercise mixed-time, contradiction,
    # graph and change competition. Their themes overlap old interventions.
    a=packet(['A rectifier overtemperature trace is 48 minutes old; no new overtemperature trace exists.',
              'Fresh independent field temperature and output-voltage measurements pass. Radio and transport diagnosis has not arrived.'])
    a['observations'][0]['observed_at']='2026-06-12T13:12:00Z'
    b=copy.deepcopy(a);b['observations'][1]['detail']='Fresh field temperature measurements and independent rectifier diagnostics confirm thermal shutdown and collapsed equipment supply.'
    rows.append(('development','power_rectifier_thermal_timeline','mixed_age',[(a,4),(b,2)]))
    a=packet(['The shared router controller reports packets rejected by an input checksum fault.',
              'At the same interface and decision time, an independent ingress/egress capture shows every tested affected packet forwarded without checksum rejection. The discrepancy is unresolved.',
              'Current local radio and power checks pass; no other domain diagnosis is available.'])
    b=copy.deepcopy(a);b['observations'][1]['detail']='An independent ingress/egress capture at the same interface and time confirms affected packets rejected by the checksum fault.'
    rows.append(('development','transport_checksum_disagreement','contradiction',[(a,4),(b,1)]))
    variants=[]
    for connected in (True,False):
        edges=[['S0','A0'],['S1','A1'],['A0','U17' if connected else 'U18'],['A1','U17' if connected else 'U19']]
        note='Complete upstream dependencies for these two affected sites; every upstream link is listed.'
        p=packet(['Independent diagnostics confirm loss on uplink U17.',
                  'Current radio and power checks pass. No shared-service diagnosis is available. The listed graph identifies affected-site dependencies.'],edges=edges,note=note)
        variants.append((p,1 if connected else 4))
    rows.append(('development','transport_shared_uplink_intervention','graph',variants))
    a=packet(['Independent direct requests and core service traces reproduce a broken signing-key lookup in the shared authentication service.',
              'Power, radio and packet delivery pass. An approved signing-key maintenance record exists but its applied scope is unverified.'],
             change={'status':'in_progress','scope':['AUTH-POOL'],'started_at':'2026-06-12T13:40:00Z','detail':'Approved authentication signing-key work; actual implementation scope is unavailable.'})
    b=copy.deepcopy(a);b['observations'][0]['detail']='No direct core service request result or current signing-key diagnostic is available. A signing-key fault is an unverified hypothesis.'
    rows.append(('development','core_signing_key_change_competition','change_competition',[(a,3),(b,5)]))
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    families=[]
    for split in ('train','development'):
        inputs=[];labels=[]
        for assigned,family,theme,variants in rows:
            if assigned!=split:continue
            pair='ET-'+hashlib.sha256(family.encode()).hexdigest()[:10]
            families.append({'family':family,'split':split,'pair_id':pair,'theme':theme,
                             'semantic_independence':'New mechanism name; concepts overlap prior data; no independent adjudication.'})
            for i,(p,category) in enumerate(variants):
                record_id=pair+('-a' if i==0 else '-b')
                answers=dict(zip(FIELDS,CLASSES[category]));answers['priority']=priority(p['service_impact'])
                inputs.append({'id':record_id,'input':p,'policy_version':'northstar-1.0'})
                labels.append({'id':record_id,'split':split+'_transfer_draft','incident_family_id':family,'pair_id':pair,
                               'labels':answers,'accepted_answers':{k:[v] for k,v in answers.items()},
                               'review_status':'Provisional AI-authored reference; teacher review pending'})
        write_jsonl(output/(split+'.inputs.jsonl'),inputs);write_jsonl(output/(split+'.reference.labels.jsonl'),labels)
    (output/'families.json').write_text(json.dumps(families,indent=2)+'\n')
    manifest={'use':'Synthetic training and inspected development, not holdout','training_families':30,'development_families':20,
              'catalog_sha256':sha(catalog.__file__),'generator_sha256':sha(__file__),
              'sha256':{p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()}}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,required=True)
    print(json.dumps(build(parser.parse_args().output_dir),indent=2))
