---
kind: independent-review-handoff
protocol_version: 6.4.0
status: AWAITING_FRESH_INDEPENDENT_D2_R1_REVIEW
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
accepted_D2_baseline: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
accepted_D2_source_target: a4824d28775164aa942fd29fa97ee0957eb87e6f
ratified_parent_D1_target: d761171f3c86c3c79b87a90cfc02ac324c261b1a
ratified_parent_D1_blob: 612294ec4680db01a18085e13fbfe5dcfa9fb7ed
immutable_D2_R1_candidate: e2b39917ab8c16556eb218d6a41e9682331bbca0
D2_R1_candidate_blob: 9e12728432d20bc7d16b9c5654bf7833cdee8df9
dependency_trace_path: workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D2_DEPENDENCY_TRACE_R1.md
highest_review_owner: D2
d3_gate_state: BLOCKED_PENDING_D2_ACCEPTANCE
---

# Independent D2 R1 Review handoff — replay/target numerical renewal

## 1. Binding

Perform a fresh Protocol-6.4 D2 review of immutable target:

`e2b39917ab8c16556eb218d6a41e9682331bbca0`

against accepted-current D2 baseline:

`a759e81aa1b4c70c8fb513c569ddce57e99cbdb2`

and exact accepted D2 source target:

`a4824d28775164aa942fd29fa97ee0957eb87e6f`.

Canonical D2 blob:

`9e12728432d20bc7d16b9c5654bf7833cdee8df9`.

The governing parent is the independently reviewed and stakeholder-ratified D1 target:

`d761171f3c86c3c79b87a90cfc02ac324c261b1a`.

Do not inherit the authoring conclusions or workplan disposition.

## 2. Material numerical amendment

Review the candidate's concretization of:

- signed same-monitor replay degradation `Delta_R = RN64(R_c - R_0)`;
- configurable replay warning/hard defaults `50/100 meV/angstrom`, strict `>` boundaries, and diagnostic-only warning;
- default foundation role thresholds `75/75/50 meV/angstrom`;
- inclusive direct binary64 target/outer predicates with no epsilon;
- complete-checkpoint strict target representative order `(target RMSE, epoch, SHA)`;
- strict `single_best_final_seed` order `(target RMSE, optimizer seed, SHA)`;
- training-versus-retention replay dependency projections;
- threshold/selection-specific currentness;
- training-semantic equivalence, evaluation-measurement equivalence and immutable policy reassessment;
- current-CV reauthorization before reassessing historically fresh final production.

P3 practical-equivalence ranking is not reopened.

## 3. Mandatory Challenge Pass

Challenge at minimum:

1. whether binary64 subtraction and comparison implement D1's signed replay observable without a hidden tolerance, bias or unstable boundary;
2. whether binary64 `v_meV / 1000` conversion and fail-closed `warning < hard` validation are exact enough for configured policy identity;
3. whether the replay training projection versus retention-measurement projection is correctly separated;
4. whether `R_c` and `R_0` use the same numerical observable while intentionally using different model states;
5. whether warning can leak into `S(c)`, representative ranking, CV acceptance or publication;
6. whether every governed checkpoint remains in the alternative set and no shortlist/rescue approximation can change the winner;
7. whether the target/tie keys are deterministic total orders and cannot be contaminated by bootstrap, practical-equivalence, secondary or maturity logic;
8. whether `tau_CV`, `theta_CV`, and `tau_prod` have the correct distinct numerical currentness effects;
9. whether alternative outer metrics are protected from force-unit `0.075` migration;
10. whether training-semantic equivalence is strong enough for continuation/reuse without treating assessment policy as a training input;
11. whether measurement equivalence prevents scalar-only stale reuse while allowing valid assessment-policy-only reuse;
12. whether historical CV/final reassessment rules can reconstruct the current strict winner without retraining or content-store heuristics;
13. whether the amended D2 remains dimensionally/type coherent and leaves unaffected D2/P3 semantics intact.

Raise SERIOUS CHALLENGE if the ratified D1 semantics cannot be faithfully or stably concretized by this candidate.

## 4. Lifecycle

Return D2 PASS only if the exact candidate is coherent and source-closed.

PASS still requires explicit stakeholder ratification of the exact reviewed D2 target before D3 can treat it as accepted authority.
