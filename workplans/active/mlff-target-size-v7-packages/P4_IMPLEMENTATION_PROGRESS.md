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
| P4-A | CampaignStore state, canonical generation, CAS, transition identity | **CLOSED** |
| P4-B | Regime cutover owner | **CLOSED** |
| P4-C | Cross-store adoption, retention fence, restart, concurrency | **CLOSED** |
| P4-D | Atomic `prepare` / `select-target-size` production switch | **CLOSED** |
| P4-E | Terminal projection, semantic restart, invalidation | **CLOSED** |
| P4-F | Full STOR integration, docs, structural closure | **CLOSED** |
| P4-G | Assembled affected-surface closure | in progress |

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

---

## Pass P4-B — Regime cutover owner

**State: CLOSED** (semantic + functional). Commit: see `git log` for
`feat(mlff): P4-B destructive target-size regime cutover owner`.

### What was implemented

New owner `mdstats/training_data/campaign_target_size_cutover.py`, consuming the P4-A state
authority. No public runtime is wired yet (P4-D owns the switch), so the runtime stays coherently
pre-switch.

- `begin_target_size_cutover(store)` — CAS `legacy -> transitioning`, allocating the **new canonical
  generation** in the same transition. Re-entry on an already-transitioning campaign returns the
  persisted transition instead of allocating a second generation, which is what makes a fresh
  process resume rather than restart.
- `inventory_retired_target_size_state(store)` — reads record **names only**. Retired payloads are
  never passed through a current deserializer, because that is exactly the reinterpretation the
  parent forbids.
- `quarantine_retired_target_size_state(store, generation=...)` — renames retired record keys under
  `quarantine:retired-target-size:g<N>:` inside one exclusive transaction. Renaming rather than
  copying keeps the operation total (sharded/native-pointer records quarantine exactly like compact
  ones), cheap, and idempotent, and it preserves the rows as forensic history without leaving them
  reachable from any current authority lookup. P4 deletes no historical scientific evidence; P6 owns
  broad topology deletion.
- `bind_current_target_size_authorities(...)` — CAS-binds the reconstructed P1/P2 identities while
  still `transitioning`.
- `complete_target_size_cutover(...)` — CAS `transitioning -> current`, but only after
  `assert_no_retired_target_size_authority(store)` proves no retired record is reachable.
- `require_current_target_size_runtime(store)` — the fail-closed gate with actionable guidance for
  legacy (destructive reset via `prepare`) and transitioning (resume the exact cutover) workspaces.
  There is no third answer: no mixed runtime exists.

### Retired-state inventory (section 7.3), as encoded in the owner

Exact keys: `target_size_study`, `target_size_historical_candidate_authority`,
`target_data_role_freeze`, `target_coverage_reference`, `target_coverage_feasibility`,
`target_coverage_sparse_index`, `target_multi_view_selection_v2`, `target_multi_view_repair_v2`,
`target_multi_view_qualification_v2`, `prepare_restart_receipt`, `training_campaign`,
`interim_evaluation`, `available_model_verification_set`, and the eleven `mlcv_*` pre-target
CV/role/catalog keys.

Prefixes: `materialization:`, `data8:` (per-variant prescribed target/evaluation materialization
authority — P3 owns candidate materialization now), `execution:`, `train2_runtime:`,
`adaptive_stop:`, `lightweight_rank:`, `checkpoint_catalog:`, `checkpoint_retention:`,
`checkpoint_shortlist:`, `evaluation:`, `selection:`, `interim_member:`, `committee_member:`,
`mlcv_run_selection:`, `mlcv_physical_attempt:`.

Reusable lower-level inputs (identity independent of retired target-size semantics; reusable only
by re-validating through their current owners — P1 consumes them via
`build_source_authority_from_data2_catalog` and `build_neutral_feature_evidence_from_data4_bundle`):
`source_catalog`, `frame_catalog`, `data4`, `data5`, `data6`.

Records that are neither retired target-size authority nor lower-level target-size input
(`replay_*`, `production_plan`, `production_qualification`, `foundation_target_audit`) are left
untouched: P4 quarantines only what is necessary for unambiguous current authority.

### Evidence executed

`tests/test_mlff_target_size_p4b_regime_cutover.py` — **19 passed**, all against real
`CampaignStore` SQLite files.

| Gate item | Covering tests |
|---|---|
| fresh current campaign | `req1_fresh_campaign_reaches_current_regime`, `req1_current_campaign_refuses_a_second_cutover` |
| legacy enters transition once | `req2_legacy_workspace_enters_transition_once`, `req2_inventory_separates_retired_authority_from_reusable_inputs` |
| old selected-N/selector never becomes current authority | `req3_retired_records_are_quarantined_not_translated`, `req3_old_selected_n_cannot_be_read_as_current_authority`, `req3_promotion_is_refused_while_retired_authority_is_reachable`, `req3_quarantine_is_idempotent`, `req3_retired_key_and_prefix_inventory_covers_the_frozen_list` |
| crash resumes the exact transition | `req4_fresh_process_resumes_the_exact_interrupted_transition` (spawned process finishes a cutover the dead parent started, keeping generation 1), `req4_interrupted_quarantine_replays_on_resume` |
| competing transition rejected | `req5_competing_cutover_transition_is_rejected`, `req5_divergent_transition_from_a_stale_revision_is_rejected`, `req5_repeating_the_exact_completion_is_idempotent_not_a_second_cutover` |
| no row-wise mixed execution | `req6_regime_is_campaign_wide_not_per_record` |
| actionable fail-closed guidance | `req6_legacy_campaign_fails_closed_with_reset_guidance`, `req6_uninitialized_campaign_fails_closed`, `req6_transitioning_campaign_fails_closed_with_resume_guidance` |
| version-agnostic naming | `test_p4b_no_version_prefixed_production_names` |

Stage-local affected regression: `test_mlff_target_size_p4a_campaign_state_cas`,
`test_mlff_target_size_p4b_regime_cutover`, `test_mlff_campaign_cli`,
`test_mlff_cli_semantic_orchestration` — **130 passed, 1 skipped**.

### Note recorded during the gate

Repeating the *exact* completion transition is idempotent by design (P4-A section 4.3), so the
first draft of the stale-revision test was wrong rather than the owner. The gate now asserts both:
an exact retry returns the same revision, and a transition that changed one authoritative
reference from the same stale predecessor is a typed `stale_revision` conflict.

---

## Pass P4-C — Cross-store adoption, retention fence, restart, concurrency

**State: CLOSED** (semantic + functional).

### What was implemented

**`mdstats/training_data/campaign_target_size_adoption.py`** (new owner)

- `adopt_reconciled_execution_head(store, revision, head, ...)` — CAS-adopts the exact immutable
  head digest plus its post-reducer digest. Re-adopting an identity the campaign already holds is a
  no-op, which is what makes crash recovery cheap: durable completed work is never rerun.
- `validate_head_scientific_identity(...)` — the head's pre/post reducer states must bind the
  campaign generation's P2 experiment definition and P3 execution context. Digest equality alone
  never authorizes adoption.
- `load_adopted_execution_head(resolver, revision)` — re-resolves the adopted head through the real
  P3 resolver. A missing or unauthenticated head is `TargetSizeAdoptionCorruptionError`; scientific
  authority is never rebuilt from the campaign summary.
- `reconcile_and_adopt_target_size_head(...)` — the section 6.1 canonical order in one place: P3
  reconciles and releases `.screen_commit.lock`, and only then does a short campaign transaction
  bind the result. `current_head.json` never participates; only the immutable head object returned
  by the real reconciler is adopted.

**`mdstats/training_data/campaign_target_size_retention.py`** (new owner, section 10.3)

Protection is derived from the **filesystem evidence graph**, never from what SQLite adopted —
that is the whole point, since the dangerous window is exactly when P3 has published and the
campaign has not yet adopted. Every head, batch, cell completion, and progress record in the
campaign-owned execution root seeds a reachability closure that follows *every* content-digest
token in each reachable record (an over-approximation on purpose: a safety fence should fail toward
retention and stay correct under schema growth). Released as provably unreachable residue: only a
member of a known content-addressed family whose identity component no reachable record mentions,
and only once it is older than the publication window.

Regime/lifecycle coupling: `transitioning` protects the whole root unconditionally; an active,
restartable, or terminal current generation protects the frontier while releasing proven residue;
a campaign with no current generation or no execution root produces an **inert** fence, so nothing
is permanently pinned (section 15).

**`mdstats/training_data/campaign_target_size_view.py`** (new)

Non-authoritative derived projection of current state, re-resolving the adopted head through the
real P3 resolver rather than copying reducer content into SQLite, so a view can never become a
second result manifest. A missing view is rebuilt; committed science is never rolled back to match it.

**Real STOR integration (smallest integration with the existing mechanism)**

- `storage_accounting.py`: `CampaignOwnershipBoundary` gained an optional `retention_fence`
  (typed by a new `RetentionFence` Protocol) consulted in `destructive_authorization` **after**
  every ownership/containment/protected-input check, on both the regular and the symlink branch.
  A fence can only *reduce* authority; it can never grant it, so external paths, symlink escapes,
  and ambiguous ownership stay denied regardless of the closure.
- `_campaign_cli_core.py`: one new helper `_campaign_ownership_boundary(cfg, paths, store)` now
  builds the boundary for **every** destructive production path — automatic safe cleanup
  (`_campaign_cleanup`), STOR2 checkpoint compaction, STOR4 manual tiers (`_build_manual_tier_report`),
  STOR5 deduplication, `command_archive`, and `command_cleanup`. `command_storage` keeps the
  unfenced boundary because STOR1 is read-only accounting whose only write is the report file
  outside any execution root. There are now zero remaining direct `CampaignOwnershipBoundary(...)`
  constructions in production code besides that helper.

### Evidence executed

`tests/test_mlff_target_size_p4c_cross_store_adoption.py` — **23 passed**. Real `CampaignStore`
SQLite, the real `target_size_execution` resolver/reconciler, and the real
`CampaignOwnershipBoundary` destructive authorization throughout.

Section 6.2 recovery matrix:

| Crash/restart state | Covering test |
|---|---|
| crash before P3 immutable publication | `recovery_crash_before_publication_leaves_campaign_unchanged` |
| complete batch durable, head absent | `recovery_complete_batch_without_head_is_reconciled_then_adopted` |
| successor head durable, P3 pointer stale | `recovery_stale_pointer_successor_is_reconciled_then_adopted` |
| P3 reconciled head ahead of SQLite | `recovery_sqlite_behind_p3_adopts_without_rerunning_science` (asserts no completion file was rewritten, and that re-adoption is a no-op) |
| SQLite references missing/corrupt P3 head | `recovery_missing_referenced_head_is_hard_corruption`, `recovery_corrupt_referenced_head_is_hard_corruption` |
| SQLite references older head, unique valid successor chain | `recovery_stale_pointer_successor_is_reconciled_then_adopted` (adopts under the same generation and attempt) |
| SQLite commit complete, derived view missing | `recovery_missing_derived_view_is_rebuilt_without_rolling_back` |
| crash during cutover | P4-B `req4_fresh_process_resumes_the_exact_interrupted_transition` |
| stale generation writer | `stale_generation_writer_cannot_mutate_or_touch_p3_history` (also byte-compares every P3 JSON before/after) |
| two same-generation writers race | `two_same_generation_adopters_admit_one_successor` |
| cleanup races publication -> adoption | `cleanup_racing_publication_and_adoption_deletes_nothing_adoptable` |

Authority and ordering:

- `current_head_pointer_is_not_campaign_authority` — deleting the rebuildable pointer does not
  invalidate the adoption, and forging it cannot change what the campaign adopted.
- `head_from_a_different_experiment_identity_is_rejected`,
  `head_from_a_different_execution_context_is_rejected`.
- `no_campaign_transaction_is_open_during_p3_reconciliation` — instruments the real reconciler and
  asserts the campaign connection is not in a transaction while it runs.
- `no_target_size_transaction_body_nests_reconciliation_or_cleanup` — AST proof over all four P4
  modules that no `exclusive_transaction` body calls reconciliation, batch commit, cleanup,
  dedup/archive, or unlink/rmtree.

Retention fence:

- `fence_protects_unadopted_head_and_batch_before_adoption` — the head/batch published but *not*
  adopted are denied deletion; absence of a SQLite reference is not orphanhood.
- `fence_protects_the_full_completion_and_snapshot_ancestry` — completions, trajectories,
  materializations, snapshots, roles, predictions, metrics, evaluation artifacts, continuations,
  planned rungs, and progress records are all denied.
- `fence_releases_provably_unreachable_owned_residue` — an aged orphan is reclaimable.
- `fence_retains_recent_evidence_that_could_still_be_referenced` — publication-window guard.
- `fence_never_grants_authority_outside_the_workspace` — external paths and symlink escapes.
- `production_cleanup_owner_consumes_the_retention_fence` — the real `_cleanup_remove` with the
  real `_campaign_ownership_boundary` refuses and records skips; this is production cleanup, not a
  test-local flag.
- `cleanup_racing_publication_and_adoption_deletes_nothing_adoptable` — a **separate spawned
  process** runs real destructive authorization over every JSON in the root (all aged past the
  window) while a successor head is published-but-unadopted: zero deletions, and the successor is
  still adoptable afterwards.
- `fence_is_inert_when_no_current_generation_owns_a_root`,
  `transitioning_campaign_protects_its_whole_execution_root`.

Stage-local affected regression: P4-A, P4-B, P4-C suites plus `test_mlff_stor1_storage_accounting`,
`test_mlff_campaign_cli`, `test_mlff_cli_semantic_orchestration`,
`test_mlff_rev3_storage_evaluation_optimizations`, `test_mlff_data9b1_campaign_checkpoint_control`,
`test_mlff_campaign_production_gate_anchor`, and the full
`test_mlff_target_size_p3a9_head_pointer_reconciliation` recovery suite —
**174 passed, 1 skipped, 1 failed**; the single failure is the pre-existing
`test_materialization_record_path_does_not_confer_external_cleanup_authority`.

### Defects found and repaired during the gate

1. **Fence released bulk evidence.** The first fence resolved an artifact's identity from the leaf
   filename, so `snapshots/<id>/boundary_1/snapshot.json` resolved to `snapshot` and was released.
   Reachability is now always decided by the identity component directly under the family
   directory, which covers both `<digest>.json` files and `<digest>/` bulk directories.
2. **Bulk directories use shortened identities.** P3 names snapshot/failure bulk directories with a
   truncated identity, so exact 64-character membership failed. A component shorter than 64
   characters is now matched as a prefix, and anything shorter than 12 characters is retained
   rather than guessed.
3. `command_storage` had no `store` in scope; it now uses the unfenced read-only boundary, which is
   correct for STOR1.

---

## Pass P4-D — Atomic `prepare` / `select-target-size` production switch

**State: CLOSED** (semantic + functional).

### What was implemented

New owner `mdstats/training_data/campaign_target_size_runtime.py` — the only current production
target-size orchestration. It owns sequencing and configuration translation; every scientific
decision stays with its P1/P2/P3 owner.

- `resolve_neutral_partition_policy(cfg)` — maps the existing `[partition]` namespace onto the
  accepted P1 `NeutralPartitionPolicy`. Translation only; every unset key keeps the P1 default.
- `build_current_target_size_authorities(cfg, paths, store)` — rebuilds
  P1 (`build_source_authority_from_data2_catalog` -> `build_vasp_canonical_frame_authority` ->
  `build_neutral_feature_evidence_from_data4_bundle` -> `build_neutral_statistical_base` ->
  `build_neutral_split_exclusion_evidence`), P2 (`resolve_target_size_policy_from_config` ->
  `build_target_size_statistical_aggregate`), and the one P3 common preparation. Only the
  target-size-neutral lower-level records (`source_catalog`, `frame_catalog`, `data4`) are reused,
  and each is re-validated by the owner that consumes it.
- `execute_current_prepare(args)` — performs/resumes/reuses the destructive cutover, then binds the
  reconstructed identities. **It has no code path that selects `N`, advances the reducer, trains,
  materializes a candidate, or ranks anything.**
- `execute_current_select_target_size(args, ...)` — the section 11.2 sequence: load/revalidate P1
  from campaign state, construct the exact P2 experiment, construct the P3 context/screen window,
  **reconcile the existing root before scheduling**, derive the active matrix from the authenticated
  reducer state, execute only surviving `(N, seed)` cells through P3 owners, publish through P3,
  commit the boundary batch, CAS-adopt the exact head, and repeat only while the P2 reducer is
  nonterminal. No P4-local ranking or restart loop exists.
- `TargetSizeRungRequest` / `TargetSizeBoundaryTrainer` / `MaceTargetSizeBoundaryTrainer` — the one
  expensive-work seam. The production trainer launches the same qualified `mdstats-mace-train`
  wrapper the rest of the campaign uses, with the P3 rung plan in
  `TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE`, so critical-precision policy and exact completed-epoch
  continuation stay active.
- `mace_run_configuration(...)` — translates P3's canonical candidate configuration into MACE's
  argument names. Pure renaming/flattening: no value is computed, defaulted, or overridden, and the
  architecture can never shadow an optimizer or data key.

CLI switch in `_campaign_cli_core.py`:

- `command_prepare` routes TRAIN2 campaigns to `execute_current_prepare`; the historical
  (non-TRAIN2) lifecycle keeps its own path.
- `command_select_target_size` routes to `execute_current_select_target_size`, passing the two
  private below-boundary seams (`_external_boundary_trainer`, `_external_inference_evaluator`) that
  bounded harnesses use. `allow_forward_override` on the P3 restart authority is enabled **only**
  when a forward seam was actually supplied, so ordinary production still requires a pinned MACE
  state dict and refuses any reconstruction fallback.
- `command_materialize` now fails closed: the retired per-variant materialization records are never
  reinterpreted, and the post-selection production path belongs to P5.
- `command_train` / `command_evaluate` consult the regime **before** any retired record, so ordinary
  training/evaluation can never become a second target-size screening scheduler regardless of what
  the workspace holds.
- `main()` now presents `TargetSizeCampaignStateError` (and its cutover/adoption subclasses) as
  clean CLI failures instead of tracebacks.

### Evidence executed

`tests/test_mlff_target_size_p4d_runtime_cutover.py` — **12 passed**. Real `build_parser()` argv
parsing, a real campaign workspace and `campaign.toml`, a real `CampaignStore` SQLite file, and the
real P1/P2/P3 owners. Only MACE's numerical work is substituted, through
`_BoundedNumericalHarness`, after real configuration parsing, authority construction,
materialization, provider/checkpoint authentication, publication, reconciliation, and adoption have
executed.

| Gate item | Covering tests |
|---|---|
| real parser + store + `prepare` proving no N selection | `req1_prepare_binds_current_authorities_and_selects_nothing` (asserts bound P1/P2/common identities and that `terminal`, `adopted_execution_head_digest`, and `attempt` are all absent, and that the operator is told `prepare` does not select) |
| one canonical generation | `req1_prepare_is_idempotent_and_keeps_one_generation` |
| retired records quarantined by the real command | `req1_prepare_quarantines_retired_target_size_records` |
| real parser + store + `select-target-size` reaching P1/P2/P3 | `req2_select_target_size_reaches_p1_p2_p3_owners` (the paired-seed matrix `{1,2}` and candidate ladder come from P2; heads/batches/completions exist on disk; the campaign adopted a head; no retired record is present) |
| restart does not rerun completed work | `req2_select_target_size_resumes_without_rerunning_completed_cells` |
| current regime required | `req2_select_target_size_requires_the_current_regime` |
| no retired authority in the current call graph | `req1_prepare_call_graph_reaches_no_retired_target_size_authority` (AST over `command_prepare`/`command_select_target_size`), `req1_current_runtime_owner_imports_no_retired_module` (AST import check over all six P4 modules) |
| `materialize` fails closed | `req3_materialize_fails_closed_without_retired_authority` |
| ordinary train/evaluate cannot schedule the screen | `req4_ordinary_train_and_evaluate_cannot_schedule_the_screen` |
| configuration translation is not a decision | `req5_mace_run_configuration_is_translation_only` |
| version-agnostic naming | `req6_no_version_prefixed_production_names` |

Stage-local affected regression: the four P4 suites plus `test_mlff_campaign_cli`,
`test_mlff_cli_semantic_orchestration`, `test_mlff_stor1_storage_accounting`,
`test_mlff_data9b1_campaign_checkpoint_control`, `test_mlff_campaign_production_gate_anchor`,
`test_mlff_mh1_config1_campaign_defaults`, and the full P3A9 recovery suite —
**203 passed, 1 skipped, 1 failed**; the failure is the pre-existing
`test_materialization_record_path_does_not_confer_external_cleanup_authority`.

### Retired-architecture tests updated or removed (section 18 disposition)

The frozen parent retires the `target_size_study` selector, prepare-time selection, and per-variant
materialization authority, so tests that assert those behaviours encode an obsolete expectation.
Removed from `tests/test_mlff_cli_semantic_orchestration.py`:

- `test_materialize_requires_selected_train2_authority`
- `test_materialize_idempotent_rerun_does_not_reopen_completed_production_receipts`
- `test_materialize_new_selected_matrix_invalidates_execution_receipts`
- `test_prepare_rejects_post_selection_semantic_reuse`
- `test_prepare_routes_legacy_target_size_payload_to_current_reconciliation` (asserted legacy
  payload *migration*, which the parent forbids outright)
- `test_select_target_size_owns_complete_restartable_funnel` (3 parametrizations)
- `test_select_target_size_selected_is_idempotent`
- `test_selected_production_commands_require_current_matrix_preflight` (2 parametrizations)

Their protected concerns are re-covered by the P4-D suite above (no N selection in `prepare`,
`select-target-size` owning the restartable screen and resuming without rerunning, `materialize`
failing closed, and the train/evaluate scheduler guard).

Updated rather than removed:
`tests/test_mlff_campaign_cli.py::test_train_cannot_bypass_target_size_selection_with_legacy_preflight_receipt`
— the protected concern (train cannot bypass target-size selection) still holds; only the expected
message changed, because the current architecture fails closed on the regime before consulting any
retired record.

### Defects found and repaired during the gate

1. Replacing `command_materialize` initially removed the adjacent module-level `_DATA8_VARIANT_RE`
   constant, breaking DATA8 variant validation; restored, and the diff re-audited for any other
   removed top-level definition (none).
2. `command_storage` had no campaign store in scope for the fenced boundary (carried over from
   P4-C); it uses the unfenced read-only boundary, which is correct for STOR1.
3. `command_train` / `command_evaluate` consulted the retired study *before* their scheduler guard,
   so a converted workspace produced a "record missing" message instead of the guard. The guard now
   fires first.
4. `TargetSizeCutoverError` escaped `main()` as a traceback because it is not a `CampaignCliError`;
   the CLI boundary now handles the typed target-size state errors.

### Known scope boundary carried forward

`preflight`, `status`, and `advance` still derive lifecycle hints from the retired
`target_size_study` record. They degrade safely (the optional loader returns `None` once the record
is quarantined) and none of them can authorize a current selected target size, but their reporting
is not yet expressed in terms of the current campaign state. This is recorded as P4-F work
(documentation/structural closure) rather than left implicit.

---

## Pass P4-E — Terminal projection, semantic restart, invalidation

**State: CLOSED** (semantic + functional).

### What was implemented

New owner `mdstats/training_data/campaign_target_size_terminal.py`.

- `derive_terminal_projection(head, definition=...)` — section 5.1. `N` comes from the terminal
  reducer state carried by the adopted immutable head; the exact `T_selected` identity is
  **re-derived** from `definition.training_order.candidate_digest(N)` and compared with what the
  reducer state carries, so a reducer state whose membership the training order does not produce is
  rejected at derivation instead of persisted. A nonterminal head cannot be projected at all.
- `commit_terminal_projection(...)` — CAS-commits the adopted head digest, the reducer digest, and
  the derived projection **in one transition**, because they are one claim.
  `record_terminal_selection` and `record_terminal_scientific_failure` are distinct transition
  kinds, and the lifecycle they publish is derived from the reducer status, not chosen by P4.
- `validate_terminal_projection(...)` — section 5.2 reload gate. It re-resolves the referenced head
  through the real P3 resolver, checks the campaign-bound reducer digest against it, re-derives both
  `N` and the exact `T_selected` identity, and compares them with the persisted projection. Any
  mismatch fails closed; updating only one field cannot make divergent state valid because each
  field is checked against its authenticated source rather than against the others.
- `classify_target_size_invalidation(state, observed)` — section 8. Returns the changed scientific
  authorities and the disposition. A changed authority is never repaired in place: the persisted
  generation is retired and a fresh one is required.
  `ensure_current_target_size_authorities` now uses this classifier, so the reason recorded in
  campaign state names exactly which authority changed.

Runtime wiring in `campaign_target_size_runtime.py`: when the P2 reducer becomes terminal, the
screen commits the terminal projection and then **re-validates it before reporting anything**. A
screen that is merely incomplete stays `screen_active` with no terminal projection, so it remains
operationally resumable.

### Evidence executed

`tests/test_mlff_target_size_p4e_terminal_and_invalidation.py` — **23 passed**. The terminal cases
drive the real production screen (real parser, real `CampaignStore`, real P1/P2/P3 owners) to a
terminal P2 outcome and then assert against re-derivation.

| Gate item | Covering tests |
|---|---|
| terminal success rederivation | `req1_terminal_selection_is_derived_and_revalidated`, `req1_fresh_process_reload_re_derives_the_identical_projection` |
| terminal replay stays terminal | `req1_repeating_select_target_size_stays_terminal` (asserts nothing was retrained) |
| selected-N tamper negative | `req2_mutating_only_selected_n_is_rejected` |
| T-selected tamper negative | `req2_mutating_only_t_selected_identity_is_rejected` |
| adopted head/reducer tamper negative | `req2_mutating_only_the_adopted_head_reference_is_rejected` |
| forged reducer membership | `req2_reducer_state_carrying_a_foreign_membership_is_rejected` |
| nonterminal state cannot be projected | `req2_nonterminal_head_cannot_be_projected` |
| P1 source/canonical, protected relation, hard support, split/order/candidate set, seed, fidelity/metric, training-policy invalidation | `req3_any_changed_scientific_authority_requires_a_fresh_generation` (parametrized over all six identity fields), `req3_target_size_policy_change_does_invalidate` (real config change of `[training].seeds`) |
| fresh generation instead of in-place repair | `req3_changed_identity_advances_the_generation_and_keeps_the_old_result` |
| equal selected `N` alone proves nothing | `req3_equal_selected_n_alone_does_not_prove_equivalence` |
| CV-only / production-only changes are target-size-neutral | `req3_cv_only_and_production_only_settings_are_target_size_neutral` (rebuilds the identity from a config differing only in cross-validation seed, checkpoint strategy, production horizon, and fold count; asserts the identity and the terminal result are untouched) |
| complete-identity requirement | `req3_classification_requires_the_complete_identity` |
| operational interruption stays resumable | `req4_operational_interruption_stays_resumable` (a rung raises mid-screen; the campaign keeps `screen_active` with no terminal projection, and a later invocation completes it) |
| terminal scientific failure is not an interruption | `req4_terminal_scientific_failure_is_not_an_interruption` |
| raw/live/EMA semantics stay with P3 | `req5_runtime_never_reinterprets_checkpoint_state` (AST identifier scan proving no P4 module names an evaluation-state constant or the canonical selector), `req5_resume_goes_through_the_real_p3_owner` (every continuation rung resolves through `resolve_target_size_candidate_for_resume`, which is where malformed EMA/live state is rejected — P3A5/P3A6/P3A7 remain the regression authority for that rejection) |

Stage-local affected regression: all five P4 suites plus `test_mlff_campaign_cli`,
`test_mlff_cli_semantic_orchestration`, `test_mlff_stor1_storage_accounting`, and
`test_mlff_target_size_statistical_authorities` — **212 passed, 1 skipped, 1 failed**; the failure is
the pre-existing `test_materialization_record_path_does_not_confer_external_cleanup_authority`.

### Note recorded during the gate

The bounded fixture screen now runs to a real terminal P2 selection (`N=4` on the 3-candidate
ladder), so the P4-D assertion that the generation is left `screen_active` was widened to accept the
terminal lifecycles. That is the production path completing, not a weakened expectation: the same
test still asserts the execution root, screen window, and adopted head.

An attempt to build a "foreign training order" by reversing `pi_train` was refused by the P2
definition's own validator, which is the correct owner behaviour. The negative is now expressed by
forging the reducer state's membership digest directly, which is the case the derivation must catch.

---

## Pass P4-F — Full STOR integration, docs, structural closure

**State: CLOSED** (semantic + functional).

### What was implemented

**Storage accounting (`storage_accounting.py`)** — `_family_for` now classifies promoted P3
evidence explicitly instead of pooling it into the generic internal bucket. New helper
`_target_size_family` maps the campaign-owned execution root
(`.mdstats/target-size/g<N>/...`) onto the section 10.2 artifact families:

| Path | Family | Retention class |
|---|---|---|
| `heads`, `batches`, `completions`, `progress`, `trajectories`, `continuations`, `planned_rungs`, `screen_window.json`, `current_head.json` | `target_size_execution_graph` | restart_critical |
| `bulk/snapshots`, `snapshots` | `target_size_boundary_snapshots` | restart_critical |
| `bulk/train2` | `target_size_training_runtime` | restart_critical |
| `bulk/materializations`, `materializations` | `target_size_candidate_materializations` | restart_critical |
| `bulk/evaluations`, `evaluation_artifacts`, `roles`, `predictions`, `metrics` | `target_size_evaluation_evidence` | evaluation_capsule |
| `failures` | `target_size_failure_evidence` | protected_diagnostic |

All are `prohibited` for both automatic and manual reclamation: whether any of it can be reclaimed
is decided by the retention fence plus reconciliation (P4-C), never by a storage tier.

**Documentation** — `docs/guides/mlff_campaign_cli_user_guide.md` now states plainly that
`prepare` rebuilds the substrate and **does not select a target size**, that the first `prepare`
performs the one-time destructive cutover with retired records quarantined rather than migrated
(and how to resume an interrupted cutover), that `select-target-size` is the only current screening
entrypoint and the only command that decides `N`, that the selected size and exact selected data are
re-derived rather than stored decisions, that a terminal scientific outcome is a result rather than
an interruption, and that `materialize` is unavailable in this release and fails closed. Parser help
for `prepare`, `select-target-size`, and `materialize` was rewritten to match, along with the
pipeline stage description. `campaign.toml.example` now documents that the `[partition]` keys define
the neutral partition the target-size substrate is built on — so changing one requires a fresh
canonical generation — while cross-validation and production-only settings never invalidate a
target-size result.

### Evidence executed

`tests/test_mlff_target_size_p4f_storage_docs_structure.py` — **18 passed**. Storage claims run
through the real `build_campaign_storage_report`, the real `command_storage`, the real
`_campaign_cleanup` owner, and the real `CampaignOwnershipBoundary`.

| Gate item | Covering tests |
|---|---|
| storage report includes promoted families/bytes | `req1_storage_report_accounts_promoted_target_size_families`, `req1_storage_command_reports_target_size_bytes` |
| safe cleanup preserves the execution root | `req2_safe_cleanup_preserves_the_execution_root` (ages every file 30 days, runs real `_campaign_cleanup` with `dry_run=False`, byte-compares the tree) |
| fresh-process replay after safe cleanup is identical | `req2_fresh_process_replay_after_safe_cleanup_is_identical` (reopens the store, re-derives the identical terminal state, and a fresh `select-target-size` retrains nothing) |
| higher tiers cannot reclaim target-size evidence | `req2_manual_cache_tier_cannot_reclaim_target_size_evidence` (every aged file denied) |
| external/symlink/ambiguous paths remain protected | `req2_external_and_symlink_paths_stay_denied` |
| docs describe the actual lifecycle | `req3_user_guide_states_prepare_does_not_select`, `req3_user_guide_does_not_claim_a_retired_lifecycle`, `req3_parser_help_describes_the_current_commands`, `req3_config_example_documents_partition_identity_coupling` |
| no second algorithmic owner | `req4_no_second_target_size_algorithm_owner` |
| no version-prefixed product names | `req4_no_version_prefixed_production_names` |
| `target_size_study` unreachable from current entrypoints | `req4_target_size_study_is_unreachable_from_current_entrypoints` (transitive call-graph walk from `command_prepare` / `command_select_target_size`) |
| exactly one mutable current authority and one canonical generation | `req4_exactly_one_mutable_current_target_size_authority` (only one class in the whole P4 surface binds regime + generation + lifecycle) |
| `current_head.json` is not campaign authority | `req4_current_head_pointer_is_not_campaign_authority` |
| no domain map / pre-target CV / complement authority | `req4_no_current_domain_or_pre_target_cv_authority` |
| no reverse nested lock/transaction path | `req4_no_reverse_nested_lock_or_transaction_path` |
| every destructive production path carries the fence | `req4_every_destructive_production_path_carries_the_fence` (exactly one `CampaignOwnershipBoundary` construction remains in production, inside the fenced helper) |

The concurrent cleanup/adoption race required by section 10.5 is covered by P4-C
(`test_p4c_cleanup_racing_publication_and_adoption_deletes_nothing_adoptable`, a separate spawned
process running real destructive authorization) and
`test_p4c_production_cleanup_owner_consumes_the_retention_fence`.

Stage-local affected regression: all six P4 suites plus `test_mlff_stor1_storage_accounting`,
`test_mlff_campaign_cli`, `test_mlff_cli_semantic_orchestration`,
`test_mlff_rev3_storage_evaluation_optimizations`, and
`test_mlff_data9b3_campaign_cli_specification` — **214 passed, 1 skipped, 3 failed** (see below).

### Pre-existing failure resolved

`tests/test_mlff_stor1_storage_accounting.py::test_materialization_record_path_does_not_confer_external_cleanup_authority`
— **now passing.** Diagnosis: the test monkeypatched `_current_materialization_roots` on the
`campaign_cli` *facade*, while the cleanup owner resolves that helper from `_campaign_cli_core`, so
the substitution never took effect and the assertion could not be reached. Production behaviour was
correct throughout (verified directly); the test was ineffective. It now patches the core module and
genuinely exercises the ownership check.

### Pre-existing failures NOT resolved (out of P4 scope, reported truthfully)

`tests/test_mlff_data9b3_campaign_cli_specification.py` — 3 failures, all present before any P4
edit and all caused by documentation-authority drift unrelated to the target-size surface:

- `test_data9b3_version_and_user_surface` pins `mdstats.__version__ == "0.20.140a0"`; the package is
  at `0.20.242a0`.
- `test_data9b3_architecture_and_stage_plan_integration` asserts an architecture-manual sentence
  about DATA9B3 "implemented in 0.20.58a0"; the manual is at architecture revision 106 and no longer
  contains it.
- `test_data9b3_dependency_graph_contract` asserts dependency-graph `schema_version == 26`; the
  graph file declares `2`.

None of these concerns target-size behaviour, and none can be made to pass without either re-pinning
a stale release constant or rewriting architecture documentation that P4 does not own. Re-pinning
them would manufacture acceptance rather than establish it, so they are left failing and carried
into the P4-G report as known unresolved documentation drift belonging to a documentation
reconciliation task.

### Carryover resolved from P4-D

The P4-D note about `preflight` / `status` / `advance` still reading the retired study record stands
as a **reporting** limitation only: the structural test
`req4_target_size_study_is_unreachable_from_current_entrypoints` proves the retired loader is
unreachable from the two current target-size entrypoints, `_load_train2_study_optional` returns
`None` once the record is quarantined so those commands degrade safely, and no old-runtime loader
can authorize a current selected target size (the selected size is only ever re-derived through
`validate_terminal_projection`). Expressing their reporting in terms of the current campaign state
is left to the post-selection package that reworks those commands.
