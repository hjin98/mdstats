---
title: "MLFF-DATA8: MACE artifact transport and general protocol records"
author: "mdstats project"
date: "2026-09-14"
geometry: margin=0.8in
fontsize: 10pt
---

# MLFF-DATA8: MACE artifact transport and general protocol records

## Status and scope

MLFF-DATA8 is the current D4 owner for generic MACE-readable artifact transport and for the broad `TrainingProtocolIdentity` / `Data8PreparationBundle` representation where a separately current non-P5 consumer still uses that representation.

It is **not** current restored-P5 method authority. Current post-selection cross-validation and final production are governed by `mlff_post_selection_p5_spec.md` and descend from `PostSelectionMethodIdentity` through role policy/plan, fitted preparation, `PostSelectionMaterialization`, and run evidence.

Historical DATA8 payloads remain provenance. Deserializing a broad `TrainingProtocolIdentity` does not authorize restored P5.

The adapter remains locked to the currently qualified MACE runtime where the surrounding current runtime specifications require that lock. Source qualification is evidence for actual dependency behavior, not timeless D1/D2 authority.

## Generic artifact boundaries

DATA8 owns these transport/concretization concerns where still consumed:

1. MACE-readable extended XYZ and compact sidecar provenance;
2. explicit atomic-reference mappings and property-availability masks;
3. generic replay train/monitor transport with authenticated source/label lineage;
4. broad `TrainingProtocolIdentity` records for separately current non-P5 consumers;
5. fixed-file job manifests/directories where that representation remains current; and
6. MACE source/runtime probe evidence needed by those consumers.

DATA8 does not own target size, current P5 method identity, current P5 common-monitor topology, current P5 foundation-residual transfer, or P5 final-publication ranking.

## MACE source qualification

Pinned-MACE source qualification records the dependency behaviors on which a current consumer relies, including as applicable:

- head ordering;
- validation ordering/checkpoint behavior;
- target duplication branches;
- multi-head LR/EMA overrides;
- loader `drop_last` behavior;
- distributed-sampler behavior;
- dry-run/checkpoint-retention capability; and
- external replay parser surfaces.

A source probe is evidence, not an assertion that a future dependency version is equivalent. A changed dependency requires current qualification at the affected owner.

Current restored-P5 source/exposure requirements are specified in `mlff_post_selection_p5_spec.md`; DATA8 SHALL NOT reinterpret them.

## Extended-XYZ artifact contract

A current MACE extended-XYZ transport contains only fields needed by its consumer. Typical target records include:

```text
REF_energy
REF_forces
REF_stress
config_weight
config_energy_weight
config_forces_weight
config_stress_weight
frame_uid
```

`config_energy_weight`, `config_forces_weight`, and `config_stress_weight` are local property-availability masks unless another accepted method explicitly assigns different semantics.

The exporter performs write/read round-trip validation of frame order, labels, weights/masks, and stress representation. Floating Cartesian values are serialized at sufficient precision to preserve the governing lossless transport contract.

Complete provenance remains in a canonical sidecar keyed by stable frame identity rather than being packed into fragile XYZ headers.

## Stress transport

`REF_stress` uses the current canonical ASE stress representation and units defined by upstream method/specification authority. Stress and virial are not silently conflated. Missing stress labels are represented through property availability, not fabricated physical values.

## Atomic-reference mapping

Where a consumer uses explicit atomic references, the transport serializes an authenticated mapping from atomic number to energy and keeps the fit-record identity in the manifest/owning protocol record.

Foundation-P5 selected-head residual E0 and composition-transfer semantics are not owned here; see `mlff_post_selection_p5_spec.md`.

## Replay artifact transport

Supported replay transport records authenticate, as applicable:

```text
replay source identity
training-label mode
exact replay-training membership/artifact digest
exact replay-monitor membership/artifact digest
geometry/label identity
property keys
element set
```

Replay training and replay monitoring remain separate evidence roles.

Canonical current P5 replay-label default/ambiguity rules are owned by `mlff_post_selection_p5_spec.md`. DATA8 SHALL NOT silently restore a pseudo-label default for current P5.

## Generic weighted-objective consumers

P3 target-size screening and P5 scratch retain their separately accepted weighted objective/weighting semantics. Where DATA8 transports those methods, it SHALL emit the exact objective/weighting values owned by their current policies and SHALL NOT rely on dependency defaults.

The historical statement that MACE `UniversalLoss` is forbidden on every current path is retired. Foundation P5 intentionally uses native UniversalLoss under accepted D1/D2 and `mlff_post_selection_p5_spec.md`. This does not change P3/P5-scratch weighted methods.

Likewise, a global MACE loss-family constant SHALL NOT be interpreted as cross-mode scientific authority. Runtime loss is resolved by the actual current method owner and authenticated execution seam.

## `TrainingProtocolIdentity`

`TrainingProtocolIdentity` remains a broad general/historical record that may bind, for consumers that still explicitly use it:

- target label domain;
- generic training mode;
- foundation checkpoint;
- replay-plan digest;
- objective/weight/E0/checkpoint-policy digests;
- compatibility/source probe;
- optimizer/precision/backend settings;
- checkpoint-control policy;
- exposure realization;
- training level; and
- random seed.

This representation SHALL NOT be used as a second restored-P5 method identity. A current P5 reader/executor SHALL reject any attempt to authorize P5 solely from this record.

## `Data8PreparationBundle`

`Data8PreparationBundle` remains a general/historical aggregate for consumers that still use the DATA8 fixed-file representation. It is not the current restored-P5 role-plan/materialization owner.

Current P5 shall not be forced back through this bundle merely to preserve old specification structure.

## Generic job transport

Where a current non-P5 consumer still uses DATA8 fixed-file jobs, a job manifest authenticates exact target/replay artifacts, runtime configuration, source probe, protocol identity, and file checksums. Held-out or locked evidence SHALL not appear in training configuration unless its owning current method explicitly permits it.

The exact current post-selection fold/common-monitor/final-plan schemas are owned by `mlff_post_selection_p5_spec.md`, not by the legacy DATA8 job layout.

## Failure and compatibility rules

DATA8 current consumers fail closed on malformed current schemas, content-digest mismatch, unsupported runtime/source behavior, incompatible label lineage, corrupt transport, or unavailable required artifacts.

Historical representations may be read only through explicit supported compatibility readers. Compatibility reading is not semantic migration. Old DATA8 weighted-stress/fold-local-monitor/foundation-from-scratch/M3-P5 records cannot become current P5 authority.

## Non-goals

DATA8 does not:

- choose target size;
- define current P5 loss;
- define current P5 monitor membership;
- allocate current P5 CV folds;
- define current P5 foundation E0 transfer;
- select current P5 final representatives; or
- override current D1-D3 authority.

Any future change that attempts to give DATA8 one of those P5 responsibilities must reopen the appropriate current owner rather than creating a second protocol graph.