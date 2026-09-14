# Documentation index

Use this index to locate current authority before consulting historical material.

| Need | Canonical location |
|---|---|
| MLFF scientific/mathematical authority (D1) | `methods/mlff_scientific_method.md` |
| MLFF numerical/algorithmic authority (D2) | `methods/mlff_numerical_algorithmic_method.md` |
| MLFF software architecture/integration authority (D3) | `arch_manuals/mlff_training_data_architecture.md` and detailed `arch_manuals/mlff_training_data/` |
| MLFF machine-readable dependency architecture | `arch_manuals/mlff_training_data_dependency_graph.json` |
| Training-data exact behavior/specifications (D4) | `specs/training_data/` |
| Active developer transition/workplan | `../workplans/active/` |
| Graphics3D CLI contract | `specs/graphics3d/` |
| MLFF campaign usage | `guides/mlff_campaign_cli_user_guide.{md,pdf}` |
| MLFF post-production qualification behavior | `specs/training_data/mlff_p7_post_production_qualification_spec.md` |
| Downstream final-GPU workstation handoff | `guides/mlff_final_gpu1_workstation_runbook.{md,pdf}` |
| MLFF architecture/release lineage | `history/mlff/LINEAGE.md` |
| MLFF D1/D2 reconstruction provenance | `history/mlff/MLFF_D1_D2_RECONSTRUCTION_EVIDENCE.md` |
| MLFF D1/D2 reconstruction review | `history/mlff/MLFF_D1_D2_RECONSTRUCTION_REVIEW_2026-09-13.md` |
| MLFF D1/D2 promotion record | `history/mlff/MLFF_D1_D2_PROMOTION_2026-09-13.md` |
| MLFF promotion preservation map | `history/mlff/MLFF_D1_D2_PROMOTION_PRESERVATION_MAP_2026-09-13.md` |
| Pre-promotion mixed architecture snapshot | `history/mlff/architecture_snapshots/pre_d1_d2_promotion_2026-09-13/` |
| MLFF lower-layer conformance challenges | `history/mlff/MLFF_D1_D2_RECONSTRUCTION_IMPLEMENTATION_CHALLENGES_2026-09-13.md` |
| Architecture revision notes | `history/mlff/architecture_revisions/INDEX.md` |
| Release/patch notes | `history/mlff/release_notes/INDEX.md` |
| Selected historical MLFF snapshots | `history/mlff/manual_snapshots/` |
| Qualification/readiness evidence | `../release/` and `../audits/` as applicable |
| Performance evidence | `../benchmarks/` and `../benchmarks/evidence/` where present |
| Other mdstats architecture manuals | `arch_manuals/` |

## Authority rule

The current MLFF authority chain is `D1 -> D2 -> D3 -> D4`.

D1 defines scientific meaning. D2 defines the numerical method that realizes D1. D3 defines software ownership, dependency/control flow, lifecycle, persistence, concurrency/resources, and integration that realize D1/D2. D4 specifications and implementation define exact schemas, constants, adapters, dependency/runtime contracts, and concrete behavior under those upstream constraints.

A lower layer may challenge an upstream contract with evidence but may not silently redefine it. Workplans describe proposed transitions and implementation gates. Files under `history/` explain lineage and preserve retired authority snapshots only. Generated reports/publications are descendants of canonical editable sources and do not override them.
