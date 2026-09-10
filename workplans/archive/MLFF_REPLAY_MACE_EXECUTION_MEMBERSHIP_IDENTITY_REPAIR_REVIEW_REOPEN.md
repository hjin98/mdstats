---
kind: implementation-workplan-review-amendment
workplan_id: CODE-MLFF-REPLAY-MACE-MEMBERSHIP-IDENTITY-REPAIR-REVIEW-REOPEN-1
parent_workplan_id: CODE-MLFF-REPLAY-MACE-MEMBERSHIP-IDENTITY-REPAIR
protocol_version: 6.0.0
status: reopened
review_date: 2026-09-09
reviewed_candidate_head: 41fd1cf0643fb7f42a8423c22368b2283f9176de
implementation_review_verdict: no-pass
highest_affected_domain: D4 realization under unchanged accepted D3 replay/MACE architecture
serious_challenge: none
precedence: parent workplan + this amendment; all non-conflicting parent invariants, non-goals, acceptance requirements, and deferred GPU qualification remain binding
---

# MLFF replay/MACE membership repair — implementation review reopen

## 0. Verdict

**NO-PASS / REOPENED.**

Candidate `41fd1cf0643fb7f42a8423c22368b2283f9176de` fixes the original identity-domain defect in the right architectural direction: target execution remains bound to target `frame_uid`; single-source replay can use canonical `replay_geometry_identity`; mixed replay identity domains fail closed; the real MACE loader path is exercised; and no new durable replay identity, registry, migration database, restart state machine, or transport rewrite was introduced.

However, the assembled realization introduces a production-scale execution-path regression that explains the stakeholder's new observation that `cross-validate` appears stuck immediately after the frozen-design banner. The repair recovers replay membership by reparsing the complete replay ExtXYZ with ASE in the parent P5 launch path, then reparses the same complete replay ExtXYZ again in the child MACE wrapper after MACE itself has already loaded that training file. Those redundant full-corpus scans occur inside the seed/fold run matrix and are invisible to the newly added tiny replay fixtures.

The public command also emits no liveness/progress line between freezing the design and completion of an entire selected size, so replay preparation, lock wait, individual fold/seed execution, MACE launch, and ordinary training are operationally indistinguishable from a hang.

No Serious Challenge is active. D1, D2, and accepted D3 remain coherent. Repair D4 and execute the missing affected evidence.

---

## 1. Accepted implementation surfaces — preserve

The following parts of `41fd1cf...` are directionally correct and should not be backed out merely to cure the stall.

1. `mace_compatibility._mace_execution_membership_values()` explicitly separates `target` and `replay` domains.
2. Target DATA execution continues to require exact non-empty `frame_uid` values.
3. Replay execution can consume `replay_geometry_identity` without injecting target-domain UIDs into single-source replay transport.
4. A replay training file cannot select `frame_uid` versus `replay_geometry_identity` independently per frame; mixed domains fail typed.
5. `post_selection_execution._build_post_selection_mace_execution_authority()` and continuation reauthentication now call the role-aware membership owner consistently.
6. The child MACE collection annotation and loader validation use the same membership digest/evidence mechanism rather than weakening replay evidence to count-only or `None`.
7. Added assembled tests preserve source/view bytes and replay-lineage identity across a same-workspace rerun.
8. The repair does not rewrite replay source/view bytes and does not change warning/dtype policy.

These close the original semantic bug family. The remaining blockers concern how that accepted identity is realized and verified at production scale.

---

## 2. Blocking R1 — redundant full replay reparsing in the inner CV run matrix

### 2.1 Parent-side redundant scan

For replay, `post_selection_execution._mace_execution_frame_uid_set_digest()` ignores the already-resolved replay source/split authority and calls `_mace_execution_membership_values(artifact.path, role="replay", ...)`.

`_mace_execution_membership_values()` then runs `ase.io.iread(..., index=":", format="extxyz")` over every replay training frame solely to recover `replay_geometry_identity` metadata and build the expected set digest.

This scan happens while building every P5 MACE launch authority and again during continuation reconciliation when applicable.

For canonical single-source replay this work is redundant. The existing replay owner has already authenticated the external source and deterministic `ReplaySplitManifest`; that manifest contains exact `train_geometry_identities`, train count, and a train-geometry-set digest. The generated view is a reconstructable transport, not the owner of replay membership.

**Required end state:** the parent expected replay membership digest for `single_source` must be derived directly from already-authenticated replay authority carried through the existing P5 replay resolution, without reopening the complete replay ExtXYZ. Preserve current legacy-split semantics separately where they remain supported.

Do not add a cache merely to compensate for this scan. Reuse the existing source/split authority already in memory/persistence.

### 2.2 Child-side duplicate scan after MACE load

`critical_precision_cli._annotate_mace_collections_with_exported_uids()` calls `_mace_execution_membership_values()` for each training head after MACE has produced `head_config.collections.train`. For the replay head this performs a second complete ASE parse of the replay training file solely to recover membership metadata, then zips those tokens onto the already-loaded MACE `Configuration` objects.

Thus one replay-enabled P5 run currently has at least:

```text
P5 expected-membership scan of replay ExtXYZ
 -> MACE's required training-data load
 -> mdstats child wrapper's second replay ExtXYZ membership scan
```

and the first and third passes repeat for every required seed/fold run.

That is contrary to Protocol 6 performance/storage doctrine: remove redundant I/O/parsing first; immutable input should be parsed once per logical operation when possible; reuse normalized/canonical authority rather than reopening it in inner loops.

**Required end state:** exact actual MACE replay membership must still be verified, but the verification should piggyback on the data MACE already loaded rather than reopening the full replay training file solely for identity.

A particularly promising bounded D4 route is available in pinned MACE 0.3.16: its `Configuration` already retains `atomic_numbers`, `positions`, `cell`, and `pbc`. Those are the inputs required to rederive the existing canonical single-source replay geometry identity. Evaluate whether the actual loaded replay collection can be projected through the existing canonical replay-geometry owner and compared with the already-authenticated split membership. This is preferable to a second ExtXYZ parse if exact equivalence can be established. Do not invent a second geometry hash or a new identity namespace.

The exact implementation remains D4-delegated. If MACE 0.3.16 cannot establish actual loaded replay membership without either a redundant full reread or changing accepted transport/scientific authority, return to Software Design under parent reopen trigger 4 rather than hiding the cost behind another cache.

### 2.3 Scaling acceptance

The new tests use replay sizes of roughly 3, 6, 10/12, and 60 frames. They establish semantics but do not expose the real 10k-class replay startup path.

Add an oracle that catches repeated full-corpus parsing without relying on a fragile wall-time threshold. Prefer call-count/owner evidence such as:

- single-source parent authority construction performs **zero** full replay ExtXYZ membership scans when authenticated split membership is already available;
- dependency-facing validation performs no additional full replay-file parse beyond the data load MACE itself requires, if the chosen realization can rederive identity from its loaded collection;
- repeated seed/fold execution does not multiply an avoidable replay membership parse.

A representative 10k-class bounded benchmark may supplement this structural oracle, but wall time alone is not the authority.

---

## 3. Blocking R2 — the user-visible CV path has a liveness blind spot

`execute_current_cross_validate()` prints the frozen design, marks the stage RUNNING, then calls `execute_post_selection_cross_validation()` serially for each size. The next public line is printed only **after the complete CV campaign for that size returns**.

Inside `execute_post_selection_cross_validation()`, every `(seed, fold)` run is built/resumed/executed without a public progress line. Therefore the following materially different states all look identical:

- waiting on the campaign writer lock;
- waiting on the P5 publication barrier;
- resolving/revalidating replay authority;
- performing redundant replay scans;
- reusing a completed fold;
- materializing one fold;
- launching MACE;
- training normally for the configured horizon;
- evaluating the checkpoint/outer fold.

For a long-running user-facing ML workflow this is inadequate operational observability and made the newly introduced parsing regression appear as a deadlock.

**Required end state:** add bounded, non-authoritative liveness/progress reporting through the existing CV orchestration. At minimum identify:

```text
N_selected
seed
fold index / total run matrix
reused versus executing
high-level phase before MACE launch / TRAIN2 execution
```

Reuse existing progress/logging mechanisms where practical. Do not log per frame and do not create durable progress authority merely for stdout. Training/runtime-owned progress may remain in its existing owner.

This observability must not change scheduling, science, restart identity, or publication semantics.

---

## 4. Runtime lock diagnosis — investigate but do not redesign without evidence

There is a second exact explanation for a process stopping immediately after the displayed banner: the next operation is `_mark_stage(... RUNNING ...)`, whose `CampaignStore.writer_exclusion()` uses blocking `fcntl.flock(LOCK_EX)` with no timeout. P5 publication and run-activity barriers also use blocking advisory file locks.

A stale lock *file* is harmless; the kernel releases `flock` when a process exits. A live competing campaign/storage process can legitimately block another writer indefinitely from the user's perspective.

This locking code was not introduced by `41fd1cf...`, so do not add timeout/retry/second-lock machinery based only on the symptom. Establish the actual runtime state first.

On the stakeholder machine, distinguish the paths using process/lock evidence:

```bash
pgrep -af 'mdstats|mace'
lslocks | grep -E 'campaign.sqlite3|publication-barrier|run-activity'
lsof <workspace>/.mdstats/campaign.sqlite3.writer-lock
strace -f -p <cross_validate_pid> -e trace=flock,openat,read,pread64,wait4 -s 128
```

Interpretation:

- blocked `flock(..., LOCK_EX)` -> another live writer/holder is the immediate cause;
- repeated reads of `.mdstats/replay-unified/views/*train*.extxyz` before MACE launch -> redundant membership scan is the immediate cause;
- parent blocked in `wait4()` with a live MACE child consuming CPU/GPU -> ordinary training is running and the missing progress reporting is the main operational defect.

If a reproducible lock-starvation/deadlock defect is actually demonstrated, route it as its own D4 concurrency issue rather than folding speculative lock changes into the replay-identity repair.

---

## 5. Blocking R3 — acceptance matrix is incomplete

The new source tests materially improve A1/A2 and provide a same-process restart path, but the parent workplan is not yet closed.

Required remaining/strengthened evidence:

1. **A3 baseline-workspace counterfactual:** prove the fixed owner consumes the exact pre-fix prepared single-source views unchanged. Since replay-generation source was not changed by this candidate, this may be established with a baseline-generated fixture/bytes plus candidate execution; do not substitute a fresh candidate-only materialization if the claim is pre-fix compatibility.
2. **A4 exact membership mutation:** establish expected replay membership, then mutate/substitute one replay training geometry and prove rejection before training evidence is accepted. The current mixed-identity test is useful but is not this counterfactual.
3. **A5 mismatched continuation:** corrupt/substitute persisted replay membership evidence and prove partial and full-horizon continuation cannot bypass reauthentication before resume/EVAL2/publication. A successful same-run rerun alone is insufficient.
4. **A6 real multi-size composition:** current multi-size single-source coverage substitutes `PostSelectionHarness` below P5 and is useful for orchestration, but pair it with the exact real-owner membership realization being changed so the optimized path cannot become first-size-only or helper-only.
5. **A7 family closure:** Semgrep if available; otherwise a validated bounded AST/source check. Serena/Semgrep were unavailable on this review host, which does not relax the claim.
6. **A8 executed evidence:** GitHub reports zero check runs for `41fd1cf...`. Execute the parent-required affected suites plus any new performance/liveness tests on the final candidate. Test source is not execution evidence.

Full GPU/CuEq/LAMMPS/MLIAP qualification remains deferred exactly as in the parent plan.

---

## 6. Repair sequence

### R1-A — remove redundant parent replay parsing

Route canonical single-source split membership through the existing P5 replay resolution and build expected MACE replay membership from that authenticated authority. No full replay ExtXYZ reread merely to build the expected digest.

Preserve explicit legacy-split behavior and target `frame_uid` behavior.

### R1-B — collapse actual-membership verification into the MACE load path

Authenticate the actual MACE replay collection without reopening the complete replay ExtXYZ solely for metadata. Prefer rederiving the existing canonical single-source geometry identity from MACE 0.3.16 `Configuration` geometry if verification proves exact equivalence. Keep one existing MACE execution-evidence record family.

Do not add a persistent mapping/cache/registry/state machine.

### R2 — make long CV work observable

Add bounded size/seed/fold/phase liveness at the existing orchestration owner. Preserve deterministic execution and existing progress conventions.

### R3 — close adversarial and assembled evidence

Run A3-A8 plus a no-redundant-full-parse oracle and the exact stakeholder same-workspace rerun. Re-derive the final affected surface after the patch.

---

## 7. Re-review PASS criteria

```text
[ ] original no-frame_uid single-source replay failure remains closed
[ ] target frame_uid exactness remains unchanged
[ ] canonical single-source replay expected membership comes from existing authenticated replay/split authority without a full replay-file reread
[ ] actual MACE-loaded replay membership is verified exactly without an avoidable second full replay ExtXYZ parse
[ ] no avoidable replay membership parse is multiplied by seed/fold count
[ ] same pre-fix prepared workspace resumes without prepare/reset/deletion or replay-lineage churn
[ ] replay geometry mutation/substitution rejects before accepted training evidence
[ ] partial and full-horizon TRAIN2 continuation reauthenticate replay membership and mismatch rejects
[ ] supported legacy replay semantics remain bounded and current
[ ] two-size replay CV still executes every requested size
[ ] CV emits bounded per-run/phase liveness so lock wait, reuse, launch, and active training are distinguishable
[ ] no new replay identity, cache registry, migration DB, state machine, wrapper, or transport rewrite
[ ] final affected pytest/static/integration evidence actually executes and passes on one unchanged candidate
[ ] full GPU/CuEq/LAMMPS qualification remains explicitly deferred
```

Until all rows close, keep the parent workplan active and this implementation review **NO-PASS / REOPENED**.
