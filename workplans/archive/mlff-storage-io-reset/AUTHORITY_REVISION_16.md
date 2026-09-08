---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 16
status: reopened
amended_date: 2026-09-01
current_authority_pointer: true
reviewed_authority_head: 4fd0931933a5a57cbc1ed480b6f93a492169a844
reviewed_authority_tree: 8054eac7f883ec3f82403710c7e04bd43b4fecce
reviewed_executable_commit: e7cd824070a6bd7fb3fb83751d2dde185acf0c16
reviewed_executable_tree: 51bab072d871c9bcef8271b01def1f82c2cad3c5
review_verdict: NO-PASS
repair_design_disposition: final-closure-reviewed implementation-ready
precedence: this authority supersedes earlier mlff-storage-io-reset authority pointers; the current supplied contract is STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md + STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md + AUTHORITY_REVISION_11.md + STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md + STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md + STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_DESIGN_CLOSURE_AMENDMENT.md + STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_2.md + STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_16.md + this authority pointer; later amendments control where they explicitly narrow or correct earlier text; the frozen parent target-size V7 workplan remains the scientific and architectural verdict
---

# Storage/I-O reset package authority — revision 16 final repair-plan closure

## Current disposition

The reviewed executable implementation remains **NO-PASS / reopened**. Revision 16 changes no executable acceptance verdict and introduces no new architecture. It completes the Design closure of the Revision-15 repair contract.

The repair contract is now **final-closure reviewed and implementation-ready** under the existing R12-S0 -> R12-S4 sequence.

## Why Revision 16 exists

The final plan challenge found six closure issues that a literal Revision-15 implementation could still mishandle:

1. the conventional `AUTHORITY.md` entrypoint was stale and contradicted the current reopened package state;
2. observational/read-only semantics needed explicit propagation through nested store opens and worker threads, without process-global receipt-mode races;
3. event pruning versus VACUUM needed distinct planned authority rather than only runtime branching;
4. the P5 terminal/member-set proof needed an explicit retained-owner-infrastructure lifecycle outside the reclaimable archive member set;
5. retained-archive protected reauthentication needed all supported storage writers to share the same storage-operation serialization contract;
6. audit-publication failure needed explicit degraded-completion semantics and direct acceptance rather than best-effort swallowing or an impossible absolute audit guarantee.

The exact corrected end states and acceptance cases are in `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_16.md`.

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
9. this authority pointer.

`AUTHORITY.md` is the canonical navigation entrypoint and must agree with this revision. Earlier authority revisions other than the explicitly included Revision 11 are provenance only.

## Preserved implementation target

All conforming R12-R15 work remains preserved. Implementation must repair only the remaining bounded surfaces and must not reopen target-size/CV/publication/qualification/calibration/locked-test/release science for storage convenience.

The key final repair additions are:

- real SQLite read-only access **plus invocation-wide propagation** to nested/worker-thread owner/store/cache opens;
- distinct prune and VACUUM planned authority, with a fresh plan/subplan required before a newly-benefit-positive rewrite;
- a create-once retained P5 terminal/member-set certification anchor that is not itself archive hot-reclaimable;
- one supported-writer serialization discipline for retained catalog/manifest/blob state, making protected archive reauthentication race-closed for package-owned actors;
- explicit operational evidence failure when durable audit publication fails, without rollback or false audited success.

The seven Revision-15 executable blockers remain binding in full: protected archive reauthentication, canonical dedup synchronization, restore parent-chain identity, P5 partial-reclaim certification, split/serialized CampaignStore maintenance, technically read-only CampaignStore observation, and dedup directory-entry durability.

## Final closure gate

A future PASS still requires a single assembled executable candidate that satisfies the complete R11-R16 contract and executes:

- focused tests for every R15/R16 repair;
- stage-local affected regression after each material executable repair stage;
- complete storage reset core + real-owner integration suites;
- affected P1/P3/P4/P5/P7 currentness/publication/restart/retention regression;
- explicit R16 worker-thread observation, prune-vs-VACUUM authority, P5 anchor retention, retained-archive writer serialization, and audit-write-failure counterfactuals;
- final affected-surface re-derivation and fresh regression/integration on the exact assembled executable candidate;
- repository-required CPU-safe broader/full checks when impact cannot be confidently bounded;
- affected static/docs/build checks and truthful candidate-bound execution evidence.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred.

## Authority boundary

No frozen P1-P7 scientific/currentness decision is reopened. The only Design correction in Revision 16 is task-local storage ownership/operation semantics needed to make the already accepted design implementable and unambiguous.

**Disposition:** executable workplan **reopened / NO-PASS**; repair design **final-closure reviewed / implementation-ready under Revision 16**.
