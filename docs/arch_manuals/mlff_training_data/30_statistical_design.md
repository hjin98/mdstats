# Part III - Statistical design and fitted preparation

## Purpose and ownership

This chapter defines the statistical evidence roles that make later model comparisons interpretable and the fitted-preparation boundary immediately upstream of multi-view target-subset construction.

It owns the architectural separation among training, monitoring, cross-validation, calibration, and locked-test evidence. It also defines what fold/final-domain fitted preparation may consume and emit.

It does **not** own target membership or target size. DATA7 prepares fitted inputs; MVSEL2/REPAIR2 determine target membership inside each authorized training domain; `TargetSizeStudyPolicy` chooses the protocol-global target size.

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

The one current membership authority consumes these inputs in the multi-view chain described in Part V. There is no competing quota/FPS `TrainingSelectionPlan` whose prefixes can disagree with MVSEL2/REPAIR2.

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
    -> MVSEL2 / REPAIR2 target membership
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
