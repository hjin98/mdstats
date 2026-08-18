# Architecture Manuals

Architecture manuals define accepted current structure: mathematical/physical theory, subsystem responsibility, data/control flow, ownership boundaries, durable execution architecture, extension boundaries, and accepted design decisions that span modules. They are not implementation workplans, status trackers, release chronologies, or substitutes for detailed module specifications.

Developer implementation sequencing belongs under repository-root `workplans/`; completed chronology belongs under `docs/history/` or release history; qualification and performance evidence belongs under audits/release/benchmarks as appropriate.

## General analysis architectures

- `structural_observables_architecture.{md,pdf}`: structural-observable architecture including RDF, coordination, angle, connectivity, and related structural metrics.
- `topology_statistics_architecture.{md,pdf}`: catalog-derived atomic, framework, temporal, and cross-layer topology statistics.
- `vacf_dynamics_architecture.{md,pdf}`: MSD, VACF, spectra, diffusion, displacement dynamics, and collective-current/transport architecture.
- `thermomechanical_energetic_validation_architecture.{md,pdf}`: thermomechanical and energetic validation architecture.
- `periodic_neighbor_search_architecture.{md,pdf}`: periodic dense/cell-list/Verlet neighbor-search architecture shared across analysis branches.

DOC-GOV1 normalizes the active MLFF authority family first. Any remaining legacy planning/status prose in non-MLFF architecture families is a DOC-GOV2 migration concern rather than MLFF authority.

## Specialized structural and kinetic architectures

- `framework_ring_architecture.{md,pdf}` (**Part I**): optional periodic framework connectivity, rings, symmetry/embedding, tilings/cages/windows, and framework semantics.
- `stage11_site_kinetics_architecture.{md,pdf}` (**Part II**): trajectory evidence, ensemble/quality state, density/attractor inference, site/saddle thermodynamics, segmentation, and observed paths/networks.
- `stage11_site_kinetics_status_history.{md,pdf}`: non-normative legacy release history; it does not define current acceptance semantics.
- `mdstats_dynamical_framework_density_architecture_standard.{md,pdf}`: dynamical-framework plotting/density/rendering architecture.

## MLFF architecture

- `mlff_training_data_architecture.{md,pdf}`: current normative MLFF training-data/fine-tuning architecture. It is state-oriented and contains no developer-status/forward-gate chapter.
- `mlff_training_data/`: maintainable current-state chapter sources for the assembled manual. Use `tools/build_mlff_architecture_manual.py`; do not hand-edit only the assembled file.
- `mlff_training_data_dependency_graph.json`: machine-readable current product/data/runtime dependency architecture. Developer implementation sequencing/status is deliberately excluded.

Historical MLFF revision, patch, and pre-DOC-GOV1 snapshots live under `../history/mlff/`. Active developer transition work lives under `../../workplans/active/`.
