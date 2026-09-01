# P4 implementation progress and evidence log

Working record for `P4_ATOMIC_RUNTIME_PERSISTENCE_CUTOVER.md` **package revision 8**.
Authority: frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` plus the revision-8 overlay in the P4 package.

The exact revision-7 candidate/evidence reviewed at `87ed7889f7e12a0842000477f97dd1eef9fea9ac` are preserved in:

- `P4_REVISION7_IMPLEMENTED_BASELINE.md`;
- `P4_REVISION7_IMPLEMENTATION_PROGRESS.md`.

Revision-4 through revision-6 baselines/evidence remain preserved unchanged.

### Revision-8 status summary

| Pass | Scope | State |
|---|---|---|
| Entry/P3 | accepted P3 revision 7 through P3A9 | **CLOSED / PRESERVED** |
| P4-A | CampaignStore state, canonical generation, CAS, transition identity | **CLOSED / PRESERVED** |
| P4-B | destructive regime cutover | **CLOSED / PRESERVED** |
| P4-C2 | single canonical execution-root construction owner | **CLOSED / PRESERVED** |
| P4-C3 | first-publication retention through actual production STOR ownership/removal | **CLOSED / ACCEPTED AT REV7** |
| P4-D | production switch architecture | **CLOSED** |
| P4-E2 | canonical current-terminal loader/full validation chain | **CLOSED / PRESERVED** |
| P4-E3 | CampaignStore-backed current view/report facade | **CLOSED / PRESERVED** |
| P4-E4 | exported/public terminal snapshot renderer/writer sealing | **CLOSED** |
| P4-F | result-view/storage/structural integration | **CLOSED** |
| P4-G4 | final assembled affected-surface closure | **CLOSED** |

## Independent-review blocker routed to revision 8

Revision 7 correctly added current terminal entrypoints that re-enter the CampaignStore-backed canonical loader. The remaining problem is a parallel public escape surface in `campaign_target_size_view.py`: exported `build_target_size_result_view(...)` and `write_target_size_result_view(...)` still accept a raw/historical `TargetSizeCampaignRevision` plus matching `ValidatedTargetSizeTerminalResult` and can render/write terminal state without consulting CampaignStore.

Exact counterexample:

```text
terminal g1
 -> legitimate g1_revision + g1_validated
 -> target-size scientific change
 -> real prepare -> g2 current
 -> write_target_size_result_view(canonical path, g1_revision,
                                  validated_result=g1_validated)
 -> stale g1 can still be published
```

The retained g1 pair is self-consistent; matching snapshot objects to each other does not prove currentness.

## Preserved evidence

The following revision-7 claims remain accepted unless revision-8 implementation directly modifies their owners:

- P1-P3 scientific/reducer/checkpoint/provider/replay semantics;
- P4-A CampaignStore/CAS/transition identity;
- P4-B destructive cutover;
- single canonical execution-root owner;
- **P4-C3 production STOR first-publication race and reclaimable control deletion**;
- canonical CampaignStore-first terminal loader and full P1/P2/common/P3/head/reducer/projection validation chain;
- production current terminal completion/reload routing through `write_current_target_size_result_view(...)` and `report_current_target_size_terminal_state(...)`;
- target-size decision/reducer semantics and nonterminal screen science.

Revision-7 recorded functional evidence remains useful for unaffected paths:

- P4-C3 suite: `25 passed`;
- P4-E3 suite: `42 passed`;
- assembled P4/P3A9 suite: `168 passed`.

The revision-7 **semantic claim** of “no public/current stale snapshot bypass” and therefore formal G3 closure are invalidated by independent source review. The 168-pass result cannot substitute for the missing E4 obligation.

## P4-E4 mandatory implementation checklist

- [x] Preserve the canonical `load_validated_target_size_terminal_result(...)` loader unchanged except for necessary local refactoring.
- [x] Preserve the CampaignStore-backed current exposure facade.
- [x] Inspect every exported/public result-view API and any package-level re-export.
- [x] No exported function lacking authoritative `cfg/paths/store` context can successfully process terminal state into a current terminal payload or file.
- [x] `build_target_size_result_view(...)` is either private/internal for terminal use or public but strictly nonterminal-only.
- [x] `write_target_size_result_view(...)` is either private/internal for terminal use or public but strictly nonterminal-only.
- [x] No exported arbitrary-path writer can accept `revision + validated_result` and write terminal state.
- [x] Any terminal-capable pure formatter used by production is private and is called only after same-invocation CampaignStore-backed current validation.
- [x] Nonterminal progress view behavior remains working.
- [x] P5-facing current-result seam continues to use the canonical current exposure owner, not result-file or retained-snapshot authority.
- [x] No second terminal loader/currentness cache/generation registry is introduced.

## Mandatory exact stale-pair regression

Construct through real owners:

```text
terminal g1
 -> expose/load legitimate g1_validated while g1 is current
 -> retain g1_revision + g1_validated
 -> preserve immutable g1 evidence
 -> change target-size scientific identity
 -> real prepare -> nonterminal g2 current
```

Then:

- [x] Directly exercise the **legacy/generic writer escape surface** with `g1_revision + g1_validated` and the canonical `target-size-state.json` destination.
- [x] If the writer remains public, it rejects terminal use before file publication.
- [x] If it is made private/removed from public API, structural acceptance proves no exported equivalent remains.
- [x] Canonical result file is absent or byte-for-byte unchanged after the stale attempt.
- [x] Directly exercise the **legacy/generic builder escape surface** with `g1_revision + g1_validated`.
- [x] If the builder remains public, it rejects terminal use; if private, it is absent from the supported export surface.
- [x] Do not count only `g2_revision + g1_validated` mismatch coverage; the exact historical self-consistent pair is mandatory.
- [x] Current facade still rejects stale `expected_revision=g1_revision` after g2 exists.
- [x] Current facade still accepts unchanged current terminal and performs zero trainer/evaluator work.
- [x] Missing/corrupt immutable adopted evidence, tampered CampaignStore, scientific invalidation, neutral config, terminal failure, and stale/missing rebuildable `current_head.json` cases remain passing.

## Structural/export acceptance

- [x] Inspect `campaign_target_size_view.__all__` and any package-level re-export surface.
- [x] Prove no exported terminal snapshot-only renderer/writer remains.
- [x] Prove no exported arbitrary-path terminal writer accepts historical snapshot objects without CampaignStore.
- [x] Search production callers of private snapshot formatters; terminal production calls must be downstream of current exposure validation.
- [x] Exactly one canonical current-terminal loader remains.
- [x] Result file remains derived/non-authoritative and is not read to determine current N/T.
- [x] No V7/version-prefixed production naming introduced.

## E4 stage-local regression required after final executable edit

At minimum:

```bash
conda run -n mace pytest -n 16 \
  tests/test_mlff_target_size_p4e_terminal_and_invalidation.py \
  tests/test_mlff_target_size_p4d_runtime_cutover.py \
  tests/test_mlff_target_size_p4f_storage_docs_structure.py \
  tests/test_mlff_target_size_p3a9_head_pointer_reconciliation.py
```

Add any specific public-export/P5-seam test file if implementation creates or changes such a surface.

P4-C3 does not need a separate stage-local rerun unless E4 touches STOR/root/C3 code.

## P4-G4 assembled closure checklist

After E4 closes:

- [x] Re-derive final affected surface from assembled candidate.
- [x] Run fresh final affected regression. Default bounded command should include the same P4-A through P4-G plus P3A9 suites used for revision 7, because they completed in bounded time and collectively exercise the assembled ownership path.
- [x] Run bounded integration: `prepare -> select terminal -> fresh current reload -> production STOR cleanup -> second current reload`.
- [x] Prove second reload performs zero retraining and returns identical N/T/reason.
- [x] Run missing/corrupt immutable-head and scientific-invalidation negatives.
- [x] Include exact historical `g1_revision + g1_validated` attempt against every remaining exported generic result-view API after g2 exists.
- [x] Structural closure: one root owner, one current-terminal loader/currentness core, no exported terminal snapshot bypass, no duplicate generation/current-state authority, no version-prefixed production naming.
- [x] Only then set P4 `status: implemented` and reconcile README to formal P4 closure / P5 eligibility.

## Closure discipline

P4 remains `status: active` and P5 remains blocked while P4-E4 or P4-G4 is open.

Implementation must not obtain closure by:

- changing only the new current facade while leaving exported legacy/generic terminal snapshot APIs intact;
- documenting snapshot APIs as “non-authoritative” while they remain capable of writing terminal state;
- renaming the bypass but keeping it exported;
- adding a caller-supplied boolean/trust token instead of consulting CampaignStore;
- testing only a mismatched `g2_revision + g1_validated` pair;
- weakening result-view schema or terminal validation;
- reopening C3, P1-P3 science, or persistence architecture without evidence.

Full long GPU/real-production qualification remains deferred to final release.

## Revision-8 execution and reclosure evidence

### P4-E4: Public terminal snapshot API sealing
- **Implementation:**
  - In `mdstats/training_data/campaign_target_size_view.py`:
    - Moved terminal snapshot formatting and file writing behind strictly private helpers: `_build_terminal_target_size_result_view` and `_write_terminal_target_size_result_view`.
    - Made generic public `build_target_size_result_view(revision, ...)` and `write_target_size_result_view(path, revision, ...)` unconditionally reject any terminal revision with `TargetSizeTerminalProjectionError`.
    - Maintained `expose_current_target_size_terminal_result(cfg, paths, store, ...)` and `write_current_target_size_result_view(cfg, paths, store, ...)` as the sole authoritative current terminal exposure entrypoints.
- **Validation Tests:**
  - `test_p4e_mandatory_legacy_generic_terminal_writer_cannot_publish_g1`: Verified that attempting to write `g1_revision + g1_validated` via `write_target_size_result_view` after `prepare` creates `g2` is rejected before file publication, leaving the result file uncreated or unmodified.
  - `test_p4e_mandatory_legacy_generic_terminal_builder_cannot_supply_g1_payload`: Verified that attempting to build a terminal payload from `g1_revision + g1_validated` via `build_target_size_result_view` after `prepare` creates `g2` raises `TargetSizeTerminalProjectionError`.
  - `test_p4e_structural_public_api_surface_sealing`: Verified that `__all__` exports no private terminal snapshot helpers and that no exported function lacking CampaignStore context can process terminal revisions.
- **Command & Output:**
  ```bash
  conda run -n mace pytest -n 16 tests/test_mlff_target_size_p4e_terminal_and_invalidation.py
  # Result: 44 passed in 58.90s
  ```

### P4-G4: Final assembled affected-surface closure and regression
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
  # Result: 170 passed in 87.83s (0:01:27)
  ```
- **Structural Integrity:**
  - Single canonical execution-root owner (`campaign_target_size_paths.py`).
  - Single canonical current-terminal loader (`campaign_target_size_terminal.py`).
  - Single current-terminal exposure boundary (`campaign_target_size_view.py`).
  - Zero public snapshot-only terminal escape hatches.