# mdstats 0.20.224a0 patch notes

## DOC-ARCH1 documentation and lineage reorganization

This release is documentation/architecture-only. It does not change scientific arrays, selection decisions, campaign schemas, training semantics, coverage thresholds, the 16,384 target ceiling, or deferred GPU authority.

The canonical MLFF architecture manual is now assembled from numbered chapter sources in `docs/arch_manuals/mlff_training_data/`. Revision chronology was removed from the beginning/end of the manual and consolidated under `docs/history/mlff/`. The new performance chapter records the theory, algorithms, exact-equivalence constraints, external design references, progress contract, and ordered implementation gates for the campaign-wide optimization program.

Root-level duplicate MLFF manuals/specifications/revision notes/qualification files were moved or deduplicated into the documentation and release trees. The FINAL-GPU workstation runbook is canonical at `docs/guides/mlff_final_gpu1_workstation_runbook.{md,pdf}`.

## Qualification

- canonical manual reduced from 12,044 revision-90 lines to 3,055 current-state lines, with the full predecessor retained under `docs/history/mlff/manual_snapshots/`;
- repository-root regular files reduced from 369 to 7 by moving/deduplicating documentation and evidence into their owning trees;
- 69 architecture revision notes and 161 release-note records are indexed under `docs/history/mlff/`;
- the synchronized architecture PDF renders as 45 pages with zero LaTeX overfull boxes;
- DOC-ARCH1 specification qualification: 7/7 passed;
- TARGET-DATA2 functional regression: 111/111 passed;
- historical version-pinned specification tests remain archival evidence and are not rewritten to claim current-release authority.

Qualification evidence is recorded in `release/qualification_logs/MLFF_DOC_ARCH1_QUALIFICATION_0.20.224a0.json`; the directory migration contract is recorded in `release/migration_records/DOC_TREE_MIGRATION_0.20.224a0.json`.
