---
kind: independent-d1-review
protocol_version: 6.4.0
status: COMPLETE
review_disposition: D1_NO_PASS
serious_challenge: NONE
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
accepted_baseline_commit: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
reviewed_immutable_candidate: 06f1255ed39f41d178daf73985829a2190a2bee8
reviewed_d1_blob: 65713ab4e8caa848e21d27a75e594664528ee6eb
review_date: 2026-09-18
highest_open_owner: D1
d2_gate_state: BLOCKED
---

# Independent D1 Review R1 — replay retention and target admissibility renewal

## 1. Disposition

**D1: NO-PASS. No SERIOUS CHALLENGE is raised against the intended scientific direction.**

The reviewed immutable target is:

`06f1255ed39f41d178daf73985829a2190a2bee8`

against accepted Protocol-6.4 D1 baseline:

`a759e81aa1b4c70c8fb513c569ddce57e99cbdb2`.

The reviewed semantic blob is:

`65713ab4e8caa848e21d27a75e594664528ee6eb`
(`docs/methods/mlff_scientific_method.md`).

The candidate is scientifically coherent in its principal policy direction:

- foundation-relative replay degradation is a distinct auxiliary retention observable;
- warning-only degradation may be non-vetoing;
- a separate catastrophic replay limit may remain hard;
- replay need not receive positive target-quality ranking credit;
- foundation-production target admission may use a configurable generated/default `50 meV/angstrom` while foundation CV remains `45/45 meV/angstrom`;
- strict target-force-RMSE ranking can own foundation-P5 checkpoint and single-best-seed choice after hard gates;
- these threshold defaults may be stakeholder-selected policy calibrations rather than universal physical constants because downstream adequacy remains a separate scientific layer;
- assessment-policy changes need not scientifically redefine an otherwise identical already-realized training trajectory, provided current assessments are reclosed and fresh-production/CV authority is preserved.

The candidate nevertheless leaves several materially different downstream concretizations possible. Those authority defects block D1 acceptance.

## 2. Review basis and independence

This review reconstructed the accepted D1 from the current Protocol-6.4 kernel and its exact imports, especially accepted `D1.IMP.P5`. The workplan, handoff, motivating TRAIN2 trajectory, current implementation, prior threshold history and author Challenge notes were treated only as evidence/challenge material.

The accepted Project Engineering Memory was also considered only as non-authoritative project evidence. Its relevant bounded lessons concern exact TRAIN2/EVAL2 realized-model authentication and authenticated restart boundaries; neither memory entry supplies authority for the new replay or target thresholds.

No D2/D3/D4 behavior was promoted into D1 merely because the implementation currently behaves a certain way.

## 3. Challenge Pass

### 3.1 Numeric policy values

No Serious Challenge is raised against the proposed defaults themselves.

The candidate correctly avoids claiming that `delta_warn = 50`, `delta_hard = 100`, or `tau_prod = 50 meV/angstrom` are universal physical constants or externally validated release criteria. The old 30-meV replay budget is not established by accepted D1 as a uniquely necessary physical boundary, and downstream physical/deployment qualification remains independent.

Therefore lack of a universal empirical calibration is a stated limitation/reopen condition, not by itself a blocker.

### 3.2 CV versus production threshold ordering

No contradiction is found in `tau_CV = 45` and `tau_prod = 50 meV/angstrom`.

The two thresholds act on distinct role claims even though both use the same target monitor. The accepted historical rationale that production was deliberately numerically stricter was calibration rationale, not a theorem. The candidate explicitly supersedes that ordering claim while preserving held-out CV acceptance and downstream adequacy as separate evidence.

### 3.3 Target-only ranking

No scientific contradiction is found in selecting the minimum target-monitor force RMSE after hard validity/target/catastrophic-replay gates.

This is a legitimate stakeholder choice of the primary model-control objective, provided the candidate universe is defined completely and replay-warning evidence cannot re-enter through another ranking/tie path. That latter requirement is not yet represented precisely enough; see D1-R1 and D1-R3.

### 3.4 Historical final-trajectory reassessment

The proposed principle is scientifically coherent: a prior fresh final TRAIN2 trajectory is not physically changed by a later assessment-policy edit. Reuse may therefore be meaningful after current CV reauthorization when exact training-semantic equivalence is proven and no CV model/checkpoint becomes a training parent.

This does not authorize publication after current CV rejection and does not relax fresh-training semantics.

## 4. Blocking findings

### D1-R1 — strict best-target rule lacks a governed checkpoint universe

**Severity: BLOCKING. Owner: D1.DEF.026.**

The candidate says:

> "For role rho and its fully evaluated checkpoint set..."

and minimizes target RMSE only over the hard-admissible subset of that set.

That does not define which checkpoints must be in the fully evaluated set. A downstream method could evaluate an arbitrary shortlist, call that subset "fully evaluated", and satisfy the literal D1 while failing the stakeholder rule that the representative is the best target-RMSE checkpoint satisfying the hard limit.

This is not a D2-only enumeration detail. D1 owns the scientific alternative set over which the target-quality decision is made.

**Required repair**

Define a governed run checkpoint universe before the hard-admissible subset, e.g. conceptually:

```text
C_rho = every authenticated durable TRAIN2 checkpoint produced by the accepted
        checkpoint cadence for the realized fixed-budget trajectory and eligible
        for checkpoint assessment

H_rho = { c in C_rho : all hard requirements pass }

c_star in argmin_{c in H_rho} r_mon(c)
```

D2 may own exact durable enumeration/authentication mechanics and typed invalid-record handling, but it may not purchase/evaluate only a quality-dependent shortlist and still claim the D1 minimum. If an accepted checkpoint class is intentionally excluded from the selection universe, that exclusion must be explicit scientific policy rather than evaluator convenience.

The same repair must make clear that failure/integrity status excludes a checkpoint through hard validity, not by silently removing a quality-relevant checkpoint from the scientific alternative set.

### D1-R2 — exact foundation identity is not made material for TRUE-reference degradation

**Severity: BLOCKING. Owner: D1.DEF.022 / D1.DEF.022A.**

`D1.DEF.022A` defines:

`Delta_replay(c) = R_replay(c) - R_replay(Phi)`.

Therefore exact foundation identity `Phi` is a scientific parent of replay degradation whenever foundation-relative retention is assessed.

But `D1.DEF.022` still states:

> "`Phi` is material when pseudo labels or head-local foundation references are used"

which permits a true-reference replay path to omit `Phi` from replay lineage even though `R_replay(Phi)` is then undefined/non-reproducible.

That is a direct internal contradiction.

**Required repair**

For foundation adaptation with replay-retention assessment enabled, exact `Phi` must be material to replay-retention lineage regardless of replay training-label mode. Pseudo-label mode may add further dependence on `Phi`, but it is no longer the condition that makes foundation identity relevant.

The replay baseline must bind the same exact foundation checkpoint/head/model identity whose inherited capability is being measured.

### D1-R3 — warning-only policy has ambiguous currentness authority

**Severity: BLOCKING. Owner: D1.DEF.022A / D1.AX.010A.**

`D1.DEF.022A` correctly says a warning-only checkpoint remains admissible and replay receives no ranking/tie credit.

However `D1.AX.010A` groups "replay warning/hard policy" together and says such a change "does alter the dependent current assessment according to its role."

That wording is too weak for the candidate's central scientific distinction. It allows D2/D3 to make a warning-threshold change stale the hard-admissible set, representative, CV acceptance, production authorization or publication membership even though D1 otherwise says the warning has zero veto/ranking authority.

**Required repair**

State the dependency semantics explicitly:

- changing `delta_warn` changes warning/diagnostic classification only and cannot by itself change `H_rho`, the representative, outer evaluation membership, CV pass/fail, production authorization or publication membership;
- changing `delta_hard`, a role target ceiling, or the target-selection rule may change hard assessment/representative and descendants according to their roles;
- neither class changes the realized training trajectory when training-bearing semantics are unchanged.

This is scientific meaning/currentness, not merely a D3 storage optimization.

### D1-R4 — D1 fixes threshold inequalities but simultaneously delegates boundary semantics to D2

**Severity: BLOCKING AUTHORITY AMBIGUITY. Owner: D1.DEF.022A.**

The candidate's three replay classes use clear scientific inequalities:

- no warning when degradation does not exceed `delta_warn`;
- warning for degradation above `delta_warn` but not above `delta_hard`;
- hard failure above `delta_hard`.

Those clauses correctly imply that equality at either threshold does not trigger the corresponding strict-`>` class.

The same definition then says:

> "D2 owns exact finite arithmetic, units and boundary comparison semantics..."

That gives D2 authority to change a boundary that D1 has just defined, and "units" is also over-broad because the D1 policy values are dimensioned force-error differences.

**Required repair**

D1 must retain the scientific inequalities and dimensions exactly. D2 owns their numerical realization: canonical unit conversion, binary64/finite representation, comparison implementation, `nextafter` or equivalent boundary oracles, and typed numerical failure.

Replace any statement that D2 owns the scientific boundary relation or threshold dimension.

### D1-R5 — TRUE_DFT terminology conflicts with the accepted TRUE_REFERENCE label-mode family

**Severity: BLOCKING SOURCE-CLOSURE AMBIGUITY. Owner: D1.DEF.021 / D1.DEF.022A / D1.AX.010.**

Accepted `D1.DEF.021` defines the scientific replay label mode as `TRUE_REFERENCE` versus `FOUNDATION_PSEUDO`. The candidate introduces "TRUE_DFT replay" as if it were the formal D1 role and later requires "mandatory TRUE_DFT replay evidence", without changing `D1.DEF.021`.

The imported source paper deliberately uses true-reference/DFT language because DFT is the current realization, while the D1 role is the canonical true-reference concept.

The candidate therefore leaves unclear whether it narrows the accepted replay family to DFT only or merely renames the same evidence role.

**Required repair**

Preserve the accepted D1 role name and object:

- define the retention observable on the exact independent **true-reference** replay monitor `M_r^true`;
- if useful, state parenthetically that the current project realization is DFT / `true_dft`;
- use the same terminology in D1.AX.010 and the handoff.

Do not silently create a third replay label-mode concept.

### D1-R6 — new display equations regress the renderer-safe canonical representation

**Severity: BLOCKING REPRESENTATION DEFECT, semantic repair not required.**

The accepted kernel uses block-math fences `$$ ... $$`. The new/edited D1 equations at candidate source lines 357-460 use single-dollar lines as display fences. Eighteen such fence lines are present:

`357, 359, 369, 371, 375, 377, 381, 385, 389, 393, 397, 401, 438, 440, 444, 446, 458, 460`.

This is an avoidable representation drift on a repository with known renderer-sensitive math documentation.

**Required repair**

Restore the accepted renderer-safe `$$ ... $$` block representation for the affected equations without changing mathematics.

## 5. Direct dependency/source-closure audit for the repaired candidate

The repaired D1 candidate should publish a bounded non-authoritative dependency trace for the changed/new objects before re-review. At minimum, independently verify the following direct semantic edges after repair:

```text
D1.DEF.022  -> D1.DEF.020, D1.DEF.021, D1.IMP.P5
D1.DEF.022A -> D1.DEF.020, D1.DEF.022, D1.IMP.P5
D1.DEF.025  -> D1.DEF.023, D1.DEF.024, D1.IMP.P5
D1.DEF.026  -> D1.DEF.022A, D1.DEF.023, D1.DEF.025, D1.IMP.P5
D1.DEF.027  -> D1.DEF.026, D1.IMP.P5
D1.AX.009   -> D1.DEF.024, D1.DEF.025, D1.DEF.026, D1.IMP.P5
D1.AX.010   -> D1.DEF.012, D1.DEF.020, D1.DEF.022, D1.DEF.022A,
               D1.DEF.023, D1.DEF.025, D1.DEF.026, D1.IMP.P5
D1.AX.010A  -> D1.DEF.022A, D1.DEF.025, D1.DEF.026, D1.DEF.027,
               D1.AX.009, D1.AX.010
```

The exact repaired trace may add a direct prerequisite where the repaired wording genuinely needs it, but it must not omit the foundation identity edge from the replay-degradation object or the governed checkpoint-universe parent from the representative object.

This trace is a review aid, not a second D1 authority owner.

## 6. Non-blocking observations

1. The candidate's explicit supersession of the old "production must be numerically stricter than CV" rationale is necessary and coherent.
2. The `50/100 meV/angstrom` replay and `50 meV/angstrom` production defaults are correctly represented as configurable stakeholder-selected defaults rather than claims of universal physical adequacy.
3. The downstream no-feedback / qualification boundary remains intact.
4. Scratch, target-size P3, E0, objective/exposure, common-monitor cardinality and fold construction are not substantively changed by the candidate.
5. `single_best_final_seed` target-only ordering is a real D1 publication-semantic change but is stated explicitly rather than hidden in D2/D3.
6. No evidence establishes that replay must regain positive ranking credit; retaining it only as a hard catastrophic guard plus diagnostic warning is scientifically coherent within the stated target-deployment focus.

## 7. Required repair scope

Repair must remain bounded to the canonical D1 file and review/trace artifacts.

Do **not** start D2, D3 or D4.

The next semantic candidate should:

1. define the complete governed checkpoint-selection universe;
2. make exact `Phi` mandatory for foundation-relative replay retention;
3. separate warning-only diagnostic currentness from hard-decision currentness;
4. keep strict/inclusive threshold relations and dimensions owned by D1 while delegating numerical realization to D2;
5. reconcile TRUE_REFERENCE/DFT terminology without changing the accepted label-mode family;
6. restore renderer-safe display math;
7. update the bounded direct-dependency review trace;
8. freeze a new immutable D1 candidate and request fresh independent re-review.

Re-review can be bounded to these repairs plus regression against the unchanged accepted imports, but must challenge that no collateral P1-P4/P5/downstream meaning moved.

## 8. Lifecycle

Candidate `06f1255e...` is **not ratifiable**.

Gate B remains open at D1. Gate C remains blocked.

No stakeholder decision is requested on this candidate because independent Review did not PASS.
