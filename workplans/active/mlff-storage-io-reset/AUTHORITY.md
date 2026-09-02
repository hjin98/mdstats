---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 26
status: reopened
current_authority_pointer: AUTHORITY_REVISION_26.md
review_verdict: NO-PASS
---

# Storage/I-O reset package authority

This is the **sole canonical navigation entrypoint** for the active storage/I-O reset package.

The **Revision-19 storage architecture and Revision-21 final repair design remain accepted**. Revision 24 remains the accepted descriptor/root-identity repair design. Revision 25 remains the bounded implementation-review finding set except where Revision 26 explicitly corrects its over-constrained final-mutation wording and refines final acceptance. Revision 26 also adds the requested current-authority cleanup of historical executable tests, fixtures, helpers, and dead benchmark drivers. None of this reopens P1-P7 science or the owner-driven storage architecture.

The reviewed executable remains:

```text
commit 8e87bc863be2470fb602a9cbb2ac411b7bc83bc4
tree   7becdd8918f4125ed69442fa07e95ed412560566
```

The Revision-25/26 commits after that executable are workplan/authority artifacts only.

## Current supplied contract

Read the still-binding supplied storage authority set through Revision 25 together with:

- `STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_REVISION_26.md`;
- `AUTHORITY_REVISION_26.md`.

Earlier `current_authority_pointer` fields inside superseded artifacts are historical metadata only; this `AUTHORITY.md` entrypoint controls navigation.

The frozen parent target-size V7 workplan remains the scientific/architectural verdict. Storage repair must not reopen target-size, CV, publication, qualification, calibration, locked-test, reference, or release science for convenience.

## Revision-26 closure

### 1. Single descriptor-bound P7 authority remains mandatory

Revision-25 §1 remains binding: storage-facing P7 view/proof/member certification must consume one descriptor-bound no-follow namespace authority. `qualification_views()` may not re-enumerate `qualification/gN/attempts/<attempt>` through a parallel `Path.is_dir()` / `iterdir()` / `glob()` path after the strict census.

### 2. Final mutation is descriptor-pinned and fd-relative

Revision-25's concern was valid but its inode-CAS-like wording is superseded.

Under the accepted storage/P5/P7 owner locks, consequential P7 cleanup must freshly reacquire the strict namespace and keep the authenticated attempt-directory descriptor alive through exact proof/member certification and mutation. Released top-level files and recursive directories are mutated relative to authenticated descriptors with no-follow semantics. Python `>=3.10` remains supported; where later `shutil.rmtree(dir_fd=...)` support is unavailable, use a bounded owner-specific descriptor-relative recursion from supported `os` dir-fd operations. If a platform cannot preserve the no-follow/dir-fd boundary, refuse rather than fall back to unauthenticated path traversal.

The product guarantee is descriptor-pinned owner ancestry and fd-relative mutation under supported-owner synchronization, not an impossible kernel inode compare-and-delete promise against an arbitrary external same-UID process racing the final syscall.

### 3. Historical test/tool debt is now explicit implementation work

Classify the executable suite against current architecture/specification owners and explicitly supported compatibility code, not against historical gate chronology.

Confirmed historical-only retirement includes the Revision-26 list of:

- adaptive/conventional-CV revision-plan chronology tests;
- MVSTATE-REUSE1 and FEAS1 PERF1/2/3 historical specification tests;
- retired MLCV AGG1/FINAL1/MIGRATE1/VERIFY1 specification tests;
- the historical DATA9A7d migration-spec snapshot while retaining current profile-runtime tests;
- retired multi-view legacy/oracle helpers and the dead MVQUAL benchmark wrapper;
- executable MVQUAL/MVSEL2/MVKERNEL benchmark drivers importing P6-deleted owners;
- orphan pre-V7 fixtures after confirming no retained current consumer.

The implementation must also exhaustively audit `tests/` and executable `benchmarks/**/*.py` for P6-retired imports/symbols, stale historical current-package pins, non-current spec/history-only assertions, missing-fixture references, dead benchmark tooling, and orphan support files.

Do **not** bulk-delete by filename. Preserve/consolidate current precision, DATA1 sampling, online-monitor, DATA8 MLCV-monitor, adaptive-stop, current profile-extension, campaign-CLI/current-architecture, and P6 destructive-closure behavior. Explicit adaptive-stop v1/v2 schema support is a live compatibility contract and remains tested.

The cleanup stage closes with clean `pytest --collect-only -q`, retained current-owner regression, and the P6 destructive-closure guard—not by converting old failures into blanket skips.

### 4. Final acceptance is affected-surface based

Mandatory final candidate evidence is:

1. all focused Revision-22 through Revision-26 P7 counterfactuals;
2. full `tests/test_mlff_storage_reset_core.py`;
3. full `tests/test_mlff_storage_reset_integration.py`;
4. affected current-owner P1/P3/P4/P5/P7 regressions plus P6 destructive/current-lifecycle consumers implicated by the common storage path;
5. clean default-suite collection after historical cleanup;
6. final affected-surface re-derivation and fresh affected regression/integration on the assembled candidate;
7. repository static and affected current-spec/document validation.

Whole-repository behavioral pytest is mandatory only when the final affected surface cannot be bounded confidently or an independent repository/release policy requires it. It remains useful broad evidence but is not a ceremonial storage gate and cannot substitute for focused/current-owner acceptance.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and are not functional-acceptance blockers.

## Rework route

```text
R26-T1  current-authority test/tool retirement + clean collection
   -> R25-P7 single descriptor-bound P7 view/proof/certification
   -> R26-M fd-relative released-file/directory mutation
   -> corrected proxy-proof counterfactuals
   -> R21-E5/F exact-candidate affected regression/integration
```

Do not redesign conforming CampaignStore, P5 typed proof, archive/dedup/restore/control-plane architecture, or P1-P7 scientific/currentness semantics.

**Design/workplan disposition:** **CLOSED / implementation-ready under Revision 26.**

**Executable disposition:** **NO-PASS / reopened under Revision 26** until the Revision-25/26 implementation and exact-candidate evidence close.