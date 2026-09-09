---
kind: implementation-final-review
workplan_id: CODE-MLFF-DOWNSTREAM-INTEGRATION-CLOSURE-FINAL-REVIEW
parent_workplan_id: CODE-MLFF-DOWNSTREAM-INTEGRATION-CLOSURE
review_amendment_id: CODE-MLFF-DOWNSTREAM-INTEGRATION-CLOSURE-REVIEW-REOPEN-1
protocol_version: 6.0.0
status: passed
review_date: 2026-09-09
reviewed_executable_commit: 13859556cd4d472837a9e171c2be32e59d5e6d82
reviewed_executable_tree: bafa9cc93a38cef7f1c07ea668bc244d111cdcd8
review_verdict: pass
serious_challenge: none
closeout_disposition: archive parent workplan and review amendment; no executable changes
---

# MLFF downstream integration closure — Protocol 6 final review

## 0. Verdict

**PASS / CLOSED.**

Independent Software Design review under SSDP Protocol 6.0 accepts executable candidate `13859556cd4d472837a9e171c2be32e59d5e6d82` for the scope of the downstream MLFF integration-closure workplan.

The previous review had already closed all source-level blockers and left one open item only: final executed affected regression/integration evidence on the unchanged executable candidate. The stakeholder has now relayed the implementation agent's final execution report for that exact candidate. No executable source, test oracle, build configuration, or runtime machinery was changed after the reviewed executable candidate; the only repository changes after it are workplan/index documentation.

No Serious Challenge is active against D1 scientific formulation, D2 numerical method, or accepted D3 architecture. The closure remains a D3/D4 integration/recovery/currentness acceptance and does not mutate scientific or numerical authority.

## 1. Final executable evidence accepted

The final execution report states that the required Stage A and Stage B suites passed on the unchanged executable candidate, including the workplan-required P5 guards, MACE execution/configuration semantics, multi-size integration, assembled lifecycle, and P7 qualification paths.

It additionally reports successful affected-owner regression, storage-core coverage, exact downstream storage cases, structural/AST checks, Python compilation, Hypothesis coverage, architecture-document assembly, and PDF render verification.

This satisfies the final Protocol 6 implementation-acceptance requirement because the evidence covers the actual affected owners and consumers rather than substituting a helper-only proxy. The previously reviewed source already established that the acceptance tests exercise the real P5 materialization/recovery/TRAIN2 owner and the real dependency-facing `MacePostSelectionTrainer` owner with expensive numerical work bounded below those owners.

## 2. Reported limitations and disposition

### 2.1 Three stale `mace_compatibility` CLI-warning tests — non-blocking

Three pre-existing tests still fail because they assert removed/changed campaign CLI APIs rather than current MACE execution semantics. Earlier independent repository evidence already documented the same three stale failures against the pre-repair baseline and excluded them from the affected MACE execution-semantics partition while all remaining affected tests passed.

They are therefore existing test debt outside this workplan's executable change surface, not regression evidence against this candidate. They should be repaired or retired under their owning CLI/test-maintenance scope rather than by reopening this completed downstream integration repair.

### 2.2 Broad 167-test storage integration timeout — non-blocking

A broad storage integration diagnostic timed out under high-fanout xdist. The binding review amendment did not require that entire broad suite unconditionally; it required the affected P5 storage/run-activity-lease integration and broader storage only when impact could not be bounded confidently.

The implementation report states that the exact downstream storage cases passed and the 291-test storage core passed. Together with the already-reviewed bounded affected surface, this is sufficient functional evidence for the storage/recovery claims in this workplan. The xdist timeout is a resource/execution-shape limitation, not a demonstrated product failure.

### 2.3 P7 target-machine MLIAP callback skip — explicitly deferred

One P7 target-machine MLIAP test remains skipped because this host cannot execute the actual target callback. The workplan explicitly excluded full GPU/CuEq/LAMMPS/target-machine qualification from this implementation round. The skip therefore does not block functional D4 closure and must not be represented as completed GPU/LAMMPS qualification.

### 2.4 Serena and Semgrep limitations — acceptable bounded fallback

Serena had no configured project, so semantic navigation used bounded repository search/AST fallback. Full network-dependent Semgrep validation was unavailable because access to `semgrep.dev` was blocked; bounded local structural scanning and AST checks were used instead and reported no findings.

Protocol 6 permits such concrete fallbacks when the preferred tool surface is unavailable or cannot establish the claim economically, provided the engineering claim itself is not weakened. Here the structural/absence claims were already represented by bounded known-positive/known-negative AST/source checks, so tool unavailability does not leave an acceptance claim unexamined.

## 3. Closed governing claims

The following workplan claims are accepted as closed for this executable candidate:

- one canonical configured-path interpretation across the affected downstream campaign fields;
- foundation scientific identity remains content/head/family based while filesystem path is runtime-locator only;
- absolute, tilde, and config-relative foundation forms reach the same canonical P5 request and dependency-facing launch from a foreign CWD;
- byte-identical foundation relocation preserves method identity and execution after reauthentication; changed bytes/head fail closed;
- same-workspace pre-fix locator-only materialization can recover without manual deletion when no durable accepted continuation exists;
- corrupt/foreign completed materialization is preserved and rejected as typed failure;
- durable TRAIN2 continuation cannot rebuild absent/incomplete materialization beneath itself;
- continuation reuse is reconciled against completed current materialization and canonical MACE execution evidence before resume, full-horizon reclosure, or EVAL2;
- a foreign sibling continuation with an equal coarse `Train2RuntimePlan` is rejected before EVAL2/publication;
- replay source/split lineage remains path-free and the single-source replay adapter repair remains intact;
- multi-size CV completes every valid per-size verdict before campaign-level methodological rejection reduction;
- final-production admission remains collection-wide;
- P5 owns final publication/currentness while P7 remains a consumer;
- explicit P7 reference-root path semantics are canonical and CWD-independent;
- current architecture documentation is reconciled to frozen per-size production horizons, P5 publication ownership, ordinary-nonlocked qualification routing, explicit-only locked activation, and the multi-size terminal boundary;
- no new path registry, migration database, compatibility registry, materialization pointer, recovery state machine, cleanup daemon, second identity, or lock layer was introduced.

## 4. Challenge Pass and stabilization disposition

The final bounded Challenge Pass finds no material counterexample requiring reopening D1, D2, or D3. The realized recovery mechanism remains more complex than a trivial happy-path implementation, but that complexity is justified by the actual durable-state/restart contract and reuses the same canonical MACE execution authority for launch and continuation reconciliation rather than creating another authoritative state representation.

No further executable simplification is required by this workplan. If future recurrence appears around this recovery owner, reassess the shared D3/D4 mechanism under Protocol 6 convergence/stabilization rules instead of adding another compatibility layer automatically.

## 5. Closure and residual routing

This workplan is complete and may be archived together with its binding review amendment. `workplans/active/README.md` should no longer list this repair as active.

Residual items are explicitly outside this closure scope:

- stale campaign-warning CLI tests should be handled by the current CLI/test-maintenance owner;
- any xdist/storage scalability or timeout tuning should be handled only if it is independently useful, not as a condition of this closed repair;
- the skipped target-machine MLIAP callback and full GPU/CuEq/LAMMPS qualification remain part of the deferred final release qualification package.

No executable change is authorized or required by this final review.
