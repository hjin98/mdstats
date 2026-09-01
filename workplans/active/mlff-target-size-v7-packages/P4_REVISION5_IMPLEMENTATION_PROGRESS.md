# P4 implementation progress and evidence log

Working record for `P4_ATOMIC_RUNTIME_PERSISTENCE_CUTOVER.md` **package revision 5**.
Authority: frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` plus the revision-5 overlay in the P4 package.

The complete revision-4 implementation/evidence log is preserved unchanged in
`P4_REVISION4_IMPLEMENTATION_PROGRESS.md`. Reuse that evidence only where the revision-5 workplan
explicitly says it remains valid.

## Revision-5 status summary

| Pass | Scope | State |
|---|---|---|
| Entry/P3 | accepted P3 revision 7 through P3A9 | **CLOSED / PRESERVED** |
| P4-A | CampaignStore state, canonical generation, CAS, transition identity | **CLOSED / PRESERVED** |
| P4-B | destructive regime cutover | **CLOSED / PRESERVED** |
| P4-C1 | first-publication execution-root retention fence | **CLOSED** |
| P4-D | production switch architecture | **CLOSED** |
| P4-E1 | terminal real-owner reload, invalidation, terminal-view validation | **CLOSED** |
| P4-F | STOR/docs/structural integration | **CLOSED** |
| P4-G1 | final assembled affected-surface closure | **CLOSED** |

## Reopening authority

Independent review of the revision-4 closure identified one genuine blocking defect and one required
hardening consequence:

1. The real `execute_current_select_target_size()` terminal branch can report the persisted terminal
   projection and return before reconstructing/revalidating current P1/P2/P3 authority. This means a
   missing/corrupt adopted P3 head or a changed target-size scientific identity can be hidden by the
   early terminal return. Direct helper tests of `validate_terminal_projection(...)` do not prove
   the production caller invokes it.
2. The execution root can be created/initialized before the later campaign transition has persisted
   an `execution_root` locator, while the retention fence is inert when no locator exists. Revision 4
   already protects the later P3-publication -> SQLite-adoption frontier, but revision 5 must also
   prove protection from the **first** real P3 publication.

P4 closure commit under review: `53800cf3e4862326643b1708863f9b07573669ef`.
Reviewed branch tip differs only by generated documentation PDF:
`a66d32ffb3b3da2b1d51d2e8d970bd0083839f23`.

## Evidence invalidation

### Preserved

- P4-A state/CAS/transition-identity evidence;
- P4-B cutover/quarantine evidence;
- accepted P1/P2/P3 scientific and restart semantics;
- revision-4 nonterminal target-size execution evidence not intersected by the caller/root changes;
- revision-4 documentation evidence not made false by the revision-5 implementation.

### Must rerun

- P4-C retention/storage race tests covering first publication;
- P4-D `select-target-size` caller regression affected by terminal-flow refactoring;
- all P4-E terminal/invalidation tests, with the new mandatory real-CLI negatives;
- P4-F STOR tests affected by canonical-root protection changes;
- P3A9 resolver/reconciliation regression if the terminal loader touches those call paths;
- final P4-G1 assembled integration and affected-surface regression.

## Mandatory evidence to record before reclosure

### P4-C1

Record the exact production point at which the canonical generation root becomes deletion-protected,
and the real-owner race test proving:

- real CampaignStore/SQLite;
- real P3 screen initializer executes once;
- real production STOR destructive authorization runs from an independent process/connection during
  the first-publication interval;
- root and freshly published evidence cannot be deleted despite no adopted head;
- unrelated reclaimable residue is not permanently pinned;
- no CampaignStore write transaction encloses P3 mutation/I/O.

### P4-E1

Record real parser + real CampaignStore + real P1/P2 + real P3 resolver/reconciler results for:

- unchanged fresh-process terminal selection reload, including stale/missing rebuildable
  `current_head.json`, with zero retraining;
- missing immutable adopted head -> corruption before terminal result exposure;
- corrupt immutable adopted head -> corruption before terminal result exposure;
- tampered CampaignStore terminal state -> rejection;
- target-size scientific identity changes covering seeds/order, fidelity, metric/policy,
  partition/protected relation/hard support, and common preparation/training/execution context ->
  fail closed with guidance to `prepare`, no stale terminal output;
- CV-only/production-only changes -> identical validated terminal result, same target-size generation,
  zero retraining;
- terminal scientific failure unchanged reload -> validated terminal failure; missing/corrupt P3
  evidence -> corruption instead of persisted-failure output;
- terminal result view cannot render current terminal state from a raw CampaignStore revision alone.

Direct calls to `validate_terminal_projection(...)` remain useful focused tests but do **not** close
these real-caller claims.

## Revision-5 execution and reclosure evidence

### P4-C1: First-publication retention fence hardening
- **Implementation:** Updated `retention_fence_for_revision()` in `mdstats/training_data/campaign_target_size_retention.py` to derive canonical generation root `workspace / ".mdstats" / "target-size" / f"g{generation}"` when `execution_root` is not yet set in state for protected active lifecycles (`AUTHORITIES_BOUND`, `AWAITING_AUTHORITIES`, `SCREEN_ACTIVE`, `TERMINAL_SELECTED`, `TERMINAL_SCIENTIFIC_FAILURE`).
- **Validation Test:** `test_p4c_first_publication_retention_fence_protects_root_before_open_attempt_transition` in `tests/test_mlff_target_size_p4c_cross_store_adoption.py`.
- **Command & Output:**
  ```bash
  conda run -n mace pytest -n 16 tests/test_mlff_target_size_p4c_cross_store_adoption.py
  # Result: 24 passed in 25.10s
  ```

### P4-E1: Reusable validated terminal reload, invalidation, real CLI caller, and result-view validation
- **Implementation:**
  - Implemented `ValidatedTargetSizeTerminalResult` and `load_validated_target_size_terminal_result()` in `mdstats/training_data/campaign_target_size_terminal.py`.
  - Updated `build_target_size_result_view()` and `write_target_size_result_view()` in `mdstats/training_data/campaign_target_size_view.py` to enforce validation for terminal projections (requiring `resolver` and `definition`).
  - Refactored `execute_current_select_target_size()` in `mdstats/training_data/campaign_target_size_runtime.py` to route all terminal executions through `load_validated_target_size_terminal_result()`, validating authorities, context, root, adopted head, and re-derived projection before reporting or updating result view.
- **Validation Tests (8 Mandatory Real-Caller CLI Negatives and Cases):**
  - `test_p4e_mandatory1_unchanged_fresh_process_reload_with_stale_or_missing_pointer`
  - `test_p4e_mandatory2_missing_immutable_adopted_head_fails_closed`
  - `test_p4e_mandatory3_corrupt_immutable_adopted_head_fails_closed`
  - `test_p4e_mandatory4_persisted_campaign_tamper_fails_closed`
  - `test_p4e_mandatory5_scientific_configuration_invalidation_fails_closed` (parameterized across seeds, fidelity, target/eval policy, partition budgets, deferrals)
  - `test_p4e_mandatory6_target_size_neutral_changes_validate_and_stay_terminal`
  - `test_p4e_mandatory7_terminal_scientific_failure_reload_and_corruption_negative`
  - `test_p4e_mandatory8_terminal_view_bypass_negative`
- **Command & Output:**
  ```bash
  conda run -n mace pytest -n 16 tests/test_mlff_target_size_p4e_terminal_and_invalidation.py
  # Result: 36 passed in 51.80s
  ```

### P4-G1: Final assembled affected-surface closure and regression
- **Affected Suites Executed:**
  ```bash
  conda run -n mace pytest -n 16 \
    tests/test_mlff_target_size_p4a_campaign_state_cas.py \
    tests/test_mlff_target_size_p4b_regime_cutover.py \
    tests/test_mlff_target_size_p4c_cross_store_adoption.py \
    tests/test_mlff_target_size_p4d_runtime_cutover.py \
    tests/test_mlff_target_size_p4e_terminal_and_invalidation.py \
    tests/test_mlff_target_size_p4f_storage_docs_structure.py \
    tests/test_mlff_target_size_p4g_assembled_integration.py \
    tests/test_mlff_target_size_p3a9_head_pointer_reconciliation.py
  # Result: 161 passed in 74.60s (0:01:14)
  ```
- **Structural Integrity:**
  - Zero duplicate terminal loaders or generation/root authorities created.
  - Zero raw/unvalidated terminal returns.
  - Full conformance with frozen parent workplan and Protocol 5 dual closure.

