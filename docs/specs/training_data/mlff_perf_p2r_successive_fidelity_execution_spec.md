---
title: "MLFF PERF-P2R Successive-Fidelity Execution Specification"
version: "0.20.184a0"
date: "2026-08-15"
status: "implementation-qualified; accelerator qualification deferred to FINAL-GPU1"
geometry: margin=0.85in
---

# Purpose

PERF-P2R optimizes execution of the corrected target-size funnel without changing its scientific decisions. Hard coverage remains an admission gate. Every admitted size reaches the coarse training boundary; learning evidence, not geometric coverage, performs the reductions.

The implementation must support the complete SIZE-FIDELITY1 calibration surface rather than assume that the provisional coarse boundary, monitor size, or practical-equivalence width will survive final calibration.

# Scientific funnel

For hard-coverage-qualified sizes $A$, coarse survivors $S_4$, and epoch-10 finalists $S_2$,

$$
A \xrightarrow{e_0} S_4 \xrightarrow{10} S_2 \xrightarrow{30} K^*,
$$

with

$$
e_0 \in \{3,4,5\}, \qquad |A|\in\{3,4,5,6,7\}.
$$

The structure follows the resource-allocation principle of successive halving: inexpensive low-fidelity observations eliminate weak candidates before additional budget is spent on survivors.[^jamieson2016] In mdstats, however, candidate set sizes, evaluation roles, continuation identities, tie handling, and downstream physical qualification are project-specific scientific authorities; they are not inherited from the generic algorithm.

# Authority split

PERF-P2R separates implementation status from accelerator qualification:

$$
I(\mathrm{PERF\!\!-\!P2R})=\mathrm{implemented},
\qquad
Q(\mathrm{PERF\!\!-\!P2R})=\mathrm{pending}.
$$

The CPU/control-plane implementation may be released and used to prepare the final qualification package. It must not authorize a GPU speed claim, calibrated coarse default, or production survivor decision before FINAL-GPU1 closes the corresponding scientific and accelerator evidence.

# P2R-1: parameterized stage authority

`PerfP2RParameterGrid` freezes the execution compatibility surface:

- coarse epoch candidates: 3, 4, 5;
- coarse target-monitor candidates: 128, 256, 512, 1024 configurations;
- coarse practical-equivalence candidates: 1, 2, 4 meV/Angstrom;
- hard-coverage-qualified ladder width: 3 through 7;
- coarse survivor limit: 4;
- short survivor limit: 2;
- short boundary: epoch 10;
- final boundary: epoch 30.

These values are a compatibility grid, not calibrated defaults.

`build_perf_p2r_stage_plan()` converts the current TARGET-DATA2D authority into exactly one authorized work stage. It derives candidate sizes, start epoch, target epoch, continuation requirement, screening seed, and allowed evidence class from the scientific state. Campaign dispatch must not duplicate independent hard-coded 3/10/30 branches.

# P2R-2: exact continuation and no repaid prefix

A promoted candidate continues the same scientific trajectory:

$$
\theta_0
\rightarrow
(\theta_{e_0},o_{e_0},r_{e_0})
\rightarrow
(\theta_{10},o_{10},r_{10})
\rightarrow
(\theta_{30},o_{30},r_{30}),
$$

where $\theta$, $o$, and $r$ denote model, optimizer/scheduler, and authenticated runtime/RNG continuation state.

The incremental structure-epoch exposure is

$$
W = e_0\sum_{i\in A}K_i
  + (10-e_0)\sum_{i\in S_4}K_i
  + 20\sum_{i\in S_2}K_i.
$$

The exhaustive reference is

$$
W_{\mathrm{full}} = 30\sum_{i\in A}K_i.
$$

A promoted candidate must never repay the already completed prefix because orchestration created a new schedule. Boundary checkpoints at $e_0$, 10, and 30 remain scientific evidence; extra recovery checkpoints are execution-only.

# P2R-3: authenticated content-addressed DATA8 fixed-file cache

Repeated DATA8 variants share immutable target fixed files through an authenticated content-addressed cache. A cache recipe binds at least:

- dataset and role;
- frame-catalog digest;
- DATA7 bundle digest;
- training-policy and training-weight identities;
- configuration-weight scale and configuration type where applicable; and
- the exact ordered frame-UID sequence.

SHA-256 is used as the package-wide content identity primitive, consistent with the Secure Hash Standard.[^nist1804]

A cache hit must validate the recipe, metadata, data-file SHA-256, sidecar SHA-256, and reconstructed artifact authority before use. Cache location, hard-link versus copy realization, mmap path, eviction policy, and filesystem placement are execution-only.

The cache may only represent immutable authorities. Mutating frame data beneath an unchanged frame-catalog authority is forbidden.

# P2R-4: shared frame-array access

DATA7 and DATA8 preparation may share one frame-array index keyed by the authenticated frame-catalog identity. The index is an execution accelerator only. The exact frame arrays and emitted ExtXYZ scientific bytes remain governed by the existing frame catalog, DATA7 weights, and MACE export authority.

# P2R-5: coarse-stage work suppression

The coarse stage purchases only evidence that can affect the coarse decision:

- the common target-only monitor;
- no replay inference;
- no replay ranking credit;
- no checkpoint-rescue sweep;
- no paired-bootstrap checkpoint selection; and
- no PES, relaxation, or dynamics qualification.

Later stages may add only the evidence authorized by their scientific boundary. The stage plan therefore carries evidence permissions rather than relying on call-site convention.

# P2R-6: resource and cache lifecycle

The campaign treats the shared DATA8 fixed-file cache as reconstructable state. It may be removed after preparation has finished and all consumer bundles are durably materialized.

Resource scheduling must remain bounded. CPU thread pools, graph builders, DataLoaders, storage traffic, and accelerator concurrency may not be oversubscribed merely to increase nominal parallelism. Host/accelerator class and execution geometry belong in performance evidence.

# CPU/control-plane qualification

The implementation gate may close on CPU when all of the following hold:

1. cache miss/population/hit produce the exact same DATA8 authority and integrity mismatch is rejected;
2. one parameterized stage plan spans coarse endpoints 3, 4, and 5 plus ladder widths 3--7, with coarse replay/physical work forbidden;
3. short/final stages require exact continuation and exposure accounting proves that no promoted candidate repays a prefix; and
4. regression tests preserve downstream scientific identities while cache/index location and lifecycle remain execution-only.

# FINAL-GPU1 qualification

PERF-P2R remains accelerator-unqualified until FINAL-GPU1 records, on the release-matched authorizing runtime:

FINAL-GPU1 must record SIZE-FIDELITY1 survivor fidelity and calibrated coarse parameters; resumed-versus-uninterrupted endpoint/continuation parity; identical target, replay, and physical evidence; whole-funnel and per-stage time with optimizer updates, structures presented, and pause/resume overhead; and GPU/host resource evidence including utilization, VRAM, preprocessing, RSS, I/O, checkpoint bytes, and cache/graph reuse. Microbenchmarks are diagnostic and cannot substitute for this whole-funnel authority.

[^jamieson2016]: Kevin Jamieson and Ameet Talwalkar, "Non-stochastic Best Arm Identification and Hyperparameter Optimization," *Proceedings of Machine Learning Research* 51, 240--248 (2016), https://proceedings.mlr.press/v51/jamieson16.html.

[^nist1804]: National Institute of Standards and Technology, *Secure Hash Standard (SHS)*, FIPS PUB 180-4, DOI: 10.6028/NIST.FIPS.180-4, https://csrc.nist.gov/pubs/fips/180-4/final.
