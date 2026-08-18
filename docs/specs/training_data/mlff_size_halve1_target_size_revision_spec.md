---
title: "MLFF SIZE-HALVE1 Target-Size Successive-Fidelity Correction Specification"
subtitle: "Hard coverage admission plus exact 3/10/30 learning screens"
author: "mdstats project"
date: "2026-08-15"
geometry: margin=0.8in
toc: true
toc-depth: 3
numbersections: true
fontsize: 10pt
header-includes:
  - |-
    \usepackage{booktabs}
  - |-
    \usepackage{longtable}
  - |-
    \usepackage{microtype}
  - |-
    \usepackage{xurl}
---

# Status

**Gate:** `SIZE-HALVE1`  
**Release:** `mdstats 0.20.182a0`  
**Authority class:** C  
**Supersedes:** the generated-campaign target-size semantics of PERF-P2 / TARGET-DATA2C v2  
**Next qualification gate:** `SIZE-FIDELITY1`  
**Next performance gate:** `PERF-P2R`

`SIZE-HALVE1` corrects the target-size decision rule. Coverage is now a hard
admissibility condition only. It cannot decide that a smaller data set is
sufficient for learning merely because that set spans the frozen geometric and
statistical support envelope.

All coverage-qualified target sizes therefore enter a common low-fidelity
training screen. Candidate reduction is driven by observed target learning at
3, 10, and 30 epochs on one uninterrupted training schedule.

# Scientific correction

The prior generated-campaign rule retained the four smallest coverage-qualified
rungs. That rule answered two different questions with one statistic:

1. whether a subset covers the required target/reference support; and
2. whether the subset samples that support densely enough to train an accurate
   interatomic potential.

Only the first question is a coverage question. A small nested subset may pass
range, local-radius, extent, and mandatory-stratum tests while still undersampling
important high-density or rapidly varying regions of the potential-energy
surface. Larger subsets must remain eligible until learning evidence shows that
they provide no material benefit.

The corrected funnel is

$$
7
\xrightarrow{\text{hard coverage}}
N_{\mathrm{eligible}}
\xrightarrow{3\ \mathrm{epochs}}
\le 4
\xrightarrow{10\ \mathrm{epochs}}
2
\xrightarrow{30\ \mathrm{epochs}}
1.
$$

The staged resource-allocation pattern is related to successive-halving methods
for allocating increasing budgets to stronger candidates [1,2]. mdstats does
not adopt those papers' objective or stochastic assumptions as scientific
authority; it uses the general multi-fidelity resource-allocation idea while
retaining project-specific deterministic target metrics, hard gates, exact
continuation, and provenance rules.

# TARGET-DATA2C v3: complete hard-coverage ladder

TARGET-DATA2C v3 materializes every globally materializable configured rung.
The generated default remains

$$
K \in \{128,256,512,1024,2048,4096,8192\}.
$$

For each rung and each target label domain, the existing frozen TARGET-DATA2B
coverage, extent, and mandatory-support predicates are evaluated exactly. A
common rung is hard-coverage-qualified only if every target label domain passes.

If fewer than three common rungs qualify, the target-size study fails with
`TargetDataCoverageError`. If three or more qualify, **all** qualifying rungs are
retained for training. No coverage-equivalent rung is discarded because of its
size.

TARGET-DATA2C v1 and v2 remain readable only where explicit historical tooling
supports them. They are stale as current generated-campaign authority.

## Monotonicity use

Nested hard-coverage monotonicity may be used to reduce redundant computation,
but never to truncate candidate membership. In particular, once an exact
predicate is proven monotone over the configured nested ladder, an implementation
may reuse state or certify later pass status from a stronger earlier result only
when that inference is part of a versioned, tested contract. It must still
materialize every candidate membership required by the 3-epoch learning screen.

# TARGET-DATA2D v2: 3/10/30 successive-fidelity authority

## Frozen policy

The generated default is

```toml
[target_data.size_convergence]
min_coverage_qualifiers = 3
coarse_training_epochs = 3
max_coarse_training_candidates = 4
coarse_target_monitor_configurations = 256
short_training_epochs = 10
max_short_training_candidates = 2
final_training_epochs = 30
coarse_practical_equivalence_mev_per_a = 1.0
practical_equivalence_mev_per_a = 1.0
screening_optimizer_seed = 1
```

The coarse practical-equivalence width is separately versioned and may be
calibrated from real 3/10/30 trajectories. If omitted, it inherits the ordinary
practical-equivalence width.

## Stage A: hard coverage admission

Stage A performs no training and no economic ranking. Its output is exactly the
ordered set of all hard-coverage-qualified rungs.

```text
if number_qualifying < min_coverage_qualifiers:
    fail
else:
    retain every qualifying rung
```

For the default policy, three is the minimum defensible convergence study.
Three or four qualifying rungs all proceed to epoch 3. More than four proceed to
epoch 3 and are reduced there.

## Stage B0: epoch-3 coarse learning screen

Every Stage-A candidate starts from the same frozen foundation checkpoint, the
same screening optimizer seed, and the same nominal 30-epoch TRAIN2 schedule.
The run pauses after exactly three completed epochs. It is not a three-epoch
training schedule.

The primary ranking quantity is the unrounded fixed target-only force selection
score

$$
S_{\mathrm{target}}^{(3)}.
$$

The coarse evaluation role is a common, leakage-safe, deterministic target
monitor shared by every candidate. The generated default contains at most 256
configurations, balanced across development correlation blocks with systematic
interior sampling. Replay inference is not purchased at this stage and has no
ranking or gating authority.

If more than four candidates are eligible, epoch-3 target evidence reduces them
to four. If at most four are eligible, all numerically valid candidates remain.

## Stage B1: epoch-10 refinement

The epoch-3 survivors resume from their exact saved states and continue to
exactly ten completed epochs on the original 30-epoch schedule. The target-size
reducer selects two finalists using common target-side evidence.

TRUE_DFT replay may be recorded diagnostically at epoch 10, but contributes zero
positive ranking credit and cannot reject a numerically valid candidate at this
stage.

## Stage C: epoch-30 qualification

The two finalists resume from their exact epoch-10 states and complete the same
30-epoch schedule. Final selection applies target metrics, hard replay retention,
and required physical qualification. Within final practical equivalence, the
smaller target size remains preferred.

If the largest available ladder rung remains materially better than its smaller
finalist, the study is `nonconverged_at_ladder_boundary`; it must not silently
report the bounded maximum as converged.

# Exact continuation identity

A candidate is initialized once. Promotion changes only the execution pause
limit. It must not restart optimization, renormalize the schedule, or rebuild a
scientifically different training run.

The authenticated chain is

$$
(\theta_0,o_0,r_0)
\rightarrow
(\theta_3,o_3,r_3)
\rightarrow
(\theta_{10},o_{10},r_{10})
\rightarrow
(\theta_{30},o_{30},r_{30}),
$$

where $\theta$ is model/checkpoint state, $o$ is optimizer/scheduler state, and
$r$ is Python/NumPy/Torch CPU/CUDA RNG state. Each continuation evidence record
must authenticate its immediate checkpoint, optimizer, and RNG parent.

Training evidence also records optimizer updates and structures presented. Epoch
count alone is not treated as a complete compute-exposure description because
larger data sets contain more batches.

# Warm-up safety

The coarse screen must occur strictly after the frozen LR warm-up interval. For
nominal final horizon $E_f$ and coarse endpoint $E_c$, generated campaign
preflight requires

$$
\frac{E_c}{E_f} > p_{\mathrm{warmup,end}}.
$$

The current defaults give $3/30=0.10>0.05$. A configuration that moves the
coarse endpoint into or onto warm-up fails preflight rather than comparing
candidates before the intended adaptation regime begins.

# Early-stage practical equivalence and boundary preservation

A smaller-size tie preference is appropriate at final qualification, but it is
unsafe during early halving. If the largest tested boundary is eliminated merely
because it is practically tied at epoch 3 or 10, the workflow can no longer
detect that the bounded ladder has not converged at epoch 30.

For epoch 3 and epoch 10, candidates are first partitioned by the applicable
practical-equivalence width. The largest coverage-qualified boundary candidate
is moved to the front **within its own equivalence band**. It is not protected
against a materially better earlier band.

Therefore:

- a boundary rung that is only practically tied is preserved when capacity
  permits;
- a boundary rung that is materially worse can still be eliminated; and
- the final epoch-30 decision returns to the smaller-size preference within the
  final equivalence band.

This safeguard preserves the ability to diagnose bounded-ladder nonconvergence
without granting the largest rung unconditional survival.

# EVAL2 role correction

The full target-size evaluation role remains the development complement of the
largest candidate training rung. The epoch-3 role is a fixed subset of that same
complement, so it is disjoint from every nested training candidate and identical
across candidate sizes.

The coarse role is part of scientific policy, not an execution-only knob. Its
maximum configuration count therefore enters the versioned TARGET-DATA2D policy
and digest.

# TARGET-DATA2E v2

The production-corpus decision now persists the complete size-study ancestry:

1. every hard-coverage-qualified Stage-A rung;
2. epoch-3 evidence for all Stage-A candidates;
3. the at-most-four epoch-3 survivors;
4. epoch-10 evidence for those survivors;
5. exactly two epoch-10 finalists;
6. epoch-30 evidence for both finalists; and
7. the selected target size or explicit bounded-ladder failure.

Legacy DATA2E authority is stale when it cannot prove this ancestry.

# PERF-P2 status

PERF-P2's `0.20.181a0` lazy-ladder benchmark remains valid as a historical
measurement of the algorithm that was implemented. Its **generated-campaign
scientific premise is superseded**: four coverage qualifiers no longer imply
that larger candidate sizes are irrelevant.

Consequently, the historical 80.23% forced-early-stop timing reduction is not a
current campaign performance claim. Current TARGET-DATA2C v3 retains the full
hard-coverage ladder required by the learning screen.

# SIZE-FIDELITY1: coarse-screen fidelity calibration

The 3-epoch screen is a scientific multi-fidelity approximation. Its production
use therefore requires empirical evidence that the low-fidelity ordering does
not systematically discard candidates that become superior later. This is a
qualification problem, not a performance optimization.

On an authorizing MACE runtime and foundation checkpoint, `SIZE-FIDELITY1` must
run a bounded exhaustive calibration in which every hard-coverage-qualified
rung is continued to 30 epochs for multiple frozen screening seeds. The same
saved trajectories are rescored at epochs 3 and 10. At minimum the gate must
measure:

- epoch-3 top-four recall of the eventual 30-epoch winner and finalists;
- epoch-10 top-two recall of the eventual 30-epoch winner;
- sensitivity of those decisions to screening seed;
- rank agreement as a diagnostic, not a substitute for survivor recall;
- the smallest coarse-monitor size whose decisions agree with the full
  development role up to the frozen practical-equivalence rule; and
- whether the largest ladder boundary is ever eliminated early and later proves
  materially superior.

The generated 256-configuration monitor and 1.0 meV/A coarse equivalence width
are therefore **provisional defaults pending this calibration**. If the
calibration fails, the remedy is to increase the coarse endpoint, monitor size,
or equivalence width through a new versioned policy; it is not permissible to
relax the hard coverage gate or hide a missed final winner.

`SIZE-HALVE1` is structurally qualified in this release, but production
scientific certification of the 3-epoch approximation remains pending
`SIZE-FIDELITY1` because the supplied environment has no authorizing MACE/GPU
runtime.

# Revised performance roadmap: PERF-P2R

PERF-P2R optimizes the corrected funnel without reintroducing scientific
truncation.

## Full-ladder coverage reuse

- Reuse the exact PERF-P1 FPS workspace through the largest materializable rung.
- Load/scale each coverage family once and carry exact incremental nearest-
  selected and extent state across all nested rungs.
- Use monotonicity only to avoid redundant computation when exact equivalence is
  proven; never omit a training candidate because of it.

## Nested training-data reuse

- Materialize the largest authorized nested target corpus once where safe.
- Represent smaller nested corpora by authenticated prefix/index manifests rather
  than duplicated frame bytes.
- Share immutable graph, neighbor, descriptor, and preprocessing caches keyed by
  frame identity and scientific preprocessing policy.
- Cache location, mmap path, worker count, and chunk size remain execution-only.

## Coarse-screen execution

- Evaluate the fixed 256-configuration target-only monitor once per candidate at
  epoch 3.
- Do not execute replay inference, checkpoint-rescue search, bootstrap model
  selection, or physical verification at the coarse stage.
- Reuse the same prepared monitor graph/cache across all candidate sizes.
- Fuse boundary evaluation with the training process when exact standalone EVAL2 prediction/evidence bytes are reproduced, avoiding an unnecessary checkpoint reload.

## Pause/resume reuse

- Initialize each candidate once.
- Persist exact epoch-3 and epoch-10 boundary checkpoint, optimizer, scheduler,
  and RNG authority.
- Continue survivors in place when the runtime permits; do not retrain the first
  3 or 10 epochs.
- After immutable elimination evidence is frozen, transient non-survivor
  checkpoints may be garbage-collected under the storage-retention policy.
- Continuation qualification must cover DataLoader/sampler ordering state or prove deterministic epoch-boundary reconstruction; Python/NumPy/Torch RNG identity alone is insufficient if worker-local stochastic state can affect training order or transforms.
- Full restart checkpoints should be mandatory at scientific boundaries (3/10/30); any extra recovery-checkpoint cadence is execution-only and may be reduced only when failure recovery remains bounded.

## Stage-aware scheduling

- Never launch a later stage for an eliminated candidate.
- On one GPU, use deterministic work-conserving dispatch and avoid cache thrash.
- On multiple GPUs, parallelize peers only within a declared resource budget;
  do not oversubscribe CPU preprocessing, storage, or GPU memory.
- Record host/GPU class so performance comparisons are matched rather than
  conflating heterogeneous hardware.

## Whole-funnel benchmark authority

PERF-P2R begins only after SIZE-FIDELITY1 validates the coarse-screen fidelity. Its qualification must measure the complete 3/10/30 funnel, not only local
microkernels. Required telemetry includes:

- total wall and process time;
- per-stage and per-candidate wall time;
- optimizer updates and structures presented;
- GPU utilization and peak VRAM;
- CPU/RSS and preprocessing time;
- disk/network I/O and checkpoint bytes;
- pause/resume overhead; and
- uninterrupted-versus-resumed endpoint scientific identity.

The cloud correction environment has no authorizing MACE/GPU runtime, so this
release does not fabricate those measurements.

# Exposure model

For hard-coverage qualifiers $A$, epoch-3 survivors $S_4$, and epoch-10
finalists $S_2$, target structure-epoch exposure is approximately

$$
W = 3\sum_{i\in A}K_i
  + 7\sum_{i\in S_4}K_i
  + 20\sum_{i\in S_2}K_i.
$$

Training every admissible candidate to 30 epochs would cost

$$
W_{\mathrm{full}} = 30\sum_{i\in A}K_i.
$$

For all seven default rungs, $\sum K_i=16256$. If the four largest and then the
two largest survive, the exposure proxy is $W=402048$ versus
$W_{\mathrm{full}}=487680$, a 17.56% reduction. If the four smallest and then
the two smallest survive, $W=69888$, an 85.67% reduction.

This is an exposure proxy, not a wall-time prediction. Replay, batching, graph
construction, GPU occupancy, I/O, and candidate-dependent throughput can change
actual runtime materially.

# Acceptance criteria

SIZE-HALVE1 is accepted only if all of the following hold:

1. TARGET-DATA2C v3 materializes every globally materializable configured rung.
2. Every hard-coverage-qualified rung enters Stage B0.
3. Fewer than three hard-coverage qualifiers fails closed.
4. Epoch-3 evidence is target-only and uses one fixed common coarse role.
5. Epoch-3 promotion retains at most four candidates and preserves the largest
   boundary only within practical equivalence.
6. Epoch-10 promotion retains exactly two candidates with the same boundary
   safeguard and zero replay ranking credit.
7. Epoch-30 selection uses final hard replay/physical qualification and smaller-
   size preference within final practical equivalence.
8. 3->10 and 10->30 continuation proves checkpoint, optimizer/scheduler, RNG,
   foundation, training-policy, schedule, and evaluation-role ancestry.
9. The epoch-3 endpoint is strictly past LR warm-up.
10. TARGET-DATA2E persists the complete corrected ancestry.
11. Historical TARGET-DATA2C v1/v2 and TARGET-DATA2D v1 authority cannot be
    mistaken for current generated-campaign authority.
12. Current manuals, examples, tests, and dependency graph no longer advertise
    coverage-based four-smallest truncation as valid generated-campaign science.

# References

[1] Kevin Jamieson and Ameet Talwalkar. "Non-stochastic Best Arm Identification
and Hyperparameter Optimization." *Proceedings of the 19th International
Conference on Artificial Intelligence and Statistics*, PMLR 51:240-248, 2016.
<https://proceedings.mlr.press/v51/jamieson16.html>

[2] Lisha Li, Kevin Jamieson, Giulia DeSalvo, Afshin Rostamizadeh, and Ameet
Talwalkar. "Hyperband: A Novel Bandit-Based Approach to Hyperparameter
Optimization." *Journal of Machine Learning Research* 18(185):1-52, 2018.
<https://www.jmlr.org/papers/v18/16-558.html>
