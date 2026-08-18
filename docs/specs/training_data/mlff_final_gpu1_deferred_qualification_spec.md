---
title: "MLFF FINAL-GPU1: Final-Release GPU Qualification Handoff"
author: "mdstats development"
date: "2026-08-15"
geometry: margin=0.8in
fontsize: 10pt
header-includes:
  - |
    \usepackage{microtype}
  - |
    \usepackage{booktabs}
  - |
    \usepackage{longtable}
---

# Status and intent

**Gate:** `FINAL-GPU1`  
**Release introducing the policy:** `mdstats 0.20.184a0`  
**Current status:** revision-82 `mdstats 0.20.215a0` FINAL-GPU1 v3 / preflight v9 is archival while revision-85 CUEQ-REPEAT1-DIAG3 warm-up/all-pairs repeatability evidence is being measured  
**Authority class:** qualification scheduling and release evidence; no scientific credit by itself  
**Development rule:** GPU-dependent qualification is deferred to one final-release execution package  

Intermediate development continues with CPU/reference tests, exact scientific-identity tests, serialization tests, and structural performance work. A GPU-dependent gate may be implemented and exercised synthetically or on CPU, but it remains **unqualified** until `FINAL-GPU1` runs on the authorizing CUDA/CuEquivariance machine.

This policy avoids repeated workstation handoffs while preserving fail-closed scientific status.

# 1. Locked foundation inputs

The final qualification package binds the supplied foundation models by byte identity.

| Foundation | Required head | SHA-256 prefix |
|---|---|---|
| MACE-MH-1 | `omat_pbe` | `ec00a2705854622f` |
| MACE-MPA-0-medium | `default` | `75428afe3a1d7d80` |

The complete SHA-256 values are authoritative in the machine-readable **foundation identity lock** shipped with the release; FINAL-GPU1 verifies the full 256-bit digest before any qualifying run.

The model binaries remain external inputs. The release package records and verifies their identities but does not silently substitute, rename, or regenerate them.

CPU/e3nn reference validation remains active during development. The supplied files match the previously locked project identities and pass the current real-model CPU reference suite.

# 2. Qualification-state separation

For a GPU-dependent gate $g$, define implementation state $I(g)$ and accelerator qualification state $Q(g)$ separately:

$$
I(g) \in \{\mathrm{planned},\mathrm{implemented}\},
\qquad
Q(g) \in \{\mathrm{pending},\mathrm{pass},\mathrm{fail}\}.
$$

Implementation progression may depend on $I(g)=\mathrm{implemented}$ when the downstream interface is stable and parameterized. Production release may depend on $Q(g)=\mathrm{pass}$.

No intermediate release may translate

$$
Q(g)=\mathrm{pending}
$$

into a success claim, a GPU speedup claim, or an accelerator-backed scientific default.

# 3. Deferred MLFF accelerator matrix

`FINAL-GPU1` consolidates the outstanding MLFF accelerator-dependent work:

1. `PREC3` real CuEq production activation;
2. `MH1-ACCEL1` real e3nn/CuEq numerical parity;
3. `MH1-DATA6-1` descriptor and deterministic selection parity under CuEq;
4. `MH1-TRAIN1` bounded real CuEq training realization and target-head round trip;
5. `MH1-CERT1` generated-default CuEq matrix;
6. `SIZE-FIDELITY1` exhaustive low-fidelity calibration on the locked MACE-MH-1 foundation;
7. `PERF-P2R` whole-funnel GPU/CPU/I/O/VRAM performance authority;
8. `VRAM1 + PERF-P4` combined-workload batch-capacity, peak/reserved VRAM, OOM-backoff, and synchronous-vs-pipelined throughput authority;
9. `PERF-P5` checkpoint-persistence and compatible-model-reload accelerator overhead/equivalence authority;
10. `CUEQ-DEP1` positive content-addressed CuEq/CUDA runtime freeze;
11. `CUEQ-PHASE1` training-only pure-CuEq qualification on the selected-head foundation;
12. optional `CUEQ-PHASE2` selected-head CuEq source-execution/DATA6 qualification;
13. `PERF-CERT1` end-to-end policy/performance certification; and
14. `E3NN-BASELINE` complete production-representative MH-1/e3nn control campaign.

`MH1-DEPLOY1` ML-IAP export and LAMMPS run-0 parity is packaged beside this matrix but is a distinct deployment-capability qualification because it additionally requires an ML-IAP-enabled `lmp` executable.

# 4. Consequence for SIZE-FIDELITY1 and PERF-P2R

`SIZE-FIDELITY1` remains scientifically required before the final target-size funnel is authorized, but it is no longer an **implementation-development blocker**. Its reducer, exhaustive calibration plan, candidate coarse epochs, monitor sizes, and equivalence widths are already parameterized.

Therefore `PERF-P2R` may be implemented against the complete candidate grid rather than against an assumed calibrated winner. In particular, optimization code must work for:

- coarse boundaries at 3, 4, or 5 epochs;
- monitor sizes 128, 256, 512, or 1024;
- coarse practical-equivalence widths 1, 2, or 4 meV/A; and
- every hard-coverage-qualified ladder width from 3 through 7 candidates.

The generated campaign default remains provisional until `SIZE-FIDELITY1` passes in `FINAL-GPU1`. If calibration selects a different point from the current 3-epoch / 256-frame / 1-meV/A default, the final release changes the versioned policy values without requiring a new orchestration design.

# 5. VRAM1/PERF-P4 final-GPU obligations

`0.20.186a0` implements VRAM1/PERF-P4 on CPU/reference paths but does not qualify accelerator performance. FINAL-GPU1 must run workload-specific `MaceBatchCapacityCalibration.v2` under the locked foundations; demonstrate scientific agreement among forced batch 1, calibrated batching, and deliberate OOM backoff; verify absolute/fractional VRAM reserve under live pressure; verify identity-bound OOM-cap restart reuse; and compare synchronous versus bounded pipelined execution. Pinned/nonblocking transfer may become a generated execution default only if the release-matched benchmark shows benefit under the same memory bound.

# 6. PERF-P5 final-GPU obligations

`0.20.187a0` CPU-qualifies PERF-P5 streamed TRAIN2/STOR2 hashing and implements a strictly optional EVAL2 compatible-model state reload path. FINAL-GPU1 must preserve the exact checkpoint and evaluation authorities while measuring release-matched accelerator behavior. It must compare fresh model reconstruction with state reload on the locked MH-1 and MPA-0 foundations, record checkpoint persistence overlap and synchronization costs, and reject shell reuse as a generated default unless it gives a repeatable end-to-end benefit without increasing VRAM/RSS beyond the active resource bounds. The CPU result is explicitly non-authorizing for accelerator default selection.


# 7. CUEQ-DEP1 final-runtime obligation

`0.20.188a0` implements `CueqDep1RuntimeRecord.v1` and upgrades FINAL-GPU1 preflight to schema v2; `0.20.189a0` advances it to v3 for CUEQ-PHASE1; `0.20.190a0` advances it to v4 for independent CUEQ-PHASE2 state; `0.20.191a0` advances it to preflight v5 for independent PERF-CERT1 state; `0.20.192a0` advances it to `mdstats.mlff-final-gpu1.preflight.2026-08.v6` with exact release-archive binding and the final handoff/reducer schemas. The final machine must produce a `passed=true` CUEQ-DEP1 record before CUEQ-PHASE1 can run.

The record requires all three CuEq layers - core, Torch frontend, and CUDA ops - rather than treating the Python frontend alone as accelerator availability. It content-addresses installed distribution metadata/RECORD evidence, freezes the imported module roots, and records CUDA device/driver/toolkit, cuDNN, PyTorch determinism/TF32/matmul state, and relevant environment variables. OpenEquivariance remains optional for phase 1. Missing or non-addressable components remain blockers and never cause e3nn fallback.

# 8. CUEQ-PHASE1 final-training obligation

`0.20.189a0` implements `CueqPhase1QualificationRecord.v1` and FINAL-GPU1 preflight v3. The final machine must use one positive CUEQ-DEP1 runtime digest for both sides of every pair, keep source inference/DATA6/pseudolabel/source evaluation on e3nn, and vary only the executable training realization between e3nn and pure CuEq.

FINAL-GPU1 must first execute the frozen 5-10 epoch short pair (default 8) and reject instability/divergence without treating short success as production authorization. It must then execute at least one representative full pair with identical selected-head starting checkpoint, DATA8 bundle, seed/order/splits, dtype, objective/LR/stopping/replay policies, and validation/EVAL2 authority. Both sides must preserve replay retention, finiteness, checkpoint admissibility, target-head extraction, EVAL2, and any available physical verification. Final checkpoint bytes may differ. Target/replay metric deltas and wall/update/VRAM telemetry are evidence only and cannot rescue a hard scientific failure.

A pass authorizes only e3nn source execution plus pure-CuEq training. It cannot authorize CuEq source/DATA6 execution or a generated-default change.

# 9. CUEQ-PHASE2 final source/DATA6 obligation

`0.20.190a0` implements `CueqPhase2QualificationRecord.v1` and FINAL-GPU1 preflight v4. This optional gate must use the original six-head MH-1/`omat_pbe` checkpoint under e3nn as the scientific reference and the exact EXTRACT1-derived single-head `omat_pbe` checkpoint under pure CuEq as the candidate executable realization. The original scientific source identity remains unchanged.

FINAL-GPU1 must run at least one deterministic stratified development-corpus assessment covering every declared-available composition/species, temperature/strain, high-force/difficulty, unusual local/mobile-ion, large/high-edge-count, and ordinary stratum. Locked-test configurations may validate a frozen decision but may not tune the realization, corpus, or tolerance.

Energy, force, stress/virial, and invariant-descriptor acceptance must reuse the existing acceleration-parity authority without relaxed tolerances. The same assessment must preserve foundation-difficulty parity, frozen-reference-transform PCA/FPS input parity, exact DATA6 and DATA7 selection fingerprints, and explicit cache/execution-realization lineage. If CuEq pseudolabel/E0 generation is to be authorized, value/E0 parity plus both original scientific-source and candidate execution-realization lineage are mandatory.

A pass may authorize only the derived selected-head CuEq source/DATA6/source-evaluation realization (and pseudolabel generation only when explicitly evidenced). Direct CuEq execution of the original six-head checkpoint and generated-default changes remain unauthorized. PERF-CERT1 remains the separate end-to-end recommendation/default authority.

# 10. PERF-CERT1 final end-to-end obligation

`0.20.191a0` implements `PerfCert1QualificationRecord.v1` and FINAL-GPU1 preflight v5. FINAL-GPU1 must first execute the optimized authoritative MH-1/`omat_pbe` e3nn baseline on the frozen production workload, then evaluate every available accelerated profile against that exact scientific protocol and workload identity.

At minimum the final evidence must bind total preparation time; TARGET-DATA2B families/s; TARGET-DATA2C selection/scoring time; DATA6 frames/s plus peak/reserved/headroom VRAM; TRAIN2 wall time and updates/s; EVAL2 time; CUDA OOM/backoff counts; target/replay metrics; deterministic target/DATA6/DATA7 selection identities; selected target size/seed, checkpoint/head identities; and available deployment/physical decisions. Different final checkpoint bytes are allowed, but all frozen hard scientific decisions must remain identical.

A pure-CuEq training profile is inadmissible without a positive CUEQ-PHASE1 record. A selected-head CuEq source/DATA6 profile additionally requires a positive CUEQ-PHASE2 record on the same CUEQ-DEP1 runtime. PHASE2 remains optional: its failure cannot invalidate an otherwise passing e3nn-source + CuEq-training profile.

The v1 recommendation authority requires a strictly positive total end-to-end speedup over the authoritative baseline. A faster path still fails if it changes source semantics, scientific protocol/workload, deterministic selection, replay retention, EVAL2, or available deployment/physical outcomes, or if locked-test evidence was used for tuning. A positive PERF-CERT1 record may recommend a phase-separated acceleration profile, but `generated_default_change_authorized` remains false; any generated-default change requires a later explicit policy revision and migration/compatibility tests.

# 11. Development-time constraints

The following remain mandatory before GPU handoff:

- exact scientific digests are invariant under CPU-side optimization;
- pause/resume ancestry is authenticated independently of accelerator timing;
- DataLoader/sampler/worker reconstruction is deterministic or explicitly persisted;
- GPU-specific caches and scheduling choices remain execution-only;
- no code path assumes that CuEq is available merely because MACE is installed;
- every GPU-dependent acceptance item remains visibly `pending` in qualification evidence; and
- final qualification scripts are shipped in the same source package as the code they test.

# 12. One-shot final execution package

The release contains `tools/run_mlff_final_gpu_qualification.py`. Its current v8 preflight verifies the exact release-archive SHA-256 plus the locked model hashes and embeds the complete CUEQ-DEP1 runtime record, including the CUDA-ops layer, plus independent deferred CUEQ-PHASE1, CUEQ-PHASE2, and PERF-CERT1 qualification states. It also records Python, PyTorch/CUDA, MACE, e3nn, OpenEquivariance, NVIDIA, and optional LAMMPS capability state.

The final package must then execute the complete deferred matrix without source edits. All resulting scientific records, logs, GPU telemetry, and checksums are written below one qualification root and are tied to the exact release artifact digest.

A failed item fails closed. The remedy is a new source release only when the result identifies a code or contract defect; environment absence remains an explicit capability failure rather than an inferred pass.

# 13. Current development-host evidence

The 2026-08-15 development host verifies both supplied foundation hashes and provides MACE 0.3.16 plus e3nn 0.4.4. PyTorch is CPU-only (`2.10.0+cpu`), CUDA is unavailable, and CuEq core, Torch frontend, and CUDA-ops layers are absent. The development-host CUEQ-DEP1 record therefore fails closed with explicit dependency/device blockers, and the consolidated state remains `deferred_not_executed`.

Machine-readable readiness-only preflight evidence (not positive GPU qualification evidence) is stored at:

`audits/analysis/mlff_final_gpu1_preflight_v6_2026-08-15.json`


# 14. FINAL-GPU1 v1 handoff and reduction authority

`0.20.192a0` implements `FinalGpu1Policy.v1`, `FinalGpu1EvidenceRecord.v1`, and `FinalGpu1QualificationRecord.v1`. The handoff is resumable and writes all state below one qualification root, but registrations are immutable: reinitializing a non-empty root or replacing a registered gate result is rejected. Initialization requires both foundation files to match the locked MH-1 and MPA-0 identities. The release archive is hashed at initialization; every registered evidence record must bind that same digest. Every CuEq-dependent gate is explicitly runtime-bound to one `CueqDep1RuntimeRecord.v1` digest, and a missing binding is a blocker rather than an inferred match.

The matrix has three acceptance classes. `must_pass` is reserved for release-blocking scientific/safety authorities: CUEQ-DEP1, the complete e3nn baseline, SIZE-FIDELITY1, PERF-P2R, VRAM1/PERF-P4, CUEQ-PHASE1, and PERF-CERT1. `measure_only` requires completed evidence but does not require the optimization to win: historical direct-six-head CuEq probes and PERF-P5 may be negative if the associated optimization remains disabled or is superseded by the qualified phase-separated path. `optional` covers CUEQ-PHASE2 and ML-IAP/LAMMPS deployment capability.

The handoff integrity pass re-hashes the exact release archive and locked models plus every evidence-record JSON and copied evidence artifact before final reduction. It also requires the manifest policy to equal the canonical FINAL-GPU1 policy and the matrix to equal the exact ordered policy matrix, including each gate ID, acceptance class, canonical record path, and allowed state. It rejects post-registration byte changes, record/evidence path escape, matrix/record state mismatch, policy/matrix structural drift, and schema/content-digest drift. Explicit `pass`/`fail` registration cannot contradict a producer payload that already exposes a boolean pass state or recognized terminal status. The final reducer then cross-checks the structured CUEQ-DEP1 runtime content digest, PERF-CERT1 content digest, PHASE1 qualification digest, and any registered PHASE2 qualification digest. A file-name match or user-supplied status string cannot override these identities. Missing must-pass evidence, a failed must-pass gate, missing measure-only evidence, a pending measurement, foundation-model drift, release-archive drift, runtime drift or missing runtime binding, handoff-integrity failure, or a failed PERF-CERT1 authority all block final qualification.

A passing FINAL-GPU1 record may expose the PERF-CERT1 recommended profile, but the generated-default authorization flag remains false. The record may instead state that a later generated-default policy revision is required.

# 15. Workstation execution workflow

The shipped workstation runbook uses the following immutable sequence: verify bundle checksums; create the release-matched CUDA/CuEq environment; run preflight v9; initialize one handoff root; capture positive CUEQ-DEP1; execute and register the authoritative e3nn baseline and required final-GPU calibration/performance authorities; execute/register the PHASE1 short and full paired evidence; optionally execute PHASE2 and deployment evidence; assemble PERF-CERT1; run the explicit handoff `verify` re-hash; then reduce FINAL-GPU1. Failures remain in the same handoff root and can be inspected without source edits. Replacement evidence belongs in a new run root rather than overwriting provenance.

No CPU-development result in `0.20.192a0` is promoted to positive accelerator evidence.

## Historical v2 extension (revision 76)

FINAL-GPU1 v2 added two release-blocking records to the historical matrix: `SIZE_FIDELITY2_MV_SURVIVOR_REQUALIFICATION` and `TARGET_DATA2C_MVMIGRATE1_LEARNING_CONTROLS`. The reducer deserializes the exact typed qualification records, requires final GPU status `passed`, requires their content digests to match immutable gate registrations, and requires a common dataset identity. These records authorize only the separately frozen MVMIGRATE1 transition; FINAL-GPU1 continues to report `generated_default_change_authorized=false` for unrelated defaults.

The post-reduction migration command remains deliberately separate. A dry-run recomputes the migration plan and v5/v3 authorities from the campaign store and final evidence. `--apply` then commits the historical-v4 preservation, live-v5 alias, v3 convergence plan, final evidence records, and activation receipt in one SQLite transaction. CPU-only tests cannot synthesize positive final GPU authority.

## Current v3 extension (revision 81)

`mdstats 0.20.214a0` regenerated the final handoff after REPLAY-UNIFY1A-E and advances the immutable matrix to 18 items: 10 `must_pass`, 6 `measure_only`, and 2 `optional`. The new release-blocking, runtime-bound item is `REPLAY_UNIFY1_GPU_PSEUDOLABEL_EXECUTION`. It closes the only accelerator path introduced by the replay migration rather than assuming the earlier FINAL-GPU1 matrix covers it implicitly.

`mdstats 0.20.215a0` retains the same v3/18-item matrix but advances preflight to v9 for CUEQ-DEFAULT1-HF2. The preflight and handoff manifest now bind the exact TRAIN2 acceleration-parity policy payload and content digest (`rtol=1e-5, atol=1e-5` for FP32). Handoff integrity verification rejects any mismatch between the recorded policy and the active release policy, so revision-81/v8 provenance cannot authorize the hotfixed archive.

The replay GPU evidence must come from the release-matched `foundation_pseudolabel` campaign path using the single authoritative replay source and the locked foundation model/head. It must demonstrate exactly 10,000 training and 2,000 monitor members from the 12,000-frame qualification source; identical pseudo-label and true-label monitor geometry membership; finite energy/force/stress predictions; successful authenticated cache restart with zero foundation reinference; and measured replay prediction throughput plus peak/reserved VRAM under the frozen CUDA/CuEq runtime. The evidence is content-addressed and registered under the exact v3 gate ID before final reduction.

FINAL-GPU1 v3 retains the v2 typed SIZE-FIDELITY2 and MVMIGRATE1 controls and remains backward-readable for historical v1/v2 qualification records, but only a current v3 record can authorize the current release. Development-host CPU/control-plane qualification remains non-authorizing.


## Revision 83 diagnostic hold

`mdstats 0.20.217a0` does not change FINAL-GPU1 matrix semantics or parity tolerance, but it refines the non-authorizing TRAIN2 repeatability investigation with complete self-tail statistics and an isolated deterministic-control probe. The 0.20.215a0/v9 workstation bundle therefore cannot authorize revision 84. Regenerate a release-matched FINAL-GPU1 handoff only after the refined MPA-0 ordinary and deterministic-control statistics are reviewed and any resulting parity-policy decision is frozen.


### Revision 85 diagnostic hold

`mdstats 0.20.218a0` advances only the non-authorizing TRAIN2 repeatability diagnostic. One warm-up evaluation per backend is discarded, then ten post-warm-up outputs produce 45 e3nn-self, 45 CuEq-self, and 100 cross-backend comparisons. FINAL-GPU1 matrix semantics and active parity tolerances are unchanged. Regenerate a release-matched handoff only after DIAG3 evidence is interpreted and the permanent noise-normalized criterion is frozen.
