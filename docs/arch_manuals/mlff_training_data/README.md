# MLFF architecture canonical chapter sources

The numbered Markdown files in this directory are the **canonical editable sources** for the current D3 MLFF architecture. The assembled `../mlff_training_data_architecture.md` and its PDF are derived publication products and must be regenerated from these chapters rather than edited independently.

Scientific and numerical method authority has been factored into:

- `docs/methods/mlff_scientific_method.md` — D1 scientific formulation;
- `docs/methods/mlff_numerical_algorithmic_method.md` — D2 numerical algorithm design.

These architecture chapters may retain concise summaries of D1/D2 consequences where needed to explain integration, but they do not independently redefine the upstream method.

The architecture is present-tense and single-generation. Historical selector/repair/migration designs belong under `docs/history/mlff/`; proposed implementation transitions belong under `workplans/`.

| Order | Chapter | Purpose |
|---:|---|---|
| 00 | `00_front_matter.md` | Purpose, D1/D2/D3 authority boundary, workflow map, terminology, retrieval index |
| 01 | `10_foundations.md` | Part I - architectural foundations and scientific consequences |
| 02 | `20_data_contracts.md` | Part II - data and evidence contracts |
| 03 | `30_statistical_design.md` | Part III - statistical-role and fitted-preparation architecture |
| 04 | `40_training_evaluation.md` | Part IV - training, evaluation, and deployment architecture |
| 05 | `50_target_size_selection.md` | Part V - target-size ownership and post-selection validation architecture |
| 06 | `60_execution_performance.md` | Part VI - bounded execution, restart, and performance architecture |
| 07 | `80_ownership_and_decisions.md` | Part VII - ownership and extension boundaries |
| 08 | `90_references.md` | Architecture references |

`70_status_and_gates.md` is not a current architecture chapter and must not be recreated as a task/status surface. Release/gate chronology is non-normative.

The current dependency/data-flow companion is `../mlff_training_data_dependency_graph.json`. It is reconciled with these chapter sources and contains no alternate legacy/migration execution path.

Publication tooling is validated in DOC-MLFF-ARCH-RESET1 A5. If the repository lacks a reproducible builder for the assembled Markdown/PDF, that is a publication-source-chain defect to repair; it is not permission to patch the derived outputs manually.
