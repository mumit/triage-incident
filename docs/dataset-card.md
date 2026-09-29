# Dataset card: version 0.1.0

## Origin and use

All data is synthetic and authored for the fictional Northstar Networks operator. No private tickets, infrastructure inventory, or operator procedures were used. Scenario prose was authored with AI assistance; deterministic Python expands it into realizations. No domain specialist has certified the labels.

Use this release to develop adapters, test scoring, inspect failure modes, and pilot supervised training. Do not treat results as an estimate of real incident prevalence, production confidence calibration, or operational savings.

## Contents

There are 600 training, 220 validation, 220 test, and 24 challenge records. The regular sets comprise 30, 11 and 11 authored families respectively, with 20 realizations per family. Challenge records comprise 12 pairs across four intervention archetypes. Repeated realizations are correlated.

Each split has separate `.inputs.jsonl` and `.labels.jsonl` files. Inputs contain only an opaque ID, policy version and incident packet. Keys contain labels, accepted answers, rationales, generation metadata, and family identifiers. `manifest.json` records distributions and SHA-256 checksums.

Labels are `initial_owner`, `priority`, `next_check`, and `insufficient_evidence`. The current release uses one accepted answer per field. The evaluator supports multiple accepted decisions for correctness; probability scoring is skipped for fields with multiple accepted answers rather than inventing a target distribution.

For a field with multiple accepted answers, an accepted prediction is credited to its own class in the confusion matrix and macro-F1. Otherwise those metrics use the canonical label. The browser marks every accepted answer correct and shows the alternatives alongside the reference decision.

## Construction and separation

An authored evidence scenario determines the initial investigating domain and diagnostic action. A fictional policy determines priority from visible service impact. Cases lacking sufficient domain evidence explicitly remain with operations. None labels a confirmed physical root cause.

Scenario families are assigned to splits before realization. No family crosses splits. Topology IDs are disjoint and the common aggregation skeleton differs by split. Some independent-path graph shapes and policy language necessarily recur; this is not a guarantee of complete structural or semantic novelty. Realizations within a family share prose. Opaque IDs are excluded from model requests.

The priority task deliberately tests policy application to structured fields. A deterministic rule can solve it perfectly. It is not evidence that an AI model can independently infer customer impact.

Observations are narrative evidence summaries with occasional numeric measurements, not a physical simulation or complete raw telemetry. The observation timestamp represents when that report is available; the prose may explicitly describe an older measurement. Topology excerpts are illustrative and may omit unaffected network elements. Synthetic observations can still contain technical simplifications or errors.

## Challenge interventions

- Change affected outage sites from nine to ten: priority must cross the policy boundary.
- Replace current power evidence with stale evidence: retain operations and gather fresh evidence.
- Add an irrelevant change-timing observation after independently verified recovery: disposition should remain monitoring.
- Remove all dependencies on an alarmed uplink: its alarm no longer justifies assigning the affected sites to transport.

Only the specified input field changes within each pair; IDs differ for scoring. No challenge archetype is used in training exports.

## Checks and limitations

The validator checks IDs, input/label correspondence, split-family separation, duplicate packets, timestamp availability, enum values, priority consistency, domain/action compatibility, pair-label relationships, and file checksums. These checks do not replace semantic review of the authored evidence.

Metrics include family-grouped bootstrap intervals, but 11 test families and four challenge archetypes are too few for strong generalization claims. The keyword baseline's high score indicates that much of this first release is straightforward. Larger independently authored cases, realistic noisy notes, alternative diagnoses, and specialist review should precede model selection for operational use.

Schemas describe the public input record and the labels object. The labels schema applies to the `labels` member of an answer-key row, not the entire row.
