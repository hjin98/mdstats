---
title: "mdstats MLFF post-selection threshold numerical policy"
artifact_level: "D2 numerical algorithm design"
status: "accepted branch authority"
branch: "fix/mlff-cv-competence-threshold-separation"
accepted_baseline_commit: "8553ebe9ed86b24dfe910c9e43acc6230d3ece90"
accepted_date: "2026-09-15"
parent_d1: "docs/methods/mlff_post_selection_threshold_policy.md"
---

# MLFF post-selection threshold numerical policy — D2 authority

## Scope and ownership

This file is the current D2 owner, on this branch, for numerical semantics of the three configurable post-selection thresholds. It supersedes only the fixed-value threshold clauses and related oracles in `docs/methods/mlff_numerical_algorithmic_method.md`; every unaffected numerical method in that paper remains governing.

## Role-effective predicates

Let `r_mon(c)` be target force-component RMSE of checkpoint `c` on the protected common monitor `M_mon`. Let `S(c)` be the conjunction of shared mandatory checkpoint constraints: finite metrics, replay-retention and authenticated TRUE_DFT evidence where replay is enabled, and required physical/integrity gates.

For role `rho`, checkpoint admissibility is

$$
A_\rho(c) = S(c) \wedge r_{\mathrm{mon}}(c) \le \tau_\rho.
$$

For foundation adaptation the role thresholds are independently resolved policy parameters:

```text
tau_cv    := configured foundation-CV checkpoint target-force ceiling
theta_cv  := configured CV held-out outer threshold
tau_prod  := configured foundation-production checkpoint target-force ceiling
```

The generated/current defaults are:

```text
tau_cv    = 0.045 eV/angstrom
theta_cv  = 0.045 eV/angstrom when the default outer metric is target-force RMSE
tau_prod  = 0.030 eV/angstrom
```

No numerical rule requires an explicitly configured value to equal its default.

## Exact comparison and dimensional semantics

`tau_cv` and `tau_prod` are finite positive target-force RMSE values in `eV/angstrom`. Comparisons use IEEE-754 double precision against the resolved double policy value. Equality passes; the next representable value above the resolved threshold fails, absent another mandatory failure.

`theta_cv` is dimensioned by the configured held-out acceptance metric. Under default `target_force_rmse_ev_per_angstrom`, it is in `eV/angstrom`; under an explicitly supported alternative outer metric it carries that metric's units. `theta_cv` never supplies either checkpoint target-force threshold.

`tau_cv` is evaluated only on `M_mon`; `theta_cv` is evaluated only on held-out fold evidence. Equal numeric values do not make those estimators interchangeable.

## Aggregation and training semantics

CV accepts only when every required `(fold, seed)` position:

1. has at least one checkpoint admissible under `A_CV`; and
2. has a frozen representative satisfying the configured held-out predicate.

Missing/failed required positions are failures. No mean, majority, or best-seed rescue exists. Dispersion is diagnostic-only.

Threshold predicates never terminate training. The full frozen CV or production horizon executes according to its role budget. A no-admissible outcome remains a typed completed rejection/failure according to the existing role semantics rather than a fallback to the numerically best inadmissible checkpoint.

## Currentness and policy changes

A stored candidate classification is evidence only under the exact role-policy threshold that governed it. Re-comparing an old metric with a newly configured threshold does not make the old evidence current.

Threshold changes have the following semantic invalidation:

```text
tau_cv change
  -> CV role policy/plan/run positions and CV acceptance move
  -> production authorization depending on that CV acceptance becomes stale
  -> shared method and production threshold policy do not move

theta_cv change
  -> CV role policy/acceptance and dependent production authorization move
  -> shared method and production threshold policy do not move

tau_prod change
  -> production role policy/plan/run positions move
  -> applicable accepted CV evidence and shared method remain current
```

A shared replay/physical/integrity constraint change remains a shared-method change and can invalidate both roles.

## Defaults and falsification oracles

Default-policy oracles remain:

- foundation CV: `0.042` passes checkpoint competence; `0.045` passes; `nextafter(0.045,+inf)` fails;
- default held-out target-force acceptance: `0.042` passes; `0.045` passes; next representable above `0.045` fails;
- default production: `0.042` fails; `0.030` passes; `nextafter(0.030,+inf)` fails.

Configurability additionally requires:

- an explicit non-default `tau_cv` changes only the CV role-policy lineage and is honored by checkpoint assessment;
- an explicit non-default `theta_cv` changes only the CV outer-policy lineage and is honored in held-out acceptance without changing checkpoint target-force units;
- an explicit non-default `tau_prod` changes only the production role-policy lineage and is honored by production checkpoint assessment; and
- setting a threshold to its default explicitly is semantically equivalent to omitting it when all other policy inputs are equal.

Foundation `scratch` remains under its separately accepted pre-existing threshold semantics; this authority does not add a new scratch-policy family.

## D2 -> D3 handoff

D3 shall give each threshold exactly one durable policy owner, bind the resolved values into existing CV/production policy identity, preserve selective invalidation above, and expose configuration without creating synchronized aliases, a second checkpoint-policy engine, or a threshold-bearing shared method identity.
