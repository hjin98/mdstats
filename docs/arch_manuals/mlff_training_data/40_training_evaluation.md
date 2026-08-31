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
