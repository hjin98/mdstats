---
kind: implementation-workplan
workplan_id: CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V5
protocol_version: 5.8.0
status: active
created_date: 2026-08-28
reviewed_source_head: 6f0d34366ca954eabe21740ddda96357afc12eb1
review_revision: 5
architecture_change: major
compatibility_policy: destructive-generation-reset
supersedes:
  - CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V1
  - CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V2
  - CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V3
  - CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V4
  - all previously active target-size amendments and MLFF closeout workplans retired on 2026-08-28
---

# MLFF Target-Size Training-Priority Evaluation-Ladder Architecture Reset — V5 Freeze Candidate

## 0. Objective and frozen outcome

V5 is the sole current implementation authority for this reset. It incorporates an implementation dry-run against current source head `6f0d34366ca954eabe21740ddda96357afc12eb1` and closes code-level ownership conflicts that were not visible from the abstract design.

The new generation has exactly one target-size study:

- one resolved target label compatibility identity;
- one qualified population `U_size`;
- one correlation-safe training pool `P_train`;
- one correlation-safe target-size evaluation pool `P_eval`;
- optional unused/reference-only qualified data `U_unused`;
- one repaired training order `pi_train`;
- one frozen evaluation order `pi_eval`;
- one nested `M1 subset M2 subset M3` evaluation ladder;
- one target-size evidence stream/reducer;
- one `N_selected` and one exact `T_selected`;
- post-selection CV only;
- fresh final production only after CV accepts the frozen protocol.

There is no target-size domain fan-out. `LabelDomain` may remain an upstream compatibility/provenance concept, and metric internals may reduce by species/condition/block, but target-size authority never replicates candidates, M ladders, reducers, capacity, or selected N by domain.

Priority:

```text
scientific/product correctness
  > single-authority/simple architecture
  > performance/resource efficiency
  > development convenience / obsolete-state compatibility
```

Derived old state is not migrated. Raw source data remain reusable. Full long GPU/target-machine qualification remains deferred to final release; functional regression/integration and bounded scientific sampling qualification remain mandatory as specified below.

## 1. Dry-run implementation corrections

The dry-run inspected the current target-size policy/state, LabelDomain construction, DATA5/partition/leakage, TARGET-DATA roles, DATA6 difficulty/prediction domains, TargetCoverage, MVSEL2/REPAIR2/MVQUAL2, DATA7/feature-fit, production materialization, DATA8, EVAL2, online-monitor, MLCV roles, protocol state and current configuration surface. The following corrections are frozen:

1. **Exactly one participating target label compatibility identity.** Current LabelDomain already separates incompatible theory/energy-reference/derivative conventions. If target inputs resolve to more than one incompatible label domain/head, fail with a typed unsupported topology; do not merge/weight/replicate inside target-size.
2. **DATA5 pre-target authority owns no CV.** Current DATA5 serializes CV plans and its leakage report binds CV digests, which would make CV configuration contaminate target-size identity. New current-generation DATA5 owns partition/correlation units, outer roles, blinding/sealed-role state and pre-target/outer leakage only.
3. **Target allocation is pre-CV.** Replace the current TARGET-DATA role-freeze dependency on CV with a pre-CV role-allocation authority.
4. **DATA6 base evidence is separated from role-dependent evidence.** Structural descriptors/raw frozen foundation predictions may be precomputed broadly when role-independent. Target-label/foundation-residual difficulty views used for target selection are derived after allocation and only on `P_train`. CV-specific views are post-selection descendants.
5. **Selection preparation is not training preparation.** Current DATA7 fits feature metric, atomic E0 and weights over a whole canonical domain before applying a prescribed prefix. New selection-only fitted evidence may use `P_train`; membership-dependent training math must be fit from the exact gradient membership of each candidate/fold/final run.
6. **Exact selected membership cannot be re-expanded through units.** Current helpers turn unit IDs back into every frame in the unit. Post-selection CV and downstream DATA7/DATA8 carry exact selected frame UIDs; inherited group IDs constrain correlation-safe assignment but never add unselected sibling frames.
7. **Current target-size TargetCoverage/MVSEL/REPAIR/MVQUAL authority is single-study.** Per-domain collections/maps are removed from current persisted target-size topology. Lower-level single-study numerical kernels may be reused internally.
8. **Outer target evidence is truly held out.** Current online target monitor consumes DATA5 outer-monitor data and can participate in checkpoint control. New generation forbids outer held-out target evidence from target-size/final checkpoint stop/rank/top-K. M-rung development evidence owns target-side selection; replay true-label evidence may remain admissibility-only.
9. **Old SIZE-FIDELITY1 does not certify the new M ladder.** It is retired as current production qualification authority unless explicitly refactored/re-versioned for the new populations.
10. **Training-harness validation is not presumed inert.** During exact target-size continuation, any harness-required target-valid/diagnostic artifact must be proven non-controlling: no effect on gradients, LR scheduling, generic early stop, pre-boundary checkpoint ranking or survivor decisions. Only exact-boundary EVAL2 on the authorized `M_i` controls the screen.
11. **Configuration migration is end-to-end.** Current campaign config still describes target sizes as fixed. Parser/schema/default/example/roundtrip/resolved snapshot all move to the new power-based policy.
12. **One screening training protocol/method owns N selection.** Extra ablation/comparison methods may consume the selected N later but may not independently select another N within this workflow.

## 2. Authoritative lifecycle

```text
source / DATA4 partition-independent evidence / events
 -> DATA5 PRE-TARGET
      partition/correlation units
      outer roles
      blinding/sealed-role metadata
      pre-target/outer leakage audit
      NO CV
 -> exactly one resolved target label compatibility identity
 -> U_size = eligible target-development configurations for that identity
 -> correlation/equivalence allocation
      P_train / P_eval / optional U_unused
 -> protected train/eval support obligations
 -> reusable role-independent base evidence
 -> P_train-only selection evidence/preparation
 -> FEAS1 -> MVIDX1 -> single-study MVSEL -> REPAIR/MVSTATE -> MVQUAL
 -> pi_train -> exact T_N = pi_train[:N]
 -> P_eval-only pi_eval, frozen before candidate TRAIN2
 -> M1 subset M2 subset M3
 -> for each candidate/run:
      exact training preparation on T_N
      TRAIN2 exact continuation boundary
      EVAL2 exact corresponding M_i
 -> freeze N_selected and exact T_selected
 -> post-selection exact-membership CV plan + separate CV leakage audit
 -> exact per-fold training preparation and CV validation
 -> exact full-T_selected final training preparation
 -> fresh final production
      frozen M3 may control target-side final checkpoint/model selection
      replay TRUE_DFT evidence may enforce admissibility only
 -> outer/held-out validation -> calibration -> locked tests
```

No downstream CV/production/held-out/calibration/locked evidence feeds back into allocation, `pi_train`, `pi_eval`, survivors, or `N_selected`.

## 3. Pre-target DATA5 and CV split

### 3.1 New current DATA5 scientific bundle

Owns only:

- partition/correlation unit catalog;
- outer-role partitions;
- blinding/sealed-role state;
- event/source/lineage correlation facts needed before target allocation;
- pre-target/outer leakage audit.

It does not contain/hash CV fold count/seed, CV plans, monitors, evaluation roles, purge assignments or CV leakage-plan digests.

The old CV-coupled DATA5 schema is a retired generation and is rejected in a new-generation workspace rather than migrated.

### 3.2 Post-selection CV authority

CV is a descendant of `selected_data_digest`. It owns exact fold memberships and a separate CV leakage audit. CV-only changes invalidate CV descendants only; they cannot invalidate/recompute target-size selection.

Generic multi-domain DATA5 utilities may remain for unrelated workflows if they cannot contaminate this current target-size dependency path.

## 4. One target label universe

Before target-size allocation:

1. resolve the target training source records to the existing LabelDomain compatibility policy or a clean successor;
2. require exactly one participating target label compatibility identity;
3. define `U_size` from its eligible development configurations only;
4. retain compatible numerical/software variants as provenance/quality evidence when existing compatibility policy permits them;
5. fail if multiple incompatible target heads/protocols remain.

Target-size current schemas may not expose `domains`, `domain_prefix_digests`, per-domain ladders/reducers or `D * ...` target-size workload/capacity semantics.

## 5. Canonical target/evaluation configuration

```toml
[target_data.size_convergence]
target_size_power_min = 7
target_size_power_max = 14
evaluation_size_powers = [8, 9, 10]
fidelity_epochs = [1, 3, 10]
```

Resolve once:

```text
candidate_target_sizes = [2^p for p in pmin..pmax]
Nmax = 2^pmax
evaluation_sizes = [2^q for q in evaluation_size_powers]
rungs = [(n1,m1),(n2,m2),(n3,m3)]
```

Validation:

- integer nonnegative powers;
- `pmin < pmax` and at least three target candidates under the current funnel;
- exactly three strictly increasing evaluation powers;
- exactly three strictly increasing positive fidelity boundaries;
- derived counts fit owning integer/index/serialization types;
- no scientific `<=16384` guard;
- no rescue/intermediate non-policy sizes;
- powers and readable sizes persisted;
- all scientific values digest-bound;
- old fixed/flexible aliases not silently reinterpreted.

Defaults produce target sizes `128..16384` and eval sizes `[256,512,1024]`. If the largest configured target remains materially superior, return `nonconverged_at_configured_ceiling`; do not invent a rescue size.

C1 includes parser/schema/default/CLI/API/config roundtrip, `campaign.toml.example`, resolved-config persistence and terminology cleanup. CV configuration remains downstream-only.

## 6. Capacity and correlation-safe role allocation

Because `M1` and `M2` are prefixes of `M3`, nominal target-size capacity is:

```text
|U_size| >= Nmax + m3
```

Default example: `16384 + 1024 = 17408` configurations. This is config-derived, not fixed, not IID, and not multiplied by folds/domains/candidates/seeds/stages. Whole correlation groups/outer exclusions may require more raw source data.

Allocation groups close over applicable:

- DATA5 correlation/partition units;
- exact/near-duplicate geometry families;
- declared correlation/active-learning families;
- protected event-window linkage;
- source/lineage relations that forbid train/eval splitting.

Each group receives one role:

```text
train_authorized | evaluation_authorized | unused_reference
```

with:

```text
P_train intersect P_eval = empty
|P_train| >= Nmax
|P_eval| >= m3
```

Pools may exceed exact counts because groups are indivisible.

Allocation uses only versioned split-safe structural/categorical/provenance evidence. It may not use candidate error/outcomes, role-local fitted transforms, role-dependent foundation residual/difficulty, fitted E0/normalization, CV/final/calibration/locked evidence.

Allocation priorities:

1. preserve unique/scarce training support;
2. make exact Nmax materializable with required support;
3. preserve disjoint capacity for exact M3 where feasible;
4. select evaluation groups from redundant/correlation-distinct support;
5. preserve representative eval support;
6. deterministic tie-break;
7. leave unnecessary surplus unused/reference-only.

The allocator publishes training must-cover obligations and evaluation representative-support goals. `T_max` and `M3` must realize them where feasible; deficiencies are explicit, not repaired by post-freeze role stealing.

## 7. Three evidence/preparation layers

### 7.1 Role-independent base evidence

May be computed before allocation when scientifically membership-independent:

- structural/profile descriptors;
- geometry/condition/provenance classifications;
- frozen foundation raw predictions/descriptors;
- immutable source/frame metadata.

These caches do not depend on CV policy.

### 7.2 P_train selection evidence/preparation

After allocation, derive on `P_train` only:

- target-label/tail coverage families;
- foundation residual/difficulty families formed from frozen predictions + true target labels;
- target coverage references;
- selection-only fitted feature/scaling authority.

This evidence may depend on all `P_train` because it chooses membership; it is non-gradient.

TargetCoverage/FEAS/MVIDX/MVSEL/REPAIR/MVQUAL publish one current target study, not a collection of target domains. Reuse optimized internal numerical kernels if their public/current scientific topology remains one study.

### 7.3 Exact gradient-bearing training preparation

Any membership-dependent quantity affecting optimization/model math is derived from the exact target gradient membership:

```text
candidate screen -> exact T_N
CV fold          -> exact selected fold-training frames
final production -> exact T_selected
```

This includes as applicable E0/reference fits, learned normalizations/statistics, global weight normalizations/fitted objective quantities and exact target training files/sidecars.

Thus:

- `P_train \ T_N` can influence selection of T_N but not candidate-N training math after membership freezes;
- `P_eval`/M_i cannot influence training preparation;
- unselected siblings in a correlation group never enter gradient preparation;
- final production cannot inherit an all-development fitted core.

Pointwise/membership-independent quantities may be reused. Exact prefix/fold sufficient statistics, subtractive identities, vectorization and caches are encouraged if reference tests prove exact equivalence and scientific identities bind the exact membership.

## 8. Rich training order

Only `P_train` enters:

```text
P_train selection prep
 -> FEAS1 -> MVIDX1 -> MVSEL -> REPAIR/MVSTATE -> MVQUAL -> pi_train
```

Required:

- one repaired master order;
- exact nested `T_N = pi_train[:N]`;
- exact `T_max` cardinality Nmax;
- one candidate-data identity per N;
- allocation-protected support carried into hard coverage/repair/qualification;
- scientifically valid target-label/foundation-residual weakness/diversity coverage retained;
- no per-rung reselection/repair;
- no eval/unused frame in candidates;
- rich failure fails closed;
- no downstream hardcoded fixed-size universe.

## 9. Frozen evaluation ladder

Build one deterministic `pi_eval` over `P_eval` after role allocation and before the first candidate TRAIN2 trajectory.

Allowed ordering evidence: structural/condition/provenance evidence, target-label distribution information inside already-frozen P_eval, and residuals from an independent frozen foundation model.

Forbidden: target-size candidate predictions/errors, survivor/ranking/N outcomes, final-production predictions, CV/calibration/locked evidence.

Materialize:

```text
M1 = pi_eval[:m1]
M2 = pi_eval[:m2]
M3 = pi_eval[:m3]
M1 subset M2 subset M3 subset P_eval
```

M3 realizes representative residual-support goals where feasible. Persist correlation/effective-sample/support diagnostics. `P_eval \ M3`/unused data may support retrospective qualification but are not runtime fallbacks.

## 10. Exact screening and training-harness controls

Stages are exactly `(n1,M1) -> (n2,M2) -> (n3,M3)`.

Funnel remains:

```text
q qualified sizes
 -> all q at n1
 -> min(q,4) at n2
 -> 2 finalists at n3
 -> 1 selected
```

with accepted minimum-qualified-size, paired optimizer seeds and practical-equivalence/smaller-size semantics.

Exactly one resolved training protocol/method owns target-size screening scientific policy and seeds. Other comparison methods do not independently select N.

Continuation rules:

- boundaries are exact checkpoints, not generic horizons;
- survivor continues from prior boundary checkpoint;
- no epoch-0 restart;
- evidence binds exact start/end/checkpoint identity;
- exact checkpoints persist/restart;
- ordinary success early stop cannot end screening before boundary;
- production epoch maximum independent of n3.

If MACE/training harness requires target-valid/monitor input during screen, it must be explicitly non-controlling: no effect on gradients, LR schedule, generic early stop, checkpoint rank/selection before boundary or survivor authorization. Use a gradient-authorized diagnostic subset or equivalent inert input. Never route `M_i`, outer held-out, calibration or locked data through a generic controlling training channel.

At the boundary EVAL2 consumes exactly the corresponding frozen M_i. The reducer alone owns survivor/ranking decisions.

Replay TRUE_DFT evidence may enforce hard checkpoint admissibility; target-side EVAL2 owns ordering. Replay score cannot become a secondary ranking objective.

## 11. EVAL2 / OPT-EVAL4

New target-size roles:

```text
coarse -> M1
short -> M2
final_screen -> M3
```

Retire `size_development_complement`, `size_development_coarse`, maximum-prefix subtraction, full-complement fallback, legacy population samplers used only by retired generations and per-domain target-size aggregation.

Preserve canonical target-force estimator and one-owner staged execution:

```text
parent/staged owner -> CPU prepare -> accelerator inference -> CPU finalize -> parent commit
```

Parent owns aggregate resource admission/lifetime; nested inference cannot reacquire aggregate RAM/VRAM or double-charge fixed overhead. Preserve existing optimized batching/cache/mmap/concurrency machinery unless evidence requires repair.

## 12. Freeze selected data

Terminal selected outcome freezes:

```text
N_selected = N
T_selected = pi_train[:N]
```

Selected-data identity binds generation/policy, resolved target label identity, role allocation, pi_train/candidate identity, pi_eval/M ladder, exact continuation/paired-seed ancestry, N and exact ordered T_selected membership.

CV/final production cannot enlarge T_selected with P_train surplus, P_eval, M3 or unused data.

## 13. Post-selection exact-membership CV

CV consumes exact T_selected plus inherited correlation/equivalence group IDs.

Each fold stores exact selected frame UIDs for gradient training, checkpoint selection/monitor, CV evaluation and purge, plus selected-data/group lineage. A group ID constrains assignment but never expands membership. Example invariant: if an upstream unit has 10 frames and T_selected contains 3, only those 3 can appear anywhere in CV; the remaining 7 are absent.

A separate CV leakage audit proves:

- every role subset is exact T_selected;
- no unselected frame introduced;
- prohibited groups do not cross incompatible roles;
- fold roles are disjoint as required;
- no P_eval/M/outer data becomes gradient data.

CV is validation-only. It may block production; it cannot tune a material training policy and retain old target-size evidence. CV-only settings invalidate CV descendants only. Material screening/training policy changes invalidate target-size and descendants.

Insufficient correlation-distinct support for requested CV topology fails after selection without changing N, stealing eval data, rerunning allocation or weakening leakage policy.

Every fold gets training preparation fitted on exact fold gradient frames (or a mathematically exact equivalent sufficient-statistic computation). No whole-unit expansion or wider all-development fitted core.

## 14. Fresh final production and held-out outer evidence

After CV acceptance:

- final training starts fresh from accepted initialization/foundation model;
- gradient target data = exact T_selected;
- membership-dependent preparation is fitted on exact T_selected;
- production budget/adaptive policy independent of n3;
- shared canonical TRAIN2 lifecycle owns execution/provenance.

Frozen M3 may control final-development target checkpoint stop/rank/model selection. It stays non-gradient and immutable.

Replay TRUE_DFT may remain a hard admissibility guard but cannot reorder target-side ranking.

Outer target monitor/validation is held out: it cannot stop/rank/top-K target checkpoints if claimed as independent validation. Any training-internal target diagnostic monitor must come from gradient-authorized data and be explicitly non-controlling. Calibration/locked tests remain later and separate. M3 is never advertised as held-out after influencing size/checkpoint choice.

## 15. DATA6 / DATA7 / DATA8 / MLCV contracts

### DATA6

Separate:

1. pre-target role-independent base evidence;
2. post-allocation P_train residual/difficulty/coverage views;
3. post-selection exact-membership CV training/prediction views;
4. separately authorized outer/calibration/locked evidence.

CV-only policy cannot invalidate base evidence/target-size state.

### DATA7

Replace the monolithic canonical-DATA5-domain assumption with distinct current-generation identities/APIs for P_train selection preparation and exact-role training preparation. A prescribed prefix cannot merely filter after E0/normalization/objective fitting on a wider domain.

### DATA8

Fixed files/protocol identities consume exact role membership/preparation. Cache keys include exact membership and scientific preparation identity where values/weights/E0/config depend on them. No helper may recover wider membership by expanding upstream units.

### MLCV roles

Version/replace the unit-ID/DATA5-CV-bound catalog. New MLCV roles descend from selected-data + post-selection CV and carry exact selected-frame membership. Reuse role-operation checking only after semantics are updated. Outer held-out target role loses checkpoint-selection permissions in the new generation.

## 16. Persistence/restart identity DAG

New generation only; old fixed/complement/domain-prefix/CV-coupled derived state is rejected.

**Pre-target/target-size identity** includes source/frame/DATA4; DATA5-without-CV; one target label identity; powers/boundaries/seeds/practical-equivalence; allocation/equivalence policy and support obligations; P_train/P_eval; base evidence; P_train selection prep; MVSEL/REPAIR/MVQUAL; frozen pi_eval policy.

**Candidate identity** adds exact T_N membership/order; exact membership-dependent training-prep digest; training scientific policy; replay admissibility policy if used; continuation start/end/checkpoint identity.

**Selected-data identity** adds terminal evidence, N_selected and exact T_selected digest.

**CV identity** adds selected-data, exact fold memberships, CV policy and CV leakage audit. CV-only settings are absent from target-size identity.

**Production identity** adds selected-data, required CV acceptance, exact final prep, production budget/adaptive policy and checkpoint-selection/admissibility policy.

Execution-only worker/chunk/cache/batch/RAM/VRAM settings do not alter scientific identity when mathematics is unchanged.

Restart acceptance proves deterministic identities; target-size policy changes invalidate target-size/descendants; CV-only changes preserve target-size/selected/base evidence; production-only changes preserve upstream; exact boundary restarts use authenticated checkpoint+M identity; pi_eval never rebuilt from candidate outcomes; old generations fail actionably.

## 17. Destructive cleanup

Remove/retire from reachable current execution as applicable:

- fixed target-size/ceiling scientific authorities and <=16384 guard;
- per-domain target-size candidates/prefixes/M ladders/reducers/fixed-size imports;
- TARGET-DATA role freeze requiring pre-selection CV;
- CV plans/digests in current DATA5 target-size lineage;
- CV-specific DATA6 domains before selected-data freeze;
- all-development DATA7 fitted cores used as training prep for exact prefixes;
- whole-unit expansion as selected-data/CV membership authority;
- complement/coarse target-size roles and fallback/subtraction evaluator;
- obsolete fixed/flexible/TARGET-SIZE-V5 aliases denoting retired semantics;
- old target-size migration/bridge/receipt code used only by retired generations;
- duplicate training/resource owners;
- outer-target checkpoint-control authority inconsistent with held-out validation;
- duplicate final target checkpoint selectors after M3 consolidation;
- tests whose sole purpose is retired behavior.

SIZE-FIDELITY1 is historical unless re-versioned for the new M ladder; old evidence cannot certify new defaults.

## 18. Preserved performance/lifecycle doctrine

Preserve:

- one shared TRAIN2 lifecycle for screening/CV/final;
- `preflight -> resource acquire -> prepared execution -> checkpoint publish -> release`;
- no direct/private/CLI alternate scientific lifecycle;
- exact continuation first-class;
- fresh final production;
- one-owner OPT-EVAL4 resource admission;
- immutable DATA7/8 cache/provenance machinery where compatible with exact membership;
- existing vectorized/parallelized coverage/index/selection/batching/mmap/scheduler machinery.

Do not replace optimized kernels with scalar/worse-scaling code unless correctness requires it. Exact prefix/fold sufficient-statistic acceleration is preferred where possible and reference-tested.

## 19. Part 1 — docs/spec authority reset

Execute first on implementation branch; do not merge future docs alone while executable main is old.

Update architecture manuals, target-size/TARGET-DATA/DATA5/leakage/coverage/MVSEL/REPAIR/MVQUAL/EVAL2/OPT-EVAL4/CV/MLCV/DATA7/8/training-monitor/persistence specs, dependency graphs/source maps and campaign configuration docs/example.

Required diagram:

```text
DATA5 pre-target NO CV
 -> one target label universe
 -> P_train/P_eval
 -> P_train selection prep -> pi_train
 -> pi_eval/M ladder
 -> exact T_N training prep + screen
 -> T_selected
 -> exact-membership post-selection CV
 -> exact T_selected final prep/production
 -> held-out outer validation
```

Docs must distinguish selection preparation vs gradient-bearing training preparation and state group identity constrains roles but does not expand exact membership. Run repository docs build/lint/reference/PDF checks.

## 20. Part 2 gates

### C1 — generation/config/single target study

Implement new semantic generation, power resolver/config surface, configured ceiling, exactly-one-target-label preflight and exactly-one-screening-protocol/method rule. Test default/nondefault powers, no hidden ceiling, ambiguous/multiple target domains/methods, serialization/config roundtrip.

### C2 — DATA5 pre-target split

Remove CV ownership from current DATA5 scientific lineage; preserve outer/correlation/blinding/pre-target leakage. Replace CV-dependent TARGET-DATA freeze. Test CV-only digest invariance and rejection of old CV-coupled generation.

### C3 — allocation/evidence staging

Implement allocation groups, P_train/P_eval/U_unused, group-aware Nmax+m3 feasibility, protected support, base-vs-role-dependent DATA6 evidence. Test nominal-but-group-infeasible cases, deterministic allocation, support preservation, no post-freeze stealing, CV independence.

### C4 — single-study selection + M ladder

Flatten TargetCoverage/FEAS/MVIDX/MVSEL/REPAIR/MVQUAL current topology; one pi_train and one pi_eval/M ladder. Test no current domain maps, exact nested T_N/M_i, protected support, eval-order independence from candidates, deterministic restart/performance/reference equivalence.

### C5 — exact candidate prep + target-size orchestration

Refactor DATA7/production/DATA8 so candidate training preparation fits exact T_N while selection prep remains P_train-scoped. Integrate real owners:

```text
config -> DATA5 pre-target -> one target label -> allocation
 -> selection prep/pi_train -> pi_eval/M
 -> exact T_N training prep -> TRAIN2 continuation
 -> boundary checkpoint -> EVAL2 M_i/replay admissibility
 -> reducer -> selected/configured-ceiling -> T_selected
```

Test exact preparation membership, excluded-frame non-influence, no P_eval influence, continuation, non-controlling harness valid input, eliminated-candidate no-work, no complement fallback.

### C6 — exact-membership post-selection CV

Implement selected-data CV + leakage audit and re-version CV-specific DATA6/DATA7/8/MLCV. Test the 10-upstream-frames/3-selected scenario, group-split rejection, CV-only invalidation direction, exact fold prep, insufficient-group failure without changing N.

### C7 — final production/monitor roles

Fresh exact-T_selected prep/training after CV. M3 target-side checkpoint control; replay admissibility only; outer target held out/non-controlling. Test exact final prep, fresh initialization, production budget independent of n3, M3 frozen/non-gradient, outer role authorization rejection.

### C8 — destructive cleanup/resources/performance

Delete retired paths and preserve one TRAIN2/OPT-EVAL4 resource owner plus optimized kernels. Run structural absence/import/package/performance/reference/affected regression.

### C9 — final functional closure

Reconcile all obligations; re-derive final affected surface; run complete affected regression, real-owner assembled integration from config through selection/CV/final entry, broader/full suite where impact cannot be bounded, docs/PDF checks, deterministic/reference/performance checks and authority-uniqueness/retired-path inspection.

Full long GPU production qualification remains deferred.

## 21. Mandatory regression/integration cases

At minimum prove:

- default/nondefault target/eval powers/boundaries;
- exactly one target label identity and typed failure for incompatible multiple domains;
- one screening method/protocol;
- DATA5 target-size digest invariant to CV-only config;
- old CV-coupled DATA5 and old target-size generation rejected;
- group-aware Nmax+m3 semantics;
- no current per-domain target-size prefix/ladder/reducer authority;
- exact T_N candidate membership and exact candidate training-prep membership;
- changes in `P_train \ T_N` cannot change candidate training preparation/model input after T_N freezes;
- P_eval/M/outer/calibration/locked cannot change candidate training prep;
- exact nested M ladder and pre-TRAIN2 eval-order freeze;
- exact continuation/restart at every boundary;
- harness valid/diagnostic input non-controlling during screen;
- replay admissibility separate from target ranking;
- immutable selected-data freeze;
- post-selection CV exact subset of T_selected and no unit expansion;
- CV group-split rejection;
- CV-only changes invalidate CV descendants only;
- exact fold training preparation;
- CV failure does not alter N or steal eval data;
- final prep exactly T_selected and fresh production;
- M3 authorized for final target checkpoint control;
- outer held-out target evidence unauthorized for checkpoint stop/rank/top-K;
- old SIZE-FIDELITY1 cannot masquerade as new M-ladder qualification;
- no complement/fixed/domain fallback;
- no duplicate aggregate training/evaluation resource ownership.

## 22. Scientific M-ladder qualification

Functional tests do not prove `[256,512,1024]` preserves target-size decisions. Provide reproducible retrospective/reference qualification against the largest practical residual/reference population using completed checkpoints/predictions or bounded representative runs, without tuning from held-out CV/calibration/locked evidence.

Before defaults are called scientifically qualified, show:

1. M1 does not falsely eliminate reference-competitive finalists;
2. M2 preserves reference finalist population;
3. M3 selects the same N under practical-equivalence/smaller-size rule;
4. support/correlation diagnostics are adequate;
5. M ladder is at least as effective as naive same-cardinality temporal/uniform baselines on important strata;
6. real orchestration consumes exact M_i at exact n_i;
7. allocation/training-prep/M evidence is leakage-clean;
8. restart/cache/worker changes preserve scientific identity;
9. evaluation work is materially reduced relative to full complement.

If evidence unavailable: `deferred/unavailable`, not passed. If defaults fail, explicitly change policy identity and requalify; never silently expand runtime M.

## 23. Frozen decisions / delegated details / reopen triggers

### Frozen

- one target-size study, one resolved target label identity, no target-size domain fan-out;
- DATA5 pre-target has no CV;
- allocation before role-dependent target selection evidence;
- base evidence separated from post-allocation residual and post-selection CV views;
- selection fitting may use P_train; membership-dependent training prep uses exact gradient membership;
- no unit/group expansion adds unselected frames;
- one pi_train, one pi_eval, exact nested T_N/M_i;
- eval order freezes before candidate TRAIN2;
- post-selection exact-membership correlation-safe validation-only CV;
- Nmax+m3 nominal capacity lower bound;
- exact continuation, non-controlling screen diagnostics, fresh production;
- target-side ranking, replay admissibility-only;
- M3 may control final target checkpoint selection; outer target validation held out;
- configured powers/ceiling and destructive reset;
- EVAL2 metric/OPT-EVAL4 resource owner and one shared TRAIN2 lifecycle preserved;
- long GPU qualification deferred.

### Delegated

- exact class/module/schema names;
- internal sparse/vectorized data structures;
- deterministic scoring/tolerances preserving frozen allocation priority;
- exact sufficient-statistic vs direct recomputation strategy for exact training prep;
- reuse/wrapping of old single-study numerical kernels;
- local fixture/fake strategy below semantic owners;
- generic non-target DATA5/CV utilities may survive if they cannot enter new target-size lineage.

### Reopen only on evidence

1. allocation closure creates pathological giant groups/default infeasibility;
2. split-safe evidence cannot protect required training edges;
3. exact candidate-specific training preparation changes the scientific screening problem enough to require policy redesign;
4. exact-membership post-selection CV cannot provide meaningful validation for representative selected datasets;
5. M3 checkpoint reuse conflicts with a genuinely independent required model-selection authority;
6. default M powers fail survivor/winner preservation;
7. a real technical bound appears beyond default 16384;
8. exact preparation is prohibitively expensive and no exact accelerated formulation exists;
9. a real product requirement emerges for multiple incompatible target training studies.

## 24. Freeze verdict

The implementation dry-run exposed substantial current-code distance but no unresolved architecture question after these corrections. Once this V5 file is committed as the sole active target-size plan, the design is frozen for implementation. Further issues are conformance/debugging problems unless they meet an explicit reopen trigger above.
