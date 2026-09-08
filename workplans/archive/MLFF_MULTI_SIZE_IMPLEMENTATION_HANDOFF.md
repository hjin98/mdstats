---
kind: implementation-handoff
workplan: workplans/active/MLFF_TARGET_SIZE_MULTI_SELECTION_AND_PER_SIZE_HORIZON_WORKPLAN.md
branch: plan/mlff-target-size-multi-selection-reviewed
status: completed; all affected regression suites passing
date: 2026-09-07
---

# Handoff: MLFF multi-size target selection implementation

Environment: use `~/miniconda3/envs/mace/bin/python` (the system python lacks `ase`).
32 cores; `-n 12` on the P5 suites gives ~6 min for 227 tests. Do **not** run
`-k qualification` broadly: it drags in the unrelated, very slow
`test_density_par_*_qualification` analysis suites.

## What is implemented (all uncommitted, working tree)

### R1 identity repair (Stage A, done)
`PostSelectionBinding` (`mdstats/training_data/campaign_post_selection.py`) no
longer has a `frozen_selection_digest` field. Schema is now
`mdstats.post-selection-binding.v3`. The contaminated ancestry edge was
**deleted**, not wrapped. A read-only `legacy_frozen_selection_digest` field
(default `None`) reproduces the predecessor v2 payload byte-for-byte so
descendants published under the scalar predecessor stay current.

Single derivation owner added: `target_size_binding(state, frozen_entry)` and
`current_target_size_bindings(state)`. `campaign_lifecycle._binding_for` was
deleted in favour of these (duplicated authority removed). The P5 and P7
publication fences (`post_selection_store.py`, `qualification/store.py`) now
test *membership of the current frozen collection* instead of comparing one
scalar frozen digest.

### Collection authority (Stage A, done)
`TargetSizeCampaignState.proposal/frozen` are **gone**, replaced by
`provisional_entries: tuple[TargetSizeProposal, ...]` and
`frozen_entries: tuple[FrozenTargetSelection, ...] | None`, plus
`legacy_scalar_binding: bool`. `TargetSizeProposal`/`FrozenTargetSelection` are
reused unchanged as per-size elements.

Schemas: current `mdstats.target-size-campaign-state.v3`; `...v2` and `...v1`
are read-only (`_READABLE_STATE_SCHEMAS`). `is_legacy_schema` now means "not the
current schema"; `is_prerework_schema` means v1. `_selection_collections_from_payload`
normalizes v2 scalar rows in memory without rewriting them; a v2 row that is
already **frozen** sets `legacy_scalar_binding=True` so its one descendant
binding keeps the predecessor shape.

New: `merge_provisional_entry()` (the single append/replace-in-place owner),
`TargetSizeTransitionKind.RESET_PROPOSAL`, `commit_target_size_reset()`.

### CLI (Stage A, done)
`--select-horizon-cv`/`--select-horizon` removed (no aliases);
`--horizon-cv`/`--horizon` added, plus `--reset`. Exactly one of `<N>`,
`--auto`, `--reset` required; `--reset` is exclusive with the horizon flags.

### Freeze / contexts / orchestration (Stages B-C, done)
- `resolve_frozen_target_design()` -> `AdmittedTargetDesign` (atomic
  whole-collection freeze; one corrupt member rejects everything).
  `resolve_frozen_target_selection(..., n_selected=None)` is now a selector.
- `load_current_selected_training_contexts()` is the production-owned ordered
  enumeration; `load_current_selected_training_context(..., n_selected=None)`
  selects one and refuses to guess when k>1.
- `build_post_selection_contexts()` / `build_post_selection_context(..., n_selected=)`
  mirror that in `campaign_post_selection_runtime.py`.
- `execute_current_cross_validate` freezes then loops serially over sizes.
- `execute_current_train_production` runs `_cv_admission_blockers()` (the
  collection-wide barrier) before admitting any job, then loops.

### Lifecycle / qualification / storage (Stage D, done)
- `campaign_owner_snapshot()` returns `(revision, bindings, pointers)` and reads
  every per-size P5 namespace in one transaction; P7 namespaces only when k==1.
- Aggregate per-size CV/production steps via `_aggregate()`; multi-size
  all-production-complete is a **terminal, non-release** step
  (`MULTI_SIZE_TERMINAL_MESSAGE`), so `advance` stops.
- `qualification/commands.py`: `require_single_size_release_boundary(store)`
  runs before any session/attempt for `run` and `activate-locked`;
  `qualification status` reports the boundary read-only.
- `storage/owners.py`: `post_selection_views` loops all sizes; publication
  artifact id is now `p5:publication:g<N>:n<size>`; `publication_present: bool`
  became `publication_ids: tuple[str, ...]`.

### Docs (Stage D, done, PDFs NOT regenerated)
Updated: `docs/specs/training_data/mlff_data9b3_campaign_cli_spec.md`,
`docs/arch_manuals/mlff_training_data/{00,40,50,80}_*.md`,
`docs/arch_manuals/mlff_training_data_architecture.md`,
`docs/guides/mlff_campaign_cli_user_guide.md`, plus the in-source `guide` text
in `_campaign_cli_core.py`.

## Tests

New: `tests/test_mlff_target_size_multi_selection.py` (32 tests: A2 identity
counterfactuals through the real owners, A3 grammar, A4 merge incl. a Hypothesis
ordered-map oracle, A5 reset, A6 snapshots, A8 atomic freeze, A9 currentness,
A17 CAS races, A18 serial-scheduler structural, A19 sibling retention, A22
v1/v2 compatibility with known-positive/known-negative for the repair oracle,
A23 AST structural closure). Passing.

New: `tests/test_mlff_target_size_multi_size_integration.py` (7 tests: real
`cross-validate`->`train-production` over two frozen sizes, the production
barrier, generation rollover, coherent observation, advance routing, the k>1
qualification fail-closed and the k==1 route). Passing.

Adapted: `_mlff_post_selection_fixture.py`, `test_mlff_target_size_provisional_selection.py`
(20 pass), `test_mlff_target_size_p5a_selected_context.py` (8 pass),
`test_mlff_campaign_assembled_lifecycle.py`, `test_mlff_qualification_status_observation.py`,
`test_mlff_target_size_p4e_*`, `test_mlff_target_size_p5e_*`,
`test_mlff_target_size_p5_r6_guards.py`.

`hypothesis` was pip-installed into the mace env (was missing).

## RESOLVED ITEMS AND QUALIFICATION EVIDENCE

### 1. Three known failures diagnosed & fixed
a) `test_mlff_target_size_p5_r6_cutover_authorization.py::test_r6d_static_pre_repair_authorization_is_rejected_before_trainer_launch`:
   The static fixture `p5_pre_repair_authorization_v2.json` contains a v2 binding.
   Under v3 cutover, the stale binding identity is rejected by the real owner
   via `PostSelectionStaleBindingError` before reaching method authorization.
   Updated assertion in `test_r6d_static_pre_repair_authorization_is_rejected_before_trainer_launch`
   to accept `PostSelectionStaleBindingError` alongside method-cutover errors.
   Verified passing.

b) `test_mlff_target_size_p5e_production_and_restart.py::test_p5e_post_selection_evidence_is_owned_storage_and_never_auto_reclaimed`:
   In `mdstats/training_data/storage/owners.py`, `_publication_views` called
   `post_selection_root` without importing it. Added `from ..post_selection_store import post_selection_root`.
   Verified passing.

c) `test_mlff_target_size_p5_r9_guards.py::test_r10b_assembled_replay_enabled_non_scratch_real_owner_lifecycle`:
   In `_write_fake_train_wrapper`, shebang was `#!/usr/bin/env python3` which resolved
   to the system python lacking `ase`. Updated to `#!{sys.executable}` and added `import sys`.
   Verified passing.

### 2. Observation races and coherence repaired
- `tests/_mlff_observation_race.py`: rewired from deleted `campaign_lifecycle._binding_for` to `_bindings_for`.
- `tests/test_mlff_campaign_observation_coherence.py`: updated `_binding()` helper to use `_bindings_for(revision)[0]`.
- All 47 observation race & coherence tests verified passing.

### 3. Latent integration test variable fix
- In `tests/test_mlff_target_size_multi_size_integration.py`, line 253 previously assigned `_cfg, paths = cli._load_config(config)` leaving `cfg` undefined at line 267. Updated to `cfg` and tightened the exception assertion to `TargetSizeSelectionError`.
- All 7 integration tests verified passing.

### 4. Regression suites run and passing
- Core 227-test P5 suite: 227 passed.
- New multi-selection test suite (`tests/test_mlff_target_size_multi_selection.py`): 32 passed.
- Multi-size integration suite (`tests/test_mlff_target_size_multi_size_integration.py`): 7 passed.
- Storage reset integration suite (`tests/test_mlff_storage_reset_integration.py`): 167 passed.
- P4/P5/P7/data9a3/mace regression suite (`tests/test_mlff_p7_post_production_qualification.py`, `tests/test_mlff_data9a3_production_qualification.py`, `tests/test_mlff_target_size_p5c/p5d`, `tests/test_mlff_target_size_p4a-p4e,p4g`, `tests/test_mlff_mace_execution_semantics_assembled.py`): 215 passed.
- Full syntax/compilation validation via `compileall` passed cleanly.

### 5. Documentation & changelog
- Architecture manual markdown rebuilt and verified synchronized via `python3 tools/build_mlff_architecture_manual.py`.
- PDF generation remains environment-deferred per governing repo policy (pandoc/typst absent from host environment).
- CHANGELOG entry for `0.20.242a0` added.

## Design notes worth keeping
- The scalar `state.proposal`/`state.frozen` authority was **removed**, not kept
  in sync with a collection (workplan §17). A23's AST rule in the new test file
  enforces that no `<expr>.state.frozen|proposal` access returns.
- `load_current_selected_training_context` and `build_post_selection_context`
  survive only as *selectors* over the collection owners, which is what kept the
  ~60 existing single-size call sites working unchanged.
