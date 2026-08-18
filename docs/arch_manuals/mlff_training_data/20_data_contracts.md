# Part II - Data and evidence contracts

## Evidence records and immutability

The MLFF data model separates source facts, workflow decisions, fitted products, runtime realizations, and external scientific results. A new policy creates new policy/decision records rather than mutating immutable source/frame facts.

### Source and frame facts

`TrainingDataSource` owns source occurrence identity, path/location hints, content hashes, composition/controls, ensemble/quality/production evidence, label-domain identity, and declared reference grouping. `TrainingFrameRecord` owns source-bound frame facts such as `frame_uid`, source occurrence, frame index/time, atoms/cell, label references, conditions, and distinct geometry/label fingerprints.

`TrainingFrameRecord` does **not** own eligibility, partition, selection, exposure, calibration, or acquisition state.

### Decision, policy, fitted, and realization records

Separate record families include, as applicable:

```text
FrameEligibilityDecision
PartitionAssignment
SelectionAssignment
ExposureAssignment
CandidateAdmissibilityDecision
AcquisitionDecision

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

A static policy defines an algorithm and fixed choices. A fitted record contains parameters learned from one explicitly authorized training domain. A realization record records behavior actually observed from an external/runtime system. Those roles are not interchangeable.

### Digests and signatures

The architecture distinguishes deterministic content/policy/source digests from authenticated digital signatures. Content digests detect modification and bind identity but do not by themselves authenticate authorship. Serialized current records carry version/schema and deterministic content identity under their owning specifications.

## Source manifest and occurrence identity

A review/production manifest supplies source locators, grouping declarations, scientific assertions that cannot be reconstructed unambiguously from one source file, and explicit expert overrides with rationale. Directory/file naming is diagnostic input, not accepted physical truth without verification.

The source byte/content identity is distinct from a manifest occurrence. Byte-identical copies may share a source-content identity while deliberately distinct manifest runs have distinct occurrence identities.

A frame occurrence is derived from the occurrence identity plus source frame index. This keeps occurrence identity stable across later concatenation/export while permitting duplicate-geometry detection across separate source occurrences.

## Geometry, label, and labeled-configuration identities

The architecture keeps three identities separate:

```text
geometry_fingerprint
label_payload_digest
labeled_configuration_fingerprint
```

`geometry_fingerprint` identifies atomic geometry independently of energy/force/stress labels under the current canonical wrapping/cell/tolerance policy. `label_payload_digest` binds the selected labeled payload and its label-domain identity. `labeled_configuration_fingerprint` combines geometry and label payload.

Leakage auditing uses occurrence overlap, exact geometry overlap, exact labeled-configuration overlap, declared near-geometry/descriptor criteria, restart/copy detection, and forbidden temporal proximity. Approximate/symmetry-aware matching may exist as an additional current policy only when explicitly specified; it cannot change the semantic roles above.

## Electronic-structure label domains

Electronic-structure identity is decomposed because not every input difference has the same scientific meaning:

```text
TheoryIdentity
EnergyReferenceIdentity
DerivativeConvention
NumericalQualityProfile
SoftwareProvenance
```

A versioned `LabelCompatibilityPolicy` classifies differences as compatible, compatible with quality evidence, separate label domain, or unresolved. Theory- or reference-defining differences cannot be silently waived.

A target training bundle contains one compatible target label domain and, when enabled, a separately identified replay head/lineage. Incompatible target DFT levels produce separate target bundles rather than an implicit mixed target domain.

### Energy channel

The selected target energy is an explicit named channel consistent with the derivative labels. Its channel, units, completeness, electronic/reference convention, and provenance are preserved. Energy/force/stress labels that do not share an accepted derivative/reference convention are not silently combined.

## Atomic-reference identifiability and fitting

For elemental correction vector $\Delta\mathbf e_0$, fitting has the schematic form

$$
\mathbf A\,\Delta\mathbf e_0 \approx \mathbf b,
$$

with configuration-element count matrix $\mathbf A$ and target-minus-foundation energy residual $\mathbf b$.

### Structural identifiability

`AtomicReferenceIdentifiabilityReport` depends on elemental count support rather than fitted target residuals. It records element order, matrix shape/rank/singular values, condition/null-space information, identifiable combinations, outcome, and transfer limitations. It does not contain fitted elemental corrections.

Rank deficiency can be acceptable only under an explicit fixed-domain/reference policy with its null space and transfer restrictions preserved. Fixed-stoichiometry systems must not imply individually identified elemental offsets when the count matrix does not support them.

### Training-domain fit

`AtomicReferenceFitRecord` is a fitted object bound to one fold/final training domain, foundation checkpoint identity, identifiability report, solver/tolerance, elemental support, fitted corrections, residual, and policy outcome.

Each cross-validation fold receives its own fold-local fit. Final training receives a separate final-training fit. Outer monitors, calibration, held-out evaluation folds, and locked tests are excluded from the fit. Missing elemental support or new rank deficiency fails or invokes an explicitly declared alternative reference policy.

MACE export receives the exact accepted numerical E0 representation (normally an atomic-number mapping); a record/path name is provenance rather than an E0 payload.

## Ensemble, temperature, cell, and strain

### Ensemble and temperature

The subsystem consumes mdstats control/ensemble certification and distinguishes equilibrium, pressure-controlled, ramped/driven, multi-thermostat, and unresolved cases under the owning control specification. Ensemble is not inferred merely from observed cell variation.

Nominal temperature controls and realized ionic-temperature statistics remain separate. `TemperatureCondition` binds requested/thermostat targets, realized series/statistics, drift/stationarity evidence, and ramp status as applicable.

### Reference-cell resolution

Strain requires an explicit or uniquely resolvable compatible reference. Accepted resolution order is controlled by current specifications and may use an explicit matrix/structure/run or a unique compatible unstrained member of the declared reference group. Ambiguity fails closed.

### Cell and deformation convention

ASE cell vectors are rows. For fractional row vector $\mathbf s_{\rm row}$ and cell $\mathbf H$,

$$
\mathbf r_{\rm row}=\mathbf s_{\rm row}\mathbf H.
$$

For reference $\mathbf H_0$ and current cell $\mathbf H_t$, the reported deformation gradient acting on Cartesian column vectors is

$$
\mathbf F_t=\left(\mathbf H_0^{-1}\mathbf H_t\right)^T.
$$

An internal right-acting row-vector form is acceptable only when serialization/reporting returns the declared Cartesian-column convention. Rotation/stretch separation uses the declared polar-decomposition convention. Stored strain evidence includes the applicable volume, linear/finite/logarithmic, hydrostatic/deviatoric, principal, shear, rotation, coordinate-frame, and storage-convention quantities.

Qualification includes nonsymmetric shear and rotated-stretch cases so transpose/left-right errors cannot hide behind diagonal fixtures.

### Hierarchical condition schemas

Condition space is not assumed to be a global Cartesian product. A material profile declares applicable condition axes and hierarchical strata. The LTA profile, for example, separates unstrained composition/temperature/regime strata from strained composition/reference-condition/strain-mode/sign/regime strata. Only observed and scientifically applicable combinations are required.

## Stress and virial

Canonical `REF_stress` is a symmetric Cartesian Cauchy-stress tensor in eV/Angstrom$^3$ under the ASE/MACE sign convention qualified by the runtime lock. Tensor shear carries no engineering-factor multiplication. Intermediate Voigt ordering, when used, is explicit and round-tripped.

Virial and stress have distinct keys and are never silently relabeled. Qualification covers units, finite-strain sign, tensor/Voigt order, shear factors, and MACE read-back. Missing stress may carry zero stress weight only under an explicit heterogeneous-label policy.

## Eligibility and quality

Run/source quality distinguishes qualified, degraded, unqualified, and unresolved states under current policy. Overrides are explicit evidence.

`FrameEligibilityDecision` applies after labels exist. Hard rejection includes absent/nonfinite required labels or geometry/cell, singular/corrupt structures, incomplete ionic records not recoverable under the current trailing-interruption policy, catastrophic overlaps, and disallowed electronic-convergence failures. Soft evidence records transient regimes, unusual but physical forces/stress, rare coordination/events, topology changes, model residuals, and degraded numerical quality without turning percentile tails into automatic rejection.

Pre-DFT candidates use a separate `CandidateAdmissibilityDecision` over geometry/cell safety, element/count policy, topology/integrity, trajectory/integrator evidence, model outputs, and descriptor availability. After DFT labeling they re-enter normal source/frame eligibility lineage.

## Material profiles and feature providers

### Declarative profile boundary

`SystemProfileProvider` owns material identity: phases, geometry, chemistry modifiers, optional structural extensions, meaningful atom groups, condition axes, and independence axes. It does not itself own calculated scientific feature arrays.

Profiles are compositional rather than a single flat material enum. Interface/multiphase systems explicitly declare component membership. Generic fallback supplies only generic groups/axes; porous/zeolite/LTA semantics require the corresponding explicit extension chain and never activate automatically.

### Universal structural selection features

The generic structural provider supplies selection-grade local geometry descriptors such as smooth chemistry-scaled coordination, support-neighbor count, radial projections, local-density/mixing proxies, angular moments, and rotationally invariant orientational-order summaries. These are frame/environment selection descriptors, not replacements for analysis-owned RDF, integer coordination, full angle distributions, structure factors, or topology observables.

Descriptors aggregate by authorized atom groups and elements present in the permitted domain. Generic temporal events capture large local structural changes without assigning material-specific physical meaning.

### Partition-critical profile features

Rare categorical states that partition policy promises to protect are available at full resolution before the outer partition freezes. A profile may supply phase, environment, defect, region, molecular, or event states. Optional LTA state includes framework/mobile roles, resolvable ring/site class, off-center class, coordination/site/ring-crossing changes, and framework-integrity evidence.

Unresolved required classifications produce explicit coverage/partition limitations rather than fabricated balanced strata.

### Optional profile extensions

Optional porous/zeolite/LTA providers may contribute framework/cation coordination, tetrahedral distortion/topology, ring/site/window geometry, site assignment, and transition/crossing evidence only when their extension is explicitly declared.

### Optional learned-model features

A qualified optional MACE provider may supply foundation/model identity, invariant atomic descriptors, group/species environment summaries, and authorized zero-shot prediction/residual evidence. MACE/PyTorch remain optional dependencies to the mdstats core.

## Feature blinding and fitted metrics

Geometry-only descriptors from a frozen model may be computed wherever authorized. Label-derived residual/difficulty features may be exposed only inside their applicable training domain.

Outer monitor, calibration, held-out evaluation, and locked-test residuals do not enter feature fitting or selection. Evaluation predictions can be persisted in blinded catalogs without exposing residual-derived selector inputs. Violating this boundary is a hard leakage failure.

Raw feature providers are partition-independent. Dataset-dependent scaling/PCA/whitening/metric fitting is represented by separate static templates and fold/final fitted records. For fold $k$, fitting may inspect only its gradient-training domain; other domains may be transformed by the frozen fitted object but cannot influence it.

A block-normalized metric may take the form

$$
d^2(i,j)=\sum_b w_b\frac{\|\mathbf z_i^{(b)}-\mathbf z_j^{(b)}\|_2^2}{d_b},
$$

where block weights, dimensions, missing-block behavior, dtype, tolerance, and any fitted scaling/projection are explicitly identified. High-dimensional learned descriptors do not dominate solely because they contain more components.

## Event detection before thinning

The controlling order is:

1. source/label integrity on full-resolution frames;
2. event/change detection on all eligible frames;
3. protected event-window preservation;
4. temporal thinning of the ordinary non-event pool;
5. higher-cost descriptor/selection operations.

Event stencils are policy-controlled and compact by default. Adjacent frames from one physical event are not mistaken for independent rare-event evidence.

## Autocorrelation and complete-frame blocks

Fast observables determine the minimum ordinary decorrelation/block scale; slow structural variables diagnose whether state-level independence exists at all. Candidate stride is defined in physical/frame time from the declared fast autocorrelation estimate and applies only to the non-event pool.

A `TrainingDataBlock` is a contiguous interval of whole configurations with block/run/frame bounds, represented time, regime, correlation evidence, and configuration identities. Atoms from one configuration are never split across statistical roles.

A purge interval separates roles using the declared physical/autocorrelation/event/restart policy. If a slow state never decorrelates, the independence report explicitly states that temporal blocking does not provide state-level independence.
