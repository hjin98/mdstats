# MLFF architecture lineage

This file is a navigation aid for code-development history. It is **non-normative**: current architecture lives in `docs/arch_manuals/mlff_training_data_architecture.md`.

| Era | Revisions | Primary theme |
|---|---:|---|
| Adaptive/CV foundations | 23-44 | adaptive stopping/ranking/evaluation, conventional CV, data-size and verification roadmaps, baseline performance qualification |
| Campaign performance and final-GPU handoff | 45-63 | CPU/GPU execution, successive fidelity, structural reduction, VRAM/training persistence, CuEq, final GPU deferral, recovery/audit hotfixes |
| Multi-view target-data architecture | 64-76 | bounded rescue, multi-view plan, FEAS1, MVIDX1, MVSEL1, REPAIR1, MVPERF1/MVQUAL1, size halving/fidelity, migration |
| Replay/CuEq/repeatability hardening | 77-87 | replay unification, CuEq defaults, repeatability diagnostics, campaign-wide warning containment |
| FEAS1 utilization hardening | 88-90 | vectorized reduction, block parallelism experiments, final global single-level PERF3 queue and global progress |
| Current documentation/performance program | 91-97 | current-state manual reorganization, PERFBASE1, shared scheduler, exact-neighborhood reuse, sparse inversion, reference-radius parallelism, and sparse vector kernels |

Detailed lineage:

- [`architecture_revisions/INDEX.md`](architecture_revisions/INDEX.md): one record per architecture revision.
- [`release_notes/INDEX.md`](release_notes/INDEX.md): release/hotfix deltas by package version.
- [`manual_snapshots/`](manual_snapshots/): selected historical full-manual snapshots.

Future revisions update the current manual first, add one concise architecture note, add one release note when applicable, and regenerate both indexes with `python tools/build_mlff_history_indexes.py`.
