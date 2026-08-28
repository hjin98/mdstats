# P1 source map — V7 neutral scientific substrate

This map is the P1-A implementation target. It does **not** replace current
DATA2/DATA3/DATA5 runtime specifications. Current prepare/select-target-size
orchestration remains on the old architecture until P4.

Parent authority: `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md`.
Package contract: `P1_NEUTRAL_SCIENTIFIC_SUBSTRATE.md`.

## Scientific identity chain

```text
precise provenance (descriptive / advisory by default)
  -> canonical numerical training labels
  -> neutral frame identities
  -> neutral correlation / statistical units
```

| Layer | What it is | What it is not |
| --- | --- | --- |
| Provenance | Exact `ElectronicStructureFingerprint` facts (XC, DFT+U, hybrid, PAW, spin, dispersion, smearing, numerical quality, k-points, software/parser) | Training-eligibility gate; partition key; role-budget axis |
| Canonical numerical labels | Quantized energy/force/stress plus the semantic/unit/convention identity needed to interpret them | Compatibility-group / `label_domain_id` assignment |
| Frame identity | Occurrence UID + geometry fingerprint + canonical label payload; provenance referenced separately | Hash of advisory grouping policy |
| Neutral statistical units | Temporal blocks, events, lineage, condition/regime, replica/realization/reference-group, duplicates/correlation | Compatibility-domain fanout; pre-target CV plans |

## Required distinctions

- Provenance facts are descriptive/advisory by default.
- Numerical label identity is independent of compatibility grouping.
- Compatibility grouping is not a target-training eligibility or partition axis.
- Cross-validation is not part of the neutral pre-target statistical substrate.

## Owning implementation (unreachable scaffolding)

Package: `mdstats.training_data.v7_neutral_substrate`

This package is **not** a public runtime. It must not be imported by campaign CLI,
current prepare/select-target-size, or `mdstats.training_data` public exports.

| Pass | Owner | Current runtime left intact |
| --- | --- | --- |
| P1-B | `sources.py` — `build_v7_source_authority` | `sources.build_training_data_source_catalog` still assigns domains |
| P1-C | `identity.py` — `canonical_training_label_payload_digest` | `identity.label_payload_digest` still hashes `label_domain_id` |
| P1-D | `partition.py` — `build_v7_neutral_statistical_base` | `partition` / `data5_bundle` still own CV and domain units |

Local reconciliation: advisory compatibility grouping is serialized on
`V7SourceAuthority` but excluded from `content_digest`, so a grouping-policy-only
change does not invalidate scientific source identity or downstream lineage that
consumes that digest.

## Hard rejection (mechanical only)

Unresolved or mixed electronic-structure provenance does not block usable labels.
Rejection remains limited to missing/corrupt/non-finite/unconvertible required
labels, explicit user filters, or a demonstrated mechanical training-engine
constraint.
