# Compact Jev input control

Status: development runs completed on 2026-09-29. All 236 new requests succeeded and resolved to `jev-1.13.0`. Questions, model, renderer, and thresholds were unchanged throughout these runs. The 16 drafts have unreviewed AI-authored labels; the 220 validation cases were already used in development. Neither cohort is a holdout.

## Finding

Compact input did not improve complete triage when priority was controlled. Original Jev with policy priority scored **13/16 drafts and 159/220 validation**. Compact Jev with the same priority policy scored **11/16 and 141/220**. The original protocol with policy priority remains the Jev reference for the next experiment. The encoder remains frozen pending specialist review and new training families.

With model-predicted priority, compact Jev scored 114/220 validation versus 112/220 original. That small aggregate gain concealed improved priority prediction and worse ownership, diagnostic check, and evidence decisions. It does not support advancing the compact configuration.

## Control

`triage_bench/compact_jev.py` sends exactly the state string used by the decomposed workflow, with the original four questions and original response normalization. It predicts priority directly. A separately saved offline diagnostic replaces only priority using public structured impact and the published policy; it reads no labels and makes no model call.

The compact state retains decision time, observation detail/source/time, structured impact, topology edges/note, and change status/scope/time/detail. It removes other packet fields and moves policy into the serialized JSON. Relative to original Jev, this changes field presence, duplication, serialization, and policy placement. Relative to decomposed Jev, it changes questions and answer composition. This is a control for that complete input transformation, not a test of length alone or model architecture.

## Complete decisions

All four decisions must match accepted answers. Both variants must pass for a complete pair.

| Configuration | Draft, 16 incidents | Complete pairs, 8 | Validation, 220 incidents |
|---|---:|---:|---:|
| Frozen MiniLM + policy priority | 8 (50.0%) | 1 | 220 (100.0%) |
| Original Jev, model priority | 8 (50.0%) | 3 | 112 (50.9%) |
| Compact Jev, model priority | 8 (50.0%) | 3 | 114 (51.8%) |
| Original Jev + policy priority, offline diagnostic | 13 (81.3%) | 5 | 159 (72.3%) |
| Compact Jev + policy priority, offline diagnostic | 11 (68.8%) | 4 | 141 (64.1%) |
| Decomposed Jev + policy priority | 11 (68.8%) | 4 | 120 (54.5%) |

Original, decomposed, and encoder results are reused from the preceding studies. The original Jev validation run had one HTTP 520 failure, counted wrong in both raw and derived scores. Compact runs had zero failures or missing outputs. Replacing compact priority changed six draft answers and 39 validation answers, adding three and 27 complete incidents respectively. Successful derived priorities all match policy by construction. Raw responses remain preserved; derived output removes obsolete priority probabilities and confidence.

## Field and family results

| Cohort and configuration | Owner | Priority | Next check | Evidence flag |
|---|---:|---:|---:|---:|
| Draft, original | 13/16 | 10/16 | 14/16 | 15/16 |
| Draft, compact | 11/16 | 10/16 | 11/16 | 13/16 |
| Validation, original | 185/220 | 130/220 | 159/220 | 194/220 |
| Validation, compact | 166/220 | 181/220 | 146/220 | 177/220 |

Raw compact and original Jev got the same eight drafts completely correct. With policy priority, compact lost both unrelated-change radio variants and gained no drafts. On validation, compact with policy priority lost 20 incidents and gained two relative to original with policy priority. Most losses came from `power_transfer`: 3/20 complete versus 20/20. Both configurations still scored zero complete decisions in each radio family. A shorter packet did not resolve those domain errors.

Compact raised 43 false evidence-insufficient flags on validation versus 25 original. Both detected all 40 positive flags, so precision fell from 61.5% to 48.2%. False domain assignments rose from 11 to 14. On drafts, compact made three false domain assignments among nine NOC cases, matching original, and raised two false evidence flags versus zero original. Neither configuration incorrectly selected monitoring in these cohorts.

The validation difference with policy priority was -8.18 percentage points. Resampling the 11 families gives a descriptive 95% bootstrap interval of -24.09 to +0.45 points. The draft difference was -12.5 points, concentrated in one of eight selected families, with an interval of -37.5 to 0. These small, synthetic, correlated cohorts do not establish a production ranking or statistical precision for deployment.

## Latency and usage

| Cohort | Original p95 | Compact p95 | Original reported input tokens | Compact reported input tokens |
|---|---:|---:|---:|---:|
| Draft | 201.3 ms | 279.1 ms | 20,724 | 20,292 |
| Validation | 253.5 ms | 246.4 ms | 312,437 | 298,387 |

Latency covers successful serial API calls, with no warmup or retries. Runs occurred at different times with uncontrolled serving conditions; these measurements establish no speedup. Original validation usage covers 219 successful calls; compact covers 220, so token totals have different successful-call denominators. Compact reported 3,162 draft and 43,551 validation output tokens. Reported usage is not an invoice. Derived runs copy model-call latency and exclude offline priority computation.

## Evidence and reproduction

Portable snapshots contain case-level predictions, provisional labels, summaries, usage, and protocol hashes: [draft](../examples/compact-jev-draft.evidence.json) and [validation](../examples/compact-jev-validation.evidence.json). Verify without model calls:

```bash
python3 scripts/workflow_evidence.py --evidence examples/compact-jev-draft.evidence.json
python3 scripts/workflow_evidence.py --inputs data/validation.inputs.jsonl --labels data/validation.labels.jsonl --evidence examples/compact-jev-validation.evidence.json
python3 scripts/analyze_workflow_evidence.py --evidence examples/compact-jev-validation.evidence.json --inputs data/validation.inputs.jsonl --labels data/validation.labels.jsonl --output runs/workflow/compact-validation-analysis-new.json
python3 scripts/verify_study_closeout.py
```

To repeat the paid control, configure `TYPESAFE_API_KEY` in an ignored local `.env` and choose new output directories:

```bash
python3 scripts/run_workflow_study.py --cohort draft --providers jev_compact --env-file .env --output-dir runs/workflow/compact-draft-02
python3 scripts/run_workflow_study.py --cohort validation --providers jev_compact --env-file .env --output-dir runs/workflow/compact-validation-02
python3 scripts/derive_policy_priority.py --inputs data/workflow-study/draft.inputs.jsonl --source runs/workflow/compact-draft-02/jev_compact.jsonl --output runs/workflow/compact-draft-02/jev_compact_policy.jsonl
```

No compact repeat consistency run was performed. Input changes and noncontemporaneous calls prevent attributing the degradation to a specific field or serialization choice. Old test/challenge and Luna results were not rerun. The closed-study reports, snapshots, and model head remain unchanged.

## Next steps

Complete the [blind specialist review](specialist-review-and-holdout.md), adjudicate revisions, and preserve reviewed development provenance. Then collect new training and family-disjoint development incidents for an encoder that distinguishes positive, negative, conflicting, and stale evidence. Reserve independently reviewed unseen families after candidate selection. Reviewed versions of these already-inspected drafts remain development data.
