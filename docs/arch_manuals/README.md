# Architecture Manuals

Architecture manuals begin with the mathematical and physical theory that
motivates each subsystem, then define ownership boundaries, staged
implementation plans, evidence contracts, and accepted design decisions. They
are written for both scientific readers and implementers and are not substitutes
for module specifications.

## General analysis architectures

- `structural_observables_architecture.{md,pdf}`: RDF, cumulative and integer
  coordination, neighbor-angle distributions, generic atomic connectivity, and
  planned general structural observables such as structure factors,
  orientational order, local packing, and interface profiles.
- `topology_statistics_architecture.{md,pdf}`: catalog-derived atomic,
  framework, temporal, and cross-layer topology statistics.
- `vacf_dynamics_architecture.{md,pdf}`: MSD, VACF, spectral, Green--Kubo
  diffusion, displacement dynamics, collective-current theory, and staged
  transport architecture.
- `thermomechanical_energetic_validation_architecture.{md,pdf}`: equation of
  state, elasticity, thermodynamic response, stress-correlation viscosity,
  harmonic phonons, surface/interface energetics, defects, and migration paths.
  Its current revision is an implementation plan; the listed numerical
  analyses remain planned unless explicitly marked implemented.
- `periodic_neighbor_search_architecture.{md,pdf}`: dense, cell-list, and
  Verlet-cache staged architecture used by multiple analysis branches.

## Specialized structural and kinetic architectures

- `framework_ring_architecture.{md,pdf}` (**Part I**): optional periodic
  framework connectivity, primitive rings, symmetry and embedding, natural
  tilings, tile/cage/window geometry, persistent and compatible-frame serrated
  ring geometry, and framework semantics through Stage 11D.
- `stage11_site_kinetics_architecture.{md,pdf}` (**Part II**): registered
  trajectory evidence, ensemble reconstruction, conservation and stationarity,
  density/attractor inference, site and saddle thermodynamics, segmentation,
  observed paths/networks, and deferred kinetic branches. Part II consumes but
  does not redefine Part I identities.
- `stage11_site_kinetics_status_history.{md,pdf}`: non-normative release
  history. It never defines current scientific acceptance gates.
- `mdstats_dynamical_framework_density_architecture_standard.{md,pdf}`:
  registered dynamical-framework plotting, density fields, and dense-to-sparse
  rendering migration.

## MLFF architecture

- `mlff_training_data_architecture.{md,pdf}`: current normative MLFF training-data/fine-tuning architecture, revision 96. The manual is state-oriented and includes theory, ownership, target-data multi-view algorithms, execution/performance design, current status, and forward gates.
- `mlff_training_data/`: numbered maintainable chapter sources for the assembled manual. Use `tools/build_mlff_architecture_manual.py`; do not hand-edit only the assembled file.
- `mlff_training_data_dependency_graph.json`: machine-readable current dependency and gate graph.

Historical MLFF revision and patch commentary lives under `../history/mlff/` and is deliberately excluded from this architecture-manual directory.
