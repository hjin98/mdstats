---
geometry: "margin=0.75in"
architecture_revision: 104
release: "mdstats 0.20.242a0"
status: "current normative architecture"
last_updated: "2026-08-18"
---

# MLFF Training-Data and Fine-Tuning Architecture

## Purpose

This manual defines the accepted current scientific, statistical, execution, and evidence architecture for the mdstats MLFF training-data package. It covers source-certified atomistic data preparation, leakage-safe partitioning, target-data construction, MACE fine-tuning, evaluation, deployment verification, and campaign execution architecture.

The manual is state-oriented. It describes what mdstats **is**, not the sequence by which the implementation was developed. Proposed transitions and developer implementation gates belong under `workplans/`; completed release chronology belongs under `docs/history/mlff/`; correctness and performance evidence belong under `audits/`, `release/`, and `benchmarks/` as appropriate.

## Architectural motive

MLFF campaigns mix several kinds of state that must not be conflated: physical source facts, eligibility decisions, statistical partitions, fitted transforms, subset-selection decisions, optimization/checkpoint state, evaluation evidence, and deployment decisions. The architecture therefore uses immutable, content-addressed records and explicit ownership boundaries. The same separation applies to execution: caches, schedulers, worker counts, memory layouts, and storage realization may change without silently changing scientific authority.

Expensive exact numerical work is computed once, exposed as independent work where safe, and reused downstream whenever its semantic inputs are unchanged. Exactness, deterministic authoritative reduction order, explicit resource ownership, and authenticated restart state take precedence over nominal utilization.

## Canonical documentation layout

The release-facing authority is this assembled file and its synchronized PDF:

- `docs/arch_manuals/mlff_training_data_architecture.md`
- `docs/arch_manuals/mlff_training_data_architecture.pdf`

The maintainable source chapters live under `docs/arch_manuals/mlff_training_data/` and are assembled deterministically by `tools/build_mlff_architecture_manual.py`. Chapter files are retrieval units for the assembled authority and must not contradict it.

Detailed current behavior is owned by `docs/specs/training_data/`. Historical lineage is non-normative and is stored under `docs/history/mlff/`. Active implementation coordination is non-normative and stored under `workplans/active/`.

## Reading index

| Need | Primary chapter |
|---|---|
| Physical/statistical motivation and scope | Part I - Foundations and ownership |
| Source, labels, strain/stress, eligibility, feature/event contracts | Part II - Data and evidence contracts |
| Leakage control, cross-validation, selection, objective weighting | Part III - Statistical design and selection |
| Replay, MACE adapter, training/evaluation, active learning, determinism | Part IV - Training and evaluation |
| FEAS1/MVIDX1/MVSEL1/REPAIR1/MVQUAL1 theory and exact multi-view graph | Part V - Multi-view target-data architecture |
| Scheduler, exact execution, cache reuse, memory/storage, progress | Part VI - Performance and execution architecture |
| Cross-subsystem ownership and accepted design boundaries | Part VII - Ownership boundaries and decision summary |
| External scientific/algorithmic sources | References |

## Context retrieval index

For targeted human or AI loading, use the smallest authoritative source that contains the needed contract:

| Query terms | Load first |
|---|---|
| `DATA*`, source/label identity, eligibility, stress/strain, features | `20_data_contracts.md` |
| partition, leakage, CV, selection, weighting, exposure | `30_statistical_design.md` |
| replay, MACE, checkpoint, evaluation, active learning, determinism | `40_training_evaluation.md` |
| FEAS1, MVIDX1, MVSEL1, REPAIR1, MVQUAL1, target rungs | `50_target_multiview.md` |
| scheduler, utilization, CSR/CSC, vectorization, memory, persistence, progress | `60_execution_performance.md` |
| ownership or accepted design boundary | `80_ownership_and_decisions.md` |
| provenance for an algorithmic/scientific idea | `90_references.md` |
| why/when a historical decision changed | `docs/history/mlff/` |
| a proposed implementation transition | `workplans/active/` |

## Normative vocabulary

- **SHALL / MUST**: required for scientific or execution correctness.
- **SHOULD**: default design unless measured evidence justifies another exact-equivalent realization.
- **MAY**: optional realization that cannot weaken scientific contracts.
- **authoritative evidence**: persisted information that defines or proves a scientific decision.
- **reconstructible execution cache**: discardable state derivable exactly from authoritative inputs.

## Current release boundary

The current architecture uses exact multi-view target selection, deterministic resource-bounded CPU scheduling, authenticated sparse execution caches, restart-safe out-of-core MVIDX inversion, exact MVSEL-to-REPAIR state reuse before repair divergence, common fixed-width progress reporting, and bounded model-training/evaluation execution. Scientific identity and sequential decision authority are independent of worker count, queue completion order, memory layout, and reconstructible cache location.

Positive accelerator qualification that has not yet been executed is not architecture history or proof. Current release-qualification requirements remain in their owning specifications/runbooks; execution planning for unfinished qualification belongs in `workplans/active/`.
