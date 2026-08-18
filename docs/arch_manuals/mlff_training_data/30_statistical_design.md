# Part III - Statistical design and selection

## Outer partition architecture

### Independence hierarchy

Evidence uses the strongest available independence level, for example:

1. independent replica/velocity seed or independently prepared realization;
2. independent structural/chemical ordering;
3. independent thermodynamic run;
4. purged temporal block within one run.

Temporal separation does not create an independent metastable state when the relevant slow variable never decorrelates. Every cohort carries machine-readable independence evidence and known limitations.

### Partition-role feasibility

Before role assignment, `PartitionRoleBudgetPolicy` declares requested cohorts, cross-validation support, minimum independent blocks/grades, purge requirements, and allowed reductions. `PartitionFeasibilityReport` determines what the available evidence can actually support.

Outcomes include full support, temporal-block-only support, deferred calibration, external-only challenge evidence, reduced fold count, or insufficient support. The workflow never fabricates every desired role from a short trajectory merely to satisfy a percentage.

### Outer evidence roles

A feasible target label domain may contain:

```text
development_pool
outer_monitor_validation
uncertainty_calibration
locked_interpolation_test
zero or more locked_challenge_tests
```

Only the development pool supplies gradient-training candidates. The fixed outer monitor may control the current final-run monitoring/checkpoint policy but supplies no gradients and is not the locked test. Calibration is reserved for predictions from the actual final committee. Locked interpolation/challenge evidence cannot affect training, selection, checkpointing, calibration policy, acquisition policy, or protocol design.

When a requested role is unsupported, the role is absent/deferred with explicit evidence rather than synthesized from correlated data.

## Independent cross-validation job families

A frame that has contributed a gradient is not independent validation evidence for that model. Likewise, a held-out evaluation fold cannot control stopping/checkpoint choice for the fold model whose error it is intended to estimate.

For $K$ folds, job $k$ contains distinct:

```text
fold_training_domain_k
fold_checkpoint_monitor_k
held_out_evaluation_fold_k
```

The checkpoint monitor is a deterministic authorized split/cohort from non-evaluation evidence. The held-out evaluation fold remains inaccessible to fitted products and checkpoint choice.

The fold model has fresh model/optimizer/checkpoint lineage. Transform, feature-metric fit, E0 fit, difficulty evidence, and target selector are fitted only on the fold-training domain. Only after checkpoint choice freezes is the model evaluated on its held-out fold. The resulting out-of-fold catalog is bound to the complete `TrainingProtocolIdentity`.

Cross-validation is therefore a family of independent jobs, not a rotating epoch schedule inside one evolving model.

## Training-set selection

Selection runs only inside the applicable fold-training or final-training domain. `SelectionBudgetPolicy` binds requested sizes, mandatory anchors/obligations, evidence-class budgets, near-duplicate policy, and deterministic tie/interleaving behavior.

### Deterministic nested order

The selector constructs a deterministic ordered target-data sequence whose permitted dataset sizes are prefixes. Mandatory anchors/obligations are satisfied first; remaining capacity is allocated among the declared evidence classes without allowing one earlier class to consume the full budget.

Representative evidence classes include:

```text
representative distribution coverage
species/atom-group environment coverage
rare/protected events
descriptor diversity/FPS
difficulty enrichment
```

Their exact fractions/counts are policy, not universal constants. Deficits are redistributed by the declared deterministic rule. A requested size smaller than mandatory support fails explicitly.

### Hierarchical quotas

Every observed and scientifically applicable combination of declared condition axes/protected classes receives its policy-defined coverage request. Condition axes are profile-owned and may include composition, temperature, pressure, strain, phase, defect, surface/interface state, molecular conformer, or preparation history.

The optional LTA profile uses hierarchical unstrained and strained schemas rather than a global Cartesian product. Empty/non-applicable combinations are not treated as missing data.

### Representative, diversity, and environment evidence

Representative anchors preserve dense expected-production regions; pure diversity sampling is insufficient because it can overweight feature-space boundaries.

Configuration-level farthest-point sampling uses the fitted heterogeneous feature metric with stable identity tie-breaking. It is one evidence source rather than the entire selector.

Declared focus atom groups receive separate environment coverage/selection so abundant host atoms cannot determine the entire target set. The generic architecture is group-driven; Li/Na/K groups are an LTA specialization, not core defaults.

### Rare-event anchors

Protected event windows are retained around declared structural/chemical/trajectory changes. Generic changes include coordination/connectivity, large non-affine displacement, local packing/order changes, phase/state changes, strain extrema, and high but physical restoring-force excursions. Site/window/ring/interface/adsorption events activate only through the appropriate profile/provider.

### Difficulty enrichment and blinding

Label-derived foundation-model residuals may enrich selection only inside the authorized training domain. Evaluation-domain residuals remain blinded. Difficulty enrichment is quota-controlled and cannot replace representative or hard coverage.

### Coverage diagnostics

Selection evidence reports condition/group/feature coverage, nearest-distance/radius statistics, event/state counts, redundancy, and realized evidence-class budgets under the current target-data coverage authority. Coverage diagnostics recommend data sufficiency; they do not by themselves prove final model adequacy.

## Training objective, weighting, and exposure

Training membership, label weighting, and runtime exposure are separate decisions.

`TrainingObjectivePolicy` binds loss family, energy/force/stress weights, head weights, normalization, robust-loss choices, and missing-label behavior. `ConfigurationWeightPolicy` and `PropertyWeightPolicy` bind condition/regime/event/quality and property-specific weights.

`ExposureAssignment`/realization evidence binds the head, eligible use, actual gradient exposures, configuration/property weights, sampling/duplication behavior, and seed/runtime lineage as applicable.

### Atom-group force imbalance

A configuration can contain many more host force components than scientifically critical minority-group components. Selection diversity does not eliminate that loss imbalance.

The standard MACE configuration/property-weight path does not claim a generic atomwise group-weighted loss. Therefore evaluation/checkpoint policy reports declared group-resolved metrics and imposes applicable group constraints. Any custom atomwise/auxiliary loss defines a different `TrainingProtocolIdentity` and requires its own qualification.

### Exposure backends

Exposure modes are distinct protocol semantics. The standard qualified fixed-file MACE path is `NATIVE_MACE_FIXED`: selected target/replay frames are materialized in fixed artifacts and the upstream loader performs the qualified shuffle/batching behavior.

Any custom epoch resampling, multi-job resampling, or final-refit behavior is valid only when a current adapter/specification explicitly supports it and binds its optimizer/checkpoint/exposure lineage. Static files alone cannot claim dynamic per-epoch resampling.

### Realized MACE exposure

`MaceExposureRealizationRecord` compares intended artifacts/weights with observed loader behavior, including target/replay counts, implicit duplication, expected/observed batches, and configuration/property exposures.

Upstream target/replay duplication behavior is version-dependent. The adapter either disables unintended duplication when supported or binds the realized behavior into the protocol and verifies it. Silent changes in effective target/replay exposure fail closed.

## Statistical authority boundary

The statistical design is controlled by explicit policies and immutable evidence lineage. Worker count, cache layout, training scheduler parallelism, and other execution realization cannot change partition membership, fold roles, selection order, checkpoint evidence role, or locked-test boundaries.
