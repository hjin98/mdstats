---
title: "Scientific Density Specification Index"
subtitle: "Stage 11E0a--11E8a closeout analysis stack"
author: "mdstats"
date: "2026-07-27"
version: "0.20.26a0"
status: "Stage 11E-GR0 through GR3 implemented; Stage 11E-GR4 next"
---

# Specification map

| Document | Ownership | Status |
|---|---|---|
| [field protocols](protocols_spec.md) ([PDF](protocols_spec.pdf)) | `mdstats.analysis.density.protocols` | implemented |
| [scientific resources](resources_spec.md) ([PDF](resources_spec.pdf)) | `mdstats.analysis.density.resources`; rendering counterpart in `mdstats.plotting.density_resource_policy` | implemented |
| [analysis facade](facade_spec.md) ([PDF](facade_spec.pdf)) | `mdstats.analysis.density.facade` and package exports | implemented |
| [common grid geometry and numerical diagnostics](common_grid_diagnostics_spec.md) ([PDF](common_grid_diagnostics_spec.pdf)) | `mdstats.analysis.density.grid_geometry`, `diagnostics`, `stencil_diagnostics`, and `broadening`; plotting compatibility adapters | implemented GR0 |
| [common budgeted grid planning](common_grid_planning_spec.md) ([PDF](common_grid_planning_spec.pdf)) | `mdstats.analysis.density.planning`; plotting finest-shape compatibility adapter | implemented GR1 |
| [plotting grid adaptation](plotting_grid_adaptation_spec.md) ([PDF](plotting_grid_adaptation_spec.pdf)) | `mdstats.plotting.density_visual_policy`; atomic/framework visual compatibility over GR0/GR1 | implemented GR2 |
| [fixed-kernel scientific grid refinement](fixed_kernel_grid_refinement_spec.md) ([PDF](fixed_kernel_grid_refinement_spec.pdf)) | `mdstats.analysis.density.refinement`; field, basin, and corridor certificates | implemented GR3 |
| [scientific grid refinement and plotting reuse](scientific_grid_refinement_spec.md) ([PDF](scientific_grid_refinement_spec.pdf)) | implemented GR0--GR3 foundations and planned GR4--GR5 selection/ownership migration | partial |
| [periodic species density](species_spec.md) ([PDF](species_spec.pdf)) | `mdstats.analysis.density.species` | implemented |
| [attractors and supported basins](attractors_spec.md) ([PDF](attractors_spec.pdf)) | `mdstats.analysis.density.attractors` | implemented |
| [local mean-force refinement](force_refinement_spec.md) ([PDF](force_refinement_spec.pdf)) | `mdstats.analysis.density.force_refinement` | implemented |
| [provisional temporal assignment](temporal_assignment_spec.md) ([PDF](temporal_assignment_spec.pdf)) | `mdstats.analysis.density.temporal_assignment` | implemented |
| [joint evidence validation and structural association](evidence_validation_spec.md) ([PDF](evidence_validation_spec.pdf)) | `mdstats.analysis.density.evidence_validation` | implemented |
| [species-dependent coordination fingerprints](coordination_fingerprints_spec.md) ([PDF](coordination_fingerprints_spec.pdf)) | `mdstats.analysis.density.coordination_fingerprints` | implemented |
| [geometry-conditioned site refinement](geometry_conditioning_spec.md) ([PDF](geometry_conditioning_spec.pdf)) | `mdstats.analysis.density.geometry_conditioning` | implemented |
| [final hysteretic segmentation and residence statistics](final_segmentation_spec.md) ([PDF](final_segmentation_spec.pdf)) | `mdstats.analysis.density.final_segmentation` | implemented |
| [observed transition paths and collective diagnostics](transition_paths_spec.md) ([PDF](transition_paths_spec.pdf)) | `mdstats.analysis.density.transition_paths` | implemented |
| [observed periodic network and transfer validation](observed_network_spec.md) ([PDF](observed_network_spec.pdf)) | `mdstats.analysis.density.observed_network` | implemented |
| [Na-LTA NVE-continuation pilot dossier](pilot_audit_spec.md) ([PDF](pilot_audit_spec.pdf)) | `mdstats.analysis.density.pilot_audit` | implemented |
| [real-trajectory source bootstrap](pilot_execution_spec.md) | `mdstats.analysis.density.pilot_execution` | implemented |
| [framework-registered density and attractor pilot](pilot_density_attractor_spec.md) | `mdstats.analysis.density.pilot_density_attractors` | implemented |
| [density refinement and attractor lineage](pilot_refinement_lineage_spec.md) | `mdstats.analysis.density.pilot_refinement_lineage` | implemented |
| [structural mapping and temporal-support preparation](pilot_structural_temporal_spec.md) | `mdstats.analysis.density.pilot_structural_temporal` | implemented |
| [force-density and transition-path readiness](pilot_force_paths_spec.md) | `mdstats.analysis.density.pilot_force_paths` | implemented |
| [Stage 11E8a closeout and regression closure](pilot_closeout_spec.md) | cross-module pilot and density-resource boundary | implemented |

The plotting-era atomic-density, framework-density, kernel, sparse-field,
planning, and runtime-resource specifications remain normative numerical oracles
for kernels that have not yet migrated into analysis-owned modules. Revision 56 completes GR3: common grid geometry and diagnostics, target/finest-feasible planning, exact nested ladders, backend-independent field identities, and fixed-kernel field/basin/corridor certificates are analysis-owned, while signed atomic/framework visual adaptation remains plotting-owned. GR4--GR5 remain planned for cross-fitted numerical-hypothesis freezing and later ownership migration.
Stage 11E0a establishes the ownership boundary; Stage 11E1 owns the registered periodic
species field; Stage 11E2 owns deterministic supported topology downstream of
that field; Stage 11E3 owns PMF-admissible local force refinement without
changing the spatial catalog; Stage 11E4 owns provisional temporal evidence
without nearest-center filling or final event certification; Stage 11E5 owns
orthogonal joint-evidence validation, source-bound structural association,
conservative exchangeability checks, and the frozen-versus-refit catalog
boundary without final event certification; Stage 11E5a owns exact physical M--O/M--T fingerprints, harmonic diagnostics, occupancy-conditioned mixtures, and conservative structural classification without moving the frozen E5 catalog; Stage 11E5b owns optional one-pass framework-conditioned center regression, translated nested regions, static/dynamic counterfactual memberships, moving-boundary diagnostics, overlap conflicts, and occupancy bounds without publishing final events; Stage 11E6 owns final hysteretic residence and passage segmentation; Stage 11E6b owns exact registered transition paths, periodic translations, compatible path ensembles, and collective-event diagnostics without rates or a kinetic network; Stage 11E7 owns the observed periodic network, structural-versus-observed comparison, identity-preserving compact transfer models, and fail-closed held-out or external transfer outcomes without state merging, refitting, or rate inference. Stage 11E8a-S0 binds one exact raw trajectory to a physical fixed-cell C0 baseline and E0b Na catalog. Stage 11E8a-S1 selects and validates the all-framework center-of-geometry translation gauge, executes a represented-time-preserving E1 density pilot and one E2 attractor realization, and keeps later evidence fail-closed. Stage 11E8a-S2 executes bandwidth lineage, grid refinement, and reference-cell sensitivity without weakening unstable saddle topology. Stage 11E8a-S3 maps the exploratory central attractors onto actual serrated primitive-ring oxygen polygons and transfers the exact coordinate-identical partition to the full represented-time catalog for provisional Stage 11E4 temporal diagnostics. Stage 11E8a-S4 executes the provenance-strict E3 force-refinement boundary and source-bound E6/E6b readiness gate without promoting inadmissible forces or an unresolved spatial hypothesis.

## Stage 11E8a pilot dossier and source execution

`pilot_audit.py` owns the source-bound Na-LTA NVE-continuation pilot dossier, bundled
real-evidence preflight, explicit blockers, accepted/unresolved fractions,
resource accounting, and deterministic human-readable report. It does not
replace a missing raw trajectory with legacy summaries.

`pilot_execution.py` owns Stage 11E8a-S0. Given a normalized real trajectory and
its raw path, it hashes the source bytes, validates the exact Na-LTA composition,
executes the physical fixed-cell C0 baseline, constructs the compact E0b Na
position/force sample catalog, and advances the dossier to
`blocked_missing_required_evidence`. It does not execute or infer E1--E7 evidence.

`pilot_density_attractors.py` owns Stage 11E8a-S1: framework-gauge selection and sensitivity, deterministic represented-time quadrature, one E1 density realization, one E2 attractor realization, and the corresponding partial dossier evidence.
`pilot_refinement_lineage.py` owns Stage 11E8a-S2: signed Cartesian bandwidth lineage, central-bandwidth grid refinement, reference-cell sensitivity, and fail-closed scale/topology certificates.

`pilot_structural_temporal.py` owns Stage 11E8a-S3: packaged persistent-ring replay, actual serrated oxygen-polygon geometry, deterministic attractor-to-ring candidates, exact spatial-partition transfer to the full-weight sample catalog, and provisional Stage 11E4 temporal support. It does not publish final events, paths, or rates.

`pilot_force_paths.py` owns Stage 11E8a-S4: provenance-strict E3 execution and conditional E6/E6b readiness. It records executed blockers rather than inventing PMF or paths.

The closeout specification freezes the engineering status after S4: deterministic LD6 research limits, exact explicit-grid Phase-A bounds, isolated runtime-resource tests, and optional interactive dependency handling. It does not change the scientific dossier or authorize Stage 11E8b kinetics.



## Stage 11E8a private common utilities

`_pilot_common.py` owns deterministic serialization, signing, metadata freezing,
array accounting, and evidence replacement shared by S0-S4. It is private and
does not alter the public pilot schemas. See `pilot_common_spec.{md,pdf}`.
