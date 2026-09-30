# Encoder regularization results

Reducing L2 regularization from `0.01` to **`0.001`** raises training agreement from **40/58 to 58/58** and development agreement from **13/16 to 14/16**. All five fits pass the recorded stationarity check. The selected head runs locally without autoregressive inference. It still falls short of the teachers' 16/16 agreement on this inspected development cohort.

## Experiment

This experiment keeps the [teacher-training release](teacher-encoder-results.md), corrected development inputs, labels, pinned MiniLM weights, renderer, structured features, feature scale, class-balanced objective and priority policy unchanged. Only head regularization varies across a predefined five-value grid. No additional teacher calls or training examples were used.

The [plan](../examples/encoder-regularization/plan.json) was saved before fitting. The best complete development agreement among converged fits selects the head; grid order breaks ties. Development contains 16 previously inspected synthetic incidents in eight pairs. Training contains 58 incidents in 29 families. Neither training fit nor selection on this cohort establishes unseen-family accuracy.

## Results

| L2 | Training agreement | Development agreement | Complete development pairs | Gradient infinity norm | Iterations |
|---:|---:|---:|---:|---:|---:|
| 0.01, control | 40/58 | 13/16 | 5/8 | 9.08e-9 | 49 |
| 0.003 | 49/58 | 12/16 | 4/8 | 8.85e-9 | 50 |
| **0.001, selected** | **58/58** | **14/16** | **6/8** | 6.60e-9 | 60 |
| 0.0003 | 58/58 | 13/16 | 6/8 | 9.19e-9 | 99 |
| 0.0001 | 58/58 | 12/16 | 5/8 | 9.86e-9 | 160 |

Serial inference from every saved float32 head reproduces the float64 fitting decisions on training and development. All 370 predictions complete without failures or missing records. For the selected head, owner, next check and evidence flag each match 14/16; priority matches 16/16 by construction from supplied structured impact. Evidence-insufficiency precision and recall are both 6/7. There is one false domain assignment and no false monitoring decisions.

The selected head fixes two errors from the previous head: normal current DC readings alongside stale fault evidence, and a confirmed core certificate fault. It retains the negative queue-drop error, now assigning transport rather than radio. It introduces an error on one confirmed radio-fault variant with an unrelated change, assigning NOC/gather evidence. The other radio variant remains correct. The net improvement is one development case, or 6.25 percentage points; this small selected sample cannot establish a reliable advantage on new incidents.

## Convergence

The previous trainer allowed 200 LBFGS iterations and used PyTorch's default loss-change tolerance. This experiment allows 1,000 iterations, retains strong-Wolfe line search and gradient tolerance `1e-8`, and tightens loss-change tolerance to `1e-15`. Every trial starts from zero weights and bias on the same once-computed feature matrices.

Convergence requires the largest absolute gradient component of the training objective to be at most `1e-7`. The objective is convex multinomial logistic loss with positive L2 weight regularization; stationarity therefore provides a useful optimization check. Saved float64 coefficients permit recomputing gradients independently of the inference head's float32 rounding. Model artifacts, matrices, data and source hashes are recorded.

The previous saved float32 head has gradient norm `1.56e-6`, above the new threshold. Its objective exceeds the converged `0.01` control by approximately `3.88e-10`, and both produce the same 40/58 training and 13/16 development counts. The stricter control reproduces all previous categorical predictions on both cohorts. This supports regularization, rather than incomplete optimization, as the cause of the observed training underfit. Loss values across different L2 settings should not be ranked as the same objective.

## Evidence and reproduction

[Training evidence](../examples/encoder-regularization/training.evidence.json) and [development evidence](../examples/encoder-regularization/development.evidence.json) retain every trial's per-case predictions, summaries, probabilities, timings and metadata. [Results](../examples/encoder-regularization/results.json) record fitting diagnostics and selection. All five compact inference heads, float64 fitting coefficients, exact feature matrices and the archived fitting source are committed under `examples/encoder-regularization/`.

Verify with NumPy and PyTorch in the encoder environment. Verification recomputes stationarity, scores, head conversion, evidence summaries and selection without model loading or API calls:

```bash
python3 scripts/verify_encoder_regularization.py --directory examples/encoder-regularization
python3 scripts/verify_study_closeout.py
python3 -m unittest discover -s tests -v
```

Refit with the pinned MiniLM already cached, using a new directory:

```bash
python3 scripts/train_encoder_regularization.py --train-inputs examples/teacher-training/release-v1/train.inputs.jsonl --train-labels examples/teacher-training/release-v1/train.labels.jsonl --dev-inputs examples/review/development-v2-reviewed-release/candidate.inputs.jsonl --dev-labels examples/review/development-v2-reviewed-release/candidate.labels.jsonl --output-dir runs/encoder-regularization-repeat
```

Run the committed selected head with the existing predictor, which reads no labels:

```bash
python3 scripts/run_teacher_encoder.py --inputs examples/review/development-v2-reviewed-release/candidate.inputs.jsonl --model-dir examples/encoder-regularization/l2-0.001 --output runs/encoder-regularization-selected-development.jsonl
```

Local execution used the same Apple M3 Pro, PyTorch MPS embeddings and CPU float64 head fitting as the prior experiment. Each candidate's development inference follows its training inference in the same process; these warmed diagnostic timings are not an independent service benchmark. Dependencies and artifact hashes are in each head's metadata. Recomputed MPS embeddings can vary numerically across environments; committed matrices permit direct verification of the recorded fits.

## Next step

Use `0.001` as the current development reference and preserve the previous head. Further L2 reduction fits training perfectly without improving development. Expand training and development with separately reviewed paired mechanisms and varied wording, then test transfer. Retain the existing development cohort for diagnostics. Freeze the chosen configuration before evaluating unseen families against a separately run Luna classifier. A larger dataset and stronger evaluation are now more useful than extending this grid on the same 16 cases.
