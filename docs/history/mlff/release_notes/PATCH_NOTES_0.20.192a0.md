# mdstats 0.20.192a0

## MLFF FINAL-GPU1 release handoff

- Implement the FINAL-GPU1 release-handoff authority and fail-closed final qualification reducer.
- Advance FINAL-GPU1 preflight to v6 with exact release-archive binding in addition to locked foundation-model and CUEQ-DEP1 runtime identity.
- Classify the consolidated accelerator matrix into release-blocking `must_pass`, measured `measure_only`, and non-blocking `optional` evidence classes.
- Keep the authoritative complete MH-1/`omat_pbe` e3nn campaign, SIZE-FIDELITY1, PERF-P2R, VRAM1/PERF-P4 safety, CUEQ-PHASE1, and PERF-CERT1 as release-blocking final evidence.
- Treat the historical direct-six-head CuEq probes and PERF-P5 accelerator reuse as measured optimization evidence: a negative result is admissible only when that optimization stays disabled or is superseded by the phase-separated authority.
- Keep CUEQ-PHASE2 and ML-IAP/LAMMPS deployment qualification optional for the core release.
- Add content-addressed evidence registration, explicit runtime binding for every CuEq-dependent matrix item, same-release/same-runtime contamination guards, immutable per-gate registration, resumable handoff-root state, status/integrity verification, and final reduction to `FinalGpu1QualificationRecord.v1`.
- Preserve `generated_default_change_authorized=false`; a positive PERF-CERT1 recommendation still requires a later explicit generated-policy revision.
- Ship a workstation runbook and complete handoff bundle containing the source release, locked foundation models, supplied LTA training/replay inputs, and offline reference dependency sources.
- Harden source-tree handoff execution by fixing the PHASE1 qualifier CLI bootstrap, exposing the full handoff command surface through top-level help, requiring content-addressed terminal evidence for every measure-only matrix item, and re-hashing release/models/evidence immediately before final reduction.
- Harden handoff initialization/integrity by requiring both locked foundation identities at `init`, requiring the serialized policy to equal the canonical FINAL-GPU1 policy, and binding the manifest to the exact ordered 15-item matrix including acceptance class, canonical record path, and state domain.
- Advance canonical MLFF architecture to revision 59 and dependency-graph schema 41. Positive GPU execution remains intentionally pending until the user runs this complete package on the final CUDA/CuEq workstation.
