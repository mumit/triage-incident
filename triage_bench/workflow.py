"""Decomposed Jev evidence decisions composed without text generation."""

import hashlib
import json
import math
from pathlib import Path

from .policy import TEXT, priority

GATES = {
    'monitor': 'Current independent service checks verify recovery, or confirmed maintenance fully explains observations with no unplanned impact.',
    'verify_change': 'Impact is not fully explained and a potentially relevant change needs scope verification; timing alone does not prove cause.',
    'gather_evidence': 'Independent evidence is missing, stale, conflicting, or cannot support a unique investigating domain.',
    'investigate_domain': 'Current independent evidence supports one investigating fault domain and its diagnostic check.',
}
DOMAINS = {
    'ran': ('radio resource, interference, antenna, timing, or mobility', 'inspect_radio'),
    'transport': ('packet or optical path, uplink, aggregation, routing, or link', 'inspect_transport'),
    'power': ('mains, battery, generator, or DC distribution', 'inspect_power'),
    'core': ('shared mobile-core or operator services across independent access paths', 'inspect_core'),
}
SUPPORT_THRESHOLD = 0.5


def questions():
    result = {'disposition': {
        'type': 'choice',
        'instructions': 'Select the initial evidence disposition under the supplied policy. Use current independent evidence. An alarm clearing alone is not verified service recovery.',
        'criteria': GATES,
    }}
    for domain, (description, _) in DOMAINS.items():
        result[f'supports_{domain}'] = {
            'type': 'noul',
            'instructions': f'Does current independent evidence justify initial {domain} investigation?',
            'criteria': {
                'true': f'Current independent {description} evidence supports this domain and accounts for the affected services.',
                'false': 'Evidence is absent, explicitly stale, contradicted, disconnected from affected services, or only an unverified symptom. Verified recovery supports monitoring instead.',
            },
        }
    return result


def request_body(record, model):
    packet = record['input']
    # Never include family IDs, labels, rationales, or an unrestricted record dump.
    state = {
        'policy': TEXT,
        'decision_timestamp': packet['decision_timestamp'],
        'observations': [
            {key: item[key] for key in ('detail', 'observed_at', 'source') if key in item}
            for item in packet['observations']],
        'service_impact': {key: packet['service_impact'][key]
                           for key in ('status', 'affected_sites', 'basis') if key in packet['service_impact']},
        'topology': {key: packet['topology'][key] for key in ('edges', 'note') if key in packet['topology']},
        'change_record': {key: packet.get('change_record', {})[key]
                          for key in ('status', 'scope', 'started_at', 'ended_at', 'detail')
                          if key in packet.get('change_record', {})},
    }
    # JSON string is supported by all existing typed model adapters.
    return {'model': model, 'state': json.dumps(state, ensure_ascii=False, sort_keys=True),
            'questions': questions()}


def normalize(response, packet):
    """Validate every primitive before mapping the answers to one disposition."""
    answers = response['answers']
    gate = answers['disposition']['choice']
    if gate not in GATES:
        raise ValueError('Invalid disposition choice')
    probabilities = answers['disposition'].get('probabilities')
    if probabilities is not None:
        if (not isinstance(probabilities, dict) or set(probabilities) != set(GATES) or
                any(not valid_probability(value) for value in probabilities.values()) or
                abs(sum(probabilities.values()) - 1) > 0.021):
            raise ValueError('Invalid disposition probability distribution')
    support = []
    for domain in DOMAINS:
        probability = answers[f'supports_{domain}']['noul']
        if not valid_probability(probability):
            raise ValueError(f'Invalid {domain} support probability')
        if probability >= SUPPORT_THRESHOLD:
            support.append(domain)
    owner, check, insufficient = 'noc', 'gather_evidence', 'yes'
    if gate == 'monitor':
        check, insufficient = 'monitor', 'no'
    elif gate == 'verify_change':
        check = 'verify_change'
    elif gate == 'investigate_domain' and len(support) == 1:
        owner = support[0]
        check, insufficient = DOMAINS[owner][1], 'no'
    predictions = dict(initial_owner=owner, next_check=check, insufficient_evidence=insufficient,
                       priority=priority(packet['service_impact']))
    # Primitive distributions are in the saved raw response, not invented as
    # calibrated distributions over the composed final decisions.
    return predictions, {}, {}


def valid_probability(value):
    return (not isinstance(value, bool) and isinstance(value, (int, float)) and
            math.isfinite(value) and 0 <= value <= 1)


def metadata():
    return {
        'request_protocol': 'northstar-decomposed-jev-v1',
        'workflow_question_sha256': hashlib.sha256(json.dumps(questions(), sort_keys=True).encode()).hexdigest(),
        'workflow_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'support_threshold': SUPPORT_THRESHOLD,
        'priority_source': 'northstar-1.0 deterministic impact policy',
        'no_autoregressive_calls': True,
    }
