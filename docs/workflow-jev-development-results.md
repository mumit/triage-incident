# Jev workflow development comparison

Status: development results collected on 2026-09-29. All Jev responses resolved to `jev-1.13.0`. No model, question wording, composer, or threshold was changed after these runs. The 16 draft incidents have unreviewed AI-authored labels. The 220 original validation cases were previously used in development. Neither cohort is a holdout.

## Finding

The decomposed Jev workflow does **not** improve on the original protocol when priority is computed by the same policy. On drafts, it scored 11/16 versus 13/16 for the original protocol with only priority replaced. On validation, it scored 120/220 versus 159/220. The latter are offline diagnostics from saved original responses, not new zero-shot scores.

The original Jev protocol with deterministic priority is the strongest configuration measured on these 16 drafts. The frozen encoder still leads on the original validation templates, but its score falls to 8/16 on drafts. This is evidence of dataset sensitivity, not a production model ranking.

## Complete decisions

An incident passes only when all four choices match the recorded accepted answers. A pair passes only when both incidents pass.

| Configuration | Draft incidents, 16 | Complete draft pairs, 8 | Original validation, 220 |
|---|---:|---:|---:|
| Frozen MiniLM + policy priority | 8 (50.0%) | 1 | 220 (100.0%) |
| Decomposed Jev + policy priority | 11 (68.8%) | 4 | 120 (54.5%) |
| Original Jev, model priority | 8 (50.0%) | 3 | 112 (50.9%) |
| Original Jev + policy priority, offline diagnostic | 13 (81.3%) | 5 | 159 (72.3%) |

The frozen encoder validation score is reused from the closed-study run. All Jev results in this table are from new calls. The draft main runs had zero failures or missing records. The original-protocol validation run had one HTTP 520 response; it counts as incorrect in both original and policy-diagnostic scores. The other validation runs had no failures or missing records.

Replacing only priority corrected six original Jev draft predictions and 89 successful validation predictions. This added five complete draft decisions and 47 complete validation decisions. No owner, next check, or evidence answer was changed. Source predictions and raw probabilities remain preserved; derived output removes the original priority probability and confidence fields because they no longer describe the final priority.

## Field results

| Draft configuration | Owner | Priority | Next check | Evidence flag |
|---|---:|---:|---:|---:|
| Frozen encoder | 8/16 | 16/16 | 8/16 | 8/16 |
| Decomposed Jev | 12/16 | 16/16 | 11/16 | 12/16 |
| Original Jev | 13/16 | 10/16 | 14/16 | 15/16 |
| Original Jev + policy priority | 13/16 | 16/16 | 14/16 | 15/16 |

| Validation configuration | Owner | Priority | Next check | Evidence flag |
|---|---:|---:|---:|---:|
| Frozen encoder | 220/220 | 220/220 | 220/220 | 220/220 |
| Decomposed Jev | 139/220 | 220/220 | 120/220 | 139/220 |
| Original Jev | 185/220 | 130/220 | 159/220 | 194/220 |
| Original Jev + policy priority | 185/220 | 219/220 | 159/220 | 194/220 |

The policy diagnostic has 219 correct validation priorities because its failed source request remains an error. All successful requests have policy-correct priority.

## What decomposition changed

The workflow asks one disposition gate and four domain-support questions. It assigns a domain only if the gate requests investigation and exactly one support probability reaches 0.5. It produces compatible owner/check/evidence triples, while the original protocol predicts those fields independently.

On the draft queue-discard incident, the gate selected investigation and transport support was 0.86. Core support was also 0.74, so the composer retained NOC and requested evidence. This rejected a supported transport diagnosis under the draft reference. The original protocol with policy priority got both queue variants correct.

Both decomposed radio drafts retained NOC despite current independent receive-chain evidence and verified unrelated change scope. On validation, the workflow got zero complete decisions in each of `transport_route`, `radio_scheduler`, and `radio_receiver`; it got only 1/20 in `power_battery` and `noc_scope`. The errors are concentrated by family rather than spread evenly.

The workflow did improve some draft handling: both mixed DC variants were correct, while the original protocol retained power on the normal-current-DC variant. It also handled the contradictory-measurement and verified-recovery pairs. However, both Jev protocols assigned transport to the disconnected complete-graph variant. The domain questions did not solve graph dependency interpretation.

Decomposition trades false domain assignment for more evidence-gathering decisions. On drafts, it assigned a domain incorrectly in 1/9 NOC cases, compared with 3/9 for the original protocol and 5/9 for the encoder. Its evidence-insufficient flag had 66.7% precision and 85.7% recall. The original protocol had 100% precision and 85.7% recall; the encoder had 40.0% and 28.6%. On validation, the workflow raised **81 false insufficient-evidence flags** among 180 negative cases, versus 25 for the original protocol. Missing or failed answers count against recall but are not treated as positive flags.

The comparison changes both question decomposition and input rendering. The compact workflow preserves timestamps and graph edges, omits duplicate ticket prose and opaque IDs, and constrains the final triple. The encoder omits timestamps and graph edges. This experiment cannot attribute differences to decomposition alone. A compact original-question variant would be needed to isolate input rendering from question design.

## Repeatability and runtime

The draft workflow repeat reproduced all 16 final categorical decisions. The original-protocol repeat reproduced all 15 successful matched decisions, with one HTTP 520 response. The failed repeat case had already been incorrect in the main run, so its aggregate score remained 8/16. Identical scores alone would not have established repeatability; the matched case decisions were checked. Two passes over 16 drafts are a small repeatability diagnostic, not a service reliability guarantee.

There were 504 attempted Jev requests across main and repeat runs, with two HTTP 520 failures retained and no missing outputs. The published main draft scores use the first run; repeat responses do not replace them.

Successful-call p95 on validation was 285.0 ms for the decomposed workflow and 253.5 ms for the original protocol. The encoder's reused validation p95 was 6.3 ms on local Apple MPS, excluding load. Different deployments and run conditions prevent a controlled speedup claim. Policy-diagnostic latency is copied from its source model call and excludes the offline derivation.

Jev reported 291,347 input tokens for the decomposed validation run and 312,437 for the original validation run's successful responses. No provider invoice or controlled cost comparison was collected. No autoregressive or Luna calls were made in this follow-up. Historical Luna scores belong to the earlier cohorts and cannot be attached to these drafts.

## Evidence

- [Draft comparison snapshot](../examples/workflow-development-comparison.evidence.json), including both repeat runs and primitive Jev answers.
- [Validation comparison snapshot](../examples/workflow-validation-comparison.evidence.json).
- [Encoder draft error analysis](workflow-development-results.md).

```bash
python3 scripts/workflow_evidence.py --evidence examples/workflow-development-comparison.evidence.json
python3 scripts/workflow_evidence.py --inputs data/validation.inputs.jsonl --labels data/validation.labels.jsonl --evidence examples/workflow-validation-comparison.evidence.json
python3 scripts/verify_study_closeout.py
```

The verifier recomputes failure-inclusive scores and checks that each policy diagnostic derives from its recorded source with only priority changed. The analysis script produces per-family counts, matched repeat comparisons, and family-bootstrap intervals. With only eight selected draft families, those intervals describe these development examples; they are not production confidence bounds.

## Next experiment

Retain the original Jev protocol with deterministic priority as the leading Jev development candidate. Preserve this failed decomposition attempt rather than tune it on the same drafts and present the result as generalization.

Prepare a compact original-question variant to isolate input effects, and add specialist-reviewed training families that teach negative, conflicting, and mixed-current evidence to the encoder. Keep the frozen encoder as a reference. Select any automation thresholds on development data and report error at matched coverage; no such calibration was performed here. Freeze candidates before evaluating new family-disjoint, specialist-reviewed incidents.
