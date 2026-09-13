# Documentation index

Use this index to locate current authority before consulting historical material.

| Need | Canonical location |
|---|---|
| MLFF current normative architecture | `arch_manuals/mlff_training_data_architecture.{md,pdf}` |
| MLFF candidate reconstructed scientific formulation (D1; reviewed, pending human acceptance) | `methods/mlff_scientific_method.md` |
| MLFF candidate reconstructed numerical algorithmic method (D2; reviewed, pending human acceptance) | `methods/mlff_numerical_algorithmic_method.md` |
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
| MLFF D1/D2 lossless reconstruction review | `history/mlff/MLFF_D1_D2_RECONSTRUCTION_REVIEW_2026-09-13.md` |
| MLFF lower-layer conformance challenges discovered during reconstruction | `history/mlff/MLFF_D1_D2_RECONSTRUCTION_IMPLEMENTATION_CHALLENGES_2026-09-13.md` |
| Architecture revision notes | `history/mlff/architecture_revisions/INDEX.md` |
| Release/patch notes | `history/mlff/release_notes/INDEX.md` |
| Selected historical MLFF snapshots | `history/mlff/manual_snapshots/` |
| Qualification/readiness evidence | `../release/` and `../audits/` as applicable |
| Performance evidence | `../benchmarks/` and `../benchmarks/evidence/` where present |
| Other mdstats architecture manuals | `arch_manuals/` |

## Authority rule

The MLFF reconstruction branch proposes an explicit D1 -> D2 -> D3 split: D1 scientific formulation, D2 numerical algorithm design, and D3 software architecture/integration, with current specifications retaining exact accepted behavior, schemas, constants, persistence, and runtime contracts. The candidate D1/D2 papers have completed an independent lossless reconstruction review but do not become normative until human review accepts that promotion and the current architecture is correspondingly refactored without semantic loss.

Until that acceptance, the current architecture and specifications remain controlling. Workplans describe proposed transitions and developer implementation gates. Files under `history/` explain completed lineage only, while audits/benchmarks/release artifacts provide evidence. Historical or workplan text does not override current normative documentation.
