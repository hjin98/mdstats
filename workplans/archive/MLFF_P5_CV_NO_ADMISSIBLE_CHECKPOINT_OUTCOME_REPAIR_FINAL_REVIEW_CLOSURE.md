---
kind: implementation-workplan-final-review-closure
workplan_id: MLFF-P5-CV-NO-ADMISSIBLE-CHECKPOINT-OUTCOME-REPAIR-FINAL-REVIEW-CLOSURE
parent_workplan: workplans/archive/MLFF_P5_CV_NO_ADMISSIBLE_CHECKPOINT_OUTCOME_REPAIR_WORKPLAN.md
predecessor_review: workplans/archive/MLFF_P5_CV_NO_ADMISSIBLE_CHECKPOINT_OUTCOME_REPAIR_IMPLEMENTATION_REVIEW_REOPEN.md
implementation_evidence: workplans/archive/MLFF_P5_CV_NO_ADMISSIBLE_CHECKPOINT_OUTCOME_REPAIR_IMPLEMENTATION_EVIDENCE.md
protocol_version: 6.3.0
status: closed-pass
review_verdict: pass
implementation_branch: fix/mlff-p5-cv-no-admissible-outcome-repair
accepted_project_baseline: 4eabe2ae9783c7ff92f3a1093c37502a01380812
reviewed_executable_candidate: abf45c050ad49a0f4eda92526c886584f919c19e
reviewed_branch_head_before_closure: b5d101d8f73d3efd63ef4e70b3913e7d281406ce
predecessor_reopen_commit: eae364b1cfaba77332ed15a6f635c80a3922c1a3
highest_affected_domain: D4 implementation/concretization and persistence/recovery closure under unchanged accepted D3 post-selection CV architecture
serious_challenge: none
precedence: This independent SSDP 6.3 closure supersedes the ACTIVE/REOPENED lifecycle states recorded in the parent/reopen/evidence snapshots. Those files are archived historical coordination/evidence after this closure. Accepted current product semantics remain owned by the permanent MLFF architecture/specification authorities.
---

# P5 CV no-admissible-checkpoint outcome repair — final SSDP 6.3 Review closure

## 0. Disposition

**PASS / CLOSED.** No genuine blocking issue remains on executable candidate `abf45c050ad49a0f4eda92526c886584f919c19e`; branch head `b5d101d8f73d3efd63ef4e70b3913e7d281406ce` adds only PEM/workplan/evidence reconciliation after that executable candidate.

No Serious Challenge is active. D1 scientific formulation, D2 numerical/training-method semantics, and accepted D3 post-selection architecture remain coherent and unchanged. The original defect was correctly classified as D4: a valid scientific state, `nonempty checkpoint candidates + zero admissible`, could not be represented by the success-shaped fold result and therefore escaped as an execution exception.

The final implementation repairs that state at the canonical CV result and recovery owners. It does not relax the scientific gate, promote an inadmissible checkpoint, create a fallback representative, add a shadow reducer/status store, or weaken final-production evidence.

## 1. Governing invariants and final implementation

The final candidate preserves the parent workplan's protected semantics:

1. zero checkpoint candidates remain a hard evidence/execution failure;
2. a nonempty all-inadmissible candidate set is a completed rejected CV fold;
3. no inadmissible checkpoint can become the fold representative;
4. replay remains a hard admissibility constraint with zero ranking credit;
5. checkpoint ranking among admissible candidates remains target-only;
6. held-out outer evaluation occurs only after a representative is frozen;
7. every required fold/seed and every frozen selected size remains required;
8. one rejected required size rejects the overall campaign and production remains unauthorized;
9. completed valid TRAIN2 is reused across restart rather than retrained solely because a prior executable could not encode the negative fold result;
10. generic/final-production run evidence remains success-shaped.

The canonical fold schema directly represents `representative_selected` and `no_admissible_representative`. The latter carries nonempty candidate-record digests and mandatory-rejection reason evidence while representative and outer-evaluation fields are absent. Historical v1 representative-bearing fold records remain losslessly readable and are not rewritten as v2.

The scientific boundaries remain exactly the accepted ones: target force RMSE maximum `0.030 eV/Angstrom`, replay degradation budget `0.030 eV/Angstrom`, authenticated `true_dft` replay requirement, strict `>` threshold comparisons, and the existing physical-gate semantics. No target-size, fold, seed, horizon, optimizer, model, precision, replay-exposure, or scheduler semantics were changed to obtain the result.

## 2. Predecessor Review blocker R1 — CLOSED

The predecessor review found that a persisted v2 negative fold verdict could be reused without re-authenticating the candidate records that actually proved it.

The final candidate alters the existing `_completed_fold_acceptance()` owner directly. For a v2 verdict it now resolves every `candidate_record_digest` through the current content-addressed evidence store with `Eval2CheckpointRecord.from_dict`; missing or corrupt objects therefore fail at the canonical store/record boundary. It then requires the resolved records to reproduce the persisted classification:

- candidate rejection-reason union equals `checkpoint_rejection_reasons`;
- `no_admissible_representative` has no admissible candidate;
- `representative_selected` resolves the bound representative candidate, requires it to be admissible, and requires stable candidate identity agreement.

A mismatch raises `PostSelectionError`; it is never translated into a methodological rejection. v1 verdicts continue their existing compatibility path and no candidate set is guessed for them.

This is the requested reduction-oriented repair: one existing recovery owner was strengthened. No sidecar registry, migration database, second recovery state machine, retry wrapper, or exception-text parser was introduced.

The added real-owner restart falsification covers deletion and digest corruption of no-admissible candidate evidence, a forged admissible candidate, a tampered reason union, deletion/corruption of a selected representative, and valid v2-negative/v1-selected reuse without retraining or rewriting v1 bytes. The implementation evidence also records the discriminating mutation check: reverting only the R1 runtime change makes the six tamper cases fail; restoring it makes them pass.

## 3. Predecessor Review blocker R2 — CLOSED

The exact five-fold acceptance realization is restored without changing production semantics. The former size-8 test fixture had only four independent split-exclusion components, so the test fixture now expands only its qualified size ladder and explicitly freezes sizes 16 and 32 through the real selection owner, each lawfully supporting `K=5`.

The assembled focused regressions therefore exercise the exact requested shape:

- one required five-fold size with an early all-inadmissible fold still persists all five fold verdicts, runs zero outer evaluation for the rejected fold and one for each representative-selected sibling, then rejects the size;
- stakeholder-shaped same-workspace recovery first completes 5/5 TRAIN2 runs for N=16 under a legacy no-admissible selection abort at EVAL2 slot 0; the repaired invocation schedules zero replacement TRAIN2 for those five runs, completes the remaining EVAL2 fold verdicts, then executes the later frozen N=32 five-fold size, reduces N=16 rejected / N=32 accepted, rejects the overall campaign, and leaves production unauthorized.

The focused module is recorded as **40 passed** on the final executable candidate.

The final affected-regression realization covers 93 materially affected test modules and records **1976 passed, 19 failed, 1 skipped**. The 19 failures were discriminated against accepted baseline `4eabe2ae`: 18 reproduce on the baseline and one P7 qualification-store failure does not reproduce when isolated and its full module passes at lower parallelism. No candidate-attributable regression was identified. The repeated P5-F structural-oracle failure is the same accepted-baseline test-maintenance issue already classified nonblocking by the preceding independently closed CuEq repair; this workplan does not weaken product code or the oracle merely to manufacture a green count.

The review environment did not independently execute the repository test suite: the repository has no executable-code CI for this candidate and the connected review environment does not expose a runnable checkout. The execution counts are therefore implementation-supplied evidence, not independently re-executed evidence. They are nevertheless durably recorded, candidate-bound, structurally consistent with the inspected tests/implementation, include a mutation counterfactual for the reopened defect, and include accepted-baseline discrimination for every reported affected-run failure. No workplan requirement mandated a second independent execution realization after those acceptance runs.

Broad production-scale GPU/CuEq qualification remains deferred under standing project policy; this repair changes no GPU-specific behavior.

## 4. Predecessor Review blocker R3 — CLOSED

The branch-local Project Engineering Memory (PEM) is reconciled through accepted project state `4eabe2ae9783c7ff92f3a1093c37502a01380812`. The prior CuEq candidate-overlay notice is retired after that repair's independent PASS and merge, FF-001 coverage is refreshed without manufacturing a recurrence occurrence, and the current branch remains explicitly a candidate overlay rather than self-ratifying accepted memory.

The workplan Historical Applicability Set was refreshed against that basis: SP-001 and SP-004 remain applicable design/review priors; FF-001 remains not applicable because the preceding accepted repair established provider/projection parity and the present defect occurs after valid candidate metric evaluation.

Closeout learning was assessed. This cycle does not create a new failure family, discovery, or preservation capability. Existing success patterns explain useful engineering instincts, but this local repair is not admitted as another permanent application episode merely to record fix chronology: it did not introduce and then consolidate a new duplicate owner, and adding every supporting local repair would inflate PEM rather than improve bounded future decisions. The material PEM mutation for this cycle is the accepted-base/notice reconciliation already performed.

The active-workplan index is also reconciled by this closure: the parent, predecessor reopen, and implementation evidence are archived with this record, and `workplans/active/README.md` returns to no active MLFF implementation lineage.

## 5. Challenge, complexity, and impact closure

**No Serious Challenge.** The accepted architecture already requires every frozen size to receive a CV verdict before collection-level methodological reduction and already requires production to fail closed. The repair simply gives D4 a lossless representation for one legitimate negative fold state and authenticates it on restart.

No additive repair machinery was introduced. The implementation center remains the existing `post_selection_cv_acceptance.py` result owner and `campaign_post_selection_runtime.py` orchestration/recovery owner. `PostSelectionRunEvidence` remains strict for success/final production. No thresholds or D1/D2 semantics moved into recovery.

Permanent architecture does not require a new D3 concept: the current architecture already owns the required collection semantics. The CLI specification was updated only to make the operator-visible methodological-rejection/failure distinction explicit; generated documentation was regenerated before the predecessor review and no further normative executable change followed.

Material persistence compatibility is closed: v2 records bind decisive candidate evidence; v1 representative-bearing records remain readable byte-for-byte; malformed/mixed v2 states fail construction; current v2 restart reuse fails closed on missing/corrupt/inconsistent bound candidate evidence.

## 6. Evidence disposition

**Executed / accepted for this cycle:**

- focused result-contract matrix A-I;
- no-promotion property/counterfactual;
- exact target/replay threshold-boundary preservation;
- outer-evaluation call-count proof;
- exact five-fold complete-fold reduction;
- both multi-size methodological-rejection orderings;
- stakeholder-shaped 5/5 TRAIN2 same-workspace recovery;
- v1/v2 persistence compatibility;
- R1 current-v2 corruption/recovery falsification;
- final-production no-admissible hard-failure preservation;
- 93-module affected regression with accepted-baseline discrimination.

**Not independently re-executed by this Review host:** repository Python tests; see Section 3. The review independently inspected the final code, exact changed surface, durable evidence record, accepted-baseline behavior/evidence, and compatibility/lifecycle state.

**Deferred/nonblocking:** broad production-scale GPU/CuEq/LAMMPS/MLIAP qualification under the existing final-release policy.

## 7. Final closeout

**PASS. No further reopen.**

All predecessor R1-R3 blockers are closed without changing the governing scientific/numerical method or adding parallel machinery. The parent workplan, Review reopen, and implementation evidence are archived by the same closure commit. Future reopening requires new evidence that falsifies a protected invariant: for example an inadmissible checkpoint being promoted, outer evidence influencing representative choice, a current v2 verdict reusing unauthenticated decisive candidate evidence, completed TRAIN2 being unnecessarily retrained, a methodological rejection short-circuiting later required folds/sizes, or production being admitted despite a rejected required size.
