---
kind: implementation-evidence
package_id: MLFF-MACE-EXECUTION-SEMANTICS-ALIGNMENT
package_revision: final-execution-evidence
parent_workplan_id: MLFF-MACE-EXECUTION-SEMANTICS-ALIGNMENT-FINAL-EXECUTION-EVIDENCE
protocol_version: 5.15.0
reviewed_candidate_commit: 60cd50cd5e7a399257c1f52bca712b51bd751916
reviewed_candidate_tree: 554f72d68982f7e322b7cfff5668c6e3d37e0d36
status: implementation-complete-evidence-documented
recorded_date: 2026-09-07
---

# MLFF MACE execution-semantics alignment — final execution evidence

## 1. Candidate and source-boundary authentication

- **Governing workplan**: `workplans/active/MLFF_MACE_EXECUTION_SEMANTICS_ALIGNMENT_FINAL_EXECUTION_EVIDENCE_REOPEN.md`
- **Exact executable candidate commit**: `60cd50cd5e7a399257c1f52bca712b51bd751916`
- **Exact executable candidate tree**: `554f72d68982f7e322b7cfff5668c6e3d37e0d36`
- **Evidence execution checkout**: `9a5dddc322e875e0bd2ac08d220cbcd440f93b88` before this evidence record was added
- **Candidate-bound source check**: `git diff --quiet 60cd50cd5e7a399257c1f52bca712b51bd751916 HEAD -- mdstats tests pyproject.toml setup.py setup.cfg tox.ini Makefile` — **PASS**
- The evidence checkout differs from the exact candidate only by this workplan/evidence lineage. No product source, test oracle, build configuration, or runtime machinery was changed to obtain this evidence.

The evidence therefore applies to the reviewed executable candidate, rather than to a later source repair or wrapper.

## 2. Execution environment and resource allocation

- **Environment**: `conda run -n mace`
- **Python**: `3.11.15`
- **PyTorch**: `2.13.0+cu126`
- **MACE**: `mace_torch 0.3.16` (`mace-torch==0.3.16`)
- **Host execution**: Linux CPU execution; no GPU or production-runtime qualification is claimed
- **CPU allocation**: `os.cpu_count()=32`, `len(os.sched_getaffinity(0))=32`, `nproc --all=32`
- **pytest concurrency**: `-n 32 --dist=load` (or `--dist=loadfile` for the assembled real-MACE case where recorded)
- **Thread caps**: `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`

All required affected partitions were executed with zero required skips. The partition results below total **474 passed, 0 failed, 0 skipped**.

## 3. Affected acceptance and regression execution

Every command below was run from the repository root with the environment and thread caps in Section 2.

### Core optimizer, currentness, P5-R6, and P3A4 acceptance

```text
conda run -n mace env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m pytest -n 32 --dist=load -q tests/test_mlff_target_size_canonical_optimizer_settings.py tests/test_mlff_target_size_p5_r6_cutover_authorization.py tests/test_mlff_target_size_p5_r6_guards.py tests/test_mlff_target_size_p3a4_final_review.py
```

**Result**: `132 passed, 0 failed, 0 skipped`.

This includes the serialized v3 -> v4 currentness oracle and the final-production authorization owner checks.

### P5 R7–R10 guards

```text
conda run -n mace env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m pytest -n 32 --dist=load -q tests/test_mlff_target_size_p5_r7_guards.py tests/test_mlff_target_size_p5_r8_guards.py tests/test_mlff_target_size_p5_r9_guards.py tests/test_mlff_target_size_p5_r10_guards.py
```

**Result**: `58 passed, 0 failed, 0 skipped`.

### P5a–P5d and historical DATA8/currentness

```text
conda run -n mace env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m pytest -n 32 --dist=load -q tests/test_mlff_target_size_p5a_selected_context.py tests/test_mlff_target_size_p5b_identity_hierarchy.py tests/test_mlff_target_size_p5c_cv_plan.py tests/test_mlff_target_size_p5d_cv_acceptance.py tests/test_mlff_data8_specification.py
```

**Result**: `43 passed, 0 failed, 0 skipped`.

### P5e/P5g production, restart, assembled integration, and P7 provider release

```text
conda run -n mace env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m pytest -n 32 --dist=load -q tests/test_mlff_target_size_p5e_production_and_restart.py tests/test_mlff_target_size_p5g_assembled_integration.py tests/test_mlff_p7_post_production_qualification.py::test_p7_provider_is_released_on_success_and_on_exception
```

**Result**: `31 passed, 0 failed, 0 skipped`.

### P5f/P5h structure and publication decision

```text
conda run -n mace env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m pytest -n 32 --dist=load -q tests/test_mlff_target_size_p5f_structure.py tests/test_mlff_target_size_p5h_publication_decision.py
```

**Result**: `21 passed, 0 failed, 0 skipped`.

### P5-R11 guards

```text
conda run -n mace env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m pytest -n 32 --dist=load -q tests/test_mlff_target_size_p5_r11_guards.py
```

**Result**: `8 passed, 0 failed, 0 skipped`.

### MACE wrapper, historical compatibility, executable configuration, objective, and export weighting

The three unrelated campaign-warning CLI tests listed in Section 5 were excluded from this affected MACE execution-semantics partition; all other tests in the files below executed.

```text
conda run -n mace env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m pytest -n 32 --dist=load -q tests/test_mlff_mace_compatibility.py tests/test_mlff_mace_execution_semantics.py tests/test_mlff_mace_executable_config.py tests/test_mlff_mace_historical_compatibility.py tests/test_mlff_target_size_mace_objective_realization.py -k 'not test_campaign_evaluate_outer_scope_catches_setup_warnings and not test_campaign_warning_domain_merges_worker_thread_local_scopes and not test_campaign_main_owns_one_warning_domain_and_normalizes_output'
```

**Result**: `39 passed, 0 failed, 0 skipped`.

### P3 real non-divisible integration and EMA/live preservation

```text
conda run -n mace env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m pytest -n 32 --dist=load -q tests/test_mlff_target_size_execution_p3a.py tests/test_mlff_target_size_execution_p3b.py tests/test_mlff_target_size_execution_p3c.py tests/test_mlff_target_size_execution_p3d.py tests/test_mlff_target_size_execution_p3e.py tests/test_mlff_target_size_execution_p3f.py tests/test_mlff_target_size_p3_realized_mace_architecture.py tests/test_mlff_target_size_p3a9_head_pointer_reconciliation.py
```

**Result**: `115 passed, 0 failed, 0 skipped`.

### TRAIN2 checkpoint, immutable-boundary, restart, and continuation regression

```text
conda run -n mace env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m pytest -n 32 --dist=load -q tests/test_mlff_train2a_policy.py tests/test_mlff_train2b_runtime.py
```

**Result**: `22 passed, 0 failed, 0 skipped`.

### P7 R13 deployment-parity/stress authority checks directly affected by the state-owner repair

```text
conda run -n mace env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m pytest -n 32 --dist=load -q tests/test_mlff_p7_r13_authority_acceptance.py::test_r13_2_qualify_deployment_parity_reaches_worker_despite_generic_probe_failure tests/test_mlff_p7_r13_authority_acceptance.py::test_r13_2_applicable_stress_requested_and_compared_when_generic_probe_fails
```

**Result**: `2 passed, 0 failed, 0 skipped`.

### Real pinned-MACE assembled acceptance

```text
conda run -n mace env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m pytest -n 32 --dist=loadfile -q tests/test_mlff_mace_execution_semantics_assembled.py
```

**Result**: `3 passed, 0 failed, 0 skipped`.

These three cases execute the real scratch, naive-fine-tuning, and replay paths under pinned MACE. The replay case creates multiple native checkpoints with EMA enabled, makes the earlier checkpoint the target-only representative, executes held-out outer evaluation through that earlier native representation, consumes the same representation through the existing qualification `member_provider`, and rejects the counterfactual hard-coded `live` requests with and without the bounded numerical forward seam.

## 4. Aggregate result

| Affected partition | Passed | Failed | Skipped |
|---|---:|---:|---:|
| Core optimizer/currentness/P5-R6/P3A4 | 132 | 0 | 0 |
| P5 R7–R10 | 58 | 0 | 0 |
| P5a–P5d and DATA8 | 43 | 0 | 0 |
| P5e/P5g and P7 provider release | 31 | 0 | 0 |
| P5f/P5h | 21 | 0 | 0 |
| P5-R11 | 8 | 0 | 0 |
| MACE wrapper/objective/export subset | 39 | 0 | 0 |
| P3 integration | 115 | 0 | 0 |
| TRAIN2 runtime | 22 | 0 | 0 |
| P7 R13 selected authority checks | 2 | 0 | 0 |
| Real assembled MACE | 3 | 0 | 0 |
| **Total** | **474** | **0** | **0** |

## 5. Unrelated baseline failures observed and intentionally not repaired

The following checks were run as diagnostic boundary checks, but are outside the exact candidate diff and outside the execution-semantics repair ownership. They do not invalidate the passing affected partitions in Section 3 and were not “fixed” with a wrapper or unrelated machinery.

### Stale campaign-warning CLI assertions

The unfiltered native MACE file group (`tests/test_mlff_mace_compatibility.py`, `tests/test_mlff_mace_execution_semantics.py`, `tests/test_mlff_mace_executable_config.py`, `tests/test_mlff_mace_historical_compatibility.py`, and `tests/test_mlff_target_size_mace_objective_realization.py`) returned **39 passed, 3 failed**. The three failures were:

- `test_campaign_evaluate_outer_scope_catches_setup_warnings`: `campaign_cli.command_evaluate` is absent from the current CLI owner;
- `test_campaign_warning_domain_merges_worker_thread_local_scopes`: `campaign_cli.main([])` exits through argparse because a command is required;
- `test_campaign_main_owns_one_warning_domain_and_normalizes_output`: the same current CLI parser contract failure.

None of these tests or their CLI owner is part of the exact `60cd50c` executable diff.

### Stale TRAIN2 architecture-manual assertions

```text
conda run -n mace env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m pytest -n 32 --dist=load -q tests/test_mlff_train2a_specification.py tests/test_mlff_train2b_specification.py
```

**Result**: `3 passed, 2 failed`.

The failures assert the removed literal `TRAIN2A is implemented in \`mdstats 0.20.169a0\`` and a removed `## Gate TRAIN2B` section in the current architecture manual. These are stale documentation assertions; the architecture manual and these specification tests are outside the exact candidate diff and outside the MACE execution-semantics repair surface.

## 6. Static and repository checks

- `git diff --check` — **PASS**.
- Candidate-bound executable surface comparison — **PASS** (Section 1).
- Python compilation of the changed acceptance-test modules — **PASS**.
- Semgrep production scan for the retired hard-coded state assignment
  `POST_SELECTION_EVALUATION_MODEL_STATE = $STATE` in
  `mdstats/training_data/campaign_post_selection_runtime.py` and
  `mdstats/training_data/qualification/providers.py` — **0 findings**.
- Semgrep production scan for `evaluation_model_state = "live"` in the same two owners — **0 findings**.

The Semgrep scans used isolated temporary settings/log/cache paths and `--disable-version-check`; no scan result was suppressed by repository ignore rules.

## 7. Qualification boundary and disposition

This record closes the previously missing executable-evidence requirement for the exact candidate: all required affected partitions executed under the pinned dependency identity with no required skips, and the real assembled MACE acceptance passed.

This is CPU-only functional evidence. It does not claim GPU qualification, LAMMPS production callback qualification, or external-reference scientific qualification. A fresh independent Software Design closure review and any resulting workplan archival remain a separate review-authority action; this evidence record does not claim that review or archival has occurred.
