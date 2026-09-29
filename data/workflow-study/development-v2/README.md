# Corrected workflow development inputs

Sixteen synthetic incidents in eight paired families, corrected after Luna/Sol review of the original drafts. These are developer-inspected development examples, not a holdout. Original draft files and their review evidence remain unchanged.

`development.inputs.jsonl` holds corrected public facts. `reference.labels.jsonl` preserves the provisional original decisions under new incident IDs. `changes.json` records every before/after edit; `manifest.json` records source and output hashes. Family and pair IDs remain shared with the originals so versions cannot be split across training and evaluation.

Changes reconcile degraded-impact wording, replace the procedural change-status placeholder, distinguish approved and actual maintenance scope, and add relevant approved-but-unverified certificate deployment scope. The last change adds a fictional fact to resolve a policy boundary; it is not independent adjudication of the old incident. Original domain negation, conflicting measurements, missing telemetry, and graph interventions remain present.

The [V2 review results](../../../docs/development-v2-results.md) document blind reviews by Luna and Sol, one preserved citation-validator failure, separate offline revalidation, and the unchanged encoder's 8/16 result. [Candidate labels](../../../examples/review/development-v2-reviewed-release/candidate.labels.jsonl) cover all seven dispositions. They may support development experiments, with teacher provenance retained. Do not call the provisional reference file an independently reviewed answer key.
