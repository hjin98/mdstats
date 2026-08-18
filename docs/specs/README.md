# Module Specifications

Documentation ownership and generated-PDF parity map as follows:

```text
docs/arch_manuals/framework_ring_architecture.md
  + docs/arch_manuals/stage11_site_kinetics_architecture.md
    -> docs/specs/documentation/architecture_manual_ownership_spec.md
```


Specification paths mirror the `mdstats/` source hierarchy.

Examples:

```text
mdstats/collection.py                         -> docs/specs/collection_spec.{md,pdf}
mdstats/analysis/framework_topology.py       -> docs/specs/analysis/framework_topology_spec.{md,pdf}
mdstats/plotting/framework_topology_graph.py -> docs/specs/plotting/framework_topology_graph_spec.{md,pdf}
mdstats/graphics3d CLI contract               -> docs/specs/graphics3d/mdstats_gfx3d_cli_spec.{md,pdf}
```

Private implementation modules retain their leading underscore, for example
`mdstats/analysis/_verlet_cache.py` maps to `docs/specs/analysis/_verlet_cache_spec.{md,pdf}`.
Supplemental specifications for one module use the module stem followed by a focused qualifier, such as `_verlet_cache_deformation_spec`.

`mdstats/analysis/primitive_ring.py` maps to `docs/specs/analysis/primitive_ring_spec.{md,pdf}`.

Topology-statistics subpackage specifications mirror `mdstats/analysis/topology_statistics/`. For example, `_common.py` maps to `docs/specs/analysis/topology_statistics/_common_spec.{md,pdf}` and `atomic.py` maps to `docs/specs/analysis/topology_statistics/atomic_spec.{md,pdf}`.

`mdstats/analysis/topology_statistics/temporal.py` maps to `docs/specs/analysis/topology_statistics/temporal_spec.{md,pdf}`.

`mdstats/analysis/topology_statistics/combined.py` maps to `docs/specs/analysis/topology_statistics/combined_spec.{md,pdf}`.

`mdstats/plotting/topology_statistics.py` maps to `docs/specs/plotting/topology_statistics_spec.{md,pdf}`.

`mdstats/io/topology_statistics.py` maps to `docs/specs/io/topology_statistics_spec.{md,pdf}`.

VACF/dynamics common contracts map as follows:

```text
mdstats/analysis/_dynamics_common.py -> docs/specs/analysis/_dynamics_common_spec.{md,pdf}
mdstats/analysis/_velocity_common.py -> docs/specs/analysis/_velocity_common_spec.{md,pdf}
mdstats/analysis/_spectral.py       -> docs/specs/analysis/_spectral_spec.{md,pdf}
mdstats/analysis/_spectral_units.py -> docs/specs/analysis/_spectral_units_spec.{md,pdf}
mdstats/analysis/velocity_spectrum.py -> docs/specs/analysis/velocity_spectrum_spec.{md,pdf}
                                      -> docs/specs/analysis/vdos_spec.{md,pdf} (VS3 supplement)
mdstats/analysis/displacement_dynamics.py -> docs/specs/analysis/displacement_dynamics_spec.{md,pdf}
mdstats/analysis/current_correlation.py -> docs/specs/analysis/current_correlation_spec.{md,pdf}
mdstats/analysis/ionic_conductivity.py -> docs/specs/analysis/ionic_conductivity_spec.{md,pdf}
```

VACF transport modules map as follows:

```text
mdstats/analysis/_quadrature.py    -> docs/specs/analysis/_quadrature_spec.{md,pdf}
mdstats/analysis/vacf_transport.py -> docs/specs/analysis/vacf_transport_spec.{md,pdf}
```

Spectral plotting maps as follows:

```text
mdstats/plotting/velocity_spectrum.py -> docs/specs/plotting/velocity_spectrum_spec.{md,pdf}
```

Custom VASP CONTCAR trajectory input maps as follows:

```text
mdstats/io/vasp_contcar_trajectory.py -> docs/specs/io/vasp_contcar_trajectory_spec.{md,pdf}
```

Reproducible watcher and caller examples are stored under
`examples/vasp_contcar_trajectory/`.

Strong-ring classification maps as follows:

```text
mdstats/analysis/ring_strength.py -> docs/specs/analysis/ring_strength_spec.{md,pdf}
```


Periodic-net symmetry and Stage-7R consolidation map as follows:

```text
mdstats/analysis/periodic_barycentric.py       -> docs/specs/analysis/periodic_barycentric_spec.{md,pdf}
mdstats/analysis/net_symmetry.py               -> docs/specs/analysis/net_symmetry_spec.{md,pdf}
mdstats/analysis/net_symmetry_discovery.py     -> docs/specs/analysis/net_symmetry_discovery_spec.{md,pdf}
mdstats/analysis/primitive_ring_symmetry.py    -> docs/specs/analysis/primitive_ring_symmetry_spec.{md,pdf}
mdstats/analysis/ring_strength.py              -> docs/specs/analysis/ring_strength_spec.{md,pdf}
Stage-7R cross-module boundary                 -> docs/specs/analysis/stage7r_certification_persistence_spec.{md,pdf}
```

Periodic cell-complex and natural-tiling modules map as follows:

```text
mdstats/analysis/periodic_cell_complex.py      -> docs/specs/analysis/periodic_cell_complex_spec.{md,pdf}
mdstats/analysis/natural_tiling.py             -> docs/specs/analysis/natural_tiling_spec.{md,pdf}
mdstats/analysis/natural_tiling_search.py      -> docs/specs/analysis/natural_tiling_search_spec.{md,pdf}
mdstats/analysis/natural_tiling_refinement.py  -> docs/specs/analysis/natural_tiling_refinement_spec.{md,pdf}
mdstats/analysis/framework_semantics.py        -> docs/specs/analysis/framework_semantics_spec.{md,pdf}
```


Density-backend architecture stages map as follows:

```text
mdstats/plotting/density_contracts.py  -> docs/specs/plotting/density_contracts_ld0_r1_spec.{md,pdf}
mdstats/plotting/density_diagnostics.py -> docs/specs/plotting/density_diagnostics_ld0_r2_spec.{md,pdf}
mdstats/plotting/density_planning.py   -> docs/specs/plotting/density_scene_planning_ld0_r3_spec.{md,pdf}
mdstats/plotting/density_kernel.py     -> docs/specs/plotting/density_kernel_ld0_k_spec.{md,pdf}
mdstats/plotting/density_block_direct.py -> docs/specs/plotting/density_block_direct_ld8_s2_spec.{md,pdf}
```

Runtime-derived density resource policy maps as follows:

```text
mdstats/plotting/runtime_resources.py -> docs/specs/plotting/density_runtime_resource_policy_ld10_spec.{md,pdf}
Cross-module LD10 integration          -> docs/specs/plotting/density_runtime_resource_policy_ld10_spec.{md,pdf}
```

Package-wide structured progress reporting maps as follows:

```text
mdstats/progress.py -> docs/specs/progress_spec.{md,pdf}
```


Stage-11 persistent ring geometry and atom-resolved boundary modules map as follows:

```text
mdstats/analysis/ring_geometry.py        -> docs/specs/analysis/ring_geometry_spec.{md,pdf}
mdstats/analysis/ring_geometry_frames.py -> docs/specs/analysis/ring_geometry_frames_spec.{md,pdf}
mdstats/analysis/ring_boundary.py        -> docs/specs/analysis/ring_boundary_spec.{md,pdf}
mdstats/analysis/registered_structural_view.py -> docs/specs/analysis/registered_structural_view_spec.{md,pdf}
```

Stage-C0 coordinate-registration foundations map as follows:

```text
mdstats/coordinates/contracts.py       -> docs/specs/coordinates/contracts_spec.{md,pdf}
mdstats/coordinates/periodic_gauge.py  -> docs/specs/coordinates/periodic_gauge_spec.{md,pdf}
mdstats/coordinates/metric_geometry.py -> docs/specs/coordinates/metric_geometry_spec.{md,pdf}
mdstats/coordinates/registration.py    -> docs/specs/coordinates/affine_registration_spec.{md,pdf}
mdstats/coordinates/consumer_adapters.py -> docs/specs/coordinates/consumer_adapters_spec.{md,pdf}
```

Stage-11E0a scientific density ownership maps as follows:

```text
mdstats/analysis/density/protocols.py -> docs/specs/analysis/density/protocols_spec.{md,pdf}
mdstats/analysis/density/resources.py -> docs/specs/analysis/density/resources_spec.{md,pdf}
mdstats/analysis/density/facade.py    -> docs/specs/analysis/density/facade_spec.{md,pdf}
mdstats/plotting/density_resource_policy.py -> docs/specs/analysis/density/resources_spec.{md,pdf}
mdstats/analysis/density/grid_geometry.py -> docs/specs/analysis/density/common_grid_diagnostics_spec.{md,pdf}
mdstats/analysis/density/diagnostics.py -> docs/specs/analysis/density/common_grid_diagnostics_spec.{md,pdf}
mdstats/analysis/density/stencil_diagnostics.py -> docs/specs/analysis/density/common_grid_diagnostics_spec.{md,pdf}
mdstats/analysis/density/broadening.py -> docs/specs/analysis/density/common_grid_diagnostics_spec.{md,pdf}
mdstats/analysis/density/planning.py -> docs/specs/analysis/density/common_grid_planning_spec.{md,pdf}
mdstats/plotting/density_visual_policy.py -> docs/specs/analysis/density/plotting_grid_adaptation_spec.{md,pdf}
mdstats/analysis/density/refinement.py -> docs/specs/analysis/density/fixed_kernel_grid_refinement_spec.{md,pdf}
GR0--GR5 umbrella contract -> docs/specs/analysis/density/scientific_grid_refinement_spec.{md,pdf}
```

Stage-11E-ENS0 source controls and named energy reconstruction map as follows:

```text
mdstats/io/source_controls.py -> docs/specs/io/vasp_run_controls_spec.{md,pdf}
mdstats/io/vasp_controls.py   -> docs/specs/io/vasp_run_controls_spec.{md,pdf}
mdstats/io/control_certificates.py -> docs/specs/io/vasp_ensemble_certificate_spec.{md,pdf}
mdstats/io/vasp_ensemble.py         -> docs/specs/io/vasp_ensemble_certificate_spec.{md,pdf}
mdstats/io/trajectory_quality.py    -> docs/specs/io/trajectory_quality_spec.{md,pdf}
mdstats/io/vasp_quality.py          -> docs/specs/io/trajectory_quality_spec.{md,pdf}
mdstats/io/production_regimes.py     -> docs/specs/io/production_regime_catalog_spec.{md,pdf}
mdstats/io/vasp_stationarity.py       -> docs/specs/io/production_regime_catalog_spec.{md,pdf}
mdstats/io/admissibility.py             -> docs/specs/io/ensemble_admissibility_spec.{md,pdf}
mdstats/io/vasp_admissibility.py        -> docs/specs/io/ensemble_admissibility_spec.{md,pdf}
mdstats/io/sampling_crossfit.py          -> docs/specs/io/sampling_crossfit_spec.{md,pdf}
mdstats/io/vasp.py integration -> docs/specs/io/vasp_run_controls_spec.{md,pdf}
```

Stage-11E0b registered position-force evidence maps as follows:

```text
mdstats/analysis/site_samples.py -> docs/specs/analysis/site_samples_spec.{md,pdf}
```

Stage-11E1 periodic species-density estimation maps as follows:

```text
mdstats/analysis/density/species.py -> docs/specs/analysis/density/species_spec.{md,pdf}
```

Stage-11E2 density-attractor and supported-basin discovery maps as follows:

```text
mdstats/analysis/density/attractors.py -> docs/specs/analysis/density/attractors_spec.{md,pdf}
```

Stage-11E3 local mean-force refinement maps as follows:

```text
mdstats/analysis/density/force_refinement.py -> docs/specs/analysis/density/force_refinement_spec.{md,pdf}
```

Stage-11E4 provisional temporal assignment maps as follows:

```text
mdstats/analysis/density/temporal_assignment.py -> docs/specs/analysis/density/temporal_assignment_spec.{md,pdf}
```

Stage-11E5 joint evidence validation and structural association maps as follows:

```text
mdstats/analysis/density/evidence_validation.py -> docs/specs/analysis/density/evidence_validation_spec.{md,pdf}
```

Stage-11E5a coordination fingerprints and structural classification map as follows:

```text
mdstats/analysis/density/coordination_fingerprints.py -> docs/specs/analysis/density/coordination_fingerprints_spec.{md,pdf}
```

Stage-11E5b optional geometry-conditioned site refinement maps as follows:

```text
mdstats/analysis/density/geometry_conditioning.py -> docs/specs/analysis/density/geometry_conditioning_spec.{md,pdf}
```


Stage-11E6 final hysteretic segmentation maps as follows:

```text
mdstats/analysis/density/final_segmentation.py -> docs/specs/analysis/density/final_segmentation_spec.{md,pdf}
```

Stage-11E6b observed transition paths map as follows:

```text
mdstats/analysis/density/transition_paths.py -> docs/specs/analysis/density/transition_paths_spec.{md,pdf}
```

Stage-11E7 observed network and transferred-model validation maps as follows:

```text
mdstats/analysis/density/observed_network.py -> docs/specs/analysis/density/observed_network_spec.{md,pdf}
```

## Stable module-specification policy

Permanent specifications are organized by module responsibility, not release chronology.
A stage-qualified specification may remain only when it owns a distinct production module
or a durable cross-module acceptance boundary. Chronology-only implementation checklists
must be absorbed into their owning module specifications once the implementation stabilizes,
then removed from the package documentation. The E8a S0-S4 specifications are permanent
because each maps one-to-one to a retained orchestration module; release audits remain
separate historical records.

Interactive density mesh modules map as follows:

```text
mdstats/plotting/density_mesh_contracts.py    -> docs/specs/plotting/density_mesh_contracts_spec.{md,pdf}
mdstats/plotting/density_render_budget.py     -> docs/specs/plotting/density_render_budget_spec.{md,pdf}
mdstats/plotting/density_scene_budget.py      -> docs/specs/plotting/density_scene_budget_spec.{md,pdf}
mdstats/plotting/density_scene_fit.py         -> docs/specs/plotting/density_scene_fit_spec.{md,pdf}
mdstats/plotting/density_mesh_simplify.py     -> docs/specs/plotting/density_mesh_simplify_spec.{md,pdf}
mdstats/plotting/density_mesh_execution.py    -> docs/specs/plotting/density_mesh_execution_spec.{md,pdf}
mdstats/plotting/density_browser_acceptance.py -> docs/specs/plotting/density_browser_acceptance_spec.{md,pdf}
```

Cross-module scene preparation and partitioned-topology rendering remain owned by
`docs/specs/plotting/framework_dynamics_spec.{md,pdf}`. Exact topology classes and
frame groups remain owned by `docs/specs/analysis/topology_catalog_spec.{md,pdf}`.

Stage-11 site topology maps as follows:

```text
mdstats/analysis/ring_site.py            -> docs/specs/analysis/site_topology_spec.{md,pdf}
mdstats/analysis/site_kinetic_network.py -> docs/specs/analysis/site_topology_spec.{md,pdf}
mdstats/analysis/site_assignment.py      -> docs/specs/analysis/site_assignment_spec.{md,pdf}
```


Stage-11E8a real-pilot dossier and source execution map as follows:

```text
mdstats/analysis/density/pilot_audit.py     -> docs/specs/analysis/density/pilot_audit_spec.{md,pdf}
mdstats/analysis/density/pilot_execution.py -> docs/specs/analysis/density/pilot_execution_spec.md
mdstats/analysis/density/pilot_density_attractors.py -> docs/specs/analysis/density/pilot_density_attractor_spec.md
mdstats/analysis/density/pilot_refinement_lineage.py -> docs/specs/analysis/density/pilot_refinement_lineage_spec.md
mdstats/analysis/density/pilot_structural_temporal.py -> docs/specs/analysis/density/pilot_structural_temporal_spec.md
```


Stage-11E8a shared private provenance utilities map as follows:

```text
mdstats/analysis/density/_pilot_common.py -> docs/specs/analysis/density/pilot_common_spec.md
```

Stage-11E8a real-source pilot and closeout specifications map as follows:

```text
mdstats/analysis/density/pilot_audit.py                -> docs/specs/analysis/density/pilot_audit_spec.md
mdstats/analysis/density/pilot_execution.py            -> docs/specs/analysis/density/pilot_execution_spec.md
mdstats/analysis/density/pilot_density_attractors.py   -> docs/specs/analysis/density/pilot_density_attractor_spec.md
mdstats/analysis/density/pilot_refinement_lineage.py   -> docs/specs/analysis/density/pilot_refinement_lineage_spec.md
mdstats/analysis/density/pilot_structural_temporal.py  -> docs/specs/analysis/density/pilot_structural_temporal_spec.md
mdstats/analysis/density/pilot_force_paths.py           -> docs/specs/analysis/density/pilot_force_paths_spec.md
Stage-11E8a cross-module closeout                      -> docs/specs/analysis/density/pilot_closeout_spec.md
```

- `documentation/stage11_revision43_consistency_spec.md`: revision-43 dependency, cross-fitting, ensemble-thermodynamic, ionic-temperature, trajectory-quality, and documentation-separation contract.

- `analysis/density/trajectory_temperature_quality_spec.md`: equipartition ionic temperature, deep MD-control parsing, and three-level trajectory-quality verdict.
- `analysis/density/common_grid_diagnostics_spec.md`: implemented Stage 11E-GR0 common triclinic grid geometry, periodic numerical diagnostics, stencil covariance, and effective broadening with plotting compatibility adapters.
- `analysis/density/common_grid_planning_spec.md`: implemented Stage 11E-GR1 target/finest-feasible scientific planning, exact nested ladders, backend-independent field keys, and backend-second selection.
- `analysis/density/plotting_grid_adaptation_spec.md`: implemented Stage 11E-GR2 signed atomic/framework visual-grid adaptation over GR0 geometry and GR1 replay planning with exact compatibility preservation.
- `analysis/density/fixed_kernel_grid_refinement_spec.md`: implemented Stage 11E-GR3 fixed-kernel ladders, exact stopping policy, periodic feature correspondence, and separate field/basin/corridor certificates.
- `analysis/density/scientific_grid_refinement_spec.md`: umbrella GR0--GR5 architecture with GR0--GR3 implemented and GR4--GR5 selection/ownership migration remaining.
- `documentation/stage11_revision44_grid_refinement_consistency_spec.md`: revision-44 documentation and stage-order contract.
- `documentation/stage11_revision45_dependency_force_transition_consistency_spec.md`: revision-45 force, cross-fit, transition-state, E8b, and late-stage DAG contract.
- `documentation/stage11_revision46_event_rate_gating_dag_spec.md`: revision-46 event/path/rate branching, gating order, thermodynamic branching, PMF/E8a placement, and machine-readable DAG contract.

- `documentation/stage11_revision47_provenance_kinetic_pmf_dag_spec.md`: revision-47 thermodynamic provenance, optional verification, PMF estimator split, kinetic cross-fitting, zero-event candidate edges, source identity, and typed DAG contract.

- `io/vasp_ensemble_certificate_spec.md` - Stage 11E-ENS1 ensemble and force-provenance certification.
- `io/trajectory_quality_spec.md` - Stage 11E-STAT0 temperature, integrity, and quality verdict.
- `io/production_regime_catalog_spec.md` - Stage 11E-STAT1 source-observable production-regime catalog.
- `io/sampling_crossfit_spec.md` - Stage 11E-SAMP0 complete-system cross-fit sampling foundation.

MLFF training-data preparation maps as follows:

```text
mdstats/training_data/* -> docs/specs/training_data/*_spec.{md,pdf}
MLFF-DATA umbrella stage and contract plan -> docs/specs/training_data/mlff_data_stage_plan_spec.{md,pdf}
```

Runtime modules are introduced only after their dedicated specifications are written.


MLFF-DATA1 shared sampling primitives map as follows:

```text
mdstats/sampling/autocorrelation.py -> docs/specs/sampling/shared_sampling_primitives_spec.{md,pdf}
mdstats/sampling/blocks.py          -> docs/specs/sampling/shared_sampling_primitives_spec.{md,pdf}
mdstats/sampling/assignment.py      -> docs/specs/sampling/shared_sampling_primitives_spec.{md,pdf}
```
