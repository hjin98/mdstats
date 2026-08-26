---
kind: implementation-workplan-amendment
parent_workplan_id: CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1-REWORK3
protocol_version: 5.6.0
status: active
reviewed_candidate: 7c057eaada12598d96b605bc607d3f2c5c1ef247
review_date: 2026-08-25
supersedes_local_realizations: true
---

# Flexible-Fidelity Rework 3 - Post-Implementation Review Amendment 2

## 1. Authority and scope

This is a **controlling delta amendment** to:

1. `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_WORKPLAN.md`; and
2. `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_REVIEW1_AMENDMENT.md`.

It is not Rework 4 and does not reopen the frozen scientific design. The parent workplan and Review 1 Amendment remain authoritative except where this amendment updates the implementation/gate state or adds newly observed runtime obligations.

All previously frozen scientific decisions remain unchanged, including:

- configurable `0 < n1 < n2 < n3 <= n`;
- fresh default `(n1,n2,n3)/n = (1,3,10)/30`;
- explicit nondefault configurations, including `(3,10,30)/30`, remain valid when actually configured;
- screening boundaries are exact checkpoints on one full-`n` trajectory/schedule rather than separately restarted short trainings;
- target-size reduction/ranking may consume only the exact configured boundary checkpoint for the active screen;
- policy-independent current DATA7/DATA8 candidate-prefix scientific identity;
- immediate fixed-fidelity predecessor compatibility only, with transitional/unknown generations failing closed unless separately and unambiguously authenticated;
- no relabeling of historical target-size screen, TRAIN2 schedule, checkpoint, evaluation, or selection evidence as current flexible-fidelity evidence;
- preserved scientifically identical DATA7/DATA8 products must be reused rather than regenerated merely because downstream fidelity/horizon changed;
- full GPU/production qualification remains deferred to the final release and is not part of this implementation closeout.

The reviewed candidate is **not accepted yet**. No reviewed evidence fires a scientific redesign trigger. Remaining findings are implementation/acceptance nonconformance plus one newly surfaced startup-I/O/operability issue.

## 2. Review-2 disposition of Review-1 findings

### 2.1 Provisionally conformant product corrections: R1-R3

The assembled candidate materially corrects the Review-1 authority defects:

- production-materialization plan schema is no longer used as the target-size candidate-authority generation discriminator;
- the immediate predecessor authority is derived from authenticated raw historical v8-study/v6-policy evidence rather than by constructing a current v7 policy with `(3,10,30)`;
- historical fixed candidate authority is captured before migration/normalization destroys the raw predecessor identity;
- transitional flexible-v1/unknown mismatch paths are explicitly fail-closed rather than silently admitted as the fixed predecessor.

These product corrections are **provisionally accepted at source/design-conformance level**. Do not redesign or replace them without new evidence. Their final acceptance still depends on the real-owner positive, negative, restart, and affected-regression evidence required below.

### 2.2 Real campaign evidence is useful but not gate-closing

The observed selection run now passes the earlier v10 predecessor failure and reaches the target-size training scheduler with the preserved candidate matrix. This is meaningful field evidence that the corrected compatibility path is directionally functional.

It does **not** replace bounded reproducible acceptance because the run does not independently prove the full negative matrix, restart/idempotence behavior, exact invalidation frontiers, anti-bypass integrity, or all A/B/C/D assembled claims.

### 2.3 Review-1 acceptance findings R4-R11 remain open

Unless explicitly refined by this amendment, Review-1 R4-R11 remain authoritative and unresolved. In particular:

- O24R-G2 real full-matrix positive acceptance remains open;
- O24R-G3 negative semantic compatibility matrix remains open;
- O24R-G4 real reopen/idempotence remains open;
- O23R anti-bypass remains open and has regressed because the previous guard was removed rather than broadened;
- O20R n1/n2/n3/n restart/invalidation frontiers remain open;
- O21R A/B/C/D1/D2/D3 assembled acceptance remains open;
- O18R durable prepare/preflight/DATA7/DATA8 reuse acceptance remains partial;
- O19R architecture/current-invariant regression remains partial;
- O22R same-candidate final affected-surface regression/integration remains open.

## 3. New runtime findings and frozen interpretation

### R12 - Boundary `3` in the observed run is configuration-dependent, not evidence that the product default reverted

The observed run begins with a target-size banner equivalent to:

```text
TARGET-SIZE-V5 boundary epoch 3
```

The current product default remains `(1,3,10)/30`. A campaign that explicitly persists/configures `(3,10,30)/30` is valid and must continue to execute boundary 3 first. Therefore implementation must **not** "fix" the observed run by hardcoding epoch 1 or silently rewriting an explicit campaign configuration.

The material product requirement is configuration authority and observability:

1. a fresh unmodified generated/default configuration must resolve to `(1,3,10)/30`;
2. an explicit `(3,10,30)/30` configuration must resolve to boundary 3 without being normalized to the default;
3. restart must use the authenticated persisted/effective configuration and must not infer a boundary from stale historical screen evidence;
4. command startup/status must make the effective fidelity tuple and full training horizon unambiguous enough to distinguish "configured old-style values" from "current default";
5. configuration changes must continue to trigger only the accepted invalidation frontier rather than upstream DATA7/DATA8 scientific rebuild when their true inputs are unchanged.

**Acceptance:** one fresh-default real-config case and one explicit-nondefault real-config case must pass through normal configuration normalization, store/restart ownership, target-size study construction, and next-operation authorization. The default case must authorize epoch 1; the explicit `(3,10,30)/30` case must authorize epoch 3.

### R13 - Live progress currently conflates active screen boundary and full schedule horizon

A line such as:

```text
phase=epoch 2/30
```

is compatible with the frozen same-trajectory design when the current screen boundary is 3 and the full schedule horizon is 30. The denominator `30` is therefore not itself a scheduling bug.

However, the live reporter should expose both concepts without forcing the operator to reconstruct them from separate messages. The implementation must preserve the full-`n` denominator while making the active exact screen endpoint visible in the live per-run status.

**Required end state:** live target-size training progress communicates both:

- current trajectory/schedule progress against `n`; and
- the active screen boundary `n1`, `n2`, or `n3` at which this command will stop/reduce.

Exact wording/formatting is delegated. A form semantically equivalent to `screen epoch 2/3; schedule epoch 2/30` is sufficient. Do not change training/schedule semantics merely to simplify reporting.

**Acceptance:** reporter tests cover at least default `(1,3,10)/30` and explicit `(3,10,30)/30`, and prove the boundary label is sourced from the active study/config rather than a hardcoded legacy constant.

### R14 - Duplicate DATA6 restoration appears within one selection invocation

The observed startup log restores the same DATA6 selection/difficulty/prediction/descriptor manifests, restores DATA4 mobile-state artifacts, and then appears to restore the same DATA6 sequence again before target-size scheduling.

This is not currently evidence of scientific recomputation or data corruption, but it is a material startup I/O/operability concern. Repeated restore/scanning of large immutable persisted products within one command should not occur when one authenticated restored representation can safely serve all consumers.

**Required investigation and corrected end state:**

1. trace the real `select-target-size` startup path and identify each DATA6 restore owner/consumer;
2. determine whether the apparent duplication is actual repeated disk restore/hash/deserialization work or only duplicate presentation of one cached operation;
3. if actual work is duplicated and the restored authority/content is identical, consolidate/reuse the owning restored state at the narrowest correct lifetime instead of suppressing only the log;
4. preserve DATA6/DATA4 integrity validation and fail-closed behavior; optimization must not bypass checksum/tree/content authority checks that are required for restart correctness;
5. do not introduce a second scientific cache/authority merely to avoid I/O; reuse the existing semantic owner or a process-local non-authoritative memoized restoration if justified;
6. do not trade the duplicate I/O for unbounded RAM retention. Any retained process-local restored state must remain within the existing resource budget and be releasable when no longer needed;
7. if two physically separate restores are proven necessary because the consumers require materially different authenticated representations/lifetimes, document that ownership and retain the minimum necessary reads rather than forcing deduplication.

**Acceptance:** add bounded instrumentation/regression that can distinguish one physical restore from two presentations and proves the corrected normal selection path does not perform redundant equivalent DATA6 restore work. No production-size benchmark or GPU qualification is required. A small persisted fixture is sufficient if it exercises the real restore owners and I/O path.

## 4. Remaining acceptance contract

### R3R-W2A.2 - Real complete predecessor-matrix positive acceptance

Retain Review-1 R4 exactly. Build a bounded real persisted immediate-predecessor campaign through production serialization/persistence and execute:

```text
real CampaignStore predecessor state
 -> real historical prepare/preflight compatibility
 -> real DATA8 discovery
 -> authenticated historical v8/v6 candidate authority
 -> real current target-size study construction
 -> predecessor/current compatibility owner
 -> complete expected candidate matrix validation
 -> real preflight/next-operation authorization
 -> configured n1 screening authorization
```

The fixture must contain the complete expected target-size candidate topology, naturally including n512 and n1024 rather than special-casing either variant. Physical MACE computation may be replaced only below the point where the real owner has authorized the run.

**Gate:** predecessor DATA8 remains byte/tree identical, one compatibility receipt is published only after the whole matrix validates, no historical screen/TRAIN2 evidence becomes current, and execution advances to configured `n1`.

### R3R-W2A.3 - Full fail-closed semantic compatibility matrix

Retain **every Review-1 R5 negative row**. Do not shorten this set to digest mismatch/missing evidence unit tests. Required rows continue to include REPAIR2, MVQUAL, candidate/prefix content, qualified-size set, missing/extra variants, topology/role, unsupported predecessor generation, ambiguous/missing evidence, inconsistent authenticated legacy digest, transitional flexible-v1 misclassification, current-generation mismatch, DATA8 bundle/tree corruption, and mixed predecessor/current bindings.

Each row must execute the real compatibility/matrix owner far enough that the intended semantic mismatch is the cause of rejection.

### R3R-W2A.4 - Real reopen/idempotence/current strictness

After successful complete-matrix bridge publication:

- close the real `CampaignStore`;
- reopen it;
- rediscover persisted production materializations through the normal owner;
- repeat compatibility/matrix/restart authorization;
- prove no scientific DATA7/DATA8 rewrite, duplicate receipt, repeated migration, or silent repair of corrupt/conflicting receipts;
- prove fresh/current authority mismatch remains strict after reopen.

A direct second call to the bridge helper with the same synthetic entry remains supplemental unit coverage only.

### R3R-W2A.5 / O23R - Restore and broaden anti-bypass protection

The implementation removed the previous AST anti-bypass guard. That is a direct regression against Review-1 R7.

Restore an anti-bypass acceptance guard that protects the **actual designated gate-closing acceptance set**, including O18R, all O20R frontier rows, A/B/C/D1/D2/D3, and O24R G2-G4. The mechanism may be AST-based or another simple repository-native structural check; the exact implementation is delegated.

The guard must fail if a gate-closing test replaces/bypasses the real semantic owner it claims to establish, including the forbidden substitutions already enumerated by Review 1. It must also reject use of direct `_invalidate_train2_downstream_state` invocation as O20 frontier acceptance.

Supplemental/unit tests remain free to mock these owners when they are not claimed as gate evidence.

**Gate:** all designated real-owner acceptance tests are protected; deleting/renaming a guard or acceptance test cannot silently convert a proxy test into accepted evidence.

### R3R-W2B - Genuine O20/O21 assembled acceptance

Retain Review-1 R8/R9 without relaxation.

#### O20R frontiers

For each independent change to `n1`, `n2`, `n3`, and `n`:

```text
authenticated persisted baseline
 -> edit actual TOML
 -> close store
 -> reopen through normal campaign command/reconciliation
 -> normal configuration identity detects change
 -> normal invalidation owner executes
 -> next-operation/status owner derives new frontier
```

Assert exact preserved and invalidated durable state, forensic retention, current tuple/horizon, next boundary, and full schedule horizon. Direct invalidation-helper calls do not count.

#### O21R A/B/C/D

- **A:** fresh default `(1,3,10)/30`, real preflight authorization, real persisted orchestration;
- **B:** nondefault `(2,5,12)/40`, same real owners;
- **C:** persisted `(1,3,30)/30` selected target-size authority flows into the real SIZE-FIDELITY consumer; semantic final-screen/reference roles remain distinct while the physical epoch-30 checkpoint is deduplicated;
- **D1:** authentic fixed predecessor -> default flexible fidelity through the corrected O24 bridge, real DATA8 matrix validation, restart/status, then `n1=1`;
- **D2:** authentic fixed predecessor -> `(2,5,12)/40`; old 30-horizon downstream schedule is rejected/invalidated and a new 40-horizon schedule is established without upstream scientific rebuild;
- **D3:** a true preparation-scientific change fails closed/reopens at the narrowest correct upstream preparation boundary using real preparation identity/receipt/restart owners.

Do not patch the semantic owners named in Review-1 R7 for these acceptance cases.

### R3R-W1 - O18 durable reuse closure

Complete O18R with one bounded real completed baseline carrying actual prepare receipt, preflight state, DATA7, and DATA8. Independently change each required downstream/execution/presentation-only field through real TOML/config normalization and prove normal restart/reuse preserves the upstream scientific products.

Include one true preparation-scientific inverse showing the narrowest correct upstream invalidation. Digest/projection-only tests remain supplemental.

### R3R-W3 - O19 architecture/current-invariant closure

Reconcile durable architecture/spec/current-invariant tests with the final assembled ownership model. Preserve at minimum:

- configurable fidelity/horizon authority and `0 < n1 < n2 < n3 <= n`;
- exact-boundary reduction on one full-`n` trajectory;
- policy-independent current candidate-prefix identity;
- authenticated immediate-predecessor-only bridge;
- production-materialization schema independence from candidate-authority generation;
- no historical downstream evidence relabeling;
- real persistent invalidation/restart frontiers;
- clear distinction between screen boundary and full schedule horizon in operator-visible behavior.

### R3R-W2C - Selection startup/observability closeout

This is a new bounded implementation stage introduced by Review 2.

1. close R12 fresh-default/nondefault configuration-authority and restart cases;
2. close R13 live boundary-vs-horizon reporting;
3. trace and close R14 duplicate DATA6 restore behavior;
4. run stage-local affected regression over campaign CLI startup/status/select, DATA6 restore/integrity/restart, target-size scheduling/reporting, and configuration normalization.

**Gate:** selection startup performs no unexplained redundant equivalent DATA6 restore work, reporting exposes the effective fidelity tuple/horizon and active boundary unambiguously, and no scientific/restart/resource invariant regresses.

W2C may be implemented after W2A authority acceptance or in parallel with W1 when the touched owners do not invalidate W2A evidence. Its final regression must be rerun if later changes touch the same startup/restore/reporting surfaces.

## 5. Final assembled acceptance: R3R-W4 / O22R

Do not close Rework 3 from unit tests or the observed field run alone.

On one final assembled commit:

1. reconcile every parent/Rework-3 obligation plus Review-1 and Review-2 amendments;
2. re-derive the final affected behavioral surface from the assembled diff rather than from the planned file list;
3. run focused checks for the modified mechanisms;
4. run all stage-local affected regression invalidated by later edits;
5. run final affected-surface regression;
6. run assembled integration through the real persistence/restart/authorization/compatibility/selection/SIZE-FIDELITY consumers;
7. run repository-required checks and the broader suite where the final impact cannot be bounded confidently;
8. record any unavailable environment-dependent checks explicitly, but do not substitute full GPU/production qualification for functional acceptance;
9. confirm no active acceptance test uses a forbidden owner substitution and O23 guard itself is present/green;
10. confirm the active workplan/amendments can be archived only after all material gates are actually green.

The user-run GPU/production qualification remains deferred until the complete final release package.

## 6. Expected affected surface

The final implementation may legitimately touch, as evidence requires:

- `mdstats/training_data/_campaign_cli_core.py` and campaign restart/status/select ownership;
- target-size authority/serialization only if needed to complete already-frozen acceptance, not to redesign the corrected R1-R3 mechanism;
- DATA6 restore/load/integrity owners reached by target-size selection startup;
- TRAIN2 progress/reporting/scheduler status surfaces;
- configuration template/normalization/status presentation;
- production materialization/DATA8 discovery validators where required for real complete-matrix acceptance;
- SIZE-FIDELITY real consumer path for case C;
- architecture/spec documentation affected by the final behavior;
- `tests/test_mlff_flexible_fidelity.py` plus whichever campaign/DATA6/materialization/restart/architecture test modules actually own the affected behavior.

Implementation must derive the real final affected surface rather than treating this list as a ceiling.

## 7. Forbidden shortcuts

The following do not satisfy this amendment:

- changing the software default back to `(3,10,30)` merely because the observed existing campaign begins at epoch 3;
- hardcoding the first boundary to 1 and thereby breaking explicit nondefault configurations;
- treating `epoch x/n` as proof that training will incorrectly run through `n` before reduction without checking the exact-boundary stop/reduction owner;
- hiding the full schedule horizon from progress output to make the reporter look simpler;
- suppressing duplicate DATA6 log lines while leaving duplicate restore/I/O work intact;
- caching restored DATA6 in a new persistent scientific authority independent of the existing store/integrity owner;
- rebuilding/deleting valid preserved DATA7/DATA8 solely to escape compatibility acceptance;
- accepting only one predecessor variant such as n512/n1024 rather than the complete expected matrix;
- using the same helper under test as the sole oracle for predecessor compatibility;
- counting direct bridge/invalidation/helper tests as real-owner acceptance;
- patching preflight, preparation identity, DATA8 discovery, target-size study, matrix validation, restart/status, schedule, or persistence owners in tests whose claims require those owners;
- deleting/renaming anti-bypass protection instead of satisfying it;
- using a production run or full GPU qualification as a substitute for bounded regression/integration acceptance.

## 8. Current gate state after Review 2

- **R3R-W2A.1:** source/product correction provisionally conformant; retain and regress.
- **R3R-W2A.2:** open; field run is positive evidence but bounded real complete-matrix acceptance missing.
- **R3R-W2A.3:** open.
- **R3R-W2A.4:** partial/open.
- **R3R-W2A.5 / O23R:** open and regressed because guard was removed.
- **R3R-W2B / O20R/O21R:** open.
- **R3R-W1 / O18R:** partial/open.
- **R3R-W3 / O19R:** partial/open.
- **R3R-W2C:** newly open for configuration/reporting/duplicate-restore closeout.
- **R3R-W4 / O22R:** blocked until all required prior gates close on the assembled candidate.
- **W5 archive/merge closeout:** blocked.

## 9. Reopen-design triggers

Return to Software Design only if implementation evidence shows that a frozen material decision itself is invalid, for example:

- exact configured boundary checkpoints cannot be obtained from one authenticated full-`n` trajectory without violating optimizer/scheduler continuity;
- candidate-prefix scientific identity is in fact materially dependent on downstream fidelity/horizon;
- authentic immediate-predecessor DATA8 cannot be proven scientifically equivalent without rewriting scientific data;
- the normal restart/invalidation ownership model cannot express the required n1/n2/n3/n frontiers without multiple competing authorities;
- eliminating duplicate restore work would require materially unsafe memory retention or weakening restart/integrity guarantees and no existing owner can be reused/refactored cleanly.

Ordinary missing tests, proxy acceptance, reporter ambiguity, duplicate I/O, or local implementation defects are **not** redesign triggers. They remain implementation work under Rework 3 and these amendments.
