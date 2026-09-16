---
kind: abstraction-concretization-change-plan
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 3
protocol_version: 6.3.0
status: active
created_date: 2026-09-15
branch: design/mlff-pi-train-fps-diversity-restoration
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
supersedes:
  - workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN.md
  - workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_2.md
review_basis: workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_REVISION_2_REVIEW.md
highest_affected_domain: D1
challenge_state: SERIOUS_CHALLENGE
human_ratification: required-before-d1-d2-promotion
---

# MLFF `pi_train` feature-space diversity restoration — Revision 3

## 0. Current disposition

The current production target-order method is under **SERIOUS CHALLENGE** because it permits a valid current `pi_train` to be generated with no structural priority evidence. The current P2 path then reduces to condition round-robin with UID ordering inside each condition. This preserves exact nested prefixes while allowing redundant configurations to occupy early target sets and structurally distinct configurations to appear late for reasons unrelated to the scientific sampling problem.

The protected correction is:

> `pi_train` must be one candidate-independent, coverage-progressive training order. Reuse the largest proven historical/current selection component that satisfies the accepted current D1/D2 method and can live underneath the one current P2/prepared-generation owner.

Revision 3 incorporates the reuse census from Revision 2 and closes its review blockers around DATA6 acquisition, prepared-generation persistence, condition ownership, MVSEL2 policy inheritance, method identity, deleted-code dependency closure, and model-free preparation.

## 1. Protected scientific and architectural invariants

### 1.1 Scientific meaning

The target-size experiment varies training cardinality `N` along one frozen data-membership policy:

```text
T_N = pi_train[:N]
```

Changing `N` adds configurations under the same accepted sampling/coverage method. It does not expose a different selector solution and does not expose an arbitrary UID prefix.

Coverage/diversity governs training membership. EVAL2/CV/qualification govern model behavior. Neither substitutes for the other.

### 1.2 Membership evidence boundary

The baseline restored order may use accepted pre-candidate structural evidence: geometry/cell/deformation, local-environment descriptors, condition identities, geometry-derived event/environment facts, and other explicitly accepted candidate-independent support evidence.

The baseline shall not use DFT energy, force, stress, force/statistical summaries derived from labels, foundation residual/difficulty, candidate model outputs, checkpoint outcomes, EVAL2 outcomes, CV evidence, or production outcomes.

Raw structural descriptors may be computed over a broader authorized population when their producer is partition-independent. Any fitted transform declared as target-order training-fitted shall be fit on its exact accepted fit domain, proposed here as exact `P_train`.

### 1.3 Preserved current architecture

Unless falsification reopens an owner, preserve:

- current exact `U_size -> P_train + M3` split and protected-relation allocation;
- current P2 `condition_id` as the target-size condition authority;
- exactly one current `TargetTrainingOrder`;
- exact nested prefixes;
- current `pi_eval`/M1/M2/M3/EVAL2 semantics;
- common P3 preparation after target-order construction;
- current target-size reducer/operator selection;
- P5 CV/fresh production semantics;
- final-release-only GPU qualification.

## 2. Reuse-first capability census

| Component | Current availability | Current fit | Required disposition |
| --- | --- | --- | --- |
| DATA5 partition/unit evidence | present | useful lineage/correlation/profile input; not target condition/order authority | reuse through current owner where D2 needs it |
| DATA6 structural providers and `build_data6_feature_bundle` | present | can build model-free universal/profile structural evidence | reuse; target-order path must be explicitly model-free |
| `feature_metric.py` fitter/records | present | reusable fitting/scaling/projection/serialization, but default `raw_physical` and default policy include forbidden label/model channels | reuse framework under explicit target-order-safe policy |
| `ExactFPSState` / `_fps_order_matrix` | present | exact bounded FP64 maximin implementation | direct reuse if R0 selects FPS semantics |
| representative/environment/event queue helpers | present | valuable historical coverage capabilities | reuse where accepted by D1/D2 |
| `build_training_selection_plan` | present | close but not current-ready: UID-min anchors, fixed quotas, difficulty, Nmax-only master order, UID fallback, old domain assumptions | adapt as a whole if smaller/cleaner than recomposition |
| coverage-report implementation | present | already provides q50/q90/q95, radius, selected-neighbor, condition/environment/event diagnostics | reuse/adapt preferentially |
| FEAS1/MVIDX1/MVSEL2/REPAIR2/MVSTATE2/MVQUAL implementation | deleted from current main | rich hard-coverage/repair semantics but requires resurrection of sparse-index/state dependency closure | eligible only if R0 proves those extra semantics are required and restoration is best fit |

Historical status is neither approval nor disqualification.

## 3. Reuse resolution Gate R0

Before D2 freezes an exact selector, compare three concretizations against the same accepted current target-order problem:

- **A — adapted current DATA7 stack:** reuse model-free DATA6 + fitted metric + current multi-queue/coverage machinery, correcting only incompatible policy/ownership semantics;
- **B — direct current primitives:** reuse DATA6/metric plus `ExactFPSState`/coverage primitives directly under P2 if the historical whole builder carries unnecessary semantics;
- **C — historical MVSEL2/REPAIR2 resurrection:** restore the coherent deleted dependency set only if its hard multi-family coverage/repair/correlation semantics are accepted current requirements and materially improve fit over A/B.

For each candidate record:

```text
required D1/D2 capabilities preserved
historical capabilities retained/omitted
exact current inputs and fit domain
condition/support behavior
full-order/continuation semantics
leakage boundary
current code availability
required deleted dependency closure
prepared-generation state/persistence
CPU/RAM scaling
historical/current evidence applicability
net architecture/state complexity
```

Choose the **largest semantically compatible reuse unit**. A candidate does not lose because it is old; it loses only when its current-required dependency/policy footprint is worse than another admissible realization.

### 3.1 MVSEL2 policy quarantine

Engine reuse and policy reuse are separate decisions. Historical MVSEL2's scientific inputs and constants—including its historical `0.95` hard family-coverage threshold, witness radii, `1e-14` contender tolerance, correlation policy, representative-gain semantics, difficulty inputs, hard-obligation scoring and REPAIR2 predicates—do **not** become current because the engine is reused.

R0/R1 must map every such predicate to current accepted D1/D2 or remove/reclassify it. The baseline restoration continues to forbid label/model difficulty unless D1 separately promotes that evidence.

### 3.2 Deleted-code closure for candidate C

R0 shall verify actual source availability. Current main does not contain the historical `target_multi_view_selector_v2.py` / `target_multi_view_repair_v2.py` implementation modules. Choosing C therefore means restoring and qualifying the coherent implementation dependency closure needed by the selected semantics, including sparse forward/index types, selector, repair/state and independent qualification where required.

Do not cite a historical benchmark/spec as proof that current code can import a deleted module.

## 4. Exact current input ownership

### 4.1 P2 condition authority

Target-size support/scheduling shall use `TargetSizePopulation.frame(uid).condition_id` as its condition identity. Historical DATA5 unit/condition grouping shall not silently become a second condition owner.

DATA5 may contribute only facts explicitly accepted by D2, such as valid profile/provider lineage or correlation/protected metadata. If a historical selector expects a `by_condition` map, adapt it to the **current P2 condition mapping** rather than deriving an alternate map from DATA5.

### 4.2 Structural evidence acquisition — close B1/B7

Current public `prepare` is the only command allowed to interpret live inputs. Target-order structural acquisition shall therefore occur inside that owner before P2 order publication.

Define one internal preparation operation conceptually equivalent to:

```text
resolve_target_order_structural_evidence(...)
```

Its required behavior is:

1. load/revalidate current source/frame/DATA4/DATA5 ancestry through existing owners;
2. if a reusable current DATA6 record exists, validate exact source/frame/DATA4/DATA5 lineage and project/reuse only structural catalogs authorized by the target-order policy;
3. if required structural evidence is absent or incompatible, call the existing DATA6/structural provider machinery in **model-free mode** to build exactly the missing structural evidence;
4. never acquire a MACE/foundation provider, model checkpoint, descriptor sweep, difficulty catalog or prediction path for baseline target-order preparation;
5. never overwrite a richer unrelated `data6` campaign record merely to obtain a model-free target-order view;
6. publish the exact structural evidence consumed by the target-order fit as part of the immutable prepared generation, so downstream commands never rebuild it.

The target-order structural object may reuse `Data6FeatureBundle` as a narrowed model-free projection if that is the smallest truthful representation. Reusing an existing richer DATA6 means copying/projecting only the authorized structural content into the prepared target-order component; model artifacts are not dragged into target-order identity.

Required negative integration test: `prepare` can produce target-order structural evidence with no MACE import/provider/checkpoint/inference access.

### 4.3 Geometry-safe fitted metric — close leakage gap

Reuse `feature_metric.py` fitting/serialization rather than writing a second fitter.

The historical default feature policy is **not** admissible as-is for `pi_train`: `raw_physical` includes force statistics and pressure/stress label-derived quantities and default policy can include model/difficulty blocks.

R1 shall choose an explicit target-order-safe metric policy. It shall either:

- add/reuse a geometry-only raw block for cell length/angle/volume/deformation coordinates while retaining the existing fitter; or
- omit `raw_physical` after proving accepted universal/profile structural blocks contain all required baseline geometry information.

Exact block weights, dimension normalization, robust scaling, PCA/projection, missing treatment, quantile convention, degeneracy threshold, precision and tie semantics are D2 method fields. Historical values require current justification/sensitivity evidence; simplicity alone is not justification.

### 4.4 Exact fit-domain identity

The fitted target-order metric shall bind exact `P_train`. Do not serialize `FINAL_DEVELOPMENT` if its membership is not exact P_train merely to reuse an old enum.

Reuse `FeatureFitDomain` if it can be truthfully extended with a target-order/P_train kind; otherwise use the smallest equivalent target-order domain record while retaining the existing metric fitter. The domain digest binds exact P_train UIDs plus current split ancestry.

Metamorphic check: changing an M3-only frame cannot alter a P_train-fitted transform/order when P_train and partition-independent raw descriptors remain unchanged.

## 5. Selector reuse requirements

### 5.1 Candidate A whole-builder adaptation

If `build_training_selection_plan` is selected as the largest clean reuse unit, change only incompatible semantics:

- candidate set exactly current P_train;
- condition support comes from current P2 condition mapping;
- UID-min mandatory anchors are replaced only if accepted D2 says they are not the current support rule;
- label/model difficulty queue disabled for baseline;
- representative/environment/event queues retained only where D1/D2 accept them;
- fixed historical quota fractions retained only if explicitly reaccepted;
- no ordinary UID fallback when structurally non-tied candidates remain;
- one full exact order or authenticated exact continuation, not only `max(target_sizes)`;
- result is consumed into one current `TargetTrainingOrder`, not promoted as a second current order authority.

### 5.2 Candidate B primitive composition

If whole-builder adaptation would require more adapters/state than direct composition, reuse the exact current numerical primitives under P2. Do not reimplement FPS distance updates, robust metric machinery or coverage scoring merely to rename them.

A newly written orchestration loop is acceptable only as the minimal glue required to express accepted D2 with those existing primitives.

### 5.3 Candidate C historical chain

If MVSEL2/REPAIR2 wins R0, restore exactly the coherent dependency closure selected by current semantics and integrate its output underneath current P2. Historical campaign record names, migration/currentness authority and pre-V7 public topology are not restored unless an accepted current invariant genuinely requires that state.

If restartable continuation state is required, MVSTATE2 is eligible for reuse; if a complete order is cheap enough, do not add continuation state merely for historical fidelity.

## 6. Full-order semantics — close historical Nmax gap

`TargetTrainingOrder` is an exact permutation of all P_train. Historical DATA7 planning only through `max(target_sizes)` is insufficient by itself.

R1/D3 shall choose one:

1. **complete-order realization:** construct and persist the exact full permutation; or
2. **exact-continuation realization:** persist authenticated continuation state such that future suffix ranks continue the same frozen method without changing prior ranks.

Arbitrary UID suffix completion is prohibited.

Prefer complete order unless representative-scale evidence justifies continuation complexity.

## 7. Prepared-generation persistence and authentication — close B2/B5

### 7.1 Current fact

The current prepared-generation schema v1 has a fixed component set and type map and does not contain target-order structural evidence, fitted metric, or coverage evidence. A digest field by itself is insufficient if no bound object can be authenticated on reload.

### 7.2 Required v2 prepared representation

Version the prepared-generation representation coherently for the restored target-order method. Prefer explicit reuse of existing record types as prepared components:

```text
manifest
source_catalog
frame_catalog
source_authority
frame_authority
feature_evidence
neutral_base
split_exclusion
target_order_features      # model-free structural evidence; preferably Data6FeatureBundle or accepted projection
target_order_metric        # reuse FittedFeatureMetric/current fitted-metric record
target_order_aggregate     # current TargetSizeStatisticalAggregate with one TargetTrainingOrder
target_order_coverage      # reuse/adapt SelectionCoverageReport
common
```

Exact component names may follow current naming conventions, but ownership must remain one prepared generation. Do not create another SQLite/currentness owner.

The prepared loader shall authenticate components in dependency order and verify cross-lineage. Current restored-policy generations require the new component set. Historical v1 prepared generations may remain readable only as historical/old-policy evidence where useful; they cannot be accepted as current restored-policy generations.

### 7.3 Selection-evidence binding

Do not leave `TargetTrainingOrder.selection_evidence_digest` as an unresolvable hash.

Define the accepted digest from the exact current ordering inputs, at minimum:

```text
target-order structural-evidence identity
+ fitted metric identity
+ accepted selector/method policy identity
+ any accepted non-metric support/event/correlation evidence used by ranking
```

Population/split/policy/order fields already carried elsewhere need not be duplicated if the binding is unambiguous. On prepared reload, verify that the `TargetTrainingOrder` evidence digest equals the digest reconstructed from the bound prepared target-order components.

Coverage evidence is diagnostic and binds the resulting order/metric; it is not part of the causal ranking evidence unless D2 explicitly uses it during selection.

### 7.4 Preparation configuration identity

The current preparation configuration identity is insufficient if target-order feature/metric/selector policy can change independently.

The accepted target-order method identity shall be included in preparation-owned configuration identity and P2/aggregate ancestry. Prefer nesting/reusing an existing policy record if R0 selects one; otherwise define the smallest current target-order policy identity. It must bind all order-changing D2 settings and provider/schema identities that are configuration-controlled.

Any order-changing policy edit creates a new prepared generation before downstream exposure. Scheduling/report-only settings remain outside scientific identity.

## 8. D1/D2 method Gate R1

After R0 selects the reuse candidate:

### D1 amendment

Require:

- candidate-independent coverage-progressive `pi_train`;
- preservation of accepted hard condition/support obligations;
- separation of membership support from training-loss weighting;
- explicit leakage boundary;
- coverage diagnostics are not model-accuracy gates.

### D2 amendment

Define the selected historical/current mechanism exactly enough to reconstruct membership without code archaeology:

- accepted structural feature families and their scientific role;
- exact fit domain;
- normalization/metric/block weighting/projection/missing semantics;
- accepted representative/support initialization;
- FPS/multi-queue/MVSEL ranking semantics as selected by R0;
- condition/support scheduler and relation to P2 condition identity;
- event/environment/correlation use, if any;
- precision/reduction/tie semantics;
- full-order/continuation method;
- coverage diagnostics and their interpretation;
- numerical/resource failure semantics.

Do not force Revision-1's newly invented condition-local median-seed FPS method if a previously qualified mechanism satisfies the current contract more completely.

Independent D1/D2 review and human ratification are required before durable promotion.

## 9. Implementation sequence

### R2 — target-order input resolver

Implement/reconcile model-free structural acquisition inside current `prepare`; reuse compatible existing DATA6 structural records and existing providers; no model access.

### R3 — metric/domain integration

Reuse the current fitted-metric implementation with exact P_train domain and accepted safe block policy. Add only the minimum geometry-only extractor/domain-kind changes required by R1.

### R4 — selector integration

Reuse the R0-selected engine at the largest compatible granularity. Current P2 remains the one order owner. Change `ResolvedTargetSizePolicy.training_order_policy`/schema or equivalent method identity so old UID-capable generations cannot masquerade as restored-policy evidence.

### R5 — full-order closure

Implement complete order or exact continuation; test ranks beyond historical Nmax.

### R6 — coverage scorer

Reuse/adapt current coverage scorer and publish authenticated diagnostic evidence. At minimum retain max covering radius, q50/q90/q95, selected-neighbor metrics and condition support; retain environment/event diagnostics where the accepted evidence is available.

For exact nested prefixes, global candidate-to-selected covering radius shall be nonincreasing with N within accepted finite-precision comparison semantics.

### R7 — prepared-generation v2/currentness

Publish/authenticate target-order feature, metric, aggregate/order and coverage components under the one prepared generation. Extend loader/type map/schema coherently. Old restored-incompatible generations are stale/historical, not migrated into current method authority.

### R8 — representative CPU/RAM qualification

Historical DATA7/MVSEL2 performance evidence is a prior, not current acceptance. Measure current population size, condition count, feature dimension, feature-build time, fit time, selector time, coverage time, peak RSS and durable/temporary state.

Do not introduce a persistent dense all-pairs matrix. If selected current DATA7 reuse is not viable, reconsider qualified historical exact algorithms including MVSEL2 before weakening diversity.

### R9 — assembled real-owner acceptance

Execute:

```text
cold/rebuilt prepare
reuse-path prepare with unchanged lower records
prepared-generation publication
fresh-process prepared reload
candidate memberships at multiple N including suffix/full-order coverage
manual select-target-size
automatic diagnostic using the same prefixes
cross-validation freeze/re-authentication
```

No helper-only selector test substitutes for this path.

## 10. Required falsification and regression evidence

At minimum:

1. UID redundancy trap.
2. single-condition diversity trap.
3. multi-condition/hard-support starvation counterexample.
4. duplicate/near-duplicate feature points.
5. constant/redundant coordinate sensitivity.
6. feature serialization/column-order invariance.
7. UID renaming outside genuine ties.
8. DFT energy/force/stress perturbation with unchanged authorized membership evidence leaves `pi_train` unchanged.
9. M3-only perturbation cannot alter P_train-fitted transform/order under fixed P_train/raw partition-independent evidence.
10. model-free prepare negative test proving no MACE/provider/checkpoint/inference access.
11. reusable DATA6 present and valid -> structural evidence reused/revalidated.
12. DATA6 absent/stale/incompatible -> only required model-free structural evidence rebuilt; unrelated richer DATA6 record is not destructively replaced.
13. P2 condition identity differs from a historical DATA5 grouping fixture -> selector follows current P2 identity or fails explicit incompatibility; it never silently substitutes DATA5 grouping.
14. old prepared v1/old target-order policy cannot load as current restored-policy authority.
15. target-order policy change invalidates prepared generation; CV-only/execution-only change does not.
16. evidence-digest mismatch between prepared metric/features and `TargetTrainingOrder` fails closed.
17. ranks beyond historical `max(target_sizes)` continue the accepted method, never UID suffix.
18. historical-equivalence tests for every reused numerical kernel whose semantics are claimed unchanged.
19. if MVSEL2 is selected, full-forward/lazy and any retained repair/qualification equivalence required by its accepted current semantics is rerun on restored code.

Compare old UID/condition order versus restored order at the same N on realistic/current structural data using accepted coverage/support diagnostics. Promotion requires evidence that the lost sampling capability is actually restored, not merely a changed order.

## 11. Invalidation and preserved evidence

Changed target-order method/metric/order invalidates materially dependent:

- restored-policy P2 aggregate/order identity;
- exact T_N memberships/prefix digests;
- automatic screen evidence tied to old memberships;
- provisional/frozen target bindings tied to old order;
- post-selection CV/production descendants whose target binding changes.

Preserve when owner-valid:

- source/frame/DATA4 records;
- DATA5;
- reusable DATA6/raw structural caches that independently validate;
- P_train/M3 split algorithm and evidence when parent identities remain unchanged;
- pi_eval/M1/M2/M3 semantics/evidence unaffected by target-order membership;
- TRAIN2/EVAL2 architecture, replay, CV threshold policy, GPU scheduler/CUDA lifetime, storage architecture.

A prior passing target-size/CV/production observation cannot confirm a different T_N.

## 12. Capability transfer map

| Capability | Historical/current source | Revision-3 disposition |
| --- | --- | --- |
| one exact master order/prefix chain | current P2 + DATA7 + MVSEL2 | preserve with `TargetTrainingOrder` as sole current authority |
| feature-space diversity | DATA7 FPS + MVSEL2 | restore; prefer current reusable implementation selected by R0 |
| representative support | DATA7 representative queue + MVSEL2 representative gain | retain if D1/D2 accepts; reuse old rule rather than inventing new one by default |
| condition support | current P2 scheduler/qualification + historical anchors/hard obligations | P2 condition identity remains current owner; exact D2 rule chosen at R1 |
| environment/species coverage | current DATA6/DATA7 | reuse where scientifically accepted |
| rare geometry events | DATA4/DATA6/DATA7 | eligible when pre-candidate and accepted |
| label/model difficulty | historical DATA7/MVSEL inputs | excluded baseline unless separately promoted |
| bounded exact FPS | current `ExactFPSState` | direct reuse if FPS selected |
| hard multi-family sparse coverage | MVSEL2 | restore only if current D1/D2 requires it |
| prefix repair | REPAIR2 | restore only if current accepted hard property requires repair |
| independent coverage scoring | current DATA7 report / historical MVQUAL | use current scorer first; MVQUAL only with retained hard semantics |
| restartable selector state | MVSTATE2 | only if exact continuation is justified over complete order |
| historical fixed quotas/thresholds/tolerances | DATA7/MVSEL policies | no automatic promotion; each requires current D2 acceptance |

## 13. Review/reopen triggers

Reopen D1 for evidence that structural coverage is not part of the target-size interpretation, that accepted support and diversity are scientifically incompatible, or that allowed pre-candidate features cannot represent the required support claim.

Reopen D2 for materially arbitrary feature metric/weights, unreproducible rank/tie semantics, required historical capability omitted by R0, or inability to define exact full-order/continuation semantics.

Reopen D3 if selected historical machinery requires a larger coherent state/dependency boundary than this plan represents, if the one prepared-generation owner cannot bind it without duplicate currentness, or if downstream recomputation becomes necessary.

If the leading current DATA7 reuse path fails capability/resource qualification, explicitly reconsider MVSEL2/REPAIR2 before creating a third selector generation or dropping diversity again.

## 14. Workplan acceptance gate

This plan is implementation-ready only when R0 and R1 resolve the exact reused method and required human ratification. Implementation completion requires R2-R9 plus all applicable falsification/regression and impact closure.

The final product must satisfy all of the following:

1. no current restored-policy `prepare` can construct `pi_train` from empty/UID-only scientific priority;
2. target membership is candidate-independent and leakage-safe;
3. current P2 condition identity remains unique;
4. reused historical components carry only current-accepted policy semantics;
5. one immutable prepared generation authenticates exact structural evidence, metric, order and coverage diagnostics;
6. `TargetTrainingOrder` is the sole current order authority;
7. every T_N is an exact prefix of one full/continuable order;
8. coverage/support diagnostics demonstrate restored diversity capability;
9. old dependent target evidence is stale rather than silently reused;
10. representative CPU/RAM evidence is acceptable or routes to an already-proven exact historical alternative;
11. no GPU qualification is claimed by this cycle.

Until those conditions are satisfied, the current UID-capable target-order method remains under **SERIOUS CHALLENGE**.