---
title: "MLFF FINAL-GPU1: Final-Release GPU Qualification Handoff"
author: "mdstats development"
date: "2026-08-22"
geometry: margin=0.8in
fontsize: 10pt
---

# Status and intent

**Gate:** `FINAL-GPU1`  
**Current software generation:** target-size v5 / `mdstats 0.20.242a0` branch state
**Current policy schema:** `mdstats.final-gpu1-policy.target-size-v5.v4`
**Current preflight schema:** `mdstats.mlff-final-gpu1.preflight.target-size-v5.2026-08.v11`
**Authority class:** final accelerator/release qualification; no target-size-selection authority
**Development rule:** GPU-dependent qualification is deferred to one final-release execution package.

FINAL-GPU1 is deliberately downstream of the scientific target-size redesign. The production target-size authority is already the fixed-eight `REPAIR2 -> MVQUAL2 -> TargetSizeStudyPolicy` path. FINAL-GPU1 does not activate, migrate, rescue, or replace target-size state and cannot change `selected_target_size`.

The development host may establish CPU/reference correctness, exact identity, restart behavior, serialization, and control-plane performance. It may not translate missing accelerator execution into a positive GPU result.

# 1. Locked foundation inputs

The final handoff binds the supplied foundation models by their complete SHA-256 identities. The authoritative digests are `mdstats.FINAL_GPU1_LOCKED_FOUNDATION_SHA256`.

| Foundation | Required head | SHA-256 prefix |
|---|---|---|
| MACE-MH-1 | `omat_pbe` | `ec00a2705854622f` |
| MACE-MPA-0-medium | `default` | `75428afe3a1d7d80` |

The model files remain external inputs. A release handoff must never silently replace, rename, or regenerate them.

# 2. Qualification-state separation

For a GPU-dependent gate \(g\), implementation state and accelerator qualification state are distinct:

$$
I(g) \in \{\mathrm{planned},\mathrm{implemented}\},\qquad
Q(g) \in \{\mathrm{pending},\mathrm{pass},\mathrm{fail}\}.
$$

Implementation may proceed when a downstream interface is stable and independently testable. Production accelerator claims require the corresponding positive final-GPU evidence. In particular, `pending` never means pass, never proves a speedup, and never authorizes a generated accelerator default.

# 3. Current immutable qualification matrix

`FinalGpu1Policy.v4` owns one exact 16-item matrix: eight `must_pass`, six `measure_only`, and two `optional` gates.

## 3.1 Must-pass gates

1. `CUEQ_DEP1_RUNTIME_FREEZE`
2. `E3NN_BASELINE_COMPLETE_CAMPAIGN`
3. `SIZE_FIDELITY1_EXHAUSTIVE_CALIBRATION`
4. `PERF_P2R_WHOLE_FUNNEL_GPU_PERFORMANCE`
5. `VRAM1_PERF_P4_ACCELERATOR_MEMORY_THROUGHPUT`
6. `CUEQ_PHASE1_TRAINING_ONLY_QUALIFICATION`
7. `REPLAY_UNIFY1_GPU_PSEUDOLABEL_EXECUTION`
8. `PERF_CERT1_END_TO_END_CERTIFICATION`

## 3.2 Measure-only gates

1. `PREC3_REAL_CUEQ_ACTIVATION`
2. `MH1_ACCEL1_CUEQ_NUMERICAL_PARITY`
3. `MH1_DATA6_1_CUEQ_DESCRIPTOR_SELECTION_PARITY`
4. `MH1_TRAIN1_CUEQ_TRAINING_REALIZATION`
5. `MH1_CERT1_GENERATED_DEFAULT_CUEQ_MATRIX`
6. `PERF_P5_ACCELERATOR_PERSISTENCE_REUSE`

A measure-only optimization may be negative when that optimization remains disabled or is superseded by the qualified production realization. Evidence is still required and remains content-addressed.

## 3.3 Optional gates

1. `CUEQ_PHASE2_SELECTED_HEAD_SOURCE_EXECUTION_OPTIONAL`
2. `MH1_DEPLOY1_MLIAP_EXPORT_AND_LAMMPS_RUN0`

These gates may establish additional capability but do not block the core final release.

The retired `SIZE_FIDELITY2_MV_SURVIVOR_REQUALIFICATION` and `TARGET_DATA2C_MVMIGRATE1_LEARNING_CONTROLS` records are historical only. They are not current matrix entries and no migration-activation command exists in the target-size-v5 release path.

# 4. Target-size ownership boundary

FINAL-GPU1 must preserve the current target-size architecture rather than qualify a second one.

The only production size population is

$$
\mathcal N_0=(128,256,512,1024,2048,4096,8192,16384).
$$

`REPAIR2` owns candidate membership through exact prefixes, `MVQUAL2` is the sole hard size-eligibility authority, and `TargetSizeStudyPolicy` owns the complete configurable screen `(n1,n2,n3)` decision. Generated campaigns default to screen `(1,3,10)` with fresh production horizon `30`; `selected_target_size` is frozen before held-out CV/EVAL/VERIFY.

FINAL-GPU1 may measure the performance of this workflow and may execute `SIZE_FIDELITY1` as an algorithm-calibration/release-qualification exercise, but it may not:

- create rescue/generated target sizes;
- migrate legacy ladder state into the current campaign;
- apply a second MV/replay/physical hard qualification to target-size eligibility;
- use held-out validation to change the selected size; or
- authorize a target-size topology change by a positive GPU result.

# 5. Runtime freeze and accelerator identity

A positive handoff uses one exact `CueqDep1RuntimeRecord` for every runtime-bound gate. The runtime record captures the CuEquivariance core, Torch frontend, CUDA operations layer, imported-package provenance, CUDA/PyTorch/device state, deterministic settings, and relevant environment identity.

Missing or incompatible accelerator components are explicit blockers. They do not imply e3nn equivalence and cannot be converted to a pass by editing the handoff manifest.

# 6. Required scientific and performance evidence

The release-matched final machine must establish, as applicable:

- a complete optimized e3nn baseline campaign;
- the current configurable target-size funnel's accelerator execution and `SIZE_FIDELITY1` calibration evidence;
- exact restart/continuation and hard-decision identity under PERF-P2R;
- VRAM capacity, reserve/headroom, OOM/backoff, and bounded-pipeline behavior;
- phase-1 e3nn-versus-pure-CuEq training qualification from the same selected-head foundation and frozen scientific protocol;
- replay pseudolabel execution with the release-authoritative replay source/split/cache identities;
- end-to-end PERF-CERT1 comparison against the authoritative e3nn baseline; and
- all required content digests, runtime bindings, logs, and telemetry.

A faster profile is not sufficient if scientific identities or hard decisions drift. Final checkpoint bytes may differ where the governing qualification explicitly allows different executable realizations.

# 7. Development-host constraints

Before the workstation handoff:

- CPU/reference optimizations must preserve exact scientific digests where exact equivalence is required;
- pause/resume ancestry must remain authenticated independently of accelerator timing;
- GPU-specific caches and scheduling remain execution-only;
- code must not infer CuEq availability from MACE installation alone;
- deferred accelerator gates remain visibly unqualified; and
- the final qualification tool ships in the exact source archive it evaluates.

No GPU qualification is required to complete the target-size-v5 architectural redesign itself.

# 8. One-shot final execution package

`tools/run_mlff_final_gpu_qualification.py` is the release handoff entry point. Current preflight v11 binds:

- the exact release archive SHA-256;
- both locked foundation model SHA-256 identities;
- CUDA/PyTorch/CuEq runtime state;
- the current FINAL-GPU1 policy and qualification schemas; and
- the frozen TRAIN2 acceleration-parity policy identities.

The handoff root is immutable at the evidence-registration layer. Replacement evidence belongs in a new root rather than overwriting provenance.

The supported lifecycle is:

```text
preflight -> init -> record ... -> verify -> reduce
```

A failed item fails closed. Environment absence remains a capability failure, while a code/contract defect requires a corrected source release.

# 9. Handoff integrity and reduction

The current reducer requires the manifest policy to equal the canonical `FinalGpu1Policy`, including gate order and acceptance classes. Integrity verification re-hashes the release archive, locked models, registration records, and copied evidence artifacts and rejects:

- post-registration byte changes;
- path escape or path substitution;
- policy/matrix structural drift;
- inconsistent disposition versus producer-reported pass state;
- missing runtime bindings for runtime-bound gates;
- schema/content-digest drift;
- missing required evidence; and
- any failed must-pass gate.

A positive qualification may expose a PERF-CERT1 recommendation, but `generated_default_change_authorized` remains false. A later explicit policy revision is required for an accelerator generated-default change.

# 10. Historical generations

Historical FINAL-GPU1 v1-v3, SIZE-FIDELITY2, MVMIGRATE1, TARGET-DATA2C migration, and associated activation records remain documented under `docs/history/mlff/`. They explain prior releases but have no current execution or restart authority.

Current target-size-v5 code deliberately rejects obsolete derived target-size/migration state rather than translating it.
