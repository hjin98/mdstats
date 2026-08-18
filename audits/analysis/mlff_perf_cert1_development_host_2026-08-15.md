---
title: "MLFF PERF-CERT1 Development-Host Qualification"
subtitle: "mdstats 0.20.191a0 / architecture revision 58"
author: "mdstats project"
date: "2026-08-15"
geometry: margin=0.8in
fontsize: 10pt
---

# Result

**Control-plane implementation: PASS.**  
**Positive GPU/CuEq execution: DEFERRED to FINAL-GPU1.**  
**PERF-CERT1 recommendation authority on this host: NOT AUTHORIZED.**

The current development host is CPU-only and therefore cannot supply the positive accelerator evidence intentionally deferred to the user's final workstation campaign. This is a capability limitation, not a scientific fallback. The PERF-CERT1 record fails closed.

# Frozen foundation identities

| Foundation | Required head | SHA-256 prefix | Result |
|---|---|---|---|
| MACE-MH-1 | `omat_pbe` | `ec00a2705854...` | PASS |
| MACE-MPA-0-medium | `default` | `75428afe3a1d...` | PASS |

Both complete hashes were recomputed from the supplied model files during FINAL-GPU1 preflight v5 and are retained in the machine-readable preflight and release-qualification JSON records. The shortened display above keeps the PDF table within its intended page width without weakening the content-addressed identity check.

# Runtime state

The fresh development-host CUEQ-DEP1 record reports:

- PyTorch `2.10.0+cpu`;
- MACE `0.3.16`;
- e3nn `0.4.4`;
- no CUDA device inventory;
- no CuEq core import;
- no CuEq Torch frontend import; and
- no CuEq CUDA-ops import.

The resulting CUEQ-DEP1 blockers are `cueq-core_import`, `cueq-torch_import`, `cueq-ops_import`, `torch_cuda_available`, and `cuda_device_inventory`.

# PERF-CERT1 deferred state

PHASE1 and PHASE2 deferred records were regenerated from the **same** fresh CUEQ-DEP1 runtime digest before building PERF-CERT1. This cross-gate runtime binding is mandatory; archived deferred records from different captures are not interchangeable.

The PERF-CERT1 record correctly reports these blockers:

- `authoritative_e3nn_baseline_missing`;
- `accelerated_profile_evidence_missing`; and
- `CUEQ_PHASE1_TRAINING_QUALIFICATION`.

No profile recommendation is made and `generated_default_change_authorized` remains false.

# FINAL-GPU1 v5 handoff

FINAL-GPU1 preflight schema `mdstats.mlff-final-gpu1.preflight.2026-08.v5` verifies both locked foundations and embeds independent states for:

1. CUEQ-DEP1 runtime freeze;
2. CUEQ-PHASE1 training-only qualification;
3. optional CUEQ-PHASE2 selected-head source/DATA6 qualification; and
4. PERF-CERT1 end-to-end certification.

The preflight state is `deferred_not_executed`. Its remaining host-level blockers are `torch_cuda_available` and `cueq_dep1_runtime_freeze`.

# Regression evidence

The gate-specific PERF-CERT1 unit suite passes 7/7. The synchronized PERF-CERT1 specification suite passes 2/2. Adjacent CUEQ/FINAL-GPU code tests pass 21 with one expected supplied-model skip in the unconfigured run; the real supplied foundation identity test passes separately. PERF-P5/VRAM-P4 adjacent code tests pass 15 with one expected supplied-model skip in the unconfigured run; the real supplied MH-1/MPA-0 prepared/direct batch comparison also passes separately. The synchronization/specification slices for CUEQ-DEP1, PHASE1, PHASE2, FINAL-GPU1, PERF-P5, and VRAM1/PERF-P4 all pass.

# Authorization boundary

This development-host evidence authorizes the PERF-CERT1 **control plane only**. It does not authorize:

- a positive CuEq runtime claim;
- pure-CuEq training;
- selected-head CuEq source/DATA6 execution;
- any accelerator speedup claim;
- a PERF-CERT1 production recommendation; or
- a generated-default change.

Those positive decisions remain reserved for the single consolidated FINAL-GPU1 workstation campaign.
