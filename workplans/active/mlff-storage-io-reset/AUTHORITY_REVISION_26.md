---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 26
status: reopened
supersedes_revision: 25
reviewed_plan_head: c36939867a4df785c106b14575cb1fe127e83827
reviewed_plan_tree: c19dd8df6fc30acfad89893217262d423e989682
reviewed_executable_commit: 8e87bc863be2470fb602a9cbb2ac411b7bc83bc4
reviewed_executable_tree: 7becdd8918f4125ed69442fa07e95ed412560566
repair_plan_closure: STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_REVISION_26.md
design_disposition: closed-implementation-ready
executable_disposition: no-pass-reopened
---

# Storage/I-O reset authority — Revision 26

Revision 26 is the current implementation handoff. It preserves Revision 19/21/24 storage architecture and the valid Revision-25 implementation findings, while correcting one over-constrained mutation requirement and adding the requested cleanup of executable historical test/tool debt.

## 1. What remains binding from Revision 25

The following Revision-25 findings remain blocking until implemented and evidenced:

- `qualification_views()` / released-attempt proof/member certification must consume one descriptor-bound P7 storage-facing namespace authority rather than rediscover `qualification/gN/attempts/<attempt>` through followable pathname APIs;
- malformed state, canonical generation spelling, generation-scoped v3 proof binding, cross-generation copy refusal, workspace-wide unknown-state retention, and deterministic owner synchronization remain as already accepted;
- the wrong-root state, basename-only proof, nested-mount, final-mutation race, and structural-absence tests must be proxy-proof rather than pass for an earlier unrelated failure;
- exact-candidate functional evidence remains required after the final executable edits.

## 2. Revision-25 final-mutation wording is replaced

Revision 25 correctly rejected `lstat(expected) -> absolute-path rmtree`, but it described the desired repair too much like an atomic inode compare-and-delete primitive. That is not the product contract supplied by the supported POSIX/Python interface.

The frozen Revision-26 contract is:

- under the accepted storage/P5/P7 owner locks, freshly reacquire the strict P7 namespace;
- keep the authenticated **attempt-directory descriptor** alive across exact proof/member certification and mutation;
- never re-resolve the authenticated generation/`attempts`/attempt ancestry by pathname after authority is established;
- mutate proof-certified top-level files relative to the retained attempt descriptor;
- recursively delete certified directories using no-follow descriptor-relative descent and fd-relative unlink/rmdir operations, including on supported Python 3.10;
- preserve typed-node, symlink/special-node, nested-mount, cross-generation, durability, and fail-closed namespace-change semantics;
- refuse on platforms that cannot provide the required no-follow/dir-fd boundary rather than silently falling back to path traversal.

The guarantee is **descriptor-pinned owner ancestry and fd-relative mutation under supported-owner synchronization**, not an impossible claim that the kernel conditionally unlinks a directory entry only if its inode equals an earlier observation while an arbitrary external same-UID process races the exact syscall.

The real-owner counterfactual must prove that replacing public generation/attempts/attempt names cannot transfer the original authority to the replacement, for both top-level regular files and directory scratch.

## 3. Historical test/tool cleanup is part of this implementation

The current specification index and P6 destructive cutover are the governing classification evidence. Historical release/gate/migration documents do not become current product semantics merely because a pytest still references them, and unsupported pre-V7 target-size/lifecycle artifacts are reject/reprepare rather than a default compatibility requirement.

### Confirmed whole-retirement floor

Remove the historical-only live pytest/tool surfaces enumerated by Revision 26, including:

- adaptive/conventional-CV revision-plan chronology tests;
- MVSTATE-REUSE1, FEAS1 PERF1/2/3, retired MLCV AGG1/FINAL1/MIGRATE1/VERIFY1 specification snapshots;
- the historical DATA9A7d migration-spec snapshot (while preserving its separate current profile-runtime test);
- retired multi-view legacy fixture/oracle helpers;
- the dead MVQUAL benchmark unit wrapper;
- executable MVQUAL/MVSEL2/MVKERNEL benchmark drivers which import P6-deleted owners;
- orphan pre-V7 fixtures after confirming no retained current consumer.

Implementation must also audit the rest of `tests/` and executable `benchmarks/**/*.py` for P6-retired imports, stale old-current-version assertions, non-current spec/history-only checks, missing-fixture references, dead benchmark drivers, and orphan support files.

### Preserve current behavior from mixed files

Do not bulk-delete historical-looking files. Preserve or consolidate live assertions for current precision APIs, DATA1 sampling, online monitors, DATA8 MLCV monitors, active adaptive-stop behavior, explicitly supported v1/v2 adaptive-stop schema compatibility, current profile-extension behavior, the current campaign CLI/current architecture tests, and P6 destructive-closure absence guards.

Broad skip conversion is not cleanup. The cleaned suite must collect truthfully.

## 4. Acceptance after cleanup

Mandatory candidate-bound storage acceptance is:

1. all focused Revision-22 through Revision-26 P7 counterfactuals;
2. complete `tests/test_mlff_storage_reset_core.py`;
3. complete `tests/test_mlff_storage_reset_integration.py`;
4. affected current-owner P1/P3/P4/P5/P7 regressions plus the P6 destructive-closure/current lifecycle consumers implicated by the common storage path;
5. `pytest --collect-only -q` after historical test/tool cleanup;
6. final affected-surface re-derivation followed by a fresh affected regression/integration pass;
7. repository static and affected current-spec/document validation.

A whole-repository behavioral pytest remains useful broad evidence but is **mandatory only when the final affected surface cannot be bounded confidently or an independent repository/release policy requires it**. It is not a ceremonial storage gate and cannot substitute for the focused/current-owner acceptance above.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and are not functional-acceptance blockers.

## 5. Route

```text
R26-T1  current-authority test/tool retirement + clean collection
   -> R25-P7 single descriptor-bound P7 view/proof/certification
   -> R26-M fd-relative released-file/directory mutation
   -> corrected proxy-proof counterfactuals
   -> R21-E5/F final exact-candidate affected regression/integration
```

Do not reopen conforming CampaignStore, P5 typed proof, archive/dedup/restore/control-plane design, or P1-P7 scientific/currentness semantics.

**Design/workplan:** **CLOSED / implementation-ready under Revision 26.**

**Executable:** **NO-PASS / reopened** until Revision-25/26 implementation and exact-candidate evidence close.