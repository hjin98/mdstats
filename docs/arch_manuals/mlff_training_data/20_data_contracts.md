# Part II - Data and evidence contracts

## Evidence records and immutability

### Source facts

`TrainingDataSource` records facts derived from one source occurrence:

```text
run_id
source_path
source_sha256
source_identity_signature
composition
timestep
frame_count
ensemble_certificate
quality_signature
production_regime_signature
label_domain_id
reference_group
```

### Frame facts

`TrainingFrameRecord` contains only source-derived, policy-independent facts:

```text
frame_uid
source_identity_signature
source_occurrence_signature
source_frame_index
time
atomic numbers
cell reference
label references
condition references
geometry_fingerprint
label_payload_digest
labeled_configuration_fingerprint
```

It does **not** contain eligibility, partition, selection, exposure, or
acquisition state. The three fingerprints have different purposes and remain
separate fields.

### Decision records

Separate records are keyed by `frame_uid` or by an explicit dataset/job identity:

```text
FrameEligibilityDecision
PartitionAssignment
SelectionAssignment
ExposureAssignment
CandidateAdmissibilityDecision
AcquisitionDecision
```

A new policy produces new decision records without mutating frame facts.

### Workflow-policy and fitted records

The architecture also separates static policy templates from data-fitted or
runtime-realized products:

```text
PartitionRoleBudgetPolicy
PartitionFeasibilityReport
FeatureMetricPolicyTemplate
FoldFeatureMetricFit
FinalFeatureMetricFit
SelectionBudgetPolicy
TrainingObjectivePolicy
ConfigurationWeightPolicy
PropertyWeightPolicy
CheckpointMetricPolicy
TrainingProtocolIdentity
MaceCheckpointControlPolicy
ExposureBackendPolicy
MaceExposureRealizationRecord
ReplayRetentionPolicy
ProtocolFreezeRecord
CalibrationApplicabilityDomain
CalibrationTransferDecision
```

A policy template specifies an algorithm and fixed choices. A fitted record
contains parameters learned from one declared training domain. A realization
record contains behavior actually observed from an external tool. These roles
are not interchangeable.

### Content digests, not digital signatures

Previous documents used the word "signed" for deterministic record hashes. This
manual uses precise terms:

- `content_digest`: canonical hash of one record;
- `policy_digest`: canonical hash of a policy;
- `source_digest`: hash of source bytes;
- `cryptographic_signature`: optional authenticated signature, not required in
  the first release.

A content digest detects modification but does not authenticate the author.

## Source and manifest contract

### Dataset manifest

A YAML or JSON manifest supplies source paths and information that cannot be
reliably reconstructed from a single `vasprun.xml`:

```yaml
dataset_id: bulk-lta-initial
system_profile: lta

runs:
  - run_id: Li_300K
    vasprun: raw/Li_300K/vasprun.xml
    reference_group: Li_bulk
    replica_id: seed001

  - run_id: LiNaK_hydro_plus_005
    vasprun: raw/LiNaK_hydro_plus_005/vasprun.xml
    reference_group: LiNaK_bulk
    reference_run_id: LiNaK_700K
    assertions:
      intended_strain_class: hydrostatic
      intended_volume_change: 0.05
```

Manifest values are either:

- source locators;
- grouping declarations;
- scientific assertions to verify;
- explicit expert overrides with rationale.

A directory name is never treated as a physical label without verification.

### Occurrence, geometry, and label identities

#### Source-occurrence identity

The DATA2 `source_identity_signature` is content-derived and may therefore be
shared by byte-identical copied sources. DATA3 first binds that identity to one
manifest occurrence:

$$
\mathrm{source\_occurrence\_signature}
=
\operatorname{SHA256}
(
\mathrm{run\_id},
\mathrm{source\_locator},
\mathrm{source\_identity\_signature}
).
$$

The frame occurrence is then

$$
\mathrm{frame\_uid}
=
\operatorname{SHA256}
(
\mathrm{source\_occurrence\_signature},
\mathrm{source\_frame\_index}
).
$$

This identity is stable under later concatenation and export, while two copied
sources declared as distinct manifest runs intentionally receive different
occurrence identities.

#### Source-independent geometry fingerprint

`geometry_fingerprint` identifies the atomic geometry independently of labels.
The first implementation supports exact copy/restart overlap detection using:

- ordered atomic numbers;
- canonical wrapped fractional coordinates;
- canonical cell representation;
- explicit numerical tolerances.

Energy and forces are deliberately excluded. The same geometry evaluated at a
different DFT level or convergence threshold must still be detectable as the
same geometry.

#### Label payload digest

`label_payload_digest` hashes the selected energy, forces, stress or virial,
label-domain identity, and their declared numerical representation. It detects
whether two occurrences carry the same labeled payload.

#### Labeled-configuration fingerprint

`labeled_configuration_fingerprint` combines the geometry fingerprint and label
payload digest. It answers the narrower question: "is this the same geometry
with the same labels?"

Leakage audits use all of the following:

- exact `frame_uid` overlap;
- exact geometry-fingerprint overlap;
- exact labeled-configuration overlap;
- near-geometry or descriptor distance;
- forbidden temporal proximity.

Later revisions may add permutation-, basis-, and symmetry-aware approximate
geometry matching without changing these identity roles.

## Electronic-structure label domains

### Why the fingerprint is decomposed

Electronic-structure settings do not all have the same meaning. The architecture separates five records.

#### `TheoryIdentity`

Examples:

- exchange-correlation functional;
- DFT+U form and parameters;
- pseudopotential or PAW datasets;
- spin formalism;
- dispersion or hybrid-functional settings.

#### `EnergyReferenceIdentity`

Examples:

- energy channel;
- smearing/free-energy convention;
- atomic reference convention;
- per-cell versus per-atom normalization.

#### `DerivativeConvention`

Examples:

- force sign and units;
- stress versus virial;
- stress sign;
- tensor/Voigt representation;
- shear convention.

#### `NumericalQualityProfile`

Examples:

- ENCUT;
- k-point density;
- EDIFF;
- PREC;
- LREAL;
- LASPH;
- SCF iteration behavior.

#### `SoftwareProvenance`

Examples:

- VASP version;
- parser version;
- POTCAR hashes;
- source-control reconstruction version.

A versioned `LabelCompatibilityPolicy` determines whether differences are:

```text
compatible
compatible_with_quality_flag
separate_label_domain
unresolved
```

Exact equality of the complete fingerprint is not required, but theory- or
reference-defining differences cannot be waived silently.

### First-release MACE rule

One MACE bundle contains exactly one target `LabelDomain` and optionally one
foundation replay head. If the dataset contains two incompatible target DFT
levels, mdstats produces two target bundles.

General arbitrary multi-target-head export is deferred until a later MACE
adapter revision. This restriction makes the initial data contract unambiguous
while preserving a path to MACE's general multi-head capability [11, 12].

### Energy-channel policy

VASP forces and stress are derivatives of the electronic free-energy surface at
the chosen electronic smearing. The selected `REF_energy` must therefore be an
explicit named channel consistent with the derivative labels [7].

Example:

```python
VaspEnergyLabelPolicy(
    channel="e_fr_energy",
    require_complete=True,
    derivative_consistency="electronic_free_energy",
)
```

The exact channel, units, completeness, and provenance are exported.

## Atomic reference-energy audit and fitting

MACE commonly writes the total energy as

$$
E = \sum_i E_{0,Z_i} + E_{\mathrm{interaction}}.
$$

When foundation-model corrections are estimated, one solves a system of the
form

$$
\mathbf A\,\Delta\mathbf e_0 \approx \mathbf b,
$$

where $A_{cZ}$ is the count of element $Z$ in configuration $c$, and $b_c$ is
the target-minus-foundation energy residual. Current MACE uses a least-squares
solution, reports matrix rank, and warns when the element-count system is rank
deficient [10].

The architecture separates two operations that have different leakage rules.

### Structural identifiability audit

`AtomicReferenceIdentifiabilityReport` depends only on elemental count vectors
and an atomic-reference policy. It may be created before partitioning and
contains:

```text
element order
count matrix shape
rank
singular values
condition number
null-space dimension
identifiable linear combinations
policy outcome
transfer limitations
```

It does **not** contain fitted elemental corrections or a fit residual.

Allowed structural outcomes are:

```text
identified
rank_deficient_but_fixed_domain_usable
user_supplied
isolated_atom_anchored
foundation_preserved
rejected
```

For fixed-stoichiometry LTA, individual Si, Al, and O corrections are not all
identifiable. A rank-deficient system may still be accepted for the same fixed
stoichiometric manifold, but its null space and transfer restrictions must be
explicit.

### Training-domain atomic-reference fit

`AtomicReferenceFitRecord` is a fitted object. It contains:

```text
training-domain frame UIDs
element support by element
structural-identifiability report digest
foundation-checkpoint digest
fitted elemental corrections
least-squares residual
solver and numerical tolerance
policy outcome
```

It may inspect only the applicable target-training domain:

- each cross-validation job has a separate fold-local fit;
- the final production run has a separate final-training fit;
- outer monitor, calibration, held-out fold, and locked-test labels are excluded.

Before fitting, every required element must have sufficient support in that
training domain. Missing-element or newly rank-deficient fold fits fail or use
an explicitly declared alternative such as user-supplied or foundation-preserved
references.

`E0s: estimated` is emitted only when the corresponding training-domain fit is
accepted. The bundle must state that rank-deficient offsets are not transferable
to a different Si/Al ratio, defect count, cation count, salt phase, or interface.

## Ensemble, temperature, and strain

### Ensemble

The branch consumes the existing mdstats control certificate. It distinguishes
at least:

```text
NVE
NVT
NpT
NpH
temperature ramp
constant-velocity path
driven nonequilibrium
multi-thermostat
unresolved
```

Ensemble is not inferred merely from observed cell variation.

### Temperature

A `TemperatureCondition` stores:

- requested `TEBEG` and `TEEND`;
- thermostat target;
- instantaneous ionic temperature series;
- production-regime mean and uncertainty;
- drift and stationarity diagnostics;
- ramp status.

Nominal and realized temperature remain separate.

### Reference-cell resolution

Strain requires an explicit reference. The resolution order is:

1. explicit cell matrix;
2. explicit reference structure;
3. explicit reference run;
4. a unique compatible unstrained run in the same reference group;
5. unresolved.

Ambiguity fails closed.

### Strain tensor

The cell-matrix convention is normative. ASE stores the three lattice vectors
as **rows** of `Cell.array`. Fractional row vectors map to Cartesian row vectors
as

$$
\mathbf r_{\mathrm{row}} = \mathbf s_{\mathrm{row}}\mathbf H.
$$

For reference cell $\mathbf H_0$ and current cell $\mathbf H_t$, the deformation
gradient acting on Cartesian **column** vectors is

$$
\mathbf F_t = \left(\mathbf H_0^{-1}\mathbf H_t\right)^T.
$$

Equivalently, a row-vector implementation may use the right-acting map
$\mathbf H_0^{-1}\mathbf H_t$ provided that all reported tensors are converted
to the declared Cartesian-column convention before serialization. Use the right
polar decomposition

$$
\mathbf F_t = \mathbf R_t\mathbf U_t
$$

to separate rotation from stretch. Record:

- volume ratio;
- linearized strain;
- Green-Lagrange strain;
- logarithmic strain;
- hydrostatic component;
- deviatoric norm;
- principal strains;
- tensor shear;
- engineering-shear equivalent;
- rotation;
- storage convention and coordinate frame.

Classifications are:

```text
unstrained
hydrostatic
orthorhombic_or_deviatoric
shear
mixed_strain
variable_cell_fluctuation
unresolved
```

The fixture suite must include a nonsymmetric shear and a rotated stretch.
Hydrostatic and diagonal fixtures alone cannot detect a transpose or left/right
multiplication error.

### Hierarchical condition schemas

The current LTA data do not occupy a full composition-temperature-strain
Cartesian product. The LTA profile therefore defines:

```text
unstrained family:
    composition x temperature x regime

strained family:
    composition x reference-condition x strain-mode x sign x regime
```

Only observed and scientifically applicable strata are required. Empty
combinations are not treated as missing data.

## Stress and virial contract

The MACE export specification is normative about stress.

Canonical `REF_stress` is:

- Cauchy stress in eV/Angstrom^3;
- a symmetric 3 x 3 tensor in Cartesian coordinates;
- ASE sign convention as verified against the chosen MACE release;
- no engineering factor applied to off-diagonal tensor components.

If six-component storage is used in an intermediate artifact, its order is
explicitly recorded and round-tripped through ASE. Virial labels are stored
under a different key and never silently relabeled as stress.

Every source domain must pass:

1. unit conversion test;
2. sign test against a finite strain energy derivative;
3. 3 x 3 to Voigt round trip;
4. shear-component test;
5. MACE read-back test.

Frames without valid stress may still train on energy and forces by using a
zero stress weight, but only under an explicit heterogeneous-label policy [8].

## Eligibility and quality screening

### Run-level state

```text
strictly_qualified
degraded_quality
unqualified
unresolved
```

The branch reuses the existing mdstats trajectory-quality evidence and records
all overrides.

### Labeled-frame eligibility

`FrameEligibilityDecision` applies after DFT labels exist.

Hard rejection includes:

- missing selected energy;
- missing or nonfinite forces;
- nonfinite positions or cell;
- singular cell;
- corrupt atom identity or ordering;
- truncated ionic step;
- catastrophic overlap;
- disallowed SCF nonconvergence.

Soft flags include:

- transient regime;
- high but physical force;
- unusual pressure or stress;
- rare coordination;
- cation transition;
- topology change;
- high foundation-model residual;
- degraded numerical quality.

A percentile tail alone is never a rejection reason.

### Candidate admissibility before DFT

An active-learning candidate has no DFT labels. It receives a separate
`CandidateAdmissibilityDecision` based on:

- finite cell and coordinates;
- minimum-distance safety;
- chemically allowed elements and counts;
- topology or framework sanity;
- integrator and trajectory integrity;
- model committee outputs;
- descriptor availability.

After DFT labeling, the candidate becomes a source occurrence and undergoes the
full labeled-frame eligibility audit.

## Material-profile and feature-provider architecture

DATA9A7a implements the declarative profile boundary:

```python
class SystemProfileProvider(Protocol):
    provider_id: str
    provider_version: str

    def build_profile(self) -> MaterialProfileIdentity: ...
    def build_atom_groups(self, profile) -> AtomGroupCatalog: ...
    def build_condition_axes(self, profile) -> ConditionAxisCatalog: ...
    def build_independence_axes(self, profile) -> IndependenceAxisCatalog: ...
```

This first protocol deliberately does not calculate scientific features. It
identifies the material, its phases, geometry, chemistry modifiers, optional
extensions, meaningful atom groups, condition axes, and independence axes.
The user explicitly declares the production profile; an automatic suggestion is
advisory until confirmed.

A material profile is compositional rather than a flat enum. One or more phase
components are combined with a geometry. For example, a solid-liquid interface
contains separate crystalline-solid and liquid phase components under the
`interface` geometry. Structural extensions such as `porous_network`, `zeolite`,
and `lta` are optional and hierarchical. The generic one-phase fallback defines
only `all_atoms`; a multi-phase profile must explicitly define phase membership.

DATA9A7b implements the first separate provider catalog for selection-grade
local structure and generic structural events. Later stages add phase-specific
activation, partition-critical profile features, additional selection evidence,
and metric-group policies. They do not silently enlarge `SystemProfileProvider`,
which remains the stable declarative identity contract.

The current DATA4-DATA7 implementation contains a generic universal path and
optional provider-specific extensions. DATA9A7d migrates the LTA implementation
behind the common extension envelope; LTA-named Python attributes remain only
as compatibility views for historical bundles.

A representative solid-liquid interface profile is expressed as:

```text
profile_id: lta-salt-interface
geometry: interface
phases:
  framework:
    phase_kind: crystalline_solid
    atom_groups: [framework_atoms]
    chemistry_modifiers: [ionic, covalent_network]
  molten_salt:
    phase_kind: liquid
    atom_groups: [salt_atoms]
    chemistry_modifiers: [ionic]
extensions: [porous_network, zeolite, lta]
```

This profile declares identity only. DATA9A7b provides a universal structural
provider that may be activated for any declared material profile; DATA9A7c and
DATA9A7d decide which phase-specific and optional-extension providers are added.
Analysis-owned validation calls remain separate.

A separate fold transformation implements:

```python
class FoldFeatureTransform(Protocol):
    def fit(self, training_frame_uids): ...
    def transform(self, frame_uids): ...
```

Raw scientific features and fitted statistical transforms are therefore not
confused.

### Universal structural selection features (DATA9A7b)

The universal structural provider is an interpretable complement to learned
MACE descriptors. For pair separation $r_{ij}$, it defines a continuous
chemistry-scaled weight from the sum of declared covalent radii. Smooth
coordination is the weighted degree, while the support-neighbor count records
how many pair weights exceed the numerical floor. Radial Gaussian projections
summarize neighbor-shell occupancy without locating RDF peaks or minima.
Weighted Legendre moments summarize neighbor-pair angles, and weighted spherical
harmonics produce rotationally invariant $q_4$ and $q_6$ order parameters.
A Gaussian local-density proxy and neighbor-species entropy provide packing and
chemical-mixing information.

These quantities are selection descriptors, not replacements for analysis-owned
RDF, integer coordination, angle-distribution, structure-factor, or topology
results. Missing angular moments are represented by a zero fill plus an explicit
mask. All minimum-image, switching, radial-width, and orientational-order
parameters are part of immutable policy evidence.

Frame descriptors aggregate atomic features by declared atom groups and by each
element present in the authorized DATA6 domain. The element schema is not
constructed from locked-test geometry. Generic temporal events identify large
changes in smooth coordination, support-neighbor count, local density,
orientational order, or same-atom minimum-image displacement. They are candidate
selection anchors only; physical interpretation remains profile-specific.

### Raw thermodynamic features

- total and per-atom energy;
- composition-relative energy;
- RMS, maximum, and quantile force statistics;
- per-species force statistics;
- pressure and stress invariants;
- temperature;
- volume and density;
- SCF iteration statistics.

### Raw cell and geometry features

- cell lengths and angles;
- strain invariants;
- pair-specific minimum distances;
- coordination histograms;
- bond-length moments;
- bond-angle moments;
- coordination anomalies.

### Partition-critical system-profile features

Partitioning must know the rare categorical states that it promises to cover.
DATA4 therefore exposes a lightweight, full-resolution system-profile layer
before the outer partition is locked.

A general profile may provide categorical phase, environment, defect, molecular,
region, or event states. For the optional LTA extension this layer provides, at
minimum:

```text
framework/mobile-species roles
coarse 4R/6R/8R site class when resolvable
on-center/off-center class
coordination-change flag
site-change flag
ring-crossing flag
framework-integrity flag
```

These features are designed for strata and event protection, not for final
high-dimensional selection. If a required partition-critical classification is
unresolved, the partition reports the missing coverage rather than claiming a
balanced split.

### Optional porous/zeolite/LTA extension

These features activate only when the declared material profile requests the
corresponding extension. They are not defaults for ordinary crystals, liquids,
amorphous systems, or interfaces.

- Si-O and Al-O coordination;
- tetrahedral distortion;
- framework topology state;
- Li-O, Na-O, and K-O coordination;
- nearest 4R, 6R, and 8R identity;
- ring-center displacement;
- signed ring-plane distance;
- off-center displacement;
- site assignment;
- entry, exit, transition, and ring-crossing events.

### Optional MACE features

An optional `mdstats[mace]` provider may compute:

- foundation checkpoint identity and SHA-256;
- MACE version and source snapshot;
- invariant atomic descriptors;
- species-separated descriptor summaries;
- declared atom-group and species environment descriptors;
- zero-shot energy, force, and stress residuals.

MACE exposes learned descriptors for atomic environments [2]. PyTorch and MACE
remain optional dependencies.

### Label-derived difficulty-feature blinding

Descriptors depend only on geometry and a frozen model and may be computed for
all domains. Foundation residuals require DFT labels and are therefore private to
an authorized training domain:

```text
TrainingDifficultyFeatureCatalog
    Residuals allowed for fold-training or final-training selection.

BlindedEvaluationPredictionCatalog
    Predictions stored without exposing residual-based selection features.
```

Outer monitor, calibration, held-out-fold, and locked-test residuals must not
enter selection reports or feature fitting. Locked-test labels and residuals
remain sealed until post-freeze evaluation. A policy violation is a hard leakage
failure, even when the split itself is unchanged.

### Fitted transforms and heterogeneous feature metric

Raw feature providers are partition-independent. Dataset-dependent operations
are represented by distinct objects:

```text
FeatureMetricPolicyTemplate
FoldFeatureTransform[k]
FoldFeatureMetricFit[k]
FinalFeatureTransform
FinalFeatureMetricFit
```

For fold $k$, fitting may inspect only the fold gradient-training domain. The
held-out fold, fold checkpoint monitor, outer monitor, calibration cohort, and
locked tests may be transformed using frozen parameters but cannot influence
the fit.

A `FeatureMetricPolicyTemplate` defines:

```text
raw feature blocks
per-feature robust scaling rule
per-block normalization
retained dimension or PCA rule
block weights
species weights
missing-block behavior
distance metric
dtype and numerical tolerance
```

A fitted metric records the medians, scales, projections, covariance factors,
and retained dimensions learned from its declared training domain.

A block-normalized distance can be

$$
d^2(i,j)=
\sum_b w_b
\frac{
\left\|\mathbf z_i^{(b)}-\mathbf z_j^{(b)}\right\|_2^2
}{d_b},
$$

where $b$ is a feature block, $d_b$ is its retained dimension, and $w_b$ is an
explicit physical weight. Species-specific atomic-environment distances are
reported separately from configuration-level distances. Dividing by retained
dimension prevents a high-dimensional MACE descriptor block from dominating
low-dimensional physical features solely through component count.

Fold-local and final transforms and metric fits are serialized separately from
the static template.

## Event detection before thinning

Rare events may be shorter than a preliminary stride. The controlling order is:

1. source and label integrity screening on all frames;
2. event and change-point detection on all eligible frames;
3. preservation of compact event windows;
4. temporal thinning of the ordinary non-event pool;
5. descriptor and physical-feature selection.

An event window may include one frame before, a representative event frame, and
one frame after. The exact stencil is policy-controlled. Dozens of adjacent
frames from one event are not retained unless required by a transition-path
analysis.

## Autocorrelation and complete-frame blocks

### Observable families

Fast observables:

- potential energy;
- force RMS;
- pressure;
- temperature.

Slow observables:

- mobile-ion coordination;
- site identity;
- ring-plane coordinate;
- framework topology state.

Fast autocorrelation controls the minimum ordinary block size. Slow variables
diagnose whether site-level independence is available at all.

### Candidate stride in frames

The candidate stride is dimensionally defined as

$$
s_{\mathrm{candidate}}
=
\max\left[
 s_{\min},
 \left\lceil
 \frac{c\tau_{\mathrm{fast}}}{\Delta t_{\mathrm{frame}}}
 \right\rceil
\right],
$$

and

$$
\Delta t_{\mathrm{candidate}}
=
s_{\mathrm{candidate}}\Delta t_{\mathrm{frame}},
\qquad 0<c\le1.
$$

The stride applies only to the non-event pool.

### Complete-frame blocks

A `TrainingDataBlock` contains whole configurations over a contiguous interval:

```text
block_id
run_id
frame_start
frame_stop
represented_time
regime
correlation diagnostics
configuration fingerprints
```

Atoms from one frame are never assigned to different partitions.

### Purge width

A purge interval separates statistical roles. The policy records whether the
purge is based on:

- a multiple of fast autocorrelation time;
- a minimum physical duration;
- event boundaries;
- restart-overlap detection.

If a slow state never decorrelates, the report states that blocked temporal
splitting does not provide state-level independence.
