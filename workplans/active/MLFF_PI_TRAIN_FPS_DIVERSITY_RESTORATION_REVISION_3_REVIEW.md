# Revision 3 workplan review — `pi_train` diversity restoration

Date: 2026-09-15
Reviewed: `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_3.md`
Basis: mdstats `e72090e21cec5311ce87745b03603f8783cd15a7`
Disposition: **PASS AS WORKPLAN — no remaining plan-level blocker found.**

This is a workplan/design-readiness disposition. It is **not** D1/D2 promotion, implementation acceptance, or scientific-method ratification. Revision 3 intentionally keeps implementation blocked on Gate R0 reuse adjudication, Gate R1 exact D1/D2 method closure, independent D1/D2 review, and required human ratification.

## 1. Serious Challenge status

The underlying current behavior remains correctly classified as a Serious Challenge: current production can construct `pi_train` with empty structural priority evidence and therefore UID-based within-condition order. Revision 3 does not conceal that defect behind implementation language.

## 2. Reuse strategy review

PASS.

The workplan no longer treats historical machinery as presumptively undesirable. It orders concretization choices by semantic compatibility and reuse granularity, and explicitly compares:

- adapted still-current DATA7 machinery;
- direct composition of still-current exact FPS/coverage primitives; and
- resurrection of the deleted MVSEL2/REPAIR2 dependency closure.

This is the correct decision boundary. Existing current machinery is preferred only because it has a materially smaller current dependency footprint, not because the historical chain is old. MVSEL2 remains eligible if its additional hard-coverage/repair semantics prove necessary.

## 3. Current pipeline fit

PASS.

Revision 3 now respects the real public prepare architecture:

- `_prepare_catalog` is not assumed to run merely because target-order evidence is needed;
- reusable DATA6 is revalidated rather than trusted by presence;
- missing structural evidence is built through existing DATA6/structural owners in an explicitly model-free path;
- a richer unrelated DATA6 record is not destructively replaced;
- structural target-order evidence is published with the immutable prepared generation and never reconstructed downstream.

This closes the principal integration gap from Revision 2.

## 4. Authority/ownership review

PASS.

The plan keeps:

- P2 `TargetSizePopulation.condition_id` as the sole target-size condition authority;
- `TargetTrainingOrder` as the sole current training-order authority;
- current P2/prepared generation as currentness owner;
- historical selector/plan/state types subordinate if reused.

It explicitly prevents DATA5 historical grouping, `TrainingSelectionPlan`, MVSTATE2, or old campaign record families from silently becoming parallel current authority.

## 5. Numerical/method review

PASS AS PLAN.

The plan correctly leaves exact D2 policy unresolved until R0 determines which proven engine is being reused. This avoids prematurely inventing a new median-seed/condition-local-FPS method and also avoids blindly inheriting historical constants.

It closes the prior Gate-A hazards by requiring current adjudication of:

- metric feature families and weights;
- exact P_train fit domain;
- projection/scaling/missing semantics;
- support/representative initialization;
- queue/interleaving or MVSEL ranking semantics;
- finite-precision/tie behavior;
- full-order/continuation semantics.

Historical MVSEL2 thresholds, witness radii, tolerance, difficulty and repair policy are explicitly quarantined from automatic promotion.

## 6. Leakage review

PASS.

The plan identifies the historical `raw_physical` feature block as unsuitable as-is because it contains force/stress-derived values, and it requires a geometry-safe metric policy. It also adds a real integration negative test proving baseline target-order preparation does not access MACE/provider/checkpoint/inference machinery.

## 7. Persistence/currentness review

PASS.

Revision 3 recognizes that prepared-generation v1 has a fixed component/type map and therefore treats target-order evidence persistence as a real prepared-generation schema/loader change. It requires bound structural evidence, fitted metric, aggregate/order, and coverage evidence, plus reconstruction/validation of the `selection_evidence_digest` from actual prepared children.

The exact component spelling shown in the illustrative v2 list is not itself frozen. Implementation should preserve the existing component name `aggregate` unless a concrete owner reason requires renaming; no semantic benefit follows from renaming it to `target_order_aggregate`.

Old prepared generations may remain historical/readable where useful but cannot satisfy the restored target-order policy.

## 8. Full-order review

PASS.

The plan closes an important mismatch in historical DATA7 behavior: `TrainingSelectionPlan` historically materialized only through `max(target_sizes)`, whereas current `TargetTrainingOrder` is an exact permutation of all P_train. Revision 3 requires either a complete exact order or authenticated exact continuation; arbitrary UID suffix completion is forbidden.

## 9. Evidence/oracle review

PASS.

The falsification set covers the material failure modes:

- UID clustering;
- single-condition redundancy;
- support starvation;
- duplicate points;
- redundant/constant coordinates;
- serialization order;
- UID renaming;
- label leakage;
- P_train/M3 fit-domain leakage;
- model-free preparation;
- DATA6 reuse/rebuild routing;
- condition-owner conflict;
- prepared-generation stale-policy rejection;
- evidence-digest mismatch;
- full suffix behavior;
- historical-kernel equivalence.

The final acceptance route crosses the real prepare -> prepared publication -> reload -> membership -> manual/auto selection -> freeze boundary, so helper-level green tests cannot counterfeit completion.

## 10. Resource/scaling review

PASS.

The plan preserves the historical bounded exact-selection design prior, requires fresh current CPU/RAM evidence, forbids introducing a persistent dense all-pairs matrix, and explicitly routes back to proven historical exact methods such as MVSEL2 if the current DATA7 reuse candidate cannot satisfy production-scale requirements. GPU qualification remains correctly deferred.

## 11. Impact and documentation review

PASS.

Dependent target memberships/screens/bindings/CV/production ancestry are invalidated when `pi_train` changes, while source/frame/DATA4/DATA5 and independently valid reusable structural caches are preserved. This follows dependency rather than stage-wide invalidation.

A semantic-evolution record should explicitly state that the August V7 cutover retired selector topology and accidentally dropped the still-required diversity/coverage capability. Historical mechanism retirement should not be described as evidence that diversity itself was rejected.

## 12. Final review decision

**PASS AS WORKPLAN.**

No remaining plan-level blocker was found after the Revision-3 closure. The canonical active plan is `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_3.md` as recorded by `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_CURRENT.md`.

Implementation must not start by arbitrarily choosing candidate A/B/C. It starts with R0 reuse/capability adjudication, then R1 exact D1/D2 method closure and independent/human acceptance. A failure at either gate reopens the owning layer rather than being patched in D4.