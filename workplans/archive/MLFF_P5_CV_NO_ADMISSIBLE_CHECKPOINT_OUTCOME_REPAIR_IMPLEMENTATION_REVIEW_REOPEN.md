---
kind: implementation-workplan-review-reopen
workplan_id: MLFF-P5-CV-NO-ADMISSIBLE-CHECKPOINT-OUTCOME-REPAIR-REVIEW-REOPEN-1
parent_workplan_id: MLFF-P5-CV-NO-ADMISSIBLE-CHECKPOINT-OUTCOME-REPAIR
protocol_version: 6.3.0
status: active-reopened
review_verdict: no-pass
implementation_branch: fix/mlff-p5-cv-no-admissible-outcome-repair
accepted_baseline: 4eabe2ae9783c7ff92f3a1093c37502a01380812
semantic_candidate: 737dd75a9afe1ab1a3214f7f96d3a44d29db0fd0
reviewed_head: e9f9e83642b99354fb3105a05f0470fcacdee778
reviewed_head_delta: generated CLI specification PDF only
highest_affected_domain: D4 implementation/evidence/lifecycle closure under coherent accepted D3 post-selection CV architecture
serious_challenge: none
precedence: This independent Protocol 6.3 Review reopens and extends the parent workplan only for the bounded blockers below. It preserves every non-conflicting D1/D2/D3 invariant, F1-F9 cycle decision, O1-O11 obligation, acceptance matrix, non-goal, and simplification constraint in the parent. No scientific threshold, replay semantics, fold/seed/horizon policy, target-size method, TRAIN2 scheduling architecture, or final-production success evidence contract is reopened.
---

# P5 no-admissible-checkpoint outcome repair — independent implementation Review reopen

## 0. Review disposition

**NO-PASS / REOPENED.** No Serious Challenge is active.

The semantic implementation candidate `737dd75a9afe1ab1a3214f7f96d3a44d29db0fd0` substantially repairs the core D4 defect in the intended owner. Current head `e9f9e83642b99354fb3105a05f0470fcacdee778` differs only by regenerated `docs/specs/training_data/mlff_data9b3_campaign_cli_spec.pdf`, so the executable candidate remains `737dd75...`.

The main design is conforming and SHALL be preserved:

- `select_cv_fold_representative()` still filters mandatory admissibility before target-only ordering and now returns no representative for a nonempty all-inadmissible set rather than promoting a rejected checkpoint;
- zero candidates remain a hard failure;
- the canonical `CvFoldAcceptance` now directly represents `representative_selected` and `no_admissible_representative` without a second reducer/status system;
- no-admissible CV execution persists candidate evidence, creates no representative, performs no held-out outer evaluation, and reaches the ordinary fold/seed/size/campaign reduction path;
- generic/final-production `PostSelectionRunEvidence` remains success-shaped; final production still hard-fails if no checkpoint is admissible;
- required sibling folds and later frozen selected sizes continue after a valid methodological rejection;
- overall campaign acceptance remains conjunctive and production remains blocked when any required size rejects;
- the 30 meV/A target ceiling, replay-retention ceiling, TRUE_DFT replay requirement, target-only ranking, outer-fold isolation, selected sizes, horizons, optimizer/training method, and GPU scheduling architecture were not weakened to obtain the result;
- the old exception-shaped unit oracle was corrected to protect the real invariant: inadmissible checkpoints are never promoted.

The repair is therefore architecturally pointed in the correct direction. Closure is blocked by one D4 restart/integrity gap and two required acceptance/impact-closure gaps. Repair them by altering the existing canonical owners. Do not add a sidecar verdict registry, migration database, candidate-validation service, retry wrapper, second reducer, exception parser, or new durable state machine.

---

## 1. Governing invariants retained from the parent

All parent invariants remain binding. The reopen specifically emphasizes these:

1. **Three-way candidate result partition** remains exact:
   - zero candidates -> hard execution/evidence failure;
   - nonempty, zero admissible -> valid rejected fold verdict;
   - one or more admissible -> freeze one admissible representative, then evaluate held-out outer evidence.
2. **No rejected candidate becomes representative**, including restart, compatibility, and persisted-record paths.
3. **A negative fold verdict is complete only when its decisive candidate evidence is authentic.** The new verdict's `candidate_record_digests` are evidence bindings, not decorative audit metadata.
4. **Current evidence corruption remains fail-closed.** Missing/corrupt/stale bound candidate evidence cannot be converted into a methodological rejection or silently bypassed by a cached terminal verdict.
5. **Completed TRAIN2 remains reusable.** Repairing verdict authentication must not force re-training valid completed TRAIN2.
6. **One canonical CV result/recovery owner.** Extend/reuse the existing fold-acceptance/evidence-store recovery path; do not create a parallel negative-result recovery mechanism.
7. **Every required fold and frozen size remains required**, and methodological collection completes before campaign reduction.
8. **Final production remains success-only** and cannot inherit nullable representative semantics from CV merely for implementation convenience.
9. **Scientific/numerical policy is frozen.** No threshold, replay, target ranking, fold/seed/horizon, model, optimizer, precision, or exposure change is authorized.

---

## 2. Blocker R1 — persisted v2 negative fold can be reused without re-authenticating the candidate evidence that proves it

### Finding

The new v2 `CvFoldAcceptance` correctly binds a nonempty `candidate_record_digests` set and records the union of mandatory checkpoint rejection reasons. During fresh execution, `_execute_post_selection_run_locked()` publishes each `Eval2CheckpointRecord`, and `build_cv_fold_acceptance()` verifies the in-memory candidates before constructing `no_admissible_representative`.

Restart reuse takes a weaker path. `_completed_fold_acceptance()` reads the fixed `fold_acceptance.json`, deserializes it, and checks only:

- `run_plan_digest`;
- `cv_plan_digest`;
- `acceptance_metric`; and
- `acceptance_maximum`.

It then returns the fold verdict as complete. It does **not** resolve the v2 `candidate_record_digests` through `context.evidence_store`, authenticate the referenced `Eval2CheckpointRecord` objects, or prove that a `no_admissible_representative` verdict is still backed by a nonempty set in which every candidate is inadmissible and the persisted rejection-reason union agrees with those records.

This matters because current P5 `objects/` is explicitly classified by the storage owner as **durable scientific evidence**, `current=True`, `restart_required=True`, immutable, and hot-path-required for the current generation. Missing/corrupt current candidate evidence is therefore not an allowed cold-storage state. Under the parent workplan's hard-failure invariant and O3/O8, incomplete or unauthenticated bound candidate evidence must fail closed.

A concrete counterexample is presently admissible through the restart path:

```text
1. execute a v2 no-admissible fold successfully;
2. retain its fold_acceptance.json;
3. delete or corrupt one candidate object named by candidate_record_digests;
4. rerun the same current cross-validation;
5. _completed_fold_acceptance() reuses the terminal fold verdict without discovering
   that decisive current evidence is missing/corrupt.
```

That is a D4 recovery/currentness violation under coherent D3, not a reason to weaken the terminal verdict or storage contract.

### Required repair

Repair the existing completed-fold authentication owner. Do not add a new recovery subsystem.

For **current v2** fold acceptances, before returning a persisted fold as reusable:

1. resolve every `candidate_record_digest` from `context.evidence_store` using the canonical `Eval2CheckpointRecord.from_dict` reader so object absence, digest mismatch, or record corruption fails closed;
2. verify the resolved record set is nonempty and contains no duplicate logical/digest identities inconsistent with the persisted verdict;
3. for `no_admissible_representative`:
   - prove every bound candidate record is inadmissible;
   - prove the union of candidate `rejection_reasons` equals the verdict's `checkpoint_rejection_reasons`;
   - prove representative/outer fields remain absent through the existing result constructor invariants;
4. for `representative_selected` v2 records, at minimum prove the bound representative checkpoint record resolves from the candidate set, is admissible, and its stable candidate identity agrees with the persisted representative identity; preserve existing outer-verdict compatibility semantics rather than inventing a second reconstruction path;
5. preserve v1 compatibility exactly: v1 records do not carry `candidate_record_digests`, so do not fabricate them or rewrite historical bytes. Continue the already-supported v1 validation path unless existing authority supplies stronger historical evidence.

If an existing helper can express these checks without duplicated validation logic, reuse it. Otherwise keep the check local to the canonical completed-fold/recovery owner. Do not move scientific thresholds into recovery; recovery authenticates the persisted candidate classification, it does not re-interpret it under a changed policy.

### Required falsification

Add real persistence/recovery tests for current v2 records:

- valid persisted no-admissible fold -> reused without TRAIN2 replacement;
- delete one bound candidate object -> restart hard-fails before treating the fold as completed;
- corrupt one bound candidate object/digest -> restart hard-fails;
- replace/tamper a candidate so it becomes admissible while the fold still claims `no_admissible_representative` -> hard-fail, never reinterpret as rejection;
- tamper the persisted reason union so it disagrees with authentic candidates -> hard-fail;
- representative-selected v2 fold with missing/corrupt representative candidate object -> hard-fail;
- existing representative-bearing v1 fixture remains readable and byte-for-byte reserializable, with no guessed v2 candidate set.

The tests must cross `_completed_fold_acceptance()` / `execute_post_selection_cross_validation()` rather than validating only dataclass constructors.

---

## 3. Blocker R2 — required final executable acceptance is not evidenced, and the stakeholder-shaped regression does not meet the frozen five-fold realization

### Finding

The parent workplan requires the complete affected regression to run after the final executable edit and makes it closeout criterion 13. The remote candidate contains no durable implementation-evidence report, and the GitHub check surface for executable commit `737dd75...` contains only the `Build documentation PDFs` workflow. No Python test, lint, type, package, or affected-regression check is attached to the candidate.

The new focused test module is strong static evidence and covers the result matrix, no-promotion property, threshold preservation, outer-evaluation call count, multi-size continuation, and same-workspace recovery through real mdstats owners with bounded TRAIN2/inference seams. But the review cannot relabel source code containing tests as evidence that those tests executed.

There is also a specific workplan-realization drift. Sections 8.3 and 8.5 freeze a stakeholder-shaped **five-fold / 5-of-5 TRAIN2** recovery proof. The implemented test explicitly reduces this to `_FOLD_COUNT = 4` because the selected fixture exposes only four independent split-exclusion components. Four required folds exercise the generic loop, but it is not the exact frozen acceptance realization and the plan was not amended before implementation to claim equivalence.

This is currently an evidence blocker, not proof of a product defect. Do not change production fold-count semantics to satisfy the test.

### Required repair/evidence

1. Run the complete affected regression from parent Section 9 against the final executable candidate after R1 is repaired. At minimum include:
   - checkpoint admissibility policy/boundary tests;
   - EVAL2 ordering/selection tests;
   - P5-D CV acceptance tests;
   - post-selection execution evidence tests;
   - campaign post-selection runtime tests;
   - TRAIN2/EVAL2 recovery/currentness tests;
   - downstream multi-size integration closure tests;
   - production-authorization barrier tests;
   - verdict persistence/schema/currentness tests;
   - assembled campaign lifecycle tests consuming stored per-size CV verdicts;
   - replay monitor/TRUE_DFT evidence tests.
2. Preserve exact thresholds, tolerances, assertions, and real-owner seams. Do not weaken the oracle to obtain green tests.
3. Close the five-fold stakeholder realization in one of two admissible ways:
   - **preferred:** extend only test data/fixture construction enough to provide five lawful independent fold components and execute the exact 5/5 TRAIN2 -> legacy slot-0 EVAL2 abort -> repaired same-workspace reuse scenario; or
   - if the accepted architecture/test owner demonstrates that the exact count carries no additional semantic or orchestration state and five lawful components cannot be constructed without distorting unrelated science, amend the parent acceptance contract explicitly before claiming closure and provide equivalent parameterized proof across fold counts including a count >=5 through the real owner. Do not silently treat 4 as 5.
4. Record the exact commands, candidate SHA, pass/fail counts, skipped/unavailable items, and any environment-limited qualification. Broad production GPU qualification remains deferred by project policy because this repair does not change GPU-specific behavior.
5. Re-run the final assembled affected regression after the last executable mutation, not merely before R1.

A required check that did not execute is not a pass.

---

## 4. Blocker R3 — lifecycle/project-memory closeout is stale and the active-workplan index contradicts repository state

### Finding

The parent workplan explicitly triggers Project Engineering Memory (PEM), requires reconciliation if the accepted basis advances, and makes a PEM closeout learning assessment criterion 16.

At reviewed head, `PROJECT-ENGINEERING-MEMORY.md` still declares:

- `reconciled_through: b65fa3b02807815d8eca758bc04fb70d514d1f45`;
- accepted base `b65fa3b...`; and
- the preceding `fix/mlff-p5-train2-eval2-cueq-architecture-recurrence` work as a **candidate overlay** with `NT-001` still `REVIEW_REQUIRED` because no independent review had accepted it.

The current parent workplan baseline is later commit `4eabe2ae9783c7ff92f3a1093c37502a01380812`, which already contains the merged preceding CuEq repair and is used by this workplan as evidence that the observed poor metric is genuine rather than a projection defect. The PEM basis/notice is therefore stale for this closeout and has not been reconciled on the implementation branch.

Separately, `workplans/active/README.md` says no MLFF workplan is active and names an older memory-pressure branch even though this directory contains the active parent plan. That is a repository-navigation/documentation contradiction introduced/left unresolved by this cycle.

### Required repair

Perform bounded impact closure; do not manufacture a new PEM family just to record a bug chronology.

1. Reconcile the canonical PEM from the accepted integration basis through `4eabe2ae...`:
   - classify the previously candidate CuEq repair according to its now-accepted repository state and available independent-review evidence;
   - retire/update stale `NT-001` candidate-overlay wording as warranted;
   - refresh `reconciled_through`, accepted-base/candidate-overlay metadata, and materially affected HAS dispositions without rewriting unrelated memory history;
   - for this no-admissible repair, perform the closeout learning assessment. Add/revise a durable family/pattern only if the evidence meets the PEM admission threshold; otherwise explicitly record **no new PEM mutation required for this defect** after the basis reconciliation.
2. Refresh the session/workplan HAS against that reconciled basis. Keep SP-001/SP-004 applicable and FF-001 not-applicable unless new provider-parity evidence contradicts the preceding repair.
3. Update `workplans/active/README.md` so it truthfully points to the active/reopened no-admissible repair and branch. Do not turn the README into parallel authority; it is navigation only.
4. When all executable/evidence blockers close, update/archive the parent/reopen lineage according to repository convention rather than leaving an `ACTIVE / PROPOSED FOR IMPLEMENTATION` plan beside a README claiming there is no active work.

---

## 5. Non-blocking observations

These do not justify additional machinery or a separate repair by themselves:

### N1 — CLI rejection catch is broader than necessary but behaviorally contained

`_campaign_cli_core.main()` catches `ValueError`, then checks `isinstance(exc, PostSelectionCvRejectedError)` and re-raises every other value error. Because the training-data error hierarchy derives from `ValueError`, this works and preserves traceback behavior for non-rejection faults. A direct specific exception catch would be simpler if local import/cycle constraints permit it, but this is not a blocker. Do not create a wrapper merely to change exception syntax.

### N2 — current architecture/manual text does not need a D3 rewrite

Current architecture already requires every frozen selected size to receive its CV verdict before campaign-level reduction and already treats missing/failing required folds as method rejection while production remains fail-closed. The implementation changes a D4 representation/control-flow gap, not the durable D3 meaning. Update human-facing text only where needed to make the new explicit no-admissible outcome discoverable; do not manufacture an architecture revision.

### N3 — schema strategy is directionally correct

Bumping only the fold acceptance schema to v2 while keeping v1 losslessly readable is appropriate because the material shape change is owned by the fold verdict. Parent seed/campaign records retain their structure and deserialize nested fold versions through the canonical reader. Preserve this unless R1 exposes a genuine incompatibility.

---

## 6. Required final regression after R1-R3

After the last executable edit, run the parent Section 9 affected surface plus the new R1 corruption/recovery falsification. In addition, retain these already-good focused checks:

- acceptance matrix A-I;
- property/no-promotion counterfactual;
- zero outer-evaluation calls for no-admissible and one for representative-selected;
- all required sibling folds complete after a methodological rejection;
- both multi-size orderings (rejected first / rejected second);
- same-workspace TRAIN2 reuse with zero replacement jobs for completed first-size folds;
- final-production no-admissible remains a hard failure with no success-shaped run evidence;
- exact threshold boundaries and TRUE_DFT replay semantics unchanged;
- v1 read compatibility and v2 mixed-state rejection.

Run repository-configured formatting/static checks affected by edited files. If no repository-wide CI exists for Python, durable local execution evidence is acceptable, but it must name the exact final candidate SHA and command/results. Source presence is not execution evidence.

---

## 7. Reopen/escalation conditions

### Keep this at D4 if

R1 can be closed by strengthening the existing completed-fold/current evidence authentication path, R2 by executing/closing required acceptance, and R3 by bounded lifecycle/documentation reconciliation. That is the expected outcome.

### Serious Challenge / D3 reopen only if

Evidence proves one of the parent Section 13 D3 conditions, especially that current architecture intentionally treats an all-inadmissible fold as a global execution abort, or that current durable persistence cannot represent/authenticate a negative fold without changing architecture ownership/external compatibility.

### D2/D1 escalation only if

New evidence shows the 0.030 target threshold, replay-retention ceiling, TRUE_DFT replay requirement, physical gates, target-only ordering, or other scientific/numerical semantics are themselves wrong. Do not infer this from a rejected trained method.

### Preceding TRAIN2/EVAL2 identity-family reopen only if

Fresh parity/authentication evidence demonstrates that the candidate metrics are wrong because provider/model realization has diverged again. Poor metrics alone are not such evidence.

---

## 8. Review closure criteria

This reopened review can PASS only when all parent closeout criteria remain true and additionally:

1. current v2 persisted fold verdicts re-authenticate the bound candidate evidence needed to prove their outcome before restart reuse;
2. missing/corrupt/inconsistent v2 candidate evidence fails hard and is not translated into a scientific rejection or accepted as a completed cached fold;
3. valid persisted negative folds still reuse completed TRAIN2 and do not schedule unnecessary replacement training;
4. the exact five-fold stakeholder-shaped regression is executed, or the acceptance contract is explicitly and legitimately amended with stronger equivalent evidence before closure;
5. the complete affected regression passes on the final executable candidate and is recorded with exact SHA/commands/results;
6. no new duplicate result/reducer/recovery/status/persistence machinery is introduced;
7. the accepted PEM basis and materially affected notice/HAS state are reconciled, with a justified new-memory update or explicit no-new-family outcome;
8. `workplans/active/README.md` and the plan lifecycle truthfully reflect the active/reopened/closed state;
9. generated documentation remains synchronized after any source-doc mutation;
10. no Serious Challenge emerges.

Until those conditions are met, the workplan remains **NO-PASS / REOPENED**.
