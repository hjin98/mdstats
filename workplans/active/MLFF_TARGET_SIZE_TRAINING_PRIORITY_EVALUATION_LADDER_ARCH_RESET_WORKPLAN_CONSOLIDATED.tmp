---
kind: implementation-workplan
workplan_id: CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V3
protocol_version: 5.8.0
status: active
created_date: 2026-08-28
reviewed_head: 729754288b99f3384677ffdbd414e91ea68f199f
review_revision: 3
architecture_change: major
compatibility_policy: destructive-generation-reset
supersedes:
  - CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V1
  - CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V2
  - prior active MLFF target-size exact-boundary amendments and closeout plans
---

# MLFF Target-Size Training-Priority Evaluation-Ladder Architecture Reset — Consolidated Workplan

## Objective and final architecture decision

Replace the current fixed-target-size/full-complement generation with one clean current target-size architecture that has exactly:

- one authoritative target-size study population;
- one target-training authorized pool;
- one target-training master order;
- one target-size evaluation authorized pool;
- one frozen nested `M1/M2/M3` evaluation ladder;
- one target-size evidence stream and reducer;
- one selected target cardinality `N_selected` and one selected target dataset `T_selected`;
- cross-validation only after target size and selected target data are frozen.

The target-size workflow must **not** introduce or preserve a second “domain” dimension. Upstream electronic-structure label compatibility remains a data-ingest/preflight safety mechanism, but label-domain count is not a target-size axis, does not replicate candidate prefixes or evaluation ladders, and does not multiply target-size capacity or evaluation workload. If target inputs require genuinely incompatible training heads/protocols, this workflow fails with an explicit unsupported-topology/preflight outcome; a separate multi-head/multi-study architecture would require an explicit future design.

The stakeholder priority remains:

```text
scientific/product correctness
  > clean single-authority architecture
  > material performance/resource efficiency
  > development convenience / obsolete-state compatibility
```

## Final independent review findings incorporated

This revision incorporates the user corrections and a fresh Software Design review over V2, current target-size code, DATA5 correlation units, current CV construction, current target-size persistence, and the active workplan set.

The following material gaps are closed in this consolidated contract:

1. **No target-size domain axis.** Current `TargetSizeStudyCandidate.domain_prefix_digests`-style topology is retired from target-size authority. One candidate size owns one target candidate-data identity, not one prefix per label domain.
2. **Role pools are distinct from exact materialized sets.** Correlation/equivalence groups may contain multiple configurations, so a train-authorized role pool cannot always contain exactly `Nmax` frames. The architecture therefore freezes correlation-safe authorized pools first, then materializes exact `Nmax` and exact `M_i` configuration sets from those pools.
3. **The capacity rule is correctly scoped.** The nominal target-size-stage lower bound is `Nmax + M3` configurations because `M1 subset M2 subset M3`. It is not multiplied by CV, label-domain count, candidate count, seed count, or cumulative inference work. Whole correlation groups and outer-role exclusions may require more raw/qualified source configurations than this lower bound.
4. **CV occurs after target-size selection.** CV is validation of the already-selected training protocol/data, not an input to target-size materializability or MVQUAL.
5. **CV is group-safe.** Post-selection CV partitions the correlation/equivalence groups represented in `T_selected`; it must not independently scatter correlated selected frames across folds.
6. **CV is validation-only.** CV may accept or reject the frozen selected protocol, but it may not tune training hyperparameters and continue as though target-size evidence remained valid. A material training-policy change requires an explicit new generation/run from the target-size boundary.
7. **CV identity is downstream-only.** Changing CV fold count/seed/monitor/purge policy invalidates CV descendants only; it must not invalidate or recompute the frozen target-size study.
8. **CV precedes final full-data production.** After `N_selected`/`T_selected` freeze, run CV validation first. Only an accepted frozen protocol proceeds to fresh final production on the full `T_selected`.
9. **Evaluation order is nonadaptive to candidate models.** `pi_eval` freezes before the first candidate TRAIN2 trajectory. Candidate predictions, survivor decisions, and selected-size outcomes cannot choose or reorder `M_i`.
10. **Surplus qualified data need not be forced into a role.** The current target-size study may leave unused/reference-only configurations outside the train/evaluation authorized pools; forcing the whole development universe into train/eval adds complexity without scientific value.
11. **Retired-plan invariants are carried forward before archival.** Exact-boundary continuation, fresh production, one shared training lifecycle, one-owner staged EVAL2 resource admission, DATA7/DATA8 provenance, and documentation build obligations remain protected without keeping their old workplans active.
12. **Scientific sampling qualification is distinct from functional closure.** If representative data/checkpoints needed to qualify `[256,512,1024]` are unavailable, the implementation may be functionally complete but sampling-policy qualification is deferred/unavailable, not passed.

## 1. Authoritative lifecycle

The current-generation lifecycle is:

```text
source / DATA4 upstream evidence / events
 -> DATA5 outer-role + correlation/equivalence authority
 -> single-target-study compatibility/preflight
 -> qualified target-size population U_size
 -> correlation-safe train/evaluation role allocation
      -> P_train  (target-training-authorized pool)
      -> P_eval   (target-size-evaluation-authorized pool)
      -> U_unused (optional unused/reference-only qualified remainder)
 -> rich target-training ordering/qualification inside P_train
      -> pi_train
      -> exact configured target-size prefixes T_N = pi_train[:N]
 -> frozen evaluation ordering inside P_eval
      -> pi_eval
      -> M1 subset M2 subset M3
 -> exact target-size screening
      (n1,M1) -> (n2,M2) -> (n3,M3)
 -> freeze N_selected and T_selected = pi_train[:N_selected]
 -> construct group-safe CV from T_selected
 -> CV validation of the frozen training protocol
 -> fresh final production on full T_selected
      -> M3 may serve final-development checkpoint/model selection
 -> outer/held-out validation, calibration, locked tests
```

No downstream CV, production, held-out, calibration, or locked evidence may feed back into the already-frozen target-size selection.

## 2. One target-size study; upstream label compatibility only

### 2.1 Target-size topology

The target-size owner consumes one resolved target-data study population `U_size`. It publishes one scientific ladder and one selected `N`.

Target-size schemas and runtime objects must not preserve a second target-size “domain” dimension such as:

- `domain_prefix_digests` on each target-size candidate;
- per-domain target-size candidate membership;
- per-domain `M1/M2/M3` ladders;
- per-domain target-size reducers/weighted aggregation;
- automatic `D * (...)` capacity or inference semantics;
- one target-size study replicated for every `LabelDomain`.

Internal metric block/condition/species reductions are allowed where they are part of the canonical force estimator; those are metric internals, not target-size domains.

### 2.2 Label compatibility boundary

`LabelDomain` remains an upstream electronic-structure compatibility concept. Before the target-size study begins, campaign preparation must resolve target inputs to one training-compatible target study/head.

If the target inputs would require more than one incompatible target-training head or incompatible scientific label convention, the target-size preflight fails with a typed unsupported-topology/incompatible-target-study outcome. It must not silently instantiate multiple target-size studies.

The exact upstream mechanism/class name is delegated; the target-size end state is not.

## 3. Capacity and role-allocation semantics

### 3.1 Nominal capacity rule

Let the canonical target-size configuration resolve:

```text
Nmax = largest configured target candidate size
m3   = largest configured target-size evaluation cardinality
```

Because:

```text
M1 subset M2 subset M3
```

the nominal qualified configuration-count lower bound is:

```text
|U_size| >= Nmax + m3
```

Default:

```text
Nmax = 2^14 = 16384
m3   = 2^10 = 1024
nominal lower bound = 17408 qualified configurations
```

This is **not** a fixed 17,408 requirement; it is derived from resolved configuration. It is not a count of IID samples. It is not multiplied by CV folds, label domains, seeds, candidates, or screening stages.

Whole correlation/equivalence groups, protected outer roles, event windows, and other leakage exclusions can make the actual raw/qualified source requirement exceed the nominal lower bound. Preflight must use real group-aware feasibility, not only arithmetic frame count.

### 3.2 Allocation groups

The train/evaluation role split operates on indivisible allocation groups. An allocation group is the connected component of observations that current leakage/correlation policy forbids from being split between target training and target-size evaluation. At minimum incorporate the current applicable relations for:

- DATA5 correlation/partition units;
- exact/near-duplicate geometry families;
- explicitly declared correlation/active-learning families;
- protected event-window linkage;
- other current source-lineage relations whose policy forbids incompatible-role splitting.

All members of one allocation group receive the same target-size role:

```text
train-authorized
or
evaluation-authorized
or
unused/reference-only
```

This role exclusivity protects train/evaluation separation; it does not claim independence among frames inside one group.

### 3.3 Authorized pools versus exact scientific sets

Define:

```text
P_train = all configurations in train-authorized allocation groups
P_eval  = all configurations in evaluation-authorized allocation groups
```

with:

```text
P_train ∩ P_eval = empty
|P_train| >= Nmax
|P_eval|  >= m3
```

The pools may exceed the exact requested configuration counts because groups are indivisible.

The exact maximum training set is materialized only after the rich training order exists:

```text
T_max = pi_train[:Nmax]
```

and the exact evaluation ladder only after `pi_eval` exists:

```text
M1 = pi_eval[:m1]
M2 = pi_eval[:m2]
M3 = pi_eval[:m3]
```

Thus role safety and exact configured cardinality are both preserved without pretending a variable-size correlation group is a single configuration.

### 3.4 Training-priority allocation objective

Allocation runs before role-local fitted target preparation and uses only a versioned split-safe feature contract.

Allowed evidence includes partition-independent:

- geometry/structural descriptors;
- composition/cell/condition/regime/temperature/strain identities;
- upstream declared event classes/protected event windows;
- source/run/replica/provenance/correlation identities;
- other explicitly documented pre-role structural/categorical evidence.

Prohibited allocation-ranking inputs include:

- candidate-model predictions/errors;
- EVAL2 outcomes or survivor decisions;
- role-local fitted DATA6/DATA7 transforms;
- training-role-dependent foundation residual/difficulty values;
- role-local E0/normalization fits;
- CV, calibration, locked-test, or downstream production evidence.

A predeclared upstream event class may be used categorically when its detector is frozen before role allocation; direct future candidate error/model-selection evidence may not.

Required allocation priority:

1. protect unique/scarce split-safe support for training;
2. ensure `P_train` can materialize `Nmax` while preserving important training coverage;
3. preserve at least enough disjoint residual capacity to form `P_eval`/`M3` whenever the qualified population makes that feasible;
4. select evaluation-authorized groups preferentially from redundant/correlation-distinct support so `M3` remains representative;
5. use deterministic stable tie-breaking;
6. leave unnecessary surplus as `U_unused` rather than over-allocating either role.

Evaluation does not steal uniquely required training support merely to appear complete. Conversely, optional training allocation must not exhaust all redundant residual support when a feasible representative `M3` can be preserved.

After the split freezes, role-local FEAS/MVQUAL/TRAIN2/EVAL2 outcomes cannot move groups between pools.

If no group-safe allocation can satisfy both `Nmax` and `m3`, fail target-size preflight with a clear capacity/leakage diagnostic. Do not lower configured sizes, split a prohibited group, or fall back to the legacy complement evaluator.

## 4. Rich target-training authority

Only `P_train` may enter target-training fitted selection.

Preserve/refactor the current rich chain:

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

- one repaired master target-training order `pi_train`;
- every configured target candidate is an exact prefix `T_N = pi_train[:N]`;
- `T_max = pi_train[:Nmax]` has exactly `Nmax` configurations;
- one candidate-data identity per target size, with no target-size domain-prefix map;
- hard coverage/obligations, repair, representative diversity, and independent MVQUAL remain authoritative where scientifically valid;
- no independent per-rung re-selection/repair;
- no evaluation-authorized/unused frame may enter a target candidate;
- a rich-selection/MVQUAL failure after role freeze fails closed rather than stealing data from `P_eval`.

The configured ladder is canonical and may be smaller/larger than the default subject to actual resource and data feasibility; no hidden eight-rung implementation loop is allowed.

## 5. Frozen target-size evaluation ladder

Build one deterministic evaluation order `pi_eval` over `P_eval` after train/evaluation roles freeze and **before the first target-size candidate TRAIN2 trajectory starts**.

Evaluation-order evidence may include:

- split-safe structural/condition/provenance features;
- target-label distribution information after role allocation freezes;
- residuals from a frozen external/foundation model whose identity is independent of target-size candidate trajectories.

It may not include:

- any target-size candidate prediction/error;
- survivor/ranking/selected-size outcomes;
- final-production predictions;
- CV, calibration, locked-test, or downstream deployment evidence.

Evaluation selection is representative model-selection coverage, not training MVQUAL. It does not automatically inherit REPAIR2 or the training hard pass threshold.

Required exact ladder:

```text
M1 = pi_eval[:m1]
M2 = pi_eval[:m2]
M3 = pi_eval[:m3]
M1 subset M2 subset M3
```

Persist correlation/effective-sample/support diagnostics so configuration count is not mislabeled as an independent-sample count.

`P_eval \ M3` and suitable `U_unused` data may serve as larger non-gradient reference evidence for retrospective scientific qualification when available. They are not automatic runtime fallback evaluation populations.

## 6. Canonical power-based policy

Canonical user configuration is:

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
rung_pairs = [(n1,m1),(n2,m2),(n3,m3)]
```

Required validation:

- target/evaluation powers are nonnegative integers;
- `pmin < pmax` and the current funnel has at least three configured target candidates;
- evaluation powers contain exactly three strictly increasing integers;
- fidelity boundaries contain exactly three strictly increasing positive integers;
- derived cardinalities are representable by owning integer/index/serialization types;
- there is no scientific `<=16384` guard;
- there is no non-power-of-two rescue size;
- one resolved canonical configuration is persisted with human-readable derived sizes;
- all scientifically relevant target-size fields participate in target-size policy identity;
- old fixed/flexible aliases are not silently reinterpreted in this destructive generation.

Defaults yield target candidates `128..16384` by powers of two and evaluation sizes `[256,512,1024]`.

Configured-ceiling semantics replace fixed-ceiling semantics. If the largest configured candidate remains materially superior under the final practical-equivalence rule, return typed `nonconverged_at_configured_ceiling`; do not invent a larger rescue size.

## 7. Exact target-size screening and first-class continuation mode

The three screening stages are exact boundary transitions:

```text
(n1,M1)
(n2,M2)
(n3,M3)
```

Preserve the accepted funnel:

```text
initial qualified count q
 -> coarse: all q at n1
 -> short: min(q,4) survivors at n2
 -> final: 2 finalists at n3
 -> select 1
```

with the existing minimum qualified-size requirement and paired optimizer seed semantics.

Protected continuation semantics carried from the retired exact-boundary workplans:

- `fidelity_epochs` are exact checkpoint boundaries, not generic training horizons;
- a surviving candidate continues from its exact prior boundary checkpoint; it does not restart at epoch 0;
- target-size training plans/evidence bind exact start boundary, end boundary, and continuation-checkpoint identity;
- success at an exact boundary persists/reuses the exact checkpoint;
- ordinary target-success early stopping does not terminate screening before the required boundary;
- the target-size screen continuation behavior is a first-class policy/mode, not an accidental branch of generic production/adaptive early-stop booleans;
- candidate failure/scientific failure handling remains typed and authenticated;
- EVAL2 at a stage consumes exactly the corresponding frozen `M_i`;
- all candidates/seeds at one stage use the same `M_i` identity;
- cross-rung metrics are not compared as if M1/M2/M3 were the same population;
- production epoch maximum is independent of `n3`.

No fixed cumulative evaluation-work count is architecture. Runtime/reporting may derive expected/actual inference work from resolved candidate count, seed count, survivor counts, and `M_i`; no constant such as 12,288 is a scientific capacity or workload authority.

## 8. EVAL2/OPT-EVAL4 ownership and resource preservation

Replace target-size/full-development complement population semantics with direct ladder roles:

```text
coarse       -> M1
short        -> M2
final_screen -> M3
```

Retire:

- `size_development_complement` target-size role;
- `size_development_coarse` legacy target-size role;
- maximum-training-prefix subtraction as an evaluation population definition;
- full-complement fallback;
- legacy deterministic block sampling used solely by retired generations;
- target-size domain-weighted aggregation introduced only to support multiple study domains.

Preserve the canonical EVAL2 target-force estimator and accepted staged execution/resource architecture:

```text
one parent/staged owner
 -> CPU prepare
 -> accelerator inference
 -> CPU finalize
 -> parent commit
```

The parent operator/scheduler owns aggregate admission/lifetime. Nested inference must not acquire a second aggregate RAM lease or double-charge fixed admission overhead. Preserve current batching/cache/mmap/concurrency machinery unless direct evidence requires repair.

Population identity changes; metric and execution ownership do not.

## 9. Freeze selected dataset before CV

When the target-size reducer returns `selected(N)`:

```text
N_selected = N
T_selected = pi_train[:N]
```

Both become immutable outputs of target-size selection.

`T_selected` is exactly the target dataset whose training cardinality was scientifically selected. CV must not enlarge it with `P_train \ T_selected`, `P_eval`, or `U_unused`.

The selected-size record binds:

- target-size policy/current-generation identity;
- `pi_train`/candidate-data identity;
- target/evaluation role-allocation identity;
- evaluation-ladder identity;
- exact target-size evidence/paired-seed ancestry;
- `N_selected` and `T_selected` membership digest.

## 10. CV is post-selection, group-safe validation only

### 10.1 Construction timing

CV does not exist as a target-size selection authority. Construct CV only after `N_selected` and `T_selected` freeze.

The current generation must remove any invariant that requires pre-selection CV evaluation units to cover the target-size development population.

### 10.2 Fold construction

CV consumes `T_selected` and the upstream correlation/equivalence identity associated with those selected configurations.

All selected configurations belonging to one indivisible CV correlation/equivalence group remain together when assigning fold roles. CV must not independently assign correlated selected frames to different train/evaluation/monitor roles merely because frame-level balancing is easier.

Fold cardinalities may therefore be uneven. Each CV fold naturally trains on fewer than `N_selected` configurations.

If `T_selected` contains too few independent/correlation-distinct groups to support the configured CV topology/monitor/purge policy, CV fails clearly **after** target-size selection. It does not:

- change `N_selected`;
- choose a larger/smaller target-size candidate;
- pull M3/evaluation data into training;
- re-run target allocation silently;
- weaken correlation/purge requirements.

The user/campaign must explicitly change CV policy or provide/reselect data through an appropriate new run/design boundary.

### 10.3 Validation-only contract

The training/model hyperparameters whose behavior target-size selection depends on must be frozen in the target-size scientific policy identity before candidate screening.

CV validates that already-frozen training protocol on `T_selected`. CV must not tune material training hyperparameters and then proceed to production while retaining the old `N_selected` evidence as though the training protocol were unchanged.

If CV exposes a need to change a material training scientific policy, the new policy receives a new identity and target-size evidence must be regenerated from the appropriate upstream boundary.

CV results may block final production; they do not retroactively optimize target size.

### 10.4 Dependency/identity direction

Target-size identity excludes downstream-only CV configuration such as:

- fold count;
- fold seed;
- CV monitor allocation;
- CV purge radius/policy;
- execution-only CV worker/batch settings.

Changing those values invalidates CV evidence and descendants only.

Conversely, changing a material training policy used during target-size candidate training invalidates target-size evidence and all downstream selected/CV/production state.

## 11. Fresh final production and checkpoint/model selection

Only after CV accepts the frozen selected protocol does final production begin.

Final production:

- starts fresh from the accepted initialization/foundation model rather than continuing a screening checkpoint;
- trains on the full exact `T_selected` target dataset;
- uses its independent configured production epoch maximum/adaptive production policy;
- uses the same canonical shared training lifecycle/entry point as screening/CV, with role-specific policy but one lifecycle owner;
- binds `T_selected` and current-generation provenance.

The frozen M3 population may be reused for final-development target checkpoint/model selection because it is development/model-selection evidence already consumed by target-size choice. It remains non-gradient and may not be mutated after selection.

CV continues to use fold-local validation/monitor evidence; outer/held-out validation, uncertainty calibration, and locked tests remain separate. Once M3 has influenced target size/final checkpoint selection, it must never be presented as independent held-out validation.

If a current separate common target online monitor has no independent non-selection responsibility after this consolidation, remove/merge it rather than preserve duplicate checkpoint authorities.

## 12. Shared training lifecycle and provenance

Still-valid obligations from the retired MLCV lifecycle plan become current architecture here:

- one canonical shared training entry point owns screening, CV, and final-production training;
- lifecycle is conceptually `preflight -> resource acquisition -> prepared execution -> checkpoint publication -> release`;
- direct/private/CLI bypasses must not create alternate scientific lifecycle ownership;
- training calls do not independently acquire/release resources outside the shared lifecycle owner;
- checkpoints/evidence bind authoritative target dataset, preparation, training policy, and current-generation lifecycle identity;
- CV provenance is a descendant of `T_selected`; final production provenance is a descendant of accepted CV plus `T_selected` where CV acceptance is required by campaign policy.

## 13. Persistence, restart, and destructive generation reset

This architecture is a new semantic generation. Old derived target-size state is unsupported and is not migrated.

Current persisted scientific identity must be dependency-directed.

### Target-size identity includes at least

- one `U_size` qualified-population identity;
- target/evaluation power configuration and exact fidelity boundaries;
- screening seed/aggregation and equivalence policy;
- allocation-group/correlation-equivalence policy identity;
- split-safe feature contract/allocation policy;
- `P_train`/`P_eval` role-allocation identity;
- rich target-training selector/repair/MVQUAL policy identity;
- frozen evaluation-order feature/policy/foundation identity;
- canonical training scientific policy used during screening.

### Selected-data identity adds

- `N_selected`;
- exact `T_selected` membership/order digest;
- terminal target-size evidence ancestry.

### CV identity adds, downstream only

- selected-data identity;
- CV fold/seed/monitor/purge policy;
- exact fold memberships/roles.

### Production identity adds

- selected-data identity;
- required CV acceptance identity where campaign policy requires it;
- production training budget/adaptive policy;
- final checkpoint-selection policy.

Execution-only worker/chunk/cache/batching/RAM/VRAM scheduling changes must not change scientific identity when mathematical results are unchanged.

Restart behavior must prove:

- same scientific input/config -> same allocation, orders, ladder, identities;
- target-size policy change -> target-size and downstream state invalidates;
- CV-only policy change -> target-size/selected data remain valid while CV descendants invalidate;
- production-only budget change -> target-size/CV state remains valid while production descendants invalidate as appropriate;
- restart at each screen boundary uses exact authenticated continuation checkpoint and M_i;
- no restart recomputes `pi_eval` from candidate predictions;
- pre-reset fixed/complement/domain-prefix state fails with actionable unsupported-generation error rather than migration.

Raw/external source data remain reusable.

## 14. Retired current-generation semantics to delete

Current code/docs/tests must remove or retire from reachable current execution:

- `FIXED_TARGET_SIZES` / `FIXED_TARGET_SIZE_CEILING` scientific authority;
- executable `<=16384` scientific guards;
- fixed-universe/current fixed-ceiling terminology;
- legacy candidate-authority migration/bridge/receipt code used only for superseded generations;
- current target-size `domain_prefix_digests`/per-domain candidate authority;
- per-domain target-size/evaluation ladders and reducers;
- `size_development` as an equally authoritative current target-size role where replaced by explicit pools;
- `size_development_complement` / `size_development_coarse` target-size runtime roles;
- pre-selection CV coupling into target-size role freeze/materializability/MVQUAL;
- complement subtraction/fallback evaluators;
- duplicate training entry/lifecycle owners;
- duplicate target checkpoint/model-selection roles after M3 consolidation;
- stale TARGET-SIZE-V5/fixed/flexible current-generation aliases that identify materially retired semantics;
- tests whose sole purpose is preserving retired behavior.

Historical documents/evidence remain historical; do not make executable current paths depend on them.

## 15. Part 1 — documentation/specification authority reset

Part 1 completes before executable implementation on the implementation branch. Future-state documentation must not be merged/released alone while the executable branch still implements retired semantics.

### D1. Rewrite architecture/manual authority

At minimum reconcile:

- `docs/arch_manuals/mlff_training_data/30_statistical_design.md`;
- `docs/arch_manuals/mlff_training_data/40_training_evaluation.md`;
- `docs/arch_manuals/mlff_training_data/50_target_multiview.md`;
- `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`;
- `docs/arch_manuals/mlff_training_data_architecture.md`;
- dependency graph/source maps/generated architecture inputs.

The diagrams must show exactly one target-size study and this ordering:

```text
U_size -> P_train/P_eval -> pi_train/M ladder -> select N/T_selected
       -> post-selection group-safe CV -> fresh production -> held-out stages
```

No target-size domain fan-out is allowed.

### D2. Rewrite normative specs/current user configuration

Update current specifications for:

- target subset/size-study policy;
- DATA5 target-study correlation/equivalence consumption;
- target-data role/allocation authority;
- target coverage/FEAS/MVIDX/MVSEL2/REPAIR2/MVQUAL ownership;
- EVAL2 target-size population roles;
- OPT-EVAL4 population identity while preserving execution semantics;
- post-selection CV construction/lifecycle;
- final-development checkpoint/model-selection role;
- campaign/configuration/default policy;
- persistence/restart/current semantic generation;
- DATA7/DATA8 materialization/provenance affected by the new single study identity.

### D3. Clean current terminology

Current normative/user docs must remove or rewrite:

- fixed target-size universe / fixed nominal population;
- fixed ceiling / `nonconverged_at_fixed_ceiling`;
- scientific 16,384 except as default `2^14` example;
- target-size per-domain prefix/evaluation terminology;
- `D * ...` target-size capacity/workload statements;
- pre-selection CV as part of target-size membership/materializability;
- full/coarse complement target-size evaluation;
- arbitrary percentage train/evaluation split;
- obsolete current migration/compatibility promises;
- unsupported IID claims;
- stale fixed/flexible/TARGET-SIZE-V5 generation language where it denotes retired semantics;
- alternate current selector/lifecycle/checkpoint paths.

### D4. Retire old active workplans

The implementation branch must leave `workplans/active/` with only:

- this consolidated target-size architecture workplan;
- `README.md` identifying it as the sole active implementation plan.

All other currently active plans/amendments are moved to `workplans/archive/retired-2026-08-28/` as historical records. Their still-valid obligations listed in this consolidated workplan remain protected; archived text does not independently impose active gates.

### D5. Part 1 acceptance

Part 1 closes only when:

1. current docs/specs describe one target-size study with no domain axis;
2. the nominal capacity formula is `Nmax + M3`, explicitly config-derived and group-aware as a lower bound;
3. role pools versus exact materialized sets are unambiguous;
4. CV is unambiguously downstream of `N_selected/T_selected` and validation-only;
5. CV correlation-group fold safety is specified;
6. final production occurs only after CV acceptance where CV is required;
7. current generation/config/restart semantics agree;
8. all retired terminology/current alternate authorities are removed;
9. the active workplan directory contains only this plan plus README;
10. repository-required documentation build/lint/reference/PDF checks pass on the branch.

## 16. Part 2 — implementation stages

### C1. Canonical single-study generation and configuration

Implement:

- new semantic generation/schema identities;
- canonical exponent-based target/evaluation resolver;
- configured-ceiling semantics;
- one target-size study population/head preflight;
- removal of target-size domain-prefix candidate topology;
- typed unsupported multi-target-study topology instead of silent replication.

Focused tests:

- default/nondefault powers and boundaries;
- at least three target candidates;
- no hidden 16,384 ceiling;
- exactly one target-size study identity;
- incompatible multi-head/label topology fails explicitly;
- no `domain_prefix_digests` target-size current schema;
- deterministic canonical serialization/digests.

Stage-local regression: config, label compatibility/preflight, target-size policy/state serialization, package exports.

### C2. Correlation-safe role pools and nominal-capacity preflight

Implement allocation-group closure, split-safe allocation, `P_train/P_eval/U_unused`, and group-aware feasibility.

Focused tests:

- nominal `Nmax + m3` arithmetic lower bound;
- actual group-aware failure despite nominal count when groups cannot be split safely;
- unique/scarce support goes to training;
- representative redundant support remains available for evaluation when feasible;
- `P_train`/`P_eval` group disjointness;
- pools may exceed exact configured counts;
- surplus may remain unused;
- no role reallocation after freeze.

Stage-local regression: DATA5/leakage/target-role/preflight/current-state identity.

### C3. Rich training order + frozen evaluation ladder

Route fitted preparation/FEAS/MVIDX/MVSEL2/REPAIR2/MVQUAL through `P_train`; build `pi_eval` over `P_eval` before candidate TRAIN2.

Focused tests:

- one `pi_train` only;
- exact `T_max` cardinality `Nmax`;
- configured candidate prefixes exact/nested;
- no eval/unused UID in candidate data;
- one `pi_eval` only;
- exact/nested M1/M2/M3;
- candidate predictions unavailable/forbidden to eval-order construction;
- effective-correlation/support diagnostics;
- rich failure cannot mutate role pools.

Stage-local regression: DATA6/7/8, coverage/index/selector/repair/MVQUAL/evaluation-order materialization.

### C4. Exact-boundary TRAIN2 + EVAL2 orchestration

Rebind the real target-size owner path to exact `(n_i,M_i)` stages and preserve first-class continuation semantics.

Real integration boundary:

```text
resolved target-size config/current generation
 -> single U_size preflight
 -> P_train/P_eval allocation
 -> pi_train/M ladder
 -> target-size candidate materialization
 -> TRAIN2 exact continuation
 -> exact boundary checkpoint publication
 -> EVAL2 M_i role
 -> OPT-EVAL4 staged execution
 -> reducer/survivor authorization
 -> selected/configured-ceiling terminal state
 -> T_selected freeze
```

Expensive MACE numerical stepping/inference may be bounded/faked only below these semantic owners. Tests proving orchestration must not patch/reimplement the owners themselves.

Required cases:

- default and nondefault fidelity/evaluation powers;
- changed pmin/pmax;
- paired-seed continuation exactness;
- no ordinary early stop before screen boundary;
- eliminated candidates receive no later work;
- restart at every boundary preserves exact checkpoint/M identity;
- configured-ceiling nonconvergence;
- no full-complement fallback;
- one selected dataset digest with no domain map.

Stage-local regression: target-size study, CLI/scheduler, TRAIN2/EVAL2/OPT-EVAL4, persistence/restart, DATA7/8 consumers.

### C5. Post-selection CV + fresh production

Build CV from `T_selected` only after target-size selection.

Focused tests:

- no CV plan exists/participates before selected-data freeze in the new generation;
- all selected frames from one correlation/equivalence group stay in the same CV role/fold;
- fold training subsets may be smaller/uneven;
- insufficient independent groups fails CV without changing `N_selected`;
- CV-only config changes preserve target-size/selected-data identities;
- material screening/training-policy changes invalidate target-size evidence;
- CV cannot consume M3/P_eval/U_unused as gradients;
- CV failure blocks production but does not optimize N;
- successful CV leads to fresh full-`T_selected` production from the intended initialization;
- production epoch max remains independent of `n3`;
- M3 final-development checkpoint selection is frozen/non-gradient;
- held-out/calibration/locked evidence remains separate.

Stage-local regression: CV lifecycle/roles, shared training entry, production materialization/checkpoint selection, provenance.

### C6. Resource/lifecycle reconciliation and destructive cleanup

Preserve accepted shared training and staged-evaluation resource ownership while deleting superseded paths.

Acceptance:

- one training lifecycle entry/owner;
- no duplicate acquisition/release path;
- one OPT-EVAL4 aggregate staged-job resource owner;
- no nested double RAM lease/fixed-overhead charge;
- old fixed/complement/domain-prefix/pre-selection-CV/migration paths structurally absent;
- active workplans already consolidated/retired;
- current docs/specs no longer claim retired architecture.

Run focused deletion/import/package tests plus affected regression after cleanup.

### C7. Final assembled functional acceptance

After all executable edits:

1. reconcile every frozen obligation against final source/current docs;
2. re-derive the complete affected surface from the final diff/dependency graph;
3. run complete affected regression;
4. run assembled integration across real semantic owners from config through selection, CV, and production entry;
5. run broader/full repository tests where impact cannot be bounded confidently;
6. rebuild/check affected documentation/PDF outputs;
7. perform structural authority-uniqueness and retired-path absence inspection;
8. run deterministic/reference/performance checks for changed allocation/index/selection paths;
9. report scientific M-ladder qualification status separately from functional closure and final GPU qualification.

New or plausibly affected failures block functional closure. Proven unrelated pre-existing failures may be attributed only with evidence.

## 17. Scientific qualification obligations

Functional tests establish correctness of implementation and role boundaries; they do not prove that the bounded M ladder preserves target-size decisions.

Provide a reproducible retrospective/reference qualification path using completed candidate checkpoints/predictions or bounded representative runs when available.

Assess:

1. M1 does not falsely eliminate an eventual competitive/reference finalist;
2. M2 preserves the reference finalist set;
3. M3 selects the same target size under practical-equivalence/smaller-size rules as a larger authenticated non-gradient reference population;
4. representative support/coverage of M1/M2/M3 improves where mathematically expected;
5. the coverage-selected ladder outperforms naive temporal/uniform same-cardinality baselines on important declared strata;
6. `P_train` still allows rich training/MVQUAL after carve-out;
7. train/evaluation correlation leakage is clean;
8. deterministic restart/worker/cache realization preserves scientific identities/results;
9. the assembled target-size path consumes exact `M_i` at exact `n_i`;
10. bounded evaluation materially reduces work versus the retired full-complement evaluator under the same candidate policy.

Do not use post-selection CV, locked tests, or final held-out evidence to tune M-ladder cardinalities.

If default `[256,512,1024]` fails decision preservation, revise the configured policy explicitly and requalify under a new policy identity. Never expand M silently at runtime.

If representative reference evidence is unavailable, report sampling-policy qualification as `deferred/unavailable`, not passed.

Full long real-data/GPU production/resource qualification remains deferred to the established final release/GPU phase.

## 18. Frozen implementation authority

The implementer MUST preserve:

- one target-size study only; no target-size domain dimension;
- upstream label compatibility as preflight only;
- config-derived nominal capacity `Nmax + M3` with group-aware feasibility;
- correlation/equivalence-safe authorized pools distinct from exact materialized sets;
- training priority for unique/scarce support;
- one rich training master order and exact configured prefixes;
- one nonadaptive evaluation master order frozen before candidate TRAIN2;
- exact nested M1/M2/M3 paired with n1/n2/n3;
- exact boundary continuation and first-class screen mode;
- paired seeds/practical-equivalence behavior unless separately redesigned;
- no full-complement fallback;
- `N_selected/T_selected` frozen before CV;
- group-safe post-selection CV from `T_selected` only;
- CV validation-only/no automatic target-size or hyperparameter feedback;
- CV-only policy identity downstream of target size;
- fresh final production only after accepted CV where required;
- M3 as development/model-selection evidence, never held-out validation;
- one shared training lifecycle and one-owner staged EVAL2 resource admission;
- destructive no-migration reset for old derived state;
- stage-local affected regression and final assembled integration;
- long target-machine/GPU qualification remains separate/deferred.

## 19. Delegated implementation mechanics

Implementation may choose, while preserving the frozen contract:

- exact class/module/schema names for `U_size`, role pools, allocation groups and ladder authorities;
- internal sparse/group representations;
- mathematically equivalent deterministic split-safe allocation scoring/tie details;
- whether M1/M2/M3 are separate artifacts or indexed views of one authenticated M3 artifact;
- exact new semantic-generation/version strings;
- local error-code names;
- bounded unit/integration fixture sizes and numerical doubles below real semantic owners.

Do not generalize role-specific policies merely for abstraction symmetry. Reuse common geometry/index/vector kernels where the mathematics is shared, but keep allocation, rich training qualification, evaluation representation, CV validation, and production policies semantically distinct.

## 20. Reopen only on evidence

Reopen only the affected design surface if implementation/representative evidence proves:

1. correlation/equivalence group granularity makes the one-study `Nmax + M3` architecture systematically infeasible or pathologically wasteful;
2. split-safe allocation evidence cannot protect training edge support adequately;
3. the residual evaluation pool is too biased to preserve target-size decisions at practical M sizes;
4. one-study preflight conflicts with a genuinely required current product capability for multiple incompatible target-training heads;
5. configured target sizes above the old 16,384 expose a genuine representation/algorithm limit requiring an explicit technical bound;
6. post-selection group-safe CV systematically lacks enough independent support even for otherwise scientifically valid selected data, requiring a revised CV validation design;
7. M3 reuse for final checkpoint selection conflicts with an independently required distinct development/model-selection authority;
8. default `[256,512,1024]` fails survivor/winner preservation.

A local reopen must not resurrect fixed-universe, full-complement, pre-selection-CV, automatic multi-domain, or compatibility-migration architecture by convenience.

## 21. Handoff closure

```text
stakeholder requirements:
  training-priority target-size selection
  + bounded nested evaluation
  + configurable base-2 ladders
  + nominal Nmax + M3 capacity
  + no target-size domain multiplier
  + CV only after N/T_selected freeze
  + documentation first
  + destructive cleanup and plan consolidation

accepted architecture:
  one U_size
  -> group-safe P_train/P_eval (+ optional unused remainder)
  -> one pi_train / exact T_N prefixes
  -> one frozen pi_eval / M1/M2/M3
  -> exact n1/n2/n3 target-size screen
  -> one N_selected/T_selected
  -> group-safe validation-only CV
  -> fresh final production
  -> held-out/calibration/locked stages

retired-plan obligations retained:
  exact boundary continuation + fresh production
  shared training lifecycle/provenance
  one-owner staged EVAL2 RAM/resource semantics
  DATA7/DATA8 current-generation identity
  documentation build/verification

acceptance:
  Part 1 single-authority documentation + workplan retirement
  + Part 2 staged semantic/functional closure
  + stage-local affected regression
  + final real-owner integration
  + structural absence of retired paths
  + explicit scientific sampling qualification status
```

No material reviewed design decision is intentionally delegated back to implementation discovery. Material changes to the single-study topology, role-pool boundary, `Nmax + M3` capacity semantics, nonadaptive M ladder, exact screening continuation, post-selection CV dependency direction, or destructive compatibility policy require a bounded Software Design reopen.
