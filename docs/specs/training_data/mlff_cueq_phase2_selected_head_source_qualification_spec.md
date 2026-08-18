---
title: "MLFF CUEQ-PHASE2 Selected-Head Source Qualification"
subtitle: "Optional CuEq execution realization for DATA6 and inference-heavy preparation"
date: "2026-08-15"
geometry: margin=0.8in
fontsize: 10pt
header-includes:
  - |
    \usepackage{microtype}
---

# 1. Scope

**Gate:** `CUEQ-PHASE2`  
**Implementation release:** `mdstats 0.20.190a0`  
**Qualification schedule:** `FINAL-GPU1`  
**Authority class:** optional accelerator execution qualification

CUEQ-PHASE2 asks whether the EXTRACT1-derived single-head `omat_pbe` artifact may be used as a pure-CuEq executable realization for source inference, DATA6, source evaluation, and - only when separately evidenced - pseudolabel/E0 generation.

The scientific source identity does not change:

```text
scientific source = original six-head MACE-MH-1 checkpoint + exact omat_pbe head
execution candidate = EXTRACT1-derived single-head omat_pbe checkpoint + cueq_pure
```

The gate cannot authorize direct CuEq execution of the original six-head checkpoint and cannot change generated defaults.

# 2. Frozen identities

The policy locks the previously qualified identities:

- original MH-1 SHA-256: `ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde`;
- scientific source-potential digest: `06bf87891d6addebd3ea300fa23fd6401f0b74897f5676394e99507d03c8fc59`;
- EXTRACT1 derived selected-head SHA-256: `7b6f3cce6d2086164082f1cb5739098de2db990d6a49f0d60e66a3a0f1ae545e`; and
- EXTRACT1 selected-head qualification digest: `0f49db0ff9da291fbb4d70430c71189552a531d0239d92c06d0ca4024b05e365`.

Each candidate execution realization is content-addressed from the positive CUEQ-DEP1 runtime digest, these identities, `cueq_pure`, and dtype. Cache/prediction/pseudolabel lineage must bind that realization explicitly while still naming the original scientific source.

# 3. Development corpus

Qualification uses a deterministic stratified **development** corpus. Where available it covers:

- composition/species environments;
- temperature and strain states;
- high-force/high-difficulty frames;
- unusual local/mobile-ion environments;
- large/high-edge-count graphs; and
- representative ordinary configurations.

The record explicitly lists available and covered strata, freezes corpus/order digests, and fails if an available stratum is not represented. A locked-test configuration may later validate a frozen decision but `locked_test_used_for_tuning=true` is a hard failure.

# 4. Existing numerical authority is reused

Energy, force, stress/virial, and invariant-descriptor comparison is represented by the existing `MaceAccelerationParityRecord`. CUEQ-PHASE2 requires that record to pass with

```text
reference = original MH-1 / omat_pbe / e3nn
candidate = derived selected-head omat_pbe / cueq_pure
```

No CUEQ-PHASE2-specific tolerance is introduced. In particular, the gate may not loosen existing parity criteria to recover acceleration.

# 5. DATA6/DATA7 path parity

The candidate path additionally records and requires:

- foundation-difficulty numerical parity;
- PCA input parity using a frozen reference fitted transform;
- FPS input parity under that same frozen transform;
- exact DATA6 deterministic selection fingerprint identity; and
- exact DATA7 downstream selection fingerprint identity.

A separately recorded full-refit selection verification may be added after the frozen-transform comparison, but it is not allowed to substitute a second independently fitted transform into the primary backend comparison.

# 6. Pseudolabel/E0 lineage

Pseudolabel generation is optional within this gate. If it is requested, the evidence must include:

- pseudolabel value parity;
- atomic-E0 parity;
- scientific-source lineage equal to the original MH-1/`omat_pbe` source-potential digest; and
- execution-realization lineage equal to the qualified selected-head/CuEq realization digest.

A phase-2 pass without pseudolabel evidence can authorize selected-head source/DATA6/source-evaluation execution but **cannot** authorize CuEq pseudolabel generation.

# 7. Gate reducer

`CueqPhase2QualificationRecord.v1` requires:

1. one positive release-matched `CueqDep1RuntimeRecord.v1`;
2. at least one passing deterministic development-corpus path assessment;
3. identical policy/runtime lineage across all assessments; and
4. no failed assessment.

Positive GPU evidence remains deferred to FINAL-GPU1. On the development CPU host the expected state is fail-closed with at least `CUEQ_DEP1_RUNTIME_FREEZE` and `development_path_assessment_missing`.

# 8. Authorization boundary

A positive record may authorize:

- derived selected-head `cueq_pure` source execution;
- DATA6 execution on that realization;
- source-evaluation execution on that realization; and
- pseudolabel/E0 execution only when every qualifying assessment contains the explicit pseudolabel parity/lineage evidence.

It never authorizes:

- direct CuEq execution of the original six-head MH-1 checkpoint;
- reinterpretation of prior e3nn scientific evidence;
- a generated-default change; or
- PERF-CERT1 release recommendation by itself.

# 9. Schemas and tooling

`mdstats.training_data.cueq_phase2` defines:

- `CueqPhase2Policy.v1`;
- `CueqPhase2DevelopmentCorpus.v1`;
- `CueqPhase2Data6ParityRecord.v1`;
- `CueqPhase2PathAssessment.v1`; and
- `CueqPhase2QualificationRecord.v1`.

The evidence tool is:

```text
tools/qualify_mlff_cueq_phase2.py
```

FINAL-GPU1 preflight advances to `mdstats.mlff-final-gpu1.preflight.2026-08.v4` and embeds independent deferred CUEQ-PHASE1 and CUEQ-PHASE2 states. No intermediate GPU qualification is performed.
