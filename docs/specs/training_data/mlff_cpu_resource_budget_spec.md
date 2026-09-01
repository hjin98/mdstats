# MLFF CPU resource-budget specification

## Scope

This specification owns the current campaign-wide CPU-capacity contract for MLFF execution. It controls execution admission only; worker counts, native widths, queue widths, and autotuning choices do not enter scientific identities or digests.

## Runtime CPU authority

Let `N_available` be the CPU-thread capacity visible to the process after host CPU count, process affinity, and cgroup CPU quota constraints are intersected. For configured `cpu_fraction`,

\[
B_{\mathrm{cpu}}=\max\!\left(1,\left\lfloor \mathrm{cpu\_fraction}\,N_{\mathrm{available}}\right\rfloor\right).
\]

The production default is `cpu_fraction = 0.90`.

`SystemResourceSnapshot.cpu_threads_budget` is the sole campaign-wide automatic CPU-capacity authority. A stage-specific explicit worker or thread request is a cap inside `cpu_threads_budget`; it MUST NOT bypass the campaign fraction by using `cpu_threads_available` directly. Changing `cpu_fraction` is the supported mechanism for changing the campaign-wide CPU fraction.

For every active stage,

\[
1 \le B_{\mathrm{effective}} \le B_{\mathrm{authorized}} \le B_{\mathrm{cpu}}.
\]

An effective width below the authorized width is conforming when caused by task cardinality, RAM or I/O admission, backend availability, a scientific serial mutation boundary, or measured throughput saturation. A measured host-specific optimum MUST NOT be converted into a fixed global CPU-capacity ceiling.

## Stage resource scopes

`StageResourceScope` is the execution-only nested-parallelism authority for one stage. It distinguishes these CPU dimensions:

- Python/process workers;
- structural workers;
- native-tree workers;
- BLAS threads;
- explicit native/OpenMP threads;
- PyTorch CPU workers.

A scope MUST reject a configuration whose estimated nested CPU demand exceeds its stage budget. Native/OpenMP width is independent from Python-worker ownership and BLAS width.

Concurrent sibling pools and nested execution share one aggregate stage/campaign budget. Implementations SHOULD expose one useful parallel layer at a time: broad deterministic outer work queues use inner native widths of one when enough independent outer work exists; a native kernel may instead consume the budget directly when it is the single parallel layer.

## Stage-specific effective widths

Stages may select any scientifically exact, RAM-safe, throughput-effective width up to the runtime budget. Automatic policies MUST NOT retain unexplained host-capacity ceilings such as 4, 8, or 16 merely because those values were historical tuning points.

Runtime meters/autotuners may probe smaller widths and the budget endpoint, then retain the smallest width within their declared throughput tolerance of the best measured result. Such tuning is execution-only and MUST preserve the owning stage's scientific equivalence and determinism contract.

## Scientific invariants

Changing CPU admission or effective execution width MUST NOT change current scientific authorities. In particular:

- the canonical training order and the target-size common preparation preserve their exact FP64 identity contract;
- MVIDX preserves authoritative sparse content and digest;
- structural selection and the target-size owners preserve their current scientific authorities and digests.

Where an algorithm contains a serial authoritative mutation/reduction boundary, parallel work may prepare or evaluate immutable candidates, but the authoritative commit remains in the current canonical order.

## Memory, I/O, and backend admission

CPU capacity does not override RAM, scratch, I/O, GPU/VRAM, or backend constraints. Worker admission remains bounded by the applicable resource estimates and current stage contracts. If those constraints or measured saturation reduce effective width, the reduction is a runtime decision rather than a new fixed CPU-capacity rule.

## Qualification requirements

Changes to this contract require focused qualification that covers, where applicable:

1. affinity/cgroup-derived `N_available` and the 90% default budget without host-specific constants;
2. explicit worker requests capped by `cpu_threads_budget`;
3. nested resource-scope rejection of oversubscription;
4. serial, selected-effective, and budget-endpoint scientific equivalence/determinism;
5. fresh and resumed paths for stages with persisted execution state;
6. representative comparable-workload timing sufficient to reject material regressions;
7. clean native source/editable/wheel import paths where the environment supports the native backend.

GPU qualification is owned by the final release workflow and is not implied by CPU qualification.
