# Northstar Network Bench

A proposed network-operations benchmark and incident-triage workbench comparing Jev, Laya, and CLM-8B using synthetic incidents for **Northstar Networks**, a fictional operator used solely for this project.

## Status

Design stage. No dataset has been generated, no model has been run, and no performance results are claimed. This repository captures the agreed direction before implementation.

## Purpose

Compare how well the three models select an initial investigating domain, apply a supplied priority policy, identify insufficient evidence, and choose the next diagnostic check. Add related-incident matching after the initial workflow is working.

The first scope is **RAN symptoms, transport dependencies, and the next diagnostic check**. The intended users are network operations engineers and technology leaders evaluating decision models.

## Demonstration

A user selects a synthetic incident packet. Three model panels show the selected answers, available probability distributions, and measured end-to-end response times. A reference panel shows the benchmark's accepted answers and supporting evidence. A paired-case view reveals whether a model changes its decision when a material fact changes.

A batch view reports quality, uncertainty, latency, and cost. All displayed results must come from actual recorded runs; example values must be clearly marked as illustrations.

## Documents

- [Project brief](docs/project-brief.md)
- [Synthetic dataset design](docs/dataset-design.md)
- [Evaluation plan](docs/evaluation-plan.md)

## Model references

These are implementation references, not endorsements of vendor benchmark claims.

- Jev: https://typesafe.ai/
- Laya: https://huggingface.co/convaiinnovations/laya
- CLM: https://github.com/Contrastive-LM/CLM

CLM is also described by its authors as a System One model. This project compares individual models and deployment configurations, not training methods in isolation. Pin the exact model versions and Laya checkpoint in every experiment.

## Boundaries

All operator names, topology, assets, incidents, notes, and operational policies will be fictional. Do not incorporate private source documents, actual infrastructure identifiers, or actual operator procedures. The first release recommends diagnostic steps; it does not change network configuration.

Synthetic performance measures consistency with this benchmark. It does not establish production accuracy, actual incident prevalence, or reductions in service-restoration time.
