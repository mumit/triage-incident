# Encoder transfer results

The expanded frozen MiniLM head matches **48/54** teacher-labeled development decisions, compared with **46/54** for the previous head and **54/54** for a separately run Luna classifier. It retains 14/16 on old development and improves new development from 32/38 to 34/38. Both fine-tuning seeds score lower on combined development. These are inspected synthetic development results, not holdout accuracy.

## Experiment

The previous [regularization experiment](encoder-regularization-results.md) selected L2 `0.001`. This experiment holds that setting, pinned MiniLM, renderer and policy fixed while adding 30 training and 20 development paired mechanisms. The new data varies current supporting versus negated or historical evidence, measurement disagreement, unrelated changes, scope verification, recovery and dependency membership. Observation order varies between families.

Luna reviewed all 100 new inputs blind to author references. Sol audited 16 fixed training cases and all 40 new development cases. The initial overlapping streams hit rate limits: 24 completed review attempts returned HTTP 429. Those attempts remain recorded. Outstanding cases were reviewed serially with at least eight seconds between starts; no serial continuation failed. Consolidation uses the first structurally valid review, never the response closest to the author label. Raw responses, exact attempt inputs, request and response hashes, teacher versions, issues and continuation selection are preserved and verified.

Luna agrees with 60/60 training references and 39/40 development references. Sol agrees with 16/16 audited training references and 40/40 development references. Luna's one different answer keeps core ownership but selects `verify_change` for a confirmed core fault during relevant approved maintenance. Sol selects `inspect_core`. Luna's combination is outside the classifier's seven coupled dispositions. Both variants of this `core_signing_key_change_competition` family are excluded. No teacher flags an input correction or unresolved labeling question.

The accepted release contains 118 training incidents in 59 pairs and 54 development incidents in 27 pairs: the prior 58 training and 16 development cases plus all 60 new training and 38 accepted new development cases. No development incident enters gradient training. Training/development IDs, family IDs and pair IDs are disjoint. Family names do not establish semantic independence. Known overlap with the original catalog includes MTU, link bundles, shared resolver and registry faults, rectifier failures, and scope/recovery themes. Both authoring and subsequent scoring occurred during development.

The excluded core/change pair exposes a model-scope limit: owner, next check and evidence sufficiency need not always map to one of seven coupled combinations. Current agreement covers the supported dispositions only. Keeping the excluded pair visible avoids implying that the classifier can express every plausible teacher decision.

## Candidates

The [predefined plan](../examples/encoder-transfer/plan.json) compares the previous frozen head, two new frozen heads and two end-to-end runs. Both new frozen heads use the same rendered text and frozen embeddings. The structured candidate adds the existing 21 flags. The text-only ablation fits embeddings alone; structured coefficients in its saved compatible head are exactly zero. Priority still comes from supplied structured impact for every encoder, including text-only. It is not a test of priority extraction from text.

Frozen heads use class-balanced multinomial logistic regression at L2 `0.001`, float64 LBFGS and the recorded stationarity threshold. Both converge. Fine-tuning retains AdamW encoder rate `3e-5`, head rate `1e-3`, weight decay `0.01`, batch size 8 and 20 epochs, with seeds 17 and 29. Earliest maximum combined-development agreement selects each checkpoint. Seed 17 selects epoch 15; seed 29 selects epoch 8. Every trial and epoch is preserved.

## Findings

| Candidate | Old development | New development | Combined | Complete combined pairs |
|---|---:|---:|---:|---:|
| Previous frozen head | 14/16 | 32/38 | 46/54 | 19/27 |
| Expanded frozen head + flags | **14/16** | 34/38 | **48/54** | **21/27** |
| Expanded text-only head | 9/16 | 32/38 | 41/54 | 17/27 |
| Fine-tuned MiniLM, seed 17 | 11/16 | **36/38** | 47/54 | 20/27 |
| Fine-tuned MiniLM, seed 29 | 12/16 | 34/38 | 46/54 | 19/27 |
| Luna classifier, separate call | **16/16** | **38/38** | **54/54** | **27/27** |

All local predictions complete. The combined-score gain for the expanded frozen head is two cases. Fine-tuning performs better on the new cohort for seed 17 but loses three old decisions, so aggregate reporting alone would hide the tradeoff. The seven-case structured-versus-text gain supports retaining these features in this configuration; it does not isolate which flag matters or demonstrate architecture superiority.

| Candidate | False domain assignments | False monitoring | Insufficiency precision | Insufficiency recall |
|---|---:|---:|---:|---:|
| Previous head | 1 | 0 | 25/32 | 25/26 |
| Expanded structured head | 5 | 0 | 21/22 | 21/26 |
| Expanded text-only head | 4 | 1 | 21/28 | 21/26 |
| Fine-tuned seed 17 | 2 | 1 | 23/26 | 23/26 |

The expanded head improves total agreement while becoming less conservative: five reference NOC cases receive a fault domain, versus one for the previous head. It also misses confirmed power evidence in a mixed-age case. Remaining errors cover negative radio diagnoses, contradictory power and transport evidence, and negative queue drops. This candidate wins the declared aggregate selection criterion but is not promoted for operational use.

Luna's separate unchanged zero-shot classifier uses the same public inputs and asks only for the four decisions. It resolves to `gpt-6-luna-2026-09-22`, matches 54/54 labels and has no request failures or recorded retries. The frozen head trails by six incidents, or 11.1 percentage points. Teacher labels still came principally from Luna with Sol review; this is teacher transfer, not independently verified accuracy.

Paired comparison against the previous head gives six newly correct and four newly incorrect cases. Its family-bootstrap 95% interval for the agreement change spans -5.6 to +13.0 percentage points. Against Luna, the expanded head's interval spans -18.5 to -3.7 points. These are descriptive resamples of 27 authored pairs after development selection, not production inference. Full paired cases and limits are in [comparison analysis](../examples/encoder-transfer/comparison-analysis.json).

An uncalibrated maximum-probability threshold of `0.8` retains 15/54 development incidents with zero observed errors, only 27.8% coverage. At `0.5`, it retains 48/54 with four errors. These [selective curves](../examples/encoder-transfer/selective-development.json) are evaluated on inspected development, so no threshold or error guarantee is promoted. Abstaining on most cases does not satisfy the full-coverage accuracy objective.

## Latency and cost

The expanded frozen head was measured in one resident process on Apple M3 Pro using PyTorch MPS and cached weights. One complete serial pass warmed every packet. Each configuration then processed the 54 packets ten times. Timings include tokenization, structured features, encoder inference and the head; model load is separate. Every measured decision matches the warmed serial result.

| Batch size | Batch p50 | Batch p95 | Observed throughput |
|---:|---:|---:|---:|
| 1 | 4.5 ms | 5.5 ms | 216 incidents/s |
| 8 | 16.9 ms | 32.3 ms | 415 incidents/s |
| 16 | 32.7 ms | 58.6 ms | 398 incidents/s |

Model load was 444 ms in the existing process and excludes interpreter/library initialization. Luna's per-request p50 was 1,979 ms and p95 3,234 ms through Fuel iX. Its 538-second run deliberately paced requests eight seconds apart after completion; those waits are excluded from per-request latency and cannot estimate maximum hosted throughput. The encoder batch timings likewise exclude queue delay and have no concurrency test. Hardware, proxy capacity, incident length and operational mix differ from a production service.

Offline label review recorded 236,396 prompt and 95,355 completion tokens, 331,751 total, including successful initial and continuation responses. Failed HTTP 429 attempts provided no usage. The separate Luna classifier recorded 50,170 prompt and 6,851 completion tokens, 57,021 total. Invoice charges are unknown because Fuel iX billing rates were not available. Local encoder inference makes no autoregressive calls and consumes no hosted tokens; capacity, training and label maintenance still cost money.

## Evidence and reproduction

[Evaluation evidence](../examples/encoder-transfer/evaluation-01/summary.json) links the training, old, new and combined cohorts with every candidate's cases, labels, predictions, scores and metadata. [Model artifacts](../examples/encoder-transfer/model-artifacts/results.json) preserve both frozen heads, float64 coefficients, feature matrices and both fine-tuning histories. Fine-tuned weights remain in `runs/encoder-transfer/candidates-01/finetuned-17/` and `finetuned-29/` in the managed worktree; reproduction commands refit them elsewhere. Large weights are not committed. The original benchmark and preceding study evidence stay unchanged.

Verify saved review attempts, releases and predictions without new API calls. NumPy/PyTorch are needed for fitting diagnostics:

```bash
python3 scripts/verify_transfer_reviews.py --evidence examples/encoder-transfer/luna-development-01/evidence.json --inputs data/encoder-transfer-v1/development.inputs.jsonl --labels data/encoder-transfer-v1/development.reference.labels.jsonl
python3 scripts/teacher_encoder_evidence.py --inputs examples/encoder-transfer/release-v1/development.inputs.jsonl --labels examples/encoder-transfer/release-v1/development.labels.jsonl --evidence examples/encoder-transfer/evaluation-01/combined-development.evidence.json
python3 scripts/verify_transfer_encoder.py --release examples/encoder-transfer/release-v1 --model-root runs/encoder-transfer/candidates-01 --evidence-root examples/encoder-transfer/evaluation-01
python3 -m unittest discover -s tests -v
python3 scripts/verify_study_closeout.py
```

Refit all four declared local candidates from the pinned model cache into a new directory:

```bash
python3 scripts/run_encoder_transfer_candidates.py --release examples/encoder-transfer/release-v1 --output-dir runs/encoder-transfer-candidates-repeat
python3 scripts/run_teacher_encoder.py --inputs examples/encoder-transfer/release-v1/development.inputs.jsonl --model-dir examples/encoder-transfer/model-artifacts/structured --output runs/encoder-transfer-selected-repeat.jsonl
```

ML versions, device, seeds, hashes and actual training source are retained in metadata. MPS numerical reproducibility across environments is not guaranteed. Reproduction of recorded feature matrices, hashes and scores is verified locally.

## Next steps

The best local candidate still trails Luna despite teacher-reviewed data, weaker regularization, structured features and end-to-end fine-tuning. A separately frozen synthetic stress evaluation can test transfer before more tuning. Define allowed owner/check combinations for real workflows and obtain de-identified tickets with evidence available at triage time and reviewed initial decisions before operational validation. The user confirmed no such dataset is currently available. Production-equivalence claims are blocked by that missing evidence; additional synthetic examples cannot remove this limitation.
