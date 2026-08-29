---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P4
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 4
status: implemented
package_revision: 6
amended_date: 2026-08-29
reopened_from_revision5_candidate: 95c905436c2b47dea0d761145f8dc222b1428e53
revision5_baseline: P4_REVISION5_IMPLEMENTED_BASELINE.md
revision5_evidence: P4_REVISION5_IMPLEMENTATION_PROGRESS.md
revision4_baseline: P4_REVISION4_IMPLEMENTED_BASELINE.md
revision4_evidence: P4_REVISION4_IMPLEMENTATION_PROGRESS.md
entry_p3_closure_commit: 9d195807cff0bb8042f447ac33ceb0586ed708ac
compatibility_policy: destructive-generation-reset
implementation_closure: Complete revision-6 reclosure: P4-C2 canonical execution-root ownership & real-runtime first-publication race, P4-E2 current-terminal authority sealing & view/report protection, and P4-G2 assembled regression/integration closed cleanly with 166 passed tests
reconciliation_reason: Revision 6 preserves the frozen parent, accepted P1-P3 semantics, and the accepted P4 architecture. Revision-5 implementation fixed the original terminal early-return defect but left two implementation-level escape hatches: storage retention independently reconstructs the execution-root convention and its first-publication test bypasses the real select-target-size runtime; and the reusable terminal loader/view can still authenticate historical terminal state when supplied stale raw revision inputs. Revision 6 closes only those ownership and proxy-proof gaps. No scientific, reducer, TRAIN2/EVAL2, checkpoint, provider, seed, target-size decision, or P5 post-selection semantics are changed.
---

# P4 revision 6 — canonical root ownership and current-terminal authority closure

## 0. Authority and scope

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the sole scientific and architectural verdict. Cumulative P3 revision 7 through P3A9 remains accepted at `9d195807cff0bb8042f447ac33ceb0586ed708ac` and is not reopened.

`P4_REVISION5_IMPLEMENTED_BASELINE.md` preserves the complete revision-5 candidate that was independently reviewed at `95c905436c2b47dea0d761145f8dc222b1428e53`. `P4_REVISION5_IMPLEMENTATION_PROGRESS.md` preserves its implementation/evidence record. Revision 4 remains preserved in the adjacent revision-4 baseline/evidence files.

Revision 6 is a narrow implementation-repair overlay. It reopens only:

1. **P4-C2 — canonical execution-root ownership + real-runtime first-publication retention acceptance**;
2. **P4-E2 — current-terminal authority/currentness + terminal-view/report sealing**;
3. **P4-G2 — fresh assembled closure after C2/E2**.

P4-A, P4-B, P1-P3 science, nonterminal reducer/screen semantics, checkpoint semantics, provider ownership, and target-size decision logic remain frozen and accepted subject only to affected regression. P5 remains blocked until P4 revision 6 recloses.

The workplan remains bound to Protocol 5.8.0. Do not silently adopt a newer protocol version.

---

## 1. Review findings being repaired

### 1.1 P4-C2 finding: storage and runtime do not share one root owner

Revision 5 currently has two independent constructions of the current-generation execution root:

- runtime: `current_target_size_execution_root(paths, generation)` derives `paths.internal / "target-size" / g<N>`;
- retention: `retention_fence_for_revision(...)` independently derives `workspace / ".mdstats" / "target-size" / g<N>` when `state.execution_root` is absent.

The strings happen to agree today, but agreement by duplication is not ownership. A future change in `CampaignPaths.internal`, root layout, or runtime construction could make screening publish under root A while STOR protects root B.

Revision-5 acceptance also manually initializes P3 at the same duplicated test path instead of traversing the real `select-target-size -> build_screen_context -> canonical-root owner -> initialize_target_size_screen` path. That evidence can remain green while the production runtime is broken, so it cannot close the first-publication owner claim.

### 1.2 P4-E2 finding: reusable terminal APIs can authenticate historical state as current

Revision 5 correctly removed the public CLI's early terminal return and added `load_validated_target_size_terminal_result(...)`. However, that loader accepts a caller-supplied `revision` and uses it directly instead of always proving that it is the **current** CampaignStore revision. A historical terminal generation can therefore be reauthenticated against its old config/evidence and returned as a `ValidatedTargetSizeTerminalResult` after CampaignStore has advanced.

The terminal result-view builder also accepts raw `TargetSizeCampaignRevision + resolver + definition`. That proves internal P2/P3 projection consistency but does not prove that the revision is the campaign's current generation or that the full current P1/P2/common/execution-context identity still matches. This leaves a downstream bypass that P5 could accidentally use.

Both are implementation nonconformance to the existing P4 authority model: CampaignStore owns which generation is current; terminal state is only a derived projection of the current authenticated generation.

---

## 2. Frozen revision-6 end state

### 2.1 Exactly one canonical execution-root construction owner

There must be exactly one production owner for constructing both:

- the absolute current-generation target-size execution root; and
- its campaign-relative persisted locator.

Runtime, retention/STOR, tests, and any later P5 consumer must reuse that owner rather than reconstructing the layout independently.

**Required implementation consequence:** extract or relocate the existing root construction into a dependency-leaf, version-agnostic P4 utility/owner that both runtime and retention can import without circular dependency. A module equivalent to `campaign_target_size_paths.py` is the preferred realization, but the exact filename is delegated.

The canonical owner should expose semantics equivalent to:

```text
target_size_execution_root(workspace_or_paths, generation) -> absolute Path
target_size_execution_root_locator(workspace_or_paths, generation) -> campaign-relative POSIX locator
```

The helper must be the one place that knows the `.mdstats/target-size/g<N>` layout. `campaign_target_size_runtime.py` and `campaign_target_size_retention.py` must not each retain their own `TARGET_SIZE_EXECUTION_ROOT_NAME`, `"target-size"`, `.mdstats` joining rule, or equivalent path formula.

The existing persisted `execution_root` remains authoritative when present and must still be validated as a campaign-relative non-escaping locator. The canonical helper owns deterministic construction for the pre-`OPEN_ATTEMPT` interval when the locator is not yet persisted.

No second mutable root manifest, pending-root row, generation counter, pointer file, or path registry may be introduced.

### 2.2 First-publication retention must be proven through the real runtime path

The first-publication claim is specifically:

> When real `select-target-size` creates/initializes the canonical P3 root for a current `AUTHORITIES_BOUND` generation, real production STOR destructive authorization cannot delete that actual runtime-created root or its first published P3 evidence before `OPEN_ATTEMPT` persists `execution_root`/attempt state.

Acceptance must therefore execute the real runtime owner.

Allowed synchronization technique:

- monkeypatch/wrap `target_size_execution.initialize_target_size_screen` **only** to observe/synchronize the race;
- the wrapper must call the real initializer exactly once with the exact arguments supplied by production runtime;
- after the real initializer returns, record the actual `root` argument, signal the test, and block until the independent cleanup attempt finishes;
- then return the real initializer's result unchanged.

Forbidden acceptance substitutions:

- manually choosing `.mdstats/target-size/g1` in the test and directly invoking P3 initialization as the acceptance path;
- reimplementing `build_screen_context` root logic in the fixture;
- calling `retention_fence_for_revision` alone and claiming runtime/STOR integration;
- constructing a test-only fence or deletion flag not consumed by `_campaign_ownership_boundary`;
- patching the canonical root owner to return the expected test path.

The numerical trainer/evaluator may remain bounded/faked below the already accepted P3/runtime semantic owner boundary.

### 2.3 A current terminal loader must always prove currentness from CampaignStore

`load_validated_target_size_terminal_result(...)` is the canonical reload/P5-facing current-terminal consumer. It must never accept caller-provided historical state as authority.

**Preferred required realization:** remove the public `revision=` authority parameter. The loader always starts with:

```text
current = require_current_target_size_runtime(store)
```

and validates that exact current revision.

If implementation has a justified reason to retain an expected revision/token for intra-command efficiency, it is only an assertion, never authority:

1. always load `current` from the real CampaignStore first;
2. require exact equality of at least `state_revision`, `sequence`, `generation`, and terminal lifecycle between the supplied expectation and `current`;
3. reject mismatch as stale/current-generation conflict before P1/P2/P3 terminal validation;
4. perform all subsequent validation on `current`, not on the caller-supplied object.

A historical generation may still be inspectable through explicitly historical/audit APIs, but it must never be returned by the API whose semantic claim is **current terminal target-size result**.

### 2.4 Terminal validation remains full-chain, not projection-only

The canonical current-terminal loader must continue to establish, before returning:

1. current CampaignStore regime/generation/revision;
2. current P1 source/frame/neutral/split-exclusion authority reconstruction;
3. current P2 policy/definition/aggregate identity;
4. current common-preparation identity;
5. current P3 execution-context identity;
6. canonical execution-root identity/location;
7. authenticated adopted immutable P3 head and reducer state;
8. re-derived `N_selected` and exact `T_selected` membership identity;
9. equality with persisted terminal projection/lifecycle.

Missing/corrupt P3 evidence remains corruption. Changed scientific identity remains invalidation with guidance to run `prepare`. CV-only/production-only changes remain target-size neutral.

Do not weaken any revision-5 terminal checks merely to close the currentness gap.

### 2.5 Terminal views and reporting must consume validated current authority

A raw terminal `TargetSizeCampaignRevision` must no longer be sufficient to render or report a **current terminal result**, even if a caller also supplies an old resolver and old P2 definition.

**Required end state:** terminal result-view generation and terminal CLI reporting consume a `ValidatedTargetSizeTerminalResult` (or an equivalent opaque/current-authenticated result produced only by the canonical validation path). Nonterminal diagnostic views may continue to accept raw nonterminal campaign revisions.

Required consequences:

- remove the terminal `raw revision + resolver + definition` rendering alternative;
- `build_target_size_result_view(...)` / `write_target_size_result_view(...)` must reject raw terminal state unless accompanied by the canonical validated-current result that exactly matches the same `state_revision`;
- `_report_terminal_state(...)` must not accept a raw `TargetSizeTerminalProjection` as sufficient authority; it should accept only the validated-current terminal result or equivalent sealed result;
- initial terminal completion in `select-target-size` must also produce/obtain the validated-current result before terminal view/report exposure;
- if avoiding a second expensive P1 reparse on the same command, implementation may factor one internal validator/factory that consumes already reconstructed authoritative P1/P2/P3 objects **but must first reload/compare the current CampaignStore revision and must share the same terminal validation core**. Do not create a second independent terminal decision/re-derivation implementation.

The validated-result type itself is a transport object, not a security primitive. Correctness comes from the single canonical factory/loader and caller routing, not from trusting that arbitrary code could not instantiate a Python dataclass.

---

## 3. Implementation obligations and acceptance

### Stage P4-C2 — consolidate root ownership and prove the actual first-publication race

#### Implementation obligations

1. Introduce/extract the single version-agnostic canonical root-construction owner described in §2.1.
2. Refactor `campaign_target_size_runtime.py` to import/use it for root construction and persisted locator generation.
3. Refactor `campaign_target_size_retention.py` to import/use the same owner when `state.execution_root is None`.
4. Remove duplicate root-name constants/path formulas from runtime and retention.
5. Preserve persisted-locator validation, reconciliation-frontier semantics, publication-window semantics, STOR containment/symlink/ownership rules, and P3 -> CampaignStore -> STOR lock ordering.
6. Do not add CampaignStore writes merely to reserve the root; deterministic derivation from the current generation is sufficient and lower complexity unless evidence proves otherwise.

#### Mandatory proxy-proof runtime race test

Drive the real parser/current runtime from a real campaign fixture:

```text
real prepare
 -> current AUTHORITIES_BOUND generation, no attempt, no persisted execution_root
 -> start real select-target-size
 -> production build_screen_context calls canonical root owner
 -> wrapper around real initialize_target_size_screen calls real initializer exactly once
 -> wrapper pauses after real first publication and exposes actual root argument
 -> assert CampaignStore is still AUTHORITIES_BOUND, attempt=None, execution_root=None, adopted_head=None
 -> independent spawned process opens same real CampaignStore
 -> child builds boundary through real _campaign_ownership_boundary(cfg, paths, store)
 -> child attempts destructive removal/authorization on actual runtime root and representative freshly published files using production cleanup authorization/removal helper
 -> zero protected runtime files removed
 -> release initializer wrapper
 -> real select-target-size continues/resumes with bounded numerical seams
 -> screen remains valid and reaches at least OPEN_ATTEMPT/reconciliation; preferably terminal bounded completion
```

The test must derive cleanup targets from the actual root argument observed from production runtime. It must not separately calculate the expected root to choose the target under test.

Add a deliberate regression guard that would fail if runtime and retention stop sharing the same canonical root owner. A focused AST/import/uniqueness check is appropriate here because the claim is ownership/absence, not ordinary behavior.

Also preserve/execute negatives proving external paths, symlink escapes, and unrelated reclaimable campaign-owned residue do not become protected merely because the target-size fence exists.

#### Stage-local regression

At minimum rerun:

- `tests/test_mlff_target_size_p4c_cross_store_adoption.py`;
- affected P4-D runtime-cutover tests;
- P4-F storage/structural tests;
- affected STOR accounting/reclamation/cleanup suites;
- any root/path helper tests added by the refactor.

P4-C2 is not closed by the old direct-initializer test. Replace or demote it to a focused helper test; the new real-runtime race is the acceptance owner.

### Stage P4-E2 — seal current-terminal authority and downstream consumers

#### Implementation obligations

1. Make `load_validated_target_size_terminal_result` always establish the current revision from CampaignStore before using any terminal state.
2. Remove caller-supplied revision authority, or convert it to a strict expected-current assertion as defined in §2.3.
3. Preserve all revision-5 P1/P2/common/context/head/reducer/projection validation.
4. Refactor terminal result-view generation so raw terminal revision + resolver + definition cannot render a current terminal result.
5. Refactor `_report_terminal_state` so raw `TargetSizeTerminalProjection` cannot be reported as current terminal authority.
6. Route both repeated-terminal reload and initial terminal completion through one canonical validated-current result path before terminal output/view publication.
7. Keep nonterminal result-view behavior and nonterminal screen continuation unchanged.
8. Do not introduce a second terminal loader/reducer/replay engine or historical/current compatibility fallback.

#### Mandatory currentness tests

All tests use real CampaignStore and real current-state transitions. Expensive numerical work may remain bounded below the existing owner seam.

**A. Historical revision cannot masquerade as current**

1. Produce terminal generation `g1` and capture its terminal revision/evidence.
2. Change a target-size scientific identity and run real `prepare` so CampaignStore advances/binds fresh generation `g2`.
3. Invoke the canonical current-terminal loader. It must not return `g1`; it must reject because current `g2` is nonterminal or because any supplied expected revision is stale.
4. If an expected-revision parameter remains, explicitly pass captured `g1` and assert stale/current mismatch before historical P3 evidence is accepted.

**B. Raw historical terminal view is rejected even when internally self-consistent**

Using the same `g1 -> g2` setup, retain intact `g1` P3 head and old definition/resolver. Calling the public terminal view builder with raw `g1` state (and old resolver/definition if those parameters still exist for nonterminal reasons) must fail. The only success path for a current terminal view is a validated-current result matching current CampaignStore `state_revision`.

**C. Valid current terminal reload still succeeds**

For unchanged terminal current generation, canonical loader -> view -> reporter succeeds, returns/reports the same terminal result, and schedules zero new trainer/evaluator work.

**D. Existing corruption/invalidation matrix remains green**

Retain revision-5 mandatory cases for missing/corrupt adopted head, campaign-row tamper, seeds/fidelity/policy/partition/common/execution-context invalidation, neutral CV/production changes, terminal scientific failure, and missing/stale rebuildable `current_head.json`.

#### Structural/ownership checks

Prove:

- exactly one public/current terminal-load owner exists;
- no public/current terminal render/report path consumes `state.terminal` directly as authority;
- no raw `TargetSizeTerminalProjection` is accepted by the current terminal reporter;
- P5 has one obvious current-terminal API to consume after P4 closes;
- historical/audit access, if any, is named/typed separately and cannot be mistaken for current terminal authority.

#### Stage-local regression

At minimum rerun:

- all P4-E terminal/invalidation tests;
- P4-D runtime/CLI tests affected by reporter/view/loader changes;
- P4-F structural/view/storage tests;
- P3A9 resolver/reconciliation tests if loader routing touches P3 resolution;
- affected campaign state/CAS tests if expected-current conflict handling changes store interaction.

### Stage P4-G2 — assembled reclosure

Only after P4-C2 and P4-E2 have both semantic and functional closure:

1. re-derive the complete affected surface from the final revision-6 diff;
2. reconcile every revision-6 obligation against actual source, not only the progress log;
3. rerun complete affected P4-C/P4-D/P4-E/P4-F regression plus P3A9 where plausibly affected;
4. run one bounded assembled flow through real owners:

```text
prepare
 -> select-target-size to terminal
 -> fresh current-terminal reload
 -> terminal view/report
 -> real STOR cleanup authorization
 -> scientific config change + prepare -> fresh generation
 -> prove old terminal revision/view cannot masquerade as current
```

5. run the real-runtime first-publication cleanup race on the same assembled candidate;
6. run structural uniqueness checks for root owner and current-terminal owner;
7. run broader/full repository regression if final impact cannot be bounded confidently; pre-existing unrelated failures may be attributed but any new or plausibly affected failure blocks closure;
8. only then update `P4_IMPLEMENTATION_PROGRESS.md`, package README, and P4 metadata from `active` to `implemented`.

Long GPU/real-production qualification remains deferred to final release.

---

## 4. Frozen / delegated / reopen authority

### Frozen

- frozen parent and accepted P1-P3 science/reducer/execution semantics;
- one CampaignStore current mutable authority and one canonical target-size generation;
- one canonical deterministic execution-root construction owner shared by runtime and STOR;
- first-publication retention proven through real `select-target-size`, real P3 initializer, and real production STOR authorization;
- P3 immutable evidence remains scientific execution/replay authority;
- current terminal result always starts from the actual current CampaignStore revision;
- terminal P1/P2/common/context/head/reducer/N/T revalidation remains mandatory;
- raw/historical terminal campaign state cannot render/report as current terminal result;
- no fallback/dual-write/second terminal authority/second root authority;
- P3 -> CampaignStore -> STOR mutation ordering remains acyclic;
- P5 remains blocked until P4 revision 6 recloses;
- production naming remains version-agnostic;
- long GPU qualification remains deferred.

### Delegated

- exact dependency-leaf module name for canonical root helpers;
- exact function names/signatures for absolute root vs locator, provided both runtime and retention reuse the same implementation;
- whether the terminal loader removes `revision=` entirely or retains a strict expected-current assertion token;
- exact internal factoring used to avoid duplicate expensive P1 reconstruction immediately after terminal commit, provided it shares the same validation core and checks current CampaignStore revision;
- exact validated-result/view function signatures and exception classes consistent with repository conventions;
- synchronization primitives used by the real-runtime race test.

### Reopen only on evidence

Reopen design only if implementation demonstrates one of:

- a single dependency-leaf root owner cannot be shared by runtime and retention without a material dependency-cycle/architecture replacement;
- real `select-target-size` cannot expose a synchronization point around the real P3 initializer without replacing the owner under acceptance;
- current CampaignStore state cannot be reloaded/compared cheaply enough to establish currentness without changing persistence architecture;
- P5 genuinely requires historical terminal inspection to share the same API as current terminal authority and cannot separate those semantics cleanly;
- a frozen parent/P1-P3 requirement is internally contradictory with these repairs.

Test inconvenience, desire to preserve duplicated root strings, desire to reuse a stale revision for speed, or desire to keep raw terminal rendering are not redesign triggers.

---

## 5. Handoff closure

Revision-6 implementation succeeds only if this chain is true in the assembled product:

```text
one canonical generation
 -> one canonical execution-root constructor
 -> real select-target-size publishes only under that root
 -> STOR derives protection from the same root owner before first publication is reclaimable

and

real CampaignStore current revision
 -> full current P1/P2/common/P3 authentication
 -> re-derived terminal N/T
 -> one validated-current terminal result
 -> terminal view/report/P5 consumption
```

The two historical escape hatches must be structurally impossible in ordinary current-product code:

```text
runtime root A + independently guessed STOR root B         # forbidden
historical raw terminal revision -> current view/report     # forbidden
```

No material requirement from revisions 4-5 is relaxed. This amendment only closes the remaining ownership/currentness gaps and strengthens their acceptance boundary so the same proxy-proof failure cannot recur.
