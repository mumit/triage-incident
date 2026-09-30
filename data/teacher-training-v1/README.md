# Paired teacher-training drafts

Sixty synthetic incidents in 30 authored mechanism families, with two variants per family. Twenty-four domain-support pairs cover radio, transport, power, and core; three pairs cover change scope and three recovery verification. Domain words occur in both supported and unsupported variants.

`train.inputs.jsonl` contains public facts. `reference.labels.jsonl` contains provisional author decisions, supplied to the scorer only after reviews are saved. `families.json` lists family identities and conceptual overlap limits; `manifest.json` records reproducible file hashes. Neither this catalog nor its references are independently sourced operational data.

The new mechanism names differ from the corrected 16-case development cohort. Evidence-sufficiency themes deliberately overlap. An independent network specialist has not established that all mechanisms are distinct. Keep both variants, all paraphrases, and future corrected versions of one mechanism together.

Teacher review output and accepted labels are separately versioned under `examples/teacher-training/`. Raw errors, disagreements, and audit outcomes are preserved. These files do not change the original benchmark or establish a new holdout.
