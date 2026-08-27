# TARGET-SIZE EVAL2 staged-execution OPT1 bounded CPU evidence

Date: 2026-08-26
Scope: implementation evidence only; not production or target-GPU qualification.

The bounded acceptance fixture executes the real TARGET-SIZE-V5 endpoint owner, canonical OPT-EVAL4 staged scheduler, real MACE static-inference executor, persistent geometry-graph cache, and two distinct authenticated checkpoint identities over the same target geometry. Expensive scientific scale is intentionally reduced; the orchestration/cache/runtime-profile owners are not replaced.

Observed on the implementation host with PyTorch 2.10.0+cpu and mace-torch 0.3.16:

- endpoint 1 static calibration: 0.403 s;
- endpoint 1 production inference: 0.557 s;
- endpoint 1 total prediction phase: 1.161 s;
- endpoint 2 provider shell: compatible checkpoint state reused;
- endpoint 2 static calibration: compatible profile reused, 0.000 s;
- endpoint 2 production inference: 0.041 s;
- endpoint 2 total prediction phase: 0.259 s.

The acceptance test additionally asserts that two distinct checkpoint/provider identities over the same authenticated geometry construct the MACE graph once, and that the second compatible checkpoint uses the retained private provider shell. A separate PERF-P5 regression proves the hot-swapped shell produces the same forward output as a freshly loaded compatible model and that structurally incompatible state is rejected/rebuilt.

Interpretation:

1. Calibration cost is material relative to production inference on this bounded workload, so retaining exact-checkpoint calibration identity would preserve measurable redundant work.
2. Cross-checkpoint runtime-profile reuse is therefore enabled only under the accepted weight-independent runtime-architecture digest plus exact authenticated geometry/workload/device/dtype/head/acceleration/precision/hardware compatibility relation.
3. Provider-shell reuse is enabled only for explicitly qualified serial target-size execution; foundation, CuEq/OEq, compiled, incompatible, corrupt, or authority-mismatched cases do not use the fast path.
4. Live RAM/VRAM clamping and OOM learning/backoff remain authoritative at every use; the runtime profile is execution state and never replaces checkpoint scientific identity.
5. No conclusion about CUDA occupancy, outer multi-checkpoint GPU concurrency, target RTX 3090 throughput, or production-scale resource use is made here. Those claims remain deferred to FINAL-GPU1 / target-hardware qualification.
