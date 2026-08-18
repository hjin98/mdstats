---
title: "mdstats 0.20.183a0"
subtitle: "SIZE-FIDELITY1 calibration authority"
date: "2026-08-15"
geometry: margin=0.72in
fontsize: 9pt
---


This release implements the **SIZE-FIDELITY1** scientific calibration machinery required after the SIZE-HALVE1 target-size correction. It intentionally does not promote the three-epoch screen to certified production authority without real exhaustive MACE evidence.

## Added

- `SizeFidelityCalibrationPolicy` with at least three frozen optimizer seeds, candidate coarse endpoints 3/4/5, monitor sizes 128/256/512/1024, and early equivalence widths 1/2/4 meV/Angstrom.
- `SizeFidelityExecutionPlan`, which freezes every calibration seed x hard-coverage-qualified target-size run and required checkpoint endpoints before training.
- `SizeFidelityMetric`, `SizeFidelityCandidateAssessment`, and `SizeFidelityQualificationReport` with canonical SHA-256-backed serialization and fail-closed validation.
- Public execution-plan, qualification-builder, and fail-closed qualification-validator APIs.
- Deterministic Spearman rank-correlation diagnostics for coarse-versus-final target scores. Correlation remains diagnostic and receives no authority to waive a survivor-recall failure.

## Scientific acceptance

A candidate low-fidelity rule must retain **both** eventual 30-epoch target finalists through the coarse and epoch-10 screens for every frozen calibration seed. The monitor-based coarse promotion set must exactly equal the corresponding full-development promotion set, and the largest ladder boundary may not be falsely eliminated when it becomes a final target finalist.

The recommendation order is earliest faithful coarse endpoint, smallest exact monitor, then smallest tested early equivalence width at or above the current production default.

## Calibration efficiency

Every checkpoint is inferred once on the complete leakage-safe development role. Candidate monitor metrics are deterministic reductions of the same authenticated per-frame prediction authority. Testing four monitor sizes therefore does not purchase four additional MACE inference passes.

With $N_K$ hard-coverage sizes and $N_s$ calibration seeds, the v1 calibration plan requires $N_KN_s$ uninterrupted 30-epoch runs and $5N_KN_s$ full-role inference endpoints at epochs 3, 4, 5, 10, and 30.

## Qualification boundary

The supplied environment has no authorizing foundation checkpoint and no qualifying GPU campaign. This release qualifies the calibration machinery and execution contract on CPU, but the **SIZE-FIDELITY1 scientific gate remains open**. PERF-P2R remains blocked until exhaustive real-trajectory evidence produces a passing report.

## Documentation

The canonical MLFF architecture advances to revision 49 and dependency-graph schema 31. The new normative specification is `docs/specs/training_data/mlff_size_fidelity1_coarse_screen_calibration_spec.md`.
