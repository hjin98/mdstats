---
kind: independent-review-handoff
protocol_version: 6.4.0
status: AWAITING_FRESH_INDEPENDENT_D1_R3_REVIEW
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
accepted_baseline_commit: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
prior_r2_reviewed_candidate: 2549dee709fb8bb383341ee3aebca7c71973a903
prior_r2_review_commit: 8bf25f37e74667ff897e938a9b17830ea9fee225
immutable_d1_r3_candidate: d32536569322cc19722d6842896c9a467f7ef30d
d1_r3_candidate_blob: 479ff368917baf576d12f553caad571da856ae28
dependency_trace_blob: 55acec8b806d65d8ceab54cace3e8419b8698800
highest_review_owner: D1
d2_gate_state: BLOCKED_PENDING_D1_ACCEPTANCE
---

# Independent D1 R3 Review handoff — CV threshold relaxation and UniversalLoss clarification

## 1. Binding

Perform a fresh Protocol-6.4 D1 review of immutable target:

`d32536569322cc19722d6842896c9a467f7ef30d`

against accepted current baseline:

`a759e81aa1b4c70c8fb513c569ddce57e99cbdb2`.

Canonical D1 blob:

`479ff368917baf576d12f553caad571da856ae28`.

The R2 PASS remains evidence for the unchanged replay-warning/hard, checkpoint-universe, target-only ordering, currentness and fresh-production semantics, but it does **not** authorize the post-R2 CV threshold amendment.

## 2. Material R3 D1 amendment

The stakeholder changes the generated/default foundation role thresholds to:

```text
tau_CV   = 75 meV/angstrom
theta_CV = 75 meV/angstrom   (default force outer metric)
tau_prod = 50 meV/angstrom
```

Lower force RMSE is better, so the two CV ceilings are intentionally more permissive than final-production checkpoint admission.

The scientific roles remain distinct:

- `tau_CV`: common-monitor checkpoint competence during each CV fold/seed;
- `theta_CV`: held-out outer-fold acceptance under the default force metric;
- `tau_prod`: final-production common-monitor checkpoint admission.

Fresh review must determine whether `75/75` is sufficiently discriminating to authorize the method while leaving the stricter `50` production ceiling meaningful.

## 3. UniversalLoss clarification — no coefficient change

The stakeholder also questioned the D1 ledger phrase `P5 E:F:S coefficients = 1:10:1`.

Accepted D2 already defines:

```text
L_P5 = L_E + 10 L_F + L_S
```

for foundation P5, with the property reductions and robust Huber semantics owned by D2.

R3 therefore clarifies—but does not change—that `1:10:1` is the **global energy/force/stress property-loss coefficient tuple**. The final reconciled D1 keeps the scientific coordinate implementation-independent; native MACE `UniversalLoss` is the currently qualified D2/D4 realization, not the D1 object itself. It is not:

- target/replay training-head balancing;
- replay-vs-target sampling/exposure balance;
- per-configuration `config_weight`;
- per-frame property-availability masks.

Review must challenge that this wording exactly matches accepted D2 and does not introduce a new D1 numerical loss definition.

## 4. Mandatory Challenge Pass

Challenge at minimum:

1. whether `tau_CV=75` is too permissive to serve as meaningful common-monitor method-competence evidence;
2. whether `theta_CV=75` is too permissive to serve as meaningful held-out authorization;
3. whether `75/75` can accept a method whose fresh production cannot meet `50`, and whether the candidate's explicit interpretation—CV authorizes the production attempt but does not guarantee production success—is scientifically coherent;
4. whether the all-position CV rule, held-out evidence, and downstream no-feedback boundary keep the looser CV policy scientifically meaningful;
5. whether `tau_CV` and `theta_CV` have correctly separated assessment currentness: `tau_CV` may change checkpoint admissibility/representative while `theta_CV` may change only the outer verdict; neither may change TRAIN2;
6. whether scratch/P3 thresholds remain unaffected;
7. whether the `1:10:1` clarification is purely a semantic clarification of the already-accepted UniversalLoss objective and does not conflate property coefficients with target/replay or frame weighting;
8. whether the historical `45/45` calibration supplied any stronger scientific guarantee than the candidate acknowledges; repository history describes it as stakeholder calibration, not a universal boundary;
9. whether all previously reviewed replay and target-only representative semantics remain source-closed after the amendment.

Raise SERIOUS CHALLENGE if the `75/75` policy makes CV scientifically incapable of performing its claimed authorization role.

## 5. Review lifecycle

Return **D1 PASS** only if the new threshold family and the clarification are coherent and all unchanged R2 semantics remain intact.

PASS still requires explicit stakeholder ratification of exact target `d32536569322cc19722d6842896c9a467f7ef30d`.

Do not start D2 before D1 PASS plus exact-target ratification.
