---
kind: d4-implementation-evidence
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 11
protocol_version: 6.3.0
status: active
created_date: 2026-09-15
branch: design/mlff-pi-train-fps-diversity-restoration
basis_commit: 018e96d867ab3bb3eecbff35f4d0fb75ec1a906b
implementation_commit: dd96ede2
highest_affected_domain: D4
upstream_authority_state: D1_D2_D3_ACCEPTED_UNCHANGED
---

# Revision 11 D4 repair — implementation evidence

This record is **evidence, not authority**. It does not close the workplan; a fresh
independent assembled-candidate D4 re-review is still required.

## 0. Summary

R11-A through R11-H were implemented in the specified order. No fallback selector,
old/new selector router, alternate suffix, compatibility mode, second currentness or
checkpoint store, semantic migration layer, new GC/cleanup owner, or duplicate
advisory-lock implementation was added. Every repair is a relocation, deletion, or
rewiring of an existing owner.

Two findings are routed to the reviewer rather than absorbed locally:

1. **REPAIR2 current-scale cost (§7.3).** Deleting the D2-non-conformant frontier
   shortcut (R11-E) makes REPAIR2 evaluate saturated zero-new-coverage frontiers that
   the pre-fix concretization skipped. On the representative substrate REPAIR2 is now
   **1 h 42 m of a 2 h 19 m** target-order build. This is correct D2 behavior on the
   accepted execution closure (the mature carrier used the same thread-queue proposal
   model), so it is a **performance-design question for D3/D4, not a licence to restore
   the shortcut**.
2. **Post-`N_max` restart replays REPAIR2 (§7.4).** REPAIR2 is not checkpointed, so an
   interruption after the configured shells replays it before the suffix resumes.

Neither finding is a D1/D2 contradiction; no Protocol Challenge is raised.

## 1. Commits and changed files

Implementation commit: `dd96ede2` ("impl: MVSEL2 restoration Revision 11 D4 repair
(R11-A..G)"), on `design/mlff-pi-train-fps-diversity-restoration` from basis
`018e96d8`. 27 files, +1004 / -301.

Product:

| File | Repair |
|---|---|
| `mdstats/training_data/persistence.py` (new) | R11-A: sole `_lock_file_path` / `_FileLock` / `artifact_publication_lock` / `fsync_parent_directory` owner |
| `mdstats/training_data/target_size_execution/persistence.py` | R11-A: primitives removed, imported from the shared owner; no re-export |
| `mdstats/training_data/target_size_execution/__init__.py` | R11-A: stops re-exporting the relocated primitives |
| `campaign_post_selection_runtime.py`, `campaign_target_size_runtime.py`, `post_selection_store.py`, `qualification/runtime.py`, `qualification/store.py`, `replay_pseudolabel.py`, `storage/archive.py`, `storage/control_plane.py`, `storage/dedup.py`, `storage/durability.py` | R11-A: rewired imports |
| `target_order/artifact_store.py` | R11-B: locked strict create-or-verify; destructive `shutil.rmtree(destination)` retry removed; parent fsync after publication |
| `target_order/preparation.py` | R11-C: per-`build_identity` single-flight fence; published stage products fail closed; R11-H: COVREF-PAR1 reference execution scope |
| `target_order/state.py` | R11-C: checkpoint-root mutation ownership documented (no second lock) |
| `target_order/coverage_reference.py` | R11-D: required structural semantic-family completeness, fail-closed |
| `campaign_target_size_runtime.py` | R11-D: target-order structural input requests the frozen family set |
| `target_order/repair.py` | R11-E: `_Frontier.proposal_possible` and the hard_pending/positive-total early exit deleted; `REPAIR2_VERSION` → `configured-shell.v2` |
| `docs/methods/mlff_scientific_method.md`, `docs/methods/mlff_numerical_algorithmic_method.md` | R11-F: superseded `pi_train` construction/qualification text delegated to the scoped owners |

Tests/harness:

| File | Purpose |
|---|---|
| `tests/test_mlff_target_order_real_owner.py` | seven new `real_target_order` falsification tests; feasible assembled-fixture geometry; COVREF-PAR1 equivalence |
| `tests/support/target_order_fixtures.py` | complete frozen eight-family structural catalog plus omission/sparsity knobs |
| `tests/conftest.py` | downstream substitute made module-scoped (see §6.2) |
| `tests/test_mlff_doc_arch1_specification.py`, `tests/test_mlff_data9b3_campaign_cli_specification.py` | R11-F: the eight stale static assertions rebased onto current authority |
| `tests/test_mlff_storage_reset_core.py`, `tests/test_mlff_storage_reset_integration.py` | R11-A: monkeypatch seams remapped to the shared persistence owner |

## 2. R11-A — one shared persistence/fencing primitive

`_lock_file_path`, `_FileLock`, `artifact_publication_lock` and `fsync_parent_directory`
were **moved** (not copied) from `target_size_execution/persistence.py` to
`mdstats/training_data/persistence.py`; all ten internal consumers now import them from
that module, and `target_size_execution` no longer re-exports them.

Structural evidence: `grep -rn "class _FileLock|def artifact_publication_lock|def
fsync_parent_directory" mdstats` returns exactly one definition of each, all in
`mdstats/training_data/persistence.py`.

Out of scope, pre-existing and unchanged: `storage/lease.py` (non-blocking lease
semantics), `_campaign_cli_core.py` (writer lock on an open handle) and
`target_size_execution/coordinator.py` each call `fcntl.flock` inline for their own
purposes. These are not the generic advisory-lock primitive R11-A names, and
consolidating them was not part of this bounded repair; the reviewer may wish to route
them separately.

## 3. R11-B — immutable publication fails closed

`publish_artifact_directory` now builds the attempt directory, then under
`artifact_publication_lock(destination)`: authenticates an existing destination, reuses
it on identical `content_digest` plus passing `verify_existing`, and otherwise raises
`TargetOrderArtifactStoreError` leaving the destination byte-for-byte untouched. The
absent-destination path is one atomic rename followed by `fsync_parent_directory`. The
`shutil.rmtree(destination, ignore_errors=True)` retry is gone (`grep` returns nothing).

Preparation no longer rebuilds a corrupt published reference/geometry/MVIDX/build: those
reads now fail closed with the path named, so ordinary `prepare` cannot overwrite content
a prepared generation may protect.

## 4. R11-C — same-build `prepare` is single-flight

`prepare_target_training_order` keeps the cheap unlocked completed-build fast path; on a
miss it takes an execution-only advisory fence at
`builds/<build_identity>.prepare` (adjacent to, and distinct from, the build publication
lock, so the publisher cannot self-deadlock), re-checks the completed build under the
fence, and only then creates attempt scratch and enters `_build`. The fence is held
through pure checkpoint restore/write/prune, REPAIR2, suffix checkpoint restore/write/
prune, build publication and build-owned checkpoint cleanup, and is released by the OS if
the holder dies. `selection_identity` is unchanged: no attempt identity entered
scientific identity, and different `build_identity` values are not serialized.

## 5. R11-D — frozen universal structural-family catalog

`_build_current_target_training_order` still derives the phase/geometry plan (local
structure policy, groups, events, aggregation) but overrides `enabled_feature_families`
with `TargetCoveragePolicy().required_structural_feature_families` before catalog
construction; `materialize_atomic_environments=False` is retained. After exact-`P_train`
projection, `build_target_coverage_reference` compares the represented structural
semantic families against the frozen set and raises `TrainingDataInputError` naming every
missing family. No threshold, minimum-element count, or dimension was weakened or
fabricated.

## 6. R11-E — REPAIR2 frontier restored

`_Frontier.proposal_possible` and `possible = hard_pending or max(totals[c] ...)` are
deleted; `build_repair_plan` now calls `_best_proposal` whenever a shortlist and frontier
exist. Family non-regression and `strictly_better(J)` remain the only admission rule, and
no D2 constant or objective component changed. `REPAIR2_VERSION` is
`mdstats.target-order.repair2.configured-shell.v2`, which flows through
`TargetMultiViewRepairPolicy` → `target_order_method_identity()` →
`target_order_build_identity()`, so pre-fix v1 builds cannot be reused as current and a
persisted v1 policy fails authentication.

## 7. Representative current-scale qualification (R11-H)

### 7.1 Fixture identity

The substrate is the existing current LTA campaign, not a synthetic fixture:

- campaign config: byte-identical copy of
  `05_mace_training/LTA/mpa0/FP32/campaign.toml` (sha256 `059ab8fe…`), run in a
  scratch workspace so the stakeholder's live campaign was never mutated;
- sources: `04_training_dataset/LTA` — 27 VASP runs, 923 MiB
  (sha256 of the per-file digest list: `5184e89f…`);
- inferred manifest: sha256 `591f2c4a…`, byte-identical to the live campaign's
  approved manifest;
- retained frames 37,633; exact `|P_train| = 33,984`;
- configured ladder `target_size_power_min/max = 7/14` → `N ∈ {128 … 16384}`,
  `N_max = 16384`; evaluation powers `[8,9,10]`;
- machine: 32 threads (28-thread CPU budget), 62 GiB RAM, RTX 3090 (unused by this
  CPU path). The run's own resolved plan was `CPU 28/32 threads; RAM 43.1 GiB available
  / 34.5 GiB budget`.

### 7.2 Scale of the built products

| Quantity | Value |
|---|---|
| structural semantic families / total reference families | 8 / 78 |
| reference elements per structural family | 33,984 |
| canonical obligations | 739 |
| NEIGHBOR1 witnesses / edges | 2,367,624 / 2,216,469,672 |
| FEAS1 terminal state | `cross_support_fragile`, `k_min_lower_bound = 90` |
| Phase A → Phase B transition rank | 361 |
| MVSEL2 evaluated edges (configured prefix / suffix) | 2.62e11 / 3.22e11 |
| REPAIR2 swaps (rungs 128…16384) | 49 (0,0,0,32,3,5,3,6) |
| MVQUAL qualified sizes | 512, 1024, 2048, 4096, 8192, 16384 |
| published build identity | `b8d75b6a1857e85c` |

### 7.3 Fresh run A — wall clock, memory, I/O

Whole `prepare`: **2 h 25 m 53 s**, peak RSS **31.5 GiB** (33,052,540 KiB),
file-system inputs 2,434,160 blocks, outputs 110,908,256 blocks (~56.8 GB), peak
mapped target-order files **2** (O(1) in family count), peak open FDs 339, target-order
store 16.9 GiB.

| Stage | Wall |
|---|---|
| P1 authorities + neutral substrate | 133 s |
| structural selector inputs (provider, 4 lanes autotuned) | 253 s |
| `TargetCoverageReference` (serial; see below) | 818 s |
| canonical obligations | < 1 s |
| shared FEAS1/NEIGHBOR1 (28 lanes, one construction) | 516 s + 19 s FEAS1 |
| MVIDX adoption/inversion (geometry adopted, not recomputed) | 72 s |
| native preflight (1/2/4/8/16/28 lanes) | 55 s → 3.28× best, width 16, `scaling=pass` |
| MVSEL2 configured prefix to `N_max` (native-OpenMP ×16) | 233 s |
| **REPAIR2 (8 configured shells)** | **6,156 s** |
| post-repair exact reconstruction | 39 s |
| MVSEL2 suffix, 16,384 → 33,984 | 164 s |
| MVQUAL | 20 s |
| build publication | 2 s |
| P3 common preparation + generation binding | 135 s |

Target-order total 2 h 19 m 08 s, of which REPAIR2 is 74 %. Per-shell REPAIR2 cost:
1024 → 60 s (32 swaps), 2048 → 1,351 s (3), 4096 → 1,858 s (5), 8192 → 1,264 s (3),
16384 → 1,620 s (6).

**Finding (routed, not absorbed).** With the R11-E shortcut deleted, every shell whose
coverage is saturated evaluates a frontier of all remaining candidates and, per removal,
representative/diversity gains over the surviving frontier. This is exactly what accepted
D2 §9.2/§9.3 require and what the pre-fix concretization skipped, so it is not repairable
by weakening the method. The accepted optimized closure **is** active (native-OpenMP
Phase B at width 16, certified-lazy refresh, packed O(1) mapped descriptors, adopted
NEIGHBOR1 geometry, thread-queue immutable proposals — the same execution model as the
mature carrier), so this is not an inactive-path defect either. Observed proposal-stage
CPU utilization is ~1.6 cores: the proposal queue is GIL-bound Python/NumPy per candidate.
A vectorized/native frontier and removal-gain evaluation over the existing CSR gather and
native row-scoring kernels is the obvious exact-preserving optimization, but it is a
performance-design change and is therefore **routed to D3/D4 performance design with this
measurement** instead of being invented inside this bounded conformance repair.

The `TargetCoverageReference` stage of run A was serial (818 s) because the restored
`prepare` had stopped passing an execution scope, although the owner and the mature
carrier both support COVREF-PAR1 single-level block parallelism. That wiring was restored
in this repair (execution-only; `query_workers=1`, one cKDTree worker per lane) and is
exercised by run B and by an owner-level digest-equality test.

### 7.4 Reuse, reload, and downstream routing

- Authenticated reuse: a second `prepare` in the same workspace completed in **5 m 38 s**
  with `status=reused; build=b8d75b6a` at the unlocked fast path, peak RSS 8.9 GiB; no
  selector, geometry, MVIDX or repair work was repeated.
- Fresh-process compact definition load: **0.37 s**; full prepared-generation component
  load 139 s at 6.0 GiB RSS (dominated by the P2/P3 aggregate components, not by
  target-order artifacts).
- Fresh-process manual `select-target-size 4096`: **1.53 s**, 627 MiB peak RSS, `rc=0`,
  with `target_order.selector`, `sparse_index`, `engine`, `repair`, `state` and
  `_mvsel2_native` **all unloaded** and **zero** mapped target-order files. Downstream
  selection does not reconstruct target-order science at current scale.

### 7.5 Fresh versus interrupted/resumed (run B)

Run B is a second fresh campaign in its own workspace, built with the COVREF-PAR1
wiring active, killed with `SIGKILL` during the suffix and then resumed.

| | run A (fresh, serial reference) | run B interrupted | run B resumed |
|---|---|---|---|
| `prepare` wall | 2 h 25 m 53 s | 2 h 04 m 24 s (killed at rank 18,432) | 2 h 00 m 21 s |
| peak RSS | 31.5 GiB | 36.4 GiB (anon 35.5 GiB) | 20.1 GiB (anon 9.6 GiB) |
| `TargetCoverageReference` | 818 s (serial) | **58 s** (COVREF-PAR1) | reused (published) |
| FEAS1/NEIGHBOR1 | 516 s | 539 s | reused |
| MVIDX | 72 s | ~70 s | reused |
| MVSEL2 to `N_max` | 233 s, width 16 | 245 s, width 16 | **12 s** restored from checkpoint |
| REPAIR2 | 6,156 s, 49 swaps | 5,894 s, 49 swaps | 6,610 s, 49 swaps (replayed) |
| suffix | 164 s (16,384 → 33,984) | killed at rank 18,432 | 197 s (18,432 → 33,984) |
| selector width chosen by preflight | 16 | 16 | 4 |
| published build identity | `b8d75b6a1857` | — | **`b8d75b6a1857`** |

The resumed run published the **identical build identity** as the fresh run across a
different workspace, a parallel rather than serial coverage reference, a different
preflight-selected selector width (4 versus 16), and a kill/resume 2,048 ranks beyond
`N_max`. Because the build content digest binds the complete order, repair plan,
qualification plan and every scientific parent, this is simultaneously the fresh-versus-
resumed, worker-width, and reference-execution-scope invariance result. MVQUAL qualified
the same sizes `{512 … 16384}` in both runs.

Checkpoint and footprint behavior:

- checkpoint store 26 MB for both roots; restoring the pure checkpoint at rank 16,384
  cost 12 s versus 233 s to recompute it;
- the killed holder left both checkpoint roots, no partial build, and an 8 KB attempt
  scratch directory; the successor acquired the OS-released fence, reused the published
  stage products, and deleted nothing it did not own;
- **restart cost finding:** REPAIR2 is not checkpointed, so a restart after the
  configured shells replays it in full (6,610 s here) before the suffix resumes from its
  own checkpoint. With the R11-E correction this is now the dominant restart cost. Like
  §7.3 this is a performance-design item for D3/D4, not a conformance defect;
- mapped target-order files peaked at 81 during OOC NEIGHBOR1/MVIDX *construction*
  (per-family scratch) and at ≤ 7 during authenticated restore/selection, so the packed
  store keeps restore descriptors O(1) in family count (78 families);
- peak FDs 416 (construction) / 360 (resume); final target-order store 17 GiB per
  campaign, peaking at 25 GiB while MVIDX scratch is live; run B wrote 3.89 M blocks on
  resume versus 110.9 M blocks for the fresh build, i.e. the resume re-published nothing;
- COVREF-PAR1 costs about 4 GiB of extra anonymous peak memory (36.4 GiB versus
  31.5 GiB) for a 14× wall reduction on that stage; peak stays inside machine capacity
  but above the campaign's own resolved RAM budget line (34.5 GiB for run A), which the
  reviewer may wish to route to the resource owner.

## 8. Executed checks

| Check | Result |
|---|---|
| `tests/test_mlff_target_order_real_owner.py` (complete, final tree) | **20 passed** (60 s) |
| Affected regression, 98 files, `-n 12` (final tree) | **2253 passed, 2 skipped, 10 failed** |
| Baseline attribution of those 10 in a `HEAD` worktree | identical 10 ids — zero new failures/errors |
| CLI/spec/help/documentation closure batch | **12 passed, 0 failed** (was 60 passed / 8 failed) |
| Pre-fix falsification of the seven new tests | all 7 fail on the pre-repair owners |
| `git diff --check` excluding PDFs | clean |
| `ruff` delta on changed files | relocated warnings moved with the code; no new class introduced |

The 10 pre-existing failures are unrelated to this repair and reproduce byte-identically
at `HEAD`: eight `*_specification.py` suites asserting the retired revision-109
architecture manual (`test_mlff_replay_unify1c` ×2, `test_mlff_replay_perf1` ×3,
`test_mlff_perf_p5`, `test_mlff_vram1_perf_p4` ×2) and two `test_topology_catalog.py`
tests requiring the untracked `tests/data/Na_LTA_relaxed.POSCAR`.

### 8.1 The eight static failures (R11-F dispositions)

The batch is `tests/test_mlff_data9b3_campaign_cli_specification.py` (2) plus
`tests/test_mlff_doc_arch1_specification.py` (6). All eight asserted the pre-promotion
mixed architecture manual that the accepted 2026-09-13 D1/D2 promotion replaced; the
retired document is preserved under
`docs/history/mlff/architecture_snapshots/pre_d1_d2_promotion_2026-09-13/`. No `xfail`,
`skip`, warning filter, or baseline whitelist was used.

| # | Node | Stale expectation | Disposition |
|---|---|---|---|
| 1 | `data9b3::test_data9b3_architecture_and_stage_plan_integration` | "one target-size architecture", "post-selection cross-validation on the frozen collection", "does not redefine RDF, MSD, VACF, VDOS" | rebased onto the current manual's wording ("one prepared target-size generation", "freezes the collection before numerical CV work", "it does not redefine those algorithms") |
| 2 | `data9b3::test_data9b3_dependency_graph_contract` | graph schema 3 and retired node/edge names | rebased onto schema 5 `d1_d2_d3_d4_layered_mlff_architecture` nodes and the screen→design→freeze→CV→production→qualification edge chain |
| 3 | `doc_arch1::test_doc_arch1_release_and_current_authority_are_synchronized` | `architecture_revision: 109`, "Part VI/VII", retired headings | asserts current status line, the four D1/D2 method owners, chapter `45_target_training_order.md`, one complete `TargetTrainingOrder`, and the preserved historical snapshot |
| 4 | `doc_arch1::test_doc_arch1_manual_is_deterministically_assembled_from_numbered_sources` | the manual is a byte-exact concatenation of nine chapters | renamed to `…manual_and_numbered_sources_index_the_same_canonical_chapters`: the manual is canonical prose ("it is not a generated aggregate"); the ten numbered chapters on disk, the chapter README table, and manual §14 must index the same set, and `70_status_and_gates.md` must not reappear |
| 5 | `doc_arch1::test_doc_arch1_current_target_size_and_execution_contract` | D1/D2-owned tokens (`T_selected`, `n1/M1 → …`, `nonconverged_at_configured_ceiling`) demanded of the D3 manual | asserts the current D3 lifecycle contract over the manual **plus its chapters** (`T_N = pi_train[:N]`, operator-owned provisional design, screen-recommends wording, `cross-validate` as the only freeze boundary, typed no-recommendation, freeze-before-CV) |
| 6 | `doc_arch1::test_doc_arch1_manual_names_no_retired_target_size_owner` | forbade `MVSEL2/REPAIR2/MVSTATE2/MVQUAL/MVIDX/FEAS1` — now the restored current owners | forbids only genuinely retired owners (`TargetSizeStudyPolicy`, `TargetDataRoleFreeze`, `target_size_study`), **requires** the restored chain to be named, and adds the R11-F guard that the general D1/D2 papers no longer present hard-support-only qualification or the condition-balanced rule as the current `pi_train` method |
| 7 | `doc_arch1::test_doc_arch1_external_algorithmic_provenance_is_cited` | citations `[32]`–`[37]` in the assembled manual | reads the current owner of those citations, `90_references.md` |
| 8 | `doc_arch1::test_doc_arch1_graph_and_directory_ownership_are_current` | schema 3 nodes/summaries/`forbidden_current_paths` | rebased onto schema 5: layered authority chain, current node set, retired ids still absent, the six forbidden edges, and no forbidden edge present among real edges; README/runbook/root-file checks retained |

### 8.2 Documentation reconciliation

`docs/methods/mlff_scientific_method.md` §1/§5.1/§6.2 and
`docs/methods/mlff_numerical_algorithmic_method.md` §1/§4.1/§6.1/§7/§22 now delegate
`pi_train` construction and configured-prefix membership qualification to the scoped
target-order papers. `pi_eval`/`M1..M3`, the exact `M3` subset-sum rule, the
condition-balanced evaluation order, the three-qualified-candidate funnel, P3 training and
reducer semantics, CV, replay, production and threshold separation are untouched. A
repository search found no surviving current claim that `pi_train` is condition-balanced
round-robin or hard-support-only. The method papers have no generated PDF siblings, so no
regeneration was required; `pandoc`/`typst` remain unavailable on this machine, which
matters only for the retired architecture-PDF chain that this repair does not touch.

## 9. Evidence boundary

All target-order claims above come from `@pytest.mark.real_target_order` tests or from
direct real-owner execution on the representative campaign. Downstream `test_mlff_*`
suites still install the below-claim substitute and are cited only as compatibility
evidence.

### 9.1 Substitute scope defect found and fixed

`tests/conftest.py` installed the substitute from a **function-scoped** autouse fixture,
but `test_mlff_storage_reset_integration.py` and
`test_mlff_qualification_status_observation.py` build their campaigns in **module-scoped**
fixtures, which pytest instantiates first. Those suites therefore reached the real
target-order owner on fixtures far below method scale, and passed only because the
pre-fix owner silently dropped required structural families — the B5 defect, exercised
unnoticed on 49 test setups. Making the substitute module-scoped restores the documented
claim boundary (208 passed).

The dedicated assembled real-owner fixture had the same false premise: its two dilute
atoms have no neighbors inside the smooth switching cutoff, so `pair_distance`,
`chemical_environment`, `angular_environment` and `orientational_order` were all
unavailable. Its geometry is now a compact 3.8 Å cubic cell with three atoms, giving every
frozen family valid reference elements. The real LTA substrate produces all eight
families with 33,984 reference elements each, so the frozen D2 catalog is satisfiable on
real current data and no upstream applicability exemption is needed.

## 10. R11-A … R11-H traceability

| Item | Code | Evidence |
|---|---|---|
| R11-A | `training_data/persistence.py`; ten rewired consumers | single-definition `grep`; storage/qualification/post-selection/replay suites green with remapped seams |
| R11-B | `target_order/artifact_store.py::publish_artifact_directory` | `test_real_owner_corrupt_published_target_order_artifacts_are_not_replaced`; retained ENOSPC test |
| R11-C | `target_order/preparation.py`, `state.py` docstrings | `test_real_owner_same_build_prepare_is_single_flight`; `test_real_owner_interrupted_fence_holder_releases_and_successor_resumes` |
| R11-D | `campaign_target_size_runtime._build_current_target_training_order`; `coverage_reference.build_target_coverage_reference` | `test_real_owner_required_structural_families_are_complete_or_fail_closed`; `test_real_owner_molecular_phase_plan_cannot_thin_target_order_families`; real LTA run §7.2 |
| R11-E | `target_order/repair.py` | `test_real_owner_repair2_zero_new_coverage_swap_strictly_improves_representative_utility`; `test_real_owner_repair2_v1_build_identity_is_not_current` |
| R11-F | general D1/D2 papers; two static suites | §8.1 dispositions; closure batch 12 passed / 0 failed |
| R11-G | `tests/test_mlff_target_order_real_owner.py`, `tests/conftest.py` | 20 passed; affected regression baseline-equal |
| R11-H | COVREF-PAR1 rewiring in `preparation.py` | §7 representative metrics; owner-level scope-equivalence assertion |

## 11. Explicit statements

- Native execution is **useful and active** at current scale: preflight measured
  3.28× best parallel speedup and selected width 16 under the accepted 1.05× / 0.05
  policy; Phase B ran `native-openmp`, and installed-package native/reference exact
  equivalence passes.
- **No** fallback selector, old/new router, alternate suffix, compatibility mode, second
  currentness or checkpoint store, semantic migration layer, new GC/cleanup owner, or
  duplicate advisory-lock implementation was added.
- Production-scale GPU qualification remains deferred to the final release package.
- No Protocol Challenge is raised: no accepted D1/D2/D3 authority was found false,
  contradictory, or impossible to concretize.
