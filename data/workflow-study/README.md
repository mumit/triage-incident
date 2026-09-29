# Workflow study draft review cohort

These 16 synthetic incidents form eight paired development families. They were authored and labeled by an AI agent on 2026-09-29. No network specialist has reviewed them. They are not an independent holdout, a representative ticket sample, or evidence of model accuracy.

`draft.inputs.jsonl` contains public incident facts. `draft.labels.jsonl` contains provisional labels and accepted answers. `review.json` lists the review questions and empty reviewer fields. `manifest.json` records the draft file identities. The runner reads only the input file.

The pairs cover mixed stale/current DC measurements, voice queue discard, alarm clearance versus verified recovery, contradictory electrical measurements, shared-service certificate failures, maintenance-scope mismatch, unrelated change framing, and graph dependency membership. Several overlap conceptually with earlier challenges and therefore belong to development.

Review the facts, causal sufficiency, policy labels, alternative diagnostic actions, and similarity to earlier scenarios. Corrections create a new draft version with new hashes. Author new, independent families for any later holdout after the workflow is frozen. See the [study plan](../../docs/workflow-study.md).
