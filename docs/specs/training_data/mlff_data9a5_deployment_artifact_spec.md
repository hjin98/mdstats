---
title: "MLFF-DATA9A5 Deployment-Artifact Closure"
version: "0.20.43a0"
status: "implemented; real MACE artifact smoke pending supplied runtime materials"
date: "2026-07-29"
---

# MLFF-DATA9A5 deployment-artifact closure

## 1. Purpose

This closure defines the boundary between an mdstats-controlled fine-tuned MACE
model and any downstream runtime that consumes it. mdstats owns the serialized
model artifact, its requested floating-point dtype, its immutable provenance,
and model-level reload validation. The downstream runtime owns its internal
mixed precision, reductions, neighbor construction, integration, accelerator
kernels, and thermodynamic bookkeeping.

The closure deliberately does not add a LAMMPS implementation stage. LAMMPS is
a downstream consumer of the selected FP32 or FP64 model. mdstats does not audit
or reproduce LAMMPS, ML-IAP, Kokkos, LibTorch, or accelerator precision
semantics.

## 2. Inputs and outputs

The exporter consumes:

- one complete or target-head MACE model serialized with `torch.save`;
- the requested deployment dtype, `float32` or `float64`;
- the source training dtype, explicitly supplied or conservatively inferred
  from a uniform source model;
- an optional precision-transition digest from DATA9A4;
- an optional target-head name;
- a model-specific inference probe, required by the default policy.

It emits:

- one digest-recorded serialized deployment model;
- one canonical JSON manifest;
- one immutable `MaceDeploymentArtifact` runtime record.

The deployment filename is consumer-neutral. No filename or manifest field
claims a particular LAMMPS execution mode.

## 3. Precision semantics

The source and exported models must each have one uniform floating dtype across
all floating parameters and buffers. Mixed floating state fails closed.

Three conversions are supported:

1. `float32 -> float32`: identity export;
2. `float64 -> float64`: identity export;
3. `float64 -> float32`: explicit precision demotion;
4. `float32 -> float64`: explicit storage and execution promotion.

A float32-to-float64 promotion does not restore information already lost during
FP32 training or prior FP32 execution. Every promotion manifest therefore
contains the note:

```text
float32_to_float64_promotion_does_not_restore_lost_precision
```

The artifact always records `precision_recovery_claimed = false`.

## 4. Deterministic conversion and exact state validation

The first implementation uses the ordinary complete-model `torch.save` format
expected by the qualified MACE Python path. PyTorch full-model pickle bytes may
contain process-specific storage identifiers, so mdstats does not claim that two
independent reload/export cycles are byte-identical. Every emitted file is still
hashed exactly. Determinism is defined at the model-state and inference levels,
not at the opaque pickle-container byte level.

The exporter hashes:

- source model bytes;
- output model bytes;
- source state semantics: tensor names, dtypes, shapes, and exact CPU bytes;
- deployed state semantics using the same canonical procedure.

After reload, every floating state tensor must exactly equal the source tensor
converted by PyTorch to the requested dtype. Every non-floating tensor must be
bitwise unchanged. Missing, additional, reshaped, or differently typed state
entries fail closed.

The source model is hashed before and after export and may not change.

## 5. Reloaded inference validation

The default `MaceDeploymentExportPolicy` requires a caller-supplied inference
probe. The probe is run on:

- the unmodified source model;
- the reloaded deployment model.

Numeric tensors, arrays, mappings, sequences, and scalars are flattened into a
stable named output set. The probe runs with autograd enabled so MACE energy,
force, virial, and stress paths can be evaluated. Output structures and shapes
must match, and all values must be finite.

When either model uses FP32, comparison uses the policy's FP32 tolerances:

```text
rtol = 1e-5
atol = 1e-6
```

For a pure FP64 identity path, comparison uses:

```text
rtol = 1e-10
atol = 1e-10
```

Each output records maximum absolute error, RMSE, maximum reference magnitude,
and pass/fail status. A failed required probe prevents model and manifest
publication.

A structural-only policy may explicitly disable the required probe, but such an
artifact records `inference_qualified = false`. Production deployment should use
the default required-probe policy.

## 6. Immutable manifest

The canonical manifest records at least:

- exporter and PyTorch versions;
- explicit `byte_determinism_claimed = false`;
- source path and byte digest;
- source training dtype;
- observed source precision inventory;
- requested deployment dtype;
- conversion kind;
- optional DATA9A4 transition digest;
- optional target-head name;
- output model path and byte digest;
- observed deployed precision inventory;
- source and deployed semantic state digests;
- exact state-conversion result;
- inference-comparison evidence;
- downstream-runtime precision claim, safety-locked to false;
- notes and record content digest.

Manifest serialization uses canonical sorted JSON and rejects content-digest
tampering.

## 7. Downstream boundary

The artifact establishes only that the serialized model passed to a consumer is
uniformly FP32 or FP64 and corresponds exactly to the requested conversion.
The downstream runtime owns and documents:

- whether model tensors are converted again at load time;
- accumulation and reduction precision;
- virial and stress implementation;
- integrator-state precision;
- TF32 or other accelerator modes;
- CPU/GPU numerical agreement;
- stability and performance of downstream MD.

mdstats neither assumes nor guarantees those behaviors. Selecting the FP32 or
FP64 model is the complete mdstats-side port.

## 8. Acceptance requirements

The closure is accepted when:

1. FP32 and FP64 deployment artifacts are independently selectable;
2. source and output floating state are uniform and verified;
3. exact state conversion survives serialization and reload;
4. model and state digests are recorded;
5. repeated export has identical semantic state digests and inference evidence;
6. the source artifact is not modified;
7. a required inference probe passes dtype-appropriate tolerances;
8. promotion is distinguished from precision recovery;
9. manifests round-trip and reject tampering;
10. downstream runtime precision cannot be claimed by the artifact;
11. documentation removes any planned mdstats implementation of LAMMPS
    internals.

This closure does not complete the production DATA6-DATA8 realization. After
closure, production DATA6-DATA8 realization is next, followed by DATA9B
protocol-matched execution and freeze.
