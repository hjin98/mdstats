---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 37
status: reopened
current_workplan: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_16.md
accepted_design: STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md
reviewed_authority_revision: 36
reviewed_executable_commit: 84a2df7779884fa3c0590588366bd139dd6241de
reviewed_executable_tree: 9e57b388a5826ea900edb674decc605605b51fe2
reviewed_repository_head: deaeff0a97a89858694e4f0a31a21a1ad2c8efbb
reviewed_repository_tree: 337c053b1acb4f78f408e3c165dd4342331d0c08
review_verdict: NO-PASS
reviewed_date: 2026-09-03
---

# Storage/I-O reset authority — Revision 37

## Verdict

The Revision-36 workplan was directionally correct and already captured the principal implementation defects, but a final plan-level closure review found two remaining acceptance/contract gaps in the durable-publication family. Revision 37 closes those gaps without reopening the accepted Revision-30 architecture.

The implementation candidate at executable commit `84a2df7779884fa3c0590588366bd139dd6241de`, tree `9e57b388a5826ea900edb674decc605605b51fe2`, remains **NO-PASS**. The later repository head `deaeff0a97a89858694e4f0a31a21a1ad2c8efbb` does not supply a conforming executable repair for these findings.

Revision 30 remains the accepted closed final-apply design. This review does not reopen P1-P7 scientific/currentness semantics, owner architecture, archive/dedup/restore product design, CampaignStore authority, the four cleanup outcomes, Python `>=3.10`, or the accepted POSIX threat boundary.

## Current bounded implementation authority

The complete current repair and acceptance contract is:

`STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_16.md`

It supersedes Revision 36 for all still-open implementation and acceptance work while preserving every conforming Revision-30 through Revision-36 decision.

## Remaining gaps closed by Revision 37

### 1. Manifest/catalog publication had a stated end state but insufficient explicit acceptance

Revision 36 correctly required archive phase evidence not to lag a manifest/catalog atomic publication if a later durability/readback step failed. However, its mandatory publication counterfactuals explicitly exercised only blob publication. The implementation uses the same `durable_publish_json()` -> `durable_publish_bytes()` -> `os.replace()` sequence for manifests and catalog entries, so both have the same post-replace failure window.

Revision 37 makes transition-exact manifest and catalog phase propagation an explicit implementation obligation and mandatory real-owner acceptance requirement, with symmetric pre-replace controls.

### 2. Restore-journal publication was omitted from execution mutation truth

Restore publishes a durable nonterminal recovery journal before staging or destination installation. That journal is retained recovery authority, and `durable_publish_json()` can successfully replace it before a later parent-fsync/readback failure escapes. The current engine does not set `result.mutated` at that transition. A restore can therefore leave durable operation state while the executor reports a nonmutating refusal.

Revision 37 requires the initial nonterminal journal and the terminal journal replacement to establish transition truth at their atomic publication boundaries. Destination-directory creation/member replacement remains separately recorded at its own transitions. Journal publication may carry zero created/restored bytes while still making `mutated=true`.

## Preserved Revision-36 blockers

Revision 37 preserves, without weakening:

- exact `durable_unlink` semantics and removal of post-hoc disappearance inference/`TypeError` mutation fabrication;
- archive blob transition truth and hot-reclamation exactness;
- continuous opened parent/child descriptor authority plus final no-follow identity comparison before every consequential fd-relative `rmdir`;
- opened-descriptor mount trust throughout individually-authorized common descent and explicit typed common-member authority;
- leak-free, terminality-safe descriptor/session closure and primary-vs-secondary failure preservation;
- real planner/owner/`StorageExecutor`/audit acceptance with only low-level timing/trust/failpoint injection;
- liveness proof that acceptance-critical injected seams actually execute;
- fresh exact-candidate affected regression/integration/static/document evidence after the last executable/test edit.

## Tooling

Serena, Semgrep, and Hypothesis are optional evidence helpers under Protocol 5.10. Use them where their available capabilities materially improve semantic discovery, variant closure, or state-transition testing; their absence does not waive any required engineering claim and is not itself a blocker.

## Disposition

**Design/workplan:** **CLOSED / implementation-ready under Revision 30 plus the bounded Revision-37 correction.**

**Implementation:** **NO-PASS / reopened under Revision 37.**

External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.
