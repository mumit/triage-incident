# Encoder versus Jev triage configurations

Status: teacher-trained encoder development complete; no held-out comparison is available. The [new head](teacher-encoder-results.md) reaches 13/16 corrected development agreement, compared with 8/16 for the original encoder. The earlier [Jev results](workflow-jev-development-results.md) use provisional draft labels: decomposed Jev trails the original protocol with policy priority, 11/16 versus 13/16 drafts and 120/220 versus 159/220 validation. The preceding [comparison study is closed](study-closeout.md).

The subsequent [compact input control](compact-jev-results.md) preserves original questions and also trails original Jev with policy priority: 11/16 drafts and 141/220 validation. The [specialist review pack and encoder plan](specialist-review-and-holdout.md) preceded the separately reviewed training experiment. No candidate has been promoted for operational use.

[Blind LLM review](llm-review-results.md) now supports the next development phase: Luna reviewed 16 cases, Sol reviewed nine flagged cases, and seven labels passed a conservative candidate filter. Nine cases remain pending; the filter excludes both uncertainty dispositions and is not sufficient for retraining. Human review is recommended for operational validation, while research can proceed with explicit teacher-label provenance.

The [corrected V2 development cohort](development-v2-results.md) has now been reviewed by both teachers across all 16 cases. Separate offline citation revalidation yields 16 candidate labels, including both uncertainty dispositions. The frozen encoder remains at 8/16. New family-disjoint training data is the next step; this already-inspected cohort remains development material.

The [teacher-trained encoder experiment](teacher-encoder-results.md) now supplies 58 accepted training incidents in 29 paired families. A separate frozen-head candidate improves corrected development agreement to 13/16; end-to-end fine-tuning reaches 11/16. Training and development IDs, pairs and families are disjoint, with conceptual overlap disclosed. The original encoder stays frozen, and unseen-family evaluation remains outstanding.

## Purpose

Determine whether a compact, decomposed Jev workflow can match a trained local encoder on initial incident triage without autoregressive inference. Test where general decision models add value: new evidence wording, ambiguous domain assignments, recovery, change scope, and conflicting observations.

RLCD is TypeSafe's training method, not a common architecture shared by the evaluated models. This study compares concrete configurations.

## Configurations

| Configuration | Semantic decisions | Priority |
|---|---|---|
| Frozen MiniLM reference | Existing seven-class head and feature protocol | Published structured-impact policy |
| Decomposed Jev | Disposition gate and four independent domain-support questions, in one typed request | Same policy |
| Original Jev reference | Original four-question protocol | Model prediction |
| Compact Jev control | Decomposed-workflow input, original four questions and normalization | Model prediction |

Original and compact Jev also have separately saved offline policy-priority diagnostics. These replace only priority from public structured impact, without reading labels or making new model calls.

The primary comparison uses no topology or freshness regex vetoes in the composition code. Jev must interpret those supplied facts. MiniLM retains its original input renderer, which omits graph edges and timestamps. This is a comparison of complete configurations, not an architecture-controlled test. Report that information difference. The original guarded encoder is a secondary reference only; any shared structured guard experiment must be separately identified.

The Jev gate chooses verified monitoring, change verification, evidence gathering, or domain investigation. A domain investigation routes only when exactly one of the four domain questions says current independent evidence supports it. Zero or multiple supported domains retain `noc / gather_evidence / yes`. Code maps a unique domain to its matching diagnostic check and computes priority. Intermediate probabilities are saved; no complete-decision confidence is invented by multiplying them or taking their minimum.

## Data and controls

Use original training and validation data for interface development only. Existing test and challenge data can check regressions, but cannot become a fresh holdout.

Collect newly authored incidents and obtain network-specialist review of inputs, labels, and accepted alternatives. Keep all realizations of each fault mechanism and all pair variants in one split. Compare against the existing scenario catalog for semantic duplication, not just matching IDs. Reserve independent families after development is complete; freeze the model head, prompts, composer, policy, review thresholds, and dataset hashes before scoring that holdout. Do not call an agent-authored or developer-inspected draft an independent specialist-reviewed holdout.

Include negated and conflicting evidence, stale observations mixed with current ones, incomplete and changed dependencies, alarm clearance without verified recovery, unrelated changes, confirmed maintenance scope, and new fault vocabulary. The main accuracy cohort needs realistic frequencies; a separate paired stress cohort can deliberately balance interventions.

Target at least 30 independent development families and 30 new holdout families as an initial planning scale, subject to specialist capacity. This is not a statistical guarantee. Report family-level uncertainty and avoid using hundreds of paraphrases to imply hundreds of independent scenarios.

## Measurements

Report owner and next-check accuracy, all four accepted decisions, insufficient-evidence precision/recall, severe-priority errors, false escalation, and complete challenge-pair accuracy. Every timeout, malformed response, oversized input, or missing record counts as an error.

Repeat a fixed sample to measure decision consistency. Fit each model's review threshold on development data only and compare error at matched automation coverage. Evidence sufficiency is an operational label, not proof that the model's own answer is reliable. This first scaffold does not implement calibrated automation thresholds; all valid responses are scored at full coverage.

Measure Brier scores for the individual Jev question probabilities where reviewed intermediate labels exist. Evaluate encoder probabilities separately if added in a versioned extension. No inference about production calibration follows from the current synthetic sets.

Measure local encoder cold load and warm inference separately from Jev end-to-end API latency. Record failures, token usage, concurrency, serving hardware, throughput, and cost per 1,000 incidents including hosted pricing and local capacity. Keep the existing Luna evidence as historical context; fresh comparative Luna accuracy would require running the same new cohort.

## Current implementation

`triage_bench/workflow.py` defines a compact public-input allowlist, five typed questions, and a deterministic composer. `scripts/run_workflow.py` exports requests for inspection or runs the workflow through the existing failure-inclusive runner. Neither prediction path reads labels. Dry-run files contain public inputs and policy only; do not use them for private tickets without an appropriate data-handling setup.

`data/workflow-study/` contains 16 agent-authored draft incidents in eight pairs and a review checklist. These are development material, not a held-out dataset. Several mechanisms deliberately extend earlier challenges. A specialist must check evidence sufficiency, accepted actions, and scenario similarity before approving any later split. This draft is well below the planned family count and does not have realistic operational class frequencies.

```bash
python3 scripts/run_workflow.py --inputs data/validation.inputs.jsonl --output runs/workflow/request-preview.jsonl --dry-run --limit 5
python3 scripts/run_workflow.py --inputs data/workflow-study/draft.inputs.jsonl --output runs/workflow/draft-request-preview.jsonl --dry-run
python3 scripts/run_study_encoder.py --inputs data/workflow-study/draft.inputs.jsonl --output runs/workflow/encoder-draft.jsonl
python3 scripts/run_workflow.py --inputs data/validation.inputs.jsonl --output runs/workflow/development.jsonl --limit 5
python3 -m triage_bench evaluate --labels data/validation.labels.jsonl --predictions runs/workflow/development.jsonl --output runs/workflow/development.metrics.json
```

Live calls require `TYPESAFE_API_KEY` and default to pinned `jev-1.13.0`. They incur normal provider charges. The default 8,192-token byte-bound preflight is conservative; failures must be recorded rather than silently truncating input. Model and prompt hashes are recorded in run metadata.

The encoder command requires the optional encoder environment and the original trained head. It verifies the head hash against the closed-study evidence, loads cached weights, and reads no labels. Its output on these drafts is a development diagnostic only. For the original Jev reference, use the existing `python3 -m triage_bench run` command with the same new input file.

## Next steps

Keep the original Jev protocol with policy priority as the historical Jev reference and the original encoder frozen. Continue the new encoder experiments using separately reviewed training families. Select candidates and thresholds on development data, freeze artifacts, then run an unseen-family comparison. Neither input compaction nor decomposition justified replacing the Jev reference. Specialist review can strengthen operational validation while research proceeds with teacher-label provenance.

The [development result note](workflow-development-results.md) provides the three-candidate run command and portable evidence export. `scripts/run_workflow_study.py` accepts an explicit local `--env-file`, freezes the encoder head and Jev identifier, and scores only saved predictions. Credential availability is checked before a run directory is created.
