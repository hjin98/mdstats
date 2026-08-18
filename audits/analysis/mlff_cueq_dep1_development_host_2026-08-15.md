---
title: "CUEQ-DEP1 Development-Host Runtime Evidence"
author: "mdstats development"
date: "2026-08-15"
geometry: margin=0.85in
fontsize: 10pt
header-includes:
  - |-
    \usepackage{booktabs}
  - |-
    \usepackage{xurl}
---

# Result

**Implementation:** `mdstats 0.20.188a0`  
**Host role:** CPU/control-plane development host  
**CUEQ-DEP1 result:** **not qualified**  
**Runtime-record digest:** `41c1e2890bc34c3d7908762efd3f9d55259fbced4e0b0c7d468e20e9cd79ff70`

The record is deliberately negative. MACE/e3nn satisfy the locked reference runtime, but this host has CPU-only PyTorch and no CuEquivariance packages. No backend fallback is interpreted as success.

# Frozen reference components

| Component | Version | Import | Content-addressed |
|---|---:|:---:|:---:|
| PyTorch | `2.10.0+cpu` | pass | pass |
| MACE | `0.3.16` | pass | pass |
| e3nn | `0.4.4` | pass | pass |
| CuEq core | unavailable | fail | fail |
| CuEq Torch | unavailable | fail | fail |
| CuEq CUDA ops | unavailable | fail | fail |
| OpenEquivariance | unavailable | fail | optional |

The supplied dependency archive is bound as

`888d545a512396697c8583d69bc9ed33110914675f466a4cbcafc3e1e1407171`.

# Accelerator state

- CUDA available: **no**.
- CUDA runtime reported by PyTorch: none.
- Visible CUDA devices: 0.
- `nvidia-smi`: unavailable.
- `nvcc`: unavailable.
- PyTorch deterministic algorithms: disabled on this development host.
- float32 matmul precision: `highest`.

# Blocking reasons

1. `cueq-core_import`;
2. `cueq-torch_import`;
3. `cueq-ops_import`;
4. `torch_cuda_available`;
5. `cuda_device_inventory`.

These blockers are expected under the deferred-GPU development policy. Final CUEQ-DEP1 qualification requires a release-matched `passed=true` record produced by the user's final CUDA/CuEq environment during `FINAL-GPU1`.
