# Project brief

## Useful decisions

| Capability | Decision | Intended benefit to test |
|---|---|---|
| Incident triage | Initial investigating domain, priority, need for more evidence | Faster assignment and fewer handoffs |
| Diagnostic selection | Select a supplied diagnostic check or escalate | More consistent investigations |
| Related-incident matching, later phase | Link to an existing incident or investigate separately | Less duplicate investigation |

Benefits are hypotheses until measured in an operational workflow.

## Initial scenarios

1. Multiple cell sites become unreachable: shared transport dependency versus independent site faults.
2. Mobile throughput falls: radio congestion, interference, or backhaul congestion.
3. Radio alarms occur during maintenance: expected impact versus impact outside the approved scope.
4. A site runs on backup power: remaining battery time and redundancy affect urgency.
5. Packet loss follows a configuration change: temporal association supports investigation but does not confirm causation.
6. Alarms clear while service KPIs remain poor: alarm recovery is not sufficient evidence of service recovery.
7. Nearby sites produce similar tickets: geographic proximity alone does not establish a common cause.
8. Missing or stale telemetry: gathering evidence may be the correct next step.

## Illustrative incident

Four sites become unreachable within 90 seconds. They share an aggregation node. Its upstream interface reports loss of signal. Site power telemetry remains normal. No maintenance is recorded.

Under a benchmark policy that prioritizes shared upstream dependencies, the expected initial owner is transport. Inspecting uplink and optical telemetry is an appropriate next check. The evidence supports investigating the sites together but does not confirm a physical root cause.

A paired case removes the shared transport dependency. The model should reconsider grouping the sites. Final accepted answers depend on the full evidence packet and the written benchmark policy.

## Product scope

The first release contains incident import, three model adapters, an evidence and label review screen, batch evaluation, and a comparison dashboard. Models receive the same evidence and candidate answers. Dataset generation and the evaluation harness should precede UI implementation.

The synthetic data will support experimentation and training where a model's supported interfaces permit it. Hosted model access must not be assumed to include fine-tuning. Compare unmodified models first and report any trained or calibrated variants separately.
