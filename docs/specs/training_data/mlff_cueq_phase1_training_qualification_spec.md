---
title: "MLFF CUEQ-PHASE1 Training-Only Qualification"
subtitle: "Phase-separated e3nn source execution and pure-cuEquivariance training"
date: "2026-08-15"
geometry: margin=0.8in
fontsize: 10pt
header-includes:
  - |
    \usepackage{microtype}
---

# 1. Scope

**Gate:** `CUEQ-PHASE1`  
**Implementation release:** `mdstats 0.20.189a0`  
**Qualification schedule:** `FINAL-GPU1`

CUEQ-PHASE1 implements the scientific-evidence and execution-separation authority for the first accelerator training experiment. It does not run or claim intermediate GPU qualification.

The frozen execution split is

$$
\text{source inference / DATA6 / pseudolabels / source evaluation}=\mathrm{e3nn},
\qquad
\text{TRAIN2}=\mathrm{CuEq}_{\mathrm{pure}}.
$$

The candidate starts from the exact EXTRACT1-qualified selected-head `omat_pbe` checkpoint. The original six-head MH-1 checkpoint and exact `omat_pbe` head remain the scientific source-foundation identity.

# 2. CUEQ-DEP1 prerequisite

Every paired trajectory binds the same `CueqDep1RuntimeRecord.v1` digest. Positive CUEQ-PHASE1 authorization is impossible unless that runtime record passes. Missing CUDA/CuEq capability remains negative evidence and never causes e3nn fallback.

OpenEquivariance remains optional for phase 1 because MACE 0.3.16 trains with pure CuEq when CuEq training is enabled.

# 3. Paired protocol identity

The e3nn reference and pure-CuEq candidate must bind identical values for:

- source-foundation scientific digest;
- selected-head starting checkpoint SHA-256 and EXTRACT1 qualification digest;
- DATA8 bundle identity;
- optimizer semantics, seed, dtype, epoch budget, and update budget;
- split and deterministic data-order identities;
- objective-weight, learning-rate, stopping, and replay-policy identities; and
- validation and EVAL2 protocol identities.

The backend realization is the deliberate independent variable: reference training is `e3nn`, candidate training is `cueq_pure`.

# 4. Two-level qualification

The gate requires both:

1. a **short paired adaptation** with the frozen short endpoint in the 5-10 epoch interval (default 8 epochs); and
2. **at least one representative full paired authorized training trajectory**.

A passing short trajectory is an instability/divergence screen only. It cannot authorize production CuEq training by itself.

# 5. Scientific acceptance

Final model weights and checkpoint bytes are not required to be bit-identical. Accelerator kernels may perturb the optimization path.

The gate instead requires both sides to preserve the existing scientific authority:

- complete the frozen epoch/update budget;
- finite losses, gradients, and parameters;
- pass TRUE_DFT replay retention;
- preserve checkpoint admissibility and the existing ranking authority;
- successfully extract the selected `target_head`;
- pass EVAL2;
- pass any physical verification that is available for the reference path; and
- avoid any hard-decision disagreement between the paired runs.

Target/replay validation metrics are recorded with their paired deltas but CUEQ-PHASE1 introduces no new tolerance and does not relax any existing scientific threshold.

# 6. Performance evidence

Each trajectory records wall time, update throughput, peak allocated VRAM, and peak reserved VRAM. Pair evidence reports speedup as a diagnostic. Performance cannot rescue a failed scientific decision.

# 7. Schemas and implementation

`mdstats.training_data.cueq_phase1` defines:

- `CueqPhase1Policy.v1`;
- `CueqPhase1TrajectoryRecord.v1`;
- `CueqPhase1PairedAssessment.v1`; and
- `CueqPhase1QualificationRecord.v1`.

The gate tool is:

```text
tools/qualify_mlff_cueq_phase1.py
```

It can build a pair record, assemble final short+full qualification evidence, or emit the current deferred fail-closed state. It deliberately does not launch GPU training.

FINAL-GPU1 preflight advances to schema `mdstats.mlff-final-gpu1.preflight.2026-08.v3` and embeds the CUEQ-PHASE1 deferred state plus the exact qualification schema expected from the final workstation campaign.

# 8. Authorization boundary

A passing CUEQ-PHASE1 record authorizes only:

```text
source execution = e3nn
training execution = cueq_pure
```

It does **not** authorize:

- CuEq execution of the original six-head MH-1 source foundation;
- CuEq DATA6 or pseudolabel generation;
- CUEQ-PHASE2;
- a generated-default change; or
- reinterpretation of prior e3nn scientific evidence.

Those remain separate gates.

# 9. Development-host state

The release environment is CPU-only and lacks the CuEq core/Torch/CUDA-ops stack. CUEQ-PHASE1 therefore remains intentionally unqualified at release build time. The implementation is CPU/control-plane qualified; positive paired training evidence is deferred to the single consolidated `FINAL-GPU1` run.
