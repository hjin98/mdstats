---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P3
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 3
status: active
package_revision: 3
amended_date: 2026-08-28
entry_p1_commit: 8ccee5a1068f8481df6a3e33ddb5f09f73654391
entry_p2_commit: 7be82ccb5ff1d99e73874e3a75a7a65d4926aaee
reviewed_revision_2_commit: 32547c427b61ff36ca54b2f436503df1f866329b
review1_amendment_commit: b9b4739ef499aee54033c22c6961c8e8d18a13ef
reconciliation_reason: Revision 3 consolidates the accepted P3 revision-2 contract and Review-1 execution-boundary/restart amendment into one lossless implementation workplan. P1 and P2 remain accepted and frozen. The frozen parent workplan remains the sole scientific and architectural verdict and is not reopened.
---

# P3 — Candidate execution and paired-seed screen

## 1. Purpose and package boundary

Connect the accepted P1/P2 scientific authorities to the existing shared DATA7/DATA8/MACE/TRAIN2/EVAL2 execution machinery **without recreating retired label-domain, pre-target CV, candidate-complement, or multi-authority target-size semantics**.

P3 owns the execution bridge only:

- one canonical deterministic common preparation for the whole target-size study;
- exact projection of that common fitted state onto each accepted `T_N` without candidate refitting or renormalization;
- one seed-neutral target-size execution context bound immutably to the accepted P2 experiment;
- one authenticated candidate realization per required `(N, optimizer_seed)`;
- exact current-generation materialization of qualified `T_N` candidates through shared DATA8/MACE mechanics;
- exact `n1 -> n2 -> n3` TRAIN2 continuation;
- direct evaluation of the exact authenticated boundary checkpoint on exact P2 `M1/M2/M3` memberships;
- authenticated translation of real TRAIN2/EVAL2 evidence into P2 boundary-evidence types;
- complete-boundary, crash-consistent, idempotent reducer application;
- P3-local durable restart/authentication sufficient to prove the execution graph before P4 makes it current campaign state.

P3 does **not** own:

- target-size policy or candidate qualification;
- `pi_train`, `pi_eval`, or `T_N`/`M_i` membership construction;
- seed aggregation, survivor ranking, practical-equivalence decisions, or selected-size authority;
- post-selection CV;
- fresh final-production training;
- current CampaignStore/SQLite generation;
- public CLI/runtime cutover.

The new execution path remains internal/unreachable from ordinary production `prepare`, `select-target-size`, `train`, and `evaluate` orchestration until the atomic P4 cutover.

All new durable product classes, functions, schemas, record names, and symbols introduced by P3 must be **version-agnostic**. `V7` is workplan/generation metadata only.

---

## 2. Governing authority and accepted entry state

The frozen parent workplan remains the sole architecture/scientific verdict:

`workplans/active/MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md`

Accepted P1 and P2 are frozen entry authorities. P3 starts from:

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
  -> exact candidate realizations/materialization
  -> TRAIN2 exact boundary continuation
  -> direct exact-checkpoint EVAL2 on M_i
  -> complete ordered boundary batch
  -> advance_target_size_reducer(...)
  -> atomic P3 execution head / restart reconciliation
```

Frozen consequences of accepted P2:

- only `definition.qualified_candidate_sizes` may enter ordinary screening execution;
- exact target membership comes only from `definition.candidate_membership(N)`;
- exact evaluation membership comes only from `definition.evaluation_membership(M)`;
- the ordered replicate set comes only from `definition.policy.optimizer_seeds`;
- the active boundary and active candidate set come only from `TargetSizeReducerState`;
- reducer outcome order is exact size-major, seed-minor P2 order;
- `bind_target_size_execution_context()` is the authority that makes execution evidence admissible;
- `advance_target_size_reducer()` is the sole target-size survivor/ranking/terminal decision owner;
- `selected_target_size` and `selected_membership_digest` are P2 reducer outputs, never independent P3 claims.

Do not replace these APIs with P3-local equivalents for convenience.

---

## 3. Protected invariants

P3 must preserve all of the following simultaneously:

- `N` remains the sole target-size data-cardinality variable;
- P1/P2 scientific identity, split, qualification, order, and reducer semantics remain unchanged;
- one common deterministic fitted preparation is computed once and reused across all N and optimizer seeds;
- candidate preparation is exact selection/projection from common fitted state, never an N-specific refit;
- seed is the sole stochastic replicate dimension and the same ordered seeds are used for every N;
- one candidate trajectory is continuous across `n1 -> n2 -> n3`; later rungs are not fresh scientific jobs;
- P2 fidelity values are completed-epoch counts; exact boundary model state is the only screening checkpoint;
- target-size MACE harness validation is fixed and non-controlling;
- only direct EVAL2 on exact active P2 `M_i` membership can produce the ranking scalar;
- EVAL2 historical checkpoint-selection, rescue, replay-admissibility, and bootstrap machinery cannot control target-size screening;
- EVAL2 correlation blocks preserve the complete accepted P1 split-exclusion/correlation closure;
- TRAIN2/EVAL2 numerical failures become scientific failure evidence only when positively authenticated by the real owner;
- ordinary input, lineage, schema, programming, subprocess, resource/OOM, filesystem, cancellation, and orchestration failures remain execution errors;
- P2 reducer advances only from one complete exact active boundary matrix;
- each complete reducer boundary is applied exactly once across crashes/restarts;
- workers may produce artifacts/outcomes but only the coordinator may commit scientific reducer transitions;
- current DATA8/TRAIN2 caching, staging, checkpointing, acceleration, resource scheduling, and optimized EVAL2 reductions are reused where semantically valid;
- no current CLI/CampaignStore ownership switches before P4;
- full long GPU/real-production qualification remains deferred to final release; bounded functional/resource validation remains required.

---

# P3-A — canonical common preparation and seed-neutral execution context

## A1. Build one current-generation common preparation

The target-size common preparation is rooted only in accepted current-generation authority:

```text
CanonicalFrameAuthority
+ accepted neutral feature/statistical evidence
+ P2 P_train membership
+ fixed common training/preparation policy
 -> one common preparation
```

Current `Data7PreparationBundle` is not itself the new authority because it embeds legacy `FeatureFitDomain` ownership and a DATA7 selection plan. Legacy DATA4/DATA5/DATA6/DATA7 objects may supply reusable low-level values or algorithms only when their recipe remains valid and the consumed result is explicitly rebound or verified against current P1/P2 authority.

Retired `label_domain_id`, `FeatureFitDomain`, DATA5 CV, selection-ladder, or candidate-complement lineage must not become scientific identity of the P3 common preparation.

Build the common preparation **once per P2 experiment**, normally over accepted `P_train`. Freeze every fitted quantity actually consumed by candidate training, including as applicable:

- exact common input-membership identity;
- atomic-reference/E0 policy and fitted result;
- objective/property/configuration-weight policy;
- deterministic per-frame configuration/property weights;
- normalization or fitted preprocessing genuinely consumed by training;
- feature/projection fit and fixed numerical seed only if genuinely consumed downstream;
- foundation/head identity required by the fit;
- replay source/exposure policy inputs used by common preparation;
- common checkpoint/metric policy inputs required by training.

The common fit may consume P1/P2-authorized training-side data but must not consume:

- `M1/M2/M3` labels or predictions;
- optimizer seed;
- candidate N or candidate outcomes;
- CV folds or CV evaluation;
- outer held-out/calibration/locked evidence;
- compatibility/label-domain grouping as a scientific fit axis.

Do not preserve obsolete selection/coverage objects merely to imitate `Data7PreparationBundle`.

## A2. Candidate preparation is exact projection only

For every candidate:

```text
candidate preparation = exact projection(common preparation, T_N)
```

Projection is selection only. It must not perform candidate-specific:

- E0/reference refitting;
- feature/normalization refitting;
- condition-weight recomputation;
- mean-one weight renormalization;
- clipping/rebalancing after projection;
- objective/property-weight changes.

This is material because the legacy configuration-weight builder normalizes over its fit domain. Re-running it on each `T_N` would make the objective vary with N beyond the intended data-cardinality change.

If real training mathematics proves that a fitted quantity must vary with N, stop dependent work and trigger the smallest design reopen. Do not hide N-dependent fitting inside an old domain API.

## A3. Define one seed-neutral execution context

Implement one canonical version-agnostic target-size execution-context authority and bind its digest through `bind_target_size_execution_context()` before ordinary boundary evidence can be accepted.

The context is the immutable study-wide scientific execution identity. It must bind, at minimum:

- `TargetSizeExperimentDefinition.content_digest`;
- common-preparation digest;
- foundation/source-potential and selected-head identity;
- replay preparation/exposure identity;
- seed-neutral optimizer/training-policy template;
- screen training-budget and LR-schedule policy identity;
- objective/weight/E0/common-fitted-preparation identity;
- precision/backend/batch/exposure policy semantics;
- TRAIN2 checkpoint/continuation policy;
- EVAL2 target metric/reduction policy;
- fixed non-controlling MACE harness-validation identity;
- genuine MACE compatibility/source-probe constraints required for mechanical execution.

The study-wide context excludes candidate-varying or execution-only state:

- N and exact `T_N` artifact digest;
- individual optimizer seed;
- active rung/boundary;
- current survivor set;
- candidate checkpoint/result identity;
- CV fold configuration/results;
- worker/process count, GPU allocation, queue order, telemetry, wall time, output path **only when those fields are proven not to alter scientific trajectory semantics**;
- fresh-final-production-only settings such as the independent production horizon.

Because current `MaceOptimizerPolicy` contains `seed`, do not use a candidate-specific optimizer-policy digest as the global context. Extract/derive one canonical seed-neutral training-policy identity and require each candidate policy to equal it except for the authorized seed and deterministic N-derived realization.

The actual screening seed set must equal `definition.policy.optimizer_seeds` exactly and in order. A changed seed set is a P2 policy change, not a P3 override.

## A4. Freeze one full-screen TRAIN2 schedule

The full screening trajectory ends at:

```text
n3 = definition.policy.fidelity_epochs[2]
```

For each `(N, seed)`:

- derive one TRAIN2 full budget/LR trajectory ending at n3;
- preserve that exact full-budget policy through all rungs;
- use `Train2RuntimePlan.execution_epoch_limit` or the semantically equivalent pause mechanism as n1, then n2, then n3;
- never construct independent rung-normalized LR schedules;
- never restart a survivor under a new training budget.

The screen-specific n3 budget is distinct from fresh final-production horizon. Current/default final production may remain 30 epochs; changing production-only horizon must not alter P2 target-size identity or a completed screen.

## A gate — required evidence

Before P3-B:

1. common-preparation focused tests prove one common digest/result across all N and seeds;
2. projection tests prove fitted weights/E0/preprocessing values are unchanged by candidate projection and never re-normalized;
3. changing only N changes membership projection, not common fitted state;
4. negative tests reject M-ladder/CV/held-out/seed/candidate-outcome inputs to common fitting;
5. seed-neutral context tests prove N/seed/path and truly execution-only resource differences do not change the context, while genuine common training-policy/preparation changes do;
6. exact P2 seed-set equality is enforced;
7. full-n3 schedule + rung-limit tests prove independence from production-only horizon;
8. run affected DATA7/reference-fit/objective/weight/TRAIN2-policy regression;
9. rerun affected P1/P2 regression for every shared helper or identity surface changed.

---

# P3-B — exact candidate realization and current-generation materialization

## B1. Do not use legacy materialization authority

Current `ProductionMaterializationPlan` and `build_data8_preparation_bundle()` retain legacy target-size topology: label domains, final/CV DATA7 bundles, selection ladders/`selection_size`, prescribed per-domain prefixes, CV plans, and complement-style target evaluation.

They are not P3 scientific authorities.

P3 may reuse/refactor their low-level cache, restart, staging, atomic-promotion, and resource-safe mechanisms, but the P3 path must not enter through a special mode that reconstructs retired topology.

## B2. Define one trajectory and authenticate its N-derived realization

There is one scientific trajectory per required `(N, optimizer_seed)`, not one independent trajectory per rung.

Its accepted parents and exact facts include at minimum:

```text
experiment-definition digest
execution-context digest
N
exact candidate-membership digest
exact ordered T_N frame membership
optimizer seed
seed-neutral training-policy identity
common-preparation digest
replay/foundation identity
```

Only qualified N values may be instantiated. Exact membership must equal `definition.candidate_membership(N)` and the P2 membership digest. Callers may not supply an alternative same-sized list.

Candidate-varying consequences of N/seed must also be bound or deterministically re-derived and verified, as applicable:

- exact target-train artifact identity;
- exact fixed harness-validation artifact identity;
- authorized optimizer seed;
- MACE loader dry-run/exposure realization;
- exported and effective target/replay counts;
- batch/exposure semantics;
- `updates_per_epoch`;
- `structures_per_epoch`;
- full-n3 `planned_updates`;
- full-n3 `planned_structures_presented`;
- resolved precision schedule;
- acceleration realization;
- candidate-specific optimizer/job protocol identity;
- exact TRAIN2 full-budget/LR policy and continuation parentage.

These are deterministic consequences of fixed policy plus N/seed, not additional experimental variables. A stale trajectory whose loader/update geometry or precision realization differs from the current exact `T_N` must be rejected even when global execution-context digest matches.

Do not blanket-classify resource settings as execution-only. Worker/process/DataLoader settings may be excluded from scientific identity only when supported-engine behavior demonstrates that they do not alter sample order, RNG draws, update geometry, or numerical-kernel semantics. Otherwise bind them in the appropriate execution identity.

Rung records descend from the trajectory and add active boundary/continuation ancestry; they do not redefine the candidate.

## B3. Refactor current-generation exact export

Target-training and harness-validation ExtXYZ/sidecar artifacts must bind current authority, at minimum:

- `CanonicalFrameAuthority` identity;
- exact ordered frame membership;
- common-preparation identity when fitted weights/E0 are consumed;
- canonical numerical label interpretation, units, signs, and conventions;
- ExtXYZ policy;
- exact artifact bytes and sidecar/content digest.

Do not retain legacy `frame_catalog_digest` or `data7_bundle_digest` as scientific parents merely because old exporter helpers require them. Refactor/extract the low-level exporter/recipe seam.

Raw frame arrays may be reused only after exported geometry and canonical energy/force/stress payloads are verified against the bound P1 authority.

Current `TrainingProtocolIdentity` may be reused internally only after extracting/refactoring target-size-relevant identity. Do not fabricate or preserve its legacy `data7_bundle_digest`, `selection_size`, monitor/CV, or historical checkpoint-selection fields as new target-size authority.

## B4. Extract one generic exact-membership DATA8/MACE primitive

Refactor/extract the smallest generic version-agnostic DATA8/MACE builder that accepts explicit exact target-training membership plus common preparation while reusing proven mechanisms for:

- immutable fixed-file/cache recipes;
- exact ExtXYZ materialization;
- replay staging and weight scaling;
- foundation/selected-head staging;
- MACE YAML generation and source/loader dry-run;
- acceleration/precision policy;
- target-size-relevant training/job identity;
- atomic file/tree publication;
- resource-safe cache behavior.

The P3 primitive must not require or synthesize:

- `label_domain_id` as scientific authority;
- CV plans/fold lists;
- DATA7 selection ladder or `selection_size` lookup;
- prescribed per-domain prefixes;
- development-complement target evaluation;
- target-size evaluation membership derived from training membership;
- fake `FeatureFitDomain`/DATA5/Data7 objects created solely to satisfy legacy APIs.

The old runtime may call shared low-level primitives while it remains current until P4; P3 must not call the legacy top-level topology.

## B5. Fixed MACE harness validation is non-controlling

If MACE mechanically requires `target_valid`, construct one deterministic fixed harness-only diagnostic input from authorized target-training-side data.

It must be identical across N and seeds under the same execution context and must not introduce a new capacity requirement. Training-side overlap is permitted because this is not statistical target-size evidence.

It has:

- no gradient contribution;
- no LR-schedule mutation;
- no generic/ordinary early-stop authority;
- no checkpoint/survivor/ranking authority;
- no M1/M2/M3 data;
- no outer held-out, calibration, or locked evidence.

Only exact boundary EVAL2 on the active P2 M rung may create target-size ranking evidence.

## B gate — required evidence

Before P3-C:

1. exact `T_N` membership/digest tests through the real candidate/materialization owner;
2. unqualified N and alternative-same-size membership rejection;
3. one trajectory identity per `(N, seed)` and no rung-as-new-trajectory drift;
4. N changes candidate realization where expected but not global context;
5. stale effective counts/update geometry/precision realization are rejected on restart;
6. same authorized candidate rematerializes the same realization;
7. any intentionally excluded worker/resource field has targeted invariance evidence;
8. exact exported frames/labels/weights authenticate against `CanonicalFrameAuthority` and common preparation;
9. canonical numerical label changes invalidate relevant export/trajectory;
10. advisory compatibility-grouping changes do not invalidate training computation;
11. materialized MACE YAML contains exact authorized seed and target-train artifact;
12. structural absence tests prove no new P3 durable scientific object requires legacy label-domain/DATA5-CV/DATA7-selection/complement fields;
13. harness-validation fixed/non-controlling tests;
14. cache/restart/serialization/atomic-promotion regression for refactored shared DATA8 mechanics;
15. affected objective/reference-fit/export/DATA8/MACE compatibility/fixed-file regression.

---

# P3-C — paired TRAIN2 execution and exact boundary state

## C1. Reuse TRAIN2 continuation; do not build another checkpoint engine

Use existing `train2_runtime.py` continuation machinery. It already persists/authenticates live parameters, EMA state, RNG state, raw checkpoint identity, optimizer-state reference, completed updates, and LR progress, and supports bounded `execution_epoch_limit` inside one frozen budget.

For each active candidate in P2 order and each optimizer seed in exact P2 order:

- seed the real MACE optimizer/training configuration with the authorized optimizer seed;
- run initialization -> n1;
- if the candidate survives, resume exact n1 state -> n2;
- if it survives again, resume exact n2 state -> n3;
- restore/authenticate model/live parameters, optimizer checkpoint state, EMA state when enabled, RNG state, completed updates, and LR/schedule progress;
- never restart a later rung from the foundation or epoch zero;
- never reinitialize RNG because orchestration resumed;
- ordinary target-success early stopping must not truncate a screen boundary;
- eliminated candidates receive no later ordinary screening work.

The invariant is same seed + same stochastic policy across N, not byte-identical RNG consumption after N changes.

Continuation acceptance must bind every later-rung request to the exact predecessor trajectory/checkpoint/companion. A checkpoint from another N, seed, context, protocol, or boundary is foreign even if tensor shapes match.

## C2. Freeze exact completed-epoch boundary semantics

P2 fidelity values `n1/n2/n3` are **completed-epoch counts**, not raw zero-based checkpoint indices.

Ordinary successful evidence at active boundary `n_i` is admissible only if real TRAIN2 state proves:

```text
Train2RuntimeSummary.completed_epochs == n_i
active execution_epoch_limit          == n_i
raw_checkpoint_epoch                  == n_i - 1
checkpoint/companion/runtime summary  == exact bound trajectory state
```

This includes the off-by-one case `n1 = 1 -> raw_checkpoint_epoch = 0`.

The exact authenticated state at the boundary is the sole model state eligible for P3 EVAL2. No earlier/later checkpoint may substitute because it appears better.

## C3. Freeze and authenticate evaluation model-state representation

P3 must explicitly fix the model-state representation evaluated by EVAL2—live/raw/EMA as applicable to the retained TRAIN2 semantics—and authenticate that representation as part of the trajectory/boundary state.

All candidates must use the same convention. Evaluation must not silently use a different representation from the one declared by the trajectory/continuation contract.

The same authenticated boundary state remains the continuation parent for a surviving candidate.

## C4. TRAIN2 numerical failure versus ordinary execution error

Do not classify scientific numerical failure from stderr text, nonzero exit status, resource exhaustion, or a generic exception.

Translate only positively authenticated real TRAIN2 numerical-failure records:

- `train_nonfinite_model_state` -> P2 `TRAIN_NONFINITE_MODEL_STATE`;
- current `train_nonfinite_ema_state` -> P2 model-state category, **not** optimizer-state category; preserve original TRAIN2 failure code/evidence;
- `TRAIN_NONFINITE_OPTIMIZER_STATE` only when a real TRAIN2 owner explicitly authenticates non-finite optimizer-state science.

If authenticated TRAIN2 numerical failure occurs while attempting to reach active boundary `n_i`, P3 may produce the corresponding P2 `TargetSizeNumericalFailure` for the **scheduled active boundary** so a complete boundary matrix can eventually exist. Classification evidence must retain actual failure location, raw epoch/completed updates, and trajectory identity. Do not pretend the candidate successfully reached n_i.

Corrupt/missing/mismatched restart state, ordinary MACE/config/schema/lineage error, OOM/resource error, filesystem/process/programming error, or cancellation remains an execution error. It produces no scientific numerical failure and does not advance the reducer.

## C gate — required evidence

Before P3-D:

1. real TRAIN2 runtime-plan tests prove one full-n3 schedule with n1/n2/n3 pause limits;
2. completed-epoch/raw-checkpoint mapping tests, explicitly including n1=1;
3. exact model/optimizer/EMA/RNG/completed-update/LR ancestry tests;
4. wrong N/seed/context/protocol/predecessor/boundary checkpoint rejection;
5. wrong checkpoint epoch/SHA/model-state representation rejection;
6. interrupted-resume and restart-after-boundary tests through real continuation owner;
7. exact continuation resumes from the same authenticated boundary state used for evaluation;
8. generic early-stop/control-path negative tests;
9. authenticated numerical-failure mapping tests, including EMA-not-optimizer;
10. authenticated pre-boundary numerical failure preserves real failure location while binding scheduled boundary;
11. generic/resource/OOM/lineage/process errors remain execution errors and leave P2 reducer unchanged;
12. affected TRAIN2 scheduler/checkpoint/resource regression.

---

# P3-D — direct exact-checkpoint EVAL2 on exact M_i

## D1. Replace legacy target-size role, not the metric engine

Current `Eval2TargetRole` carries legacy label-domain, role-freeze, complement/coarse, excluded-prefix, and CV semantics. It is not P3 authority.

Introduce/refactor one version-agnostic direct target-size EVAL2 role binding:

- P2 experiment-definition digest;
- P3 execution-context digest;
- N and optimizer seed trajectory identity;
- active boundary completed epoch;
- active evaluation size;
- exact P2 evaluation-membership digest;
- exact `definition.evaluation_membership(M_i)` frame UIDs;
- one stable correlation-block identity per evaluation frame from accepted P1 split-exclusion/correlation authority;
- exact authenticated TRAIN2 boundary checkpoint/model-state identity.

It contains no label-domain, CV-fold, development-complement, coarse-fallback, or excluded-training-prefix semantics.

Reuse existing EVAL2 target metric calculations, force reductions, numerical guards, cache/indexing machinery, correlation-block reductions, and optimized inference/resource path after replacing population/role authority.

## D2. Evaluate exactly one authorized boundary checkpoint

Current EVAL2 historical trajectory selection is **not** target-size screening authority.

P3 must expose/refactor direct exact-checkpoint inference + target-metric reduction and evaluate exactly one authorized checkpoint per ordinary successful `(N, seed, n_i, M_i)`.

Do not use any mechanism equivalent to:

- best/lightweight historical checkpoint selection;
- `build_eval2_shortlist()` selection;
- rescue checkpoint evaluation;
- `Eval2RunRecord.selected_checkpoint` as target-size boundary;
- replay admissibility to reject/select a target-size boundary checkpoint;
- bootstrap comparison to replace P2 reducer decision;
- generic MACE-validation score to choose the checkpoint.

An artificially better earlier checkpoint must be ignored.

## D3. Correlation blocks use the same complete P1 closure as P2

P2 splits `P_train/M3` using complete canonical `NeutralSplitExclusionEvidence` closure: correlation units, exact geometry duplicates, protected events, replica lineage, structural-realization lineage, and transitive chains.

EVAL2 must not regress to narrower legacy DATA5/unit-ID blocks.

Extract/refactor only as needed to create **one canonical component-projection implementation** shared by:

- P2 exact split construction; and
- P3 EVAL2 correlation-block assignment.

Frozen semantics:

- no duplicate component algorithm in P3;
- P2 split behavior/content remains scientifically unchanged;
- each M3 frame receives its full M3/P1 split-exclusion component identity;
- M1/M2 retain parent M3 component identities instead of recomputing prefix-local names.

Because this touches an accepted shared owner, run complete affected P2 split/restart regression after extraction.

## D4. Translate only the frozen authoritative target metric

Successful direct-M evidence produces P2 `TargetSizeBoundaryMetric` only when all lineage binds exactly:

- experiment-definition digest;
- execution-context digest;
- N and optimizer seed;
- exact authenticated boundary checkpoint;
- boundary completed epoch;
- exact P2 M-rung membership digest;
- frozen global target force-component RMSE.

The transferred scalar is exactly:

```text
TargetSizeBoundaryMetric.target_force_rmse_mev_per_a
    = Eval2TargetMetricRecord.force_component_rmse_ev_per_angstrom * 1000.0
```

No species-macro, worst-stratum, lightweight, replay, bootstrap, or checkpoint-selected metric may replace it. Correlation-block reductions remain supporting authenticated diagnostics/evidence; they do not replace the P2 scalar.

Authenticated EVAL2 numerical failures map losslessly:

- non-finite energy/force/stress predictions -> `EVAL_NONFINITE_PREDICTION`;
- non-finite target metric -> `EVAL_NONFINITE_TARGET_METRIC`;
- original EVAL2 failure code/record remains bound through classification evidence.

An authenticated EVAL2 numerical failure binds the exact `(N, seed, n_i, M_i)` attempt.

Schema/shape/lineage/missing-artifact/programming/resource failures are ordinary execution errors and produce no P2 scientific failure.

## D gate — required evidence

Before P3-E:

1. exact M1/M2/M3 role membership and digest tests;
2. direct role authenticates exact boundary checkpoint/model-state identity;
3. an artificially better earlier checkpoint is ignored;
4. historical shortlist/rescue/replay-admissibility/bootstrap/checkpoint-selection cannot alter P3 target-size evidence;
5. exact `eV/A -> meV/A` conversion test;
6. stable full-component correlation-block mapping across M1/M2/M3;
7. mixed-relation/transitive-chain tests prove complete P1 closure is retained;
8. negative tests against complement/coarse/CV fallback and M-ladder use as generic harness validation;
9. reference-equivalence tests for retained EVAL2 metric/block reductions;
10. EVAL2 numerical-failure translation and ordinary-error separation;
11. affected EVAL2 inference/cache/resource regression plus affected P2 component/split/restart regression.

---

# P3-E — complete-boundary coordinator, exactly-once commit, and restart

## E1. P2 reducer remains the sole decision owner

Implement one internal P3 screen coordinator that follows P2 state and is deliberately not a second ranking state machine.

For each boundary it must:

1. load/validate current P1/P2 aggregate and bound execution context;
2. read `reducer_state.status` and `reducer_state.active_candidate_sizes`;
3. derive active `n_i` and `M_i` from P2 reducer status/policy;
4. schedule only active N values, each with exact ordered P2 optimizer seeds;
5. materialize/resume corresponding candidate trajectories;
6. evaluate exact authenticated boundary checkpoint on exact active M rung;
7. collect candidate outcomes in required order:

```text
for N in reducer_state.active_candidate_sizes:
    for seed in definition.policy.optimizer_seeds:
        outcome(N, seed)
```

8. do **not** call the reducer until the exact active matrix is complete;
9. build one immutable complete boundary batch;
10. compute the pure reducer transition exactly once from that batch;
11. persist/publish the resulting P2 aggregate/reducer state through the owning P3 commit protocol;
12. stop when P2 reducer becomes terminal.

P3 must not independently:

- average seeds;
- sort scores;
- apply practical equivalence;
- decide survivors/finalists;
- maintain an authoritative active-candidate table;
- reorder an otherwise complete matrix;
- average a subset of successful seeds;
- fabricate `N_selected/T_selected`.

Execution queues/checkpoints may cache reconstructible work status, but restart must reconcile them to P2 authority and trajectory lineage.

## E2. Partial execution is not reducer evidence

P2 reducer advancement requires one complete ordered boundary matrix for active candidate sizes and ordered seeds.

A candidate outcome may be either:

- a successful `TargetSizeBoundaryMetric`; or
- a positively authenticated supported `TargetSizeNumericalFailure`.

Ordinary execution errors:

- create no P2 numerical failure;
- do not eliminate a candidate;
- leave reducer at the pre-boundary state;
- may persist reconstructible execution progress for retry/resume;
- must never trigger `advance_target_size_reducer()` on a partial matrix.

Partial successful/failure outcomes are execution progress only until the exact matrix is complete.

Do not call P2 with a partial matrix merely to force `INSUFFICIENT_COMPARISON`.

## E3. Immutable complete boundary batch

Create one immutable/content-addressed complete boundary-batch record only after the exact active matrix exists.

It binds at minimum:

- pre-transition `TargetSizeReducerState.content_digest`;
- experiment-definition digest;
- execution-context digest;
- active boundary completed epoch `n_i`;
- exact `M_i` membership digest;
- exact active candidate-size tuple;
- exact ordered optimizer-seed tuple;
- exact ordered boundary-outcome digests in P2-required size-major/seed-minor order.

Per-candidate checkpoints, evaluations, and completion records before this point are execution artifacts. They may be durable/reconstructible but are not independently applied to the reducer.

Parallel workers may produce authenticated artifacts/outcomes but may not mutate P2 reducer state. Only the coordinator may commit a boundary.

## E4. Deterministic reducer application and atomic execution head

Reducer transition is pure:

```text
post_state = advance_target_size_reducer(
    definition,
    pre_state,
    complete_batch.outcomes,
)
```

Persist the content-addressed complete batch **before** publishing an atomic P3 execution-head/aggregate pointer that binds:

- complete batch identity;
- resulting P2 aggregate/reducer digest;
- required P3 execution aggregate identity.

Exact filesystem representation is delegated. Externally visible committed state must never expose a half-applied transition.

Do not schedule speculative ordinary `n_(i+1)` work before the `n_i` reducer transition is durably committed and its survivors are authoritative.

## E5. Crash-consistent, idempotent restart reconciliation

Restart/reopen must reconstruct/validate P1 owners first and deserialize/rederive P2 through its real owner. It then validates context, common preparation, candidate realization/materialization, TRAIN2 ancestry, EVAL2 evidence, complete boundary batches, and reducer history.

Recovery semantics are frozen:

- **pre-state + complete valid unapplied batch:** deterministically apply it exactly once and publish/repair the head;
- **post-state already equals deterministic result of the same batch:** validate and treat as committed; never reapply/append outcomes;
- **same pre-state + different complete batch:** reject conflicting scientific evidence;
- **post-state with missing/mismatched required batch ancestry:** fail closed;
- **partial batch only:** remain at pre-state and resume missing work;
- historical outcomes are validated against the boundary/M membership recorded for their own reducer-history position, not current active boundary.

P3 restart must also:

- verify bound context still matches P2 definition and common training protocol;
- verify each candidate membership is exact P2 `T_N`;
- verify candidate N-derived loader/update/precision realization;
- verify exact TRAIN2 continuation/boundary ancestry;
- verify EVAL2 points to exact historical boundary checkpoint and exact historical M membership;
- replay/validate P2 reducer history through `validate_target_size_reducer_state()`;
- reject stale or coordinated-rehash state rather than silently repairing scientific authority.

## E6. Minimal durable P3 record before P4

P3 remains outside current CampaignStore generation. Implement the smallest version-agnostic durable execution aggregate needed to authenticate:

- accepted P2 statistical aggregate identity and current reducer state;
- execution-context identity;
- common-preparation identity;
- candidate trajectory/realization identities;
- materialized DATA8/MACE artifact identities;
- exact TRAIN2 continuation ancestry and runtime summaries/companions;
- direct exact-checkpoint EVAL2 evidence identities;
- partial execution progress;
- complete boundary-batch identities;
- atomic execution-head ancestry.

Do not duplicate P2 policy/order/reducer scientific state. Persist references/bindings to P2 authority and validate/replay through P2 owners.

CampaignStore/SQLite current-generation persistence and destructive old-generation rejection remain P4 responsibilities. Do not switch current receipt/state keys in P3.

## E7. Invalidation expectations

Dependency direction must be explicit:

- changed P1/P2 experiment definition -> all bound P3 scientific execution evidence stale;
- changed hard-support qualification/order/split/evaluation ladder/fidelity/seed set -> rejected through changed P2 definition/context;
- changed common preparation or seed-neutral training protocol -> context changes; old candidate evidence rejected;
- changed candidate N membership -> exact candidate must be rematerialized from P2;
- changed optimizer seed outside P2 seed set -> reject;
- changed candidate-derived effective counts/update geometry/precision realization -> stale trajectory rejected;
- changed canonical numerical label -> relevant export/trajectory/evidence stale;
- changed advisory compatibility grouping only -> training computation remains valid;
- changed execution-only worker/resource/telemetry field -> no scientific invalidation only when invariance is established;
- changed CV-only configuration or fresh-final-production horizon -> must not invalidate completed target-size screen.

## E gate — required evidence

Before P3-F:

1. coordinator structural/source tests prove P2 reducer APIs are the sole ranking/survivor calls;
2. exact outcome-order tests and negative reordered/missing/duplicate/foreign-seed tests through real P2 reducer;
3. partial boundary outcomes never invoke/advance reducer;
4. OOM/resource/process/lineage errors leave reducer scientifically unchanged;
5. retry after ordinary failure finishes same boundary without duplicate scientific evidence;
6. eliminated candidates receive no later ordinary work;
7. selected state comes only from P2 terminal output;
8. restart after every rung through real P3 record + P2 aggregate owner;
9. stale context/preparation/candidate/seed/boundary/continuation/evaluation/realization evidence rejection;
10. execution-only resource-setting invariance plus CV/production-only isolation;
11. concurrent-worker test proves workers cannot publish scientific reducer transition;
12. inject crash/restart through real coordinator/restart owner at least:
    - after candidate TRAIN2 persistence;
    - after only some boundary EVAL2 outcomes exist;
    - after complete boundary batch persistence but before reducer/head commit;
    - after deterministic reducer computation but before durable head publication;
    - immediately after durable head publication;
13. every crash recovery converges to exactly one valid reducer history with no duplicated/skipped/partial boundary;
14. affected P1/P2 restart/regression tests for every shared owner touched.

---

# P3-F — assembled closure and acceptance

## F1. Bounded end-to-end through real semantic owners

Run one bounded paired-seed target-size screen through the assembled owners:

```text
P1 CanonicalFrameAuthority + NeutralStatisticalBase
 -> P2 TargetSizeStatisticalAggregate
 -> canonical common preparation
 -> bind seed-neutral execution context
 -> qualified active T_N trajectory realizations
 -> current-generation exact export/materialization
 -> TRAIN2 to exact completed n1 boundary
 -> exact-checkpoint EVAL2 on M1
 -> complete boundary batch
 -> P2 reducer transition + durable P3 head
 -> exact TRAIN2 continuation to n2
 -> exact-checkpoint EVAL2 on M2
 -> complete boundary batch
 -> P2 reducer transition + durable P3 head
 -> exact TRAIN2 continuation to n3
 -> exact-checkpoint EVAL2 on M3
 -> complete boundary batch
 -> P2 terminal reducer state
 -> exact N_selected / T_selected digest
 -> P3 restart/reopen reproduces same accepted state
```

The fixture may use reduced candidate/evaluation sizes and very short bounded scientific computation. Expensive neural-network training/inference may be reduced or faked **below** the real materialization/TRAIN2/EVAL2 owner boundaries.

Acceptance may not monkeypatch, reimplement, seed around, or bypass:

- P1/P2 aggregate construction/restart;
- P3 common-preparation/execution-context owner;
- candidate realization and exact materialization owner;
- TRAIN2 continuation/boundary state machine;
- direct exact-checkpoint EVAL2 role/metric owner;
- complete boundary-batch coordinator/commit owner;
- P2 reducer transitions;
- P3 restart/reconciliation logic.

A test that seeds post-decision reducer state or directly calls a helper while bypassing its owning coordinator/restart path does not establish the integration claim.

## F2. Mandatory structural/absence inspection

Establish that the new P3 target-size path has:

- no scientific dependency on legacy label-domain identity;
- no DATA5-CV or pre-target CV dependency;
- no DATA7 selection-ladder/`selection_size` authority;
- no complement-derived target-size evaluation population;
- no fabricated legacy `FeatureFitDomain`/DATA5/Data7 object used solely for API compatibility;
- no historical EVAL2 shortlist/rescue/replay/bootstrap/checkpoint-selection path controlling target-size evidence;
- no second P3 ranking/survivor/selected-size authority;
- no current CLI/CampaignStore cutover before P4.

## F3. Required final affected regression surface

After all P3 executable edits, re-derive the actual affected surface and run at minimum:

- complete P3 focused suite;
- complete affected P2 target-size statistical/reducer/restart suite;
- affected P1 neutral split-exclusion/statistical restart suite when component mapping/shared relation helpers changed;
- affected DATA7 reference-fit/objective/weight/common-fit tests;
- affected current-generation export/sidecar tests;
- affected DATA8 fixed-file/cache/materialization/MACE-config/compatibility tests;
- affected TRAIN2 runtime, exact-boundary continuation, numerical-failure, scheduler/resource tests;
- affected EVAL2 direct metric/reduction/cache/numerical-failure tests;
- P3 crash/idempotency/concurrency tests;
- bounded P1 -> P2 -> P3 end-to-end integration on the assembled candidate;
- repository-required import/package/static/Python checks.

If implementation broadens the affected surface, broaden regression accordingly. Green focused tests do not excuse affected integration/regression.

No full long GPU/real-production qualification is required in P3. Do not infer production-scale throughput/VRAM conclusions from bounded functional tests.

---

# 4. Implementation authority

## Frozen

Implementation must preserve:

- frozen parent architecture and accepted P1/P2 semantics;
- version-agnostic durable P3 product naming;
- canonical P1 frame/label authority as source of target training/evaluation exports;
- one common deterministic fitted preparation computed once;
- exact projection onto each `T_N` without per-N refit, recomputation, clipping/rebalancing, or renormalization;
- one seed-neutral execution context bound once to P2;
- exact P2-qualified `T_N` memberships and ordered optimizer seeds;
- candidate-specific authentication of N-derived loader/update/exposure/precision realization;
- one scientific trajectory per `(N, seed)` with exact n1->n2->n3 continuation;
- one full-screen n3 TRAIN2 schedule with rung limits as continuation pauses;
- P2 n_i as completed epochs and raw TRAIN2 checkpoint index `n_i - 1`;
- explicit, fixed, authenticated evaluation model-state representation;
- exact active boundary checkpoint as sole screening checkpoint;
- shared DATA8/MACE/TRAIN2 machinery rather than a second training engine;
- fixed non-controlling harness validation separate from M1/M2/M3;
- direct exact-M EVAL2 role and exact-checkpoint inference;
- exact P2 scalar equal to global EVAL2 force-component RMSE converted `eV/A -> meV/A` by `* 1000.0`;
- EVAL2 correlation blocks derived from complete inherited P1 split-exclusion closure through one shared component implementation;
- authenticated, lossless TRAIN2/EVAL2 -> P2 outcome translation;
- ordinary execution errors never become scientific elimination;
- P2 reducer advances only from complete exact boundary matrix;
- immutable complete boundary batch and crash-safe exactly-once reducer application;
- coordinator-only scientific commit; workers never mutate P2 reducer;
- durable P3 restart validation while current CampaignStore/CLI cutover remains deferred to P4;
- stage-local affected regression and fresh final assembled regression/integration;
- no routine full GPU/production qualification.

## Delegated

Implementation may choose:

- exact version-agnostic class/module/schema names for common preparation, execution context, candidate realization, direct-M EVAL2 role, complete boundary batch, and P3 execution aggregate/head;
- location of neutral reusable fit/export helpers;
- whether candidate realization stores derived fields directly or binds canonical sub-object digests plus deterministic validation;
- location/name of shared split-exclusion component projection helper, provided P2 and P3 use one implementation;
- how much legacy DATA7/DATA8 code is extracted versus internally refactored, provided P3 does not reconstruct retired scientific topology;
- exact deterministic harness-validation sampling policy from authorized training-side data, provided it is study-wide, non-controlling, and adds no new capacity requirement;
- exact content-addressed filesystem layout and atomic pointer primitive;
- reconstructible queue/telemetry representation;
- bounded fake boundary below real semantic owners for expensive MACE work;
- exact fault-injection mechanism for crash tests;
- local refactors needed to preserve cache/resource machinery without changing scientific identity.

## Forbidden shortcuts

Implementation may not:

- create fake legacy `FeatureFitDomain`/DATA5/Data7 objects solely to satisfy old APIs;
- retain old label-domain/CV/DATA7-selection lineage as new common-preparation authority;
- recompute or renormalize frozen common weights separately for each `T_N`;
- derive candidate membership from DATA7 selection ladders/`selection_size` instead of P2 `T_N`;
- call legacy target-size `ProductionMaterializationPlan`/`build_data8_preparation_bundle()` through disguised old topology and claim current-generation P3;
- preserve legacy `frame_catalog_digest`/`data7_bundle_digest` as scientific parents of current target exports;
- fabricate obsolete `TrainingProtocolIdentity` fields to make old APIs fit;
- accept a candidate merely because global context matches while loader/update/precision realization is stale;
- exclude a worker/resource setting from scientific identity without evidence that it cannot alter sample/RNG/update/kernel semantics;
- use M1/M2/M3 as generic MACE validation or early-stop data;
- construct EVAL2 target-size roles by subtracting training membership from development data;
- use only legacy neutral unit IDs as correlation blocks when accepted P1 relation closure is broader;
- create independent n1/n2/n3 budgets/LR schedules;
- evaluate or select an earlier/better checkpoint instead of exact `n_i` boundary state;
- let EVAL2 shortlist/rescue/replay/bootstrap/checkpoint-selection logic control target-size outcomes;
- substitute species/worst-stratum/lightweight/replay/bootstrap metric for frozen global force-component RMSE;
- classify EMA non-finiteness as optimizer-state failure;
- classify stderr/resource/programming/lineage/restart errors as scientific numerical failures;
- call P2 reducer on a partial matrix to force `INSUFFICIENT_COMPARISON`;
- maintain P3-local ranking/survivor/selected-N authority;
- let workers race reducer transitions;
- reapply a complete boundary batch after crash/restart;
- schedule next-rung ordinary work before current reducer transition is durably committed;
- make current CLI/CampaignStore runtime partially switch before P4;
- retain old architecture merely to keep obsolete tests green.

## Reopen only on evidence

The parent design remains closed. Reopen only the smallest affected surface if real-owner evidence proves one of the following:

- a common fitted quantity mathematically must be re-estimated as N changes and cannot be represented as exact projection of common fitted state;
- canonical P1 numerical labels cannot be exported to MACE without reintroducing a scientifically material legacy authority;
- MACE/TRAIN2 cannot resume/authenticate the accepted exact full-trajectory model/optimizer/RNG/LR state at later fidelity boundary;
- supported MACE/TRAIN2 cannot expose/authenticate the exact completed-epoch boundary state required by the screen;
- a fixed non-controlling harness validation input cannot satisfy a demonstrated mechanical MACE requirement without gaining scientific control;
- complete P1 split-exclusion closure cannot supply stable EVAL2 block identities without changing accepted P1/P2 semantics;
- exact-boundary EVAL2 cannot compute the frozen primary target-force metric without historical checkpoint-selection authority;
- the P2 boundary-evidence/reducer contract cannot represent a positively authenticated real execution outcome without lossy/false classification;
- crash-consistent single application cannot be represented without changing accepted P2 reducer contract.

Legacy API inconvenience, obsolete tests, implementation effort, or documentation drift are not reopen evidence.

---

# 5. Implementation sequence and gates

Implement in this dependency order:

1. **P3-A:** canonical common preparation, exact projection, seed-neutral execution context, full-screen TRAIN2 policy.
2. **P3-B:** candidate realization, current-generation export, generic exact-membership DATA8/MACE materialization, fixed harness validation.
3. **P3-C:** paired TRAIN2 execution, exact completed-epoch boundary state, exact continuation, authenticated TRAIN2 failure adapter.
4. **P3-D:** shared P1/P2 component projection, direct exact-checkpoint M_i EVAL2 role, frozen metric conversion, EVAL2 failure adapter.
5. **P3-E:** complete-matrix coordinator, immutable boundary batch, crash-consistent exactly-once reducer commit, durable P3 restart/reconciliation.
6. **P3-F:** final assembled conformance review, structural absence inspection, complete affected regression, bounded real-owner end-to-end integration.

Each executable stage closes only after both:

- semantic/conformance closure of the obligations assigned to that stage; and
- focused checks plus stage-local affected regression.

Do not defer all regression to P3-F.

---

# 6. Exit gate

P3 is accepted only when one assembled implementation candidate proves:

> The accepted P1/P2 experiment executes a complete paired-seed `n1/M1 -> n2/M2 -> n3/M3` target-size screen through shared production DATA8/TRAIN2/EVAL2 machinery using exact P2 prefixes, one canonical current-generation common preparation projected without per-N refitting or renormalization, one immutable seed-neutral execution context, authenticated N-derived candidate realizations, exact completed-epoch TRAIN2 boundary continuation, exact-checkpoint direct-M EVAL2 with the frozen global force-component RMSE, complete inherited P1 correlation blocks, lossless scientific-failure translation, no scientific elimination from ordinary execution errors, and one crash-safe/idempotent reducer commit per complete boundary while P2 remains the sole screening decision authority. The entire P3 execution graph restarts deterministically, and the new path remains unreachable from current production CLI/CampaignStore orchestration until P4.

P4 remains blocked until this gate and all stage-local/final affected regression requirements pass.

Commit/tag the accepted P3 checkpoint before beginning P4.