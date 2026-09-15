---
kind: independent-D1-D2-rereview-handoff
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
gate: R1
protocol_version: 6.3.0
lifecycle: REREVIEW_REQUESTED
candidate_authority_state: PROPOSED_NOT_ACCEPTED
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
recovery_snapshot: 3937881ef00222e80845aa81f5471d89a4a7736c
branch: design/mlff-pi-train-fps-diversity-restoration
supersedes: MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_INDEPENDENT_REREVIEW_HANDOFF.md
---

# R1 independent D1/D2 re-review handoff 2 — obligation-strength repair

## 1. Reviewer instruction

Perform a fresh independent Protocol-6.3 D1/D2 Review/Challenge of the repaired R1 candidate. Do not inherit the repair author's conclusion or the prior NO-PASS. Accepted-current authority remains the D1/D2 method papers at `e72090e21cec5311ce87745b03603f8783cd15a7`; this candidate remains proposed and still requires stakeholder ratification after PASS.

The governing Revision-8 workplan remains PASS as a workplan. This re-review determines only whether R1's reconstructed proposed D1/D2 authority is now lossless, internally coherent and sufficiently exact to proceed to ratification.

## 2. Effective candidate

Review together:

1. `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_METHOD_AMENDMENT.md`;
2. `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D2_METHOD_AMENDMENT.md`;
3. `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_D2_RECONSTRUCTION_EVIDENCE.md`;
4. `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_EXACT_RECONSTRUCTION_LEDGER.md`;
5. `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_D2_REPAIR_ADDENDUM.md`.

The repair addendum is controlling wherever earlier proposed R1 text conflicts with it, including older obligation-minimum language in the ledger or prior handoffs. The first and second prior handoffs are historical review evidence only; this document is the active handoff.

Primary historical recovery carrier remains exact pre-P6 snapshot `3937881ef00222e80845aa81f5471d89a4a7736c`.

## 3. Remaining blocker that was repaired

The prior review found that R1 incorrectly treated a stronger current explicit P2 minimum on the same restored automatic support locus as a contradiction. That would reject a valid current policy such as:

```text
automatic condition=A, minimum 1
explicit condition_id=A, minimum 2
```

The repair now separates scientific support-locus identity from requirement strength.

For source obligation `o`:

```text
L(o) = semantic support locus, excluding source ID and minimum count
A(o) = exact current-P_train candidate incidence
k(o) = positive required minimum
```

Same-locus records are admissible only when their exact incidence agrees. Their canonical requirement is

```text
k_canonical(L) = max k(o).
```

Thus the example above becomes exactly one canonical condition obligation with minimum two. Source aliases cannot create additional hard-gain votes.

True contradictions remain fail closed: same source ID with different semantics, same purported locus with different incidence, incompatible applicability/provider/family/side/target identity, or an explicit selector that cannot be projected unambiguously to current `P_train`.

Different scientific loci remain distinct even if their candidate incidence is identical.

## 4. Mandatory obligation counterexamples

Independently falsify at least these cases:

1. **exact alias** — same locus/incidence/minimum under another source ID: canonical set, MVSEL2 history, REPAIR2 and MVQUAL unchanged;
2. **weaker alias** — same locus/incidence with minima 1 and 2: equivalent to one minimum-2 obligation;
3. **automatic + explicit strengthening** — automatic condition minimum 1 plus current explicit same-condition minimum `k>1`: equivalent to one minimum-`k` obligation;
4. **source-ID rename** — unchanged semantics: no scientific effect;
5. **source-ID collision** — same ID, changed semantics: fail closed;
6. **same locus, changed incidence**: fail closed;
7. **different loci, identical incidence**: remain separate obligations;
8. **minimum-strength progression** — once one member satisfies the automatic baseline but not an effective minimum two, the canonical locus remains unsatisfied and contributes one hard-gain vote, not zero and not two.

Check that REPAIR2 deficit/safety and MVQUAL use the same effective canonical minimum and that no current P2 configured hard-support capability is lost.

## 5. Re-falsify the previously repaired areas

Do not limit review to the new delta. Reconfirm:

- `TargetCoverageReference` remains the sole fitted selector numeric owner while DATA7 retains lineage/input semantics;
- every selector-relevant recovered field has a justified RESTORE/REBIND/DROP disposition;
- uniform `0.95` is the only instantiated recovered family threshold and named-family override remains dormant/uninstantiated;
- NEIGHBOR1/MVIDX exact boundary semantics remain `d <= r + 1e-12*max(1,r)`;
- Phase-A comparator order and inclusive `1e-14` filtering remain exact;
- certified-lazy Phase B has all-candidate rebase, conservative outward bounds, exact contender certification and full-forward per-rank oracle equivalence;
- accepted REPAIR2 swaps invalidate/reconstruct stale selector state before continuation;
- configured shells preserve lower prefixes and same MVSEL2 continues through all `P_train`;
- MVQUAL is independent membership qualification and does not acquire P3 target-size ranking authority;
- retired label-domain/fold fanout and fixed-eight/fixed-16384 target-size topology remain retired;
- current `pi_eval/M1/M2/M3`, P3 ranking/reducer, CV, replay and production semantics remain unaffected.

## 6. Required disposition

Report:

1. any SERIOUS CHALLENGE first;
2. exact blocking D1/D2 findings, if any;
3. whether the obligation-strength counterexample is closed without losing current P2 policy capability;
4. whether the effective reconstruction is lossless after justified current-architecture rebinding;
5. whether any mature instantiated capability was dropped or any historical mechanism improperly promoted;
6. PASS/NO-PASS for the repaired proposed R1 D1/D2 candidate.

If PASS, state explicitly that stakeholder ratification and accepted-method-paper promotion remain mandatory before R2/D3/D4 implementation. Do not implement source code as part of this re-review.
