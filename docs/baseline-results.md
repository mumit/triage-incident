# Baseline results

These are measured outputs of the included keyword router and deterministic priority rule, not outputs of Jev, Laya or CLM-8B. Raw predictions and metrics are in `examples/`.

| Measure | Test result |
|---|---:|
| initial_owner accuracy | 90.9% |
| priority accuracy | 100.0% |
| next_check accuracy | 90.9% |
| insufficient_evidence accuracy | 100.0% |
| All four decisions correct | 90.9% |
| P1 misses | 0.0% of 16 P1 cases |

Challenge: 87.5% of records have all fields correct; 75.0% of pairs have both records fully correct.

The baseline solves priority directly from structured impact fields. Its high score on the regular test indicates that the first release is relatively easy. It fails the topology intervention because keyword rules do not interpret the dependency graph. These results are a starting reference, not evidence of realistic operational performance.

No calibration score is available because the baseline emits decisions without probabilities. Its microsecond local function timing is not comparable with a hosted model round trip. Family counts, rather than row counts alone, should guide interpretation.
