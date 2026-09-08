---
kind: implementation-workplan
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R30
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: closed-implementation-ready
supersedes_revision: 29
reviewed_executable_commit: 6423a3f33a36c09ca1b89f5740f42c402b1993d2
reviewed_executable_tree: a40bdf7cbd4bc1e2a2de4ec41ccb77fede4dc926
scope: snapshot-complete final-apply repair closure consolidating the still-binding Revision-28 and Revision-29 semantics plus final independent design-review corrections
---

# Storage/I-O reset final-apply closure — Revision 30

## Objective and protected concerns

Revision 30 is the **single current implementation contract for the remaining storage final-apply repair**. It consolidates the still-binding Revision-28 design and Revision-29 implementation-review corrections so implementation no longer has to reconstruct the target from a chain of superseded review artifacts.

The protected product outcome is unchanged:

- destructive P7 cleanup acts only on released scratch the real P7 owner has freshly authenticated;
- the exact released authority, attempt root, and planned target remain bound from the immutable plan through the final destructive boundary;
- final P7 certification and mutation share one live descriptor capability rather than a pathname or a memory of a closed descriptor;
- cleanup may resume after legitimate monotonic shrinkage but may never convert new/foreign topology into authority;
- storage execution and durable audit evidence state exactly what changed, including partial mutation and post-mutation durability failure;
- no repair reopens accepted P1-P7 science/currentness, R26 historical test/tool retirement, CampaignStore ownership, P5 typed proof, archive/dedup/restore/control-plane architecture, or the accepted Python/POSIX threat boundary.

The reviewed executable `6423a3f33a36c09ca1b89f5740f42c402b1993d2` already implements substantial conforming pieces: exact released-authority identity, `ReleasedAttemptSession`, proof-as-upper-bound semantics, explicit four-way mutation outcomes, descriptor-relative mutation, and materially improved focused tests. Preserve those pieces and repair only the gaps specified here.

## Engineering envelope and frozen product design

The following are frozen:

1. **Owner authority.** P7 remains the sole semantic owner of qualification attempt state, released-proof binding, and released-scratch authorship. Storage consumes P7 authority; it does not infer it from pathnames or create a second registry.
2. **One strict namespace authority.** Storage-facing P7 state/proof/topology comes from the continuous no-follow descriptor-relative P7 descent. No permissive parallel reader or post-certification pathname rewalk may create destructive authority.
3. **Plan binding.** The immutable plan binds the exact derived released authority plus the target filesystem identity already carried by `PlannedAction`. Release identity, root identity, target identity, and typed proof are independent constraints; none substitutes for another.
4. **Ephemeral final capability.** Final destructive authority is an in-memory attempt capability opened under the existing storage/P5/P7 synchronization. It is not persisted and must not survive close.
5. **Python/platform floor.** Python `>=3.10` remains supported. Final deletion uses the existing no-follow fd-relative `os` primitives and refuses where the platform cannot provide the required boundary; do not raise the floor merely to avoid the explicit recursion.
6. **Threat boundary.** The product guarantees descriptor-pinned owner ancestry and fd-relative no-follow mutation under supported-owner synchronization. It does not claim a nonexistent atomic inode-compare-and-delete primitive against an arbitrary same-UID process racing the exact final POSIX unlink/rmdir syscall. Checks immediately before that final syscall are still required; only the irreducible race *after* the final check is outside the guarantee.
7. **Monotonic release semantics.** The released v3 proof is an upper bound on P7-authored topology. Missing recorded nodes are legitimate monotonic shrink; live additions, kind changes, symlinks, special nodes, nested mounts, substituted roots, changed release authority, or changed planned target identity reduce authority and never widen it.
8. **Truthful execution.** Mutation state is semantic data, not inferred from reason prose. Clean completion, already-terminal absence, no-change refusal, and partial mutation followed by refusal/failure remain distinct.
9. **Bounded reporting.** Ordinary storage reporting stays bounded independently of released-scratch node count. O(node-count) proof/topology certification remains consequential plan/apply work.
10. **No new persistent control plane.** No persistent descriptor ledger, inode registry, release registry, retry state machine, or platform-specific kernel extension is authorized.

## Implementation obligations

### R30-A — exact released authority remains plan-bound and final-apply reauthenticated

**Concern / rationale.** A released attempt can be resealed into a different, internally valid released authority while retaining the same names and kinds. Path/kind/root identity alone cannot distinguish the two authorities.

**Required end state.** Every certified released P7 scratch action remains bound to a non-persistent identity derived from the authenticated attempt-state content digest and authenticated v3 proof content digest, bound to generation/attempt. The identity flows through the existing owner-state plan binding and is freshly recomputed on the final live attempt descriptor.

**Required constraints.**

- Preserve the current `OwnerArtifactView.state_identity -> PlannedAction.owner_state_identity` realization or an engineering-equivalent existing binding; no second persistent registry.
- Final session acquisition refuses if the freshly derived release authority differs from the plan-bound expectation.
- Root identity and target identity checks remain separately mandatory.

**Acceptance.** Drive an old real cleanup plan through the real executor after resealing state+proof into a different but valid released authority with the same target names/kinds. The old plan/session must stale/refuse without destructive transfer.

### R30-B — final capability continuity, final target identity, and one-way close

**Concern / rationale.** A live attempt descriptor closes the ancestor-resolution gap only if the exact target is also checked at the final owner boundary and the capability cannot be spent after close. An fd integer is not an identity: the OS may reuse it after close.

**Required end state.** Under the already-held storage/P5/P7 synchronization, final P7 apply performs:

```text
strict attempt reacquisition
  -> retain attempt descriptor/capability
  -> authenticate current state on that descriptor
  -> read/validate/bind current released proof on that descriptor
  -> certify current typed topology on that descriptor
  -> compare plan-bound release identity
  -> compare plan-bound attempt-root identity
  -> immediately before each member mutation, compare the plan-bound target identity
       by no-follow descriptor-relative observation
  -> mutate only through the retained attempt descriptor/no-follow child descriptors
  -> close capability after terminal disposition
```

**Required consequences.**

- Planning/resnapshot `certified_nodes` are not final destructive authority and are not passed into the final mutation owner as though they were.
- For the final target identity check, use the target identity already bound into the `PlannedAction`; no new identity schema is needed. At minimum preserve the current revalidation dimensions `kind`, `device`, `inode`, `size_bytes`, and `mtime_ns`, observed no-follow relative to the retained attempt descriptor. If normal plan revalidation later strengthens its bounded identity dimensions, the final P7 boundary must not silently become weaker.
- A missing target is `already_absent`, with zero reclaimed bytes. A present target whose identity differs from the plan is `refused_no_change` and invalidates the attempt capability for remaining actions under R30-D.
- Do **not** require a full-tree size recomputation merely for the final target check; the proof owns descendant topology and the plan's bounded filesystem identity owns the target entry.
- `ReleasedAttemptSession.close()` or its equivalent is one-way. Every public/internal mutation entry that accepts a session must reject `closed` **before any stat/open/unlink/rmdir syscall using the stored fd**. A recycled integer descriptor must never revive a stale capability.
- A successful session acquisition may serve multiple actions of the same attempt. A failed acquisition is cached as a refusal for the remainder of that attempt in the execution rather than repeatedly retrying the same authority boundary.

**Acceptance boundary.** Use the real executor, synchronization, P7 owner, and fd-relative mutation. Instrumentation may observe/replace objects below those owners.

**Acceptance.** Cover both top-level file and directory targets. Replace a target with a same-name/same-kind different object after ordinary plan revalidation but before the final member mutation check; the replacement must survive and the action must refuse. Separately close a valid session and prove a later call through that object reaches no filesystem mutation/observation syscall even if fd-number reuse is forced or simulated. Capability-lifetime evidence must prove no close occurs between final certification and the first destructive transition.

### R30-C — proof is an upper bound; monotonic shrink remains resumable

**Concern / rationale.** Requiring equality with the original released proof makes multi-action cleanup invalidate itself after its own first successful removal and makes interrupted cleanup unrecoverable.

**Required end state.** Fresh certification accepts the live tree exactly when every observed live descendant is present in the released proof with the same kind and no forbidden boundary is crossed. Proof-recorded nodes that are absent are simply absent.

**Required consequences.**

- Missing recorded nodes grant no new authority and earn no reclaimed bytes in the current execution unless this execution actually removed them.
- New descendants, kind changes, symlinks, special nodes, nested mounts, substituted roots, changed release identity, or changed target identity refuse the affected action.
- Multi-member cleanup may continue after `removed` or `already_absent` because those are expected monotonic states.
- A fresh retry after interruption re-plans/re-inventories and may reclaim the surviving certified subset under the unchanged proof.

**Acceptance.** A bounded multi-member attempt removes multiple distinct surviving members without self-staling solely because earlier members disappeared. An interrupted first run followed by a fresh retry reclaims the remaining certified members. Addition/kind-change counterfactuals still refuse.

### R30-D — mutation-time contradiction invalidates the same-attempt capability

**Concern / rationale.** Once a member mutation discovers topology/identity evidence inconsistent with the session's certification, continuing to spend that same attempt capability ignores positive evidence that its premise is no longer sufficient.

**Required end state.** Outcome handling for a live P7 session is:

```text
removed / already_absent
  -> record truthfully
  -> same attempt capability may continue

refused_no_change / partial_change_refused caused at the mutation boundary
  -> record current action truthfully
  -> close/invalidate the attempt capability
  -> cache an explicit no-change refusal for later planned members of that attempt
  -> later same-attempt members perform no mutation
```

A session-acquisition refusal likewise withholds all same-attempt actions for that execution. Independent attempts may continue. There is no retry-until-convenient loop and no persistent invalidation state.

**Acceptance.** Through the real cleanup executor, inject a contradiction only after final session certification in an attempt with at least two planned members. Prove the current action has the correct outcome, every later same-attempt action is a no-change refusal without a destructive call, and an unrelated attempt may still proceed. If the first action mutated before refusal, execution and audit are partial with `mutated=true`.

### R30-E — materialize the authenticated proof lookup once and never widen it

**Concern / rationale.** Rebuilding `{path: kind}` from the complete proof for every top-level member creates avoidable `O(N*M)` traversal/allocation and weakens the value of the attempt-scoped session.

**Required end state.** The live session materializes the proof's typed-node lookup once (eagerly at construction or lazy-once) and reuses it for all member checks and recursive descent.

**Required consequences.**

- The lookup is derived only from the proof authenticated on the live descriptor.
- It is ephemeral and not persisted.
- It is private/read-only in authority terms: no caller may extend or mutate it to widen the session's certified node set after authentication.
- No O(node-count) rebuild is performed per planned member.

**Acceptance.** A focused instrumented multi-member test proves complete proof-map materialization occurs at most once per live session and that attempted caller-side mutation cannot widen destructive authority.

### R30-F — four terminal mutation outcomes remain authoritative

**Required semantic outcomes.** Equivalent internal names are allowed, but the product must distinguish:

```text
removed                 requested target cleanly removed by this execution
already_absent          desired terminal state already held; this execution removed nothing
refused_no_change       owner withheld the action; this execution changed nothing
partial_change_refused  authorized mutation occurred, then the action was stopped or failed
```

Reason strings are diagnostics only and may not determine outcome semantics.

**Required consequences.**

- `removed` is a completed action and credits only attributable bytes under the existing storage accounting metric.
- `already_absent` may be a terminally satisfied completed action but credits zero.
- `refused_no_change` is a refused action, credits zero, and yields execution `refused` when nothing else succeeded or mutated.
- `partial_change_refused` is a refused/partial action with `mutated=true`; it makes execution `partial` even if it is the only action and credits only substantiated bytes already removed.
- Any mix of success with refusal/partial remains `partial`; only all-terminal-success actions produce ordinary `complete`.
- Audit-publication failure degradation remains unchanged and never turns a mutation failure into success.

Apply these semantics to the P7 released-member path, common certified-subtree cleanup, and generic cleanup removal wherever the helper can distinguish absence, no-change refusal, or partial mutation.

### R30-G — post-mutation exceptions must cross the action boundary with mutation truth intact

**Concern / rationale.** A helper can unlink/rmdir successfully and then fail during fsync/durability or a later recursive transition before returning its normal `MutationOutcome`. If the exception bypasses the current action boundary, the executor can know only that "something failed", not which action mutated or how many bytes were already removed.

**Required end state.** Once the first destructive transition for an action has occurred, any later exception before clean completion carries/exposes a structured partial-mutation outcome to the **current action boundary** before propagation continues.

The required ownership flow is:

```text
helper performs destructive transition
  -> later failure occurs
  -> helper exposes structured partial_change_refused + substantiated removed bytes + cause
  -> current action engine catches that structured failure
  -> record_removal(result, current_action, partial outcome)
  -> invalidate P7 session when applicable
  -> propagate the original/structured failure
  -> StorageExecutor outer interruption handling settles/finalizes partial audit
  -> exception remains visible to the caller under the existing error contract
```

**Required consequences.**

- A structured exception carrying `MutationOutcome`, an engine-owned catch/rethrow protocol, or an engineering-equivalent mechanism is delegated; silently letting a post-mutation exception jump from helper directly to the executor's outer `BaseException` handler is not sufficient because the current action evidence is then lost.
- A failure **before** the first destructive transition records no mutation and no reclaimed bytes.
- A failure after unlink/rmdir but before durability confirmation is **not** `removed`; it is partial mutation/failure. `removed_bytes` means bytes whose directory entries were actually removed before the failure under the existing runtime accounting metric; it is not a promise that crash durability was confirmed. The durability failure remains explicit in detail/cause and is propagated.
- Apply this rule to changed P7 file/recursive paths and the common generic cleanup removal path where unlink-before-fsync or equivalent sequencing exists.
- Existing audit-publication failure semantics remain independent: if the mutation audit itself cannot be published, the existing unaudited status degradation still applies.

**Acceptance.** Inject a deterministic failure immediately after a successful unlink/rmdir and before the relevant durability step can report clean completion. Through the real executor, prove the durable execution record (when audit publication itself succeeds) contains the current action as partial mutation, `mutated=true`, exact substantiated bytes, and `status=partial`, while the operation still raises. Inject the counterfactual immediately before the first destructive transition and prove no mutation or byte credit is fabricated.

### R30-H — exact byte accounting for recursive partial mutation

**Concern / rationale.** A fully removed nested subtree can currently disappear from a later parent partial outcome because the successful nested result does not propagate its measured byte count. Partial accounting must also retain the existing storage metric rather than introducing a local competing definition.

**Required end state.** Every recursive removal propagates the bytes it actually measured and removed so parent recursion can accumulate an exact action-local total if a later sibling refuses/fails.

**Required consequences.**

- Measure before unlink; do not reconstruct deleted size after the fact.
- Successful nested removal carries its measured amount internally even when the top-level clean-success representation could otherwise rely on the equivalent planned amount.
- Already-absent contributes zero.
- A partial result includes every successful removal in the mutated prefix and excludes every retained/absent node.
- Preserve the existing action/planner storage-size convention. Where that convention deduplicates repeated inode identity within a directory action, share the minimum action-local `(device,inode)` accounting state needed across recursive calls so hard links are not silently overcounted. Do not redefine `reclaimed_bytes` as physical freed blocks unless the existing product metric already does so.

**Acceptance.** Remove a complete nested subtree before encountering a later contradiction and assert the exact expected action-local bytes, including a representative hard-link case when the existing metric deduplicates it. The real executor's aggregate `reclaimed_bytes` and durable audit must match the action outcomes exactly.

## Implementation authority

### Frozen

- The parent `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` remains the broader owner-driven storage architecture and non-goal authority.
- Exact released authority is plan-bound and final-apply reauthenticated.
- Final attempt certification and mutation share a live descriptor capability.
- Final target identity is compared no-follow relative to that retained capability immediately before each P7 member mutation.
- Closed capability objects are unspendable regardless of fd-number reuse.
- Released topology may shrink monotonically but may not expand/change kind under old authority.
- A mutation-time contradiction invalidates later same-attempt actions for that execution.
- Proof lookup is once-per-session derived state, not a mutable/persistent authority.
- Mutation outcomes and post-mutation failures remain truthful at action, execution, and durable-audit levels.
- Partial bytes use the existing storage metric and never default to full planned size.
- Public bounded reporting remains bounded.
- Python `>=3.10`, the accepted descriptor-pinned threat boundary, R26 historical test/tool retirement, CampaignStore, P5 typed proof, archive/dedup/restore/control-plane architecture, and P1-P7 scientific/currentness semantics remain unchanged.

### Delegated

- Internal class/enum/exception names.
- Eager versus lazy-once proof-map materialization.
- The exact read-only representation of the session lookup.
- Whether post-mutation truth propagates via structured exception, engine-owned catch/rethrow, or equivalent local mechanism, provided the current action is recorded before outer propagation.
- Local helper factoring and test instrumentation hooks.
- Backward-compatible action-evidence representation details, provided semantic outcome/mutation/bytes remain explicit and existing consumers stay valid.

### Reopen only on evidence

Reopen only the affected surface if:

- supported Python/POSIX interfaces cannot enforce the final descriptor/target/capability boundary without changing the supported-platform contract;
- preserving exact existing storage accounting requires an incompatible public metric/schema change rather than local action state;
- a real external/public execution-result consumer cannot represent truthful partial mutation without an incompatible migration.

Do not reopen because a different helper layout, exception type, cache representation, or session shape is more convenient.

## Affected surface and task-specific acceptance

Initially expected executable surface is bounded to:

- `mdstats/training_data/qualification/store.py` — live P7 session, final target check, one-way close, once-per-session typed lookup, recursive outcome/byte propagation;
- `mdstats/training_data/storage/commands.py` — same-attempt invalidation and action-boundary recording/catch/rethrow;
- `mdstats/training_data/storage/executor.py` and `storage/outcome.py` — structured outcome/partial-failure plumbing and generic cleanup truth where needed;
- `mdstats/training_data/storage/durability.py` only if the generic unlink-before-fsync path needs local structured-failure plumbing;
- `mdstats/training_data/storage/plan.py` only if passing the already-existing target identity to the P7 final owner cannot be done without a local interface adjustment; do not create a new plan identity schema merely for this repair;
- focused storage core/integration tests and affected current storage specification wording.

Preserve conforming `owners.py` released-authority projection unless final implementation evidence shows a local interface adjustment is necessary.

### Required real-owner acceptance

Material acceptance claims must execute the real `StorageExecutor`, existing owner synchronization, real P7 authority/session logic, real outcome settlement, and durable audit publication. Deterministic hooks may alter filesystem timing/state or force low-level failure **below** these semantic owners. Direct helper tests remain useful focused evidence but cannot close the assembled owner claims alone.

Required bounded counterfactuals include:

1. old real plan + valid-but-different resealed release authority -> refuse/stale, no transfer;
2. state/proof/topology damage after planning/revalidation but before final session certification -> refuse before mutation;
3. same-name/same-kind target replacement after ordinary revalidation but before final P7 target check, for file and directory -> refuse, replacement survives;
4. capability lifetime continuity from certification to first mutation and closed-session rejection before any syscall, including fd reuse simulation/forcing where practical;
5. multi-action monotonic shrink and interrupted retry;
6. mutation-time contradiction -> same-attempt invalidation; unrelated attempt may continue;
7. once-per-session proof-map materialization and no authority widening through cached lookup;
8. all four terminal outcomes through real cleanup settlement;
9. one success + later no-change refusal -> `partial` with correct collections/bytes;
10. recursive partial mutation after successful nested removal -> exact bytes, `mutated=true`, `partial`, matching audit;
11. post-mutation durability failure -> current action recorded partial before exception propagation; pre-mutation failure -> no fabricated mutation;
12. wrong-root, basename-only proof, cross-generation copy, nested mount, public attempt-root replacement, and existing P7 concurrency/lock counterfactuals remain green.

### Candidate-bound final acceptance

After the **last executable edit**:

1. run focused R22-R30 P7 namespace/state/proof/root/release-authority/target-identity/capability/mutation/outcome/concurrency counterfactuals;
2. run complete `tests/test_mlff_storage_reset_core.py`;
3. run complete `tests/test_mlff_storage_reset_integration.py`;
4. run affected current-owner P1/P3/P4/P5/P7 plus P6 destructive/current-lifecycle regressions implicated by the common cleanup/result/durability path;
5. run clean maintained-suite `pytest --collect-only -q`;
6. re-derive the affected surface from the assembled candidate and then rerun the complete affected regression/integration set on that exact executable commit/tree;
7. run repository static checks and affected current specification/document validation.

Evidence may be CI, captured command output, or a concise commit/workplan closeout note; no new evidence schema is required. It must identify the executable commit/tree and the actual command/result. A generated-document-only successor does not invalidate executable evidence when independently proven non-executable, but affected documentation validation must cover the delivered documentation successor.

A broader/full behavioral pytest is mandatory only if final impact cannot be bounded confidently or independent repository/release policy requires it.

**Production qualification:** external-DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking. They do not substitute for functional regression/integration.

## Implementation sequence and redesign risks

Treat R30-A through R30-H as one coherent final-apply correction stage; the authority identity, live capability, target identity, contradiction handling, outcome semantics, exception propagation, and byte accounting are coupled.

```text
final-apply correction
  exact release + root + target binding
  + live/unspendable capability
  + monotonic proof semantics
  + same-attempt invalidation
  + once-per-session proof lookup
  + truthful outcomes/post-mutation failures
  + exact action-local bytes
 -> focused real-owner counterfactuals
 -> stage-local affected regression
 -> final affected-surface re-derivation
 -> exact-candidate affected regression/integration + static/docs validation
```

Do not split this into helper-by-helper micro-gates. A redesign trigger is evidence that the supported platform cannot realize the frozen boundary, that the existing public result/accounting contract is incompatible with truthful partial mutation, or that final affected-surface inspection discovers a materially broader owner/consumer dependency. Otherwise repair locally under this plan.

## Handoff closure

Revision 30 is intentionally snapshot-complete for the still-binding **final-apply repair**. The current supplied normative set is:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader frozen owner-driven storage architecture and non-goals;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` — all still-binding final-apply repair semantics and acceptance;
3. `docs/specs/training_data/mlff_storage_management_spec.md` — current product storage contract;
4. `AUTHORITY.md` — canonical navigation/status only.

Revision-26/28/29 authority, closure, and implementation-review files remain provenance/history. **No implementation requirement in this final-apply stage depends exclusively on reading them, Git history, prior conversation, or review prose.**

Snapshot-loss counterfactual: with `.git`, prior chats, and superseded Revision-26/28/29 review files removed, the normative set above still states the protected outcome, owner/trust boundary, release/root/target constraints, capability lifetime, monotonic shrink rule, contradiction invalidation, proof-map scaling rule, four terminal outcomes, post-mutation exception flow, byte-accounting rule, real-owner acceptance boundary, final candidate evidence, preservation/non-goals, and redesign triggers.

**Design/workplan disposition: CLOSED / implementation-ready under Revision 30.**

**Reviewed executable disposition: NO-PASS / bounded implementation repair remains required.**
