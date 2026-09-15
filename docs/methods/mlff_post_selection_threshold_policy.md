---
title: "mdstats MLFF post-selection threshold policy"
artifact_level: "D1 scientific formulation"
status: "accepted branch authority"
branch: "fix/mlff-cv-competence-threshold-separation"
accepted_baseline_commit: "8553ebe9ed86b24dfe910c9e43acc6230d3ece90"
accepted_date: "2026-09-15"
---

# MLFF post-selection threshold policy — D1 authority

## Scope and ownership

This file is the current D1 owner, on this branch, for the three post-selection threshold-policy claims below. It supersedes only threshold-value/configurability wording in `docs/methods/mlff_scientific_method.md`; every unaffected scientific statement in that paper remains governing.

The stakeholder clarified and ratified on 2026-09-15 that **all three threshold values are configurable policy parameters by design**, with generated/current defaults `45 / 45 / 30 meV/angstrom`. The scientific invariant is role separation and evidence interpretation, not immutability of those three numeric defaults.

## Governed parameters

For foundation adaptation (`naive_fine_tuning`, `multihead_replay`) define:

- `tau_cv`: CV checkpoint-competence target-force RMSE ceiling on the protected campaign-common monitor `M_mon`;
- `theta_cv`: CV held-out acceptance ceiling. Under the default outer metric it is a target-force RMSE ceiling on held-out fold evidence; for an explicitly selected alternative outer metric it has that metric's units and interpretation; and
- `tau_prod`: fresh-production checkpoint-quality target-force RMSE ceiling on the same protected `M_mon`.

All three are independently configurable policy values. Their current/generated defaults are:

```text
tau_cv    = 0.045 eV/angstrom = 45 meV/angstrom
theta_cv  = 0.045 eV/angstrom = 45 meV/angstrom  # for default target-force outer metric
tau_prod  = 0.030 eV/angstrom = 30 meV/angstrom
```

These defaults are cycle/current policy, not universal physical constants.

## Scientific interpretation

Foundation CV asks whether every required fold/seed of the frozen shared foundation-adaptation method reaches the configured CV competence regime and then passes the configured held-out acceptance predicate. A mean, majority, or best-seed aggregate cannot rescue a failing required position; cross-fold/cross-seed dispersion remains diagnostic-only.

`tau_cv` and `theta_cv` may have the same numeric value while remaining different scientific evaluations on different evidence. `M_mon` controls checkpoint choice; held-out fold evidence evaluates the frozen representative. Equal numbers never permit evidence substitution or leakage.

Fresh production uses the same shared adaptation method, common monitor, checkpoint-selection mechanics, replay-retention semantics, and integrity constraints, but applies its separately configured `tau_prod`. CV acceptance under `tau_cv` never authorizes a production checkpoint that violates `tau_prod`.

Changing any one threshold is a change of that role policy, not a change of the shared foundation-adaptation method. A different configured value therefore defines a different policy instantiation and invalidates materially dependent evidence according to the role boundary.

Current default intent remains asymmetric: `45 / 45` permits CV to establish competence without forcing disposable fold models through the late slow-convergence regime, while default production retains the stricter `30` checkpoint-quality criterion. An operator may deliberately configure another value; that choice is explicit policy, not silent relaxation.

## Preserved boundaries

- CV training remains fixed-budget; crossing a threshold never terminates training.
- A shorter CV horizon remains a separately frozen design choice.
- Foundation CV checkpoint competence remains target-force RMSE even when the held-out outer metric is changed.
- Held-out labels remain evaluation-only and cannot affect fitting, common-monitor construction, or checkpoint choice.
- Replay retention, TRUE_DFT evidence requirements, physical/integrity gates, common-monitor membership, target selection, and P1/P2/P3 semantics are unchanged.
- Post-selection `scratch` remains separately governed and is not changed by this foundation-policy revision.
- Neither CV nor production common-monitor thresholds constitute external adequacy, locked-test evidence, or release qualification.

## Calibration and adequacy

The generated/default `45 meV/angstrom` CV values retain the stakeholder-authorized calibration premise from recalled foundation-adaptation learning curves: rapid initial error reduction followed by slower convergence through roughly `40–20 meV/angstrom`. The generated/default `30 meV/angstrom` production value remains intentionally inside that slower regime. This is stakeholder calibration, not a recovered repository study.

Evidence showing that these defaults are systematically inappropriate for the intended foundation-adaptation regime reopens the policy calibration; it does not authorize hidden threshold changes.

## D1 -> D2 handoff

D2 shall represent `tau_cv`, `theta_cv`, and `tau_prod` as independently resolved policy parameters, preserve their evidence populations and dimensions, define exact comparison/boundary semantics, and make policy changes currentness-significant without promoting the values into shared-method identity.
