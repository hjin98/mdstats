---
title: "MLFF CUEQ-PHASE1 Development-Host Qualification"
subtitle: "mdstats 0.20.189a0 / architecture revision 56"
date: "2026-08-15"
geometry: margin=0.8in
fontsize: 10pt
---

# Result

**Control-plane gate:** PASS  
**Positive GPU qualification:** DEFERRED to `FINAL-GPU1`  
**Phase-separated CuEq training authorization:** NOT YET AUTHORIZED

CUEQ-PHASE1 is implemented as a training-only accelerator qualification. Source-foundation inference, DATA6, pseudolabel generation, and source evaluation remain on original MH-1/`omat_pbe`/e3nn. Only TRAIN2 may vary between e3nn and `cueq_pure` in the final paired campaign.

# Development-host evidence

The retained CUEQ-DEP1 development-host record is negative by design: `passed=false`, CUDA device count `0`, and blockers `cueq-core_import, cueq-torch_import, cueq-ops_import, torch_cuda_available, cuda_device_inventory`. Its content digest is `45a3d9aa919e557388dc6858feb64b7009f4eeaa838c097d4456f7f29b56f069`.

The phase-1 reducer is also fail-closed: `passed=false`, with blockers `CUEQ_DEP1_RUNTIME_FREEZE, short_paired_adaptation_missing, representative_full_pair_missing`. A short-only result cannot authorize training, and no short or representative full CuEq trajectory was executed on this development host.

# Foundation identities

| Foundation | Required head | SHA-256 |
|---|---|---|
| MACE-MH-1 | `omat_pbe` | `ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde` |
| MACE-MPA-0-medium | `default` | `75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638` |

Both uploaded model identities pass the release lock. The FINAL-GPU1 preflight schema is `mdstats.mlff-final-gpu1.preflight.2026-08.v3` and remains `deferred_not_executed` on this CPU-only host.

# CPU/control-plane validation

The focused adjacent suite passes **26/26 tests** with the real supplied foundation-model paths enabled. Serialization/tamper guards, protocol mismatch rejection, hard-decision mismatch rejection, short-only non-authorization, positive synthetic reducer behavior, FINAL-GPU1 handoff, and revision/schema synchronization all pass. `compileall` and stale current-version/schema scans also pass.

# Final-GPU1 obligations

A release-authorizing CUEQ-PHASE1 record still requires, on the same positive CUEQ-DEP1 runtime:

1. one passing 5-10 epoch paired e3nn versus pure-CuEq adaptation (default 8 epochs); and
2. at least one passing representative full paired trajectory under identical frozen scientific/training inputs.

Final checkpoint bytes are not required to match. Existing replay-retention, finiteness, checkpoint-admissibility, selected-head extraction, EVAL2, and available physical-verification decisions must agree and pass. Performance/VRAM telemetry is diagnostic and cannot relax scientific thresholds.

# Authorization boundary and next gate

This release does **not** authorize CuEq training yet, CuEq source execution, CuEq DATA6/pseudolabel generation, or a generated-default change. The next implementation gate is optional `CUEQ-PHASE2`, selected-head CuEq source-execution/DATA6 qualification, while the actual GPU evidence for CUEQ-PHASE1 remains consolidated into `FINAL-GPU1`.
