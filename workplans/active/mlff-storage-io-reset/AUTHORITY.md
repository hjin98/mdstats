---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 27
status: reopened
current_authority_pointer: AUTHORITY_REVISION_27.md
review_verdict: NO-PASS
---

# Storage/I-O reset package authority

This is the **sole canonical navigation entrypoint** for the active storage/I-O reset package.

Revision 19 storage architecture, Revision 21 final repair design, Revision 24 descriptor/root-identity repair design, and Revision 26 final realizable descriptor-pinned mutation/test-retirement design remain accepted. Revision 27 is a bounded implementation-review reopen of the Revision-26 implementation; it does not reopen P1-P7 science or the owner-driven storage architecture.

Reviewed executable:

```text
commit f8bd22fcb5d1b5b62246b0ca17653e6b31191a51
tree   928e9507ecac84040e1604ed5949f03440044740
```

Branch head `60b29f6992f088dd42f78b01424a9054c14e46a0` is a generated-PDF-only successor. Revision-27 commits after it are authority/workplan artifacts only.

## Current supplied contract

Read the still-binding supplied storage authority through Revision 26 together with:

- `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_8.md`;
- `AUTHORITY_REVISION_27.md`.

Earlier `current_authority_pointer` fields are historical metadata only; this entrypoint controls navigation.

## Review result

Substantial Revision-26 implementation is conforming and frozen for preservation:

- historical-only pytest/benchmark retirement and restored current fixtures;
- one descriptor-relative no-follow P7 namespace/state/proof/topology observation consumed by `qualification_views()`;
- descriptor-relative exact proof/topology certification and generation-scoped root binding;
- P7-specific fd-relative file/directory mutation primitives compatible with Python >=3.10;
- corrected wrong-root, basename-only-proof, nested-mount, and public-path-swap counterfactuals;
- updated current storage specification.

The executable remains **NO-PASS** for three bounded groups:

1. the apply resnapshot certifies P7 state/proof/topology on an attempt descriptor which is closed before mutation; the final remover then reacquires a new descriptor, checks root inode identity, and consumes the earlier snapshot's certified nodes. Revision 26 requires fresh final certification and mutation on the same retained attempt descriptor;
2. `remove_released_attempt_member(...)->False` is appended to `completed_actions`, so `StorageExecutor._settle()` can report `complete` for a mutation the P7 owner actually refused. Refused no-op outcomes must enter `refused_actions`, yielding `refused` or `partial` as appropriate;
3. current tests do not prove those exact seams, and exact executable candidate functional evidence remains absent. GitHub exposes only the successful `docs` check for `f8bd22f...`.

## Bounded rework route

```text
IR27-1  final same-descriptor P7 reacquisition + state/proof/topology certification + mutation
   -> IR27-2 truthful refused/completed action accounting
   -> IR27-3 proxy-proof final seams
   -> R21-E5/F exact-candidate affected regression/integration evidence
```

Do not redesign or rework conforming R26-T1 cleanup, single P7 observation, fd-relative mutation primitives, CampaignStore, P5 typed proof, archive/dedup/restore/control-plane machinery, or P1-P7 scientific/currentness semantics.

Whole-repository behavioral pytest remains conditional as frozen by Revision 26. Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and nonblocking.

**Design/workplan disposition:** **CLOSED / implementation-ready under Revision 26.**

**Executable disposition:** **NO-PASS / reopened under Revision 27.**
