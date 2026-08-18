# Stage 11E-STAT1 production-regime catalog specification

## Status and ownership

This specification owns the first runtime implementation of **Stage 11E-STAT1**.
The implementation owners are:

- `mdstats.io.production_regimes`;
- `mdstats.io.vasp_stationarity`;
- full-source metadata integration in `mdstats.io.vasp`.

STAT1 consumes the signed ENS0 source identity, ENS1 simulation-control certificate,
and STAT0 trajectory-quality verdict. It does not reinterpret `SYSTEM`, filenames, or
user labels. It does not use adaptive site density, discovered basins, or transition
features to select a production interval.

## Purpose

STAT1 answers a narrower question than STAT0:

> Which contiguous source intervals show source-observable evidence compatible with a
> stable production regime, and how strongly is that conclusion conditioned on the same
> data used to select the interval?

It does not certify a canonical PMF, a microcanonical thermodynamic measure, or site
sampling adequacy. Those permissions belong to STAT2 and later stages.

## Inputs

The public source-general API is:

```python
assess_production_regimes(
    collection,
    *,
    energy_catalog,
    simulation_control_certificate,
    trajectory_quality_verdict,
    source_identity_signature,
    policy=None,
    external_candidate_boundaries=(),
)
```

The VASP convenience API is:

```python
assess_vasp_production_regimes(...)
```

Every input signature must refer to the same `SourceTrajectoryBundleIdentity`. Source
mixing is a hard contract error.

## Persistent records

STAT1 defines immutable, signed records:

- `ProductionWindowPolicy`;
- `QualityDiagnosticBlockPartition`;
- `ObservableStationarityDiagnostic`;
- `ExternalBoundaryAssessment`;
- `ChangePointCatalog`;
- `ProductionRegime`;
- `ProductionRegimeCatalog`.

All records support deterministic JSON serialization and signature verification.

## Source-observable restriction

The first implementation may use only predeclared low-complexity observables available
before site discovery:

- equipartition ionic temperature reconstructed by STAT0;
- named potential, kinetic, and total-energy channels from ENS0;
- cell volume and cell behavior;
- pressure and stress when present;
- center-of-mass momentum only when native velocities are available.

The adaptive E1 density and any inferred site or saddle catalog are forbidden inputs.

## Quality-diagnostic blocks

`QualityDiagnosticBlockPartition` covers the complete source with contiguous
complete-system blocks. All atoms and all mobile ions from one frame remain in one
block.

The target block length is

```text
max(minimum_block_frames,
    ceil(autocorrelation_block_multiplier * max_detrended_tau))
```

where `max_detrended_tau` is the largest accepted integrated autocorrelation time among
the nonoptional source observables after removing only a linear trend for correlation-
length estimation. The raw source series are never detrended for stationarity tests.

Fewer than `minimum_independent_blocks` yields `insufficient`; thresholds are never
relaxed to force a result.

STAT1 blocks are quality-diagnostic blocks. They are distinct from the later SAMP0
`EvidenceCrossfitPartition`.

## Change-point detection

The initial implementation uses exact penalized multivariate least-squares segmentation
on standardized complete-system block means. The cost, penalty scale, minimum segment
length, maximum number of change points, selected block indices, and frame indices are
persisted.

A smooth drift does not have to produce a discrete change point. Change-point absence
therefore does not imply stationarity.

User- or workflow-declared continuation boundaries are candidates, not truth. Internal
boundaries receive a two-sided block-mean test. Source-edge boundaries are retained as
provenance but cannot be tested without the preceding or following source.

## Observable stationarity

For each candidate regime and observable, STAT1 records:

- raw mean and standard deviation;
- block standard deviation;
- integrated autocorrelation time;
- slope and slope standard error;
- slope z score;
- observation-span change;
- observation-span change normalized by block fluctuation;
- `stationary`, `nonstationary`, `insufficient`, or `unavailable`.

An observable is nonstationary only when both the trend significance and normalized
span thresholds fail. This prevents tiny statistically detectable effects from being
confused with materially important drift.

The first policy distinguishes:

- `supported`: every primary distribution/cell observable passes;
- `ambiguous`: evidence is mixed or the drift is measurable but bounded;
- `rejected`: the primary distribution evidence is materially nonstationary;
- `insufficient`: too few independent blocks.

Total-energy drift is retained as an ensemble-conservation diagnostic and remains bound
to the STAT0 quality verdict. It is not silently repaired by segmentation.

## Thermalization evidence

STAT1 reports evidence, not proof of ergodicity:

- `no_detected_transient`;
- `transient_detected`;
- `ambiguous`;
- `insufficient`.

A full source with no accepted change point may report `no_detected_transient` even when
slow stationarity drift remains ambiguous. This means no heating-like source transient
was detected; it does not certify a thermodynamic ensemble.

## Production interval outcome

Each contiguous regime is labeled:

- `scientific_candidate` when stationarity is supported and STAT0 is not unqualified;
- `diagnostic_only` when stationarity is ambiguous;
- `insufficient` when independent support is too small;
- `rejected` when stationarity fails or STAT0 is unqualified.

Strictly qualified and degraded-quality trajectories may both contain scientific
production candidates. An unqualified trajectory cannot produce a scientific regime.

Selection provenance is explicit:

- `full_source`;
- `externally_bounded_tested`;
- `selection_conditioned`.

Downstream uncertainty must preserve this status.

## NVE drift policy update

The STAT0 policy used by this release adopts the requested two-level NVE drift rule:

```text
<= 1 meV / atom / ps   strict energy-drift criterion passes
> 1 and <= 26 meV / atom / ps   degraded quality; analysis continues
> 26 meV / atom / ps   hard failure; trajectory is unqualified by default
```

The 26 meV scale is recorded as one room-temperature `kT` per atom over a 1 ps
reference interval. The policy metadata records the 300 K reference temperature and
1 ps reference time. This is an mdstats quality convention, not a universal VASP
threshold.

Other strict and catastrophic checks remain independent. Passing the drift criterion
alone does not make the trajectory `strictly_qualified`.

## VASP reader behavior

For a complete, unstrided `vasprun.xml` trajectory, `read_vasp_frames(...)` attaches:

```text
production_regime_catalog
production_regime_catalog_signature
```

when `assess_stationarity=True`.

Subselected sources receive:

```text
production_regime_assessment_status =
    not_evaluated_for_subselected_source_segment
```

and must be assessed as their own source segment.

## Acceptance tests

The focused acceptance boundary includes:

1. stable synthetic NVE source -> one scientific full-source regime;
2. heating transient -> detected early regime and retained later stable regime;
3. smooth drift -> no false stationary promotion;
4. short source -> `insufficient`, not catastrophic;
5. declared boundaries are tested rather than trusted;
6. deterministic record round trips and source-signature rejection;
7. public API and reader metadata;
8. real Na-LTA `vasprun.xml` replay;
9. regression of ENS0, ENS1, STAT0, and adjacent Stage 11 modules.

## Non-goals

STAT1 does not:

- authorize a canonical or force-integrated PMF;
- choose site-density bandwidth or grid resolution;
- discover basins or saddles;
- compute thermodynamic populations;
- estimate transition rates;
- prove complete equilibration or ergodicity.
