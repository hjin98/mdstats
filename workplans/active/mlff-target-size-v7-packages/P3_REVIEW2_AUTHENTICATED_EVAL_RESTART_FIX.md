---
kind: implementation-package-amendment
package_id: CODE-MLFF-TARGET-SIZE-V7-P3-REVIEW2
amends_package_id: CODE-MLFF-TARGET-SIZE-V7-P3
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 3
status: active
package_revision: 4
amended_date: 2026-08-28
blocked_implementation_commit: e7535c691f6da09013649c327a2be4c32d032c2f
reconciliation_reason: Review-2 found two scientific/durability blockers in the implemented P3 D/E/F boundary. The direct EVAL2 path bound the intended M_i and boundary identity in metadata but did not authenticate that the supplied evaluation view/predictions actually came from that exact ordered M_i and exact boundary model state. The durable coordinator then persisted only reduced P2 outcomes, so restart could not revalidate the full candidate materialization -> TRAIN2 boundary -> exact-M evaluation -> P2 outcome execution graph. This amendment reopens only P3-D/E/F. P3-A/B/C and accepted P1/P2 semantics remain frozen.
---

# P3 Review-2 amendment — authenticated exact-M evaluation and durable execution proof

## 1. Authority, scope, and package status

This amendment is mandatory implementation authority for P3 revision 4 and must be read together with `P3_CANDIDATE_EXECUTION_PAIRED_SCREEN.md` revision 3.

It **supersedes any weaker interpretation** of P3-D2/D4, P3-E3/E4/E5/E6, P3-F1/F3, the P3 exit gate, and the revision-3 execution record where those sections allowed metadata-only or count-only evidence to stand in for real execution provenance.

The architectural/scientific verdict is **not reopened**:

- P1 remains accepted and frozen;
- P2 remains accepted and frozen;
- P3-A common preparation/context remains accepted and frozen;
- P3-B candidate realization/materialization remains accepted except where its durable artifact identity must now be referenced by P3-E completion records;
- P3-C TRAIN2 continuation/boundary semantics remain accepted, but P3-D/E must preserve immutable historical boundary evidence after continuation;
- only P3-D/E/F are reopened for the two Review-2 blockers and their necessary persistence consequences;
- P4 remains blocked until this amendment and the original P3 exit requirements close.

Do not redesign target-size statistics, membership construction, seed policy, fidelity policy, TRAIN2 schedule, reducer semantics, or current CLI/CampaignStore ownership to solve these defects.

The revision-3 statement that `P3-A..P3-F are closed` is superseded. P3 is **not accepted** at `e7535c691f6da09013649c327a2be4c32d032c2f`.

---

# R2-D — make exact-checkpoint / exact-M_i evaluation provenance non-forgeable

## D-R2.1. Diagnose the violated invariant

The target-size EVAL2 role already records the intended exact P2 `M_i` frame UIDs, membership digest, trajectory, boundary and model-state representation. That metadata is necessary but not sufficient.

The scientific owner must prove that the numerical evidence actually consumed by EVAL2 came from:

```text
exact authenticated TRAIN2 boundary state
+ exact ordered P2 M_i evaluation population
-> direct single-checkpoint inference
-> authenticated prediction evidence
-> EVAL2 reduction
-> P2 TargetSizeBoundaryMetric / authenticated numerical failure
```

A same-sized but different/reordered evaluation cohort, or predictions produced by another checkpoint/model state, must be rejected even if all counts and externally supplied role metadata match.

`EvaluationDatasetView.configuration_count`, prediction count, tensor shapes, or a caller-supplied role digest are **not** sufficient proof of membership or model-state origin.

## D-R2.2. Create one exact evaluation-data authority per M rung

Introduce/refactor one version-agnostic P3 evaluation-input/artifact authority for each exact P2 `M_i`. Exact class/schema names are delegated.

The authority must be built from `definition.evaluation_membership(M_i)` and canonical P1 numerical/frame authority, not from an arbitrary ASE list or prebuilt `EvaluationDatasetView`.

It must bind at minimum:

- P2 experiment-definition digest;
- canonical P1 frame-authority/dataset identity required to authenticate geometry and labels;
- exact evaluation size `M_i`;
- exact ordered `definition.evaluation_membership(M_i)` frame UID tuple;
- exact P2 evaluation-membership digest;
- canonical energy/force/stress label interpretation and units;
- evaluation/export/view policy identity required to reproduce the numerical input;
- immutable evaluation artifact bytes/content digest when a file representation is used;
- a deterministic evaluation-view/input digest derived from that exact artifact/membership.

The three M-rung artifacts/views are study-wide immutable inputs and should normally be materialized/cached **once per P2 experiment**, not once per candidate/seed. M1/M2/M3 may reuse existing exact-export and EVAL2 view/cache machinery, but their exact ordered memberships must remain explicit authority.

The generic `EvaluationDatasetView` may remain a numerical/indexing cache. If it does not carry frame UID/source identity, it **must not be treated as scientific membership proof by itself**. Wrap/bind it in the P3 exact-evaluation authority or extend the shared owner only if that is the lower-complexity correct solution.

Forbidden:

- placeholder membership digests;
- `membership_digest="a" * 64`-style test/runtime stand-ins at the accepted owner boundary;
- accepting a view because only its configuration count equals `M_i`;
- rebuilding M_i from training complement or another same-sized frame list;
- reordering exact M_i frames without changing/rejecting identity.

## D-R2.3. Add one real direct-boundary inference owner

P3 must have one real semantic owner for **single exact boundary checkpoint inference**. Reuse/extract the existing optimized MACE/EVAL2 inference machinery; do not create a second inference engine or re-enter historical shortlist/rescue/checkpoint-selection authority.

The owner must accept/derive and validate, at minimum:

- `TargetSizeCandidateTrajectory`;
- the validated candidate materialization needed to reconstruct the trained model architecture/source configuration;
- exact immutable `TargetSizeBoundaryState` / boundary snapshot;
- the direct target-size EVAL2 role;
- the exact P3 evaluation-data authority for that role's M_i;
- the frozen evaluation backend/precision/batching/resource policy already bound by the execution context/trajectory where scientifically material.

Before inference, it must prove:

1. trajectory, materialization, boundary state and EVAL2 role belong to the same P2 experiment/context/N/seed;
2. `boundary_state.boundary_epoch == n_i` and its state is the exact authenticated completed-epoch state;
3. the role's M size, ordered frame UIDs and membership digest equal the supplied exact evaluation authority byte-for-byte;
4. the evaluated model-state representation equals the frozen trajectory convention;
5. the exact evaluated state digest is derived from the authenticated boundary state:
   - `live` -> `rung_runtime_summary.live_parameter_digest`;
   - `ema` -> `rung_runtime_summary.ema_state_digest`;
6. if `ema` is the frozen convention, inference actually loads/materializes the authenticated EMA shadow state rather than silently using the raw/live checkpoint;
7. the low-level inference receives exactly the ordered M_i structures represented by the bound evaluation authority.

If current MACE/EVAL2 cannot evaluate the exact frozen live/EMA boundary representation without using historical checkpoint-selection authority, stop and trigger the existing smallest P3-D reopen condition. Do not substitute another checkpoint/state.

## D-R2.4. Prediction evidence must bind origin, not only values

Direct inference must return/persist one version-agnostic authenticated prediction-evidence record (exact naming delegated) rather than exposing an arbitrary `Sequence[prediction]` as sufficient scientific evidence.

It must bind at minimum:

- direct EVAL2 role digest;
- trajectory digest;
- boundary-state/snapshot digest;
- boundary completed epoch;
- evaluation model-state representation (`live`/`ema`);
- exact evaluated model-state digest from D-R2.3;
- exact evaluation-data authority/artifact digest;
- exact ordered M_i membership digest and count;
- prediction count/order;
- canonical prediction payload digest covering energy/force/stress values actually reduced;
- backend/precision realization only where required to authenticate the frozen scientific execution identity.

The prediction payload may be held in memory during one process, but durable cell completion/restart evidence must retain either immutable prediction bytes or another reproducible authenticated artifact sufficient to revalidate the EVAL2 metric without trusting the final scalar. Exact storage format is delegated.

A caller may not construct a role and arbitrary same-shaped predictions and thereby obtain admissible P2 evidence.

## D-R2.5. EVAL2 reduction consumes authenticated evaluation + prediction evidence

Refactor the P3 target-size reduction boundary so successful P2 evidence is produced only from the authenticated chain:

```text
role
+ exact evaluation-data authority/view
+ direct-boundary prediction evidence
-> existing EVAL2 target metric engine
-> Eval2TargetMetricRecord
-> TargetSizeBoundaryMetric
```

The existing global force-component RMSE and exact `* 1000.0` conversion remain unchanged.

Before transfer to P2, validate that:

- role, evaluation artifact/view and prediction evidence have identical M_i identity/order;
- prediction evidence belongs to the exact role/boundary/model-state digest;
- EVAL2 metric record binds the exact role and prediction-evidence digest;
- the metric configuration/force-component counts are consistent with the exact evaluation input;
- no historical checkpoint-selection/rescue/replay/bootstrap authority was consulted.

For a positively authenticated EVAL2 numerical failure, classification evidence must bind the same exact boundary-state/model-state and exact evaluation-data/prediction-attempt identity. Ordinary input/membership/checkpoint/provenance mismatches remain execution errors and produce no P2 scientific failure.

## D-R2 gate — required evidence before R2-E

1. exact M1/M2/M3 evaluation artifacts/views are built from real P2 membership owner and canonical P1 labels;
2. same-sized wrong membership is rejected before metric transfer;
3. exact-frame-set but reordered membership is rejected;
4. truncated/extended membership is rejected;
5. stale/foreign evaluation artifact digest is rejected;
6. prediction evidence from another N, seed, boundary, role or experiment is rejected;
7. prediction evidence from the same N/seed but another boundary state is rejected;
8. `live` versus `ema` model-state mismatch is rejected, and the evaluated state digest equals the frozen boundary representation;
9. tampered boundary companion/state digest is rejected before inference/evidence acceptance;
10. direct exact-checkpoint inference ignores an artificially better earlier checkpoint because it has no selection surface;
11. ordinary arbitrary prediction sequences cannot enter the coordinator as scientific evidence without passing the real direct-inference/evidence owner;
12. numerical-failure mapping remains lossless and is bound to exact boundary + exact M_i attempt;
13. retained EVAL2 metric/block/cache/inference affected regression remains green;
14. bounded tests may fake the expensive model forward pass **below** the direct-inference owner, but the owner must execute real provenance validation and construct the prediction evidence itself.

---

# R2-E — persist and replay the complete execution proof, not only the P2 scalar

## E-R2.1. Preserve immutable historical TRAIN2 boundary snapshots

A surviving trajectory continues from n1 -> n2 -> n3, while ordinary TRAIN2 `runtime_summary` / continuation-companion filenames may represent only the latest boundary. P3 restart nevertheless must authenticate historical n1/n2 evidence after the candidate has advanced.

Therefore, when a candidate reaches each accepted boundary and **before later-rung continuation can overwrite/replace mutable latest-state files**, promote one immutable/content-addressed boundary snapshot.

The snapshot must preserve/authenticate enough real TRAIN2 state to prove both evaluation origin and continuation ancestry later, including at minimum:

- trajectory digest;
- boundary completed epoch and rung-plan digest;
- raw epoch/checkpoint name + SHA/content identity;
- runtime summary bytes/content digest;
- continuation companion bytes/content digest sufficient to revalidate live parameters, EMA state when enabled, RNG state and other continuation content protected by TRAIN2;
- optimizer-state reference/checkpoint identity;
- live-parameter digest;
- EMA-state digest when enabled;
- RNG-state digest;
- completed update/LR/schedule geometry.

The snapshot does not require wasteful full duplicate copies when the filesystem can safely preserve immutable bytes via content-addressed hardlink/reflink/atomic promotion. Storage strategy is delegated; **historical bytes/evidence may not disappear when the active continuation files advance**.

Raw checkpoint or companion garbage collection must not remove a snapshot still referenced by any committed P3 cell/batch/head.

## E-R2.2. Add one immutable per-cell completion record

For every completed scientific matrix position `(N, seed, n_i, M_i)`, persist one immutable/content-addressed completion record before it can enter a complete boundary batch.

For successful evaluation it must bind, directly or by content-addressed references:

```text
screen/window identity
P2 experiment + execution context
common preparation
candidate trajectory + N-derived realization
validated materialization identity
exact boundary snapshot / continuation ancestry
exact direct EVAL2 role
exact M_i evaluation-data authority/artifact
prediction evidence
Eval2TargetMetricRecord
translated P2 TargetSizeBoundaryMetric
```

For an authenticated TRAIN2/EVAL2 scientific numerical failure, bind the corresponding real failure record/evidence chain and translated `TargetSizeNumericalFailure` instead of pretending successful downstream artifacts exist.

Execution-only locators/relative paths may be persisted to find artifacts, but absolute paths/queue order/telemetry must not become scientific identity merely for convenience. Every locator used on restart must resolve to content that matches its bound digest.

A per-candidate progress record should reference the completion-record digest. It must not reduce the durable scientific chain to only `{trajectory_digest, P2 outcome}`.

## E-R2.3. Complete boundary batch binds completion records and derived P2 outcomes

Extend/refactor the immutable complete boundary batch so it binds, in exact P2 size-major/seed-minor order:

- the ordered completion-record digests for every active `(N, seed)` cell;
- the corresponding ordered P2 outcome digests derived from those records;
- the existing pre-state/definition/context/boundary/M_i/active-size/seed identities.

Batch construction must load/validate each completion record and derive/compare the P2 outcome; callers may not supply an unrelated syntactically valid P2 outcome beside a completion-record digest.

A batch is incomplete if any matrix position lacks a validated completion record, even if a caller can manually construct all expected P2 outcomes.

## E-R2.4. Execution head must form a replayable ancestry chain

The durable head must bind the complete batch and enough ancestry to replay from the initial bound P2 reducer state to the current state without trusting embedded post-state objects.

Require either an explicit `parent_head_digest`/genesis identity or another unambiguous content-addressed ancestry scheme. Exact schema is delegated, but restart must be able to prove:

```text
initial bound reducer state
 -> batch_1 -> recomputed post_1
 -> batch_2 -> recomputed post_2
 -> ...
 -> current head
```

Embedding `pre_state`/`post_state` in a head is permitted as cached evidence, but **never authoritative over deterministic replay**.

Atomic visibility order remains:

1. immutable underlying artifacts/completion records;
2. immutable complete batch;
3. immutable head;
4. atomic current-head pointer.

A crash before a cell completion record is durably published leaves only reconstructible execution residue and cannot become reducer evidence.

## E-R2.5. Restart/reconciliation algorithm is exact and fail-closed

`reconcile_target_size_screen_root()` or its version-agnostic successor must execute the real validation/replay path, not merely validate final P2 state shape.

For every reopen:

1. validate immutable screen/window against current accepted P1/P2 aggregate, context and common preparation;
2. obtain the initial bound reducer state from accepted P2 authority and validate its digest against the window;
3. discover the unique committed head ancestry from genesis/current pointer; reject forks, orphans, skipped parents and conflicting batches;
4. for each historical batch in order, load its exact historical active boundary/M_i context from the replayed pre-state;
5. for every ordered cell completion record in the batch, revalidate through the real owners:
   - trajectory against definition/context/common;
   - N-derived realization;
   - materialization and exact target/harness artifacts against canonical P1 authority;
   - immutable TRAIN2 boundary snapshot and predecessor continuation ancestry;
   - exact direct EVAL2 role;
   - exact evaluation-data authority/M_i membership;
   - prediction evidence + exact model-state digest, or authenticated numerical-failure evidence;
   - EVAL2 metric/failure translation and final P2 outcome;
6. reconstruct the ordered P2 outcomes from those validated completion records;
7. rebuild/revalidate the complete boundary-batch identity;
8. compute `post_state = advance_target_size_reducer(definition, replayed_pre_state, outcomes)` through the real P2 owner;
9. require the recomputed post-state digest to equal the head's declared post-state digest/cached state;
10. validate the resulting P2 reducer state and continue to the next ancestry node;
11. require the final recomputed state/head to equal the atomic current-head pointer;
12. only then expose the reopened P3 state or schedule subsequent ordinary work.

Recovery semantics from the original P3 remain, with stronger proof:

- valid complete batch persisted before head -> apply/rebuild exactly once after validating all cell completion records;
- valid immutable head persisted but current pointer missing -> repair only the pointer after deterministic replay;
- partial execution/completion records -> remain at pre-state and resume missing work;
- same pre-state with conflicting complete batches -> fail closed;
- missing/tampered/stale materialization/TRAIN2/evaluation/prediction/metric/completion ancestry -> fail closed;
- syntactically valid head/post-state that does not equal deterministic replay -> fail closed;
- no "coordinated rehash" or rewriting downstream digests to bless changed upstream scientific evidence.

## E-R2.6. Pre-amendment P3-local durable roots are not compatibility authority

P3 has not cut over CampaignStore/current production ownership. Therefore revision-3 P3-local screen roots that lack the new completion/provenance chain are **not accepted durable scientific state**.

Do not add a migration/fallback layer merely to preserve those unaccepted internal schemas. Fail closed with a clear stale-schema/rebuild diagnostic and rerun the bounded/internal P3 screen under revision-4 records. P4 owns future current-generation migration/cutover semantics.

## E-R2 gate — required evidence before R2-F

1. immutable n1/n2/n3 boundary snapshots remain independently authenticatable after later-rung continuation has advanced the active runtime files;
2. deleting/tampering a historical raw checkpoint, summary or companion referenced by a committed cell causes restart failure;
3. stale/wrong candidate materialization causes restart failure even when the final P2 scalar is unchanged;
4. stale/wrong boundary snapshot or continuation ancestry causes restart failure;
5. same-size wrong/reordered M_i evaluation artifact causes restart failure;
6. prediction evidence from another checkpoint/model-state causes restart failure;
7. tampered EVAL2 metric record or translated P2 outcome causes restart failure;
8. batch with correct P2 outcomes but wrong/missing completion-record digest is rejected;
9. head with syntactically valid but forged pre/post state is rejected by deterministic P2 replay;
10. orphan head, skipped parent, conflicting sibling head/batch and conflicting same-pre-state batch are rejected;
11. crash injection/restart through the **real coordinator/reconciler** covers at least:
    - after candidate materialization;
    - after TRAIN2 boundary persistence but before immutable boundary-snapshot promotion;
    - after boundary-snapshot promotion;
    - after exact evaluation artifact/view availability;
    - after prediction evidence but before cell completion;
    - after only some cell completions exist;
    - after complete batch persistence but before reducer/head commit;
    - after deterministic reducer computation but before durable head publication;
    - after immutable head publication but before current-pointer publication;
    - immediately after current-pointer publication;
12. every valid crash point converges to one reducer history with no duplicated/skipped/partial boundary;
13. worker concurrency may publish independent artifacts/completion records but cannot publish a reducer transition;
14. old revision-3 P3-local roots fail closed rather than silently receiving fabricated provenance;
15. affected TRAIN2 persistence/restart, export/materialization, EVAL2, P2 reducer/restart and P3 concurrency regressions pass.

---

# R2-F — assembled acceptance through real provenance and restart owners

## F-R2.1. Required bounded end-to-end path

The final P3 integration must execute this assembled path:

```text
P1 canonical authority
 -> P2 experiment / initial bound reducer state
 -> P3 common preparation + context
 -> exact candidate trajectory + materialization
 -> TRAIN2 to exact n_i
 -> immutable boundary snapshot
 -> exact P2 M_i evaluation artifact/view
 -> direct exact-boundary inference owner
 -> authenticated prediction evidence
 -> EVAL2 reduction / authenticated failure
 -> immutable per-cell completion record
 -> complete ordered batch bound to completion records
 -> P2 reducer transition
 -> immutable ancestry head + current pointer
 -> surviving trajectory continuation
 -> ... n2/M2 ... n3/M3
 -> terminal P2 state
 -> fresh P3 reopen
 -> full deterministic replay of every committed cell/batch/head
 -> identical terminal P2 state and selected membership
```

A final integration that injects predictions directly into `evaluate_target_size_boundary()` or seeds already-translated P2 outcomes does **not** close this claim.

## F-R2.2. Test-double boundary

Bounded CPU-friendly testing remains required; no full GPU/real-production qualification is introduced.

Allowed:

- fake/reduced expensive neural-network forward computation **inside/below** the real direct-boundary inference owner;
- tiny candidate/evaluation memberships;
- short n1/n2/n3 values consistent with the real completed-epoch semantics;
- synthetic but canonical P1 frame/label fixtures;
- deterministic fault injection below/around atomic persistence points.

Forbidden for acceptance of the repaired owners:

- manually constructing prediction evidence outside the direct-inference owner;
- bypassing exact evaluation-artifact construction with an arbitrary same-sized `EvaluationDatasetView`;
- bypassing immutable boundary-snapshot validation;
- manually constructing cell completion records from final scalars without validating their parents;
- invoking `advance_target_size_reducer()` directly instead of the real coordinator/restart commit path for the end-to-end claim;
- seeding a post-transition reducer/head and calling validation only on the finished object;
- monkeypatching/reimplementing restart ancestry or P2 transition logic in the harness.

## F-R2.3. Final affected regression and conformance

After the corrective implementation, rerun fresh final assembled regression covering at minimum:

- complete P3 A-F focused suite, revised so D/E/F acceptance goes through the repaired semantic owners;
- all new Review-2 adversarial provenance/restart tests;
- affected P1 canonical export/label and split-exclusion surfaces;
- affected P2 experiment/reducer/restart tests;
- affected DATA8/MACE materialization/config/cache validation;
- affected TRAIN2 runtime/continuation/persistence/numerical-failure tests;
- affected evaluation-view/export and EVAL2 metric/cache/inference/numerical-failure tests;
- P3 coordinator concurrency, atomic persistence and crash/replay tests;
- one bounded P1 -> P2 -> P3 terminal screen and fresh-process-equivalent reopen/replay;
- repository-required import/package/static/Python checks.

Re-derive the final affected surface after implementation. Broaden the suite if the repair changes shared `EvaluationDatasetView`, MACE inference, TRAIN2 persistence, artifact export or other consumers beyond this initial list.

Previously green revision-3 D/E/F tests are not sufficient evidence where they bypassed these real provenance/restart owners. P3-A/B/C evidence may be reused only where the corrective edits do not touch their affected surfaces.

---

# 2. Revision-4 implementation authority

## Frozen additions

Implementation must additionally preserve:

- exact ordered M_i identity is authenticated at the numerical evaluation input, not merely written into role metadata;
- one study-wide immutable exact evaluation artifact/view authority per M rung, derived from P2 membership + P1 canonical labels;
- one direct single-boundary inference owner with no checkpoint-selection surface;
- evaluated live/EMA model-state representation and digest come from the exact immutable TRAIN2 boundary snapshot;
- predictions become scientific evidence only through an authenticated record binding exact boundary state + exact M_i input + prediction payload;
- EVAL2 metric/failure evidence is derived from that authenticated prediction/input chain;
- each historical n1/n2/n3 boundary remains independently authenticatable after continuation advances;
- every scientific `(N, seed, n_i, M_i)` cell has one immutable completion record binding its full execution proof;
- complete batches bind ordered completion-record digests as well as P2 outcomes;
- reducer/head state is reconstructed by deterministic replay from initial P2 state, never trusted because serialized fields are internally consistent;
- stale/tampered upstream execution evidence cannot be made valid by rewriting downstream digests;
- pre-amendment unaccepted P3-local durable roots are rejected rather than migrated through compatibility fallback;
- P4 remains blocked until corrected P3 D/E/F semantic and functional closure passes.

## Delegated additions

Implementation may choose:

- whether exact M_i authority wraps `EvaluationDatasetView` or extends a shared evaluation owner;
- exact version-agnostic names/schemas for evaluation artifacts, prediction evidence, boundary snapshots and cell completion records;
- whether prediction payloads are persisted as arrays, file artifacts, content-addressed blobs or another reproducible immutable form;
- exact low-level direct MACE inference primitive extracted/reused from EVAL2;
- hardlink, reflink, copy, immutable rename or equivalent content-addressed mechanism for historical TRAIN2 boundary snapshot preservation, provided byte identity and lifetime guarantees hold;
- exact head-parent/ancestry representation, provided unique deterministic replay is provable;
- exact relative locator/index layout for durable artifacts;
- local schema replacement of revision-3 P3-only records, because they are not current production persistence.

## Forbidden additions

Implementation may not:

- accept exact M_i merely because evaluation/prediction counts match;
- accept arbitrary same-sized/reordered views under an authorized role;
- accept caller-manufactured predictions as checkpoint-authenticated evidence without the direct-inference owner;
- calculate a prediction digest from values + role and treat that alone as proof that the bound checkpoint generated those values;
- declare EMA evaluation while actually predicting from live/raw parameters;
- discard/overwrite the only durable proof of historical n1/n2 boundaries after continuation;
- persist only translated P2 outcomes and call that full P3 restart evidence;
- let a batch omit completion-record provenance;
- trust serialized head `post_state` without recomputing the transition from validated batch evidence;
- validate only the latest boundary when historical committed batches exist;
- repair stale scientific evidence by coordinated digest rewriting;
- add a migration/fallback path for the unaccepted revision-3 P3-local schema solely to keep old tests/artifacts working;
- move any part of this repair into public CLI/CampaignStore cutover before P4.

## Reopen only on evidence

The original P3 reopen conditions remain. This amendment adds no new broad redesign authority.

Reopen only the smallest affected D/E surface if real-owner evidence proves that:

- supported MACE cannot deterministically evaluate the exact frozen live/EMA boundary representation from authenticated TRAIN2 state without materially changing the accepted TRAIN2/EVAL2 contract;
- canonical P1 exact M_i input cannot be represented/authenticated by the retained export/evaluation machinery without introducing a scientifically material new authority;
- durable historical boundary proof cannot be preserved within acceptable storage/I/O bounds using content-addressed checkpoint/companion retention and requires a different persistence contract.

Implementation inconvenience, existing helper signatures, revision-3 test shape, or desire to preserve unaccepted P3-local files are not reopen evidence.

---

# 3. Corrective implementation order

Implement the reopened work in this dependency order:

1. **R2-D1:** exact M_i evaluation artifact/view authority + negative membership/order authentication.
2. **R2-D2:** immutable TRAIN2 boundary-snapshot promotion needed by direct inference and later restart.
3. **R2-D3:** real single-boundary inference owner + authenticated prediction evidence + EVAL2 reduction transfer.
4. **R2-E1:** immutable per-cell completion record and progress reference.
5. **R2-E2:** completion-bound complete batch + replayable head ancestry + exact deterministic reconciler.
6. **R2-F:** adversarial provenance/restart coverage, fresh affected regression, bounded assembled end-to-end + full reopen/replay.

Each executable corrective stage requires semantic/conformance closure and its stage-local affected regression before dependent work proceeds. Do not postpone all new negative/restart testing to R2-F.

---

# 4. Revision-4 exit gate

P3 is accepted only when the original P3 exit gate **and** this stronger condition both hold:

> Every target-size screening scalar or authenticated numerical failure is provably descended from the exact accepted candidate trajectory, exact immutable completed-epoch TRAIN2 boundary model state, and exact ordered P2 M_i canonical evaluation population through one direct single-checkpoint inference/reduction owner. Every committed matrix cell preserves that provenance durably; every complete batch binds those cell records; and restart reconstructs the entire historical execution graph and every P2 reducer transition from the initial bound state rather than trusting final serialized outcomes. Same-sized wrong/reordered M_i data, foreign/stale checkpoint predictions, lost historical boundary state, tampered materialization/evaluation/metric evidence, forged batches or forged heads all fail closed. The repaired path remains internal until P4 and requires no full GPU/production qualification.

Only after this gate passes may the owning P3 workplan be marked closed/accepted and P4 begin.
