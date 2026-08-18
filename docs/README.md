# Documentation

Start with [`INDEX.md`](INDEX.md) for the current documentation map.

The documentation tree is organized by artifact responsibility.

- `specs/` mirrors the Python package hierarchy. A module
  `mdstats/<path>/<name>.py` uses `docs/specs/<path>/<name>_spec.{md,pdf}`.
- `arch_manuals/` contains high-level theory, ownership, and staged architecture
  documents that span multiple modules.

Specifications are maintained in paired Markdown and PDF forms from one
Markdown source.

## MLFF data preparation and fine-tuning

- `arch_manuals/mlff_training_data_architecture.{md,pdf}` is the current normative MLFF architecture (revision 91 / `0.20.224a0`). It is assembled from indexed chapter sources in `arch_manuals/mlff_training_data/` and now includes the frozen campaign-wide performance roadmap.
- `arch_manuals/mlff_training_data_dependency_graph.json` is the machine-readable dependency/status graph.
- `specs/training_data/` owns module/gate contracts.
- `guides/mlff_campaign_cli_user_guide.{md,pdf}` and `guides/mlff_final_gpu1_workstation_runbook.{md,pdf}` are operational runbooks.
- `history/mlff/` owns non-normative architecture revision notes, release notes, and historical manual snapshots.

The documentation rule is current-state-first: update the canonical architecture/specification, then record the release delta in history. Historical revision commentary must not be prepended to the current architecture manual.

## Physical validation ownership

- `arch_manuals/structural_observables_architecture.{md,pdf}` owns RDF,
  coordination, angles, connectivity, the selection-grade local-structure
  kernel, and planned general structural metrics.
- `arch_manuals/vacf_dynamics_architecture.{md,pdf}` owns displacement,
  velocity, spectra, diffusion, and current-based transport analyses.
- `arch_manuals/topology_statistics_architecture.{md,pdf}` owns graph-state
  statistics.
- `arch_manuals/thermomechanical_energetic_validation_architecture.{md,pdf}`
  defines the planned EOS, elasticity, thermodynamic response,
  stress-correlation viscosity, phonon, surface/interface, defect, and migration
  analyses.
- `arch_manuals/framework_ring_architecture.{md,pdf}` and
  `arch_manuals/stage11_site_kinetics_architecture.{md,pdf}` own optional porous
  framework, ring/site, and kinetic semantics.

The standardized dispatcher in `mdstats.analysis.observable_validation` binds
recipes to the authoritative analysis APIs. The MLFF layer may invoke and compare
those results but does not redefine their physical algorithms.

Runtime note: 0.20.112a0 condenses repeated upstream MACE/PyTorch evaluation warnings; the architecture roadmap remains STOR1 -> STOR2.

