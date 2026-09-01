# Part III - Statistical design and fitted preparation

## Purpose and ownership

This chapter defines the evidence roles and fitted-preparation boundary that
make target-size comparisons and later method validation interpretable. It
owns independence, protected relations, leakage boundaries, fitted products,
objective/weighting inputs, and the distinction between development evidence
and later validation roles.

It does **not** own target membership or target size. The Part V owners derive
one `P_train`/`M3` split, one canonical `pi_train`, and one target-size result.
After selection, the Part V/P5 owners may partition the already frozen
`T_selected` for cross-validation; that operation cannot choose a new size or
membership.

## Independence and evidence roles

Evidence uses the strongest available independence level, for example:

1. independent replica/velocity seed or independently prepared realization;
2. independent structural or chemical ordering;
3. independent thermodynamic run;
4. a purged temporal block within one run.

Temporal separation does not create an independent metastable state when the
relevant slow variable has not decorrelated. Every cohort carries machine-
readable independence evidence and known limitations.

Before roles are assigned, the partition policy declares requested cohorts,
minimum independent blocks, purge requirements, protected relations, and
allowed reductions. A feasibility report may therefore record full support,
temporal-block-only support, deferred calibration, external-only challenge
evidence, a reduced fold count, or insufficient support. The workflow never
fabricates a role from a short or correlated trajectory to satisfy a percentage
target.

The current development evidence roles are:

```text
development_pool
common_target_monitor
post_selection_cv_folds
```

The broader product architecture reserves separate calibration and locked-test
roles for downstream qualification. Those consumers are not part of the P6
campaign lifecycle and their absence is not converted into current selection
or production evidence.

Only the development pool supplies gradient-training candidates. The common
target monitor is development/model-selection evidence: it may control the
authorized target-size screen and post-selection checkpoint policy, but it
supplies no gradients and is not a held-out CV fold.

## One global selection universe

The neutral statistical substrate supplies duplicate groups, correlation
families, provenance relations, and split exclusions before target-size
selection exists. It produces exactly one development split:

```text
eligible labelled frames -> P_train (target-training pool) + M3 (development monitor)
```

`P_train` is ordered once as `pi_train`; the target-size owner defines every
candidate as an exact prefix. `M3` is ordered once as `pi_eval`; `M1`, `M2`,
and `M3` are direct nested evaluation populations. No complement, per-domain
membership map, or alternate ordering may change the universe.

Protected relations remain intact wherever the current owner assigns roles.
An inseparable duplicate/correlation component cannot be split merely to
obtain a requested fold count. A frame outside `T_selected` cannot enter
post-selection CV because it is convenient or because it belongs to a related
source cohort.

## Cross-validation validates a frozen protocol

Target size is frozen before protocol-matched cross-validation is interpreted.
For each required post-selection fold (k), the owner keeps distinct:

```text
fold_training_partition_k within T_selected
fold_checkpoint_monitor_k
held_out_evaluation_partition_k within T_selected
```

The selected cardinality and the exact global membership remain unchanged for
every fold. Fold assignment may be local to `T_selected`, and fold-local
fitted preparation may use only that fold's training partition and authorized
monitor. It may not inspect the held-out partition, outer protected evidence,
or locked evidence before checkpoint choice. The final fold evaluation occurs
only after the fold representative is frozen.

This gives the required distinction:

```text
global target-size choice -> one N_selected and one T_selected
post-selection CV        -> method validation on partitions of T_selected
```

Held-out CV error, calibration evidence, and locked-test evidence therefore
cannot select `N_selected`, alter `T_selected`, or tune the target-size policy.

## Fitted preparation

The current common preparation is built once from the neutral substrate and
the frozen foundation/training protocol. It may emit:

- descriptor coordinates and fitted feature metrics;
- foundation predictions and training-domain residual/difficulty evidence;
- atomic-reference/E0 fits;
- objective, configuration-weight, and property-weight records;
- condition, provenance, event, environment, and diversity inputs;
- deterministic identities binding each product to its authorized inputs.

These products are inputs to the one canonical training order. They are not a
second selector. A fitted transform, metric, residual, or E0 correction must
be bound to the evidence that fitted it and may not be inferred from a
downstream held-out result.

For post-selection CV, a fold-local transform or metric is valid only when the
CV owner explicitly records the fold training partition, protected relations,
and protocol identity. A fold-local product can change the fold's evaluation
realization; it cannot change the global target membership or target-size
decision. Final production uses the accepted method and complete `T_selected`.

## Selection inputs are not a second selector

Representative density, diversity, environment coverage, protected events,
difficulty, condition balance, and provenance/correlation structure remain
useful scientific information. The current owner represents them as:

```text
fitted feature coordinates/metrics
hard obligations or applicability masks
representative-density and diversity evidence
event/environment/condition evidence
difficulty and correlation identities
```

The target-size policy combines these inputs into the one deterministic
`pi_train`. There is no competing quota/FPS plan whose prefixes can disagree
with that order. A materialization or export record may describe a consumer
view of `T_selected`, but it is not an independent membership authority.

## Objective, weighting, and exposure

Target membership, target size, loss weighting, and runtime exposure are
separate decisions. `TrainingObjectivePolicy` binds the loss family,
energy/force/stress weights, head weights, normalization, robust-loss choices,
and missing-label behavior. Configuration/property weighting binds applicable
condition, regime, event, quality, and property weights. Exposure binds the
head, actual gradient exposures, batching/duplication behavior, seed, and
runtime lineage.

A frame can be selected once, weighted non-uniformly, and exposed through a
qualified loader without those decisions becoming one authority. A custom
atomwise or auxiliary loss changes `TrainingProtocolIdentity` and requires its
own accepted method identity; it cannot be smuggled into the current protocol
through a loader option.

## Material and profile specialization

Condition axes and focus groups are declared by the applicable material/profile
contract. They may include composition, temperature, pressure, strain, phase,
defect, surface/interface state, conformer, preparation history, or another
scientifically justified axis. A profile may define hierarchical applicability
rather than a Cartesian product. Empty or physically inapplicable combinations
are not missing observations merely because their names exist.

Material-specific concepts remain explicit extensions. LTA ring/cage/site
groups or Li/Na/K focus groups are not generic defaults and cannot silently
change the global target order.

## Dependency boundary and failure semantics

The allowed dependency direction is:

```text
raw source / label / feature / event evidence
    -> neutral statistical substrate and protected relations
    -> P_train/M3 split and canonical orders
    -> common fitted preparation
    -> one target-size screen and reducer
    -> frozen N_selected/T_selected
    -> post-selection fold partitions and method acceptance
    -> fresh final production
    -> downstream qualification roles when separately implemented and activated
```

Forbidden reverse dependencies include held-out CV error choosing target size,
locked evidence tuning preparation or checkpoint policy, calibration fitting
the protocol it evaluates, and executor/cache behavior changing membership or
evidence roles.

The workflow fails closed when labels or protected relations are unresolved,
requested roles are infeasible, a fitted product has the wrong lineage, a
fold would split an inseparable relation, or a downstream result is offered as
selection authority. Explicit absence or deferral is evidence; it is not a
synthetic pass.
