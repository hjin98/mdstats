# mdstats 0.20.144a0 — PAR-DENS5 optional GPU density backend

**Date:** 2026-08-10  
**Gate:** PAR-DENS5  
**Base:** mdstats 0.20.143a0

## Summary

This release implements the optional GPU execution gate for atomic/framework density preparation while preserving the PAR-DENS0--PAR-DENS4 CPU path as the scientific reference. GPU execution is an execution backend only: grid resolution, CIC semantics, Gaussian/operator identity, sparse support, HDR definition, field identities, and scientific planning authority do not depend on whether a kernel executes on CPU or CUDA.

## GPU resource policy

- CUDA discovery is runtime-optional through an already-available PyTorch installation; mdstats gains no hard Torch/CuPy dependency.
- Automatic GPU admission uses **80% of currently free VRAM**, not 80% of total board memory.
- Host staging remains bounded by the active PAR-DENS2 host-memory authority.
- Only one major scheduled density field may own a CUDA device at once; that field may batch many FFT/support tiles internally.
- Automatic selection prices setup and host/device transfer in addition to predicted compute time. A visible GPU is not sufficient for admission.
- `MDSTATS_DENSITY_GPU=auto` is the default; `off` forces the CPU reference; `force` requests CUDA but cannot override VRAM/host-memory limits.
- CUDA disappearance, allocation/kernel failure, insufficient VRAM, a busy major-job GPU, or an unfavorable cost estimate all fall back to CPU rather than making an otherwise valid density calculation fail.

## Accelerated kernels

The initial FP64 CUDA backend covers:

- dense CIC deposition using sorted destination indices and FP64 segmented reduction;
- canonical/dense periodic Gaussian convolution and legacy spectral filtering;
- exact binary support-mask FFT dilation with the existing integer-roundoff certificate;
- sufficiently large hybrid sparse/tiled FFT convolutions.

Grouped target-owned direct sparse accumulation remains on the qualified CPU path in PAR-DENS5. Its packed irregular traffic and frequent host/device exchange are not promoted to CUDA without measured benefit and a deterministic reduction design.

## Precision and provenance

All CUDA inputs, transforms, reductions, and returned fields use FP64. FP32/mixed density accumulation is not authorized. GPU decision/report metadata records device identity, free/usable VRAM snapshot, predicted CPU/GPU cost, transfer bytes, required VRAM, selection/fallback reasons, and bounded decision exemplars. These execution details are not part of scientific field/content identity.

## Qualification

The supplied 300 K Na-LTA MLFF trajectory remains bound by SHA-256 `81c86cc40f5a11031f80817213eb558c02348494d1c6cad9b4775a5bc3c9f9cd` (10,001 frames, 168 atoms). A bounded stride-100 101-frame Na/Si/O, 64^3 local-sparse workload was run with GPU explicitly disabled and with automatic GPU selection. The packaging host exposes no CUDA runtime, so `auto` correctly records `cuda_unavailable` and uses the CPU path. The two runs are bit-identical for packed density values (`max |Δρ| = 0`), integrated populations, field content identities, and 50/80/95% HDR thresholds.

Real-CUDA FP64 equivalence tests for circular FFT convolution and CIC deposition are included and run automatically on CUDA-capable test hosts; they are skipped on the packaging host because CUDA is unavailable. No GPU speedup is claimed from this host. PAR-DENS6 remains responsible for 100/1,000/10,000+ frame CPU/GPU performance qualification and production auto-tuning.
