# MLFF P5 CV no-admissible-checkpoint outcome representation repair workplan

**Status:** ACTIVE / REOPENED — independent review NO-PASS in `MLFF_P5_CV_NO_ADMISSIBLE_CHECKPOINT_OUTCOME_REPAIR_IMPLEMENTATION_REVIEW_REOPEN.md`; blockers R1-R3 implemented (see `MLFF_P5_CV_NO_ADMISSIBLE_CHECKPOINT_OUTCOME_REPAIR_IMPLEMENTATION_EVIDENCE.md`), awaiting independent re-review  
**Protocol:** SSDP 6.3  
**Repository:** `hjin98/mdstats`  
**Branch:** `fix/mlff-p5-cv-no-admissible-outcome-repair`  
**Accepted project baseline:** `4eabe2ae9783c7ff92f3a1093c37502a01380812`  
**Problem class:** P5 post-selection CV valid methodological rejection is unrepresentable when no checkpoint passes mandatory admissibility  
**Earliest affected semantic level:** D4 implementation/concretization under coherent accepted D3 post-selection CV architecture  
**Current Serious Challenge:** NONE

---

## 1. Problem statement and observed failure

A real `cross-validate` run completed all five TRAIN2 fold runs for the first frozen selected size and entered serial EVAL2. EVAL2 then stopped at slot 0 with:

```text
PostSelectionError: No CV fold checkpoint passed mandatory admissibility;
rejection reasons: ['replay_retention_ceiling_exceeded', 'target_threshold_exceeded'].
An inadmissible checkpoint is never promoted to a fold representative.
```

The observed scientific rejection reasons are produced by the existing mandatory checkpoint-admissibility policy. At the accepted baseline:

- target checkpoint admissibility has a default maximum target force RMSE of `0.030 eV/Å`;
- true-DFT replay retention is a mandatory constraint when replay is enabled;
- replay receives no checkpoint-ranking credit;
- a checkpoint that violates target, replay, or physical admissibility is ineligible for fold-representative selection;
- a fold with one or more admissible checkpoints selects among only those admissible checkpoints using the frozen target-only ordering.

The immediately preceding P5 TRAIN2/EVAL2 repair independently demonstrated that this exact stakeholder outcome can be scientifically real rather than an evaluation-projection defect: the trained checkpoint/provider path matched the dependency model to the required numerical tolerance while target force RMSE remained materially above the frozen admissibility maximum. Therefore this cycle SHALL NOT weaken the scientific gate merely to make the run proceed.

The defect is representational and control-flow related:

```text
valid TRAIN2 fold execution
 -> nonempty checkpoint-candidate evidence
 -> mandatory EVAL2 admissibility classification
 -> zero admissible candidates
 -> valid scientific rejection of this fold
```

is currently forced through a success-shaped fold contract that assumes a representative checkpoint exists. The implementation therefore throws an execution-style exception before the valid methodological rejection can reach the fold, size, and campaign reducers.

The intended state flow is:

```text
valid fold execution
 -> checkpoint-candidate evidence
 -> if >=1 admissible:
      select representative
      held-out outer evaluation
      accepted/rejected fold verdict
 -> if 0 admissible:
      rejected fold verdict
      no representative
      no held-out outer evaluation
```

A nonempty evaluated candidate set with zero admissible checkpoints is a valid negative CV outcome. An empty candidate set remains an execution/evidence failure.

---

## 2. Governing authority and preserved invariants

### 2.1 Current owners

Implementation SHALL resolve and obey the accepted-current owners at the baseline, including at minimum:

- `docs/arch_manuals/mlff_training_data/50_target_size_selection.md` for post-selection CV collection semantics;
- `mdstats/training_data/train2_policy.py` for checkpoint admissibility policy and rejection reasons;
- `mdstats/training_data/post_selection_cv_acceptance.py` for checkpoint ordering, representative selection, fold verdict, and campaign reduction semantics;
- `mdstats/training_data/campaign_post_selection_runtime.py` for TRAIN2/EVAL2 orchestration, recovery, fold completion, size sequencing, and publication;
- `mdstats/training_data/post_selection_execution.py` for generic successful post-selection run evidence and final-production evidence contracts;
- current persistence/currentness owners for stored P5 CV evidence;
- current multi-size downstream integration and production-authorization barriers.

Historical workplans and qualification reports are evidence/provenance, not current normative authority.

### 2.2 D1/D2/D3 invariants that SHALL NOT change

This is not a scientific-method or numerical-method retuning cycle. Preserve all of the following:

1. **Mandatory checkpoint admissibility remains mandatory.** Do not change the target threshold, replay-retention budget, physical gate, or true-DFT replay requirement to create a representative.
2. **No inadmissible checkpoint promotion.** A checkpoint failing any mandatory gate remains ineligible to become a fold representative under every path, including recovery and compatibility paths.
3. **Target-only checkpoint ranking remains unchanged.** Replay remains a hard constraint with zero ranking credit after admissibility filtering.
4. **Outer-fold isolation remains unchanged.** Held-out outer evaluation occurs only after a valid representative has been frozen and may not leak into checkpoint selection.
5. **Every required fold/seed remains required.** A valid scientific rejection is a completed negative verdict, not permission to omit a required fold.
6. **Every frozen selected size receives its own CV verdict.** A methodological rejection for one size is recorded and remaining frozen sizes continue to CV so the operator-requested frozen collection is completed.
7. **Campaign acceptance remains conjunctive over required accepted size verdicts.** One valid rejected size means the overall post-selection CV campaign rejects and production remains unauthorized.
8. **Hard failures remain fail-fast.** Missing/corrupt evidence, lineage failure, authority mismatch, persistence corruption, impossible state, or other execution/integrity failures are not converted into scientific rejection merely to continue the campaign.
9. **Recovery remains content/authority preserving.** Valid completed TRAIN2 work is reused; scientific rejection does not trigger unnecessary retraining.
10. **Generic successful-run evidence remains strict where possible.** Do not weaken final-production or generic `PostSelectionRunEvidence` by making representative/checkpoint fields nullable solely to represent this CV-only rejection state if the CV verdict/result layer can own the negative state cleanly.

### 2.3 Accepted architectural interpretation

Current D3 already requires completion of each frozen size's CV verdict before campaign-level methodological reduction. Therefore:

```text
coherent D3 + D4 cannot encode a valid negative fold state -> D4 blocker
```

There is no Serious Challenge to D3 at plan acceptance. Reopen D3 only if implementation evidence proves that current architecture actually requires all-inadmissible fold outcomes to abort the frozen-size collection or that no lossless negative fold representation is possible without changing durable architecture semantics.

---

## 3. Historical applicability and recurrence context

This task materially depends on recent project history because the preceding repair independently classified the same stakeholder EVAL2 outcome as a genuine trained-method rejection rather than a provider/projection defect, and current multi-size integration work explicitly requires later selected sizes to continue after a methodological rejection.

Use the canonical root `PROJECT-ENGINEERING-MEMORY.md` from the exact accepted/base project state and reconcile it if the accepted basis advances before closeout. The current decision-level HAS SHALL include at least:

```yaml
pem_basis:
  accepted_project_state: 4eabe2ae9783c7ff92f3a1093c37502a01380812
  accepted_pem: "hjin98/mdstats@4eabe2ae9783c7ff92f3a1093c37502a01380812:PROJECT-ENGINEERING-MEMORY.md (published still declaring the b65fa3b basis and NT-001 REVIEW_REQUIRED)"
  candidate_overlay_semantic_candidate: "fix/mlff-p5-cv-no-admissible-outcome-repair: basis reconciled through 4eabe2ae (NT-001 retired after the CuEq repair's PASS closure and merge; FF-001 coverage refreshed without a new occurrence)"
  closeout_learning_assessment: "No new PEM family, occurrence, or application episode for this defect. It is a first local D4 representation/control-flow gap with no recurrence signal; possible SP-001/SP-002/SP-003/SP-004 application episodes are not recorded while the repair is unaccepted and may be assessed at acceptance."
has:
  - id: SP-004-real-owner-integration
    disposition: APPLICABLE
    reason: The defect escaped narrower unit seams and is visible at the real TRAIN2 -> EVAL2 -> CV reduction boundary.
  - id: SP-001-reduce-duplicated-machinery
    disposition: APPLICABLE
    reason: Repair should alter the canonical CV outcome contract rather than add a parallel exception/status/reconciliation subsystem.
  - id: FF-001-realized-model-identity-drift
    disposition: NOT_APPLICABLE
    reason: The preceding qualified repair established provider/model projection parity for this exact scientific rejection family; current failure occurs after valid candidate metric evaluation. Re-confirmed against the reconciled basis; no new provider-parity evidence contradicts it.
```

If exact entry identifiers differ in the baseline PEM, preserve the same material dispositions using the canonical IDs actually present. Do not create permanent memory entries merely because this is a bug; closeout learning determines whether evidence justifies a new/revised family.

---

## 4. Root cause classification

### 4.1 Confirmed current defect

At the accepted baseline:

- `select_cv_fold_representative(...)` correctly refuses to promote inadmissible candidates but raises `PostSelectionError` when the admissible ordering is empty;
- the canonical fold acceptance representation requires representative identity/digest and held-out outer metric evidence;
- `_execute_post_selection_run_locked(...)` and its callers are structured around returning a representative and later building success-shaped fold acceptance;
- the campaign/size reducer can represent a rejected fold only after a representative and outer evaluation exist;
- therefore the valid state `nonempty candidates + all inadmissible` cannot reach the canonical reducer as a fold verdict.

The mandatory gate is correct. The missing capability is a first-class, lossless negative fold result before representative selection.

### 4.2 Distinguish three materially different outcomes

Implementation MUST preserve this partition:

| Candidate-stage result | Meaning | Required control result |
|---|---|---|
| zero checkpoint candidates | missing execution/evidence | hard failure |
| one or more candidates, zero admissible | valid methodological rejection | completed rejected fold verdict |
| one or more admissible candidates | representative selection possible | select representative, run outer evaluation, then accepted/rejected fold verdict |

Do not collapse the first two cases.

---

## 5. Cycle-scoped design decisions

These decisions are frozen for this implementation cycle unless reopened by the evidence conditions in Section 13.

### F1 — zero admissible candidates is a valid fold rejection

Once the candidate set is nonempty and each candidate has valid authenticated monitor/admissibility evidence, the absence of any admissible candidate is a scientific verdict for the fold, not an execution exception.

### F2 — no synthetic representative

The negative fold state SHALL contain no representative checkpoint identity, no representative record digest, and no held-out outer metric pretending to belong to a representative. Sentinel checkpoint IDs, “best rejected” promotion, threshold bypasses, or placeholder outer metrics are forbidden.

### F3 — outer evaluation requires a representative

Held-out outer evaluation SHALL be skipped when no admissible representative exists. The observable proof is zero outer-evaluation calls for an all-inadmissible fold.

### F4 — fold reduction consumes valid negative verdicts

A no-admissible-representative fold counts as a present/completed fold verdict whose acceptance is false. It SHALL NOT be reinterpreted as a missing fold or absent evidence by the fold/size reducer.

### F5 — completed sibling folds remain useful evidence

After one fold is scientifically rejected, remaining required folds for that frozen size continue to evaluation unless a genuine hard failure occurs. This preserves complete required-fold evidence and prevents the first rejection from masking additional defects or outcomes.

### F6 — later frozen sizes continue

After a size obtains a valid rejected CV verdict, the orchestrator records/publishes that size verdict and continues every remaining frozen selected size. Campaign reduction happens only after every frozen size has either a valid CV verdict or a genuine hard failure has stopped execution.

### F7 — recovery reuses completed TRAIN2

If TRAIN2 is already valid and complete while the fold lacks a persisted CV verdict, recovery resumes at EVAL2/candidate classification and SHALL NOT schedule retraining merely because the old implementation previously threw at no-admissible selection.

### F8 — one canonical CV outcome representation

Repair the existing CV verdict/result owner so it can express the two legitimate result shapes:

```text
REPRESENTATIVE_SELECTED
NO_ADMISSIBLE_REPRESENTATIVE
```

Names are delegated D4 detail; semantics are not. Do not create a second persistent status subsystem, shadow reducer, wrapper exception taxonomy, or duplicate database solely for this distinction.

### F9 — generic success evidence remains success-shaped

Keep generic/final-production execution evidence representative-bearing unless current owner analysis proves it is itself the canonical CV verdict owner. Prefer a CV-specific negative verdict over making downstream production success records nullable.

---

## 6. Canonical result invariants

The implemented canonical fold result SHALL enforce construction-time invariants equivalent to the following.

### 6.1 Representative-selected result

Required:

- nonempty candidate evidence;
- at least one admissible candidate;
- selected representative candidate identity;
- selected checkpoint record digest and checkpoint identity/hash as currently required;
- held-out outer metric evidence;
- final fold accepted/rejected result according to existing outer acceptance policy;
- all current provenance/currentness/lineage bindings.

Forbidden:

- representative identity that refers to an inadmissible candidate;
- missing outer metric evidence;
- candidate rejection summary inconsistent with the selected candidate.

### 6.2 No-admissible-representative result

Required:

- nonempty candidate evidence;
- authenticated evidence that every candidate was classified and rejected by mandatory admissibility;
- deterministic rejection-reason summary preserving the actual reason set across candidates;
- final fold acceptance `false`;
- all current fold/run/seed/size/method/provenance/currentness bindings needed to identify the completed fold.

Must be absent:

- representative candidate identity;
- representative checkpoint-record digest;
- representative checkpoint hash/path as a promoted representative;
- held-out outer metric record/digest/value.

Any mixed state such as `NO_ADMISSIBLE_REPRESENTATIVE` plus representative/outer evidence MUST fail validation rather than be normalized silently.

### 6.3 Hard-failure states are not persisted as scientific verdicts

Examples include:

- no checkpoint candidates were produced;
- candidate evidence is malformed, unauthenticated, stale, lineage-mismatched, or incomplete;
- rejection reason cannot be derived under the frozen policy;
- a supposedly admissible representative cannot be authenticated;
- persistence/currentness contract fails;
- outer evaluation fails after a representative has been selected.

These remain execution/integrity errors and may abort immediately.

---

## 7. Required implementation obligations

### O1 — separate admissibility classification from representative selection failure

Refactor the existing CV selection owner so callers can distinguish:

```text
nonempty evaluated candidates + no admissible candidate
```

from actual invalid/missing candidate evidence.

This may be implemented by returning a canonical classified result, an explicit optional representative plus classification, or another simpler local concretization. The forbidden outcome is preserving the generic exception as the only signal and catching/parsing it higher in the stack.

Exception-message parsing, special-case matching on `target_threshold_exceeded`, or catching broad `PostSelectionError` to fabricate rejection is not acceptable.

### O2 — extend the canonical fold verdict/result representation

Modify the existing owner in `post_selection_cv_acceptance.py` or its true canonical equivalent so both result shapes in Section 6 are representable and validated.

Prefer conditional fields under one authoritative result rather than parallel “success” and “rejection” schemas that duplicate fold identity/provenance/reduction fields.

### O3 — preserve candidate-stage evidence losslessly

For a no-admissible result, preserve enough durable evidence to establish:

- which fold/seed/selected size/method was evaluated;
- that the candidate set was nonempty;
- candidate identity/evidence needed by current audit/currentness semantics;
- that each candidate failed mandatory admissibility;
- the exact frozen policy identity/digest if currently persisted;
- the union or canonical structured summary of actual rejection reasons;
- no representative was selected.

Do not persist a lossy single generic reason if candidates can fail different mandatory gates and current evidence already contains the distinctions.

### O4 — propagate the negative state through EVAL2 runtime without outer evaluation

Update `campaign_post_selection_runtime.py` or the current canonical runtime owner so:

1. candidate metrics/evidence are produced normally;
2. all-inadmissible classification returns a valid negative fold result;
3. no held-out outer evaluation is attempted;
4. cleanup/device-lifetime behavior remains identical to normal EVAL2 completion/failure ownership;
5. the fold result is made available to the reducer and persistence path;
6. subsequent required fold slots continue.

No extra scheduler/resource state machine is justified for this repair.

### O5 — make fold/size reducers treat the negative state as present evidence

The reducer SHALL count a no-admissible fold as a completed required fold with acceptance false. It may reject the size only after the currently required fold-completion semantics are satisfied.

Do not let optional representative fields accidentally drive “missing fold” logic.

### O6 — preserve multi-size collection semantics

The outer `execute_current_cross_validate` path SHALL:

- persist/publish the valid rejected size verdict;
- continue later frozen sizes;
- preserve accepted size verdicts that follow or precede the rejection;
- reject the overall campaign after all frozen-size methodological verdicts are complete;
- keep production authorization closed when any required size rejects.

### O7 — preserve same-workspace recovery

For the stakeholder-shaped recovery state:

```text
TRAIN2 5/5 complete and valid
EVAL2 fold verdict absent because prior implementation aborted at slot 0
```

repaired code SHALL reuse the completed TRAIN2 state and resume EVAL2 classification. It must not delete/retrain the five fold runs merely because the prior executable could not represent the negative result.

If old partial EVAL2 artifacts are present, classify them using current currentness/authority rules. Reuse only evidence that is valid under the repaired contract; recompute bounded EVAL2 evaluation where necessary, but preserve valid TRAIN2.

### O8 — persistence/version compatibility is explicit

Inspect whether the fold verdict/result is persisted durably and whether the changed shape modifies an on-disk schema.

- If the current persisted schema already supports absent representative/outer fields with explicit outcome semantics, use it and tighten validation.
- If the schema materially changes, increment the owning schema/version according to existing repository convention.
- Readers MUST continue to read previously valid representative-bearing records losslessly.
- Do not rewrite historical accepted records merely to adopt the new representation.
- A previously persisted malformed/ambiguous record that cannot prove its outcome remains invalid; compatibility is not permission to guess.
- Do not introduce a migration database or second sidecar registry when the existing record can be versioned directly.

### O9 — operator diagnostics distinguish science from execution failure

For a no-admissible fold, user-facing output SHALL report it as a methodological rejection with the actual mandatory rejection reasons and fold/size identity. It SHALL not emit a traceback unless a separate hard failure occurs.

Use the existing reporting owner. Do not add a second log/report subsystem.

### O10 — update the misleading unit oracle

The existing unit test that requires `select_cv_fold_representative(...)` itself to throw whenever all candidates are inadmissible encodes the current implementation limitation as normative behavior. Replace/refactor that oracle so it protects the real invariant:

```text
no inadmissible candidate may become representative
```

while permitting the canonical caller/result owner to produce a valid negative fold verdict.

### O11 — no method/policy drift

Add explicit regression that the exact target/replay/physical boundary behavior in `train2_policy.py` is unchanged. A repair that passes by changing `0.030`, comparison operators, replay-budget interpretation, true-label replay requirement, or target-only ranking is a failure.

---

## 8. Acceptance and falsification matrix

The implementation is not complete until the assembled behavior proves every row below at the real owner boundary appropriate to the row.

| Case | Candidate state | Representative | Outer eval | Fold result | Execution result |
|---|---|---:|---:|---|---|
| A | >=1 admissible; outer passes | yes | yes | accepted | continue |
| B | >=1 admissible; outer fails acceptance | yes | yes | valid rejected | continue methodological collection |
| C | nonempty; all fail target threshold | no | no | valid rejected | continue |
| D | nonempty; all fail replay retention | no | no | valid rejected | continue |
| E | nonempty; failures include target + replay across candidates | no | no | valid rejected preserving both reason classes | continue |
| F | nonempty; all fail physical admissibility | no | no | valid rejected | continue |
| G | zero candidates | no | no | none | hard failure |
| H | corrupt/unauthenticated candidate evidence | no | no | none | hard failure |
| I | representative selected, outer evaluation crashes/corrupts | yes | attempted | none | hard failure |

### 8.1 Required counterfactual: no promotion

Construct at least one case where an inadmissible candidate has numerically better target ranking than an admissible candidate. Prove the inadmissible candidate is never selected.

For the all-inadmissible case, prove no candidate identity appears in representative-bearing fields merely because one candidate is “least bad.”

### 8.2 Outer-evaluation call-count proof

Instrument the real outer-evaluation seam in test scope and prove:

```text
all-inadmissible fold -> outer evaluation call count == 0
representative-selected fold -> outer evaluation call count == 1
```

Do not satisfy this with a test-double-only helper that bypasses the runtime owner.

### 8.3 Complete-fold reduction proof

For a required five-fold size, create a bounded real-owner integration where one early fold is all-inadmissible and later folds are executable. Prove:

- all five fold verdicts are completed/persisted unless a true hard failure is injected;
- the rejected fold is counted as present;
- the size verdict is rejected;
- no missing-fold error is manufactured from absent representative fields.

### 8.4 Multi-size order-independence proof

Using the actual `execute_current_cross_validate` path and a frozen two-size selection, prove both orderings:

```text
N1 = valid no-admissible rejection; N2 = valid acceptance
N1 = valid acceptance; N2 = valid no-admissible rejection
```

For each ordering:

- both size CV verdicts are produced/published;
- the second size actually executes rather than being skipped by the first scientific rejection;
- overall campaign rejects;
- production remains unauthorized.

### 8.5 Stakeholder-shaped same-workspace recovery regression

Create/reuse a fixture representing:

```text
5/5 TRAIN2 runs complete
0 TRAIN2 failures
EVAL2 has not produced a fold verdict because legacy execution stopped at slot 0
```

Then prove repaired execution:

1. admits/reuses all five valid TRAIN2 runs;
2. schedules zero replacement TRAIN2 jobs;
3. enters EVAL2;
4. records the all-inadmissible fold as a valid rejection;
5. completes the remaining fold verdicts for that selected size;
6. continues the later frozen selected size;
7. performs final campaign reduction only after methodological collection completion.

GPU execution is not required for this cycle unless the implementation changes GPU-specific behavior. Preserve the project policy of deferring broad GPU qualification to final release; the repair should be covered through CPU/control-path and existing qualified dependency/model seams unless a material GPU-only behavior is changed.

### 8.6 Persistence compatibility proof

If a durable schema changes:

- read a representative-bearing pre-change fixture successfully;
- write/read the new no-admissible result;
- reject an invalid mixed-state record;
- prove currentness/digest/identity checks remain active;
- prove old records are not rewritten as part of read compatibility.

If no durable schema changes, record evidence that the existing schema already lawfully represents the new state and why no migration/version bump is required.

### 8.7 Threshold boundary preservation

Retain/add exact boundary tests for target and replay admissibility around the current comparisons. The implementation must not “fix” this issue by moving a scientific boundary.

---

## 9. Required affected regression surface

At minimum, inspect and run the materially affected portions of:

- checkpoint admissibility policy tests;
- EVAL2 admissible ordering/selection tests;
- P5-D/post-selection CV acceptance tests;
- post-selection execution evidence tests;
- campaign post-selection runtime tests;
- TRAIN2/EVAL2 recovery/currentness tests;
- downstream multi-size integration closure tests;
- production-authorization barrier tests;
- persistence/schema/currentness tests for the changed verdict representation;
- assembled campaign lifecycle tests that consume stored per-size CV verdicts;
- replay monitor/true-DFT evidence tests to confirm the scientific constraint remains intact.

Run the complete affected regression after the final executable edit, not only stage-local tests from earlier intermediate states.

Do not weaken assertions, tolerance, threshold, fold count, or real-owner integration scope merely to obtain green tests.

---

## 10. Implementation staging

### Stage P1 — outcome contract

Modify the canonical checkpoint-classification/fold-result owner so the three-way partition in Section 4.2 is explicit and construction invariants in Section 6 are enforceable.

**Stage exit evidence:** unit/owner tests for cases A-H at the result/selection boundary, including no-promotion and mixed-state rejection.

### Stage P2 — runtime propagation and reduction

Wire the negative result through EVAL2, fold completion, size acceptance, and campaign orchestration. Skip outer evaluation when no representative exists; continue sibling folds and later frozen sizes for methodological rejection.

**Stage exit evidence:** runtime integration for complete-fold reduction and both multi-size orderings.

### Stage P3 — recovery and persistence compatibility

Close same-workspace recovery and any durable schema/currentness obligations. Preserve valid completed TRAIN2 and old representative-bearing records.

**Stage exit evidence:** stakeholder-shaped recovery plus persistence compatibility matrix.

### Stage P4 — assembled regression and impact closure

Run complete affected regression, verify scientific-policy immutability, reconcile documentation/test oracles/currentness/PEM impact, and perform simplification review.

**Stage exit evidence:** no remaining blocking drift and no new duplicate status/reducer/persistence machinery.

Stages may be combined if the implementation is smaller than the decomposition, but stage-local acceptance obligations may not be deferred or omitted.

---

## 11. Non-goals

This workplan does not authorize:

- retuning target error or replay-retention thresholds;
- changing scientific fold counts, seeds, horizons, selected sizes, or target-size selection;
- changing true-label replay membership or label authority;
- changing model architecture, optimizer, loss, learning rate, EMA, precision, or training exposure;
- redesigning TRAIN2 scheduling or GPU concurrency;
- changing CuEq/e3nn projection/authentication semantics already qualified in the preceding repair;
- automatically choosing a different selected size because one frozen size rejects;
- production authorization after a rejected required size;
- adding a generic retry/fallback around scientific rejection;
- introducing a new orchestration database/status service/event bus;
- broad schema migration unrelated to the directly affected CV verdict record.

---

## 12. Forbidden repair strategies and simplification trigger

Reject an implementation that adds any of the following when existing ownership can be altered directly:

- fake/sentinel representative checkpoints;
- “best rejected checkpoint” promotion;
- threshold relaxation or conditional bypass;
- generic exception catches that translate `PostSelectionError` text into scientific verdicts;
- special cases for `N_selected=512` or a specific horizon;
- a second fold-result type with duplicated identity/provenance/reduction machinery when conditional state under the canonical result is sufficient;
- a second reducer for no-admissible folds;
- sidecar reconciliation records or migration databases;
- retraining as a workaround for already-valid completed TRAIN2;
- wrappers around existing persistence solely to encode nullability.

If implementation begins requiring several compatibility wrappers, duplicated synchronized state, sentinel identities, exception parsing, or a second reducer/status owner, stop and re-derive the simpler canonical result flow before proceeding.

---

## 13. Reopen and escalation conditions

### 13.1 Reopen D3 only if

- accepted architecture actually requires an all-inadmissible fold to abort the entire frozen-size collection rather than produce a rejected fold verdict;
- current per-fold/per-size persistence semantics cannot represent a valid negative verdict without changing durable architecture ownership or external compatibility guarantees;
- completion of remaining folds after a scientific rejection conflicts with another accepted current architecture owner;
- the campaign-level “evaluate every frozen size before methodological reduction” invariant is found contradictory or unrealizable under current authority.

### 13.2 Route upstream to D2/D1 only if

Evidence shows the frozen scientific admissibility semantics themselves are wrong, e.g. the `0.030` target threshold, replay-retention ceiling, true-DFT replay constraint, or target-only selection objective must scientifically change. Do not make that change inside this D4 repair.

### 13.3 Reopen the preceding TRAIN2/EVAL2 identity family only if

Fresh evidence shows candidate metrics are wrong because provider/model projection/authentication has again diverged. A merely poor metric value is not sufficient; require actual parity/authentication evidence of divergence.

---

## 14. Completion and closeout criteria

This workplan may be closed only when all of the following are true:

1. a nonempty all-inadmissible candidate set produces a canonical rejected fold verdict without a traceback;
2. no inadmissible checkpoint can be promoted to representative;
3. no held-out outer evaluation runs without a representative;
4. zero candidate evidence still hard-fails;
5. required sibling folds continue after a valid scientific rejection;
6. later frozen selected sizes continue after a rejected size;
7. overall campaign rejects if any required size rejects;
8. production authorization remains fail-closed;
9. completed valid TRAIN2 is reused across the stakeholder-shaped recovery path with zero unnecessary replacement TRAIN2 jobs;
10. persistence compatibility/currentness obligations are satisfied and explicitly evidenced;
11. target/replay/physical scientific policy and boundary behavior are unchanged;
12. the misleading unit oracle has been corrected to test the real invariant rather than the old exception shape;
13. complete affected regression passes on the final assembled candidate;
14. no duplicate status/reducer/persistence machinery was introduced where alteration of the existing owner suffices;
15. documentation/current architecture remains accurate without unnecessary D3 mutation;
16. PEM closeout learning assessment is performed against the accepted integration basis.

If the closeout learning assessment finds a reusable new family, update PEM with evidence-backed causal scope. Otherwise record no PEM mutation rather than manufacturing project memory from one repaired defect.

---

## 15. Expected implementation center of gravity

The highest-priority implementation surface is the CV outcome contract spanning:

- `mdstats/training_data/post_selection_cv_acceptance.py`; and
- `mdstats/training_data/campaign_post_selection_runtime.py`.

`mdstats/training_data/train2_policy.py` is primarily a preservation/verification surface, not the expected repair owner. `PostSelectionRunEvidence` in `post_selection_execution.py` should remain strict if possible; alter it only if owner analysis proves it is the canonical fold-verdict representation rather than generic successful-run evidence.

The preferred repair is therefore a direct correction of the existing CV classification/result/reduction flow, with the minimum persistence change required to represent a valid negative fold outcome losslessly.
