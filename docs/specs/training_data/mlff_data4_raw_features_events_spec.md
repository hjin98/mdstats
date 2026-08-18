# MLFF-DATA4: Raw Features, Optional Profile States, Events, Cache, and Role Budget

**Status:** implemented in mdstats 0.20.32a0; schema-v2 profile binding added in 0.20.47a0  
**Target release:** mdstats 0.20.47a0  
**Namespace:** `mdstats.training_data`

## 1. Purpose

MLFF-DATA4 converts eligible DATA3 frame occurrences into partition-independent,
full-resolution physical evidence. The stage exists before train/validation/test
assignment. It therefore computes only quantities that may be inspected without
learning a transform from the complete dataset and without using model residuals
from protected evaluation labels.

DATA4 currently provides six products:

1. `MaterialProfileContracts` (optional only for pre-DATA9A7 compatibility):
   user-declared phase, geometry, atom-group, condition-axis, and independence-axis identity;
2. `RawFeatureCatalog`: thermodynamic, force, stress, cell, strain, and selected
   pair-geometry summaries for every frame occurrence;
3. `LtaPartitionFeatureCatalog`: optional historical LTA framework/mobile-ion states
   needed to protect rare site and transition categories during DATA5 partitioning;
4. `FullResolutionEventCatalog`: deterministic event anchors and compact
   before/event/after preservation windows detected before temporal thinning;
5. `PartitionRoleBudgetPolicy`: the requested statistical roles and minimum
   independent-unit support that DATA5 must test for feasibility;
6. `Data4FeatureBundle` and `FeatureCacheManifest`: immutable, source-bound
   serialization and replay contracts.

DATA4 does **not** assign statistical roles, fit scalers or PCA, compute MACE
residuals, select training frames, or export MACE files.

## 2. Scientific rationale

An MD trajectory sampled every femtosecond is highly redundant, but short-lived
physical events can occur between any two candidate-stride frames. Event
classification must therefore precede ordinary thinning. Correlation-aware
blocking and protected evaluation roles begin only after the event catalog is
complete. The general need to treat correlated MD data differently from
independent samples is discussed by Flyvbjerg and Petersen [1] and in structured
cross-validation work [2,3].

The raw features are deliberately low-dimensional and interpretable. They are
not intended to replace learned MACE descriptors. Their purpose is to expose the
physical range of the source data, detect state changes, define partition strata,
and provide auditable coverage diagnostics. Rich learned descriptors and
training-domain-only foundation-model residuals remain DATA6 capabilities.

ASE 3.29.0 is the reference geometry/runtime dependency for this implementation. The supplied source archive was verified as `sha256:ef4e2caa38169e3fbbc4164764a060d1877a6692519a4bed82521328eeb0d9aa`.
Cells follow ASE's row-vector convention, consistent with DATA3 strain records.
ASE's design and units are described by Larsen et al. [4].

## 3. Ownership and stage boundary

DATA4 consumes:

- `TrainingDataSourceCatalog` from DATA2;
- `TrainingFrameCatalog` and `FrameData` from DATA3;
- DATA3 eligibility, strain, temperature, and source-occurrence identities.

DATA4 owns:

- binding the declarative `MaterialProfileContracts` identity to the feature bundle;
- raw feature policies and records;
- pair-distance and coordination summary rules;
- lightweight LTA partition-profile definitions and state records;
- event detection and event-window preservation;
- the requested partition-role budget;
- deterministic cache manifests.

DATA5 owns feasibility, blocking, statistical-role assignment, independence
evidence, blinding, and leakage audit.

## 4. Public data contracts

### 4.1 `PairFeatureRule`

A directed pair rule identifies center and neighbor atomic numbers:

```text
rule_id
center_atomic_number
neighbor_atomic_number
coordination_cutoff_angstrom | null
```

The direction matters for coordination. `Na-O` means oxygen neighbors around
Na centers. For equal species, self-pairs are excluded.

### 4.2 `RawFeaturePolicy`

The policy records:

```text
pair_rules
force_quantiles
minimum_volume
minimum_distance_tolerance
stress_convention
mass_table_identity
policy_version
```

The generic default has no pair rules. `RawFeaturePolicy.lta_default()` adds
coarse Si-O, Al-O, Li-O, Na-O, and K-O rules. The default cutoffs are broad,
mdstats-local partitioning cutoffs rather than claims of experimental bond
lengths. Every cutoff is serialized and user-overridable.

### 4.3 `RawFrameFeatureRecord`

Each record is keyed by `frame_uid` and contains:

```text
energy_total_ev
energy_per_atom_ev
instantaneous_temperature_kelvin
cell_volume_angstrom3
mass_density_g_cm3
cell_lengths_angstrom
cell_angles_degrees
force_component_rms_ev_per_angstrom
force_norm_mean_ev_per_angstrom
force_norm_max_ev_per_angstrom
force_norm_quantiles_ev_per_angstrom
pressure_ev_per_angstrom3
stress_deviatoric_norm_ev_per_angstrom3
stress_von_mises_ev_per_angstrom3
hydrostatic_strain
deviatoric_strain_norm
engineering_shear
species_force_statistics
pair_geometry_statistics
warning_codes
```

ASE stress is treated as positive in tension. The reported pressure is

$$
P=-\frac{1}{3}\operatorname{tr}\boldsymbol{\sigma},
$$

so positive pressure denotes compression. The von Mises-like invariant is

$$
\sigma_{\mathrm{vm}}
=\sqrt{\frac{3}{2}\,\mathbf{s}:\mathbf{s}},
\qquad
\mathbf{s}=\boldsymbol{\sigma}
-\frac{\operatorname{tr}\boldsymbol{\sigma}}{3}\mathbf{I}.
$$

No nonfinite label is converted into a finite feature. Missing or invalid
optional quantities are represented as `null` with warning codes.

### 4.4 Pair geometry

For each directed pair rule and frame, DATA4 computes minimum-image distances
using fractional displacements and the frame cell:

$$
\Delta\mathbf{s}_{ij}
\leftarrow
\Delta\mathbf{s}_{ij}
-\operatorname{nint}(\Delta\mathbf{s}_{ij})
$$

on periodic axes, followed by

$$
\Delta\mathbf{r}_{ij}=\Delta\mathbf{s}_{ij}\mathbf{H}.
$$

The record reports:

```text
minimum_pair_distance
mean_nearest_neighbor_distance
maximum_nearest_neighbor_distance
coordination_mean | null
coordination_maximum | null
center_count
neighbor_count
```

Coordination is computed only when the rule supplies a cutoff.

### 4.5 `LtaRingDefinition`

The lightweight profile accepts explicit ring definitions:

```text
ring_id
ring_size in {4, 6, 8}
framework_atom_indices
```

DATA4 does not rediscover the LTA topology. Ring definitions may be supplied by
existing mdstats natural-tiling/ring catalogs or by a signed user manifest.
Invalid or absent definitions yield unresolved LTA states rather than guessed
sites.

### 4.6 `LtaPartitionProfilePolicy`

The policy records:

```text
framework atomic numbers: Al, Si, O
mobile atomic numbers: Li, Na, K
framework T-O cutoffs
mobile-O cutoffs
maximum ring-center assignment radius by ring size
on-center radial threshold by ring size
ring-crossing plane tolerance
framework coordination requirements
policy version
```

The policy is intentionally coarse. It protects partition categories; it does
not claim an energetic adsorption-site model. Rich site landscapes remain a
DATA6 selection-grade feature.

### 4.7 Ring geometry and site states

Ring atoms are unwrapped relative to the first ring atom under the minimum-image
convention. The center is their Cartesian mean. The ring plane normal is the
right singular vector associated with the smallest singular value of centered
coordinates. The normal sign is made deterministic by requiring the component
with largest magnitude to be positive.

For mobile ion position $\mathbf{x}$, ring center $\mathbf{c}$, and normal
$\mathbf{n}$:

$$
z=(\mathbf{x}-\mathbf{c})\cdot\mathbf{n},
\qquad
\rho=\left\|(\mathbf{x}-\mathbf{c})-z\mathbf{n}\right\|.
$$

The nearest admissible ring defines a coarse site class:

```text
ring_4_on_center / ring_4_off_center
ring_6_on_center / ring_6_off_center
ring_8_on_center / ring_8_off_center
unassigned
unresolved
```

### 4.8 `LtaMobileSiteState`

For every mobile atom and frame:

```text
frame_uid
atom_index
atomic_number
ring_id | null
ring_size | null
site_class
ring_center_distance_angstrom | null
signed_plane_distance_angstrom | null
radial_distance_angstrom | null
oxygen_coordination | null
coordination_changed
site_changed
ring_crossing
```

A site change occurs when two consecutive source frames assign different
resolved ring IDs. A coordination change occurs when the integer M-O count
changes. A ring crossing requires the same ring assignment, opposite signed
plane distances, and at least one endpoint within the policy plane tolerance.
No interpolation-based transition time is inferred.

### 4.9 `LtaFramePartitionRecord`

The frame-level partition record summarizes:

```text
profile_status
framework_integrity: true / false / unresolved
site_classes_present
ring_sizes_present
coordination_change
site_change
ring_crossing
mobile_state_count
warning_codes
```

Framework integrity is resolved only when required framework species are
present. The default coarse rule requires each Si/Al center to have four O
neighbors within its configured cutoff and each O to have two framework-T
neighbors. This is a screening state, not a bond-order definition.

### 4.10 Event contracts

`EventDetectionPolicy` records:

```text
pre_frames
post_frames
merge_gap_frames
force_norm_max_threshold | null
absolute_pressure_threshold | null
temperature_deviation_threshold | null
include_lta_state_changes
include_framework_integrity_changes
```

`FullResolutionEventCatalog` contains deterministic event bursts. Supported
partition-critical event types are:

```text
coordination_change
site_change
ring_crossing
framework_integrity_loss
framework_integrity_recovery
force_threshold
pressure_threshold
temperature_deviation
```

Adjacent anchors of the same run and type within `merge_gap_frames` form one
burst. The representative anchor is the most severe frame when a scalar
severity exists, otherwise the earliest stable frame UID/order. The protected
window is the union of `pre_frames`, burst frames, and `post_frames`, clipped to
the source trajectory. Events are detected from every eligible frame before any
ordinary candidate stride is applied.

### 4.11 `PartitionRoleBudgetPolicy`

DATA4 records requests, not feasibility conclusions:

```text
development minimum independent units
outer monitor minimum independent units
calibration minimum independent units
locked interpolation-test minimum independent units
cross-validation fold count
checkpoint-monitor minimum units per fold
purge units between roles
allow calibration deferral
allow external challenge tests
required condition axes
```

DATA5 compares this request with available autocorrelation-aware blocks and
returns a `PartitionFeasibilityReport`.

### 4.12 `Data4FeatureBundle`

The bundle binds:

```text
source catalog digest
frame catalog digest
material-profile contracts | null for legacy evidence
raw feature catalog
LTA partition feature catalog | null
event catalog
partition-role budget policy
notes
```

No field stores partition assignments, selected training frames, fitted
statistics, or MACE predictions.

## 5. Event detection before thinning

Event detection uses the full eligible frame stream. Ordinary stride selection is forbidden until protected event windows have been recorded.

## 6. Deterministic builder algorithm

For each label-domain source occurrence:

1. verify source/frame catalog and `FrameData` run coverage;
2. process frames in source-frame order;
3. compute raw scalar and pair features for every frame;
4. if the LTA profile is enabled, compute ring geometry and mobile site states
   at full resolution;
5. compare only adjacent source-frame states within the same run to set state-
   change flags;
6. construct frame-level LTA summaries;
7. detect and merge full-resolution event bursts;
8. create the role-budget request;
9. bind the declared material-profile contracts when supplied;
10. serialize the immutable bundle and optional cache files.

Ineligible frames remain identifiable in the raw catalog but receive warning
codes and are excluded from physical event anchoring by default. This preserves
source accounting without allowing corrupt labels to create protected events.

## 7. Cache contract

DATA4 schema v2 writes `material_profile_contracts.json` when the aggregate is
present. The bundle reader retains exact digest-compatible support for schema-v1
bundles and caches. Supplying a generic material profile does not activate LTA;
LTA states still require an explicit `LtaPartitionProfilePolicy` until DATA9A7d.


`write_data4_feature_cache()` writes:

```text
cache_manifest.json
material_profile_contracts.json    # when supplied
raw_features.json
profile_partition_features.json    # when optional extensions are enabled
events.json
partition_role_budget.json
data4_feature_bundle.json
```

The cache manifest stores file SHA-256 hashes and the content digest of every
record. `read_data4_feature_cache()` verifies path containment, file hashes,
record digests, cross-file digests, and bundle identity before returning data.
The first implementation uses canonical JSON because DATA4 features are low-
dimensional. High-dimensional MACE descriptors use array sidecars in DATA6.

## 8. VASP/ASE integration

`build_vasp_data4_feature_bundle()` reads the sources bound by the DATA2 catalog
with the provided ASE-compatible mdstats VASP parser, reconstructs `FrameData`,
builds or verifies the DATA3 frame catalog, and then executes DATA4. Source and
control signatures must match the catalog. The ASE source-distribution checksum
used by the focused tests is recorded in the release audit.

## 9. Resource behavior

The implementation processes one run at a time and one frame at a time. Pair
rules are explicit to avoid unconditional all-pairs feature growth. The first
implementation uses vectorized minimum-image distance blocks. It must not retain
an $N_\mathrm{frames}\times N_\mathrm{atoms}^2$ tensor.

The cache is deterministic but not a streaming random-access store. A later
performance stage may add chunked binary sidecars without changing the public
record semantics.

## 10. Failure semantics

Hard failures include:

- source/frame catalog mismatch;
- missing `FrameData` for a source;
- duplicate or unknown run IDs;
- frame UID/order mismatch;
- invalid pair or LTA policies;
- out-of-range ring atom indices;
- non-positive cell determinant;
- cache path escape, hash mismatch, or record tampering.

Degraded/unresolved outputs include:

- absent optional stress or temperature;
- pair species absent in one composition;
- no LTA ring definitions;
- rank-deficient ring plane;
- absent required framework species;
- unassigned mobile ions;
- role requests that DATA5 may later find infeasible.

## 11. Focused acceptance tests

The stage gate requires:

1. real ASE 3.29.0 import from the supplied source archive;
2. real ASE-backed VASP parsing through `build_vasp_training_frame_catalog()`;
3. deterministic raw feature values and round-trip serialization;
4. pressure-sign and stress-invariant tests;
5. triclinic minimum-image pair-distance tests;
6. species-resolved force statistics;
7. 4R/6R/8R on/off-center assignment fixtures;
8. coordination-change, site-change, and ring-crossing detection;
9. event-before-thinning preservation-window behavior;
10. framework-integrity loss/recovery events;
11. deterministic event merging;
12. cache write/read and tamper rejection;
13. role-budget policy round trip;
14. VASP DATA3/DATA4 integrated smoke test;
15. DATA0-DATA3 regression tests;
16. wheel build and installed-wheel import.

## 12. Non-goals

DATA4 does not implement:

- automatic natural-tiling discovery;
- detailed LTA energetic site models;
- MACE descriptors or foundation residuals;
- temporal autocorrelation partition assignment;
- fitted feature metrics;
- farthest-point selection;
- MACE export or training.

## References

[1] H. Flyvbjerg and H. G. Petersen, "Error Estimates on Averages of
Correlated Data," *Journal of Chemical Physics* **91**, 461-466 (1989).
DOI: 10.1063/1.457480.

[2] J. Racine, "Consistent Cross-Validatory Model-Selection for Dependent
Data: hv-Block Cross-Validation," *Journal of Econometrics* **99**, 39-61
(2000). DOI: 10.1016/S0304-4076(00)00030-0.

[3] D. R. Roberts, V. Bahn, S. Ciuti, et al., "Cross-Validation Strategies for
Data with Temporal, Spatial, Hierarchical, or Phylogenetic Structure,"
*Ecography* **40**, 913-929 (2017). DOI: 10.1111/ecog.02881.

[4] A. H. Larsen, J. J. Mortensen, J. Blomqvist, et al., "The Atomic Simulation
Environment - A Python Library for Working with Atoms," *Journal of Physics:
Condensed Matter* **29**, 273002 (2017). DOI: 10.1088/1361-648X/aa680e.

[5] M. Kulichenko, B. Nebgen, N. Lubbers, J. S. Smith, et al., "Data
Generation for Machine Learning Interatomic Potentials and Beyond,"
*Chemical Reviews* **124**, 13681-13714 (2024). DOI:
10.1021/acs.chemrev.4c00572.

# DATA9A7d amendment: optional partition-profile extensions

Beginning with `0.20.50a0`, canonical DATA4 schema v3 stores optional
material-specific partition evidence as `profile_partition_features`. Each
entry is a `ProfileFeatureCatalog` that binds extension identity, provider
identity, frame lineage, provider-owned payload schema, and content digest.

The old `lta_partition_features` top-level field is not emitted by new DATA4
records. It remains a Python compatibility view and a v1/v2 deserialization
input. LTA construction requires an explicit material profile containing the
`porous_network`, `zeolite`, and `lta` extension chain. Generic profiles cannot
carry LTA evidence.

Event catalogs bind the generic profile-feature catalog digests. The historical
LTA digest remains only as nested compatibility evidence required to restore
v1 event records exactly.
