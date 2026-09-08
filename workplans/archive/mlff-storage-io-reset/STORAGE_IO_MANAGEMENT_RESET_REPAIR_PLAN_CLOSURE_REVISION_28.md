---
kind: implementation-workplan
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R28
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: closed-implementation-ready
supersedes_revision: 27
reviewed_executable_commit: f8bd22fcb5d1b5b62246b0ca17653e6b31191a51
reviewed_executable_tree: 928e9507ecac84040e1604ed5949f03440044740
scope: final bounded repair-plan reconciliation after independent review of Revision 27
---

# Storage/I-O reset repair-plan closure — Revision 28

## Objective and protected concerns

Revision 28 closes the remaining design/workplan gaps in the bounded Revision-27 rework. The protected product outcome remains unchanged: destructive P7 cleanup may act only on released scratch that the real P7 owner freshly authenticates, authority must remain descriptor-pinned through mutation, storage execution/audit results must state exactly what happened, interrupted cleanup must remain safely resumable, and no repair may reopen the accepted P1-P7 scientific/currentness architecture or the already-conforming R26 historical-test retirement.

Revision 26 remains the accepted storage architecture/mutation basis. Revision 27 correctly identified the closed-descriptor certification gap and false `complete` accounting, but its repair wording was still incomplete in three material ways:

1. a boolean removal result cannot distinguish **no-change refusal** from **partial mutation followed by refusal**; both the common certified-subtree helper and descriptor-relative recursive deletion can make some authorized removals before a later contradiction stops the enclosing action;
2. the released P7 action does not yet expose the exact released-state/proof authority identity through the plan's existing owner-state binding, so “verify planned identity” is underspecified;
3. repeated final certification must distinguish hostile/unsupported authority expansion from **monotonic shrinkage caused by earlier successful storage actions or an interrupted prior cleanup**. Requiring full topology equality after every action would make correct multi-action cleanup self-stale.

These are bounded storage-apply contract corrections. No new persistent state, descriptor ledger, inode registry, state machine, or kernel-specific deletion primitive is justified.

## Engineering envelope and frozen product design

The following remain frozen:

- one continuous no-follow P7 namespace/state/proof/topology owner for storage-facing P7 authority;
- supported-owner synchronization order already established by the storage/P5/P7 locks;
- Python `>=3.10` support;
- descriptor-relative, no-follow top-level file removal and recursive directory removal;
- generation-scoped proof binding and exact typed-node certification;
- workspace-wide fail-closed behavior for unresolved P7 state;
- bounded observational reporting: exact proof/topology work is consequential-plan/apply work, not ordinary report cost;
- the R26 threat boundary: descriptor-pinned owner ancestry and fd-relative mutation are required, but the product does not claim a nonexistent atomic inode-compare-and-delete primitive against an arbitrary same-UID process racing the exact final POSIX directory-entry syscall;
- R26 test/tool retirement, CampaignStore, P5 typed proof, archive/dedup/restore/control-plane architecture, and P1-P7 scientific/currentness semantics remain closed.

The final P7 destructive authority is an **ephemeral capability**, not persisted state. A planning/resnapshot record may constrain what the action is allowed to target, but the mutation owner must reacquire and authenticate the live P7 attempt itself under the already-held owner synchronization.

## Implementation obligations

### R28-A — bind the exact released P7 authority into the immutable plan

**Concern / rationale.** `StoragePlan` already claims to bind each target's owner state identity, but the certified released-attempt scratch views currently leave `state_identity` empty. A state/proof replacement that remains released and happens to expose the same paths/kinds can therefore evade the intended owner-state binding.

**Required end state.** Every certified released P7 scratch action carries a derived, non-persistent owner authority identity sufficient to bind the exact released authority used to plan it.

**Required consequences / constraints.**

- Derive the identity from the real P7 owner records, at minimum the authenticated attempt-state `content_digest` and the authenticated v3 released-proof `content_digest`, together with the generation/attempt binding when needed to make the value unambiguous.
- Feed that identity through the existing `OwnerArtifactView.state_identity` -> `PlannedAction.owner_state_identity` -> owner-binding/revalidation machinery, or an engineering-equivalent existing binding field. Do not create a parallel persistent registry.
- The final P7 mutation owner re-derives the same authority identity from the state/proof read on its retained descriptor and refuses if it differs from the plan-bound expectation.
- Root `(device,inode)`, target filesystem identity, generation-scoped locator, and typed topology remain independent constraints; this identity does not replace them.

**Acceptance evidence.** With an otherwise valid released attempt, replace/reseal state+proof to a different valid authority identity while preserving the same released target names/kinds. The old plan must stale/refuse rather than silently authorize the replacement authority.

### R28-B — final P7 authority session: certify and mutate on one live descriptor capability

**Concern / rationale.** A certification made on a descriptor that is later closed cannot be the final destructive capability.

**Required end state.** Under the already-held storage/P5/P7 synchronization, the final P7 owner performs:

```text
strict attempt reacquisition
  -> retain attempt descriptor/capability
  -> authenticate current attempt state on that descriptor
  -> read/validate/bind current released proof on that descriptor
  -> observe and certify current typed topology on that descriptor
  -> compare exact plan-bound release/root/target constraints
  -> mutate target only through that retained descriptor and no-follow child descriptors
  -> close descriptors after terminal disposition
```

**Required consequences / constraints.**

- A prior planning/resnapshot `certified_nodes` set is not final destructive authority and must not be passed into the final mutation primitive as if it were.
- The existing fd-relative file/directory mutation machinery should be reused rather than duplicated.
- For multiple released actions belonging to one attempt, implementation may either retain one attempt-scoped authority session or reacquire per action. Whichever realization is chosen must preserve the same-capability requirement and must not introduce an avoidable full-tree rewalk per member when an equivalent bounded attempt-scoped realization is available.
- If a mutation-time contradiction indicates external namespace/topology interference, do not widen authority or retry until convenient. Stop or refuse the affected remaining action(s) according to the truthful outcome rules below.

**Acceptance boundary.** Use the real storage executor, real synchronization, real P7 owner, and real descriptor-relative mutation. Test instrumentation may observe opens, closes, state/proof reads, certification, and destructive transitions below these owners, but may not replace the owner's authorization decision.

**Anti-proxy constraint.** Raw integer file-descriptor equality is not sufficient evidence: an OS may reuse the same integer after close/reopen. The test must prove lifetime continuity of the certifying capability (for example by instrumenting open/close ownership or an attempt-session object) through the first destructive transition.

### R28-C — monotonic released-topology shrink is valid; authority expansion is not

**Concern / rationale.** The v3 proof records the released attempt's full typed topology. After storage removes one certified member, later final checks necessarily see a smaller live tree. Treating that expected shrink as plan drift would make multi-action and retry cleanup self-invalidating.

**Required end state.** Fresh final certification uses the released proof as an upper bound on owner-authored topology, not a requirement that every originally recorded node still exists.

**Required consequences / constraints.**

- Every **observed** live descendant must still be present in the proof with the exact recorded kind and must not cross a mount/symlink/special-node boundary.
- Missing proof-recorded nodes are allowed as monotonic absence; they do not grant authority to any new node.
- A planned target that is already absent is an idempotent terminal outcome, not reclaimed work performed by this execution.
- Newly appeared descendants, kind changes, substituted authority roots, changed released state/proof identity, or other proof contradictions refuse the affected destructive action.
- Interrupted cleanup remains resumable from the same unchanged released proof: already-removed members do not make the surviving certified subset unauthorizable.

**Acceptance evidence.** A bounded multi-member released attempt must allow action 1 to remove one certified member and action 2 to remove a different surviving certified member without self-staling solely because action 1 shrank the live tree. A fresh retry after an injected partial/interrupted cleanup must likewise reclaim remaining certified members. Additions/kind changes must still refuse.

### R28-D — replace lossy `bool + reason` mutation semantics with truthful terminal outcomes

**Concern / rationale.** `False` currently conflates materially different states. `remove_certified_subtree()` can remove individually authorized members and then return `False` because the container is retained; descriptor-relative recursion can likewise remove earlier children before a later race/contradiction stops the action. Mapping every `False` to `refused` would therefore be as false as the current mapping of every normal return to `completed`.

**Required end state.** Cleanup removal helpers return or expose a structured internal terminal outcome that distinguishes at least:

```text
removed                 # requested target removed by this execution
already_absent          # desired terminal state already held; no mutation credited
refused_no_change       # owner withheld mutation; nothing changed
partial_change_refused  # some authorized mutation occurred, then the action was stopped/refused
```

Equivalent naming/representation is delegated. Reason-string parsing is forbidden as the semantic discriminator.

**Required consequences / constraints.**

- Apply this truth model to the P7 released-member remover, `remove_certified_subtree()`, and the generic cleanup `remove_durably()` path wherever their current normal return can mean absence/refusal/partial change.
- `removed` enters completed actions and credits only bytes actually attributable under the existing storage size metric.
- `already_absent` may count as a terminally satisfied completed action, but credits **zero** reclaimed bytes for this execution.
- `refused_no_change` enters refused actions, credits zero bytes, and yields execution `refused` when no action mutated/succeeded.
- `partial_change_refused` must make the execution `partial` even if it is the only planned action. The returned/audited action evidence must state that mutation occurred before refusal; it may not masquerade as either a clean completion or a no-op refusal.
- Reclaimed-byte accounting must never credit the full planned action size when only a subset was removed. Partial branches must report only substantiated removed bytes under the existing metric; if the current helper lacks the information, collect it before unlink rather than inventing it after deletion.
- A mixture of completed and refused/partial actions remains `partial`; only all-terminal-success actions produce `complete`.
- Audit-publication failure semantics remain unchanged.

**Acceptance evidence.** Through the real cleanup executor, cover: unsupported dir-fd with no mutation -> refused; already-absent target -> terminal success with zero reclaimed bytes; one success plus one no-change refusal -> partial; a certified-subtree or injected descriptor-recursion case that deletes at least one member before a later refusal -> partial with explicit mutation evidence and no full-size over-credit.

### R28-E — proxy-proof final tests

Preserve the corrected R26 wrong-root, basename-only-proof, nested-mount, cross-generation, public-path-swap, and interruption tests. Add/repair only the bounded final seams:

- capability-lifetime continuity from final state/proof/topology certification through destructive transition, not raw fd-number equality;
- valid-but-different released state/proof identity stales/refuses an old plan;
- invalid/tampered final state/proof/topology refuses before mutation;
- public attempt-path replacement after final capability acquisition never transfers authority to the replacement;
- file and directory top-level actions;
- monotonic multi-action shrink and interrupted retry;
- all four terminal mutation outcomes and truthful execution/audit accounting.

The real executor and real P7 owner remain the semantic boundary. Deterministic filesystem/race instrumentation below them is allowed.

## Implementation authority

### Frozen

- R26 architecture and preservation boundary listed above.
- Exact P7 released authority is plan-bound and final-apply reauthenticated.
- Final destructive certification and mutation share a live descriptor capability.
- Live topology may shrink monotonically but may never expand or change kind under old authority.
- Mutation results distinguish success, already-terminal absence, no-change refusal, and partial-change refusal truthfully.
- No full planned-byte credit for absence or partial removal.
- Existing public report remains bounded.

### Delegated

- Internal type/enum/dataclass names for removal outcomes.
- Whether multiple P7 actions use one attempt-scoped retained session or equivalent per-action sessions, provided correctness and bounded work are preserved.
- Local helper boundaries and exact instrumentation hooks.
- Backward-compatible representation details inside execution/audit action entries, provided existing consumers remain valid and the semantic outcome is explicit.

### Reopen only on evidence

Reopen only the affected surface if the supported Python/POSIX interfaces cannot implement the frozen descriptor-capability boundary without changing the supported platform contract, or if an existing external/public consumer requires an execution-result schema that cannot represent truthful partial mutation without an incompatible migration. Do not reopen because another implementation style is merely more convenient.

## Affected surface and task-specific acceptance

Initially affected executable surface is bounded to:

- `mdstats/training_data/qualification/store.py` final released-attempt authority/mutation boundary;
- `mdstats/training_data/storage/owners.py` P7 released authority identity/view projection;
- `mdstats/training_data/storage/commands.py` cleanup action outcome mapping;
- `mdstats/training_data/storage/executor.py` removal outcome/settlement/reclaimed-byte truthfulness where required;
- `mdstats/training_data/storage/plan.py` only if an existing binding field cannot carry the derived P7 release identity without change;
- focused storage core/integration tests and affected current storage specification wording.

Final implementation must re-derive the affected surface from the assembled candidate.

Mandatory candidate-bound acceptance after the last executable edit:

1. focused R22-R28 P7 namespace/state/proof/root/capability/mutation/outcome counterfactuals;
2. full `tests/test_mlff_storage_reset_core.py`;
3. full `tests/test_mlff_storage_reset_integration.py`;
4. affected current-owner P1/P3/P4/P5/P7 plus P6 destructive/current-lifecycle regressions implicated by the changed common cleanup/result path;
5. clean maintained-suite `pytest --collect-only -q`;
6. final affected-surface re-derivation followed by fresh final affected regression/integration on the exact assembled executable candidate;
7. repository static checks and affected current specification/document validation.

A broader/full behavioral pytest is mandatory only if the final impact cannot be bounded confidently or independent repository/release policy requires it. Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and nonblocking.

Candidate evidence must identify the executable commit/tree actually tested. A later generated-document-only successor does not invalidate executable evidence when its diff is independently proven non-executable; affected documentation validation must still bind to the delivered documentation successor.

## Implementation sequence and redesign risks

Treat R28-A through R28-D as **one coherent final-apply behavior stage**: the release identity, retained capability, monotonic topology rule, and terminal-outcome accounting are coupled and should close semantically plus with focused/affected regression before dependent final evidence work.

```text
R28 final-apply stage
  release authority binding
  + retained descriptor certification/mutation
  + monotonic shrink semantics
  + truthful structured mutation outcomes
  -> proxy-proof focused + stage-local affected regression
  -> final assembled affected-surface re-derivation
  -> fresh affected regression/integration + static/docs validation
```

Do not create micro-gates per helper.

## Handoff closure

The snapshot-loss counterfactual is closed by Revision 28 together with the current supplied Revision-26 storage authority/specification set: the remaining task-specific semantics no longer depend on the implementation-review conversation or on Revision-27 shorthand. Implementation does not need to infer:

- what exact P7 owner identity is plan-bound;
- whether missing proof-recorded nodes after earlier cleanup are acceptable;
- how to classify partial mutation versus no-op refusal;
- how reclaimed bytes behave for absence/partial mutation;
- what constitutes real same-descriptor evidence.

**Design/workplan disposition:** **CLOSED / implementation-ready under Revision 28.**

**Executable disposition:** **NO-PASS / bounded rework remains required.**
