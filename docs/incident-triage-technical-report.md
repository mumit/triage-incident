# Incident triage benchmark: System One models, rules, and GPT-6 Luna

## Finding

On the synthetic Northstar Networks benchmark, GPT-6 Luna and a simple rules baseline made the most complete decisions. Jev and Kev-4B showed useful capability but changed rank across incident families. The tested Laya and CLM-8B deployments rarely made all four decisions correctly without task-specific training. These results justify further experiments, not a production model choice for TELUS.

## Purpose and task

The experiment asks whether a model can make four *initial* triage decisions from the information available at one point in an incident:

1. Assign an investigating owner: radio access (`ran`), transport, power, core, or the network operations centre (`noc`).
2. Set priority from the stated service impact (`P1` to `P4`).
3. Choose one of seven diagnostic actions, including a domain check, change verification, evidence gathering, or monitoring.
4. State whether evidence is insufficient to select a unique investigating fault domain.

An owner is an initial investigation route, not a confirmed root cause. The task does not authorize configuration changes. Related-incident matching is planned but **not part of this evaluation**.

## Data

All **1,064 incidents are synthetic** and belong to a fictional operator. AI-assisted scenario writing and deterministic expansion produced the records. No private TELUS tickets or infrastructure data were used, and no network specialist has certified the labels.

| Set | Records | Authored families | Use in this study |
|---|---:|---:|---|
| Training | 600 | 30 | Available for later specialization; excluded from zero-shot scoring |
| Validation | 220 | 11 | Error analysis and possible future development |
| Test | 220 | 11 | Comparison on different authored families |
| Challenge | 24 | 12 paired interventions across 4 archetypes | Check response to one controlled change at a time |

Each regular family has 20 related realizations. Families do not cross the regular splits, but the 20 realizations share scenario prose and are **not independent incidents**. A public input contains a ticket, timestamped observations, service-impact status and affected-site count, topology excerpt, and change information. Separate answer-key files contain the four labels and rationales; the runner sends only public input and policy to models.

For example, a test incident says that a blown DC fuse isolates one site's radio and router while upstream probes remain healthy. The reference decision is `power / P2 / inspect_power / no`. The example tests initial ownership and the next check, not whether the model can establish a final physical cause. [Dataset card](dataset-card.md) and [sample incidents](samples.md) give the schema and further cases.

## Policy and rules baseline

The fictional policy sets priority directly from structured impact: outage at **10 or more sites is P1**; outage at 1–9 sites or degradation at 10 or more is P2; other degradation or unknown impact is P3; no current unplanned impact is P4. Current, independent domain evidence determines owner and next check. Missing, stale, or conflicting evidence stays with `noc`; recovery or fully explained maintenance can lead to `noc / monitor`. Proximity or change timing alone does not establish cause.

The baseline implements the exact priority rule. For the other fields, it assigns `noc / monitor / no` when impact is `none`. Unknown impact or a small list of uncertainty phrases yields `noc`, an evidence-gathering or change-verification check, and `yes`. Otherwise it scans observation text for domain keywords in this order: **power, core, transport, radio**. A match selects that domain and its diagnostic check; no match stays with `noc / gather_evidence / yes`. It does not reason over the topology graph. Its high score tests whether a model adds value beyond policy code and simple routing, but these keyword rules are tailored to the synthetic templates. See the [full policy](policy.md) and [baseline implementation](../triage_bench/runner.py).

## Experiment design and model choice

All providers saw the same public incidents, policy, and allowed decisions. Jev, Kev-4B, Laya, and CLM-8B used the same typed System One question schema. The selected checkpoints were: hosted Jev (`jev-1.13.0`), local decision-trained Kev-4B, local Laya multilingual, and local CLM-8B with its original decision head and an MLX encoder. They offer different ways to score structured choices, with potential advantages in local deployment, latency, or cost that this benchmark must measure rather than assume. They are **not one interchangeable architecture**. The Laya multilingual checkpoint was selected for its context capacity; the shorter-context English checkpoint could not be assumed to fit these packets. CLM's Mac serving path has not been proven numerically equivalent to upstream vLLM.

We added **GPT-6 Luna through the Fuel iX proxy** because current ticket classification, triage, and routing systems already use LLMs. A lower-cost chat model is a practical reference for both quality and operating cost. The request named `gpt-6-luna` and resolved to `gpt-6-luna-2026-09-22`; it requested `reasoning_effort=none`. Luna received the same facts and choices in a separate zero-shot chat prompt and returned four JSON labels. It received no Northstar examples or tools. The chat prompt and typed API are different interfaces, so the scores compare complete tested configurations, not model architectures under identical tokenization or output mechanics.

“Zero-shot” here means **no Northstar training examples or task-specific few-shot examples**. It does not mean the released checkpoints were never trained on other decisions. Joint accuracy requires all four accepted decisions on one incident; any failed or missing response counts as incorrect. Field accuracy, P1 misses, and paired challenge outcomes expose errors hidden by a single score. All 2,784 final provider-by-incident records were present and scored. The Luna test run recovered an initial rate-limited batch through paced calls; its final test set has no missing results. The [full evaluation](full-zero-shot-evaluation.md) records versions, hashes, field metrics, and run details.

## Results

**Complete incident accuracy: all four decisions correct**

| Provider | Validation, 220 | Test, 220 | Challenge, 24 | Complete challenge pairs, 12 |
|---|---:|---:|---:|---:|
| GPT-6 Luna | 214 (97.3%) | 202 (91.8%) | 23 (95.8%) | 11 |
| Rules baseline | 200 (90.9%) | 200 (90.9%) | 21 (87.5%) | 9 |
| Jev | 112 (50.9%) | 128 (58.2%) | 18 (75.0%) | 6 |
| Kev-4B | 77 (35.0%) | 156 (70.9%) | 18 (75.0%) | 6 |
| Laya | 1 (0.5%) | 4 (1.8%) | 0 | 0 |
| CLM-8B | 0 | 0 | 0 | 0 |

Luna got **every priority right** across 464 evaluated incidents, including all 31 P1 cases. The rules baseline also got every priority right by construction. Luna's test lead over rules was only **2 of 220 incidents**; a bootstrap grouped by the 11 authored test families gives a Luna-minus-rules interval that includes zero. The benchmark does not establish a reliable advantage over rules. Luna's remaining test errors were mostly `radio_neighbor` cases where it chose change verification instead of radio inspection, sometimes retaining the case at `noc`.

Jev and Kev changed rank between the disjoint main splits. Jev led 112 to 77 on validation; Kev led 156 to 128 on test. Both got every P1 priority right, but Jev often escalated P3 to P2, while Kev frequently chose `gather_evidence` or flagged insufficient evidence when a domain was supported. Their challenge performance was also uneven: each passed all priority-boundary and stale-evidence pairs but none of the irrelevant-change-timing or topology-change pairs. This is a stronger warning about decision stability than their 18/24 challenge row scores alone.

Laya and CLM's low joint scores are **not just a consequence of requiring four correct fields**. Both answered `insufficient_evidence=yes` on every case, while the reference says yes for 40/220 in each main split and 6/24 challenge cases. Laya missed every P1 priority across the three sets; CLM missed 30 of 31. CLM also made nearly constant owner and next-check choices. These were completed model responses, not request failures. The finding applies to the pinned checkpoints and serving paths under this question protocol; it does not establish that all Laya or CLM variants cannot learn incident triage.

The rules baseline scored 200/220 on both main splits, but all 20 validation misses came from one family (`radio_receiver`) and all 20 test misses from another (`transport_qos`). Repeated, explicit templates make keyword routing unusually effective. A separate offline calculation replaced only model priority with the exact policy rule: Jev's complete score would become 160/220 on validation and 200/220 on test; Kev's would become 82/220 and 164/220. Those are **hybrid diagnostics, not measured zero-shot model scores**. The rule cannot repair wrong owner or next-check decisions.

## What could improve System One results

1. **Test the interface before changing the model.** On validation families, try compact packets that preserve every decision-relevant fact and clearer, model-specific question and choice wording. Change one factor at a time, record prompt and checkpoint hashes, and check for gains in owner-plus-next-check accuracy rather than only joint score. Check CLM's MLX/vLLM serving parity before attributing all behavior to the model.
2. **Train where access and licenses permit.** Adapt the 600 training records to the supported trainer for Kev, Laya, or CLM; compare specialized checkpoints with their unchanged zero-shot counterparts. Include difficult `noc` versus domain and `gather_evidence` versus domain-check examples. Thirty training families are a small base, so add independently authored, specialist-reviewed families before treating a gain as robust. Hosted Jev inference access does not imply training access.
3. **Build a separate hybrid track.** Compute priority from reliable structured impact fields. Let a model propose owner and next check, and send uncertain or conflicting cases to a human. Select any abstention threshold on validation data and report both the fraction automated and the error rate on that fraction. Do not relabel hybrid gains as raw model gains.
4. **Freeze candidates and evaluate on new families.** The existing test and challenge labels were inspected before Luna was added. A new family-disjoint holdout is needed after prompt, threshold, or training decisions. Include noisy notes, missing telemetry, conflicting evidence, changed topology, and realistic class frequencies.

## Applicability to TELUS

**Do not deploy any of these configurations for unattended TELUS triage based on this study.** The data is fictional, labels lack specialist review, and accuracy on balanced synthetic families does not estimate real ticket mix, handoffs, or operational savings.

For a controlled follow-up, keep **Kev-4B and Jev** as System One candidates, and keep Luna and explicit rules as reference systems. Kev merits testing because it reached 156/220 complete decisions on unseen test families with a local checkpoint; Jev merits testing because it was stronger on validation and provides fast hosted typed decisions. Neither matched the rules baseline consistently. Do not advance unmodified Laya or CLM to an unattended pilot under this protocol. Reconsider them only after a measured interface or training gain on independent families. This is a choice of **what to test next**, not a claim that Kev or Jev is ready for TELUS incidents.

Before a pilot, define acceptance criteria with operations staff: maximum severe-priority miss rate, owner and next-check quality, false escalations, human-review coverage, latency, and cost per 1,000 tickets at expected volume. Audit labels and measure error by incident type and evidence quality. The test-set successful-call p95 latency was 0.21 seconds for Jev, 2.70 for Kev, and 5.21 for Luna, but these are different hosted/local deployments and serial request paths, not a controlled throughput comparison. Fuel iX usage was recorded, but its actual billing and the other providers' full operating costs were not measured. Validate data handling and operational handoff in the intended environment before any live use.

## Evidence and limits

The [case-level evidence snapshot](../examples/full-zero-shot-evaluation.evidence.json) contains labels, predictions, accepted answers, run metadata, and input hashes. The [dataset card](dataset-card.md), [evaluation plan](evaluation-plan.md), and [full evaluation](full-zero-shot-evaluation.md) provide generation, scoring, and reproducibility details. Family-grouped uncertainty is wide with only 11 validation and 11 test families. The synthetic policy makes priority deterministic, and the later-added Luna configuration used a different API prompt after earlier results had been examined. Treat the reported ranking as a finding about **this benchmark and these configurations** until a new, specialist-reviewed holdout confirms it.
