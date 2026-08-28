---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P2
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 2
status: active
package_revision: 2
amended_date: 2026-08-28
entry_p1_commit: 8ccee5a1068f8481df6a3e33ddb5f09f73654391
rework_reason: P1 is frozen. Independent design review found that the original P2 package preserved the parent architecture direction but compressed several now-material handoff constraints: the exact P1-to-U_size projection, correlation/duplicate leakage ownership, canonical resolved target-size policy identity, aggregate restart semantics, the P2 statistical-definition versus P3 execution-context boundary, typed reducer failure semantics, and target-scale/scaling obligations. Revision 2 makes those consequences explicit without changing the frozen parent workplan or moving DATA7/TRAIN2/EVAL2 execution into P2.
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

Any additional P1 relation explicitly designated as split-excluding/protected must likewise be honored. These relations constrain allocation; they do **not** become label/provenance domains and do not multiply the study.

Training support has priority. Subject to exact feasibility and protected disjointness, M3 should preferentially consume redundant residual support while retaining useful representative/condition coverage according to one deterministic split policy.

A production allocator must not declare scientific infeasibility merely because one greedy traversal failed when another valid allocation exists. Keep or construct a bounded exact/reference feasibility oracle suitable for adversarial fixtures; the production path may use a more efficient deterministic algorithm when reference-equivalent.

Persist enough deterministic diagnostic evidence to explain material capacity loss or infeasibility without creating another scientific authority.

### Verification cycle

1. focused P1 -> `U_size` projection tests through real `CanonicalFrameAuthority` + `NeutralStatisticalBase` owners;
2. negative tests proving physical-only/non-authoritative or non-`DEVELOPMENT` P1 frames cannot enter `U_size`;
3. exact allocation/cardinality/disjointness tests;
4. adversarial temporal-unit and exact-geometry-duplicate fixtures proving forbidden train/eval splits cannot occur;
5. fixtures where naive greedy allocation fails but a valid allocation exists, checked against the bounded exact/reference oracle;
6. genuinely impossible correlation allocations fail explicitly and deterministically;
7. deterministic reconstruction/serialization tests;
8. affected P1 neutral-statistical regression sufficient to prove P2 did not reinterpret P1 state.

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
- Required qualification remains intentionally small: the prefix exists, all member labels remain training-usable, and explicitly configured hard support obligations are satisfied.
- Rich coverage/diversity/residual diagnostics are observational/supporting evidence and do not recreate multiple public gate authorities.
- There is one order for the study, not one order per provenance group, compatibility group, CV fold, optimizer seed, or candidate.
- Persisted candidate membership, when serialized for convenience, is derived/checkable state. Restart must recompute/verify it against `pi_train` rather than trust an independently edited membership/digest.

### Scaling/performance requirement

The current-generation owner must retain target-scale feasibility. For representative default-scale input, do not regress into unjustified dense `O(|P_train|^2)` pair/state materialization, repeated full rescans with materially bad scaling, or redundant repeated I/O merely because old optimized kernels are hidden behind a new owner.

Preserve a simple bounded reference/oracle for semantic comparison. Reused optimized sparse/CSR/lazy scoring/repair machinery must remain reference-equivalent on bounded fixtures. Performance acceptance is bounded CPU/RAM/I/O/scaling evidence, not full production qualification.

### Verification cycle

1. exact permutation/prefix/nested-membership tests for all configured N;
2. deterministic tie/order/restart tests;
3. reference/oracle equivalence for reused optimized kernels;
4. representative scaling and peak-RAM checks sufficient to detect dense-quadratic or repeated-rescan regression;
5. structural inspection proving no per-provenance/per-CV/per-seed master-order fanout exists in the current owner.

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
10. structural schema assertions for forbidden old fields.

Complete stage-local affected regression before P2-F.

---

## Pass P2-F — aggregate persistence/restart integrity and package closure

P2 persistence must follow the P1A8 standard: local content digests are necessary but insufficient. A current-generation aggregate must prove that all persisted components describe the same deterministic statistical experiment.

### F1. Aggregate restart graph

At the real construction/deserialization boundary, validate enough of the following graph to reject stale/replayed/rehashed state:

```text
accepted P1 authority
  -> resolved target-size policy
  -> U_size
  -> P_train/M3 split
  -> pi_train/pi_eval
  -> derived T_N/M_i
  -> target-size experiment definition/reducer state
  -> optional bound P3 execution context for real evidence
```

Required consequences:

- every child binds the exact expected parent identity;
- `U_size` is reproducible from the accepted P1 owners/policy and contains only authorized DEVELOPMENT frames;
- `P_train/M3` reconstruct exactly and satisfy the P1 correlation/duplicate constraints;
- `pi_train`/`pi_eval` are exact permutations of their bound populations;
- `T_N` and `M_i` are freshly derivable exact prefixes of the stored/reconstructed orders;
- reducer candidates/evidence bind the exact configured sizes, ordered seed set, memberships, boundary, and execution context where applicable;
- a changed scientific policy/order/split/context cannot retain stale downstream reducer/terminal state merely by updating local digest references;
- invalid persisted state is rejected; it is not silently recomputed and substituted while claiming the old aggregate is valid.

Use established P1/P2 owners for re-derivation. Do not duplicate split/order/reducer algorithms inside the deserializer or test harness.

### F2. Mandatory adversarial restart evidence

Use real serializers/deserializers and real semantic owners. At minimum prove rejection of:

1. locally valid P2 object with P1 lineage from a different neutral base;
2. changed/rehashed split with stale `pi_train` or `pi_eval`;
3. changed/rehashed `pi_train` with stale candidate `T_N` identities;
4. changed/rehashed M3/`pi_eval` with stale M-ladder memberships;
5. changed seed/power/fidelity/ranking policy with stale reducer evidence/state;
6. changed execution-context identity with stale real evidence/selected terminal state;
7. forged locally digest-valid selected `T_selected` that is not exactly `pi_train[:N_selected]`;
8. positive untouched round-trip preserving aggregate scientific identity.

Evidence must cross the real aggregate constructor/from-dict/restart boundary. Helper-only comparison tests cannot establish this claim.

### F3. Integrated package path

Run one bounded integration using the real P1/P2 semantic owners:

```text
accepted P1 canonical frames + neutral statistical base
 -> resolved target-size policy
 -> U_size
 -> P_train/M3
 -> pi_train/pi_eval
 -> T_N + M1/M2/M3
 -> pure target-size experiment ready for P3 execution-context binding / first boundary
```

Acceptance requires:

- exactly one target-size study regardless of provenance-group count;
- capacity has no provenance/CV/seed/candidate multiplier;
- all populations/orders/memberships are exact, deterministic, and restart-authenticated;
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
- exact P1 correlation/duplicate split protection;
- one canonical target-size policy;
- one split, one training order, one evaluation order, one study;
- derived exact prefix memberships;
- optimizer-seed namespace isolation;
- P2 statistical-definition versus P3 execution-context separation;
- semantic restart validation beyond local digests;
- no compatibility-domain/CV/complement/multi-authority target-size topology;
- version-agnostic product naming;
- bounded target-scale performance/scaling preservation.

### Delegated

Implementation may choose, while preserving frozen behavior:

- exact version-agnostic class/module names;
- exact deterministic split/order data structures;
- production feasibility algorithm, provided bounded exact/reference equivalence establishes correctness;
- internal reuse/refactoring boundary for old optimized selection kernels;
- exact serialization representation and check ordering;
- exact deterministic diagnostics and error wording;
- test parametrization/fixture organization;
- whether derived memberships are stored redundantly for convenience, provided aggregate restart always re-derives/verifies them.

### Reopen only on evidence

Reopen only the affected parent/P2 design surface if repository/engine evidence proves one of these material assumptions false:

- P1 DEVELOPMENT-role frames cannot serve as the authorized `U_size` population without violating a frozen parent requirement;
- P1 unit/duplicate evidence is insufficient to express a materially required leakage constraint;
- no feasible/resource-safe deterministic split can satisfy the parent capacity semantics at expected target scale;
- the optimized training-order semantics cannot be represented as one deterministic order without losing a material required constraint;
- a training-engine quantity that the parent freezes as common preparation is mathematically required to depend on N;
- the accepted evaluation ladder/reducer cannot support the parent scientific decision rule without candidate-dependent evaluation population construction;
- exact restart re-derivation is materially infeasible at expected scale and cannot be made feasible without changing scientific ownership.

Do not reopen merely because legacy V5 APIs/tests prefer domains, complements, fixed candidates, or pre-target CV.

## Exit gate

P2 is accepted only when:

> The complete target-size statistical experiment can be deterministically constructed from the accepted P1 scientific substrate, persisted/restarted with semantic coherence, and reduced under its frozen policy without executing training and without dependency on label domains, CV plans, complement populations, old multi-authority target-size topology, or current runtime state.

Additionally:

- `U_size` is exact P1-authorized DEVELOPMENT configuration membership;
- `P_train/M3` is exactly feasible/disjoint under actual P1 correlation/duplicate constraints;
- `pi_train`/`pi_eval` are exact bound permutations;
- all `T_N/M_i` memberships are re-derivable exact prefixes;
- the ordered optimizer-seed population and reducer policy are authenticated;
- P3 execution context is mandatory before real training/evaluation evidence can become authoritative;
- stale/replayed/rehashed aggregate state cannot counterfeit validity;
- default-scale split/order behavior remains resource-feasible;
- all focused, stage-local affected-regression, integrated P1/P2, restart, and repository-required checks execute successfully.

Commit/tag the accepted P2 checkpoint before P3.