# Historical narrative: TRAIN2 resource-admission evolution

**Status:** non-normative history  
**Current authority:** `docs/arch_manuals/mlff_training_data/60_execution_performance.md`, `mdstats/training_data/training_parallel.py`, and the current specifications indexed by `docs/specs/training_data/README.md`

## Why this history is retained

An earlier accepted execution rule stated that CUDA training *always* begins
with one job and adapts upward. That rule was not a scientific or numerical
claim; it was an architectural assumption that one configured training job is
always feasible on a usable CUDA device. Target-host evidence falsified it, and
the correction is easy to reintroduce by accident because "start at least one
job" reads like ordinary conservatism.

This document records rationale only. It is not current authority.

## The falsifying observation

A post-selection cross-validation run on a 24 GiB device reported, before the
first training future was submitted:

```text
device total                 24.0 GiB
configured training ceiling  21.6 GiB   (the 90% default)
pre-launch occupied          20.2 GiB
safe envelope remaining       1.4 GiB
configured job estimate       6.0 GiB
```

The planner nevertheless produced `initial=1, ceiling=1`, and the run reached
CUDA out of memory inside the CuEq backward pass roughly 2,411 optimizer updates
into epoch 0.

Three separate mechanisms had to cooperate to produce that outcome:

1. the planner applied `max(1, ...)` to the hard RAM and VRAM feasibility
   results, so a zero-capacity calculation was rewritten as one feasible job;
2. the submission loop independently floored the controller target to one, so
   even a zero target could not reach execution;
3. memory safety was subordinated to optimizer-activity calibration, so
   occupancy above the configured envelope during initialization and validation
   was reported only as "waiting for true epoch compute".

## What was rejected

The correction deliberately did not:

- raise the 90% training VRAM fraction to make the observed case pass;
- adopt the contaminated 20.2 GiB observation as a new per-job estimate;
- treat out of memory as authority to change batch size, gradient
  accumulation, precision, the CuEq/e3nn backend, replay membership, or model
  architecture. Those are D2/D3-owned scientific and numerical decisions, and an
  allocation failure is not a mandate to mutate them.

## The corrected invariant

> CUDA starts with one training job only when one job is currently
> resource-admissible; zero safe admission is a valid execution state.

Supporting consequences, all of which are execution-only: current aggregate
occupancy counts regardless of which process owns it; a configured minimum
concurrency is subordinate to current feasibility; a positive configured job
count is a maximum cap; memory safety is judged on every trustworthy sample
independently of calibration readiness; and an idle queue holding pending work
with no feasible slot fails with a typed resource outcome rather than launching
or spinning.

## A contributing lifetime defect

Recovery/currentness classification could realize a CuEq/OEq training model on
the configured device to compute an architecture digest and return without an
explicit retirement boundary. Because that classification runs *before* the
admission baseline is sampled, its residency was counted into the baseline and
then kept for the remainder of the process. Classification is not training, so
the temporary portable and realized models are now retired at their own
ownership boundary, including on conversion/digest exception paths, reusing the
same collect/unused-cache-release/synchronize semantics as MACE provider
retirement.

Reference cycles are the reason a retirement boundary is required at all:
dropping the last name is not sufficient to reclaim device memory from module
graphs, so function-scope reclamation was never a guarantee.

## The second falsification: live safety was still conditional

The first correction made zero-safe admission real but left three conditional
paths that could reproduce the same physical family:

1. a sustained over-envelope observation became terminal only when exactly one
   training job was active. With two or more jobs the run was left to the
   calibrated saturation throttle, which lowers the *replacement* target and
   cannot return memory that already-running jobs hold.
2. a missing live memory observation cleared the accumulated unsafe history, so
   repeated telemetry loss could leave active accelerator work with no live
   safety observation at all - the exact assumption the corrected architecture
   depends on.
3. a generic training-child failure was stored, evaluation was run for the
   previously trained siblings, and only then was the original failure raised.
   That put fresh accelerator work on a device whose training state was unknown.

The correction is uniform rather than conditional. Live aggregate safety is
judged on every trustworthy sample at every active-job count; one unsafe
observation blocks all further admission and may be rechecked once; persistence
into the next normal control observation with any owned job active cancels and
reaps the whole training wave. Missing observability fails closed on the same
cadence, tolerating one isolated blind sample only after a safe one. Any
exception escaping the training wave cancels owned children and re-raises before
evaluation.

The transient tolerance moved from a wall-clock debounce to the scheduler's own
control cadence. The wall-clock form had briefly acquired an undocumented
`parallel_training_memory_hazard_grace_seconds` configuration key; operator
tuning was never an accepted requirement, so the public surface was removed
rather than documented. Expressing the bound in control observations also made
the state a two-value controller-local flag instead of a timestamp.

## Phase ownership

The training scheduler previously submitted the whole fold lifecycle as one
future - materialization, TRAIN2, checkpoint authentication, candidate and
replay EVAL2, outer evaluation, and publication. A scheduler whose resource
model is specifically a *training-job* model cannot calibrate against that, and
at concurrency above one a completed fold could hold evaluation providers while
a sibling TRAIN2 child was still active. A training slot now ends at the
authenticated TRAIN2 summary, and post-training EVAL2 runs afterwards through
the same run path. The authenticated summary was already the durable boundary,
so no handoff record was introduced, and an interruption before EVAL2 resumes
without retraining.

That same authenticated summary - not a same-invocation sibling EVAL2 - is the
progress-preservation boundary when a training wave fails. Running evaluation
for already-trained siblings after a failure preserved nothing that the durable
summary did not already preserve, while it did start fresh accelerator work on a
device that had just failed.

## Scope boundary

These rules govern TRAIN2 admission. The evaluation/verification and inference
controller keeps its own accepted calibration contract, including its serial
floor and its rule that a soft fractional envelope may not self-block an idle
queue. That contract has a different owner and a different history; it was
deliberately not changed here.

## Durable lessons

1. A "conservative" floor that rewrites an infeasible resource calculation into
   a feasible one is not conservative; it destroys the only signal that could
   have prevented the failure.
2. A readiness condition for *estimating* demand must not become a precondition
   for *recognizing* a hazard. Neither may an active-job count: a safety rule
   that exempts the concurrency levels it was introduced to protect is not a
   safety rule.
3. A transient diagnostic or classification realization needs the same explicit
   accelerator lifetime ownership as production execution, because it pollutes
   the baseline that later decisions are measured against.
4. A scheduler's future must span exactly the phase its resource model
   describes.
5. An aggregate-occupancy observation attributes nothing; process attribution is
   diagnostic, and admission must still treat whatever occupies the device as
   real.
6. Losing the observation that a safety rule depends on is a failure of that
   rule, not an absence of evidence against it. Blind supervision of live
   accelerator work must fail closed.
7. A debounce expressed in the control loop's own cadence needs no clock, no
   stored timestamp, and no operator knob.
