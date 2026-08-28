---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P3
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 3
status: active
package_revision: 2
amended_date: 2026-08-28
entry_p1_commit: 8ccee5a1068f8481df6a3e33ddb5f09f73654391
entry_p2_commit: 7be82ccb5ff1d99e73874e3a75a7a65d4926aaee
reconciliation_reason: P1 and P2 are accepted and frozen. The original P3 package had the correct broad execution topology but predated the concrete version-agnostic P1/P2 authorities now implemented. Revision 2 aligns P3 to CanonicalFrameAuthority, NeutralStatisticalBase, TargetSizeStatisticalAggregate, TargetSizeExperimentDefinition, the qualified-candidate/reducer contract, and the existing exact TRAIN2 continuation machinery. It also closes implementation ambiguities around seed-neutral execution identity, common preparation, exact-membership DATA8 materialization, direct-M EVAL2 correlation blocks, authenticated TRAIN2/EVAL2 outcome translation, and restart ownership. The frozen parent workplan remains the verdict and is not reopened.
---

# P3 — Candidate execution and paired-seed screen

## Purpose

Connect the accepted P1/P2 scientific authorities to the existing shared DATA7/DATA8/MACE/TRAIN2/EVAL2 execution machinery **without recreating retired label-domain, pre-target CV, candidate-complement, or multi-authority target-size semantics**.

P3 owns the execution bridge only:

- one deterministic common preparation for the whole target-size study;
- one seed-neutral target-size execution context bound immutably to the accepted P2 experiment;
- exact materialization of qualified `T_N` candidates for the ordered optimizer seeds;
- exact `n1 -> n2 -> n3` TRAIN2 continuation;
- direct evaluation on exact P2 `M1/M2/M3` memberships;
- authenticated translation of real TRAIN2/EVAL2 evidence into the P2 boundary-evidence types;
- scheduling/orchestration that follows, but does not duplicate, the P2 reducer;
- P3-local durable restart/authentication sufficient to prove the execution graph before P4 makes it current campaign state.

P3 does **not** own target-size policy, candidate qualification, `pi_train`, `pi_eval`, survivor ranking, practical-equivalence decisions, selected-size authority, post-selection CV, current CampaignStore generation, or CLI/runtime cutover.

The new execution path remains internal/unreachable from ordinary production `prepare`, `select-target-size`, `train`, and `evaluate` orchestration until the atomic P4 cutover.

All new durable product classes, functions, schemas, record names, and symbols introduced by P3 must be **version-agnostic**. `V7` is workplan/generation metadata only.

## Governing authority and accepted entry state

The frozen parent workplan remains the sole architecture/scientific verdict:

`workplans/active/MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md`

P3 starts from the accepted implementation graph:

```text
P1 CanonicalFrameAuthority + NeutralStatisticalBase
  -> P2 TargetSizeStatisticalAggregate
       policy
       population / P_train-M3 split
       TargetSizeExperimentDefinition
         one pi_train
         one pi_eval
         exact T_N and M1/M2/M3 membership identities
         derived candidate qualification
       TargetSizeReducerState
         status = awaiting_execution_context
  -> P3 common preparation
  -> P3 seed-neutral execution context
  -> bind_target_size_execution_context(...)
  -> exact candidate trajectories using shared DATA8/TRAIN2/EVAL2 owners
  -> TargetSizeBoundaryMetric / TargetSizeNumericalFailure
  -> advance_target_size_reducer(...)
```

Frozen consequences of the accepted P2 implementation:

- only `definition.qualified_candidate_sizes` may enter ordinary screening execution;
- exact target membership comes only from `definition.candidate_membership(N)`;
- exact evaluation membership comes only from `definition.evaluation_membership(M)`;
- the ordered replicate set comes only from `definition.policy.optimizer_seeds`;
- the active rung and active candidate set come only from `TargetSizeReducerState`;
- reducer outcome order is size-major then seed-minor in the exact P2 order;
- `bind_target_size_execution_context()` is the authority that makes execution evidence admissible;
- `advance_target_size_reducer()` is the only target-size survivor/ranking/terminal decision owner;
- `selected_target_size` and `selected_membership_digest` are P2 reducer outputs, not independently writable P3 claims.

Do not replace these APIs with a P3-local equivalent simply because the execution layer needs convenient state.

---

## Protected concerns

P3 must preserve all of the following simultaneously:

- `N` remains the sole target-size data-cardinality variable;
- P1/P2 scientific identity and split/qualification semantics remain unchanged;
- one common deterministic fitted preparation is reused across all N and optimizer seeds;
- seed is the only stochastic replicate dimension and the same ordered seeds are used for every N;
- a candidate trajectory is continuous across `n1 -> n2 -> n3`; later rungs are not fresh jobs scientifically;
- target-size MACE validation required only by the training harness is fixed and non-controlling;
- only direct EVAL2 on the exact active P2 `M_i` membership can produce the ranking metric;
- EVAL2 correlation blocks preserve the full P1 split-exclusion/correlation closure rather than falling back to retired DATA5 label-domain/unit semantics;
- TRAIN2/EVAL2 numerical failures are converted to scientific failure evidence only when positively authenticated by the real owner;
- ordinary input, lineage, programming, subprocess, resource, filesystem, and orchestration failures remain execution errors;
- P3 orchestration follows the P2 reducer state and never maintains a second survivor/ranking authority;
- current DATA8/TRAIN2 caching, staging, checkpointing, acceleration, resource scheduling, and optimized EVAL2 reductions are reused where semantically valid;
- P3 does not make the new architecture reachable from current production commands;
- full long GPU/real-production qualification remains deferred to final release; bounded functional/resource validation remains required.

---

## P3-A — common deterministic preparation and seed-neutral execution context

### A1. Extract the training-relevant common preparation from legacy DATA7 topology

The current `Data7PreparationBundle` is not itself the new target-size common-preparation authority because it embeds legacy `FeatureFitDomain` ownership and a DATA7 selection plan. Current `FeatureFitDomain` is label-domain/CV scoped, while P2 already owns target-size ordering and candidate membership.

Implement one version-agnostic common-preparation authority for target-size execution. Exact naming is delegated; semantics are frozen.

It is built **once per P2 experiment** from the accepted common training-side population, normally `P_train`, and contains only training-relevant fitted state actually consumed by target-size materialization/training, as applicable:

- exact common input-membership identity;
- atomic-reference/E0 policy and fitted result;
- objective/property/configuration-weight policy and deterministic per-frame weights;
- any normalization/fitted preprocessing genuinely consumed by the training engine;
- feature/projection fit and its fixed numerical seed only if that fitted state is genuinely consumed downstream;
- foundation/head identity needed by the fit;
- replay source/exposure policy inputs needed by common preparation;
- checkpoint/metric policy inputs that are common scientific training context.

Do **not** preserve an obsolete selection/coverage object merely to imitate `Data7PreparationBundle`. P2 already owns `pi_train`. Product simplicity is preferred after the required training semantics are preserved.

The common-preparation fit may consume P1/P2-authorized training-side data but must not consume:

- `M1/M2/M3` labels or predictions;
- optimizer seed;
- candidate N or candidate outcomes;
- CV folds or CV evaluation;
- outer held-out/calibration/locked evidence;
- compatibility/label-domain grouping as a scientific fit axis.

No candidate-specific E0, normalization, objective, or configuration-weight refit is permitted. Per-candidate materialization may **project/subset already-frozen per-frame common results** onto `T_N`; that is not a refit.

If a real MACE/training mathematical requirement proves that a fitted quantity must change with N, stop the dependent work and reopen only that parent decision. Do not hide N-dependent fitting inside an old domain API.

### A2. Define one seed-neutral execution context

Implement one canonical version-agnostic target-size execution-context authority and bind its `content_digest` to the P2 reducer through `bind_target_size_execution_context()` before any ordinary boundary evidence can be accepted.

The execution context is the immutable study-wide identity of the scientific execution protocol. It must bind, at minimum:

- `TargetSizeExperimentDefinition.content_digest`;
- common-preparation digest;
- foundation/source-potential and selected-head identity;
- replay preparation/exposure identity;
- seed-neutral optimizer/training-policy template;
- screen training-budget and LR-schedule policy identity;
- objective/weight/E0/common-fitted-preparation identity;
- precision/backend/batch/exposure semantics;
- TRAIN2 checkpoint/continuation policy;
- EVAL2 target metric/reduction policy;
- fixed non-controlling MACE harness-validation identity;
- genuine MACE compatibility/source-probe constraints required for mechanical execution.

The study-wide context must **exclude candidate-varying or execution-only state**:

- N and exact `T_N` artifact digest;
- individual optimizer seed;
- active rung/boundary;
- current survivor set;
- candidate checkpoint/result identity;
- CV fold configuration/results;
- worker count, process count, GPU allocation, queue order, telemetry, wall time, output path;
- fresh-final-production-only settings such as the independent production horizon.

Because the current `MaceOptimizerPolicy` contains `seed`, do not use a candidate-specific optimizer-policy digest as the global seed-neutral context. Define/derive one canonical seed-neutral training-policy identity and require every candidate optimizer policy to equal that template except for the authorized seed and N-consequential runtime quantities.

The actual screening seed set must equal `definition.policy.optimizer_seeds` exactly and in order. A changed seed set is a P2 scientific-policy change, not a P3-local override.

### A3. Freeze one full-screen TRAIN2 schedule

The screen has one full trajectory ceiling `n3 = definition.policy.fidelity_epochs[2]`.

For each `(N, seed)` trajectory:

- derive one TRAIN2 budget/LR trajectory whose full screen budget ends at n3;
- preserve that same full-budget policy through all rungs;
- use `Train2RuntimePlan.execution_epoch_limit` (or the semantically equivalent existing pause mechanism) as `n1`, then `n2`, then `n3`;
- never construct independent n1/n2/n3 LR schedules or restart a survivor under a newly normalized later-rung schedule.

The screen-specific n3 budget is distinct from the fresh final-production horizon. Current/default final production may remain 30 epochs; changing that production-only horizon must not alter P2 target-size identity or a completed screen.

### A verification cycle

Before P3-B:

1. common-preparation focused tests prove one digest/results across all N and seeds;
2. negative tests reject M-ladder/CV/held-out/seed/candidate-outcome inputs to common fitting;
3. seed-neutral execution-context identity tests prove seed/N/worker/path differences do not alter the global context while a genuine common training-policy/preparation change does;
4. exact seed-set equality with the P2 policy is enforced;
5. screen-budget tests prove full n3 schedule + rung execution limits and independence from production-only horizon;
6. run affected DATA7/reference-fit/objective/weight/TRAIN2-policy regression;
7. preserve P1/P2 focused regression for any shared helper or identity surface changed in this pass.

---

## P3-B — exact-membership candidate materialization through shared DATA8 machinery

### B1. Do not use the legacy production materialization plan as P3 authority

Current `ProductionMaterializationPlan` still contains legacy domain/CV target-size fields such as `domains`, `cross_validation_plans`, `selection_size`, prescribed per-domain prefixes, and prescribed target-size evaluation cohorts. It is therefore not the new P3 scientific object.

P3 may reuse/refactor its cache, restart, staging, atomic-promotion, and resource-safe execution mechanisms, but it must not preserve the old target-size topology behind renamed fields.

### B2. Introduce one exact candidate-trajectory identity

Each target-size trajectory is identified by the accepted parents and exact candidate facts, including:

```text
experiment-definition digest
execution-context digest
N
exact candidate-membership digest
exact T_N frame membership
optimizer seed
seed-neutral training-protocol identity
common-preparation digest
replay/foundation identity
```

Only qualified N values may be instantiated. Exact membership must equal `definition.candidate_membership(N)` and its P2 membership digest. A P3 caller may not supply an alternative same-sized list.

There is one scientific trajectory per required `(N, optimizer_seed)`, not one independent trajectory per rung. Rung execution records descend from the trajectory and add active boundary/continuation ancestry; they do not redefine candidate identity.

### B3. Extract/refactor an exact-membership DATA8/MACE materialization primitive

Current `build_data8_preparation_bundle()` is legacy-scoped: it requires one label domain, final/CV DATA7 bundles, old MLCV roles, selection-ladder lookup, and optional complement-style target-size evaluation. P3 must not enter through that topology.

Refactor/extract the smallest generic version-agnostic DATA8/MACE job builder that accepts explicit exact target-training membership and the common preparation, while reusing existing proven mechanisms for:

- immutable fixed-file/cache recipes;
- exact ExtXYZ materialization;
- replay staging and weight scaling;
- foundation/selected-head staging;
- MACE YAML generation and source/loader dry-run;
- acceleration/precision policy;
- `TrainingProtocolIdentity` / MACE job artifact mechanics where their semantics remain valid;
- atomic file/tree publication and resource-safe cache behavior.

The exact-membership primitive must not require or synthesize:

- `label_domain_id` as target-size scientific authority;
- CV plans/fold lists;
- DATA7 selection ladder or `selection_size` lookup;
- prescribed per-domain prefixes;
- development-complement target evaluation;
- target-size evaluation membership derived from training membership.

The legacy builder may temporarily call shared low-level primitives while the old runtime remains current until P4. Do not make P3 call the legacy top-level builder in a special mode that reconstructs the retired topology.

### B4. Fixed MACE harness validation is explicitly non-controlling

If MACE requires `target_valid`, construct one deterministic fixed harness-only diagnostic input from target-training-side authorized data. It must be identical across N and seeds under the same execution context and must not impose a new capacity requirement.

It is permitted to overlap training-side data because it is not statistical target-size evidence; no new disjoint population should be invented solely to satisfy the harness. Its role must be explicit and non-controlling:

- no gradients;
- no LR-schedule mutation;
- no ordinary/generic early stop;
- no checkpoint/survivor/ranking authority;
- no M1/M2/M3, outer held-out, calibration, or locked evidence routed through it.

Only exact boundary EVAL2 on the P2 M rung may create target-size ranking evidence.

### B verification cycle

1. exact `T_N` membership/digest tests through the real candidate/materialization owner;
2. unqualified N and alternative-same-size membership rejection;
3. one trajectory identity per `(N, seed)` and no rung-as-new-trajectory drift;
4. materialized MACE YAML contains the exact authorized optimizer seed and target train artifact;
5. structural absence checks for label-domain/CV/selection-ladder/complement fields on new P3 durable objects;
6. harness-validation fixed/non-controlling tests;
7. cache/restart/serialization/atomic-promotion regression for refactored shared DATA8 mechanics;
8. affected DATA8/MACE compatibility and fixed-file regression.

---

## P3-C — paired-seed TRAIN2 execution and exact continuation

Use the existing `train2_runtime.py` continuation machinery rather than creating another checkpoint engine. It already persists/authenticates live parameters, EMA state, RNG state, raw checkpoint identity, optimizer-state reference, completed updates, and LR progress, and supports a bounded `execution_epoch_limit` inside one frozen budget.

For each active candidate in P2 reducer order and every optimizer seed in exact P2 order:

- seed the real MACE optimizer/training configuration with the authorized optimizer seed;
- run the trajectory from initialization to n1;
- if it survives, resume the exact n1 state to n2;
- if it survives, resume the exact n2 state to n3;
- restore/authenticate model/live parameters, optimizer checkpoint state, EMA state when enabled, RNG state, completed updates, and LR/schedule progress;
- never restart a later rung from the foundation or epoch zero;
- never reinitialize RNG merely because a new orchestration invocation resumes the trajectory;
- ordinary generic target-success early stopping must not truncate an exact screen boundary;
- eliminated candidates receive no later **ordinary** screening work.

The contract is same seed and same stochastic policy across N, not byte-identical RNG consumption across different dataset cardinalities.

Continuation acceptance must bind each later-rung request to the exact predecessor trajectory/checkpoint/companion. A valid checkpoint from another N, seed, execution context, training protocol, or boundary is foreign even if tensor shapes happen to match.

### C numerical-failure translation

Do not classify scientific numerical failure from stderr text or nonzero exit status.

Translate only authenticated real TRAIN2 numerical-failure records into P2 `TargetSizeNumericalFailure`:

- `train_nonfinite_model_state` -> `TRAIN_NONFINITE_MODEL_STATE`;
- current `train_nonfinite_ema_state` also maps to the P2 model-state category because EMA is persisted model/checkpoint state, **not** optimizer state; preserve the original authenticated TRAIN2 record/code through `classification_evidence_digest` or equivalent bound evidence;
- `TRAIN_NONFINITE_OPTIMIZER_STATE` may be emitted only when the real TRAIN2 owner positively authenticates a non-finite optimizer-state failure; do not relabel EMA or a generic subprocess failure as optimizer failure.

Any ordinary MACE/configuration/schema/lineage/resource/filesystem/process/programming failure remains an execution error and does not enter the P2 reducer as scientific candidate failure.

### C verification cycle

1. real TRAIN2 runtime-plan tests prove one full n3 schedule with n1/n2/n3 pause limits;
2. exact model/optimizer/EMA/RNG/completed-update/LR ancestry tests;
3. interrupted-resume and restart-after-boundary tests through the real continuation loader/runtime owner;
4. wrong N/seed/context/protocol/predecessor checkpoint rejection;
5. generic early-stop/control-path negative tests;
6. authenticated numerical-failure mapping tests, including EMA-not-optimizer and generic-error-not-scientific cases;
7. affected TRAIN2 scheduler/checkpoint/resource regression.

---

## P3-D — direct-M EVAL2 authority with inherited P1 correlation blocks

### D1. Replace the legacy EVAL2 target-size role, not the metric engine

Current `Eval2TargetRole` is legacy target-size/CV state: it carries label-domain authority, old role-freeze lineage, complement/coarse role kinds, excluded training membership, and fold state. It is not the P3 target-size role.

Introduce/refactor one version-agnostic direct target-size EVAL2 role whose identity binds:

- P2 experiment-definition digest;
- P3 execution-context digest;
- active boundary epoch and evaluation size;
- exact P2 evaluation-membership digest;
- exact `definition.evaluation_membership(M_i)` frame UIDs;
- one correlation-block identity per evaluation frame from the accepted P1 split-exclusion/correlation authority.

It must contain no label-domain, CV-fold, development-complement, coarse-fallback, or excluded-training-prefix semantics.

Reuse the existing EVAL2 target metric calculations, force reductions, numerical guards, cache/indexing machinery, correlation-block reductions, and optimized inference/resource path after replacing the population/role authority.

### D2. Correlation blocks must use the same complete P1 closure as P2

P2 now splits `P_train/M3` using the complete canonical `NeutralSplitExclusionEvidence` closure: correlation units, exact geometry duplicates, protected events, replica lineage, structural realization lineage, and transitive chains among them.

EVAL2 must not regress to a narrower block definition such as legacy DATA5 unit IDs alone.

Refactor the existing P2 private component construction only as much as necessary so there is **one canonical component-projection implementation** reusable by both:

- P2 exact split construction; and
- P3 EVAL2 correlation-block assignment.

The shared helper may be owned with the P1 split-exclusion evidence or a neutral shared P2 utility; exact placement/name is delegated. Frozen semantics:

- no duplicate component algorithm in P3;
- P2 split behavior/content remains scientifically unchanged;
- each M3 frame receives the identity of its full M3/P1 split-exclusion component;
- M1/M2 retain those parent M3 component identities rather than recomputing a smaller-prefix component name, so correlation identity is stable across the nested ladder.

Because this is a shared-owner extraction from accepted P2 behavior, run the complete affected P2 split/restart regression after the refactor.

### D3. Convert only authoritative EVAL2 output

A successful direct-M EVAL2 boundary produces a P2 `TargetSizeBoundaryMetric` only when all of the following bind exactly:

- experiment-definition digest;
- execution-context digest;
- N and optimizer seed of the evaluated checkpoint trajectory;
- active boundary epoch;
- exact P2 M-rung membership digest;
- target force RMSE with the P2-required `meV/A` units.

Authenticated EVAL2 numerical failures map losslessly:

- non-finite energy/force/stress prediction failures -> `EVAL_NONFINITE_PREDICTION`;
- non-finite target metric -> `EVAL_NONFINITE_TARGET_METRIC`;
- original EVAL2 failure record/code is bound by the classification-evidence digest.

Schema/shape/lineage/missing-artifact/programming/resource failures are execution errors, not numerical target-size evidence.

### D verification cycle

1. exact M1/M2/M3 role membership and membership-digest tests;
2. stable full-component correlation-block mapping across M1/M2/M3;
3. mixed-relation component tests proving relation chains beyond neutral unit IDs remain one EVAL2 block;
4. negative tests against complement/coarse/CV-role fallback and M-ladder use as generic MACE validation;
5. reference-equivalence tests for retained EVAL2 metric/block reductions;
6. EVAL2 numerical-failure translation and ordinary-error separation tests;
7. affected EVAL2 inference/cache/resource regression plus affected P2 component/split regression.

---

## P3-E — reducer-following orchestration and P3 restart integrity

### E1. P2 reducer remains the sole decision owner

Implement one internal P3 screen coordinator that is deliberately **not** a second ranking state machine.

For each iteration it must:

1. load/validate the current P1/P2 aggregate and bound execution context;
2. read `reducer_state.status` and `reducer_state.active_candidate_sizes`;
3. derive the active boundary from P2 reducer status/policy;
4. schedule only those active N values, each with the exact ordered P2 optimizer seeds;
5. materialize/resume the corresponding candidate trajectories;
6. evaluate the exact active M rung;
7. construct authenticated P2 boundary outcomes in the exact required insertion order:

```text
for N in reducer_state.active_candidate_sizes:
    for seed in definition.policy.optimizer_seeds:
        emit outcome(N, seed)
```

8. call `advance_target_size_reducer(definition, reducer_state, outcomes)` exactly once for the complete boundary batch;
9. persist the returned reducer state through the P2 aggregate owner;
10. stop when the P2 reducer is terminal.

P3 must not:

- independently average seeds;
- independently sort scores;
- independently apply practical equivalence;
- independently decide survivors/finalists;
- maintain a second authoritative active-candidate table;
- reorder an otherwise complete evidence matrix before calling P2;
- accept partial successful seeds and average a subset;
- fabricate `N_selected/T_selected` separately from the P2 reducer terminal state.

Execution queues/checkpoints may cache derived work status for recovery, but after restart they must reconcile to the authoritative P2 reducer and trajectory lineage. Queue state cannot override scientific state.

### E2. P3-local durable execution record before P4

P3 must prove restart integrity while remaining outside current CampaignStore generation. Implement the smallest version-agnostic durable execution record/aggregate needed to authenticate:

- accepted P2 statistical aggregate identity and current reducer state;
- execution-context identity;
- common-preparation identity;
- candidate trajectory identities;
- materialized DATA8/MACE artifact identities;
- exact TRAIN2 continuation ancestry and runtime summaries/companions;
- direct-M EVAL2 evidence identities;
- which execution work is complete/reconstructible versus pending.

Do not create a second copy of P2 policy/order/reducer scientific state. Persist references/bindings to P2 authority and validate/replay through P2 owners.

On P3 restart/reopen:

- reconstruct/validate P1 owners first;
- deserialize/re-derive the P2 aggregate through its real owner;
- verify the bound execution context still matches the P2 definition and common training protocol;
- verify each materialized candidate membership is exactly the P2 `T_N`;
- verify checkpoint continuation ancestry and boundary identity;
- verify EVAL2 evidence points to the exact active M membership;
- replay/validate P2 reducer history through `validate_target_size_reducer_state()`;
- reject stale or coordinated-rehash state rather than silently repairing scientific authority.

CampaignStore/SQLite current-generation persistence and destructive old-generation rejection remain P4 responsibilities. P3 should not prematurely switch current receipt/state keys.

### E3. Invalidation expectations

At P3 level, changed state must fail/rebuild according to actual dependency direction:

- changed P1/P2 experiment definition -> all bound P3 execution evidence is stale;
- changed hard-support qualification/order/split/evaluation ladder/fidelity/seed set -> stale bound execution rejected through changed P2 definition/context;
- changed common preparation or seed-neutral training protocol -> execution-context digest changes; old candidate evidence rejected;
- changed candidate N membership -> only an exact P2-derived candidate can be rematerialized;
- changed optimizer seed outside the frozen P2 seed set -> reject;
- changed execution-only worker/resource/telemetry settings -> do not change scientific execution context unless they alter an accepted scientific execution policy;
- changed CV-only configuration or fresh-final-production horizon -> must not invalidate an already valid target-size screen.

### E verification cycle

1. coordinator structural/source tests prove P2 reducer APIs are the sole ranking/survivor decision calls;
2. exact outcome-order tests and negative reordered/missing/duplicate/foreign-seed tests through the real P2 reducer;
3. eliminated-candidate-no-later-ordinary-work scheduling tests;
4. selected state comes only from P2 reducer terminal output;
5. restart after each rung through the real P3 record + P2 aggregate deserializer;
6. stale context/preparation/candidate/seed/boundary/continuation/evaluation evidence rejection;
7. execution-only resource-setting invariance and CV/production-only setting isolation;
8. affected P1/P2 restart/regression tests for every shared owner touched.

---

## P3-F — assembled closure and acceptance

Run one bounded end-to-end paired-seed target-size screen through the **real semantic owners**:

```text
P1 CanonicalFrameAuthority + NeutralStatisticalBase
 -> P2 TargetSizeStatisticalAggregate
 -> common target-size preparation
 -> bind seed-neutral execution context
 -> qualified active T_N trajectories
 -> exact-membership DATA8/MACE materialization
 -> TRAIN2 to n1
 -> direct EVAL2 on M1
 -> P2 reducer
 -> exact TRAIN2 continuation to n2
 -> direct EVAL2 on M2
 -> P2 reducer
 -> exact TRAIN2 continuation to n3
 -> direct EVAL2 on M3
 -> P2 terminal reducer state
 -> exact N_selected / T_selected digest
 -> P3 restart/reopen reproduces the same accepted state
```

The fixture may use reduced candidate/evaluation sizes and very short bounded scientific computation. Expensive neural-network training/inference may be faked **below** the real materialization/TRAIN2/EVAL2 orchestration and state-owner boundaries. Acceptance may not monkeypatch/reimplement:

- P1/P2 aggregate construction/restart;
- P3 common-preparation/execution-context owner;
- exact candidate materialization ownership;
- TRAIN2 continuation state machine;
- direct-M EVAL2 role/metric owner under test;
- P2 reducer transitions;
- P3 restart/reconciliation logic.

A test that seeds post-decision reducer state or calls a helper while bypassing the owning coordinator/restart path does not close the corresponding integration claim.

### Required final regression surface

After all P3 executable edits, re-derive the actual affected surface and run, at minimum:

- complete P3 focused suite;
- complete affected P2 target-size statistical/reducer/restart suite;
- affected P1 neutral split-exclusion/statistical restart suite when component mapping/shared relation helpers changed;
- affected DATA7 reference-fit/objective/weight/common-fit tests;
- affected DATA8 fixed-file/cache/materialization/MACE-config/compatibility tests;
- affected TRAIN2 runtime, continuation, numerical-failure, scheduler/resource tests;
- affected EVAL2 metric/reduction/cache/numerical-failure tests;
- bounded P1 -> P2 -> P3 end-to-end integration on the assembled candidate;
- repository-required import/package/static/Python checks.

If implementation broadens the affected surface beyond these owners, broaden regression accordingly. Green focused tests do not excuse affected integration/regression.

No full long GPU/real-production qualification is required in P3. Do not infer production-scale throughput/VRAM conclusions from bounded functional tests.

---

## Implementation authority

### Frozen

Implementation must preserve:

- the frozen parent V7 architecture and accepted P1/P2 scientific semantics;
- version-agnostic durable P3 product naming;
- one common deterministic training-relevant preparation;
- one seed-neutral execution context bound once to P2;
- exact P2-qualified `T_N` memberships and ordered optimizer seeds;
- one scientific trajectory per `(N, seed)` with exact n1->n2->n3 continuation;
- one full-screen n3 TRAIN2 schedule, with rung limits implemented as continuation pauses;
- shared DATA8/MACE/TRAIN2 machinery rather than a second training engine;
- fixed non-controlling harness validation separate from M1/M2/M3;
- direct exact-M EVAL2 population authority;
- EVAL2 correlation blocks derived from the complete inherited P1 split-exclusion closure through one shared component implementation;
- authenticated, lossless TRAIN2/EVAL2 -> P2 outcome translation;
- P2 reducer as sole ranking/survivor/terminal authority;
- durable P3 restart validation while current CampaignStore/CLI cutover remains deferred to P4;
- stage-local affected regression and fresh final assembled regression/integration;
- no routine full GPU/production qualification.

### Delegated

Implementation may choose:

- exact class/module/schema names for common preparation, execution context, candidate trajectory, direct-M EVAL2 role, and P3 execution record, provided names are version-agnostic;
- whether the shared split-exclusion component projection helper is owned in the neutral-substrate relation module or a neutral target-size utility, provided P2 and P3 use the same implementation;
- how much of legacy DATA7/DATA8 code is extracted versus internally parameterized, provided the new P3 path does not reconstruct old scientific topology;
- exact fixed harness-validation sampling policy from authorized training-side data, provided it is deterministic, study-wide, non-controlling, and adds no new capacity requirement;
- exact artifact directory layout and reconstructible queue/telemetry representation;
- bounded fake boundary below the real semantic owners for expensive MACE work;
- local refactors needed to preserve cache/resource machinery without changing scientific identity.

### Forbidden shortcuts

Implementation may not:

- use old `FeatureFitDomain` label-domain/CV identity as the new common-preparation scientific owner;
- call old target-size `ProductionMaterializationPlan`/`build_data8_preparation_bundle()` through a disguised label-domain/complement mode and claim P3 is current-generation;
- derive candidate membership from DATA7 selection ladders or `selection_size` rather than P2 `T_N`;
- use M1/M2/M3 as MACE generic validation/early-stop data;
- construct EVAL2 target-size roles by subtracting training membership from development data;
- use only legacy neutral unit IDs as correlation blocks when the accepted P1 relation closure merges them into a larger dependency component;
- create independent n1/n2/n3 training budgets that renormalize the trajectory at each rung;
- classify EMA non-finiteness as optimizer-state failure;
- classify stderr/resource/programming failures as scientific numerical failures;
- maintain a P3-local ranking/survivor/selected-N authority in parallel with P2;
- make current CLI/CampaignStore target-size runtime partially switch before P4;
- retain old architecture merely to keep obsolete tests green.

### Reopen only on evidence

Reopen only the smallest affected parent/P1/P2 decision if implementation demonstrates one of these conditions with real-owner evidence:

- a mathematically required training fit/normalization must depend on N and cannot be represented as projection of common fitted state;
- MACE/TRAIN2 cannot resume the accepted exact full-trajectory model/optimizer/RNG/LR state at a later fidelity boundary using the qualified existing continuation machinery;
- a fixed non-controlling harness validation input cannot satisfy a demonstrated MACE mechanical requirement without introducing scientific control;
- the complete P1 split-exclusion relation closure cannot supply stable EVAL2 block identities without changing accepted P1/P2 split semantics;
- a required EVAL2 target-force metric cannot be computed on direct exact-M roles without materially changing the retained metric engine;
- the P2 boundary evidence/reducer contract is insufficient to represent a positively authenticated real execution outcome without lossy or false classification.

Do not reopen merely because legacy APIs are inconvenient; refactor the legacy execution seam instead.

---

## Implementation sequence and package gates

Implement in this dependency order:

1. **P3-A:** common preparation + seed-neutral execution context + full-screen TRAIN2 policy.
2. **P3-B:** exact candidate trajectory + generic exact-membership DATA8/MACE materialization seam.
3. **P3-C:** paired TRAIN2 execution, exact continuation, authenticated TRAIN2 failure adapter.
4. **P3-D:** shared P1/P2 component projection + direct-M EVAL2 role + EVAL2 outcome adapter.
5. **P3-E:** reducer-following coordinator + durable P3 restart/reconciliation.
6. **P3-F:** final assembled conformance review, complete affected regression, bounded end-to-end integration.

Each executable stage closes only after both semantic/conformance inspection and the relevant focused + affected regression pass. Do not defer all regression until P3-F.

## Exit gate

P3 is accepted only when:

> The accepted P1/P2 experiment can execute a complete paired-seed `n1/M1 -> n2/M2 -> n3/M3` screen through shared production DATA8/TRAIN2/EVAL2 machinery using exact P2 memberships, one common preparation, one immutable seed-neutral execution context, exact continuation, complete inherited correlation blocks, authenticated outcome translation, and the P2 reducer as the sole decision authority; the entire P3 execution state restarts deterministically, and the new path remains unreachable from current production CLI/CampaignStore orchestration until P4.

Commit/tag the accepted P3 checkpoint before P4. Do not begin P4 while P3 still relies on a legacy label-domain/CV/complement target-size execution seam or a duplicate screening decision authority.
