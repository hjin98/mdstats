---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P4
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 4
status: active
package_revision: 5
amended_date: 2026-08-29
reopened_from_p4_closure_commit: 53800cf3e4862326643b1708863f9b07573669ef
reviewed_branch_tip: a66d32ffb3b3da2b1d51d2e8d970bd0083839f23
revision4_baseline: P4_REVISION4_IMPLEMENTED_BASELINE.md
revision4_evidence: P4_REVISION4_IMPLEMENTATION_PROGRESS.md
entry_p3_closure_commit: 9d195807cff0bb8042f447ac33ceb0586ed708ac
compatibility_policy: destructive-generation-reset
implementation_closure: P4 reopened after independent review; P4-E terminal real-owner reload and P4-C first-publication retention hardening are open, and P4-G assembled closure is invalidated until both close
reconciliation_reason: Revision 5 preserves the frozen parent, accepted P1-P3 semantics, and the accepted revision-4 P4 architecture. It reopens only two implementation surfaces exposed by independent review: the public terminal select-target-size path can currently report persisted terminal state before mandatory P1/P2/P3 revalidation, and the first P3 execution-root publication can occur before STOR has a provable current-generation retention fence. P4-A, P4-B, the nonterminal/cutover substance of P4-D, and P4-F remain accepted baseline work subject only to affected regression. No scientific, statistical, reducer, TRAIN2/EVAL2, checkpoint, provider, seed, target-size decision, or post-selection P5 semantics are changed.
---

# P4 revision 5 — reopened terminal reload and first-publication retention closure

## 0. Authority, baseline, and reopening scope

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the sole scientific and architectural verdict. Cumulative P3 revision 7 through P3A9 remains accepted at `9d195807cff0bb8042f447ac33ceb0586ed708ac` and is **not reopened**.

This file is the authoritative P4 revision-5 overlay. `P4_REVISION4_IMPLEMENTED_BASELINE.md` is the complete revision-4 P4 contract and is incorporated by reference. Revision 4 remains authoritative everywhere this revision does not explicitly override status, sequencing, acceptance, or implementation consequences. `P4_REVISION4_IMPLEMENTATION_PROGRESS.md` preserves the accepted revision-4 implementation evidence for reuse where the reopened changes cannot plausibly invalidate it.

Revision 5 reopens only:

1. **P4-E terminal reload / invalidation through the real public owner** — **blocking**;
2. **P4-C first-publication execution-root retention coverage** — required hardening discovered by independent review;
3. **P4-G assembled closure** — necessarily invalidated until the two reopened surfaces close.

P4-A and P4-B remain closed. P4-D remains architecturally closed except that its real `select-target-size` caller is modified by the P4-E repair and therefore its affected CLI regression must rerun. P4-F remains architecturally closed except that affected STOR regression must rerun after the P4-C hardening. No accepted P1-P3 scientific behavior may be redesigned to solve either defect.

**P5 is blocked while P4 revision 5 is active.** P5 may not consume terminal target-size state as frozen current authority until revision 5 is functionally and semantically reclosed.

The workplan remains bound to Protocol 5.8.0. Do not silently upgrade its protocol version merely because a newer protocol is installed.

---

## 1. Reopen diagnosis and protected concerns

### 1.1 Blocking defect — terminal public reload bypasses the mandatory authority chain

The revision-4 implementation already has a correct low-level `validate_terminal_projection(...)` mechanism. The defect is the **real caller path**: `execute_current_select_target_size()` loads CampaignStore state and, when lifecycle is terminal, reports `revision.state.terminal` and returns before reconstructing current P1/P2/P3 authorities or invoking terminal re-derivation.

That violates the frozen P4 requirement that a terminal `N_selected` / exact `T_selected` may be exposed only after current scientific identity and referenced P3 terminal evidence are authenticated and re-derived. It allows a stale persisted terminal projection to be reported after missing/corrupt P3 evidence or after target-size scientific configuration changed.

Protected concerns:

- CampaignStore terminal fields remain a **projection/reference**, never a decision authority;
- a public terminal reload must be at least as strict as initial terminal commit;
- scientific invalidation must be detected before stale `N` is printed, returned, rendered, or handed to P5;
- unchanged terminal reload must not retrain or reevaluate completed science;
- terminal scientific failure is validated by the same authority chain before it is reported as terminal;
- CV-only and production-only changes remain target-size-neutral;
- no second terminal validator, reducer, replay engine, or compatibility path is introduced.

### 1.2 Required hardening — first P3 publication can precede a provable STOR protected root

The revision-4 runtime can derive/create the current generation execution root and call P3 screen initialization before the later `OPEN_ATTEMPT` CampaignStore transition records `execution_root`. The revision-4 retention fence is inert when no root locator is available from current state. Therefore there is a narrow first-publication interval in which a real STOR destructive path can see campaign-owned P3 bytes without a lifecycle fence that proves they are the current generation's protected root.

This is narrower than the already-covered P3-head-publication -> SQLite-adoption race, but it is still inconsistent with the frozen requirement that cleanup cannot encounter promoted current-generation P3 evidence before protection exists.

Protected concerns:

- no current-generation P3 file may become deletion-eligible merely because the campaign has not yet adopted/bound a head or attempt;
- protection must derive from the one canonical campaign generation/root owner, not a second mutable manifest;
- no long-lived coarse fence may permanently pin provably unreachable residue;
- existing P3 -> CampaignStore adoption ordering and no-nested-lock constraints remain intact;
- STOR ownership checks remain authoritative and the target-size fence may only reduce deletion authority.

### 1.3 Classification

The terminal reload defect is **implementation nonconformance** to the already-correct revision-4 contract. The first-publication gap is a **new necessary implementation consequence** of the existing storage invariant. Neither requires a parent/P1/P2/P3 redesign.

---

## 2. Frozen revision-5 end state

The following are frozen additions/clarifications to the revision-4 contract.

### 2.1 No terminal exposure before validated reload

For every current terminal campaign state, the real production consumer must establish all of the following **before** exposing terminal status, selected `N`, selected membership identity, terminal reason, or any derived terminal result view:

1. load the current CampaignStore revision through the real SQLite owner;
2. reconstruct the current P1/P2 scientific authorities from current source/config inputs through their accepted owners;
3. compare the complete target-size scientific identity against the persisted canonical generation, including the common preparation / execution-context dimensions that affect screening semantics;
4. if scientific identity changed, fail closed as invalidated current state and direct the operator to `prepare` for a fresh canonical generation; `select-target-size` must not print the stale terminal result first;
5. resolve the persisted current-generation execution root through the real P3 owner without manufacturing a new screen;
6. reconcile/resolve the P3 terminal execution state through accepted P3 resolver/reconciliation semantics and authenticate the adopted head/reducer identity;
7. re-derive terminal `N_selected` from the authenticated terminal reducer state and exact `T_selected` identity from the P2 training order;
8. compare the complete re-derived projection to CampaignStore terminal projection;
9. only after all checks pass may the CLI/report/view/downstream loader expose terminal state.

A raw `TargetSizeCampaignRevision` with `state.terminal != None` is **not** by itself a validated terminal result.

### 2.2 One reusable validated terminal-load owner

Implement or consolidate one reusable current terminal-load path in the existing P4 terminal/runtime ownership area. Exact symbol and module placement are delegated, but it must be the production path used by `select-target-size` terminal replay and be suitable for direct reuse by P5 rather than forcing P5 to reconstruct validation logic.

The validated result must bind enough authenticated objects/identities that a downstream caller cannot accidentally treat the persisted terminal projection as independently authoritative. A small immutable return object is acceptable; a second persisted manifest/database is forbidden.

### 2.3 Invalidated terminal behavior

When reconstructed target-size scientific identity differs from the persisted terminal generation:

- do **not** report the old selected `N` or old terminal failure as current;
- do **not** silently reinterpret old P3 evidence under new configuration;
- do **not** mutate/advance generation as an incidental terminal-read side effect of `select-target-size`;
- fail closed with typed/actionable guidance to run `prepare`, which remains the owner that binds a fresh scientific substrate/generation;
- preserve the old generation and its terminal evidence as historical authenticated state.

CV-only or post-selection-production-only changes that do not participate in target-size identity must continue to validate and report the same terminal result without retraining.

### 2.4 Terminal result views cannot bypass validation

Any current API that can serialize/render a terminal projection, including the target-size result view, must not expose persisted terminal fields from a raw CampaignStore revision alone. For terminal state it must either:

- consume the validated terminal-load result, or
- receive the real P2/P3 inputs required to perform equivalent validation before rendering.

Nonterminal diagnostic/current-state views may continue to render nonterminal CampaignStore metadata without pretending it is terminal scientific authority.

### 2.5 First-publication retention is established before first P3 bytes are reclaimable

Before the current generation publishes or initializes any P3 execution-root artifact that a destructive STOR path could encounter, STOR must already be able to derive a protected current-generation execution root.

Acceptable realizations include either:

- durably binding/reserving the deterministic current-generation root locator in CampaignStore before P3 publication, with the CampaignStore transaction fully released before any P3 mutation lock/I/O; or
- having the retention fence derive the deterministic canonical generation root from the one canonical generation/root-construction owner even when the later explicit state locator is not yet populated.

Other equivalent realizations are allowed only if they preserve the same single authority and race safety.

Forbidden realizations:

- a second mutable "pending root" manifest or counter;
- deriving protection from `current_head.json` or file existence alone;
- a test-only cleanup bypass/flag;
- globally pinning the entire workspace indefinitely;
- holding a CampaignStore write transaction while invoking P3 initialization/reconciliation;
- weakening STOR containment, ownership, symlink, or capability checks.

The initial root-protection step is campaign allocation/protection, not adoption of P3 scientific evidence. Ordinary P3 evidence publication/reconciliation -> bounded CampaignStore adoption ordering remains unchanged.

---

## 3. Reopened implementation sequence

Only these stages are executable under revision 5. Preserve all unrelated revision-4 code/evidence.

### Stage P4-C1 — close first-publication retention gap

**Required implementation consequences**

1. Trace the exact production order from `execute_current_select_target_size` / screen-context construction through root derivation, `initialize_target_size_screen`, CampaignStore state transition, and `_campaign_ownership_boundary`.
2. Ensure the canonical current-generation root is protected by the production retention fence **before** the first real P3 initializer can publish bytes beneath it.
3. Use the existing canonical generation and existing `current_target_size_execution_root(...)` ownership/convention; do not duplicate path derivation in an independent storage policy if it can be imported/reused.
4. Keep any CampaignStore reservation/CAS short and release it before real P3 mutation or filesystem traversal.
5. Preserve current reconciliation-frontier reachability and later reclamation of proven unreachable residue.

**Real-owner acceptance boundary**

The claim under acceptance is the production runtime -> P3 first publication -> real STOR destructive authorization ordering. Tests must use a real CampaignStore SQLite file and real `CampaignOwnershipBoundary`/production fence. The real P3 initializer must execute. It may be **wrapped only to synchronize/observe the race and must call the real initializer exactly once**. It may not be replaced by a fake initializer that merely creates a convenient file. Expensive later training/inference remains replaceable below its already accepted seam.

**Mandatory focused acceptance**

- Start from a current `AUTHORITIES_BOUND` generation before any screen attempt/head has been adopted.
- Enter the real `select-target-size` path and pause immediately after the real first P3 screen/root publication but before any later transition that revision 4 previously relied on to populate `execution_root`/attempt state.
- From an independent process/connection, construct the real production STOR destructive boundary and attempt to delete the root plus representative freshly published P3 files.
- Deletion must be denied and the real screen must remain resumable.
- Repeat with no adopted head to prove protection does not depend on SQLite head adoption.
- Prove external/symlink/ambiguous paths remain denied by existing ownership semantics and an unrelated campaign-owned reclaimable path is not accidentally pinned by the new rule.

**Stage-local affected regression**

Rerun P4-C retention/adoption tests, touched STOR ownership/reclamation tests, and the bounded P4-D `select-target-size` current-runtime integration. Any change to common retention/root helpers also requires their existing structural/cleanup regression.

P4-C1 closes only when semantic review confirms there is still one canonical root/generation authority and the real race test above passes.

### Stage P4-E1 — make terminal reload a real authenticated consumer

**Required production flow**

The implementation must remove the current early terminal-return bypass. A production terminal invocation of `select-target-size` must follow this ordering:

```text
parse real config
  -> open real CampaignStore / require current regime
  -> reconstruct current P1/P2/common scientific authorities
  -> compare current scientific identity with persisted canonical generation
     -> mismatch: fail closed + direct to prepare; expose no stale terminal result
  -> reconstruct/validate the P3 execution-context identity without publishing new screen state
  -> resolve/reconcile the persisted execution root through real P3 owner
  -> authenticate adopted terminal head + reducer
  -> re-derive N_selected + exact T_selected through P2/P3
  -> compare persisted terminal projection
  -> only now report/render/return terminal result
```

For a nonterminal generation, the existing P4-D/P3 screening path continues after the same current-authority checks. Do not force terminal reload through a helper that initializes a new screen or writes new P3 evidence merely to validate old terminal state; factor pure authority/context construction from screen initialization if needed.

**Required caller consolidation**

- `execute_current_select_target_size()` must consume the validated terminal-load owner before `_report_terminal_state` or equivalent output.
- `_report_terminal_state` or its replacement must not accept an unvalidated raw terminal revision in a way that permits future bypass; accepting a validated terminal result/projection is preferred.
- terminal target-size result-view rendering must use the validated load path or reject raw terminal rendering.
- P5-facing code must have one obvious validated loader to reuse; do not leave two nearly equivalent terminal loaders.

**Failure semantics**

- missing adopted head -> hard corruption, no terminal output;
- corrupt/tampered adopted head/reducer -> hard corruption, no terminal output;
- changed P1/P2/protected relation/hard-support/seed/order/fidelity/metric/practical-equivalence/common-preparation/training-policy/execution-context identity -> scientific invalidation, no stale terminal output, guidance to `prepare`;
- malformed schema/regime -> fail closed;
- unchanged terminal selection -> validate, report same `N`, perform zero new training/evaluation;
- unchanged terminal scientific failure -> validate, report same terminal scientific outcome, perform zero new training/evaluation;
- CV-only/production-only changes -> remain target-size-neutral and report the same validated terminal state.

**Real-owner acceptance boundary**

The material claim is the real public CLI terminal consumer. Direct unit calls to `validate_terminal_projection(...)` are necessary low-level tests but **cannot close this stage**. Mandatory tests must drive the real parser/function, real CampaignStore, real P1/P2 authority reconstruction, and real P3 resolver/reconciler. Bounded trainer/inference fakes may be used only to create the initial terminal fixture. On the reload invocation, use a poison/no-call trainer/evaluator or equivalent observation to prove zero numerical work is scheduled.

**Mandatory terminal CLI cases**

1. **Unchanged fresh-process reload:** close/reopen CampaignStore, remove or stale the rebuildable `current_head.json` pointer, rerun real `select-target-size`; P3 recovery/resolve succeeds, identical terminal projection is reported, and no trainer/evaluator executes.
2. **Missing immutable adopted head:** create a valid terminal campaign, remove the immutable adopted head file, rerun real CLI; command fails as corruption before printing/returning the selected `N` or terminal scientific outcome.
3. **Corrupt immutable adopted head:** tamper its authenticated content, rerun real CLI; fail closed before terminal exposure.
4. **Persisted campaign tamper:** mutate a terminal CampaignStore row/payload outside the owner so its authenticated revision/projection no longer verifies; real CLI rejects rather than reporting stored `N`.
5. **Scientific configuration invalidation:** parameterize representative changes covering at minimum optimizer seed set/order, fidelity boundaries, target/evaluation-size policy or metric/practical-equivalence, neutral partition/protected relation or hard-support identity, and common preparation/training/execution-context policy. Rerun terminal CLI; each must expose no stale result and direct to `prepare`/fresh generation semantics.
6. **Target-size-neutral changes:** representative CV-only and production-only changes must still validate the terminal result, keep the same canonical target-size generation, and schedule no screening work.
7. **Terminal scientific failure reload:** drive a bounded authenticated terminal scientific-failure fixture; unchanged reload validates and reports it, while missing/corrupt referenced P3 evidence fails instead of reporting the persisted failure.
8. **Terminal view bypass negative:** a raw terminal CampaignStore revision must not be sufficient to render a current terminal result view; validated-load input/path succeeds.

Retain the existing direct projection/tamper tests as lower-level coverage, but do not cite them as substitutes for these real-caller cases.

**Stage-local affected regression**

Rerun all P4-E tests, P4-D runtime/CLI tests touched by caller refactoring, P3A9 resolver/reconciliation tests if the new terminal loader invokes those surfaces, target-size view tests, and affected campaign CLI/state tests. Newly introduced failures block the stage.

### Stage P4-G1 — assembled reclosure

After P4-C1 and P4-E1 both close semantically and functionally:

1. reconcile the complete revision-5 diff against the frozen parent + revision-4 baseline + this overlay;
2. re-derive the affected surface from the final assembled diff rather than relying on the list above;
3. rerun complete affected P4-C/P4-D/P4-E/P4-F regression;
4. rerun P3A9 recovery regression whenever terminal/reconciliation caller changes can plausibly affect it;
5. run bounded real-owner integration:

```text
prepare
 -> select-target-size to terminal using bounded numerical substitutes below P3 owner
 -> fresh-process terminal reload through real CLI
 -> real STOR accounting/cleanup authorization
 -> second terminal reload proving no retraining and identical authenticated result
```

6. include negative assembled runs for missing/corrupt terminal head and changed scientific identity;
7. run the broader/full repository suite if final impact cannot be bounded confidently; compare failing identifiers against the preserved pre-P4/revision-4 baseline rather than declaring an unexecuted check a pass;
8. run structural searches proving no second terminal loader/authority, no retired target-size owner regained reachability, no duplicate canonical root/generation authority, and no new `v7_`/`V7` production names;
9. update `P4_IMPLEMENTATION_PROGRESS.md` with executed commands/results and only then change P4 metadata from `active` to `implemented`.

Long GPU/real-production qualification remains deferred to final release and is not a P4-G1 exit requirement.

---

## 4. Evidence reuse and invalidation

Revision-4 evidence is intentionally preserved rather than discarded wholesale.

**Still reusable unless touched code proves otherwise:** P4-A CAS/transition identity; P4-B cutover/quarantine; P1/P2/P3 scientific semantics; nonterminal P3 execution/reducer behavior; P4-F documentation statements unrelated to reopened behavior.

**Invalidated and must rerun:** P4-C first-publication/storage-race evidence for the newly exposed interval; P4-E terminal reload/invalidation acceptance; P4-D caller regression intersecting `select-target-size`; P4-F STOR regression intersecting retention-root derivation; P4-G final assembled closure.

The previous full-suite baseline attribution remains useful for identifying pre-existing unrelated failures, but final revision-5 affected/full-suite execution must be fresh after the executable repairs.

---

## 5. Implementation authority

### Frozen

- the complete frozen parent and accepted P1/P2/P3 scientific semantics;
- revision-4 P4 single CampaignStore authority, single canonical generation, subordinate attempts, transactional predecessor CAS, deterministic transition identity, destructive no-fallback cutover, and P3 immutable execution authority;
- public terminal state is a derived authenticated projection and cannot be exposed from CampaignStore alone;
- scientific invalidation precedes terminal exposure;
- `prepare` owns creation/binding of a fresh scientific generation after invalidation; `select-target-size` does not silently convert stale terminal state into a new generation;
- first current-generation P3 publication is protected from STOR deletion before head adoption and before any later attempt/root field that would otherwise create a race window;
- no nested CampaignStore transaction around P3 reconciliation/publication or STOR destructive work;
- current result views are non-authoritative and cannot become a terminal-validation bypass;
- P5 remains blocked until revision 5 closes;
- production naming remains version-agnostic;
- full GPU qualification remains deferred.

### Delegated

Implementation may choose:

- exact symbol/return type for the reusable validated terminal loader;
- whether pure terminal context validation is factored from `build_screen_context` or implemented as a smaller adjacent builder, provided it calls accepted P1/P2/P3 owners and performs no terminal-time screen publication;
- whether first-publication protection is achieved by pre-binding/reserving the canonical root or by deterministic fence derivation from canonical generation, provided there is one authority and the race test passes;
- exact typed exception names/messages consistent with existing conventions;
- exact test filenames and synchronization technique for the first-publication race, subject to the real-owner boundary above.

### Reopen only on evidence

Reopen design only if implementation demonstrates that one of the following is impossible without changing a frozen owner/contract:

- current P1/P2/P3 authorities cannot be reconstructed on terminal load without mutating scientific state;
- P3 cannot authenticate/reconcile the persisted terminal root/head without creating new screening evidence;
- the canonical generation/root convention cannot protect first publication without a second authority or lock-order violation;
- the frozen parent/P3 semantics are internally contradictory with mandatory terminal re-derivation.

Test inconvenience, runtime cost of bounded revalidation, desire to preserve the early return, or desire to rely on persisted selected `N` are not redesign triggers.

---

## 6. Exit criteria and handoff closure

P4 revision 5 is complete only when all revision-4 exit criteria still hold **and**:

1. no real terminal consumer reports/returns/renders current target-size terminal state before current P1/P2/P3 identity and evidence revalidation;
2. the real repeated `select-target-size` path rejects missing/corrupt terminal P3 authority and changed scientific identity before exposing stale terminal state;
3. unchanged terminal selection and terminal scientific failure reload through the real CLI without retraining;
4. CV-only/production-only changes remain neutral under the same real reload path;
5. terminal result-view rendering cannot bypass validated terminal loading;
6. the production STOR fence protects the deterministic current-generation execution root before the first real P3 publication can be reclaimed;
7. the new first-publication race test uses real CampaignStore, real P3 initializer, and real production STOR authorization and cannot remain green if the fence is removed from the production path;
8. revision-5 stage-local affected regression and final assembled affected-surface integration pass with no new attributable failures;
9. `P4_IMPLEMENTATION_PROGRESS.md` records revision-5 evidence and metadata is returned to `implemented` only after those gates close.

Handoff compression:

```text
revision-4 accepted P4 architecture
+ terminal state is never authoritative by persistence alone
+ real public reload reconstructs and authenticates P1/P2/P3 before exposure
+ scientific invalidation fails before stale terminal reporting
+ first P3 publication is protected before any cleanup race can reach it
+ proxy-proof CLI/P3/STOR acceptance
+ fresh assembled regression/integration
-> reclosed P4 suitable for P5 consumption
```

No P1-P3 science, reducer policy, target-size decision semantics, or P5 post-selection design is reopened by this amendment.
