# P4 implementation progress and evidence log

Working record for `P4_ATOMIC_RUNTIME_PERSISTENCE_CUTOVER.md` (package revision 4).
Authority: frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md`.

This file exists so an interrupted implementation can be restarted cleanly. It records,
per pass: what was implemented, which owners were touched, what evidence was executed,
and what remains. It is coordination material, not product documentation.

## Status summary

| Pass | Scope | State |
|---|---|---|
| Entry gate | P3A9 closure + section 3 assertions | **CLOSED** |
| P4-A | CampaignStore state, canonical generation, CAS, transition identity | in progress |
| P4-B | Regime cutover owner | not started |
| P4-C | Cross-store adoption, retention fence, restart, concurrency | not started |
| P4-D | Atomic `prepare` / `select-target-size` production switch | not started |
| P4-E | Terminal projection, semantic restart, invalidation | not started |
| P4-F | Full STOR integration, docs, structural closure | not started |
| P4-G | Assembled affected-surface closure | not started |

---

## Entry gate (section 0.1 / section 3)

Package metadata is `status: active` with
`entry_gate: cumulative-p3-revision-7-through-p3a9-accepted-at-9d195807cff0bb8042f447ac33ceb0586ed708ac`
and `entry_p3_closure_commit: 9d195807cff0bb8042f447ac33ceb0586ed708ac`. The package README records
the same formal P3 closure. Executable P4 work is therefore authorized.

Evidence executed before any P4 edit:

- `tests/test_mlff_target_size_p3a9_head_pointer_reconciliation.py` — **15 passed** (81 s).
  Covers stale-`current_head.json` unique authenticated successor recovery,
  complete-batch-without-head recovery, fork/orphan/corrupt-successor rejection,
  fresh-process identity equivalence, and canonical lock identity.
- Baseline P3/P2 regression (`test_mlff_target_size_execution_p3a..f`,
  `test_mlff_target_size_p3a4_final_review`, `test_mlff_target_size_statistical_authorities`)
  — see "Baseline regression" below.

## Section 2.2 reconnaissance (recorded, reusable)

Real owners located (all under `mdstats/training_data/`):

- **CampaignStore / SQLite owner**: `_campaign_cli_core.py:361` (`class CampaignStore`).
  Tables: `meta`, `records`, `stages`, `events`. Schema marker
  `CAMPAIGN_STATE_SCHEMA = "mdstats.mlff-campaign-state.v2"` (line 127).
  Thread-local pooled connection via `CampaignStore._connect()`; no transaction/CAS primitive existed.
- **`prepare`**: `command_prepare` at `_campaign_cli_core.py:10688` ->
  `_execute_prepare_current_authority`.
- **`select-target-size`**: `command_select_target_size` at `_campaign_cli_core.py:16372`.
  Parser registration near line 29688.
- **Pre-existing target-size generation authority** (retired authority to consolidate):
  there is **no** numeric generation counter. The de-facto authority is the
  `target_size_study` record (`target_size_study.py`, `_ensure_target_size_study` at
  `_campaign_cli_core.py:5068`) combined with the prepare restart receipt schema
  `PREPARE_RESTART_RECEIPT_SCHEMA` (line 129) and the reset path
  `_invalidate_train2_downstream_state` (line 5261), which together implement
  "screening generation changed -> reset downstream state". P4 therefore creates one new
  canonical generation field and must make that retired authority non-authoritative
  in the same cutover (P4-B/P4-D), rather than letting both advance.
- **P1 owner**: `mdstats/training_data/neutral_substrate/` (sources, frame_authority,
  identity, partition, split_exclusion).
- **P2 owner**: `target_size_experiment.py` (`TargetSizeStatisticalAggregate`,
  `TargetSizeReducerState`, `ReducerStatus`, `TargetTrainingOrder.candidate_digest`,
  `target_training_prefix_digest`, `advance_target_size_reducer`).
- **P3 owner**: `target_size_execution/` package; public API in its `__init__.py`.
  Key entrypoints: `initialize_target_size_screen`, `reconcile_target_size_screen_root`,
  `TargetSizeRestartAuthority`, `TargetSizeExecutionResolver`, `TargetSizeExecutionHead`,
  `resolve_target_size_candidate_for_resume`, `commit_target_size_boundary_batch`.
  P3 head/screen mutation lock: `<root>/.screen_commit.lock` (`fcntl.flock`, exclusive)
  taken inside `reconcile_target_size_screen_root` and
  `_commit_target_size_boundary_batch_locked`.
- **Storage owners**: `storage_accounting.py`, `storage_reclamation.py`, `storage_archive.py`;
  CLI `command_storage` (`_campaign_cli_core.py:27156`), `command_cleanup` (27841),
  `command_archive` (27790), `command_deduplicate` (27750).
- **Docs**: `docs/guides/mlff_campaign_cli_user_guide.md`, in-module guide text
  (`command_guide`, `_campaign_cli_core.py:28705`), `campaign.toml.example`.

Retired target-size authority inventory (section 7.3) confirmed present:
`target_size_study.py`, `target_data_roles.py` (`TargetDataRoleFreeze`),
`target_coverage_feasibility.py` (FEAS), `target_coverage_sparse_index.py` (MVIDX),
`target_multi_view_selector*.py` (MVSEL), `target_multi_view_repair*.py` (REPAIR),
`target_multi_view_selection_state*.py` (MVSTATE), `target_multi_view_qualification_v2.py` (MVQUAL).

### Baseline regression (pre-P4, for failure attribution)

- P3/P2 suites (`test_mlff_target_size_execution_p3a..f`, `test_mlff_target_size_p3a4_final_review`,
  `test_mlff_target_size_statistical_authorities`): **106 passed** (179 s).
- **Pre-existing failures present before any P4 edit** (verified by stashing the P4 diff):
  - `tests/test_mlff_data9b3_campaign_cli_specification.py::test_data9b3_dependency_graph_contract`
  - `tests/test_mlff_data9b3_campaign_cli_specification.py::test_data9b3_version_and_user_surface`
  - `tests/test_mlff_data9b3_campaign_cli_specification.py::test_data9b3_architecture_and_stage_plan_integration`
  - `tests/test_mlff_stor1_storage_accounting.py::test_materialization_record_path_does_not_confer_external_cleanup_authority`

  These are **not** caused by P4. The three `data9b3` cases assert architecture-manual/stage-plan text
  that has since moved; the STOR1 case is a storage-ownership assertion. They are carried into the
  P4-F documentation/structural pass and the P4-G assembled closure for disposition.

---

## Pass P4-A — CampaignStore state, canonical generation, CAS, transition identity

**State: CLOSED** (semantic + functional).

### What was implemented

New owner `mdstats/training_data/campaign_target_size_state.py` (version-agnostic; no `v7`/`V7`
symbol, key, schema, or record name). It owns the single mutable current-runtime target-size
authority and nothing scientific:

- `TargetSizeRegime` = `legacy | transitioning | current` (durable regime marker, section 7.1).
- `TargetSizeLifecycle` = `unconverted | awaiting_authorities | authorities_bound | screen_active |
  terminal_selected | terminal_scientific_failure`.
- `TargetSizeCampaignState` — the one mutable aggregate. Binds schema, regime, **one** canonical
  `generation`, subordinate `attempt`, lifecycle, P1 identities (`frame_authority_digest`,
  `neutral_statistical_base_digest`, `split_exclusion_digest`), P2 identities (`policy_digest`,
  `experiment_definition_digest`, `aggregate_digest`), P3 identities (`execution_context_digest`,
  `common_preparation_digest`, `screen_window_digest`, campaign-relative `execution_root`),
  the adopted immutable P3 `adopted_execution_head_digest` + `adopted_reducer_state_digest`,
  the terminal projection, and a stop/failure `disposition`. It stores **references and digests
  only**; no P1-P3 immutable graph is copied into SQLite.
- `TargetSizeTerminalProjection` (section 5 fields, not yet publicly wired — P4-E owns wiring).
  `N_selected` and exact `T_selected` identity are structurally forced to be bound together, and
  the projection must agree with the adopted head/reducer references.
- `TargetSizeCasExpectation` — the complete predecessor token: schema + regime + canonical
  generation + subordinate attempt + predecessor state revision.
- `target_size_transition_identity(...)` — deterministic logical-transition identity binding the
  transition kind, the exact expected predecessor authority, and the **complete** canonical
  successor payload. No PID, timestamp, or retry count participates.
- `commit_target_size_campaign_transition(...)` — the only mutation entrypoint.
- Typed outcomes: `TargetSizeCampaignConflictError` (with `conflict_kind` in
  `stale_generation | unknown_generation | stale_revision | regime_mismatch | attempt_mismatch |
  schema_mismatch | uninitialized | already_initialized`) and
  `TargetSizeCampaignCorruptionError`.

Store-level primitive added to the real owner `_campaign_cli_core.py`:

- `CampaignStore.exclusive_transaction()` — one real serialized SQLite write transaction
  (`BEGIN IMMEDIATE`, rollback on any exception, refuses to nest). Compare-then-write is never an
  unlocked CLI operation.
- New table `target_size_campaign_state` in the campaign schema script:
  append-only chain with `state_revision` PK, `sequence` UNIQUE, `predecessor_revision` UNIQUE,
  `transition_identity` UNIQUE. The `predecessor_revision` unique index makes
  "two divergent transitions from one predecessor" structurally impossible even across processes,
  and `transition_identity` uniqueness is what makes an exact retry recognizable.
  Current authority = the maximum-`sequence` row; there is no second head pointer to drift.

`state_revision` is an authenticated chain digest over
`{sequence, predecessor_revision, transition_identity, kind, state payload}`, so any out-of-band
row edit is detected on load as corruption rather than accepted as current authority.

### Canonical generation decision (section 4.1)

Reconnaissance found **no** pre-existing numeric target-size generation counter. The de-facto
retired authority is `target_size_study` + `PREPARE_RESTART_RECEIPT_SCHEMA` +
`_invalidate_train2_downstream_state`. P4-A therefore creates the single canonical `generation`
field; P4-B/P4-D must make the retired authority unreachable in the same destructive cutover so the
two never advance independently. `_validate_transition_semantics` enforces that only
`begin_cutover` / `advance_generation` may change the generation and that a replaced generation
cannot inherit a subordinate attempt.

### Evidence executed

`tests/test_mlff_target_size_p4a_campaign_state_cas.py` — **35 passed**. Real `CampaignStore`
SQLite files throughout; no in-memory or faked store.

| Gate item | Covering tests |
|---|---|
| schema/serialization roundtrip | `req1_state_serialization_roundtrip_is_exact`, `req1_tampered_payload_fails_authentication` |
| real SQLite close/reopen | `req2_state_survives_real_close_and_reopen`, `req2_genesis_is_created_once_and_reused` |
| rollback leaves predecessor unchanged | `req3_transaction_rollback_cannot_expose_partial_state`, `req3_nested_transactions_are_refused` |
| older-generation rejection | `req4_older_generation_writer_loses_after_takeover`, `req4_generation_replacement_clears_subordinate_attempt`, `req4_only_generation_transitions_may_change_the_generation` |
| same-generation stale-revision rejection | `req5_same_generation_stale_revision_cannot_mutate`, `req5_attempt_mismatch_is_typed_conflict`, `req5_regime_mismatch_is_typed_conflict` |
| divergent same-predecessor race admits one successor | `req6_two_connections_racing_one_predecessor_admit_one_successor` (two independent `CampaignStore` connections), `req6_process_level_race_admits_exactly_one_successor` (4 spawned processes synchronized on a barrier so all read the same predecessor) |
| exact logical duplicate retry idempotent | `req7_exact_duplicate_retry_returns_the_committed_successor`, `req7_duplicate_retry_after_further_transitions_still_verifies`, `req7_duplicate_genesis_retry_is_idempotent` |
| near-duplicate changed-reference retry conflicts | `req8_near_duplicate_changed_reference_conflicts` (5 parametrizations), `req8_same_successor_under_a_different_kind_is_not_a_duplicate`, `req8_transition_identity_binds_kind_predecessor_and_successor` |
| one canonical generation authority | `req9_only_one_canonical_generation_symbol_exists_in_current_state_authority` (AST field inspection), `req9_campaign_store_owns_exactly_one_target_size_state_table`, `req9_state_table_structurally_admits_one_successor_per_predecessor` |
| retired schema cannot deserialize/relabel as current | `req10_retired_schema_is_never_reinterpreted_as_current`, `req10_relabeled_retired_payload_fails_authentication`, `req10_out_of_band_row_edit_is_detected_as_corruption` |
| no `v7_`/`V7` production name | `req11_no_version_prefixed_production_names_in_new_state_authority` |

Stage-local affected regression (campaign store/CLI surface touched by the schema + transaction
addition): `test_mlff_campaign_cli`, `test_mlff_data9b3_campaign_cli_specification`,
`test_mlff_cli_semantic_orchestration`, `test_mlff_stor1_storage_accounting`,
`test_mlff_data9b1_campaign_checkpoint_control`, `test_mlff_campaign_production_gate_anchor`
— **99 passed, 1 skipped, 4 failed**; all 4 failures are the pre-existing baseline failures listed
above (confirmed by stashing the P4 diff and re-running).

### Defect found and repaired during the gate

The first CAS mismatch classifier compared regime/attempt before the predecessor revision, so a
same-generation writer that lost a race was reported as `attempt_mismatch` instead of
`stale_revision`. Ordering is now schema -> generation -> revision -> regime/attempt: generation is
the coarse authority, and because the revision digest authenticates the whole state, a regime or
attempt disagreement *at a matching revision* is a forged expectation rather than a lost race.

### Not yet done in P4-A (owned by later passes, intentionally)

- No public runtime wiring of the terminal projection (P4-E).
- Regime transition `legacy -> transitioning -> current` semantics and retired-state
  quarantine (P4-B).
- P3 head adoption, retention fence, recovery matrix (P4-C).
