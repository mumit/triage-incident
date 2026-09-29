# Small encoder classifier for incident triage

## Result

A local, non-generative **22.7M-parameter MiniLM encoder** with a trained seven-class linear head made all four Northstar decisions correctly on **220/220 validation and 220/220 test incidents**. It got **18/24** paired-challenge incidents correct. Adding explicit stale-evidence and complete-topology checks raised the challenge score to **24/24**. The checks were added after reviewing those challenge errors, so 24/24 is a **post-hoc development result**, not an independent holdout score.

| Configuration | Validation | Test | Challenge | Complete challenge pairs |
|---|---:|---:|---:|---:|
| MiniLM classifier, raw | 220/220 | 220/220 | 18/24 | 6/12 |
| MiniLM + policy checks | 220/220 | 220/220 | 24/24 | 12/12 |
| GPT-6 Luna via Fuel iX | 214/220 | 202/220 | 23/24 | 11/12 |
| Rules baseline | 200/220 | 200/220 | 21/24 | 9/12 |

An incident counts only when all four decisions are accepted. Both encoder variants made zero P1-priority errors because priority is computed from the explicit policy. Luna also made zero priority errors. The [case-level encoder evidence](../examples/encoder-evaluation.evidence.json) contains predictions, model and head identities, dataset hashes, and latency summaries. `python3 scripts/verify_encoder_evidence.py` recomputes every reported encoder count from the committed labels and predictions.

## Model and data flow

The pretrained encoder is [`sentence-transformers/all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), pinned to revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. It is frozen. Mean-pooled, normalized embeddings feed a seven-way logistic classifier trained on the 600 Northstar training realizations from 30 families. The head also sees seven simple features: the four structured impact-status values and three indicators for change, recovery, and missing/stale/conflicting evidence. The chosen feature scale and logistic regularization were selected with the 220 validation incidents. No test or challenge label enters training or inference.

The seven classes are the four domain owners with their corresponding diagnostic check and sufficient-evidence flag, plus `noc / gather_evidence / yes`, `noc / verify_change / yes`, and `noc / monitor / no`. This enforces compatible owner, check, and evidence outputs. Code computes priority from structured impact using the published policy. **The system is an encoder classifier plus deterministic policy, not a single learned four-output model.** It makes no autoregressive call and uses no text generation at inference.

The compact input uses current observation details, structured impact, and a topology note. It omits duplicate ticket prose and opaque IDs. The raw encoder does not inspect graph edges. Its six challenge misses were three stale power observations that it treated as current and three transport alarms disconnected from all affected sites in the supplied graph. The guarded variant vetoes a domain assignment only when the sole domain evidence is explicitly stale with no current telemetry, or a declared complete topology shows that no affected site depends on the alarmed uplink. Six challenge records were changed; no validation or test prediction changed.

## Runtime and comparison limits

The raw classifier's successful-call p95 on the 220-record test was **9.6 ms**; the guarded variant's was **7.2 ms**. These serial, warm, per-incident measurements used Apple MPS and exclude model loading. The model's 22.7M parameters are about two orders of magnitude fewer than Kev-4B. Luna's test p95 was 5.21 seconds through Fuel iX, but its hosted network path and protocol differ; these timings are **not a controlled speedup measurement**. No production throughput, serving cost, or cold-start service SLO was measured.

This is a small, AI-authored synthetic benchmark with 20 correlated realizations per regular family. The rules baseline already scored 200/220 on each main split, which shows how explicit the templates are. The test and challenge labels had been analyzed in earlier work. We did not tune the encoder head on test predictions in this experiment, but the test set is not a pristine model-selection holdout. The guarded challenge score is especially optimistic because those checks were added after its errors were inspected. Neither the 100% regular-set scores nor the local latency establish TELUS production accuracy.

## Reproduce and show in the app

The optional encoder environment needs NumPy, scikit-learn, PyTorch, and Transformers. The [app setup guide](app.md#7-set-up-the-local-minilm-encoder) gives the virtual-environment commands. The tested local environment used Python 3.12, PyTorch 2.8.0, Transformers 5.17.0, scikit-learn 1.9.1, and Apple MPS; scripts do not require a hard-coded Python version. The first training run downloads the pinned encoder from Hugging Face. The model weights remain in the Hugging Face cache; the trained head is saved under ignored `runs/encoder/minilm-v1/`. Neither artifact is committed. Inference loads cached weights only and makes no network call.

```bash
python3 scripts/train_encoder.py
python3 scripts/run_encoder.py --split validation --output runs/encoder/minilm-v1/validation.predictions.jsonl
python3 scripts/run_encoder.py --split test --output runs/encoder/minilm-v1/test.predictions.jsonl
python3 scripts/run_encoder.py --split challenge --output runs/encoder/minilm-v1/challenge.predictions.jsonl
python3 scripts/run_encoder.py --split challenge --guards policy-v1 --output runs/encoder/minilm-v1/challenge.guarded.predictions.jsonl
```

Prediction outputs are immutable; use a new path for a repeat run. To use the browser app, start it with the same Python environment, then select **MiniLM encoder** or **MiniLM + policy**. Set `ENCODER_MODEL_DIR` if the trained head is elsewhere. The app does not train the model automatically. The two entries make raw-model and guarded-system results visible side by side with Luna and the other providers.

The next validation should use **new specialist-reviewed incident families**, including negated evidence, incomplete topology, stale and fresh telemetry together, ambiguous change timing, and realistic class frequencies. Freeze the classifier, guards, and thresholds before that holdout. Report complete-decision accuracy, severe misses, pair consistency, calibration and review coverage, p95 latency, throughput, and cost on the intended serving hardware.
