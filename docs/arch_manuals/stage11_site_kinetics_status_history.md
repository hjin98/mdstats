---
title: "Stage 11 Part II - Implementation Status and Revision History"
author: "mdstats"
date: "2026-07-27 (status appendix for architecture revision 57)"
toc: true
toc-depth: 3
numbersections: true
geometry: margin=0.85in
fontsize: 10pt
---

## 0.20.26a0 - Stage 11E-GR3

- Added signed fixed-kernel scientific-refinement policies bound to source, SAMP0 partition, scientific resources, and one immutable Cartesian kernel.
- Added exact factor-two nested ladders with a $\Delta_{\max}/\sigma_{\min}\le 0.5$ physical gate and two required consecutive passing comparisons.
- Added independent field, basin, and corridor convergence certificates with explicit budget-, depth-, metric-, and missing-evidence outcomes.
- Added deterministic periodic basin correspondence, split/merge/ambiguity handling, corridor bottleneck/width/density/support comparisons, canonical replay, and tamper rejection.
- Preserved GR2 visual fields, backend behavior, meshes, and browser policy without promoting visual adaptation to scientific convergence.


## 0.20.25a0 - Stage 11E-GR2

- Added signed plotting-owned visual-grid adaptation records over common GR0 geometry and optional GR1 replay plans.
- Adapted atomic and framework density producers without changing scalar fields, selected grids, bandwidths, diagnostics, warnings, storage routing, meshes, or browser/scene policy.
- Preserved visual Gaussian/grid coupling as plotting policy rather than scientific fixed-kernel convergence.
- Added exact old/new field and metadata oracle checks, canonical replay, tamper rejection, and analysis-layer rendering-import isolation tests.


## 0.20.24a0 - Stage 11E-GR1

- Added signed target and finest-feasible logical-grid plans under scientific resource limits.
- Added exact deterministic nested-grid ladders with target-reached, budget-limited, and level-limited outcomes.
- Added backend-independent field-reuse cache keys and fail-closed source/sample/weight/kernel/grid/normalization checks.
- Added backend candidate and selection records that cannot change the frozen logical grid or fixed kernel.
- Moved the plotting-private finest-budgeted grid helper behind an analysis-owned compatibility adapter while preserving the zero-target adaptive sentinel.


## 0.20.23a0 - Stage 11E-GR0

- Moved common periodic grid shape, realized interval, cell-metric, Frechet-mean,
  spread, reciprocal-resolution, CIC covariance, Gaussian-stencil moment, and
  effective-broadening diagnostics into analysis ownership.
- Added immutable `DensityGridGeometry` serialization and analysis-domain density
  numerical exceptions.
- Retained plotting compatibility imports, exact numerical/metadata parity, and
  graph-facing resource-error translation without importing rendering policy into
  the common layer.
- Added focused orthogonal/triclinic, periodic-invariance, dense-oracle, ownership,
  serialization, and exception-boundary tests.


## 0.20.22a0 - Stage 11E-SAMP0

- Implemented signed complete-system cross-fit blocks inside one accepted STAT1 regime.
- Added explicit and nested discovery/model-selection partition modes with held-out basin, corridor, and thermodynamic domains.
- Added local decorrelation, complete-system effective-sample, represented-time, block, and replica diagnostics.
- Added versioned `SamplingAdequacyPolicy` and the exact `stage11_feature_correspondence_v1` preset.
- Added immutable replay, sample-mask APIs, final-refit lineage separation, and focused provenance/adequacy tests.


## 0.20.21a0 - Stage 11E-STAT2

- Implemented source- and policy-bound ensemble admissibility per STAT1 regime.
- Added explicit descriptive, microcanonical, canonical, NpT/Gibbs, reweighted,
  conditional-force, diagnostic-only, and PMF-force overlay semantics.
- Preserved NVE as microcanonical by default and required explicit signed approximation
  or verified reweighting provenance for promotion.
- Integrated STAT2 into full-source VASP reader metadata and added deterministic replay
  and E0b mask-intersection tests.

## 0.20.20a0 - Stage 11E-STAT1

- Implemented source-observable block construction, deterministic change-point detection, stationarity diagnostics, external-boundary testing, and signed production-regime catalogs.
- Updated the STAT0 NVE drift policy to 1 meV/(atom ps) for strict quality and 26 meV/(atom ps) for hard failure.
- Retained the real Na-LTA source as one full-source scientific production candidate with no detected heating transient, while preserving the independently degraded total-energy-conservation verdict.

## 0.20.19a0 - Stage 11E-STAT0

- Implemented equipartition ionic-temperature reconstruction, correlated uncertainty, hard-integrity checks, soft numerical-quality checks, NVE energy diagnostics, and the three-level trajectory-quality verdict.
- Classified the real Na-LTA NVE continuation source as degraded but analyzable rather than unqualified.


# Purpose

This appendix contains descriptive release history and audit status removed from the
normative Part II architecture manual. It does not define scientific contracts or the
current implementation order. The authoritative manual is
`stage11_site_kinetics_architecture.{md,pdf}`.

# Revision 57 implementation update

Architecture revision 57 records Stage 11E-GR3 as implemented. One signed
`ScientificGridRefinementPolicy` now freezes source, resource, SAMP0 partition,
and Cartesian kernel identities before a deterministic GR1 ladder is evaluated.
Separate field, basin, and corridor certificates apply the exact
`stage11_grid_stopping_v1` policy and retain budget, depth, metric, or missing
evidence as unresolved. GR2 plotting adaptation remains unchanged. Final
cross-fitted numerical-hypothesis selection and candidate freezing remain GR4.

# Revision 55 implementation update

Architecture revision 55 records Stage 11E-GR2 as implemented. Atomic and
framework plotting paths now bind their resolved visual numerics to signed GR0
geometry and optional GR1 replay plans through
`DensityVisualGridAdaptation`. Exact field values, metadata, warnings, storage
routing, meshes, and browser/scene admission remain compatible. Visual
Gaussian/grid coupling remains plotting policy and is not promoted to the
fixed-kernel scientific convergence owned by Stage 11E-GR3.

# Revision 54 implementation update

Architecture revision 54 records Stage 11E-GR1 as implemented. Scientific target and finest-feasible logical-grid decisions, exact nested ladders, backend-independent field identities, and backend-second selection now have analysis ownership. Browser, mesh, scene, and HTML policy cannot change those plans. No density estimator, mesh producer, or browser admission policy moved, and no budget-limited grid was promoted as scientifically converged.

# Revision 53 implementation update

Architecture revision 53 records Stage 11E-GR0 as implemented. Common density-grid
geometry and diagnostics now have analysis ownership; plotting is a compatibility
adapter for the migrated names and translates analysis numerical failures at its
boundary. No density estimator, backend selection, mesh, scene, or browser policy moved
in this stage, and no scientific result was promoted.


# Revision 48 implementation update

Version `0.20.17a0` implements Stage 11E-ENS0. The package now reconstructs exact
explicit and effective VASP controls, exact named ionic-step energy channels, numerical
MD quality controls, per-step SCF iteration traces, explicitly bound companion-file
states, and one immutable source-trajectory bundle identity. `SYSTEM` remains a
non-authoritative user comment. The real 1,500-step Na-LTA source reconstructs VASP
6.4.2, 168 atoms, 1,500 ionic steps, `MDALGO=2`, `SMASS=-3`, `ISIF=2`, `POTIM=1 fs`,
`EDIFF=1e-5 eV`, complete forces/cells/stresses, zero native velocity frames, and eight
complete named energy channels. Ensemble interpretation and quality verdicts remain
ENS1 and STAT0.

# Revision 47 planning correction

Architecture revision 47 requires source-bound provenance on every thermodynamic result
and makes independent cross-checks optional verification rather than a prerequisite for a
source-qualified estimate. It splits density-derived, force-integrated, and PMF-crosscheck
products; introduces structural/thermodynamic and kinetic crossfit partitions; adds a
predeclared rate-candidate edge universe for zero-event bounds; assigns final candidate
freezing to GR4; adds persistent model-generation records; separates E8b product nodes;
and upgrades the machine-readable DAG to typed edges with source-bundle identity. No
runtime scientific result changed.

# Revision 46 planning correction

Architecture revision 46 separates event-supported edges and empirical rates from
path-resolved and saddle-supported products; splits E9 into pre-rate and post-fit
adequacy; moves G0 gating diagnosis before F0 rate promotion; branches THERMO4A away from
THERMO3A; places PMF, E8a milestone sub-dossiers, and M1/M2 in the authoritative graph;
and adds a machine-readable DAG with semantic tests. The release-specific statement that
Stage 11E5a first appeared in `0.20.4a0` is retained here rather than in the normative
manual. No runtime scientific result changed.

# Revision 45 planning correction

Architecture revision 45 repairs the remaining normative dependency and scientific-
semantics issues. It separates mechanical force refinement from canonical thermodynamic
mean force, adds a dedicated thermodynamic-validation partition, stops SAMP2 at
preliminary corridor/saddle-candidate support, splits static and event-conditioned
transition thermodynamics, divides pre-kinetic thermodynamic validation from post-rate
kinetic consistency, assigns RateBoundModel to Stage 11F0, and defines roadmap-level
contracts for Stages 11G--11I. Historical implementation bullets were removed from the
normative manual and remain in this appendix. No runtime scientific output changed.

# Revision 44 planning update

Architecture revision 44 adopts a partial refactor of the tested atomic-density grid
machinery. Backend-neutral grid geometry, periodic spread, reciprocal resolution,
artificial broadening, budgeted planning, and dense/local-sparse feasibility move toward
analysis ownership through stages 11E-GR0-GR5. Plotting retains its visual one-grid and
bandwidth/grid coupling policy. Stage 11 uses fixed-kernel grid ladders and separate field,
basin, and corridor convergence certificates. This is a planning/documentation revision;
no current density field or pilot result is changed.

# Revision 43 planning update

Architecture revision 43 adds the equipartition ionic-temperature contract, deep
`vasprun.xml` numerical-control reconstruction, and the three-level trajectory-quality
verdict. This is a planning/documentation revision only. Runtime ENS/STAT modules remain
to be implemented. A degraded-quality trajectory is permitted to proceed with warnings
and signed flags; only catastrophic `unqualified` integrity failure blocks scientific
execution.

# Revision history retained from revision 41

Architecture revision 41 added the ensemble, sampling-confidence, and thermodynamic roadmap. It
required source-control reconstruction of the MD ensemble instead of trusting user
labels, ensemble-specific conservation and stationarity certificates, feature-level
sampling confidence for basins and saddles, partial-catalog scope diagnostics,
basin and saddle thermodynamic certificates, interaction-aware occupancy models,
and multi-temperature or independent-estimator consistency tests. These stages are
planned only; they do not retroactively promote the current Na-LTA pilot beyond
`scientifically_partial`.

Architecture revision 40 establishes the normative Part I/Part II ownership
boundary, consolidates private E8a provenance helpers, and regenerates the
maintained architecture/specification PDFs without changing scientific outputs.

Architecture revision 39 closes the Stage 11E8a engineering and package-wide
regression boundary. All S0-S4 modules are implemented, the bounded file-complete
test matrix is clean, and the real pilot remains explicitly
`scientifically_partial` rather than being promoted to kinetics.

Architecture revision 38 adds Stage 11E8a-S4. The source-bound central S2 density and attractor catalog now feed the existing Stage 11E3 force-refinement contract without any provenance override. The real trajectory supplies 1,440 represented-time joint position/force samples but zero PMF-admissible samples because equilibrium, stationarity, and declared constant-temperature PMF provenance are not jointly established; all 24 local refinements are therefore retained as `pmf_provenance_rejected`. S4 also records transition-path readiness from the eight provisional S3 passages, but it refuses Stage 11E6 and 11E6b because the S2 saddle topology is non-authoritative and no source-compatible E5 validated frozen-state catalog has been supplied. The dossier now contains every required evidence record and is `scientifically_partial`, with force-density and transition-path blockers explicit. Stage 11E8b remains prohibited pending closure review.

Architecture revision 37 adds Stage 11E8a-S3. The packaged persistent Na-LTA topology and 82 primitive rings are replayed against the mean registered framework. Each 4R/6R/8R is represented by its actual locally unwrapped ordered oxygen polygon; circular and elliptical substitutes are prohibited. All 24 central exploratory attractors have unique ring candidates, but structural evidence remains partial because the S2 scale and saddle topology are unresolved. The signed S2 partition is transferred only to the exact coordinate-identical full 36,000-sample catalog, after which Stage 11E4 reports persistent provisional temporal support with return excursions but no resolved jumps. Final event and path claims remain closed. Force-density agreement and observed transition paths are now the remaining mandatory E8a blockers. Stage 11E8a-S4 is next; Stage 11E8b remains prohibited.

Architecture revision 36 adds Stage 11E8a-S2. The S1 source, registration, and represented-time catalog now feed an explicit 0.40/0.50/0.60 Å Cartesian bandwidth ladder, deterministic attractor correspondence, 12³→16³ central-bandwidth grid refinement, and signed reference-cell sensitivity. The fixed cell passes the exact identity comparison. All 24 basin identities match across the bandwidth ladder, but saddle adjacency changes across bandwidth and grid realizations; scale consensus is therefore `scale_ambiguous` and grid topology is `unstable`. These are retained as partial evidence rather than weakened. Structural mapping, temporal support, force-density agreement, and transition paths remain missing. Stage 11E8a-S3 is the next mandatory boundary; Stage 11E8b remains prohibited.

Architecture revision 35 adds Stage 11E8a-S1. It selects and validates the
all-framework center-of-geometry translation gauge, compares an independent
center-of-mass gauge, preserves represented time through deterministic
quadrature, and executes one source-bound E1 density and E2 attractor pilot while
leaving refinement, temporal, force, and path evidence unresolved.

Architecture revision 34 adds Stage 11E8a-S0, the first real-trajectory execution boundary. The exact raw file bytes are SHA-256 bound to a physical fixed-cell C0 registration and a compact E0b Na position/force catalog. Equilibrium and stationarity remain unresolved, and no E1--E7 result is inferred from the source bootstrap. The pilot is no longer blocked by a missing trajectory, but remains blocked by missing required density, attractor, temporal, force-agreement, path, and network evidence. Stage 11E8a-S1 is the next mandatory boundary; Stage 11E8b remains prohibited.

Architecture revision 33 adds the Stage 11E8a source-bound pilot dossier and
execution preflight while preserving the source, registration,
structural-geometry, sample-catalog, scientific-density, supported-attractor,
local-force, provisional-temporal, joint-evidence, coordination-fingerprint,
geometry-conditioning, final-segmentation, observed-path, and observed-network
contracts completed in revisions 16--32. The dossier records every required
pilot evidence channel, accepted and unresolved fractions, artifacts, cost,
memory, scientific outcomes, and explicit blockers. The bundled nominal-300-K
Na-LTA reference, 2,000-frame topology summary, primitive-ring catalog, and
1,300-frame density benchmark are certified as legacy real evidence, but are not
promoted to source-bound E0b--E7 results. Because the raw trajectory and complete
serialized stage products are absent, the real pilot remains blocked and Stage
11E8b must not begin. The optional support-limited PMF branch remains available.

# Stage 11E8a S0--S4 detailed implementation history

## Historical Stage 11E8a - nominal-300-K Na-LTA pilot

Report registration success, structural mapping, stationarity, kernel metric and triclinic
periodization, reference-cell sensitivity, field/topology certificates, attractor lineage,
provisional cores, temporal support, force availability, force-density agreement,
observed transition paths, unresolved fractions, cost, and memory.

A valid outcome may be:

```text
site centers resolved
two basins spatially and temporally supported
one observed connection
transition-path ensemble undersampled
rates unidentified
global PMF unsupported
```

Implementation status in `0.20.9a0`:

- `mdstats.analysis.density.pilot_audit` owns the immutable E8a dossier,
  required-evidence taxonomy, artifact manifest, accepted/unresolved fractions,
  resource accounting, scientific outcome, strict serialization, and Markdown
  rendering;
- the bundled 168-atom Na-LTA reference structure is read with real ASE and its
  24 Na, 24 Al, 24 Si, and 96 O composition is verified;
- the real historical 2,000-frame topology summary, 82-ring catalog complete
  through size eight, 1,300-frame all-species density benchmark, and plotting
  summary are hashed and retained as `legacy_summary_only` or partial evidence;
- legacy summaries never substitute for raw registered coordinates or current
  E0b--E7 source-bound results; and
- the packaged preflight therefore reports `blocked_missing_trajectory`.

The following S0 preflight text is retained as historical status from revision 33;
it was superseded by the completed S0--S4 real-source execution and revision-39
engineering closeout. Stage 11E8b now follows the revised entry gates below.

Implementation status in `0.20.10a0` (Stage 11E8a-S0):

- `mdstats.analysis.density.pilot_execution` accepts one already-normalized real
  trajectory and hashes the exact source bytes independently of in-memory
  coordinate signatures;
- the source must match the required 168-atom composition: 24 Na, 24 Al, 24 Si,
  and 96 O, with trajectory semantics, physical time, and full periodicity;
- the default C0 operation is the physical fixed-cell baseline with no fitted
  translation gauge, preserving source positions and force covectors while
  certifying round-trip and work invariance;
- one compact frame-major E0b Na position/force catalog is emitted and bound to
  the raw digest, registration signature, and source contract; and
- equilibrium, stationarity, E1 density, E2 attractors, E3 force-density
  agreement, E4--E6b temporal/path evidence, and E7 network evidence remain
  unresolved, so the dossier correctly reports
  `blocked_missing_required_evidence`.

Implementation status in `0.20.11a0` (Stage 11E8a-S1):

- `mdstats.analysis.density.pilot_density_attractors` selects all 144 framework
  atoms as the matched-reference group and uses equal geometric weights as the
  canonical density/site coordinate gauge;
- an independent center-of-mass registration measures gauge-weighting
  sensitivity without changing the selected field coordinates;
- localized framework residuals use an exact geodesic-convexity certificate for
  the unique intrinsic translation mean, with the exhaustive multiseed torus
  solver retained as the fallback;
- deterministic contiguous represented-time bins preserve the full trajectory
  measure while reducing the real E1 pilot to 60 positive-weight frames;
- one 16-cubed, 0.50-Angstrom Gaussian E1 field and one E2 attractor realization
  are source-bound and recorded with normalization, image-tail, support,
  topology, and provisional-core diagnostics; and
- structural mapping, reference-cell sensitivity, temporal support,
  force-density agreement, and transition paths remain missing, so the dossier
  correctly stays `blocked_missing_required_evidence`.

Implementation status in `0.20.12a0` (Stage 11E8a-S2):

- `mdstats.analysis.density.pilot_refinement_lineage` evaluates the signed
  0.40/0.50/0.60-Angstrom bandwidth ladder and deterministic attractor
  correspondence on the source-bound S1 catalog;
- the central 0.50-Angstrom hypothesis is compared on 12-cubed and 16-cubed
  grids, reusing the identical signed S1 realization where applicable;
- the fixed-cell reference sensitivity is accepted by exact identity;
- all 24 basin identities persist, but saddle adjacency changes across both
  bandwidth and grid realizations, so scale consensus remains `scale_ambiguous`
  and topology refinement remains `unstable`; and
- structural mapping, temporal support, force-density agreement, and transition
  paths remain missing.

Implementation status in `0.20.13a0` (Stage 11E8a-S3):

- `mdstats.analysis.density.pilot_structural_temporal` digest-binds the packaged
  persistent T--O topology and 82 primitive rings complete through size eight;
- actual ordered oxygen polygons are locally unwrapped in the triclinic metric,
  fitted to ring planes, and retained as serrated boundaries without circle or
  ellipse substitution;
- central exploratory attractors receive deterministic ring candidates with
  plane distance, polygon clearance, side, and serrated-boundary radial
  diagnostics;
- the represented-time quadrature partition is transferred to the full E0b Na
  catalog only after exact source, registration, topology, atom, frame,
  coordinate, and image-shift identity is proven;
- Stage 11E4 provisional temporal diagnostics then use all 1,500 frames and all
  36,000 Na samples, retaining excursions, censoring, gaps, and stride
  sensitivity without nearest-center filling; and
- all 24 mappings are unique and temporal support is persistent, but both
  evidence records remain partial because the S2 scale/grid saddle topology is
  not authoritative.

Implementation status in `0.20.14a0` (Stage 11E8a-S4):

- `mdstats.analysis.density.pilot_force_paths` executes E3 on the exact central S2 source-bound density and attractor signatures;
- 1,440 represented-time joint position/force samples are available, but zero samples satisfy the stricter PMF-force mask, so all 24 local refinements are provenance-rejected without deleting any attractor;
- eight S3 passages are retained as five return excursions and three right-censored exits, with zero provisional inter-attractor jumps;
- Stage 11E6 final segmentation and Stage 11E6b observed paths are not executed because the S2 spatial hypothesis remains non-authoritative and no source-compatible E5 validated state catalog is available; and
- every required E8a evidence record is now present, changing the dossier from `blocked_missing_required_evidence` to `scientifically_partial` with explicit force-density and transition-path blockers.

Implementation status in `0.20.15a0` (Stage 11E8a closeout):

- the S0--S4 implementation sequence is complete and no additional E8a software stage is mandatory;
- LD6 research phase sweeps use the documented deterministic 2,000-evaluation default rather than a host-calibration-dependent value;
- explicit atomic and framework density grid shapes produce exact Phase-A logical and mesh bounds instead of fictitious per-field maximums;
- runtime-derived production resource limits remain authoritative while tests of one limit are constructed below all earlier limits;
- optional `fast-simplification` tests skip in the base environment while the production API retains fail-closed dependency diagnostics; and
- every package test file has been replayed in bounded groups, yielding 1,493 passes, one optional skip, and no failures.

The scientific pilot remains partial. Stage 11E8b may proceed only for explicitly occupancy/structure-only comparisons, or after a new resolved-grid and adequately sampled dataset satisfies the spatial-topology, stationarity/PMF-provenance, and transition-support gates. No kinetic comparison is authorized by the closeout release.

Implementation status in `0.20.16a0` (architecture and maintainability refactor):

- framework/ring/natural-tiling/structural-semantic ownership is consolidated in
  Part I;
- registered statistical-site and kinetic ownership is consolidated in Part II;
- the stale duplicated Stage 11C-I plan is removed from Part I;
- common E8a canonical serialization, hashing, immutable metadata, array
  accounting, and evidence replacement are centralized without changing public
  signatures; and
- maintained Stage 11 architecture/specification PDFs are regenerated from the
  release Markdown sources.

The scientific status is unchanged: E8a is engineering-complete and the real
Na-LTA pilot is `scientifically_partial`.


# Current normative status

Architecture revision 57 is the controlling documentation and planning contract. ENS0, ENS1, STAT0, STAT1, STAT2, SAMP0, GR0, GR1, GR2, and GR3 are implemented. Stage 11E-GR4 and later stages remain planned. Existing S0--S4 algorithms and the `scientifically_partial` pilot dossier are unchanged.

# Historical contract-test notes

## Additional revision-15 contract tests

Focused synthetic and metamorphic tests also require:

- registration translation invariance when the analysis metric is changed but the
  registration-fit metric is fixed;
- continuous translation-branch recovery across periodic crossings, explicit segment
  resets, and fail-closed ambiguous branch histories;
- affine covariance of the density score covector and the metric gradient, including
  force agreement only with the covector;
- model selection on selection blocks followed by untouched final-validation blocks,
  plus explicit selection-conditioned and unavailable-validation outcomes;
- overlapping moving cores and basins with exclusive assignment, occupancy bounds,
  and ambiguous first-hit behavior;
- pooling compatible independent-run transition paths whose member registration
  signatures differ; and
- a supported annular or punctured PMF domain with nontrivial circulation despite
  locally small curl.


## Earlier revision-14 contract tests retained

Focused synthetic and metamorphic tests also require:

- periodic reference-translation recovery under arbitrary common image relabeling;
- ambiguous translation-branch rejection and nonuniform-framework residual detection;
- closest-lattice-vector agreement for strongly triclinic cells where componentwise
  fractional rounding is incorrect;
- affine covariance of the analysis geometry metric, gradient flow, basin ownership, and
  attractor correspondence;
- stable-scale selection with one clear interval, competing split/merge hypotheses, and an
  explicit `scale_ambiguous` result;
- unsupported gaps that cannot connect basins or create saddles;
- one-attractor core construction without an invented interbasin saddle;
- recovery of a displaced force center from a nonzero intercept and rejection when the
  inferred center leaves the supported chart;
- coordinate-correct framewise M--O forward prediction under variable cells;
- biased-density reweighting with an unusable force channel unless the bias gradient is
  explicitly removed;
- one-pass frozen geometry-conditioned refinement with reproducible static/dynamic
  disagreement diagnostics; and
- periodic HDBSCAN comparison for a cluster crossing a cell boundary.
