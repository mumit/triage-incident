# Accepted teacher training release

58 synthetic incidents in 29 paired families, across all seven dispositions. Luna supplied labels from blind public-packet review; Sol audited a fixed 14-case selection. Both variants of `change_edge_acl_scope` were excluded because Luna flagged an ambiguous end timestamp. No specialist has independently adjudicated these labels.

`train.labels.jsonl` contains the teacher's decisions, not copied author references. `decisions.json` records each input's review issues and audit status; `manifest.json` records hashes and family exclusion. The corrected development V2 cohort is kept out of training.

See [results and reproduction](../../../docs/teacher-encoder-results.md). Rebuild into a new directory:

```bash
python3 scripts/export_teacher_training.py --inputs data/teacher-training-v1/train.inputs.jsonl --labels data/teacher-training-v1/reference.labels.jsonl --primary-evidence examples/teacher-training/luna-01/evidence.json --audit-evidence examples/teacher-training/sol-audit-01/evidence.json --audit-inputs examples/teacher-training/audit-inputs/inputs.jsonl --audit-labels examples/teacher-training/audit-inputs/reference.labels.jsonl --output-dir runs/teacher-release-repeat
```
