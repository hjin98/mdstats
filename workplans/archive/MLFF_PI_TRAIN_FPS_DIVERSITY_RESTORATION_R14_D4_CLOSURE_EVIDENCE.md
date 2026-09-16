---
kind: implementation-evidence
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 14
protocol_version: 6.3.0
status: active
evidence_date: 2026-09-16
branch: design/mlff-pi-train-fps-diversity-restoration
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
parent_implementation_commit: d993f25e28f7d0886ef7628c0a39feeb91adaf33
r14_implementation_commit: bc733983
reviewed_r13_candidate: a616f8aa54a80ff003abeb1a2c6b0e882055e4a7
highest_affected_domain: D4
upstream_authority_state: D1_D2_D3_ACCEPTED_UNCHANGED
serious_challenge: false
---

# Revision 14 D4 FEAS1/NEIGHBOR1 resource-scope closure evidence

Revision 14 closes B14-1: FEAS1/NEIGHBOR1 was the one remaining target-order
stage that bypassed the restored campaign resource owner. No D1/D2/D3 change was
required and none is proposed.

## 1. Changed files

| File | Change |
|---|---|
| `mdstats/training_data/target_order/preparation.py` | `_build()` derives one FEAS1/NEIGHBOR1 child `StageResourceScope` from the existing root scope and passes it to the existing `build_target_coverage_geometry(..., resource_scope=)` parameter. |
| `mdstats/training_data/target_order/feasibility.py` | Deleted the `manage_resource_scope=resource_scope is not None` override at the FEAS1 queue; extended the existing `status=complete` progress line with the stage scope and queue disposition already published by COVREF. |
| `tests/test_mlff_target_order_real_owner.py` | Four R14 falsification tests at the real production/FEAS1 owners. |

The product diff adds **no class, no function, no module and no configuration
key**:

```text
$ git diff -U0 -- mdstats/ | grep -E '^\+' | grep -E 'class |def '
(no output)
$ git diff -- mdstats/ | grep -E '^\+.*(Manager|Policy|Cache|Store|Registry|fallback|compat)'
(no output)
```

## 2. B14-1 — the one missing edge and the last polarity exception

### 2.1 Preparation owner

`_build()` called `build_target_coverage_geometry(reference, build_directory=...,
policy=..., global_workers=workers, progress_callback=...)` with no
`resource_scope`, so FEAS1 fell back to `_default_scope(...)` whose
`ram_budget_bytes` is `None`. The repair is one argument through the interface
that already existed, using the root scope R13 already routed into `_build()`:

```python
resource_scope=None
if resource_scope is None
else StageResourceScope(
    stage_name=f"{resource_scope.stage_name}/feas1-neighbor1",
    cpu_threads_available=int(resource_scope.cpu_threads_available),
    cpu_threads_budget=int(resource_scope.cpu_threads_budget),
    python_workers=workers,
    tree_workers=1,
    blas_threads=1,
    native_openmp_threads=1,
    ram_budget_bytes=resource_scope.ram_budget_bytes,
)
```

The child scope carries the root CPU and RAM numbers unchanged and declares only
the widths FEAS1 already ran at (`python_workers=workers`, `tree_workers=1`,
`blas_threads=1`, `native_openmp_threads=1`), which is exactly what
`build_target_coverage_geometry()`'s pre-existing width assertion requires. No
second resource snapshot, RAM fraction, worker policy or coordinator exists. An
isolated direct caller that supplies no root scope keeps the existing
`_default_scope(...)` local fallback.

### 2.2 The last `manage_resource_scope` exception, removed rather than replaced

R13 removed the flag's two `resource_scope is None` readings at MVIDX and
MVQUAL. FEAS1 carried the opposite polarity, `resource_scope is not None`, so on
the production route it declined its own declared native-thread quarantine. The
override is deleted and the queue's existing `manage_resource_scope=True`
default applies. No flag, wrapper or branch replaces it. The flag now has **no
reader anywhere in the repository**:

```text
$ grep -rn "manage_resource_scope" --include=*.py mdstats/
mdstats/training_data/work_queue.py:235:        manage_resource_scope: bool = True,
mdstats/training_data/work_queue.py:247:        self.manage_resource_scope = bool(manage_resource_scope)
mdstats/training_data/work_queue.py:292:        if self.manage_resource_scope:
```

Budget provenance and native-thread quarantine are now independent at every
queue in the target-order chain.

### 2.3 Stage telemetry, not new machinery

FEAS1's existing `status=complete` progress line was extended with
`scope.summary()` and the queue's existing `snapshot()` fields, in the exact
shape COVREF already publishes. It reuses existing methods on an existing
callback, adds no instrumentation object, and enters no scientific identity —
without it the §4 requirement to record the FEAS1 budget and admission
disposition at representative scale would not be observable at all.

## 3. Focused falsification (real owner, four tests)

`tests/test_mlff_target_order_real_owner.py`, R14 section. Test doubles observe
the queue and the applied scope only *below* the real production/FEAS1 owner and
delegate all real queue behavior to `DeterministicWorkQueue`.

| Test | Workplan §4 item | Claim |
|---|---|---|
| `..._r14_feas1_inherits_the_campaign_scope_and_owns_its_native_limits` | 1, 2, 3 | production `_build_current_target_training_order()` → `prepare_target_training_order()` → FEAS1 reaches exactly the root CPU/RAM budget; widths preserved; `manage_resource_scope` true; queue enters with a finite `memory_budget_bytes` and reports it |
| `..._r14_a_small_finite_budget_reaches_feas1_queue_admission` | 4 | a deliberately small finite budget is refused by the FEAS1 queue that owns admission, with no host exhaustion and no geometry produced for publication |
| `..._r14_a_locally_synthesized_feas1_scope_is_still_applied` | 5 | with no caller scope, FEAS1's own synthesized scope is actually applied by `stage_resource_scope()` |
| `..._r14_feas1_products_are_identical_under_the_resource_routing` | 6 | serial, bounded-parallel and inherited-finite-budget FEAS1/NEIGHBOR1 produce identical geometry and neighborhood digests |

Item 7 (final target-order build/selection/repair/order/MVQUAL identity) is
carried by the existing R13 identity test, which prepares the same exact
`P_train` with and without a finite scope and now exercises the FEAS1 routing on
both paths, and by the representative build identity in §4.

**Falsification check.** With only the two product edits stashed and the new
tests kept, the two routing tests fail at the basis:

```text
FAILED ..._r14_feas1_inherits_the_campaign_scope_and_owns_its_native_limits
FAILED ..._r14_a_locally_synthesized_feas1_scope_is_still_applied
2 failed, 2 passed
```

## 4. Representative current-scale acceptance

Same substrate as R11/R12/R13: the stakeholder's live LTA/mpa0/FP32 campaign
configuration, copied into a disposable scratch workspace. The live campaign
directory is never entered. The inferred manifest is byte-identical to every
earlier run (`sha256 591f2c4a21cf…`), 27 VASP runs, exact `|P_train| = 33,984`.

### 4.1 FEAS1/NEIGHBOR1 under the inherited budget

The one FEAS1 stage line, verbatim:

```text
[target-order] status=complete; families=78; edges=2216469672; elapsed=00:08:49;
TARGET-ORDER/feas1-neighbor1: cpu=28/28 budget; python=28; structure=1; tree=1;
blas=1; openmp=1; torch=1; gpu_jobs=0; ram_budget=41804365824;
queue_lanes=28; queue_max_busy=28; queue_peak_accounted_bytes=990128480;
queue_memory_budget_bytes=41804365824; queue_memory_backpressure=0;
queue_backpressure=12; queue_tasks=4744
```

| Required item | Observed |
|---|---|
| finite stage RAM budget inherited from the campaign scope | `ram_budget=41,804,365,824` B (38.93 GiB), identical to the root/COVREF budget; R13 logged no FEAS1 budget at all |
| worker/tree/native-thread disposition | `python=28; tree=1; blas=1; openmp=1`, 28 queue lanes, `max_busy=28` — the widths FEAS1 already used, now with its own quarantine applied |
| queue memory budget | `queue_memory_budget_bytes=41,804,365,824` (was unbounded) |
| queue peak accounted memory | `990,128,480` B over 4,744 committed tasks |
| backpressure / fail-closed disposition | `queue_memory_backpressure=0`; 12 queue-shape backpressure events (ready/completed bounds, not memory); no refusal, so the budget is non-constraining here |

### 4.2 External peak RSS across FEAS1/NEIGHBOR1

10 Hz external `/proc/<pid>/statm` + `VmHWM` sampling of the unmodified campaign
process, correlated against the campaign's own stage markers. 5,268 samples over
the 528.7 s stage.

| Quantity | Value |
|---|---|
| FEAS1 entry RSS | 4.80 GiB |
| **FEAS1 in-stage peak RSS** | **32.91 GiB** |
| FEAS1 exit RSS | 15.14 GiB (packed NEIGHBOR1 roots still resident until publication) |
| `VmHWM` at stage entry → exit | 5.73 GiB → 32.90 GiB |
| process peak before FEAS1 | 5.60 GiB |
| whole-`prepare` peak RSS | 32.91 GiB |
| stage RAM budget | 38.93 GiB |

`VmHWM` rising only inside this window is the second witness that the whole-run
peak is FEAS1's, and that no earlier stage set it. The stage peak is **84.5 % of
the inherited budget** and inside it; the whole process never exceeded the
budget. Compare R12's 32.1 GiB and R13's envelope: unchanged within run-to-run
variation.

**Reported honestly, not smoothed:** the queue's accounted peak (0.94 GiB) is
two orders of magnitude below the process peak. The deterministic queue accounts
its per-task estimates and its explicit `state:*` reservations; the dominant
FEAS1 allocation at this scale is the packed NEIGHBOR1 CSR store (2.22 B edges),
which is not a queue task. The budget therefore genuinely reaches FEAS1 and
genuinely fails closed on task admission (§3, item 4), but on this substrate it
is not the quantity that bounds the stage's true peak. This is an accounting
coverage observation for the resource owner (§8), not a defect introduced here,
and not a reason to bypass the budget: the workload fits the accepted campaign
resource policy, so no D3 resource Challenge is raised.

### 4.3 Scientific identity and stage cost versus R13

```text
[target-order] stage=published; build=b8d75b6a1857; swaps=49;
phase_a_completed_at=361; selector_workers=16
[target-order] stage=FEAS1; state=cross_support_fragile; k_min_lower_bound=90
[target-order] stage=MVQUAL; qualified_sizes=[512, 1024, 2048, 4096, 8192, 16384]
```

Every accepted invariant of this substrate is reproduced exactly: 78 families,
739 obligations, 2,216,469,672 NEIGHBOR1 edges, FEAS1 `cross_support_fragile`
with `k_min_lower_bound=90`, Phase A→B at rank 361, 49 REPAIR2 swaps, MVQUAL
{512…16384}, published build **`b8d75b6a1857`**. The per-rung REPAIR2 trace is
bitwise the accepted one:

| shell | 128 | 256 | 512 | 1,024 | 2,048 | 4,096 | 8,192 | 16,384 |
|---|---|---|---|---|---|---|---|---|
| swaps | 0 | 0 | 0 | 32 | 3 | 5 | 3 | 6 |
| `proposals` | 0 | 0 | 0 | 2,048 | 320 | 448 | 320 | 512 |
| `frontier_max` | 0 | 0 | 0 | 18 | 31,936 | 29,888 | 25,792 | 17,600 |

| Stage | R12 | R13 | **R14** |
|---|---|---|---|
| universal structural provider | 253 s | 249.9 s | 258.8 s |
| `TargetCoverageReference` (PAR1) | 58 s | 55.2 s | 55.7 s |
| **shared FEAS1/NEIGHBOR1** | 150–516 s band | 544.6 s | **528.7 s** |
| MVIDX | ~70 s | 124.6 s | 131.0 s |
| MVSEL2 to `N_max` | 234.9 s | 266.2 s | 238.9 s |
| **REPAIR2** | 99 s | 111 s | **102 s** |
| MVSEL2 suffix | 162.3 s | 199.5 s | 167.6 s |
| MVQUAL | ~20 s | 19.8 s | 20.0 s |
| whole `prepare` | 1,920.9 s | 2,014.97 s | **1,967.3 s** |

FEAS1 is 16 s *faster* than R13 despite now running under an applied
`blas=1; openmp=1` quarantine, so the quarantine costs nothing material on this
substrate. This run's preflight chose width 16 (as R11/R12 did; R13 chose 28),
which accounts for the MVSEL2/REPAIR2/suffix differences versus R13 — the
preflight is a sub-10 ms wall-clock meter and takes no `resource_scope`; it is
untouched by this revision. R12's performance closure is intact: REPAIR2 102 s
against R11's 6,156 s.

### 4.4 Reuse

A second `prepare` on the published workspace, same command:

```text
[target-order] status=reused; build=b8d75b6a1857
EXIT=0 elapsed=337s          (R13 reuse: 333.4 s; R12: 5 m 36 s)
```

The immutable create-or-verify publication is authenticated and reused; no
target-order stage re-executes and FEAS1 is not re-entered.

## 5. Evidence preserved as applicable

Preserved without rerunning; the FEAS1 scope change does not invalidate their
regimes:

- R11 correctness/ownership evidence — no R11-owned surface changed;
- R12 bitwise REPAIR2 scalar/native equivalence and optimization evidence — the
  repair plan is reproduced bitwise above at the same width R12 measured;
- R12 restart-cost closure — the reuse path is re-confirmed in §4.4;
- R13 COVREF finite-budget peak-RSS evidence — COVREF's route, budget and
  telemetry are unchanged (`ram_budget=41804365824`, zero backpressure);
- R13 canonical HAS against accepted `main` `e72090e2…`;
- R13 MVIDX/MVQUAL resource-scope behavior — re-exercised by the affected
  regression in §7.

## 6. Canonical Protocol 6.3 Historical Applicability Set

Accepted `main` is unchanged at `e72090e21cec5311ce87745b03603f8783cd15a7`, so
no basis refresh is required. `PROJECT-ENGINEERING-MEMORY.md` is byte-identical
to the accepted basis on this branch, so there is no validated same-branch
candidate overlay. Every entry is `EVIDENCE_ONLY`: a replaceable design prior,
not authority. R13's dispositions are preserved; only the reasons are updated
for this revision's surface.

```yaml
pem_basis:
  accepted_project_state: e72090e21cec5311ce87745b03603f8783cd15a7
  accepted_pem: hjin98/mdstats@e72090e21cec5311ce87745b03603f8783cd15a7:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: SP-001
    disposition: APPLICABLE
    reason: >-
      Owner-layer reduction governed this repair directly. B14-1 was closed by
      passing one existing argument through one existing interface and deleting
      the last provenance-dependent manage_resource_scope override; no resource
      manager, admission policy, memory fraction or wrapper was added, and the
      flag now has no reader in the repository.
  - id: SP-002
    disposition: APPLICABLE
    reason: >-
      Fail-closed authenticated boundaries remain applicable to target-order
      publication and currentness state. None was relaxed. The small-budget
      test confirms the FEAS1 queue refuses inadmissible work at the real owner
      rather than degrading silently or publishing partial geometry.
  - id: SP-003
    disposition: APPLICABLE
    reason: >-
      Immutable durable boundaries and restart reuse governed the decision to
      add no resource-side persistent state; the representative reuse run in
      section 4.4 re-confirms create-or-verify reuse at scale.
  - id: SP-004
    disposition: APPLICABLE
    reason: >-
      Acceptance rests on the real production and FEAS1 owners plus a
      representative current LTA prepare on the stakeholder's own campaign
      configuration, with the FEAS1 peak-RSS claim measured externally against
      the real process rather than inferred from stage deltas.
  - id: FF-001
    disposition: NOT_APPLICABLE
    reason: >-
      R14 touches no MACE model reconstruction, accelerator realization or
      checkpoint architecture identity.
  - id: FF-002
    disposition: APPLICABLE
    reason: >-
      Pre-adoption target-order checkpoints and post-N_max restart behavior lie
      inside the continuation-authority family surface; R14 adds no continuation
      state and changes no authenticated restart boundary.
  - id: FF-003
    disposition: APPLICABLE
    reason: >-
      Immutable publication and cleanup ownership remain material to the
      target-order durable boundary; R14 adds no storage, cleanup or GC path,
      and FEAS1 scratch remains attempt-owned and removed by prepare.
  - id: FF-004
    disposition: NOT_APPLICABLE
    reason: >-
      Preserved from R13. Its accepted semantic identity is bounded to P5 TRAIN2
      GPU scheduling, process supervision and CUDA residency lifetime; the
      accepted metadata does not place target-order CPU-RAM admission inside
      that family, and mechanism resemblance alone is not sufficient to widen an
      accepted family. Current resource authority governs B14-1 independently.
  - id: FF-005
    disposition: APPLICABLE
    reason: >-
      Downstream selection must keep consuming prepared target-order evidence
      without reconstructing preparation-owned science; R14 changes only
      preparation-internal execution, and section 4.4 re-confirms the routing.
```

**Closeout learning assessment.** No PEM mutation is proposed. The
`manage_resource_scope` polarity incoherence now has three closed instances
across two revisions, which is closer to an admissible chronology than R13's
single observation — but all three were one latent coupling in one parameter,
closed by deletion, and the parameter now has no reader at all. That is an
incomplete sweep inside one repair episode, not a recurrence after a closed
repair, and it does not meet the Protocol 6.3 threshold for a new family,
occurrence or application episode. It is recorded as the §8 observation instead.

## 7. Executed checks

Python for this repository is `/home/samjin/miniconda3/envs/mace/bin/python`.

```text
# real-owner suite including the four R14 falsification tests
python -m pytest tests/test_mlff_target_order_real_owner.py -q -p no:randomly

# representative current-scale LTA campaign, disposable scratch workspace;
# the stakeholder's live campaign directory is never entered
cp ~/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/campaign.toml <ws>/
python -m mdstats.training_data.campaign_cli --config <ws>/campaign.toml doctor
                                             prepare                    # infers manifest
                                             prepare --approve-manifest
# the measured fresh build, under the external 10 Hz /proc sampler
python harness.py <ws> python -m mdstats.training_data.campaign_cli \
                             --config <ws>/campaign.toml prepare
# the reuse path on the published workspace, same command again

# affected regression
python -m pytest $(cat affected.txt) -q -p no:randomly -n 16
```

| Check | Result |
|---|---|
| `tests/test_mlff_target_order_real_owner.py` | **37 passed** (33 pre-existing + 4 new) |
| representative fresh LTA `prepare` | **exit 0**, build `b8d75b6a1857`, 1,967.3 s |
| FEAS1/NEIGHBOR1 in-stage peak RSS under the inherited finite budget | **measured**, §4.2 |
| representative reuse `prepare` | **exit 0**, 337 s, `status=reused; build=b8d75b6a1857` |
| affected regression, 52 files | **1,275 passed / 4 failed**; all four reproduced at the basis (§7.1) |

**Affected-surface derivation.** Every test file referencing `target_order`,
`prepare_target_training_order`, `build_target_coverage_reference`, `REPAIR2`,
`MVQUAL`, `MVIDX`, `MVSEL2`, the `real_target_order` substitute marker,
`campaign_target_size_runtime`, `work_queue`/`DeterministicWorkQueue`,
`StageResourceScope`/`build_stage_resource_scope`, `_performance_resources`,
`detect_system_resources`, `training_data.resources`, `prepared_generation`, or
the `prepare` command — the same rule R13 used. The excluded remainder is the
density/geometry/topology subsystem, which shares no changed module.

### 7.1 Affected regression, with a stashed baseline

52 files at `-n 16`, after all R14 edits:

```text
4 failed, 1275 passed, 2424 warnings in 1834.89s
FAILED tests/test_mlff_mace_compatibility.py::test_campaign_evaluate_outer_scope_catches_setup_warnings
FAILED tests/test_mlff_mace_compatibility.py::test_campaign_main_owns_one_warning_domain_and_normalizes_output
FAILED tests/test_mlff_mace_compatibility.py::test_campaign_warning_domain_merges_worker_thread_local_scopes
FAILED tests/test_mlff_target_order_real_owner.py::test_real_owner_many_family_forward_restore_maps_constant_fds
```

The same 52 files at the basis, with every R14 product **and** test edit
stashed (`git stash push -- <the three changed files>`):

```text
4 failed, 1271 passed, 2428 warnings in 1754.29s
```

— the identical four failures. **New-failure delta against the basis: zero**,
and the +4 passes are exactly the four new R14 tests.

None of the four is skipped, xfailed or otherwise suppressed. Attribution:

- the three `test_mlff_mace_compatibility.py` failures are the long-standing
  environment defect already attributed in R13 — the `mdstats-mlff-campaign`
  console script is not installed in this environment, so the campaign argument
  parser is never reached;
- `test_real_owner_many_family_forward_restore_maps_constant_fds` fails with
  `OSError: [Errno 24] Too many open files` while memory-mapping a published
  MVIDX packed member under 16-way worker contention. It passes in isolation
  (`1 passed in 3.54s`) and in a 9-file `-n 16` subset, and it fails identically
  at the basis, so it is xdist fd pressure rather than a product regression. R14
  opens no additional persistent descriptor: FEAS1 scratch is attempt-owned and
  removed, and the MVIDX restore path is untouched.


## 8. Documentation, dependency, history and residual risk

**Documentation.** None required. The D3 manual delegates worker counts, queue
timing and native-thread realization to D4 and declares them execution-only. R14
changes no documented interface, schema, CLI surface or scientific product, and
the `60_execution_performance.md` constraint that long-stage work is admitted
under its resource owner is satisfied for the first time at FEAS1.

**Dependencies.** None added or changed.

**History.** No migration, revert or recovery; no published artifact schema or
build identity moved (`b8d75b6a1857` is unchanged).

**Residual risk, reported not acted on.**

1. **Queue accounting does not cover FEAS1's dominant allocation.** §4.2: the
   process peaked at 32.91 GiB while the queue accounted 0.94 GiB, because the
   packed NEIGHBOR1 CSR store is not a queue task. The budget is real, reaches
   the stage and refuses inadmissible tasks, but it is not what bounds the true
   stage peak at this scale. Widening queue accounting to the packed store is a
   resource-owner question with its own design cost and is not silently taken
   here.
2. **`manage_resource_scope` now has no reader.** Every call site uses the
   default. Removing the parameter is a further reduction, but the accepted
   Revision 14 contract explicitly directs FEAS1 to "use its existing default",
   so changing a general utility's signature is left to the resource owner
   rather than taken unilaterally.
3. **The MVSEL2 native preflight decision is not stable across runs** (16 here
   and in R11/R12, 28 in R13). Pre-existing, outside R14's scope, recorded in
   §4.3.
4. **Final production GPU qualification remains deferred** to the complete
   release package on the stakeholder machine, per the accepted plan.
5. **No CI status is attached to this candidate.** Everything above is
   implementation-recorded local execution, to be assessed as evidence rather
   than treated as CI-attested fact.

## 9. Reconciliation against the Revision 14 re-review gate

| Gate | Status |
|---|---|
| 1. every R11/R12/R13 accepted closure intact | **yes** — §5, §4.3; build identity, repair trace and reuse path all reproduced |
| 2. campaign root CPU/RAM scope reaches FEAS1/NEIGHBOR1 through the existing interface | **yes** — §2.1, §4.1; `ram_budget=41804365824` where R13 had none |
| 3. FEAS1 no longer disables its own declared native-thread scope by provenance | **yes** — §2.2; the override is deleted and the flag has no reader |
| 4. finite-budget queue admission/backpressure/failure exercised at the real FEAS1 owner | **yes** — §3 test 2 at `build_target_coverage_geometry`, plus §4.1's live budget and backpressure counters |
| 5. representative FEAS1 and whole-prepare execution inside the accepted envelope | **yes** — §4.2; 32.91 GiB peak against a 38.93 GiB budget, no refusal, no host pressure |
| 6. exact FEAS1/NEIGHBOR1 and final target-order scientific identities unchanged | **yes** — §3 test 4 and §4.3; 2,216,469,672 edges, `b8d75b6a1857`, 49 swaps, MVQUAL {512…16384} |
| 7. affected final regression introduces no new failure | §7 |
| 8. no new resource-policy/selector/persistence/currentness/cleanup/compatibility owner | **yes** — §1 structural negative evidence |
| 9. canonical HAS/PEM basis valid or refreshed | **yes** — §6; accepted basis unchanged |
