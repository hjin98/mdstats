---
kind: restoration-final-status
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
protocol_version: 6.3.0
status: closed
final_verdict: PASS
final_reviewed_candidate: caab58e87db281f90181da1e43a5ba73c231cb85
final_d4_implementation_commit: bc733983df328b9e5c285878443b2017e55e5469
accepted_project_basis: e72090e21cec5311ce87745b03603f8783cd15a7
closed_date: 2026-09-16
---

# MLFF `pi_train` restoration — final status

## Lifecycle result

The restoration is **CLOSED / PASS** after fresh independent assembled-candidate
review of `caab58e87db281f90181da1e43a5ba73c231cb85`.

```text
R1 D1/D2 reconstruction:       PASS / ACCEPTED
R2 dependency recovery:        PASS / CLOSED
R3 repaired D3 architecture:   PASS / ACCEPTED / PROMOTED CURRENT
D4 original implementation:    REVIEWED / REPAIRED
R11 correctness/ownership:     PASS
R12 REPAIR2 performance/restart: PASS
R13 resource routing + HAS:    PASS
R14 FEAS1/NEIGHBOR1 resource closure: PASS
Final assembled review:        PASS / CLOSED
```

## Canonical authority after closeout

- D1: `docs/methods/mlff_target_training_order_scientific_method.md`
- D2: `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`
- D3: `docs/arch_manuals/mlff_training_data/45_target_training_order.md` plus
  `docs/arch_manuals/mlff_training_data/60_execution_performance.md` and the
  reconciled canonical MLFF Architecture Manual.
- D4: accepted assembled implementation culminating in
  `bc733983df328b9e5c285878443b2017e55e5469`, with evidence/current-state
  binding through reviewed candidate `caab58e87db281f90181da1e43a5ba73c231cb85`.

The archived workplan/evidence lineage is historical coordination/evidence, not
a parallel semantic authority.

## Final protected outcome

The accepted implementation preserves one exact `P_train`, one complete
`pi_train`, exact nested `T_N = pi_train[:N]`, one `TargetCoverageReference`,
one canonical obligation authority, one shared FEAS1/NEIGHBOR1 construction,
MVIDX as sparse representation, MVSEL2/REPAIR2 as the single order owner,
independent MVQUAL, prepare-owned live-input/build/publication orchestration, and
prepared-generation/CampaignStore completed-generation currentness/adoption.

The final resource path uses the existing campaign resource owner and existing
stage-scope/work-queue machinery through COVREF, FEAS1/NEIGHBOR1, MVIDX,
REPAIR2 and MVQUAL. No competing resource manager or resource policy was added.

## Evidence qualification

Representative current-scale LTA execution preserved the accepted scientific
build identity `b8d75b6a1857`. Revision 14 measured FEAS1/NEIGHBOR1 inside its
finite inherited resource envelope and the affected-regression new-failure delta
was zero. Execution results are implementation-recorded local qualification
evidence; no CI statuses were attached and the final independent reviewer did
not re-execute the suite in a separate runtime.

No new Project Engineering Memory mutation is required by this closeout.

Final production-scale GPU qualification remains deferred to the final complete
MLFF release package on the stakeholder machine.
