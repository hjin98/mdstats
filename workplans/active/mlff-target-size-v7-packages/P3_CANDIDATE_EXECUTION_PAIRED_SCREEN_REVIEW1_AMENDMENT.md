---
kind: implementation-package-amendment
package_id: CODE-MLFF-TARGET-SIZE-V7-P3-REVIEW1
amends_package_id: CODE-MLFF-TARGET-SIZE-V7-P3
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
status: active
package_revision: 3
amended_date: 2026-08-28
reviewed_package_commit: 32547c427b61ff36ca54b2f436503df1f866329b
entry_p1_commit: 8ccee5a1068f8481df6a3e33ddb5f09f73654391
entry_p2_commit: 7be82ccb5ff1d99e73874e3a75a7a65d4926aaee
---

# P3 Review-1 amendment — execution-boundary and restart closure

## Authority and scope

The frozen parent workplan remains the scientific and architectural verdict. Accepted P1 and P2 remain frozen. This amendment closes implementation ambiguities found in independent review of P3 revision 2; it does not reopen the target-size model, split/order authorities, seed semantics, fidelity ladder, reducer, or P3/P4 ownership boundary.

This amendment has precedence over `P3_CANDIDATE_EXECUTION_PAIRED_SCREEN.md` only where it is more specific. Every unaffected P3 revision-2 requirement remains mandatory.

The review found five material handoff gaps:

1. common preparation/export could still inherit legacy DATA4/DATA5/`FeatureFitDomain` scientific lineage or re-normalize weights per `T_N`;
2. the seed-neutral study context did not explicitly authenticate N-derived loader/update/precision realization at the trajectory level;
3. P3 did not freeze exact completed-epoch boundary checkpoint semantics strongly enough to exclude historical EVAL2 checkpoint-selection logic or an epoch off-by-one;
4. ordinary execution errors versus authenticated scientific failures were not fully defined for an incomplete boundary matrix;
5. restart semantics did not define a single crash-consistent/idempotent reducer-advance commit boundary.

All five are P3 contract deficiencies. None invalidates the frozen parent design.

---

## R3.1 — canonical P1 preparation/export lineage and exact projection

### Required end state

The target-size common preparation is rooted in accepted current-generation owners:

```text
CanonicalFrameAuthority
+ accepted neutral feature/statistical evidence
+ P2 P_train membership
+ fixed common training/preparation policy
 -> one common preparation
```

Legacy DATA4/DATA5/DATA6/DATA7 objects may supply reusable low-level values or algorithms only when their content/recipe remains valid and the consumed result is explicitly rebound or verified against current P1/P2 authority. Their retired `label_domain_id`, `FeatureFitDomain`, DATA5 CV, or selection-ladder lineage must not become scientific identity of the new common preparation.

The common preparation must freeze, once over its authorized common population, every fitted quantity used by candidate training, including as applicable E0/reference state, normalization, objective/property policy, and deterministic per-frame configuration/property weights.

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

This is material because the current legacy configuration-weight builder normalizes over its fit domain. Re-running that normalization on each prefix would make the training objective vary with N beyond the intended data-cardinality change.

### Current-generation exact export

P3 target-training and harness-validation ExtXYZ/sidecar artifacts must bind current authority, at minimum:

- `CanonicalFrameAuthority` identity;
- exact ordered frame membership;
- common-preparation identity when fitted weights/E0 are consumed;
- canonical label interpretation/units/sign/conventions;
- ExtXYZ policy and exact bytes/sidecar digest.

Do not retain legacy `frame_catalog_digest` or `data7_bundle_digest` as the scientific parent merely because current exporter helpers require them. Refactor/extract the low-level exporter/recipe seam as needed. Raw frame arrays may be reused only after the exported geometry and canonical E/F/stress payload are verified to correspond to the bound canonical P1 frame authority.

Likewise, current `TrainingProtocolIdentity` may be reused internally only after extracting/refactoring the target-size-relevant identity. Its existing `data7_bundle_digest`, `selection_size`, legacy monitor/CV/checkpoint-selection fields must not be fabricated or preserved as new target-size authority.

### Required evidence

Add focused tests proving:

- common fitted weights/E0 are identical before and after projection and candidate prefixes do not re-normalize them;
- changing only N changes membership projection, not common fitted state;
- exact exported frames/labels/weights are authenticated against `CanonicalFrameAuthority` and common preparation;
- changing a canonical numerical label invalidates the relevant export/trajectory;
- changing only advisory compatibility grouping does not;
- new P3 durable scientific objects do not require legacy label-domain/DATA5-CV/DATA7-selection identity.

Run affected objective/reference-fit/export/DATA8 regression after this refactor.

---

## R3.2 — authenticate candidate-derived execution realization

The global P3 execution context remains deliberately seed- and N-neutral. Candidate-varying consequences of N are nevertheless scientific execution state and must be authenticated by the `(N, optimizer_seed)` trajectory.

Each trajectory must bind or deterministically re-derive and verify, as applicable:

- exact target-train and fixed harness-validation artifact identities;
- authorized optimizer seed;
- MACE loader dry-run/exposure realization;
- exported and effective target/replay counts;
- batch/exposure semantics;
- `updates_per_epoch` and `structures_per_epoch`;
- full-n3 `planned_updates` and `planned_structures_presented`;
- resolved precision schedule and acceleration realization;
- candidate-specific optimizer/job protocol identity;
- exact TRAIN2 full-budget/LR policy and continuation parentage.

These are deterministic consequences of fixed policy plus N/seed, not additional independently configurable experimental variables. A stale trajectory whose loader/update geometry differs from the current exact `T_N` must be rejected even when the study-wide execution-context digest is unchanged.

Do not blanket-classify a setting as execution-only merely because it affects resource use. In particular, worker/process/DataLoader settings may be excluded from scientific identity only if the realized training sample/RNG/numerical trajectory is invariant to that setting under the supported engine. If a setting can alter sample order, stochastic draws, update geometry, or numerical kernel semantics, it belongs in the appropriate scientific execution identity.

### Required evidence

Tests must prove:

- N changes the candidate realization where expected but not the global execution context;
- stale effective counts/update geometry/precision realization are rejected on restart;
- same authorized candidate rematerializes the same realization;
- any resource/worker field intentionally excluded from scientific identity has a targeted invariance test or is otherwise shown not to affect the supported training trajectory.

---

## R3.3 — exact completed-epoch boundary checkpoint is the sole screen checkpoint

### Boundary semantics

P2 fidelity values `n1/n2/n3` are **completed-epoch counts**, not raw zero-based checkpoint indices.

For active boundary `n_i`, ordinary successful evidence is admissible only when the real TRAIN2 state proves:

```text
Train2RuntimeSummary.completed_epochs == n_i
active execution_epoch_limit          == n_i
raw_checkpoint_epoch                  == n_i - 1
checkpoint/companion/runtime summary  == exact bound trajectory state
```

The exact authenticated model state at this boundary is what EVAL2 evaluates. No earlier or later checkpoint may substitute, even if it has a better target diagnostic.

The evaluation model-state convention (live/raw/EMA where relevant) must be explicitly fixed and authenticated so all candidates are evaluated from the same semantic boundary state that is preserved for continuation. P3 may not silently evaluate a different model representation from the one its trajectory/checkpoint contract declares.

### EVAL2 reuse boundary

Current EVAL2 contains useful target-metric and block-reduction kernels, but its historical trajectory shortlist/checkpoint-selection/replay-admissibility machinery is **not** target-size screening authority.

For P3 screening, do not use any mechanism equivalent to:

- best/lightweight historical checkpoint selection;
- `build_eval2_shortlist()` selection;
- rescue checkpoint evaluation;
- `Eval2RunRecord.selected_checkpoint` as the target-size boundary;
- replay admissibility to reject/select a target-size boundary checkpoint;
- bootstrap comparison to replace the P2 reducer decision;
- generic MACE-validation score to choose the checkpoint.

P3 should expose/refactor the direct exact-checkpoint inference + target metric reduction path and evaluate exactly one authorized checkpoint per `(N, seed, n_i, M_i)` ordinary success.

The scalar transferred into P2 is exactly:

```text
TargetSizeBoundaryMetric.target_force_rmse_mev_per_a
    = Eval2TargetMetricRecord.force_component_rmse_ev_per_angstrom * 1000.0
```

No species-macro, worst-stratum, lightweight, replay, bootstrap, or checkpoint-selected metric may silently replace it. Correlation-block reductions remain authenticated supporting evidence/diagnostics and retained EVAL2 machinery; they do not change the P2 primary scalar unless the frozen parent/P2 policy is explicitly revised.

### Required evidence

Add tests proving:

- the n_i completed-epoch/raw-checkpoint `n_i - 1` mapping, including n1=1;
- an artificially better earlier checkpoint is ignored and the exact n_i boundary is evaluated;
- historical EVAL2 shortlist/rescue/replay-admissibility/bootstrap logic cannot alter target-size boundary evidence;
- exact `eV/A -> meV/A` conversion;
- wrong checkpoint epoch/SHA/model-state representation is rejected;
- exact continuation resumes from the same authenticated boundary state after evaluation.

---

## R3.4 — complete-boundary evidence and failure semantics

P2 reducer advancement requires one complete ordered boundary matrix for the active candidate sizes and optimizer seeds. P3 must distinguish candidate-specific authenticated scientific failure from an incomplete execution attempt.

### Authenticated scientific failure

If real TRAIN2 positively authenticates a supported numerical failure while attempting to reach active boundary `n_i`, P3 may create the corresponding P2 `TargetSizeNumericalFailure` for the **scheduled active boundary** so the boundary matrix can complete. Its classification evidence must retain the exact TRAIN2 failure record, including actual failed raw epoch/completed updates and trajectory identity. Do not pretend the candidate successfully reached n_i.

Likewise, an authenticated EVAL2 numerical failure while evaluating the exact n_i checkpoint on exact M_i becomes the corresponding P2 failure for `(N, seed, n_i, M_i)` with the original owner evidence bound.

`TRAIN_NONFINITE_OPTIMIZER_STATE` remains reserved for a real TRAIN2 owner that explicitly authenticates non-finite optimizer-state science. A corrupt/missing/mismatched optimizer restart, generic exception, or EMA failure does not qualify.

### Ordinary execution error

Configuration, lineage, schema, programming, subprocess, resource/OOM, filesystem, missing-artifact, cancellation, or other ordinary execution errors:

- do not create `TargetSizeNumericalFailure`;
- do not eliminate the candidate scientifically;
- leave the P2 reducer at the pre-boundary state;
- may persist reconstructible execution progress for retry/resume;
- must not cause `advance_target_size_reducer()` to run on a partial matrix.

A partial set of successful/numerical-failure candidate outcomes is execution progress, not reducer evidence until the exact complete ordered active matrix exists.

### Required evidence

Tests must cover:

- authenticated TRAIN2 failure before n_i preserves actual failure location while binding the scheduled n_i outcome;
- EVAL2 numerical failure binds exact n_i/M_i;
- OOM/resource/process/lineage failures leave reducer state byte-for-byte/scientifically unchanged;
- partial boundary outcomes never advance the reducer;
- retry after ordinary failure can finish the same boundary without duplicate scientific evidence.

---

## R3.5 — crash-consistent, idempotent boundary commit

P3 needs one explicit commit unit between parallel execution work and P2 scientific state.

### Immutable complete boundary batch

Create one immutable/content-addressed boundary-batch record only after the exact active matrix is complete. It binds at minimum:

- pre-transition `TargetSizeReducerState.content_digest`;
- experiment-definition and execution-context digests;
- active boundary completed-epoch `n_i`;
- exact M_i membership digest;
- exact active candidate-size tuple;
- exact ordered optimizer-seed tuple;
- exact ordered boundary-outcome digests in P2-required size-major/seed-minor order.

Per-candidate checkpoints, evaluations, and completion records before this point are execution artifacts. They may be durable/reconstructible but are not independently applied to the reducer.

Only the coordinator may commit a boundary. Parallel workers may produce authenticated artifacts/outcomes but may not mutate P2 reducer state.

### Deterministic application and atomic head

Reducer transition is pure:

```text
post_state = advance_target_size_reducer(definition, pre_state, complete_batch.outcomes)
```

Persist the content-addressed complete batch before publishing an atomic P3 execution-head/aggregate pointer that binds the resulting P2 aggregate/reducer digest and batch identity. Exact filesystem representation is delegated; the externally visible committed state must never expose a half-applied transition.

Restart reconciliation must be deterministic:

- **pre-state + complete valid unapplied batch:** apply it exactly once and publish/repair the head;
- **post-state already equals deterministic result of the same batch:** validate and treat it as committed; never append/reapply outcomes;
- **same pre-state + different complete batch:** reject conflicting scientific evidence;
- **post-state with missing/mismatched required batch ancestry:** reject/fail closed;
- **partial batch only:** remain at pre-state and resume missing work;
- historical outcomes are validated against the boundary/M membership recorded for their own reducer-history position, not against whichever boundary is currently active.

Do not schedule speculative ordinary n_(i+1) training before the n_i reducer transition is durably committed and survivors are authoritative.

### Required crash/restart evidence

Inject failures through the real coordinator/restart owner at least:

1. after candidate TRAIN2 persistence;
2. after only some boundary EVAL2 outcomes exist;
3. after the complete boundary batch is persisted but before reducer/head commit;
4. after computing the reducer result but before publishing the durable head;
5. immediately after durable head publication.

Every recovery must converge to exactly one valid reducer history with no duplicated outcome and no skipped/partially applied boundary. Add a concurrent-worker test proving only the coordinator can publish the transition.

---

## Cross-cutting acceptance additions

The Revision-2 P3-A through P3-F sequence remains. Apply this amendment at the owning stages:

- **P3-A:** R3.1 common preparation lineage/projection and the common part of R3.2 identity;
- **P3-B:** R3.1 current-generation export plus R3.2 candidate realization;
- **P3-C:** R3.3 TRAIN2 exact boundary state and R3.4 TRAIN2 failure semantics;
- **P3-D:** R3.3 direct exact-boundary EVAL2 and metric conversion plus R3.4 EVAL2 failures;
- **P3-E:** R3.4 complete-matrix rule and all R3.5 crash/idempotency semantics;
- **P3-F:** re-run all amendment-focused tests and the complete affected P1/P2/P3/DATA7/DATA8/TRAIN2/EVAL2 regression/integration surface on one assembled candidate.

Mandatory structural/absence inspection must establish that the new P3 target-size path has no scientific dependency on legacy label-domain/DATA5-CV/DATA7-selection topology and no call path through historical EVAL2 checkpoint-selection as target-size decision authority.

The bounded end-to-end test must cross the real owners for common preparation, exact export/materialization, TRAIN2 boundary persistence/continuation, exact-checkpoint EVAL2 reduction, complete boundary-batch commit, P2 reducer transition, and P3 restart reconciliation. Expensive neural-network math may be reduced/faked below those owners. Full production/GPU qualification remains deferred.

## Frozen / delegated / forbidden

### Frozen additions

Implementation must preserve:

- common fitted state computed once and exact-projected without candidate renormalization/refitting;
- canonical P1 frame/label authority as the scientific source of target training/evaluation export;
- candidate-specific loader/update/precision realization authentication beneath one N-neutral study context;
- P2 n_i as completed epochs and raw TRAIN2 checkpoint index `n_i - 1`;
- exact active boundary checkpoint as the sole screening checkpoint;
- P2 scalar equal to exact EVAL2 global force-component RMSE converted to meV/A;
- ordinary execution errors cannot become scientific failure/elimination;
- reducer advances only from one complete exact boundary matrix;
- crash-safe/idempotent single application of each boundary batch.

### Delegated additions

Implementation may choose:

- exact current-generation common-preparation/export/trajectory/batch record class and schema names;
- where to place neutral reusable fit/export helpers;
- whether the candidate realization stores all derived fields directly or stores canonical sub-object digests plus deterministic validation;
- exact content-addressed filesystem layout and atomic pointer primitive;
- exact bounded fault-injection mechanism used for crash tests.

### Forbidden additions

Implementation may not:

- create a fake legacy `FeatureFitDomain`/DATA5/Data7 bundle solely to satisfy old fitter/exporter APIs;
- renormalize frozen common configuration weights separately for each T_N;
- accept a candidate merely because the global context matches while its loader/update/precision realization is stale;
- evaluate or select an earlier historical checkpoint instead of exact n_i;
- let EVAL2 shortlist/replay/bootstrap/checkpoint-selection logic control target-size outcomes;
- call the P2 reducer with a partial matrix to force `INSUFFICIENT_COMPARISON` after an ordinary execution error;
- reapply a complete boundary batch after crash/restart;
- allow workers to race scientific reducer transitions.

## Reopen only on evidence

The parent design remains closed. Reopen only the smallest affected surface if real-owner implementation evidence proves that:

- a common fitted quantity mathematically must be re-estimated as N changes;
- canonical P1 numerical labels cannot be exported to MACE without reintroducing a scientifically material legacy authority;
- the supported MACE/TRAIN2 engine cannot expose/authenticate the exact completed-epoch boundary state required by the parent screen;
- exact-boundary EVAL2 cannot compute the frozen primary target-force metric without historical checkpoint-selection authority;
- crash-consistent single application cannot be represented without changing the accepted P2 reducer contract.

Legacy API inconvenience, obsolete tests, or implementation effort are not reopen evidence.

## Amended P3 exit gate

P3 is accepted only when the Revision-2 exit gate **and** all Review-1 obligations above are satisfied on one implementation candidate. In particular:

> The target-size screen must train only exact P2 prefixes using one canonical current-generation common preparation projected without per-N refitting/renormalization, authenticate each N-derived execution realization, evaluate exactly the completed n1/n2/n3 TRAIN2 boundary state on exact M1/M2/M3 with the frozen EVAL2 force-component RMSE, distinguish scientific numerical failure from ordinary execution interruption, and commit each complete reducer boundary exactly once across crashes/restarts while P2 remains the sole screening decision authority.

P4 remains blocked until this amended P3 gate is accepted.
