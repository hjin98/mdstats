---
title: "MLFF Architecture Revision 54"
subtitle: "PERF-P5 TRAIN2/EVAL2 persistence and reuse hardening"
author: "mdstats development"
date: "2026-08-15"
geometry: margin=0.8in
fontsize: 10pt
header-includes:
  - |
    \usepackage{microtype}
---

# Revision 54

Revision 54 closes the CPU/control-plane portion of **PERF-P5** without changing scientific authority. The release is `mdstats 0.20.187a0`; dependency-graph schema 36 is synchronized with this manual revision.

## TRAIN2/STOR2 persistence

TRAIN2 live/EMA-state hashing and STOR2 evaluation-capsule hashing retain the existing canonical metadata and contiguous tensor-byte sequence. The implementation now feeds those bytes to SHA-256 through bounded `memoryview` chunks instead of creating an additional full-size `bytes` object through `numpy().tobytes()` solely for hashing.

For a state sequence $T=(t_1,\ldots,t_n)$, the authority remains

$$
H=\operatorname{SHA256}\!\left(S\Vert\big\Vert_i[D_i\Vert Q_i\Vert B_i]\right),
$$

with unchanged schema marker $S$, dtype metadata $D_i$, shape metadata $Q_i$, and canonical tensor bytes $B_i$.

TRAIN2 additionally writes execution-only `train2_persistence.jsonl` records that separate clone, tensor-hash, raw-checkpoint-hash, continuation-write, summary-write, and total persistence costs. Continuation state is unchanged.

## EVAL2 compatible-model reload

A candidate-only, unaccelerated, uncompiled MACE shell may opt into strict compatible-state reload. The path fails closed unless model class, complete state-key set, tensor shapes and tensor dtypes match exactly; state application is strict. Source-foundation-bound, CuEq/OEq, and compiled providers do not use this path. Fresh model construction remains the default.

The supplied MH-1 CPU/e3nn comparison is prediction-exact but the reload path is 6.49% slower than fresh construction on this host. It is therefore not promoted as a CPU default. Any accelerator benefit must be established in FINAL-GPU1.

## Measured CPU result

On a 256 MB contiguous FP32 state, two fresh-process samples per path show:

| Authority | Pre-P5 median | PERF-P5 median | Change | Extra RSS before | Extra RSS after |
|---|---:|---:|---:|---:|---:|
| TRAIN2 state digest | 265.02 ms | 142.97 ms | 46.05% lower | 245.00 MiB | 0.75 MiB |
| STOR2 capsule digest | 248.19 ms | 146.87 ms | 40.82% lower | 244.94 MiB | 0.81 MiB |

Old and new digests are byte-identical in both cases.

## Dataset-format boundary

No HDF5/LMDB conversion is introduced. Those formats remain MACE dataset-storage mechanisms; they are not represented as authenticated reusable `AtomicData` graph caches. Existing DATA8 fixed-file reuse and DATA6/EVAL2 graph/prediction caches remain authoritative.

## Roadmap

All remaining accelerator-dependent evidence is held for the one-shot **FINAL-GPU1** package. CUEQ-DEP1, the CuEq phase gates, E3NN-BASELINE, accelerator-side PERF-P5 comparison, and PERF-CERT1 therefore remain final-release obligations rather than intermediate development interruptions.

# References

- Python Software Foundation, *Built-in Types - Memory Views*, Python 3 documentation: <https://docs.python.org/3/library/stdtypes.html#memory-views>.
- PyTorch, *Saving and Loading Models* and `torch.nn.Module.load_state_dict`: <https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html>; <https://docs.pytorch.org/docs/stable/generated/torch.nn.Module.html#torch.nn.Module.load_state_dict>.
- MACE documentation, *Heterogeneous Data Training* and *Large Dataset Pre-processing*: <https://mace-docs.readthedocs.io/en/latest/guide/heterogeneous_data.html>; <https://mace-docs.readthedocs.io/en/latest/guide/multipreprocessing.html>.
