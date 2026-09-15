---
title: "mdstats MLFF Training-Data Architecture"
artifact_level: "D3 software architecture and integration"
status: "current normative D3 architecture"
accepted_date: "2026-09-15"
---

# mdstats MLFF Training-Data Architecture (D3)

## Authority and scope

This manual is the current D3 software-architecture authority for the machine-learned force-field (MLFF) branch of mdstats. It was narrowed from the former mixed pre-SSDP architecture when the reconstructed D1 and D2 method papers were explicitly accepted.

Authority is layered and directional:

1. **D1 scientific/mathematical authority:** [`../../methods/mlff_scientific_method.md`](../../methods/mlff_scientific_method.md), with [`../../methods/mlff_target_training_order_scientific_method.md`](../../methods/mlff_target_training_order_scientific_method.md) as the accepted scoped owner for `TargetTrainingOrder` / `pi_train` scientific meaning.
2. **D2 numerical/algorithmic authority:** [`../../methods/mlff_numerical_algorithmic_method.md`](../../methods/mlff_numerical_algorithmic_method.md), with [`../../methods/mlff_target_training_order_numerical_algorithmic_method.md`](../../methods/mlff_target_training_order_numerical_algorithmic_method.md) as the accepted scoped owner for target-training-order numerics.
3. **D3 architecture/integration authority:** this manual, including [`45_target_training_order.md`](45_target_training_order.md) as the canonical detailed owner for the restored target-order subsystem.
4. **D4 executable/source-specific authority:** [`../../specs/training_data/README.md`](../../specs/training_data/README.md) and the code owners it indexes.

D3 owns subsystem decomposition, dependency direction, lifecycle and orchestration, interface and artifact boundaries, persistence responsibilities, backend seams, and ownership routing. D3 does **not** redefine scientific observables, estimands, assumptions, numerical estimators, deterministic algorithms, error semantics, or stochastic semantics owned by D1/D2. Exact schema fields, constants, source encodings, dependency probes, and runtime representations remain D4 unless they alter D1/D2 semantics.

The retired mixed architecture is preserved byte-for-byte under `../../history/mlff/architecture_snapshots/pre_d1_d2_promotion_2026-09-13/` for provenance only.

## Architectural pipeline

The current MLFF data/training path is organized as:

```text
source evidence
 -> source adapters
 -> canonical evidence plane / protected relations
 -> exact P_train + M3 split
 -> TargetCoverageReference + canonical target-order obligations
 -> shared FEAS1/NEIGHBOR1 -> MVIDX -> MVSEL2/REPAIR2 -> independent MVQUAL
 -> one complete TargetTrainingOrder and exact configured prefixes
 -> common P3 target-size training preparation
 -> P3 target-size screening/reducer
 -> operator-owned provisional design
 -> P5 post-selection cross-validation
 -> fresh final production
 -> downstream qualification consumer
```

`pi_eval/M1/M2/M3` remain under their existing current owners. The target-order subsystem does not consume target-size model outcomes, CV, replay, production, or qualification evidence. The architecture separates evidence construction, target-size selection, method validation, production, and downstream qualification so that later evidence cannot acquire forbidden upstream control.

## Package-level ownership

- `mdstats.data`: canonical source/frame evidence and source-normalization surfaces.
- `mdstats.sampling`: shared correlation/sampling primitives.
- `mdstats.training_data`: MLFF evidence construction, target-order selection, campaign state, persistence, and orchestration.
- `mdstats.training`: training/checkpoint/evaluation execution surfaces.
- `mdstats.cli`: operator-facing composition; it must not become an independent semantic owner.

The remaining chapters define only the architectural consequences of D1/D2 and route exact behavior to the owning D4 specification/code surface.
