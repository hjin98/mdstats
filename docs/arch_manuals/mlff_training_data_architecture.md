---
geometry: "margin=0.75in"
architecture_revision: 107
status: "current normative architecture"
last_updated: "2026-08-30"
---

# MLFF Training-Data and Fine-Tuning Architecture

## Purpose and authority

This manual defines the accepted current scientific, statistical, execution, and evidence architecture for the mdstats MLFF workflow: source-certified atomistic data preparation, leakage-safe evidence roles, fitted preparation, multi-view target-subset construction, target-size selection, MACE fine-tuning, protocol validation, deployment, calibration, and bounded campaign execution.

It is intentionally present-tense and single-generation. A reader does not need release chronology, migration history, or obsolete stage semantics to determine current behavior.

The canonical editable architecture sources are the numbered chapters under `docs/arch_manuals/mlff_training_data/`. The assembled Markdown and PDF are generated publication products of those sources and must not be edited as independent authorities.

Detailed exact behavior is owned by current specifications under `docs/specs/training_data/`. Methods/theory material may explain rationale but does not override architecture or specifications. Proposed transitions live in `workplans/`; completed chronology lives under `docs/history/mlff/`; correctness/performance evidence lives in audits, release evidence, and benchmarks.

## Architectural motive

MLFF campaigns combine state with fundamentally different epistemic roles: physical source facts, eligibility decisions, evidence partitions, fitted transforms, subset-membership decisions, target-size decisions, optimization/checkpoint state, protocol-validation evidence, calibration evidence, locked tests, and deployment decisions. Conflating those roles creates leakage and ambiguous authority even when the numerical code is correct.

The architecture therefore uses immutable/content-addressed evidence, explicit statistical roles, one normative owner per scientific decision, and authenticated dependency direction. Execution realization is kept separate: cache layout, worker count, queue order, out-of-core storage, and scheduler policy may change without changing scientific membership, ordering, coverage, ranking, or evidence roles.

Expensive exact numerical work is computed once per semantic identity and reused wherever its inputs are unchanged. Exactness, deterministic authoritative decisions, bounded materialization, explicit resource ownership, and restartable authenticated state take precedence over nominal utilization.

## Current workflow at a glance

```text
source evidence and labels
  -> eligibility / physical conditions
  -> raw feature and event evidence
  -> evidence-role partitioning
  -> fold/final training domains
  -> fitted descriptors, metrics, E0/objective/weight inputs
  -> one P_train / M3 target-size development split
  -> one canonical training order pi_train and evaluation ladder M1 subset M2 subset M3
  -> one common deterministic target-size preparation
  -> paired optimizer-seed screen over candidate sizes
  -> one target-size reducer
  -> N_selected and T_selected = pi_train[:N_selected]
  -> post-selection cross-validation on exactly T_selected
  -> fresh final production on the complete T_selected
  -> currentness-fenced publication
```

The current graph has exactly one target-size architecture. The retired
per-domain multi-view selection generation is not an alternate current path: it
is neither migrated nor semantically read forward, and a workspace still holding
its derived state is rejected with an actionable destructive reset/reprepare
requirement before any candidate, checkpoint, or descendant is reused. Raw
scientific inputs and independently valid low-level content caches remain
reusable when their recipes do not depend on retired target-size semantics.

## Reading index

| Need | Primary chapter |
|---|---|
| Scientific motivation, record/evidence model, and scope | Part I - Foundations |
| Source identity, labels, strain/stress, eligibility, raw features/events | Part II - Data and evidence contracts |
| Evidence roles, leakage-safe CV, fitted preparation, objective/weighting/exposure boundaries | Part III - Statistical design and fitted preparation |
| Replay, MACE protocol, checkpointing, validation, deployment, calibration, active learning | Part IV - Training, evaluation, and deployment |
| Target-size split/orders, paired-seed screen, reducer, post-selection CV, fresh final production | Part V - Target-size selection and post-selection validation |
| Exact execution, bounded resource/materialization, cache/restart/storage/progress | Part VI - Performance and execution architecture |
| Sole-owner matrix and accepted extension boundaries | Part VII - Ownership and extension boundaries |
| External scientific/algorithmic sources | References |

## Context retrieval index

For targeted human or AI loading, use the smallest current source containing the needed concept:

| Query terms | Load first |
|---|---|
| source/label identity, eligibility, strain/stress, raw features/events | `20_data_contracts.md` |
| evidence roles, leakage, CV, fitted metrics, E0, objective, weighting, exposure | `30_statistical_design.md` |
| replay, MACE, checkpoint, evaluation, deployment, calibration, active learning | `40_training_evaluation.md` |
| target size, `pi_train`, `T_selected`, `M1/M2/M3`, `n1/n2/n3`, post-selection CV, final production | `50_target_size_selection.md` |
| scheduler, sparse execution, out-of-core, memory, persistence, progress | `60_execution_performance.md` |
| owner, dependency direction, unsupported generation, extension boundary | `80_ownership_and_decisions.md` |
| scientific/algorithmic provenance | `90_references.md` |
| superseded design rationale or release chronology | `docs/history/mlff/` |
| proposed transition | `workplans/active/` |

## Stable terminology

- **training domain** — the DATA5-authorized fold/final gradient-training evidence available to fitted preparation and subset construction.
- **target membership** — frame membership in a target-training subset; an exact prefix of the one canonical training order `pi_train`.
- **target size** — the protocol-level scientific target-training cardinality chosen by the one target-size reducer.
- **monitor size** — the cardinality of a monitoring/evaluation evidence set; never target-size authority.
- **training order** — the one canonical deterministic ordering `pi_train` of the target-training pool whose prefixes define candidate target subsets.
- **qualified size** — a candidate size admitted by the configured target-size policy for the current experiment definition.
- **selected size** — the one target size `N_selected` frozen by the reducer together with the exact membership `T_selected`.
- **authoritative evidence** — persisted information that defines or independently proves a scientific decision.
- **reconstructible execution cache** — discardable state derivable exactly from authoritative inputs.
- **unsupported generation** — an old campaign/artifact generation that current architecture does not interpret or migrate; it requires re-preparation.

## Normative vocabulary

- **SHALL / MUST** — required for scientific, statistical, or execution correctness.
- **SHOULD** — the default design unless measured evidence justifies another exact-equivalent realization.
- **MAY** — optional realization that cannot weaken the scientific contract.

When architecture explains a change-sensitive constant whose exact value is specification-owned, the owning specification remains the sole normative location for changing that value.

## Retrieval and local-context rule

Each major chapter states what its concepts own, consume, emit, and explicitly do not own. Equations and symbols are defined near first use. A chapter may repeat a dependency boundary for local comprehension, but repeated prose must not create a second independently tunable contract.

# Part I - Foundations

## What an MLFF learns

An energy-conserving machine-learned force field represents a potential-energy function

$$
E_\theta=E_\theta(\mathbf Z,\mathbf R,\mathbf H),
$$

where \(\mathbf Z\) contains atomic numbers, \(\mathbf R\) positions, \(\mathbf H\) the periodic cell, and \(\theta\) model parameters. Forces and stress follow from derivatives of the same energy,

$$
\mathbf F_i=-\frac{\partial E_\theta}{\partial\mathbf R_i},
\qquad
\boldsymbol\sigma=-\frac{1}{V}\frac{\partial E_\theta}{\partial\boldsymbol\epsilon},
$$

under the declared stress sign and strain convention of the label source. MACE constructs symmetry-aware local atomic representations and sums atomic-energy contributions [1]. A useful training/evaluation corpus must therefore constrain both the energy surface and its derivatives throughout the intended simulation domain.

A low global force error is not sufficient. Common framework vibrations can dominate aggregate statistics while rare mobile-ion environments, strain states, migration geometries, interfaces, defects, or other declared focus physics remain poorly represented. The architecture separates broad numerical metrics, condition/group-resolved evidence, physical-observable validation, and explicit extrapolation/challenge evidence.

## Why trajectory frames need statistical roles

Molecular-dynamics frames are temporally correlated. Neighboring configurations can be near duplicates, so assigning them to nominally different roles can create leakage and overstate model quality.

For observable \(x_t\), normalized autocorrelation at lag \(k\) is

$$
\rho_x(k)=
\frac{\langle(x_t-\bar x)(x_{t+k}-\bar x)\rangle}
     {\langle(x_t-\bar x)^2\rangle}.
$$

A truncated integrated autocorrelation time is

$$
\tau_{\mathrm{int},x}=\Delta t\left[\frac12+\sum_{k=1}^{k^\star}\rho_x(k)\right],
$$

with approximate effective sample count

$$
N_{\mathrm{eff},x}\approx\frac{T}{2\tau_{\mathrm{int},x}}.
$$

mdstats therefore uses autocorrelation-aware complete-frame blocks, purge semantics, and explicit independence grades rather than treating every frame as independent [3-5]. Exact estimators, truncation, block size, purge, and role-assignment rules are specification-owned.

## Evidence-role model

The architecture distinguishes evidence by what it is allowed to control.

| Role | Supplies gradients? | May control fitted preparation/subset/size/checkpoint? | Purpose |
|---|---:|---:|---|
| development / training domain | Yes when selected | Yes, within the authorized training/model-selection contract | fitting and protocol development |
| checkpoint / common target monitor | No | Yes, only for explicitly authorized development/model-control decisions | stopping/checkpoint and target-size development evidence |
| held-out CV evaluation | No | No for the frozen protocol it evaluates | protocol validation |
| calibration | No | No training/subset/checkpoint changes | final-committee uncertainty calibration |
| locked interpolation/challenge test | No | No | sealed final evaluation |

Calibration is not test data; held-out CV is not a checkpoint monitor; and a monitor cardinality is not a target-training cardinality.

## Scope and ownership

The MLFF subsystem owns dataset certification, evidence-role construction, fitted preparation, multi-view target-subset construction, target-size study, training-artifact construction, campaign orchestration, checkpoint/evaluation lineage, deployment verification coordination, and active-learning lineage.

Its current responsibilities include:

- VASP source discovery/certification and source/label identities;
- composition, thermodynamic condition, ensemble, reference-cell, strain/stress reconstruction;
- electronic-structure compatibility and label-domain grouping;
- energy/force/stress audit and atomic-reference identifiability/fitting lineage;
- immutable frame facts, eligibility, and quality decisions;
- generic raw structural features/events plus explicit optional material/profile extensions;
- autocorrelation-aware complete-frame blocks and role feasibility;
- fixed outer roles and independent CV job families;
- fold/final-domain fitted descriptors, transforms, metrics, E0, objective/weight, and difficulty evidence;
- the target-size development split, the canonical training/evaluation orders, the common preparation, and the paired optimizer-seed screen;
- one protocol-global target-size decision with domain-local membership;
- MACE target/replay artifacts and explicit exposure realization;
- replay-retention and checkpoint admissibility;
- protocol-matched CV, final training, committee export, calibration, sealed evaluation, and deployment verification;
- active-learning candidate/DFT lineage where supported by current specifications.

The subsystem does not silently merge incompatible electronic-structure levels, infer ambiguous scientific references, use held-out/locked evidence for forbidden model-control decisions, redefine analysis-owned physical-observable algorithms, create a second target selector, generate rescue target sizes, or migrate unsupported old campaign generations.

LTA/zeolite ring, cage, site, crossing, and related semantics are optional profile extensions rather than generic defaults.

## Reference application: Li/Na/K-LTA

The principal reference application contains AIMD evidence spanning multiple cation compositions, temperatures, and strain conditions. It motivates—but does not hard-code into generic architecture—several requirements:

1. framework atoms can outnumber mobile cations, so aggregate metrics must not hide declared mobile-species environments;
2. strain conditions need not form a full Cartesian product with composition/temperature, so condition applicability may be hierarchical;
3. one trajectory per condition supplies limited independence and must not be represented as an independent-replica test;
4. fixed framework stoichiometry can make individual atomic reference-energy corrections non-identifiable without anchors;
5. short trajectories may contain few rare transitions, so absent events are explicit coverage gaps rather than evidence of irrelevance.

## Reuse of analysis and sampling capabilities

The MLFF workflow orchestrates existing mdstats capabilities instead of duplicating them.

| Capability | MLFF use |
|---|---|
| `mdstats.io.vasp.read_vasp_frames` | cells, coordinates, energies, forces, stress, temperature, provenance |
| VASP control/ensemble readers | controls, energy-channel and ensemble evidence |
| trajectory-quality / production-regime assessment | source and stationary-regime evidence |
| analysis structural/topology modules | optional profile-owned raw evidence or post-training observables under analysis contracts |
| sampling/cross-fit primitives | source-bound blocks, purge, and independence semantics |

Physical observables remain owned by `mdstats.analysis`. The MLFF layer may orchestrate matched evaluation and retain analysis-owned result identities, but it does not redefine RDF, MSD, VACF, VDOS, diffusion, topology, conductivity, or related numerical algorithms.

## Current controlling data flow

```text
source bytes / controls / trajectory collections
  -> source and label-domain certification
  -> immutable frame facts and eligibility
  -> raw features/events before ordinary thinning
  -> correlation-aware blocks and evidence-role feasibility
  -> development / monitor / CV / calibration / locked roles
  -> required fold/final training domains
  -> domain-local DATA6/DATA7 fitted preparation
  -> P_train / M3 split -> pi_train / pi_eval
  -> common target-size preparation
  -> paired optimizer-seed screen -> target-size reducer
  -> common qualified target-size population
  -> target-size study using authorized development/model-selection evidence
  -> one frozen protocol-global N_selected
  -> domain-local selected prefixes
  -> protocol-matched CV with held-out folds inaccessible to size/checkpoint choice
  -> accepted frozen protocol
  -> independent final seeds and checkpoint admission
  -> final committee + deployment artifacts
  -> final-committee calibration where supported
  -> explicit locked-test / observable-validation activation
  -> active-learning lineage where configured
```

No allowed dependency runs from held-out CV or locked-test evidence backward into fitted transforms, E0 fitting, target membership, target-size selection, checkpoint choice, or calibration-policy design.

## Responsibility separation is more durable than module layout

The implementation may reorganize Python modules while preserving the architecture. The durable separation is among:

- physical/source facts;
- evidence-role and policy decisions;
- training-domain fitted products;
- target-membership and target-size decisions;
- runtime/execution realization;
- validation/calibration/locked evidence;
- external analysis-owned results.

Current specifications control public/serialized current-generation contracts. Internal refactoring may reuse common sampling/execution primitives when externally owned scientific behavior and persisted current-generation identities remain conforming. Backward compatibility with superseded campaign generations is not an architectural requirement, except for the narrow immediately preceding fixed-fidelity restart boundary: it may reuse authenticated unchanged preparation inputs, but it must create a fresh configurable target-size authority and fails closed when compatibility is ambiguous.

# Part II - Data and evidence contracts

## Purpose and ownership

This chapter defines immutable source/frame facts, label-domain identity, physical conditions, quality/eligibility, raw feature/event providers, and correlation-aware complete-frame evidence blocks.

It does not own evidence-role assignment beyond the records needed to support DATA5, fitted statistics, target membership, target size, training exposure, checkpoint selection, or validation decisions.

## Evidence records and immutability

The MLFF data model separates source facts, workflow decisions, fitted products, runtime realizations, and external scientific results. A new policy creates new policy/decision records rather than mutating immutable source/frame facts.

### Source and frame facts

`TrainingDataSource` owns source occurrence identity, path/location hints, content hashes, composition/controls, ensemble/quality/production evidence, label-domain identity, and declared reference grouping.

`TrainingFrameRecord` owns source-bound frame facts such as `frame_uid`, source occurrence, frame index/time, atoms/cell, label references, physical conditions, and distinct geometry/label fingerprints.

`TrainingFrameRecord` does **not** own eligibility, statistical role, target membership, target size, training exposure, calibration, or acquisition state.

### Decision, policy, fitted, and realization families

Representative downstream/current families include:

```text
FrameEligibilityDecision
PartitionAssignment
CandidateAdmissibilityDecision
AcquisitionDecision

PartitionRoleBudgetPolicy
PartitionFeasibilityReport
FeatureMetricPolicyTemplate
FoldFeatureMetricFit
FinalFeatureMetricFit
TrainingObjectivePolicy
ConfigurationWeightPolicy
PropertyWeightPolicy
CheckpointMetricPolicy
TargetSizeExperimentDefinition
ResolvedTargetSizePolicy
TargetSizeCommonPreparation
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

Target membership is intentionally absent from the generic DATA2-DATA4 record list because its current authority is the canonical training order `pi_train` derived by the target-size owners in Part V.

### Digests and signatures

Deterministic content/policy/source digests bind identity and detect modification. They do not by themselves authenticate authorship. Serialized current records carry version/schema and deterministic content identity under their owning specifications.

## Source manifest and occurrence identity

A review/production manifest supplies source locators, grouping declarations, scientific assertions that cannot be reconstructed unambiguously from one source file, and explicit expert overrides with rationale. Directory/file naming is diagnostic input, not accepted physical truth without verification.

The source byte/content identity is distinct from a manifest occurrence. Byte-identical copies may share a source-content identity while deliberately distinct manifest runs have distinct occurrence identities.

A frame occurrence derives from occurrence identity plus source frame index. This keeps occurrence identity stable across later concatenation/export while permitting duplicate-geometry detection across separate source occurrences.

## Geometry, label, and labeled-configuration identities

The architecture keeps three identities separate:

```text
geometry_fingerprint
label_payload_digest
labeled_configuration_fingerprint
```

`geometry_fingerprint` identifies atomic geometry independently of energy/force/stress labels under the current canonical wrapping/cell/tolerance policy. `label_payload_digest` binds the selected labeled payload and label-domain identity. `labeled_configuration_fingerprint` combines geometry and label payload.

Leakage auditing may use occurrence overlap, exact geometry overlap, exact labeled-configuration overlap, declared near-geometry/descriptor criteria, restart/copy detection, and forbidden temporal proximity. Approximate or symmetry-aware matching may exist only under an explicit current policy; it cannot change the semantic roles above.

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

The selected target energy is an explicit named channel consistent with derivative labels. Its channel, units, completeness, electronic/reference convention, and provenance are preserved. Energy/force/stress labels that do not share an accepted derivative/reference convention are not silently combined.

## Atomic-reference identifiability and fitting boundary

For elemental correction vector $\Delta\mathbf e_0$, the schematic fit is

$$
\mathbf A\,\Delta\mathbf e_0 \approx \mathbf b,
$$

with configuration-element count matrix $\mathbf A$ and target-minus-foundation energy residual $\mathbf b$.

`AtomicReferenceIdentifiabilityReport` depends on elemental count support rather than fitted target residuals. It records element order, matrix shape/rank/singular values, condition/null-space information, identifiable combinations, outcome, and transfer limitations. It does not contain fitted elemental corrections.

The actual `AtomicReferenceFitRecord` is a DATA7 fitted object bound to one fold/final training domain, foundation checkpoint identity, identifiability report, solver/tolerance, elemental support, fitted corrections, residual, and policy outcome.

Each cross-validation fold receives its own fold-local fit. Final training receives a separate final-training fit. Monitors, calibration, held-out evaluation folds, and locked tests are excluded from the fit.

MACE export receives the exact accepted numerical E0 representation, normally an atomic-number mapping; a record/path name is provenance rather than an E0 payload.

## Ensemble, temperature, cell, and strain

### Ensemble and temperature

The subsystem consumes mdstats control/ensemble certification and distinguishes equilibrium, pressure-controlled, ramped/driven, multi-thermostat, and unresolved cases under the owning control specification. Ensemble is not inferred merely from observed cell variation.

Nominal temperature controls and realized ionic-temperature statistics remain separate. `TemperatureCondition` binds requested/thermostat targets, realized series/statistics, drift/stationarity evidence, and ramp status as applicable.

### Reference-cell resolution

Strain requires an explicit or uniquely resolvable compatible reference. Accepted resolution order is controlled by current specifications and may use an explicit matrix/structure/run or a unique compatible unstrained member of the declared reference group. Ambiguity fails closed.

### Cell and deformation convention

ASE cell vectors are rows. For fractional row vector $\mathbf s_{\mathrm{row}}$ and cell $\mathbf H$,

$$
\mathbf r_{\mathrm{row}}=\mathbf s_{\mathrm{row}}\mathbf H.
$$

For reference $\mathbf H_0$ and current cell $\mathbf H_t$, the reported deformation gradient acting on Cartesian column vectors is

$$
\mathbf F_t=\left(\mathbf H_0^{-1}\mathbf H_t\right)^T.
$$

An internal right-acting row-vector form is acceptable only when serialization/reporting returns the declared Cartesian-column convention. Rotation/stretch separation uses the declared polar-decomposition convention.

Stored strain evidence includes the applicable volume, linear/finite/logarithmic, hydrostatic/deviatoric, principal, shear, rotation, coordinate-frame, and storage-convention quantities. Qualification includes nonsymmetric shear and rotated-stretch cases so transpose/left-right errors cannot hide behind diagonal fixtures.

### Hierarchical condition schemas

Condition space is not assumed to be a global Cartesian product. A material profile declares applicable condition axes and hierarchical strata. For example, an LTA profile may separate unstrained composition/temperature/regime strata from strained composition/reference-condition/strain-mode/sign/regime strata. Only observed and scientifically applicable combinations are required.

## Stress and virial

Canonical `REF_stress` is a symmetric Cartesian Cauchy-stress tensor in eV/Angstrom$^3$ under the ASE/MACE sign convention qualified by the runtime lock. Tensor shear carries no engineering-factor multiplication. Intermediate Voigt ordering, when used, is explicit and round-tripped.

Virial and stress have distinct keys and are never silently relabeled. Qualification covers units, finite-strain sign, tensor/Voigt order, shear factors, and MACE read-back. Missing stress may carry zero stress weight only under an explicit heterogeneous-label policy.

## Eligibility and quality

Run/source quality distinguishes qualified, degraded, unqualified, and unresolved states under current policy. Overrides are explicit evidence.

`FrameEligibilityDecision` applies after labels exist. Hard rejection includes absent/nonfinite required labels or geometry/cell, singular/corrupt structures, incomplete ionic records not recoverable under the current interruption policy, catastrophic overlaps, and disallowed electronic-convergence failures.

Soft evidence records transient regimes, unusual but physical forces/stress, rare coordination/events, topology changes, model residuals, and degraded numerical quality without turning percentile tails into automatic rejection.

Pre-DFT candidates use a separate `CandidateAdmissibilityDecision` over geometry/cell safety, element/count policy, topology/integrity, trajectory/integrator evidence, model outputs, and descriptor availability. After DFT labeling they re-enter normal source/frame eligibility lineage.

## Material profiles and feature providers

### Declarative profile boundary

`SystemProfileProvider` owns material identity: phases, geometry, chemistry modifiers, optional structural extensions, meaningful atom groups, condition axes, and independence axes. It does not itself own calculated scientific feature arrays.

Profiles are compositional rather than a single flat material enum. Interface/multiphase systems explicitly declare component membership. Generic fallback supplies only generic groups/axes; porous/zeolite/LTA semantics require the corresponding explicit extension chain and never activate automatically.

### Universal structural selection inputs

The generic structural provider supplies selection-grade local geometry descriptors such as smooth chemistry-scaled coordination, support-neighbor count, radial projections, local-density/mixing proxies, angular moments, and rotationally invariant orientational-order summaries.

These are upstream target-subset inputs, not an independent selector and not replacements for analysis-owned RDF, integer coordination, full angle distributions, structure factors, or topology observables.

Descriptors aggregate by authorized atom groups and elements present in the permitted domain. Generic temporal events capture large local structural changes without assigning material-specific physical meaning.

### Partition-critical profile features

Rare categorical states that partition policy promises to protect are available at full resolution before the outer partition freezes. A profile may supply phase, environment, defect, region, molecular, or event states.

Optional LTA state includes framework/mobile roles, resolvable ring/site class, off-center class, coordination/site/ring-crossing changes, and framework-integrity evidence. Unresolved required classifications produce explicit coverage/partition limitations rather than fabricated balanced strata.

### Optional learned-model features

A qualified optional MACE provider may supply foundation/model identity, invariant atomic descriptors, group/species environment summaries, and authorized zero-shot prediction/residual evidence. MACE/PyTorch remain optional dependencies to the mdstats core.

## Feature blinding and fitted metrics

Geometry-only descriptors from a frozen model may be computed wherever authorized. Label-derived residual/difficulty features may be exposed only inside their applicable training domain.

Outer monitor, calibration, held-out evaluation, and locked-test residuals do not enter feature fitting or target-subset construction. Evaluation predictions can be persisted in blinded catalogs without exposing residual-derived selector inputs. Violating this boundary is a hard leakage failure.

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
5. higher-cost descriptor/fitted target-subset-input operations.

Event stencils are policy-controlled and compact by default. Adjacent frames from one physical event are not mistaken for independent rare-event evidence.

## Autocorrelation and complete-frame blocks

Fast observables determine the minimum ordinary decorrelation/block scale; slow structural variables diagnose whether state-level independence exists at all. Candidate stride is defined in physical/frame time from the declared fast autocorrelation estimate and applies only to the non-event pool.

A `TrainingDataBlock` is a contiguous interval of whole configurations with block/run/frame bounds, represented time, regime, correlation evidence, and configuration identities. Atoms from one configuration are never split across statistical roles.

A purge interval separates roles using the declared physical/autocorrelation/event/restart policy. If a slow state never decorrelates, the independence report explicitly states that temporal blocking does not provide state-level independence.

# Part III - Statistical design and fitted preparation

## Purpose and ownership

This chapter defines the statistical evidence roles that make later model comparisons interpretable and the fitted-preparation boundary immediately upstream of multi-view target-subset construction.

It owns the architectural separation among training, monitoring, cross-validation, calibration, and locked-test evidence. It also defines what fold/final-domain fitted preparation may consume and emit.

It does **not** own target membership or target size. It supplies the protected relations - duplicate groups, correlation families, and split exclusions - that the target-size owners in Part V consume; the canonical training order `pi_train` determines target membership, and the one target-size reducer chooses `N_selected`.

## Independence and evidence roles

### Independence hierarchy

Evidence uses the strongest available independence level, for example:

1. independent replica/velocity seed or independently prepared realization;
2. independent structural/chemical ordering;
3. independent thermodynamic run;
4. purged temporal block within one run.

Temporal separation does not create an independent metastable state when the relevant slow variable never decorrelates. Every cohort carries machine-readable independence evidence and known limitations.

### Partition feasibility

Before assigning roles, the partition policy declares requested cohorts, cross-validation support, minimum independent blocks/grades, purge requirements, and allowed reductions. A feasibility report states what the available evidence can support.

Valid outcomes include full support, temporal-block-only support, deferred calibration, external-only challenge evidence, reduced fold count, or insufficient support. The workflow never fabricates every desired role from a short or correlated trajectory to satisfy a percentage target.

### Outer evidence roles

A feasible target label domain may contain:

```text
development_pool
outer_monitor_validation
uncertainty_calibration
locked_interpolation_test
zero or more locked_challenge_tests
```

Only the development pool supplies gradient-training candidates. The common target monitor is development/model-selection evidence: it may control the current authorized monitoring/checkpoint and target-size-screen policies but supplies no gradients and is not a held-out CV fold or locked test.

Calibration is reserved for predictions from the actual final committee. Locked interpolation/challenge evidence cannot affect fitting, subset construction, target-size selection, training protocol, checkpoint selection, calibration-policy choice, acquisition policy, or protocol design.

When a requested role is unsupported, it is absent/deferred explicitly rather than synthesized from correlated evidence.

## Cross-validation validates a frozen protocol

A frame that supplied a gradient is not independent validation evidence for that model. Likewise, a held-out evaluation fold cannot control stopping, checkpoint choice, or target-size choice for the protocol it is intended to evaluate.

For cross-validation fold \(k\), keep distinct:

```text
fold_training_domain_k
fold_checkpoint_monitor_k
held_out_evaluation_fold_k
```

The fold model has fresh model/optimizer/checkpoint lineage. Fitted transforms, feature metrics, E0 fits, difficulty evidence, and target membership are constructed only from `fold_training_domain_k`. Checkpoint selection uses its authorized monitor, not the held-out evaluation fold.

Target size is frozen **before** protocol-matched held-out CV evaluation. The same selected cardinality is used as a protocol hyperparameter across required folds/final development, while each domain has its own leakage-safe target membership. Only after checkpoint choice freezes is a fold model evaluated on `held_out_evaluation_fold_k`.

Cross-validation is therefore a family of independent jobs evaluating one frozen protocol, not a rotating epoch schedule and not an inner loop for choosing target size.

## Fitted preparation inside each training domain

For each fold/final training domain, DATA6/DATA7 may construct products whose statistical meaning depends on that domain. These include, as applicable:

- descriptor transforms and heterogeneous fitted feature metrics;
- training-domain foundation-model predictions/residual difficulty evidence;
- atomic-reference/E0 fits;
- objective, configuration-weight, and property-weight records;
- condition/provenance/event/environment/diversity inputs needed by target-subset construction;
- deterministic identities binding those products to the training domain and complete protocol.

No fitted product may inspect held-out CV evaluation, calibration, or locked-test evidence unless an owning specification explicitly gives it a non-training role that preserves the relevant independence boundary.

### Raw versus fitted information

Partition-independent physical facts and raw feature/event providers belong upstream. A fitted normalization, metric, model residual, E0 correction, or difficulty transform belongs to the training domain that fitted it.

This distinction prevents an apparently innocuous global normalization or residual calculation from leaking held-out evidence into subset construction.

## Selection inputs are not a second selector

Representative density, diversity/FPS, environment coverage, condition balance, protected events, difficulty, provenance/correlation structure, and mandatory anchors remain useful scientific information. They do not define an independent DATA7 target order.

DATA7 expresses them as one or more of:

```text
fitted feature coordinates/metrics
hard obligations or applicability masks
representative-density / utility evidence
diversity evidence
event/environment/condition evidence
difficulty evidence
correlation/provenance identities
policy inputs with deterministic identities
```

The one current membership authority consumes these inputs in the target-size chain described in Part V. There is no competing quota/FPS `TrainingSelectionPlan` whose prefixes can disagree with `pi_train`.

### Material/profile specialization

Condition axes and focus groups are declared by the applicable material/profile contract. They may include composition, temperature, pressure, strain, phase, defect, surface/interface state, molecular conformer, preparation history, or other scientifically justified axes.

A profile may define hierarchical applicability rather than a global Cartesian product. Empty or physically inapplicable combinations are not treated as missing observations merely because all axis names exist.

Material-specific semantics remain explicit extensions. Li/Na/K focus groups, ring/cage/site concepts, or LTA-specific condition hierarchies are not generic defaults.

## Training objective, weighting, and exposure

Target membership, target size, loss weighting, and runtime exposure are separate decisions.

`TrainingObjectivePolicy` binds the loss family, energy/force/stress weights, head weights, normalization, robust-loss choices, and missing-label behavior. Configuration/property weighting policies bind condition/regime/event/quality and property-specific weights.

Exposure realization binds the head, eligible use, actual gradient exposures, configuration/property weights, sampling/duplication behavior, seed, and runtime lineage as applicable.

A frame can therefore be selected once, weighted non-uniformly, and exposed according to a qualified loader policy without those three decisions becoming the same authority.

### Atom-group force imbalance

A configuration can contain many more host force components than scientifically critical minority-group components. Subset diversity alone does not eliminate that loss imbalance.

The standard MACE configuration/property-weight path does not claim a generic atomwise group-weighted loss. Evaluation/checkpoint policy therefore reports declared group-resolved metrics and imposes applicable group constraints. A custom atomwise or auxiliary loss defines a different `TrainingProtocolIdentity` and requires separate qualification.

### Exposure backends

The qualified fixed-file MACE path materializes selected target/replay frames in fixed artifacts and binds the realized upstream loader shuffle/batching behavior into the protocol.

Dynamic epoch resampling, multi-job resampling, or alternate final-refit exposure semantics are valid only when a current adapter/specification supports them and records optimizer/checkpoint/exposure lineage. Static files alone cannot claim dynamic resampling.

### Realized exposure audit

Exposure evidence compares intended artifacts and weights with observed loader behavior, including target/replay counts, implicit duplication, expected/observed batches, and configuration/property exposures.

Upstream target/replay duplication behavior is version-dependent. The adapter either disables unintended duplication when supported or binds the realized behavior into the protocol and verifies it. Silent changes in effective target/replay exposure fail closed.

## Statistical dependency boundary

The allowed dependency direction is:

```text
raw source / feature / event evidence
    -> role assignment
    -> training domain
    -> fitted preparation
    -> pi_train prefix target membership
    -> target-size study using authorized development/model-selection evidence
    -> frozen target size and training protocol
    -> checkpoint selection
    -> held-out protocol validation
    -> calibration / locked-test activation
```

Forbidden reverse dependencies include:

- held-out CV error choosing target size;
- locked-test evidence tuning subset policy or checkpoint policy;
- calibration evidence fitting the training protocol it calibrates;
- execution worker/cache/scheduler behavior changing partition membership, fitted domains, target order, or evidence roles.

This dependency boundary is the statistical contract that makes the later model-quality evidence interpretable.

# Part IV - Training, evaluation, and deployment

## Purpose and ownership

This chapter defines the current training-protocol identity, replay boundary, checkpoint admissibility, protocol-matched cross-validation, final training/committee construction, calibration, sealed evaluation, deployment verification, and active-learning lineage.

Target membership and target size are already frozen by the Part V authorities before protocol-validation cross-validation is interpreted. This chapter consumes those decisions; it does not create a second subset or size authority.

## Multi-head replay and complete protocol identity

Multi-head replay fine-tuning trains a shared MACE backbone on target data and a foundation replay dataset with separate output heads. Replay constrains catastrophic forgetting while the target head adapts.

Every scientifically compared run is bound to a complete `TrainingProtocolIdentity` containing, as applicable:

```text
foundation checkpoint / model family / head identity
selected protocol-global target size
domain-local target-membership identity
replay source, split, and replay-monitor identity
training objective and property/configuration weights
target/replay head weights
exposure backend and realized balancing/duplication policy
checkpoint metric and checkpoint-control policy
replay-retention policy
optimizer, LR schedule, epoch cap, stopping policy, and seed policy
model precision and execution backend
MACE adapter/runtime lock
```

Cross-validation evidence validates only the protocol identity it actually used. A change to replay semantics, objective, selected size, membership policy, checkpoint policy, precision/backend, stopping/LR policy, or another protocol-defining field creates a different protocol.

## Separate target and replay evidence

Target and replay evidence retain separate source/label identities, atomic-reference rules where applicable, split/membership plans, weights/exposure accounting, and monitors. Replay training and replay monitoring are disjoint evidence roles.

The mdstats workflow records replay preparation and does not silently acquire external replay data. True-label replay is evaluated against held-out labels; pseudo-label replay, when supported, measures drift from the bound foundation model on an unseen sentinel set.

`ReplayRetentionPolicy` binds the retention metric, baseline, allowed degradation, aggregation, and failure semantics. A checkpoint that violates a mandatory replay-retention requirement is inadmissible even when its target metric improves.

## Common online monitors

Monitoring evidence sets are deterministic protocol inputs with their own policy identities. Their cardinalities are monitor properties, not target-size candidates.

The common target monitor is authorized development/model-selection evidence. It may be used by the target-size study and by the current checkpoint/stopping policy as explicitly specified. It supplies no gradients and is distinct from held-out CV evaluation and locked tests.

The replay monitor is separately owned and separately identified. Numeric equality between a monitor cardinality and one nominal target size has no semantic effect.

## Checkpoint metrics and constrained choice

`CheckpointMetricPolicy` defines the primary target objective and every mandatory target, focus-group/species, condition, energy/stress/property, replay, and physical-integrity constraint applicable to checkpoint admission.

A typical constrained form is

$$
\min_c L_{\mathrm{target\ monitor}}(c)
$$

subject to requirements such as

$$
L_{F,g}(c)\le\delta_g,
\qquad
\Delta L_{\mathrm{replay}}(c)\le\delta_{\mathrm{replay}}.
$$

Exact metrics and thresholds are specification-owned serialized policy. Replay retention, structural integrity, relaxation/deployment integrity, and similar mandatory predicates are constraints rather than score bonuses unless an explicit current policy says otherwise.

Checkpoint selection is deterministic over the complete authorized candidate set and fails closed when no candidate satisfies mandatory constraints.

## MACE adapter and runtime lock

The current MACE adapter binds the upstream behaviors on which the protocol depends, including package/source identity, target/replay head ordering, loader realization, scheduler/stopping behavior, checkpoint retention, precision/backend realization, and accelerator qualification where applicable.

Documentation URLs are not a runtime contract. If version-locked upstream behavior changes materially, preparation or qualification fails closed until the current adapter specification is revised and requalified.

### Minimal Extended XYZ plus sidecar provenance

Extended XYZ contains only MACE-readable labels, weights, and compact stable identities. Long provenance, policy identities, and audit reasons live in sidecar manifests keyed by stable frame/configuration identity.

Target export includes the declared energy channel, forces, authorized stress, configuration/property weights, cell/PBC, atom order, and exact label-domain/E0 provenance. Export precision and round-trip behavior are qualified through the current parser/reader path.

### Explicit E0 realization

An `AtomicReferenceFitRecord` is converted to the exact numerical representation accepted by the current MACE runtime, normally an explicit atomic-number mapping. A provenance record name or path never substitutes for the numerical E0 payload.

### Label-domain boundary

A target bundle contains one compatible target `LabelDomain` and, when replay is enabled, a separately identified replay head/lineage. Incompatible target electronic-structure domains are not silently merged.

## Target-size study versus ordinary stopping

The target-size experiment is a special protocol-comparison control described in Part V. It uses authenticated `n1 -> n2 -> n3` continuation at exact configured boundaries, with a common seed set, and disables ordinary target-success early stopping so candidate sizes reach comparable fidelity boundaries. Where TRAIN2 needs a full deterministic schedule extent, it derives that value from the terminal boundary; it is not a second target-size authority. The separate production maximum `n` is reserved for a fresh selected-size campaign. Hard numerical/scientific failure remains a valid rejection.

Epoch has deliberately different semantics in the two phases. During target-size selection, epoch is a **controlled variable**: the configured coarse, short, and final screens consume only exact `n1`, `n2`, and `n3` checkpoints. An earlier checkpoint is inadmissible even when it scores better, because substituting it would confound target-data size with achieved training fidelity. The public `select-target-size` operation owns this complete restartable `n1 -> n2 -> n3` experiment; generated campaigns default to `(n1,n2,n3)/n = (1,3,10)/30`, with `n` consumed only by fresh post-selection production.

After `N_selected` is frozen, ordinary production/CV training resumes under the frozen protocol. Production checkpoint epoch is then a **selectable model variable**: an earlier admissible checkpoint may be chosen when it is better under the frozen checkpoint-selection policy, even though the configured training horizon remains `n` epochs. Its target-oriented stopping and LR-refinement semantics are part of the shared post-selection method identity; changing them after protocol comparison invalidates the comparison.

The stable TRAIN2 command boundary is therefore `prepare -> preflight -> select-target-size -> cross-validate -> train-production -> verify`. `prepare` owns only the initial screening workload; the two post-selection commands materialize exactly the workload their own authenticated plan authorizes, so there is no separate selected-size `materialize` step.

## Post-selection ownership: method, policies, plans, evidence

Everything downstream of selection is arranged as a strictly acyclic dependency graph, because a policy that authorizes work cannot be defined by that work's results:

```text
current P4 SELECTED authority
  -> current selected-training context
  -> shared post-selection method identity
  -> CV validation policy | final-production policy
  -> CV plan              | final-production plan
  -> fold/final materialization, TRAIN2, EVAL2 evidence
```

The **shared method identity** binds only what cross-validation validates and final production must therefore execute: the preparation/objective recipe, the foundation and initialization family, the optimizer family and its non-role-specific settings, the LR-schedule policy, the checkpoint admissibility and target-only ordering semantics, and the precision/backend lock. It contains no fold membership, no fitted product, no `M3`, and no epoch budget.

The two **role-specific policies** sit beside it. The CV validation policy owns the fold count (`K >= 2`), the partition seed, the fold-construction algorithm identity, the monitor/purge allocation, the CV-only training budget, and the target-only acceptance predicate together with the all-required-fold/all-required-seed aggregation rule. The final-production policy owns `[training].max_num_epochs`, the production seed matrix, and the committee policy. Neither owns the other's fields, which is what makes the invalidation consequences match the accepted DAG: a production horizon edit leaves the selection and the accepted cross-validation evidence current, and a fold-count edit leaves the selection and the production-only policy identity unchanged.

**Plans** below them bind the exact current scientific lineage that policies deliberately exclude. The CV plan binds the current selected binding, the canonical P1 relation authority, the selected-only projected components, the exact per-fold role memberships, and the required run matrix. The final-production plan binds the full `T_selected`, the accepted cross-validation authorization, and the frozen `M3` development lineage. `M3` lives here rather than in the production policy because it is inherited P2/P4 evidence, not an operator setting.

**Evidence** - fitted preparations, materializations, checkpoints, EVAL2 records, acceptance records - descends from a plan and binds it. Corrupt or changed evidence invalidates itself; it never rewrites the plan or policy that authorized it.

Post-selection cross-validation consumes exactly `T_selected` and allocates fold roles over whole P1 split-exclusion components, so a non-separable pair cannot straddle training and evaluation, and a related but unselected frame never enters the universe. Each fold freezes its representative on its own checkpoint monitor under target-only ordering, after mandatory admissibility, and only then evaluates the held-out fold. Replay constrains admissibility and receives no ranking or acceptance credit. Final production is fresh training on the complete `T_selected`: it continues no screening or fold trajectory, and its execution namespace is disjoint from both even when `N` and the numeric seed coincide.

Post-selection descendants are immutable and content-addressed under a campaign-owned root per canonical generation. There is no mutable post-selection current-state authority: a current read re-resolves P4 currentness and then looks only inside that binding's namespace, and publication re-checks the current campaign revision inside the same transaction that would make a pointer current, so work begun under a superseded generation loses the race deterministically.

## Gate TRAIN2B

TRAIN2B executes one authenticated trajectory per `(target size, seed)`. During
screening it durably pauses only at the active exact boundary, then the real
target-size owner ranks outcomes before authorizing survivors to continue.
Continuation preserves model parameters, EMA state, optimizer/LR state, and
Python/NumPy/Torch CPU/CUDA RNG states. `train2_true_replay` remains a bounded
runtime monitor below this scheduler/selection boundary. Restart restores live non-EMA
parameters, EMA state, optimizer/LR state, and RNG ancestry before new work. A run that has passed
its active boundary is invalidated to a fresh coarse screen; it cannot supply
current ranking evidence. Eliminated-size jobs receive no later authorization.

## Protocol-matched cross-validation

Cross-validation validates the **complete already-frozen protocol**, including selected target size. It does not choose target size.

For each fold \(k\):

1. DATA5 provides `fold_training_domain_k`, a disjoint authorized checkpoint monitor, and `held_out_evaluation_fold_k`.
2. DATA6/DATA7 fit descriptors, transforms, metrics, E0, objective/weights, and difficulty evidence only within `fold_training_domain_k`.
3. Post-selection cross-validation folds are drawn from exactly `T_selected` under the protected relations of Part III.
4. The already-frozen protocol-global `N_selected` defines the fold target prefix.
5. A fresh model/optimizer lineage is trained under the bound production stopping/checkpoint policy.
6. Checkpoint choice freezes without inspecting `held_out_evaluation_fold_k`.
7. Only then is the checkpoint evaluated on the held-out fold.

The fold membership is local because each fold has different authorized evidence; the selected cardinality is global because it is part of the one protocol being validated.

If held-out fold performance were used to select `N_selected`, that evidence would no longer be independent protocol validation unless the complete size-selection procedure were nested inside another outer validation design.

## Final training and committee construction

After protocol-matched CV is accepted, final-development fitted products and the final-domain target master order are already governed by the same frozen protocol and selected size. Final seeds are trained independently under that protocol.

Candidate checkpoints are evaluated under the current constrained policy. The selected target heads are exported and a committee is constructed with explicit member/seed/checkpoint identity.

`ProtocolFreezeRecord` binds the final training protocol, selected target-size decision, final-domain target-membership identity, replay/monitor identities, model/checkpoint identities, committee identity, and required upstream evidence.

## Sealed evaluation and deployment

Development artifacts are separated from calibration and sealed-evaluation artifacts. A locked evaluation bundle may exist before activation, but development/training/checkpoint processes cannot inspect it.

Locked-test activation requires the frozen protocol/committee plus every owning-specification promotion predicate. Locked evidence cannot retroactively alter fitted preparation, target membership, target size, stopping/LR policy, checkpoint selection, replay policy, calibration-policy choice, or acquisition policy.

Deployment artifacts are produced only from admitted final target heads with explicit precision/runtime identity. Deployment verification is bounded and uses the frozen downstream-runtime contract. Structural/relaxation failure, NaN/Inf behavior, topology breakage where prohibited, or another mandatory deployment-integrity failure rejects the candidate independently of force-RMSE rank.

## Calibration and uncertainty lineage

Committee disagreement is a ranking signal, not an error guarantee. Numerical uncertainty/acquisition thresholds are calibrated only using predictions of the actual frozen final committee on an authorized calibration cohort.

Calibration identity binds model/committee digests, complete training protocol, target/replay/seed/runtime lineage, precision/backend, calibration cohort, and declared applicability domain.

A transfer decision distinguishes at least:

```text
within_calibrated_domain
rank_only_outside_domain
recalibration_required
rejected_incompatible_domain
```

Without valid final-committee calibration, acquisition is explicitly uncalibrated or rank-only. Locked tests are excluded from calibration and acquisition.

## Active-learning lineage

Selection-biased active-learning labels enter a new development/training candidate pool. Existing frame roles are inherited unchanged by default. Independent new evidence may create new calibration/validation/challenge cohorts only through explicit lineage.

Repartitioning previously classified evidence creates a new evaluation lineage rather than silently rewriting old roles. A new active-learning generation may require re-preparation of fitted products and target membership; this is normal current-generation construction, not compatibility migration of obsolete campaign schemas.

## Reproducibility identity

A reproducible campaign binds, as applicable:

- source/parser and label-domain identities;
- partition/independence roles;
- feature/provider and fitted DATA6/DATA7 product identities;
- the target-size experiment definition, training/evaluation orders, and common preparation identities;
- target-size decision and domain-local target-prefix identities;
- foundation/model/runtime lock;
- replay and monitor identities;
- objective, weights, exposure realization;
- optimizer/LR/stopping/seed policy;
- checkpoint metrics/admission decision;
- committee/protocol freeze;
- calibration and locked-test activation evidence;
- output/deployment checksums.

Execution-only worker counts, queue completion order, cache paths, file-backing choice, and similar non-semantic settings are excluded unless a current specification explicitly declares otherwise.

## Failure semantics

The workflow fails closed when, among other current-specification conditions:

- source/label identity is unresolved or incompatible;
- required strain/reference conventions are ambiguous;
- requested evidence roles are infeasible under the declared independence policy;
- held-out, calibration, or locked evidence reaches a forbidden fitted/subset/size/checkpoint operation;
- a fold held-out evaluation controls checkpoint choice or target size;
- compared CV and final runs do not share the claimed complete protocol identity;
- runtime behavior differs materially from its qualified lock;
- realized target/replay exposure differs from accepted protocol;
- no checkpoint satisfies mandatory target/focus/replay/integrity constraints;
- calibrated acquisition is attempted outside its applicability domain without the declared transfer action;
- active-learning lineage silently rewrites prior evidence roles.

Absent rare events, replicas, condition combinations, calibration cohorts, or challenge sets are reported as limitations/coverage gaps rather than fabricated evidence.

# Part V - Target-size selection and post-selection validation

## Purpose and ownership

This chapter defines how the campaign decides **how much labelled data a training method needs**, and how that decision is validated afterwards without contaminating it.

The current chain is:

```text
canonical frame authority (Part II)
    -> neutral statistical substrate (Part III)
    -> one P_train / M3 target-size development split
    -> one canonical training order pi_train
    -> one canonical evaluation order pi_eval with nested M1 subset M2 subset M3
    -> one common deterministic target-size preparation
    -> paired optimizer-seed screen over candidate sizes
    -> one target-size reducer
    -> N_selected and T_selected = pi_train[:N_selected]
    -> post-selection cross-validation on exactly T_selected
    -> fresh final production on the complete T_selected
    -> currentness-fenced publication
```

Each element has exactly one owner. The reducer is the only authority that may declare a selected size; `CampaignStore` is the only authority that holds the current selected set; post-selection cross-validation is the only authority that accepts or rejects the training *method*; and final production is the only authority that publishes a production model.

There is no alternate selection path. The retired per-domain multi-view chain (compatibility-domain role freezes, full-pool feasibility, exact sparse neighborhood indices, progressive multi-view ordering, repaired master orders, continuation-state families, and independent prefix qualification) is not a current architecture, is not migrated, and is not reachable from any current runtime owner. Workspaces holding that derived state are rejected with an actionable destructive-reset requirement rather than translated; see Part VII.

## Why target size is decided by a screen, not by coverage

The scientific question is empirical: *at what training-set cardinality does the accepted training method stop improving materially on a representative held-in evaluation population?* That is a property of the method, the data distribution, and the optimizer - not of a geometric covering argument over descriptor neighborhoods.

Four principles control the design:

1. one deterministic training order, so candidate sizes are exact nested prefixes and size comparisons are never confounded by resampling;
2. one common preparation shared by every candidate size and optimizer seed, so preparation cannot become a hidden per-size variable;
3. only the ordered optimizer-seed set is the stochastic replicate dimension of the screen;
4. the decision consumes target-side metric evidence alone, and downstream replay, cross-validation, physical, or deployment evidence can never rank or tie-break a size.

## The development split and the two canonical orders

The neutral statistical substrate supplies protected relations - duplicate groups, correlation families, and split exclusions - before any target-size object exists. From it the architecture derives exactly one split:

```text
eligible labelled frames -> P_train (target-training pool) + M3 (evaluation pool)
```

`P_train` is ordered once into `pi_train`. A candidate of nominal size `N` is the exact prefix

$$
T_N = \pi_{\text{train}}[:N].
$$

`M3` is ordered once into `pi_eval`, and the evaluation ladder is the nested family

$$
M_1 \subset M_2 \subset M_3,
$$

taken as direct prefixes of `pi_eval`. Rungs are direct populations, never complements of one another: a rung is evaluated on exactly the frames it names.

Both orders are deterministic functions of the canonical frame authority, the neutral substrate, and the configured target-size policy. Neither depends on any compatibility grouping, label-domain identity, or cross-validation plan.

## The common preparation

One `TargetSizeCommonPreparation` identity is frozen before any candidate trajectory starts. It derives from `P_train` and the configured foundation/training protocol, and it is shared unchanged by every candidate size and every optimizer seed.

It MUST NOT derive from `M1`, `M2`, `M3`, held-out evidence, calibration evidence, locked evidence, or any cross-validation plan. A change to the common preparation is a change to the target-size scientific identity and produces a new generation rather than an in-place edit.

## The paired optimizer-seed screen

For every candidate size `N`, the screen runs the same ordered optimizer-seed set - by current policy the two seeds `[1, 2]` - through the same fidelity ladder:

```text
n1 / M1  ->  n2 / M2  ->  n3 / M3
```

Fidelity boundaries are continuation points, not restarts: model, optimizer, and RNG state continue exactly across `n1 -> n2 -> n3`. Ordinary early stopping may not truncate a required screen boundary, and the seed set is identical at every `N` so a size comparison is never a seed comparison.

Candidate rungs execute through the accepted TRAIN2 runtime and are evaluated through the accepted EVAL2 owners. Expensive numerical training has exactly one substitution seam, strictly below the mdstats owner boundary; configuration resolution, authority construction, materialization, provider and checkpoint authentication, publication, reconciliation, and adoption are production code in every invocation.

## The reducer and the terminal decision

One reducer consumes the screen evidence and advances the experiment. Its outcome is one of:

- **selected** - a size `N_selected` is frozen together with the exact membership `T_selected = pi_train[:N_selected]`;
- **typed scientific terminal failure** - the configured candidate ceiling did not converge, too few candidates qualified, or the surviving candidates were not comparable.

A configured-ceiling nonconvergence is a typed result, not an invitation to invent a rescue size outside the configured ladder.

Ranking is owned by the target-side metric and practical-equivalence policy alone. Inside the practical-equivalence band the **smaller** `N` is preferred, because the scientific question is the smallest sufficient training-set size.

## Currentness and the selected set

`CampaignStore` holds one canonical target-size generation. Its durable regimes are `legacy`, `transitioning`, and `current`; only `current` executes target-size work. Every mutation is one compare-and-set transition against the exact predecessor revision, so an interrupted operation is owned by the persisted transition rather than by the process that began it.

The terminal projection binds `N_selected` and the exact `T_selected` membership digest together; neither may be edited independently, and a reload re-derives the projection from the authenticated reducer state and training order rather than trusting the stored copy. Terminal currentness is always established from the current store revision, never from a caller-supplied snapshot, and a public terminal view is re-authenticated at exposure time so a stale object cannot be published after the store advances.

## Invalidation scope

A change to target-size scientific identity - source or frame membership, canonical numerical labels or their interpretation policy, the candidate ladder or configured ceiling, the evaluation-size ladder, fidelity boundaries, the ordered optimizer-seed set, the training-order policy, the `P_train`/`M3` split or `pi_eval` ordering policy, the common preparation, the metric/practical-equivalence policy, or the foundation/replay identity where it is part of the experiment - replaces the generation. The old selected set stays readable as history and can never re-enter current authority.

Changes that are *not* target-size identity invalidate only their own descendants:

- advisory provenance grouping or report presentation invalidates only the advisory evidence that depends on it, and never the frame UID, the canonical label identity, the neutral partition, or the target-size result;
- cross-validation-only settings such as fold count and partition seed invalidate cross-validation and its descendants, and leave `N_selected`/`T_selected` byte-identical;
- production-only budget or runtime policy invalidates only final-production descendants.

## Post-selection cross-validation

Cross-validation starts only after the terminal selection is frozen, and it consumes exactly `T_selected` - complete coverage, no unselected sibling frame, no held-out outer frame.

It validates the **training method**, not the size:

- the configured fold count `K >= 2` and every required fold of every required CV seed must pass the configured target-only acceptance predicate; there is no mean, majority, best-seed, partial, `K = 0` or `K = 1` authorization;
- the full P1 split-exclusion and correlation-family constraints continue to hold inside fold assignment;
- fold-local preparation, training, checkpoint selection, and replay admissibility may never see that fold's held-out outer target set, and the fold representative freezes before held-out outer evaluation;
- replay training exposure and the TRUE_DFT replay admissibility monitor remain distinct concerns, and TRUE_DFT replay contributes no ranking, tie-break, fold, or seed credit;
- a cross-validation failure is a methodological result: `N_selected` and its evidence are unchanged, and final production is simply not authorized. If cross-validation shows that a materially different training method is required, that changed method needs a **new** target-size experiment, because the method whose convergence was measured has changed.

Supported training modes remain exactly `scratch`, `naive_fine_tuning`, and `multihead_replay`; the canonical post-selection heads remain `target_head` and `pt_head`; and the foundation checkpoint head remains a separate foundation-owned concept. Method, foundation, replay, and content identity all fail closed.

## Fresh final production

Final production starts fresh from the accepted foundation/initialization with fresh optimizer, RNG, and run state. It trains on the complete exact `T_selected`, under the cross-validation-accepted method, for the configured `[training].max_num_epochs` - an independent production horizon that is deliberately unrelated to the screen's `n3`.

Frozen `M3` evidence may remain development/model-selection evidence. Final authorization and publication remain currentness-fenced and restart-authenticatable: a reopened campaign reauthenticates the selected binding, the cross-validation acceptance, and the final publication identity before exposing any of them as current.

## Public command surface

The current lifecycle is exactly:

```text
doctor -> prepare -> select-target-size -> cross-validate -> train-production
```

`prepare` reconstructs the current substrate and cannot select a size. `select-target-size` is the only command that trains candidates and decides `N`. `cross-validate` is the only command that accepts the method. `train-production` is the only command that publishes a fresh production model. `status` and `advance` project this lifecycle from the owning authorities rather than from stage markers.

# Part VI - Bounded execution, restart, and performance architecture

## Purpose and authority

Execution optimization is acceptable only when it preserves the scientific/statistical authorities defined in Parts I-V and improves measured throughput, memory behavior, storage behavior, or restart cost. Utilization is diagnostic; scientific digests, exact decision traces, and authoritative records decide correctness.

Worker count, queue depth, query-block size, cache location, file-backing threshold, storage path, and similar execution choices do not enter scientific identity unless a current specification explicitly makes them part of the scientific algorithm.

The central rule is:

> change how exact work is scheduled or represented, not what scientific evidence is consumed or what authoritative decision is produced.

## Work/span and single-level parallelism

For serial work \(T_1\), critical path \(T_\infty\), and \(P\) admitted CPU lanes,

$$
T_P\ge\max\!\left(\frac{T_1}{P},T_\infty\right).
$$

Independent work is exposed at the highest useful level. Nested numerical parallelism is suppressed while outer work can fill the resource budget:

$$
P_{\mathrm{outer}}P_{\mathrm{native}}\le P_{\mathrm{budget}}.
$$

For native kernels such as cKDTree, BLAS, or OpenMP, a campaign resource scope owns native-thread admission. Individual workers do not independently oversubscribe the machine.

## DATA6-to-DATA8 materialization boundary

DATA6 is the last preparation stage that owns the MACE accelerator model. After its final descriptor/prediction consumer, production explicitly releases calculator/model references and unused CUDA allocator state. DATA7/DATA8 are CPU/I/O stages and advertise no GPU jobs. Heavy frame-cache restoration and foundation-energy reconstruction remain lazy until a materialization variant actually misses the completed-artifact reuse path.

DATA7 exposes canonical final/fold domains as the outer parallel unit. Each domain retains independent fitted scaler, PCA, E0, weighting, selection, and coverage state. Immutable frame arrays and authenticated descriptor shards may be shared, but task-local mutable extraction state is not shared between concurrent domains. Outer DATA7 work is admitted through the deterministic resource queue using the live runtime CPU budget and a conservative peak incremental-memory estimate; inner BLAS/OpenMP/PyTorch widths are one while multiple domains are available. Workers publish authenticated immutable DATA7 cache generations and return compact receipts. Only the coordinator mutates production records/checkpoints, in canonical domain order.

Target-size screening is treated as a distinct reuse topology. Candidate rungs are exact prefixes of the one canonical training order, so a rung is a *view* of one authority rather than an independently prepared dataset. The one common target-size preparation is shared unchanged by every candidate size and optimizer seed, and evaluation rungs are direct `M1/M2/M3` populations that cannot shrink across `n1/n2/n3` continuation.

The expensive DATA7 fitted metric/E0/weight core is selection-size invariant, so target-size variants may reuse that core through a reconstructible execution-only index to a fully authenticated DATA7 carrier artifact. The fitted-core index authenticates both the execution recipe and the actual fitted-result digest; publication is create-once/validate-winner, and divergent results for one recipe fail closed. A stale carrier that fails the exact foundation-prediction/reference/lineage reuse contract is discarded and refit rather than promoted to a scientific failure. Reuse admission uses a separate conservative RAM estimate for carrier load, selection/coverage realization, and archive output instead of charging the hypothetical full fit. Size-specific selection and coverage are then realized normally, and the resulting full `Data7PreparationBundle` remains the sole scientific authority. Full shared DATA7 publication likewise requires any concurrently computed winner to match the local bundle digest and deterministic archive SHA. The shared full-artifact recipe is v2 and excludes DATA8-only evaluation membership/target-study outcome state while retaining the exact prescribed training prefix and selection policy. Legacy full-artifact v1 recipes remain read-compatible; reconstructible fitted-core v1 indices are cache misses.

DATA8 separates immutable fixed-file production from production-tree assembly. Unique ExtXYZ cache misses are enumerated first, then balanced across fresh CPU-only interpreter batches when the estimated byte volume is large enough to amortize fresh-interpreter startup; small batches remain on the serial producer. The large read-only context is serialized once with mmap/file references; worker messages carry compact context paths and recipe digests rather than dense arrays. Fixed-file cache generations use atomic publish-or-validate-winner semantics. CPU, RAM, task count, configured free-disk reserve, and both estimated and measured worker-context spill bound concurrency; insufficient transient headroom reduces execution to the serial producer before subprocess launch. After cache population, the production tree, YAML, scripts, protocol identities, tree digest, and promotion are assembled canonically in the parent process.

Externally owned foundation, selected-head, and replay inputs cross an authenticated inode-independent copy boundary into mdstats-owned content-addressed snapshots before reuse. Hardlinking is reserved for mdstats-owned immutable snapshots/cache generations and their consumers. Optimizer-invariant weighted replay and MLCV TRUE_DFT replay-light realizations are content-addressed execution caches, so seed variants do not repeat identical corpus transformations/scans. Shared DATA7/DATA8 caches are reconstructible execution state. Cache layout, worker count, batch assignment, and completion order do not enter scientific identity. Legacy DATA7 flat cache generations and PAR1 lexically ordered checkpoint digests remain read-compatible; current writes use atomically installed content-addressed generations and canonical `plan.domains` checkpoint order.

## Deterministic resource-bounded work queue

CPU-heavy independent tasks use a shared deterministic queue abstraction with explicit CPU and memory ownership. Its architectural responsibilities are:

- bound executing, ready, in-flight, and buffered work;
- reserve persistent memory before admitting temporaries;
- propagate deterministic task identities and exceptions;
- allow arbitrary completion order where scientific order is irrelevant;
- restore canonical reduction/commit order where FP64 arithmetic or record order is authoritative;
- expose progress/resource telemetry without placing telemetry in scientific identity.

Task submission may run ahead of execution to hide hand-off latency, but simultaneous execution remains bounded by the declared resource scope.

## One product-scale authority per semantic input

The candidate ladder does not permit one full descriptor/graph/preparation copy per rung. The product-scale execution model is:

```text
one canonical frame/feature authority
one neutral statistical substrate
one P_train / M3 split and one pi_train / pi_eval ordering
one common target-size preparation shared by every size and seed
prefix views for candidate rungs
training artifacts only for candidates still authorized by the reducer
```

This is an architectural resource invariant, not merely an optimization preference. A realization whose memory or storage scales with one independent copy of the target-selection state per candidate size is non-conforming even if it eventually produces the same scientific result.

## Candidate execution and continuation

The screen executes one `(candidate size, optimizer seed)` cell at a time through the accepted TRAIN2 runtime, under the campaign resource scope that owns CPU, RAM, VRAM, disk, and native-thread admission. Cells that already completed are not re-executed on restart: the persisted execution head is reconciled before anything new is scheduled, and the reconciled head is adopted by compare-and-set.

Continuation across a fidelity boundary restores exact model, optimizer, and RNG state rather than restarting the run. Checkpoint publication is atomic and content-addressed, so an interrupted boundary either published a complete checkpoint or did not publish at all.

Execution choices - worker count, batch assignment, queue depth, cache location, completion order - are reconstructible realization details and never enter scientific identity.

## Provider lifetime and accelerator ownership

Model providers are acquired and retired in explicit non-overlapping scopes so a second provider is never constructed while the first still owns accelerator memory:

```text
candidate provider acquire -> target EVAL2 -> candidate TRUE_DFT replay when applicable
  -> candidate close in an exception-safe finally
  -> only then foundation provider construction -> foundation TRUE_DFT replay
  -> foundation close in an exception-safe finally

outer representative provider acquire -> held-out outer EVAL2
  -> outer close in an exception-safe finally
```

Provider retirement is owned by these scopes. Garbage-collection timing, a live provider cache, or ad hoc allocator cleanup are not substitutes, and an evaluation exception still closes the provider it opened.

## Target-size funnel materialization

The configurable `n1/n2/n3` size study materializes training state only for candidates still authorized by the production funnel:

```text
qualified population
  -> coarse (`n1`) candidates
  -> at most four short (`n2`) continuations
  -> two final-screen (`n3`) continuations
  -> one selected size or typed failure
```

Continuation authenticates model, optimizer, RNG, and protocol parentage. Eliminated candidates are not trained further in ordinary production.

Exhaustive training of the full candidate population to final fidelity is release/algorithm qualification only and must use a bounded dedicated qualification design. It is not permitted to become an unbounded default campaign artifact generator.

## Replay indexing and bounded parsing

The selected replay source remains external scientific authority. A replay source index may store authenticated source-byte identity, frame offsets/lengths, atom counts, and source-order geometry identity to permit sparse monitor access and bounded chunk parsing.

The index is reconstructible execution state. It cannot replace replay source, split, label, prediction, monitor, or retention authority. Source mutation or index corruption causes safe reconstruction.

Parser concurrency is introduced only when measurement on representative workload shows benefit and exact persisted replay bytes/identities are preserved.

## Training, evaluation, and verification concurrency

Independent training, checkpoint-evaluation, and deployment-verification jobs may execute concurrently under common CPU/RAM/GPU/VRAM admission where their owning policies permit concurrency.

Runtime concurrency never enters the scientific checkpoint score or admissibility policy. Hard GPU/VRAM or RAM limits fail closed rather than silently switching precision/backend, shrinking scientific evidence, or changing model policy.

Positive accelerator qualification is evidence. The architecture does not assume an accelerator path is correct merely because it is available.

### Canonical staged checkpoint evaluation and target-size reuse

OPT-EVAL4 owns checkpoint-evaluation execution as a bounded CPU-prepare -> accelerator -> CPU-finalize pipeline. TARGET-SIZE-V5 exact-boundary EVAL2 uses this same scheduler rather than a private checkpoint loop. The target-size parent enumerates and authenticates scientific endpoint authority, the staged workers perform computational preparation/inference/finalization, and the parent validates returned run/checkpoint/target-role/prediction/metric identities before any durable endpoint publication. Cache-only and freshly computed endpoints converge through that same parent validation path, and the target-size reducer cannot run until the complete expected `(size, seed)` population has authenticated terminal evidence in deterministic order.

One compatible target role may expose a stage-resident immutable target context. Reuse is content-addressed for computation but never substitutes byte identity for scientific authority: every contributing artifact lineage is authenticated against the role and exact frame-UID sequence. The stage RAM ledger charges shared target atoms/evaluation views once; per-endpoint admission charges only incremental prepared state. Downstream mutation requires a private copy rather than mutating the shared context.

The accelerator stage retains one resource owner. A TARGET-SIZE-V5 population may serially reuse one worker-private MACE provider/model shell when checkpoint bytes authenticate and exact model class/state key/shape/dtype plus runtime-architecture policy prove weight replacement compatible. Foundation-model providers, CuEq/OEq transforms, compiled providers, structural incompatibility, or other unqualified shells rebuild normally. Corruption or authority mismatch remains fatal rather than falling back. Weight-dependent calculator/descriptor state is invalidated on replacement; geometry graph caches remain separately governed by geometry/policy identity.

Static-inference calibration is execution state, not scientific model identity. A calibrated runtime profile may be reused across checkpoint weights only when the provider exposes the same authenticated weight-independent runtime-architecture digest and the exact authenticated geometry workload, device, dtype, head, acceleration/precision policy, and relevant hardware identity match. Without stable geometry identities, compatibility remains checkpoint-exact. Every use still applies live RAM/VRAM clamping and existing OOM/backoff policy.

Cancellation stops new staged admission and is polled at safe preparation/materialization/inference/finalization boundaries. Owned legacy checkpoint-reconstruction subprocesses are monitored so cancellation or timeout terminates the owned process group and cleans attempt-local staging without publishing partial scientific state. Already authenticated terminal evidence remains restartable.

## Memory and storage budget

Long stages account for persistent and transient memory:

$$
M_{\mathrm{stage}}=
M_{\mathrm{persistent}}+M_{\mathrm{inflight}}+M_{\mathrm{buffered}}+
M_{\mathrm{sparse}}+M_{\mathrm{result}}+M_{\mathrm{scratch}}.
$$

New work is admitted only when its CPU and memory reservations fit the stage budget. Large reconstructible arrays may use mmap-compatible/file-backed persistence to lower peak RSS or restart cost.

Every persistent cache authenticates its semantic inputs and payload independently. Corrupt/stale reconstructible caches are rebuild events; they are not silently accepted and are not scientific evidence unless another current contract explicitly defines them as such.

Scratch-space admission is part of bounded execution. A stage that can create product-scale temporary files must predict and cap scratch use before production work begins.

## GPU/VRAM admission

GPU jobs are admitted against explicit free-memory and configured-budget evidence. Calibration/measurement windows and utilization estimators are runtime policy owned by the current execution specifications, not by release chronology in this manual.

Soft GPU-utilization and fractional-VRAM envelopes regulate additional concurrency above a serial floor. A successfully completed one-job CUDA calibration is direct evidence that serial execution of the applicable job/resource profile is viable, so measured demand above a soft envelope caps additional concurrency at one (serial fallback) instead of proving the queue infeasible; only actual execution failure or genuine device/resource unavailability may terminate queued work. Absence of preflight GPU telemetry selects conservative serial execution without parallel expansion evidence, rather than blocking the first execution attempt when the CUDA device is available.

An execution controller may reduce job concurrency after measured resource pressure. It cannot change the scientific batch/exposure semantics, precision policy, checkpoint evidence, or target/replay membership merely to fit memory unless the owning scientific specification explicitly permits that change.

Adaptive OOM recovery is acceptable only when the recovered execution is protocol-equivalent and the changed execution parameter is non-semantic.

## NUMA-ready locality

A flat queue is appropriate when locality is not limiting. Multi-socket systems may add node-local queues/shards, worker affinity, local stealing first, and cross-node stealing to avoid idle lanes.

NUMA policy is an execution extension. It is activated only after measurement and cannot alter scientific identity, canonical reduction order, or data partition/evidence roles.

## Vectorization and allocation discipline

Performance-critical implementations should avoid:

- repeated linear searches and immutable-map reconstruction;
- repeated full-array scaling when a fitted/scaled authority can be reused;
- unnecessary concatenation or Python-object materialization where typed arrays suffice;
- repeated per-frame/per-species masks that can be safely cached;
- full candidate rescans when exact sparse/local updates suffice;
- duplicate descriptor/graph/materialization per target-size rung.

Useful exact kernels include offset-derived ragged CSR gathers, bounded integer indexed counting/reduction, epoch/stamp arrays, preallocated typed outputs, and cached static reduction metadata.

Optimization reviews must distinguish arithmetic preparation from authoritative arithmetic order. Reordering memory accesses or batching independent work is acceptable only when the authoritative records satisfy the required exact/tolerance contract.

## Progress and observability

Every long-running stage exposes both scientific progress and resource/executor state. At minimum:

1. completed/total work and percent where meaningful;
2. elapsed and ETA when estimable;
3. throughput with an explicit stable unit;
4. active/pending/buffered work or equivalent scheduler state;
5. resource pressure or current hot item when relevant.

A heartbeat is emitted during long periods without task completion. ETA is based on globally committed work.

User-facing MLFF elapsed and known ETA use fixed `HH:MM:SS` formatting; unavailable ETA is `--:--:--`. Presentation state never enters scientific digests or cache identity.

## Performance qualification

A performance change is reviewed against representative target-scale work. Evidence records, as applicable:

- wall and CPU time;
- throughput and measured occupancy/utilization;
- peak RSS/VRAM and scratch/persisted bytes;
- queue occupancy/backpressure;
- output/content digests;
- exact scientific-record equality or the explicitly declared tolerance contract.

Sequential-authority algorithms are checked at sufficient state granularity to detect drift—for example the canonical training/evaluation orders, the common-preparation identity, and the reducer state transitions.

Detailed before/after measurements, failed optimization experiments, release qualification results, and chronology belong in benchmarks/audits/history rather than the current architecture.

# Part VII - Ownership and extension boundaries

## One-generation authority model

The current MLFF workflow has one semantic generation. A record, policy, or artifact is either compatible with that generation or unsupported. Historical selector, repair, migration, and campaign-generation formats do not form alternate current execution paths.

Architecture owns durable structure and scientific/algorithmic invariants. Narrow specifications own exact schemas, policy values, numerical tolerances, failure codes, and module-local runtime behavior. Workplans coordinate proposed transitions and never become product authority merely because an implementation follows them.

The core authority chain is:

```text
source evidence and labels
    -> eligibility / conditions / evidence roles
    -> fold- or final-training domain
    -> DATA7 fitted selection inputs
    -> P_train / M3 target-size development split
    -> canonical training order pi_train and evaluation ladder M1 subset M2 subset M3
    -> one common target-size preparation
    -> paired optimizer-seed screen
    -> target-size reducer
    -> N_selected and T_selected
    -> post-selection cross-validation on exactly T_selected
    -> fresh final production on the complete T_selected
    -> currentness-fenced publication
```

There is no branch from this graph to a retired per-domain multi-view selection
chain, a generated-size rescue, or a second membership selector. Retired derived
target-size state is rejected with an actionable destructive reset requirement
rather than migrated.

## Scientific decision ownership

| Decision or product | Sole current owner | Consumes | Emits | Explicitly does not own |
|---|---|---|---|---|
| source/label identity | DATA2-family source and label contracts | immutable source material | normalized labeled-record identity | partition, selection, training |
| conditions/eligibility | DATA3-family contracts | source records | eligible frames and physical conditions | evidence-role assignment |
| raw features/events | DATA4-family contracts | eligible evidence, profile/provider declarations | partition-independent raw evidence | fitted metrics or target membership |
| evidence roles and fold domains | DATA5 partition contracts | cohorts, independence evidence, purge rules | development/monitor/CV/calibration/test roles and authorized training domains | target ranking |
| descriptors/difficulty inputs | DATA6 contracts | authorized domain evidence, frozen foundation model where applicable | raw/blinded descriptor and prediction products | target membership |
| fitted selection inputs | DATA7 contracts | one authorized fold/final training domain | fitted transforms/metrics, E0 fits, objective/weights, difficulty and condition/provenance inputs | target-membership order or target size |
| target-size development split | target-size experiment definition | canonical frame authority, neutral substrate, target-size policy | one `P_train`/`M3` split | training order, size choice |
| canonical training order | `pi_train` owner | the split plus the configured training-order policy | one deterministic order whose prefixes are candidate subsets | evaluation populations, size choice |
| canonical evaluation ladder | `pi_eval` owner | the split plus the configured evaluation-order policy | nested direct populations `M1 subset M2 subset M3` | training membership, size choice |
| common target-size preparation | `TargetSizeCommonPreparation` | `P_train` and the frozen foundation/training protocol | one preparation identity shared by every size and seed | any per-size or per-seed variation |
| scientific target size | the one target-size reducer | paired optimizer-seed screen evidence at matched fidelity | typed terminal outcome: `N_selected` or typed scientific failure | monitor cardinalities, held-out CV evaluation, locked tests |
| current selected set | `CampaignStore` terminal projection | authenticated reducer state and training order | `N_selected` bound to the exact `T_selected` membership digest | re-deciding the size, post-selection acceptance |
| post-selection method acceptance | post-selection cross-validation owner | exactly `T_selected`, protected relations, configured `K >= 2` and CV seeds | all-required-fold target-only acceptance verdict | choosing or changing `N_selected` |
| fresh final production | final-production owner | the accepted method and the complete exact `T_selected` | published production run under `[training].max_num_epochs` | target-size or CV authority |
| target online monitor | `OnlineTargetMonitorPolicy` | DATA5-authorized monitor domain | deterministic common target monitor | target-size population |
| replay monitor | `ReplayMonitorPolicy` | authorized replay evidence | deterministic replay monitor | target-size population |
| training/checkpoint selection | current training/checkpoint specifications | frozen protocol, selected domain-local target prefix, replay, monitors | selected checkpoints and complete evidence | held-out fold as checkpoint controller |
| protocol validation | DATA5/CV + evaluation specifications | frozen protocol and held-out folds | out-of-fold protocol evidence | target-size selection |
| deployment/committee | deployment specifications | admissible final checkpoints, frozen protocol | deployment artifacts and committee identity | post-hoc policy changes |
| uncertainty calibration | calibration owner | predictions from the actual final committee and authorized calibration role | applicability/calibration evidence | refitting the frozen training protocol |
| locked-test activation | activation/evaluation owner | frozen protocol/committee plus explicit activation | locked-test evidence | training, selection, checkpointing, calibration-policy choice |

A narrow specification may refine how its row is realized, but it cannot create a second semantic owner for the decision.

## DATA7 boundary: fitted preparation, not membership

DATA7 is the last fitted-preparation authority before multi-view subset construction. For each authorized fold/final training domain it may fit and publish:

- heterogeneous feature transforms and metrics;
- atomic-reference/E0 fits where applicable;
- training objective and configuration/property weight records;
- training-domain difficulty evidence;
- condition, provenance, event, environment, and diversity inputs needed by subset construction;
- immutable identities linking those products to the domain and protocol.

DATA7 does **not** publish an independent quota/FPS membership decision, a second target-membership ladder, or a target-size decision. Representative coverage, diversity/FPS, environment coverage, protected events, difficulty, and condition balance are expressed as inputs to the one canonical training order.

After the target size is frozen, post-selection materialization consumes exactly `T_selected = pi_train[:N_selected]`. A `TrainingSelectionPlan` used to record that materialization is a consumer record, not an independent selector.

This boundary prevents two selectors from producing incompatible notions of the target set while preserving the useful fitted/statistical information accumulated in DATA7.

## Target-size authority

### Distinct size concepts

Let \(N_{\mathrm{available}}=|P_{\mathrm{train}}|\) be the size of the target-training pool. The candidate ladder is configured, not frozen in schema: a contiguous power range with an explicit configured ceiling,

$$
\mathcal N_0=\{2^{p}: p_{\min}\le p\le p_{\max}\}.
$$

The materializable population is

$$
\mathcal N_M=\{N\in\mathcal N_0: N\le N_{\mathrm{available}}\},
$$

and the qualified population \(\mathcal Q\subseteq\mathcal N_M\) is the subset admitted by the configured target-size policy for the current experiment definition. The selected size must satisfy \(N_{\mathrm{selected}}\in\mathcal Q\).

`N_available`, a monitor cardinality, a replay cardinality, or an implementation batch/budget count can never become `N_selected` through numeric coincidence. There is no hidden scientific ceiling: the ladder and its ceiling are configuration.

### One membership, one protocol-global size

Every candidate is an exact prefix of the one canonical training order,

$$
T_N=\pi_{\mathrm{train}}[:N],
$$

so frame membership is a global property of the experiment rather than a per-domain construction. `N_selected` is one protocol hyperparameter, and the exact membership `T_selected` is frozen with it. Post-selection cross-validation validates the training method on that already-frozen set; held-out fold performance does not choose it.

Because all candidates are prefixes of one order, increasing `N` only adds frames. A qualification predicate evaluated on those prefixes therefore cannot regress solely because `N` grows, and a pass/fail/pass sequence is an invariant violation that must fail closed.

## Target-size screen

The reducer is the sole scientific target-size owner. It consumes only authorized target-side development/model-selection evidence. Replay semantics and monitor identity may remain bound through the frozen training protocol, but replay metric values are diagnostics and cannot rank, qualify, reject, or tie-break target sizes. Post-selection cross-validation folds and locked tests remain unavailable to the size decision.

### Exact fidelity continuation

Each candidate follows one authenticated continuation trajectory:

```text
foundation -> n1 / M1 -> n2 / M2 -> n3 / M3
```

Each boundary authenticates the exact model/optimizer/RNG parent of its predecessor. `0 < n1 < n2 < n3` are the screening boundaries, while fresh production uses an independent positive `[training].max_num_epochs` with no required ordering against `n3`. Candidates share the same foundation, replay semantics, objective, optimizer/LR schedule, exposure policy, precision/backend, common preparation, and ordered seed set. That seed set comes from the `seeds` field of the sole enabled training method; current generated campaigns default it to `[1, 2]`. The target-size policy serializes the ordered set and does not invent a second seed convention.

At every boundary the endpoint itself is authoritative: `S(N,n1)`, `S(N,n2)`, and `S(N,n3)` are evaluated at matched fidelity on the direct rung population `M1`, `M2`, `M3`. A better earlier checkpoint cannot replace the prescribed endpoint. This is distinct from post-selection production checkpoint selection, where `N_selected` is fixed and the checkpoint epoch may be optimized over the admissible trajectory.

Ordinary target-success early stopping is disabled during the size experiment because candidates must reach comparable fidelity boundaries. Every expected candidate/seed produces exactly one stage outcome: strict successful endpoint evidence, or explicit authenticated candidate-specific numerical/scientific failure evidence. Generic execution/resource/input/schema/lineage failures remain campaign errors. Normal production stopping resumes after the target size is frozen.

### Public orchestration boundary

The campaign CLI is a projection of existing scientific/execution authorities, not an additional persistent lifecycle authority. Its stable lifecycle is:

```text
doctor -> prepare -> select-target-size -> cross-validate -> train-production
```

`prepare` reconstructs the current substrate and cannot select a size, train a candidate, run the reducer, or rank anything. `select-target-size` is the sole public owner of the restartable `n1/n2/n3` controlled-fidelity loop.

Once `N_selected` is frozen, `cross-validate` and `train-production` are the two public post-selection owners. Both re-establish the current selection through the canonical terminal loader in the same invocation, so neither a caller-held object nor a persisted descendant is ever current authority. `cross-validate` owns the complete selected-only K-fold plan and the target-only acceptance verdict; `train-production` owns fresh full-`T_selected` training under the method that verdict accepted. Each materializes exactly the workload its own plan authorizes, so there is no separate `materialize` step and no second preflight boundary. `status` and `advance` derive the lifecycle from those same owners and never write a second scientific state machine.

### Successive-fidelity funnel

Let \(q=|\mathcal Q|\). Fewer than three qualified sizes is a typed failure. Otherwise the production funnel is:

```text
q >= 3
  n1 / M1: q -> min(q,4)
  n2 / M2: <=4 -> 2
  n3 / M3: 2 -> 1
```

All candidates use the same authenticated ordered training-seed set, and comparisons aggregate paired seed evidence rather than unrelated stochastic realizations. Missing, duplicated, reordered, or candidate-specific seed populations invalidate the state.

At `n1` and `n2`, the configurable coarse practical-equivalence width defaults to 1 meV/Angstrom in the primary target-force metric, and candidates inside that band prefer the smaller size. The independently configurable final width also defaults to 1 meV/Angstrom for `n3` ranking and configured-ceiling material superiority. Both positive finite values are policy-identity fields, not frozen schema constants. Early screens need not satisfy the final absolute force-accuracy threshold.

At `n3`, the two finalists are ranked only by the target-side metric under the frozen practical-equivalence rule. Target-threshold, replay, physical-integrity, relaxation, deployment, and other model/protocol acceptance evidence is downstream of the immutable size choice. Only complete paired successful candidates are rankable; authenticated trajectory failures remain explicit evidence and replay scores cannot affect ranking or tie-breaking.

### Typed terminal outcomes

The target-size decision is a typed result, at minimum:

```text
selected(N)
insufficient_qualified_sizes
insufficient_comparable_candidates
nonconverged_at_configured_ceiling
```

`insufficient_comparable_candidates` records the failed fidelity stage and authenticated candidate/seed failure reasons when authenticated numerical/scientific trajectory failure leaves too few complete paired candidates for a required comparison. Input/lineage/programming defects remain fail-closed exceptions.

If the configured ceiling reaches the final comparison and remains materially better than every smaller complete finalist by more than the configured final practical-equivalence width, the result is `nonconverged_at_configured_ceiling`. No generated or intermediate rescue size is synthesized.

Exhaustively training all sizes to the final fidelity to measure survivor recall is release/algorithm qualification, not the ordinary scientific production path.

## Bounded materialization and execution ownership

The configured candidate ladder does not imply one independent product-scale copy per rung. Per training domain, the intended materialization model is:

```text
one fitted selection-input authority
one canonical training order pi_train
one common target-size preparation
prefix metadata for candidate rungs
training artifacts only for candidates authorized to train
```

Descriptor, feature, and preparation caches are reconstructible and resource-bounded. Out-of-core inversion, memory mapping, chunking, work queues, NUMA placement, and concurrency are execution strategies. They may change work/span, RSS, VRAM, scratch, or wall time; they may not change scientific membership, hard coverage, rank order, paired-seed comparison, or decision authority.

This bounded representation is an architectural requirement because duplicating product-scale state per rung makes the fixed ladder scale roughly with rung count and is not an acceptable realization of the scientific policy.

## Superseded campaign generations

Current architecture does not provide migration state machines, legacy construction modes, or alternate retired selection execution. A workspace holding retired derived target-size state is detected before any semantic deserialization, candidate or checkpoint reuse, or descendant publication, and is refused with an explicit destructive reset/reprepare requirement. Retired records are quarantined under a namespace no current loader reads rather than translated.

Historical schemas may remain under `docs/history/mlff/` when needed to interpret durable evidence. Their presence never creates current product compatibility requirements.

## Physical-observable validation ownership boundary

Physical-observable calculation is not owned by `mdstats.training_data`. RDF, coordination, neighbor-angle statistics, connectivity, topology statistics, MSD, VACF, spectra, VDOS, diffusion, displacement distributions, current correlations, ionic conductivity, and related physical observables remain authoritative in their respective `mdstats.analysis` modules, specifications, and architecture manuals.

The MLFF layer owns only:

1. choosing an advisory observable-recommendation profile and explicit recipe;
2. constructing an immutable recipe of analysis call IDs and parameters;
3. running the same recipe on matched reference and MLFF collections;
4. preserving verified collection/frame-selection identity, symmetric reference/candidate trajectory-generation identity, runtime/capability identity, warnings, and analysis-owned result identities;
5. binding execution to an explicit statistical role and, where required, a predeclared comparison policy, protocol freeze, and test-activation record;
6. applying comparison and acceptance policies only after those policies are frozen and independently identified.

The MLFF layer does not own the physical numerical algorithms, normalization, neighbor definitions, plateau estimators, spectral transforms, or graph statistics.

Compact structural descriptors used for partitioning or subset construction are workflow inputs. Full physical observables used to judge a trained model remain analysis products. Expensive trajectory observables such as diffusion, VDOS, conductivity, or residence statistics are validation jobs rather than ordinary frame-selection features.

Physical-observable evidence has one explicit role such as `training_diagnostic`, `checkpoint_monitor`, `outer_validation`, `calibration`, `locked_test`, or `external_benchmark`. The role is never inferred from filenames. Realized observables cannot choose their own acceptance policy, and locked-test evidence cannot alter fitting, subset construction, target-size choice, training protocol, checkpoint selection, calibration policy, or acquisition.

## Extension boundaries

A future extension is compatible with this architecture only when it preserves the ownership graph above or explicitly revises it. In particular:

- a new feature/provider may enrich DATA4/DATA6/DATA7 inputs but cannot create a second membership selector;
- a new training-order feature may extend the `pi_train` policy only through an explicit scientific design revision that preserves one deterministic order;
- a new size-screen metric may enter the target-size policy only with an explicit evidence role and leakage analysis;
- a new acceleration may change execution representation only after exactness/resource qualification against the same scientific semantics;
- a new campaign generation is not entitled to automatic migration support;
- a custom atomwise/auxiliary loss defines a different `TrainingProtocolIdentity` and requires its own qualification rather than silently modifying the current protocol.

## Decision summary

The current MLFF subsystem follows these durable rules:

1. independent evidence remains independent;
2. the complete training protocol is the comparison unit;
3. fitted preparation and target membership are separate authorities;
4. one canonical training order and one common preparation define every candidate;
5. target size and monitor cardinalities are typed, distinct policy families;
6. frame membership and the selected target size are both protocol-global and frozen together;
7. every candidate is an exact prefix of the one training order, so candidate sets are nested by construction;
8. the target-size experiment uses development/model-selection evidence, configured `n1/n2/n3` continuation on a screen-local horizon `n3`, paired seeds, and typed non-convergence/failure outcomes; fresh selected-size production owns the independent horizon `n`;
9. the reducer is the sole target-size authority; post-selection cross-validation accepts the method and can never re-choose the size;
10. locked tests remain sealed until the frozen protocol/committee activation boundary;
11. retired derived target-size state is rejected before reuse and re-prepared rather than migrated;
12. execution is resource-bounded and may not alter scientific semantics.

# References


[1] I. Batatia, D. P. Kovacs, G. N. C. Simm, C. Ortner, and G. Csanyi,
"MACE: Higher Order Equivariant Message Passing Neural Networks for Fast and
Accurate Force Fields," *Advances in Neural Information Processing Systems*
**35**, 11423-11436 (2022). DOI:
[10.48550/arXiv.2206.07697](https://doi.org/10.48550/arXiv.2206.07697).

[2] ACEsuit, "MACE descriptors," MACE documentation. Available at:
[https://mace-docs.readthedocs.io/en/latest/guide/descriptors.html](https://mace-docs.readthedocs.io/en/latest/guide/descriptors.html)
(accessed 2026-07-27).

[3] H. Flyvbjerg and H. G. Petersen, "Error Estimates on Averages of
Correlated Data," *Journal of Chemical Physics* **91**, 461-466 (1989). DOI:
[10.1063/1.457480](https://doi.org/10.1063/1.457480).

[4] J. Racine, "Consistent Cross-Validatory Model-Selection for Dependent
Data: hv-Block Cross-Validation," *Journal of Econometrics* **99**, 39-61
(2000). DOI:
[10.1016/S0304-4076(00)00030-0](https://doi.org/10.1016/S0304-4076(00)00030-0).

[5] D. R. Roberts, V. Bahn, S. Ciuti, et al., "Cross-Validation Strategies for
Data with Temporal, Spatial, Hierarchical, or Phylogenetic Structure,"
*Ecography* **40**, 913-929 (2017). DOI:
[10.1111/ecog.02881](https://doi.org/10.1111/ecog.02881).

[6] J. D. Morrow, J. L. A. Gardner, and V. L. Deringer, "How to Validate
Machine-Learned Interatomic Potentials," *Journal of Chemical Physics* **158**,
121501 (2023). DOI:
[10.1063/5.0139611](https://doi.org/10.1063/5.0139611).

[7] VASP Software GmbH, "Smearing technique," VASP Wiki. Available at:
[https://vasp.at/wiki/Smearing_technique](https://vasp.at/wiki/Smearing_technique)
(accessed 2026-07-27).

[8] ACEsuit, "Training," MACE documentation. Available at:
[https://mace-docs.readthedocs.io/en/latest/guide/training.html](https://mace-docs.readthedocs.io/en/latest/guide/training.html)
(accessed 2026-07-27).

[9] ACEsuit, `mace-torch` 0.3.16, Python Package Index, released 2026-05-10.
Available at:
[https://pypi.org/project/mace-torch/0.3.16/](https://pypi.org/project/mace-torch/0.3.16/)
(accessed 2026-07-27).

[10] ACEsuit, `estimate_e0s_from_foundation`, MACE reference implementation,
version-locked by the adapter at implementation time. Current source available
at:
[https://github.com/ACEsuit/mace/blob/main/mace/data/utils.py](https://github.com/ACEsuit/mace/blob/main/mace/data/utils.py)
(accessed 2026-07-27).

[11] ACEsuit, "Multihead Replay Finetuning," MACE documentation. Available at:
[https://mace-docs.readthedocs.io/en/latest/guide/multihead_finetuning.html](https://mace-docs.readthedocs.io/en/latest/guide/multihead_finetuning.html)
(accessed 2026-07-27).

[12] ACEsuit, "Multihead Training for MACE," MACE documentation. Available at:
[https://mace-docs.readthedocs.io/en/latest/guide/multihead_training.html](https://mace-docs.readthedocs.io/en/latest/guide/multihead_training.html)
(accessed 2026-07-27).

[13] C. Schran, K. Brezina, and O. Marsalek, "Committee Neural Network
Potentials Control Generalization Errors and Enable Active Learning,"
*Journal of Chemical Physics* **153**, 104105 (2020). DOI:
[10.1063/5.0016004](https://doi.org/10.1063/5.0016004).

[14] A. R. Tan, S. Urata, S. Goldman, J. C. B. Dietschreit, and
R. Gomez-Bombarelli, "Single-Model Uncertainty Quantification in Neural
Network Potentials Does Not Consistently Outperform Model Ensembles,"
*npj Computational Materials* **9**, 225 (2023). DOI:
[10.1038/s41524-023-01180-8](https://doi.org/10.1038/s41524-023-01180-8).

[15] I. Batatia, P. Benner, Y. Chiang, et al., "A Foundation Model for
Atomistic Materials Chemistry," *Journal of Chemical Physics* **163**, 184110
(2025). DOI:
[10.1063/5.0297006](https://doi.org/10.1063/5.0297006).

[16] M. Kulichenko, B. Nebgen, N. Lubbers, J. S. Smith, et al., "Data
Generation for Machine Learning Interatomic Potentials and Beyond," *Chemical
Reviews* **124**, 13681-13714 (2024). DOI:
[10.1021/acs.chemrev.4c00572](https://doi.org/10.1021/acs.chemrev.4c00572).

[17] ACEsuit, `mace.tools.train`, MACE version 0.3.16 source, especially the
validation-head iteration and last-head checkpoint rule. Available at:
[https://github.com/ACEsuit/mace/blob/v0.3.16/mace/tools/train.py](https://github.com/ACEsuit/mace/blob/v0.3.16/mace/tools/train.py)
(accessed 2026-07-27).

[18] ACEsuit, `mace.cli.run_train`, MACE version 0.3.16 source, especially
multi-head assembly, replay-ratio duplication, head ordering, and loader
construction. Available at:
[https://github.com/ACEsuit/mace/blob/v0.3.16/mace/cli/run_train.py](https://github.com/ACEsuit/mace/blob/v0.3.16/mace/cli/run_train.py)
(accessed 2026-07-27).


[19] ACEsuit, `mace-torch` version 0.3.16 `setup.cfg`, complete runtime
`install_requires` contract. Available at:
[https://github.com/ACEsuit/mace/blob/v0.3.16/setup.cfg](https://github.com/ACEsuit/mace/blob/v0.3.16/setup.cfg)
(accessed 2026-07-28).

[20] e3nn developers, `e3nn` 0.4.4 package metadata and dependency contract,
Python Package Index. Available at:
[https://pypi.org/project/e3nn/0.4.4/](https://pypi.org/project/e3nn/0.4.4/)
(accessed 2026-07-28).

[21] R. Kern, "A Simple File Format for NumPy Arrays," NumPy Enhancement
Proposal 1, 2007. Available at:
[https://numpy.org/doc/1.13/neps/npy-format.html](https://numpy.org/doc/1.13/neps/npy-format.html)
(accessed 2026-08-15).

[22] NumPy developers, "numpy.load," NumPy reference documentation. Available
at:
[https://numpy.org/doc/stable/reference/generated/numpy.load.html](https://numpy.org/doc/stable/reference/generated/numpy.load.html)
(accessed 2026-08-15).

[23] National Institute of Standards and Technology, *Secure Hash Standard
(SHS)*, FIPS PUB 180-4, 2015. DOI:
[10.6028/NIST.FIPS.180-4](https://doi.org/10.6028/NIST.FIPS.180-4).

[24] R. J. Hyndman and Y. Fan, "Sample Quantiles in Statistical Packages,"
*The American Statistician* **50**(4), 361--365 (1996). DOI:
[10.1080/00031305.1996.10473566](https://doi.org/10.1080/00031305.1996.10473566).

[25] J. L. Bentley, "Multidimensional Binary Search Trees Used for Associative
Searching," *Communications of the ACM* **18**(9), 509--517 (1975). DOI:
[10.1145/361002.361007](https://doi.org/10.1145/361002.361007).

[26] SciPy developers, "scipy.spatial.cKDTree," SciPy reference documentation.
Available at:
[https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.html](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.html)
(accessed 2026-08-15).

[27] T. F. Gonzalez, "Clustering to Minimize the Maximum Intercluster
Distance," *Theoretical Computer Science* **38**, 293--306 (1985). DOI:
[10.1016/0304-3975(85)90224-5](https://doi.org/10.1016/0304-3975(85)90224-5).

[28] SciPy developers, "scipy.spatial.cKDTree.query," SciPy reference
documentation. Available at:
[https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.query.html](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.query.html)
(accessed 2026-08-15).

[29] SciPy developers, "scipy.stats.wasserstein_distance," SciPy reference
documentation. Available at:
[https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wasserstein_distance.html](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wasserstein_distance.html)
(accessed 2026-08-15).

[30] K. Jamieson and A. Talwalkar, "Non-stochastic Best Arm Identification and
Hyperparameter Optimization," *Proceedings of AISTATS*, PMLR 51:240--248, 2016.
Available at: [https://proceedings.mlr.press/v51/jamieson16.html](https://proceedings.mlr.press/v51/jamieson16.html).

[31] L. Li, K. Jamieson, G. DeSalvo, A. Rostamizadeh, and A. Talwalkar,
"Hyperband: A Novel Bandit-Based Approach to Hyperparameter Optimization,"
*Journal of Machine Learning Research* **18**(185), 1--52 (2018). Available at:
[https://www.jmlr.org/papers/v18/16-558.html](https://www.jmlr.org/papers/v18/16-558.html).

[32] R. D. Blumofe and C. E. Leiserson, "Scheduling Multithreaded
Computations by Work Stealing," *Journal of the ACM* **46**(5), 720-748
(1999). DOI: [10.1145/324133.324234](https://doi.org/10.1145/324133.324234).

[33] SciPy developers, `scipy.spatial.cKDTree.query_ball_point`, SciPy
reference documentation. Available at:
[https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.query_ball_point.html](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.query_ball_point.html)
(accessed 2026-08-17).

[34] SciPy developers, compressed sparse row/column matrix documentation,
including `scipy.sparse.csr_matrix` and `scipy.sparse.csc_matrix`. Available at:
[https://docs.scipy.org/doc/scipy/reference/sparse.html](https://docs.scipy.org/doc/scipy/reference/sparse.html)
(accessed 2026-08-17).

[35] `threadpoolctl` developers, "Python helpers to limit native thread pools,"
project documentation and source. Available at:
[https://github.com/joblib/threadpoolctl](https://github.com/joblib/threadpoolctl)
(accessed 2026-08-17).

[36] J. Deters, J. Wu, Y. Xu, and I.-T. A. Lee, "A NUMA-Aware
Provably-Efficient Task-Parallel Platform Based on the Work-First Principle,"
arXiv:1806.11128 (2018). Available at:
[https://arxiv.org/abs/1806.11128](https://arxiv.org/abs/1806.11128).

[37] NumPy developers, `numpy.bincount`, NumPy reference documentation.
Available at:
[https://numpy.org/doc/stable/reference/generated/numpy.bincount.html](https://numpy.org/doc/stable/reference/generated/numpy.bincount.html)
(accessed 2026-08-17).
