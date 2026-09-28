"""Versioned fictional policy; not a real operator's runbook."""
VERSION = 'northstar-1.0'
OPTIONS = {
    'initial_owner': {
        'ran': 'Radio access: radio resource, interference, antenna, timing or mobility evidence.',
        'transport': 'Packet or optical transport: uplink, aggregation, routing or link evidence.',
        'power': 'Site electrical supply: mains, battery, generator or DC distribution evidence.',
        'core': 'Shared mobile-core or operator service evidence across independent access paths.',
        'noc': 'Retain at operations for insufficient/conflicting evidence, change checks or recovery monitoring.'},
    'priority': {'P1': 'Outage affecting at least 10 sites.',
                 'P2': 'Outage affecting 1–9 sites, or degradation affecting at least 10 sites.',
                 'P3': 'Other degradation or unknown impact.',
                 'P4': 'No current unplanned service impact.'},
    'next_check': {
        'inspect_radio': 'Inspect sector radio KPIs, timing and radio hardware diagnostics.',
        'inspect_transport': 'Inspect path reachability, routing, queues, counters and optical diagnostics.',
        'inspect_power': 'Inspect independent mains, battery, generator and DC supply telemetry.',
        'inspect_core': 'Inspect shared core-service health and request traces.',
        'verify_change': 'Verify change/maintenance scope and timing against current evidence; do not execute rollback.',
        'gather_evidence': 'Collect current independent service, topology and domain telemetry before assigning a fault domain.',
        'monitor': 'Continue service observation under the maintenance or recovery policy.'},
    'insufficient_evidence': {'yes': 'A unique investigating fault domain cannot be justified yet.',
                              'no': 'Evidence supports an initial domain or an explicit monitor-only disposition.'},
}
TEXT = '''Northstar Networks fictional benchmark policy v1.0.
Select the initial investigating domain, not a confirmed root cause. Use current, independent evidence; a symptom at a radio site does not establish a radio fault. Shared dependencies can justify transport investigation. Do not infer causation from proximity or change timing alone. Missing, stale or conflicting evidence stays with noc; gather_evidence unless checking a relevant change scope is the immediate next step. When maintenance fully explains the observations with no unplanned impact, or independent recovery checks pass, choose noc/monitor and insufficient_evidence=no. Otherwise insufficient_evidence=yes means no unique fault domain is supported. Domain-specific evidence supports its matching diagnostic check. If an otherwise supported domain's telemetry becomes stale, retain noc/gather_evidence. Priority is independent of owner: outage at >=10 affected sites=P1; outage at 1–9 sites or degraded at >=10 sites=P2; other degraded or unknown=P3; none=P4. Unknown impact never implies no impact. Select only a diagnostic action; no configuration changes are authorized.'''


def priority(impact):
    status, count = impact['status'], impact['affected_sites']
    if status == 'outage':
        return 'P1' if count >= 10 else 'P2'
    if status == 'degraded':
        return 'P2' if count >= 10 else 'P3'
    return 'P4' if status == 'none' else 'P3'


def questions():
    instructions = {
        'initial_owner': 'Which domain should initially investigate under the policy?',
        'priority': 'What is the incident priority under the supplied impact policy?',
        'next_check': 'Which next diagnostic check is best supported now?',
        'insufficient_evidence': 'Is evidence insufficient to select a unique investigating fault domain, using the policy definition?'
    }
    return {key: dict(type='choice', instructions=instructions[key], criteria=values)
            for key, values in OPTIONS.items()}
