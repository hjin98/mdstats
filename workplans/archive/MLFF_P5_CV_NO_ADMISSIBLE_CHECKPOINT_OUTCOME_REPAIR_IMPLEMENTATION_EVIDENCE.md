---
kind: implementation-evidence
parent_workplan_id: MLFF-P5-CV-NO-ADMISSIBLE-CHECKPOINT-OUTCOME-REPAIR
review_reopen_id: MLFF-P5-CV-NO-ADMISSIBLE-CHECKPOINT-OUTCOME-REPAIR-REVIEW-REOPEN-1
protocol_version: 6.3.0
implementation_branch: fix/mlff-p5-cv-no-admissible-outcome-repair
accepted_baseline: 4eabe2ae9783c7ff92f3a1093c37502a01380812
final_executable_candidate: abf45c05
status: awaiting independent re-review
serious_challenge: none
---

# P5 no-admissible-checkpoint outcome repair — reopen implementation evidence

This record is non-authoritative implementation evidence for the independent re-review of blockers R1-R3. It does not close the workplan.

## Executable candidate

`abf45c05` ("fix: re-authenticate bound candidate evidence before reusing a v2 CV fold verdict") on top of the reviewed semantic candidate `737dd75a`. Later commits on this branch change only PEM, workplan, and README text; no executable or test file changes after `abf45c05`.

## R1 — restart re-authentication of v2 fold verdicts

Owner: `_completed_fold_acceptance()` in `mdstats/training_data/campaign_post_selection_runtime.py`, the only restart-reuse reader of `fold-acceptance.json` (checked structurally: the only other `CvFoldAcceptance.from_dict` call site deserializes folds nested in a campaign record).

For a v2 verdict it now resolves every `candidate_record_digest` through `context.evidence_store.get(..., Eval2CheckpointRecord.from_dict)`, so a missing object or a digest mismatch fails there. The resolved records must then reproduce the verdict:

- the sorted union of candidate `rejection_reasons` equals `checkpoint_rejection_reasons`;
- `no_admissible_representative`: no resolved candidate is admissible;
- `representative_selected`: the representative record (guaranteed by the constructor to be one of the bound digests) is admissible and its `stable_candidate_identity` equals the persisted identity.

Otherwise it raises `PostSelectionError` and never reuses the fold. v1 verdicts are returned as before, with no candidate set guessed and no bytes rewritten. Recovery does not re-apply thresholds; it only checks the persisted classification against authentic records. Outer metric records are not durable in the evidence store today, so the selected-fold check stops at representative authentication and keeps the existing outer-verdict semantics. No new recovery, status, or persistence machinery was added.

Tests in `tests/test_mlff_p5_cv_no_admissible_outcome.py` go through the real `cross-validate` path:

| Case | Result |
|---|---|
| valid persisted no-admissible fold + v1 selected fold for the same run plan | reused; zero TRAIN2 runs, zero EVAL2 evaluations, zero outer evaluations; v1 bytes unchanged, `candidate_record_digests == ()` |
| no-admissible: bound candidate object deleted | hard failure (`missing`), no retraining, not a CV rejection |
| no-admissible: bound candidate object corrupted | hard failure (`digest`) |
| no-admissible: candidate forged admissible and verdict re-bound to it | hard failure (not reproduced) |
| no-admissible: persisted reason union tampered | hard failure (not reproduced) |
| selected: representative object deleted | hard failure (`missing`) |
| selected: representative object corrupted | hard failure (`digest`) |

Falsification of the oracle: with only the R1 runtime change reverted (tests kept), all six tamper cases failed and the reuse case passed; with the change restored, all passed.

## R2 — exact five-fold stakeholder realization

The fixture's auto-selected size 8 has four independent split-exclusion components. Probing showed `K=5` raises `PostSelectionCvInfeasibleError` there, while explicit operator selection of frozen sizes 16 and 32 lawfully supports five folds (it completed CV 5/5 per size). Only test fixture construction changed: `target_size_power_max` 4 -> 5, and sizes 16/32 frozen through the real `select-target-size` owner. Production fold-count semantics are unchanged.

- `test_all_inadmissible_fold_is_a_completed_rejection_and_siblings_complete`: 5 required folds, fold 1 all-inadmissible, 0 outer evaluations for it and 1 for each of the others, all 5 verdicts persisted, size rejected with `fold_1_no_admissible_checkpoint`.
- `test_stakeholder_shaped_recovery_reuses_train2_and_completes_every_size`: legacy executable trains 5/5 TRAIN2 for N=16 and aborts at EVAL2 slot 0; the repaired same-workspace run schedules zero replacement TRAIN2 for N=16, records fold 0 as a no-admissible rejection, completes the remaining four folds, runs 5/5 for N=32, rejects N=16, accepts N=32, rejects the campaign, and keeps production unauthorized.

Focused module on `abf45c05`: `conda run -n mace python -m pytest -q -n 12 -p no:cacheprovider tests/test_mlff_p5_cv_no_admissible_outcome.py` -> **40 passed**.

## Complete affected regression on `abf45c05`

Target set: 93 test modules selected by consumers of `campaign_post_selection_runtime`, `post_selection_cv_acceptance`, `post_selection_execution`, `post_selection_store`/publication, `train2_policy`/checkpoint admissibility, EVAL2 ordering/assessment, replay/TRUE_DFT, production authorization, the post-selection and multi-size/downstream/lifecycle fixtures, and `campaign_cli.main` callers. This covers every category in parent Section 9 and reopen Section 6.

Command (from the repository root; the working-tree diff hash was checked to match the `abf45c05` commit content before it ran):

```text
/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q -n 16 -p no:randomly -p no:cacheprovider <93 modules>
```

Result: **1976 passed, 19 failed, 1 skipped** in 34 min 33 s.

Attribution: the 19 failing node IDs were rerun at accepted baseline `4eabe2ae` (detached worktree, same interpreter, `-n 8`): 18 fail there too, and 1 passes.

- 18 pre-existing: documentation/architecture-revision drift in `*_specification.py` suites (adapt_prec1, adapt_stop1 x3, cueq_default1, data0_architecture, eval_storage_roadmap x2, opt_ctrl1 x2, perf2_parallel_acceleration, replay_unify1d x2, train2a), `test_mlff_mace_compatibility.py` warning-domain tests x3, and `test_mlff_target_size_p5f_structure.py::test_p5f_no_screening_continuation_owner_is_reachable_from_post_selection`.
- 1 not reproduced: `test_mlff_p7_r12_repair_acceptance.py::test_r12b9_capability_resolves_applicable_and_stress_is_compared` failed only under `-n 16` with a P7 qualification-store `PostSelectionPublicationConflictError`, a path that does not read fold verdicts. On `abf45c05` it passes alone, and its full module passes at `-n 8` (31 passed). Classified as a parallel-load flake, not a regression.

**New regressions attributable to the candidate: none.**

## Checks not run

- No repository lint, format, or type tooling is configured (the only CI workflow builds documentation PDFs), so none was run.
- GPU/CuEq production qualification is deferred by project policy; this repair changes no GPU-specific behavior.
- No permanent specification or architecture text changed in this reopen, so no PDF regeneration was needed. The existing CLI failure contract already covers corrupt and incompatible persisted state.

## R3 — lifecycle and PEM

- `PROJECT-ENGINEERING-MEMORY.md` is reconciled through `4eabe2ae`: accepted base advanced, NT-001 retired because the CuEq repair closed PASS and merged (no FF-001 occurrence added, as that closure directs), FF-001 coverage refreshed, and the candidate overlay declared as basis reconciliation only.
- Closeout learning assessment: no new PEM family, occurrence, or application episode for this defect. HAS refreshed in the parent workplan: SP-001 and SP-004 applicable, FF-001 not applicable.
- `workplans/active/README.md` now points to this active lineage. The parent status is ACTIVE / REOPENED, awaiting re-review. Archival follows an independent closing review, per repository convention.
