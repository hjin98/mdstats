# MLFF PREC1-PREC3 staged-precision profile specification

> **Historical compatibility specification.** PREC1-PREC3 describe the staged precision
> implementation used by campaigns created before ADAPT-PREC1. From mdstats 0.20.122a0,
> newly initialized production campaigns support only binary `single|double` learned-model
> precision; `refine`/user-facing `mixed` production semantics are retired. Historical
> staged schedules remain readable and regression-tested but cannot seed a new production
> protocol silently. See `mlff_binary_model_precision_spec.md`.

Status: PREC1 implemented in mdstats 0.20.108a0; PREC2 implemented in mdstats 0.20.109a0; PREC3 implemented in mdstats 0.20.110a0. STOR1 is implemented in mdstats 0.20.111a0, STOR2 in mdstats 0.20.113a0, STOR3 in mdstats 0.20.114a0, STOR4 in mdstats 0.20.115a0, and STOR5 in mdstats 0.20.116a0; the post-0.20.105 evaluation/precision/storage roadmap is complete.

## Purpose

This specification defines a user-facing precision-profile layer and a generalized,
protocol-bound precision schedule for MACE fine-tuning. It extends the implemented
DATA9A4 one-stage FP32/FP64 precision contract; it does not reinterpret or invalidate
existing frozen protocols.

The implementation order is:

1. **PREC1** - profile/configuration schema, deterministic schedule resolution,
   `init --precision` generation, and protocol identity;
2. **PREC2** - in-process precision-stage execution, optimizer/AMSGrad/EMA promotion,
   LR/scheduler continuity, and exact restart semantics;
3. **PREC3** - campaign integration, reporting, bounded real-MACE qualification, and
   activation of the generated profiles.

Storage stages follow only after PREC3 because staged checkpoints introduce new dtype,
optimizer-state, and capsule-lifetime requirements.

## Canonical profiles

The initializer exposes exactly three canonical profile names initially:

- `single`: float32 preparation/foundation, one-stage float32 training, float32
  evaluation, float32 verification, and float32 export;
- `double`: float64 preparation/foundation, one-stage float64 training, float64
  evaluation, float64 verification, and float64 export; and
- `refine`: float64 preparation/foundation, staged float32 -> float64 training, float64
  evaluation, float64 verification, and float64 export.

Plain `init` is equivalent to `init --precision single`. No hardware heuristic may
silently substitute a different profile.

`refine` is an economical FP64-refined protocol, not a guarantee of scientific
identity with a full-FP64 (`double`) optimization trajectory.

Canonical `single` is genuinely profile-wide FP32: existing critical reductions and
returned-observable precision must resolve to FP32 rather than silently retaining the
historical critical-FP64 lock. `double` and the non-training portions of `refine` use
FP64 critical precision. Legacy FP32-body/critical-FP64 configurations remain readable
and reproducible as legacy/custom policies, not canonical `single`.

## PREC1 - explicit configuration and schedule identity - implemented in 0.20.108a0

The generated TOML must record both the friendly requested profile and the explicit
resolved schedule. The reference refine policy is:

- 80% of epochs in float32;
- 20% of epochs in float64;
- base training learning rate `1.0e-4` under the current campaign default;
- FP32-stage learning-rate scale `1.0`;
- FP64-stage learning-rate scale `0.5`;
- final-stage floor of 3 FP64 epochs;
- reference final-stage floor of 15,000 FP64 gradient updates;
- optimizer, scheduler, and EMA state preserved across the transition.

Fractions are deterministic schedule inputs, not hard-coded epoch numbers. With 30
epochs, the canonical 80/20 profile resolves to 24 FP32 and 6 FP64 epochs. Rounding
residue is assigned deterministically so resolved stage epochs sum exactly to the frozen
epoch budget.

If the nominal 20% final stage does not satisfy configured minimum refinement floors,
the final stage expands until they are satisfied while preserving at least one FP32
epoch. The three-epoch floor is always hard. The canonical 15,000-update value is a
reference floor calibrated on replay-sized exposure rather than a portable absolute
optimizer-step requirement: when the exact canonical 80/20 profile already satisfies
the hard epoch floor but 15,000 FP64 updates are mathematically impossible within the
whole staged budget, the resolver preserves the nominal split and binds the achievable
FP64 update floor into the resolved protocol. User-edited/custom schedules retain strict
fail-closed update-floor semantics.

The generalized schema should support more than two explicit stages for advanced
manual configurations, although the canonical generated profiles use one stage
(`single`, `double`) or two (`refine`).

### Learning-rate contract

`learning_rate_scale` is relative to the effective optimizer learning rate at the stage
boundary. The scheduler and optimizer parameter-group LR bookkeeping must be transformed
coherently. A profile transition must not accidentally increase LR unless the user has
explicitly requested an absolute stage LR that does so.

### Identity

`TrainingProtocolIdentity` binds the fully resolved stage schedule, not merely the
friendly profile label. At minimum it binds stage dtype, resolved epoch/update bounds,
LR scale, optimizer/scheduler/EMA preservation policy, critical-operation dtype, and
non-training pipeline dtypes. Thus `refine` 80/20 and `refine` 90/10 are distinct
protocols.


### 0.20.108a0 implementation note

PREC1 is implemented as a protocol/configuration gate without claiming the later runtime
transition. `init` accepts `--precision {single,double,refine}` and plain `init` resolves
to `single`. Generated TOML writes the requested profile, explicit ordered stage tables,
critical-operation dtype, preservation policy, evaluation/verification/export dtypes, and
refinement floors. DATA8 resolves the schedule only after effective loader exposure is
known, so epoch and gradient-update boundaries are bound into `TrainingProtocolIdentity`.
Legacy campaign files with no `[training.precision]` remain schedule-free in serialized
v4 optimizer/v2 protocol identity and can be mapped losslessly to the generalized
one-stage representation for inspection.

Because production profile activation belongs to PREC3, preflight remains fail-closed for
explicit multi-stage schedules and for canonical `single` critical-FP32 execution rather
than silently executing the legacy critical-FP64 wrapper or remaining in the first stage.
The existing one-stage `double` path is compatible with the already-qualified FP64 runtime.

## PREC2 - in-process transition and exact restart - implemented in 0.20.109a0

The canonical FP32 -> FP64 switch occurs inside a live training process at a frozen
epoch boundary. It is not implemented as a normal stop/restart with a different MACE
`default_dtype`.

Promotion includes every floating model parameter/buffer and every floating optimizer
or EMA state required for continuation, including Adam/AMSGrad first and second moments,
AMSGrad maximum-second-moment tensors, and EMA shadow parameters. Backend-specific
floating training state discovered by the qualified MACE/e3nn/CuEq adapter is included.

A transition record persists source/destination stage identities, epoch/update boundary,
pre/post dtype inventories, LR before/after, scheduler identity, backend identity, and
state/checkpoint digests.

Exact restart is mandatory. If upstream MACE checkpoint bytes do not contain sufficient
EMA or precision-stage state, mdstats must persist an authenticated companion state.
Restart before, at, or after the boundary may neither repeat nor skip the transition.


### 0.20.109a0 implementation note

PREC2 installs the resolved DATA8 precision schedule into the live MACE 0.3.16 training loop. At a stage boundary mdstats promotes model floating parameters/buffers, all floating Adam/AMSGrad state, EMA shadow state, and floating batches; integral graph/index tensors are preserved. The stage LR scale is applied to optimizer groups and scheduler-held LR bookkeeping.

Exact restart uses a latest-only authenticated companion because upstream MACE checkpoints contain EMA-averaged model weights and optimizer/scheduler state but do not persist the live model plus EMA shadow state required for exact continuation. The companion is committed atomically after the matching raw checkpoint; an unpaired newer raw checkpoint is ignored after interruption. Restart constructs the model in the companion stage dtype before loading the raw checkpoint and restores live/EMA state from the companion.

A durable transition receipt records source/destination stage, epoch/update boundary, pre/post dtype inventories, LR state, schedule/protocol identities, and source checkpoint/companion digests. Focused restart tests demonstrate identical continuation across the boundary, and a real MACE 0.3.16 e3nn force-training smoke finishes the post-switch stage uniformly FP64. Existing CuEq campaign/source-contract tests pass, but `cuequivariance` is not present in the supplied qualification environment; real CuEq runtime execution is therefore retained as a PREC3 activation requirement.

PREC2 intentionally left production profile activation to PREC3. mdstats 0.20.110a0 removes that temporary gate only after profile-bound critical precision, cross-stage evaluation, deployment dtype enforcement, and campaign reporting are integrated.

## PREC3 - campaign integration and qualification - implemented in 0.20.110a0

The requested profile and resolved schedule are visible in doctor/preflight/training,
evaluation, verification, and final reports. `refine` uses FP64 for all non-training
stages and produces a uniformly FP64 final deployment artifact. PREC3 also generalizes
the existing critical-precision policy so canonical `single` is FP32 throughout
profile-controlled critical operations, while `double`/`refine` retain FP64 critical
precision.

Bounded qualification covers `single`, `double`, canonical `refine`, at least one
non-default staged schedule, restart on both sides of the transition, and naive plus
multi-head replay where feasible. Qualification tests arithmetic realization,
restartability, lineage, finite execution, and final artifact dtype. It does not require
`refine` to match `double` RMSE; that is empirical model-quality evidence evaluated by
the checkpoint-evaluation system.

After qualification, plain `init` still generates `single`; `double` and `refine` remain
explicit opt-ins.

### PREC3 implementation closure (0.20.110a0)

The campaign now activates the DATA8-bound critical-precision policy instead of inferring behavior from a local model dtype. Explicit `single` disables the historical ScaleShiftMACE critical-FP64 patch and executes profile-controlled critical operations in native FP32. `double` and `refine` activate the qualified FP64 critical policy. Schedule-free legacy configurations retain their historical FP32-body/critical-FP64 behavior and serialization identity.

`doctor`, `prepare`, `preflight`, `train`, evaluation, verification, and final result surfaces expose the requested profile and resolved stage schedule. Preparation writes `results/precision-profile.json`; final evaluation and verification payloads embed the same profile record. No accelerator/resource heuristic changes the requested precision profile.

Checkpoint evaluation is stage-independent: explicit-profile checkpoint reconstruction may cast the completed whole-model architecture template to the checkpoint state dtype, and MACECalculator then converts that model to the profile's evaluation dtype. Thus EVAL-MF can evaluate FP32 and FP64 refine epochs under the same FP64 authoritative evaluation contract. Legacy materialization retains the old fail-safe dtype-mismatch fallback.

Target-head deployment for explicit profiles passes through the existing exact MACE deployment converter. Consequently, a refine winner originating in the FP32 stage is still serialized, reloaded, and state-verified as a uniformly FP64 deployment/verification model; canonical single exports uniformly FP32. Conversion manifests are retained beside deployment artifacts.

Real MACE 0.3.16/e3nn qualification exercises canonical FP32 and FP64 calculator paths, FP32-checkpoint evaluation under an FP64 refine policy, exact FP32-to-FP64 deployment conversion, and the PREC2 staged force-training transition/restart tests. The build environment does not provide `cuequivariance`/`cuequivariance_torch`; therefore no local real-CuEq execution claim is made. CuEq campaigns remain fail-closed on runtime availability and their normal real-MACE preflight consumes the same immutable critical-precision policy. A CuEq-enabled environment must complete that runtime preflight before production training.

PREC3 does not claim that refine and double converge to equal RMSE. That remains empirical model-quality evidence for EVAL-MF.

## Acceptance checklist

### PREC1

- deterministic profile generation and parsing;
- explicit generated TOML schedule;
- 30 -> 24/6 canonical refine resolution;
- deterministic refinement-floor handling;
- schedule-bound protocol digests;
- backward-compatible one-stage FP32/FP64 configuration mapping.

### PREC2

- model/optimizer/AMSGrad/EMA dtype promotion;
- no stale FP32 floating continuation state after the transition;
- LR/scheduler continuity;
- durable stage-boundary record;
- uninterrupted versus resumed equivalence;
- real MACE 0.3.16 and qualified CuEq force-training smoke;
- uniformly FP64 final refine model.

### PREC3

- end-to-end single/double/refine campaign smoke;
- profile/schedule visible in reports and manifests;
- EVAL-MF and deployment/verification compatibility;
- generated example/config documentation parity;
- no silent hardware-driven profile substitution.
