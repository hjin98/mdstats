# Part IV - Training and evaluation

## Multi-head replay and training-protocol contract

Multi-head replay fine-tuning trains a shared MACE backbone on target data and a foundation replay dataset with separate output heads. The replay objective limits catastrophic forgetting while the target head adapts [11, 12]. Replay, objective, exposure, checkpoint control, backend, precision, optimizer/scheduler, and seed policy are part of the training protocol rather than incidental runtime settings.

### `TrainingProtocolIdentity`

Every cross-validation family and final run is bound to one complete protocol identity containing, as applicable:

```text
foundation checkpoint and head
model/foundation family and target head
naive or multi-head mode
replay source, selection, and monitor
training objective and property weights
target/replay head weights
exposure backend and realized balancing policy
checkpoint metric and checkpoint-control policy
replay-retention policy
optimizer, scheduler, epoch cap, stopping/LR policy, and seed policy
model precision and execution backend
MACE adapter/runtime lock
```

Cross-validation results apply only to that identity. Results from a different replay mode, objective, precision/backend realization, checkpoint policy, or other protocol-defining choice are not validation of the final protocol.

### Separate target and replay lineages

Target and replay evidence retain separate source/label identities, atomic-reference policy where applicable, selection/split plans, weights/exposure accounting, and validation/sentinel monitoring. Replay train and replay monitor roles are disjoint.

The mdstats core records replay preparation and does not silently download external replay data. True-label replay is evaluated against held-out labels; pseudo-label replay measures drift from the bound foundation model on an unseen sentinel set.

### Replay retention

`ReplayRetentionPolicy` binds the retention metric, foundation/pre-fine-tuning baseline, tolerated degradation, aggregation over properties, and failure/override behavior. Candidate checkpoints that violate a mandatory replay-retention constraint are inadmissible even when target error improves.

### Checkpoint metrics and constrained choice

`CheckpointMetricPolicy` defines the primary target objective together with all mandatory target, focus-group/species, condition, stress/property, and replay constraints. Candidate checkpoint selection is deterministic over the complete evaluated candidate set and fails closed when no candidate satisfies mandatory constraints.

A typical mathematical form is

$$
\min_c L_{\mathrm{target\ monitor}}(c)
$$

subject to profile- and protocol-specific constraints such as

$$
L_{F,g}(c)\le\delta_g,
\qquad
\Delta L_{\mathrm{replay}}(c)\le\delta_{\mathrm{replay}}.
$$

Exact metrics and thresholds are serialized policy, not hard-coded universal constants.

### MACE checkpoint control

The supported MACE adapter is version-locked and verifies the native validation-head ordering, scheduling/stopping behavior, checkpoint retention, target/replay loader realization, and other upstream behaviors on which the protocol depends. The accepted native-target-monitor mode ensures that the target checkpoint monitor owns native scheduling/checkpoint control while replay behavior cannot silently terminate the run.

Every candidate checkpoint needed by the external selection policy is retained and evaluated on the authorized target and replay monitors. If the version-locked upstream behavior changes, preparation/qualification fails closed rather than silently accepting a different control flow.

## MACE adapter and artifact boundary

### Version/runtime lock

Every supported runtime lock records sufficient identity to reproduce and requalify upstream-dependent behavior, including package/source identity, relevant CLI/parser/loader/train-loop identity, validated head order, checkpoint behavior, replay-ratio behavior, precision/backend realization, and accelerator qualification where applicable. Documentation URLs alone are not treated as a stable API contract.

### Minimal Extended XYZ plus sidecar provenance

Extended XYZ contains only MACE-readable labels, weights, and compact stable identities. Long provenance, policy identities, and selection/audit reasons live in a sidecar manifest keyed by `frame_uid`.

Target-frame export includes the declared energy channel, forces, stress when available/authorized, stable frame/config identities, configuration/property weights, cell/PBC, atom order, and exact label-domain/E0 provenance. Export uses sufficient numerical precision and certifies round-trip semantics through the locked parser/reader path.

### Separated development, calibration, and sealed-evaluation artifacts

The architecture separates:

```text
development_bundle/
calibration_bundle/
sealed_evaluation_bundle/
evaluation_activation/
evaluation_results/
```

Development artifacts contain no locked-test path. A sealed evaluation bundle may exist before activation, but training and checkpoint selection cannot inspect it. Activation requires the applicable `ProtocolFreezeRecord`, selected committee identity, complete training-protocol identity, checkpoint-selection decision, and other owning-specification predicates.

### Explicit E0 serialization

`AtomicReferenceFitRecord` is converted to the exact upstream representation accepted by the runtime lock, normally an explicit atomic-number mapping. A conceptual record name/path is provenance and is never substituted for the numerical `E0s` payload.

### One compatible target label domain per bundle

A target bundle contains one compatible target `LabelDomain` and, when replay is enabled, its separately identified replay head/lineage. Incompatible target electronic-structure domains are not silently merged.

### Export/loader qualification

The adapter qualifies atom order, cell/PBC, selected energy, forces, stress/virial convention, weights, head labels/order, explicit E0 mapping, parser recognition, effective target/replay counts, and downstream element mapping where required. Intended exposure never substitutes for observed loader realization.

## Protocol-matched cross-validation and final training

The current workflow preserves a strict dependency order:

1. freeze one outer partition, feasibility report, and independence evidence;
2. bind each candidate protocol to complete `TrainingProtocolIdentity` and replay/exposure/checkpoint lineages;
3. create independent cross-validation jobs with fold-training, disjoint checkpoint-monitor, and held-out evaluation domains;
4. fit transforms, metrics, E0, difficulty evidence, and target selection using only each fold-training domain;
5. train a fresh model for each fold under the bound checkpoint-control policy;
6. freeze checkpoint choice without inspecting the held-out evaluation fold;
7. evaluate the frozen checkpoint on the held-out fold and aggregate protocol-matched out-of-fold evidence;
8. freeze the chosen protocol/data/selection/stopping/checkpoint/seed policies;
9. fit final training-domain products and train the declared independent final seeds;
10. externally evaluate/admit candidate checkpoints, export the selected target heads, and construct the final committee;
11. emit protocol/committee freeze evidence;
12. calibrate final-committee uncertainty on a dedicated authorized cohort where available;
13. activate sealed evaluation only after all promotion predicates pass;
14. execute bounded deployment verification under the frozen model/runtime identity.

If a protocol intentionally consumes an ordinary monitor during final refit, that loss of independent monitoring is explicit in the protocol/evidence lineage; it cannot be hidden by relabeling the consumed data.

## Training monitoring, stopping, and learning-rate control

Online monitors are deterministic, common protocol inputs rather than resampled per epoch. Lightweight monitoring may control target-oriented stopping or detect unacceptable replay degradation only under the current stopping specification. The held-out cross-validation evaluation fold never controls stopping or checkpoint choice.

Learning-rate scheduling/refinement is part of `TrainingProtocolIdentity`. Scheduler changes, epoch-cap changes, or checkpoint-control changes define a different protocol and require protocol-matched validation rather than being applied after comparison.

## Evaluation and candidate reduction

Checkpoint evaluation proceeds from lightweight online evidence to the current bounded full-evaluation/selection policy without changing the role of the underlying evidence. Screening reduces computation; it does not authorize inspecting locked-test data or changing thresholds after seeing candidate results.

Full candidate metrics are persisted with their exact model/data/runtime identities. Replay retention is a hard admissibility condition rather than a bonus in a combined target score unless the current metric policy explicitly says otherwise. Where physical relaxation/deployment integrity is required, structural failure is a rejection condition independent of numerical force-RMSE ranking.

## Committee, protocol freeze, and sealed evaluation

A committee is constructed only from selected final-run target heads with explicit seed/member identity. `ProtocolFreezeRecord` binds the selected training protocol, model/checkpoint identities, committee identity, and required upstream evidence.

Locked interpolation/challenge evaluation is operationally sealed until the applicable activation predicates pass. Locked evidence cannot retroactively alter training selection, stopping, checkpoint choice, replay policy, calibration policy, or acquisition rules.

## Calibration and active-learning lineage

Committee disagreement is a ranking signal rather than an error guarantee [13, 14]. Numerical uncertainty/acquisition thresholds are calibrated only from predictions of the actual frozen final committee on an authorized calibration cohort.

Calibration identity binds the committee/model digests, training/replay/seed/runtime lineage, precision/backend, calibration cohort, and declared applicability domain. The applicability domain records relevant elements/compositions, thermodynamic/strain ranges, cell sizes, structural/event classes, descriptor-distance ranges, force/stress ranges, and integrity states.

`CalibrationTransferDecision` distinguishes at least:

```text
within_calibrated_domain
rank_only_outside_domain
recalibration_required
rejected_incompatible_domain
```

Without valid final-committee calibration, acquisition is explicitly uncalibrated/rank-only. Locked tests are excluded from calibration and acquisition.

Selection-biased active-learning labels enter a new development/training candidate pool. Existing frame roles are inherited unchanged by default. Independent new evidence may create new calibration/validation/challenge cohorts only under explicit lineage. Repartitioning existing evidence creates a new evaluation lineage rather than silently rewriting the old one.

## Determinism and reproducibility

A reproducible campaign binds source and parser identities, policies/digests, reference-cell/deformation conventions, feature providers, foundation/model/runtime locks, random seeds/dtype/backend, fitted metrics/E0, partition/independence evidence, target selection/coverage policy, training objective/weights, complete protocol identity, exposure realization, replay-retention and checkpoint decisions, committee/protocol freeze, activation/calibration evidence, role inheritance, tie rules, fold assignments, ordered selections, and output checksums as applicable.

Execution-only worker counts, queue completion order, cache location, and storage layout are excluded from scientific identities unless a current specification explicitly declares otherwise.

## Failure semantics

The workflow fails closed when, among other owning-specification conditions:

- source/label identity is unresolved or required labels are invalid;
- incompatible label domains are mixed;
- strain/reference conventions are ambiguous;
- requested evidence roles are infeasible under the declared independence policy;
- monitor/locked evidence reaches a forbidden fitted/selection/calibration/acquisition operation;
- a held-out evaluation fold controls checkpoint choice;
- cross-validation and final training do not share the compared complete protocol identity;
- required MACE/runtime behavior differs from its qualified lock;
- realized target/replay exposure differs from the accepted plan;
- a locked-test path appears in development configuration;
- no checkpoint satisfies mandatory target/focus/replay/integrity constraints;
- replay checkpoint/source lineage is incompatible;
- calibrated acquisition is attempted outside its applicability domain without the declared transfer action;
- active-learning child generation rewrites existing roles without a new evaluation lineage.

Absent rare events, replicas, condition combinations, calibration cohorts, or challenge sets are reported as limitations/coverage gaps rather than fabricated evidence.
