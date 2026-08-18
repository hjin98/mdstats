---
title: "CUEQ-DEFAULT1 generated TRAIN2 CuEq default policy"
author: "mdstats development"
date: "2026-08-16"
geometry: margin=0.75in
fontsize: 10pt
---

# CUEQ-DEFAULT1 - generated TRAIN2 CuEq default policy

## Purpose

CUEQ-DEFAULT1 changes only the generated policy for new MLFF campaigns. The authoritative source-foundation path remains e3nn, while TRAIN2 defaults to the portable pure-CuEq training implementation.

## Required generated configuration

A plain `mdstats-mlff-campaign init` SHALL emit:

```toml
[acceleration]
backend = "e3nn"
training_backend = "cueq"
only_cueq = false
require_available = true
```

`backend` governs source inference, DATA6, pseudolabel generation, checkpoint evaluation, and verification. `training_backend` governs DATA8/TRAIN2 optimizer realization only.

## Compatibility

Historical campaign TOML without `training_backend` SHALL retain the old unified-backend interpretation: TRAIN2 inherits `backend`. Existing campaign files are never rewritten automatically.

## Qualification and failure behavior

`doctor` SHALL qualify the source and training realizations independently. CuEq TRAIN2 qualification SHALL bind the exact selected-head training checkpoint and pure-CuEq parity evidence through `TrainingAccelerationRealizationRecord.v1`. The record SHALL NOT authorize CuEq source inference or DATA6. If the requested CuEq runtime or parity is unavailable and `require_available=true`, doctor SHALL fail; silent fallback is forbidden.

## Runtime binding

DATA8 optimizer identity SHALL use the training policy and training realization digest. DATA6/source inference and post-training evaluation SHALL continue to use the source policy and source realization. Preflight SHALL verify the training-side CuEq flags and evaluate the resulting portable checkpoint under the source policy.

## Evidence scope

This policy migration is explicit and prospective. It does not modify historical CUEQ-PHASE1, PERF-CERT1, or FINAL-GPU1 records and does not assert positive GPU performance evidence.
