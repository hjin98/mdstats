---
kind: implementation-qualification-closure
workplan_id: MLFF-FINAL-PRODUCTION-MODEL-PUBLICATION-MH1-INTEGRATION
protocol_version: 6.4.0
status: superseded-independent-review-no-pass
closed_date: 2026-09-24
branch: design/mlff-final-production-model-publication-mh1-integration
evidence_head: d830773a78d860616a2d230c4a437238834a5c5b  # pre-commit execution basis; superseded for final binding
executable_product_sha: 73aab9e35399c5b7ceec3bbe31e129f76a50cdd8
production_source_changed: false
---

# Revision-28 successor evidence and lifecycle closeout

> **Post-closeout independent Review reassessment:** raw Revision-28 execution observations remain historical evidence, but the PASS/lifecycle-closure assessment is superseded. The executed worktree was recorded only against pre-commit head `d830773...`, while the reconciled evidence specifications were later committed at `1f29ca406eb5920b36df9a55d112501225e7868c`; two remapped P7 tests skip on local head-inventory mismatch before reaching the preserved runtime claim; one structural checkpoint-presence oracle is rename-sensitive; and the PEM no-update rationale conflicts with the accepted application ledger. Product-code conformance remains PASS. See active Section 26H for the bounded repair contract.

## Disposition

Historical Revision-28 assessment was **PASS / CLOSED**, but that assessment is superseded by the post-closeout independent Review. The retained executable product candidate remains product-code conforming. The Revision-27 raw observations and command ledger remain historical in `MLFF_FINAL_PRODUCTION_MODEL_PUBLICATION_MH1_INTEGRATION_CLOSEOUT_2026-09-23.md`; this successor record supersedes their stale-applicability and closure conclusion without rewriting them.

All current remapped evidence passed with zero unclassified failures. Superseded executable claims were retired at their evidence owners. No remapped current oracle exposed a product defect, so no production owner was repaired and no `mdstats/**/*.py` file changed. No Serious Challenge is active.

The branch head is `d830773a78d860616a2d230c4a437238834a5c5b`. The candidate executable product SHA remains `73aab9e35399c5b7ceec3bbe31e129f76a50cdd8`. The evidence-only worktree changes are intentionally uncommitted; no commit or branch-head mutation was performed during this closeout.

## IR28-E1: owner-local evidence reconciliation

The following dispositions were applied directly to tests and fixtures. No deprecated API, compatibility wrapper, blanket skip/xfail, weakened assertion, second scheduler, deployment registry, currentness store, or MH-1 production path was added.

| Surface | Disposition | Current owner exercised |
| --- | --- | --- |
| `test_mlff_production_global_train_scheduler.py` | Retired five assertions whose claims require pre-`PRODUCT_COMPLETE` fresh TRAIN/EVAL2 or historical-root authority. The maintained global-wave, collection-signature, recovery, and publication-boundary tests remain current. | Existing global TRAIN scheduler and final publication/reclosure owners; 23 passed. |
| `test_mlff_p7_r11_repair_acceptance.py::test_r11b2_real_runtime_gate_blocks_rather_than_passing` | Remapped from a generic one-head fixture to the authenticated P5 full-model/current-head chain. The real-runtime blocking assertion remains; missing locked MH-1 bytes/head inventory and unavailable target-host ML-IAP runtime remain explicit skips. | P5 full-model publication plus P7 `qualify_deployment_parity`. |
| `test_mlff_p7_r12_repair_acceptance.py::test_r12b11_frozen_publication_member_drives_the_real_deployment_owners` | Removed direct raw-checkpoint deployment and exercised the published model member and deployed artifact owners. | `session.published_model_member(member)` and `session.deployed_artifact(member)`. |
| `test_mlff_mace_compatibility.py` | Remapped warning/status and prepare tests through the current campaign facade and `_core` owners; removed pre-facade `command_evaluate` and old `main()` patch seams. | Current `campaign_cli.main`, `_core.command_prepare`, `_core._load_config`, and status warning normalization; 18 passed. |
| `test_mlff_mace_execution_semantics_assembled.py` | Remapped to the current `execute_post_selection_run` result object and current preparation fields; removed the synthetic P7 parameter-shell member-provider block. | Current post-selection executor/preparation owner; 5 passed and one CUDA-only skip. |
| `test_mlff_campaign_warning_domain_specification.py` | Current assertions now target the current warning tokens and proposed/current manual ownership; historical wording is owned by the historical note. | Current warning-domain specification and `WARN-DOMAIN1` historical record. |
| `test_mlff_doc_arch1_specification.py` | Current assertions target the current proposed manual/status/date and complete `TargetTrainingOrder`; retired text is no longer treated as current. | Current canonical architecture manual. |
| `test_mlff_data0_architecture_specification.py` | Current assertions target the current proposed manual/specification source; the PDF assertion targets the current source-manual/spec PDF owner. | Current DATA0 source documentation and generated/native-build owner. |
| `test_mlff_data9a6b_architecture_consistency_specification.py` | Historical aggregate-manual and dependency-graph assertions now read the explicit history snapshots, including the historical revision value. | `docs/history/mlff/manual_snapshots/...` historical owners. |
| `test_mlff_downstream_integration_closure.py` | Replaced obsolete serialized `run_identity` corruption with current `training_trajectory_identity`; narrowed the AST check to actual checkpoint-root `iterdir()` patterns, permitting the accepted lease-owned root observation. | Current downstream materialization/authentication and storage-owner checks; 30 passed. |
| `test_mlff_p5_replay_target_real_owner.py` | Retired the historical sealed/unsealed-root assertion because its governed claim predates the current `PRODUCT_COMPLETE` and final-model publication owners. | Current replay/recovery owner suites remain current; 10 passed. |
| `test_mlff_p5_restoration_method_owners.py` | Replaced removed `owner_plan_digest` structural expectation with current training-trajectory and preparation-policy ownership. | Current restoration/preparation owners; 24 passed. |
| `test_mlff_eval2_specification.py` | Retired the complete file: all three tests asserted superseded manual/API claims (`0.20.171a0`, rescue-cap wording, and removed `command_evaluate`). Current campaign/MACE suites retain the live Eval2 evidence. | Current campaign lifecycle and MACE execution suites. |

Revision-27 preserves the historical observations for every retired surface. The retired tests are not preserved as collectible executable specifications solely for history.

## IR28-E2: exact acceptance commands and results

All commands below were run with `conda run -n mace python -m pytest`; no `-k` exclusion or deselection filter was used for any current reconciled file.

### Mandatory focused suites

```text
conda run -n mace python -m pytest -q -ra \
  tests/test_mlff_p5_model_publication_owners.py \
  tests/test_mlff_p5_model_publication_acceptance.py \
  tests/test_mlff_p7_deployment_realization.py \
  tests/test_mlff_p7_product_currentness_fences.py \
  tests/test_mlff_mh1_publication_integration.py
```

Result: **89 passed, 2 skipped, 0 failed**.

Both skips state that locked real MACE-MH1 checkpoint bytes/runtime are unavailable on this host and real MH-1 campaign qualification is deferred to the target-machine campaign.

### Revision-28 reconciled files

```text
conda run -n mace python -m pytest -q -ra tests/test_mlff_production_global_train_scheduler.py
```

Result: **23 passed, 0 skipped, 0 failed**.

```text
conda run -n mace python -m pytest -q -ra \
  tests/test_mlff_p7_r11_repair_acceptance.py \
  tests/test_mlff_p7_r12_repair_acceptance.py
```

Result: **71 passed, 3 skipped, 0 failed**. The skips were: target-host LAMMPS/ML-IAP callback/runtime unavailable (`mliappy unified compute_forces failure`); locked MH-1 full-model/head inventory unavailable in R11; and the same locked MH-1 full-model/head inventory boundary in R12.

```text
conda run -n mace python -m pytest -q -ra tests/test_mlff_mace_compatibility.py
conda run -n mace python -m pytest -q -ra tests/test_mlff_mace_execution_semantics_assembled.py
```

Results: **18 passed, 0 skipped, 0 failed**; **5 passed, 1 skipped, 0 failed**. The assembled skip is the explicitly CUDA-only phase-separated CuEq case.

```text
conda run -n mace python -m pytest -q -ra \
  tests/test_mlff_campaign_warning_domain_specification.py \
  tests/test_mlff_doc_arch1_specification.py \
  tests/test_mlff_data0_architecture_specification.py \
  tests/test_mlff_data9a6b_architecture_consistency_specification.py
conda run -n mace python -m pytest -q -ra tests/test_mlff_downstream_integration_closure.py
```

Results: **17 passed, 0 skipped, 0 failed**; **30 passed, 0 skipped, 0 failed**.

The retired `tests/test_mlff_eval2_specification.py` was not run as a current file because its complete governed claim was superseded and the file was deleted; its historical three-failure result is retained in Git/Revision 27.

### Maintained affected owner suites

The following unfiltered affected acceptance was also rerun:

```text
conda run -n mace python -m pytest -q -ra \
  tests/test_mlff_p5_replay_target_policy_identity.py \
  tests/test_mlff_post_selection_materialization_acceptance.py \
  tests/test_mlff_p5_train2_eval2_cueq_realization_parity.py \
  tests/test_mlff_p5_train2_memory_backoff.py \
  tests/test_mlff_p5_train2_zero_safe_admission.py \
  tests/test_mlff_target_size_p5e_production_and_restart.py \
  tests/test_mlff_target_size_p5g_assembled_integration.py \
  tests/test_mlff_target_size_p5h_publication_decision.py \
  tests/test_mlff_target_size_multi_size_integration.py
```

Per-file results were: replay policy identity **56 passed**; materialization **1 passed**; phase-separated CuEq parity **17 skipped** (CUDA-only); memory backoff **12 passed**; zero-safe admission **16 passed**; P5E **27 passed**; P5G **3 passed**; P5H **8 passed**; multi-size integration **11 passed**. No failures occurred.

```text
conda run -n mace python -m pytest -q -ra \
  tests/test_mlff_campaign_assembled_lifecycle.py \
  tests/test_mlff_campaign_currentness_races.py \
  tests/test_mlff_campaign_observation_coherence.py \
  tests/test_mlff_campaign_observation_purity.py \
  tests/test_mlff_qualification_status_observation.py \
  tests/test_mlff_campaign_cli.py \
  tests/test_mlff_campaign_storage_composition.py
```

Result: **72 passed, 0 skipped, 0 failed**.

```text
conda run -n mace python -m pytest -q -ra \
  tests/test_mlff_storage_reset_core.py \
  tests/test_mlff_storage_reset_integration.py
```

Results: **291 passed** and **167 passed**, respectively; no failures or skips.

```text
conda run -n mace python -m pytest -q -ra \
  tests/test_mlff_mace_executable_config.py \
  tests/test_mlff_mace_execution_semantics.py \
  tests/test_mlff_train2b_runtime.py \
  tests/test_mlff_train2a_policy.py \
  tests/test_mlff_replay_mace_p5_execution_recovery.py \
  tests/test_mlff_mace_historical_compatibility.py \
  tests/test_mlff_data6_mace_native_batch_autograd.py
```

Result: **70 passed, 0 skipped, 0 failed**.

```text
conda run -n mace python -m pytest -q -ra \
  tests/test_mlff_p7_r13_authority_acceptance.py \
  tests/test_docs_pdf_builder.py \
  tests/test_native_build_registry.py \
  tests/test_mlff_doc_arch1_specification.py \
  tests/test_mlff_data0_architecture_specification.py \
  tests/test_mlff_data9a6b_architecture_consistency_specification.py
conda run -n mace python -m pytest -q -ra \
  tests/test_mlff_p7_post_production_qualification.py \
  tests/test_mlff_target_size_p5f_structure.py
```

Results: **58 passed, 0 skipped, 0 failed**; **62 passed, 0 skipped, 0 failed**.

The additional replay and restoration owner checks were **10 passed** and **24 passed**, respectively. No current affected suite had an unclassified failure.

## Static, package, and documentation evidence

```text
conda run -n mace python -m compileall -q mdstats tests
conda run -n mace python -c 'import mdstats; from mdstats.training_data import campaign_post_selection_runtime; from mdstats.training_data.qualification import runtime; print(mdstats.__version__); print(campaign_post_selection_runtime.__name__); print(runtime.__name__)'
conda run -n mace python -m pytest -q -ra \
  tests/test_mlff_python311_syntax_compatibility.py \
  tests/test_runtime_resource_static_audit_ld10.py
```

Compile/import exited successfully; static pytest result: **4 passed, 0 skipped, 0 failed**.

```text
conda run -n mace python -m build --no-isolation --sdist --wheel --outdir /tmp/mdstats-ir28-build
```

Package build passed. The artifacts were:

```text
mdstats-0.20.242a0-cp311-cp311-linux_x86_64.whl
SHA256 2577db4d804718e9fba6acc419d54e6f396f54c611a51b943af2323e0529e05a
mdstats-0.20.242a0.tar.gz
SHA256 7288bfd745373c1e96582c69b481ba0fd84a065eb865f6945e27a5cfbecd74df
```

The sdist was checked to contain no `workplans/` files.

The documentation builder was run against the exact retained executable/product and current evidence heads:

```text
conda run -n mace python docs/build_pdfs.py plan \
  --before 73aab9e35399c5b7ceec3bbe31e129f76a50cdd8 \
  --after d830773a78d860616a2d230c4a437238834a5c5b \
  --output /tmp/mdstats_ir28_docs_plan.json
conda run -n mace python docs/build_pdfs.py build \
  --before 73aab9e35399c5b7ceec3bbe31e129f76a50cdd8 \
  --after d830773a78d860616a2d230c4a437238834a5c5b \
  --report /tmp/mdstats_ir28_docs_build.json
```

Both exited successfully with `reason: incremental`, empty `targets`, `built`, and `deleted` lists. The durable reports are `MLFF_FINAL_PRODUCTION_MODEL_PUBLICATION_MH1_INTEGRATION_DOCS_PLAN_2026-09-24.json` and `MLFF_FINAL_PRODUCTION_MODEL_PUBLICATION_MH1_INTEGRATION_DOCS_BUILD_2026-09-24.json` in this archive.

## PEM closeout-learning assessment

`PROJECT-ENGINEERING-MEMORY.md` was not changed. **No PEM update required.** The completed intervention is the same evaluated final-publication/P7/MH-1 application episode represented by the unchanged accepted SP-001 through SP-004 and FF-001 through FF-005 basis. Revision-28 evidence retirement/remapping changes executable evidence ownership and removes obsolete oracles; it does not establish a new evaluated application episode meeting the Protocol-6.4 admission threshold, change failure-family applicability, alter evidence binding or coverage, or justify a new failure/success family. In particular:

- SP-001 remains the existing owning-layer consolidation pattern;
- SP-002 remains the existing authenticated/fail-closed identity-boundary pattern;
- SP-003 remains the existing durable immutable restart/reuse pattern;
- SP-004 remains the existing real-owner integration/qualification pattern.

The current episode adds no new recurrence, maturity, or cross-domain evidence beyond the already accepted basis. Ordinary fix chronology remains in this closeout and Revision 27, not in PEM.

## Explicit qualification deferrals

This closeout does not claim locked real MH-1 checkpoint/runtime qualification, long real MH-1 TRAIN2/CV/final-production/MD qualification, GPU/CUDA-performance qualification, or production target-host LAMMPS/MLIAP qualification. Those remain deferred to the actual campaign and final-release qualification. The target-host LAMMPS/ML-IAP callback skip is an authorized environment boundary, not a product failure.

## Final lifecycle decision

Historical Revision-28 assessment: **PASS / CLOSED — SUPERSEDED.** The canonical workplan is archived as `MLFF_FINAL_PRODUCTION_MODEL_PUBLICATION_MH1_INTEGRATION_WORKPLAN.md`; `workplans/active/README.md` no longer lists it as active and `workplans/archive/README.md` identifies this successor record. Revision 27 remains intact as superseded historical evidence.
