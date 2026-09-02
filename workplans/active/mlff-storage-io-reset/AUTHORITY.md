---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 29
status: reopened
current_authority_pointer: AUTHORITY_REVISION_29.md
review_verdict: NO-PASS
---

# Storage/I-O reset package authority

This is the **sole canonical navigation entrypoint** for the active storage/I-O reset package.

Revision 26 remains the accepted storage architecture/mutation/test-retirement basis. Revision 28 remains the accepted final repair design for plan-bound released authority, live descriptor capability, monotonic proof shrink, and structured mutation outcomes. Revision 29 is a bounded implementation-review reopen of the executable realization; it does not reopen P1-P7 science or the owner-driven storage architecture.

Reviewed executable:

```text
commit 6423a3f33a36c09ca1b89f5740f42c402b1993d2
tree   a40bdf7cbd4bc1e2a2de4ec41ccb77fede4dc926
```

The reviewed branch head `106081269735c27c862c174e18cb1ffaa3820382` is a generated-PDF-only successor and does not alter the executable verdict.

## Current supplied contract

Read the still-binding Revision-26 storage authority/specification set together with:

- `STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_REVISION_28.md`;
- `AUTHORITY_REVISION_28.md` for the accepted final repair design;
- `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_9.md` for the exact remaining implementation findings;
- `AUTHORITY_REVISION_29.md` for the current bounded rework authority.

Earlier `current_authority_pointer` fields are historical metadata only; this `AUTHORITY.md` controls navigation.

## Revision-29 bounded implementation corrections

Preserve the conforming Revision-28 implementation: exact released-authority plan binding, `ReleasedAttemptSession`, proof-as-upper-bound monotonic shrink, the four-outcome `MutationOutcome` model, descriptor-relative no-follow mutation, corrected R26/R28 counterfactuals, synchronization, and specification updates.

Close only these remaining surfaces:

1. a mutation-time P7 refusal/partial contradiction invalidates that attempt's live capability for the remainder of the execution; later same-attempt actions are refused without mutation, while `removed`/`already_absent` may continue;
2. materialize the authenticated `{path: kind}` proof lookup once per ephemeral attempt session instead of rebuilding the whole mapping per member;
3. propagate exact measured nested-removal bytes under the existing storage/inode metric so later partial outcomes neither drop removed subtrees nor claim full planned size;
4. once a destructive transition has occurred, any later exception/durability failure must expose structured partial-mutation truth and substantiated bytes to the executor/audit before error propagation can discard them; pre-mutation failures must fabricate nothing;
5. add real-executor/real-P7-owner counterfactuals for resealed release authority, final state/proof/topology damage, mixed success/refusal, partial recursive mutation, same-attempt invalidation, post-mutation versus pre-mutation exception behavior, returned execution status/collections/bytes, and durable audit truth;
6. after the final executable edit, record exact-candidate focused R22-R29, full storage core/integration, affected P1/P3/P4/P5/P7 + P6 current-lifecycle regressions, clean collection, final re-derived affected regression/integration, and static/current-doc validation.

Whole-repository behavioral pytest remains conditional on inability to bound the final affected surface or independent repository policy. External-DFT, long GPU, and environment-specific HPC/storage production qualification remain deferred and nonblocking.

## Route

```text
same-attempt contradiction invalidation
 + one proof lookup per session
 + exact nested partial-byte propagation
 + post-mutation exception truth
 -> real-owner proxy-proof tests
 -> affected regression
 -> final affected-surface re-derivation
 -> exact-candidate regression/integration + static/docs evidence
```

**Design/workplan disposition:** **CLOSED / implementation-ready under Revision 28 plus the bounded Revision-29 implementation corrections.**

**Executable disposition:** **NO-PASS / reopened under Revision 29.**
