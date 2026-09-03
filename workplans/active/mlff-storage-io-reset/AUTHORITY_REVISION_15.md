---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 15
status: reopened
amended_date: 2026-09-01
current_authority_pointer: true
reviewed_candidate_head: 0d91ce50d7ca7cad65657c90ba17a9ecfd0ad4ee
reviewed_candidate_tree: 81b314680f7333160081c07b08afc64025d22ba4
reviewed_executable_commit: e7cd824070a6bd7fb3fb83751d2dde185acf0c16
reviewed_executable_tree: 51bab072d871c9bcef8271b01def1f82c2cad3c5
review_verdict: NO-PASS
authoritative_rework_amendments:
  - STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md
  - STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md
  - STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_DESIGN_CLOSURE_AMENDMENT.md
  - STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_2.md
precedence: this authority supersedes earlier mlff-storage-io-reset authority pointers; the current supplied contract is STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md + STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md + AUTHORITY_REVISION_11.md + STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md + STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md + STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_DESIGN_CLOSURE_AMENDMENT.md + STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_2.md + this authority pointer; later repair amendments control where they explicitly narrow or correct earlier repair text; the frozen parent target-size V7 workplan remains the scientific and architectural verdict
---

# Storage/I-O reset package authority — revision 15 implementation review reopen

## Verdict

The reviewed executable implementation is **NO-PASS / reopened**.

The Revision-14 design remains accepted. The new candidate closes most prior implementation-review findings, but independent source review found seven remaining executable correctness/recovery/concurrency/durability gaps plus missing final executable acceptance evidence. These findings are implementation nonconformance and affected-surface consequences; they do not justify redesigning the owner-driven storage architecture.

Reviewed executable candidate:

```text
commit e7cd824070a6bd7fb3fb83751d2dde185acf0c16
tree   51bab072d871c9bcef8271b01def1f82c2cad3c5
```

Reviewed branch head:

```text
commit 0d91ce50d7ca7cad65657c90ba17a9ecfd0ad4ee
tree   81b314680f7333160081c07b08afc64025d22ba4
```

The head-only delta is documentation/PDF regeneration and does not close the executable findings.

## Current implementation contract

Implementation must read these supplied artifacts together:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md`;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md`;
3. `AUTHORITY_REVISION_11.md` for archive locator/crash-durability corrections;
4. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md` for R12 findings;
5. `STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md` for R13 corrections;
6. `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_DESIGN_CLOSURE_AMENDMENT.md` for R14 subtree/restore-container corrections;
7. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_2.md` for the exact Revision-15 implementation blockers and repair contract;
8. this authority pointer.

Earlier authority revisions are provenance only.

## Remaining blocking surfaces

The exact requirements and acceptance cases are in the Revision-15 reopen amendment. In summary:

1. **Protected cold-authority reauthentication:** reclaim/restore currently verify the archive before owner/storage locking and can consume an old in-memory manifest during mutation. The exact catalog/manifest/blob representation must be rebound and reauthenticated inside the protected consequential window before hot deletion or restore installation.
2. **Dedup canonical-source synchronization:** P5 run activity synchronization is derived from replacement action paths, while a canonical source may be in another historical run root. Every canonical source owner/run must be synchronized and freshly authorized too.
3. **Restore parent identity:** restore binds parent path/type/mode constraints but not the exact existing parent inode/device chain, so a same-path ordinary-directory replacement can evade stale-plan detection.
4. **P5 partial reclaim recovery:** closed-run certification still requires a hot terminal evidence file. If partial archive reclamation removes that terminal member first, a fresh process can no longer certify the run and cannot resume reclaiming the remaining represented hot members.
5. **CampaignStore maintenance split/serialization:** event pruning and VACUUM remain coupled; any excess event can cause an unconditional full rewrite, and `CampaignStore.compact()` still relies on a sole-writer assumption. Pruning and benefit-gated VACUUM must be separate owner decisions under real SQLite serialization.
6. **Actual SQLite read-only observation:** `CampaignStore(create=False)` prevents initialization but `_connect()` still opens a normal writable SQLite connection. Observational owner access must be technically read-only at the database boundary.
7. **Dedup crash durability:** hardlink alias publication uses `os.replace()` without persisting the destination parent directory before recording completion/audit.
8. **Acceptance evidence:** on the exact executable candidate, GitHub-visible execution evidence establishes only the documentation workflow. The required storage/P1-P7 regression and assembled real-owner integration execution has not been established; source test files do not substitute for executed evidence.

## Preserved conforming implementation

Do not regress or rewrite still-conforming work merely because the plan remains open. Preserve the substantial accepted implementation, including:

- invocation-local authorization and action-scoped policy identity;
- observational command routing/non-creating control-plane behavior;
- cross-owner dependency closure, graph-integrity checks, and relevant currentness identities;
- real P5 run activity lease and deterministic owner lock order;
- conservative frame-cache retention;
- R14 closed-subtree/per-descendant authorization and unexpected-descendant retention;
- archive root narrowing, hostile-input bounds, locator containment, self-contained owner/member manifests, immutable representation identities, and create-once immutable catalog fields;
- direct dedup realization with no persistent CAS and external-hardlink canonical protection;
- bounded normal reporting, bounded explicit deep audit, nonadditive physical accounting, and complete/ambiguous census;
- bounded terminal-journal lifecycle and uncataloged archive-residue ownership;
- restore's no-implicit-metadata-mutation behavior for pre-existing containers;
- production-qualification deferral.

## Repair sequence

Continue the existing sequence; do not create another lifecycle or restart accepted P1-P7 work:

```text
R12-S0  observational owner access + P5 terminal proof + CampaignStore maintenance semantics
R12-S1  archive representation binding + canonical dedup synchronization + restore parent identity
R12-S2  protected archive reauthentication + partial-reclaim recovery + dedup durability + SQLite maintenance realization
R12-S3  documentation/public-contract reconciliation and affected maintenance/recovery tests
R12-S4  assembled real-owner integration + fresh final affected regression/evidence
```

Stage-local semantic/conformance plus affected-regression functional closure is required after each material executable stage before proceeding to dependent work.

## Final closure gate

A future PASS requires a single new assembled executable candidate that:

- satisfies every still-binding R12-R15 source/conformance obligation;
- executes focused regression for each Revision-15 repair;
- executes the full storage reset core and integration suites;
- executes affected P1/P3/P4/P5/P7 currentness/publication/restart/retention tests;
- performs final affected-surface re-derivation and fresh affected regression/integration after all executable edits;
- runs repository-required CPU-safe broader/full checks where impact cannot be bounded confidently;
- records truthful command/result/candidate identity proving the required checks actually ran;
- returns for independent Software Design acceptance review.

A test source file or benchmark artifact without execution remains insufficient evidence.

Full external-DFT scientific qualification, long GPU production qualification, and environment-specific HPC/storage qualification remain deferred under the frozen parent/P7 authority and are not repair gates.

## Authority boundary

No target-size science, P2 statistical rule, P3/P4 currentness rule, P5 CV/final-production science, P7 qualification/locked/release science, or frozen parent V7 verdict is reopened.

**Disposition:** workplan **reopened / NO-PASS under Revision 15**. Repair only the bounded remaining implementation surfaces, preserve the accepted R12-R14 architecture and conforming code, proceed through R12-S4, then return with executed acceptance evidence on the final candidate.