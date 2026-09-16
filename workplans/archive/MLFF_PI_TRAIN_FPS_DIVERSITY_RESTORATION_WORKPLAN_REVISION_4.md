---
kind: abstraction-concretization-change-plan
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 4
protocol_version: 6.3.0
status: active
created_date: 2026-09-15
branch: design/mlff-pi-train-fps-diversity-restoration
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
supersedes:
  - workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN.md
  - workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_2.md
  - workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_3.md
historical_recovery_source:
  pre_p6_tree_commit: 3937881ef00222e80845aa81f5471d89a4a7736c
  mvsel2_initial_commit: c34ae2b2c2e2e2de4a3afee9f8fba464425344d3
highest_affected_domain: D1
challenge_state: SERIOUS_CHALLENGE
human_ratification: stakeholder_direction-recorded-exact-d1-d2-reconciliation-still-required
---

# MLFF `pi_train` latest-path restoration — Revision 4

## 0. Governing decision

The restoration target is no longer open among competing selector generations.

**Restore the latest mature pre-V7 selection path:**

```text
DATA6 raw/candidate-independent evidence
  -> DATA7 fitted subset-input evidence / metric
  -> FEAS1 feasibility
  -> MVIDX1 authenticated sparse coverage relation
  -> MVSEL2 exact forward/lazy progressive selection
  -> MVSTATE2 authenticated continuation state where useful
  -> REPAIR2 exact active-shell repair
  -> MVQUAL2 independent prefix qualification
  -> one current P2 TargetTrainingOrder / pi_train
  -> T_N = pi_train[:N]
```

The user has explicitly chosen restoration of this latest working path rather than replacing it with the older direct DATA7 queue/FPS selector or a newly invented simplified FPS method. Historical age is not a defect. Remove or alter only the portions that conflict with current accepted P1/P2/P3/P5 architecture, current authority, or current target-size semantics.

The direct DATA7 selector (`selection.py`, `ExactFPSState`, historical multi-queue plan) remains useful as numerical/reference evidence and fallback implementation material, but it is **not** the primary production restoration target.

## 1. Why this is the correct historical generation

The repository history establishes the evolution:

```text
older DATA7 direct selection machinery
  -> DATA7 fitted subset-input authority
  -> FEAS1/MVIDX1/MVSEL2/REPAIR2/MVSTATE2/MVQUAL2
  -> V7 destructive P6 removal
```

MVSEL2 was implemented after the original DATA7 direct selector and subsequently became the production selection engine. Its mature production realization removed eager inverse/marginal state while preserving exact scientific ranking:

- candidate-forward sparse rows;
- exact staged hard-coverage scoring;
- exact representative phase with conservative lazy bounds;
- full-forward reference/fallback;
- compact authenticated continuation state;
- exact active-shell repair;
- independent qualification instead of trusting selector counters.

The V7 P6 cleanup removed this chain because V7 retired the surrounding target-size topology. No evidence establishes that MVSEL2's coverage/diversity method itself failed. This work treats the loss as an over-broad capability deletion.

## 2. Protected current architecture

Restoration shall preserve the current architecture unless a concrete contradiction reopens it:

1. one canonical `U_size -> P_train + M3` split;
2. one current target-size training population `P_train`, not per-label-domain or per-CV-fold training domains;
3. one current `pi_train` owner represented publicly by `TargetTrainingOrder`;
4. exact nested membership `T_N = pi_train[:N]`;
5. current configurable target-size ladder/policy rather than the historical fixed-eight universe;
6. current `pi_eval`, M1/M2/M3, EVAL2, paired-seed screen and reducer semantics;
7. current manual/provisional selection and P5 post-selection CV/fresh-production semantics;
8. immutable preparation-owned generation loaded downstream without live-input reconstruction;
9. final-release-only GPU qualification.

Restoring the selector must **not** restore the old target-size campaign architecture around it.

## 3. Capability-preservation rule

For every pre-V7 MVSEL2-chain capability, use this decision rule:

```text
latest working capability
  -> preserve by default
  -> adapt its binding to current P_train/P2 ownership
  -> drop only when a specific current authority incompatibility is demonstrated
```

Do not remove a capability merely because its original record/schema/module name was retired.

### 3.1 Capabilities to restore

Restore, subject only to current-input rebinding:

- multi-view structural coverage rather than a single undifferentiated Euclidean distance;
- hard coverage evaluated per required feature/view family rather than hidden in one weighted average;
- deterministic nested progressive ordering;
- hard scientific/support obligations;
- correlation/provenance balancing where its source facts remain current and non-leaky;
- representative/density-aware utility;
- explicit diversity tie/objective contribution;
- two-phase hard-coverage then representative-fill selection;
- exact forward/lazy execution with full-forward oracle/fallback;
- compact authenticated restart/continuation state where execution duration justifies it;
- active-shell repair with protected lower prefixes, rank inheritance and no hard-coverage regression;
- independent qualification of repaired prefixes;
- deterministic identities, precision/tie rules and current-scale resource controls.

### 3.2 Historical scientific policy is preserved unless incompatible

Revision 3 over-quarantined historical MVSEL2 policy. Revision 4 reverses that presumption.

The latest accepted historical MVSEL2 policy is the starting scientific/numerical method, including the historically frozen hard-family coverage threshold (`0.95`), exact ranking hierarchy, hard-obligation handling, representative gain, correlation balancing, diversity contribution, and accepted tolerance/reduction semantics.

A historical policy field is removed or changed only if one of the following is shown:

- it depends on an authority/current population that V7 intentionally removed and has no truthful current binding;
- it leaks candidate/CV/production outcomes into membership;
- it contradicts accepted current D1/D2 meaning;
- it is a fixed-size/campaign-lifecycle assumption rather than a selection-method semantic;
- independent reconstruction proves it was superseded before the last mature pre-V7 selector state.

Candidate-independent foundation/descriptor/difficulty evidence is **not automatically forbidden** merely because it is model-derived. Current D1 already permits candidate-independent feature metrics, foundation predictions and difficulty evidence. R1 must reconstruct the exact latest input semantics and preserve them when they remain pre-candidate and leakage-safe. Candidate model outcomes, EVAL2, CV and production outcomes remain forbidden membership inputs.

## 4. Exact restoration/pruning map

| Historical component/capability | Revision-4 disposition | Current binding |
| --- | --- | --- |
| DATA6 raw structural/model evidence providers | RESTORE/REUSE | preparation-owned evidence source; reuse authenticated current DATA6 where lineage matches |
| DATA7 fitted metric / `TargetSubsetInputBundle` role | RESTORE | fit exactly for current `P_train`; no per-fold/per-label-domain fanout |
| FEAS1 | RESTORE | feasibility over exact current `P_train` and current configured ladder/capacity |
| MVIDX1 | RESTORE | one authenticated sparse multi-view relation for exact current P_train selector domain |
| MVSEL2 forward/lazy engine | RESTORE | sole restored progressive-selection engine beneath P2 |
| full-forward MVSEL2 oracle/fallback | RESTORE | independent correctness path for optimized/lazy engine |
| MVSTATE2 | RESTORE when useful | preparation checkpoint/restart state; identity rebound to current P_train/split/method, not label-domain authority |
| REPAIR2 | RESTORE | operates on current configured prefix shells; one repaired master order, no independent per-N selector |
| MVQUAL2 independent scoring | RESTORE | independently scores current configured repaired prefixes and hard obligations |
| historical `0.95` hard family coverage threshold | RESTORE by default | current coverage-qualification policy unless D1/D2 review produces a concrete contradiction |
| historical exact tie/tolerance/reduction semantics | RESTORE by default | numerical method identity; change only with explicit D2 evidence |
| label-domain selector fanout | DROP/REBIND | one current P_train selector domain; label-domain ID cannot branch target membership |
| preselection CV/fold selector fanout | DROP | current CV is post-selection P5 only |
| fixed `128..16384` candidate universe | DROP | current configured `ResolvedTargetSizePolicy` candidate sizes / ceiling |
| old target-size study/reducer | DROP | retain current EVAL2/paired-seed screen/reducer |
| old selected-N authority | DROP | retain current provisional/frozen target-size campaign state |
| old DATA8/per-domain prescribed materialization | DROP | retain current P3/P5 materialization owners |
| old campaign record/currentness/migration topology | DROP | prepared-generation + current campaign-store generation remain sole currentness owner |
| old compatibility readers/migration envelopes | DROP | reprepare current selector evidence instead of semantically migrating retired derived state |
| MVQUAL as model-accuracy criterion | PROHIBITED | coverage/support qualification only; EVAL2/CV still own model behavior |

## 5. Current-domain rebinding

### 5.1 One selector domain

The old chain operated per canonical DATA5/label training domain. Current target-size science owns one exact `P_train`. Rebind the restored chain to one selector domain:

```text
selector_population = exact P_train
candidate_uids = P_train UIDs in canonical current identity order
reference/witness population = exact D2-defined current support population derived from P_train
condition/support facts = current P1/P2 + accepted reusable evidence
```

Do not recreate label-domain branching merely to satisfy historical schemas. Where historical identities contain `label_domain_id`, replace that dimension with a truthful current selector-domain/split identity rather than filling a fake constant that could later be mistaken for authority.

### 5.2 Current P2 condition/support ownership

Current `TargetSizePopulation.frame(uid).condition_id` remains the current categorical condition owner. Historical DATA5 condition/unit facts may contribute correlation/provenance evidence, but cannot silently create a second target-size condition authority.

Where historical hard obligations represented real scientific support obligations still expressible from current condition/event/environment evidence, retain them and bind them to current evidence. If a historical obligation depended solely on a retired role topology, document the exact reason for omission.

## 6. Evidence and fitted-input restoration

### 6.1 Restore the latest DATA6 -> DATA7 input semantics

Do not reduce the restored selector to geometry-only FPS unless independent review proves the latest MVSEL2 method itself must be narrowed.

Reconstruct the last mature `TargetSubsetInputBundle`/DATA7 fitted inputs from historical code/specs and map each field:

```text
historical field
 -> scientific role
 -> source owner
 -> leakage classification
 -> current equivalent/source
 -> retained / rebound / dropped with reason
```

At minimum inspect:

- fitted feature families and block metrics;
- witness/reference weights;
- hard obligations;
- representative utility inputs;
- diversity inputs;
- event/environment/focus evidence;
- correlation-unit identities;
- difficulty inputs;
- condition/provenance identities.

This mapping is mandatory before D1/D2 promotion. It prevents both accidental capability loss and accidental resurrection of obsolete domain authority.

### 6.2 Preparation ownership

All evidence and fitted transforms needed by MVSEL2 are produced/reused by `prepare` and persisted in the immutable prepared generation. `select-target-size`, manual selection, CV and production must not run DATA6/DATA7 fitting or MVSEL2 preparation from live sources.

If foundation-model descriptors/predictions/difficulty are part of the restored accepted input bundle, acquire/reuse them only in `prepare`, with authenticated provider/checkpoint identity. Manual `select-target-size N` remains cheap and loads exact prepared membership.

## 7. FEAS1 and MVIDX1 restoration

### 7.1 FEAS1

Restore FEAS1 as the complete-population preflight for the current selector domain. Remove only its fixed-universe/per-domain assumptions.

FEAS1 shall validate, as applicable under the reconstructed latest policy:

- witness self/support feasibility;
- hard-obligation feasibility;
- fragile/low-support witness mass;
- candidate/reference support;
- capacity limitations relevant to the **current configured candidate-size ladder**;
- exact identities of population, families, policy and obligations.

FEAS1 does not choose N and does not relax coverage when a configured prefix cannot satisfy the policy.

### 7.2 MVIDX1

Restore the authenticated sparse relation and candidate-forward projection used by the mature MVSEL2 engine. Preserve the exact scientific relation; execution representation may retain the proven forward/mmap/chunked/native optimizations.

One current selector domain gets one product-scale MVIDX relation, not one copy per candidate N.

## 8. MVSEL2 restoration

Restore the last production engine semantics rather than the older direct FPS queue.

### 8.1 Phase A — hard coverage

Preserve the historical staged exact ranking hierarchy unless R1 establishes a concrete incompatibility:

1. hard-obligation gain;
2. worst/bottleneck family coverage improvement;
3. best relative bottleneck-family gain;
4. total coverage gain;
5. correlation-unit balance;
6. representative gain;
7. diversity;
8. stable UID only as the final exact tie key.

Use the historical exact tolerance/reduction semantics as the default restored D2 contract.

### 8.2 Phase B — representative fill

After hard coverage is satisfied, preserve the latest representative-fill authority:

1. representative gain;
2. correlation balance;
3. diversity;
4. stable UID final tie.

Preserve the exact all-candidate rebase, certified lazy frontier, conservative upper-bound logic, exact refresh and full-forward fallback/equivalence oracle.

### 8.3 Production engine

Restore the latest single production MVSEL2 rank loop and its qualified optimized kernels/backend rather than reviving superseded eager/inverse or failed candidate-thread generations.

The historical source recovery baseline is the pre-P6 tree where `mvsel2_selection_engine.py` states that production owns one rank loop for fresh/resumed selection and that the failed PAR1 candidate-thread path is absent.

## 9. MVSTATE2 restoration

Restore compact authenticated continuation state because it is compatible with current immutable preparation and valuable for a potentially long full-population selection.

Rebind identity from historical per-label-domain fields to exact current:

- P_train population/split identity;
- DATA7 fitted-input identity;
- MVIDX1 identity;
- candidate/family order;
- witness/obligation/correlation identities;
- selector policy/version.

Retain the proven rule that reconstructible candidate marginals and lazy-heap contents are not durable authority.

MVSTATE2 is preparation-local continuation evidence, not a second campaign currentness owner. The prepared-generation manifest/campaign state decides what completed generation is current.

## 10. REPAIR2 restoration

Restore REPAIR2 unless a focused R1 falsification demonstrates it is incompatible with the current one-order/prefix contract. Historical evidence says the opposite: REPAIR2 already produced one repaired master order and protected lower prefixes.

Adapt shell boundaries from the historical fixed universe to the current sorted configured candidate sizes.

Preserve by default:

- active-shell-only mutation;
- protected lower prefixes;
- zero-unique/hard-safe removal admission;
- deficit/frontier replacement scoring;
- hard-obligation safety;
- strict no-hard-coverage regression;
- rank inheritance and deterministic future displacement;
- bounded passes/swaps/shortlist semantics;
- deterministic repair trace.

No independently repaired `T_N` objects may exist. The result is still one master order whose configured candidates are exact prefixes.

## 11. MVQUAL2 restoration and the coverage criterion

This cycle restores **coverage qualification as a real target-membership admissibility criterion**, not merely a dashboard diagnostic.

For every configured candidate size `N`, MVQUAL independently recomputes the restored hard family coverage and hard-obligation predicates from authenticated primitive inputs and the repaired prefix.

The historical default coverage threshold `0.95` is restored unless D1/D2 review produces evidence requiring a different accepted value.

Current qualification becomes conceptually:

```text
qualified(N) =
    prefix_exists(N)
    AND labels_training_usable(T_N)
    AND current hard support obligations satisfied(T_N)
    AND restored MVQUAL hard multi-view coverage satisfied(T_N)
    AND restored MVQUAL required obligations satisfied(T_N)
```

Coverage qualification does **not** claim that the model is accurate. A coverage-qualified N may still fail EVAL2/CV. Conversely, a prefix that fails the accepted coverage criterion is not a scientifically admissible target-size candidate merely because a trained model happens to score well.

Remove only the obsolete MVQUAL2 bindings:

- no import/use of historical `FIXED_TARGET_SIZES`;
- candidate sizes come from current target-size policy;
- no historical target-size study/currentness authority;
- no per-label-domain qualification plan.

Retain independent scoring, monotone nested-prefix checks, per-family coverage, deficits, hard obligations, redundancy/unique-support and provenance/correlation diagnostics.

## 12. Full `pi_train` semantics

Current `TargetTrainingOrder` expects an exact permutation of `P_train`. Therefore the restored chain must have exact semantics beyond the largest configured N.

Preferred realization: run the restored MVSEL2 continuation through the complete P_train order, carrying repaired-state effects forward deterministically. REPAIR2 only needs configured shell boundaries; after the final shell the same restored selector state continues to exhaustion.

If full-order runtime is materially excessive, D2/D3 may instead introduce an authenticated exact continuation representation, but only if current `TargetTrainingOrder`/prepared-generation semantics are coherently revised. Arbitrary UID suffix completion is prohibited.

## 13. Prepared-generation integration

The current prepared-generation remains the sole immutable completed-preparation boundary.

Version it as needed to persist/authenticate the restored chain inputs/results, preferably as content-addressed components:

```text
current P1 components
DATA6/raw selector evidence or accepted projection
DATA7 fitted subset-input / metric identity
FEAS1 result
MVIDX1 relation identity + product-scale backing artifacts
MVSEL2 policy/order evidence
MVSTATE2 completion/restart evidence as non-current preparation state
REPAIR2 repaired master-order evidence
MVQUAL current candidate-prefix qualification evidence
current TargetSizeStatisticalAggregate / TargetTrainingOrder
current common P3 preparation
```

Do not duplicate large MVIDX arrays into JSON if the historical authenticated file-backed representation is the correct owner. The prepared generation may bind content-addressed external artifacts by authenticated identity/path manifest rather than embedding them.

Downstream consumers load the resulting current `TargetTrainingOrder` and qualifications; they do not need to understand the historical component names.

## 14. D1/D2 authority reconciliation — Gate R1

The stakeholder has ratified the restoration direction: latest mature MVSEL2 selection behavior should be restored, with only current-incompatible parts removed.

R1 must now reconstruct the exact last mature scientific/numerical selection method and write it into current D1/D2, not redesign it from scratch.

### D1 amendments

At minimum state:

- `pi_train` is a candidate-independent multi-view coverage/representation-progressive order;
- required hard coverage/support is a membership-admissibility property;
- each configured `T_N` must satisfy the accepted coverage/support predicates before it is an admissible target-size candidate;
- target-size N is still selected by EVAL2/model behavior among admissible candidates;
- post-selection CV cannot feed back into pi_train or N;
- candidate/CV/production outcomes cannot influence membership.

### D2 reconstruction

Recover exactly from the last mature chain:

- feature/view families and fit domains;
- reference/witness definitions and weights;
- hard obligations;
- MVIDX adjacency/radius/scaling semantics;
- historical 0.95 threshold;
- exact MVSEL2 ranking phases/hierarchy;
- representative/diversity/correlation semantics;
- exact tolerance, FP64 reduction and tie rules;
- REPAIR2 rules;
- MVQUAL predicates;
- current-ladder adaptation;
- full-order continuation semantics.

Any intentional omission from the old method must identify the exact current incompatibility. "Simpler" or "retired" is not sufficient reason.

Independent D1/D2 falsification remains required before accepted-current promotion.

## 15. Implementation recovery gate — R2

Before editing production call paths, recover the exact coherent source dependency closure from the latest pre-P6 generation.

At minimum census and classify:

```text
feature_metric.py / DATA7 fitted-input owners
target_coverage.py
target_coverage_sparse_index.py
target_coverage_sparse_forward_view.py
FEAS1 implementation
MVIDX1 runtime/builders
target_multi_view_selector.py
target_multi_view_selector_v2.py
mvsel2_selection_engine.py
mvsel2_phase_a_kernel.py
mvsel2_phase_b_kernel.py
mvsel2_native_backend.py / native sources where qualified
target_multi_view_selection_state_v2.py
target_multi_view_selection_history_v2.py
target_multi_view_repair.py
target_multi_view_repair_v2.py
target_multi_view_qualification_v2.py
independent scoring/reference helpers
associated serializers/tests/benchmarks
```

For every recovered file/function classify:

- `RESTORE_UNCHANGED` — semantics and owner fit current use;
- `RESTORE_REBIND` — implementation reusable but historical domain/currentness/fixed-size assumptions must change;
- `REFERENCE_ONLY` — superseded implementation useful as oracle/evidence;
- `DROP` — incompatible lifecycle/authority with no current-required capability.

Restore the minimum coherent dependency closure that retains the latest engine. Do not restore superseded MVSEL1/eager-inverse/PAR1/migration generations merely because the latest files import a shared type; replace such imports with the surviving/latest shared type or smallest equivalent current type.

## 16. Implementation sequence

### R3 — current input/data7 integration

- bind exact P_train to the restored DATA7 fitted-input owner;
- reuse current DATA6 and historical/current structural/difficulty providers according to accepted R1 semantics;
- remove per-label-domain/fold fanout;
- authenticate exact source/split/input identities.

### R4 — FEAS1/MVIDX1

- restore feasibility and sparse relation over exact P_train;
- adapt capacity to current candidate ladder;
- preserve file-backed/bounded-memory behavior.

### R5 — MVSEL2/MVSTATE2

- restore the single production exact forward/lazy engine;
- restore reference/full-forward equivalence path;
- restore compact restart state with current identity;
- generate exact complete order or approved exact continuation.

### R6 — REPAIR2

- restore active-shell repair using current candidate sizes;
- prove one repaired master order and immutable lower-prefix behavior.

### R7 — MVQUAL/current P2 qualification

- restore independent coverage/obligation scoring for every current configured N;
- integrate coverage into current `TargetSizeCandidateQualification`/experiment-definition admissibility without restoring old target-size study/reducer.

### R8 — prepared generation/currentness

- publish/authenticate all required completed selector evidence under one current prepared generation;
- downstream manual/auto/CV/production only load current P2 products;
- stale old UID-only generations fail closed or are explicitly historical.

### R9 — assembled acceptance and documentation

- update D1/D2/D3/D4 docs and semantic history;
- run full affected regression and real-owner integration;
- archive superseded workplans only after acceptance.

## 17. Required falsification and acceptance evidence

### 17.1 Historical-equivalence fixtures

Where current-domain rebinding does not intentionally change a semantic input, the restored implementation must reproduce the latest historical MVSEL2/REPAIR2/MVQUAL decisions on preserved fixtures.

Required comparisons include:

- full-forward vs optimized/lazy MVSEL2 exact rank equality;
- restart/resume vs uninterrupted equality;
- worker/batch/backend independence within qualified realizations;
- REPAIR2 final-order and swap-trace equivalence on shared policy fixtures;
- independent MVQUAL equality to primitive recomputation.

### 17.2 Current-domain fixtures

Required adversarial tests include:

1. UID-cluster trap: stable UID cannot dominate genuine coverage ranking.
2. single-condition structural-diversity trap.
3. multi-view conflict: one family is covered while another is not; hard bottleneck family must remain visible.
4. hard-obligation trap: representative/diverse candidate cannot win by violating required support.
5. correlation/provenance imbalance trap where that policy remains current.
6. duplicate/near-duplicate candidate trap.
7. restart/corrupt-MVSTATE2 rejection.
8. stale/wrong-MVIDX identity rejection.
9. repaired-prefix no-regression test.
10. MVQUAL monotone qualification over nested configured prefixes.
11. configured-ladder change invalidates qualifications/order-policy ancestry without restoring fixed-eight assumptions.
12. candidate/CV/production outcome perturbation cannot change pi_train.
13. manual `select-target-size N` performs no selector/Data6/MVIDX rebuild and simply binds the prepared exact prefix.

### 17.3 Resource evidence

Re-run representative current-scale CPU/RAM/scratch benchmarks. Historical performance is a design prior, not current proof.

Report at least:

```text
|P_train|
feature families/dimensions
witness/edge cardinalities by family
MVIDX build wall/RSS/scratch
MVSEL2 wall/RSS/restart state size
REPAIR2 wall/RSS
MVQUAL wall/RSS
prepared artifact sizes
```

Preserve the latest forward/lazy resource principle: no complete inverse marginal state and no per-N copy of the selector graph.

If restored latest machinery is too slow, first reuse its historically qualified native/OpenMP and lazy optimizations. Do not replace it with a weaker selector merely to pass a performance gate without reopening D2.

## 18. Invalidation/evidence impact

Changing `pi_train` invalidates every descendant whose membership/order ancestry changes:

- target-size candidate-prefix digests;
- current target-size screen evidence;
- selected-size bindings whose `T_N` changed;
- post-selection CV evidence for changed T_N;
- final-production evidence for changed T_N;
- target-order prepared-generation identity.

Preserve unaffected owners/evidence, including source authentication, exact P_train/M3 split when unchanged, pi_eval/M1/M2/M3, EVAL2 algorithm, training objective, replay, CV acceptance method, production method, scheduler/CUDA and storage architecture.

Historical MVSEL2 qualification/benchmarks can support mechanism recovery but cannot directly certify the current rebinding.

## 19. Non-goals

This cycle does not:

- restore MVSEL1 or eager/inverse selector generations;
- restore failed PAR1 candidate-thread execution;
- restore historical per-label-domain target-size authority;
- restore preselection CV;
- restore fixed-eight target-size policy;
- restore old target-size study/reducer/selected-N owner;
- restore old prescribed per-domain materialization;
- restore migration compatibility for retired derived selector records;
- change current model-performance target-size reducer merely because MVQUAL is restored;
- perform final production-scale GPU qualification.

## 20. Pass criteria

The cycle passes only when:

1. current D1/D2 explicitly describe the restored latest MVSEL2-chain selection/qualification method and every intentional historical omission has an exact compatibility reason;
2. exact current P_train is the single selector domain;
3. DATA7 fitted inputs, FEAS1, MVIDX1, MVSEL2, REPAIR2 and independent MVQUAL are restored under current preparation/P2 ownership;
4. MVSTATE2 or an equally exact current continuation mechanism protects long-running preparation without becoming campaign currentness authority;
5. current candidate sizes replace the old fixed-eight universe everywhere;
6. each admissible configured T_N passes the restored hard multi-view coverage/support criterion;
7. target-size N is still chosen by current EVAL2/model-behavior logic among admissible prefixes;
8. one current TargetTrainingOrder remains the downstream membership authority;
9. no current command downstream of prepare reconstructs selector evidence from live inputs;
10. exact optimized/reference, restart, repair, MVQUAL, currentness and resource evidence pass;
11. no superseded MVSEL1/eager-inverse/PAR1/old target-size campaign topology becomes reachable;
12. materially dependent evidence/documentation are reconciled;
13. final production-scale GPU qualification remains deferred.

Until those conditions hold, the current UID-capable target-order path remains under **SERIOUS CHALLENGE**.