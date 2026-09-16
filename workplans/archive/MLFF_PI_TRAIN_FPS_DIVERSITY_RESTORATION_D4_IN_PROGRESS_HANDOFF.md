# D4 in-progress handoff: MLFF `pi_train` multi-view restoration

> **Superseded for the current cycle (2026-09-15).** The Revision 9/10 review found this
> implementation NO-PASS. The Revision 11 repair is implemented at commit `dd96ede2`;
> its evidence, including the reconciled dispositions of the eight static failures listed
> in item 8 below and the representative current-scale performance record that item 9
> could not supply, is in
> `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R11_D4_REPAIR_EVIDENCE.md`. Items 2
> (REPAIR2 frontier shortcut) and 8 are now closed by that repair; the rest of this
> document remains historical implementation provenance.

Status: **D4 implementation complete, uncommitted working tree, awaiting fresh independent D4 review** on branch
`design/mlff-pi-train-fps-diversity-restoration` (start head `188089867d3e8378f0550d0299eb1ef5bb2b6007`).
The continuation preserved the inherited work and added no commit. Nothing here is independent review or
release approval.

Governing authority (unchanged, read first): workplan entry
`workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_CURRENT.md`, executable handoff
`workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R3_D3_D4_IMPLEMENTATION_HANDOFF_REPAIRED.md`
(sections 4-19 are the D4 contract), D1 `docs/methods/mlff_target_training_order_scientific_method.md`,
D2 `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`,
D3 `docs/arch_manuals/mlff_training_data/45_target_training_order.md`.
Historical carrier `3937881e` (extract with `git show 3937881e:<path>`) is the restoration source.

## Environment pitfall (cost this session real time)

`conda run -n mace python - <<'EOF'` does **not** forward stdin: heredoc scripts silently do nothing
(exit 0). Use `/home/samjin/miniconda3/envs/mace/bin/python - <<'EOF'` or a script file. Always verify
edits with `git diff --stat`. Native extension build: `conda run -n mace python tools/mdstats-build.py --no-deps`
(the `.so` is gitignored). Max 16 concurrent test jobs.

## Continuation update (2026-09-15)

The inherited dirty inventory was preserved. Direct current-v2 P2 callers were migrated to the explicit
`target_order_builder` seam, retired v1 assertions were rewritten to their owning v1/P5A6 or current-v2
contracts, and the real-owner test module was added with the required `real_target_order` opt-out from the
downstream substitute. The full target-order real-owner suite now covers rows of at least eight witnesses,
native and serial parity, a one-swap REPAIR2 fixture, suffix/checkpoint resume beyond `N_max`, independent
MVQUAL, checkpoint rejection, FD/ENOSPC bounds, installed-package native equivalence, and preparation
build/reuse/crash-resume/scratch cleanup.

`prepare_target_training_order` was executed end-to-end on a feasible assembled campaign fixture. The
assembled real-owner integration then verified prepare/reuse, authenticated v2 reload in a fresh process,
manual selection without importing the selector, screening, CV, production planning, currentness, and
stale v1 rejection. A downstream continuation test needed `partition_seed = 2` because restored `pi_train`
membership is part of the authenticated identity; seed 0's old equal-shape coincidence no longer holds.
This changes only the test fixture premise, not P5 semantics.

The exact native build completed, and the installed-package native/reference equivalence test passed. The
performance checkpoint passed on the small real-owner fixture and recorded stage timings, peak RSS, packed
MVIDX/checkpoint bytes, FD counts, selector edge/scoring telemetry, checkpoint restore, suffix work, and
REPAIR2 swaps. Native preflight was exact but did not pass a scaling threshold on that small fixture, so no
native performance qualification is claimed.

The CLI/spec/guide source documentation and their generated PDF siblings were reconciled with the restored
prepare-owned chain. Eight architecture/manual static-test failures were also reproduced at the clean start
head and are stale baseline expectations for the already accepted newer D3/manual topology; they were not
altered as part of this D4 implementation.

## Implemented (new files, still uncommitted)

| File | Content | Verified |
|---|---|---|
| `mdstats/training_data/work_queue.py` | PARCORE1 deterministic queue, verbatim carrier restore | smoke |
| `mdstats/_mvsel2_native.c` + spec in `build_support/native_extensions.py` | native/OpenMP candidate-row scorer (NumPy pairwise-sum order) | builds; installed-package equivalence |
| `target_order/_sparse_vector_kernels.py` | CSR gather kernels (verbatim) | smoke |
| `target_order/artifact_store.py` | packed NPY roots, manifests, create-or-verify atomic publish | smoke |
| `target_order/coverage_reference.py` | single-domain `TargetCoverageReference` on exact `P_train`, direct scoring, packed persistence | smoke |
| `target_order/obligations.py` | one canonical obligation authority (condition/unit/event/extent + explicit P2; k=max; fail-closed) | smoke |
| `target_order/neighborhood.py` | NEIGHBOR1 cKDTree exact relation, OOC CSR stream, packed store | smoke |
| `target_order/feasibility.py` | shared FEAS1/NEIGHBOR1 one-pass builder + canonical capacity report | worker-invariant smoke |
| `target_order/sparse_index.py` | MVIDX adoption/inversion (OOC), forward-only view | smoke |
| `target_order/selector.py` | MVSEL2 primitives, full-forward/lazy reference oracle, plan records | oracle |
| `target_order/native.py`, `kernels.py` | backend qualification, optimized Phase A/B, native preflight | ranks == oracle (w=1,4) |
| `target_order/state.py` | MVSTATE2 checkpoints (identity-bound, authenticated restore, prune) | resume == fresh |
| `target_order/engine.py` | the single rank loop (pure prefix, suffix, resume) | ranks == oracle |
| `target_order/repair.py` | REPAIR2 single-domain restore, reuses selector primitives, deterministic parallel proposals | worker-invariant; real fixture makes 1 swap |
| `target_order/qualification.py` | independent MVQUAL (progressive per family, canonical counts, MVIDX cross-check 5e-12, FAIL*->PASS*) | worker-invariant |
| `target_order/preparation.py` | prepare-owned orchestration, stage artifacts under `<prepared>/target-order/{reference,geometry,mvidx,checkpoints,builds,attempts}`, `TargetOrderPreparation` component | end-to-end build/reuse/crash-resume/scratch cleanup |
| `target_order/__init__.py` | docstring only (no eager imports, so P2 records stay light) | - |
| `tests/support/target_order_fixtures.py` | real P2 population/split + duck-typed raw/structural catalogs | - |
| `tests/support/target_order_substitute.py` | below-claim substitute of the target-order owner for downstream suites | downstream affected suites pass |
| `tests/test_mlff_target_order_real_owner.py` | dedicated real-owner, assembled, resource-bound, package, and performance tests | 13 passed; 2 warnings |

The dedicated real-owner tests supersede the earlier scratch-only limitation: a duplicated-cluster fixture
has CSR rows of at least eight witnesses and passes native/serial rank equality at workers 1 and >1, while
the separate package test passes exact native/reference equivalence after wheel installation. The older
160-frame scratch evidence remains useful as development evidence but is not an independent qualification.

## Modified current owners (tracked files)

- `mdstats/training_data/target_size_experiment.py` (P2 cutover):
  `TARGET_TRAINING_ORDER_POLICY="multi_view_mvsel2_repair2.v1"` is the only token valid under policy
  schema v2 (v1 schema only accepts `LEGACY_TRAINING_ORDER_POLICY`); `TargetTrainingOrder` schema v2
  (`selection_evidence_digest` = `TargetOrderPreparation.content_digest`); `build_target_training_order`
  now projects a prepared build; old priority order renamed `_legacy_priority_training_order` (v1 only);
  `TargetSizeCandidateQualification` v2 (coverage/extent/failed families/min coverage/`mvqual_rung_digest`)
  via new `project_target_size_qualification`; `qualify_target_size_candidates` is v1-only; definition
  checks schema coherence; aggregate `__post_init__` re-derives qualification only for v1 and rejects
  training priority evidence for v2; aggregate `from_dict` for v2 re-derives only population/split/pi_eval
  (no target-order science); `build_target_size_statistical_aggregate(..., target_order_builder=...)`
  (required for v2) with helper `_target_size_split_substrate`.
- `mdstats/training_data/campaign_target_size_runtime.py`: `CurrentTargetSizeAuthorities.target_order`
  field + `"target_order"` component; prepare passes a builder calling new
  `_build_current_target_training_order` (universal structural catalog on exact `P_train`,
  phase-geometry policy when contracts exist, `materialize_atomic_environments=False`, workers from
  `_performance_resources(cfg).cpu_threads_budget`); loader passes the component through.
- `mdstats/training_data/campaign_prepared_generation.py`: schema v2; `"target_order"` component before
  `"aggregate"`; old-schema manifest -> `PreparedGenerationMissingError` "run prepare"; loader checks the
  training order binds the target-order component; protected paths include target-order artifact dirs.
- `tests/conftest.py`: `real_target_order` marker; autouse fixture substitutes
  `_build_current_target_training_order` for `test_mlff_*` modules unless marked.

The current owners import successfully. The direct P2 caller migration is complete; current-v2 aggregate
construction now has an explicit target-order builder, while preserved v1 callers remain covered by the
P5A6 compatibility owner. The downstream `test_mlff_*` substitute is not used by the dedicated real-owner
module.

## Next steps (in order)

1. **Migrated direct P2 callers — complete.** Current-v2 callers pass
   `target_order_builder=substitute_target_order_builder(policy)` where their claims do not concern ordering;
   retired v1 priority/qualification assertions were moved to v1/P5A6 coverage or rewritten against the
   current prepared projection. The four directly affected authority/runtime suites produced 59 passes plus one
   corrected focused pass; the broader downstream suites are listed below.
2. **Dedicated real-owner tests — complete.** `tests/test_mlff_target_order_real_owner.py` passed 13 tests
   with two warnings. It includes the required rows>=8 native/serial rank equality, actual one-swap
   REPAIR2 fixture, suffix and checkpoint resume beyond `N_max`, MVQUAL independence, stale/corrupt
   checkpoint rejection, FD/ENOSPC bounds, and installed-package native equivalence.
3. **End-to-end preparation — complete.** The real owner passed build, reuse without rebuild, interrupted
   checkpoint resume, publication/adoption, and attempt-scratch cleanup. The assembled integration also
   passed fresh-process reload and stale v1 rejection.
4. **Closure/registry reconciliation — complete.** P6 closure now protects the restored target-order owner
   and native registry tests assert the optional `_mvsel2_native` source/spec rather than its absence.
5. **Assembled real-owner integration — complete.** The feasible 332-frame campaign passed prepare, v2
   authentication/currentness, manual select without selector import/mmap, auto screen, CV freeze, and
   production planning on the prepared order.
6. **Performance/docs/review handoff — complete for this implementation turn.** The §16.5 checkpoint
   passed and source Markdown, CLI help, examples, and generated guide/spec PDFs were reconciled. Leave the
   branch uncommitted for a fresh independent D4 review; production-scale GPU qualification remains
   deferred.

Affected suites to run (<=16 jobs): `test_mlff_target_size_statistical_authorities`,
`test_mlff_target_size_p4d_runtime_cutover`, `test_mlff_target_size_execution_p3a`,
`test_mlff_campaign_prepared_generation_efficiency`, `test_mlff_campaign_storage_composition`,
`test_mlff_campaign_stateful_properties`, `test_mlff_campaign_observation_purity`,
`test_mlff_replay_true_dft_default_and_prepare_ownership`, `test_mlff_target_size_corrected_identity_cutover`,
`test_mlff_target_size_mace_objective_realization`, `test_mlff_target_size_p4_authority_reconstruction_io`,
`test_mlff_target_size_p4e_terminal_and_invalidation`, `test_mlff_target_size_p4g_assembled_integration`,
`test_mlff_target_size_p6_destructive_closure`, `test_mlff_target_size_terminal_decision_policy`,
`test_native_build_registry`, plus post-selection/P5A6 suites that reach `campaign_post_selection`.

## Validation record

- `conda run -n mace python tools/mdstats-build.py --no-deps`: PASS; the optional `_mvsel2_native` extension
  built and installed. The installed-package real-owner equivalence check also passed exact native/reference
  results.
- `tests/test_mlff_target_order_real_owner.py`: **13 passed, 2 warnings**. The performance checkpoint within
  this suite passed in 3.37 seconds; it recorded 32-frame/6-family stage metrics, 79,121-byte published
  MVIDX, 37,876-byte checkpoint output, 208,852 KiB peak RSS, bounded FDs, and one REPAIR2 swap.
- Authority/runtime batch (`test_mlff_target_size_statistical_authorities`, P4D runtime cutover, P3A
  execution, and MACE objective): **59 passed, 1 corrected focused failure**; the corrected test then passed.
- Ownership/currentness/storage/P6/registry batch: **334 passed, 259 warnings**.
- Downstream/P5/P5A6/closure batch after the fixture-seed correction: **289 passed, 1,407 warnings**.
- CLI/spec/help/documentation closure batch: **60 passed, 8 failures**. The eight failures were reproduced
  at the clean start head and are stale architecture/manual schema, revision, topology, and provenance
  expectations; they are baseline-equal, not implementation regressions.
- Meaningful source diff check, excluding generated PDF byte diffs: `git diff --check -- . ':(exclude)*.pdf'`:
  PASS. The final branch status remains dirty and uncommitted by instruction.

## Items to report to the D4 reviewer (do not silently resolve)

1. **Carrier native Phase-A defect repaired**: the carrier's native Phase-A coverage gain summed full rows
   with zeros for covered witnesses, which associates differently from the D2 masked reduction for rows >= 8
   (9900/20000 mismatches in a probe). `kernels.choose_phase_a` now always uses the canonical masked
   reduction for coverage gains; native is used only for representative/diversity sums (pairwise-matched).
2. **REPAIR2 frontier shortcut**: restored carrier REPAIR1/2 returns no proposal when no hard obligation is
   pending and no candidate has positive new coverage; D2 section 9 does not state this condition
   (J could still improve via U_rep/balance). Kept the mature semantics; needs D2 clarification.
3. **REPAIR2 bottleneck**: uses the MVSEL2 definition (`C_m/0.95`, first canonical within 1e-14) instead of
   the carrier's raw-mass minimum, so there is one bottleneck definition.
4. **P5A6 legacy tension**: `campaign_post_selection._load_p5a6_selected_training_context` must reproduce
   preserved v1 aggregates bit-for-bit, so the retired priority order/qualification remain reachable only
   under `TARGET_SIZE_POLICY_V1_SCHEMA`. Not a current selector; flag against "no old/new router".
5. v2 aggregate qualification is not re-derivable from P2 alone (by D3: no downstream selector rebuild);
   it is authenticated by the prepared generation digest plus the target_order-component link check.
6. Absent families: no profile or foundation families (no active selection-stage provider in the current
   protocol, scratch mode) — per handoff section 5.

7. **Restored membership changes one downstream fixture premise**: because authenticated `pi_train`
   membership participates in identity, the foreign-sibling continuation test uses `partition_seed = 2`
   to obtain equal fold runtime shapes. Seed 0 was a pre-restoration coincidence; no downstream production
   semantics were changed.
8. **Architecture/manual static tests remain baseline-stale**: eight failures in the combined documentation
   batch were reproduced at clean start head and assert the older schema/revision/topology, so they were not
   weakened or rewritten here. The user-surface closure portion and P6/registry checks passed.
9. **Native scaling is not qualified**: the real-owner native preflight had exact parity but did not meet its
   scaling threshold on the small fixture (effective runtime width was one); only correctness/equivalence is
   reported.
