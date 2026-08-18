# Part III - Statistical design and selection

## Outer partition architecture

### Independence hierarchy

Use the strongest available evidence level:

1. independent replica or velocity seed;
2. independent cation ordering;
3. independent thermodynamic run;
4. purged temporal block within one run.

Temporal separation does not create an independent metastable state when the
slow variable never decorrelates.

### Partition-role feasibility

Before assigning roles, a `PartitionRoleBudgetPolicy` states the requested
cohorts and minimum support. A `PartitionFeasibilityReport` evaluates whether the
available independent blocks can support:

```text
development_pool
outer_monitor_validation
uncertainty_calibration
locked_interpolation_test
locked_challenge_tests
cross-validation folds
nested checkpoint monitors
purge intervals
```

Possible outcomes are:

```text
fully_supported
supported_with_temporal_blocks_only
calibration_deferred
challenge_set_external_only
reduced_cross_validation_folds
insufficient_for_locked_test
insufficient_for_requested_roles
```

The workflow never carves every desired role from a short trajectory merely to
satisfy a percentage. A calibration cohort or challenge set may be deferred to
later independent calculations.

### Outer domains

For each target `LabelDomain`, define:

```text
development_pool
outer_monitor_validation
uncertainty_calibration
locked_interpolation_test
zero or more locked_challenge_tests
```

#### Development pool

Only this domain supplies cross-validation fold-training and final target
training candidates.

#### Outer monitor validation

This fixed, representative domain controls final-run monitoring, stopping, and
checkpoint choice and never supplies gradients. It is not the locked test.

#### Uncertainty calibration

This domain is reserved for predictions from the actual final independent-seed
committee. Out-of-fold predictions may diagnose ranking behavior, but they do
not automatically calibrate numerical final-committee thresholds.

#### Locked interpolation test

This domain estimates unseen-frame performance within sampled conditions. It
cannot affect hyperparameters, selection, calibration, acquisition, stopping,
checkpoint choice, or protocol design.

#### Locked challenge tests

Examples include:

- omitted temperature;
- omitted composition;
- omitted strain mode;
- independent structural or chemical realization;
- migration-coordinate calculations.

These remain separate named evidence cohorts.

### Machine-readable independence evidence

Every outer, fold-evaluation, checkpoint-monitor, calibration, and test cohort
receives one or more evidence grades:

```text
independent_replica
independent_structural_realization
independent_thermodynamic_run
purged_temporal_block
slow_state_not_decorrelated
insufficient_independence
```

The report records purge width, autocorrelation evidence, duplicate checks, and
known limitations. Metrics must carry these grades.

## Independent cross-validation job families

### Invalid design that is prohibited

The same continuously trained model must not train on fold $F_1$, later call
$F_1$ validation, and report the result as out-of-fold evidence. Once a frame
has contributed a gradient, it is no longer independent validation evidence for
that model.

The held-out evaluation fold must also not control early stopping or checkpoint
choice. Selecting the best checkpoint on the evaluation fold would bias the
reported fold error.

### Correct cross-validation

For $K$ evaluation folds, create $K$ independent jobs. For job $k$, partition
the non-evaluation development data into:

```text
fold_training_domain_k
fold_checkpoint_monitor_k
held_out_evaluation_fold_k
```

The default checkpoint monitor is a deterministic, purged nested split carved
from the non-evaluation data. A versioned policy may instead use a declared
fixed monitor cohort, but the held-out evaluation fold is never used for model
selection.

Train a fresh model:

$$
M_k = \operatorname{Train}
\left(
S_k\left[T_k(\mathcal D_{\mathrm{fold\ train},k})\right],
\mathcal D_{\mathrm{checkpoint},k}
\right),
$$

where:

- $T_k$ is fitted only on the fold-training domain;
- $S_k$ selects only from that domain;
- the fold-local atomic-reference fit uses only that domain;
- the checkpoint monitor controls stopping and checkpoint choice but no gradients;
- $M_k$ has an independent initialization, optimizer, and checkpoint lineage.

Only after checkpoint choice is frozen is $M_k$ evaluated on the held-out fold
$\mathcal F_k$. Combining these predictions gives a genuine out-of-fold
catalog.

### Cross-validation output

```text
CrossValidationJobFamily
  evaluation-fold definitions
  fold-training domains
  fold checkpoint-monitor domains
  fold-local transforms and FeatureMetricPolicy records
  fold-local training selections
  fold-local AtomicReferenceFitRecord objects
  one development MACE bundle per fold
  fresh-seed and initialization contract
  held-out out-of-fold prediction catalog
  aggregate metrics with independence grades
```

Every fold uses the same `SelectionBudgetPolicy`. Equal nominal target sizes are
used where feasible; mandatory-anchor differences and actual counts are
reported. Hyperparameter comparisons use the same budget policy and coverage
criteria, not an assumption that different folds contain identical selected
frames.

Cross-validation selects policies and estimates development-domain performance.
It is not implemented as a rotating epoch schedule.

## Training-set selection

Selection runs only inside the applicable fold-training or final-training
domain. A `SelectionBudgetPolicy` fixes requested sizes, mandatory-anchor
requirements, evidence-class quotas, and deterministic interleaving.

### Deterministic quota-interleaved master order

The selector first resolves mandatory coverage anchors. Remaining positions are
filled by a deterministic interleaving schedule across evidence classes:

```text
representative coverage
species-environment coverage
rare events
descriptor FPS
difficulty enrichment
```

The policy stores either explicit counts or fractions for every target size. A
representative default may reserve, after mandatory anchors:

```text
representative coverage     45%
species environments        20%
rare events                  15%
descriptor FPS               10%
difficulty enrichment        10%
```

These values are project policy, not universal constants. Deficits in one class
are redistributed by a declared deterministic rule. This prevents later
selectors from being starved when an earlier class consumes the size budget.

Near-duplicate pruning occurs during construction. The result is one ordered
sequence

$$
q_1,q_2,\ldots,q_N,
$$

and requested datasets are prefixes:

$$
\mathcal T_n = \{q_1,\ldots,q_n\}.
$$

A requested size below the mandatory-anchor count fails explicitly.

### Mandatory hierarchical quotas

The generic rule is that every observed, applicable combination of declared
condition axes and protected event classes receives an auditable minimum
coverage request. The axis catalog is profile-provided and may include
composition, temperature, pressure, strain, phase, defect state, surface
termination, interface registry, molecular conformer, or preparation history.

For the optional LTA profile:

```text
unstrained: composition x temperature x regime
strained: composition x reference-condition x strain-mode x sign x regime
```

Only applicable observed strata are required.

### Representative anchors

Representative anchors preserve dense equilibrium regions and expected
production frequencies. Diversity-only sampling is insufficient because it may
overweight feature-space boundaries.

### Configuration-level FPS

Use the fitted heterogeneous feature metric. Deterministic farthest-point
sampling selects

$$
i^*=\arg\max_i\min_{j\in S}d(\mathbf z_i,\mathbf z_j),
$$

with stable `frame_uid` tie-breaking. Pure FPS is not the complete selector.

### Atom-group-specific environment selection

Run separate environment selection for every declared focus atom group. Groups
may be defined by species, molecule, phase, spatial region, defect neighborhood,
interface side, or profile-generated tags. Selecting an atomic environment adds
its parent configuration. Abundant atom groups cannot determine the complete
selection. The historical LTA implementation uses Li, Na, and K groups; these
identities are not core defaults.

### Rare-event anchors

Include a compact temporal stencil around profile-declared events. General
defaults include coordination or neighbor changes, connectivity changes, large
nonaffine displacements, local-density changes, phase/order changes, strain
extrema, and high but physical restoring-force excursions. Site changes,
ring-plane crossings, pore-window events, adsorption/desorption, or interphase
transfer activate only when their profile providers are present.

### Difficulty enrichment

Within the training domain only, add a controlled quota of configurations with
large foundation-model residuals, stratified by condition and species. These
label-derived features remain blinded in evaluation domains.

### Coverage diagnostics

Report by feature block, condition, and species:

- candidate-to-training nearest distance;
- selected-to-selected nearest distance;
- 90th and 95th percentile covering radius;
- physical-feature quantiles;
- event/state counts;
- redundancy fraction;
- budget realized by evidence class.

These metrics recommend a coverage-complete size. Learning curves remain
necessary to establish model adequacy.

## Training objective, weighting, and exposure

### Membership, weighting, and exposure are different

Training-set membership says a frame may be used. Weighting says how strongly
its labels affect the loss. Exposure says when and how often it is presented.

`TrainingObjectivePolicy` binds:

```text
loss family
energy/force/stress global weights
head weights
normalization conventions
missing-label behavior
robust-loss settings
```

`ConfigurationWeightPolicy` binds condition-, regime-, event-, and
quality-dependent configuration weights. `PropertyWeightPolicy` binds
per-configuration energy, force, stress, or virial weights.

`ExposureAssignment` records:

```text
frame_uid
head_id
eligible epochs
actual gradient exposures
configuration weight
energy/force/stress weights
sampling probability
random-seed lineage
```

### Atom-group force imbalance

A configuration may contain many more force components from an abundant host
group than from a scientifically critical minority group. Selection diversity
does not remove this loss imbalance. The first adapter uses the standard MACE
configuration/property-weight interface and therefore does not claim a general
atomwise group-weighted loss. It must:

- report force metrics for all declared evaluation groups;
- impose profile-declared group, stress, and replay constraints during checkpoint
  selection;
- record any custom atomwise or auxiliary objective as a distinct protocol
  identity.

The historical LTA profile defines framework and Li/Na/K groups. Other systems
may define defects, adsorbates, interface atoms, reactive centers, rare elements,
or molecular subunits.

### Exposure backends

```text
NATIVE_MACE_FIXED
CUSTOM_EPOCH_RESAMPLE
MULTI_JOB_RESAMPLE
FINAL_REFIT
```

#### `NATIVE_MACE_FIXED`

All selected target and replay frames are present in fixed files. MACE shuffles
the training loader reproducibly. This is the only backend supported by the
first adapter.

#### `CUSTOM_EPOCH_RESAMPLE`

A custom MACE/PyTorch adapter rebuilds eligible data loaders at epoch boundaries.
This requires runtime integration and is not deliverable by files alone.

#### `MULTI_JOB_RESAMPLE`

A deterministic sequence of restart jobs uses different fixed subsets. Its
optimizer/checkpoint lineage is explicit and it is not equivalent to one native
MACE run.

#### `FINAL_REFIT`

After protocol and epoch rules are frozen, all declared development data may be
used. If outer validation is consumed, the final model loses that independent
monitor and may be judged only on locked external evidence.

### MACE exposure realization

`MaceExposureRealizationRecord` compares exported intent with the actual loader:

```text
real_pt_data_ratio_threshold
pre-MACE target/replay counts
post-MACE effective target/replay counts
implicit duplication factor
expected and observed batches
configuration, energy, force, and stress exposures
```

MACE 0.3.16 can duplicate fine-tuning-head data when the target/replay ratio is
below the MACE real-point data-ratio threshold [18]. The exact loader field is recorded in the exposure realization above. The first adapter disables this behavior where the locked CLI permits it; otherwise the duplication is declared
in `TrainingProtocolIdentity` and audited as realized exposure. Silent exposure
changes are prohibited.

Cross-validation is a job family, not an epoch mode.
