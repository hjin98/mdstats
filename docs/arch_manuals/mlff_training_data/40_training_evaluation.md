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

The target-size experiment is a special protocol-comparison control described in Part V. It uses authenticated `n1 -> n2 -> n3` continuation on a screen-local scheduler horizon `n3`, with a common seed set, and disables ordinary target-success early stopping so candidate sizes reach comparable fidelity boundaries. The separate production horizon `n` is reserved for a fresh selected-size campaign. Hard numerical/scientific failure remains a valid rejection.

Epoch has deliberately different semantics in the two phases. During target-size selection, epoch is a **controlled variable**: the configured coarse, short, and final screens consume only exact `n1`, `n2`, and `n3` checkpoints, and the screen scheduler is planned for `n3`. An earlier checkpoint is inadmissible even when it scores better, because substituting it would confound target-data size with achieved training fidelity. The public `select-target-size` operation owns this complete restartable `n1 -> n2 -> n3` experiment; generated campaigns default to `(n1,n2,n3)/n = (1,3,10)/30`, with `n` consumed only by fresh post-selection production.

After `N_selected` is frozen, ordinary production/CV training resumes under the frozen protocol. Production checkpoint epoch is then a **selectable model variable**: production `evaluate` may choose an earlier admissible checkpoint when it is better under the frozen checkpoint-selection policy, even though the configured training horizon remains `n` epochs. Its target-oriented stopping and LR-refinement semantics are part of `TrainingProtocolIdentity`; changing them after protocol comparison invalidates the comparison.

The stable TRAIN2 command boundary is therefore `prepare -> preflight -> select-target-size -> materialize -> preflight -> train -> evaluate -> verify`. `prepare` owns only the initial screening workload; `materialize` owns only the selected-size final-development/CV realization; both `preflight` occurrences have the same operational meaning and are bound to the exact current DATA8 matrix. The screening preflight remains valid throughout an unchanged `n1/n2/n3` candidate matrix, while selected-production materialization changes that matrix and therefore requires a new preflight.

## Protocol-matched cross-validation

Cross-validation validates the **complete already-frozen protocol**, including selected target size. It does not choose target size.

For each fold \(k\):

1. DATA5 provides `fold_training_domain_k`, a disjoint authorized checkpoint monitor, and `held_out_evaluation_fold_k`.
2. DATA6/DATA7 fit descriptors, transforms, metrics, E0, objective/weights, and difficulty evidence only within `fold_training_domain_k`.
3. MVSEL2/REPAIR2 construct the fold-local repaired master order from fold-authorized evidence.
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
- MVIDX, MVSEL2, REPAIR2, MVSTATE2, and MVQUAL identities;
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
