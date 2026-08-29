---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P4
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 4
status: active
package_revision: 8
amended_date: 2026-08-29
reopened_from_revision7_candidate: 87ed7889f7e12a0842000477f97dd1eef9fea9ac
revision7_baseline: P4_REVISION7_IMPLEMENTED_BASELINE.md
revision7_evidence: P4_REVISION7_IMPLEMENTATION_PROGRESS.md
revision6_baseline: P4_REVISION6_IMPLEMENTED_BASELINE.md
revision6_evidence: P4_REVISION6_IMPLEMENTATION_PROGRESS.md
revision5_baseline: P4_REVISION5_IMPLEMENTED_BASELINE.md
revision5_evidence: P4_REVISION5_IMPLEMENTATION_PROGRESS.md
revision4_baseline: P4_REVISION4_IMPLEMENTED_BASELINE.md
revision4_evidence: P4_REVISION4_IMPLEMENTATION_PROGRESS.md
entry_p3_closure_commit: 9d195807cff0bb8042f447ac33ceb0586ed708ac
compatibility_policy: destructive-generation-reset
implementation_closure: P4 revision 8 reopened after independent review; P4-C3 is accepted/preserved, P4-E4 public terminal snapshot-API sealing is open, and P4-G4 is invalidated until E4 closes and fresh assembled affected regression passes
reconciliation_reason: Revision 7 correctly closed the production-STOR first-publication owner path and introduced CampaignStore-backed current terminal view/report entrypoints. Independent review found one remaining public API escape hatch: exported build_target_size_result_view(...) and write_target_size_result_view(...) still accept a self-consistent historical TargetSizeCampaignRevision plus ValidatedTargetSizeTerminalResult and can render/write that stale terminal snapshot after prepare advances CampaignStore to a newer generation. Revision 8 closes only that public terminal snapshot exposure surface. No target-size science, P3 execution/reducer/replay, canonical root ownership, CampaignStore schema, terminal-loader validation chain, STOR behavior, or P5 scientific semantics are reopened.
---

# P4 revision 8 — public terminal snapshot API sealing and final reclosure

## 0. Authority, preserved state, and scope

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the sole scientific and architectural verdict. Cumulative P3 revision 7 through P3A9 remains accepted at `9d195807cff0bb8042f447ac33ceb0586ed708ac` and is not reopened.

`P4_REVISION7_IMPLEMENTED_BASELINE.md` preserves the exact revision-7 candidate reviewed at `87ed7889f7e12a0842000477f97dd1eef9fea9ac`; `P4_REVISION7_IMPLEMENTATION_PROGRESS.md` preserves its evidence record. Revision-4 through revision-6 baselines/evidence remain preserved adjacent.

Revision 8 is a narrow implementation repair. It reopens only:

1. **P4-E4 — seal the public/exported terminal result-view API so historical snapshots cannot be exposed as current authority**;
2. **P4-F affected structural/result-view integration** only as required by E4;
3. **P4-G4 — fresh assembled reclosure after E4**.

The following revision-7 work is **accepted and preserved** unless the E4 implementation directly changes it:

- P4-A CampaignStore state/CAS/transition identity;
- P4-B destructive regime cutover;
- P4-C2 single canonical execution-root owner;
- **P4-C3 production-STOR first-publication race and control-artifact deletion acceptance**;
- P4-D production `prepare` / `select-target-size` cutover architecture;
- P4-E2 canonical `load_validated_target_size_terminal_result(...)` CampaignStore-first validation chain;
- P4-E3 current exposure owners introduced in revision 7: `expose_current_target_size_terminal_result(...)`, `write_current_target_size_result_view(...)`, and `report_current_target_size_terminal_state(...)`, subject only to caller/API sealing required below;
- P1-P3 science, TRAIN2/EVAL2, reducer, checkpoint, replay, provider, seed, and immutable-evidence semantics;
- canonical root layout and STOR retention behavior.

P5 remains blocked until revision 8 receives semantic/conformance and functional closure. The workplan remains bound to Protocol 5.8.0.

---

## 1. Independent-review blocker being repaired

Revision 7 correctly routes production terminal completion/reload through CampaignStore-backed current exposure entrypoints. However, `campaign_target_size_view.py` still exports the generic snapshot functions:

```text
build_target_size_result_view(revision, validated_result=..., resolver=...)
write_target_size_result_view(path, revision, validated_result=..., resolver=...)
```

A `ValidatedTargetSizeTerminalResult` proves that its revision was current **when validation ran**. It does not prove that revision remains current later.

The exact remaining failure is:

```text
terminal g1
  -> canonical loader returns legitimate g1_validated
  -> retain g1_revision + g1_validated
  -> change target-size scientific identity
  -> real prepare advances CampaignStore to nonterminal g2
  -> exported write_target_size_result_view(
         canonical_result_path,
         g1_revision,
         validated_result=g1_validated,
     )
  -> stale g1 terminal payload is written without consulting CampaignStore
```

`g1_revision` and `g1_validated` are internally self-consistent, so matching them to each other is insufficient. This is a **public current-authority escape hatch**, not a defect in the canonical loader or revision-7 current exposure facade.

---

## 2. Frozen revision-8 end state

### 2.1 Public API authority rule

There must be no exported/public function that can render, write, report, or return a terminal target-size result as current authority using only snapshot objects such as:

- `TargetSizeCampaignRevision`;
- `ValidatedTargetSizeTerminalResult`;
- `TargetSizeTerminalProjection`;
- a P3 resolver/definition;
- any combination of those without authoritative `cfg + paths + CampaignStore` currentness validation in the same invocation.

For terminal state, the public/current authority path is:

```text
public current terminal consumer
  -> cfg + paths + CampaignStore
  -> expose_current_target_size_terminal_result(...)
       -> load_validated_target_size_terminal_result(...)
            -> reload actual current CampaignStore revision
            -> full existing P1/P2/common/P3/head/reducer/projection validation
  -> private/pure snapshot formatter
  -> current file publication / stdout / downstream return
```

`ValidatedTargetSizeTerminalResult` remains a snapshot/transport object **inside** that current exposure call. It is not itself a public currentness token.

### 2.2 Required treatment of generic view helpers

The implementer must close the exported snapshot bypass by one of these engineering-equivalent realizations, with the first preferred for clarity:

**Preferred realization — private terminal formatter:**

1. Move terminal-capable pure formatting/writing behind private/internal helpers, e.g. `_build_target_size_snapshot_view(...)` and, if needed, `_write_target_size_snapshot_view(...)`.
2. Remove terminal-capable snapshot helpers from `__all__` and from the supported public/current API surface.
3. `write_current_target_size_result_view(...)` may call the private formatter only **after** it obtains a freshly current `ValidatedTargetSizeTerminalResult` from the canonical exposure owner.
4. Nonterminal progress rendering may remain public because it carries no terminal scientific authority.

**Allowed compatibility realization — public generic names become nonterminal-only:**

If repository compatibility requires keeping `build_target_size_result_view(...)` and/or `write_target_size_result_view(...)` public, they must reject **every terminal revision unconditionally**, even if a matching `ValidatedTargetSizeTerminalResult`, resolver, or definition is supplied. Terminal rendering/writing then exists only behind the CampaignStore-backed current API.

The following is **not sufficient**:

- leaving exported `build_target_size_result_view(...)` / `write_target_size_result_view(...)` terminal-capable and merely documenting them as “snapshot” or “non-authoritative”;
- requiring only that `validated_result.revision == revision`;
- renaming the old function while keeping it exported and terminal-capable;
- adding another boolean such as `current=True` / `trusted=True` / `historical=True` that bypasses CampaignStore;
- trusting dataclass type identity, generation number, result-file contents, or P3 evidence alone as proof of currentness.

### 2.3 Historical/debug rendering

If terminal historical rendering is genuinely required for tests/debugging, it may exist only as an explicitly non-current internal/private helper. It must not be the supported current-result API and must not provide an exported arbitrary-path writer capable of overwriting the canonical current result file.

No new persistence schema, freshness cache, generation registry, compatibility database, or second terminal loader is permitted for this repair.

---

## 3. Stage P4-E4 — public terminal snapshot API sealing

### 3.1 Implementation obligations

1. Preserve `load_validated_target_size_terminal_result(...)` as the single canonical current-terminal loader.
2. Preserve `expose_current_target_size_terminal_result(cfg, paths, store, ...)` as the current-result exposure owner, or a semantically equivalent single owner if locally refactored.
3. Preserve `write_current_target_size_result_view(...)` and `report_current_target_size_terminal_state(...)` as CampaignStore-backed current consumers.
4. Inspect **all exported/public functions** in `campaign_target_size_view.py` and affected re-export modules. Any function that lacks authoritative CampaignStore context must not accept/render/write terminal scientific state as a current result.
5. Seal `build_target_size_result_view(...)` and `write_target_size_result_view(...)` specifically:
   - preferred: make the terminal-capable implementation private and remove these terminal-capable helpers from `__all__`; or
   - if their public names must remain, make them nonterminal-only and reject terminal revisions before creating/writing payloads.
6. If a private terminal formatter remains, ensure production current terminal callers reach it only downstream of `expose_current_target_size_terminal_result(...)`/canonical loader in the same invocation.
7. Keep nonterminal diagnostic/progress view behavior working. Nonterminal view files remain derived and non-authoritative.
8. Do not alter terminal scientific projection contents, selection N/T, reducer semantics, result schema fields, P3 evidence semantics, CampaignStore transitions, or current root/STOR behavior merely to seal this API.
9. Search for production callers of the generic snapshot helpers and migrate any terminal-capable caller to the current exposure owner. Tests may invoke private snapshot helpers only for pure-formatting unit coverage; such tests cannot establish currentness.
10. Keep the P5-facing seam pointed at the CampaignStore-backed current exposure owner; P5 must never consume the result-view file or a retained validated snapshot as current authority.

### 3.2 Exact mandatory bypass regression

Construct the historical pair through the real authority path:

```text
real terminal generation g1
  -> load current g1 through canonical current exposure
  -> retain legitimate g1_revision and g1_validated
  -> keep g1 immutable P3 evidence intact
  -> change target-size scientific identity
  -> real prepare
  -> CampaignStore advances/binds nonterminal g2
```

Then test the **old escape surface itself**, not only the new facade.

#### A. Legacy/generic terminal writer cannot publish g1

If `write_target_size_result_view(...)` remains importable/public:

```text
write_target_size_result_view(
    paths.results / "target-size-state.json",
    g1_revision,
    validated_result=g1_validated,
)
```

must fail before publication because terminal use is unsupported outside the current owner.

If the function is intentionally removed/private, acceptance must instead prove it is absent from the supported export surface and no exported replacement has equivalent terminal snapshot capability.

For the canonical result file:

- remove it before the attempt and prove it is not created; **or**
- record exact pre-attempt bytes/digest and prove the stale attempt does not change them.

#### B. Legacy/generic terminal builder cannot supply a public current payload

If `build_target_size_result_view(...)` remains public, calling it with `g1_revision + g1_validated` after g2 is current must reject terminal use. If it becomes private/internal, prove it is not exported as current API.

Returning a stale terminal dictionary from an exported generic builder counts as a bypass even if it does not itself perform file I/O, because downstream callers can publish or consume it as current without CampaignStore.

#### C. Current facade still rejects stale g1 and accepts unchanged current terminal

Retain the revision-7 current-facade tests:

- after g2 exists, `write_current_target_size_result_view(...)` rejects stale `expected_revision=g1_revision` and does not publish stale data;
- `report_current_target_size_terminal_state(...)` rejects stale g1 before stdout;
- unchanged current terminal reload validates and reports/writes identically with zero new TRAIN2/EVAL2/trainer/inference work;
- stale/missing rebuildable `current_head.json` remains recoverable while missing/corrupt immutable adopted evidence fails closed.

### 3.3 Mandatory structural/export acceptance

Add source/API-surface checks that would fail if the bypass is reintroduced:

1. Enumerate `campaign_target_size_view.__all__` (and any package-level re-export surface if applicable).
2. Prove no exported function lacking `cfg/paths/store` or equivalent authoritative context can successfully process a terminal `TargetSizeCampaignRevision` into a terminal result payload/file.
3. Specifically prove no exported arbitrary-path writer accepts `revision + validated_result` for terminal state.
4. Search production code for calls to any private terminal snapshot formatter. Every terminal production call must be downstream of the CampaignStore-backed current exposure owner in the same invocation.
5. Confirm exactly one canonical current-terminal loader remains and no second freshness/currentness authority was introduced.
6. Confirm the result file remains derived/non-authoritative and is never read as the source of current N/T.

Do not satisfy this with name-string checks alone. Pair structural inspection with the executable stale-g1 regression above.

### 3.4 E4 stage-local regression

After the final E4 executable edit, at minimum run:

- `tests/test_mlff_target_size_p4e_terminal_and_invalidation.py` including the exact legacy/generic `g1_revision + g1_validated` bypass reproducer;
- affected P4-D terminal completion/reload runtime tests;
- affected P4-F result-view/storage/structural tests;
- P3A9 resolver/reconciliation tests because current terminal exposure authenticates adopted immutable evidence;
- any tests covering package/module public exports or P5-facing current-result seam.

P4-C3 need not be reopened or rerun as a stage-local requirement unless E4 changes C3/STOR/root code. Its accepted evidence remains preserved.

---

## 4. Stage P4-G4 — assembled reclosure

P4-G4 is blocked until P4-E4 achieves both semantic/conformance and functional closure.

After all E4 edits are assembled:

1. Re-derive the affected surface from the final candidate.
2. Run fresh final affected regression covering P4-A through P4-G suites plus P3A9. The existing bounded suite is cheap enough that the default final command should include all eight previously assembled suites unless repository impact analysis identifies an additional affected suite.
3. Re-run the bounded assembled real-owner integration:

```text
prepare
  -> bounded select-target-size terminal
  -> fresh current terminal reload, zero retraining
  -> production STOR cleanup, current target-size evidence survives
  -> second current terminal reload, identical N/T/reason
```

4. Include assembled negatives for missing/corrupt immutable terminal P3 evidence and changed scientific identity requiring `prepare`/fresh generation.
5. Include the exact retained `g1_revision + legitimate g1_validated` attempt against every remaining exported generic result-view API after g2 becomes current.
6. Structural/absence closure must confirm:
   - one canonical execution-root owner;
   - one canonical current-terminal loader/currentness core;
   - no exported/public terminal snapshot renderer/writer bypass;
   - no production current terminal caller bypasses CampaignStore-backed exposure;
   - no duplicate generation/current-state authority;
   - no V7/version-prefixed production naming introduced by this repair.

Only after fresh G4 closure may P4 metadata return to `status: implemented` and the package README be changed to formal P4 reclosure / P5 eligibility.

Long GPU/real-production qualification remains deferred to final release. Revision 8 requires bounded functional/API/persistence integration only.

---

## 5. Implementation authority

### Frozen

- Frozen parent scientific/architectural decisions and accepted P1-P3 semantics.
- Protocol binding at 5.8.0.
- P4-C3 production STOR acceptance at revision 7.
- Single canonical execution-root owner.
- CampaignStore as sole current generation/revision authority.
- Single canonical CampaignStore-first terminal loader and complete validation chain.
- Revision-7 current terminal exposure facade (`expose_current...`, current writer, current reporter) or semantically equivalent one-owner local refactor.
- Terminal result files are derived/non-authoritative.
- No public terminal result is current without CampaignStore currentness validation in that same exposure invocation.
- P5 remains blocked until formal revision-8 reclosure.

### Delegated

- Exact private helper names and factoring for pure snapshot formatting.
- Whether legacy generic view names are removed from exports or retained as nonterminal-only compatibility APIs.
- Whether `validated_result` remains an argument on private formatting helpers.
- Local import organization and internal call factoring, provided the authority boundary above is preserved.

### Reopen only on evidence

Reopen design only if repository evidence demonstrates that a supported external compatibility contract requires public historical terminal snapshot rendering/writing and cannot be safely separated from the current-result API. If that occurs, stop and redesign only the API separation surface; do not reopen science, CampaignStore, P3, STOR, or P5 semantics by convenience.

---

## 6. Handoff closure

The implementer should be able to recover the complete revision-8 target without replaying this review:

```text
Preserved:
  P4-C3 real production STOR race is accepted.
  Canonical root owner and CampaignStore-first terminal loader are accepted.
  Revision-7 current view/report facade is the correct direction.

Remaining defect:
  exported generic build/write helpers still let a legitimate historical
  g1_revision + g1_validated produce terminal output after g2 is current.

Required product state:
  terminal-capable snapshot formatting is private/internal, OR public generic
  helpers are strictly nonterminal-only. No exported snapshot-only terminal
  renderer/writer may exist.

Required proof:
  terminal g1 -> legitimate g1 pair -> real prepare -> g2 -> invoke old generic
  escape surface directly -> no terminal payload/file can be produced; canonical
  result file unchanged/absent; current facade still works for the actual current
  terminal generation.

Final closure:
  E4 semantic + stage regression -> fresh G4 affected regression/integration ->
  formal P4 reclosure -> only then P5.
```

A renamed/exported snapshot writer, documentation-only warning, type check, or green current-facade test does not satisfy revision 8 if a caller can still publish a terminal snapshot without consulting CampaignStore.