# Encoder transfer development catalog

100 synthetic incidents: 60 in 30 new training pairs and 40 in 20 new development pairs. Training contains six radio, six transport, six power, six core, three change-scope and three recovery pairs. Development contains three pairs per fault domain, two change-scope pairs, two recovery pairs, and four interventions covering mixed-age evidence, contradictory measurements, graph membership and diagnosis competing with recent change.

Domain pairs retain similar vocabulary while changing the current diagnostic support. Observation order varies between families. Several radio cases include independently verified unrelated remote-lab work. Change packets omit actual completion time while work is in progress. Public facts and provisional author references are separate JSONL files. Live reviewers receive public facts and policy only.

Family names and split assignment were recorded before reviews and model scoring. These are synthetic, developer-inspected development materials, not independently sourced incident families. Concepts overlap earlier data. Known examples include transport MTU with the original `transport_mtu` family, link-bundle routing with `transport_lag`, shared resolvers with `core_dns`, service registries with `core_service_discovery`, rectifier faults with `power_rectifier`, and scope/recovery/graph/negation themes with the previous paired development sets. Distinct IDs do not establish semantic independence.

Teacher evidence and accepted releases are under `examples/encoder-transfer/`. Preserve complete pairs together. Do not reinterpret these cases as holdout data after model selection or inspect their outcomes to claim production accuracy. The balanced paired mixture differs from operational incident frequencies.

Reproduce into a new directory:

```bash
python3 scripts/prepare_encoder_transfer.py --output-dir runs/encoder-transfer-data-repeat
```
