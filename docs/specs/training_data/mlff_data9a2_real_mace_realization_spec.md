---
title: "MLFF-DATA9A2: Real MACE Configuration Realization and Execution Smoke"
version: "0.20.39a0"
status: "implemented"
---

# MLFF-DATA9A2: real MACE configuration realization and execution smoke

## 1. Purpose and stage boundary

MLFF-DATA9A2 closes the executable-compatibility gap between the deterministic
DATA8 artifact bundle and `mace-torch==0.3.16`. It proves that every selected
DATA8 job can be parsed by the locked MACE parser, loaded by the real training
entry point, trained for a minimal CPU epoch, enumerated by head, reduced to the
target head, and evaluated back to finite extended-XYZ predictions.

DATA9A2 is an integration qualification stage. It does not select a production
checkpoint, compare scientific candidates, calibrate uncertainty, or expose
locked-test labels. Those operations remain owned by DATA9B and later stages.
A DATA9A2 smoke checkpoint is disposable execution evidence, not a model
candidate.

## 2. Locked runtime contract

The first implementation is locked to `mace-torch==0.3.16`. A configuration is
accepted only when the installed runtime is already represented by a passing
`MaceRuntimeEnvironmentRecord` and the DATA8 job/config digests match the files
being executed.

MACE v0.3.16 applies `ast.literal_eval` or equivalent string processing to
several command-line values. Therefore the following YAML values are scalar
strings containing deterministic Python literals, not native YAML containers:

| Field | Required DATA8 representation | Realized value |
|---|---|---|
| `atomic_numbers` | YAML scalar string | sorted list of atomic numbers |
| `heads` | YAML scalar string | ordered head-definition mapping |
| `heads.<name>.atomic_numbers` | nested scalar string | head-local atomic-number list when narrower than the global union |
| `heads.<name>.E0s` | YAML scalar string | `"foundation"` or atomic-energy mapping |
| `loss` | lowercase scalar | `universal` |

The adapter must reject source-compatible-looking configurations that fail the
real parser or loader dry run.

For fixed-file multi-head replay, `target_head.atomic_numbers` must be the
target-only element set. MACE 0.3.16 otherwise applies the top-level
target/replay union to the target head and requires explicit target E0s for
replay-only species. Realization checks E0 coverage against each head's own
element table and fails before training if the mapping is incomplete.

## 3. Fixed-file target/replay weight realization

DATA8 supplies already-selected fixed target and replay files. For this path,
head exposure weights are realized in the extended-XYZ configuration weights:

\[
 w_i^{\mathrm{realized}} =
 w_i^{\mathrm{base}}\,s_h,
\]

where `s_h` is `target_weight` for target training structures and `head_weight`
for replay training structures. Monitor, validation, fold-evaluation, and
locked-test files are never reweighted.

Each target sidecar records:

- `base_configuration_weight`;
- `configuration_weight_scale`;
- realized `configuration_weight` (the MACE extended-XYZ `config_weight`).

Replay training files are staged through an ASE round trip and receive the same
multiplicative realization. DATA8 must not emit the unsupported v0.3.16 options
`weight_pt` or `weight_ft`. The MACE option `weight_pt_head` belongs to MACE's
automatic replay-sampling path and does not own mdstats' preselected fixed-file
replay contract.

## 4. Configuration-realization record

`MaceConfigRealizationRecord` is immutable evidence for one DATA8 job. It binds:

- the qualified environment digest;
- the DATA8 job digest and exact configuration SHA-256;
- the realization-policy digest;
- a real `build_default_arg_parser` invocation;
- a real `mace_run_train --dry_run` invocation when enabled;
- parsed job name, loss, atomic numbers, head names, and E0 atomic numbers;
- command return codes, executable paths, stream hashes, and bounded tails.

The record passes only when:

1. the runtime is qualified and reports MACE 0.3.16;
2. the DATA8 configuration checksum is unchanged;
3. the real parser exits successfully;
4. parsed atomic numbers are sorted and unique;
5. parsed E0 elements are contained in the model element set;
6. parsed loss is `universal`;
7. the real loader dry run succeeds when requested.

## 5. Execution-smoke record

`MaceJobExecutionSmokeRecord` executes a disposable, bounded training job and
records:

- one-epoch CPU training command and result;
- all produced model and checkpoint files with SHA-256 hashes;
- real `mace_select_head --list_heads` output;
- target-head extraction and extracted-model hash;
- real `mace_eval_configs` output and prediction-file hash;
- evaluated configuration count;
- finiteness of MACE energy, force, and stress fields.

Head parsing is restricted to the indented block printed after
`Available heads:` on standard output. Warnings on standard error cannot become
head names.

The execution smoke passes only when training succeeds, at least one model and
checkpoint are produced, expected head operations succeed, and the evaluation
round trip contains finite fields for every evaluated configuration.

## 6. Determinism and resource containment

Both policies carry an explicit positive thread count and timeout. Child
processes receive identical values for `OMP_NUM_THREADS`, `MKL_NUM_THREADS`,
`OPENBLAS_NUM_THREADS`, and `NUMEXPR_NUM_THREADS`. The executable directory and
qualified inherited Python paths are derived from the runtime record.

The records capture content hashes rather than treating logs or filenames as
proof. Absolute smoke-output locations are audit metadata; model, checkpoint,
and prediction identity is established by relative path plus SHA-256.

Some MACE commands can finish their scientific work while an imported runtime
component keeps the process or inherited stream handles alive during shutdown.
The adapter may terminate that lingering process group only after observing a
stable, independently validated completion sentinel: parser JSON, the canonical
dry-run completion message, or non-empty output artifacts whose size and
modification time remain stable across repeated polls. Sentinel intervention is
recorded in command evidence, does not replace downstream checksum/content
validation, and cannot convert absent or malformed artifacts into success.

## 7. Failure behavior

The stage fails closed for:

- a runtime, job, or checksum lineage mismatch;
- an unavailable CLI executable;
- parser, loader, training, extraction, or evaluation failure;
- timeout;
- absent expected artifacts;
- malformed head enumeration;
- non-finite predictions;
- incompatible record deserialization or digest mismatch.

No compatibility stub, skipped command, or synthetic success marker satisfies
the gate.

## 8. Acceptance criteria

DATA9A2 is accepted when focused tests demonstrate all of the following:

1. native DATA8 replay and naive configurations use the scalar-literal schema;
2. fixed-file target/replay weights are realized exactly once;
3. both configurations pass the genuine MACE parser and loader dry run;
4. a real two-head one-epoch replay job produces checkpoints and models;
5. `pt_head` and `target_head` are enumerated without warning contamination;
6. `target_head` extraction succeeds;
7. real evaluation writes finite energy, force, and stress fields;
8. policy and record serialization round trips preserve content digests;
9. a real Na-LTA VASP frame and the supplied MPA-0 checkpoint remain readable
   through the mdstats/MACE adapter.

Completion of DATA9A2 does not close the full DATA9A production gate. The final
DATA9A gate additionally requires production-scale qualification of all intended
LTA trajectories, resource envelopes, role feasibility, coverage, and artifact
sizes before DATA9B execution begins.


## Precision realization extension

The parser probe SHALL capture `default_dtype` and reject disagreement with the
DATA8 optimizer policy before any training process starts. The execution smoke
SHALL use the protocol value; an explicit smoke-policy override may only repeat
that value.

After training, mdstats SHALL inspect every floating parameter and buffer in the
foundation, final trained, and extracted target-head artifacts. A passing smoke
requires uniform `float32` or uniform `float64` state matching the protocol.
Mixed state, a model-load failure, or a requested-dtype mismatch fails closed.
For a single-head model whose sole head is `target_head`, the trained artifact is
itself the extracted target model; MACE 0.3.16's removal command need not and
must not be invoked.
