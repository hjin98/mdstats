---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 13
status: reopened
amended_date: 2026-09-01
current_authority_pointer: true
reviewed_repair_authority_head: e093e607ab64fc7c09da58e0695880081dd51997
reviewed_repair_authority_tree: 3e738894c2e8b49ae03a02eed00888ecfc868331
repair_closure_amendment_commit: 6790263ddfbbbb745bd5998e47b59bead7ed18c3
repair_closure_amendment_tree: b9ed1ef86c9cb1bec8bf35d3d13087bdd9868a34
reviewed_executable_commit: 53edc1c75c5b7c9df8f414914534ce915c34f303
reviewed_executable_tree: 8d24e6326b67c38e69a1fe1383be7b975788cac5
review_verdict: NO-PASS
repair_design_disposition: closure-reviewed implementation-ready while workplan remains reopened
authoritative_rework_amendments:
  - STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md
  - STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md
precedence: this authority supersedes earlier mlff-storage-io-reset authority pointers; the current supplied contract is STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md + STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md + AUTHORITY_REVISION_11.md + STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md + STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md + this authority pointer; where the repair-plan closure amendment explicitly corrects R12 it controls; the frozen parent target-size V7 workplan remains the scientific and architectural verdict
---

# Storage/I-O reset package authority — revision 13 repair-plan closure

## Current verdict

The executable storage implementation remains **NO-PASS / reopened**. No new executable candidate was presented after revision 12.

Revision 13 records a second independent Software Design challenge of the **reopened repair plan itself**. That challenge found and corrected additional contract gaps before Implementation resumes. The repair design is now closure-reviewed and implementation-ready, but the workplan is not closed because the required executable repairs and acceptance evidence do not yet exist.

Reviewed executable source remains:

```text
commit 53edc1c75c5b7c9df8f414914534ce915c34f303
tree   8d24e6326b67c38e69a1fe1383be7b975788cac5
```

The revision-12 Design authority head reviewed for this closure pass was:

```text
commit e093e607ab64fc7c09da58e0695880081dd51997
tree   3e738894c2e8b49ae03a02eed00888ecfc868331
```

No target-size/P1-P7 executable source changed between those identities.

## Current implementation contract

Implementation must read the following supplied current artifacts together:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md`;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md`;
3. `AUTHORITY_REVISION_11.md` for archive locator and crash-durable publication constraints;
4. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md` for the first implementation-review repair set;
5. `STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md` for the final repair-plan corrections and R12-B5 dedup simplification;
6. this authority pointer.

Earlier authority revisions are provenance only. No still-binding repair semantic depends on prior chat or Git archaeology.

## Additional blocking surfaces closed in the repair contract

Revision 13 adds precise repair authority for issues not fully captured by revision 12:

- persistent configuration must never grant `apply` authority or redirect an explicitly invoked action/tier;
- policy identity is action-scoped and every public storage knob must have real behavior or be removed/rejected;
- all non-apply report/list/verify/planning/dry-run paths are side-effect-free with respect to managed campaign, owner, cache, currentness, receipt and storage-control-plane state;
- owner graph duplicate/missing dependency state fails closed before consequential planning;
- archive/dedup/restore synchronization is derived from every touched historical/current owner generation, not current generation alone;
- any new owner activity/liveness lease participates in one cycle-free lock order with existing publication barriers;
- the persistent dedup content-store is removed from the accepted target design in favor of direct owner-certified hardlink aliasing, avoiding unnecessary CAS/GC authority;
- a dedup canonical inode may not carry unknown external hardlink ownership;
- restore has an exact owner-bound restore plan with fresh semantic, destination, archive and admission revalidation;
- retained archive authority carries enough immutable owner/member/action material for future fresh-process reclaim/restore without advisory plan files;
- recursive storage traversal does not cross nested mount boundaries implicitly;
- archive/restore/dedup/maintenance admission conservatively bounds actual peak byte and inode/directory-entry amplification;
- archive, reclaim, restore, dedup and actual database maintenance participate in the same truthful durable storage audit contract as cleanup;
- CampaignStore maintenance is independently authorized and benefit-gated, so a stale/refused cleanup cannot still mutate the database as a tail action;
- normal reporting is bounded end-to-end across semantic owner adapters as well as physical metadata; deep audit enforces its resource bound;
- the owner census includes known results/generated/helper/storage-native families or explicitly marks them ambiguous/retained;
- nonterminal restore journals remain recovery authority while terminal journals become bounded diagnostic evidence;
- immutable archive representation/catalog fields are create-once/validate-existing and cannot be rewritten under a retained identity;
- current normative specification/architecture/guide/config/help/README wording must be reconciled to the repaired behavior.

## Design correction from revision 12

Revision 12 IR12-B5 would have formalized the implementation's persistent `.mdstats/storage/content-store` and added storage-owner garbage collection around it. Further review found that this state is unnecessary: Revision 2 permits hardlink deduplication but does not require a persistent canonical object store.

Revision 13 therefore **supersedes only that R12 realization**. The required target is direct same-filesystem hardlink aliasing among freshly authorized immutable campaign members. This removes a durable state owner, garbage collector, recovery surface and physical-byte accounting trap while preserving the accepted dedup product behavior. A persistent CAS may be reconsidered only through the explicit evidence-backed reopen trigger in the closure amendment.

All other R12 findings remain binding.

## Preserved accepted implementation and authority

Do not regress the already-conforming mechanisms unless a local compatible refactor is required by the repair:

- transitive cross-owner dependency closure, especially post-terminal P7 -> P5 checkpoint and waiting-for-reference retention;
- accepted P3 stale-generation no-write/history semantics and P3 retention fence;
- P5/P7 object-pointer publication barriers;
- cleanup's immutable plan -> storage lease -> owner barrier -> fresh resnapshot/revalidation -> physical boundary execution shape;
- external-input and symlink protections;
- archive member/path/locator/expansion validation already implemented;
- durable publication ordering helpers;
- hardlink byte/metadata authentication and atomic replacement mechanics, subject to the new no-external-hardlink canonical-source rule;
- archive catalog/blob/manifest authority and restore staging durability where already conforming;
- production-qualification deferral.

## Rework sequence

Resume the existing R12 sequence; do not create another lifecycle:

```text
R12-S0  recensus/authority/liveness/trust closure
R12-S1  canonical plan/policy/synchronization repair
R12-S2  liveness + direct dedup + archive/control-plane lifecycle repair
R12-S3  reporting + CampaignStore I/O + public-contract reconciliation
R12-S4  assembled real-owner integration + final affected regression
```

`STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md` adds the exact revision-13 obligations and tests to those stages.

Stage-local semantic/conformance and affected-regression closure is required before proceeding to the next dependent stage. Reuse still-valid R12 evidence only where the revised dimension cannot plausibly affect its claim.

## Final closure gate

A future PASS requires a new assembled executable candidate satisfying the full current composed authority and demonstrating, on that same candidate:

- all R12 and R13 source/conformance repairs;
- focused tests for each material repair mechanism;
- stage-local affected regression after each material executable stage;
- real-owner concurrency/authorization/currentness tests rather than owner-bypassing proxies;
- final affected-surface re-derivation and fresh affected regression/integration;
- repository-required CPU-safe broader/full checks where impact cannot be bounded;
- truthful executed command/result evidence;
- independent Software Design acceptance review.

A test file or benchmark artifact existing in source does not prove execution.

Full external-DFT scientific qualification, long GPU production qualification, and environment-specific HPC/storage qualification remain deferred under the frozen parent/P7 authority and are not repair gates.

## Authority boundary

No target-size science, P2 statistical rule, P3/P4 selected/currentness rule, P5 CV/final-production science, P7 qualification/locked/release science, or frozen parent V7 decision is reopened. Revision 13 changes only the storage repair implementation contract and one unnecessary dedup realization choice.

**Disposition:** workplan **reopened / implementation-ready under revision 13**. Implement from R12-S0 through R12-S4, then return for independent closure review.