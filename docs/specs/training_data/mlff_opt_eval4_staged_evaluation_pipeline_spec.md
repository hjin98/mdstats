# OPT-EVAL4 staged checkpoint-evaluation pipeline

Status: implemented in mdstats 0.20.101a0.

## 1. Purpose

Checkpoint evaluation previously scheduled one heterogeneous job per candidate.
A single worker performed checkpoint authentication/materialization, monitor parsing,
accelerator graph conversion, MACE inference, prediction persistence, metric reduction,
SQLite commit, run selection, and selected-model publication.  Independent checkpoint
jobs could run concurrently, but CPU-only work before and after inference occupied the
same admitted slot.  When model forwards were short relative to preparation/finalization,
GPU slots could therefore be idle even though later checkpoints were ready to prepare.

OPT-EVAL4 changes execution topology only.  It does not change model weights, monitor
membership/order, prediction-cache identity, graph-cache identity, metric definitions,
checkpoint admissibility, selection policy, replay lineage, or verification policy.

## 2. Required pipeline

Campaign evaluation shall execute uncached checkpoints through three bounded stages:

```text
CPU preparation
  - authenticate checkpoint/monitor bytes
  - load/cache target and replay monitors
  - materialize immutable evaluation views
  - resolve persisted candidate predictions
  - resolve/import DATA6 or replay-pseudolabel foundation predictions
        |
        v
bounded prepared queue
        |
        v
accelerator stage
  - materialize the candidate checkpoint model only when candidate inference is needed
  - serialize CuEq/OEq/PyTorch-FX conversions through the existing process-wide guard
  - construct or acquire a worker-private calculator/provider under the compatibility rules below
  - execute target/replay model forwards under adaptive CPU/GPU admission
        |
        v
bounded finalization queue
        |
        v
CPU finalization
  - persist newly generated candidate predictions
  - reduce immutable prediction arrays against cached evaluation views
  - construct the checkpoint evaluation record
        |
        v
parent-thread durable commit / run selection / selected-model publication
```

Preparation for later checkpoints and finalization for completed checkpoints should be
able to overlap inference.  A completed accelerator slot shall be refilled before
parent-side run selection/model publication callbacks execute.

TARGET-SIZE-V5 exact-boundary EVAL2 is a required consumer of this pipeline.  Its parent
constructs immutable authority-rich endpoint descriptors, may bind one authenticated
shared target context for compatible endpoints, and validates every returned endpoint
against the expected run/size/seed/checkpoint/target-role/prediction/metric authority before
writing `CampaignStore`.  Worker-supplied keys are not publication authority.  Shared
target atoms/evaluation views are reserved once in the stage RAM ledger and excluded from
per-task incremental prepared-state accounting.  Cached and fresh results traverse the
same parent validation path before the deterministic terminal-population barrier/reducer.

## 3. Compatibility API

`evaluate_mace_checkpoint()` remains public and synchronous.  It shall execute the same
three scientific stages sequentially so existing callers do not need to know about the
campaign pipeline.

The runtime stage APIs are:

- `prepare_mace_checkpoint_evaluation(...)`
- `run_prepared_mace_checkpoint_inference(...)`
- `finalize_prepared_mace_checkpoint_evaluation(...)`

`PreparedCheckpointEvaluation` and `CheckpointEvaluationPredictionBundle` are runtime
objects only and are not campaign-state serialization formats.

## 4. Cache-only behavior

If CPU preparation proves that all required candidate/foundation predictions are already
durable or can be imported from authenticated DATA6/pseudolabel sources, the checkpoint
shall bypass accelerator admission entirely.  Metric recomputation after a reference-label
or reporting-policy change must therefore remain possible after the raw checkpoint has
been pruned, as established by OPT-EVAL2.

## 5. Accelerator ownership and safety

A MACE calculator/provider is private to one active inference owner.  No calculator may
be passed to a sibling worker or to CPU finalization.  A serial TARGET-SIZE-V5 accelerator
lane may retain one provider shell across endpoint checkpoints only when authenticated
checkpoint loading proves exact model-class/state-key/state-shape/state-dtype compatibility
and the provider has been explicitly qualified for weight replacement.  Foundation-model,
CuEq/OEq, compiled, or otherwise unqualified providers rebuild instead.  Incompatible
shells rebuild; corruption or authority mismatch fails closed.  Weight-dependent adapter
or calculator state is invalidated when weights change.

Candidate checkpoint materialization is part of the admitted accelerator stage rather
than the unmetered CPU preparation stage.  This is required because direct restoration of
CuEq/OEq checkpoints can execute accelerator/FX conversion, and the legacy qualified
fallback may invoke a device-bound MACE reconstruction process.

MACE CuEq/OEq/hybrid FX rewriting remains serialized by the existing process-wide
conversion lock.  Independent model inference may overlap on separately admitted CUDA
streams after conversion.

## 6. Resource admission

The existing `AdaptiveInferenceConcurrency` policy remains authoritative for the
accelerator stage:

- CUDA starts with one admitted inference job while calibration is incomplete;
- the fixed post-calibration per-job GPU/VRAM estimate determines target concurrency;
- live GPU-utilization spikes do not demote the calibrated target;
- the hard live VRAM guard remains active;
- CPU-only inference remains bounded by CPU/RAM policy.

OPT-EVAL4 changes the meaning of evaluation calibration boundaries: CPU monitor/cache
preparation and CPU metric/persistence finalization are outside CUDA calibration.  Model
materialization, accelerator conversion, transfer, and actual MACE inference remain
inside it.  Verification retains its existing admission behavior.

## 7. Pipeline backpressure

CPU stages must not run arbitrarily far ahead of inference.  The campaign exposes:

- `parallel_evaluation_prepare_jobs` (`0` = auto),
- `parallel_evaluation_finalize_jobs` (`0` = auto),
- `evaluation_pipeline_buffer_jobs` (`0` = auto).

The auto policy uses a small CPU-stage worker count and a bounded prepared/finalization
backlog.  Accelerator admission pauses when the finalization backlog reaches its bound so
fresh prediction arrays cannot accumulate without limit.

## 8. Failure and restart semantics

A failure in any stage stops admission of new work.  Active evaluation work polls the
stage cancellation signal at safe preparation, model-materialization, inference-wave, and
finalization boundaries.  Owned legacy reconstruction subprocesses are terminated on
cancellation/timeout with attempt-local cleanup.  The command fails without marking
incomplete checkpoints as evaluated.

Durable prediction artifacts and evaluation records keep their existing OPT-EVAL2/3
identities.  No new scientific-record schema is required merely for pipeline scheduling.
TARGET-SIZE-V5 additionally persists deterministic typed terminal EVAL2 scientific-failure
evidence so a sibling infrastructure failure does not force already authenticated terminal
work to repeat.  A restart revalidates success/failure authority before reuse; conflicting
success and failure evidence fails closed.

## 9. Progress and observability

Campaign output shall distinguish pipeline stages.  At minimum it should expose:

- CPU preparation;
- accelerator model conversion/inference;
- CPU prediction persistence/metric finalization;
- active/ready/finalization-backlog counts in periodic scheduler reporting.

Per-checkpoint completion should report total wall time and the accumulated prepare,
inference, and finalization times.  Target-size execution additionally exposes low-overhead
phase timing sufficient to distinguish target preparation, model/provider materialization,
static-inference calibration, production inference, graph/prediction reuse, and
finalization/persistence.  These timings are diagnostics and do not enter any scientific
digest or acceptance decision.

Static-inference calibration profiles may cross checkpoint-weight identity only when a
weight-independent runtime-architecture digest and exact authenticated geometry identities
are available and the device/dtype/head/acceleration/precision/hardware/workload contract
matches.  Otherwise profile compatibility remains checkpoint-exact.  Reused profiles are
still live-clamped to current resource evidence and retain OOM learning/backoff behavior.

## 10. Acceptance tests

OPT-EVAL4 is complete only if all of the following hold:

1. staged scientific execution reproduces synchronous `evaluate_mace_checkpoint()`
   metrics and provenance;
2. an OPT-EVAL2 cache-only restart bypasses the inference executor and works after raw
   checkpoint deletion;
3. with one inference slot, preparation of checkpoint N+1 overlaps inference of N;
4. with one inference slot, CPU finalization of N overlaps inference of N+1;
5. completion callbacks remain parent-thread operations so campaign SQLite/publication
   semantics are unchanged;
6. CuEq/OEq conversion guards and checkpoint materialization tests remain green;
7. true-label replay and persistent prediction-cache regressions remain green;
8. the existing adaptive inference controller tests remain green;
9. exact source-patch and isolated-wheel smoke tests pass before release;
10. TARGET-SIZE-V5 uses the real staged scheduler and parent authority validator, with
    successful durable publication, typed scientific-failure restart reuse, and reducer
    completion exercised through a real `CampaignStore`;
11. stage-shared target atoms/views are RAM-accounted once while per-task accounting charges
    only incremental prepared state;
12. compatible target-size checkpoint weights may reuse one private provider shell only
    when hot-swapped forward output matches a freshly loaded compatible model, and
    incompatible shells rebuild;
13. cross-checkpoint calibration-profile and geometry-graph reuse is exercised through the
    assembled target-size owner without weakening checkpoint scientific identity.
