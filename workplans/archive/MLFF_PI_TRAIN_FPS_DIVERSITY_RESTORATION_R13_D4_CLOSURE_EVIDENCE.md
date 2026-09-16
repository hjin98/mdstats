---
kind: implementation-evidence
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 13
protocol_version: 6.3.0
status: active
evidence_date: 2026-09-16
branch: design/mlff-pi-train-fps-diversity-restoration
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
parent_implementation_commit: 9c41f44be32dd0e4f3869e6e48be4e85b9effce9
r13_implementation_commit: d993f25e28f7d0886ef7628c0a39feeb91adaf33
reviewed_r12_candidate: c6fbe03c92f23a79123031922f338966e9c76c6b
highest_affected_domain: D4
upstream_authority_state: D1_D2_D3_ACCEPTED_UNCHANGED
serious_challenge: false
---

# Revision 13 D4 resource-routing and HAS closure evidence

Revision 13 closes B13-1 (the campaign RAM budget never reached target-order
preparation, and the R12 COVREF RAM measurement was not a peak) and B13-2 (the
HAS was not in the canonical Protocol 6.3 interface). No D1/D2/D3 change was
required and none is proposed.

## 1. Changed files

| File | Change |
|---|---|
| `mdstats/training_data/campaign_target_size_runtime.py` | `_build_current_target_training_order()` builds one root `TARGET-ORDER` `StageResourceScope` from the already-resolved `_performance_resources(cfg)` snapshot and passes it as `resource_scope`. |
| `mdstats/training_data/target_order/sparse_index.py` | Removed the `manage_resource_scope=resource_scope is None` override at the MVIDX queue. |
| `mdstats/training_data/target_order/qualification.py` | Removed the `manage_resource_scope=owned` override at the MVQUAL queue. |
| `tests/test_mlff_target_order_real_owner.py` | Four R13 falsification tests; `_prepare` takes `workers` through `kwargs` so a test can choose the execution width. |

The complete product diff adds **no class, no function, no module and no
configuration key**:

```text
$ git diff -U0 -- mdstats/ | grep -E '^\+' | grep -E 'class |def '
(no output)
```

## 2. B13-1 — the missing edge, and why it was the only defect

### 2.1 Production routing

`_build_current_target_training_order()` already resolved the campaign
`SystemResourceSnapshot` through `_performance_resources(cfg)` and already
passed it to the universal structural provider. It passed only
`workers=resources.cpu_threads_budget` to `prepare_target_training_order()`.
Everything downstream of that call already accepted or inherited
`resource_scope`: COVREF builds its `TARGET-ORDER-COVREF` scope from it, MVIDX
derives its per-lane out-of-core admission ceiling from it, REPAIR2 caps its
execution width by it, and MVQUAL inherits it. The repair is therefore one
argument through an interface that already existed, using the existing
`build_stage_resource_scope()` helper and the existing snapshot:

```python
target_order_scope = build_stage_resource_scope(resources, stage_name="TARGET-ORDER")
...
    workers=max(1, int(resources.cpu_threads_budget)),
    resource_scope=target_order_scope,
```

The root scope declares `python_workers=1`: it is a budget carrier, not a width
authority. Every nested stage keeps the width decision it already owned, so
COVREF, MVIDX, MVQUAL and REPAIR2 receive exactly the CPU numbers they received
before, plus a RAM budget they previously did not receive.

### 2.2 The one coupling that had to be altered, not wrapped

`DeterministicWorkQueue.manage_resource_scope` decides whether the queue applies
its scope's BLAS/OpenMP limits. Three call sites read it three different ways:

| Stage | Before | Meaning |
|---|---|---|
| MVIDX | `resource_scope is None` | quarantine only when *no* scope was inherited |
| MVQUAL | `owned` (= `resource_scope is None`) | same |
| FEAS1 | `resource_scope is not None` | the exact opposite |

The flag conflates two unrelated facts: *who supplies the budget* and *who has
already quarantined native threads*. Nothing in the target-order path ever
enters `stage_resource_scope()` around preparation, so before R13 both MVIDX and
MVQUAL quarantined (their `resource_scope` was `None`). Threading the root scope
through without touching this would have silently **stopped** applying
`blas=1`/`openmp=1` in both stages, oversubscribing 28 Python lanes against
BLAS/OpenMP pools and violating the accepted D3 constraint in
`docs/arch_manuals/mlff_training_data/60_execution_performance.md`:

> Nested numerical parallelism is suppressed while outer work fills the resource
> budget: `P_outer · P_native ≤ P_budget`. … A process or worker does not
> independently oversubscribe the host.

Both stages construct and describe their own stage nesting, so both must apply
it. The repair is the removal of the two overrides — the queue default is
already `True` — not a new flag, wrapper or coordinator. FEAS1 is left untouched:
it is never passed a `resource_scope` from preparation, so its behavior is
unchanged either way (§9).

### 2.3 MVIDX admission is provably unchanged by the finite budget

MVIDX computes

```text
admission = min(768 MiB, ram_budget_bytes // width)
```

At representative scale `ram_budget_bytes = 41,431,436,492` and
`width = min(28, 78) = 28`, so the per-lane share is **1,479,694,160 B
(1.38 GiB) > 768 MiB** and the admission ceiling stays at its unbounded value of
768 MiB. `chunk_scratch` derives from `admission` and is likewise unchanged at
384 MiB. The finite budget is therefore non-constraining for MVIDX on this
substrate by arithmetic, not by assumption.

## 3. Focused falsification (real owner, four tests)

`tests/test_mlff_target_order_real_owner.py`, which opts out of the downstream
target-order substitute (`pytestmark = pytest.mark.real_target_order`):

| Test | Claim falsified |
|---|---|
| `..._r13_campaign_ram_budget_reaches_target_order_preparation` | The production caller passes a non-`None` `resource_scope` binding the snapshot's exact `cpu_threads_available`, `cpu_threads_budget` and `ram_budget_bytes`; `workers` is still the CPU budget alone; the root scope claims `python_workers=1`; an unresolvable host RAM budget stays `None` rather than being invented. |
| `..._r13_covref_and_mvidx_inherit_the_finite_ram_budget` | COVREF-PAR1 telemetry reports a finite `ram_budget` and `queue_memory_budget_bytes`; every MVIDX and MVQUAL queue is entered with the same finite budget and the same CPU numbers, still manages its own native limits, and records `memory_backpressure_events=0` under a non-constraining budget. |
| `..._r13_finite_budget_does_not_change_any_scientific_identity` | Paired bounded/unbounded preparation of the same exact `P_train`: identical `build_identity`, preparation digest, selection-plan digest, repair-plan digest, `total_swaps`, qualification digest, complete order, REPAIR2 start width and MVSEL2 preflight `effective_workers`; serial COVREF digest equals block-parallel COVREF digest under the finite budget. |
| `..._r13_a_small_finite_budget_reaches_queue_admission` | A deliberately small finite budget routed through the production caller reaches deterministic-queue admission and fails closed there (`DeterministicWorkQueueMemoryError`, "above the stage RAM budget"), publishing no reference, geometry, MVIDX or build artifact. No host exhaustion is used. |

The real semantic owner of every claim is live: the production routing function,
the real `prepare_target_training_order`, the real COVREF/MVIDX/MVQUAL stages
and the real `DeterministicWorkQueue`. The only doubles are *below* the owner —
a controlled `SystemResourceSnapshot` in place of host detection, the fixture's
structural catalog in place of the universal provider, and a `DeterministicWorkQueue`
subclass that records the scope it is entered with and delegates every behavior
to the real queue.

Whole file: **33 passed** (29 pre-existing R11/R12 tests plus 4).

## 4. Representative current-scale acceptance under the restored routing

### 4.1 Fixture identity — the same substrate R11 and R12 measured

A byte-identical copy of the stakeholder's
`05_mace_training/LTA/mpa0/FP32/campaign.toml` (sha256
`059ab8fe5e856fb1a676111219ed399379d8fde12e757e9e37267e53879ca5f3`, the same
hash R12 recorded), run in a disposable scratch workspace; the live campaign
directory was never entered. Machine: 32 threads / 28-thread budget, 62 GiB RAM,
RTX 3090.

| Identity | R11 | R12 | **R13** |
|---|---|---|---|
| retained frames / exact `\|P_train\|` | 37,633 / 33,984 | 37,633 / 33,984 | **37,633 / 33,984** |
| reference families / structural | 78 / 8 | 78 / 8 | **78 / 8** |
| NEIGHBOR1 witnesses | 2,367,624 | 2,367,624 | **2,367,624** |
| FEAS1 state / `k_min` | `cross_support_fragile` / 90 | same | **`cross_support_fragile` / 90** |
| REPAIR2 swaps per rung | (0,0,0,32,3,5,3,6) | same | **(0,0,0,32,3,5,3,6) = 49** |
| Phase A → B rank | 361 | 361 | **361** |
| MVQUAL qualified sizes | {512…16384} | same | **{512…16384}** |
| **published build identity** | `b8d75b6a1857` | `b8d75b6a1857` | **`b8d75b6a1857`** |
| exit status | 0 | 0 | **0** |

The complete scientific build identity is unchanged. Gate 6 holds.

### 4.2 The required COVREF RAM evidence, item by item

Measured with an **external** qualification harness (`rss_probe.py`) that spawns
the unmodified campaign process and samples `/proc/<pid>/statm` and
`/proc/<pid>/status:VmHWM` at 10 Hz while timestamping the campaign's own stdout.
No product machinery was added for this measurement and nothing here enters a
build identity.

| Workplan §2.5 item | Measured |
|---|---|
| 1. process RSS immediately before COVREF | **5,350,711,296 B (4.98 GiB)** |
| 2. **actual peak process RSS while COVREF executes** | **5,531,447,296 B (5.15 GiB)**, from 548 samples across the 55.2 s stage |
| 3. incremental peak (`peak − entry`) | **+180,736,000 B (+172.4 MiB)** |
| 4. process RSS after COVREF release | **5,141,274,624 B (4.79 GiB)** |
| 5. governing `StageResourceScope.ram_budget_bytes` | **41,431,436,492 B (38.6 GiB)** — finite; R12 recorded `None` |
| 6. deterministic-queue accounting | peak accounted **140,204,736 B (133.7 MiB)** over **20,234** committed tasks; `memory_backpressure=0`; `queue_backpressure=0`; `memory_budget_bytes=41,431,436,492` (R12: `None`) |
| 7. COVREF worker width / block size | `queue_lanes=28`, `queue_max_busy=28`, `python_workers=28`, `tree_workers=1`, `blas_threads=1`, `openmp=1`, `radius_block_size=1024`, `query_workers=1`; estimated nested threads 28 ≤ budget 28 |
| 8. whole-prepare peak RSS / wall | **37,185,024,000 B (34.63 GiB)** / **2,014.97 s (33 m 35 s)**, exit 0 |

The governing stage telemetry line, in full:

```text
stage=target-coverage-reference; execution=covref-par1; TARGET-ORDER-COVREF:
cpu=28/28 budget; python=28; structure=1; tree=1; blas=1; openmp=1; torch=1;
gpu_jobs=0; ram_budget=41431436492; radius_block_size=1024; query_workers=1;
queue_lanes=28; queue_max_busy=28; queue_peak_accounted_bytes=140204736;
queue_memory_budget_bytes=41431436492; queue_memory_backpressure=0;
queue_backpressure=0; queue_tasks=20234
```

**The transient-peak scenario R12 could not falsify is now falsified two ways.**
The direct sampler observed an in-stage peak only 172 MiB above entry — 0.44 %
of the stage budget, the whole stage peaking at 13.3 % of it. Independently,
`VmHWM` was **6,150,418,432 B at both stage entry and stage exit**: COVREF set no
new process high-water mark at all, so no unobserved excursion above the sampled
peak is possible within the stage. Measured execution is inside the governing
resource envelope with three orders of magnitude of headroom, and no admission
contract was approached, let alone exceeded.

For completeness on the observation that originally raised this question: the
**whole-prepare** peak was 34.63 GiB (R11: 36.4 GiB), against a campaign plan
line of 41.7 GiB resolved at doctor time and a target-order stage budget of
38.6 GiB. That peak is accumulated across P1/P2 substrate, the structural
provider and NEIGHBOR1 — not by COVREF, whose own contribution is the +172 MiB
above. Both quantities are now measured against a real budget instead of
compared across incommensurable scopes.

### 4.3 Stage wall clock, and an honest attribution of what moved

| Stage | R12 | R13 | Attribution |
|---|---|---|---|
| universal structural provider | 253 s | 249.9 s | unchanged |
| `TargetCoverageReference` (PAR1) | 58 s | **55.2 s** | unchanged |
| shared FEAS1/NEIGHBOR1 | ~150 s + FEAS1 | 544.6 s | inside the historically observed 150–516 s band; not on the R13 route |
| MVIDX | ~70 s | 124.6 s | out-of-core I/O variance; admission ceiling provably identical (§2.3) |
| MVSEL2 to `N_max` | 234.9 s | 266.2 s | execution width 28 vs 16 |
| **REPAIR2** | **99 s** | **111 s** | execution width 28 vs 16 |
| MVSEL2 suffix | 162.3 s | 199.5 s | execution width 28 vs 16 |
| MVQUAL | ~20 s | 19.8 s | unchanged |
| whole `prepare` | 1,920.9 s | 2,014.97 s | +4.9 % |

**The width difference is not caused by R13.** `preflight_native_workers()` takes
no `resource_scope` and is untouched by this revision. Its meters run at
`sample=256` and resolve in single-digit milliseconds, and this run's best
parallel meter landed on 28 rather than 16:

```text
stage=MVSEL2-preflight; sample=256; edges=16558201;
meters=1w:0.012s/1.00x,2w:0.008s/1.60x,4w:0.006s/1.91x,8w:0.005s/2.53x,
16w:0.005s/2.52x,28w:0.005s/2.71x; best_parallel_speedup=2.71x;
threshold=1.05x; scaling=pass; effective_workers=28
```

Two consequences, both recorded rather than smoothed over:

1. **This strengthens the execution-only claim.** R11 and R12 both ran REPAIR2
   at width 16. R13 ran it at width 28 and reproduced the repair *exactly* —
   same 49 swaps in the same per-rung distribution, and identical
   `proposals`/`frontier_max`/`shortlist_max` at every rung:

   | shell | swaps R12 → R13 | proposals | `frontier_max` | `shortlist_max` |
   |---|---|---|---|---|
   | 128 / 256 / 512 | 0 → **0** | 0 | 0 | 0 |
   | 1,024 | 32 → **32** | 2,048 | 18 | 64 |
   | 2,048 | 3 → **3** | 320 | 31,936 | 64 |
   | 4,096 | 5 → **5** | 448 | 29,888 | 64 |
   | 8,192 | 3 → **3** | 320 | 25,792 | 64 |
   | 16,384 | 6 → **6** | 512 | 17,600 | 64 |

   A width-independent repair plan across two different widths on the real
   substrate is better evidence than a matched-width repeat would have been.

2. **The preflight decision is not stable run to run**, and 28 is mildly worse
   than 16 here (+12 s REPAIR2, +31 s MVSEL2, +37 s suffix). That is a
   pre-existing property of a sub-10 ms meter, is outside R13's scope, and is
   reported as an observation in §9 rather than repaired here.

R12's headline closure is intact on its own terms: REPAIR2 remains ~111 s
against R11's 6,156 s.

### 4.4 Reuse and downstream routing

A second `prepare` on the published workspace re-confirms the R11 create-or-verify
reuse path under the restored resource routing: see §8 for the executed command
and result.

## 5. B13-2 — canonical Protocol 6.3 Historical Applicability Set

Resolved basis. Accepted `main` is unchanged at
`e72090e21cec5311ce87745b03603f8783cd15a7`, so no basis refresh is required. The
branch tip carries a byte-identical `PROJECT-ENGINEERING-MEMORY.md`
(`git diff e72090e2..HEAD -- PROJECT-ENGINEERING-MEMORY.md` is empty; sha256
`7b0d342b3be3b2773bc2012fde74af2ddb89bcd6106885aae2ace3d217ce5945`), so there is
**no validated same-branch candidate overlay**. The literal `candidate_overlay`
string inside that file names an unrelated branch and is not an overlay for this
candidate. Every entry below is `EVIDENCE_ONLY` binding: a replaceable design
prior, not authority.

```yaml
pem_basis:
  accepted_project_state: e72090e21cec5311ce87745b03603f8783cd15a7
  accepted_pem: hjin98/mdstats@e72090e21cec5311ce87745b03603f8783cd15a7:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: SP-001
    disposition: APPLICABLE
    reason: >-
      Owner-layer reduction governed this repair directly. B13-1 was closed by
      passing one existing argument through one existing interface and by
      deleting two contradictory manage_resource_scope overrides; no resource
      manager, admission database, memory fraction or wrapper was added.
  - id: SP-002
    disposition: APPLICABLE
    reason: >-
      Fail-closed authenticated boundaries remain applicable to target-order
      publication, checkpoint and currentness state. None was relaxed, and the
      small-budget test confirms the queue refuses inadmissible work rather
      than degrading silently.
  - id: SP-003
    disposition: APPLICABLE
    reason: >-
      Immutable durable boundaries and restart reuse governed the decision to
      add no repair-side persistent state in R12 and to add no resource-side
      persistent state in R13; the reuse path is re-confirmed in section 8.
  - id: SP-004
    disposition: APPLICABLE
    reason: >-
      Acceptance rests on the real-owner suite plus a representative current
      LTA prepare on the stakeholder's own campaign configuration, with the
      peak-RSS claim measured against the real process rather than inferred.
  - id: FF-001
    disposition: NOT_APPLICABLE
    reason: >-
      R12/R13 touch no MACE model reconstruction, accelerator realization or
      checkpoint architecture identity.
  - id: FF-002
    disposition: APPLICABLE
    reason: >-
      Pre-adoption target-order checkpoints and post-N_max restart behavior lie
      inside the continuation-authority family surface; R13 adds no continuation
      state and changes no authenticated restart boundary.
  - id: FF-003
    disposition: APPLICABLE
    reason: >-
      Immutable publication and cleanup ownership remain material to the
      target-order durable boundary; R13 adds no storage, cleanup or GC path.
  - id: FF-004
    disposition: NOT_APPLICABLE
    reason: >-
      Its accepted semantic identity is bounded to P5 TRAIN scheduler, TRAIN2
      process supervision and CUDA residency lifetime, with aggregation_scope
      "P5 TRAIN2 GPU scheduling and process/resource lifetime repairs". The
      accepted metadata does not place target-order CPU-RAM admission inside
      that family, and its mechanism resemblance is not sufficient to widen it.
      Current resource authority governs B13-1 independently of PEM.
  - id: FF-005
    disposition: APPLICABLE
    reason: >-
      Downstream selection must keep consuming prepared target-order evidence
      without reconstructing preparation-owned science; R13 changes only
      preparation-internal execution, and section 8 re-confirms the routing.
```

**Closeout learning assessment.** No PEM mutation is proposed. B13-1 is a single
missing call argument in one function, closed in one revision with no recurrence
chronology; it does not meet the Protocol 6.3 admission threshold for a new
family, occurrence or application episode. The `manage_resource_scope` polarity
incoherence is a more interesting candidate but has exactly one observed
instance and is offered as the §9 observation instead.

## 6. R11/R12 closure preservation and negative evidence

Structural negative evidence, run against the product diff:

```text
$ git diff -U0 -- mdstats/ | grep -E '^\+' | grep -E 'class |def '
(no output)
$ git diff -- mdstats/ | grep -E '^\+.*(Manager|Policy|Cache|Store|Registry|fallback|compat)'
(no output)
```

Confirmed absent from R13's surface: no new selector, no alternate suffix, no
repair algorithm or compatibility mode, no currentness/checkpoint store, no
repair-side durable cache, no cleanup or GC owner, no second memory manager, no
target-order-specific memory fraction, no change to the campaign RAM fraction,
and no second structural-provider resource policy — the provider still receives
`resources` directly from its existing owner.

R12's own closures are re-confirmed by the representative run: the `_StateBatch`
batched REPAIR2 path is unchanged, D2 §9 semantics are unchanged, the repair
plan is bitwise reproduced (§4.3), REPAIR2 remains ~111 s against R11's 6,156 s,
and no repair persistence owner exists. R11's six correctness/ownership closures
are untouched by this diff and re-exercised by the 29 pre-existing real-owner
tests, all green.

## 7. Restart-cost evidence: R12's realization is preserved, with rationale

Workplan §5 item 6 requires a fresh post-`N_max` resumed run **only if** the
restored resource scope changes a target-order stage width or admission regime
used by the R12 restart evidence. It does not:

- COVREF width is 28 before and after, with zero backpressure;
- MVIDX's admission ceiling is arithmetically identical (§2.3);
- REPAIR2's width is `min(selector_workers, cpu_threads_budget)`, and
  `cpu_threads_budget` equals the `workers` value already passed, so the cap is
  a no-op;
- MVQUAL's width is unchanged and its queue records no memory backpressure.

The R12 restart realization (replay 6,610 s → 100 s, no longer dominant, no
repair-side persistence) therefore remains applicable, and §4.3 independently
shows the repair replay reproduces exactly at a *different* execution width,
which is the property the restart evidence depends on. Per the workplan's
explicit second branch, it is preserved rather than re-run.

## 8. Executed checks

Python for this repository is `/home/samjin/miniconda3/envs/mace/bin/python`.

```text
# real-owner suite including the four R13 falsification tests
python -m pytest tests/test_mlff_target_order_real_owner.py -q -p no:randomly

# representative current-scale LTA campaign, disposable scratch workspace;
# the stakeholder's live campaign directory is never entered
cp ~/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/campaign.toml <ws>/
python -m mdstats.training_data.campaign_cli --config <ws>/campaign.toml doctor
                                             prepare                    # infers manifest
                                             prepare --approve-manifest
# the measured fresh build, under the external /proc sampler
python rss_probe.py <out> python -m mdstats.training_data.campaign_cli \
                             --config <ws>/campaign.toml prepare
# the reuse path on the published workspace, same command again

# affected regression (61 files)
python -m pytest $(cat affected_tests.txt) -q -p no:randomly -n 16
```

| Check | Result |
|---|---|
| `tests/test_mlff_target_order_real_owner.py` | **33 passed** |
| representative fresh LTA `prepare` | **exit 0**, build `b8d75b6a1857`, 2,014.97 s |
| COVREF in-stage peak RSS under a finite budget | **measured**, §4.2 |
| representative reuse `prepare` | **exit 0**, 333.4 s, `status=reused; build=b8d75b6a1857` |
| affected regression, 61 files | **1,439 passed / 4 failed**; 3 pre-existing, 1 test-only flake repaired (§8.2) |

### 8.1 Reuse run

A second `prepare` on the published workspace, same command, same restored
resource routing:

```text
[target-order] status=reused; build=b8d75b6a1857
exit_code=0; wall_seconds=333.45   (R12 reuse: 5 m 36 s)
```

The target-order authority stage completed in **2 s**. The immutable
create-or-verify publication is authenticated and reused rather than rebuilt,
the structural provider is not re-entered, and no target-order stage re-executes
under the finite budget. R11 closures 2, 3 and 6 are re-confirmed at scale.

### 8.2 Affected regression

61 files at `-n 16`: **1,439 passed, 4 failed, 1,961.99 s**.

Three failures are **pre-existing and unrelated**, reproduced at the basis with
every R13 change stashed (`git stash push -- mdstats tests`):

```text
tests/test_mlff_mace_compatibility.py::test_campaign_evaluate_outer_scope_catches_setup_warnings
tests/test_mlff_mace_compatibility.py::test_campaign_main_owns_one_warning_domain_and_normalizes_output
tests/test_mlff_mace_compatibility.py::test_campaign_warning_domain_merges_worker_thread_local_scopes
-> 3 failed, 15 passed   (at basis, changes stashed)
```

They fail on `mdstats-mlff-campaign: error: the following arguments are required:
command` — the campaign console script is not installed in this environment —
and lie entirely outside the changed surface.

The fourth was **my own new test, and the test was wrong**, not the product:

```text
tests/test_mlff_target_order_real_owner.py::test_real_owner_r13_finite_budget_does_not_change_any_scientific_identity
E  assert 'stage=REPAIR2; status=start; width=2' == 'stage=REPAIR2; status=start; width=1'
```

It compared the MVSEL2 preflight's **measured** width across two separate
preparations. Under a loaded 16-way machine the sub-10 ms meter chose 2 in one
and 1 in the other — the same nondeterminism §4.3 documents at representative
scale (16 in R11/R12, 28 in R13). Asserting reproducibility of a wall-clock
measurement is not a falsifiable claim about this change.

The assertion was replaced with the deterministic claim it should always have
made: within each run, REPAIR2's execution width must equal the width its own
preflight published, i.e. a non-constraining RAM budget never caps REPAIR2 below
the selector's decision. Every scientific-identity assertion in that test
(build identity, preparation/selection/repair/qualification digests, swap count,
complete order, serial-vs-parallel COVREF digest) was already passing and is
unchanged.

After the repair, `tests/test_mlff_target_order_real_owner.py` was re-run three
times at `-n 16` under deliberate contention: **33 passed** each time.

**New-failure delta against the basis: zero.**

Affected-surface derivation: every test file referencing `target_order`,
`prepare_target_training_order`, `build_target_coverage_reference`, `REPAIR2`,
`MVQUAL`, `MVIDX`, `MVSEL2`, the `real_target_order` substitute marker,
`campaign_target_size_runtime`, `work_queue`/`DeterministicWorkQueue`,
`StageResourceScope`/`build_stage_resource_scope`, `_performance_resources`,
`detect_system_resources`, `training_data.resources`, `prepared_generation`, or
the `prepare` command. This is a superset of R12's 55-file set. The excluded
remainder is the density/geometry/topology subsystem, which shares no changed
module.

## 9. Documentation, dependency, history and residual risk

**Documentation.** None required. The D3 manual delegates worker counts, queue
timing and native-thread realization to D4 and declares them execution-only; R13
changes no documented interface, schema, CLI surface or scientific product. The
`60_execution_performance.md` constraint quoted in §2.2 is *better* satisfied
after the change than it would have been without the override removal.

**Dependencies.** None added or changed.

**History.** No migration, revert or recovery; no published artifact schema or
build identity moved (`b8d75b6a1857` is unchanged).

**Residual risk, reported not acted on.**

1. **FEAS1/NEIGHBOR1 is the one target-order stage the restored route does not
   reach.** `preparation.py` calls `build_target_coverage_geometry(...,
   global_workers=workers)` with no `resource_scope`, so FEAS1 still runs on CPU
   accounting alone. Workplan §2.3 item 6 enumerates COVREF/MVIDX/MVQUAL
   deliberately and does not include FEAS1, and FEAS1's inverted
   `manage_resource_scope` polarity means passing it a scope would *also* turn on
   a native-thread quarantine it does not have today — a behavior change with its
   own qualification cost. This is offered to the resource owner as a separate
   bounded question, not silently widened here.
2. **`manage_resource_scope` is an incoherent parameter with one remaining
   user.** After R13 it is read at exactly one call site (FEAS1). Consolidating
   it away belongs with item 1.
3. **MVIDX publishes no queue telemetry**, so its admission behavior at
   representative scale is established by the §2.3 arithmetic and the
   fixture-scale runtime assertion rather than by a production snapshot line.
4. **The MVSEL2 native preflight decision is not stable across runs** (16 in R11
   and R12, 28 here) and 28 is mildly slower on this substrate. Outside R13's
   scope; recorded in §4.3.
5. **No CI status is attached to this candidate.** Everything above is
   implementation-recorded local execution, to be assessed as evidence rather
   than treated as CI-attested fact.

## 10. Reconciliation against the Revision 13 re-review gate

| Gate | Status |
|---|---|
| 1. every R11 correctness/ownership closure intact | **yes** — untouched by the diff, 29 pre-existing real-owner tests green |
| 2. R12 REPAIR2 exactness and performance closure intact | **yes** — repair plan bitwise reproduced at a different width; REPAIR2 ~111 s vs R11's 6,156 s |
| 3. campaign RAM budget actually routed through the existing `resource_scope` | **yes** — §2.1, §4.2; `ram_budget=41431436492` where R12 logged `None` |
| 4. COVREF in-stage peak and incremental peak measured, not inferred | **yes** — §4.2, 10 Hz `/proc` sampling plus an unchanged `VmHWM` across the stage |
| 5. finite-budget execution inside the governing envelope | **yes** — incremental peak 0.44 % of budget; zero backpressure; no violation to correct |
| 6. build, repair/order and MVQUAL identities exact under the restored routing | **yes** — `b8d75b6a1857`, 49 swaps, Phase A at 361, MVQUAL {512…16384} |
| 7. HAS in the canonical Protocol 6.3 schema against the unchanged basis | **yes** — §5 |
| 8. affected final regression applicable, no new failures | §8.2 |
| 9. no competing scientific/persistence/currentness/cleanup/resource/compatibility owner | **yes** — §6 structural negative evidence |
