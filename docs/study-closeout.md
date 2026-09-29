# Northstar comparison study closeout

Status: closed on 2026-09-29. The zero-shot comparison and encoder follow-up are merged in PRs [1](https://github.com/mumit/triage-incident/pull/1) and [2](https://github.com/mumit/triage-incident/pull/2). The archived result files remain reproducible and will not be updated with later experiments.

## Conclusions

The unchanged Jev and Kev deployments showed useful domain routing, but did not consistently match rules or Luna across complete decisions. Laya and CLM were ineffective under the tested zero-shot protocol. These findings apply to the recorded checkpoints and interfaces, including the unverified CLM Mac/reference parity.

The frozen 22.7M MiniLM encoder with a trained head and deterministic priority scored 220/220 validation, 220/220 test, and 18/24 challenge incidents. Luna scored 214/220, 202/220, and 23/24. The encoder's separate policy-guarded variant scored 24/24 challenge incidents after its errors were inspected. That guarded score is post-hoc.

The study demonstrates that task training can remove autoregressive inference from this synthetic classification task. It does not establish production parity, deployment cost, or accuracy on TELUS incidents. Regular families repeat authored prose, labels lack specialist review, and the existing test sets were inspected during earlier work.

## Frozen evidence

- [Full zero-shot evaluation](full-zero-shot-evaluation.md) and [case-level evidence](../examples/full-zero-shot-evaluation.evidence.json).
- [Encoder follow-up](encoder-study.md) and [case-level evidence](../examples/encoder-evaluation.evidence.json).
- [Technical report](incident-triage-technical-report.md).

`examples/comparison-study.closed.json` records SHA-256 identities of the result documents, evidence snapshots, and original dataset files. Run `python3 scripts/verify_study_closeout.py` to verify closure and recompute the original scores. Raw responses and trained weights remain in ignored local directories; they are not part of the portable snapshot.

## Next study

[Encoder versus decomposed Jev workflow](workflow-study.md) starts a separate experiment. Its purpose is to measure complete decisions and errors at a fixed automation coverage on newly reviewed families. The current classifier and old scores remain reference configurations. New prompts, labels, and results belong to the new study.
