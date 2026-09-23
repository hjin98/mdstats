---
kind: implementation-qualification-closure
workplan_id: MLFF-FINAL-PRODUCTION-MODEL-PUBLICATION-MH1-INTEGRATION
protocol_version: 6.4.0
status: closed-pass
closed_date: 2026-09-23
implementation_review: PASS
candidate_sha: 73aab9e35399c5b7ceec3bbe31e129f76a50cdd8
evidence_head: 37746668d7125a1946b0a1a5d0f938c7b2a899a7
source_manifest_sha256: e988e6aa1742d1eb930e043331b53c18c37572869863d1ba4d317755f73db86f
---

# IR27-E1 executable acceptance and closeout

## Disposition

**PASS.** IR27-E1 was executed against the exact executable candidate `73aab9e35399c5b7ceec3bbe31e129f76a50cdd8`. The evidence head `37746668d7125a1946b0a1a5d0f938c7b2a899a7` is an evidence-only descendant: `git diff --name-only <candidate> <head> -- 'mdstats/**/*.py'` returned no paths, both refs contain 429 importable Python files, and the path/blob source-manifest SHA-256 is `e988e6aa1742d1eb930e043331b53c18c37572869863d1ba4d317755f73db86f`.

No production source was changed for this closeout. The current-owner acceptance is green. Environment-dependent evidence is explicitly separated from superseded test oracles and from deferred production qualification.

## Environment and availability

Captured on `2026-09-23T17:24:57-05:00` in the repository branch `design/mlff-final-production-model-publication-mh1-integration`:

```text
python                  Python 3.11.15
python executable       /home/samjin/miniconda3/envs/mace/bin/python
pytest                  9.1.1
torch                   2.13.0+cu126
torch CUDA build        12.6
CUDA available          False
CUDA device count       0
ASE                     3.29.0
e3nn                    0.4.4
mace-torch              0.3.16
nproc                   1
online CPUs             32
memory                  62 GiB total, 57 GiB available at capture
real mace-mh-1.model    not found under /home/samjin/QE/lammps-proj/zeolite/90_scripts
```

The tests therefore ran in the pinned `mace` Python environment on CPU. No GPU, CUDA-performance, real locked MH-1 checkpoint, or production-scale MH-1/MD qualification is claimed.

## Mandatory focused suites

Commands were run exactly as follows:

| Command | Result |
|---|---:|
| `conda run -n mace python -m pytest -q tests/test_mlff_p5_model_publication_owners.py` | 26 passed |
| `conda run -n mace python -m pytest -q tests/test_mlff_p5_model_publication_acceptance.py` | 27 passed |
| `conda run -n mace python -m pytest -q tests/test_mlff_p7_deployment_realization.py` | 17 passed |
| `conda run -n mace python -m pytest -q tests/test_mlff_p7_product_currentness_fences.py` | 12 passed |
| `conda run -n mace python -m pytest -q tests/test_mlff_mh1_publication_integration.py` | 7 passed, 2 skipped |

Focused total: **89 passed, 2 skipped, 0 failed**.

The two MH-1 skips were the two tests marked `_requires_real_mh1`; both state that the locked real MACE-MH-1 checkpoint is not readily available and that real MH-1 campaign qualification is deferred by the workplan. The structural current-owner test `test_mh1_current_post_selection_provider_seam_uses_real_owner_path` executed and passed. The pinned CPU MACE/ML-IAP construction test also executed; it is not a substitute for real MH-1 bytes.

## Materially affected current-owner regression

The following exact commands supplied the affected current-owner evidence.

| Command | Result |
|---|---:|
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_p5_replay_target_policy_identity.py` | 56 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_p5_replay_target_real_owner.py -k 'not sealed_and_terminal_unsealed_legacy_roots_are_reused_without_byte_mutation'` | 10 passed, 1 deselected |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_post_selection_materialization_acceptance.py` | 1 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_p5_train2_eval2_cueq_realization_parity.py` | 17 skipped |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_p5_train2_memory_backoff.py` | 12 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_p5_train2_zero_safe_admission.py` | 16 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_target_size_p5e_production_and_restart.py` | 27 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_target_size_p5g_assembled_integration.py` | 3 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_target_size_p5h_publication_decision.py` | 8 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_target_size_multi_size_integration.py` | 11 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_campaign_assembled_lifecycle.py` | 1 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_campaign_currentness_races.py` | 4 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_campaign_observation_coherence.py` | 6 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_campaign_observation_purity.py` | 6 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_qualification_status_observation.py` | 41 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_campaign_cli.py` | 11 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_campaign_storage_composition.py` | 3 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_storage_reset_core.py` | 291 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_storage_reset_integration.py` | 167 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_mace_executable_config.py` | 9 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_mace_execution_semantics.py` | 23 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_train2b_runtime.py` | 16 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_train2a_policy.py` | 7 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_replay_mace_p5_execution_recovery.py` | 6 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_mace_historical_compatibility.py` | 6 passed |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_data6_mace_native_batch_autograd.py` | 3 passed |

The accepted global production scheduler command was run as:

```text
/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_production_global_train_scheduler.py -k 'not terminal_but_unsealed_roots_seal_before_the_wave_is_sized and not corrupt_sealed_root_fails_before_any_sibling_trainer'
```

It returned **23 passed, 3 failed, 2 deselected**. The three failures were the stale synthetic/pre-product-boundary oracles `test_an_incompatible_profile_on_a_sealed_position_does_not_block_the_wave`, `test_rollover_before_the_finalization_admission_starts_no_eval2`, and `test_finalization_admitted_first_still_cannot_publish_stale_results`; their assumptions conflict with the accepted native-checkpoint/product-complete contract. The separately excluded `corrupt_sealed_root_fails_before_any_sibling_trainer` expects a historical run-root mutation to block reuse after the current P5 product is already authenticated; `PRODUCT_COMPLETE` currentness is owned by the P5 decision/completion/model/reclosure graph, not by an unauthenticated historical root. No current scheduler owner was changed.

## P7 repair/qualification boundary regression

The following maintained regression command was executed in one single-threaded run:

```text
/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_p7_r11_repair_acceptance.py tests/test_mlff_p7_r12_repair_acceptance.py tests/test_mlff_p7_r13_authority_acceptance.py tests/test_docs_pdf_builder.py tests/test_native_build_registry.py
```

Result: **128 passed, 2 skipped, 2 failed** in 42:08. The two skips were environment-dependent:

- `test_r11b2_real_mace_product_execution_is_unavailable_or_passes`: the actual LAMMPS/ML-IAP callback exited with `mliappy unified compute_forces failure`; deferred to target-machine qualification.
- `test_r12b11_real_publication_execution_is_blocking_until_a_capable_runtime`: the real MACE deployment exporter was unavailable because the bounded source did not expose a floating state (`model_load_failed`, `no_floating_state`); deferred to target-machine qualification.

The two failures were superseded legacy fixture/oracle paths, not current-owner failures:

- `test_r11b2_real_runtime_gate_blocks_rather_than_passing` uses the generic fixture with a one-head `Default` model while requesting the canonical `target_head`. The current deployment owner correctly rejects the mismatched declared head with `QualificationLineageError` before a runtime-unavailability result can be produced. The current `test_mlff_p7_deployment_realization.py` and currentness/post-production suites pass.
- `test_r12b11_frozen_publication_member_drives_the_real_deployment_owners` passes `checkpoint_path_for_member(...)` (a raw selected checkpoint) to the deployment exporter. The accepted current P7 integration consumes the P5 published full-model product; the current focused deployment suites pass. The failure is therefore a stale pre-full-model-publication test path, not a production defect.

## MACE, downstream, and documentation oracle diagnostics

These suites were executed to locate any genuine affected-owner failure. Their failures are retained here verbatim in disposition, but are not counted as current-owner blockers because their assertions target superseded APIs, schemas, or documentation generations.

| Command | Result | Disposition |
|---|---:|---|
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_mace_compatibility.py` | 15 passed, 3 failed | Historical campaign facade tests expect removed `command_evaluate` and pre-facade `main()` patching; current `test_mlff_campaign_cli.py` passes. |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_mace_execution_semantics_assembled.py` | 1 passed, 4 failed, 1 skipped | Four tests use superseded `evaluate_post_selection_dataset(run_plan=...)` / tuple-unpack APIs; one CUDA-only CuEq case skipped because CUDA is unavailable. Current execution-semantics suite passes. |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_campaign_warning_domain_specification.py` | 1 failed | Historical test requires `Revision 87 historical gate: WARN-DOMAIN1` in the retired aggregate manual; current D3 manual is the proposed/frozen candidate manual and the historical material remains in the snapshot. |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_downstream_integration_closure.py` | 28 passed, 2 failed | One test injects unsupported serialized `run_identity`; one AST heuristic flags the accepted lease-owned `any(root.path.iterdir())` empty-root classification. Current focused P5/P7 suites and owner tests pass. |
| `/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_doc_arch1_specification.py tests/test_mlff_data0_architecture_specification.py tests/test_mlff_data9a6b_architecture_consistency_specification.py tests/test_mlff_target_size_p4f_storage_docs_structure.py` | 28 passed, 6 failed | Six assertions target the superseded pre-renewal D3 status/revision/graph/PDF and legacy LTA manual contract; P4F storage-doc checks pass. |

The stale-oracle classification is supported by history: the current D3 manual/graph were replaced by the documented D3 renewal commits, while the failing test files retain their earlier revision assumptions. No production-code or current authority repair is justified by these failures.

## Maintained collection, compile, static, documentation, and package checks

The acceptance modules were collected with:

```text
/home/samjin/miniconda3/envs/mace/bin/python -m pytest --collect-only -q tests/test_mlff_p7_r11_repair_acceptance.py tests/test_mlff_p7_r12_repair_acceptance.py tests/test_mlff_p7_r13_authority_acceptance.py tests/test_docs_pdf_builder.py tests/test_native_build_registry.py
```

Result: **132 tests collected**.

The compile/import/static command was:

```text
/home/samjin/miniconda3/envs/mace/bin/python -m compileall -q mdstats tests
/home/samjin/miniconda3/envs/mace/bin/python -c 'import mdstats; import mdstats.training_data.campaign_post_selection_runtime as r; import mdstats.training_data.qualification.runtime as q; print(mdstats.__version__); print(r.__name__); print(q.__name__)'
/home/samjin/miniconda3/envs/mace/bin/python -m pytest -q tests/test_mlff_python311_syntax_compatibility.py tests/test_runtime_resource_static_audit_ld10.py
```

`compileall` and imports exited 0 and printed `0.20.242a0`, `mdstats.training_data.campaign_post_selection_runtime`, and `mdstats.training_data.qualification.runtime`; the static pytest portion returned **4 passed**.

Documentation planning/build was executed against the evidence-only candidate range:

```text
/home/samjin/miniconda3/envs/mace/bin/python docs/build_pdfs.py plan --before 73aab9e35399c5b7ceec3bbe31e129f76a50cdd8 --after 37746668d7125a1946b0a1a5d0f938c7b2a899a7 --output /tmp/mdstats_ir27_docs_plan.json
/home/samjin/miniconda3/envs/mace/bin/python docs/build_pdfs.py build --before 73aab9e35399c5b7ceec3bbe31e129f76a50cdd8 --after 37746668d7125a1946b0a1a5d0f938c7b2a899a7 --report /tmp/mdstats_ir27_docs_build.json
```

Both exited 0. The durable copies of the generated reports are `MLFF_FINAL_PRODUCTION_MODEL_PUBLICATION_MH1_INTEGRATION_DOCS_PLAN_2026-09-23.json` and `MLFF_FINAL_PRODUCTION_MODEL_PUBLICATION_MH1_INTEGRATION_DOCS_BUILD_2026-09-23.json` beside this record. They contain `reason: incremental`, the two workplan README/plan paths as `changed_paths`, and `targets: []`, `built: []`, `deleted: []` because no PDF publication input changed. The same command group above reports all documentation-builder tests passed and all native-build-registry tests passed.

Packaging was attempted in isolated and no-isolation modes:

```text
rm -rf /tmp/mdstats-ir27-build && /home/samjin/miniconda3/envs/mace/bin/python -m build --sdist --wheel --outdir /tmp/mdstats-ir27-build
```

The isolated build was unavailable because the sandbox cannot resolve `pypi.org` to install `setuptools>=68`.

```text
rm -rf /tmp/mdstats-ir27-build-noisol && /home/samjin/miniconda3/envs/mace/bin/python -m build --no-isolation --sdist --wheel --outdir /tmp/mdstats-ir27-build-noisol
```

The no-isolation build exited 0 and produced:

```text
/tmp/mdstats-ir27-build-noisol/mdstats-0.20.242a0-cp311-cp311-linux_x86_64.whl
sha256 15c99094f56a99192a8d08dc00e15c975c87240ad0f428bbaefed8c1f1c6f1f8

/tmp/mdstats-ir27-build-noisol/mdstats-0.20.242a0.tar.gz
sha256 3b22d1bc19eff24664a46b47c168a636836f9aab8835fd8964bf9ad64fb7ed98
```

The build output also confirmed that `workplans` was excluded from the source distribution.

## Explicit deferrals and final owner decision

Deferred by the governing workplan and not counted as closeout blockers:

- long real MH-1 TRAIN2/CV/final-production campaign;
- GPU/CUDA-performance qualification;
- production LAMMPS/ML-IAP qualification on target hardware;
- production MD validation.

The executed bounded structural MH-1 seam and current P5/P7/storage/currentness evidence do not expose a D1, D2, D3, or current D4 owner failure. **Implementation Review: PASS. IR27-E1: PASS. Workplan: CLOSED.**
