---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 28
status: reopened
current_authority_pointer: AUTHORITY_REVISION_28.md
review_verdict: NO-PASS
---

# Storage/I-O reset package authority

This is the **sole canonical navigation entrypoint** for the active storage/I-O reset package.

Revision 26 remains the accepted storage architecture/mutation/test-retirement basis. Revision 28 is the current final bounded implementation handoff and supersedes Revision-27 shorthand where that shorthand was incomplete. No P1-P7 science or owner-driven storage architecture is reopened.

Reviewed executable remains:

```text
commit f8bd22fcb5d1b5b62246b0ca17653e6b31191a51
tree   928e9507ecac84040e1604ed5949f03440044740
```

All later Revision-27/28 commits are workplan/authority artifacts only unless an executable successor is supplied for review.

## Current supplied contract

Read the still-binding Revision-26 storage authority/specification set together with:

- `STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_REVISION_28.md`;
- `AUTHORITY_REVISION_28.md`.

Earlier `current_authority_pointer` fields are historical metadata only; this `AUTHORITY.md` controls navigation.

## Revision-28 final corrections

### 1. Plan-bind the exact released P7 authority

Certified released P7 scratch must expose a derived owner state identity from the authenticated attempt state plus authenticated v3 released proof, using the existing plan/owner-state binding machinery rather than a new registry. Final apply re-derives that identity on its retained attempt descriptor and refuses a mismatch.

### 2. Final P7 certification and mutation share a live descriptor capability

Under the established storage/P5/P7 synchronization, final apply strictly reacquires the attempt, keeps that descriptor alive, authenticates current state, proof, and typed topology on it, checks the plan-bound authority/root/target constraints, and mutates only relative to that descriptor/no-follow child descriptors. Planning/resnapshot `certified_nodes` are not final destructive authority.

Proxy evidence must prove descriptor **lifetime continuity**, not only equality of integer fd values, because a closed descriptor number may be reused.

### 3. Released topology may shrink monotonically

The released proof is an upper bound on owner-authored topology during cleanup. Every observed live node must still be proof-recorded with the exact kind. Missing proof-recorded nodes are allowed so earlier actions and interrupted cleanup do not self-stale. New nodes, kind changes, substituted roots, symlinks/special nodes, nested mounts, or changed release authority refuse. An already-absent target is terminally satisfied with zero reclaimed bytes.

### 4. Mutation outcomes are structured and truthful

A boolean removal result cannot distinguish a no-change refusal from a partial mutation followed by refusal. Cleanup removal paths must distinguish, with equivalent internal naming allowed:

```text
removed
already_absent
refused_no_change
partial_change_refused
```

This applies to the P7 released-member remover, common certified-subtree removal, and generic cleanup removal wherever current normal returns can represent absence/refusal/partial change. Reason-string parsing may not determine outcome semantics.

`removed` credits only attributable removed bytes; `already_absent` credits zero; `refused_no_change` is a refused action with zero bytes; `partial_change_refused` makes the execution partial even when it is the only action and may credit only substantiated removed bytes, never the full planned size by default.

## Acceptance

Use the real storage executor, real synchronization, real P7 owner, and real descriptor-relative mutation. Preserve the corrected R26 wrong-root, basename-only-proof, nested-mount, cross-generation, public-path-swap, interruption, and historical-test cleanup work.

Add focused evidence for valid-but-different state/proof authority identity, capability lifetime continuity, invalid final state/proof/topology, file and directory targets, monotonic multi-action shrink, interrupted retry, unsupported dir-fd refusal, already-absent zero-byte success, mixed success/refusal partial status, and partial recursive mutation followed by refusal.

After the final executable edit, run focused R22-R28 tests, full storage core/integration, affected current-owner P1/P3/P4/P5/P7 plus P6 destructive/current-lifecycle regressions, clean collection, final affected-surface re-derivation and fresh affected regression/integration, and static/affected current-doc validation on the exact candidate. Whole-repository behavioral pytest remains conditional on unbounded impact or independent repository policy. External-DFT, long GPU, and environment-specific HPC/storage qualification remain deferred and nonblocking.

## Route

Treat the remaining repair as one coherent final-apply behavior stage:

```text
plan-bound released authority
 + retained descriptor certification/mutation
 + monotonic shrink semantics
 + truthful structured mutation outcomes
 -> proxy-proof focused + affected regression
 -> final affected-surface re-derivation
 -> fresh affected regression/integration + static/docs validation
```

Do not redesign conforming R26 test retirement, single P7 observation, fd-relative primitives, synchronization, CampaignStore, P5 typed proof, archive/dedup/restore/control-plane machinery, or P1-P7 scientific/currentness semantics.

**Design/workplan disposition:** **CLOSED / implementation-ready under Revision 28.**

**Executable disposition:** **NO-PASS / reopened under Revision 28.**
