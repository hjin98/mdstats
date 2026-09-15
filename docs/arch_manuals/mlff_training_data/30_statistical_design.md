# Part III - Evidence flow and fitted-product integration

## Purpose and boundary

This chapter owns the D3 integration structure that carries accepted D1 evidence semantics and D2 constructions into executable MLFF products. Scientific meanings such as independence, leakage, target-size interpretation, objective semantics, and validity are owned by D1. Numerical definitions such as correlation units, deterministic orders, common fitting, weighting algorithms, fold construction, common-monitor construction, and transfer-identifiability tests are owned by D2.

For `TargetTrainingOrder` / `pi_train`, the accepted scoped method owners are `docs/methods/mlff_target_training_order_scientific_method.md` and `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`, and the canonical D3 subsystem owner is `45_target_training_order.md`.

D3 therefore answers a narrower question: which software owner may create, persist, consume, or invalidate each product, and in what dependency direction?

## Evidence-role pipeline

The architectural flow is:

```text
canonical frame/evidence authority
  -> neutral statistical substrate and protected-relation authority
  -> exact P_train + M3 split
  -> selector input lineage on exact P_train
  -> sole fitted TargetCoverageReference
  -> canonical target-order obligations
  -> shared FEAS1/NEIGHBOR1 -> MVIDX -> MVSEL2/REPAIR2 -> independent MVQUAL
  -> one complete TargetTrainingOrder and exact configured prefixes
  -> common target-size training preparation
  -> target-size execution/reducer evidence
  -> operator-owned provisional design
  -> cross-validate admission / frozen target bindings
  -> campaign-common post-selection target monitor
  -> selected-only post-selection fold products
  -> final-production products
```

`pi_eval/M1/M2/M3` remain under their existing current owners. Each arrow is one-way. A downstream consumer may challenge an upstream product with evidence, but it cannot mutate or reinterpret the upstream product in place.

The canonical D1 role semantics and D2 relation/allocation algorithms are not repeated here. Their D3 consequence is that role-bearing and membership-bearing artifacts must bind exact parent identities, and consumers must reject stale, foreign, or incomplete ancestry rather than reconstructing a convenient substitute.

## Target-order fitted evidence versus common training preparation

Two fitted stages exist on opposite sides of the target-order boundary and are separate architectural owners.

### Target-order selector evidence

DATA6/DATA7-era surfaces may provide authenticated raw descriptors, provider outputs, condition/event/environment evidence, and lineage needed by the current target-order method. They do **not** own a current fitted selector metric/reference.

On exact current `P_train`, `TargetCoverageReference` is the sole selector-specific fitted numerical product. It owns the fitted statistics/reference state consumed by FEAS1, NEIGHBOR1/MVIDX, MVSEL2/REPAIR2, and independent MVQUAL under the accepted scoped D2 method. Historical DATA7 scaler/PCA/metric/reference ownership is retired as current authority and may survive only as lineage/input provenance where explicitly consumed.

The canonical membership-obligation authority is constructed once from accepted automatic evidence, TargetCoverageReference-derived extent semantics, and current P2 explicit support requirements. FEAS1, MVIDX, MVSEL2, REPAIR2, and MVQUAL consume or represent this one authority rather than projecting their own obligation semantics.

These selector-evidence owners do not own candidate model outcomes, target size, P3 reducer decisions, post-selection CV, replay, or production.

### Common target-size training preparation

After the target-size split and canonical orders exist, the P3 preparation owner publishes one `TargetSizeCommonPreparation` for the accepted training pool. Candidate execution consumes projections of that product. It does not create one independent fitted preparation per target size or optimizer seed.

This P3 common preparation is not the current foundation-P5 preparation authority. Restored foundation P5 projects only genuinely shared component owners into its own method/preparation lineage; P3-only objective, weighting, or harness fields cannot become hidden P5 currentness parents merely because they are bundled in a P3 common policy.

Exact fitted quantities and projection semantics are D2. Exact schema, serialization, policy fields, and resolver code are D4. D3 requires one authenticated owner per fitted product and one dependency direction.

## Campaign-common post-selection target monitor

Post-selection checkpoint control consumes one immutable campaign-common target monitor, `M_mon`, constructed once from the neutral authorized `OUTER_MONITOR` parent. `M_mon` is external to selected-fold membership. It is reused unchanged across every selected size, CV fold, CV seed, and final-production seed/run that belongs to the same current campaign/method lineage.

The common-monitor membership owner and the protected-relation-separation owner are distinct:

1. the monitor owner deterministically constructs the exact D2 membership from the label-usable neutral parent; then
2. the canonical P1 protected-relation authority proves that the realized monitor is separated from every governed selected target membership.

A selected-only relation projection cannot prove this cross-role claim because it deliberately excludes outside frames. Relation conflicts fail closed; they do not cause monitor members to be filtered, replaced, or resampled.

The monitor record is a plan ancestor. Every current CV and final-production plan binds the same immutable monitor-record digest. Fewer than the accepted exact cardinality is typed P5 infeasibility, not a smaller successful monitor.

## Post-selection selected-fold products

After `cross-validate` freezes a target binding, the post-selection owner may create fold-local products whose fit domain is the fold-authorized selected training partition. Such products are descendants of the frozen binding and fold plan. They cannot change frozen target membership, create another target-size order, or become reusable outside the lineage they name.

Selected-fold membership contains only:

```text
gradient-training membership
held-out outer-evaluation membership
accepted purge/exclusion membership
```

The target checkpoint monitor is not fold-local membership. It is the external campaign-common `M_mon` described above. Replay monitoring remains a separate replay-domain interface.

## Foundation-P5 fitted preparation

The existing atomic-reference fitter remains the sole E0 solver. Foundation adaptation uses that owner in selected-foundation-head residual mode and adds a fitted-preparation transfer-validation responsibility; it does not create a second solver.

For foundation modes, fitted preparation binds the exact authorized fit membership, selected foundation checkpoint/head and foundation prediction/E0 inputs, residual-fit result, and the composition-transfer evidence required by D2. Geometry/composition information from the common monitor or held-out evaluation may be inspected only to establish required composition classes; their labels do not enter the fit.

A current foundation-P5 fitted preparation cannot carry inert P3 objective/configuration-weight ancestry. If scratch and foundation preparation share one implementation type, D4 must make the representation tagged and mode-disjoint so forbidden cross-mode fields fail closed rather than being ignored or digested.

## Objective, weighting, and exposure integration

D1/D2 distinguish global training objective, per-configuration weighting, local property-availability masks, checkpoint/adaptive-stop score weights, and runtime exposure. D3 preserves those separations by routing each value from its single resolver/owner into the executable training plan without introducing a second policy surface.

Foundation P5 resolves its fixed accepted UniversalLoss objective through the P5 method owner and MACE adapter seam. P3 and P5 scratch retain their separately accepted weighted objective/weighting owners. The architecture therefore requires mode-specific execution routing; a global loss-family switch is not an admissible repair.

Retired target/replay training-head scalar weights have no current P5 owner. Their removal must not remove the separately owned target/replay checkpoint/adaptive-stop score weights.

The accepted foundation-P5 stochastic exposure includes the authenticated pre-shuffle replay/`pt_head`-first then target layout, no implicit target duplication, accepted shuffle/seed behavior, `drop_last=true` update geometry, and the single-process execution boundary. D4 owns exact fields/source probes; D3 owns the fact that one execution seam must realize the accepted method rather than a second sampler/trainer.

## Identity and invalidation

A fitted product identity binds, as applicable:

- exact parent evidence or membership;
- fitting/method policy identity;
- fit domain;
- required foundation/head or external-model identity;
- common-monitor ancestry where the product consumes it;
- transfer/separation evidence required for admission; and
- the representation version needed for authenticated reuse.

For the target-order subsystem, `TargetCoverageReference` binds exact `P_train` and its accepted selector-input/provider parents. The canonical obligation authority, NEIGHBOR1/MVIDX, final order/repair ancestry, and MVQUAL evidence bind their true semantic parents as defined in `45_target_training_order.md`; execution-only queue/cache/mmap choices do not become fitted identity.

Invalidation follows semantic dependency rather than pathname proximity. A target-order D1/D2/policy-parent change invalidates the dependent restored selector generation, while an obligation-only change need not invalidate an authenticated NEIGHBOR relation whose true geometry/reference parents are unchanged. A P5-only method-generation change does not invalidate unchanged P3 evidence. A P3-only objective/weighting edit does not invalidate foundation P5 when no real shared owner changed. Conversely, a true P5 method, common-monitor, foundation-head, fitted-preparation, or transfer-evidence change invalidates the descendants that consume it.

Historical weight-bearing foundation preparations, fold-local checkpoint-monitor schemas, M3-dependent P5 publication records, broad `TrainingProtocolIdentity` payloads, and retired DATA7 fitted-selector references may remain readable as historical provenance where supported, but they cannot become current authority merely because they deserialize.

## Failure routing

D3 routes typed failure rather than converting it into another evidence role. Typical examples include unavailable labels, incompatible ancestry, target-order global/rung infeasibility, exact-monitor infeasibility, protected-relation collision, failed fitted preparation, failed composition transfer, stale lineage, unsupported distributed foundation execution, and unavailable execution capability.

If the failure exposes a contradiction in scientific meaning, route to D1. If it exposes a numerical-method contradiction, route to D2. If accepted D1/D2 is coherent but component ownership or dependency flow is defective, it is a D3 issue. Schema/parser/implementation defects under a coherent architecture remain D4.
