# P1 source map — Neutral scientific substrate

This map is the P1-A implementation target. It does **not** replace current
DATA2/DATA3/DATA5 runtime specifications. Current prepare/select-target-size
orchestration remains on the old architecture until P4.

Parent authority: `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md`.
Package contract: `P1_NEUTRAL_SCIENTIFIC_SUBSTRATE.md`.

## Scientific identity chain

```text
precise provenance (descriptive / advisory by default)
  -> version-agnostic source authority (SourceAuthority)
  -> canonical usable frame authority (CanonicalFrameAuthority)
  -> neutral feature / correlation evidence (NeutralFeatureEvidence)
  -> neutral statistical base (NeutralStatisticalBase)
```

| Layer | What it is | What it is not |
| --- | --- | --- |
| Provenance | Exact `ElectronicStructureFingerprint` facts (XC, DFT+U, hybrid, PAW, spin, dispersion, smearing, numerical quality, k-points, software/parser) | Training-eligibility gate; partition key; role-budget axis |
| Source authority | Record of sources, usability, corpus atomic-reference identifiability, and advisory compatibility diagnostics | Compatibility-group / `label_domain_id` gate or scientific ancestor digest |
| Canonical labels & frame authority | Quantized energy/force/stress plus semantic/unit/convention identity, frame occurrence, geometry, and conditions | Compatibility-group hash; legacy DATA3 catalog wrapper |
| Neutral feature evidence | Raw features, events, and profile features bound to neutral source/frame authority digests | Legacy DATA4 bundle wrapper embedding label-domain digests |
| Neutral statistical base | Temporal blocks, events, lineage, condition/regime, replica/realization/reference-group, duplicates/correlation, protected outer roles | Compatibility-domain fanout; pre-target CV plans |

## Required distinctions

- Provenance facts are descriptive/advisory by default.
- Numerical label identity is independent of compatibility grouping.
- Compatibility grouping is not a target-training eligibility or partition axis.
- Cross-validation is not part of the neutral pre-target statistical substrate.
- All new code, symbol, and schema names are version-agnostic (no `v7_` or `V7` prefixes).

## Owning implementation (unreachable scaffolding)

Package: `mdstats.training_data.neutral_substrate`

This package is **not** a public runtime. It must not be imported by campaign CLI,
current prepare/select-target-size, or `mdstats.training_data` public exports.

| Pass | Owner | Current runtime left intact |
| --- | --- | --- |
| P1-B | `sources.py` — `build_source_authority` | `sources.build_training_data_source_catalog` still assigns domains |
| P1-C | `identity.py` & `frame_authority.py` — `build_canonical_frame_authority` | `identity.label_payload_digest` still hashes `label_domain_id` |
| P1-D1 | `features.py` — `build_neutral_feature_evidence` | `data4_bundle` still binds legacy frame/source catalogs |
| P1-D2 | `partition.py` — `build_neutral_statistical_base` | `partition` / `data5_bundle` still own CV and domain units |

Local reconciliation: advisory compatibility grouping is serialized on
`SourceAuthority` but excluded from `content_digest`, so a grouping-policy-only
change does not invalidate scientific source identity or downstream lineage that
consumes that digest.

## Hard rejection (mechanical only)

Unresolved or mixed electronic-structure provenance does not block usable labels.
Rejection remains limited to missing/corrupt/non-finite/unconvertible required
labels, explicit user filters, or a demonstrated mechanical training-engine
constraint.
