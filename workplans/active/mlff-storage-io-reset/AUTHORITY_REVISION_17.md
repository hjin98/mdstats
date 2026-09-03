---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 17
status: reopened
amended_date: 2026-09-01
current_authority_pointer: true
reviewed_candidate_head: 8561cad5dced86f9c1089f80aa455ce5a381906f
reviewed_candidate_tree: 69f4ab4625876778b29c67edc6752484871e2983
reviewed_executable_commit: 2e6a2768341f75a87430d1313b7d64a1e85dfd04
reviewed_executable_tree: 681ed2b915bb29f05505eef87fcc83cf8e1c4b99
review_verdict: NO-PASS
precedence: this authority supersedes earlier mlff-storage-io-reset authority pointers; the current supplied contract is STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md + STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md + AUTHORITY_REVISION_11.md + STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md + STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md + STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_DESIGN_CLOSURE_AMENDMENT.md + STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_2.md + STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_16.md + STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_3.md + this authority pointer; later amendments control where they explicitly narrow or correct earlier text; the frozen parent target-size V7 workplan remains the scientific and architectural verdict
---

# Storage/I-O reset package authority — revision 17 implementation review reopen

## Verdict

The reviewed executable candidate is **NO-PASS / reopened**.

Revision 16's global design remains accepted and most R15/R16 executable blockers are now closed. Independent review of the assembled implementation found six bounded source/conformance defects plus missing final executable regression/integration evidence. Exact repair instructions and acceptance cases are in `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_3.md`.

## Current supplied implementation contract

Implementation must read these artifacts together:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md`;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md`;
3. `AUTHORITY_REVISION_11.md`;
4. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md`;
5. `STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md`;
6. `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_DESIGN_CLOSURE_AMENDMENT.md`;
7. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_2.md`;
8. `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_16.md`;
9. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_3.md`;
10. this authority pointer.

`AUTHORITY.md` is the canonical navigation entrypoint and must agree with this revision. Earlier authority revisions other than the explicitly included Revision 11 are provenance only.

## Remaining blocking surfaces

1. **P5 completion-anchor integrity/create-once:** the new retained `run-members.json` is written through a mutable pointer primitive, existing proof verification checks only member names, and consequential readers lack full proof/integrity validation. It must become versioned immutable/create-or-verify owner authority with one validating reader and explicit old-schema handling.
2. **Event-retention policy exactness:** policy/planning accept `sqlite_compaction_maximum_events < 100`, but `CampaignStore.prune_events()` silently clamps execution to at least 100. The resolved bound and execution bound must be identical.
3. **VACUUM predicate freshness:** benefit/admission are checked before the rewrite obtains the writer exclusion on which it may wait. The final benefit predicate must remain valid across that serialization boundary.
4. **Durable audit self-truth:** successful durable audit records currently serialize `audit_published=false` because the flag is set only after append returns. Persisted and returned evidence must agree.
5. **Dedup crash residue:** the pre-rename temporary hardlink lives inside the P5 closed subtree. A hard crash can strand an unexpected descendant with no storage owner and prevent fresh-process certification. Reuse storage-owned staging or an equivalent recoverable owner surface.
6. **Bounded report terminal semantics:** the cheap P5 report prefilter still requires terminal evidence to remain hot even though R16 made the retained anchor the completion authority after terminal evidence goes cold.
7. **Executed acceptance evidence:** the exact executable commit has only the docs check attached; source tests and benchmark JSON do not establish the mandatory storage/P1-P7 regression and real-owner integration execution.

## Preserved implementation

Do not rewrite already-conforming work. Preserve protected archive reauthentication, retained-archive storage serialization, canonical dedup owner synchronization, restore parent inode binding, SQLite read-only observation/context propagation, per-call receipt observation, split maintenance actions, P5 anchor retention outside archive members, dedup directory fsync, explicit unaudited public outcomes, and all unaffected R12-R16 owner/currentness/subtree/archive/report/journal/catalog/admission work.

## Repair sequence

Continue the existing R12-S0 -> R12-S4 lifecycle:

```text
R12-S0  anchor/policy/maintenance/recovery contract correction
R12-S1  immutable validating anchor + exact event policy + serialized VACUUM predicate
R12-S2  dedup crash recovery + truthful stored audit + maintenance race closure
R12-S3  bounded report/public docs reconciliation
R12-S4  all R12-R17 real-owner/failure counterfactuals + fresh final affected regression/integration
```

Stage-local semantic/conformance and affected-regression closure remain required after every material executable stage.

## Final closure gate

A future PASS requires one assembled executable candidate that:

- satisfies every still-binding R11-R17 source/conformance obligation;
- runs focused R17 counterfactuals plus every still-binding R15/R16 focused case;
- runs the complete storage reset core and real-owner integration suites;
- runs affected P1/P3/P4/P5/P7 currentness/publication/restart/retention regression;
- re-derives the final affected surface and runs fresh final affected regression/integration after all executable edits;
- runs repository-required CPU-safe broader/full checks when impact cannot be confidently bounded;
- provides truthful candidate-bound command/CI results establishing those checks actually executed;
- returns for independent Software Design acceptance.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred.

## Authority boundary

No target-size science, P2 statistical rule, P3/P4 currentness rule, P5 CV/final-production science, P7 qualification/locked/release science, or frozen parent V7 verdict is reopened.

**Disposition:** executable workplan **reopened / NO-PASS under Revision 17**.
