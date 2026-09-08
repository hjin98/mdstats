---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 28
status: reopened
supersedes_revision: 27
reviewed_executable_commit: f8bd22fcb5d1b5b62246b0ca17653e6b31191a51
reviewed_executable_tree: 928e9507ecac84040e1604ed5949f03440044740
repair_plan_closure: STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_REVISION_28.md
design_disposition: closed-implementation-ready
executable_disposition: no-pass-reopened
---

# Storage/I-O reset authority — Revision 28

Revision 28 is the current final implementation handoff for the bounded storage repair. It preserves Revision-26 storage architecture, test-retirement policy, single descriptor-bound P7 observation, descriptor-relative mutation machinery, synchronization, and all closed P1-P7 scientific/currentness semantics. It supersedes Revision 27 only where Revision 27 left the final apply/result contract underspecified.

## Frozen corrections

### 1. Exact released P7 authority is plan-bound

A certified released-attempt scratch action must carry a derived owner authority identity based on the authenticated released attempt state and authenticated v3 released proof (at minimum their content digests, with generation/attempt binding as needed). Use the existing owner-state/plan-binding machinery or an engineering-equivalent existing field; create no persistent parallel registry.

The final mutation owner re-derives that identity from the state/proof it reads on its retained attempt descriptor and refuses if the plan-bound authority changed.

### 2. Final certification and mutation share one live descriptor capability

Under the already-held storage/P5/P7 synchronization, the final P7 apply owner strictly reacquires the attempt, keeps that descriptor alive, authenticates current state, reads/binds the current released proof, observes/certifies current typed topology, checks the plan-bound release/root/target constraints, and performs top-level file/directory mutation only relative to that descriptor and no-follow child descriptors.

Planning/resnapshot `certified_nodes` may constrain/revalidate a plan but are not the final destructive authority. Do not pass a closed-descriptor certification into the remover as if it were live authority.

Tests must prove capability **lifetime continuity**, not raw integer fd equality, because a closed descriptor number may be reused by the OS.

### 3. Released topology is monotone-shrinkable

The released v3 proof is an upper bound on P7-authored topology during cleanup. Every observed live descendant must remain proof-recorded with the exact kind; additions, kind changes, symlinks/special nodes, nested mounts, substituted roots, or changed release authority refuse.

Missing proof-recorded nodes are allowed: they may have been removed by an earlier action in the same cleanup or by an interrupted prior cleanup. A planned target already absent is terminally satisfied but contributes zero reclaimed bytes. This preserves multi-action and retry cleanup without granting authority to any new node.

### 4. Mutation outcomes must distinguish refusal from partial mutation

A `bool + reason` result is insufficient because a recursive/certified helper can mutate some authorized members before a later contradiction stops the enclosing action.

The cleanup implementation must distinguish at least these semantic outcomes, with equivalent internal naming allowed:

```text
removed
already_absent
refused_no_change
partial_change_refused
```

Apply the outcome contract across the P7 released-member remover, common certified-subtree removal, and generic cleanup removal path wherever normal returns can represent absence/refusal/partial change.

- `removed`: completed action; credit only actually attributable reclaimed bytes.
- `already_absent`: terminally satisfied; completed with zero reclaimed bytes.
- `refused_no_change`: refused action; zero reclaimed bytes.
- `partial_change_refused`: execution is partial even when it is the only action; returned/audited evidence states that mutation occurred before refusal and credits only substantiated removed bytes, never the full planned size by default.

Reason-string parsing may not determine the semantic outcome.

## Acceptance boundary

Use the real storage executor, real synchronization, real P7 owner, and real fd-relative mutation. Bounded deterministic instrumentation below these semantic owners is allowed.

Required focused counterfactuals include:

- valid-but-different released state/proof authority with unchanged target names/kinds stales/refuses an old plan;
- final state/proof/topology corruption refuses before mutation;
- certifying capability remains open through destructive transition;
- public attempt-path replacement after final capability acquisition transfers no authority;
- both top-level file and directory actions;
- multi-action monotonic shrink and interrupted retry;
- unsupported dir-fd -> no-change refusal;
- already-absent -> zero-byte terminal success;
- success plus refusal -> partial;
- partial recursive/certified mutation followed by refusal -> partial with truthful mutation evidence and no full-size over-credit.

After the last executable edit, run candidate-bound focused R22-R28 tests, full storage core/integration, affected current-owner P1/P3/P4/P5/P7 plus P6 destructive/current-lifecycle regressions, clean collection, final re-derived affected regression/integration, and static/affected current-document validation. Whole-repository behavioral pytest remains conditional on inability to bound impact or independent repository policy. External-DFT, long GPU, and environment-specific HPC/storage qualification remain deferred and nonblocking.

## Preservation and route

Do not reopen R26 historical test/tool retirement, single P7 namespace/view authority, parser/canonical-generation/cross-generation/ambiguity behavior, fd-relative mutation primitives, established synchronization, CampaignStore, P5 typed proof, archive/dedup/restore/control-plane machinery, or P1-P7 scientific/currentness semantics.

Treat the remaining executable work as one coherent final-apply behavior stage:

```text
plan-bound released authority
 + retained descriptor certification/mutation
 + monotonic shrink semantics
 + truthful structured mutation outcomes
 -> proxy-proof focused + affected regression
 -> final affected-surface re-derivation
 -> fresh affected regression/integration + static/docs validation
```

**Design/workplan:** **CLOSED / implementation-ready under Revision 28.**

**Executable:** **NO-PASS / reopened under Revision 28.**
