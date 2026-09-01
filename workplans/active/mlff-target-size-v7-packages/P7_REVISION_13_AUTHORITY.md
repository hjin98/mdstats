---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
protocol_version: 5.8.0
revision: 13.2
status: reopened
reviewed_implementation_commit: cc098c18b39bbfdc65be6d5266fc2582d9bc9e01
reviewed_implementation_tree: 918d7670a6441a5431c95313c452499387b5ec60
review_verdict: NO-PASS
current_amendment: P7_REVISION_13_2_IMPLEMENTATION_REVIEW_RUNTIME_GATE_REOPEN_AMENDMENT.md
current_review_evidence: P7_REVISION_13_2_REVIEW_EVIDENCE.md
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
---

# P7 revision 13.2 — authoritative reopened workplan

The frozen parent `MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the controlling scientific and architectural verdict.

Independent Software Design review of P7A3 at executable commit
`cc098c18b39bbfdc65be6d5266fc2582d9bc9e01`, tree
`918d7670a6441a5431c95313c452499387b5ec60`, is **NO-PASS**.

P7A3 materially closes the broad revision-13 source repair set. The current reopen is intentionally narrow: preserve the accepted stress/provenance, resource-lineage, static-PBC, release-graph, and selected-worker repairs; remove the remaining generic runtime-preflight authority that can suppress the selected semantic KOKKOS/MACE worker; then execute the mandatory real B11 and B12 target-machine release gates on one newly frozen executable candidate.

## Current authority precedence

Read P7 as one composed authority in this order:

1. frozen parent scientific workplan — controlling verdict;
2. accepted/reclosed predecessor P1-P6 authorities, including the revision-11 P5 publication-decision repair and affected P6 rebind;
3. `P7_REVISION_13_2_IMPLEMENTATION_REVIEW_RUNTIME_GATE_REOPEN_AMENDMENT.md` — current residual implementation and closure authority;
4. `P7_REVISION_13_B11_KOKKOS_MACE_RUNTIME_CORRECTION_AMENDMENT.md` — binding B11 semantic runtime owner/lifecycle contract where revision 13.2 does not narrow or clarify it;
5. `P7_REVISION_13_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` — binding where accepted/unsuperseded;
6. `P7_REVISION_12_FINAL_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` — binding where later revisions do not preserve/clarify/supersede it;
7. `P7_REVISION_11_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` — binding where later revisions do not supersede it;
8. `P7_REVISION_10_IMPLEMENTATION_REALIGNMENT_AMENDMENT.md` — implementation-state architecture except where later revisions supersede it;
9. `P7_POST_PRODUCTION_QUALIFICATION_REPLACEMENT.md` — base qualification science/no-fallback contract except stale predecessor assumptions already superseded;
10. `P7_REVISION_2_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md` — storage-neutral successor handoff;
11. revisions 3-9 — historical predecessor-entry alignment records.

`P7_REVISION_13_2_REVIEW_EVIDENCE.md` records the independent review of P7A3. Earlier implementation/review evidence remains historical and does not establish closure for this candidate.

## Accepted P7A3 source surfaces — preserve

These previously reopened source surfaces are now accepted and MUST NOT be redesigned absent contradictory evidence:

- **R13-B9A:** stress capability is component/member/claim/geometry scoped; committee order/member-0 no longer owns the decision; exact capability sets participate in relevant component input identity before reuse.
- **R13-B9B:** applicable trained stress fails closed when required runtime/reference evidence is missing; external-reference stress authenticates raw source representation, units, sign, order, virial-volume semantics where applicable, canonicalization provenance, and canonical tensor.
- **R13-B7:** resource observations form an immutable resumable predecessor chain with cumulative timings/samples, explicit locked timing, stable resource-scope material, selected-device telemetry, and reserve-plus-bounded-write-headroom admission.
- **R13-B13:** static and dynamics runtime evidence preserve exact three-axis PBC; static execution additionally returns and verifies post-build cell against the authenticated request.
- **R13-B14:** public terminal/release exposure authenticates resource-observation lineage and release-index -> single terminal-record referential integrity.
- **R13.1 worker mechanics:** selected KOKKOS arguments reach the child LAMMPS instance, mliappy is activated on that exact instance, actual MACE callback execution returns structured evidence, abnormal child failure cannot publish success, and external Python finalization is not invoked.

The fixed R12 LAMMPS bar/pressure-sign source adapter, accepted R11 publication/currentness/reference/locked owners, exact target-head identity, no committee shrinkage/fallback, and P1-P6 science remain binding.

## Residual blockers

P7 remains reopened for exactly these current blockers:

### R13.2-B11A — generic runtime preflight still owns a semantic veto

P7A3 demotes static `forward_exchange` introspection, but the runtime still performs a separate generic/default LAMMPS probe and uses `supports_deployed_execution` through `_require_supported_runtime()`, `execute_lammps_request()`, deployment-parity pre-gating, and deployment stress/currentness logic before the selected KOKKOS/MACE worker has executed.

A generic preflight may remain diagnostic, but it may not suppress, reinterpret, or stale the selected product execution. The exact selected worker is authoritative for product runtime availability/evidence. Scientific stress applicability remains training/member/geometry owned; when applicable, the selected worker must be asked for stress and missing/invalid stress fails closed.

The precise source end state and mandatory tests are specified by the revision-13.2 amendment.

### R13.2-B11B — real current-publication product execution is not closed

After B11A repair and fresh affected regression/integration, freeze a new executable candidate. Then execute the **actual current durable P5 publication member bytes** through the production P7 owner:

```text
current P5 publication/member bytes
 -> real mdstats target-head exporter
 -> real canonical-head LAMMPS_MLIAP_MACE artifact
 -> exact selected qualification resource scope
 -> selected KOKKOS LAMMPS child + mliappy
 -> actual MACE callback/message passing
 -> E/F + applicable stress + exact PBC/cell
 -> frozen deployment-parity comparison
 -> clean structured worker completion
```

A synthetic fixture, construction-only check, direct helper bypass, or hardware skip does not close B11.

### R13.2-B12 — final target-machine release qualification is not closed

On the exact same frozen candidate that passes B11B, execute the final real-reference target qualification, all mandatory nonlocked components, cumulative target-machine resource evidence, explicit one-shot locked activation/result, immutable terminal record/release index, and process-restart close/reopen authentication of the complete publication/product/component/resource/reference graph.

No executable source change is permitted between freeze and accepted B11B/B12 evidence. A source defect found during the real run requires repair, fresh affected regression/integration, and a new freeze.

## Binding implementation sequence

```text
R13.2-P1  remove/demote generic runtime preflight veto and generic-probe stress/currentness coupling
R13.2-P2  fresh focused + complete affected R11/R12/R13 regression/integration
R13.2-P3  freeze a new executable candidate commit/tree
R13.2-P4  actual current-publication selected-KOKKOS MACE E/F/applicable-stress parity
R13.2-P5  final target-machine real-reference qualification + one-shot locked closure on the same candidate
R13.2-P6  close/reopen terminal/release/resource/reference graph and record exact evidence identities
R13.2-P7  independent Software Design closure review
```

## Closure gate

P7 may receive PASS only when all of the following are true on one final executable candidate:

1. R13.2-B11A is source- and test-closed and no generic preflight owns selected product availability, stress applicability, or component currentness.
2. Accepted P7A3 R13-B9A/B9B/B7/B13/B14 and all preserved R11/R12 surfaces remain green under fresh affected regression/integration.
3. Exact current durable P5 publication member execution succeeds through the selected KOKKOS/mliappy MACE owner with E/F/applicable-stress parity and clean worker completion.
4. Final target-machine real-reference qualification succeeds on that same candidate.
5. One-shot locked activation/result succeeds and is crash/reopen safe.
6. Terminal record, release index, cumulative resource observations, component evidence, publication/product identities, and external-reference descendants all reauthenticate current after process restart.
7. Independent Software Design review finds no remaining genuine blocker.

Until then P7 remains **REOPENED / NO-PASS** and `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` remains blocked.
