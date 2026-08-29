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
| P4-D | Atomic `prepare` / `select-target-size` production switch | in progress |
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
