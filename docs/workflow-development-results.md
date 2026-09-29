# Workflow study development results

Status: initial encoder diagnostic on 2026-09-29. The subsequent [Jev comparison](workflow-jev-development-results.md) is now complete. This note preserves the first encoder error analysis. This is not a holdout result. The 16 synthetic inputs and their provisional labels were authored and inspected by an AI agent, with no specialist review.

## Result

The unchanged MiniLM encoder made all four decisions correctly on **8/16 incidents** and **1/8 complete pairs**. It previously scored 220/220 on each regular Northstar split. These draft cases are harder for the frozen configuration and show why the earlier perfect scores did not establish generalization.

| Configuration | All four | Owner | Priority | Next check | Evidence flag | Complete pairs |
|---|---:|---:|---:|---:|---:|---:|
| Frozen MiniLM + policy priority | 8/16 | 8/16 | 16/16 | 8/16 | 8/16 | 1/8 |
| Decomposed Jev + policy priority | 11/16 | 12/16 | 16/16 | 11/16 | 12/16 | 4/8 |
| Original Jev protocol | 8/16 | 13/16 | 10/16 | 14/16 | 15/16 | 3/8 |

There were zero failed or missing encoder predictions. A second fresh run reproduced every categorical decision. Both reference P1 priorities were correct by construction; this does not measure the model's ability to recognize severe service impact from raw tickets.

## Errors

| Draft pair | Correct variants | Error |
|---|---:|---|
| Mixed stale/current DC evidence | 1/2 | Assigns power despite current normal DC measurements and missing diagnostic evidence |
| Voice queue discard | 1/2 | Assigns transport when current captures and counters explicitly show no discard |
| Alarm clearance and service probes | 1/2 | Assigns core to continued service failure with no domain evidence |
| Contradictory electrical measurements | 1/2 | Assigns power despite unresolved disagreement between current sources |
| Shared-service certificate | 1/2 | Assigns core from a recent certificate change without current diagnostics |
| Maintenance scope | 2/2 | Both verified planned suspension and unexplained extra impact match draft labels |
| Unrelated change and radio evidence | 0/2 | Chooses change verification despite confirmed radio evidence and unrelated work scope |
| Graph dependency membership | 1/2 | Retains NOC for the connected uplink variant; renderer omits graph edges |

The classifier incorrectly assigns a fault domain to **5/9 reference NOC incidents**. It detects evidence insufficiency in 2/7 positive cases and raises 3 false flags among nine negative cases: precision 40.0%, recall 28.6%. It never incorrectly chooses monitoring in this cohort. These counts are descriptive and use unreviewed labels.

The errors are consistent with a classifier using domain vocabulary and change indicators without robustly distinguishing negative, conflicting, and current evidence. That is an error-pattern interpretation, not a causal explanation of its internal representations. No head weights, input features, or guard logic were changed after this evaluation.

## Evidence and limits

The [portable draft evidence](../examples/workflow-encoder-draft.evidence.json) records every provisional label, prediction, latency, dataset identity, and original head identity. Verify with:

```bash
python3 scripts/workflow_evidence.py --evidence examples/workflow-encoder-draft.evidence.json
python3 scripts/verify_study_closeout.py
```

The first run's p95 was 376.7 ms across only 16 calls; it excludes model loading and includes first-inference effects. It is not a serving latency estimate or directly comparable with the earlier 220-case warm-run summaries. The repeated run confirms decisions, not a throughput or consistency guarantee for all incidents.

The eight pairs share earlier challenge concepts and do not follow production class frequencies. Labels and alternative actions require specialist review. MiniLM's original renderer omits timestamps and graph edges; Jev's new request preserves them. That input difference must be reported in any comparison.

## Continue the comparison

Configure `TYPESAFE_API_KEY` in a local ignored `.env` file. Run these commands in the encoder Python environment, using a new output directory:

```bash
python3 scripts/run_workflow_study.py --cohort draft --providers encoder jev_workflow jev_original --env-file .env --output-dir runs/workflow/draft-comparison-01
python3 scripts/workflow_evidence.py --evidence runs/workflow/draft-comparison-01/evidence.json --run encoder_frozen runs/workflow/draft-comparison-01/encoder.jsonl --run jev_workflow runs/workflow/draft-comparison-01/jev_workflow.jsonl --run jev_original runs/workflow/draft-comparison-01/jev_original.jsonl
```

Run development validation separately with `--cohort validation`. Preserve the first complete Jev workflow run before changing wording or thresholds. The study runner scores all requested records, including missing or failed predictions, after inference is complete. Jev calls use pinned `jev-1.13.0`; the runner does not accept a moving model alias.

Specialist review and new family-disjoint holdout collection remain outstanding. The [completed development comparison](workflow-jev-development-results.md) records Jev's results and the separate priority-only diagnostic; it does not establish held-out or production performance.
