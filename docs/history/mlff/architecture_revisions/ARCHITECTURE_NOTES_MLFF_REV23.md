# MLFF architecture revision 23 planning notes

This source-tree planning update records the next implementation sequence after mdstats 0.20.105a0. It does **not** claim runtime implementation.

1. EVAL-MF1 - nested multi-fidelity checkpoint evaluation core.
2. EVAL-MF2 - conservative survivor control, comprehensive epoch reporting, and production-default qualification.
3. STOR1 - storage accounting and campaign/user ownership boundary.
4. STOR2 - lossless completed-checkpoint evaluation-state compaction.
5. STOR3 - automatic lifecycle-safe reclamation.
6. STOR4 - manual tiered reclamation with capability-loss reporting.
7. STOR5 - immutable deduplication and optional cold archival.

The canonical details are in `docs/arch_manuals/mlff_training_data_architecture.md`, `docs/specs/training_data/mlff_eval_mf_successive_halving_spec.md`, and `docs/specs/training_data/mlff_storage_management_spec.md`.
