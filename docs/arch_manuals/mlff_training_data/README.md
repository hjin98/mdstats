# MLFF architecture canonical chapter sources

The numbered Markdown files in this directory are the **canonical editable sources** for the current MLFF architecture. The assembled `../mlff_training_data_architecture.md` and its PDF are derived publication products and must be regenerated from these chapters rather than edited independently.

The architecture is present-tense and single-generation. Historical selector/repair/migration designs belong under `docs/history/mlff/`; proposed implementation transitions belong under `workplans/`.

| Order | Chapter | Purpose |
|---:|---|---|
| 00 | `00_front_matter.md` | Purpose, authority, workflow map, terminology, retrieval index |
| 01 | `10_foundations.md` | Part I - Foundations |
| 02 | `20_data_contracts.md` | Part II - Data and evidence contracts |
| 03 | `30_statistical_design.md` | Part III - Statistical design and fitted preparation |
| 04 | `40_training_evaluation.md` | Part IV - Training, evaluation, and deployment |
| 05 | `50_target_size_selection.md` | Part V - Target-size selection and post-selection validation |
| 06 | `60_execution_performance.md` | Part VI - Bounded execution, restart, and performance architecture |
| 07 | `80_ownership_and_decisions.md` | Part VII - Ownership and extension boundaries |
| 08 | `90_references.md` | References |

`70_status_and_gates.md` is not a current architecture chapter and must not be recreated as a task/status surface. Release/gate chronology is non-normative.

The current dependency/data-flow companion is `../mlff_training_data_dependency_graph.json`. It is reconciled with these chapter sources and contains no alternate legacy/migration execution path.

Publication tooling is validated in DOC-MLFF-ARCH-RESET1 A5. If the repository lacks a reproducible builder for the assembled Markdown/PDF, that is a publication-source-chain defect to repair; it is not permission to patch the derived outputs manually.
