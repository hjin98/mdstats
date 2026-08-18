---
geometry: "margin=0.75in"
architecture_revision: 103
release: "mdstats 0.20.240a0"
status: "current normative architecture; revision 103 unchanged; MVIDX multi-billion-edge scaling and bounded-queue backpressure hardened; exact-equivalence CPU optimization closed; FINAL-GPU1 next"
last_updated: "2026-08-18"
---

# MLFF Training-Data and Fine-Tuning Architecture

## Purpose

This manual defines the current scientific, statistical, execution, and evidence architecture for the mdstats MLFF training-data package. It covers source-certified atomistic data preparation, leakage-safe partitioning, target-data construction, MACE fine-tuning, evaluation, deployment verification, and the campaign performance architecture.

The manual is intentionally **state-oriented rather than revision-oriented**. Historical release deltas, architecture revision notes, and patch notes are retained under `docs/history/mlff/`; they do not define current scientific contracts. The complete revision-90 predecessor is retained in `docs/history/mlff/manual_snapshots/`.

## Architectural motive

MLFF campaigns mix several kinds of state that must not be conflated: physical source facts, eligibility decisions, statistical partitions, fitted transforms, subset-selection decisions, optimization/checkpoint state, evaluation evidence, and deployment decisions. The architecture therefore uses immutable, content-addressed records and explicit ownership boundaries. The same separation is applied to performance: execution caches, schedulers, worker counts, and memory layouts may change without silently changing scientific authority.

The current performance roadmap has one additional motive: **expensive exact numerical work should be computed once, exposed as enough independent tasks to occupy the allowed hardware, and reused downstream whenever its semantic inputs are unchanged**. This principle is applied first to the exact TARGET-DATA2B neighborhood graph shared by FEAS1 and MVIDX1.

## Canonical documentation layout

The release-facing authority is this assembled file and its synchronized PDF:

- `docs/arch_manuals/mlff_training_data_architecture.md`
- `docs/arch_manuals/mlff_training_data_architecture.pdf`

The source chapters are maintained under `docs/arch_manuals/mlff_training_data/` and assembled deterministically by `tools/build_mlff_architecture_manual.py`. This split is for navigation and contextual loading only; chapter files must not contradict the assembled authority.

Historical lineage is non-normative and is stored under:

- `docs/history/mlff/architecture_revisions/`
- `docs/history/mlff/release_notes/`
- `docs/history/mlff/manual_snapshots/`

## Reading index

| Need | Primary chapter |
|---|---|
| Physical/statistical motivation and scope | Part I - Foundations and ownership |
| Source, labels, strain/stress, eligibility, feature/event contracts | Part II - Data and evidence contracts |
| Leakage control, cross-validation, selection, objective weighting | Part III - Statistical design and selection |
| Replay, MACE adapter, training/evaluation, active learning, determinism | Part IV - Training and evaluation |
| FEAS1/MVIDX1/MVSEL1/REPAIR1/MVQUAL1 theory and exact multi-view graph | Part V - Multi-view target-data architecture |
| Shared scheduler, vectorization, cache reuse, NUMA/memory policy, progress | Part VI - Performance and execution architecture |
| Current implementation state, frozen optimization gates, acceptance | Part VII - Status and forward gates |
| External scientific/algorithmic sources | References |

## Context retrieval index

For targeted human or AI loading, use the smallest authoritative source that contains the needed contract:

| Query terms | Load first |
|---|---|
| `DATA*`, source/label identity, eligibility, stress/strain, features | `20_data_contracts.md` |
| partition, leakage, CV, selection, weighting, exposure | `30_statistical_design.md` |
| replay, MACE, checkpoint, evaluation, active learning, determinism | `40_training_evaluation.md` |
| FEAS1, MVIDX1, MVSEL1, REPAIR1, MVQUAL1, target rungs | `50_target_multiview.md` |
| scheduler, utilization, CSR/CSC, vectorization, NUMA, progress | `60_execution_performance.md` |
| `PERFBASE1` through `MVSTATE-REUSE1`, current status | `70_status_and_gates.md` |
| ownership or current design decision | `80_ownership_and_decisions.md` |
| provenance for an algorithmic/scientific idea | `90_references.md` |
| why/when a historical decision changed | MLFF revision index under `docs/history/` |

The assembled manual is the release-facing authority; chapter files are retrieval units, not independent competing specifications.

## Normative vocabulary

- **SHALL / MUST**: required for scientific or execution correctness.
- **SHOULD**: default design unless measured evidence justifies another exact-equivalent realization.
- **MAY**: optional realization that cannot weaken scientific contracts.
- **authoritative evidence**: persisted information that defines or proves a scientific decision.
- **reconstructible execution cache**: discardable state derivable exactly from authoritative inputs.

## Current release boundary

`mdstats 0.20.240a0` is an exact-execution MVIDX/PARCORE1 backpressure hardening release on architecture revision 103. MVIDX no longer eager-submits every required family inversion into the bounded PARCORE1 ready queue. It feeds family and hard-obligation tasks through a deterministic producer/consumer refill loop: submit only while ready capacity exists, wait for completion, drain canonical completions, then refill. This preserves bounded ready/in-flight/completed queues and explicit RAM admission while allowing domains with arbitrarily more required families than queue slots (including the observed 165-family / 56-ready-slot production case). Scientific sparse-index authority, out-of-core storage semantics, worker-independent digests, and `FINAL-GPU1` as the next scientific gate are unchanged.

`mdstats 0.20.239a0` is a Python-3.11 compatibility hotfix on architecture revision 103. It corrects the DATA6 progress reporter so canonical timing fields are computed before f-string interpolation; the 0.20.238a0 MVIDX out-of-core execution/storage hardening and all scientific authority are unchanged. Release qualification now includes whole-tree Python 3.11 grammar parsing. `FINAL-GPU1` remains the next scientific gate.

`mdstats 0.20.238a0` is an exact-equivalence MVIDX scaling-hardening release on architecture revision 103. Multi-billion-edge NEIGHBOR1 caches may exceed the anonymous-RAM capacity required by the original full-family SciPy transpose even when the final scientific uint32/uint64 sparse arrays are valid. Campaign MVIDX therefore uses bounded row-chunk CSR-to-CSC transposes for large families, writes candidate-to-witness arrays directly as file-backed NPY memmaps, hard-links whole mmap-backed arrays into the authenticated native store on the same filesystem, and reloads the durable mmap authority before removing transient build paths. Queue admission accounts bounded transient scratch rather than the complete inverse payload for this path. A disk-space preflight fails before inversion if the exact inverse edge payload plus safety headroom cannot fit. In-memory and out-of-core arrays are required to be byte-identical and produce the same MVIDX content digest. This hardening changes execution/storage realization only; revision 103, schema 83, scientific authority, MPA-0/MH-1 semantics, and the `FINAL-GPU1` next-gate decision remain unchanged.

`mdstats 0.20.237a0` is a presentation-only maintenance release on top of architecture revision 103. It standardizes MLFF progress and heartbeat output across preparation, TARGET-DATA2, model sweep, training, inference/evaluation schedulers, and qualification callbacks. Every elapsed/ETA field now uses fixed-width `HH:MM:SS`; unavailable ETA is `--:--:--`; progress counters, rates, phase/status fields, and semicolon delimiters follow the common Part VI observability contract. No scientific identity, scheduler authority, model-family behavior, dependency-graph node, or CPU/GPU gate decision changes. `FINAL-GPU1` remains next.

Revision 103 completes `MVSTATE-REUSE1` and closes the exact-equivalence CPU optimization program. MVSEL now emits authenticated exact sparse-state checkpoints at materializable target rungs; REPAIR consumes those checkpoints only while its state is still identical to MVSEL and falls back to the historical carried-forward arithmetic after the first accepted repair swap. Pure checkpoint reconciliation after repair divergence was rejected because it perturbed FP64 representative-gain arrays at the 1e-17--1e-16 level. On the common 8,192-candidate/six-family closure fixture, untouched 0.20.235a0 takes about 12.00 s while 0.20.236a0 takes about 11.02 s excluding persistence; including the one-time ~0.18 s authenticated cache write, the fresh chain is about 11.19 s. REPAIR itself improves from about 5.37 s to 4.27 s with exact selection/repair/qualification digests. Cumulative fresh-chain speedup versus the PERFBASE1-era 0.20.225a0 authority is about 2.44x. Remaining target-chain cost is dominated by the exact sequential sparse-state arithmetic itself, so no further CPU-only gate is justified under the exact-equivalence policy. `FINAL-GPU1` is next; positive accelerator qualification remains deferred to that workstation gate.

