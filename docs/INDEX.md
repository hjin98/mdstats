# Documentation index

Use this index to locate current authority before consulting historical material.

| Need | Canonical location |
|---|---|
| MLFF scientific formulation (D1) | `methods/mlff_scientific_method.md` |
| MLFF numerical algorithmic method (D2) | `methods/mlff_numerical_algorithmic_method.md` |
| MLFF training-data/fine-tuning architecture (D3) | `arch_manuals/mlff_training_data_architecture.{md,pdf}` |
| MLFF chapter-level current architecture context | `arch_manuals/mlff_training_data/` |
| MLFF machine-readable dependency architecture | `arch_manuals/mlff_training_data_dependency_graph.json` |
| Training-data current behavior/specifications | `specs/training_data/` |
| Active developer transition/workplan | `../workplans/active/` |
| Graphics3D CLI contract | `specs/graphics3d/` |
| MLFF campaign usage | `guides/mlff_campaign_cli_user_guide.{md,pdf}` |
| MLFF post-production qualification behavior | `specs/training_data/mlff_p7_post_production_qualification_spec.md` |
| Downstream final-GPU workstation handoff | `guides/mlff_final_gpu1_workstation_runbook.{md,pdf}` (release-pinned; separate from P6 campaign lifecycle) |
| MLFF architecture/release lineage | `history/mlff/LINEAGE.md` |
| MLFF D1/D2 reconstruction provenance | `history/mlff/MLFF_D1_D2_RECONSTRUCTION_EVIDENCE.md` |
| Architecture revision notes | `history/mlff/architecture_revisions/INDEX.md` |
| Release/patch notes | `history/mlff/release_notes/INDEX.md` |
| Selected historical MLFF snapshots | `history/mlff/manual_snapshots/` |
| Qualification/readiness evidence | `../release/` and `../audits/` as applicable |
| Performance evidence | `../benchmarks/` and `../benchmarks/evidence/` where present |
| Other mdstats architecture manuals | `arch_manuals/` |

## Authority rule

For the MLFF branch, D1 method documents own scientific formulation, D2 method documents own numerical algorithm design, D3 architecture owns software structure/dependency/ownership consequences, and current specifications own exact accepted behavior, schemas, constants, persistence, and runtime contracts. A lower layer must preserve accepted upstream meaning rather than silently redefining it.

Workplans describe proposed transitions and developer implementation gates. Files under `history/` explain completed lineage only, while audits/benchmarks/release artifacts provide evidence. Historical or workplan text does not override current D1-D3 authority or current specifications.
