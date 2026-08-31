---
kind: implementation-evidence
package_id: CODE-MLFF-TARGET-SIZE-V7-P6
package_revision: 13
protocol_version: 5.8.0
entry_p5_accepted_baseline_commit: 1670275487d29bbcde4c59efafdef9d1f8b0ced7
entry_p5_accepted_baseline_tree: 17e2c5609974712bda1efd3375f09f42da830f68
tested_executable_commit: 4c4b2f5a93fa86aa17613afae2279c5faf5446a5
tested_executable_tree: 164a2393613faa2aa2c116117e266ee56abf15eb
status: implementation-complete-pending-design-review
recorded_date: 2026-08-31
---

# P6 revision 13 — implementation evidence

Implementation authority: `P6_REVISION_13_AUTHORITY.md` plus
`P6_REVISION_13_FINAL_PROXY_PROOF_AND_EXECUTION_EVIDENCE_CLOSURE_AMENDMENT.md`,
under the composed P6 revisions (R3–R13) and frozen parent
`../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md`.

## 1. Starting point

Implementation began from branch HEAD `94c3286`, whose **code tree is
byte-identical to the accepted P5A6 baseline** `1670275` / tree `17e2c56`; the
three intervening commits changed only `workplans/`. No reconciliation of an
intervening code diff was required.

Baseline suite before any edit (`pytest -n 16 -q -p no:randomly`):

```text
246 failed, 3899 passed, 34 skipped, 100 errors in 600s
```

These pre-existing failures are dominated by version-pinned `*_specification`
tests (each asserts the `mdstats.__version__` at which it was written) and by
missing `tests/data/*.json` fixtures. They are unrelated to P6 and were recorded
before any change so post-P6 results could be attributed honestly.

## 2. Mandatory P5A6 compatibility fixture (amendment §2, §3)

Created **before the first destructive edit**, from a clean `git worktree` at the
exact accepted baseline:

```bash
git worktree add <dir> 1670275487d29bbcde4c59efafdef9d1f8b0ced7
python <dir>/build_p5a6_compat_fixture.py \
  qualification/p6-p5a6-compat/workspace
```

The builder (committed as
`qualification/p6-p5a6-compat/build_p5a6_compat_fixture.py`) drives the real
production path end to end: real `_load_config`, real `CampaignStore`/SQLite,
real P1/P2 authority construction, `prepare`, `select-target-size`,
`cross-validate`, and `train-production` through the production CLI dispatch,
then reads the result back through the real terminal/selected/post-selection
owners.

Bounded numerical seams used during fixture creation are exactly the ones P5
already accepted below the mdstats owner boundary: `PostSelectionHarness.train`
(drives the *real* TRAIN2 runtime with a toy `torch.nn.Linear` model) and
`PostSelectionHarness.evaluate` (returns predictions for artifacts real owners
exported and authenticated). No selected authority, replay lineage, CV
authorization, or final publication was injected.

Immutable fixture identity (recorded in
`qualification/p6-p5a6-compat/P5A6_FIXTURE_IDENTITY.json`):

```text
baseline_commit  1670275487d29bbcde4c59efafdef9d1f8b0ced7
baseline_tree    17e2c5609974712bda1efd3375f09f42da830f68
generation       1        regime current   lifecycle terminal_selected
N_selected       4
T_selected       dcca0861c901...
selected binding 77337bc37b98...
method identity  c66a6f057668...
cv plan          ebaab03a8299...
cv acceptance    8cf95a90aaa6...
final plan       d9ec29dc9e7e...
content manifest 79833746e8a2...  (802 files)
```

`P5A6_FIXTURE_CONTENT_MANIFEST.json` records the SHA-256 of every one of those
802 files; `P5A6_FIXTURE_DATABASE_SNAPSHOT.json` records the row count and
content digest of every table of `campaign.sqlite3`. The ~3 MiB workspace itself
(which contains `.pt` checkpoints) is git-ignored per repository hygiene policy;
its identity, content manifest, database snapshot, and deterministic builder are
tracked.

The fixture was **not** regenerated, rewritten, normalized, migrated, or
pre-opened-and-saved by P6 at any point.

## 3. P6-A census and disposition

The census was derived structurally rather than by search-term listing: a
package-wide import graph plus `mdstats.<Name>` attribute resolution, iterated to
a fixpoint from the real current runtime roots (`_campaign_cli_core`,
`campaign_cli`, `critical_precision_cli`, `campaign_target_size_runtime`,
`campaign_post_selection_runtime`, `target_size_execution`, `neutral_substrate`,
the three subprocess worker entry points, and the independent `mdstats.analysis`
/ `graphics3d` / `io` / `plotting` / `sampling` / `coordinates` / `collection` /
`semantics` / `provenance` products).

The decisive finding was that the retired architecture was **not** unreachable
scaffolding: the current `train2` runtime still consumed it.

| Retired surface | Reached from | Disposition |
|---|---|---|
| `[training].policy_generation != "train2"` lifecycle | `command_prepare`, `command_status`, `command_advance`, `command_preflight` | **R1** — replaced by a reject-only obsolete-generation gate |
| `_load_verified_target_size_study_authority` (V5 study) | `preflight`, `train`, `evaluate`, `verify`, `status`, `advance` in **train2** mode | **R1** — removed; the current terminal authority is `CampaignStore` |
| `_train2_public_lifecycle` | `status` / `advance` | **R3** — rewritten as `_current_public_lifecycle` on the V7 owners |
| `target_data_role_freeze` built and persisted by `_prepare_catalog` | the current `prepare` | **R1** — removed (the P4 cutover already quarantines the record it wrote) |
| DATA5 `cross_validation_plans` reported by `prepare` | the current `prepare` | **R1** — pre-target CV plans no longer reported as current; the DATA5 bundle itself stays an R5 lower-level input under P4's accepted reuse contract |
| `Eval2TargetRole` + `size_development_complement` / `size_development_coarse` builders | retired `evaluate` only | **R1** — removed; the V7 `target_size_execution` evaluation path never used them |
| `CampaignStore` native-pointer readers/writers for retired records | store dispatch | **R1** — removed; DATA4/DATA6 sharded readers retained |
| `MlcvRoleCatalog` optional field on `Data8PreparationBundle` | `build_data8_preparation_bundle` (no current caller) | **R3** — field and retired builder removed |
| `TrainingCampaignPlan` / `build_training_campaign_plan` | retired `train`/`evaluate`/`verify` | **R1** — removed; checkpoint inventory/selection owners in `campaign_control` retained (used by `post_selection_execution`) |
| `_compact_evaluated_checkpoints`, `_current_data8_entries`, `_current_materialization_roots` | STOR2/STOR4 | **R1** — removed; the remaining STOR owners no longer deserialize retired derived state |
| retired protocol-freeze gate on STOR compact/dedup | `command_cleanup`, `command_deduplicate` | **R3** — replaced by `_current_lifecycle_is_complete`, derived from the V7 lifecycle owners |
| `FEAS1 / MVIDX1 / MVSEL2 / REPAIR2 / MVSTATE2 / MVQUAL2 / target_size_study / size_fidelity / production_materialization / DATA7 / MLCV / adaptive_* / lightweight_rank / multi_fidelity_evaluation / campaign_execution / work_queue` modules | only each other and the retired lifecycle | **R1** — deleted (see §4) |
| `deploy_verify / pes_verify / relax_verify / dyn_verify / locked_test2 / select2 / perf_p2r / foundation_audit` | retired `verify` chain, and their record identities bind `target_size_study_digest` / `target_data_role_freeze_digest` | **R1** — deleted; see the deviation in §10 |

### Retained with recorded purpose (R2/R5/R6/R8)

- **R2 shared execution machinery still used by current paths:** `acceleration`,
  `precision_runtime`, `precision_schedule`, `resources`, `training_parallel`,
  `inference_parallel`, `progress_timing`, `work-queue-free` scheduling,
  `train2_runtime`, `train2_policy`, `replay`, `replay_index`, `foundation`,
  `mace_compatibility`, `mace_export`, `mace_head_extraction`, `data8_bundle`,
  `data6_bundle`, `frame_cache`, `data4_sharded_store`, `data6_sharded_store`,
  `storage_accounting`, `storage_reclamation`, `storage_archive`,
  `campaign_target_size_retention`, `eval2` (metric/admissibility engine).
- **R5 lower-level content-addressed inputs:** `data5_bundle` — retained under
  the P4-accepted `REUSABLE_LOWER_LEVEL_RECORD_KEYS` contract; its pre-target CV
  plans are no longer current authority or reported as such.
- **R6 independently supported product surfaces, currently without a CLI entry
  point because the V7 downstream verification lifecycle is out of P6 scope:**
  `accelerator_runtime_freeze`, `cueq_phase1`, `cueq_phase2`, `final_gpu1`,
  `mace_realization`, `mace_runtime`, `mace_qualification`, `mace_deployment`,
  `precision`, `cross_system_qualification`, `perf_cert1`, `artifact_staging`,
  `checkpoint_capsule`, `evaluation_predictions`, `replay_invalidation`.
  None of these binds retired target-size lineage (verified by source scan).
- **R8 validation-only measurement surfaces:** `perfbase1`,
  `performance_baseline`, `observable_comparison`, `observable_validation` —
  measurement/oracle authorities over retained current implementations, outside
  production runtime authority.
- **Subprocess entry points** (`source_worker`, `feature_worker`,
  `_repeatability_deterministic_worker`) are reached by `-m` launch, not import;
  they were explicitly excluded from the unreachable set.

## 4. Destructive removals

**Source (60 files, ~88.6k lines deleted).** Module list:

```text
_mvsel2_native.c  _sparse_vector_kernels  _target_coverage_neighborhood
_target_multi_view_scoring  adaptive_full_evaluation  adaptive_migration
adaptive_verification  campaign_execution  data7_archive  data7_bundle
deploy_verify  dyn_verify  foundation_audit  lightweight_rank  locked_test2
mlcv_aggregate  mlcv_final  mlcv_migration  mlcv_roles  mlcv_select
mlcv_verification  multi_fidelity_evaluation  mvidx1_forward_receipt_runtime
mvqual_p2_runtime  mvsel2_hardening_runtime  mvsel2_native_backend
mvsel2_native_preflight  mvsel2_phase_a_kernel  mvsel2_phase_b_kernel
mvsel2_repair_checkpoint_runtime  mvsel2_selection_engine
mvsel2_streaming_frontier  mvsel2_v5_runtime  perf_p2r  pes_verify
production_materialization  relax_verify  select2  size_fidelity
target_coverage{,_store,_feasibility,_exact_neighborhood{,_store},
                _sparse_index{,_store},_sparse_forward_view}
target_data_roles  target_multi_view_{selector,selector_v2,selector_v2_resume,
                selection_state,selection_state_store,selection_state_v2,
                selection_history_v2,repair,repair_v2,qualification_v2}
target_size_study  work_queue
```

**`_campaign_cli_core.py`: 29,948 -> 8,239 lines.** Removals were driven by
AST reachability from the module's live roots after each behavioral edit, never
by pattern matching:

- retired subcommands `materialize`, `preflight`, `train`, `extend-seed`,
  `evaluate`, `verify` and their parser entries;
- 229 top-level definitions that became unreachable once those commands and the
  retired generation branch were gone, then 12 more across two further waves;
- the retired prepare-receipt key tables and retired `[performance]`
  coverage/repair/qualification worker knobs from the generated config template.

**Package exports.** `mdstats/__init__.py` and `mdstats/training_data/__init__.py`
were reconciled by parsing every `from .x import (...)`, dropping imports of
deleted modules and names, and dropping the matching `__all__` string entries:
~1,300 export lines removed. `mdstats.__all__` 2,819 names,
`mdstats.training_data.__all__` 1,366 names, with no retired target-size symbol
reachable (asserted structurally in
`tests/test_mlff_target_size_p6_destructive_closure.py`).

**Native build registry.** `build_support/native_extensions.py` no longer
declares the retired `mdstats._mvsel2_native` kernel; the registry itself remains
as the canonical declaration point.

## 5. Reject-only obsolete-generation detection

Two layers, both reject-before-reuse:

1. **Configuration.** `_training_policy_generation` now accepts only
   `"train2"`. A missing value or any of `adaptive`, `adaptive_stop`,
   `adaptive_stop_v3`, `legacy` raises before any campaign record is opened,
   with actionable destructive reset/reprepare guidance.
2. **Workspace.** The P4 owner `require_current_target_size_runtime` /
   `inventory_retired_target_size_state` remains the store-level detector. It is
   structurally proven to read record *names* only — the test asserts that
   `inventory_retired_target_size_state` calls `record_keys` and never
   `get_record`/`get_payload` — and `quarantine_retired_target_size_state`
   renames rows inside one transaction rather than decoding any retired payload.

No migration adapter, semantic reader, reconstruction helper, or receipt for
retired target-size derived state remains.

## 6. Current public lifecycle

`_train2_public_lifecycle` (built entirely on the retired V5 study) was replaced
by `_current_public_lifecycle`, which reads the campaign-store target-size
revision and the post-selection CV/final-production owners:

```text
doctor -> prepare -> select-target-size -> cross-validate -> train-production
```

`command_status`, `_next_public_operation`, and `command_advance` derive from
that projection; `PIPELINE` now names the stage keys the current runtimes
actually write (`prepare`, `target_size_selection`,
`post_selection_cross_validation`, `post_selection_final_production`).

Parser surface after cleanup:

```text
advance cross-validate doctor guide init prepare select-target-size
status storage train-production
```

## 7. Executed checks

### Stage-local

| Stage | Command | Result |
|---|---|---|
| CLI generation cutover | `pytest tests/test_mlff_target_size_p4g_assembled_integration.py tests/test_mlff_target_size_p5g_assembled_integration.py` | 5 passed |
| module deletion + export reconciliation | same assembled pair | 5 passed |
| P5A6 compatibility | `pytest tests/test_mlff_target_size_p6_p5a6_compatibility.py` | 2 passed (twice, proving idempotence) |
| P6 destructive closure | `pytest tests/test_mlff_target_size_p6_destructive_closure.py` | 12 passed |
| P3/P4/P5 structure + cutover | `pytest tests/test_mlff_target_size_execution_p3f.py tests/test_mlff_target_size_p4d_runtime_cutover.py tests/test_mlff_target_size_p4f_storage_docs_structure.py tests/test_mlff_target_size_p5f_structure.py` | all passed |
| storage / eval2 / policy after test disposition | `pytest tests/test_mlff_stor{1,3,4,5}*.py tests/test_mlff_eval2.py tests/test_mlff_train2a_policy.py tests/test_mlff_data9b1_campaign_checkpoint_control.py tests/test_mlff_prec1_precision_profiles.py tests/test_mlff_opt_ctrl1_control_plane.py tests/test_mlff_parallel_resources.py tests/test_mlff_cueq_train_repeatability_diag_hf.py` | 69 passed |
| documentation architecture contract | `pytest tests/test_mlff_doc_arch1_specification.py tests/test_mlff_final_gpu1_specification.py` | passed |

### The three separately identified persistence results (amendment §5)

```text
P5A6 -> P6 current-generation compatibility     PASS
P6   -> P6 current-generation restart           PASS
V5/V6 retired target-size reject-before-reuse   PASS
```

- **P5A6 -> P6** (`test_p6_reopens_the_preserved_p5a6_workspace_through_real_owners`):
  the preserved workspace is verified byte-identical (non-database files) and
  table-identical (`campaign.sqlite3`) *before* anything opens it, proving no
  pre-load rewrite or migration; it is then opened through `cli._load_config`,
  the real `CampaignStore`, `require_current_target_size_runtime`,
  `load_current_selected_training_context`, `build_post_selection_context`,
  `resolve_current_cv_plan/acceptance/final_production_plan`; every recorded
  P5A6 identity authenticates; it is closed, reopened in a fresh store context,
  and re-authenticated; and the persisted campaign state is proven unchanged
  afterwards. The only on-disk additions are the executable wrapper shims and the
  restored normalized frame cache — derived material carrying no authority — and
  the content-hash receipt cache, which is a recomputable low-level content cache
  explicitly reusable under the frozen parent's reuse boundary.
- **P6 -> P6** (`test_p6_current_workspace_closes_reopens_and_restarts_deterministically`):
  a workspace built by the final candidate through the real CLI closes, reopens,
  and produces an identical owner-derived snapshot; re-running `cross-validate`
  and `train-production` reauthenticates rather than rebuilding; `status`
  projects the complete lifecycle.
- **Reject-before-reuse**
  (`test_p6_retired_target_size_workspace_is_rejected_before_reuse`): retired
  records are planted, `require_current_target_size_runtime` refuses with reset
  guidance, `prepare` quarantines them, and the retired selected size never
  becomes current authority.

### Documentation checks

| Check | Command | Result |
|---|---|---|
| architecture manual assembly | `python tools/build_mlff_architecture_manual.py` | rebuilt deterministically from the numbered chapters |
| architecture PDF publication | `python docs/build_pdfs.py build --target docs/arch_manuals/mlff_training_data_architecture.pdf` | **passed** — pandoc 3.10.2 + typst 0.15.1 (the repository's documented `mace-dependencies/typst-x86_64-unknown-linux-musl.tar.xz`); manifest regenerated |
| intra-repository Markdown link check | link scanner over all non-workplan Markdown | 3 broken links, all pre-existing in one historical manual snapshot; **no new broken link** |
| doc/architecture contract tests | `pytest tests/test_mlff_doc_arch1_specification.py` | 8 passed |

No required documentation check was classified as deferred-success. The PDF
toolchain was located and used rather than reported unavailable.

## 8. Test disposition

- **127 test files deleted** — files whose entire contract was the retired
  topology (MVSEL2/REPAIR2/MVQUAL/MVIDX/FEAS1/coverage, the V5 study,
  DATA7/production materialization, MLCV, adaptive-stop, the retired
  verify/deploy/pes/relax/dyn/locked/select2 chain, and their `*_specification`
  siblings whose specs were archived).
- **Rewritten against the current owners:** `tests/test_mlff_campaign_cli.py`
  (retained the neutral configuration/store/manifest/wrapper/stage tests, added
  a current-surface parser test and a retired-command-absence test);
  `test_mlff_target_size_p4d_runtime_cutover.py`,
  `test_mlff_target_size_p4f_storage_docs_structure.py`,
  `test_mlff_target_size_p5f_structure.py`,
  `test_mlff_target_size_execution_p3f.py`, `test_native_build_registry.py`,
  `test_mlff_doc_arch1_specification.py` — all now assert the current V7
  contract, several as structural-absence assertions.
- **Individual retired tests removed** from otherwise-current files (eval2,
  data9b1 checkpoint control, inference-parallel scheduler, precision profiles,
  STOR1/3/4/5, train2a policy, parallel resources, opt-ctrl1, cueq diagnostics).
- **Extracted** `tests/_mlff_tiny_mace.py` so the still-valid bounded real-MACE
  model factory survived deletion of the retired suite that hosted it.
- **New:** `tests/test_mlff_target_size_p6_p5a6_compatibility.py` and
  `tests/test_mlff_target_size_p6_destructive_closure.py`.

## 9. Documentation reconciliation

- `docs/arch_manuals/mlff_training_data/50_target_multiview.md` →
  **`50_target_size_selection.md`**, rewritten as the current target-size
  selection and post-selection validation chapter (split/orders/common
  preparation/paired-seed screen/reducer/currentness/invalidation scope/CV/fresh
  production/public commands).
- Parts I, II, III, IV, VI, VII reconciled: the retired chain removed from the
  workflow diagram, ownership table, retrieval indexes, terminology, resource
  invariants, decision summary, and extension boundaries; Part VI gained the
  current candidate-execution/continuation and provider-lifetime sections.
- `mlff_training_data_dependency_graph.json` schema 2 → 3: the eight retired
  nodes replaced by seven current ones
  (`TARGET_SIZE_DEVELOPMENT_SPLIT`, `CANONICAL_TRAINING_ORDER`,
  `CANONICAL_EVALUATION_LADDER`, `COMMON_TARGET_SIZE_PREPARATION`,
  `CURRENT_SELECTED_SET`, `POST_SELECTION_CV_ACCEPTANCE`,
  `FRESH_FINAL_PRODUCTION`), with updated forbidden paths and resource
  invariants.
- `architecture_revision` 106 → 107.
- **39 retired specifications archived** to `docs/history/mlff/retired_specs/`
  (65 files including PDFs and manifests) with an explicit README stating they
  are not current authority; the current spec index was pruned and 12 documents
  were repointed at the archive location.
- `README.md`, `campaign.toml.example`, and the FINAL-GPU1 runbook/guide pair
  reconciled to the current architecture and command surface.

## 10. Material deviations and risks

1. **Removal of the downstream verification lifecycle.** `deploy_verify`,
   `pes_verify`, `relax_verify`, `dyn_verify`, `locked_test2`, and `select2`
   were deleted rather than retained as R6. Reason: their persisted record
   identities bind `target_size_study_digest` / `target_data_role_freeze_digest`,
   and their only entry point was the retired `verify` command whose inputs
   (`training_campaign`, `data8:`, `execution:`, `materialization:`) are
   quarantined by the P4 cutover — so they were unreachable *and*
   retired-lineage-bound, not independently supported. This removes a
   user-visible product capability (physical/deployment/locked verification).
   Re-establishing it on V7 selected/final-production authority is a design
   question outside P6's accepted scope and is flagged for Design review.
2. **Retained-but-unreachable R6/R8 modules.** Fifteen qualification/performance/
   observable modules (§3) remain exported with no current CLI entry point. They
   carry no retired target-size lineage, but their reachability depends on a
   future downstream-lifecycle design.
3. **Fixture portability.** The preserved P5A6 workspace is git-ignored and its
   `campaign.toml` holds absolute paths, so the compatibility test skips (with an
   explicit rebuild command) on a checkout that has not regenerated it. It was
   executed and passed on the final candidate here; a companion always-running
   test asserts the recorded identity/manifest/builder are present and bound to
   the accepted baseline.
4. **Pre-existing red baseline.** 246 failures / 100 errors existed before P6 and
   are unrelated (version-pinned specification assertions and missing test data).
   They are attributed, not repaired.

## 11. Three-way final status

1. **Functional V7/P6 acceptance** — see §12 for the final assembled result.
2. **M-ladder scientific decision-preservation qualification** —
   **`deferred/unavailable`**. No representative larger-reference-population
   evidence exists in the repository; P6 did not manufacture decision-preservation
   from synthetic timing, and did not tune `M` using post-selection CV,
   calibration, or locked evidence.
3. **Long target-machine GPU / real-production qualification** — **`deferred`**
   to the established final-release phase, per the frozen parent. No GPU
   qualification is claimed.

## 12. Final assembled acceptance

### Re-derived affected surface

Derived from the assembled final diff (326 files changed; 10,711 insertions,
126,843 deletions), not from the initial deletion list:

- package import/export surface (`mdstats`, `mdstats.training_data`) and the
  native build registry;
- the campaign CLI parser, dispatch, stage machinery, public lifecycle
  projection, and STOR1/3/4/5 owners;
- persistence: `CampaignStore` encode/decode dispatch, `storage_references`,
  the target-size campaign state/terminal/cutover owners;
- P1/P2 preparation (`_prepare_catalog`) and the current authority builder;
- P3 target-size execution and `eval2`;
- P4 currentness/terminal/retention;
- P5 post-selection CV, final production, provider lifetime, `data8_bundle`,
  `campaign_control`, `adaptive_stop`;
- shared execution/resource/scheduling/precision/acceleration machinery
  (unchanged, but transitively reachable through removed imports);
- documentation: architecture manual chapters, assembled manual + PDF,
  dependency graph, specification index, README, config example, guides.

### Complete affected-surface regression (final candidate)

`conda run -n mace python -m pytest -n 16 -q -p no:randomly` over the whole
repository — chosen deliberately over a narrower bound because P6 crosses package
exports, foundational identity, persistence, and orchestration boundaries:

```text
200 failed, 2825 passed, 14 skipped, 100 errors
```

Compared line-by-line against the recorded pre-P6 baseline node-ID set:

```text
new failures introduced by P6: 0
```

All 286 remaining failing/erroring node IDs are members of the pre-P6 baseline
set. Their causes are two unrelated pre-existing families: missing
`tests/data/*.json` LTA topology/geometry fixtures (91 occurrences) and
version-pinned `*_specification` assertions comparing `mdstats.__version__`
(0.20.242a0) against the historical version each test was written at.

### Integration through real owners

`tests/test_mlff_target_size_p4g_assembled_integration.py` and
`tests/test_mlff_target_size_p5g_assembled_integration.py` execute the bounded
assembled lifecycle through the **real production CLI parser and dispatch**
(`cli.main(["--config", ..., "prepare"])`, then `select-target-size`,
`cross-validate`, `train-production` through `args.func(args)`), the real
`CampaignStore`/SQLite file, the real P1/P2/P3 owners, the real P4
reducer/terminal projection, `MacePostSelectionTrainer`, real candidate and
foundation provider authentication, `MaceCalculatorProvider.from_model_path`,
real EVAL2 reduction/admissibility, real final publication, and a fresh-process
reopen with re-resolved currentness. Both pass on the final candidate.

`tests/test_mlff_target_size_p6_destructive_closure.py::test_p6_current_workspace_closes_reopens_and_restarts_deterministically`
adds the P6-owned close/reopen/re-run/`status` path on the same owners.

### Restart / invalidation matrix

Executed on the final candidate through the real owners:

- `test_mlff_target_size_p4e_terminal_and_invalidation.py` — 27 tests: terminal
  derivation and re-derivation on reload, rejection of independently mutated
  `N_selected` / `T_selected` / adopted head / foreign membership, fresh
  generation on any changed scientific authority, CV-only and production-only
  settings proven target-size neutral, target-size policy change proven
  invalidating, operational interruption resumable, typed scientific terminal
  distinguished from interruption, and the mandatory negative cases
  (stale/missing pointer, missing/corrupt adopted head, persisted tamper, stale
  current-view and stale current-report exposure, historical revision
  masquerade).
- `test_mlff_target_size_p4b_regime_cutover.py` — 20 tests: obsolete-generation
  detection, quarantine-not-translation, old selected `N` unreadable as current
  authority, promotion refused while retired authority is reachable, idempotent
  quarantine, interrupted-cutover resume, CAS conflict rejection, and fail-closed
  guidance for legacy/uninitialised/transitioning campaigns.
- `test_mlff_target_size_p5e_production_and_restart.py` — 22 tests: CV-only
  policy change leaves P4 byte-identical, production-only horizon change requires
  no CV rerun, stale-generation descendants unreachable, publication idempotence
  and create-once conflict, and the P4 selection surviving the whole
  post-selection lifecycle.

All pass.

### Determinism, reference equivalence, resource/lifecycle

- P3 execution suites (`p3a`–`p3f`) including deterministic reproduction,
  exact continuation across fidelity boundaries, restart, and the structural
  proof that the P3 path is unreachable from the retired production surface —
  pass.
- P5 provider-lifetime guards (`p5_r6`–`p5_r11`), including the real-owner
  foundation-provider counterfactuals and the replay-enabled non-scratch
  assembled lifecycle — pass.
- Resource/scheduling suites (`test_mlff_parallel_resources.py`,
  `test_mlff_inference_parallel_scheduler.py`, `test_mlff_cpu_*`) — pass.
- No retained optimized current kernel lost its oracle: the R8 measurement
  modules (`perfbase1`, `performance_baseline`, `observable_comparison`,
  `observable_validation`) were retained precisely so independent equivalence and
  performance measurement over current implementations survives. The retired
  MVQUAL/M5 product benchmark, whose central contract was reopening V5 state and
  executing fixed-eight MVQUAL2, was deleted rather than rewritten.

### Repository-required checks

- `python tools/build_mlff_architecture_manual.py` — deterministic assembly.
- `python docs/build_pdfs.py build --target ...` for the architecture manual and
  every changed Markdown/PDF sibling pair — all rebuilt with pandoc 3.10.2 +
  typst 0.15.1; manifests regenerated.
- Intra-repository Markdown link scan — no new broken link.
- `python -m unittest -v tests.test_docs_pdf_builder` — the documentation
  builder regression the repository's `docs-build` workflow runs before
  publishing: 13 tests, OK.
- No repository lint/type configuration is declared (`pyproject.toml` carries
  `[tool.pytest.ini_options]` only; there is no ruff/mypy/flake8/pre-commit
  configuration), so no additional static gate applies. The only CI workflow is
  `docs-build`, whose builder regression and pinned pandoc/typst toolchain were
  both exercised locally above.

## 12. Revision 13 — final proxy-proof acceptance and executable evidence

Under `P6_REVISION_13_AUTHORITY.md` and `P6_REVISION_13_FINAL_PROXY_PROOF_AND_EXECUTION_EVIDENCE_CLOSURE_AMENDMENT.md`, the acceptance suite and executable evidence were closed on tested executable commit `4c4b2f5a93fa86aa17613afae2279c5faf5446a5` / tree `164a2393613faa2aa2c116117e266ee56abf15eb`.

### 12.1 R13-A: SHA-256 receipt retention crossing real prune boundary

In `tests/test_mlff_target_size_p6_destructive_closure.py::test_p6_r13_sha256_receipt_retention_through_storage_cleanup`:
- Inserted 100,050 unique syntactically valid receipt rows into the real `receipts` table in a single batched transaction, exceeding the default 100,000-row `prune_sha256_receipts()` limit.
- Verified real cached digests on physical files through `sha256_file_cached()` and stored validation receipts.
- Executed public `storage cleanup --tier safe` and `storage cleanup --tier cache` through `cli.main()`.
- Proved receipt count is exactly preserved (100,050 rows retained), sentinel rows remain, validation receipts remain unchanged, and `sha256_file_cached()` returns exact digests without recomputation.
- Structural AST inspection proves `prune_sha256_receipts` is absent from `_campaign_cleanup()` and `CampaignStore.compact()`.

### 12.2 R13-B: Real CampaignStore external pointer retention

In `tests/test_mlff_target_size_p6_destructive_closure.py::test_p6_r13_orphan_record_positive_reclamation_and_referenced_record_retention`:
- Published a >4 MiB record via `CampaignStore.put_record()`, verifying `EXTERNAL_RECORD_POINTER_SCHEMA` generation.
- Verified the referenced external sharded artifact is within `store.external_record_directory` and owned by `store.storage_references()`.
- Set the referenced artifact mtime to 48 hours old (older than `[cleanup].stale_age_hours`).
- Created an unreferenced sibling artifact with 48h mtime.
- Executed public safe and cache cleanup.
- Proved the stale referenced file and its record payload roundtrip remain intact, while the stale unreferenced sibling artifact is positively reclaimed.

### 12.3 R12 historical workspace/runs trap retention

`test_p6_r12_historical_run_tree_trap_across_marker_cases` verifies retention across all 4 marker cases:
1. No `active_process.json`;
2. Malformed `active_process.json`;
3. Dead/stale PID;
4. Live process PID.
All historical run directories, logs, caches, and markers remain intact under both safe and cache cleanup.

### 12.4 Dedicated qualification driver results (A, B, C)

Command:
```bash
conda run -n mace python qualification/p6-p5a6-compat/qualify_p5a6_to_p6.py
```
Output:
```text
P5A6 -> P6 authenticated current-generation compatibility: PASS
P6 -> P6 current-generation restart: PASS
V5/V6 -> reject-before-reuse: PASS
```

### 12.5 Focused R13 stage-local closure results

Command:
```bash
conda run -n mace pytest -v tests/test_mlff_target_size_p6_destructive_closure.py tests/test_mlff_stor1_storage_accounting.py tests/test_mlff_stor3_safe_reclamation.py tests/test_mlff_stor4_manual_reclamation.py
```
Result: **51 passed, 0 failed** in 101s.

### 12.6 Full MLFF target-size & storage regression suite

Command:
```bash
conda run -n mace pytest -n 32 tests/test_mlff_target_size_*.py tests/test_mlff_stor*.py tests/test_mlff_campaign_cli.py tests/test_mlff_doc_arch1_specification.py
```
Result: **517 passed, 0 failed** in 150s.

### 12.7 Broader repository-wide CPU-safe regression

Command:
```bash
conda run -n mace python -m pytest -n 32 -q -p no:randomly
```
Result:
```text
202 failed, 2843 passed, 14 skipped, 2282 warnings, 116 errors in 270s
```
All failing and erroring node IDs are pre-existing baseline failures (version-pinned `*_specification` tests and missing `tests/data/*.json` fixtures). Zero new nonpasses are attributable to P6 / Revision 13.

### 12.8 Repository documentation and PDF generation

Command:
```bash
conda run -n mace python tools/build_mlff_architecture_manual.py
```
Output: `docs/arch_manuals/mlff_training_data_architecture.md` assembled and verified.

## 13. Final status

1. **Functional V7/P6 Revision 13 acceptance — PASS.** Contract reconciliation, structural absence, discriminating SHA-256 receipt retention, real CampaignStore external pointer retention, 4-case historical run trap retention, separately proven A/B/C compatibility, real parser lifecycle, and broader regression with zero new attributable nonpasses all executed and passed on tested tree `164a2393613faa2aa2c116117e266ee56abf15eb`.
2. **M-ladder scientific decision-preservation qualification — `deferred/unavailable`.**
3. **Long target-machine GPU / real-production qualification — `deferred`.**
