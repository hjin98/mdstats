---
kind: abstraction-concretization-change-plan
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 5
protocol_version: 6.3.0
status: active
created_date: 2026-09-15
branch: design/mlff-pi-train-fps-diversity-restoration
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
supersedes:
  - workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN.md
  - workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_2.md
  - workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_3.md
  - workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_4.md
highest_affected_domain: D1
challenge_state: SERIOUS_CHALLENGE
human_ratification: stakeholder-restoration-direction-recorded-exact-d1-d2-reconciliation-still-required
historical_recovery_snapshot:
  deletion_commit: 747bf1d97d686447b06dd95605f61cf896d7f2a2
  exact_pre_deletion_parent: 3937881ef00222e80845aa81f5471d89a4a7736c
  normative_spec_index: docs/specs/training_data/README.md
  integrated_chain_spec: docs/specs/training_data/mlff_target_data2c_mvsel2_forward_lazy_chain_spec.md
  data7_spec: docs/specs/training_data/mlff_data7_fitted_metrics_selection_spec.md
  architecture_chapter: docs/arch_manuals/mlff_training_data/50_target_multiview.md
---

# MLFF `pi_train` latest-path restoration — Revision 5

## 0. Disposition and purpose

The current production target-order path remains under **SERIOUS CHALLENGE** because it can construct `pi_train` without the multi-view coverage/diversity machinery that the last mature selector generation supplied.

The stakeholder decision is now fixed:

> Restore the latest mature MVSEL2 selection path at the largest coherent granularity. Rebind it to the current one-`P_train` / P2 / prepared-generation architecture. Remove or alter only parts that are concretely incompatible with current authority or current lifecycle ownership.

Revision 5 is a snapshot-complete replacement for Revision 4. It closes the second-review gaps around exact historical recovery identity, DATA7 ownership, the missing target-coverage reference authority, exact MVSEL2 ranking wording, family-specific coverage policy, REPAIR2/continuation semantics, candidate-qualification identity, prepared-generation currentness, provider/resource lifetime, PEM/HAS, and active-workplan discoverability.

The direct pre-MVSEL DATA7 queue/FPS selector remains reference/fallback material only. It is not the primary production restoration target.

---

## 1. Exact historical recovery authority: no cross-commit hybrid

### 1.1 Recovery snapshot

The source-of-recovery snapshot for the latest selector generation is the **exact parent of the destructive P6 deletion**:

```text
hjin98/mdstats@3937881ef00222e80845aa81f5471d89a4a7736c
```

P6 deleted the chain at:

```text
hjin98/mdstats@747bf1d97d686447b06dd95605f61cf896d7f2a2
```

Use `3937881...` as the coherent historical snapshot for code, current-at-that-snapshot specifications, architecture, tests, fixtures, benchmarks, schemas, and policy defaults. Do **not** compose a synthetic historical method by taking a selector implementation from one commit, a repair policy from another, and a qualification rule from another merely because all are called MVSEL2-era.

### 1.2 Historical normative owners at the snapshot

At `3937881...`, the current specification index explicitly identifies the following as current owners of the mature chain:

- `docs/specs/training_data/mlff_data7_fitted_metrics_selection_spec.md`;
- `docs/specs/training_data/mlff_target_data2b_feas1_support_capacity_spec.md`;
- `docs/specs/training_data/mlff_neighbor1_exact_neighborhood_spec.md`;
- `docs/specs/training_data/mlff_target_data2c_mvidx1_sparse_coverage_index_spec.md`;
- `docs/specs/training_data/mlff_target_data2c_mvsel2_forward_lazy_chain_spec.md`;
- `docs/specs/training_data/mlff_target_data2c_mvqual1_same_n_qualification_spec.md` where not superseded by the integrated chain;
- applicable material/profile structural-selection contracts;
- `docs/arch_manuals/mlff_training_data/50_target_multiview.md` for the cross-component architecture.

Historical code is concretization/evidence for those historical owners, not an authority that may silently override them. If recovered normative text and recovered executable behavior disagree materially, Gate R1 records the contradiction and adjudicates it explicitly before current D1/D2 promotion. No implementation review may silently choose whichever historical surface is easier to port.

### 1.3 Terminology correction

This is the **latest mature pre-P6/pre-deletion MVSEL2 chain**, not generically “pre-V7.” V7 P1-P5 work had already begun before P6 physically removed the selector modules. Using the exact pre-deletion snapshot avoids accidentally recovering an older selector revision and losing the August 20-23 production/performance fixes.

---

## 2. Protected current architecture

The restoration shall preserve, unless a concrete higher-owner contradiction reopens one of them:

1. one canonical current `U_size -> P_train + M3` split;
2. one target-size training population `P_train`, not per-label-domain or preselection-CV training domains;
3. one public/current `TargetTrainingOrder` / `pi_train` authority;
4. exact nested membership `T_N = pi_train[:N]`;
5. the current configurable target-size policy and current candidate ladder rather than the old fixed-eight size-study authority;
6. current `pi_eval`, M1/M2/M3, EVAL2, paired-seed screen and current reducer semantics;
7. current provisional/frozen target-size state and P5 post-selection CV/fresh-production lifecycle;
8. `prepare` as the only owner that interprets live selector inputs and publishes the immutable prepared generation;
9. the campaign store as the only owner of which prepared generation is current;
10. final production-scale GPU qualification deferred to the established final-release package.

Restoring MVSEL2 does **not** restore the old target-size campaign around it.

---

## 3. Canonical restored selection chain

The restored scientific/numerical selection chain is:

```text
current P1/P2 P_train + authorized upstream evidence
  -> DATA6 raw selection/prediction evidence
  -> DATA7 selector-relevant fitted projection
  -> TargetCoveragePolicy + TargetCoverageReference
  -> FEAS1 full-pool feasibility/support evidence
  -> MVIDX1 exact authenticated sparse multi-view relation
  -> MVSEL2 exact forward/lazy progressive order
  -> REPAIR2 repaired master order
  -> MVQUAL independent prefix qualification
  -> one current TargetTrainingOrder / pi_train
  -> T_N = pi_train[:N]
```

`MVSTATE2` is the authenticated compact continuation/checkpoint family for expensive selector construction and reconstruction. It is subordinate preparation state, not a second ordering or campaign-currentness authority.

### 3.1 Restore the historical coverage-reference owner explicitly

Revision 4 skipped a material historical owner. `target_coverage.py` froze what coverage meant and constructed the reference/witness families consumed by FEAS/MVIDX/MVSEL/MVQUAL. Restore/rebind that owner rather than rebuilding witnesses, radii, weights, extents, conditions/events/profile support, or empirical reference mass ad hoc inside P2.

The recovered `TargetCoveragePolicy`/reference semantics are preserved by default, including their exact family construction and identity fields, unless R1 demonstrates a current incompatibility.

---

## 4. Restore/prune map

| Historical surface | Revision-5 disposition | Current binding / reason |
| --- | --- | --- |
| DATA6 raw structural / foundation / difficulty inputs | RESTORE/REUSE | preparation-owned candidate-independent evidence with exact current lineage |
| DATA7 selector-relevant fitted feature metric and subset inputs | RESTORE/REBIND | fit on exact current `P_train` under reconstructed policy |
| DATA7 atomic-reference fit, training objective, training/property weight authority | DO NOT RESTORE AS SELECTOR AUTHORITY | current P3 common training preparation owns these semantics |
| DATA7 checkpoint metric policy | DO NOT RESTORE AS SELECTOR AUTHORITY | current TRAIN2/EVAL2/P5 owners retain checkpoint/evaluation policy |
| `TargetCoveragePolicy` and `TargetCoverageReference` | RESTORE/REBIND | sole restored owner of multi-view coverage reference/witness semantics |
| FEAS1 | RESTORE/REBIND | one current P_train domain; current ladder capacity only |
| MVIDX1 | RESTORE/REBIND | one exact sparse relation for the current selector domain |
| MVSEL2 reference/full-forward path | RESTORE | independent exact oracle/fallback |
| MVSEL2 forward/lazy production engine | RESTORE | sole restored selection engine beneath P2 |
| qualified native/OpenMP sparse kernels | RESTORE where current build/runtime supports them | execution optimization only; exact rank must match reference |
| MVSTATE2 | RESTORE/REBIND | exact preparation continuation state; no campaign-currentness authority |
| REPAIR2 | RESTORE/REBIND | one repaired master order; shell schedule uses current configured candidate sizes |
| MVQUAL | RESTORE/REBIND | independent hard coverage/obligation verifier feeding current P2 qualification |
| old label-domain / preselection-fold selector fanout | DROP | one current P_train selector domain |
| old fixed `128..16384` size-study authority | DROP | current `ResolvedTargetSizePolicy.candidate_sizes` owns the configured ladder |
| old target-size study/reducer/selected-N authority | DROP | current EVAL2/reducer/provisional/frozen owners remain authoritative |
| old prescribed DATA8/per-domain materialization | DROP | current P3/P5 materialization remains authoritative |
| old campaign selector/currentness/migration records | DROP | current prepared-generation + campaign-store lifecycle owns currentness |
| MVSEL1/eager inverse/reuse1/failed PAR1 generations | DROP / REFERENCE_ONLY | superseded before the recovery snapshot |

The historical `TargetSubsetInputBundle` may be reused as a type only if it can be narrowed truthfully to selector-relevant fields without reintroducing P3/P5 authority. Otherwise introduce the smallest current selector-input projection backed by existing DATA6/DATA7 record types; do not create duplicate training-preparation machinery merely to preserve an old class name.

---

## 5. D1 scientific restoration contract

Gate R1 shall amend the current scientific method so that:

1. `pi_train` is a candidate-outcome-independent, multi-view coverage/representation-progressive training order;
2. membership support/coverage is distinct from model-accuracy evidence;
3. each configured `T_N` is an admissible target-size candidate only when its hard membership predicates pass independently;
4. EVAL2 selects `N` among admissible prefixes based on model behavior; MVQUAL does not choose `N`;
5. post-selection CV cannot feed back into `pi_train` or `N`;
6. candidate-model, EVAL2, CV, checkpoint-selection and production outcomes cannot influence target membership;
7. candidate-independent DATA6/DATA7 evidence used by the latest method—including structural/profile evidence and, where actually part of the recovered method, foundation/difficulty evidence—is not discarded merely because it is model- or label-derived; it remains subject to exact leakage/fit-domain rules;
8. the current P_train/M3 split and current evaluation population semantics remain unchanged.

The stakeholder has ratified the restoration direction. Exact D1 wording/input-role reconciliation remains proposed until independent falsification and required human acceptance complete.

---

## 6. D2 exact numerical restoration contract

D2 must be reconstructible without code archaeology. It shall recover the exact historical policy records from the recovery snapshot and then record only the current-binding deltas.

At minimum reconstruct and preserve-by-default:

- `TargetCoveragePolicy` fields and reference-family construction;
- DATA7 metric/fit policy fields actually consumed by selector/reference construction;
- FEAS1 feasibility predicates;
- exact MVIDX neighborhood relation, distance/scaling/radius semantics and canonical ordering;
- `TargetMultiViewSelectorPolicyV2` semantics;
- `TargetMultiViewRepairPolicyV2` semantics;
- MVQUAL hard predicates;
- FP64 reduction/order/tolerance rules;
- current-ladder adaptation;
- exact full-order continuation semantics.

### 6.1 Coverage policy and named-family overrides

The historical default hard family threshold is `0.95`, but the recovery snapshot's integrated specification permits an explicitly identified material/profile policy to override the threshold for a named family. Revision 5 therefore forbids flattening all families to one scalar if an accepted recovered family override is actually active.

R1 shall establish the exact threshold map:

```text
family_id -> threshold -> owning policy identity
```

If the historical normative spec permits an override but the last implementation cannot represent it, that is a historical spec/code discrepancy requiring explicit adjudication; it is not permission to silently drop the normative capability.

Canonical family order, witness order, weights, radii, scaling, obligations, correlation-unit order and stable UID order are scientific/numerical identity where the recovered method says they are.

### 6.2 Exact Phase-A authority

Use the recovered integrated specification and exact reference kernel. The staged authority is:

1. if required obligations remain unsatisfied, retain candidates with **maximum hard-obligation gain**;
2. from current family coverage ratios, choose the **first canonical minimum-coverage/bottleneck family** within the accepted tolerance; this chooses the family/state focus, not a separate candidate utility;
3. retain candidates with best gain in that bottleneck family using the inclusive `value >= best - epsilon` rule;
4. retain candidates with best total multi-family coverage gain;
5. retain candidates in the least-selected correlation unit;
6. retain candidates with best harmonic representative gain;
7. retain candidates with best sparse-diversity score;
8. stable UID is the final exact tie key.

Do not add an extra candidate-ranking stage between steps 2 and 3. Revision 4's wording was ambiguous enough to permit a nonexistent additional criterion.

The historical default contender tolerance is `1e-14`; any change requires D2 evidence rather than implementation convenience.

### 6.3 Exact Phase-B authority

After hard obligations/coverage complete, candidate comparison is:

1. representative gain;
2. least-selected correlation-unit balance;
3. sparse diversity;
4. stable UID.

Preserve the exact all-candidate rebase, conservative outward lazy bounds, exact refresh/certification and full-forward equivalence oracle. Execution batching/worker/backend may vary only when exact rank authority remains unchanged.

### 6.4 Do not relabel MVSEL2 diversity as classic FPS

The mature MVSEL2 diversity term is the recovered sparse-neighborhood inverse-multiplicity quantity, not classic Euclidean farthest-point sampling. Direct DATA7 FPS remains a historical/reference comparator. Current D1/D2 shall call the restored method what it is rather than describing it as FPS simply because this cycle began as an FPS restoration investigation.

---

## 7. One current obligation/support authority

Current P2 already has declarative `hard_support_obligations`; historical DATA7/MVSEL2 also carried hard obligations that could represent conditions, environments, events, profile support and other membership requirements.

R1 must create one exact **membership-obligation set identity** for the restored selector generation:

```text
current configured P2 support obligations
+ retained historical selector hard obligations
- exact semantic duplicates
- obligations whose only owner was retired topology
= one canonical restored obligation set
```

Rules:

- current `TargetSizePopulation.frame(uid).condition_id` remains the current categorical condition owner;
- DATA5/provenance/profile facts may supply correlation or obligation evidence without becoming a second condition owner;
- obligation IDs are stable and unique after reconciliation;
- contradictory obligations fail closed;
- MVSEL2/REPAIR2 consume the canonical set;
- MVQUAL independently verifies the same canonical set;
- current P2 candidate qualification projects the verified result rather than separately reimplementing a divergent obligation definition.

Do not force event/environment/profile obligations into the current narrow condition-only `TargetSizeHardSupportObligation` representation if doing so loses meaning. Version/generalize the representation or preserve a separate restored obligation record whose identity is bound into one qualification owner.

---

## 8. FEAS1, rung feasibility and no rescue policy

Restore FEAS1 as a complete-population preflight over exact current P_train and the restored coverage/obligation policy.

Distinguish:

1. **global infeasibility**: the complete P_train/reference authority cannot satisfy a required family threshold or required obligation -> `prepare` fails closed;
2. **rung infeasibility**: the complete population is feasible but a configured prefix size cannot satisfy the policy -> that candidate size is not qualified;
3. **insufficient qualified size population**: after current P2 qualification, fewer than the current funnel's required number of qualified candidate sizes remain -> fail with the current typed/actionable insufficient-candidate outcome; do not invent a rescue N, relax 0.95, or silently drop a hard family.

Current `ResolvedTargetSizePolicy` requires at least three configured candidate sizes and current experiment construction requires at least three qualified candidates. Preserve that requirement unless its current owner is separately reopened.

---

## 9. MVIDX1 and resource representation

Restore one exact authenticated sparse relation for the current selector domain. Scientific identity binds candidate/reference ordering, family identities, metric/scaling/radius semantics, sparse array content/dtypes/cardinalities, obligations/correlation incidence and schema/cache semantic version.

Execution-only worker/chunk/queue/mmap choices remain delegated when exact content and ranking are invariant.

Requirements:

- no per-N MVIDX copy;
- no product-scale eager inverse marginal arrays in normal MVSEL2/REPAIR2 execution;
- product-scale arrays may remain file-backed/content-addressed;
- every external array file referenced by a prepared generation has authenticated content identity and lifecycle protection while any current/recoverable generation references it;
- a pathname alone is never authority.

---

## 10. MVSEL2, REPAIR2 and exact one-order semantics

### 10.1 Historical configured-prefix semantics

Reconstruct the exact recovery-snapshot orchestration order between MVSEL2 and REPAIR2. Do not invent a new interleaving merely because the component algorithms are known individually.

For all ranks `<= Nmax_current` that correspond to current configured candidate shells, the restored implementation shall reproduce the historical algorithm after only the explicitly accepted current-domain/ladder rebinding.

REPAIR2 remains the sole repair authority and preserves by default:

- active-shell-only mutation;
- immutable protected lower prefixes;
- zero-unique/hard-safe removal admission;
- exact deficit/frontier replacement scoring;
- hard-obligation safety;
- strict no-hard-coverage regression;
- rank inheritance and deterministic future displacement;
- the recovered repair-policy defaults/tolerances/budgets;
- deterministic accepted/rejected repair trace.

Independent per-N repaired datasets are forbidden. There is one repaired master order.

### 10.2 Extending the historical order to current full `P_train`

Current `TargetTrainingOrder` requires an exact permutation of all P_train, while the historical chain was materially concerned with configured target rungs. The current adaptation shall preserve historical configured-prefix behavior and define the suffix exactly.

Preferred realization:

1. construct the restored historical MVSEL2 + REPAIR2 repaired master order through the largest current configured shell `Nmax_current`;
2. reconstruct an exact MVSEL2 forward state **from the final repaired prefix** and authenticated primitive MVIDX/obligation/correlation inputs;
3. do not patch or reconcile a stale pre-repair mutable state into the repaired state;
4. continue the same MVSEL2 phase logic from that reconstructed state to P_train exhaustion;
5. append those ranks to the repaired prefix without additional repair shells beyond the configured ladder unless R1 explicitly defines such shells.

If the exact historical algorithm already defines an equivalent continuation mechanism, reuse it instead. Any alternative must prove identical configured prefixes and deterministic full-order semantics.

Arbitrary UID suffix completion is prohibited.

---

## 11. MVSTATE2 restart semantics after repair

Revision 4 under-bound repair identity. A resumable checkpoint must authenticate the exact scientific position from which continuation is valid.

Restore the compact historical state quantities—selected prefix, family witness multiplicities/coverage mass, obligation counts, correlation counts, representative state—while rebinding identity to current:

- P_train / split identity;
- DATA7 selector-input identity;
- TargetCoverageReference/FEAS1/MVIDX1 identity;
- candidate/family/witness/obligation/correlation order identities;
- selector policy/version;
- repair policy/version and, after repair, exact repaired-prefix/repair-plan identity;
- schema/version.

After any accepted REPAIR2 swap:

1. all pre-swap lazy frontier state and any checkpoint that authenticates the pre-swap prefix are stale;
2. reconstruct the compact forward state from the exact repaired prefix and primitive sparse authority;
3. verify reconstructed multiplicities/coverage/obligation/correlation quantities against the prefix;
4. only then publish a new continuation checkpoint if more ranks remain to be selected.

This follows the historical lesson that selected-set equality alone does not authorize continuation after divergent mutation histories. No informal delta-patching between pre-repair and post-repair mutable states is allowed.

MVSTATE2 remains preparation-local continuation evidence. A completed prepared generation does not become current because an MVSTATE checkpoint exists.

---

## 12. MVQUAL and current P2 candidate qualification

MVQUAL independently recomputes hard coverage and obligation predicates from authenticated primitive inputs and repaired prefixes. Selector/repair counters cannot serve as MVQUAL's independent oracle.

For every configured N, conceptually:

```text
qualified(N) =
    prefix_exists(N)
    AND labels_training_usable(T_N)
    AND canonical membership obligations pass(T_N)
    AND every required multi-view family threshold passes(T_N)
```

Coverage is a membership-admissibility criterion, not a model-accuracy criterion.

### 12.1 One current qualification projection

Do not create a second public qualification authority beside current P2. Version current `TargetSizeCandidateQualification` (and dependent experiment-definition schema as needed) so it can bind at minimum:

- target size and exact candidate prefix digest;
- label usability;
- canonical obligation counts/unsatisfied IDs;
- MVQUAL result digest;
- required family coverage/deficit pass state or a resolvable digest to authenticated MVQUAL evidence;
- overall qualified state derived from the above.

The persisted P2 qualification is a projection of independent MVQUAL evidence plus current label/support checks; it does not recompute a competing multi-view algorithm.

Manual `select-target-size N` must reject a configured but MVQUAL-unqualified N without executing training/CV and without rebuilding selector evidence.

### 12.2 Monotonicity

For fixed repaired nested prefixes and positive coverage/obligation predicates, hard satisfaction cannot regress as N increases. PASS -> FAIL at a larger configured prefix is an invariant failure and fails closed. Do not weaken this to a warning.

---

## 13. Policy/schema identity and stale-generation rejection

The restored method must be identity-distinct from the current UID-capable `candidate_independent_priority.v1` path.

At minimum:

1. replace/version `ResolvedTargetSizePolicy.training_order_policy` with a new current token identifying the accepted restored MVSEL2 method;
2. bind exact restored coverage, selector, repair, qualification, provider/schema identities into the target-order scientific identity;
3. bind the current configured candidate ladder because REPAIR2 shell boundaries and MVQUAL rungs depend on it;
4. version qualification/experiment/prepared-generation schemas where old fields cannot losslessly authenticate the new evidence;
5. prohibit compatibility translation that reads an old UID-only `TargetTrainingOrder`/prepared generation and simply relabels it as MVSEL2 current.

An old generation may remain readable as historical evidence if useful, but it cannot satisfy the restored current policy. Re-preparation is required.

`TargetTrainingOrder.selection_evidence_digest` shall resolve to an authenticated restored selector-evidence manifest or equivalent exact digest composition. It may not remain an opaque hash with no recoverable bound inputs.

---

## 14. Prepared-generation/currentness architecture

The completed prepared generation remains the sole immutable preparation product consumed by downstream commands.

### 14.1 Completed selector component graph

Version the prepared representation coherently to bind, directly or through an authenticated selector manifest:

```text
current source/frame/P1 authorities
current P_train/M3 split
DATA6 raw selector evidence used
DATA7 selector-relevant fitted projection
TargetCoveragePolicy + TargetCoverageReference
FEAS1
MVIDX1 manifest + authenticated file-backed arrays
MVSEL2 policy/order evidence
REPAIR2 repaired-master-order evidence
MVQUAL configured-prefix evidence
current TargetTrainingOrder / experiment aggregate
current P3 common preparation
```

MVSTATE2 scratch/checkpoints are not a second completed scientific component. A completed generation may record the final continuation/trace identity for provenance, but downstream currentness never depends on live checkpoint scratch.

### 14.2 Preserve current publish-before-adopt and CAS fencing

Restoration must preserve the current expensive-prepare currentness pattern:

1. capture the exact campaign/configuration expectation before expensive selector construction;
2. build/reuse and authenticate all immutable selector components;
3. publish immutable content-addressed objects before adoption;
4. CAS-bind the completed prepared-manifest digest only if the captured expectation remains current;
5. if another prepare/configuration change wins first, the stale build remains inert/unreachable and cannot supersede the current generation merely because it finished later.

A corrupt/missing prepared selector component fails closed. Downstream commands do not repair it by rereading live source data.

### 14.3 Preparation configuration identity

Extend `preparation_configuration_identity` so any order-changing selector policy/provider/schema edit invalidates the prepared generation. It must include the restored target-order method/policy identity in addition to existing neutral partition, target-size and common-training preparation identities.

Execution scheduling/report-only settings remain outside scientific identity.

---

## 15. DATA6/foundation/provider resource lifetime

The exact latest DATA7/MVSEL2 field map determines whether foundation descriptors/predictions/difficulty remain required. If they do:

- reuse the existing current provider/descriptor owner rather than creating an MVSEL2-specific model loader;
- bind checkpoint/provider/model identity into selector evidence;
- acquire model resources only inside `prepare`;
- release the selector's model/provider residency before a later independent prepare owner (including replay preparation) acquires its provider;
- do not allow downstream manual/auto selection/CV/production to reacquire the selector provider;
- do not infer GPU residency/teardown outside the owner that actually holds the provider/process.

Functional CPU-safe qualification is required where feasible. Full production-scale GPU qualification remains deferred, but deferral does not authorize duplicate or unbounded provider lifetime.

---

## 16. Project Engineering Memory / Historical Applicability Set

This is mature-machinery restoration, so PEM is activated.

```yaml
pem_basis:
  accepted_project_state: 4eabe2ae9783c7ff92f3a1093c37502a01380812
  accepted_pem: hjin98/mdstats@4eabe2ae9783c7ff92f3a1093c37502a01380812:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: SP-001
    disposition: APPLICABLE
    reason: restoration must reconnect one selector beneath current P2 rather than create parallel old/new ordering or currentness owners
  - id: SP-002
    disposition: APPLICABLE
    reason: restored MVIDX/MVSTATE/repair/qualification/prepared identities must fail closed on stale or corrupt lineage
  - id: SP-003
    disposition: APPLICABLE
    reason: expensive selector/MVIDX products should remain immutable/content-addressed and restartable without live-source reconstruction
  - id: SP-004
    disposition: APPLICABLE
    reason: final acceptance must exercise real prepare -> persisted generation -> downstream consumer boundaries, not helper-only mocks
  - id: FF-001
    disposition: REVIEW_REQUIRED
    reason: applicable only if R1 retains foundation-model descriptor/prediction/difficulty inputs; then provider/model identity must not be duplicated or reconstructed inconsistently
  - id: FF-002
    disposition: APPLICABLE
    reason: MVSTATE2 restoration directly reintroduces interruption/resume and authenticated continuation boundaries
  - id: FF-003
    disposition: NOT_APPLICABLE
    reason: this cycle does not create a second destructive cleanup owner; external selector artifacts remain under existing prepared/storage lifecycle
  - id: FF-004
    disposition: REVIEW_REQUIRED
    reason: becomes applicable if restored selector evidence acquires accelerator-backed model providers during prepare; resource ownership must then remain with the real provider/process owner
  - id: FF-005
    disposition: APPLICABLE
    reason: the defect family directly warns against rebuilding preparation-owned target-size state in downstream select/CV/production commands
```

The accepted PEM has **PARTIAL** coverage and does not claim exhaustive pre-August-20 selector history. This work therefore supplements PEM with bounded direct historical intake over the exact recovery snapshot and relevant August 18-23 selector evolution. Absence from PEM is not evidence that a selector capability never existed.

### 16.1 Capability-transfer map

Before implementation closeout, maintain a bounded map:

```text
historical MVSEL2-chain capability
 -> current D1/D2/D3 owner/binding
 -> restored/rebound mechanism or explicit incompatible omission
 -> current acceptance/evidence route
```

At minimum include coverage reference families, hard obligations, correlation balance, representative utility, sparse diversity, exact forward/lazy oracle equivalence, REPAIR2, MVSTATE2, MVQUAL, restart/currentness and resource bounds.

---

## 17. Implementation gates

### R1 — exact D1/D2 historical reconstruction and challenge

1. Bind all recovery evidence to `3937881...` and exact file/spec identities.
2. Produce a field-by-field DATA6/DATA7 selector-input map.
3. Produce exact policy-field maps for coverage, selector, repair and qualification policies.
4. Resolve any historical normative-spec/code contradiction explicitly.
5. Reconcile one canonical membership-obligation set.
6. Define current-ladder and full-order continuation semantics.
7. Amend D1/D2 as proposed authority.
8. Perform independent D1/D2 falsification.
9. Obtain required human ratification before accepted-current promotion.

No D4 production cutover begins before this gate closes.

### R2 — source dependency-closure recovery

Recover/classify exact source at `3937881...`, including at least:

```text
feature_metric.py and selector-relevant DATA7 owners
target_coverage.py
target_coverage_feasibility / FEAS1 owners
target_coverage_sparse_index.py
target_coverage_sparse_forward_view.py
MVIDX builders/runtime
target_multi_view_selector.py shared record types
target_multi_view_selector_v2.py
mvsel2_selection_engine.py
mvsel2_phase_a_kernel.py
mvsel2_phase_b_kernel.py
mvsel2_native_backend.py + native source/build hooks where applicable
target_multi_view_selection_state_v2.py
target_multi_view_selection_history_v2.py
target_multi_view_repair.py shared record types
target_multi_view_repair_v2.py
target_multi_view_qualification_v2.py
independent scoring/reference helpers
serializers, tests, fixtures and benchmarks
```

Classify each recovered surface as `RESTORE_UNCHANGED`, `RESTORE_REBIND`, `REFERENCE_ONLY`, or `DROP`, with exact blob/source identity. Restore the smallest coherent closure that retains the latest mature chain; do not reintroduce superseded selector generations merely to satisfy old imports.

### R3 — current selector-input/coverage-reference integration

- bind exact P_train;
- restore selector-relevant DATA7 fitted evidence only;
- restore TargetCoveragePolicy/Reference;
- preserve current P3/P5 ownership of training preparation/checkpoint policy;
- bind exact provider/input identities.

### R4 — FEAS1/MVIDX1

- restore global/rung feasibility semantics;
- restore exact sparse multi-view relation;
- preserve bounded/file-backed behavior and authenticated content identities.

### R5 — MVSEL2/MVSTATE2

- restore exact reference and forward/lazy engine;
- prove reference/optimized rank equality;
- restore exact continuation-state authentication;
- reconstruct post-repair state rather than patching stale state.

### R6 — REPAIR2/full order

- restore exact historical repair sequence and policy;
- rebind shells to current configured sizes;
- prove lower-prefix immutability/no hard regression;
- extend deterministically from final repaired configured prefix to full P_train.

### R7 — MVQUAL/current qualification

- restore independent MVQUAL from primitive inputs;
- version current candidate qualification as needed;
- preserve >=3 qualified-candidate funnel requirement;
- reject unqualified manual selection.

### R8 — prepared generation/currentness/resource lifecycle

- version/bind selector prepared components;
- bind selector method into preparation configuration identity;
- preserve publish-before-adopt/CAS fencing;
- prove downstream commands load prepared products only;
- prove provider teardown/lifetime where model-derived selector evidence is retained.

### R9 — assembled acceptance/documentation/closeout

- update D1/D2 method papers, D3 architecture, D4/current specs, configuration/help where affected, semantic history and workplan index;
- run complete affected regression and assembled real-owner integration;
- perform closeout learning assessment/PEM update only if admission criteria are met;
- archive superseded plans only after accepted closure.

---

## 18. Required falsification and acceptance evidence

### 18.1 Historical-equivalence/reference tests

For semantics intentionally unchanged by rebinding:

- full-forward reference vs optimized/lazy MVSEL2 exact rank equality;
- recovered reference/kernel Phase-A contender/winner equality;
- Phase-B lazy vs full-forward equality;
- restart/resume vs uninterrupted equality;
- qualified worker/batch/backend invariance;
- REPAIR2 final repaired-order and accepted/rejected swap-trace equality on preserved fixtures;
- independent MVQUAL equality to primitive recomputation;
- recovered policy serialization/digest round trips.

Historical fixtures must be provenance-bound to the recovery snapshot. Do not regenerate expected values from the candidate under test.

### 18.2 Current-domain counterexamples

Required cases include:

1. UID clustering cannot dominate genuine coverage ranking.
2. Single-condition structural diversity still progresses.
3. Multi-view conflict exposes the worst/bottleneck family even when aggregate coverage looks good.
4. Hard-obligation gain outranks discretionary utility while obligations are pending.
5. First-canonical bottleneck-family tie behavior is deterministic.
6. Correlation/provenance imbalance is corrected where retained policy requires it.
7. Duplicate/near-duplicate candidates do not consume early ranks unnecessarily under the restored relation.
8. Family/profile threshold override, if supported, cannot be flattened to global 0.95.
9. Candidate/CV/EVAL2/production outcome perturbations cannot alter pi_train.
10. Current P2 condition identity cannot be replaced by a historical DATA5/label-domain condition owner.
11. Selector-irrelevant DATA7 objective/E0/weight/checkpoint fields cannot become membership authority.
12. Changing current candidate ladder changes only policy/shell-dependent ancestry and forces reprepare; no fixed-eight assumptions survive.
13. Full-pool impossible coverage/obligation fails prepare without threshold relaxation.
14. Rung-infeasible candidates are unqualified; fewer than three qualified candidates fail without rescue sizes.
15. Manual selection of an unqualified N fails before training/CV.
16. Old UID-only prepared generation cannot load as restored-current by schema/token translation.
17. Missing/corrupt MVIDX/prepared external artifact fails closed; downstream does not reconstruct from live inputs.
18. Interrupted pre-publication selector state cannot become current.
19. Competing prepare/currentness change cannot be overwritten by a stale selector build that finishes later.
20. Pre-repair MVSTATE checkpoint is rejected after an accepted repair swap.
21. Rebuilt post-repair state exactly matches primitive replay of the repaired prefix.
22. Continued suffix after final repair is deterministic and does not alter configured repaired prefixes.
23. Manual `select-target-size N` performs no DATA6/DATA7/coverage/MVIDX/MVSEL/repair/MVQUAL reconstruction.
24. If foundation evidence is retained, selector provider identity/lifetime is authenticated and no overlapping replay/provider residency is introduced.

### 18.3 Resource evidence

On representative current-scale input report at least:

```text
|P_train|
selector feature/view families and dimensions
witness counts and sparse edges by family
coverage-reference build wall/RSS
FEAS1 wall/RSS
MVIDX build wall/RSS/scratch/artifact size
MVSEL2 wall/RSS/checkpoint size
REPAIR2 wall/RSS/swaps
MVQUAL wall/RSS
prepared-generation component sizes
provider/model residency where applicable
```

Historical performance is design evidence, not current qualification. If performance regresses, first recover the already-qualified forward/lazy/native/OpenMP realization before considering any D2 simplification.

### 18.4 Real-owner assembled acceptance

Exercise:

```text
prepare
 -> current P_train
 -> restored selector evidence/reference/FEAS/MVIDX
 -> MVSEL2/REPAIR2/MVQUAL
 -> immutable prepared generation publish + CAS adopt
 -> process restart / exact reload
 -> manual select-target-size
 -> auto diagnostic path
 -> cross-validate freeze
 -> fresh production planning
```

Mocks may replace external expensive providers below their owner boundaries, but may not replace prepared-generation publication/currentness, target-order construction, repaired-prefix qualification, restart authentication or downstream routing being claimed.

---

## 19. Identity/invalidation and impact closure

The restored selector changes target-order semantics. Therefore old evidence depending on UID-capable `pi_train` becomes stale where membership/order ancestry changes.

Invalidate/rebuild as applicable:

- target-order policy/evidence identity;
- candidate prefix digests;
- candidate-qualification records;
- target-size experiment-definition/aggregate digest;
- prepared-generation identity;
- screen evidence for changed T_N;
- provisional/frozen selection bindings whose membership digest changes;
- P5 CV evidence for changed T_N;
- final-production evidence for changed T_N.

Preserve with explicit reason where semantically unchanged:

- source/frame authentication;
- exact P_train/M3 split if unchanged;
- pi_eval/M1/M2/M3;
- EVAL2 numerical algorithm and target metric;
- current training objective/P3 method;
- replay semantics;
- post-selection CV acceptance method;
- production method;
- scheduler/CUDA/storage owners outside the affected selector/preparation surface.

Historical selector qualification can validate restored unchanged mechanisms but cannot directly certify current one-P_train/current-ladder rebinding.

---

## 20. Documentation/current-state reconciliation

Before the cycle can close:

- current D1 and D2 describe the accepted restored method, not UID fallback;
- current D3 architecture shows the restored selector beneath one P2/prepared owner;
- current D4/specification index names the actual current selector/coverage/qualification owners;
- current configuration/help describes any user-visible selector policy fields;
- semantic history records that P6 over-broadly removed a still-required selection capability and that this cycle restores it under current ownership;
- `workplans/active/README.md` lists this cycle as active until closure;
- superseded Revision 1-4 workplans/reviews remain clearly non-current and are archived/cleaned only after accepted closeout.

---

## 21. Non-goals

This cycle does not:

- restore MVSEL1/eager-inverse/MVSTATE-REUSE1 or failed PAR1 candidate-thread execution;
- restore per-label-domain or preselection-CV target-size authority;
- restore the historical fixed-eight target-size decision policy;
- restore the old target-size study/reducer/selected-N owner;
- restore selector-irrelevant DATA7 E0/objective/weight/checkpoint authority over current P3/P5;
- restore old prescribed per-domain materialization;
- restore migration compatibility for retired derived selector records;
- use MVQUAL as a model-accuracy criterion;
- allow downstream commands to reconstruct selector science from live inputs;
- perform final production-scale GPU qualification.

---

## 22. Pass criteria

This cycle passes only when all of the following hold:

1. exact historical recovery is bound to `3937881...` with no cross-commit hybrid semantics;
2. current D1/D2 explicitly own the restored latest coverage/reference/MVSEL2/REPAIR2/MVQUAL method and every intentional omission has a concrete current incompatibility reason;
3. exact current P_train is the single selector domain;
4. selector-relevant DATA7 inputs are restored without reintroducing P3/P5 training-preparation authority;
5. TargetCoveragePolicy/Reference, FEAS1, MVIDX1, MVSEL2, REPAIR2 and independent MVQUAL are restored under current preparation/P2 ownership;
6. exact Phase-A/Phase-B ranking/tie/reduction semantics match the recovered method after accepted rebinding;
7. one canonical membership-obligation set is shared by selection/repair/qualification;
8. current configured candidate sizes replace fixed-eight target-size authority while their shell dependence is identity-bound;
9. every qualified configured T_N satisfies independent hard multi-view coverage/support predicates;
10. the current >=3 qualified-candidate funnel rule remains intact and no rescue threshold/size is invented;
11. current `TargetTrainingOrder` remains one exact full permutation of P_train, with deterministic suffix semantics after the last repaired configured shell;
12. post-repair continuation state is reconstructed/authenticated from the repaired prefix; stale pre-repair state is never patched forward;
13. a new selector-policy/schema identity prevents UID-only generations from being admitted as restored current state;
14. prepared selector evidence is immutable/authenticated, publish-before-adopt/CAS fenced, and downstream commands never rebuild it from live sources;
15. foundation/provider resources, if retained, have one current owner and bounded lifetime;
16. historical-reference, current-domain, restart/currentness, corruption, no-legacy-path and resource evidence all pass;
17. materially dependent evidence/documentation/current-state indexes are reconciled;
18. PEM/HAS and capability-transfer obligations are closed or explicitly preserved for closeout;
19. production-scale GPU qualification remains deferred to the final complete-release package.

Until these conditions hold, the current UID-capable target-order path remains under **SERIOUS CHALLENGE**.
