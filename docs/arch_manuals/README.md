# Architecture Manuals

Architecture manuals are current D3 software-architecture authorities: component/state/interface ownership, dependency/data/control flow, persistence/recovery, concurrency, resource/deployment structure, and accepted integration boundaries. They concretize applicable D1/D2 semantics and constrain D4; they do not independently redefine scientific or numerical method authority.

Developer implementation sequencing belongs under repository-root `workplans/`; completed chronology belongs under `docs/history/` or release history; qualification and performance evidence belongs under audits/release/benchmarks as appropriate.

## General analysis architectures

- `structural_observables_architecture.{md,pdf}`: structural-observable architecture including RDF, coordination, angle, connectivity, and related structural metrics.
- `topology_statistics_architecture.{md,pdf}`: catalog-derived atomic, framework, temporal, and cross-layer topology statistics.
- `vacf_dynamics_architecture.{md,pdf}`: MSD, VACF, spectra, diffusion, displacement dynamics, and collective-current/transport architecture.
- `thermomechanical_energetic_validation_architecture.{md,pdf}`: thermomechanical and energetic validation architecture.
- `periodic_neighbor_search_architecture.{md,pdf}`: periodic dense/cell-list/Verlet neighbor-search architecture shared across analysis branches.

## Specialized structural and kinetic architectures

- `framework_ring_architecture.{md,pdf}`: optional periodic framework connectivity, rings, symmetry/embedding, tilings/cages/windows, and framework semantics.
- `stage11_site_kinetics_architecture.{md,pdf}`: trajectory evidence, ensemble/quality state, density/attractor inference, site/saddle thermodynamics, segmentation, and observed paths/networks.
- `stage11_site_kinetics_status_history.{md,pdf}`: non-normative legacy release history.
- `mdstats_dynamical_framework_density_architecture_standard.{md,pdf}`: dynamical-framework plotting/density/rendering architecture.

## MLFF authority stack

The current MLFF authority chain is:

- D1: `../methods/mlff_scientific_method.md`
- D2: `../methods/mlff_numerical_algorithmic_method.md`
- D3 entrypoint: `mlff_training_data_architecture.md`
- D3 detailed sources: `mlff_training_data/`
- D4: `../specs/training_data/` plus the indexed implementation owners

`mlff_training_data_architecture.md` is now a canonical current D3 entrypoint, not the generated mixed monolith used before the D1/D2 split. The numbered sources under `mlff_training_data/` provide detailed current D3 ownership, lifecycle, execution, storage, and integration contracts.

`mlff_training_data_dependency_graph.json` is the machine-readable current D3 dependency/ownership companion.

The former mixed pre-SSDP architecture - including its old assembler and PDF publication chain - is preserved exactly under `../history/mlff/architecture_snapshots/pre_d1_d2_promotion_2026-09-13/` and is no longer current authority.

Exact current MLFF D4 contracts are indexed by `../specs/training_data/README.md`. Historical MLFF revision, patch, compatibility, and pre-reset snapshots live under `../history/mlff/`. Active developer transitions live under `../../workplans/active/`.

A historical document, workplan, audit, benchmark, release note, or generated publication cannot override the current D1-D4 canonical sources.
