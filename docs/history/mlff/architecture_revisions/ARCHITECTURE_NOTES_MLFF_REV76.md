---
title: "MLFF Architecture Revision 76"
subtitle: "FINAL-GPU1 v2 consolidated workstation qualification and atomic MVMIGRATE1 activation"
author: "mdstats project"
date: "2026-08-16"
geometry: margin=0.85in
fontsize: 10pt
---

# Revision 76

Revision 76 closes the development-side implementation of the consolidated `FINAL-GPU1` handoff. The final-release reducer is advanced to v2 and now treats `SIZE_FIDELITY2_MV_SURVIVOR_REQUALIFICATION` and `TARGET_DATA2C_MVMIGRATE1_LEARNING_CONTROLS` as release-blocking, runtime-bound evidence in addition to the existing CUEQ-DEP1, e3nn baseline, SIZE-FIDELITY1, PERF-P2R, VRAM1/PERF-P4, CUEQ-PHASE1, and PERF-CERT1 requirements. The matrix therefore contains nine must-pass gates, six measure-only optimization gates, and two optional capability gates.

The two new migration records are not accepted as generic pass/fail JSON. `FINAL-GPU1` v2 deserializes the exact `SizeFidelity2QualificationReport` and `TargetMultiViewLearningControlReport`, requires positive final-GPU status, binds their content digests to the immutable handoff registrations, and requires a common dataset identity. Dedicated source-tree CLIs assemble both records from their frozen inputs.

Revision 76 also implements the explicit MVMIGRATE1 release transaction. A passing FINAL-GPU1 v2 record is first dry-run against the campaign store. The transaction recomputes the authorized migration plan, rebuilds and independently validates the fixed-eight TARGET-DATA2C v5 ladder from REPAIR1, and constructs a fresh TARGET-DATA2D v3 convergence plan requiring at least four hard qualifiers. Only `--apply` publishes the replacement generation. Publication is one SQLite transaction that preserves the historical v4 ladder, stores the final GPU records and activation receipt, switches the live ladder/convergence aliases together, and invalidates stale generation-dependent production/prepare aliases. Existing activation is idempotent only when the complete receipt digest matches; a different activation is rejected.

No positive GPU evidence is synthesized in this development environment. The complete package is therefore `workstation_ready`, not GPU-qualified. Production remains on v4/v2/v2 until the user's final CUDA workstation produces a passing FINAL-GPU1 v2 record and the explicit activation transaction is applied. FINAL-GPU1 itself still cannot authorize unrelated generated-default changes; its only new promotion effect is the separately frozen MVMIGRATE1 transaction whose prerequisites were established in revisions 74-75.

**Release:** `mdstats 0.20.209a0`  
**Dependency-graph schema:** 58  
**Next action:** execute the one-shot FINAL-GPU1 v2 workstation bundle; on pass, dry-run and apply MVMIGRATE1 activation.
