---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 25
status: reopened
current_authority_pointer: AUTHORITY_REVISION_25.md
review_verdict: NO-PASS
---

# Storage/I-O reset package authority

This is the **sole canonical navigation entrypoint** for the active storage/I-O reset package.

The **Revision-19 storage architecture and Revision-21 final repair design remain accepted**. Revisions 22 and 23 are bounded implementation-review reopens. Revision 24 is the accepted final repair-plan closure. Revision 25 is a bounded independent implementation-review reopen of the Revision-24 implementation and does not reopen P1-P7 science or the owner-driven storage architecture.

The reviewed executable is:

```text
commit 8e87bc863be2470fb602a9cbb2ac411b7bc83bc4
tree   7becdd8918f4125ed69442fa07e95ed412560566
```

Branch head `8c96180617e5ce38c476d68804155c5bf2a85501` is a generated-PDF-only successor and does not change the functional review target.

## Current supplied contract

Read the still-binding supplied storage authority set through Revision 24 together with:

- `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_7.md` (Revision 25);
- `AUTHORITY_REVISION_25.md`.

Earlier `current_authority_pointer` fields inside superseded artifacts are historical metadata only; this `AUTHORITY.md` entrypoint controls navigation.

The frozen parent target-size V7 workplan remains the scientific/architectural verdict. Storage repair must not reopen target-size, CV, publication, qualification, calibration, locked-test, reference, or release science for convenience.

## Review result

Substantial Revision-24 work is conforming and must be preserved:

- descriptor-relative strict P7 attempt-state census;
- exact absence-versus-namespace-change/ambiguity classification;
- malformed-state parser totality with observational report availability;
- generation-scoped v3 released-attempt root locator derived from authoritative P7 generation state;
- cross-generation copied-attempt refusal;
- workspace-wide unknown-attempt retention reduction;
- deterministic P7 attempt-state synchronization and one serializer including `attempt_roots`;
- the earlier CampaignStore and specification repairs.

The executable remains **NO-PASS** for four blocking groups:

1. `qualification_views()` and released-proof certification still rediscover the P7 attempt hierarchy through pathname APIs after the strict descriptor census, so the strict result is not yet the single end-to-end storage-facing namespace/proof authority;
2. final released-scratch mutation still separates the last `(device,inode)` check from the pathname destructive syscall, and proof-certified top-level regular files bypass the P7 root-continuity mutation check entirely;
3. several new tests are not proxy-proof for the claimed invariant: the wrong-root state also violates canonical binding-derived identity, the basename-only proof is self-digest-invalid, the nested-mount fixture is already invalidated by an unrecorded proof node, and the final-removal race fires before the last identity check rather than after it;
4. exact-candidate functional evidence is still absent: GitHub exposes only a successful `docs` check for executable `8e87bc8...`, not the required focused/storage/integration/affected regression runs.

## Bounded rework route

Resume at **R21-E2** under `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_7.md`:

1. consolidate P7 attempt-facing view/proof/certification onto the descriptor-bound owner result with no followable parallel rediscovery;
2. preserve expected attempt-root/member identity to the actual destructive primitive for every released file/directory action, or truthfully refuse when the platform cannot do so;
3. repair the proxy-proof counterfactuals and narrow structural absence guard;
4. complete R21-E5/F exact-candidate affected regression/integration evidence after final affected-surface re-derivation.

Do not redesign conforming CampaignStore, archive/dedup/restore, P5 typed proof, P7 scientific/currentness, or storage-control-plane machinery.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and are not functional-acceptance blockers.

**Design/workplan disposition:** Revision 24 remains **CLOSED**; Revision 25 is bounded implementation rework authority.

**Executable disposition:** **NO-PASS / reopened under Revision 25**.