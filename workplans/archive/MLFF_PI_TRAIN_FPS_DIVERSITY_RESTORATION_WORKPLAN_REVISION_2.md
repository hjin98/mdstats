---
kind: abstraction-concretization-change-plan
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 2
protocol_version: 6.3.0
status: active
created_date: 2026-09-15
branch: design/mlff-pi-train-fps-diversity-restoration
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
supersedes: workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN.md
highest_affected_domain: D1
challenge_state: SERIOUS_CHALLENGE
human_ratification: required-before-d1-d2-promotion
---

# MLFF `pi_train` feature-space diversity restoration — Revision 2 reuse-first workplan

## 0. Disposition and governing correction

The current target-size method has a real adequacy defect: ordinary production `prepare` constructs the P2 aggregate without target-training selection evidence, so current D2 may legally reduce `pi_train` to condition round-robin with UID order inside each condition. This preserves nestedness but does not preserve structural diversity or progressive feature-space coverage. The target-size learning curve can therefore vary with arbitrary record order rather than only with training-set cardinality under one scientifically meaningful sampling policy.

This remains a **SERIOUS CHALLENGE to current D1/D2 target-order adequacy**.

Revision 1 correctly identified the lost capability but was too prescriptive about avoiding historical machinery and prematurely froze a newly described condition-local FPS method. Revision 2 replaces that stance with the following rule:

> **Reuse the largest proven historical component that still satisfies the current D1/D2 contract and can be subordinated cleanly to the current P2/prepared-generation owner. Alter or remove only incompatible semantics. Write replacement machinery only where no compatible implementation remains.**

A component is not disqualified because it is old or retired. Conversely, historical qualification does not make obsolete scientific policy current. Reuse is decided by current semantic fit, ownership fit, leakage safety, exact-prefix behavior, resource fitness, and evidence.

The current one-study architecture remains protected:

```text
U_size -> exact current P_train/M3 split
       -> one immutable pi_train
       -> T_N = pi_train[:N]
       -> one P3 target-size screen/reducer
       -> operator selection
       -> post-selection CV
       -> fresh production
```

The repair concerns **how `pi_train` is constructed**, not how `N` is selected.

## 1. Protected outcome and upstream contract

### 1.1 D1 capability requirement

D1 shall require that `pi_train` be one candidate-independent, coverage-progressive training order. Subject to accepted hard support/condition constraints, early and successive prefixes must deliberately represent the authorized structural configuration space rather than inherit UID order.

D1 shall keep distinct:

- **membership/support design** — which configurations enter each nested `T_N`;
- **training-loss influence** — weights/masks/objective coefficients applied after membership exists; and
- **model adequacy** — EVAL2/CV/qualification observations.

Coverage is a membership property, not an accuracy claim. A good geometric covering radius does not pass EVAL2, and EVAL2 does not justify arbitrary target membership.

### 1.2 Candidate-independent evidence boundary

The baseline current membership method may use only evidence authorized before candidate training. Geometry, structural/environment descriptors, condition identities, protected-event facts, and other genuinely pre-candidate structural evidence may be considered if D1/D2 accept their role.

DFT energy/force/stress values, force statistics derived from DFT labels, foundation residuals/difficulty, candidate model predictions, checkpoint behavior, target-size EVAL2 outcomes, post-selection CV, and production outcomes shall not affect the baseline `pi_train`.

### 1.3 Current invariants preserved

Unless concrete falsification reopens them, preserve:

- current exact `U_size -> P_train + M3` split;
- inherited protected-relation disjointness;
- one current P2 target-order owner;
- exact nested prefixes `T_N = pi_train[:N]`;
- current `pi_eval`/M1/M2/M3/EVAL2 semantics;
- common P3 candidate-training preparation after target-order construction;
- target-size reducer and operator-owned selection;
- P5 CV and fresh production semantics;
- final-release-only GPU qualification policy.

## 2. Historical applicability and PEM basis

The repository publication at basis commit `e72090e21cec5311ce87745b03603f8783cd15a7` contains `PROJECT-ENGINEERING-MEMORY.md`, whose admitted memory is partial and reconciled only through `4eabe2ae9783c7ff92f3a1093c37502a01380812`. That limitation is explicit; absence after that watermark is not evidence of no relevant history. This workplan therefore combines applicable PEM guidance with direct bounded historical intake over the target-selection lineage through the basis commit.

```yaml
pem_basis:
  accepted_project_state: e72090e21cec5311ce87745b03603f8783cd15a7
  accepted_pem: hjin98/mdstats@e72090e21cec5311ce87745b03603f8783cd15a7:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: SP-001
    disposition: APPLICABLE
    reason: prefer restoring responsibility through an existing real owner/component over adding duplicate selector ownership or translation machinery.
  - id: SP-002
    disposition: APPLICABLE
    reason: selection metric/order identities and prepared ancestry must fail closed on mismatch or staleness.
  - id: SP-003
    disposition: APPLICABLE
    reason: fitted selection evidence and pi_train are immutable preparation products reused downstream.
  - id: SP-004
    disposition: APPLICABLE
    reason: acceptance must exercise real prepare -> persisted generation -> reload -> target membership consumers.
  - id: FF-005
    disposition: APPLICABLE
    reason: downstream commands must consume immutable preparation-owned selection state rather than reconstruct it.
  - id: FF-001
    disposition: NOT_APPLICABLE
    reason: baseline restoration excludes model-dependent membership and does not alter MACE model construction.
  - id: FF-002
    disposition: NOT_APPLICABLE
    reason: TRAIN2 restart ownership is unchanged; only target-generation ancestry/currentness is affected.
  - id: FF-003
    disposition: NOT_APPLICABLE
    reason: destructive storage routing is unchanged.
  - id: FF-004
    disposition: NOT_APPLICABLE
    reason: GPU scheduling/CUDA lifetime is unchanged.
```

## 3. Reuse census against the current pipeline

The following census is a design input, not historical authority.

| Historical/current component | Current state | Compatibility with current `pi_train` | Revision-2 disposition |
| --- | --- | --- | --- |
| current DATA5 partition/unit evidence | present/current | already supplies condition/unit/protected-relation context; not itself target-order authority | **REUSE AS CURRENT INPUT** where exact lineage is useful |
| `build_data6_feature_bundle` and universal/profile structural providers | present/current | supports model-free structural selection evidence and current lineage validation | **REUSE WITH CURRENT PREPARE BINDING**; model/difficulty paths off for baseline |
| `feature_metric.py` fitted metric/scaling/PCA infrastructure | present/current | strong reusable fitter/serialization, but default `raw_physical` contains force/stress label-derived coordinates and default policy contains model/difficulty blocks | **REUSE FRAMEWORK, NOT DEFAULT POLICY**; define target-order-safe block policy/domain |
| `ExactFPSState` / `_fps_order_matrix` | present/current | exact bounded FP64 incremental maximin engine with O(N) nearest-distance state | **REUSE DIRECTLY** if accepted D2 uses FPS/maximin |
| structural/environment queue helpers in `selection.py` | present/current | already express generic/profile environment diversity | **REUSE WHERE D1/D2 RETAIN THAT CAPABILITY** |
| `build_training_selection_plan` | present/current | has exact master-prefix concept and multiple useful queues, but currently embeds historical fixed quotas, UID-min condition anchors, difficulty, Nmax-bounded order, UID fallback and old DATA7 domain assumptions | **ADAPT IF THIS IS THE SMALLEST CLEAN CHANGE; NOT AS-IS** |
| `TrainingSelectionPlan` / `SelectionMasterEntry` record shapes | present/current | useful internal representation, but current canonical owner is `TargetTrainingOrder` | **REUSE INTERNALLY ONLY IF IT AVOIDS DUPLICATION**; do not create second current authority |
| `build_selection_coverage_report` and coverage records | present/current | already computes condition/environment/event coverage, q50/q90/q95, max radius and selected-neighbor diagnostics incrementally | **REUSE/ADAPT PREFERENTIALLY** |
| FEAS1/MVIDX1/MVSEL2/REPAIR2/MVSTATE2/MVQUAL | implementation deleted from current main; specs/evidence historical | scientifically rich hard-coverage/representative/correlation/repair chain, but depends on sparse witness graph, hard family thresholds, continuation state, repair and qualification semantics no longer present in current pipeline | **HISTORICAL RESURRECTION CANDIDATE, NOT DEFAULT**; reuse only if its extra capabilities are required and cannot be obtained more directly from still-current DATA6/DATA7 components |

### 3.1 Why the currently present DATA7 lineage is the leading reuse candidate

The current repository already contains almost the complete numerical substrate needed for diversity restoration:

```text
current DATA5 context
 + current model-free DATA6 structural evidence
 + current fitted metric framework
 + current exact FPS state/kernels
 + current structural/environment queues
 + current coverage scorer
```

The missing integration is principally the **binding of those capabilities to exact current `P_train` and to the current P2 `TargetTrainingOrder`/prepared generation**.

This is materially smaller than reconstructing the deleted MVSEL2 sparse-index/runtime chain and does not sacrifice the proven FPS/coverage implementation.

### 3.2 Why MVSEL2 remains eligible but is not selected by default

Historical MVSEL2 was not merely an FPS function. It consumed an authenticated multi-view sparse witness relation and implemented a lexicographic hard-coverage phase followed by representative/correlation/diversity ranking; REPAIR2 then performed exact prefix-preserving repair; MVSTATE2 carried continuation state; MVQUAL independently requalified prefixes. Reusing it faithfully would require deciding whether all of those scientific predicates are current requirements and then restoring their deleted implementation/dependencies.

Gate R0 below must still inspect MVSEL2/REPAIR2 capability against the accepted D1 requirement. If hard witness-family coverage, repair, or correlation balancing is shown to be required and the deleted chain is the cleanest proven realization, resurrection is allowed. Its retired status alone is not a rejection reason.

## 4. Reuse decision rule

Before implementation, compare candidate concretizations in this order:

1. **Reuse an existing current component unchanged** when its semantics already match.
2. **Rebind or narrowly parameterize an existing current component** when ownership/input lineage changed but algorithmic semantics remain correct.
3. **Restore a deleted historical component** when its additional semantics are still required and restoration is lower-risk/lower-complexity than recreating them.
4. **Write new machinery only for the residual capability** that none of the above can satisfy cleanly.

Choose the **largest semantically compatible reuse unit**, not the smallest code fragment and not the oldest complete subsystem.

The decision comparison shall consider:

- exact D1/D2 semantic coverage;
- no label leakage;
- exact `P_train` fit domain;
- one master order and exact-prefix/full-continuation behavior;
- hard condition/support preservation;
- determinism and reproducible numerical identity;
- current prepared-generation ownership/currentness;
- persistence/restart requirements;
- CPU/RAM scaling;
- implementation/dependency/state complexity; and
- available historical/current qualification evidence.

## 5. Proposed reuse architecture

### 5.1 Preferred assembled path

Subject to Gate R0 falsification, the preferred architecture is:

```text
prepare
  -> current source/frame/DATA4 reconstruction
  -> current DATA5 leakage-safe partition/unit evidence
  -> current neutral P1 evidence
  -> current exact P2 P_train/M3 split
  -> model-free DATA6 structural evidence (reused current provider machinery)
  -> target-order fitted metric over exact P_train (reused metric machinery, safe policy)
  -> reused DATA7 selection engine / exact FPS primitives
  -> one current TargetTrainingOrder pi_train
  -> reused/adapted coverage report
  -> current P2 aggregate + prepared generation
  -> downstream consumers load exact immutable prefixes only
```

`TargetTrainingOrder` remains the canonical current order authority. A reused `TrainingSelectionPlan` may exist only as an internal calculation product if it removes code duplication; it shall not become a second persisted/current order authority.

### 5.2 DATA5 reuse

Reuse current DATA5 only for facts it still owns or validly represents: condition/unit context, profile-related evidence lineage, and protected/correlation relations where the current target-order method actually needs them. Do not revive pre-target CV fold authority or make DATA5 itself the target selector.

### 5.3 DATA6 reuse

Prefer `build_data6_feature_bundle` and existing structural providers rather than inventing target-size-only descriptors. For baseline target-order construction:

- enable available universal structural selection evidence;
- enable accepted profile/LTA structural evidence when the current material/profile contract provides it;
- disable MACE descriptors unless D1/D2 separately accepts model-dependent geometry embeddings;
- disable training difficulty;
- disable blinded/model prediction evidence as membership inputs.

Raw structural evidence may be computed before the P2 split when its producer is genuinely partition-independent. **Fitted transforms used for target order shall be fit on the exact authorized target-order fit domain**, currently proposed as exact `P_train`.

### 5.4 Feature-metric reuse and mandatory repair

Reuse the `feature_metric.py` fitting, robust scaling, optional projection, transformed feature table, digest and serialization machinery where its numerical semantics are accepted.

Do **not** use the historical default feature policy unchanged. In particular, the current `raw_physical` block includes force magnitude/statistics and stress/pressure values derived from labels, and the default policy also permits model/difficulty blocks. A target-order-safe policy must enumerate only accepted pre-candidate coordinates.

The implementation shall either:

- add a geometry-only raw block/extractor to the existing metric framework for cell/shape/strain coordinates; or
- demonstrate that accepted universal/profile structural blocks already contain every required baseline coordinate, allowing `raw_physical` to be omitted.

Do not duplicate the metric fitter merely to obtain a geometry-safe block.

The exact metric block weights, dimension normalization, projection/PCA choices, quantile convention and degeneracy/tie rules are D2 decisions. Historical defaults are evidence candidates, not automatically current authority. Gate R1 requires sensitivity/counterexample evidence sufficient to close the prior Gate-A metric-weighting objection.

### 5.5 Exact fit-domain identity

Do not falsely reuse historical `FeatureFitDomainKind.FINAL_DEVELOPMENT` if its membership is larger/different than exact current `P_train`. Reuse the `FeatureFitDomain` mechanism only if it can truthfully represent exact `P_train`; otherwise extend it with a target-order domain kind or introduce the smallest equivalent current record while reusing the metric implementation.

The fit-domain digest must bind exact `P_train` membership and split ancestry.

### 5.6 Selector reuse

First attempt to adapt the still-current DATA7 selector rather than write a new one.

Required semantic changes to `build_training_selection_plan` if it is reused as the engine:

- candidates are exactly current `P_train`;
- current scientific support/condition policy replaces UID-min mandatory anchors where UID currently carries scientific priority;
- forbidden difficulty/model queues are disabled for baseline membership;
- representative/environment/rare-event queues are retained only where D1/D2 ratify them;
- fixed historical quota fractions are retained only if D1/D2 explicitly reaccept them; otherwise parameterize/remove quota semantics rather than copying them accidentally;
- no stable-UID fallback may determine ordinary non-tied scientific priority;
- full `pi_train` must be reconstructible as one exact permutation of `P_train`, or exact continuation state must be persisted so a later larger prefix continues the same method;
- candidate sizes remain prefixes of the single order; no independent per-N selector invocation.

If adapting the whole builder becomes more complex than composing its existing exact FPS/queue primitives under the current P2 order owner, use the primitives directly. The choice is based on total system simplicity and capability preservation, not a preference for new code.

### 5.7 Coverage scorer reuse

Prefer adapting `build_selection_coverage_report` rather than implementing a second scorer. Its existing q50/q90/q95, maximum covering radius, selected-neighbor, condition, environment and protected-event diagnostics are directly relevant.

Add per-condition radius/Q95 only if D1/D2 require it and the existing report cannot express the accepted diagnostic without distortion.

Coverage diagnostics remain non-consequential unless D1 separately promotes a threshold. They may falsify a proposed sampling method but do not substitute for EVAL2/CV.

### 5.8 MVSEL2/REPAIR2 conditional resurrection

Gate R0 shall produce a capability comparison against the preferred DATA7 reuse path. Restore MVSEL2/REPAIR2 only if at least one material accepted requirement cannot be satisfied cleanly by the present components, such as:

- mandatory family-specific witness coverage with accepted radii/thresholds;
- exact hard-obligation gain semantics beyond current condition support;
- correlation-unit balancing that D1 declares consequential;
- active-shell prefix repair that is required to preserve an accepted hard property; or
- production-scale behavior where the present exact FPS/queue route demonstrably fails and historical MVSEL2 provides the proven exact solution.

If restored, recover only the coherent dependency closure actually required for those semantics. Do not recreate historical public generation/migration authority merely because the selector once depended on it. The current P2/prepared generation remains the current owner.

## 6. D1/D2 method-resolution gates

### Gate R0 — Historical reuse/capability adjudication

Before freezing a selector algorithm, produce a bounded comparison of:

- A: adapted current DATA7 selector stack;
- B: current exact FPS/coverage primitives composed directly under P2;
- C: restored historical MVSEL2/REPAIR2 dependency closure.

Use the same accepted `P_train` and structural evidence where possible. For each candidate state which required capabilities it preserves, which historical capabilities it omits, why those omissions are permissible, its required current dependencies/state, and its resource behavior.

**Exit:** select the largest compatible reuse candidate and record explicit reasons for every materially relevant omitted historical capability. A blanket “retired” or “simpler” rationale is insufficient.

### Gate R1 — D1/D2 authority repair

Amend D1 with the required coverage-progressive/nested sampling meaning, leakage boundary, condition/support meaning, and coverage-versus-accuracy distinction.

Amend D2 only after R0 identifies the reused mechanism. D2 must then define the exact current method reconstructibly: accepted feature families, metric/weights/normalization/projection, fit domain, representative/support initialization, progressive selection rule, any queue/interleaving policy, deterministic ties/precision, exact-prefix/full-continuation semantics and diagnostics.

Do not force a newly invented median-seed/condition-local FPS design if an older qualified selector is the selected reuse candidate and satisfies the accepted D1 contract more completely.

**Exit:** independent D1/D2 review finds no unresolved ambiguity capable of changing `T_N` while claiming conformance; designated human ratification is recorded before promotion.

## 7. D3/D4 implementation gates

### Gate R2 — Rebind preparation inputs without parallel ownership

Modify current `prepare` ownership so exact target-order inputs are available at the P2 boundary. Reuse current DATA5/DATA6 products or construct them through their existing owners; do not make downstream commands reconstruct live structural evidence.

The current prepared generation shall persist/authenticate enough exact state to establish the selected metric/order and reload it without source reinterpretation. Prefer binding reusable existing records/digests rather than inventing a duplicate selection database.

### Gate R3 — Current target-order owner integration

`build_target_training_order` / `build_target_size_statistical_aggregate` shall consume the selected reused ordering engine/evidence. Current production under the new training-order policy shall not accept empty structural evidence and silently fall back to UID priority.

Change the training-order policy/schema identity so pre-repair UID-capable aggregate/order evidence cannot be replayed as the restored method.

Frame UID may be a final exact tie key only under explicitly accepted tie semantics.

### Gate R4 — Full-order/continuation closure

Close the mismatch between historical DATA7 `selection_limit = max(target_sizes)` and current `pi_train`'s semantic identity as an order over all `P_train`.

One of the following must be accepted and implemented:

1. construct/persist the complete exact permutation; or
2. persist authenticated exact continuation state so any newly required suffix continues the same frozen method without re-solving earlier ranks.

Appending arbitrary UID order after `Nmax` is prohibited.

### Gate R5 — Coverage evidence integration

Reuse/adapt the existing coverage scorer and bind its metric/order ancestry. At minimum retain:

```text
R_max(N)
Q50/Q90/Q95 candidate-to-selected distance
selected nearest-neighbor diagnostics
represented condition count/support
available environment/event representation diagnostics
```

Required nested property:

```text
N_b > N_a  =>  R_max(N_b) <= R_max(N_a)
```

within accepted finite-precision comparison semantics.

### Gate R6 — Prepared-generation currentness and invalidation

A change in target-order feature policy, fitted metric, selector policy, exact order or continuation identity creates a new target-size generation and invalidates dependent screen/selected-binding/CV/production evidence whose target membership changes.

Preserve unaffected source/frame/DATA4/DATA5/raw structural caches when their owning identity remains valid. Old green target-size evidence is not evidence for a new membership.

### Gate R7 — Resource qualification

Reuse historical performance evidence as a design prior, then obtain fresh CPU/RAM evidence on representative current input. Report at least population size, condition count, feature dimension, maximum required prefix/full-order strategy, feature-build time, metric-fit time, selector time, coverage-score time, peak RSS and durable/temporary state size.

No persistent dense all-pairs matrix is permitted merely to restore diversity. If exact current-scale execution is not viable, first consider already-qualified historical exact algorithms—including MVSEL2—before weakening the scientific capability.

GPU qualification is not required for this CPU/data-selection cycle and remains deferred to final release.

### Gate R8 — Real-owner integration acceptance

Final assembled acceptance must execute the real path:

```text
prepare
 -> prepared-generation publication
 -> fresh reload
 -> candidate memberships at multiple N
 -> manual target-size selection
 -> optional automatic screen over the same prefixes
 -> cross-validation freeze/re-authentication
```

No helper-only FPS test can close this boundary.

## 8. Required falsification/oracles

Use an independently simple bounded reference that does not import production selector logic for the exact accepted D2 method. Depending on the R0 result, the oracle must reconstruct the governed ranking/coverage predicates sufficiently to falsify production behavior.

Required fixtures include:

1. UID redundancy trap: early UIDs are near-duplicates; structurally distinct frames occur later.
2. Single-condition trap: condition balancing alone cannot produce diversity.
3. Multi-condition/support trap: unconstrained diversity cannot starve an accepted hard condition/support requirement.
4. Duplicate/near-duplicate trap.
5. Constant/redundant coordinate trap.
6. Feature serialization/column-order metamorphic.
7. UID renaming: non-tied geometry priority remains invariant; only accepted exact ties may depend on tie identity.
8. Forbidden-label perturbation: changing DFT energy/force/stress while geometry/evidence authorized for membership is unchanged cannot change `pi_train`.
9. Fit-domain leakage: adding/removing M3-only frames cannot change a transform that D2 says is fitted on exact `P_train`, except through a separately accepted pre-split raw feature provider that does not fit dataset statistics.
10. Restart/currentness: persisted metric/order/continuation reload exactly; stale ancestry fails closed.
11. Full-suffix continuation: ranks beyond historical `Nmax` follow the same method and do not become UID suffix.
12. Historical-equivalence fixtures for every reused selector/metric kernel whose semantics are claimed unchanged.

On representative current data, compare the current UID/condition order against the restored candidate at the same `N` using accepted coverage/support diagnostics. The restoration must demonstrate that it actually restores the lost sampling capability; aesthetics or code age are insufficient.

## 9. Capability-transfer map

| Capability | Historical evidence | Current binding | Planned realization |
| --- | --- | --- | --- |
| one master order / exact prefixes | DATA7, MVSEL2, current P2 | current D1/D2 | `TargetTrainingOrder`; reused engine subordinate to P2 |
| feature-space diversity | DATA7 FPS, MVSEL2 diversity | proposed D1 promotion | prefer existing DATA7 metric/FPS machinery |
| representative support | DATA7 representative queue, MVSEL2 representative gain | D1/D2 adjudication required | reuse accepted historical rule if retained; do not invent by default |
| condition/support protection | DATA7 mandatory condition anchors, current condition scheduler, MVSEL2 hard obligations | current/proposed D1 | preserve current hard support; choose D2 scheduler/anchor after R0 |
| environment/species diversity | DATA6 + DATA7 queue, MVSEL2 multi-view families | D1/D2 adjudication | reuse current structural/profile providers and queues if accepted |
| rare structural events | DATA4/DATA6 event evidence, DATA7 rare queue | D1/D2 adjudication | reuse if geometry-derived and accepted; no label leakage |
| label/model difficulty | historical DATA7/MVSEL inputs | not required for baseline | excluded unless separately promoted by D1 |
| exact bounded FPS | current `ExactFPSState` | D2 if FPS selected | direct reuse |
| hard multi-family coverage/repair | MVSEL2/REPAIR2/MVQUAL | not presently current | restore only if R0 shows accepted need |
| coverage diagnostics | current DATA7 coverage report, historical MVQUAL | proposed/current evidence need | reuse current scorer first |
| restartable selection continuation | MVSTATE2; current immutable prepare pattern | D3 if full order is lazy | reuse only if continuation needed; otherwise complete order avoids extra state |
| fixed historical quota fractions | DATA7 policy | no current authority | do not restore without D1/D2 acceptance |

## 10. Affected surface and identity closure

Expected affected:

- D1/D2 target-order sections;
- `ResolvedTargetSizePolicy.training_order_policy` and likely policy/schema identity;
- target-order feature/metric fit-domain records if reused/extended;
- `build_target_training_order` / aggregate construction;
- current `prepare` input routing and prepared-generation component/identity set;
- exact `pi_train`, every `T_N`, screen evidence and selected target bindings derived from it;
- dependent post-selection CV/production ancestry where target membership changes;
- coverage diagnostics/reporting;
- specs/guides/history describing empty priority evidence or retired coverage capability.

Expected preserved absent contradictory evidence:

- source authentication/canonical labels;
- protected-relation construction;
- exact P_train/M3 split semantics;
- pi_eval/M1/M2/M3/EVAL2 semantics;
- P3 optimizer/objective/common-preparation semantics;
- TRAIN2/EVAL2 process/checkpoint architecture;
- replay;
- CV threshold separation and role predicates;
- final-production horizons/method;
- GPU scheduler/CUDA lifetime;
- storage cleanup architecture.

## 11. Review and reopen triggers

Reopen D1 if structural coverage is not required for the target-size scientific interpretation, if accepted hard support and diversity are scientifically incompatible, or if geometry-only/pre-candidate evidence cannot represent the support claim.

Reopen D2 if feature weighting/projection is materially arbitrary, accepted providers cannot support leakage-safe ordering, exact ranking is irreproducible, or an omitted historical capability is shown to be required.

Reopen D3 if current P2/prepared-generation ownership cannot host the selected reused engine without duplicate authority, if downstream recomputation would be required, or if a necessary historical subsystem has a larger coherent state/dependency closure than the proposed integration admits.

If the preferred current DATA7 route fails resource or capability qualification, **explicitly reconsider MVSEL2/REPAIR2 before inventing a third selector generation or weakening coverage**.

## 12. Workplan acceptance criteria

This workplan is ready for implementation only when:

1. R0 identifies the reuse granularity with evidence rather than prejudice for/against historical machinery.
2. D1 defines the required coverage/support capability independent of implementation name.
3. D2 ratifies the exact selected reused method and closes feature-weighting, fit-domain, precision/tie, queue/scheduler and full-order semantics.
4. Independent D1/D2 review passes and required human ratification occurs.
5. Current production cannot create a restored-policy generation with empty/UID-only scientific priority.
6. One current prepared generation owns/authenticates the order evidence and downstream consumers do not reconstruct it.
7. Full-order or exact continuation semantics are closed.
8. Current coverage diagnostics and historical equivalence/reference tests pass.
9. Representative CPU/RAM evidence establishes operational viability or routes to an already-proven exact historical alternative.
10. Dependent identity/evidence/documentation/history impact is closed without invalidating unrelated evidence.
11. No GPU PASS is claimed; final consolidated GPU qualification remains deferred.

Until accepted D1/D2 and assembled implementation satisfy these conditions, the current UID-capable `pi_train` remains under **SERIOUS CHALLENGE**.