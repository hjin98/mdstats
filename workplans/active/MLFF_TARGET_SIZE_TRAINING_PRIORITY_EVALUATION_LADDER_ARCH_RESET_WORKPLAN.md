---
kind: implementation-workplan
workplan_id: CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V4
protocol_version: 5.8.0
status: active
created_date: 2026-08-28
review_revision: 4
architecture_change: major
compatibility_policy: destructive-generation-reset
supersedes:
  - CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V1
  - CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V2
  - CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V3
  - all previously active target-size amendments and MLFF closeout workplans retired on 2026-08-28
---

# MLFF Target-Size Training-Priority Evaluation-Ladder Architecture Reset — Final Consolidated Workplan

## 0. Purpose and frozen outcome

Rebuild target-size selection as one clean current-generation workflow with exactly one target-size study and no second target-size “domain” axis.

The final architecture has:

- one qualified target-size study population `U_size`;
- one correlation-safe target-training authorized pool `P_train`;
- one correlation-safe target-size-evaluation authorized pool `P_eval`;
- one rich repaired target-training master order `pi_train`;
- one frozen representative evaluation master order `pi_eval`;
- one nested evaluation ladder `M1 subset M2 subset M3`;
- one target-size evidence stream and reducer;
- one selected cardinality `N_selected`;
- one exact selected target dataset `T_selected`;
- cross-validation only after `N_selected` and `T_selected` freeze;
- fresh final production only after post-selection CV accepts the frozen training protocol.

Target-size code must not replicate any of these objects per `LabelDomain`, per electronic-structure source, or per internal metric block. Upstream label compatibility remains a data-ingest/preflight safety mechanism only. If current target inputs require genuinely incompatible training heads or scientific label conventions, this workflow fails with an explicit unsupported-topology outcome rather than silently creating multiple target-size studies.

Priority remains:

```text
scientific/product correctness
  > clean single-authority architecture
  > material performance/resource efficiency
  > development convenience / obsolete-state compatibility
```

## 1. Final review corrections incorporated

This revision closes the remaining issues found after the V2/V3 reviews and current-code inspection.

1. **No target-size domain dimension.** Current `TargetSizeStudyCandidate.domain_prefix_digests`-style state is retired. One candidate size owns one candidate-data identity.
2. **`Nmax + M3` is the target-size capacity lower bound.** It is config-derived, not fixed, and is not multiplied by CV folds, label domains, seeds, candidates, or cumulative inference work.
3. **Role pools are not exact configured sets.** Correlation/equivalence groups may contain multiple frames, so `P_train` and `P_eval` can be larger than `Nmax` and `M3`. Exact cardinalities are materialized later as prefixes of `pi_train`/`pi_eval`.
4. **Surplus data need not be forced into a role.** Qualified data not needed for either authorized pool may remain `U_unused`/reference-only.
5. **Training-priority support must survive exact materialization.** The allocation owner publishes protected train-support obligations for unique/scarce support. Rich selection/REPAIR2/MVQUAL must honor those obligations in exact candidate prefixes where feasible; merely placing a rare group somewhere in an oversized `P_train` is insufficient.
6. **Evaluation support must survive `M3` materialization.** The allocation/evaluation authorities publish representative residual-support goals; `pi_eval[:m3]` must satisfy them where feasible, with explicit diagnostics for unrepresentable strata.
7. **Evaluation order freezes before candidate TRAIN2.** Candidate predictions, survivor decisions, or selected-size outcomes cannot alter `pi_eval` or `M_i`.
8. **CV is post-selection only.** It validates the already-selected training data/protocol; it is not a target-size materializability, MVQUAL, or ranking input.
9. **CV is correlation-group safe.** Selected frames from one indivisible correlation/equivalence family stay together in one CV role/fold.
10. **CV is validation-only.** It may block production but may not tune a material training policy and keep old target-size evidence. A material training-policy change requires new target-size evidence.
11. **CV identity is downstream-only.** CV fold/seed/monitor/purge changes invalidate CV descendants only, never the already-frozen target-size study.
12. **CV precedes final full-data production.** `N_selected/T_selected` freeze -> CV -> accepted protocol -> fresh final production.
13. **Replay semantics remain explicit.** Replay may remain a hard checkpoint/model admissibility constraint where the accepted current protocol requires it, but target-size ranking/order remains target-side only; replay score is not a target-size ranking signal.
14. **Accepted lifecycle/resource improvements survive plan retirement.** Exact boundary continuation, one shared TRAIN2 lifecycle, one-owner OPT-EVAL4 staged resource admission, DATA7/DATA8 provenance, and documentation build obligations are folded into this plan.
15. **Sampling-policy qualification is separate.** Missing representative evidence means `deferred/unavailable`, never an invented pass.

## 2. Authoritative lifecycle

```text
source / DATA4 upstream evidence / events
 -> DATA5 outer-role + correlation/equivalence authority
 -> single-target-study compatibility/preflight
 -> qualified target-size population U_size
 -> correlation-safe target-size role allocation
      -> P_train
      -> P_eval
      -> optional U_unused/reference-only remainder
 -> split-safe protected train/eval support obligations
 -> rich target-training preparation/selection inside P_train
      -> FEAS1 -> MVIDX1 -> MVSEL2 -> REPAIR2/MVSTATE2 -> MVQUAL
      -> pi_train
      -> exact T_N = pi_train[:N]
 -> representative evaluation ordering inside P_eval
      -> pi_eval frozen before candidate TRAIN2
      -> M1 subset M2 subset M3
 -> exact target-size screen
      -> (n1,M1) -> (n2,M2) -> (n3,M3)
 -> freeze N_selected and T_selected = pi_train[:N_selected]
 -> construct correlation-group-safe CV from T_selected
 -> CV validation of the frozen training protocol
 -> fresh final production on full T_selected
      -> M3 may serve final-development checkpoint/model selection
 -> outer/held-out validation -> calibration -> locked tests
```

No downstream CV, production, held-out, calibration, or locked evidence may feed back into target-size population allocation, training membership, evaluation membership, survivor ranking, or `N_selected`.

## 3. One target-size study; upstream compatibility only

### 3.1 One current target-size topology

The target-size subsystem owns one `U_size`, one `P_train`, one `P_eval`, one `pi_train`, one `pi_eval`, one `M1/M2/M3`, one reducer, and one selected target dataset.

Remove current target-size schema/runtime concepts whose sole purpose is a second study dimension, including as applicable:

- `domain_prefix_digests` on target-size candidates;
- per-domain target candidate materialization;
- per-domain target-size ladders;
- per-domain M1/M2/M3 populations;
- per-domain target-size reducers or weighted target-size aggregation;
- automatic `D * (...)` target-size capacity/work calculations;
- one target-size study instantiated for every upstream `LabelDomain`.

Internal EVAL2 force reductions by condition/block/species are metric internals and may remain. They do not create target-size domains.

### 3.2 Label compatibility preflight

`LabelDomain` or its clean successor may continue to partition source data by theory identity, energy reference, derivative convention, numerical-quality policy, or software provenance.

Before target-size work, preparation must resolve the target training inputs to one scientifically compatible target study/head. If that cannot be done without multiple incompatible target-training protocols, preflight returns a typed unsupported/incompatible topology result. The target-size subsystem must not solve that by multiplying studies.

## 4. Canonical configurable target/evaluation ladders

Canonical user configuration:

```toml
[target_data.size_convergence]
target_size_power_min = 7
target_size_power_max = 14
evaluation_size_powers = [8, 9, 10]
fidelity_epochs = [1, 3, 10]
```

One canonical resolver derives:

```text
candidate_target_sizes = [2^p for p in pmin..pmax]
Nmax = 2^pmax
evaluation_sizes = [2^q for q in evaluation_size_powers]
(n1,m1), (n2,m2), (n3,m3)
```

Validation:

- powers are nonnegative integers;
- `pmin < pmax` and the current funnel has at least three configured target candidates;
- evaluation powers contain exactly three strictly increasing integers;
- fidelity boundaries contain exactly three strictly increasing positive integers;
- derived cardinalities fit owning index/count/serialization types;
- no scientific `<=16384` guard remains;
- no non-power-of-two rescue size is generated;
- resolved canonical config persists both powers and readable derived sizes;
- semantically relevant scientific values participate in target-size policy identity;
- destructive reset means old fixed/flexible aliases are not silently normalized into materially new semantics.

Defaults yield target sizes `128..16384` and evaluation sizes `[256,512,1024]`.

Configured ceiling replaces fixed ceiling. If the largest configured candidate remains materially superior under the final practical-equivalence rule, return `nonconverged_at_configured_ceiling`; never invent a larger/intermediate rescue size.

## 5. Capacity rule and correlation-safe role allocation

### 5.1 Nominal target-size capacity

Because `M1` and `M2` are prefixes of `M3`, the target-size-stage nominal qualified configuration lower bound is:

```text
|U_size| >= Nmax + m3
```

Default example only:

```text
Nmax = 16384
m3   = 1024
nominal lower bound = 17408 qualified configurations
```

This is not a fixed 17,408 requirement, not an IID sample count, and not a training-only count. It is derived from the configured largest training candidate plus the largest disjoint target-size evaluation set.

The real source requirement may be larger because outer-role exclusions, protected events, whole correlation/equivalence groups, lineage constraints, or other leakage policy may make a nominal frame count infeasible. Preflight must perform real group-aware feasibility.

### 5.2 Allocation groups

An allocation group is the smallest connected component that current leakage/correlation policy forbids from being split between target training and target-size evaluation.

At minimum close over applicable current relations for:

- DATA5 correlation/partition units;
- exact/near-duplicate geometry families;
- explicit correlation/active-learning families;
- protected event-window linkage;
- source/lineage relations whose policy forbids incompatible-role splitting.

Each group receives exactly one target-size role:

```text
train_authorized | evaluation_authorized | unused_reference
```

This prevents train/evaluation correlation leakage. It does not claim frames inside a group are IID.

### 5.3 Authorized pools and exact materialized sets

```text
P_train = configurations in train-authorized groups
P_eval  = configurations in evaluation-authorized groups

P_train ∩ P_eval = empty
|P_train| >= Nmax
|P_eval|  >= m3
```

Pools may exceed the exact cardinalities because groups are indivisible.

Exact scientific sets are later materialized as:

```text
T_max = pi_train[:Nmax]
M1 = pi_eval[:m1]
M2 = pi_eval[:m2]
M3 = pi_eval[:m3]
```

Thus exact configured counts and group-safe role separation coexist without rounding or group splitting.

### 5.4 Split-safe allocation evidence

Role allocation runs before fitted target preparation. Allocation inputs are restricted to a versioned split-safe evidence contract, such as partition-independent:

- geometry/structural descriptors;
- composition/cell/condition/regime/temperature/strain identities;
- predeclared event classes/protected windows;
- source/run/replica/provenance/correlation identities;
- other explicitly documented upstream structural/categorical evidence.

Allocation ranking may not use:

- target-size candidate predictions/errors;
- EVAL2 outcomes or survivors;
- role-local DATA6/DATA7 fitted transforms;
- training-role-dependent foundation residual/difficulty;
- role-local E0/normalization fits;
- CV/calibration/locked/final-production evidence.

A predeclared upstream event class may be used categorically when its detector is frozen before allocation. Candidate-dependent hard-example mining is forbidden.

### 5.5 Training-priority allocation objective

Required ordering of concerns:

1. protect unique/scarce split-safe support for training;
2. ensure a train-authorized pool can materialize exact `Nmax` with required important support;
3. preserve enough disjoint residual capacity to materialize `M3` whenever the qualified population makes that feasible;
4. choose evaluation-authorized groups preferentially from redundant/correlation-distinct residual support;
5. preserve representative residual support for evaluation where multiple alternatives exist;
6. use deterministic stable tie-breaking;
7. leave unnecessary surplus as unused/reference-only rather than over-allocating either role.

Evaluation never steals uniquely required training support merely to appear complete. Optional training allocation also may not exhaust all redundant residual support if a scientifically representative `M3` can otherwise be preserved.

If no group-safe allocation satisfies `Nmax` and `m3`, preflight fails clearly. Do not lower configured sizes, split prohibited groups, or fall back to complement evaluation.

### 5.6 Protected support handoff into exact selectors

The allocation authority must publish two explicit downstream contracts:

**Training protected-support obligations.** Unique/scarce split-safe support that motivated assignment to `P_train` is represented as must-cover obligations consumable by the rich training selection/repair/qualification chain. `T_max` must contain the required representative(s) where mathematically feasible. For smaller `T_N`, the existing qualification mechanism determines whether the obligations can be satisfied; a rung that cannot satisfy required hard support is unqualified rather than silently dropping the obligation.

**Evaluation representative-support goals.** Important residual support preserved in `P_eval` is passed to `pi_eval` as representative coverage goals. `M3` must include representative support where feasible. Missing/unrepresentable residual strata are explicit diagnostics/qualification evidence; they do not trigger post-freeze role stealing.

This handoff prevents an oversized authorized pool from “containing” protected support that the exact materialized dataset later omits.

After role freeze, FEAS/MVQUAL/TRAIN2/EVAL2 outcomes cannot reassign groups.

## 6. Rich target-training master order

Only `P_train` enters fitted target-training selection.

Preserve/refactor the rich chain:

```text
P_train
 -> role-local fitted selection inputs
 -> FEAS1
 -> MVIDX1
 -> MVSEL2
 -> REPAIR2 / MVSTATE2
 -> MVQUAL
 -> pi_train
```

Required semantics:

- one repaired master order only;
- each configured target size is one exact prefix `T_N = pi_train[:N]`;
- `T_max` contains exactly `Nmax` configurations;
- one candidate-data identity per target size, not a domain map;
- allocation-protected training obligations are included in hard coverage/repair/qualification where applicable;
- target-label/foundation-residual weakness families, hard coverage, representative utility/diversity, repair, and independent MVQUAL remain scientifically authoritative unless a bounded design reopen proves a specific predicate obsolete;
- no independent per-rung re-selection/repair;
- no `P_eval`/unused frame enters any target candidate;
- rich failure after role freeze fails closed rather than stealing evaluation data;
- no hidden eight-rung loop/static current universe remains.

## 7. Frozen representative evaluation ladder

Build one deterministic `pi_eval` over `P_eval` after role allocation freezes and before the first candidate TRAIN2 trajectory.

After role freeze, evaluation ordering may use:

- structural/condition/provenance evidence;
- target-label distribution information;
- residuals from a frozen external/foundation model whose identity is independent of target-size candidate trajectories.

It may not use:

- candidate predictions/errors;
- survivor/ranking/selected-size outcomes;
- final-production predictions;
- CV/calibration/locked evidence.

Evaluation selection is representative model-selection coverage, not training MVQUAL. It does not automatically inherit REPAIR2 or the training hard pass threshold.

Required ladder:

```text
M1 = pi_eval[:m1]
M2 = pi_eval[:m2]
M3 = pi_eval[:m3]
M1 subset M2 subset M3 subset P_eval
```

`M3` must satisfy preserved representative residual-support goals where feasible. M1/M2 are progressive prefixes and need not contain every M3 support goal.

Persist correlation/effective-sample/support diagnostics so configuration count is never mislabeled as independent-sample count.

`P_eval \ M3` and suitable unused/reference-only groups may be used for retrospective scientific qualification when available. They are not runtime fallback evaluation populations.

## 8. Exact target-size screening

Stage pairs are exactly:

```text
(n1,M1)
(n2,M2)
(n3,M3)
```

Preserve the current intended funnel:

```text
q qualified sizes
 -> coarse: all q at n1
 -> short: min(q,4) survivors at n2
 -> final: 2 finalists at n3
 -> select 1
```

with the accepted minimum qualified-size threshold, paired optimizer seeds, and practical-equivalence/smaller-size preference.

### 8.1 Exact continuation is a first-class training mode

Carry the nonconflicting exact-boundary design from retired plans:

- `fidelity_epochs` are exact checkpoint boundaries, not generic horizon caps;
- a survivor continues from its exact prior boundary checkpoint;
- no survivor restarts at epoch 0;
- training evidence binds exact start boundary, end boundary, and continuation checkpoint;
- exact boundary checkpoints are persisted/reused;
- ordinary target-success early stopping cannot terminate a screen before the required boundary;
- screen continuation is a first-class policy/mode, not an accidental branch of generic production/adaptive booleans;
- production epoch maximum remains independent of `n3`.

### 8.2 Stage evaluation identity

At one stage every candidate and paired seed uses the same frozen `M_i` identity. Cross-rung metrics are not compared as if M1/M2/M3 were the same population.

No constant cumulative inference count is architecture. Expected/actual work is derived at runtime from resolved candidate count, seed count, survivor count, and `M_i`. Numbers such as 12,288 are neither data-capacity requirements nor fixed workload policy.

### 8.3 Replay remains admissibility-only for target-size ranking

Preserve the accepted target-first model-selection semantics:

- target-side EVAL2 evidence owns target-size ordering/ranking;
- replay may remain a hard admissibility/guardrail check for a checkpoint/model if required by current scientific policy;
- replay score must not become a secondary ranking objective or change the target-side practical-equivalence ordering;
- target-size evaluation populations M1/M2/M3 contain target-side evaluation data, not replay data;
- any replay admissibility evidence is authenticated separately from M-ladder target evidence.

## 9. EVAL2 / OPT-EVAL4 ownership and resources

Target-size roles resolve directly:

```text
coarse       -> M1
short        -> M2
final_screen -> M3
```

Retire current target-size semantics based on:

- `size_development_complement`;
- `size_development_coarse`;
- maximum-training-prefix subtraction;
- full-complement fallback;
- legacy target-size temporal/block sampling used only by retired generations;
- per-domain target-size aggregation introduced solely to support multiple target studies.

Preserve the canonical EVAL2 target-force estimator and accepted one-owner staged execution:

```text
parent/staged owner
 -> CPU prepare
 -> accelerator inference
 -> CPU finalize
 -> parent commit
```

The outer staged operator owns aggregate resource admission/lifetime. Nested inference must not obtain a second aggregate RAM lease or double-charge fixed admission overhead. Preserve bounded buffers, batching, cache/mmap, accelerator admission and concurrency machinery unless direct evidence requires repair.

## 10. Freeze selected target dataset

When the reducer returns `selected(N)`:

```text
N_selected = N
T_selected = pi_train[:N]
```

Both are immutable target-size outputs.

`T_selected` is the exact target dataset whose cardinality was selected. CV/final production must not enlarge it with `P_train \ T_selected`, `P_eval`, or unused/reference-only data.

The selected-data authority binds:

- target-size policy/current generation;
- role-allocation identity;
- `pi_train`/candidate-data identity;
- `pi_eval`/M-ladder identity;
- paired-seed/exact-continuation ancestry;
- `N_selected`;
- exact ordered `T_selected` membership digest.

## 11. Post-selection correlation-safe CV

### 11.1 Construction timing

CV is created only after selected-data freeze. Remove any current-generation invariant that makes pre-selection CV part of size-development role freeze, target-size materializability, FEAS/MVQUAL, or target-size ranking.

### 11.2 CV consumes only `T_selected`

CV partitions the selected configurations using the correlation/equivalence identity inherited from upstream DATA5/target allocation.

All selected frames from one indivisible CV correlation/equivalence group stay together in the same CV role/fold. Frame-level balancing cannot split a prohibited group.

Fold sizes may be uneven. Fold training sets are naturally smaller than `N_selected`.

If selected data contain too few correlation-distinct groups for the requested CV topology/monitor/purge policy, CV fails after selection. It does not:

- change `N_selected`;
- select another target-size rung;
- add `P_train` surplus or M3 to gradients;
- rerun target allocation silently;
- weaken correlation/purge requirements.

The user/campaign may explicitly change CV-only policy or provide/reselect data through an appropriate new run/design boundary.

### 11.3 CV is validation, not tuning

Material training/model hyperparameters used by candidate screening are part of target-size scientific identity and freeze before screening.

CV validates that already-frozen protocol on `T_selected`. If CV indicates that a material training scientific policy must change, the changed policy gets a new identity and the old target-size evidence is no longer authoritative for that new protocol.

CV may block production. It never retroactively optimizes `N_selected`.

### 11.4 Dependency direction

Target-size identity excludes CV-only configuration such as fold count, fold seed, monitor assignment, purge policy, and execution-only CV worker/batch values.

Changing CV-only policy invalidates CV evidence/descendants only; `N_selected` and target-size evidence remain intact.

Changing a material screening/training scientific policy invalidates target-size evidence and therefore selected/CV/production descendants.

## 12. Fresh final production after CV

Only after CV accepts the frozen selected protocol does final production begin.

Final production:

- starts fresh from the accepted initialization/foundation model, not a screening checkpoint;
- trains on the full exact `T_selected`;
- uses its own configured production epoch maximum/adaptive production policy;
- uses the shared canonical training lifecycle/entry point;
- binds selected-data/current-generation provenance.

M3 may be reused for final-development target checkpoint/model selection because it is already development/model-selection evidence. It stays non-gradient and frozen.

Replay may continue as a hard checkpoint admissibility constraint where required, but target-side M3 evidence owns model ordering under the accepted target-first policy.

CV uses its fold-local evidence; outer/held-out validation, uncertainty calibration, and locked tests remain independent. M3 must never be advertised as held-out validation after influencing size or final checkpoint choice.

If a separate common target online monitor has no distinct non-selection responsibility after M3 consolidation, remove/merge it rather than retain duplicate checkpoint authorities.

## 13. Shared training lifecycle and provenance

Carry the valid lifecycle obligations from the retired MLCV plan:

- one canonical shared training entry point owns target-size screening, CV training, and final production;
- conceptual lifecycle: `preflight -> resource acquisition -> prepared execution -> checkpoint publication -> release`;
- no CLI/private/direct-entry bypass creates a second scientific lifecycle owner;
- nested training functions do not independently acquire/release aggregate resources outside the shared owner;
- checkpoints/evidence bind authoritative target/replay data identities, preparation identity, training policy and current generation;
- CV provenance descends from `T_selected`;
- final production provenance descends from `T_selected` and required CV acceptance where campaign policy requires CV passage.

## 14. Persistence, restart and dependency-directed identity

This is a new semantic generation. Old derived target-size state is unsupported and is not migrated.

### Target-size identity includes

- one `U_size` qualified-population identity;
- target/evaluation powers and fidelity boundaries;
- screening seed/aggregation/practical-equivalence policy;
- correlation/equivalence/allocation-group policy;
- split-safe feature contract and role-allocation policy;
- protected train/eval support obligations;
- `P_train/P_eval` role identity;
- rich training selector/repair/MVQUAL policy;
- frozen evaluation-order feature/policy/foundation identity;
- target-first/replay-admissibility policy;
- material candidate-training scientific policy.

### Selected-data identity adds

- terminal target-size evidence ancestry;
- `N_selected`;
- exact `T_selected` ordered membership digest.

### CV identity adds downstream only

- selected-data identity;
- CV fold/seed/monitor/purge policy;
- exact CV group/fold memberships.

### Production identity adds

- selected-data identity;
- required CV acceptance identity;
- production budget/adaptive policy;
- final checkpoint-selection/admissibility policy.

Execution-only worker/chunk/cache/batch/RAM/VRAM scheduling values must not alter scientific identity when they do not alter mathematics.

Restart acceptance:

- identical scientific config/input -> identical role allocation/orders/ladder/digests;
- target-size policy change -> target-size and all descendants invalidate;
- CV-only change -> target-size/selected data stay valid, CV descendants invalidate;
- production-only budget change -> target-size/CV stay valid, production descendants invalidate as appropriate;
- restart at each screen boundary uses exact authenticated continuation checkpoint and `M_i`;
- no restart rebuilds `pi_eval` from candidate outcomes;
- pre-reset fixed/complement/domain-prefix state fails with actionable unsupported-generation error rather than migration.

Raw/external source inputs remain reusable.

## 15. Current-generation cleanup contract

Delete/retire from reachable current execution as applicable:

- `FIXED_TARGET_SIZES` / `FIXED_TARGET_SIZE_CEILING` scientific authority;
- executable `<=16384` scientific guards;
- fixed-universe/current fixed-ceiling error/terminal language;
- legacy candidate-authority migration/bridge/receipt code used only for superseded generations;
- target-size `domain_prefix_digests` and per-domain candidate/evaluation authority;
- per-domain target-size reducers/automatic multipliers;
- `size_development` as an equally authoritative target-size role where replaced;
- `size_development_complement` / `size_development_coarse` target-size roles;
- pre-selection CV coupling into target-size role freeze/materializability/MVQUAL;
- complement/fallback target evaluators;
- obsolete fixed/flexible/TARGET-SIZE-V5 aliases that denote retired semantics;
- duplicate training lifecycle/resource owners;
- duplicate final-development target checkpoint selectors after M3 consolidation;
- tests that exist only to preserve retired behavior.

Historical docs/evidence may remain historical and non-executable.

## 16. Retired workplan consolidation

`workplans/active/` must contain only:

- this consolidated workplan;
- `README.md` pointing to it.

All previously active MLFF workplans/amendments are archived under `workplans/archive/retired-2026-08-28/` and are historical records only.

The following still-valid obligations have been folded into this plan before retirement:

- exact n1/n2/n3 checkpoint-boundary continuation;
- no ordinary success early stop during target-size screen;
- fresh selected-size production with independent production epoch budget;
- first-class target-size continuation mode;
- one shared training lifecycle/provenance owner;
- one-owner OPT-EVAL4 staged RAM/resource admission;
- current DATA7/DATA8 artifact/provenance reconciliation;
- documentation build/lint/reference/PDF verification required by repository policy.

Archived plans do not independently impose active gates.

## 17. Part 1 — documentation and specification reset

Part 1 executes first on the implementation branch. Future-state normative docs must not be merged/released alone while the shipped executable still implements the retired architecture.

### D1. Architecture/manual rewrite

At minimum reconcile:

- `docs/arch_manuals/mlff_training_data/30_statistical_design.md`;
- `docs/arch_manuals/mlff_training_data/40_training_evaluation.md`;
- `docs/arch_manuals/mlff_training_data/50_target_multiview.md`;
- `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`;
- `docs/arch_manuals/mlff_training_data_architecture.md`;
- current dependency graphs/source maps/generated architecture inputs.

Required lifecycle diagram:

```text
U_size
 -> correlation-safe P_train/P_eval (+ optional unused)
 -> protected support obligations
 -> one pi_train / exact T_N
 -> one frozen pi_eval / M1/M2/M3
 -> select N_selected/T_selected
 -> post-selection group-safe validation-only CV
 -> fresh final production
 -> held-out/calibration/locked stages
```

No target-size domain fan-out.

### D2. Normative specs/configuration

Update current specs for:

- target-size policy and configured powers;
- DATA5 correlation/equivalence consumption by target study;
- target role-allocation/protected-support authority;
- FEAS/MVIDX/MVSEL2/REPAIR2/MVQUAL exact membership authority;
- EVAL2 M-ladder population/admissibility semantics;
- OPT-EVAL4 population identity while preserving execution ownership;
- post-selection CV construction/lifecycle;
- final checkpoint/model selection and replay admissibility;
- campaign/configuration/current generation;
- persistence/restart;
- DATA7/DATA8 selected/candidate artifact provenance.

### D3. Terminology cleanup

Remove/rewrite current normative/user statements implying:

- fixed target-size universe or fixed ceiling;
- scientific hard-coded 16384 except as default `2^14` example;
- target-size per-domain prefixes/M ladders/reducers;
- `D * ...` target-size capacity/workload;
- pre-selection CV target-size authority;
- full/coarse complement target-size evaluation;
- arbitrary percentage train/evaluation split;
- obsolete migration/compatibility promises;
- IID claims unsupported by actual correlation evidence;
- stale fixed/flexible/TARGET-SIZE-V5 current-generation semantics;
- alternate current selector/lifecycle/checkpoint authorities.

### D4. Part 1 acceptance

Part 1 closes only when:

1. all current docs/specs describe one target-size study;
2. nominal capacity is `Nmax + M3` and clearly identified as config-derived/group-aware lower bound;
3. authorized pools versus exact materialized sets are unambiguous;
4. protected training/evaluation support handoff into exact selectors is explicit;
5. CV is post-selection, group-safe and validation-only;
6. replay is admissibility-only for target-size/final target ordering;
7. fresh final production follows accepted CV where CV is required;
8. generation/config/restart dependency direction agrees;
9. active workplans contain only this plan + README;
10. repository-required docs build/lint/reference/PDF checks pass.

## 18. Part 2 — gated implementation

Every material executable gate requires focused checks plus stage-local affected regression before dependent work proceeds.

### C1. Single-study generation + canonical configuration

Implement:

- new semantic generation/schema identities;
- canonical exponent resolver/configured ceiling;
- one target-size study compatibility/preflight;
- removal of target-size domain-prefix candidate topology;
- typed unsupported multi-target-study topology.

Focused acceptance:

- default/nondefault powers/boundaries;
- at least three target candidates;
- no hidden 16384 ceiling;
- one target-size study identity;
- incompatible target-head topology fails explicitly;
- no current `domain_prefix_digests` target-size schema;
- deterministic serialization/digests.

Stage-local regression: configuration, label compatibility/preflight, target-size policy/state serialization, exports.

### C2. Correlation-safe role pools + protected obligations

Implement allocation-group closure, split-safe allocation, `P_train/P_eval/U_unused`, group-aware capacity and protected support records.

Focused acceptance:

- nominal `Nmax + m3` arithmetic rule;
- real group-aware failure despite nominal count where safe split is impossible;
- unique/scarce training support assigned to `P_train`;
- protected training obligations emitted;
- representative residual support retained when feasible;
- evaluation support goals emitted;
- P_train/P_eval group disjointness;
- pools may exceed exact configured counts;
- surplus may remain unused;
- no role mutation after freeze.

Stage-local regression: DATA5/leakage/target roles/preflight/state identity.

### C3. One rich training order + one frozen evaluation ladder

Route fitted training preparation through P_train and evaluation ordering through P_eval.

Focused acceptance:

- one `pi_train` only;
- exact `T_max == Nmax`;
- exact/nested configured training prefixes;
- protected train obligations represented in qualified prefixes where feasible;
- no eval/unused UID in target candidates;
- one `pi_eval` only;
- exact/nested M1/M2/M3;
- M3 representative support goals satisfied where feasible;
- deficits explicit when unrepresentable;
- candidate predictions unavailable/forbidden to `pi_eval` construction;
- correlation/effective-sample diagnostics;
- rich/eval failure cannot mutate role pools.

Stage-local regression: DATA6/7/8, coverage/index/selector/repair/MVQUAL/evaluation materialization.

### C4. Exact-boundary TRAIN2 + EVAL2 orchestration

Exercise the real owner path:

```text
resolved config/current generation
 -> one U_size preflight
 -> P_train/P_eval allocation + obligations
 -> pi_train/pi_eval + M ladder
 -> candidate materialization
 -> TRAIN2 exact continuation
 -> exact boundary checkpoint publication
 -> EVAL2 target M_i + replay admissibility
 -> OPT-EVAL4 staged execution
 -> target-side reducer/survivor authorization
 -> selected/configured-ceiling terminal state
 -> exact T_selected freeze
```

Only expensive MACE stepping/inference may be bounded/faked below these owners. Tests proving orchestration must not patch/reimplement allocation, ladder resolution, continuation, reducer, or selected-data transition.

Required cases:

- default/nondefault fidelity/evaluation powers;
- changed pmin/pmax;
- exact paired-seed continuation;
- no normal early stop before boundary;
- eliminated candidate receives no later work;
- restart at each boundary preserves checkpoint/M identity;
- replay failure can make a checkpoint inadmissible but cannot reorder target scores;
- configured-ceiling nonconvergence;
- no complement fallback;
- one selected-data digest with no domain map.

Stage-local regression: target-size study, CLI/scheduler, TRAIN2/EVAL2/OPT-EVAL4, persistence/restart, DATA7/8 consumers.

### C5. Post-selection CV + fresh production

Construct CV only from T_selected after selected-data freeze.

Focused acceptance:

- no pre-selection CV authority in new generation;
- one correlation/equivalence group never split across CV roles/folds;
- uneven/smaller fold training sets supported;
- insufficient independent support fails CV without changing N;
- CV cannot use P_eval/M3/unused as gradients;
- CV-only config change preserves target-size/selected identities;
- material training-policy change invalidates target-size evidence;
- CV failure blocks production but cannot optimize N;
- accepted CV leads to fresh full-T_selected production from intended initialization;
- production epoch max independent of n3;
- M3 final checkpoint selection is frozen/non-gradient/target-first;
- replay remains hard admissibility only;
- held-out/calibration/locked evidence stays independent.

Stage-local regression: CV roles/lifecycle, shared training entry, production materialization/checkpoint selection, provenance.

### C6. Resource/lifecycle reconciliation + destructive cleanup

Acceptance:

- exactly one shared training lifecycle/entry owner;
- no duplicate resource acquisition/release path;
- one OPT-EVAL4 aggregate staged resource owner;
- no nested double RAM lease/fixed overhead;
- old fixed/complement/domain-prefix/pre-selection-CV/migration paths structurally absent;
- duplicate checkpoint selector removed where M3 consolidates ownership;
- docs/specs no longer claim retired semantics;
- active workplans remain only this plan + README.

Run deletion/import/package tests plus affected regression after cleanup.

### C7. Final assembled functional acceptance

1. reconcile every frozen obligation against final source/current docs;
2. re-derive the complete affected surface from final diff/dependency graph;
3. run complete affected regression;
4. run real-owner integration from config through selection, CV and final-production entry;
5. run broader/full repository tests where impact cannot be bounded confidently;
6. rebuild/check affected documentation/PDF outputs;
7. perform structural authority-uniqueness and retired-path absence inspection;
8. run deterministic/reference/performance checks for changed allocation/index/selection paths;
9. report functional acceptance, M-ladder scientific qualification and final GPU qualification as separate statuses.

New/plausibly affected failures block functional closure. Proven unrelated pre-existing failures may be attributed only with evidence.

## 19. Scientific qualification

The bounded M ladder is a sampling estimator. Unit/regression tests do not prove it preserves target-size decisions.

Provide a reproducible retrospective/reference qualification path using completed checkpoints/predictions or bounded representative runs when available.

Required claims:

1. M1 does not falsely eliminate an eventual competitive/reference finalist;
2. M2 preserves the reference finalist population;
3. M3 selects the same target size under practical-equivalence/smaller-size rules as a larger authenticated non-gradient reference;
4. representative support/coverage improves where mathematically expected;
5. selected M sets outperform naive temporal/uniform same-cardinality baselines on important declared strata;
6. P_train still permits rich training/MVQUAL after carve-out;
7. protected train obligations appear in exact qualified candidates as required;
8. train/evaluation correlation leakage is clean;
9. deterministic restart/worker/cache changes preserve scientific identity/results;
10. real assembled screening consumes exact M_i at exact n_i;
11. bounded evaluation materially reduces work versus retired full complement under the same candidate policy.

Do not use post-selection CV, locked tests or final held-out evidence to tune M cardinalities.

If `[256,512,1024]` fails decision preservation, revise the configured powers explicitly and requalify under a new policy identity. Never expand M silently at runtime.

If representative qualification evidence is unavailable, report `deferred/unavailable`, not passed.

Full long real-data/GPU performance/resource qualification remains deferred to the established final release/GPU phase.

## 20. Frozen implementation authority

Implementation MUST preserve:

- exactly one target-size study; no target-size domain axis;
- upstream label compatibility as preflight only;
- config-derived `Nmax + M3` nominal capacity with real group-aware feasibility;
- correlation/equivalence-safe authorized pools distinct from exact sets;
- training priority for unique/scarce support;
- protected support handoff into exact training/evaluation selectors;
- one rich training order and exact configured prefixes;
- one nonadaptive evaluation order frozen before candidate TRAIN2;
- exact nested M1/M2/M3 paired to n1/n2/n3;
- exact checkpoint-boundary continuation as first-class screen mode;
- paired seeds and practical-equivalence/smaller-size rule unless separately redesigned;
- target-side ordering with replay admissibility-only semantics;
- no complement fallback;
- one N_selected/T_selected before CV;
- group-safe post-selection CV from T_selected only;
- CV validation-only and downstream-only identity;
- fresh final production after accepted CV where required;
- M3 development/model-selection role, never held-out validation;
- one shared training lifecycle and one-owner staged EVAL2 resource admission;
- destructive no-migration reset for old derived state;
- stage-local affected regression and final real-owner integration;
- long target-machine/GPU qualification separate/deferred.

## 21. Delegated mechanics

Implementation may choose, while preserving frozen semantics:

- exact class/module/schema names for study population, role pools, allocation groups and ladders;
- internal sparse/group representations;
- deterministic mathematically equivalent split-safe allocation scoring/tie details;
- exact representation of protected support records;
- three M artifacts versus indexed views of one authenticated M3 artifact;
- concrete new generation/version/error-code names;
- bounded test fixture sizes and numerical doubles below real semantic owners.

Reuse shared geometry/index/vector kernels where mathematics is genuinely common. Do not force allocation, rich training qualification, evaluation representation, CV validation and production through one generic policy abstraction merely for symmetry.

## 22. Reopen only on evidence

Reopen only the affected design surface if evidence proves:

1. correlation/equivalence group granularity makes the one-study `Nmax + M3` architecture systematically infeasible or pathologically wasteful;
2. split-safe evidence cannot protect training edge support adequately;
3. protected support cannot be represented robustly by the rich selector/repair mechanism;
4. residual evaluation is systematically biased enough to alter target-size decisions at practical M sizes;
5. one-study preflight conflicts with a genuinely required current product capability for multiple incompatible target-training heads;
6. configured sizes above old 16384 expose a real algorithm/representation limit needing explicit technical bounds;
7. post-selection group-safe CV systematically lacks enough independent support for scientifically valid selected data, requiring a revised CV validation design;
8. M3 reuse for final checkpoint selection conflicts with an independently required distinct model-selection authority;
9. default `[256,512,1024]` fails survivor/winner preservation.

A local reopen must not resurrect fixed-universe, full-complement, pre-selection-CV, automatic multi-domain, or migration architecture by convenience.

## 23. Handoff closure

```text
stakeholder requirements:
  training-priority size selection
  + bounded nested target evaluation
  + configurable power-of-two ladders
  + nominal Nmax + M3 capacity
  + no target-size domain multiplier
  + CV only after selected data freeze
  + one active plan / destructive cleanup

accepted architecture:
  one U_size
  -> group-safe P_train/P_eval (+ optional unused)
  -> protected train/eval support obligations
  -> one pi_train / exact T_N
  -> one frozen pi_eval / M1/M2/M3
  -> exact n1/n2/n3 target-size screen
  -> one N_selected/T_selected
  -> group-safe validation-only CV
  -> fresh final production
  -> held-out/calibration/locked stages

retired-plan invariants retained:
  exact boundary continuation + fresh production
  target-first ranking + replay admissibility
  shared training lifecycle/provenance
  one-owner staged EVAL2 RAM/resource semantics
  DATA7/DATA8 current-generation identity
  documentation build/verification

acceptance:
  Part 1 coherent single-authority documentation
  + Part 2 stage-local semantic/functional closure
  + affected regression after every material stage
  + final real-owner integration
  + structural absence of retired paths
  + explicit scientific sampling qualification status
```

No material reviewed design decision is intentionally delegated back to implementation discovery. Changes to single-study topology, role-pool separation, protected-support handoff, `Nmax + M3` capacity semantics, nonadaptive M ladder, target-first replay semantics, exact continuation, post-selection CV dependency direction, or destructive compatibility policy require a bounded Software Design reopen.
