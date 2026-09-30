# Teacher-trained encoder results

The new frozen MiniLM head matches **13/16 teacher-reviewed development decisions**, compared with **8/16** for the original encoder. End-to-end MiniLM fine-tuning reaches **11/16**. Both run locally without autoregressive inference. Neither matches the teachers on this cohort, and neither has been evaluated on an unseen-family holdout.

## Experiment

Train a small classifier from offline LLM-reviewed incidents, keeping the corrected 16-case development cohort out of gradient training. Predict seven supported owner/check/evidence dispositions with a 22.7M-parameter MiniLM encoder. Compute priority from the existing structured-impact policy.

The new catalog contains 60 synthetic incidents in 30 paired mechanism families: 24 domain-support pairs across radio, transport, power and core; three change-scope pairs; and three recovery pairs. Both variants retain domain vocabulary while changing the evidence that supports a decision. New mechanisms include fronthaul clocks, forwarding loops, busbar joints and replica quorum failures.

Luna reviewed all 60 public packets without seeing reference labels, family names or prior predictions. Sol reviewed 14 incidents in seven full families selected during the primary review, before scoring references. The audit spans all dispositions; it was a fixed selection, not a random sample. Review schema, exact evidence citations and policy consistency were checked locally.

| Reviewer | Requested model | Resolved model | Valid reviews | Author-decision agreement |
|---|---|---|---:|---:|
| Primary | `gpt-6-luna` | `gpt-6-luna-2026-09-22` | 60/60 | 60/60 |
| Audit | `gpt-6-sol` | `gpt-6.1-sol-2026-09-29` | 14/14 | 14/14 |

Luna flagged one ACL change input: `ended_at` is in the future while status is `in_progress`, without distinguishing planned from actual completion. Sol did not flag it. The release filter still excludes both variants of that family. The accepted release contains **58 incidents in 29 families**, covers all seven dispositions, and uses the primary teacher's decisions. Author labels serve only as review diagnostics. No failed requests or invalid citations occurred in these 74 reviews.

Training and development incident, pair and family IDs are disjoint. Conceptual themes deliberately overlap, and no independent reviewer has established semantic family independence. Both sets are authored synthetic material. Teacher agreement measures consistency with these labels, not independently verified network accuracy.

## Candidates

Both new candidates use the same 512-token renderer, mean pooling, normalized embeddings and 21 structured features. The renderer retains observation text, age, impact, graph edges and change facts. Features describe impact, freshness, change status and graph connectivity. Connectivity is an input to the learned head; it does not impose an output veto. Priority remains deterministic. Inference reads public inputs and local model artifacts only.

The original encoder retains its old renderer, which omits timestamps and graph edges. Its comparison therefore measures a complete configuration change, including inputs, training data and features. It does not isolate the effect of teacher training.

The frozen-head experiment fits class-balanced logistic regression on pinned `sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. Four L2 settings were recorded before scoring. Maximum complete development agreement selects the candidate; the first trial wins ties.

| L2 | Training agreement | Development agreement |
|---:|---:|---:|
| 0.01, selected | 40/58 | 13/16 |
| 0.1 | 32/58 | 6/16 |
| 1 | 29/58 | 4/16 |
| 10 | 29/58 | 4/16 |

After preserving those results, a separate end-to-end candidate trains encoder weights and a linear head with AdamW: encoder learning rate `3e-5`, head rate `1e-3`, weight decay `0.01`, batch size 8, balanced loss, seed 17 and 20 epochs. Development is scored each epoch; the earliest maximum selects epoch 14. That checkpoint matches **57/58 training cases**. Later epochs reach 58/58 training agreement but do not improve development agreement. The full history is preserved in [metadata](../examples/teacher-training/encoder-finetuned-v1/metadata.json).

## Development findings

The [corrected development cohort](development-v2-results.md) contains 16 previously inspected incidents in eight paired families. Luna and Sol agree on all 16 after the separately recorded citation revalidation. Those reviews supply the target labels here; they are offline teacher evidence, not a new production-LLM benchmark.

| Configuration | All four decisions | Owner | Priority | Next check | Evidence flag | Complete pairs |
|---|---:|---:|---:|---:|---:|---:|
| Original frozen encoder | 8/16 | 8/16 | 16/16 | 8/16 | 8/16 | 1/8 |
| New frozen encoder head | **13/16** | 13/16 | 16/16 | 13/16 | 13/16 | **5/8** |
| End-to-end MiniLM, epoch 14 | 11/16 | 12/16 | 16/16 | 11/16 | 12/16 | 4/8 |

Every prediction completed; there were zero failed or missing records. Priority is correct by construction from supplied impact, so this result does not measure priority extraction from raw tickets.

The better candidate makes three errors:

| Development case | Teacher decision | New head decision |
|---|---|---|
| Normal current DC measurements with stale fault evidence | NOC, gather evidence | Power, inspect power |
| Queue-drop hypothesis ruled out by current counters | NOC, gather evidence | Radio, inspect radio |
| Current confirmed core certificate failure | Core, inspect core | NOC, verify change |

Its evidence-insufficiency precision is 5/6 and recall is 5/7. It incorrectly assigns a domain to two reference NOC cases. Fine-tuning raises insufficiency recall to 6/7 but lowers precision to 6/9 and makes five complete-decision errors: contradictory power measurements, maintenance scope, both unrelated-change/radio variants and a connected transport dependency.

These results support further encoder development but do not show that small-model training automatically transfers decision logic. The frozen head underfits the reviewed training set. Fine-tuning fits that set closely while making more development errors. With only 29 training families and eight development families, both fitting and generalization remain unresolved. The next candidate should test weaker head regularization and more diverse paired training material, with every added trial recorded. No development case should be inserted into training to remove its observed error.

## Latency and cost

Measurements use an Apple M3 Pro, macOS 26.6.2 and PyTorch MPS, serial local inference, cached weights and no explicit warmup. Model load excludes interpreter and ML-library imports. There are only 16 development requests per run.

| Run | Model load | All-request p50 | All-request p95 | p50 after first request | p95 after first request |
|---|---:|---:|---:|---:|---:|
| New frozen head, serial repeat | 1,788 ms | 5.2 ms | 67.8 ms | 5.2 ms | 7.9 ms |
| Fine-tuned encoder | 292 ms | 6.2 ms | 203.0 ms | 6.2 ms | 12.5 ms |

The original new-head development and training runs overlapped; their timings are preserved but excluded from this table. The serial repeat reproduced all 16 head decisions. Different checkpoint loaders and small samples prevent interpreting load differences as an architecture advantage. These are local diagnostics, not service throughput or p95 guarantees. Training uses padded batches; serial unpadded inference reproduced selected scores, with small floating-point probability differences possible.

Offline labeling used 105,857 prompt tokens and 49,482 completion tokens, 155,339 total across Luna and Sol. Token usage is recorded evidence, not an invoice; proxy billing rates were not available. Serving the classifiers incurs no hosted-model call or token charge, but local capacity, training and ongoing label maintenance still cost money. Probabilities have not been calibrated for automatic acceptance.

## Evidence and reproduction

[Development evidence](../examples/teacher-training/development.evidence.json) preserves the original reference, both new candidates and the serial head repeat. [Training evidence](../examples/teacher-training/training.evidence.json) preserves both selected candidates. Each includes labels, per-case predictions, failures, timings, input hashes, selection history and model identities. [Primary reviews](../examples/teacher-training/luna-01/evidence.json), [audit reviews](../examples/teacher-training/sol-audit-01/evidence.json) and the [release manifest](../examples/teacher-training/release-v1/manifest.json) retain review provenance and exclusion decisions.

Verify without model calls:

```bash
python3 scripts/teacher_encoder_evidence.py --inputs examples/review/development-v2-reviewed-release/candidate.inputs.jsonl --labels examples/review/development-v2-reviewed-release/candidate.labels.jsonl --evidence examples/teacher-training/development.evidence.json
python3 scripts/teacher_encoder_evidence.py --inputs examples/teacher-training/release-v1/train.inputs.jsonl --labels examples/teacher-training/release-v1/train.labels.jsonl --evidence examples/teacher-training/training.evidence.json
python3 -m unittest discover -s tests -v
python3 scripts/verify_study_closeout.py
```

Use an encoder environment with NumPy, PyTorch and Transformers and the pinned model already cached for fitting. Run from this checkout, using a new output directory:

```bash
python3 scripts/train_teacher_encoder.py --train-inputs examples/teacher-training/release-v1/train.inputs.jsonl --train-labels examples/teacher-training/release-v1/train.labels.jsonl --dev-inputs examples/review/development-v2-reviewed-release/candidate.inputs.jsonl --dev-labels examples/review/development-v2-reviewed-release/candidate.labels.jsonl --output-dir runs/teacher-head-repeat
python3 scripts/run_teacher_encoder.py --inputs examples/review/development-v2-reviewed-release/candidate.inputs.jsonl --model-dir runs/teacher-head-repeat --output runs/teacher-head-repeat/development.jsonl
python3 scripts/teacher_finetune.py train --train-inputs examples/teacher-training/release-v1/train.inputs.jsonl --train-labels examples/teacher-training/release-v1/train.labels.jsonl --dev-inputs examples/review/development-v2-reviewed-release/candidate.inputs.jsonl --dev-labels examples/review/development-v2-reviewed-release/candidate.labels.jsonl --output-dir runs/teacher-finetune-repeat --epochs 20
python3 scripts/teacher_finetune.py predict --inputs examples/review/development-v2-reviewed-release/candidate.inputs.jsonl --model-dir runs/teacher-finetune-repeat --output runs/teacher-finetune-repeat/development.jsonl
```

The compact new head is saved with its metadata under `examples/teacher-training/encoder-head-v1/`. Fine-tuned weights remain in the managed worktree at `runs/teacher-training/encoder-finetuned-v1/`; they are not committed. Refit them to reproduce the experiment in another checkout. Metadata records hashes of the exact evaluated artifacts and archived training sources. Seeds and versions are recorded; bit-identical MPS retraining across environments is not guaranteed. Boundary validation was strengthened after fitting, and the existing training release passes it; the archived source records the actual fitting implementation.

## Next steps

Keep the original closed-study artifacts unchanged and retain the new frozen-head candidate as the current development reference. Add teacher-reviewed training families that test unsupported domain vocabulary, conflicting measurements, unrelated changes and confirmed domain evidence despite recent changes. Compare weaker head regularization before expanding fine-tuning. Freeze the selected model, renderer, policy and acceptance thresholds before scoring newly collected unseen families. Network-specialist review remains valuable for operational validation; research can continue with explicit teacher-label provenance.
