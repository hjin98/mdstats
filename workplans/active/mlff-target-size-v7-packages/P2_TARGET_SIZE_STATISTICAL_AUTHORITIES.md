---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P2
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 2
status: active
package_revision: 3
amended_date: 2026-08-28
entry_p1_commit: 8ccee5a1068f8481df6a3e33ddb5f09f73654391
reviewed_implementation_commit: eb0fd0d52ede072d62ec8b136295654a9c19206e
rework_reason: P1 remains frozen. Revision 2 established the complete P2 statistical-authority contract. Independent implementation review of commit eb0fd0d52ede072d62ec8b136295654a9c19206e found two blocking closure gaps without invalidating that architecture: P2 split construction did not consume every P1 split-excluding/protected relation, and explicitly configured hard-support obligations were not represented or enforced during target-prefix qualification. Revision 3 adds precise corrective instructions, restart authentication, focused negative tests, and version-agnostic funnel-schema cleanup. All unaffected Revision 2 requirements remain frozen.
---

# P2 — Target-size statistical authorities

## Purpose

Build the complete current-generation target-size **statistical experiment definition** on top of the accepted P1 neutral substrate, while keeping it unreachable from current production commands until P4.

P2 owns:

- the canonical resolved target-size scientific policy;
- the exact target-size-authorized population `U_size` projected from P1;
- one deterministic `P_train/M3` split under P1 correlation/duplicate leakage constraints;
- one deterministic target-training order `pi_train`;
- one deterministic evaluation order `pi_eval` and exact `M1/M2/M3` ladder;
- exact candidate memberships `T_N = pi_train[:N]`;
- the pure successive-fidelity study/reducer state and its persistence/restart semantics.

P2 does **not** own common DATA7/E0/normalization/objective fitting, candidate materialization, MACE/TRAIN2/EVAL2 execution, post-selection CV, or current-runtime persistence cutover. Those remain P3/P4/P5 responsibilities under the frozen parent plan.

The parent `MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the sole scientific/architectural authority. This package is a lossless implementation refinement beneath it; it does not reopen that verdict.

All new durable product packages, classes, functions, symbols, schemas, and persisted authority names introduced by P2 must be **version-agnostic**. `V7` may remain in workplan/generation/process metadata, not in product-code names.

## Entry conditions

- P1 exit gate is accepted at or after commit `8ccee5a1068f8481df6a3e33ddb5f09f73654391`.
- `SourceAuthority`, `CanonicalFrameAuthority`, `NeutralFeatureEvidence`, and `NeutralStatisticalBase` are the accepted current-generation P1 owners.
- P1 aggregate restart validation and deterministic neutral statistical semantics are preserved.
- Parent V7 workplan remains unchanged in authority.
- P2 remains internal/unreachable from current production prepare/select-target-size commands until P4.

## Protected concerns

P2 must preserve all of the following simultaneously:

- target size `N` is the one experimental data-cardinality variable;
- one study exists regardless of provenance/compatibility-group count;
- P1 protected outer evidence never leaks into target-size training/evaluation populations;
- training and evaluation are disjoint under the actual P1 temporal/correlation/duplicate constraints, not merely by raw frame UID;
- target candidate and M-ladder memberships are exact deterministic derivations, not independently editable persisted claims;
- the ordered optimizer-seed set is the only target-size stochastic replicate namespace;
- candidate-independent evaluation ordering freezes before any candidate outcome exists;
- CV state/configuration is absent from target-size identity;
- common preparation/training scientific identity will be bound by P3 before real execution evidence is accepted;
- stale/replayed/rehashed persisted statistical state fails closed rather than being silently repaired;
- useful optimized selection kernels may be reused internally without preserving the retired public FEAS/MVIDX/MVSEL/REPAIR/MVQUAL topology;
- default-scale ordering/splitting must remain resource-feasible and must not regress into unjustified dense quadratic state;
- full long GPU/real-production qualification remains deferred; bounded functional/reference/resource checks remain required where affected.

## Frozen cross-package ownership

The intended authority chain is:

```text
P1 CanonicalFrameAuthority + NeutralStatisticalBase
  -> canonical target-size policy resolution
  -> TargetSizePopulation / U_size
  -> one P_train/M3 split
  -> one pi_train + one pi_eval
  -> derived T_N + M1/M2/M3
  -> pure target-size experiment definition/reducer
  -> P3 binds common preparation/training execution context
  -> real TRAIN2/EVAL2 evidence may advance reducer state
```

Exact implementation names are delegated, but this ownership and dependency direction are frozen.

P2 may not depend on DATA7, DATA8, TRAIN2, EVAL2 execution, CV plans, current campaign persistence, label-domain maps, or the retired target-size multi-authority chain in order to construct the statistical experiment.

---

## Revision 3 mandatory rework overlay — blocking review closure

This overlay is a **narrow corrective amendment** to Revision 2. It has precedence wherever it makes a Revision 2 requirement more explicit. It does not reopen P1, the parent architecture, the target-size decision rule, the evaluation ladder, or the P2/P3 execution boundary. Requirements not mentioned here remain unchanged.

The implementation under review is `eb0fd0d52ede072d62ec8b136295654a9c19206e`. P2 remains **not accepted** until every requirement and negative test in this overlay is satisfied on one reviewed candidate.

### R3.1 — inherit the complete P1 split-exclusion authority

#### Problem closed by this amendment

The reviewed split component builder treated same-P1-unit membership and exact geometry-duplicate membership as the complete split-exclusion graph. Revision 2 requires those relations **plus every additional P1 relation explicitly designated split-excluding/protected**. Omitting such a relation can place correlated/protected frames on opposite sides of `P_train/M3` while all local P2 digests remain valid.

#### Required ownership and data flow

P2 must consume one canonical P1-owned split-exclusion relation authority when it constructs the `U_size -> P_train + M3` constraint components:

```text
accepted P1 authority
  -> canonical P1 split-exclusion relation evidence/identity
  -> U_size projection
  -> full split-constraint connected components
  -> exact P_train/M3 allocation
```

Frozen rules:

1. Same P1 neutral partition/correlation unit and exact canonical geometry-duplicate membership remain mandatory split-excluding relations.
2. They are **not** an exhaustive definition. Every other P1 relation whose accepted semantics mark it `split-excluding`, `protected`, or equivalent must enter the same component graph.
3. P2 may not rediscover or reinterpret those P1 relations from raw features, labels, provenance, or ad hoc campaign state. The relation semantics belong to P1.
4. If the accepted P1 objects do not currently expose a canonical consumable relation authority, make the **smallest P1 owner/API extension necessary to expose existing P1 semantics**. Do not alter P1 partition membership, invent a new P2 relation taxonomy, or create a parallel source of truth.
5. The P1 relation representation may be edges or groups. P2 must reduce it deterministically to the same transitive split-exclusion closure. For every relation containing two or more frames that are members of `U_size`, those in-`U_size` endpoints belong to one connected component. A chain through unit, duplicate, and additional protected relations is one component even when no single relation spans the full chain.
6. Relations wholly outside `U_size` do not create new P2 membership. Relations touching P1-protected outer roles remain governed by P1's own validity semantics; P2 may not silently downgrade an invalid P1 lineage into an ignorable edge.
7. Exact `M3` feasibility/allocation runs **after** the complete connected-component closure is constructed. A greedy or partial pre-pass may not allocate before all protected relations are applied.

#### Canonical identity and restart binding

The accepted P1 split-exclusion relation authority must have a deterministic canonical identity/digest. Exact field/class names are delegated, but the identity must be derived from canonical P1 relation content and lineage, not Python object identity, traversal order, or an unordered container representation.

That identity must be bound into the P2 split/restart derivation chain strongly enough that:

- changing only the inherited P1 split-exclusion relation content invalidates the old `P_train/M3` split;
- stale `pi_train`, `pi_eval`, `T_N`, M-ladder, reducer evidence, and terminal state cannot survive such a change by locally rehashing only the edited object;
- aggregate deserialization re-derives/validates the split through the actual P1/P2 owners rather than trusting a stored relation digest as a standalone claim.

Do **not** create a new independently editable P2 scientific authority for these relations. They are inherited P1 authority and P2 stores only the binding/derivation evidence required for deterministic validation.

#### Required focused tests

Add direct tests through the real P1/P2 owners proving all of the following:

1. **relation-only protection:** two `U_size` frames with different unit identities and different geometry fingerprints but joined only by an additional P1 split-excluding/protected relation can never be separated across `P_train/M3`;
2. **transitive mixed closure:** a chain such as unit relation -> geometry duplicate -> additional protected relation collapses into one indivisible component;
3. **exact-allocation preservation:** the full relation graph still finds an exact feasible `|M3| = m3` allocation when one exists and fails deterministically when none exists;
4. **changed-authority restart rejection:** mutate/rebuild the P1 protected-relation authority while keeping locally valid serialized P2 component digests; aggregate restart rejects the stale split and descendants;
5. **no relation-source fanout:** structural inspection proves P2 has one P1 relation input and does not independently infer split-excluding relations from provenance/CV/candidate outcomes.

Existing unit/geometry duplicate, exact-cardinality, disjointness, and greedy-versus-reference feasibility tests remain mandatory and must continue to pass.

### R3.2 — explicit hard-support obligation authority and prefix qualification

#### Problem closed by this amendment

Revision 2 states that a candidate prefix is qualified only when the prefix exists, labels remain training-usable, **and explicitly configured hard support obligations are satisfied**. The reviewed implementation contains priority/support diagnostics but no canonical hard-obligation representation or qualification gate, so an N-prefix can currently enter the funnel while violating an explicitly mandatory support requirement.

#### Canonical hard-obligation contract

Extend the resolved target-size scientific policy with an explicit canonical hard-support-obligation collection.

Frozen semantics:

1. The default/no-configuration representation is one canonical **empty collection**. Empty obligations preserve the current Revision 2 behavior; no legacy coverage/balance heuristic becomes a hard gate by default.
2. A hard obligation is declarative and serializable. It must identify a support subset using only **frozen pre-candidate evidence already authorized for P2 ordering/qualification**, together with the required minimum membership/count or equivalent deterministic satisfaction criterion.
3. Exact schema names are delegated, but obligation identity may not depend on callbacks, object identity, mutable runtime state, model predictions, candidate outcomes, CV state, or execution results.
4. Normalize obligations before hashing: stable ordering, canonical selector representation, validated nonnegative/positive bounds as appropriate, no duplicate contradictory aliases, and deterministic rejection of malformed/unknown selectors.
5. Only obligations explicitly present in this resolved collection are hard gates. Coverage, novelty, uncertainty, residual/support-gain, balance, provenance, and other diagnostics remain ordering/observational evidence unless the user/configuration explicitly expresses the corresponding hard obligation through this authority.
6. The normalized hard-obligation collection participates in canonical target-size policy identity. Editing it invalidates the appropriate P2 descendants and any P3 execution evidence derived from them.

Do not create a second public qualification topology. Hard-obligation resolution belongs to the existing target-size policy/order experiment owner and produces derived qualification evidence.

#### Candidate-prefix qualification

For each configured candidate size, derive the candidate exactly as before:

```text
T_N = pi_train[:N]
```

Then deterministically qualify that exact prefix:

```text
qualified(N) =
    prefix_exists(N)
    AND labels_training_usable(T_N)
    AND all_configured_hard_support_obligations_satisfied(T_N)
```

Frozen rules:

- Qualification may **not** reorder, repair, swap, or construct a different prefix for an individual N.
- There remains exactly one `pi_train` for the study. If a hard obligation is intended to affect global training-order prioritization, that effect must be part of the one frozen order policy before `pi_train` is built; qualification itself never mutates the order.
- Derive deterministic per-N qualification evidence containing enough information to explain pass/fail and to reproduce the decision. Persisted qualification evidence is derived/checkable state, not an independently editable authority.
- Only qualified configured N values may enter ordinary funnel execution or accept ordinary TRAIN2/EVAL2 evidence.
- After qualification, the eligible candidate set must still satisfy the existing P2-A structural precondition needed by the frozen `q -> min(q,4) -> 2 -> 1` funnel. If it does not, fail **before expensive training** with deterministic required/available candidate information. Do not relax a hard obligation, synthesize a candidate size, or silently change the funnel.
- Qualification is based only on frozen P1/P2 membership/evidence and resolved policy. It must not depend on optimizer seed results, evaluation outcomes, survivor state, or P3 runtime accidents.

#### Restart/authentication consequences

Bind normalized hard-obligation identity and derived candidate-qualification state into the aggregate derivation graph so that:

- changed hard obligations reject stale `pi_train` descendants/qualification/funnel/reducer evidence as appropriate;
- a stored `qualified=true` cannot survive when recomputation from the exact prefix and current obligation policy returns false;
- ordinary real evidence for an unqualified N is rejected rather than accepted and later ignored;
- coordinated local rehashing of policy/qualification objects cannot counterfeit a valid aggregate lineage.

Re-use the existing aggregate constructor/from-dict/restart boundary. Do not add a helper-only validation path that production restart bypasses.

#### Required focused tests

Add tests proving:

1. **empty authority compatibility:** empty hard obligations reproduce current prefix qualification and do not change `pi_train`;
2. **satisfied obligation:** an explicitly configured obligation is satisfied by a prefix and the candidate is admitted;
3. **prefix threshold behavior:** early configured N values fail and the first sufficiently supported larger exact prefix passes, without any per-N reorder/repair;
4. **impossible obligation:** no configured prefix can satisfy an obligation; failure occurs before expensive funnel execution and reports the structural qualification failure deterministically;
5. **policy identity:** changing only the normalized hard-obligation definition changes target-size policy identity;
6. **restart rejection:** changed obligations with stale persisted qualification/reducer evidence are rejected through the real aggregate deserializer;
7. **soft diagnostic isolation:** changing a diagnostic-only coverage/support threshold or score that is not explicitly a hard obligation cannot turn candidate eligibility on/off;
8. **single-order invariant:** qualification of multiple N values never constructs or persists separate per-N master orders;
9. **evidence admission:** reducer/execution-boundary tests reject ordinary evidence for an N that is not qualified under the bound policy.

### R3.3 — remove fidelity values from the funnel schema name

The reviewed implementation uses a stale value equivalent to:

```text
FUNNEL_SCHEMA = "target-size-funnel/3-6-10-v1"
```

while the accepted resolved default fidelity is `(1,3,10)`.

Required correction:

- replace the product schema identifier with a **version-agnostic, fidelity-agnostic** schema name such as `target-size-funnel/v1`;
- the actual `fidelity_epochs` tuple remains the sole scientific identity for the configured boundary values;
- no schema/type/symbol name may encode the historical `3/6/10` ladder;
- statically inspect P2 product code and focused tests for stale `3-6-10`, `3/6/10`, fixed-6-middle-boundary, or equivalent superseded fidelity literals. Historical workplan prose may retain historical values only when clearly marked historical/non-authoritative;
- add/retain an identity test proving that changing `fidelity_epochs` changes target-size policy identity even though the schema name itself stays unchanged.

This is an identity/schema cleanup, not permission to change the accepted default `(1,3,10)` or production `[training].max_num_epochs` semantics.

### R3.4 — mandatory re-pass and closure evidence

The correction round is accepted only on one candidate commit that satisfies all Revision 2 gates plus this overlay.

Required closure sequence:

1. implement R3.1 and run its focused tests plus affected P1 neutral-statistical regression;
2. implement R3.2 and run policy/order/prefix/reducer/restart focused tests;
3. implement R3.3 and run static/schema/config identity regression;
4. run the complete P2 focused suite, not only newly added tests;
5. run all affected P1/P2 regression tests for modified and newly introduced owners;
6. run bounded P1 -> P2 integration through the real aggregate serialization/deserialization boundary;
7. run repository-required Python/package/import/static checks on the same candidate.

Final review must explicitly establish:

- no P1 split-excluding/protected relation can be cut by `P_train/M3`;
- exact `|M3| = m3`, `|P_train| >= Nmax`, disjointness, and deterministic exact-feasibility behavior remain intact;
- hard obligations gate prefixes **only when explicitly configured**;
- diagnostic-only support/coverage machinery remains non-gating;
- one `pi_train`, one `pi_eval`, exact prefix nesting, and candidate-independent evaluation ordering remain unchanged;
- restart rejects changed inherited P1 relation authority and changed hard-obligation authority;
- no new CV/provenance/compatibility-domain/per-seed/per-candidate authority fanout was introduced;
- no production runtime cutover occurred;
- no full GPU/long production qualification is required for this P2 correction. Bounded functional/reference/resource tests remain the acceptance evidence, consistent with the parent plan.

**Gate rule:** P2 remains **NO PASS** until both blocking fixes have direct positive and negative tests through the real owners, all affected regression/integration checks are green, and an independent review finds no remaining genuinely blocking issue.

---

## Pass P2-A — canonical size/evaluation/fidelity policy authority

Implement one canonical resolver for the target-size scientific policy. Downstream P2 objects consume only the resolved representation, not scattered parser/default state.

Resolve at least:

```text
candidate_sizes = [2^p for p in pmin..pmax]
Nmax = max(candidate_sizes)
(m1,m2,m3) = [2^q for q in evaluation_size_powers]
(n1,n2,n3) = fidelity_epochs
ordered screening optimizer seeds = sole enabled method's target-size optimizer seeds
paired-seed aggregation = arithmetic_mean under current policy
target force ranking metric + practical-equivalence policy
```

### Frozen requirements

- Current defaults reproduce the frozen parent defaults:
  - target-size powers `7..14`;
  - evaluation powers `[8,9,10]`;
  - fidelity epochs `[1,3,10]`;
  - ordered optimizer seeds `[1,2]`.
- Candidate sizes are unique, strictly increasing positive powers resolved from the configured inclusive power range.
- The configured candidate universe must contain enough distinct sizes to execute the configured `q -> min(q,4) -> 2 -> 1` funnel; invalid degenerate ranges fail before expensive work.
- Evaluation sizes are exactly three unique strictly increasing positive sizes with `m1 < m2 < m3`.
- Fidelity boundaries are exactly three strictly increasing positive integer epochs with `n1 < n2 < n3`.
- `[training].max_num_epochs`/production horizon is independent of `n3` and is not part of the P2 fidelity ladder.
- No hidden fixed-eight or fixed-16384 scientific guard remains in current-generation P2 objects.
- Exactly one nonempty ordered set of unique nonnegative optimizer seeds belongs to the study and is sourced from the sole enabled target-size training method.
- Feature/projection, replay, evaluation-order, bootstrap, monitor, CV-fold, or unrelated fields named `seed` cannot enter the target-size replicate set implicitly.
- A target-size optimizer seed-set edit changes target-size scientific policy identity and invalidates P2/P3 target-size descendants.
- CV-only fold count/partition-seed changes do not change P2 target-size policy identity.
- The ranking metric/practical-equivalence policy that can change target-size decisions participates in target-size scientific policy identity.
- Canonical serialized resolved values, not partial user input or unordered implementation representations, own the policy digest/identity.

### Verification cycle

1. focused default/non-default normalization, boundary, and invalid-combination tests;
2. affected config/template/spec regression;
3. canonical serialization/digest stability tests;
4. identity tests proving target-size seed/power/fidelity/ranking-policy edits invalidate target-size identity while CV-only changes do not;
5. negative seed-namespace tests proving unrelated seeds cannot masquerade as optimizer replicates.

Complete stage-local affected regression before P2-B.

---

## Pass P2-B — authoritative P1 -> `U_size` projection and one `P_train/M3` split

### B1. Freeze `U_size` from real P1 owners

Do not treat `U_size` as an untyped list supplied by callers.

Construct it from the exact accepted P1 authorities:

```text
CanonicalFrameAuthority
+ NeutralStatisticalBase
+ exact shared lineage
  -> TargetSizePopulation / U_size
```

`U_size` is a population of **canonical configurations/frames**. Cardinalities `N`, `Nmax`, `m1/m2/m3`, `|P_train|`, and `|M3|` count configurations, not neutral units, blocks, effective-sample counts, or correlation groups.

A frame may enter `U_size` only when all required conditions hold:

- its P1 canonical frame/label authority is valid for the configured target training operation;
- it belongs to the exact `NeutralUnitCatalog` carried by the same accepted `NeutralStatisticalBase`;
- its neutral outer role is explicitly `DEVELOPMENT`;
- it is not `OUTER_MONITOR`, `UNCERTAINTY_CALIBRATION`, `LOCKED_INTERPOLATION_TEST`, `PURGED`, or otherwise protected/excluded by the accepted P1 statistical state;
- all P1 aggregate lineage/policy identities agree; no caller-supplied reinterpretation of stale component state is accepted.

P2 must preserve a deterministic mapping from each `U_size` frame to the P1 unit/correlation evidence and canonical duplicate evidence needed by the split/order owners.

### B2. Split constraints and leakage ownership

Build one deterministic split:

```text
U_size -> P_train + M3
```

with exact configuration cardinality invariants:

```text
P_train intersect M3 = empty
|P_train| >= Nmax
|M3| = m3
```

The nominal count lower bound remains `Nmax + m3`, but successful construction must prove a real feasible allocation under the actual P1 leakage constraints.

At minimum, frames may not be separated across `P_train` and `M3` when they belong to:

- the same P1 neutral partition/correlation unit; or
- the same exact canonical geometry-duplicate group.

Any additional P1 relation explicitly designated as split-excluding/protected must likewise be honored. These relations constrain allocation; they do **not** become label/provenance domains and do not multiply the study. **Revision 3 R3.1 is the mandatory implementation contract for this sentence: the complete inherited P1 relation authority, its transitive closure, identity binding, and restart-negative tests are required.**

Training support has priority. Subject to exact feasibility and protected disjointness, M3 should preferentially consume redundant residual support while retaining useful representative/condition coverage according to one deterministic split policy.

A production allocator must not declare scientific infeasibility merely because one greedy traversal failed when another valid allocation exists. Keep or construct a bounded exact/reference feasibility oracle suitable for adversarial fixtures; the production path may use a more efficient deterministic algorithm when reference-equivalent.

Persist enough deterministic diagnostic evidence to explain material capacity loss or infeasibility without creating another scientific authority.

### Verification cycle

1. focused P1 -> `U_size` projection tests through real `CanonicalFrameAuthority` + `NeutralStatisticalBase` owners;
2. negative tests proving physical-only/non-authoritative or non-`DEVELOPMENT` P1 frames cannot enter `U_size`;
3. exact allocation/cardinality/disjointness tests;
4. adversarial temporal-unit and exact-geometry-duplicate fixtures proving forbidden train/eval splits cannot occur;
5. **Revision 3 relation-only and mixed-transitive protected-relation fixtures through the real P1 relation owner;**
6. fixtures where naive greedy allocation fails but a valid allocation exists, checked against the bounded exact/reference oracle;
7. genuinely impossible correlation allocations fail explicitly and deterministically;
8. deterministic reconstruction/serialization tests;
9. **restart-negative test for changed inherited P1 split-exclusion relation authority;**
10. affected P1 neutral-statistical regression sufficient to prove P2 did not reinterpret P1 state.

Complete stage-local affected regression before P2-C.

---

## Pass P2-C — one durable current target-training order

Implement exactly one current owner:

```text
P_train + frozen selection evidence/policy -> pi_train + diagnostics
```

Reuse/refactor the optimized sparse/lazy MVSEL2/REPAIR2 numerical kernels only behind this owner when semantically justified. Do not persist or publicly expose FEAS/MVIDX/MVSEL/REPAIR/MVSTATE/MVQUAL as current-generation scientific authorities.

### Frozen invariants

- `pi_train` is an exact deterministic permutation of every configuration in `P_train`: no missing, duplicate, foreign, or additional frame identity.
- Every configured candidate is derived only as:

```text
T_N = pi_train[:N]
```

- `T_N` cardinality is exactly `N` configurations.
- Candidate sets are exactly nested by configured N.
- Required qualification remains intentionally small: the prefix exists, all member labels remain training-usable, and explicitly configured hard support obligations are satisfied. **Revision 3 R3.2 defines the mandatory canonical hard-obligation authority, exact-prefix qualification, restart binding, evidence-admission behavior, and diagnostic/non-gating boundary.**
- Rich coverage/diversity/residual diagnostics are observational/supporting evidence and do not recreate multiple public gate authorities.
- There is one order for the study, not one order per provenance group, compatibility group, CV fold, optimizer seed, or candidate.
- Persisted candidate membership, when serialized for convenience, is derived/checkable state. Restart must recompute/verify it against `pi_train` rather than trust an independently edited membership/digest.

### Scaling/performance requirement

The current-generation owner must retain target-scale feasibility. For representative default-scale input, do not regress into unjustified dense `O(|P_train|^2)` pair/state materialization, repeated full rescans with materially bad scaling, or redundant repeated I/O merely because old optimized kernels are hidden behind a new owner.

Preserve a simple bounded reference/oracle for semantic comparison. Reused optimized sparse/CSR/lazy scoring/repair machinery must remain reference-equivalent on bounded fixtures. Performance acceptance is bounded CPU/RAM/I/O/scaling evidence, not full production qualification.

### Verification cycle

1. exact permutation/prefix/nested-membership tests for all configured N;
2. deterministic tie/order/restart tests;
3. **Revision 3 hard-obligation pass/fail, first-satisfiable-prefix, impossible-obligation, policy-identity, soft-diagnostic-isolation, and stale-restart tests;**
4. reference/oracle equivalence for reused optimized kernels;
5. representative scaling and peak-RAM checks sufficient to detect dense-quadratic or repeated-rescan regression;
6. structural inspection proving no per-provenance/per-CV/per-seed/per-candidate master-order fanout exists in the current owner.

Complete stage-local affected regression before P2-D.

---

## Pass P2-D — one evaluation order and exact M ladder

Freeze one `pi_eval` over the exact M3 reserve using only candidate-independent evidence available before any candidate training/result exists:

```text
pi_eval = exact deterministic permutation of M3
M1 = pi_eval[:m1]
M2 = pi_eval[:m2]
M3 = pi_eval[:m3]
```

### Frozen invariants

- `pi_eval` contains every M3 configuration exactly once and no foreign configuration.
- `M1 subset M2 subset M3` is exact prefix nesting.
- `|M1|=m1`, `|M2|=m2`, `|M3|=m3`.
- All M configurations are disjoint from every `T_N` by construction because M3 is disjoint from P_train under the stronger P1 correlation/duplicate split constraints.
- No complement subtraction, fallback population, CV monitor role, or candidate-dependent population repair exists.
- Candidate predictions, metric results, survivor state, optimizer seed outcomes, or selected N cannot be supplied to or influence the evaluation-order owner.
- Evaluation-order randomness, if the frozen policy uses any, is a fixed evaluation-order policy seed and not an optimizer replicate.
- Persisted M memberships are derived/checkable from `pi_eval`; restart re-derives and verifies them.

### Verification cycle

1. exact permutation/nested-membership/cardinality/disjointness tests;
2. deterministic ordering/restart tests;
3. negative API/schema tests proving candidate result/evidence cannot enter the ordering owner;
4. correlation/support diagnostic checks showing diagnostics cannot alter an already frozen order;
5. coordinated-rehash restart test: changed M3/order/membership with locally valid component digests must be rejected by aggregate lineage/derivation validation.

Complete stage-local affected regression before P2-E.

---

## Pass P2-E — pure target-size experiment definition and reducer

Implement the target-size study state machine/evidence model without executing training.

### E1. Pre-execution statistical definition

The P2 definition must represent and bind:

- dataset/P1 population identity;
- resolved target-size scientific policy;
- exact `P_train/M3` split identity;
- exact `pi_train/pi_eval` identities;
- exact derived `T_N` identities;
- exact derived `M1/M2/M3` identities;
- configured `n1/n2/n3` boundaries;
- the ordered optimizer-seed replicate set;
- funnel transition policy `q -> min(q,4) -> 2 -> 1`;
- target-force ranking/practical-equivalence policy;
- typed terminal/nonterminal reducer states.

It must contain no label-domain maps, CV plan/fold state, complement roles, per-domain prefix digests, DATA7 materialization state, or current-runtime receipt state.

### E2. Explicit P2 -> P3 execution-context boundary

P2 defines the statistical experiment before common preparation exists. Do **not** move common E0/normalization/objective/foundation/replay/training-protocol preparation into P2.

However, real training/evaluation evidence must not be admissible solely because it matches P2 memberships. Before real evidence can advance authoritative reducer state, P3 must supply/bind one execution-context identity covering the common preparation and target-size training scientific context required by the parent plan, including as applicable common preparation/training protocol/foundation/replay identity.

Frozen rule:

```text
P2 statistical definition
+ P3 execution_context_digest
+ exact boundary evidence
  -> authoritative reducer transition
```

A changed common preparation/training scientific context invalidates target-size execution evidence/terminal selection even when the P2 population/orders are unchanged.

P2 reducer unit tests may use an explicit deterministic synthetic execution-context digest, but production/current-generation real evidence must descend from the actual P3 owner. Do not create a default/empty context that allows unbound real evidence.

### E3. Reducer semantics

The reducer must represent:

- complete ordered seed evidence for every candidate at a boundary;
- arithmetic-mean paired aggregation under current policy;
- practical-equivalence comparison where the smaller N wins within the accepted equivalence band;
- eliminated candidates receiving no later ordinary boundary work;
- typed `nonconverged_at_configured_ceiling` when the largest configured N remains materially superior at the terminal comparison;
- typed insufficient/incomplete/unrankable comparison state when evidence cannot support a legitimate decision;
- immutable selected result only after a valid terminal comparison:

```text
N_selected
T_selected = pi_train[:N_selected]
```

Missing, duplicate, reordered, or candidate-specific optimizer-seed populations are incomplete/unrankable; they are not silently reordered, padded, averaged over a subset, or treated as equivalent evidence.

Only the authorized target-size target-force metric and practical-equivalence policy may rank/tie-break N. Replay, CV, physical/deployment, provenance diagnostics, or other secondary evidence cannot select or tie-break target size.

If numerical trajectory failures leave too little comparable evidence for the configured reducer step, return a typed insufficient-comparison/unrankable state rather than silently selecting the only remaining candidate.

Only explicitly authenticated numerical TRAIN2/EVAL2 failures defined by the accepted failure taxonomy may become scientific candidate failure evidence. Ordinary programming, input, lineage, resource, persistence, orchestration, or environment failures remain execution errors and may not be converted into scientific elimination evidence. P3 owns the real TRAIN2/EVAL2 classification boundary; P2 owns only the reducer-side typed contract.

`nonconverged_at_configured_ceiling` is terminal scientific evidence but does **not** fabricate `N_selected/T_selected` or invent an unconfigured rescue size.

### Verification cycle

1. reducer/state-transition unit/property tests with synthetic typed metrics/evidence;
2. paired-seed ordering, aggregation, practical-equivalence, and smaller-N tests;
3. missing/duplicate/reordered/candidate-specific seed-population negatives;
4. typed numerical-failure versus ordinary execution-failure contract tests;
5. ceiling-nonconvergence test proving no selected N is fabricated;
6. insufficient-comparison test proving failure attrition cannot silently select a survivor;
7. tests proving replay/CV/physical/deployment diagnostics cannot rank/tie-break N;
8. immutable terminal `N_selected/T_selected` and exact-prefix reconstruction tests;
9. serialization/restart tests through the real aggregate/deserializer boundary;
10. **evidence-admission tests proving unqualified Revision 3 candidate prefixes cannot advance reducer state;**
11. structural schema assertions for forbidden old fields.

Complete stage-local affected regression before P2-F.

---

## Pass P2-F — aggregate persistence/restart integrity and package closure

P2 persistence must follow the P1A8 standard: local content digests are necessary but insufficient. A current-generation aggregate must prove that all persisted components describe the same deterministic statistical experiment.

### F1. Aggregate restart graph

At the real construction/deserialization boundary, validate enough of the following graph to reject stale/replayed/rehashed state:

```text
accepted P1 authority
  -> inherited P1 split-exclusion relation identity
  -> resolved target-size policy, including hard-support obligations
  -> U_size
  -> P_train/M3 split
  -> pi_train + derived candidate qualification
  -> pi_eval
  -> derived qualified T_N/M_i
  -> target-size experiment definition/reducer state
  -> optional bound P3 execution context for real evidence
```

Required consequences:

- every child binds the exact expected parent identity;
- `U_size` is reproducible from the accepted P1 owners/policy and contains only authorized DEVELOPMENT frames;
- `P_train/M3` reconstruct exactly and satisfy the **complete inherited P1 split-exclusion relation authority**, including unit, duplicate, and additional protected relations;
- `pi_train`/`pi_eval` are exact permutations of their bound populations;
- `T_N` and `M_i` are freshly derivable exact prefixes of the stored/reconstructed orders;
- **candidate qualification is freshly derivable from exact `T_N`, training-label usability, and the bound normalized hard-support obligations;**
- reducer candidates/evidence bind the exact configured **qualified** sizes, ordered seed set, memberships, boundary, and execution context where applicable;
- a changed scientific policy/order/split/**inherited relation authority/hard-obligation authority**/context cannot retain stale downstream reducer/terminal state merely by updating local digest references;
- invalid persisted state is rejected; it is not silently recomputed and substituted while claiming the old aggregate is valid.

Use established P1/P2 owners for re-derivation. Do not duplicate split/order/reducer algorithms inside the deserializer or test harness.

### F2. Mandatory adversarial restart evidence

Use real serializers/deserializers and real semantic owners. At minimum prove rejection of:

1. locally valid P2 object with P1 lineage from a different neutral base;
2. **changed inherited P1 split-exclusion/protected relation authority with stale split/order descendants;**
3. changed/rehashed split with stale `pi_train` or `pi_eval`;
4. changed/rehashed `pi_train` with stale candidate `T_N` identities;
5. changed/rehashed M3/`pi_eval` with stale M-ladder memberships;
6. changed seed/power/fidelity/ranking/**hard-support-obligation** policy with stale qualification/reducer evidence/state;
7. changed execution-context identity with stale real evidence/selected terminal state;
8. forged locally digest-valid selected `T_selected` that is not exactly `pi_train[:N_selected]`;
9. **forged locally digest-valid `qualified=true` for a prefix that fails the current hard-obligation policy;**
10. positive untouched round-trip preserving aggregate scientific identity.

Evidence must cross the real aggregate constructor/from-dict/restart boundary. Helper-only comparison tests cannot establish this claim.

### F3. Integrated package path

Run one bounded integration using the real P1/P2 semantic owners:

```text
accepted P1 canonical frames + neutral statistical base
 -> inherited P1 split-exclusion relation authority
 -> resolved target-size policy + hard-support obligations
 -> U_size
 -> P_train/M3
 -> pi_train + candidate qualification
 -> pi_eval
 -> qualified T_N + M1/M2/M3
 -> pure target-size experiment ready for P3 execution-context binding / first boundary
```

Acceptance requires:

- exactly one target-size study regardless of provenance-group count;
- capacity has no provenance/CV/seed/candidate multiplier;
- all populations/orders/memberships/qualification are exact, deterministic, and restart-authenticated;
- P2 objects are independently serializable/restartable without DATA7/TRAIN2/EVAL2/CV/current-runtime dependencies;
- CV-only changes leave P2 identity unchanged;
- target-size scientific-policy changes invalidate the appropriate P2 descendants;
- default-scale split/order machinery remains resource-feasible and reference-equivalent where optimized;
- complete P2 affected regression and repository-required Python/package/import/static checks pass on the same candidate;
- no current production-runtime switch has occurred;
- no long GPU/full-production qualification is used as a substitute for functional acceptance.

## Implementation authority

### Frozen

Implementation must preserve every material invariant in this package and the parent plan, especially:

- P1-owned `U_size` authorization/protected-role exclusion;
- exact **complete inherited P1 split-exclusion** protection, including unit/correlation, geometry duplicate, and additional P1 protected relations;
- one canonical target-size policy, including explicit normalized hard-support obligations;
- one split, one training order, one evaluation order, one study;
- derived exact prefix memberships and derived hard-obligation qualification;
- optimizer-seed namespace isolation;
- P2 statistical-definition versus P3 execution-context separation;
- semantic restart validation beyond local digests;
- no compatibility-domain/CV/complement/multi-authority target-size topology;
- version-agnostic product naming and fidelity-agnostic funnel schema naming;
- bounded target-scale performance/scaling preservation.

### Delegated

Implementation may choose, while preserving frozen behavior:

- exact version-agnostic class/module names;
- exact canonical serialization shape of inherited P1 relation evidence, provided P1 remains its owner;
- exact declarative hard-support-obligation schema and diagnostics, provided R3.2 semantics and canonical identity are preserved;
- exact deterministic split/order data structures;
- production feasibility algorithm, provided bounded exact/reference equivalence establishes correctness;
- internal reuse/refactoring boundary for old optimized selection kernels;
- exact serialization representation and check ordering;
- exact deterministic diagnostics and error wording;
- test parametrization/fixture organization;
- whether derived memberships/qualification are stored redundantly for convenience, provided aggregate restart always re-derives/verifies them.

### Reopen only on evidence

Reopen only the affected parent/P2 design surface if repository/engine evidence proves one of these material assumptions false:

- P1 DEVELOPMENT-role frames cannot serve as the authorized `U_size` population without violating a frozen parent requirement;
- P1 existing scientific semantics contain a required split-excluding/protected relation that cannot be exposed canonically without changing P1 partition semantics;
- no deterministic serializable hard-support selector over frozen pre-candidate P1/P2 evidence can express an actually required configured obligation;
- no feasible/resource-safe deterministic split can satisfy the parent capacity semantics at expected target scale;
- the optimized training-order semantics cannot be represented as one deterministic order without losing a material required constraint;
- a training-engine quantity that the parent freezes as common preparation is mathematically required to depend on N;
- the accepted evaluation ladder/reducer cannot support the parent scientific decision rule without candidate-dependent evaluation population construction;
- exact restart re-derivation is materially infeasible at expected scale and cannot be made feasible without changing scientific ownership.

Do not reopen merely because legacy V5 APIs/tests prefer domains, complements, fixed candidates, pre-target CV, implicit support heuristics, or the stale `3/6/10` schema name.

## Exit gate

P2 is accepted only when:

> The complete target-size statistical experiment can be deterministically constructed from the accepted P1 scientific substrate, including every inherited P1 split-excluding/protected relation and every explicitly configured hard-support obligation, persisted/restarted with semantic coherence, and reduced under its frozen policy without executing training and without dependency on label domains, CV plans, complement populations, old multi-authority target-size topology, or current runtime state.

Additionally:

- `U_size` is exact P1-authorized DEVELOPMENT configuration membership;
- `P_train/M3` is exactly feasible/disjoint under the **complete inherited P1 split-exclusion relation graph**;
- `pi_train`/`pi_eval` are exact bound permutations;
- all `T_N/M_i` memberships are re-derivable exact prefixes;
- candidate qualification is re-derivable from exact prefixes and the normalized hard-support policy, with diagnostic-only evidence remaining non-gating;
- the ordered optimizer-seed population and reducer policy are authenticated;
- P3 execution context is mandatory before real training/evaluation evidence can become authoritative;
- stale/replayed/rehashed aggregate state cannot counterfeit validity, including after relation-authority or hard-obligation changes;
- the funnel schema identifier is fidelity-agnostic and actual fidelity values remain in resolved policy identity;
- default-scale split/order behavior remains resource-feasible;
- all focused, stage-local affected-regression, integrated P1/P2, restart, and repository-required checks execute successfully.

Commit/tag the accepted P2 checkpoint before P3.