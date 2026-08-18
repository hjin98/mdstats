---
title: "MLFF-DATA3: Frame Identity, Eligibility, Conditions, and Strain"
author: "mdstats project"
date: "2026-07-28"
geometry: margin=0.78in
toc: true
toc-depth: 2
numbersections: true
fontsize: 10.5pt
header-includes:
  - |-
    \usepackage{booktabs}
  - |-
    \usepackage{longtable}
  - |-
    \usepackage{microtype}
---

# Scope

MLFF-DATA3 converts each DATA2 source into immutable frame occurrences and
separate decision records. It introduces exact geometry and label identities,
post-DFT frame eligibility, temperature conditions, reference-cell resolution,
and finite-strain reconstruction. It does **not** assign train/validation/test
roles, fit feature transforms, select configurations, or generate MACE files.

The implementation MUST consume normalized `AtomisticFrameCollection` geometry
or the existing VASP reader. It MUST preserve ASE's row-vector cell convention,

$$
\mathbf r_{\mathrm{row}}=\mathbf s_{\mathrm{row}}\mathbf H.
$$

ASE represents the three cell vectors as rows of its $3\times3$ cell array [1].

# Public modules

```text
mdstats.training_data.identity
mdstats.training_data.conditions
mdstats.training_data.strain
mdstats.training_data.eligibility
mdstats.training_data.frame_catalog
```

# Frame-array adapter

`FrameData` is the source-independent runtime adapter between a normalized
trajectory and the immutable catalog. It SHALL contain:

```text
source_frame_indices
frame_ids
steps
Times in ps
atomic_numbers
periodic boundary flags
cells in Angstrom
wrapped or unwrapped fractional positions
selected total energies in eV
forces in eV/Angstrom
Cauchy stresses in eV/Angstrom^3
instantaneous temperatures in K
per-frame SCF-limit flags
```

The adapter validates fixed atom order, frame-axis alignment, finite geometry,
and exact source-frame count. `FrameData.from_collection()` uses an explicitly
supplied source-frame index vector when available; otherwise it uses the local
complete-source frame axis. `collection.steps` remains a physical MD-step field,
not an occurrence index.

# Identity contract

## Source occurrence

The DATA2 content-derived source signature is not sufficient by itself because
byte-identical copied files may share it. DATA3 constructs

$$
S_{\mathrm{occ}}
=
\operatorname{SHA256}
(\mathrm{run\_id},\mathrm{source\_locator},S_{\mathrm{content}}),
$$

then defines

$$
\mathrm{frame\_uid}
=
\operatorname{SHA256}(S_{\mathrm{occ}},k),
$$

where $k$ is the source-frame index. A copied source declared as a distinct
manifest run therefore receives a new occurrence identity while retaining the
same source-content signature for provenance and duplicate analysis.

## Geometry fingerprint

The first release detects exact copies and restart overlaps while preserving
atom order and cell basis. The canonical payload contains:

- ordered atomic numbers;
- periodic-boundary flags;
- row-vector cell entries quantized by `cell_tolerance_angstrom`;
- wrapped fractional coordinates quantized by `fractional_tolerance`.

Energy, force, stress, temperature, source path, and label-domain identity SHALL
be excluded. Fractional values within the declared wrap tolerance of one are
canonicalized to zero.

This first fingerprint is not permutation-, symmetry-, or integer-basis
invariant. Those comparisons require a later approximate duplicate layer.

## Label payload digest

The label payload digest contains:

- target label-domain identity;
- selected energy-channel identity;
- total energy, when present;
- force array, when present;
- stress tensor, when present;
- units and derivative conventions.

Each numerical field is quantized with an explicit policy tolerance. Missing
labels are represented explicitly rather than silently omitted.

## Labeled configuration

```text
labeled_configuration_fingerprint =
    SHA256(geometry_fingerprint, label_payload_digest)
```

The three identities SHALL remain separate fields.

# Duplicate and restart detection

`DuplicateDetectionCatalog` groups exact geometry fingerprints and exact labeled
configuration fingerprints. It SHALL classify whether a group:

- is within one source;
- crosses multiple sources;
- includes a restart-boundary pattern, where a first frame of one source matches
  a final frame of another source.

Duplicate membership does not by itself make a frame ineligible. Later
partitioning and leakage audits decide whether duplicates may occupy different
statistical roles.

# Temperature-condition contract

A source-level `TemperatureConditionRecord` SHALL preserve:

```text
run identity
ensemble identity
TEBEG and TEEND when available
resolved schedule kind
instantaneous-temperature count
mean, standard deviation, minimum, and maximum
source of target-temperature evidence
```

Schedule kinds are:

```text
constant
ramp
not_applicable
unresolved
```

Instantaneous temperatures are source observations, not substitutes for the
requested thermostat schedule. NVE may have no target temperature while still
carrying instantaneous temperatures.

# Eligibility contract

Eligibility is a separate decision keyed by `frame_uid`.

Default hard requirements are:

- finite, nonsingular positive-volume cell;
- finite fractional positions;
- exact atom-count agreement with the source composition and a fixed valid atomic-number vector for the complete frame collection;
- complete selected energy;
- complete finite force field;
- symmetric finite stress when stress is present;
- no per-frame SCF iteration-limit flag when the strict policy is active;
- no source-level `unqualified` outcome when the strict policy is active.

Stress is optional by default because later heterogeneous-label policies may set
its training weight to zero. An absent optional stress produces a warning, not a
false stress tensor.

Eligibility outcomes are:

```text
eligible
ineligible
unresolved
```

Every decision SHALL contain machine-readable reason codes. High but finite
forces, unusual strain, transients, or duplicated geometry SHALL NOT be rejected
at DATA3.

# Reference-cell resolution

`ReferenceCellCatalog` resolves one cell for each source under the following
precedence:

1. explicit cell supplied for a reference group;
2. explicit `reference_run_id` from the manifest;
3. a unique manifest-asserted unstrained/reference run;
4. multiple compatible unstrained candidates with equivalent constant cells;
5. unresolved.

A reference run with appreciable cell variation SHALL fail closed unless the
policy explicitly allows a selected frame. The default selected reference frame
is source frame zero. Compatibility is tested in the declared row-vector cell
representation.

Reference records and per-run resolution records are separate. A single
reference record may serve multiple strained runs.

# Strain reconstruction

For reference cell $\mathbf H_0$ and current row-vector cell $\mathbf H_t$, the
Cartesian column-vector deformation gradient is

$$
\mathbf F=\left(\mathbf H_0^{-1}\mathbf H_t\right)^T.
$$

The proper polar decomposition is

$$
\mathbf F=\mathbf R\mathbf U,
$$

where $\mathbf R$ is a proper rotation and $\mathbf U$ is symmetric positive
definite. DATA3 computes it by singular-value decomposition, a standard stable
construction for the polar factors [2]. Reflections, singular cells, or
nonpositive stretch singular values are rejected.

The record contains:

$$
\boldsymbol\varepsilon_{\mathrm{lin}}=\tfrac12(\mathbf F+\mathbf F^T)-\mathbf I,
$$

$$
\mathbf E=\tfrac12(\mathbf F^T\mathbf F-\mathbf I),
$$

and logarithmic strain

$$
\mathbf L=\log\mathbf U.
$$

It also stores:

- volume ratio $J=\det\mathbf F$;
- rotation angle;
- principal logarithmic strains;
- hydrostatic logarithmic strain $\operatorname{tr}(\mathbf L)/3$;
- deviatoric norm;
- engineering shear components $2L_{xy}$, $2L_{yz}$, and $2L_{zx}$.

The rotation-separated tensor class is one of:

```text
unstrained
hydrostatic
orthorhombic_or_deviatoric
shear
mixed
unresolved
```

For variable-cell NpT/NpH sources without an intentional strain assertion, the
source context is separately marked `variable_cell_fluctuation`; the actual
tensor class remains available.

Manifest strain assertions are verification targets. DATA3 records
`verified`, `mismatch`, `not_provided`, or `unresolved`; assertions never replace
the calculated tensor.

# Catalog contract

`TrainingFrameCatalog` SHALL contain:

```text
source-catalog digest
identity-policy digests
eligibility-policy digest
reference-cell catalog
temperature-condition records
immutable TrainingFrameRecord objects
FrameEligibilityDecision objects
FrameStrainRecord objects
DuplicateDetectionCatalog
notes and content digest
```

`TrainingFrameRecord` SHALL contain source facts and identity references only.
It SHALL NOT contain partition, selection, exposure, or acquisition state.

# VASP integration

`build_vasp_training_frame_catalog()` SHALL:

1. resolve each DATA2 source locator relative to an explicit base directory;
2. re-read source controls and verify the source/control signatures;
3. extract the exact selected named energy channel from `FrameEnergyCatalog`;
4. read normalized frames through `read_vasp_frames()` without rerunning source-level quality, stationarity, or admissibility analyses;
5. carry per-frame SCF-limit flags from the control bundle;
6. infer TEBEG/TEEND from effective controls;
7. build the same source-independent catalog as `build_training_frame_catalog()`.

The exact selected VASP energy remains the finite-smearing `e_fr_energy` channel
by default; `vasprun.xml` documents it as the electronic free energy $F=E-TS$
[3].

# Determinism

All policies and records SHALL serialize to canonical JSON-compatible mappings
and verify their content or policy digest on replay. Numerical fingerprints
SHALL use float64 inputs, explicit tolerances, round-to-nearest integer
quantization, and stable sorted ordering of groups.

# Failure behavior

The implementation SHALL fail explicitly for:

- mismatched source and collection frame counts;
- changed atom order or composition;
- missing selected energy arrays when required;
- source-signature mismatch during VASP re-read;
- singular or reflected deformation;
- ambiguous reference-cell resolution;
- unsupported serialized schema;
- modified record or policy digests.

Ambiguous reference cells do not prevent frame identity or eligibility records;
they produce unresolved strain records.

# Focused test gate

DATA3 is accepted when focused tests cover:

- occurrence UID stability and source sensitivity;
- periodic-wrap-invariant geometry fingerprints;
- label-independent geometry identity;
- energy/force/stress-sensitive label digests;
- exact copy, cross-source duplicate, and restart-overlap groups;
- eligibility reason codes and optional stress;
- constant, ramp, NVE, and unresolved temperature conditions;
- explicit, reference-run, compatible-consensus, and unresolved reference cells;
- hydrostatic strain;
- constant-volume orthorhombic strain;
- non-symmetric engineering shear under the ASE row-vector convention;
- pure rotation separated from strain;
- assertion verification and mismatch;
- complete serialization/tamper rejection;
- DATA1 and DATA2 regression boundaries.

# References

1. Atomic Simulation Environment, "The Cell object," ASE documentation. The
   cell array stores cell vectors as rows and scaled positions are expressed in
   that basis.
2. N. J. Higham, "Computing the Polar Decomposition-with Applications," *SIAM
   Journal on Scientific and Statistical Computing* **7**, 1160-1174 (1986),
   DOI: 10.1137/0907079.
3. VASP Wiki, "vasprun.xml," documenting `e_fr_energy` as free energy
   $F=E-TS$ and the per-step force and stress arrays.
