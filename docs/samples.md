# Sample synthetic incidents

Each example is fictional. Labels are benchmark references for initial investigation, not confirmed root causes.

## power fuse

Investigation notes: A blown DC distribution fuse isolates the radio and site router. Independent upstream probes show the aggregation node is healthy.

Impact: `{"affected_sites": 1, "basis": "Current independent service checks", "status": "outage"}`

Expected decisions: `{"initial_owner": "power", "insufficient_evidence": "no", "next_check": "inspect_power", "priority": "P2"}`

## noc clear only

Shift update — The alarm cleared, but post-clear service measurements have not arrived. Recovery cannot yet be established from the available evidence.

Impact: `{"affected_sites": null, "basis": "Not independently verified", "status": "unknown"}`

Expected decisions: `{"initial_owner": "noc", "insufficient_evidence": "yes", "next_check": "gather_evidence", "priority": "P3"}`

## radio neighbor

Mobility failures are restricted to a newly introduced neighbor relation. Stationary sessions and transport probes succeed.

Impact: `{"affected_sites": 2, "basis": "Current independent service checks", "status": "degraded"}`

Expected decisions: `{"initial_owner": "ran", "insufficient_evidence": "no", "next_check": "inspect_radio", "priority": "P3"}`

## power controller

Operator observation: The power controller repeatedly opens the DC contactor despite healthy mains. Equipment resets align with the contactor events.

Impact: `{"affected_sites": 1, "basis": "Current independent service checks", "status": "degraded"}`

Expected decisions: `{"initial_owner": "power", "insufficient_evidence": "no", "next_check": "inspect_power", "priority": "P3"}`

## noc postmaintenance

Shift update — Planned work has ended. Independent service checks confirm sustained baseline performance for the full recovery observation interval; a delayed maintenance alarm is historical, not a current fault.

Impact: `{"affected_sites": 0, "basis": "Current independent service checks", "status": "none"}`

Expected decisions: `{"initial_owner": "noc", "insufficient_evidence": "no", "next_check": "monitor", "priority": "P4"}`

## core certificate

Operator observation: Core service-to-service authentication fails after a certificate expired. Radio and transport checks pass on independent access paths.

Impact: `{"affected_sites": 12, "basis": "Current independent service checks", "status": "outage"}`

Expected decisions: `{"initial_owner": "core", "insufficient_evidence": "no", "next_check": "inspect_core", "priority": "P1"}`

## transport qos

Only the expedited forwarding queue drops traffic on the common uplink. Other classes succeed and radio resource occupancy is normal.

Impact: `{"affected_sites": 9, "basis": "Current independent service checks", "status": "degraded"}`

Expected decisions: `{"initial_owner": "transport", "insufficient_evidence": "no", "next_check": "inspect_transport", "priority": "P3"}`

## core signaling

A shared core signaling worker queue is stalled. Requests from independent access paths reach it but are not processed.

Impact: `{"affected_sites": 18, "basis": "Current independent service checks", "status": "degraded"}`

Expected decisions: `{"initial_owner": "core", "insufficient_evidence": "no", "next_check": "inspect_core", "priority": "P2"}`

## noc nearby

Nearby sites report similar symptoms but have independent documented transport and power paths. No current domain-specific fault evidence is available.

Impact: `{"affected_sites": null, "basis": "Not independently verified", "status": "unknown"}`

Expected decisions: `{"initial_owner": "noc", "insufficient_evidence": "yes", "next_check": "gather_evidence", "priority": "P3"}`

## transport asymmetry

Operator observation: Bidirectional probes show loss only on the return aggregation path. Radio processing and the outbound transport path are healthy.

Impact: `{"affected_sites": 12, "basis": "Current independent service checks", "status": "degraded"}`

Expected decisions: `{"initial_owner": "transport", "insufficient_evidence": "no", "next_check": "inspect_transport", "priority": "P2"}`

## radio pim

Operator observation: Uplink interference tracks downlink transmit power on one sector. The shared transport path has clean counters and normal latency.

Impact: `{"affected_sites": 1, "basis": "Current independent service checks", "status": "degraded"}`

Expected decisions: `{"initial_owner": "ran", "insufficient_evidence": "no", "next_check": "inspect_radio", "priority": "P3"}`
