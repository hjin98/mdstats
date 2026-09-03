---
kind: implementation-review-reopen
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R27
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
reviewed_date: 2026-09-02
reviewed_authority_revision: 26
reviewed_executable_commit: f8bd22fcb5d1b5b62246b0ca17653e6b31191a51
reviewed_executable_tree: 928e9507ecac84040e1604ed5949f03440044740
reviewed_branch_head: 60b29f6992f088dd42f78b01424a9054c14e46a0
review_verdict: NO-PASS
scope: independent implementation review of Revision 26; preserve the conforming historical-test retirement, single descriptor-bound P7 namespace/view/proof authority, fd-relative mutation primitives, corrected wrong-root/basename/nested-mount fixtures, and current storage specification; reopen only final apply-time certification-to-mutation descriptor continuity, truthful refusal accounting, proxy-proof coverage of those two seams, and exact-candidate functional evidence
precedence: Revision 26 remains the accepted closed implementation-ready design. This review does not reopen P1-P7 science, the owner-driven storage architecture, or the R26 test-retirement policy. It adds bounded implementation corrections where executable f8bd22f... does not yet realize the frozen R26 apply contract.
---

# Storage/I-O reset implementation review reopen 8 — Revision 27

## 0. Verdict and reviewed candidate

**NO-PASS / bounded implementation reopen.**

Reviewed executable:

```text
commit  f8bd22fcb5d1b5b62246b0ca17653e6b31191a51
tree    928e9507ecac84040e1604ed5949f03440044740
```

Branch head `60b29f6992f088dd42f78b01424a9054c14e46a0` is a generated-PDF-only successor and does not change the executable review target.

The following Revision-26 work is conforming and must be preserved:

- R26-T1 materially retired historical-only pytest/benchmark debt while restoring real tracked current fixtures and preserving/consolidating current semantic coverage;
- `observe_qualification_namespace()` now supplies one continuous descriptor-relative no-follow P7 storage-facing observation, and `qualification_views()` no longer re-enumerates `qualification/gN/attempts/<attempt>` through a parallel pathname walk;
- exact released-attempt proof reads, generation-scoped root binding, and descendant topology certification are descriptor-relative inside that observation;
- both released top-level files and directories route to a P7-specific fd-relative mutation owner; the Python >=3.10 realization uses supported `os` dir-fd primitives and refuses where they are unavailable;
- the previously weak wrong-root, basename-only proof, and nested-mount fixtures were repaired so the named invariant is the actual reason for refusal;
- the current storage specification was reconciled to descriptor-pinned ancestry and fd-relative mutation semantics.

Three blocking groups remain.

---

## 1. IR27-1 — final apply still closes the certifying descriptor and consumes a stale certification snapshot

### Finding

Revision 26 froze a stronger apply boundary than the candidate actually implements:

```text
fresh strict P7 reacquisition under owner locks
  -> keep the authenticated attempt-directory descriptor alive
  -> exact state/proof/member certification on that descriptor
  -> mutation relative to that same retained descriptor
  -> close descriptor
```

The candidate's fresh `StorageExecutor.run()` resnapshot correctly invokes `qualification_views(..., certify=True)` under the storage/P5/P7 synchronization. During that resnapshot, `observe_qualification_namespace()` opens each attempt descriptor, authenticates state, reads/validates `attempt-members.json`, observes exact typed descendants, and builds `AttemptStateAuthority.certified_nodes`.

However `_observe_generation()` then closes that attempt descriptor before the snapshot returns. Later `_cleanup_engine()` calls `remove_released_attempt_member()`, which performs another strict path reacquisition to obtain a **new** attempt descriptor, compares its `(device, inode)` with the earlier snapshot identity, and then mutates using the **previous snapshot's `certified_nodes`**. It does not re-authenticate the state, released proof, and exact descendant topology through the descriptor it is about to mutate.

That is still materially safer than the Revision-25 absolute-path implementation, but it is not the frozen Revision-26 same-capability boundary. The final destructive authority is reconstructed as:

```text
certification on descriptor A
  -> close A
  -> carry typed names + inode identity in memory
  -> reacquire descriptor B by namespace
  -> root inode equality
  -> mutation from B using certification produced from A
```

The accepted R26 owner synchronization means supported writers should not mutate this state while the locks are held, but the implementation may not silently weaken an explicit frozen ownership/trust boundary merely because the common case is synchronized. No redesign is required: the final P7 mutation owner can perform the fresh state/proof/topology certification itself after reacquiring the attempt and retain that exact descriptor through mutation.

### Required repair

1. For each P7 released action, the final owner-specific apply primitive must freshly reacquire the attempt under the already-held owner synchronization and keep that descriptor open until the action reaches a terminal mutation/refusal disposition.
2. On that same descriptor, re-read/authenticate the current attempt state, exact released proof, generation-scoped root binding, and exact typed descendant topology before mutation.
3. The planned snapshot may supply the expected attempt/root/state identity and target member as stale-plan constraints, but a previously closed snapshot's `certified_nodes` may not be the **final** destructive authority.
4. Mutate the certified top-level file/directory relative to that retained descriptor, using the existing fd-relative no-follow recursion. Do not add another pathname walk or another inode-CAS fiction.
5. If the freshly certified state/proof/topology no longer matches the plan or target, refuse the action. No unbounded retry.
6. Preserve bounded `storage report`: only consequential apply/certification pays the exact proof/topology cost.

### Acceptance boundary

Use the real storage executor, real owner locks, real strict P7 owner, and real fd-relative mutation. Instrumentation may wrap descriptor/proof/open/mutation primitives below those semantic owners.

Required counterfactuals:

- after planning but before final apply certification, alter the released proof/state/topology through a test-only external seam not represented as a supported writer; the final P7 mutation owner re-reads it and refuses rather than consuming old certified names;
- prove by instrumentation that final state/proof/topology certification and the first destructive transition use the same retained attempt descriptor/capability;
- keep the existing public-attempt-path swap after final certification/before syscall: authority must remain pinned to the already-open attempt and never transfer to the replacement;
- exercise both a top-level regular file and a directory.

A narrow structural guard may assert the final P7 apply primitive performs `_authenticate_attempt_from_descriptor` / `_certify_attempt_from_descriptor` or an engineering-equivalent descriptor-bound owner operation after fresh reacquisition and before mutation. Do not create a general AST registry.

---

## 2. IR27-2 — a refused P7 mutation is recorded as a completed action and can yield a false `complete` execution

### Finding

`remove_released_attempt_member()` correctly returns `(False, reason)` for material refusal conditions, including:

- unsupported dir-fd/no-follow platform;
- unresolved/replaced attempt namespace;
- root identity mismatch;
- current member kind/topology contradiction;
- mount/symlink/special/unrecorded descendant refusal.

But `_cleanup_engine()` currently does:

```text
removed, why = remove_released_attempt_member(...)
result.completed.append({... "removed": removed, "detail": why})
if removed:
    reclaimed_bytes += ...
```

Therefore `removed=False` still enters `completed`. `StorageExecutor._settle()` declares `complete` whenever `result.refused` is empty. A cleanup in which every P7 action is refused at the final owner boundary can consequently report `status=complete`, with `removed=false` hidden inside `completed_actions`.

This violates the executor's own terminal-status contract and Revision 26's explicit requirement that an unsupported/no-longer-authenticated P7 mutation **refuse explicitly**.

### Required repair

1. A P7 owner-specific `(False, reason)` terminal result must enter `result.refused`, not `result.completed`.
2. If no planned mutation succeeded and all relevant actions refused, execution status is `refused`.
3. If at least one action succeeded and at least one refused, execution status is `partial`.
4. Only an actually removed/already-terminal-success action enters `completed` and contributes reclaimed bytes.
5. Apply the same truth rule to any common `remove_certified_subtree()` branch where a `(False, reason)` is presently appended to `completed`; the shared executor must not encode a refused mutation as success merely because the helper returned normally.
6. Keep audit semantics unchanged otherwise: durable audit reports the truthful terminal status; audit publication failure remains an evidence-status degradation, not rollback.

### Acceptance boundary

Through the real cleanup executor:

- force `dir_fd_mutation_supported()` false and prove bytes remain, the action appears only in `refused_actions`, and the execution is `refused` when nothing else mutates;
- force a fresh P7 namespace/root/state/proof mismatch at the final apply boundary and assert the same refusal accounting;
- construct a bounded multi-action case where one released action succeeds and a later one refuses; execution is `partial`, with each action in the correct collection;
- no test may infer truth only from CLI return code; assert the returned execution payload/status.

---

## 3. IR27-3 — exact-candidate functional evidence is still absent, and current race tests do not cover IR27-1/2

### Existing test improvements accepted

The candidate's new R26 counterfactuals are materially better and must be retained:

- basename-only proof recomputes its self digest and asserts the bare-root-locator failure;
- wrong-root state is independently valid and asserts the root/state relation failure;
- nested-mount directory exists before release, so the proof records it and the mount check itself is what withholds traversal;
- the public attempt-path replacement race injects below the owner and above the fd-relative destructive transition;
- interruption/retry exercises both generic and P7 removal owners.

### Remaining proxy-proof gaps

The public-path race fires **after** `remove_released_attempt_member()` has reacquired and checked the new mutation descriptor. It therefore cannot detect that final certification occurred earlier on a descriptor that was already closed; it proves fd-relative mutation pinning after the second open, not R26's certification-to-mutation same-descriptor boundary.

It also captures helper outcomes but does not prove the real storage execution classifies `removed=False` as `refused` rather than a completed action. A CLI zero exit is not a substitute for checking the execution payload/status.

Repair the tests as specified in IR27-1/2.

### Exact executable evidence

For executable `f8bd22fcb5d1b5b62246b0ca17653e6b31191a51`, GitHub exposes one successful check run named `docs` and no functional status/check result. The implementation commits contain source/tests, and the R26-T1 commit records a collection count, but there is no review-visible candidate-bound record of the final R22-R26 focused/storage/integration/affected regression commands and outcomes.

After IR27-1/2 are repaired on the final executable candidate, record actual commands, pass/fail/skip summaries, executable commit, and executable tree for:

1. all focused Revision-22 through Revision-27 P7 namespace/state/proof/root/mutation/refusal/concurrency counterfactuals;
2. complete `tests/test_mlff_storage_reset_core.py`;
3. complete `tests/test_mlff_storage_reset_integration.py`;
4. affected current-owner P1/P3/P4/P5/P7 regressions and P6 destructive/current-lifecycle consumers touched by the common storage path;
5. clean `pytest --collect-only -q` on the maintained suite;
6. final affected-surface re-derivation followed by a fresh final affected regression/integration pass;
7. repository static checks and affected current specification/document validation.

Whole-repository behavioral pytest remains conditional under Revision 26: run it if the final affected surface cannot be bounded confidently or another repository/release policy independently requires it. Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and nonblocking.

---

## 4. Preservation boundary

Do not reopen or redo conforming work:

- R26-T1 historical test/tool retirement and restored current fixtures;
- the single descriptor-relative `observe_qualification_namespace()` authority and `qualification_views()` consolidation;
- parser totality, canonical generation spelling, generation-scoped released-root binding, cross-generation copy refusal, and workspace-wide ambiguity fence;
- fd-relative no-follow mutation primitives and Python >=3.10 support;
- corrected wrong-root/basename/nested-mount fixtures;
- established P5/P7/storage synchronization order;
- CampaignStore, archive/dedup/restore/control-plane architecture;
- P1-P7 scientific/currentness/publication/qualification semantics;
- current storage specification except for wording needed to reflect the exact final same-descriptor apply realization.

No persistent descriptor/inode ledger, new state machine, or platform-specific kernel extension is authorized.

---

## 5. Rework route and exit

Resume only at the final R26 apply boundary:

```text
IR27-1  final same-descriptor P7 reacquisition + certification + mutation
   -> IR27-2 truthful refusal/completed accounting
   -> IR27-3 proxy-proof final seams
   -> R21-E5/F exact-candidate affected regression/integration evidence
```

**Design/workplan disposition:** Revision 26 remains **CLOSED / implementation-ready**; Revision 27 is bounded implementation rework only.

**Executable disposition:** **NO-PASS / reopened under Revision 27** until the three groups above close.
