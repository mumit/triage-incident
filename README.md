# Northstar Network Bench

A runnable synthetic network-incident benchmark for **Jev, Kev, Laya, CLM-8B, and a configurable LLM**, using **Northstar Networks**, a fictional operator used solely for this project.

The project includes a **local browser comparison app**, **1,064 labeled examples**, a reproducible generator, a model-neutral training exporter, a rule-based baseline, model-server setup scripts, and an evaluation harness. It uses Python 3.10+ with no runtime dependencies. Run commands from this checkout.

The [full zero-shot evaluation](docs/full-zero-shot-evaluation.md) covers all 220 validation, 220 test, and 24 paired challenge incidents for the rules baseline, Jev, Kev-4B, Laya, CLM, and GPT-6 Luna through Fuel iX. Luna got **214/220 validation, 202/220 test, and 23/24 challenge** incidents fully correct, with no priority errors. The rules baseline got 200/220 on each main split; Jev got 112/220 and 128/220, Kev got 77/220 and 156/220, Laya got 1/220 and 4/220, and CLM got 0/220 on both. The earlier [20-case pilot](docs/zero-shot-study.md) has separate [original](examples/zero-shot-validation20.evidence.json) and [Kev supplement](examples/kev-zero-shot-validation20.evidence.json) snapshots. These are synthetic, family-correlated cases, not estimates of production accuracy. Luna used a later-added chat prompt and the test/challenge labels had previously been examined, so new incident families are needed for a fresh model-selection holdout.

The [technical report](docs/incident-triage-technical-report.md) summarizes the data, experiment, findings, limits, and recommended next experiments for a team discussion.

A [small encoder follow-up](docs/encoder-study.md) trains a frozen 22.7M-parameter MiniLM classifier with no autoregressive inference. It reached 220/220 on both regular evaluation splits; the raw classifier got 18/24 challenge cases and a separately labeled, post-hoc policy-guarded variant got 24/24. These synthetic results need a new specialist-reviewed holdout before operational use.

The [current comparison study is closed](docs/study-closeout.md), with frozen file identities and a verification command. The [next study](docs/workflow-study.md) compares the frozen encoder with Jev input and question configurations. The [development comparison](docs/workflow-jev-development-results.md) scores the encoder at 8/16 drafts, decomposed Jev at 11/16, and original Jev with policy priority at 13/16. The [compact input control](docs/compact-jev-results.md) also trails the original with policy priority: 11/16 versus 13/16 drafts and 141/220 versus 159/220 validation. A [blind specialist review pack](docs/specialist-review-and-holdout.md) is ready; review and new holdout collection remain pending.

The [blind LLM review](docs/llm-review-results.md) uses Luna as an offline label teacher and a second model for flagged cases. It preserves reviewer issues and candidate-label provenance. Autoregressive calls support development; the current encoder still runs locally without them.

The [corrected development V2 review](docs/development-v2-results.md) retains valid uncertainty examples and produces 16 candidate labels across all seven dispositions after a separately recorded citation revalidation. Luna and Sol agree on these corrected inputs; the original frozen encoder remains at 8/16.

The [teacher-trained encoder experiment](docs/teacher-encoder-results.md) adds 58 accepted synthetic training incidents in 29 paired families. A new frozen MiniLM head reaches **13/16** corrected development agreement; end-to-end MiniLM fine-tuning reaches **11/16**. Both run locally without autoregressive calls. These candidates were selected on development data and do not yet match teacher decisions or establish holdout accuracy.

The [bounded regularization experiment](docs/encoder-regularization-results.md) keeps that data and configuration fixed. L2 `0.001` reaches **58/58 training and 14/16 development agreement**, with all five trial fits verified as converged. Broader reviewed data and unseen-family evaluation remain the next steps.

## Browser app

```bash
python3 -m triage_bench.app
```

Open **http://127.0.0.1:8765**. Add Jev credentials or configure the Fuel iX LLM entry in Model settings if you use them, select models and incidents, then run a comparison. You can inspect individual decisions and available probabilities, compare batch metrics, export JSON, and revisit saved runs. To run GPT-6 Luna alone, check **LLM · Fuel iX** and uncheck the other providers; prior runs stay in history.

For a **36 GB Apple Silicon Mac**, use the included Kev, Laya and CLM setup scripts. No paid API keys are needed for those open models. Software setup does not download weights; starting a model server does. The Mac CLM path has been exercised with actual weights and two published MLX reference canaries; numerical equivalence with the upstream vLLM deployment remains unverified.

**[Step-by-step Mac setup and app guide](docs/app.md)**

## CLI quick start

```bash
python3 -m triage_bench validate
python3 -m unittest discover -s tests -v
python3 -m triage_bench run --inputs data/test.inputs.jsonl --output runs/baseline.jsonl
python3 -m triage_bench evaluate --labels data/test.labels.jsonl --predictions runs/baseline.jsonl --output runs/baseline.metrics.json
```

Run output paths are immutable: choose a new filename for a repeat experiment. A model run exits with status 2 when any request fails, while preserving per-record errors for evaluation.

## Dataset

| Split | Records | Authored scenario families |
|---|---:|---:|
| Training | 600 | 30 |
| Validation | 220 | 11 |
| Test | 220 | 11 |
| Challenge | 24 | 4 intervention archetypes, 12 pairs |

Each regular scenario has 20 parameterized realizations. Those realizations vary identifiers, times, surface presentation, and service-impact counts where appropriate. They are **not 1,040 independent fault scenarios**. The challenge pairs test priority boundaries, stale evidence, irrelevant change timing, and topology-dependent ownership.

Public inputs and answer keys are separate JSONL files. The runner reads only inputs and constructs requests with an explicit allowlist. Test labels are supplied for reproducibility, not held secret; keep them out of prompt tuning, calibration and training.

- [Dataset card](docs/dataset-card.md)
- [Sample incidents](docs/samples.md)
- [Fictional operations policy](docs/policy.md)
- [Model setup and evaluation](docs/model-runs.md)
- [Measured baseline results](docs/baseline-results.md)
- [Data files and checksums](data/manifest.json)

## Training export

```bash
python3 -m triage_bench export-training --split train --output runs/training.jsonl
python3 -m triage_bench export-training --split validation --output runs/validation.jsonl
```

Exports contain `state`, typed `questions`, reference `answers`, and `accepted_answers`. This is a model-neutral supervised format, not a claim of native compatibility with every trainer. Adapt it to the selected training implementation. Hosted model access does not imply fine-tuning access. Test and challenge export are intentionally unavailable from this command.

## Regenerate

```bash
python3 -m triage_bench generate
python3 -m triage_bench validate
```

The fixed seed reproduces committed data and checksums. The catalog is in `triage_bench/scenarios.py`. Changes to policy or generation require a versioned dataset release and fresh evaluations.

## Scope and next steps

Implemented decisions: initial investigating domain, policy priority, next diagnostic check, and insufficient evidence. Five owner classes cover radio access, transport, site power, core services and operations. All actions are diagnostic; none changes network configuration.

The generator is scenario-driven, not a network physics simulator. The authored prose often states evidence clearly and is intentionally easier than messy operational tickets. A network specialist has not reviewed these labels. Synthetic scores establish performance on this policy benchmark, not production accuracy or restoration-time savings.

Next work: specialist review, richer structured telemetry and timeline simulation, trained model experiments, validation-selected thresholds, and related-incident matching. The app is an evaluation workbench, not a production incident-management system.

[Project brief](docs/project-brief.md) · [Dataset design](docs/dataset-design.md) · [Evaluation plan](docs/evaluation-plan.md)
