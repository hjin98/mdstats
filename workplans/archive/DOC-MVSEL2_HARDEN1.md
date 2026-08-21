---
kind: implementation-workplan
workplan_id: DOC-MVSEL2-HARDEN1
plan_revision: 1
status: READY_FOR_IMPLEMENTATION
protocol_version: 2.0.1
analysis_base_ref: feat/mvsel2-forward-lazy
analysis_base_commit: e24d5168ce01bf2d773339e1a91d5ded4871a57f
assumption_paths:
  - workplans/archive/DOC-MVSEL2_forward_lazy_selector.md
  - release/MLFF_MVSEL2_QUALIFICATION_0.20.242a0.json
  - mdstats/training_data/target_multi_view_selector.py
  - mdstats/training_data/target_multi_view_selector_v2.py
  - mdstats/training_data/target_multi_view_repair.py
  - mdstats/training_data/target_multi_view_repair_v2.py
  - mdstats/training_data/target_multi_view_selection_state_v2.py
  - mdstats/training_data/target_coverage_sparse_forward_view.py
  - mdstats/training_data/target_coverage_sparse_index_store.py
  - mdstats/training_data/campaign_cli.py
  - tests/test_mlff_mvsel2_forward.py
  - tests/test_mlff_mvstate2.py
  - tests/test_mlff_repair2.py
  - tests/test_mlff_mvmigrate2.py
  - benchmarks/mlff_mvsel2_production_density_2026-08-18.json
  - benchmarks/mlff_mvstate2_repair2_production_2026-08-18.json
architecture_refs:
  - docs/arch_manuals/mlff_training_data_architecture.md
  - docs/arch_manuals/mlff_training_data/50_target_multiview.md
  - docs/arch_manuals/mlff_training_data/60_execution_performance.md
spec_refs:
  - docs/specs/training_data/mlff_target_data2c_mvsel2_forward_lazy_chain_spec.md
expected_change_paths:
  - mdstats/training_data/target_multi_view_repair_v2.py
  - mdstats/training_data/target_multi_view_selector_v2.py
  - mdstats/training_data/target_multi_view_selection_state_v2.py
  - mdstats/training_data/target_coverage_sparse_index_store.py
  - mdstats/training_data/campaign_cli.py
  - tests/test_mlff_repair2.py
  - tests/test_mlff_mvstate2.py
  - tests/test_mlff_mvmigrate2.py
  - tests/test_mlff_mvsel2_forward.py
  - benchmarks/
  - release/MLFF_MVSEL2_QUALIFICATION_0.20.242a0.json
  - docs/specs/training_data/
  - docs/arch_manuals/mlff_training_data/
  - docs/arch_manuals/mlff_training_data_architecture.md
  - docs/history/mlff/
  - CHANGELOG.md
default_gate_approval: AUTO
---

# DOC-MVSEL2-HARDEN1 — MVSEL2 Post-Implementation Conformance Hardening

## 1. Objective and status

Harden the completed `feat/mvsel2-forward-lazy` implementation so it conforms to the frozen `DOC-MVSEL2` revision-4 architecture and is genuinely merge/release ready.

The core MVSEL2 Phase-A/Phase-B selector design is **accepted and out of redesign scope**. This workplan reopens only the review-discovered G5/G7/G8 integration and qualification gaps:

1. REPAIR2 policy/default and durable-trace drift from REPAIR1;
2. production campaign use of an in-memory full MVIDX1 projection instead of the native forward-only reader;
3. MVSTATE2 library persistence without campaign-level interrupted-selection resume;
4. REPAIR2 replaying selector prefixes instead of consuming MVSTATE2;
5. REPAIR2 proposal-time full-state copies and insufficient large-rung scaling evidence;
6. qualification/evidence binding and broad-suite collection gaps.

The archived revision-4 workplan remains historical evidence and must not be rewritten to hide the failed review. This hardening plan is the new active implementation authority.

## 2. Review diagnosis

### 2.1 REPAIR2 scientific-policy mismatch

Current REPAIR1 defaults are:

- `max_passes_per_shell=2`;
- `max_swaps_per_shell=32`;
- `removal_shortlist_limit=64`;
- `active_shell_only=True`;
- `replacement_rank_inheritance=True`;
- `strict_no_coverage_regression=True`;
- `clustering_score_authority="diagnostic_only"`;
- existing REPAIR1 tolerance validation bounds.

Current REPAIR2 instead defaults to 64 swaps and a 32-item shortlist, and does not mirror all frozen policy fields/validation. Existing trace tests override the swap budget, so they do not prove default-policy equivalence.

### 2.2 Production forward-only path is not wired end-to-end

A correct native forward-only MVIDX1 reader exists and production benchmarks use it. Campaign execution currently receives a full `TargetCoverageSparseIndex` and calls `target_coverage_sparse_forward_view(sparse_index)` for MVSEL2/REPAIR2. Thus the kernel is forward-only but the production build path does not prove the stronger contract that inverse arrays are not mapped/touched for v2 execution.

### 2.3 MVSTATE2 is persisted but not consumed for campaign resume

The selector builder always starts from a fresh state. Campaign code writes rung checkpoints, but an interrupted run without a complete v2 selection record rebuilds selection from rank zero instead of restoring the latest compatible MVSTATE2 checkpoint.

### 2.4 REPAIR2 does not consume MVSTATE2

REPAIR2 constructs a fresh v2 forward state and replays selector prefixes. The production benchmark records this as prefix replay. This is cheaper than v1 inverse replay but violates the frozen selector-to-repair state-reuse design.

### 2.5 REPAIR2 proposal scaling

Each current REPAIR2 proposal clones the full forward mutable state before hypothetical removal/replacement. That cost scales with all family witness multiplicities rather than the bounded candidate/frontier incidence intended by the design. Existing production repair evidence covers only rungs 128 and 256 with zero swaps.

### 2.6 Qualification identity and breadth

The committed production benchmark records identify an earlier code-under-test SHA, while final branch evidence does not explicitly prove that no runtime change occurred afterward. The release qualification also records the full non-slow suite as `BLOCKED_AT_COLLECTION`; therefore final G8/release PASS must be reopened.

## 3. Frozen invariants

This hardening pass MUST NOT change:

- MVSEL2 target sizes, `tau=0.95`, default gain tolerance, FP64 scoring, hard-obligation semantics, bottleneck-family rule, lexicographic criteria, sparse diversity, or UID tie-break;
- Phase-A exact staged forward scoring;
- Phase-B exact rebase, conservative outward-rounded stale bounds, certification rule, or fallback limits;
- MVIDX1 scientific identity/schema or persisted graph content;
- REPAIR1 scientific repair semantics;
- legacy MVSEL1/MVSTATE-REUSE1/REPAIR1 readability;
- target-data coverage/qualification policy;
- unrelated MLFF training/evaluation behavior.

Any need to change those contracts is `DESIGN_REVISION_REQUIRED`.

## 4. Frozen correction design

### 4.1 REPAIR2 policy is a semantic mirror of REPAIR1

`TargetMultiViewRepairPolicyV2` shall mirror every REPAIR1 scientific/algorithmic policy field and default except the v2 authority/schema version. Validation ranges and fail-closed behavior shall match REPAIR1 unless a field is provably execution-only.

At minimum the v2 defaults become:

```text
max_passes_per_shell         = 2
max_swaps_per_shell          = 32
removal_shortlist_limit      = 64
active_shell_only            = True
replacement_rank_inheritance = True
strict_no_coverage_regression = True
clustering_score_authority   = "diagnostic_only"
```

Tolerance defaults and accepted ranges match REPAIR1. If a frozen boolean is hard-coded by the v2 implementation, it must still be represented or explicitly authenticated in policy identity so v2 cannot silently drift later.

### 4.2 Complete repair-trace equivalence

The legacy-equivalence oracle is the complete accepted REPAIR1 trace and terminal order, not only swap UIDs/ranks.

For a shared reference fixture/policy, compare every persisted `TargetMultiViewRepairSwap` field:

- target size, pass/swap index, rank;
- removed/replacement UID and future-displacement rank;
- removed unique coverage and representative loss;
- hard deficit before/after;
- minimum/total coverage before/after;
- representative utility before/after;
- unit balance before/after;
- bottleneck family ID.

Discrete fields must be identical. FP64 fields must use the same authoritative scalar arithmetic and should be bit/equality-identical; if an unavoidable numerical-order difference appears, stop `DESIGN_REVISION_REQUIRED` rather than silently weakening the oracle.

REPAIR2 `bottleneck_family_id` must use the same pre/post-swap semantics as REPAIR1.

### 4.3 Production v2 runtime uses the native forward-only MVIDX reader

MVSEL2 and REPAIR2 build execution shall obtain their runtime graph through `read_target_coverage_sparse_index_forward_view_native_record(...)` (or one equivalent native forward-only authority-preserving path), not by projecting an already materialized full MVIDX1 object.

The full MVIDX1 object may still be loaded later/elsewhere for independent MVQUAL, legacy compatibility, or other consumers, but v2 selection/repair performance measurements and runtime construction must not require inverse-array materialization.

Integration tests shall fail if the v2 build/repair path opens/maps inverse `witness_offsets`/`witness_candidates` arrays.

### 4.4 MVSTATE2 campaign resume

Campaign selection must resume from the highest valid compatible MVSTATE2 rung checkpoint when a complete `target_multi_view_selection_v2` record is absent.

Required behavior:

1. enumerate authorized materializable checkpoint keys for the domain and choose the highest compatible valid checkpoint below/equal to the requested limit;
2. authenticate and restore it with existing MVSTATE2 identity checks;
3. reconstruct the already-selected prefix's `TargetMultiViewSelectionEntry`/rung records deterministically from the selected order using **selected-candidate-only forward replay**, never an all-candidate selection rescan;
4. continue selection from the restored state;
5. if continuation begins in Phase B, rebuild the lazy frontier by one exact deterministic rebase;
6. if the newest checkpoint is stale/corrupt, try earlier compatible checkpoints; if none are valid, rebuild from rank zero;
7. resumed and uninterrupted final plan/entries/rungs/digests must be identical.

Selected-candidate-only replay is execution reconstruction, not new scientific authority, and its work is bounded by the selected prefix's own forward rows.

### 4.5 REPAIR2 consumes MVSTATE2 and obeys divergence rules

REPAIR2 shall accept/use selector checkpoint state at the selector-to-repair boundary.

- At the first materializable repair rung, restore the corresponding compatible MVSTATE2 checkpoint instead of replaying the prefix when available.
- While repair order is still identical to the pure selector order, later pure-selector checkpoints may be reused or current exact state may simply be carried forward.
- **After the first accepted repair swap, do not restore a later pure-selector checkpoint.** Carry the repaired mutable state forward exactly.
- Missing/stale/corrupt MVSTATE2 falls back to selected-candidate-only forward replay, never MVSEL1 eager reconstruction.

Production telemetry must distinguish `mvstate2_restore`, `selected_prefix_forward_replay`, and post-divergence carried state.

### 4.6 REPAIR2 proposals are no-copy analytical hypotheticals

Do not clone full witness state for each removal proposal.

Exploit the already-frozen removal admission invariants:

- removals are zero-unique, so removing one selected candidate does not reduce family coverage;
- removals are hard-safe, so removing it does not increase hard deficit;
- therefore current-state hard/coverage replacement frontiers remain valid under the hypothetical removal;
- only pair-specific representative/diversity values and correlation-unit balance need hypothetical correction.

For each shortlisted removal:

1. mark its witnesses using bounded reusable stamp/epoch scratch per family;
2. compute the replacement hard/coverage frontier on demand from forward rows without mutating/copying global state;
3. apply correlation balance using hypothetical removal counts;
4. compute pair-specific representative gain in canonical replacement-row witness order with multiplicity `m-1` on witnesses shared with the removed row and `m` elsewhere;
5. compute diversity with the same hypothetical multiplicity correction;
6. evaluate the exact frozen repair objective/ties analytically;
7. choose the winning proposal deterministically;
8. mutate the real state exactly once by deselecting the accepted removal and selecting the accepted replacement with a score recomputed in the actual post-removal state.

Reusable scratch is execution-only and must not enter scientific identity. There shall be zero full `TargetMultiViewForwardStateV2` copies per rejected proposal.

## 5. Gate sequence

| Gate | Approval | Initial status | Purpose |
|---|---|---|---|
| H0 REVIEW-BASELINE | AUTO | PENDING | freeze review findings and add regression tests that fail current branch |
| H1 REPAIR2-SEM1 | AUTO | PENDING | exact REPAIR1 policy/default/trace fidelity |
| H2 MVIDX-FWD-RUNTIME1 | AUTO | PENDING | native forward-only production selector/repair runtime path |
| H3 MVSTATE2-RESUME1 | AUTO | PENDING | campaign interrupted-selection resume and repair checkpoint reuse |
| H4 REPAIR2-SCALE1 | AUTO | PENDING | no-copy exact proposal scoring and production-rung scaling |
| H5 QUAL-HARDEN1 | AUTO | PENDING | final committed-code tests, broad suite, production/e2e qualification |
| H6 CLOSEOUT-HARDEN1 | AUTO | PENDING | refresh normative/release evidence and archive hardening plan |

## 6. H0 — REVIEW-BASELINE

**Goal:** convert every review blocker into an executable regression before changing runtime behavior.

**Work:**

- verify `e24d5168ce01bf2d773339e1a91d5ded4871a57f` is the analyzed implementation ancestor;
- add tests that expose current default-policy mismatch;
- extend legacy repair-trace comparison to all persisted fields;
- add campaign-path sentinel tests proving current v2 orchestration does not yet use native forward-only restore/resume;
- add a campaign interrupted-selection fixture demonstrating current rebuild-from-zero behavior;
- add a repair fixture that detects full-state copy/replay telemetry where appropriate.

**Acceptance:** each identified defect is reproducible by a focused test or source/runtime sentinel, with failures attributable to the diagnosed contract rather than unrelated environment state.

## 7. H1 — REPAIR2-SEM1

**Goal:** restore exact REPAIR1 semantic policy and trace fidelity.

**Acceptance:**

- V1/V2 default policy fields and validation semantics match except authority/schema identity;
- default-policy non-empty repair fixtures produce identical complete swap records and terminal orders;
- explicit-policy fixtures remain schedule invariant;
- `bottleneck_family_id` and all objective fields have identical historical semantics;
- no MVSEL1 eager mutation/inverse dependency is reintroduced.

If exact complete trace equality cannot be achieved without changing scientific semantics, stop `DESIGN_REVISION_REQUIRED`.

## 8. H2 — MVIDX-FWD-RUNTIME1

**Goal:** make the actual campaign MVSEL2/REPAIR2 execution path forward-only at storage/runtime level.

**Acceptance:**

- production v2 build/repair obtains MVIDX execution state from the native forward-only reader;
- inverse-array open/map sentinels remain untouched during v2 selection/repair build;
- MVIDX1 content/digests and legacy readers remain unchanged;
- independent qualification may load full MVIDX1 only outside the measured v2 execution boundary;
- cold/warm forward-only restore benchmark remains authenticated and reports inverse arrays unmapped.

## 9. H3 — MVSTATE2-RESUME1

**Goal:** make MVSTATE2 a real production continuation boundary for both selection and repair.

**Acceptance:**

- an intentionally interrupted campaign resumes from the highest valid checkpoint rather than rank zero;
- resumed and uninterrupted selection plans are identical in complete entries/rungs/content digest;
- corrupt/stale newest checkpoint falls back to an earlier valid checkpoint, then to exact rank-zero rebuild if necessary;
- Phase-B continuation performs an exact frontier rebase after restore;
- REPAIR2 consumes an MVSTATE2 checkpoint at the selector-to-repair boundary when valid;
- after first repair divergence, later pure-selector checkpoints are never restored;
- fallback selected-prefix forward replay is explicit, bounded, and never uses v1 eager state.

## 10. H4 — REPAIR2-SCALE1

**Goal:** eliminate proposal-time full-state copies and qualify repair at the rungs relevant to production.

**Acceptance:**

- rejected repair proposals perform zero full forward-state clones;
- proposal evaluation follows the no-copy analytical algorithm in section 4.6;
- accepted swap trace remains exactly equal to the H1 oracle fixtures;
- default-policy production repair is measured through every materializable rung up to 16,384 on the 36,408-candidate/165-family production graph, or is marked BLOCKED with the exact external prerequisite rather than PASS;
- evidence records rung wall time, proposals/removal shortlist, swaps, selected-prefix restore/replay mode, peak/current RSS, and inverse-array access status;
- repair completes under `StageResourceScope` without unbounded memory/object growth;
- combined measured/projected MVSEL2 + checkpoint/resume + REPAIR2 chain retains at least the original **10x** performance improvement requirement versus the same-host MVSEL1 full-order baseline/projection.

If large-rung exact repair cannot meet bounded-resource execution without a different algorithmic design, stop `DESIGN_REVISION_REQUIRED`.

## 11. H5 — QUAL-HARDEN1

**Goal:** bind correctness/performance evidence to the actual corrected code and remove release-qualification ambiguity.

**Work and acceptance:**

- run focused MVSEL2/MVSTATE2/REPAIR2/MVMIGRATE tests;
- run adjacent v1 MVIDX/MVSEL/MVSTATE/REPAIR/MVQUAL/campaign-store regressions;
- resolve the prior full non-slow collection blockers (`psutil` environment/import handling and the legacy top-level test-helper import) without unrelated dependency churn;
- run the full non-slow suite, or record a genuinely external blocker as BLOCKED rather than passing H5/H6;
- rerun production selector and state/repair benchmarks when runtime code changed;
- record the exact **code-under-test commit SHA** in every benchmark/qualification artifact;
- after evidence is generated, later commits may contain only evidence/docs/closeout changes; any subsequent runtime/test behavior change invalidates the prior qualification and requires rerun;
- confirm clean wheel build/install/import and v2 modules/records, with `workplans/` excluded from distribution;
- preserve GPU status as `DEFERRED_NOT_RUN` unless genuinely executed.

There is no GitHub-CI requirement if the repository has no configured checks, but absence of CI must not substitute for the locally executed qualification matrix above.

## 12. H6 — CLOSEOUT-HARDEN1

**Goal:** make permanent authority and release evidence truthful after hardening acceptance.

**Work:**

- update the current MVSEL2 chain specification for actual resume/native-forward/repair-state behavior;
- update Part V/VI architecture only for accepted implemented state, with no gate chronology;
- rebuild assembled architecture Markdown/PDF/provenance and the changed specification PDF/provenance;
- visually/content-verify required PDFs;
- append a concise correction note to history/changelog/release notes if behavior/evidence changed materially;
- refresh `release/MLFF_MVSEL2_QUALIFICATION_0.20.242a0.json` so G5/G7/G8/hardening status, code-under-test SHA, benchmark digests, broad-suite status, and deferred GPU state are exact;
- update/remove stale `workplans/active/DOC-MVSEL2_REPO_HANDOFF.md` coordination text;
- record the completed hardening workplan SHA-256 and archive this plan only after all mandatory gates PASS.

**Acceptance:** permanent specifications/architecture match corrected code; qualification claims match executed evidence; no active coordination artifact claims the original implementation is complete while hardening remains unresolved.

## 13. Non-goals

Do not:

- redesign MVSEL2 scoring/lazy certification;
- change target sizes/coverage/tolerances or REPAIR1 scientific policy;
- remove MVIDX1 inverse storage (MVIDX2 remains separate);
- introduce approximate/stochastic selection or repair;
- add GPU selector/repair authority;
- redesign global scheduler/NUMA behavior;
- change MACE training/evaluation policy;
- perform unrelated dependency modernization.

## 14. Design-revision triggers

Stop `DESIGN_REVISION_REQUIRED` if implementation would require:

- any change to MVSEL2 frozen scientific selection semantics;
- any change to REPAIR1 scientific repair semantics or default policy;
- relaxing complete repair-trace equivalence rather than reproducing historical scalar authority;
- changing MVIDX1 scientific schema/content to expose the native forward path;
- persisting complete candidate gain arrays or lazy heap authority in MVSTATE2;
- synthesizing repaired state from a later pure-selector checkpoint after repair divergence;
- approximate/stochastic repair to meet scale requirements;
- failure to retain the existing 10x end-to-end performance floor under bounded resources;
- destructive migration of legacy records rather than explicit compatibility/rebuild.

Use `STALE_WORKPLAN` if the implementation branch materially moves beyond the analyzed code before hardening begins.

## 15. Final closeout checklist

- [ ] H0-H6 statuses/evidence recorded honestly.
- [ ] REPAIR2 defaults/validation mirror REPAIR1 scientific policy.
- [ ] Complete persisted repair trace and terminal order match the legacy oracle.
- [ ] Production MVSEL2/REPAIR2 runtime uses native forward-only MVIDX restore.
- [ ] Campaign interruption resumes from MVSTATE2.
- [ ] REPAIR2 consumes MVSTATE2 before divergence and never restores pure state afterward.
- [ ] Rejected repair proposals perform no full forward-state copies.
- [ ] Production repair qualification reaches all materializable rungs through 16,384 or hardening remains BLOCKED.
- [ ] Combined v2 chain retains >=10x performance improvement.
- [ ] Full non-slow suite executes successfully or final status remains BLOCKED.
- [ ] Benchmarks/qualification bind the corrected code-under-test SHA.
- [ ] Clean wheel/install qualification passes; workplans remain excluded.
- [ ] Specs/architecture/history/changelog/release evidence are synchronized.
- [ ] Required Markdown/PDF/provenance artifacts pass parity and visual checks.
- [ ] GPU qualification remains explicitly DEFERRED unless actually executed.
- [ ] Completed workplan SHA-256 is recorded and this plan is archived only after PASS.

## 16. Implementation start instruction

Codex continues on **`feat/mvsel2-forward-lazy`** and starts at **H0 REVIEW-BASELINE**. Gates are `AUTO`: after objective PASS, record concise evidence and continue. Stop only on FAIL that cannot be corrected locally, BLOCKED, `STALE_WORKPLAN`, `DESIGN_REVISION_REQUIRED`, an irreversible/external action requiring approval, or a genuinely unresolved user decision.
