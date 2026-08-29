# P4 implementation progress and evidence log

Working record for `P4_ATOMIC_RUNTIME_PERSISTENCE_CUTOVER.md` **package revision 8**.
Authority: frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` plus the revision-8 overlay in the P4 package.

The exact revision-7 candidate/evidence reviewed at `87ed7889f7e12a0842000477f97dd1eef9fea9ac` are preserved in:

- `P4_REVISION7_IMPLEMENTED_BASELINE.md`;
- `P4_REVISION7_IMPLEMENTATION_PROGRESS.md`.

Revision-4 through revision-6 baselines/evidence remain preserved unchanged.

## Revision-8 status summary

| Pass | Scope | State |
|---|---|---|
| Entry/P3 | accepted P3 revision 7 through P3A9 | **CLOSED / PRESERVED** |
| P4-A | CampaignStore state, canonical generation, CAS, transition identity | **CLOSED / PRESERVED** |
| P4-B | destructive regime cutover | **CLOSED / PRESERVED** |
| P4-C2 | single canonical execution-root construction owner | **CLOSED / PRESERVED** |
| P4-C3 | first-publication retention through actual production STOR ownership/removal | **CLOSED / ACCEPTED AT REV7** |
| P4-D | production switch architecture | **CLOSED / AFFECTED REGRESSION REQUIRED** |
| P4-E2 | canonical current-terminal loader/full validation chain | **CLOSED / PRESERVED** |
| P4-E3 | CampaignStore-backed current view/report facade | **CLOSED / PRESERVED SUBJECT TO E4 API SEAL** |
| P4-E4 | exported/public terminal snapshot renderer/writer sealing | **OPEN** |
| P4-F | result-view/storage/structural integration | **CLOSED / AFFECTED REGRESSION REQUIRED** |
| P4-G4 | final assembled affected-surface closure | **OPEN / BLOCKED ON E4** |

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

- [ ] Preserve the canonical `load_validated_target_size_terminal_result(...)` loader unchanged except for necessary local refactoring.
- [ ] Preserve the CampaignStore-backed current exposure facade.
- [ ] Inspect every exported/public result-view API and any package-level re-export.
- [ ] No exported function lacking authoritative `cfg/paths/store` context can successfully process terminal state into a current terminal payload or file.
- [ ] `build_target_size_result_view(...)` is either private/internal for terminal use or public but strictly nonterminal-only.
- [ ] `write_target_size_result_view(...)` is either private/internal for terminal use or public but strictly nonterminal-only.
- [ ] No exported arbitrary-path writer can accept `revision + validated_result` and write terminal state.
- [ ] Any terminal-capable pure formatter used by production is private and is called only after same-invocation CampaignStore-backed current validation.
- [ ] Nonterminal progress view behavior remains working.
- [ ] P5-facing current-result seam continues to use the canonical current exposure owner, not result-file or retained-snapshot authority.
- [ ] No second terminal loader/currentness cache/generation registry is introduced.

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

- [ ] Directly exercise the **legacy/generic writer escape surface** with `g1_revision + g1_validated` and the canonical `target-size-state.json` destination.
- [ ] If the writer remains public, it rejects terminal use before file publication.
- [ ] If it is made private/removed from public API, structural acceptance proves no exported equivalent remains.
- [ ] Canonical result file is absent or byte-for-byte unchanged after the stale attempt.
- [ ] Directly exercise the **legacy/generic builder escape surface** with `g1_revision + g1_validated`.
- [ ] If the builder remains public, it rejects terminal use; if private, it is absent from the supported export surface.
- [ ] Do not count only `g2_revision + g1_validated` mismatch coverage; the exact historical self-consistent pair is mandatory.
- [ ] Current facade still rejects stale `expected_revision=g1_revision` after g2 exists.
- [ ] Current facade still accepts unchanged current terminal and performs zero trainer/evaluator work.
- [ ] Missing/corrupt immutable adopted evidence, tampered CampaignStore, scientific invalidation, neutral config, terminal failure, and stale/missing rebuildable `current_head.json` cases remain passing.

## Structural/export acceptance

- [ ] Inspect `campaign_target_size_view.__all__` and any package-level re-export surface.
- [ ] Prove no exported terminal snapshot-only renderer/writer remains.
- [ ] Prove no exported arbitrary-path terminal writer accepts historical snapshot objects without CampaignStore.
- [ ] Search production callers of private snapshot formatters; terminal production calls must be downstream of current exposure validation.
- [ ] Exactly one canonical current-terminal loader remains.
- [ ] Result file remains derived/non-authoritative and is not read to determine current N/T.
- [ ] No V7/version-prefixed production naming introduced.

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

- [ ] Re-derive final affected surface from assembled candidate.
- [ ] Run fresh final affected regression. Default bounded command should include the same P4-A through P4-G plus P3A9 suites used for revision 7, because they completed in bounded time and collectively exercise the assembled ownership path.
- [ ] Run bounded integration: `prepare -> select terminal -> fresh current reload -> production STOR cleanup -> second current reload`.
- [ ] Prove second reload performs zero retraining and returns identical N/T/reason.
- [ ] Run missing/corrupt immutable-head and scientific-invalidation negatives.
- [ ] Include exact historical `g1_revision + g1_validated` attempt against every remaining exported generic result-view API after g2 exists.
- [ ] Structural closure: one root owner, one current-terminal loader/currentness core, no exported terminal snapshot bypass, no duplicate generation/current-state authority, no version-prefixed production naming.
- [ ] Only then set P4 `status: implemented` and reconcile README to formal P4 closure / P5 eligibility.

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

Long GPU/real-production qualification remains deferred to final release.