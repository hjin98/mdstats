---
kind: implementation-evidence
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 12
protocol_version: 6.3.0
status: complete
branch: design/mlff-pi-train-fps-diversity-restoration
accepted_project_base: e72090e21cec5311ce87745b03603f8783cd15a7
reviewed_r11_implementation_commit: dd96ede2b24540977ee0bb280764907ea258e356
reviewed_r11_evidence_candidate: 029b274474c1adc3b4ea0021a82abf6a5de8c27d
r12_basis_commit: e935c18c
r12_implementation_commit: 9c41f44b
verdict_requested: independent-d4-re-review
highest_affected_domain: D4
upstream_authority_state: D1_D2_D3_ACCEPTED_UNCHANGED
---

# Revision 12 D4 current-envelope closure evidence

Governing contract: `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_12.md`.
Scope is the four bounded D4 surfaces B12-1 … B12-4. No scoped D1/D2/D3 authority
was reopened and no accepted R11 correctness/ownership repair was modified.

## 1. Changed files

| File | R12 change |
|---|---|
| `mdstats/training_data/target_order/repair.py` | B12-1: the candidate-at-a-time Python-thread proposal evaluator is replaced by `_StateBatch`, exact batched evaluation over the existing MVIDX forward CSR through the already-qualified native pairwise row primitive; `DeterministicWorkQueue`/`threading` removed from the stage |
| `mdstats/training_data/target_order/preparation.py` | B12-1: REPAIR2 now takes the metered native preflight width (one execution-width authority for MVSEL2 and REPAIR2); B12-3: process RSS / `MemAvailable` recorded on entry to and release from `TargetCoverageReference` |
| `mdstats/training_data/target_order/coverage_reference.py` | B12-3: the COVREF stage reports its `StageResourceScope` summary and the deterministic queue's admission accounting (peak accounted bytes, budget, backpressure events, lanes, block size) |
| `mdstats/training_data/resources.py` | B12-3: `process_rss_bytes()` at the resource owner, so budget and RSS are recorded as the distinct quantities they are |
| `tests/test_mlff_target_order_real_owner.py` | B12-1 falsification: bitwise batch/scalar-oracle equivalence, fail-closed invariant, per-state invalidation, contender-filter property test, structural absence of the worker queue, width invariance extended to 16 |

Net product change: +403 / -102 lines across four product files; `repair.py` is
+346 / -99 with the thread queue, thread-local scratch and per-candidate task
plumbing deleted.

## 2. B12-1 — REPAIR2 execution serialization

### 2.1 Located mechanism

The R11 profile localized the defect to `_best_proposal`/`_proposal`. Reading the
owner shows the cost is a product of three Python-level per-candidate loops that
each call one NumPy row primitive per (candidate, family) pair:

- `_build_frontier`: `family_coverage_gain` over every available candidate, then
  `total_coverage_gain` (78 families) over the bottleneck-tied set — which, once
  coverage saturates, is *every* available candidate;
- `_proposal`: `_representative_after_removal` and `_diversity_after_removal`
  over the balance-filtered frontier, once per shortlist entry (up to 64);
- the shell scan: `removal_metrics` over every active-shell member per iteration.

At `|P_train| = 33,984`, `N_max = 16,384`, 78 families and ~65,300 MVIDX edges per
candidate, the dominant term is 64 removals x ~17,000 frontier candidates x 78
families of Python-dispatched NumPy calls per repair iteration. Python threads
cannot help: the work is NumPy-call-dispatch bound, i.e. GIL bound.

### 2.2 Repair: rewire onto the existing qualified row primitive

`repair.py` now evaluates every candidate-indexed quantity through `_StateBatch`,
which is created per unchanged repair state and discarded by any accepted swap.
Nothing new was added below the owner:

- full-row FP64 sums go to `native.score_family_candidate_batch`, the primitive
  MVSEL2 Phase A/B already use, whose qualification certifies it bitwise equal to
  `np.sum(terms[row], dtype=np.float64)`; at width 1 the identical NumPy row
  reduction is used, preserving the proven serial path as the baseline;
- removal dependence is expressed as a **per-witness patch** of the state's base
  term vector: a witness shared with the removed candidate has denominator `n`
  instead of `n + 1`. The divisions use the same FP64 operands the scalar owner
  divides, so the patched row sums are bitwise equal, and the shortlist needs one
  batched sweep per removal instead of one Python task per candidate;
- masked reductions (uncovered coverage mass, uniquely covered mass) keep the
  canonical **compacted** association. The batch only establishes, by an exact
  integer indicator count, which rows own no masked witness; those rows are
  exactly `0.0`, and every remaining row is delegated to the scalar owner. This is
  why no dense candidate-by-witness matrix and no second incidence representation
  were introduced, and why the association-sensitive coverage gains are still the
  D2 reference reduction;
- `DeterministicWorkQueue`, `threading.local` and the per-candidate task
  submission are **deleted**, not wrapped. Reduction over the shortlist is a plain
  canonical-order loop, so completion order, worker count and task boundaries no
  longer exist as things that could perturb the reduction.

`prepare` now passes the metered native preflight width to REPAIR2 instead of the
raw CPU budget, so MVSEL2 and REPAIR2 share one execution-width authority and a
host without the qualified native extension runs both serially instead of
spawning Python threads.

Frozen and unchanged: the `_build_frontier` hard-gain / canonical-bottleneck /
bottleneck-coverage / total-coverage filter chain; the `_proposal` correlation
balance, post-removal representative gain, sparse diversity, UID, family
non-regression and `strictly_better(J_before, J_after)` sequence; the objective;
the policy tolerances and per-shell limits; the `(representative_loss,
removed_rank, removed_UID, replacement_UID)` reduction rule. The scalar formula
owners `removal_metrics`, `_representative_after_removal` and
`_diversity_after_removal` are retained as the D2 oracle the equivalence tests
compare against.

### 2.3 D2 section 9 conformance, clause by clause

`docs/methods/mlff_target_training_order_numerical_algorithmic_method.md` §9
specifies REPAIR2 semantically and imposes **no** execution, parallelism or
evaluation-schedule requirement, which is why this repair is entirely inside
D4's delegated space and raises no D1/D2 challenge:

| D2 §9 clause | R12 status |
|---|---|
| 9.1 removable iff `unique_mass(c) <= 1e-14` **and** removal raises no canonical hard-obligation deficit | unchanged; `unique_mass` is now computed in batch and proved bitwise equal to `removal_metrics`, the hard-safety test is the same scalar owner, and the `and` short-circuit still means hard safety is only asked for zero-unique members |
| 9.1 order removable by (representative loss asc, removed correlation-unit selected count desc, removed UID asc), keep at most 64 | unchanged sort key and `removal_shortlist_limit = 64`; `shortlist_max = 64` is observed at every saturated shell in §7.2 |
| 9.2 "evaluate replacement against **immutable pre-swap state**" | preserved, and strengthened: the removal-dependent term patch is written into a derived term vector and restored in a `finally` block, so the forward state itself is never mutated during evaluation |
| 9.2 steps 1-8 (hard gain → first canonical bottleneck family → bottleneck new coverage → total new coverage → min hypothetical correlation-unit count → max representative gain after removal → max sparse diversity after removal → min replacement UID) | the same eight filters in the same order; only how each candidate's number is produced changed |
| 9.3 `J`, the `1e-14` tolerance on components 2-4, exact integer balance, strict improvement, `C_m(after) + 1e-14 >= C_m(before)` | unchanged code |
| 9.3 objective-equivalent tie-break `(representative_loss, removed_rank, removed_UID, replacement_UID)` | unchanged `_preferred`; now reached by a canonical-order loop instead of a queue drain, so the reduction has no completion-order input at all |
| 9.4 at most 2 passes, 32 accepted swaps, shortlist 64, replacement inherits removed rank, future occurrence displaced, earlier prefixes immutable | unchanged; the frozen policy still rejects any other value |
| 9.5 after any accepted swap every prefix-dependent lazy/frontier/marginal/cache state is stale | this is exactly why `_StateBatch` is per unchanged state and is dropped on every accepted swap; the §2.3 invalidation test makes the requirement load-bearing rather than assumed |

### 2.4 Exactness falsification

`tests/test_mlff_target_order_real_owner.py`:

| Test | Claim |
|---|---|
| `…repair2_batch_quantities_are_bitwise_equal_to_the_scalar_oracle[1,2,4,16]` | every batched quantity is **bit-identical** to the scalar D2 formula owner, over bounded adversarial states with the hard deficit pending, satisfied and with a saturated frontier, at removal shortlists of size 1 and of the frozen limit 64, for every family and every available candidate |
| `…repair2_batch_fails_closed_on_an_illegal_removal[1,2]` | the zero-unique removal invariant still raises where the scalar oracle raises, in both execution paths |
| `…repair2_batch_state_arrays_are_invalidated_by_an_accepted_swap` | after a real accepted swap a fresh batch matches the oracle on the new state, and the pre-swap batch would have answered differently — so per-state construction is load-bearing |
| `…repair2_best_relative_mask_matches_the_selector_filter` | hypothesis property test: the array contender filter is the MVSEL2 `filter_best_relative` rule, not a new one |
| `…repair2_has_no_python_worker_queue_left_in_the_proposal_path` | structural/negative: no `DeterministicWorkQueue`, no `threading`, no thread pool remains in the stage, and exactly one execution primitive call site |
| `…repair2_zero_new_coverage_swap_strictly_improves_representative_utility` (R11, extended) | identical repair plan dictionaries at widths 1, 2, 4 and 16 |
| `…repair_swaps_and_reconstructs_cold_continuation` (R11) | serial and parallel plans identical; post-repair cold reconstruction matches |

### 2.5 Paired bounded-scale profile (mechanism proof)

A bounded real-owner REPAIR2 problem (14 reference families, 458,752 MVIDX edges,
256 frames, configured ladder 32/64/128, `workers=16`) run against the R11
baseline in a detached `HEAD` worktree and against this tree, same fixture, same
process count, sequentially on an otherwise idle 32-thread host:

| | R11 baseline (`e935c18c`) | R12 | ratio |
|---|---|---|---|
| REPAIR2 wall | **242.51 s** | **4.41 s** | **55.0x faster** |
| REPAIR2 CPU seconds | 360.36 | 75.83 | |
| effective cores in the stage | **1.49** | **17.2** | |
| accepted swaps | 64 | 64 | equal |
| repair-plan `content_digest` | `9acc1227c9c6116ca951c3733b6a6ecdc66c33c9ef34dfa4a437352b27e980fd` | **identical** | |

The baseline's 1.49 effective cores reproduces the R11 finding of "~1.6 CPU
cores" exactly, and the repaired stage saturates the authorized width at 17.2
cores. The repair-plan content digest — which binds the complete repair trace,
every swap objective pair and the repaired prefix — is byte-identical, so the
speedup carries no scientific change. This is the mechanism proof; the current-
scale paired result is in §7.

## 3. B12-4 — Protocol 6.3 PEM / Historical Applicability Set

Resolved memory basis:

- accepted project base at review start: `e72090e21cec5311ce87745b03603f8783cd15a7` (`main`);
- `PROJECT-ENGINEERING-MEMORY.md` carried at that base: sha256
  `7b0d342b3be3b2773bc2012fde74af2ddb89bcd6106885aae2ace3d217ce5945`,
  `coverage_state: PARTIAL`, `reconciled_through:
  4eabe2ae9783c7ff92f3a1093c37502a01380812`, `accepted_base.project_state:
  4eabe2ae…`, high-impact unresolved notices: **none** (NT-001 retired);
- the branch tip carries the **byte-identical** PEM (`git diff e72090e2..HEAD --
  PROJECT-ENGINEERING-MEMORY.md` is empty), so there is **no validated
  same-branch candidate overlay** for this restoration. The literal
  `candidate_overlay` string in that file names
  `fix/mlff-p5-cv-no-admissible-outcome-repair` and is not an overlay for this
  candidate;
- every applicable lesson is `EVIDENCE_ONLY` binding, i.e. a replaceable design
  prior, not authority.

Session-local Historical Applicability Set:

| ID | Bounded lesson | Disposition | Rationale |
|---|---|---|---|
| `SP-001` | Repair at the owning layer by reduction and consolidation | **applied** | The bottleneck was removed inside the existing REPAIR2 owner by deleting the thread queue and reusing the MVSEL2 native row primitive; no repair backend module, execution router, alternate algorithm or compatibility mode was created, and `prepare` lost a second execution-width authority. |
| `SP-002` | Fail closed on authenticated identity/durable-state disagreement | **applied** | The zero-unique-removal and multiplicity-underflow invariants are preserved in the batched path and proved to raise exactly where the scalar oracle raises; no artifact, build or checkpoint authentication boundary was relaxed. |
| `SP-003` | Immutable durable boundaries enable exact restart and reuse | **applied** | It is the reason B12-2 is answered by making the recomputation cheap rather than by inventing a repair-side durable cache; the existing MVSEL2/suffix checkpoint boundaries are unchanged. |
| `SP-004` | Qualify through real owners and real regimes | **applied** | Closure rests on the real-owner suite plus a representative current-scale LTA `prepare` on the stakeholder's own campaign configuration, not on the bounded fixtures alone; the bounded fixtures carry the bitwise oracle equivalence. |
| `FF-002` | Continuation authority admitted before an authenticated restart boundary | **applied** | No new pre-adoption continuation state was introduced. The one new cache (`_StateBatch`) is in-process, per unchanged repair state, discarded by any accepted swap, never serialized and never consulted across a restart; the invalidation test makes that load-bearing. |
| `FF-003` | Duplicated destructive-storage authority | **applied** | R12 adds no storage, cleanup or GC path; the fail-closed create-or-verify publication boundary and single-flight fence are untouched. |
| `FF-005` | Downstream command reconstructs preparation-owned science | **applied** | R12 changes only preparation-internal execution, so the R11 no-rebuild routing still holds; re-confirmed by the representative manual-selection probe in §7.5. |
| `FF-001` | Realized-model identity drift across duplicated MACE construction | **rejected** | No MACE model construction, accelerator realization or checkpoint-authentication path is in R12's surface. |
| `FF-004` | Resource decisions inferred outside the process/residency owner | **review-required** | B12-3 is exactly a resource-accounting question. R12 does not move any admission decision out of the resource owner — it makes the existing owner *report* its scope and queue accounting — but the budget-versus-RSS disposition in §6 is the evidence that settles it. |

No PEM mutation is proposed. A single bounded performance observation on one
stage does not meet Protocol 6.3's learning threshold for a new recurring family,
and no accepted-repair chronology for a recurrence occurrence exists here.

## 4. R11 closure preservation and negative (no-new-owner) evidence

### 4.1 The six R11 repairs remain intact

R12 touches no R11 repair surface. Each closure keeps its own real-owner test,
and all of them pass on the final R12 tree:

| R11 closure | Owner untouched by R12 | Test |
|---|---|---|
| 1. REPAIR2-v2 semantics + v1 identity invalidation | frontier/objective/admission sequence unchanged; `REPAIR2_VERSION` unchanged | `…repair2_zero_new_coverage_swap_strictly_improves_representative_utility`, `…repair2_v1_build_identity_is_not_current` |
| 2. Immutable create-or-verify publication, fail closed | `artifact_store.py` unchanged | `…corrupt_published_target_order_artifacts_are_not_replaced`, `…write_failure_leaves_no_partial_accepted_artifact` |
| 3. Per-build single-flight `prepare` | fence logic in `preparation.py` unchanged | `…same_build_prepare_is_single_flight`, `…interrupted_fence_holder_releases_and_successor_resumes` |
| 4. Frozen universal structural-family completeness, fail closed | the `required_structural_feature_families` check in `coverage_reference.py` is unchanged (R12 only adds a progress report after it) | `…required_structural_families_are_complete_or_fail_closed`, `…molecular_phase_plan_cannot_thin_target_order_families` |
| 5. Scoped/general D1/D2 documentation reconciliation | no documentation authority changed by R12 | static/documentation closure batch (§8) |
| 6. Prepared-generation currentness + downstream no-rebuild | `campaign_target_size_*` untouched | `…assembled_campaign_uses_prepared_order_through_production`, representative manual-selection probe (§7.5) |

`git diff --stat` over the product tree is confined to four files (§1); none of
`artifact_store.py`, `state.py`, `qualification.py`, `obligations.py`,
`feasibility.py`, `sparse_index.py`, `selector.py`, `kernels.py`, `native.py`,
`engine.py` or any `campaign_*` module is modified.

### 4.2 No new competing owner was introduced

| Prohibited addition | Status | Evidence |
|---|---|---|
| separate REPAIR2 backend module / execution router | absent | `repair.py` gained no module; `_StateBatch` is private to the stage and holds no policy |
| fallback selector, alternate suffix, REPAIR2 compatibility mode | absent | no version/mode branch exists; `mvsel2_execution_backend` is the same width contract MVSEL2 already uses, and width 1 is the proven serial path |
| alternate repair algorithm | absent | the filter/objective/admission sequence is byte-for-byte the D2 sequence; bitwise oracle equivalence in §2.4 |
| second currentness/checkpoint store, repair-side durable cache | absent | `_StateBatch` is in-process, per unchanged repair state, never serialized, discarded on any accepted swap; no file, no digest, no schema |
| duplicate sparse representation / dense candidate-by-witness matrix | absent | every quantity reads the existing MVIDX forward CSR (`candidate_offsets`/`candidate_witnesses`); the only matrices are `(candidates x families)` reduction scratch, never `(candidates x witnesses)` |
| second memory manager, new cleanup/GC owner | absent | B12-3 adds reporting only; admission stays with `StageResourceScope`/`DeterministicWorkQueue` |
| new Python thread pool | **removed, not added** | `…has_no_python_worker_queue_left_in_the_proposal_path` |
| second execution-width authority | **removed** | `prepare` now feeds the metered native preflight width to both MVSEL2 and REPAIR2 |

The D3 manual already delegates this space to D4: `45_target_training_order.md`
§"Execution-only worker widths, queue timing, cache residence … do not enter
scientific identity", "The mature deterministic bounded queue and qualified
native candidate-row backend **may** be restored beneath that owner", and "D4 may
choose … worker implementation". `60_execution_performance.md` states "native
candidate-row acceleration is an execution primitive only". No documentation
authority therefore required amendment for B12-1; the deterministic queue remains
in service at COVREF, NEIGHBOR1 and MVIDX, where the work is not GIL bound.

The D3 acceptance clause "if the native/OpenMP backend is retained,
installed-package native/reference exact-equivalence qualification is part of D4
acceptance" is satisfied without change, because REPAIR2 reuses the *same*
primitive the existing `test_installed_package_native_equivalence` qualifies
(`score_family_candidate_batch`) rather than introducing a second kernel.

## 5. Exact commands

Python for this repository is `/home/samjin/miniconda3/envs/mace/bin/python`.

```text
# bounded scalar / batched / native exact-equivalence + real owner suite
python -m pytest tests/test_mlff_target_order_real_owner.py -q -p no:randomly

# the R12 equivalence subset alone
python -m pytest tests/test_mlff_target_order_real_owner.py -q -p no:randomly \
  -k "batch or best_relative or worker_queue or zero_new_coverage"

# paired bounded REPAIR2 profile (baseline worktree versus this tree)
git worktree add --detach <scratch>/base HEAD           # e935c18c
cp mdstats/_mvsel2_native.cpython-311-x86_64-linux-gnu.so <scratch>/base/mdstats/
PROBE_REPO=$PWD          python <scratch>/midscale.py <out> 256 16 32,64,128
PROBE_REPO=<scratch>/base PYTHONPATH=<scratch>/base \
                         python <scratch>/base/midscale.py <out> 256 16 32,64,128

# representative current-scale campaign (disposable scratch workspace; the
# stakeholder's live campaign directory is never entered)
cp ~/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/campaign.toml <ws>/
cd <ws> && mdstats-mlff-campaign --config <ws>/campaign.toml doctor
                                 prepare                      # infers the manifest
                                 prepare --approve-manifest
/usr/bin/time -v                 prepare                      # the measured build

# affected regression (55 files, the target-order/prepare/COVREF/resources surface)
python -m pytest $(cat <scratch>/affected_tests.txt) -q -p no:randomly -n 16
```

## 6. B12-3 — COVREF-PAR1 RAM-budget accounting: resolved, no violation

Measured on the R12 representative run, same campaign configuration and same
machine class as R11 (32 threads / 28-thread CPU budget, 62 GiB RAM):

| Required quantity (workplan §4) | Measured |
|---|---|
| 1. process RSS immediately before `TargetCoverageReference` | **5,354,549,248 B (4.99 GiB)**; `MemAvailable` 52,372,664,320 B (48.8 GiB) |
| 2. stage incremental RSS above that baseline | **−209,240,064 B (−200 MiB)** — process RSS *fell* to 5,145,309,184 B (4.79 GiB) once the stage released its execution state |
| 3. its `StageResourceScope.ram_budget_bytes` | **`unbounded` (None)** — see the finding below |
| 4. deterministic-queue peak accounted in-flight/completed/reserved memory; backpressure | **138,112,128 B (131.7 MiB)** peak accounted over **20,234** committed tasks; `memory_backpressure_events=0`; `queue_backpressure_events=0`; `memory_budget_bytes=None` |
| 5. worker width / block size actually selected | `queue_lanes=28`, `queue_max_busy=28`, `python_workers=28`, `tree_workers=1`, `blas_threads=1`, `radius_block_size=1024`, `query_workers=1`; scope CPU `28/28 budget`, estimated nested threads 28 ≤ budget |
| 6. process RSS after the stage releases temporary state | **5,145,309,184 B (4.79 GiB)** |

### 6.1 Disposition — close without code change

The R11 observation compared two quantities that do not govern each other:

- **36.4 GiB was whole-process peak RSS** for an entire `prepare`, accumulated
  across P1/P2 substrate, the structural provider, NEIGHBOR1/MVIDX and the
  selector — not the coverage-reference stage's demand;
- **34.5 GiB was the campaign-level resolved resource plan line**, derived from
  *currently available* RAM at plan time. It is not a fixed product constraint:
  the R12 run on the same configuration and machine printed
  `RAM 53.1 GiB available / 42.5 GiB budget`, because more RAM happened to be
  free. Both lines are the same fixed fraction of available RAM
  (34.5/43.1 = 42.5/53.1 = 0.80), which makes the arithmetic explicit: the
  "budget" tracks unrelated host state at plan time, so it is not a constraint a
  process peak can be said to "violate".

The comparable quantities are now measured, and every one of them is far inside
any plausible bound: the stage's incremental process demand is **negative**
(−200 MiB, because releasing the structural catalog exceeds the stage's own
working set), its deterministic queue accounted a peak of **132 MiB**, and it
recorded **zero** memory- and queue-backpressure events. No admission contract
was exceeded. Per workplan §4 first branch, **B12-3 closes without a code
change**; COVREF parallel width and block admission are not reduced, and no
second memory manager was added. The serial/parallel digest-equivalence proof is
untouched (`build_target_coverage_reference` semantics unchanged; R11's
owner-level scope-equivalence test still passes).

### 6.2 Residual finding, reported not acted on

Item 3 is the honest surprise: the COVREF stage scope reports
`ram_budget=unbounded` and its queue `memory_budget_bytes=None`. The cause is
wiring, not this stage —
`campaign_target_size_runtime.py:518` calls `prepare_target_training_order(...,
workers=resources.cpu_threads_budget)` and passes **no `resource_scope`**, so
`resource_scope is None` for every target-order stage and the RAM budget the
campaign does resolve (42.5 GiB here, 34.5 GiB in R11's run) never reaches them.
Target-order stages are therefore admitted on CPU accounting alone.

This strengthens rather than weakens the §6.1 disposition — there was no stage
RAM contract for the 36.4 GiB peak to violate — but it is a real gap and is
recorded as residual risk rather than buried:

- it is **not** a demonstrated defect: observed peaks (31.5 / 36.4 GiB) stayed
  inside machine capacity on the representative substrate, and COVREF's own
  accounted demand is ~132 MiB;
- workplan §4 conditions any code change on a **proven** over-budget behavior,
  and none is proven;
- threading a RAM budget through would begin reducing COVREF/NEIGHBOR1/MVIDX
  width and block admission, i.e. it would change the very current envelope this
  revision is measuring, and needs its own resource-owner design decision and
  qualification. Inventing it here would create a larger problem than it solves.

This is why `FF-004` is recorded `review-required` in §3 rather than `applied`.
It is offered to the resource owner / D3 as a separate bounded question.

## 7. B12-1 representative current-scale acceptance (run A, fresh)

### 7.1 Fixture identity — paired with R11, not anecdotal

Same substrate as R11 §7.1: a byte-identical copy of the stakeholder's
`05_mace_training/LTA/mpa0/FP32/campaign.toml` (sha256
`059ab8fe5e856fb1a676111219ed399379d8fde12e757e9e37267e53879ca5f3`), run in a
disposable scratch workspace so the live campaign was never entered. The
inferred manifest was accepted unchanged. The build came out on the same
substrate R11 measured, confirmed stage by stage:

| Identity | R11 | R12 run A |
|---|---|---|
| retained frames / exact `\|P_train\|` | 37,633 / 33,984 | 37,633 / **33,984** |
| reference families / structural | 78 / 8 | **78** / 8 |
| canonical obligations | 739 | **739** |
| NEIGHBOR1 witnesses | 2,367,624 | **2,367,624** |
| FEAS1 terminal state / `k_min` | `cross_support_fragile` / 90 | **`cross_support_fragile` / 90** |
| configured ladder | 128 … 16,384 | 128 … 16,384 |
| machine | 32 threads / 28-thread budget, 62 GiB | same |

### 7.2 Stage wall clock — paired

| Stage | R11 run A | R12 run A | |
|---|---|---|---|
| `TargetCoverageReference` | 818 s serial / 58 s PAR1 | 58 s (COVREF-PAR1) | |
| shared FEAS1/NEIGHBOR1 | 516 s + 19 s | ~150 s + FEAS1 | |
| MVIDX adoption/inversion | 72 s | ~70 s | |
| native preflight | 55 s → 3.28x, width 16 | 3.29x, **width 16**, `scaling=pass` | identical decision |
| MVSEL2 configured prefix to `N_max` | 233 s | **234.94 s** | unchanged |
| **REPAIR2 (8 configured shells)** | **6,156 s** | **99 s** | **62x faster** |
| MVSEL2 suffix 16,384 → 33,984 | 164 s | **162.26 s** | unchanged |
| MVQUAL | 20 s | ~20 s | |
| **whole `prepare`** | **2 h 25 m 53 s** | **32 m 00.95 s** | **4.6x faster** |
| peak RSS | 31.5 GiB | 32.1 GiB (33,676,584 KiB) | comparable |
| file-system outputs | 110,908,256 blocks | 110,909,128 blocks | comparable |
| target-order store | 16.9 GiB | 20 GiB workspace total | |
| exit status | 0 | **0** | |

Per-shell REPAIR2, with the **same swap count at every rung**:

| shell | R11 | R12 | proposals | `frontier_max` | `shortlist_max` | swaps |
|---|---|---|---|---|---|---|
| 128 / 256 / 512 | ~0 s | 2 s | 0 | 0 | 0 | 0 / 0 / 0 |
| 1,024 | 60 s | ~20 s | 2,048 | **18** | 64 | 32 |
| 2,048 | 1,351 s | **~11 s** | 320 | **31,936** | 64 | 3 |
| 4,096 | 1,858 s | **~17 s** | 448 | **29,888** | 64 | 5 |
| 8,192 | 1,264 s | **~18 s** | 320 | **25,792** | 64 | 3 |
| 16,384 | 1,620 s | **~21 s** | 512 | **17,600** | 64 | 6 |
| **total** | **6,156 s** | **99 s** | 3,648 | | | **49** |

The `frontier_max` column is the direct measurement of the diagnosed mechanism:
from shell 2,048 on, coverage is saturated and the D2-correct replacement
frontier is essentially *every* remaining candidate (31,936 of 33,984). R11
walked that frontier one candidate at a time in Python, 64 times per repair
iteration; R12 sweeps it in the native batch. Where the frontier is small
(`frontier_max = 18` at shell 1,024) the batch costs nothing extra — that shell
also got faster, 60 s → 20 s — so the repair has no regressed regime.

### 7.3 Scientific products are byte-identical at current scale

| Product identity | R11 | R12 run A |
|---|---|---|
| **published build identity** | `b8d75b6a1857e85c` | **`b8d75b6a1857…`** |
| REPAIR2 swaps per rung | 49 = (0,0,0,32,3,5,3,6) | **49 = (0,0,0,32,3,5,3,6)** |
| Phase A → Phase B transition rank | 361 | **361** |
| MVSEL2 prefix evaluated edges | 2.62e11 | **262,006,362,336** |
| suffix evaluated edges | 3.22e11 | **321,905,841,476** |
| MVQUAL qualified sizes | {512, 1024, 2048, 4096, 8192, 16384} | **{512, 1024, 2048, 4096, 8192, 16384}** |
| selector fallback count | 0 | **0** |

The build content digest binds the complete order, the repair plan, the
qualification plan and every scientific parent. Reproducing
`b8d75b6a1857` therefore establishes at full current scale — not merely on
bounded fixtures — that the optimized execution changed **no** repair trace, no
final order, no qualification result and no scientific digest, which is exactly
the §2.5 acceptance condition.

### 7.4 Cause-based closure of B12-1

The workplan sets no time SLA and asks whether the known GIL-bound
candidate-at-a-time serialization is still the material reason REPAIR2 dominates.
It is not, on all three of the criteria that were used to identify it:

1. **the mechanism is gone, not faster** — there is no Python task per candidate
   and no work queue in the stage at all (structural test in §2.4);
2. **execution width is now real** — the stage runs at the metered qualified
   native width 16; the bounded paired profile measures 17.2 effective cores
   against the baseline's 1.49, which reproduced R11's "~1.6 cores" exactly;
3. **REPAIR2 no longer dominates** — 74% of target-order wall at R11, and
   99 s of a ~1,750 s target-order total here, i.e. about **3%**. The largest
   target-order stages are now the two MVSEL2 passes (235 s + 162 s), which are
   unchanged accepted work.

### 7.5 Reuse and downstream routing (R11 closures 2, 3, 6 re-confirmed at scale)

| Probe | R11 | R12 |
|---|---|---|
| authenticated reuse `prepare` in the same workspace | 5 m 38 s, peak RSS 8.9 GiB, `status=reused; build=b8d75b6a` | **5 m 36.41 s**, peak RSS **8.93 GiB** (9,366,784 KiB), `status=reused; build=b8d75b6a1857`, `rc=0` |
| fresh-process manual `select-target-size 4096` | 1.53 s, 627 MiB, `rc=0`, zero target-order modules, zero mapped files | **1.52 s**, **628 MiB** (643,072 KiB), `rc=0`, `target_order_modules_loaded=none`, `mapped_target_order_files=0` |

The reuse path repeated no selector, geometry, MVIDX or repair work, and the
downstream manual selection produced `T_provisional = pi_train[:4096]` identity
`ca3470c7b6f7…` without importing `target_order.selector`, `sparse_index`,
`engine`, `repair`, `state`, `preparation`, `coverage_reference` or
`_mvsel2_native`, and without mapping a single target-order file. `FF-005` is
confirmed absent at current scale, and R11 closure 6 holds.

## 8. B12-2 — post-`N_max` restart cost: retain the current topology

Per workplan §3.2 the ordering was obeyed: B12-1 was implemented first, then the
same post-`N_max` interruption/resume qualification was repeated. Run B is a
second fresh representative campaign in its own workspace, `SIGKILL`ed during the
MVSEL2 suffix past `N_max`, then resumed.

| | R11 run B interrupted | R11 run B resumed | R12 run B interrupted | R12 run B resumed |
|---|---|---|---|---|
| kill point | suffix rank 18,432 | — | suffix rank **20,480** | — |
| `prepare` wall | 2 h 04 m 24 s | 2 h 00 m 21 s | **27 m 29.34 s** | **11 m 16.62 s** |
| peak RSS | 36.4 GiB | 20.1 GiB | **31.96 GiB** (33,507,544 KiB) | **20.03 GiB** (20,994,216 KiB) |
| MVSEL2 to `N_max` | 245 s, width 16 | 12 s restored | ~235 s, width 16 | **restored from checkpoint** (`resume=16384`) |
| **REPAIR2** | 5,894 s, 49 swaps | **6,610 s replayed** | **97 s, 49 swaps** | **100 s replayed** |
| suffix | killed at 18,432 | 197 s (18,432 → 33,984) | killed at 20,480 | resumed at **20,480** → 33,984 |
| preflight-selected width | 16 | 4 | 16 | **16** |
| file-system outputs on resume | — | 3.89 M blocks | — | **3,870,800 blocks** |
| published build identity | — | `b8d75b6a1857` | — | **`b8d75b6a1857`** |
| exit status | — | 0 | — | **0** |

### 8.1 Exactness across the restart

The resumed run published the **same** build identity `b8d75b6a1857` as R12 run A,
as R12 run B's own killed attempt would have, and as R11 — across a different
workspace, a kill 4,096 ranks beyond `N_max`, and a checkpoint restore. Swap count
49, per-rung swaps (0,0,0,32,3,5,3,6), `phase_a_completed_at=361` and MVQUAL
qualified sizes `{512 … 16384}` are identical in both R12 runs. The suffix resumed
from the authenticated checkpoint at exactly the kill rank 20,480, and the resume
re-published nothing (3.87 M blocks against 110.9 M for a fresh build). Workplan
re-review condition 4 — "fresh and post-`N_max` resumed execution produce identical
repair/order/MVQUAL identities" — holds.

### 8.2 Disposition: replay is no longer a material restart cost

| | R11 | R12 |
|---|---|---|
| REPAIR2 replay wall on resume | 6,610 s | **100 s** (**66x less**) |
| share of the resumed `prepare` | 6,610 / 7,221 s = **91.5%** | 100 / 676 s = **14.8%** |
| dominant resumed cost | **REPAIR2 replay** | P1/P2 authority replay + the suffix remainder |

The workplan's first branch therefore applies: *"If the optimized exact REPAIR2
replay is no longer a material restart cost, retain the simpler current topology
and record that result."*

**Disposition: retain the current topology. No new durable repair state is
introduced and no D3 Challenge is raised.** The reasoning is stated so a reviewer
can disagree with it on the numbers:

- 100 s is no longer the dominant restart cost, nor even the largest target-order
  item on resume; it is comparable to one MVSEL2 suffix continuation;
- a reusable authenticated repair result would add a new pre-adoption persistence
  boundary with its own identity, schema, corruption, staleness and cleanup
  surface. `SP-003` and `FF-002` both say that boundary must be *authenticated
  and immutable* to be safe, and `FF-002` records real restart defects from
  treating pre-boundary state as authority. Buying back ~100 s with that surface
  would create more problems than it solves;
- workplan §3.2 also requires that any such D3 proposal "first show why existing
  build/checkpoint identities cannot be rewired more simply". After B12-1 there is
  nothing to show: the expensive computation is no longer expensive.

Re-review condition 5 is therefore satisfied by the first of its two branches.

## 9. Executed checks

| Check | Result |
|---|---|
| `tests/test_mlff_target_order_real_owner.py`, complete, final tree | **29 passed** (58.9 s) — 20 R11 tests plus 9 new R12 tests |
| R12 batch/scalar-oracle bitwise equivalence, widths 1/2/4/16 | **4 passed** |
| R12 fail-closed illegal-removal parity, widths 1/2 | **2 passed** |
| R12 per-state invalidation (stale batch is distinguishable) | **1 passed** |
| R12 contender-filter hypothesis property test (200 examples) | **1 passed** |
| R12 structural absence of the Python worker queue | **1 passed** |
| REPAIR2 plan equality across widths 1/2/4/**16** | **1 passed** (R11 test, width coverage extended) |
| installed-package native/reference exact equivalence (wheel build + isolated install) | **1 passed**, unchanged and already covering the primitive REPAIR2 now reuses |
| serial/parallel/COVREF-PAR1 `TargetCoverageReference` digest equality | **1 passed** (`serial == parallel == blocked` content digests) |
| documentation / CLI-spec closure batch | **12 passed, 0 failed** |
| **affected regression, 55 files, `-n 16`** | **1,264 passed, 4 failed** (30 m 52 s) |
| baseline attribution of those 4 at `e935c18c` | **identical 4 node IDs — zero new failures, zero new errors** |
| representative fresh `prepare` (run A) | `rc=0`, build `b8d75b6a1857` |
| representative kill/resume `prepare` (run B) | `rc=0`, build `b8d75b6a1857`, killed at suffix rank 20,480 |
| authenticated reuse `prepare` | `rc=0`, `status=reused` |
| downstream manual `select-target-size 4096`, fresh process | `rc=0`, zero target-order imports, zero mapped target-order files |
| `ruff` on changed files | no new warning class; `repair.py` 8 pre-existing, `resources.py` + `coverage_reference.py` 19 pre-existing, all unchanged from `HEAD` |
| `git diff --check -- . ':!*.pdf'` | clean |

### 9.1 The four affected-regression failures are pre-existing

| Node ID | Cause | Baseline |
|---|---|---|
| `test_density_tiled_fft.py::test_fft_kernel_spectrum_is_reused_for_equal_tile_shapes` | FFT kernel-spectrum cache reuse count (`assert 2 == 1`) | fails at `e935c18c` |
| `test_mlff_mace_compatibility.py::test_campaign_evaluate_outer_scope_catches_setup_warnings` | campaign warning-domain CLI argument handling (`error: the following arguments are required: command`) | fails at `e935c18c` |
| `test_mlff_mace_compatibility.py::test_campaign_main_owns_one_warning_domain_and_normalizes_output` | same | fails at `e935c18c` |
| `test_mlff_mace_compatibility.py::test_campaign_warning_domain_merges_worker_thread_local_scopes` | same | fails at `e935c18c` |

None touches a changed owner: R12 modifies only REPAIR2 execution, two progress
reports, one REPAIR2 worker argument and one additive resource helper. They are
preserved as explicit baseline-equal, out-of-scope evidence rather than hidden
with skips or xfails, per workplan §6.

The ten failures R11 recorded in its wider 98-file batch (eight
`*_specification.py` suites asserting the retired revision-109 architecture
material, two `test_topology_catalog.py` tests needing an untracked
`Na_LTA_relaxed.POSCAR`) lie in owners outside this revision's affected surface —
replay/perf specification and topology-catalog owners, none of which R12 touches —
so they do not become affected and are not re-litigated here. The repository is
therefore still not globally green, and this record does not claim it is.

### 9.2 Affected-surface derivation

The 55-file set is the target-order / `prepare` / COVREF / resources surface:
every test file referencing `target_order`, `prepare_target_training_order`,
`build_target_coverage_reference`, `REPAIR2`, the `real_target_order` substitute
marker or the `prepare` command, unioned with every file importing the changed
modules' own consumers (`resources`, `work_queue`, `coverage_reference`).
`resources.py`'s change is purely additive — a new `process_rss_bytes()` function
with no existing call-site behavior altered — so its broad import base does not
widen the behavioral surface; only new callers can be affected, and the only new
caller is `preparation.py`.

## 10. Documentation, dependency and history impact

- **Documentation:** none required. The D3 manual already delegates worker
  implementation, queue timing and cache residence to D4 and declares them
  outside scientific identity; `60_execution_performance.md` already states that
  native candidate-row acceleration is an execution primitive only. D2 §9
  imposes no execution schedule (§2.3). No D1/D2/D3 text became false.
- **Dependencies:** none added or removed. REPAIR2 reuses the existing
  `_mvsel2_native` extension and its existing installed-package qualification
  route; no second kernel and no new third-party package.
- **Project memory:** no PEM mutation proposed (§3). The session-local HAS is
  recorded in this file against accepted base `e72090e2`.
- **Known duplication left in place (out of scope):** three private
  process-RSS helpers already exist (`model_features._current_process_rss_bytes`,
  `_campaign_cli_core._process_rss_mib`, and an inline one in
  `structural_selection.py`). R12 adds the owner-level `resources.process_rss_bytes()`
  and uses it, but does not rewire those three, because converting unrelated
  owners is not in this revision's surface and would carry its own regression
  risk. Recorded as a consolidation candidate.

## 11. Residual risk

1. **Target-order stages carry no RAM admission contract** (§6.2). Not a proven
   defect and explicitly out of B12-3's remit, but real, and offered to the
   resource owner / D3 as a separate bounded question.
2. **Small-frontier regimes gain an indicator pass.** Where coverage is not
   saturated the batch pays one extra exact integer pass per family before
   delegating to the scalar owner. Measured to be non-harmful — shell 1,024 went
   60 s → ~20 s with `frontier_max = 18` — so no regime regressed, but a
   hypothetical problem with a permanently tiny frontier would see the overhead
   without the benefit.
3. **The repository is not globally green** (§9.1); four pre-existing failures in
   the affected set and ten in R11's wider set remain open against other owners.
4. **Production-scale GPU qualification remains deferred** to the final release
   package on the stakeholder machine, as the workplan directs. The target-order
   path is CPU-only.
5. **No CI attestation.** All results here are local. As workplan §6 notes for
   R11, implementation-recorded local results remain evidence to be independently
   assessed, not CI-attested facts.

## 12. Reconciliation against the Revision 12 re-review gate

This is the implementer's reconciliation, not an acceptance claim. Workplan §8
requires a fresh independent assembled-candidate review, and until that review
passes the workplan stays **ACTIVE / D4 NO-PASS** and must not be closed or
archived.

| §8 condition | Status | Where |
|---|---|---|
| 1. every R11 correctness/ownership closure remains intact | satisfied | §4.1 — owners untouched, each closure's own test green |
| 2. REPAIR2 exact semantics and scientific products unchanged | satisfied | §2.3 clause-by-clause D2 §9 conformance; §2.4 bitwise oracle equivalence; §7.3 identical build identity at current scale |
| 3. the measured GIL-bound candidate-at-a-time bottleneck removed at its D4 owner, with paired current-scale evidence that the mechanism no longer materially dominates | satisfied | §2.2 removal; §2.5 paired 1.49 → 17.2 effective cores; §7.2 6,156 s → 99 s; §7.4 74% → ~3% of target-order wall |
| 4. fresh and post-`N_max` resumed execution produce identical repair/order/MVQUAL identities | satisfied | §8.1 — `b8d75b6a1857` from both, 49 swaps, rank 361, same MVQUAL sizes |
| 5. restart replay no longer material **or** escalated to D3 before new durable repair state | satisfied by the first branch | §8.2 — 6,610 s → 100 s, 91.5% → 14.8%; no persistence added, no Challenge raised |
| 6. the COVREF-PAR1 RAM-budget question quantitatively resolved, real over-budget behavior corrected via the existing resource owner | satisfied; no violation found, so no correction applied | §6 — stage incremental RSS −200 MiB, queue peak 132 MiB, zero backpressure; residual gap reported in §6.2 |
| 7. session-local PEM/HAS disposition recorded against the exact accepted/base project state | satisfied | §3 — base `e72090e2`, PEM sha256 `7b0d342b…`, no same-branch overlay, 9 dispositions |
| 8. real-owner, native/reference, OOC/FD, publication/currentness, documentation/static, downstream no-rebuild and affected regression evidence applicable and green or preserved-with-reason | satisfied | §9 — 29 real-owner, installed-package native equivalence, FD/OOC and publication tests green; 12 documentation/static; downstream no-rebuild; 1,264 passed with 4 baseline-equal failures preserved with reason |
| 9. no new competing scientific, persistence, currentness, cleanup or compatibility owner exists | satisfied | §4.2 — and two owners were *removed* (the Python worker queue, the second execution-width authority) |

**No Serious Challenge is raised.** The accepted D1/D2/D3 authority was found
coherent and adequate throughout: D2 §9 specifies REPAIR2 semantically and
imposes no execution schedule, and the D3 manual already delegates worker
implementation and queue timing to D4. The defect was entirely in the D4
concretization, which is where it was repaired.
