---
title: "mdstats FINAL-GPU1 Workstation Qualification Runbook"
author: "mdstats development"
date: "2026-08-22"
geometry: margin=0.8in
fontsize: 10pt
---

# CURRENT TARGET-SIZE-v5 HANDOFF

This runbook describes the current one-shot FINAL-GPU1 handoff for the target-size-v5 software generation. It is intentionally independent of the retired SIZE-FIDELITY2/MVMIGRATE1 activation workflow. Target-size v5 is already the production architecture; FINAL-GPU1 qualifies accelerator execution and release performance only.

# 1. Inputs

Prepare one workstation directory containing:

- the exact release source archive being qualified;
- the locked `mace-mh-1.model` and `mace-mpa-0-medium.model` files;
- the target/replay data required by the release-matched campaign;
- the project offline dependency bundle; and
- a writable qualification root.

Do not replace either foundation model. The tool verifies both model SHA-256 identities against the locked `mdstats` constants.

# 2. Runtime prerequisite

Activate the CUDA environment intended to authorize the release. It must contain the release-matched MACE/e3nn stack plus the CuEquivariance core, Torch frontend, and CUDA operations package appropriate to the installed PyTorch/CUDA runtime.

Missing accelerator capability is a failed/deferred runtime, not permission to alter scientific settings or silently fall back inside the same qualification record.

# 3. Verify and unpack the release

Verify the source archive with the checksum manifest supplied with the final bundle, then unpack it without editing source. The exact archive SHA-256 is part of every handoff registration.

Example:

```bash
sha256sum -c VERIFY_BUNDLE_SHA256.txt
mkdir -p work/source
unzip -q <release-archive.zip> -d work/source
cd work/source/<release-directory>
```

# 4. Preflight

```bash
python tools/run_mlff_final_gpu_qualification.py preflight \
  --mh1-model ../../../inputs/mace-mh-1.model \
  --mpa0-model ../../../inputs/mace-mpa-0-medium.model \
  --release-archive ../../../<release-archive.zip> \
  --output ../../../final-gpu1/preflight.json
```

The current preflight is the target-size-v5 **v11** contract. A `ready_for_final_gpu_execution` result requires the locked models, a readable release archive, CUDA availability, and a positive CUEQ-DEP1 runtime freeze.

# 5. Initialize one immutable handoff root

```bash
python tools/run_mlff_final_gpu_qualification.py init \
  --root ../../../final-gpu1/run-001 \
  --mh1-model ../../../inputs/mace-mh-1.model \
  --mpa0-model ../../../inputs/mace-mpa-0-medium.model \
  --release-archive ../../../<release-archive.zip>
```

The current policy creates a 16-item matrix: 8 `must_pass`, 6 `measure_only`, and 2 `optional` gates. Do not re-run `init` on a populated root. Replacement evidence belongs in a new run root.

# 6. Capture CUEQ-DEP1 once

```bash
mkdir -p ../../../final-gpu1/run-001/raw
python tools/capture_mlff_cueq_dep1_runtime.py \
  --supplied-artifact ../../../inputs/mace-mh-1.model \
  --supplied-artifact ../../../inputs/mace-mpa-0-medium.model \
  --output ../../../final-gpu1/run-001/raw/cueq_dep1_runtime.json

python tools/run_mlff_final_gpu_qualification.py record \
  --root ../../../final-gpu1/run-001 \
  --gate CUEQ_DEP1_RUNTIME_FREEZE \
  --evidence ../../../final-gpu1/run-001/raw/cueq_dep1_runtime.json \
  --disposition auto
```

All runtime-bound evidence must authenticate to this exact runtime digest.

# 7. Execute the current matrix

## 7.1 Must-pass gates

| Gate ID | Required evidence |
|---|---|
| `CUEQ_DEP1_RUNTIME_FREEZE` | positive release-authorizing CuEq/CUDA runtime freeze |
| `E3NN_BASELINE_COMPLETE_CAMPAIGN` | complete optimized e3nn production-representative baseline |
| `SIZE_FIDELITY1_EXHAUSTIVE_CALIBRATION` | release qualification of the current size-screen calibration policy |
| `PERF_P2R_WHOLE_FUNNEL_GPU_PERFORMANCE` | whole-funnel GPU/control-plane performance with restart/decision equivalence |
| `VRAM1_PERF_P4_ACCELERATOR_MEMORY_THROUGHPUT` | VRAM/headroom/OOM/backoff and bounded-pipeline throughput evidence |
| `CUEQ_PHASE1_TRAINING_ONLY_QUALIFICATION` | paired e3nn/CuEq training qualification on one frozen runtime |
| `REPLAY_UNIFY1_GPU_PSEUDOLABEL_EXECUTION` | release-authoritative replay pseudolabel execution and cache/restart evidence |
| `PERF_CERT1_END_TO_END_CERTIFICATION` | end-to-end certification against the authoritative e3nn baseline |

## 7.2 Measure-only gates

Register evidence for:

- `PREC3_REAL_CUEQ_ACTIVATION`
- `MH1_ACCEL1_CUEQ_NUMERICAL_PARITY`
- `MH1_DATA6_1_CUEQ_DESCRIPTOR_SELECTION_PARITY`
- `MH1_TRAIN1_CUEQ_TRAINING_REALIZATION`
- `MH1_CERT1_GENERATED_DEFAULT_CUEQ_MATRIX`
- `PERF_P5_ACCELERATOR_PERSISTENCE_REUSE`

These measurements must be complete even if a particular optimization remains disabled.

## 7.3 Optional gates

- `CUEQ_PHASE2_SELECTED_HEAD_SOURCE_EXECUTION_OPTIONAL`
- `MH1_DEPLOY1_MLIAP_EXPORT_AND_LAMMPS_RUN0`

# 8. Run the scientific campaign normally

Use the normal staged CLI. Do not bypass target-size selection or held-out boundaries:

```bash
python tools/mdstats-mlff-campaign.py --config <frozen-campaign.toml> doctor
python tools/mdstats-mlff-campaign.py --config <frozen-campaign.toml> prepare
python tools/mdstats-mlff-campaign.py --config <frozen-campaign.toml> preflight
python tools/mdstats-mlff-campaign.py --config <frozen-campaign.toml> train
python tools/mdstats-mlff-campaign.py --config <frozen-campaign.toml> evaluate
python tools/mdstats-mlff-campaign.py --config <frozen-campaign.toml> verify
```

The campaign itself owns the fixed-eight target-size path:

```text
REPAIR2 -> MVQUAL2 -> Q -> epoch 3 -> epoch 10 -> epoch 30
        -> selected_target_size -> selected REPAIR2 prefix
        -> held-out CV/EVAL/VERIFY
```

FINAL-GPU1 must not create rescue sizes, migrate old target ladders, or alter a selected target size.

# 9. Register evidence

For every matrix item, use the handoff tool rather than editing the manifest:

```bash
python tools/run_mlff_final_gpu_qualification.py record \
  --root ../../../final-gpu1/run-001 \
  --gate <GATE_ID> \
  --evidence ../../../final-gpu1/run-001/raw/<evidence.json> \
  --disposition auto
```

The registration binds the evidence bytes, schema/content digest where available, release archive, and CuEq runtime digest where required.

# 10. Verify integrity before reduction

```bash
python tools/run_mlff_final_gpu_qualification.py verify \
  --root ../../../final-gpu1/run-001
```

Any source/model/evidence mutation, policy/matrix drift, path escape, missing runtime binding, or inconsistent producer status fails closed.

# 11. Reduce FINAL-GPU1

```bash
python tools/run_mlff_final_gpu_qualification.py reduce \
  --root ../../../final-gpu1/run-001 \
  --runtime ../../../final-gpu1/run-001/raw/cueq_dep1_runtime.json \
  --perf-cert1 ../../../final-gpu1/run-001/raw/perf_cert1_qualification.json \
  --output ../../../final-gpu1/run-001/FINAL_GPU1_QUALIFICATION.json
```

A positive record requires every must-pass gate to pass, every measure-only gate to be complete, handoff integrity to pass, and all runtime/release/model identities to agree.

A pass may recommend an accelerator profile but does not directly change generated defaults. The handoff record keeps generated-default authorization false.

# 12. Retired target-size migration workflow

Do **not** run SIZE-FIDELITY2, MVMIGRATE1 learning controls, or a target-data migration activation command. Those belonged to historical campaign generations and are not prerequisites for target-size v5. Current campaigns reject obsolete derived migration/rescue state and rebuild the target-size authority from authenticated REPAIR2/MVQUAL2 state.
