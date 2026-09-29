# Incident review pack

These fictional incidents are development drafts. Review each case from the facts available at its decision time. No draft labels or model answers are shown.

Enter answers in `responses.json`. Use `approve`, `revise`, or `reject` for each case. An approved case needs one or more accepted values for each field and an evidence-based rationale. For revisions, state the necessary input or policy correction. Do not infer missing evidence. If more than one initial diagnostic action is valid, record those alternatives.

State your name and relevant network operations experience. Review tooling validates completeness and policy consistency; it cannot authenticate expertise. These already-inspected drafts remain development data after review.

## Policy

Northstar Networks fictional benchmark policy v1.0.
Select the initial investigating domain, not a confirmed root cause. Use current, independent evidence; a symptom at a radio site does not establish a radio fault. Shared dependencies can justify transport investigation. Do not infer causation from proximity or change timing alone. Missing, stale or conflicting evidence stays with noc; gather_evidence unless checking a relevant change scope is the immediate next step. When maintenance fully explains the observations with no unplanned impact, or independent recovery checks pass, choose noc/monitor and insufficient_evidence=no. Otherwise insufficient_evidence=yes means no unique fault domain is supported. Domain-specific evidence supports its matching diagnostic check. If an otherwise supported domain's telemetry becomes stale, retain noc/gather_evidence. Priority is independent of owner: outage at >=10 affected sites=P1; outage at 1–9 sites or degraded at >=10 sites=P2; other degraded or unknown=P3; none=P4. Unknown impact never implies no impact. Select only a diagnostic action; no configuration changes are authorized.

## Allowed answers

### initial_owner

- `ran`: Radio access: radio resource, interference, antenna, timing or mobility evidence.
- `transport`: Packet or optical transport: uplink, aggregation, routing or link evidence.
- `power`: Site electrical supply: mains, battery, generator or DC distribution evidence.
- `core`: Shared mobile-core or operator service evidence across independent access paths.
- `noc`: Retain at operations for insufficient/conflicting evidence, change checks or recovery monitoring.

### priority

- `P1`: Outage affecting at least 10 sites.
- `P2`: Outage affecting 1–9 sites, or degradation affecting at least 10 sites.
- `P3`: Other degradation or unknown impact.
- `P4`: No current unplanned service impact.

### next_check

- `inspect_radio`: Inspect sector radio KPIs, timing and radio hardware diagnostics.
- `inspect_transport`: Inspect path reachability, routing, queues, counters and optical diagnostics.
- `inspect_power`: Inspect independent mains, battery, generator and DC supply telemetry.
- `inspect_core`: Inspect shared core-service health and request traces.
- `verify_change`: Verify change/maintenance scope and timing against current evidence; do not execute rollback.
- `gather_evidence`: Collect current independent service, topology and domain telemetry before assigning a fault domain.
- `monitor`: Continue service observation under the maintenance or recovery policy.

### insufficient_evidence

- `yes`: A unique investigating fault domain cannot be justified yet.
- `no`: Evidence supports an initial domain or an explicit monitor-only disposition.

## Case 1: WF-887c2bb778-a

```json
{
  "decision_timestamp": "2026-04-01T10:00:00Z",
  "observations": [
    {
      "detail": "The battery-low alarm is from 08:00. At 10:00, the site controller independently measures the DC bus at 0 V, and a field technician confirms the supply fuse is open. The affected services remain down. Current probes through the upstream optical path pass.",
      "observed_at": "2026-04-01T10:00:00Z",
      "source": "Fictional operations evidence"
    }
  ],
  "service_impact": {
    "affected_sites": 2,
    "basis": "Independent current service checks",
    "status": "degraded"
  },
  "topology": {
    "edges": [
      [
        "S0",
        "A0"
      ],
      [
        "S1",
        "A1"
      ]
    ],
    "note": "Documented independent access paths; this excerpt does not prove absence of shared services."
  },
  "change_record": {
    "status": "Use the supplied observation and confirmed work scope."
  }
}
```

## Case 2: WF-887c2bb778-b

```json
{
  "decision_timestamp": "2026-04-01T10:00:00Z",
  "observations": [
    {
      "detail": "The battery-low alarm is from 08:00. At 10:00, a field technician confirms the supply fuse is closed and the DC bus measures 48 V. The affected services remain down. Current probes through the upstream optical path pass. No current radio or shared-service diagnostics are available.",
      "observed_at": "2026-04-01T10:00:00Z",
      "source": "Fictional operations evidence"
    }
  ],
  "service_impact": {
    "affected_sites": 2,
    "basis": "Independent current service checks",
    "status": "degraded"
  },
  "topology": {
    "edges": [
      [
        "S0",
        "A0"
      ],
      [
        "S1",
        "A1"
      ]
    ],
    "note": "Documented independent access paths; this excerpt does not prove absence of shared services."
  },
  "change_record": {
    "status": "Use the supplied observation and confirmed work scope."
  }
}
```

## Case 3: WF-e4d3ea3699-a

```json
{
  "decision_timestamp": "2026-04-01T10:00:00Z",
  "observations": [
    {
      "detail": "Voice quality is poor at four sites. Optical light levels and site power pass current checks. During the impairment interval, independent packet captures and queue counters on the shared egress show voice packets discarded by the configured policer. The radio scheduler has spare capacity.",
      "observed_at": "2026-04-01T10:00:00Z",
      "source": "Fictional operations evidence"
    }
  ],
  "service_impact": {
    "affected_sites": 4,
    "basis": "Independent current service checks",
    "status": "degraded"
  },
  "topology": {
    "edges": [
      [
        "S0",
        "A0"
      ],
      [
        "S1",
        "A1"
      ],
      [
        "S2",
        "A2"
      ],
      [
        "S3",
        "A3"
      ]
    ],
    "note": "Documented independent access paths; this excerpt does not prove absence of shared services."
  },
  "change_record": {
    "status": "Use the supplied observation and confirmed work scope."
  }
}
```

## Case 4: WF-e4d3ea3699-b

```json
{
  "decision_timestamp": "2026-04-01T10:00:00Z",
  "observations": [
    {
      "detail": "Voice quality is poor at four sites. Optical light levels and site power pass current checks. During the impairment interval, independent packet captures and queue counters on the shared egress show no packet discard. The radio scheduler has spare capacity. No other current domain evidence is available.",
      "observed_at": "2026-04-01T10:00:00Z",
      "source": "Fictional operations evidence"
    }
  ],
  "service_impact": {
    "affected_sites": 4,
    "basis": "Independent current service checks",
    "status": "degraded"
  },
  "topology": {
    "edges": [
      [
        "S0",
        "A0"
      ],
      [
        "S1",
        "A1"
      ],
      [
        "S2",
        "A2"
      ],
      [
        "S3",
        "A3"
      ]
    ],
    "note": "Documented independent access paths; this excerpt does not prove absence of shared services."
  },
  "change_record": {
    "status": "Use the supplied observation and confirmed work scope."
  }
}
```

## Case 5: WF-25bee86485-a

```json
{
  "decision_timestamp": "2026-04-01T10:00:00Z",
  "observations": [
    {
      "detail": "The site alarm cleared at 09:58 and an operator closed the notification. At 10:00, independent end-to-end service probes still fail from all three affected sites. Domain-level telemetry is unavailable.",
      "observed_at": "2026-04-01T10:00:00Z",
      "source": "Fictional operations evidence"
    }
  ],
  "service_impact": {
    "affected_sites": 3,
    "basis": "Independent current service checks",
    "status": "outage"
  },
  "topology": {
    "edges": [
      [
        "S0",
        "A0"
      ],
      [
        "S1",
        "A1"
      ],
      [
        "S2",
        "A2"
      ]
    ],
    "note": "Documented independent access paths; this excerpt does not prove absence of shared services."
  },
  "change_record": {
    "status": "Use the supplied observation and confirmed work scope."
  }
}
```

## Case 6: WF-25bee86485-b

```json
{
  "decision_timestamp": "2026-04-01T10:00:00Z",
  "observations": [
    {
      "detail": "The site alarm cleared at 09:58 and an operator closed the notification. Independent end-to-end service probes passed repeatedly from all three sites over the completed recovery observation interval; no current impairment is detected.",
      "observed_at": "2026-04-01T10:00:00Z",
      "source": "Fictional operations evidence"
    }
  ],
  "service_impact": {
    "affected_sites": 0,
    "basis": "Independent current service checks",
    "status": "none"
  },
  "topology": {
    "edges": [
      [
        "S0",
        "A0"
      ]
    ],
    "note": "Documented independent access paths; this excerpt does not prove absence of shared services."
  },
  "change_record": {
    "status": "Use the supplied observation and confirmed work scope."
  }
}
```

## Case 7: WF-8c543664cc-a

```json
{
  "decision_timestamp": "2026-04-01T10:00:00Z",
  "observations": [
    {
      "detail": "Two sites are unreachable. The remote controller reports zero DC voltage, but the field meter reports 48 V at the same equipment and timestamp. Both feeds claim current independent measurements. Transport and radio telemetry are missing; the discrepancy has not been resolved.",
      "observed_at": "2026-04-01T10:00:00Z",
      "source": "Fictional operations evidence"
    }
  ],
  "service_impact": {
    "affected_sites": 2,
    "basis": "Independent current service checks",
    "status": "outage"
  },
  "topology": {
    "edges": [
      [
        "S0",
        "A0"
      ],
      [
        "S1",
        "A1"
      ]
    ],
    "note": "Documented independent access paths; this excerpt does not prove absence of shared services."
  },
  "change_record": {
    "status": "Use the supplied observation and confirmed work scope."
  }
}
```

## Case 8: WF-8c543664cc-b

```json
{
  "decision_timestamp": "2026-04-01T10:00:00Z",
  "observations": [
    {
      "detail": "Two sites are unreachable. The remote controller and field meter both report zero DC voltage at the same equipment and timestamp. The field technician confirms an open supply fuse. Current upstream path probes pass.",
      "observed_at": "2026-04-01T10:00:00Z",
      "source": "Fictional operations evidence"
    }
  ],
  "service_impact": {
    "affected_sites": 2,
    "basis": "Independent current service checks",
    "status": "outage"
  },
  "topology": {
    "edges": [
      [
        "S0",
        "A0"
      ],
      [
        "S1",
        "A1"
      ]
    ],
    "note": "Documented independent access paths; this excerpt does not prove absence of shared services."
  },
  "change_record": {
    "status": "Use the supplied observation and confirmed work scope."
  }
}
```

## Case 9: WF-b81deaf387-a

```json
{
  "decision_timestamp": "2026-04-01T10:00:00Z",
  "observations": [
    {
      "detail": "Registration requests fail at twelve sites with documented distinct access paths. Current radio, power, and path probes pass. Independent service traces show TLS certificate validation failing at the shared registration endpoint after its certificate expired; direct endpoint probes reproduce the failure.",
      "observed_at": "2026-04-01T10:00:00Z",
      "source": "Fictional operations evidence"
    }
  ],
  "service_impact": {
    "affected_sites": 12,
    "basis": "Independent current service checks",
    "status": "outage"
  },
  "topology": {
    "edges": [
      [
        "S0",
        "A0"
      ],
      [
        "S1",
        "A1"
      ],
      [
        "S2",
        "A2"
      ],
      [
        "S3",
        "A3"
      ],
      [
        "S4",
        "A4"
      ],
      [
        "S5",
        "A5"
      ],
      [
        "S6",
        "A6"
      ],
      [
        "S7",
        "A7"
      ],
      [
        "S8",
        "A8"
      ],
      [
        "S9",
        "A9"
      ],
      [
        "S10",
        "A10"
      ],
      [
        "S11",
        "A11"
      ]
    ],
    "note": "Documented independent access paths; this excerpt does not prove absence of shared services."
  },
  "change_record": {
    "status": "Use the supplied observation and confirmed work scope."
  }
}
```

## Case 10: WF-b81deaf387-b

```json
{
  "decision_timestamp": "2026-04-01T10:00:00Z",
  "observations": [
    {
      "detail": "Registration requests fail at twelve sites with documented distinct access paths. Current radio, power, and path probes pass. A certificate was renewed yesterday, but current direct endpoint probes and service traces are unavailable. The renewal record alone does not establish the failing domain.",
      "observed_at": "2026-04-01T10:00:00Z",
      "source": "Fictional operations evidence"
    }
  ],
  "service_impact": {
    "affected_sites": 12,
    "basis": "Independent current service checks",
    "status": "outage"
  },
  "topology": {
    "edges": [
      [
        "S0",
        "A0"
      ],
      [
        "S1",
        "A1"
      ],
      [
        "S2",
        "A2"
      ],
      [
        "S3",
        "A3"
      ],
      [
        "S4",
        "A4"
      ],
      [
        "S5",
        "A5"
      ],
      [
        "S6",
        "A6"
      ],
      [
        "S7",
        "A7"
      ],
      [
        "S8",
        "A8"
      ],
      [
        "S9",
        "A9"
      ],
      [
        "S10",
        "A10"
      ],
      [
        "S11",
        "A11"
      ]
    ],
    "note": "Documented independent access paths; this excerpt does not prove absence of shared services."
  },
  "change_record": {
    "status": "Use the supplied observation and confirmed work scope."
  }
}
```

## Case 11: WF-025f5b51ee-a

```json
{
  "decision_timestamp": "2026-04-01T10:00:00Z",
  "observations": [
    {
      "detail": "The approved maintenance record covers two sites until 10:15. Independent checks show planned service suspension at those two sites only, matching the verified work scope. All other sites pass and there is no unplanned impact.",
      "observed_at": "2026-04-01T10:00:00Z",
      "source": "Fictional operations evidence"
    }
  ],
  "service_impact": {
    "affected_sites": 0,
    "basis": "Independent current service checks",
    "status": "none"
  },
  "topology": {
    "edges": [
      [
        "S0",
        "A0"
      ]
    ],
    "note": "Documented independent access paths; this excerpt does not prove absence of shared services."
  },
  "change_record": {
    "status": "Use the supplied observation and confirmed work scope."
  }
}
```

## Case 12: WF-025f5b51ee-b

```json
{
  "decision_timestamp": "2026-04-01T10:00:00Z",
  "observations": [
    {
      "detail": "The approved maintenance record covers two sites until 10:15. At 10:00 independent checks show four sites unreachable, including two outside the approved scope. No current fault-domain diagnostics are available. Verify actual work scope before attributing the extra impact.",
      "observed_at": "2026-04-01T10:00:00Z",
      "source": "Fictional operations evidence"
    }
  ],
  "service_impact": {
    "affected_sites": 4,
    "basis": "Independent current service checks",
    "status": "outage"
  },
  "topology": {
    "edges": [
      [
        "S0",
        "A0"
      ],
      [
        "S1",
        "A1"
      ],
      [
        "S2",
        "A2"
      ],
      [
        "S3",
        "A3"
      ]
    ],
    "note": "Documented independent access paths; this excerpt does not prove absence of shared services."
  },
  "change_record": {
    "status": "Use the supplied observation and confirmed work scope."
  }
}
```

## Case 13: WF-218b817fda-a

```json
{
  "decision_timestamp": "2026-04-01T10:00:00Z",
  "observations": [
    {
      "detail": "Two sectors have current receive-chain failure indications, confirmed by an independent local diagnostic and radio KPI loss. Current DC and upstream path checks pass. A billing portal change was deployed on unrelated infrastructure shortly before the alarms.",
      "observed_at": "2026-04-01T10:00:00Z",
      "source": "Fictional operations evidence"
    }
  ],
  "service_impact": {
    "affected_sites": 2,
    "basis": "Independent current service checks",
    "status": "degraded"
  },
  "topology": {
    "edges": [
      [
        "S0",
        "A0"
      ],
      [
        "S1",
        "A1"
      ]
    ],
    "note": "Documented independent access paths; this excerpt does not prove absence of shared services."
  },
  "change_record": {
    "status": "Use the supplied observation and confirmed work scope."
  }
}
```

## Case 14: WF-218b817fda-b

```json
{
  "decision_timestamp": "2026-04-01T10:00:00Z",
  "observations": [
    {
      "detail": "Two sectors have current receive-chain failure indications, confirmed by an independent local diagnostic and radio KPI loss. Current DC and upstream path checks pass. A billing portal change was deployed on unrelated infrastructure shortly before the alarms. The change title calls this a network outage fix, but its verified scope remains the billing portal.",
      "observed_at": "2026-04-01T10:00:00Z",
      "source": "Fictional operations evidence"
    }
  ],
  "service_impact": {
    "affected_sites": 2,
    "basis": "Independent current service checks",
    "status": "degraded"
  },
  "topology": {
    "edges": [
      [
        "S0",
        "A0"
      ],
      [
        "S1",
        "A1"
      ]
    ],
    "note": "Documented independent access paths; this excerpt does not prove absence of shared services."
  },
  "change_record": {
    "status": "Use the supplied observation and confirmed work scope."
  }
}
```

## Case 15: WF-a33ebc4c18-a

```json
{
  "decision_timestamp": "2026-04-01T10:00:00Z",
  "observations": [
    {
      "detail": "Four sites are unreachable. Current optical diagnostics show loss of signal at uplink A7. Independent power checks pass at all affected sites. The supplied complete dependency graph lists every affected site; current radio and shared-service diagnostics are unavailable.",
      "observed_at": "2026-04-01T10:00:00Z",
      "source": "Fictional operations evidence"
    }
  ],
  "service_impact": {
    "affected_sites": 4,
    "basis": "Independent current service checks",
    "status": "outage"
  },
  "topology": {
    "edges": [
      [
        "S0",
        "A7"
      ],
      [
        "S1",
        "A7"
      ],
      [
        "S2",
        "A7"
      ],
      [
        "S3",
        "A7"
      ]
    ],
    "note": "Complete upstream dependencies for these four sites."
  },
  "change_record": {
    "status": "Use the supplied observation and confirmed work scope."
  }
}
```

## Case 16: WF-a33ebc4c18-b

```json
{
  "decision_timestamp": "2026-04-01T10:00:00Z",
  "observations": [
    {
      "detail": "Four sites are unreachable. Current optical diagnostics show loss of signal at uplink A7. Independent power checks pass at all affected sites. The supplied complete dependency graph lists every affected site; current radio and shared-service diagnostics are unavailable.",
      "observed_at": "2026-04-01T10:00:00Z",
      "source": "Fictional operations evidence"
    }
  ],
  "service_impact": {
    "affected_sites": 4,
    "basis": "Independent current service checks",
    "status": "outage"
  },
  "topology": {
    "edges": [
      [
        "S0",
        "A20"
      ],
      [
        "S1",
        "A21"
      ],
      [
        "S2",
        "A22"
      ],
      [
        "S3",
        "A23"
      ]
    ],
    "note": "Complete upstream dependencies for these four sites."
  },
  "change_record": {
    "status": "Use the supplied observation and confirmed work scope."
  }
}
```
