# Northstar Network Bench

A runnable synthetic network-incident benchmark for **Jev, Laya, and CLM-8B**, using **Northstar Networks**, a fictional operator used solely for this project.

The project includes a **local browser comparison app**, **1,064 labeled examples**, a reproducible generator, a model-neutral training exporter, a rule-based baseline, model-server setup scripts, and an evaluation harness. It uses Python 3.10+ with no runtime dependencies. Run commands from this checkout.

**No Jev, Laya, or CLM model results have been measured.** The included results are from the rule-based baseline only. Model adapters have been tested against a local HTTP fixture, not live model servers.

## Browser app

```bash
python3 -m triage_bench.app
```

Open **http://127.0.0.1:8765**. Add Jev credentials in Model settings, select models and incidents, then run a comparison. You can inspect individual decisions and probabilities, compare batch metrics, export JSON, and revisit saved runs.

For a **36 GB Apple Silicon Mac**, use the included Laya and CLM/MLX setup scripts. No paid API keys are needed for those open models. Software setup does not download weights; starting a model server does. The Mac CLM path is documented and contract-tested, but has not been validated with actual weights here.

**[Step-by-step Mac setup and app guide](docs/app.md)**

## CLI quick start

```bash
python -m triage_bench validate
python -m unittest discover -s tests -v
python -m triage_bench run --inputs data/test.inputs.jsonl --output runs/baseline.jsonl
python -m triage_bench evaluate --labels data/test.labels.jsonl --predictions runs/baseline.jsonl --output runs/baseline.metrics.json
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
python -m triage_bench export-training --split train --output runs/training.jsonl
python -m triage_bench export-training --split validation --output runs/validation.jsonl
```

Exports contain `state`, typed `questions`, reference `answers`, and `accepted_answers`. This is a model-neutral supervised format, not a claim of native compatibility with every trainer. Adapt it to the selected training implementation. Hosted model access does not imply fine-tuning access. Test and challenge export are intentionally unavailable from this command.

## Regenerate

```bash
python -m triage_bench generate
python -m triage_bench validate
```

The fixed seed reproduces committed data and checksums. The catalog is in `triage_bench/scenarios.py`. Changes to policy or generation require a versioned dataset release and fresh evaluations.

## Scope and next steps

Implemented decisions: initial investigating domain, policy priority, next diagnostic check, and insufficient evidence. Five owner classes cover radio access, transport, site power, core services and operations. All actions are diagnostic; none changes network configuration.

The generator is scenario-driven, not a network physics simulator. The authored prose often states evidence clearly and is intentionally easier than messy operational tickets. A network specialist has not reviewed these labels. Synthetic scores establish performance on this policy benchmark, not production accuracy or restoration-time savings.

Next work: specialist review, richer structured telemetry and timeline simulation, trained model experiments, validation-selected thresholds, and related-incident matching. The app is an evaluation workbench, not a production incident-management system.

[Project brief](docs/project-brief.md) · [Dataset design](docs/dataset-design.md) · [Evaluation plan](docs/evaluation-plan.md)
