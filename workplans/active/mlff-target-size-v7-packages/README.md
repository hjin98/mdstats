# MLFF target-size V7 implementation packages

These files decompose `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` into seven sequential implementation packages. The frozen parent V7 workplan remains the **sole scientific and architectural authority**. Package contracts constrain execution order, package-local scope, acceptance, and verification; omission from a package does not waive a frozen parent requirement.

A package may not reinterpret the frozen parent merely to preserve legacy code/tests. Newly discovered necessary implementation consequences that preserve the parent are incorporated at the owning package. Reopen design only on a parent-listed reopen condition or equivalent material evidence.

## Current sequencing state

P1-P6 remain the accepted predecessor architecture, including the revision-11 P5 final-publication decision repair for both supported committee policies and its affected P5/P6 reclosure/rebind.

The P7A3 implementation reviewed by revision 13.2 is:

- executable commit: `cc098c18b39bbfdc65be6d5266fc2582d9bc9e01`;
- executable tree: `918d7670a6441a5431c95313c452499387b5ec60`.

**P7 revision 13.2 is the current authority and is REOPENED / NO-PASS.** P7A3 materially closes the broad revision-13 source repair set. The current reopen is intentionally narrow.

Accepted P7A3 source repairs to preserve:

- component/member/geometry-scoped stress capability and fail-closed applicable-stress reducers;
- authenticated external-reference stress source representation/units/sign/order/virial/canonicalization provenance;
- immutable cumulative attempt-wide resource observation lineage, locked timing, selected-device telemetry, and reserve-plus-write-headroom disk admission;
- exact static/dynamics per-axis PBC and static post-build cell observation/verification;
- public release/resource/terminal referential integrity;
- selected KOKKOS/mliappy child-worker mechanics, callback evidence, crash isolation, and no external Python finalization;
- all previously accepted R12 pressure-unit/sign and R11 publication/currentness/locked/reference repairs.

Residual blockers are now exactly:

1. **R13.2-B11A:** a generic/default LAMMPS runtime probe can still veto execution, influence stress availability, and affect reuse before the exact selected KOKKOS/MACE worker is attempted. Generic preflight must become diagnostic-only; the selected semantic worker owns product runtime availability/evidence.
2. **R13.2-B11B:** the exact current durable P5 publication member has not yet been accepted through the final selected KOKKOS/mliappy MACE deployment-parity path with E/F/applicable-stress parity.
3. **R13.2-B12:** final target-machine real-reference qualification, one-shot locked result, cumulative resource evidence, immutable terminal/release graph, and process-restart close/reopen have not yet been accepted on the same frozen candidate.

Long real-production/GPU qualification remains the final P7 release gate and is distinct from bounded regression/integration.

## Mandatory sequence

```text
P1 neutral scientific substrate
  -> P2 target-size statistical authorities
  -> P3 candidate execution and paired-seed screen
       -> FORMAL P3 CLOSURE
  -> P4 atomic runtime/persistence cutover
       -> FORMAL P4 CLOSURE
  -> P5 post-selection CV and fresh final production
       -> revision-11 final-publication decision repair
       -> affected P5 reclosure
  -> P6 destructive cleanup and assembled closure
       -> affected P6 reclosure/rebind after P5 repair
  -> P7 V7-native post-production qualification and locked release evidence
       -> accepted R11/R12 repairs
       -> accepted P7A3 R13 stress/provenance/resource/PBC/release repairs
       -> R13.2 remove generic runtime-preflight semantic veto/coupling
       -> fresh focused + complete affected R11/R12/R13 regression/integration
       -> freeze new executable candidate
       -> actual current-publication selected-KOKKOS MACE E/F/applicable-stress parity
       -> final target-machine real-reference qualification on same candidate
       -> one-shot locked closure
       -> immutable terminal/resource/reference graph close-reopen
       -> independent P7 PASS
  -> CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
```

The successor storage reset remains blocked until P7 receives independent PASS.

## Cross-package rules

- The frozen parent is the controlling scientific/architectural verdict; package amendments may reconcile implementation consequences but may not silently change it.
- Historical workplan/evidence records are preserved. Current authority files identify which revisions are operative.
- P3 owns target-size scientific execution evidence/replay; P4 consumes/adopts that authority rather than recreating reducer/replay semantics.
- P4 owns the production runtime/persistence cutover and current selected-binding/currentness model.
- P5 owns selected-only CV, fresh final production, and the exact pre-qualification final-publication member decision for both `all_qualified_final_seeds` and `single_best_final_seed`.
- P7 consumes the P5 final-publication owner. Cross-seed member ranking must never be implemented in P7.
- P6 owns the accepted transitional storage public surface, current-cache owner, and safe-cleanup owner. P7 may add owner-local immutable qualification evidence, active-attempt references, bounded disk-safety checks using existing policy, and release observations, but may not implement the post-P7 storage subsystem.
- P7 is read-only with respect to target-size selection, CV, production training, checkpoint/seed/member choice, and publication membership.
- P7 downstream deployment/physical/calibration/locked evidence has pass/reject/waiting authority only for the exact frozen product; it has zero fallback/model-selection authority.
- Public/current plan, verdict, and release views must reauthenticate the exact current P7 binding and all acceptance-critical immutable objects they reference.
- Reference-dependent component evidence must bind the exact authenticated reference-bundle content and invalidate only the correct descendants.
- Deployment qualification must bind the canonical P5 target head through the actual MACE deployment/ML-IAP/LAMMPS owner path; an analytic ML-IAP runtime smoke is not product-path evidence.
- Generic/static LAMMPS probes may report diagnostics but may not replace, veto, or reinterpret the selected semantic KOKKOS/MACE product execution required for B11.
- LAMMPS thermo pressure remains bar/positive-compression and is converted only by its fixed source adapter to canonical ASE/MACE tensile-positive eV/A^3 stress.
- Stress applicability/evidence must be claim-scoped across exact member/component/geometry identities. Runtime/reference availability cannot redefine an applicable trained channel as `not_applicable`.
- External-reference stress must authenticate source units, sign, ordering/representation, volume semantics where needed, and canonicalization provenance before entering physical evidence.
- Exact per-axis periodicity is product geometry. Runtime adapters may not collapse mixed PBC, and both static and dynamics evidence must authenticate what was actually executed.
- Dynamics must start from exact authenticated reference-relaxed bases and enforce the frozen NVT/NVE/topology/displacement/bond/angle policy.
- Explicit one-shot locked activation remains mandatory; an already-open activation must be crash-resumable to its exact terminal result.
- Resource observations are release evidence, not selection authority. Final evidence must cover the complete resumable attempt, preserve prior immutable observations, identify the selected execution scope/device, and preserve the configured disk reserve with bounded write headroom.
- Full production qualification is distinct from regression/integration: regression establishes functionality and absence of new affected hard failures; final target-machine qualification establishes real deployment/physical/resource claims for the exact frozen release candidate.

## Packages

1. `P1_NEUTRAL_SCIENTIFIC_SUBSTRATE.md` — neutral statistical identity/provenance substrate.
2. `P2_TARGET_SIZE_STATISTICAL_AUTHORITIES.md` — configurable N/M ladders, one split, one training order, one evaluation order, and pure target-size state.
3. `P3_CANDIDATE_EXECUTION_PAIRED_SCREEN.md` plus revision-7 closure amendments — canonical candidate execution, authenticated exact-boundary evaluation, immutable evidence, deterministic reducer/restart.
4. `P4_ATOMIC_RUNTIME_PERSISTENCE_CUTOVER.md` plus revision-8 closure — current runtime/persistence/currentness ownership cutover.
5. `P5_POST_SELECTION_CV_FINAL_PRODUCTION.md` plus accepted amendments — post-selection CV, fresh final production, and the revision-11 pre-qualification publication decision/evidence owner.
6. `P6_DESTRUCTIVE_CLEANUP_FINAL_CLOSURE.md` plus accepted reclosure/rebind amendments — destructive retirement, transitional storage/cache/safe-cleanup ownership, and assembled predecessor closure.
7. `P7_POST_PRODUCTION_QUALIFICATION_REPLACEMENT.md` composed with revision 2, revision 10, revision 11, revision 12, revision 13/13.1, and **current revision 13.2** — consume the exact predecessor publication, qualify exact executable/product/environment/reference/resource identities, and publish immutable release evidence without recreating predecessor or successor authorities.

## Current P7 authority

Read P7 in this precedence order:

1. frozen parent workplan;
2. accepted/reclosed predecessor authorities;
3. `P7_REVISION_13_2_IMPLEMENTATION_REVIEW_RUNTIME_GATE_REOPEN_AMENDMENT.md` and `P7_REVISION_13_AUTHORITY.md`;
4. `P7_REVISION_13_B11_KOKKOS_MACE_RUNTIME_CORRECTION_AMENDMENT.md` where revision 13.2 does not narrow/clarify it;
5. `P7_REVISION_13_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` where still binding;
6. `P7_REVISION_12_FINAL_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` except where later revisions supersede it;
7. `P7_REVISION_11_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` except where later revisions supersede it;
8. `P7_REVISION_10_IMPLEMENTATION_REALIGNMENT_AMENDMENT.md` except where later revisions supersede it;
9. `P7_POST_PRODUCTION_QUALIFICATION_REPLACEMENT.md` except stale predecessor assumptions already superseded;
10. `P7_REVISION_2_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md`, preserving P6 cache/safe-cleanup ownership and the post-P7 storage boundary;
11. P7 revisions 3-9 as historical predecessor-entry alignment records.

`P7_REVISION_13_AUTHORITY.md` is the current authority pointer. `P7_REVISION_13_2_REVIEW_EVIDENCE.md` records the independent P7A3 NO-PASS review. Older implementation/review evidence remains historical.

P7 is **REOPENED / NO-PASS**. Only after R13.2-B11A source repair, fresh affected regression/integration, actual current-publication selected-KOKKOS MACE execution, final target-machine real-reference qualification, one-shot locked closure, full immutable terminal/resource/reference evidence close-reopen, and independent final review may the accepted P7 executable commit/tree become the baseline for `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.
