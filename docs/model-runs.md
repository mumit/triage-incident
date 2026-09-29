# Running the models

For the browser app and local Laya/CLM setup on a 36 GB Apple Silicon Mac, start with [the app guide](app.md). This page covers the lower-level CLI.

The runner uses the shared `POST /v1/systemone` wire format with `state`, `model`, and `questions`. Owner, priority, and next check are Choice questions. Insufficient evidence is a binary Noul question; its returned probability is converted to yes/no for scoring. Answer distributions and provider confidence are retained separately. No probability is fabricated for the baseline. Kev uses the same request and scoring path, with its own provider identity and deployment metadata.

This format was checked against the [Jev quickstart](https://docs.typesafe.ai/introduction/quickstart), [Laya model card](https://huggingface.co/convaiinnovations/laya), and [CLM repository](https://github.com/Contrastive-LM/CLM). Compatibility tests use a local HTTP fixture. The [20-case pilot](zero-shot-study.md) and [full zero-shot evaluation](full-zero-shot-evaluation.md) record live comparisons. Those results establish behavior for the measured deployments and prompts only; CLM Mac/reference numerical parity remains unverified.

## Configure a deployment

Set up the model according to its upstream documentation. Supply the actual endpoint and model identifier accepted by that deployment. Use environment variables for API keys; do not commit them. The repository does not download model weights, purchase hosting, or invoke paid APIs automatically.

Example Jev invocation, after setting `TYPESAFE_API_KEY`, `JEV_MODEL`, and `CONTEXT_TOKENS` in your shell:

```bash
python3 -m triage_bench run \
  --provider jev --model "$JEV_MODEL" \
  --endpoint https://api.typesafe.ai/v1/systemone --key-env TYPESAFE_API_KEY \
  --context-tokens "$CONTEXT_TOKENS" --deployment 'Hosted API; record version and client region here' \
  --inputs data/validation.inputs.jsonl --output runs/jev-validation.jsonl
```

Example local Laya invocation, after setting the deployed model identifier and context capacity:

```bash
python3 -m triage_bench run \
  --provider laya --model "$LAYA_MODEL" \
  --endpoint http://127.0.0.1:8000/v1/systemone \
  --context-tokens "$CONTEXT_TOKENS" --deployment 'Record checkpoint, runtime, hardware and precision here' \
  --inputs data/validation.inputs.jsonl --output runs/laya-validation.jsonl
```

For local Kev, start `scripts/start_kev_mac.sh` after setup, then use `--provider kev`, model `kev-latest`, endpoint `http://127.0.0.1:8009/v1/systemone`, and the checkpoint revision reported by `/v1/models` in deployment metadata. The [20-case pilot supplement](zero-shot-study.md) used the original `runs/app/b80756a81ff248c9/inputs.jsonl` and matching labels without rerunning paid Jev calls; its Kev predictions are in app run `3ed6c46570454f2b`. Keep Kev's zero-shot results separate from any later Northstar-trained Kev checkpoint.

For CLM use `--provider clm`, the deployed CLM identifier, and its endpoint (the upstream default server port is 8700). All four model provider names use the same transport adapter; selecting a name does not start or configure a model server. Add `--key-env VARIABLE_NAME` if a self-hosted endpoint requires authentication.

Pin the Laya checkpoint rather than silently routing between checkpoints. The English checkpoint's short context is unlikely to fit full benchmark requests. The runner conservatively compares serialized UTF-8 request bytes plus a 512-token reserve against your declared token capacity. This intentionally overestimates most token counts and can reject requests that would actually fit. It does not verify the server's tokenizer or configured truncation behavior. Configure and independently verify adequate capacity for every deployment; do not simply increase the CLI declaration to bypass a short server limit.

Use `--limit 3` for a connection smoke test. Do not present its score against the full answer key as a full benchmark: unattempted examples correctly count as missing errors. Omit the limit for benchmark runs. The runner is serial and does not warm up. Typed decision providers are not retried; the LLM chat adapter retries HTTP 429 up to four times with backoff and records the retry count per successful incident. Results mix first-call and subsequent cache states; use separate controlled experiments for cold/warm or concurrency comparisons.

## Evaluate

```bash
python3 -m triage_bench evaluate \
  --labels data/validation.labels.jsonl \
  --predictions runs/jev-validation.jsonl \
  --output runs/jev-validation.metrics.json
```

Use matching files for the test and challenge sets. Scores include failed and missing records. Reports include confusion matrices, macro-F1, joint correctness, P1 misses, probability coverage, Brier score, reliability bins, descriptive coverage/error curves, paired correctness, family bootstrap intervals, and successful-call latency percentiles. Raw responses, usage when provided, requested/resolved model identifiers and run metadata are saved alongside predictions.

The coverage curves use the selected answer's probability, not a provider's separate confidence estimate. They are descriptive fixed-threshold evaluations, not fitted calibration. Select any deployment threshold using validation data and freeze it before test evaluation. Automatic threshold fitting is not implemented yet.

The runner normalizes two-decimal answer distributions when their sum differs from one by no more than the maximum independent rounding error for the number of options. It records the original sum beside that prediction; larger discrepancies remain per-record errors. Run metadata includes a question-schema hash. Compare runs with different hashes as separate prompt protocols, including runs created before the binary question replaced the yes/no Choice question.

Token usage and wall time are recorded, but monetary cost and load-test throughput are not estimated in this release. Cost requires actual endpoint pricing or hosting costs and workload utilization. Compare hosted end-to-end latency separately from local inference measurements.

## Training

`export-training` emits model-neutral examples for training or validation only. Adapting them to Laya or CLM training code, training weights, and post-hoc calibration are subsequent experiments. Keep those experiments separate from unmodified models. Do not assume Jev fine-tuning is available through hosted inference access.
