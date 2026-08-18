---
title: "mdstats MLFF Architecture Revision 60"
author: "mdstats development"
date: "2026-08-16"
geometry: margin=0.8in
fontsize: 10pt
---

# Revision 60 - CUEQ-DEFAULT1 training-default policy migration

**Release:** `mdstats 0.20.193a0`  
**Dependency-graph schema:** 42  
**Gate:** CUEQ-DEFAULT1  
**Development-host accelerator result:** not claimed

Revision 60 performs the explicit generated-policy change that earlier CUEQ-PHASE1/PERF-CERT1/FINAL-GPU1 authorities deliberately left outside their scope. Newly initialized campaigns now use authoritative e3nn for source-foundation inference, DATA6, pseudolabel generation, checkpoint evaluation, and verification, while TRAIN2 defaults to pure CuEq. Saved training checkpoints remain portable e3nn artifacts because `only_cueq=false`.

## Phase-separated configuration

New campaign TOML freezes `backend = "e3nn"` for the source side and `training_backend = "cueq"` for TRAIN2. Historical campaign files without `training_backend` retain the exact legacy unified-backend interpretation; they are not silently migrated. Users may explicitly request `--training-backend e3nn` for reference runs or change the source backend separately.

## Independent realization authority

`TrainingAccelerationRealizationRecord.v1` binds the exact selected-head training checkpoint, backend, pure training kernel, device/dtype, MACE/CuEq runtime identity, and training parity evidence. It intentionally contains no source-foundation inference authority. `doctor` freezes source and training realizations independently. A missing CuEq stack or failed pure-CuEq training-foundation parity makes the generated default fail closed rather than falling back to e3nn.

DATA8 and TRAIN2 optimizer identity consume the training realization. DATA6, source-foundation caches, checkpoint evaluation, and deployment/physical verification continue to consume the source realization. The one-epoch production preflight verifies CuEq training activation and then evaluates the resulting portable checkpoint through the source/e3nn path.

## Evidence boundary

This is an explicit project policy revision, not a fabricated accelerator certification. CUEQ-PHASE1, PERF-CERT1, and FINAL-GPU1 records keep their original semantics and immutable `generated_default_change_authorized=false` fields. Revision 60 changes only the generated policy for new campaigns; positive CUDA/CuEq performance evidence remains a separate workstation qualification concern.
