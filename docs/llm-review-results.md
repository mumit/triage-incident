# Blind LLM review of development incidents

Status: completed on 2026-09-29. Luna reviewed all 16 drafts; a second model independently reviewed nine flagged cases. Seven cases passed the conservative candidate filter. Existing inputs, benchmark labels, and encoder weights remain unchanged. These are LLM-reviewed development candidates, not specialist-approved labels or independent accuracy results.

## Purpose and design

Use an autoregressive model offline to review synthetic inputs and propose training labels for an encoder that will run without autoregressive calls. Review disagreements and input quality before training; measure teacher-to-encoder transfer separately from operational accuracy.

Each request contains public facts and the fictional policy. An explicit nested allowlist retains observation text/source/time, impact, decision time, topology, and change information. No draft labels, author rationales, family names, prior model answers, or incident IDs enter the request. Each case is a separate chat with no shared history.

The reviewer returns four decisions, packet citations, a short rationale, input issues, and unresolved labeling questions. Code checks allowed answers, citation paths and quotes, policy priority, and the seven supported owner/check/evidence combinations. It saves the provider response, request hash, requested/resolved model, usage, prompt/renderer/source identities, and errors. All predictions are saved before a separate command opens draft labels.

The first run used requested model `gpt-6-luna`, resolved as `gpt-6-luna-2026-09-22`. The second used requested `gpt-6-sol`, resolved by Fuel iX as `gpt-6.1-sol-2026-09-29`. Both explicitly requested `reasoning_effort=none`; provider usage nevertheless included reasoning tokens. Requests used the same review prompt, serial execution, no warmup or retries, and at least 3.5 seconds between starts. The second reviewer saw only the nine flagged inputs, without Luna's answers, flags, or draft keys.

## Results

| Reviewer | Requested cases | Valid reviews | All four agree with draft | Cases with input issues | Cases with unresolved questions |
|---|---:|---:|---:|---:|---:|
| Luna | 16 | 15 | 15/16 | 8 | 6 |
| Sol, flagged subset | 9 | 9 | 8/9 | 6 | 2 |

Luna's 15 valid reviews matched every draft decision, with no policy-combination errors. Its last review failed citation validation: it quoted the topology edge array as compact JSON while the validator expected the default JSON spacing. The raw answer itself matched the draft, but the strict run records it as failed. This was a citation-format failure, not evidence of invented graph edges. No response was retried or silently repaired.

Luna raised at least one issue on eight otherwise agreeing cases. The remaining seven passed the first candidate filter. Sol agreed with eight of nine draft decision sets, including the case with Luna's citation failure. It disagreed on one next check. Both reviewers agreed on all four decisions in seven of the eight cases where Luna's review was valid; the failed primary case is excluded from that matched comparison.

The second review did not promote additional cases. The filter requires every participating review to be valid and free of input issues, unresolved questions, and policy errors, with matching decisions. Final exports contain **seven candidates and nine pending cases**. The candidates span six of eight draft families and cover five of seven dispositions. They omit both `noc/gather_evidence/yes` and `noc/verify_change/yes`.

This filter is deliberately conservative and is not a calibrated quality threshold. It excludes all uncertainty examples here, so retraining on this subset would introduce a class-selection bias. Candidate exports are preparation artifacts, not a complete training release. All variants of a family must remain in one eventual split even when only some currently pass review.

## Findings about the inputs and rubric

| Mechanism | Review finding | Next action |
|---|---|---|
| Mixed stale/current DC evidence, both variants | Both reviewers flag “services remain down” versus structured `degraded` impact | Write a versioned development correction that reconciles service wording and stated impact, then review it again |
| Queue discard and negation | Luna flags a procedural change-status placeholder; Sol flags it on the negative variant | Replace the placeholder with explicit factual change status, keeping unknown scope unknown |
| Alarm clearance without recovery | Missing domain data correctly supports evidence gathering; reviewers also flag the change placeholder | Preserve the absence of telemetry, clarify change status, and distinguish missing operational evidence from an unlabelable input |
| Conflicting DC measurements | Both reviewers identify the intentionally conflicting readings; the placeholder also needs clarification | Keep the intended contradiction and NOC disposition; the rubric must not require a known fault before accepting an uncertainty label |
| Certificate timing without direct diagnostics | Luna and draft choose `verify_change`; Sol chooses `gather_evidence` | Clarify why change-scope verification is the immediate step, or explicitly adjudicate accepted alternatives |
| Maintenance beyond approved scope | “Confirmed work scope” conflicts with an instruction to verify actual scope | Distinguish approved scope from independently verified actual scope |
| Disconnected alarm in complete dependency graph | Sol correctly retains NOC but also requests confirmation that the unrelated alarm is unrelated | Preserve the graph intervention; refine the rubric so absence from an explicitly complete graph can be valid negative evidence |

LLM review is useful here: it reproduces the provisional decisions while exposing ambiguous authoring. It also over-flags facts intentionally missing or conflicting under the policy. Agreement and reviewability are separate measurements. Neither model has established which initial action is operationally best in the certificate case.

## Usage and limits

Luna reported 18,015 prompt and 16,973 completion tokens over 16 responses, including the citation failure. Sol reported 10,179 prompt and 4,989 completion tokens over nine responses. Total reported usage was 50,156 tokens. Run wall times were 107.1 and 62.7 seconds, including pacing. These measure offline review with explanations and citations, not production classifier latency or invoiced cost. There were no HTTP failures.

The 16 incidents are AI-authored, previously inspected, paired development examples from eight selected mechanisms. Sol evaluated a selected subset, so its 8/9 agreement cannot be compared directly with Luna's 15/16. Same-provider models can share mistakes. Citation existence checks verify quotation fidelity, not whether the cited fact entails the answer. No repeat-consistency experiment, new holdout, or independent operational audit was performed.

Official [evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices#llm-as-a-judge-and-model-graders) supports scalable model review while emphasizing rubric quality and agreement with human annotations. Human review remains a recommended operational audit, not a prerequisite for research using explicitly identified teacher labels.

## Reproduce and verify

The committed [Luna evidence](../examples/review/luna-draft-01/evidence.json), [Sol evidence](../examples/review/sol-draft-01/evidence.json), and [reconciliation](../examples/review/draft-reconciliation-01/reconciliation.json) preserve all outcomes. Raw provider responses and the exact archived reviewer source remain in evidence. Local credentials are excluded.

```bash
python3 scripts/analyze_llm_review.py --evidence examples/review/luna-draft-01/evidence.json
python3 scripts/analyze_llm_review.py --inputs examples/review/luna-draft-01/adjudication.inputs.jsonl --labels examples/review/luna-draft-01/adjudication.labels.jsonl --evidence examples/review/sol-draft-01/evidence.json
python3 scripts/reconcile_llm_reviews.py --primary-dir examples/review/luna-draft-01 --secondary-evidence examples/review/sol-draft-01/evidence.json --verify-dir examples/review/draft-reconciliation-01
python3 scripts/verify_study_closeout.py
```

For a new paid blind review, configure the ignored `.env` with `FUELIX_BEARER_TOKEN` and `LLM_BASE_URL`. Use a new output path. Inference accepts no label-file argument:

```bash
python3 scripts/run_llm_review.py --model gpt-6-luna --env-file .env --output runs/review/luna-draft-02/review.jsonl
python3 scripts/analyze_llm_review.py --predictions runs/review/luna-draft-02/review.jsonl --output-dir runs/review/luna-draft-02/export
```

## Next encoder experiment

1. Refine the review rubric to distinguish defects in the authored record from missing evidence that correctly supports NOC triage. Handle graph citations structurally in a separately versioned protocol; preserve the current failure.
2. Create a new development-input version with factual change status and consistent impact wording. Preserve intentional negation, stale evidence, contradictions, unrelated changes, and disconnected dependencies. Review corrections without providing prior answers.
3. Resolve the certificate diagnostic-action boundary explicitly. Keep a pending status when reviewers disagree; accepted alternatives must preserve valid owner/check/evidence combinations.
4. Add new teacher-reviewed training families covering all seven dispositions, with positive and negative domain evidence using similar vocabulary. Select input features and training settings on separate family-disjoint development data.
5. Freeze the encoder and score unseen families. Report agreement with Luna, agreement with independently adjudicated labels where available, priority failures, complete decisions, and latency/cost at matched coverage. If Luna supplies evaluation labels, call that teacher agreement.

The current head remains frozen. This review enables development without waiting for a specialist, but seven selected cases cannot establish an encoder that matches Luna.
