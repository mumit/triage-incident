# Evaluation plan

This is the target evaluation plan. See [model runs](model-runs.md) for implemented metrics and remaining work. Model inference has not yet been benchmarked; only the keyword baseline has been run.

## Shared task

Give each model identical visible evidence, a versioned benchmark policy, and the same candidate decisions. Preserve equivalent question semantics when adapting API formats. Record any input truncation, unsupported output, timeout, or adapter failure.

## Metrics

- Initial-owner accuracy and macro-F1.
- Priority confusion matrix and severe-incident miss rate under the fictional policy.
- Accepted diagnostic-step accuracy, allowing explicitly recorded alternatives.
- Insufficient-evidence detection precision and recall.
- Related-incident matching precision and recall when that phase is implemented.
- Calibration using Brier score and reliability plots for supported probability outputs.
- Error versus automation coverage after selecting model-specific thresholds on validation data.
- Median and p95 end-to-end latency, throughput, and failure rate.
- Cost per 1,000 incident packets at a stated workload, including self-hosted idle capacity.

Define whether each probability is over candidate answers or represents a separate confidence estimate. Do not treat all exposed confidence fields as interchangeable or invent probabilities for models that do not return them.

## Experimental controls

Pin models, checkpoints, adapters, prompts, policies, hardware, precision, context limits, and serving configurations. Report hosted API latency separately from local model inference time. Test cold and warm caches; CLM can reuse candidate embeddings. Use a rule-based baseline to establish whether a model adds value.

Evaluate unmodified models first. Keep fine-tuning, prompt optimization, and post-hoc calibration in separate experimental tracks with disclosed training data. A hosted model without training access remains an unmodified reference.

Use grouped uncertainty estimates over independent incident families, not individual paraphrases. Report performance by scenario category. A balanced synthetic suite does not estimate production incident frequencies, production calibration, or operational savings.

## Integrity checks before publication

Confirm disjoint split families; reject duplicate or near-duplicate leakage; check that future evidence and labels never enter requests; validate policy-label consistency; verify all reported results against raw run records. Review project files and publication metadata to ensure only the fictional operator identity appears.
