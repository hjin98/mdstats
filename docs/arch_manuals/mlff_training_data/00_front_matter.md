---
title: "mdstats MLFF Training-Data Architecture"
artifact_level: "D3 software architecture and integration"
status: "current normative D3 architecture"
accepted_date: "2026-09-13"
---

# mdstats MLFF Training-Data Architecture (D3)

## Authority and scope

This manual is the current D3 software-architecture authority for the machine-learned force-field (MLFF) branch of mdstats. It was narrowed from the former mixed pre-SSDP architecture when the reconstructed D1 and D2 method papers were explicitly accepted on 2026-09-13.

Authority is layered and directional:

1. **D1 scientific/mathematical authority:** [`../../methods/mlff_scientific_method.md`](../../methods/mlff_scientific_method.md).
2. **D2 numerical/algorithmic authority:** [`../../methods/mlff_numerical_algorithmic_method.md`](../../methods/mlff_numerical_algorithmic_method.md).
3. **D3 architecture/integration authority:** this manual.
4. **D4 executable/source-specific authority:** [`../../specs/training_data/README.md`](../../specs/training_data/README.md) and the code owners it indexes.

D3 owns subsystem decomposition, dependency direction, lifecycle and orchestration, interface and artifact boundaries, persistence responsibilities, backend seams, and ownership routing. D3 does **not** redefine scientific observables, estimands, assumptions, numerical estimators, deterministic algorithms, error semantics, or stochastic semantics owned by D1/D2. Exact schema fields, constants, source encodings, dependency probes, and runtime representations remain D4 unless they alter D1/D2 semantics.

The retired mixed architecture is preserved byte-for-byte under `../../history/mlff/architecture_snapshots/pre_d1_d2_promotion_2026-09-13/` for provenance only.

## Architectural pipeline

The current MLFF data/training path is organized as:

`source evidence -> source adapters -> canonical evidence plane -> sampling/evidence roles -> candidate-independent ML preparation -> P3 target-size screening -> P5 post-selection cross-validation -> fresh final production -> downstream qualification consumer`.

The architecture separates evidence construction, target-size selection, method validation, production, and downstream qualification so that later evidence cannot acquire forbidden upstream control.

## Package-level ownership

- `mdstats.data`: canonical source/frame evidence and source-normalization surfaces.
- `mdstats.sampling`: shared correlation/sampling primitives.
- `mdstats.training_data`: MLFF evidence construction, selection, campaign state, persistence, and orchestration.
- `mdstats.training`: training/checkpoint/evaluation execution surfaces.
- `mdstats.cli`: operator-facing composition; it must not become an independent semantic owner.

The remaining chapters define only the architectural consequences of D1/D2 and route exact behavior to the owning D4 specification/code surface.
