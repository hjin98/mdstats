---
title: "MLFF PERF-P3 CPU Structural and Reduction Hardening Specification"
version: "0.20.185a0"
date: "2026-08-15"
status: "CPU-qualified; accelerator qualification remains deferred to FINAL-GPU1"
geometry: margin=0.85in
---

# Purpose

PERF-P3 removes avoidable CPU allocation, wrapper, and nested-thread overhead from DATA6 structural selection and FOUNDATION-AUDIT1 without changing scientific features, selection rules, quantiles, target membership, or model evidence. It is an **Authority Class E** gate: execution may change; scientific bytes and decisions may not.

# P3-1: direct local-structure frame kernel

The public `compute_local_structure_features()` API remains the validated user-facing entry point. High-throughput DATA6 may instead invoke an internal array kernel with atomic numbers, fractional positions, cell/PBC, an immutable topology workspace, and worker-local scratch.

The direct path must preserve the public-path operation order and output bytes. The current qualified topology workspace caches immutable chemistry/topology arrays: covalent radii, species indicators, pair radii, center indices, upper-triangle indices, and fallback-radius metadata. It is execution-only.

# P3-2: bounded worker-local scratch

Only wrapped fractional-coordinate scratch is retained by the qualified implementation. Larger persistent pair/radial scratch was measured and rejected because it increased resident memory and reduced throughput on the bounded LTA-like workload.

A proposed chunked radial evaluation was also rejected: it changed FP64 radial values by approximately $10^{{-16}}$ to $8.9\times10^{{-16}}$. Those differences are small numerically but unacceptable for a Class-E gate because they would change scientific byte identity.

The existing shared pair-geometry computation remains authoritative. PERF-P3 does not replace the dense structural definition with a sparse cutoff approximation.

# P3-3: exact FOUNDATION-AUDIT1 temporary arrays

For a domain with $N$ atoms, exact force-tail reduction allocates one vector-error array of length $N$ and one component-absolute-error array of length $3N$ and fills them by deterministic cursors. This removes list accumulation followed by a second concatenated copy.

If the requested temporary allocation exceeds the execution-only RAM threshold, the same dtype, shape, order, and fill order are realized through temporary `numpy.memmap` storage. NumPy defines `memmap` as an array-like view over a binary file; this mechanism changes storage realization, not the scientific reduction.[^numpy-memmap]

The mmap directory, threshold, and file names are execution-only. Normal completion flushes and removes temporary mappings. Exact audit digests must equal the in-memory path.

# P3-4: unified stage resource scope

Each stage declares one CPU budget. Python concurrency, structural workers, cKDTree native workers, BLAS/OpenMP threads, and PyTorch CPU workers may not independently multiply beyond that budget. The conservative admission estimate is

$$
T_{\mathrm{est}}
=
W_{\mathrm{py}}
\max\!\left(
W_{\mathrm{struct}}T_{\mathrm{BLAS}},
W_{\mathrm{tree}},
W_{\mathrm{torch}},
1
\right)
\le T_{\mathrm{budget}}.
$$

`StageResourceScope` validates this bound before execution. `threadpoolctl.threadpool_limits()` is used where practical to bound supported BLAS/OpenMP thread pools; the project documents the library's own limitation that runtime limits should be applied from a consistent controlling Python thread.[^threadpoolctl]

Resource counts and thread-pool state are telemetry only and may not enter scientific digests.

# P3-5: campaign integration

DATA6 structural selection builds one immutable topology workspace per fixed-topology run and one worker-local coordinate scratch object. TARGET-DATA2B cKDTree work runs inside an explicit stage resource scope. FOUNDATION-AUDIT1 accepts `performance.foundation_audit_temporary_ram_mib`; generated configuration defaults to 512 MiB and rejects nonpositive values.

# Acceptance

PERF-P3 CPU qualification requires:

1. bitwise equality between public and direct local-structure feature paths;
2. exact FOUNDATION-AUDIT1 content equality for in-memory and forced-mmap temporary storage;
3. worker/resource admission that fails closed on nested oversubscription;
4. no scientific change from rejected scratch/chunking experiments;
5. measured CPU throughput or memory benefit on bounded realistic workloads; and
6. no accelerator claim. GPU qualification remains deferred to `FINAL-GPU1`.

The bounded cloud evidence records a 7.42% median wall-time reduction for a 168-atom, 300-frame, single-worker LTA-like structural fixture and an 8.02% peak-RSS reduction for an exact 900,000-atom FOUNDATION-AUDIT1 reduction fixture. The audit preallocation is not claimed to be faster; its authority is lower temporary memory.

# Handoff

After PERF-P3, the next implementation gate is **VRAM1 + PERF-P4**. VRAM1 revises DATA6 accelerator-memory calibration authority; PERF-P4 implements bounded CPU/GPU/I/O overlap. Their GPU qualification remains part of the final consolidated `FINAL-GPU1` package per the project qualification schedule.

# References

[^numpy-memmap]: NumPy Developers, "`numpy.memmap` / standard array subclasses," *NumPy Reference*, https://numpy.org/doc/stable/reference/arrays.classes.html. Accessed 2026-08-15.

[^threadpoolctl]: Thomas Moreau et al., "threadpoolctl: Python helpers to limit native thread pools," project documentation, https://github.com/joblib/threadpoolctl. Accessed 2026-08-15.
