# P1 source map — Neutral scientific substrate

This map is the P1-A implementation target. It does **not** replace current
DATA2/DATA3/DATA5 runtime specifications. Current prepare/select-target-size
orchestration remains on the old architecture until P4.

Parent authority: `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md`.
Package contract: `P1_NEUTRAL_SCIENTIFIC_SUBSTRATE.md`.

## Scientific identity chain

```text
precise compatibility-neutral source facts + provenance
  + normalized per-frame arrays carrying actual E/F/stress/geometry
    -> version-agnostic source authority (SourceAuthority)
    -> canonical usable frame authority (CanonicalFrameAuthority)
    -> neutral feature / correlation evidence (NeutralFeatureEvidence)
         -> material-agnostic profile rebind dispatch
         -> provider-owned typed scientific-payload reconstruction
    -> neutral statistical base (NeutralStatisticalBase)
```

| Layer | What it is | What it is not |
| --- | --- | --- |
| Provenance | Exact `ElectronicStructureFingerprint` facts (XC, DFT+U, hybrid, PAW, spin, dispersion, smearing, numerical quality, k-points, software/parser) | Training-eligibility gate; partition key; role-budget axis |
| Source authority | Compatibility-neutral source facts required downstream: composition/atom count, ensemble/control interpretation, quality status/outcome, energy semantics, replica/reference/assertion facts, precise provenance, corpus atomic-reference identifiability, advisory compatibility diagnostics | Compatibility-group / `label_domain_id` gate; a lossy summary that forces downstream code to reconstruct real source facts from assertions |
| Canonical labels & frame authority | Actual E/F/stress plus semantic/unit/convention identity, frame occurrence, geometry, conditions, source-quality-aware eligibility, strain/context, duplicates; authoritative label/labeled identity only after configured required-label validity is proven | Compatibility-group hash; legacy DATA3 label digest; legacy DATA3 metadata converted without real numerical labels; granting authoritative label identity to missing required values |
| Neutral feature evidence | Raw features, events, and partition-stage material profiles rebound to neutral source/frame authority | Legacy DATA4 wrapper embedding retired lineage; opaque profile digest copied into a new wrapper |
| Material-profile provider | Owns typed scientific reconstruction of provider-specific frame/catalog lineage against canonical frame authority | Material-specific science implemented in neutral core; arbitrary dictionary-field rewriting |
| Neutral statistical base | Temporal blocks, events, lineage, condition/regime, replica/realization/reference-group, duplicates/correlation, protected outer roles | Compatibility-domain fanout; pre-target CV plans |

## Required distinctions

- Provenance facts are descriptive/advisory by default.
- Source authority retains real compatibility-neutral source facts needed by reused scientific algorithms; removing compatibility authority does not remove composition, ensemble, quality, source/control interpretation binding, explicit companion bindings or other independent source truth.
- Source authority deserialization must not synthesize missing authoritative facts from obsolete provisional payloads, uses `mdstats.source-record.v2`, and enforces strict status/outcome pair coherence.
- Numerical label identity is independent of compatibility grouping and comes from actual normalized frame arrays.
- Physical frame presence and geometry/source identity are distinguished from authoritative canonical label identity; missing configured-required labels prevent label and labeled-configuration authority while allowing physical diagnostics where needed.
- Canonical label payload digest and labeled configuration fingerprint are an atomic, deterministic pair in all constructors and deserializers.
- Any exported direct identity constructor (`build_canonical_frame_identity`) enforces the exact same required-label authority contract as the assembled owner.
- Direct VASP canonical rebuild replays explicit manifest companion-file bindings (`source.companion_files`) and verifies exact source/control interpretation bindings.
- Legacy DATA3 may coexist for old-runtime isolation but is not a required scientific parent of canonical frame authority.
- Compatibility grouping is not a target-training eligibility or partition axis.
- Material-profile rebinding is generic at the neutral-core boundary and provider-owned in scientific detail.
- LTA is the mandatory P1 reference provider because it currently carries typed frame lineage; it is not a neutral-core special case.
- Supported rebound typed profile payloads must remain resolvable and usable after serialization/restart.
- A legacy DATA3-to-canonical path lacking actual E/F/stress must not return an authoritative canonical type.
- Cross-validation is not part of the neutral pre-target statistical substrate.
- All new code, symbol and schema names are version-agnostic (no `v7_` or `V7` prefixes).

## Owning implementation (unreachable scaffolding)

Package: `mdstats.training_data.neutral_substrate`

This package is **not** a public runtime. It must not be imported by campaign CLI,
current prepare/select-target-size, or `mdstats.training_data` public exports.

| Pass | Owner | Current runtime left intact |
| --- | --- | --- |
| P1-B | `sources.py` — compatibility-neutral `SourceAuthority` with downstream-required source facts | legacy `sources.build_training_data_source_catalog` may still assign compatibility domains |
| P1-C | `identity.py` + `frame_authority.py` and shared established DATA3 helpers — real-array canonical identity, source/frame validation, ensemble/quality semantics, preserved per-run parallel construction | legacy DATA3 identity may still hash `label_domain_id` for old runtime |
| P1-D1 | neutral feature owner — raw/event evidence rebind | legacy DATA4 may remain a value source |
| P1-D2 | generic profile rebind boundary + provider-owned typed adapters | legacy profile wrappers/payloads remain old-runtime values, not neutral authority |
| P1-D3 | LTA provider adapter — mandatory reference realization of generic contract | LTA science remains provider-owned |
| P1-D4 | typed profile persistence/restart owner | digest-only wrappers are insufficient when typed payload cannot be restored |
| P1-D5 | `partition.py` — `NeutralStatisticalBase` | legacy `partition` / `data5_bundle` may still own old CV/domain units until cutover |

## Profile-provider contract

The neutral core owns only generic dispatch, canonical-lineage validation, persistence requirements and explicit rejection of unsupported/opaque providers.

Each supported partition-stage provider owns how its typed scientific payload is rebound:

```text
legacy/current typed provider payload
  -> provider rebind(CanonicalFrameAuthority)
  -> same physical/profile state with canonical frame/catalog lineage
  -> recomputed typed scientific digest
  -> generic ProfileFeatureCatalog wrapper
  -> durable typed payload reconstruction after restart
```

For LTA, the mandatory reference consequence is:

```text
LtaPartitionFeatureCatalog.frame_catalog_digest
    = CanonicalFrameAuthority.content_digest

LtaFramePartitionRecord.frame_record_digest
    = CanonicalFrameAuthority.frame(frame_uid).content_digest
```

The neutral core must not contain an `extension_id == "lta"` scientific reconstruction branch. Unsupported providers must fail explicitly rather than inheriting an opaque legacy scientific digest.

## Source/frame semantic preservation

The canonical owner must reuse established DATA3 scientific algorithms without compatibility-domain ancestry and without semantic drift:

- validate frame atom count/species against `SourceAuthority` composition;
- use actual source ensemble for temperature and strain context;
- use actual source quality status/outcome for frame eligibility;
- preserve reference-cell, strain, eligibility, duplicate and geometry semantics;
- preserve applicable per-run parallel construction, with worker-count-independent scientific output.

A check such as `data.n_atoms == len(data.atomic_numbers)` does not establish source/frame consistency because both values come from the same frame payload.

## Runtime isolation

Advisory compatibility grouping may be serialized on `SourceAuthority` but is excluded from its scientific `content_digest`, so grouping-policy-only changes do not invalidate downstream scientific lineage.

Current production prepare/select-target-size remains on the old runtime until P4. Isolation does not permit the new substrate to depend scientifically on retired compatibility-domain owners.

## Hard rejection

Unresolved or mixed electronic-structure provenance does not itself block usable labels.

Hard rejection remains appropriate for missing/corrupt/non-finite/unconvertible required labels, source/frame composition inconsistency, actual source-quality exclusions required by established eligibility policy, explicit user filters, demonstrated mechanical training-engine constraints, unsupported material-profile payloads that cannot be safely rebound, or other genuine scientific invalidity.
