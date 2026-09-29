# Corrected development inputs and V2 review

Status: completed on 2026-09-29. Both models reviewed all 16 corrected incidents independently. All returned decisions agree with the provisional references and each other. One original Luna review failed citation validation; a separately recorded offline revalidation clears that failure without a new model call. The reviewed candidate release contains all 16 cases, all eight families, and all seven dispositions. The frozen encoder still matches 8/16.

## Changes

The [development V2 dataset](../data/workflow-study/development-v2/README.md) preserves the original draft files and gives corrected incidents new IDs. Family and pair IDs remain unchanged across versions. A before/after change log and hashes identify the corrections.

Both mixed-DC variants now say services remain impaired with partial availability, consistent with their unchanged structured `degraded` impact. The generic change-status placeholder is replaced by factual fictional status or an explicit statement that activity is unknown. Maintenance records distinguish approved scope from independently verified actual scope.

The certificate variant now states that approved renewal scope includes the affected endpoint but actual deployment coverage is unverified. This adds a relevant fictional fact after inspecting the prior reviewer disagreement. It supports change-scope verification under the existing policy. Agreement on this revised incident does not resolve the old incident independently.

Domain negation, missing current telemetry, conflicting measurements, and complete-graph membership interventions remain intact. The provisional reference decisions are unchanged; they are opened only after blind review output is saved.

## Review protocol

`northstar-blind-llm-review-v2` distinguishes authoring defects that prevent a policy label from diagnostic uncertainty that supports a NOC disposition. It does not require missing telemetry to be supplied, conflicting current measurements to be reconciled, or unrelated assets to be inserted into an explicitly complete graph. Ambiguous impact or equally justified actions can still remain pending.

The public-input allowlist and four decisions are unchanged. Citation validation compares quoted arrays/objects by JSON structure, with strict types; quoted strings may be exact substrings or an exact JSON string value. Invented facts and paths still fail validation. The original V1 prompt, strict citation behavior, evidence, and failed responses remain reproducible.

Luna and Sol independently reviewed the full cohort rather than a selected dispute subset. Each case was a separate chat containing policy and public facts only. Neither reviewer received labels, previous answers, previous issue lists, family names, or incident IDs. This independence concerns the requests; related models can share errors.

Requested models resolved as `gpt-6-luna-2026-09-22` and `gpt-6.1-sol-2026-09-29`. Both requests set `reasoning_effort=none`, though reported usage included reasoning tokens. Two serial runners operated concurrently, each with at least 3.5 seconds between starts, no warmup, and no retries. There were 32 new calls and no HTTP failures.

## Results

| Configuration or artifact | Valid records | All four agree with reference | Complete pairs | Candidate records |
|---|---:|---:|---:|---:|
| Luna, original V2 run | 15/16 | 15/16 | 7/8 | 15 |
| Sol, original V2 run | 16/16 | 16/16 | 8/8 | 16 |
| Two-reviewer reconciliation, original outcomes | 15/16 matched valid | 15/16 | 7/8 | 15 |
| Two-reviewer reconciliation after offline revalidation | 16/16 matched valid | 16/16 | 8/8 | 16 |
| Frozen MiniLM encoder + policy priority | 16/16 | 8/16 | 1/8 | Not a label reviewer |

Both reviewers raised zero input issues or unresolved labeling questions under V2. All 15 matched valid reviews in the original runs agreed on all four decisions; the separately revalidated pair raises that to 16. The clearer facts and revised rubric changed together, so their effects cannot be separated. Reduced flag counts do not independently establish better label quality.

Luna's recovery-case failure came from quoting the string status as JSON `"none"`. The V2 rubric permits the JSON form of a scalar, but its initial validator did not accept that string form. Code now accepts an exact JSON string value. A separate offline diagnostic revalidated the saved provider response and preserved the original `error` status, error message, raw response, request hash, and copied latency. No labels or new model call were needed. The old failed run remains frozen; its count remains 15/16.

The final candidate distribution is five evidence-gathering cases, two each for power, transport, monitoring, change verification, and radio, plus one core case. This removes the first review's complete exclusion of uncertainty dispositions. It still contains only eight selected, correlated mechanisms and is far too small to establish generalization.

## Encoder diagnostic

The original MiniLM head and renderer were loaded from the pinned checkpoint/cache and run without autoregressive calls. All 16 predictions succeeded. Owner, next-check, and evidence-flag agreement each remained 8/16; structured-policy priority remained 16/16. The model still matched one complete pair. Repeated authoring cleanup did not repair its handling of the new evidence patterns.

These predictions were generated from the corrected inputs. Old predictions were not rescored as if they saw the corrections. The [portable encoder evidence](../examples/review/encoder-development-v2.evidence.json) records the frozen head and dataset hashes. This is a development diagnostic, not a fresh holdout or a trained model improvement.

## Usage and limits

Luna reported 23,367 prompt and 11,771 completion tokens; Sol reported 23,367 prompt and 6,617 completion tokens. Total reported usage was 65,122 tokens, including the failed citation response. Wall times were 78.6 and 76.2 seconds including pacing, with the two runners overlapping. These are offline review measurements, not classifier latency or invoiced cost. Offline derivation copies request latency and excludes revalidation time.

Corrections and rubric design used prior misses and review flags. References were known to developers. Both teachers are related models accessed through one gateway. Citation fidelity does not prove entailment, and agreement does not establish operational correctness. The candidate release remains LLM-reviewed development material with no specialist audit. Original closed-study evidence, original draft inputs, and encoder weights remain unchanged.

## Verification

```bash
python3 scripts/analyze_llm_review.py --inputs data/workflow-study/development-v2/development.inputs.jsonl --labels data/workflow-study/development-v2/reference.labels.jsonl --evidence examples/review/luna-development-v2-01/evidence.json
python3 scripts/analyze_llm_review.py --inputs data/workflow-study/development-v2/development.inputs.jsonl --labels data/workflow-study/development-v2/reference.labels.jsonl --evidence examples/review/luna-development-v2-revalidated-01/evidence.json
python3 scripts/analyze_llm_review.py --inputs data/workflow-study/development-v2/development.inputs.jsonl --labels data/workflow-study/development-v2/reference.labels.jsonl --evidence examples/review/sol-development-v2-01/evidence.json
python3 scripts/reconcile_llm_reviews.py --all-cases --inputs data/workflow-study/development-v2/development.inputs.jsonl --labels data/workflow-study/development-v2/reference.labels.jsonl --primary-dir examples/review/luna-development-v2-revalidated-01 --secondary-evidence examples/review/sol-development-v2-01/evidence.json --verify-dir examples/review/development-v2-reviewed-release
python3 scripts/workflow_evidence.py --inputs data/workflow-study/development-v2/development.inputs.jsonl --labels data/workflow-study/development-v2/reference.labels.jsonl --evidence examples/review/encoder-development-v2.evidence.json
python3 scripts/verify_study_closeout.py
```

For a new paid run, use `scripts/run_llm_review.py --protocol v2` with a new output path and ignored local Fuel iX credentials. `scripts/prepare_reviewed_development_v2.py` reproduces the dataset in a new directory. `scripts/revalidate_llm_review.py` derives offline validation outcomes while preserving source responses and hashes. No command overwrites existing benchmark labels.

## Next encoder experiment

Use this cohort for development selection and error analysis. Keep it out of a fresh generalization claim. Collect at least 30 new training mechanisms spanning all seven dispositions, with similar domain vocabulary paired with positive, negative, stale, and conflicting evidence. Keep paired variants, paraphrases, and corrected versions of each mechanism together. The 30-family target is a planning scale, not a statistical guarantee.

Use Luna as the primary offline teacher, Sol for independent review of disagreements and an audit sample, and policy/citation checks throughout. Preserve input, prompt, requested/resolved model, raw review, and label hashes. Reject unresolved labelability problems without excluding ordinary NOC evidence insufficiency.

Start with a new trained head and an explicit renderer that supplies freshness and dependency information, then compare end-to-end encoder training if the frozen embeddings still fail. Freeze settings after development selection. Reserve new families for teacher-agreement evaluation after selection, and label that metric as teacher agreement. Report independent adjudication separately when available.

The 16 reviewed cases are now suitable development material. They are not a family-disjoint training/validation pair and cannot alone demonstrate an encoder matching Luna. No model was retrained in this step.
