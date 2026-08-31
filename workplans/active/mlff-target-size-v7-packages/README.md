# MLFF target-size V7 implementation packages

These files decompose `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` into seven sequential implementation packages. The frozen parent V7 workplan remains the **sole scientific and architectural authority**. Package contracts constrain execution order, package-local scope, acceptance, and verification; omission from a package does not waive a frozen parent requirement.

A package may not reinterpret the frozen parent merely to preserve legacy code/tests. Newly discovered necessary implementation consequences that preserve the parent are incorporated at the owning package. Reopen design only on a parent-listed reopen condition or equivalent material evidence.

## Current sequencing state

P1-P6 were the independently accepted predecessor authorities for the original revision-10 P7 implementation. Revision 11 then correctly reopened the P5 final-publication decision surface so both supported committee policies could be decided pre-qualification, followed by affected P5/P6 reclosure/rebind.

The revision-11 repair implementation reviewed by revision 12 is:

- executable commit: `d24c16cecfd25f2dfcd83b10e0850981d5b64318`;
- executable tree: `2a01d92197ae4663fc7fc789ddb0aa21a97cdb4e`;
- documentation-only PDF regeneration head after that executable candidate: `4f8b624acedf23c0cf15a59ba5d7994336dc9755`.

**P7 revision 12 is the current authority and is REOPENED / NO-PASS.** Revision 11 materially closed the P5 publication-decision owner, target-head product identity, exact P7 currentness, reference-bundle descendant identity, reference-relaxed dynamics architecture, crash-resumable one-shot locked activation, explicit reference protocol, and canonical analysis-owner reconciliation. Revision 12 retains those repairs and reopens only the residual/newly surfaced blocking surfaces described below.

Residual blockers are:

- canonical stress qualification is not correct yet: LAMMPS `units metal` thermo pressure is in bar but the current worker converts the numeric values as GPa; the pressure-to-ASE/MACE stress sign and capability-based applicability decision also require closure;
- deployed static/dynamics execution collapses the exact three-axis PBC vector to one Boolean and therefore changes mixed-boundary systems such as `[T,T,F]`;
- the accepted resource-scope scheduler is present, but disk-reserve/availability and measured target-machine performance/resource observations are not yet represented in immutable release evidence;
- the development host can build the real MACE target-head ML-IAP product but cannot execute it in LAMMPS because its ML-IAP Python data interface lacks the MACE message-passing exchange capability; this remains `unavailable/blocking` rather than a pass;
- final target-machine qualification with the exact frozen repaired candidate/publication, real authenticated external references, actual supported MACE target-head deployment runtime, and one-shot locked closure has not run.

Long GPU/real-production qualification remains the final P7 release gate and is distinct from bounded functional/regression evidence.

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
       -> revision-11 source/design repair
       -> REVISION-12 STRESS / PBC / RESOURCE-EVIDENCE REPAIR
       -> fresh affected regression/integration
       -> actual frozen MACE target-head deployment execution on supported runtime
       -> final target-machine + real-reference qualification
       -> one-shot locked closure
       -> immutable terminal evidence/resource close-reopen
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
- P6 owns the accepted transitional storage public surface, current-cache owner, and safe-cleanup owner. P7 may add owner-local immutable qualification evidence, active-attempt references, disk-safety checks using existing policy, and release observations, but may not implement the post-P7 storage subsystem.
- P7 is read-only with respect to target-size selection, CV, production training, checkpoint/seed/member choice, and publication membership.
- P7 downstream deployment/physical/calibration/locked evidence has pass/reject/waiting authority only for the exact frozen product; it has zero fallback/model-selection authority.
- P7 public/current plan, verdict, and release-evidence views must reauthenticate the exact current P7 binding at exposure time, not merely the P4 selected binding.
- Reference-dependent component evidence must bind the exact authenticated reference-bundle content and invalidate only the correct descendants.
- Deployment qualification must bind the canonical P5 target head through the actual MACE deployment/ML-IAP/LAMMPS owner path; an analytic ML-IAP runtime smoke is not product-path evidence.
- Stress qualification, when applicable, must use one canonical ASE/MACE Cauchy-stress convention with authenticated source units/sign/order. LAMMPS pressure conversion is a source adapter, not a user-tunable scientific convention.
- Exact per-axis periodicity is product geometry. Runtime adapters may not collapse mixed PBC to all-periodic/all-fixed.
- Dynamics must start from the exact authenticated reference-relaxed bases and enforce the complete frozen NVT/NVE/topology/displacement/bond/angle policy.
- Explicit one-shot locked-test activation remains mandatory, but an already-open activation must be crash-resumable to its exact terminal result.
- P7 concurrency/resource behavior must use the accepted resource owner and may change scheduling only, never scientific policy or evidence membership. Disk/resource/performance observations are release evidence, not selection authority.
- Full production qualification is distinct from regression/integration: regression establishes functionality and absence of new affected hard failures; final target-machine qualification establishes real deployment/physical/resource claims for the exact frozen release candidate.

## Packages

1. `P1_NEUTRAL_SCIENTIFIC_SUBSTRATE.md` — neutral statistical identity/provenance substrate.
2. `P2_TARGET_SIZE_STATISTICAL_AUTHORITIES.md` — configurable N/M ladders, one split, one training order, one evaluation order, and pure target-size state.
3. `P3_CANDIDATE_EXECUTION_PAIRED_SCREEN.md` plus revision-7 closure amendments — canonical candidate execution, authenticated exact-boundary evaluation, immutable evidence, deterministic reducer/restart.
4. `P4_ATOMIC_RUNTIME_PERSISTENCE_CUTOVER.md` plus revision-8 closure — current runtime/persistence/currentness ownership cutover.
5. `P5_POST_SELECTION_CV_FINAL_PRODUCTION.md` plus accepted amendments — post-selection CV, fresh final production, and the revision-11 pre-qualification publication decision/evidence owner.
6. `P6_DESTRUCTIVE_CLEANUP_FINAL_CLOSURE.md` plus revisions through revision 13 and affected revision-11 reclosure/rebind — destructive retirement, transitional storage/cache/safe-cleanup ownership, and assembled predecessor closure.
7. `P7_POST_PRODUCTION_QUALIFICATION_REPLACEMENT.md` composed with revision 2, revision 10, revision 11, and **current revision 12** — consume the exact predecessor publication, perform deployment/physical/dynamics/calibration/locked qualification on exact executable/product/environment/reference identities, and publish immutable release/resource evidence without recreating predecessor or successor authorities.

## Current P7 authority

Read P7 in this precedence order:

1. frozen parent workplan;
2. accepted/reclosed predecessor authorities;
3. `P7_REVISION_12_FINAL_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` and `P7_REVISION_12_AUTHORITY.md`;
4. `P7_REVISION_11_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` except where revision 12 records a surface as closed or gives more specific residual instructions;
5. `P7_REVISION_10_IMPLEMENTATION_REALIGNMENT_AMENDMENT.md` except where later revisions supersede it;
6. `P7_POST_PRODUCTION_QUALIFICATION_REPLACEMENT.md` except stale predecessor assumptions already superseded;
7. `P7_REVISION_2_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md`, preserving P6 cache/safe-cleanup ownership and the post-P7 storage boundary;
8. P7 revisions 3-9 as historical predecessor-entry alignment records.

`P7_REVISION_12_AUTHORITY.md` is the current authority pointer. `P7_REVISION_12_REVIEW_EVIDENCE.md` records the independent NO-PASS review. Earlier implementation/review evidence remains historical and must not be interpreted as revision-12 closure evidence.

P7 is **REOPENED / NO-PASS**. Only after revision-12 source repair, required predecessor/affected regression reclosure, actual frozen-publication MACE target-head deployment execution, final target-machine real-reference qualification, one-shot locked closure, immutable terminal release/resource evidence close-reopen, and independent final review may the accepted post-P7 executable commit/tree become the baseline for `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.
