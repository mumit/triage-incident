# Synthetic dataset design

This document describes the target design. The current release uses authored evidence scenarios and parameterized realizations rather than a physical topology-and-timeline simulator. See [the dataset card](dataset-card.md) for implemented behavior and limitations.

## Generation method

Create a fictional topology and incident timeline first. Render ticket text and operator notes from the resulting facts. Keep the latent simulated cause separate from evidence visible to the model.

Each example represents a decision at a specific timestamp. Only evidence available by that time may appear in its input. Eventual repair notes and confirmed causes belong in hidden evaluation metadata, if retained at all.

## Proposed record fields

- `id`, `incident_family_id`, `topology_family_id`, `split`, and `decision_timestamp`.
- `input`: ticket title and description, timestamped operator notes, alarm observations, KPI observations, relevant topology, maintenance/change records, known service impact, and candidate diagnostic checks.
- `policy_version`: the fictional policy supplied to the model.
- `labels`: initial owner, priority, next check, and insufficient-evidence flag.
- `accepted_answers`: alternative valid decisions where the evidence does not justify a unique answer.
- `label_rationale`: evidence and policy rules supporting the labels; never passed to a tested model.
- `generation_metadata`: seed, generator version, scenario category, and source scenario identifiers; never passed to a tested model.

Specify exact enumerations, units, thresholds, and schemas before generating the release. Do not label a speculative root cause as confirmed.

## Splits

Provide separate training, validation, and test files. Group all paraphrases, timeline snapshots, and counterfactual relatives of an incident in the same split. Separate topology families to prevent memorizing asset dependencies.

Use validation data for threshold selection and calibration. Keep test labels unavailable to prompt tuning and training. A separate challenge set should test unfamiliar combinations, missing evidence, misleading notes, maintenance exceptions, and multiple acceptable actions.

Report both record counts and independent family counts. Additional paraphrases do not create independent incidents. Version 0.1.0 contains 600 training, 220 validation, 220 test and 24 challenge records; family counts are disclosed in the dataset card.

## Label quality

Write the fictional operations policy before assigning labels. Validate timestamp ordering, topology consistency, physical units, and label-policy agreement. Distinguish an initial investigating domain from a confirmed fault domain. Permit uncertainty and multiple accepted checks rather than forcing an unsupported unique answer.

A network specialist should review a sample before interpreting benchmark results as evidence of operational suitability. Synthetic labels reflect the simulator and policy, and can contain mistakes.

## Packaging

Planned outputs: JSONL split files, a human-readable preview, machine-readable schemas, policy, dataset card, reproducible generator, and integrity checks. Release records and labels in a layout that prevents accidental label inclusion in inference inputs.

Use only Northstar Networks as the operator identity. Use fictional asset names and reserved documentation address ranges where addresses are required. Do not imply that the fictional topology represents any real network.
