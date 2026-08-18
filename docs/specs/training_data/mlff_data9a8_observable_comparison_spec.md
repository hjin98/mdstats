---
title: "MLFF-DATA9A8 Profile-Aware Observable Comparison Policies"
author: "mdstats project"
date: "2026-07-30"
version: "0.20.52a0"
geometry: margin=0.8in
fontsize: 10pt
header-includes:
  - |
    ```{=latex}
    \usepackage{microtype}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{array}
    \usepackage{enumitem}
    \setlist{nosep}
    ```
---

# 1. Purpose

MLFF-DATA9A8 adds the policy layer that compares paired physical-observable
results generated through the analysis-owned validation bridge. The stage does
not calculate RDFs, coordination distributions, spectra, diffusion,
conductivity, or thermomechanical properties. Those algorithms and native result
objects remain owned by their respective analysis modules and architecture
manuals.

DATA9A8 owns only:

1. predeclared comparison rules;
2. explicit quality and hard-acceptance thresholds;
3. identity binding to one recipe and material profile;
4. optional score-level uncertainty allowances whose provenance is external to
   the comparator;
5. atom-group and condition scopes;
6. comparison records;
7. acceptance decisions suitable for later checkpoint selection.

The normative dependency order is:

```text
comparison policy + activation + frozen recipe/profile identity
    -> paired observable evidence
    -> comparison result
    -> acceptance decision
```

Realized observable values SHALL NOT be used to choose their own metric,
threshold, uncertainty allowance, statistical role, or aggregation rule.

# 2. Ownership boundary

## 2.1 Analysis-owned responsibilities

The authoritative analysis branch owns:

- scientific definitions and normalization;
- neighbor, time-window, projection, and plateau semantics;
- native result dataclasses;
- result serialization or canonical result identity;
- scientific uncertainty estimators when such estimators exist;
- warnings about insufficient sampling or invalid physics assumptions.

## 2.2 MLFF-owned responsibilities

The MLFF branch owns:

- selecting which native result fields are compared;
- selecting a mathematically declared discrepancy metric;
- binding the rule to a recipe call, profile, atom group, and condition;
- consuming independently justified score uncertainty;
- applying predeclared thresholds;
- aggregating rule outcomes by worst required rule;
- issuing checkpoint-facing acceptance evidence.

No comparison adapter may silently reinterpret an analysis result or create an
alternative physical observable.

# 3. Core records

## 3.1 `ObservableComparisonThresholds`

Each lower-is-better score has two levels:

- `quality_max`: scores at or below this level pass;
- `acceptance_max`: scores above the quality level but at or below this level
  are degraded;
- scores above the acceptance level fail.

The invariant is

$$
0 \leq s_{\mathrm{quality}} \leq s_{\mathrm{accept}}.
$$

This mirrors the package's broader distinction between a high-quality result and
an admissible but degraded result. Thresholds are scientifically material and
must be supplied by the user or frozen project protocol.

## 3.2 `ObservableScoreUncertainty`

DATA9A8 supports a conservative score-space allowance

$$
u = k\sqrt{u_r^2 + u_c^2},
$$

where $u_r$ and $u_c$ are predeclared standard uncertainties on the
comparison score and $k$ is a coverage multiplier. The thresholded score is

$$
s_{\mathrm{adjusted}} = \max(0, s_{\mathrm{raw}} - u).
$$

This record does not estimate uncertainty. A nonzero allowance requires explicit
provenance such as independent block bootstrap, replica statistics, or an
analysis-owned uncertainty record. It must not manufacture an independent
standard error from one serially correlated running curve.

## 3.3 `ObservableComparisonRule`

A rule binds:

- unique rule ID;
- recipe `call_id` and `observable_id`;
- native result field path;
- optional axis field path;
- discrepancy metric;
- optional scalar reducer;
- interpolation permission;
- thresholds;
- required versus advisory status;
- atom-group and condition scope;
- score uncertainty and notes.

Result-field access is restricted to attributes and mapping keys. Arbitrary
method execution is forbidden.

## 3.4 `ObservableComparisonPolicy`

The policy binds all rules to:

- one recipe digest;
- one observable-recommendation profile;
- an optional compositional material-profile-contract digest;
- allowed statistical roles;
- capability and result-type compatibility requirements;
- degraded-result acceptance behavior;
- required-rule indeterminate behavior.

At least one rule must be required. The policy digest must already be present in
the validation activation record before observable execution.

## 3.5 Results and decisions

`ObservableRuleComparisonResult` records raw and adjusted scores, source-result
digests, outcome, summaries, uncertainty allowance, scope, and diagnostics.

`ObservableComparisonResult` records all rules, the evidence and policy digests,
statistical role, worst required outcome, weighted reporting score, and
condition/group outcome summaries.

`ObservableAcceptanceDecision` is separate from the numerical comparison. It
records acceptance, blocking rules, degraded rules, advisory failures, and
reasons. This separation prevents the scientific result object from being
mutated into a checkpoint policy object.

# 4. Implemented metrics

All metrics are lower-is-better.

## 4.1 Absolute error

For scalar reference $x$ and candidate $y$,

$$
d_{\mathrm{abs}} = |y-x|.
$$

## 4.2 Symmetric relative error

$$
d_{\mathrm{srel}} =
\frac{|y-x|}{\max[(|x|+|y|)/2,\epsilon]}.
$$

The explicit floor $\epsilon$ prevents undefined behavior near zero.

## 4.3 Normalized RMSE

For jointly finite entries,

$$
d_{\mathrm{NRMSE}} =
\frac{\sqrt{N^{-1}\sum_i(y_i-x_i)^2}}
{\max[\sqrt{N^{-1}\sum_i x_i^2},\epsilon]}.
$$

The current implementation accepts arrays of arbitrary shape when reference and
candidate shapes match. Undefined pairs are omitted only when at least one
jointly finite entry remains.

## 4.4 Normalized integrated absolute error

For one-dimensional curves over the reference axis,

$$
d_{\mathrm{IAE}} =
\frac{\int |y(q)-x(q)|\,dq}
{\max[\int |x(q)|\,dq,\epsilon]}.
$$

Interpolation is permitted only when explicitly enabled and when the candidate
axis covers the complete reference interval.

## 4.5 Jensen--Shannon distance

For normalized nonnegative discrete distributions $p$ and $q$,

$$
d_{\mathrm{JS}} =
\sqrt{\frac{1}{2}D_{\mathrm{KL}}(p\|m)
+\frac{1}{2}D_{\mathrm{KL}}(q\|m)},
\qquad m=(p+q)/2.
$$

Explicit supports may be union-aligned. Continuous interpolation is used only
when the rule author enables it.

## 4.6 Peak displacement

For one-dimensional curves, the score is the absolute displacement between the
reference and candidate global-maximum locations. This metric is intentionally
simple and should be supplemented by a full-curve metric when peak multiplicity
or shoulder structure matters.

## 4.7 Exact mismatch

Exact scalar or array equality scores zero; mismatch scores one. This is
appropriate only for declared categorical invariants, never for floating-point
curves.

# 5. Profile and scope behavior

A comparison policy may bind the full `MaterialProfileContracts` digest. This
prevents a policy prepared for a bulk liquid from being reused silently for an
interface or porous crystal.

Rules may declare `atom_group_id` and `condition_id`. These labels identify the
scientific scope already encoded by the recipe call; they do not select atoms or
frames after the result has been computed. The comparison result reports the
worst outcome for each condition/group pair.

The acceptance decision uses the worst required rule. A weighted mean score is
reported for diagnostics only and cannot hide a required failure.

# 6. Recommended templates

`recommended_observable_comparison_templates()` provides field/metric
suggestions for common implemented observable IDs, including RDF,
coordination, angle distributions, MSD, VACF, spectra, VDOS, running and plateau
diffusion, displacement dynamics, current correlations, ionic conductivity,
and Nernst--Einstein comparisons.

Templates deliberately contain no thresholds and make no pass claim. Some
observables, especially topology catalogs, require domain-specific state
matching and therefore have no generic template.

# 7. Failure semantics

A rule becomes `indeterminate` when, for example:

- a declared result field is absent;
- required axes are incompatible;
- interpolation coverage is incomplete;
- a distribution has negative or zero total mass;
- no jointly finite entries remain;
- native result types or capability identities conflict.

Required indeterminate rules fail by default. A policy may downgrade them only
explicitly. Advisory failures are recorded but do not block acceptance.

# 8. Leakage and locked-test constraints

The policy digest must be upstream of observable evidence. Locked-test evidence
retains all DATA9A6c gates: protocol freeze, partition identity, and explicit
activation. Locked-test comparison results and decisions may report final model
performance but cannot alter feature fitting, selection, calibration,
checkpoint selection, or acquisition.

# 9. Development-stage compatibility cleanup

Because `mdstats` remains pre-1.0 and this branch is undergoing active
architectural generalization, DATA9A8 removes misleading deprecated Python
surfaces:

- `MaterialValidationProfile`;
- `MLFFTrajectoryGenerationIdentity`;
- `MLFFObservableValidationPlan.material_profile`;
- cation-named objective/checkpoint properties;
- `species_aware_force_objective` alias;
- `PartitionUnit.cation_ordering_id`;
- `IndependenceGrade.INDEPENDENT_CATION_ORDERING`;
- `SelectionCoverageLevel.represented_species_site_classes`.

The canonical names are recommendation profile, symmetric trajectory-generation
identity, focus groups, structural realization, and environment classes.

Pre-generalization objective, checkpoint, partition-unit, and coverage-policy
schemas are no longer accepted. DATA4/DATA6 historical bundle readers remain
for the moment because they protect package-generated cache artifacts rather
than ambiguous user-facing aliases. Their eventual removal must be a separate,
explicit cache-migration decision.

# 10. Required tests

Focused tests SHALL cover:

- identical-result pass;
- changed-result fail;
- pass/degraded/fail threshold boundaries;
- predeclared-policy digest enforcement;
- material-profile digest enforcement;
- score-uncertainty adjustment and provenance gate;
- curve interpolation and coverage rejection;
- Jensen--Shannon distribution comparison;
- indeterminate required-rule handling;
- condition/group summaries;
- policy/result/decision round trips and tamper rejection;
- removal of deprecated public aliases;
- existing observable bridge, role, and locked-test regressions.

# 11. Completion boundary

DATA9A8 is complete when comparison and decision records are immutable,
profile-bound, leakage-safe, and exercised against native analysis results.
It does not define universal scientific thresholds. After this stage, the plan
returns to production DATA6--DATA8 realization and then DATA9B training,
checkpoint selection, committee construction, and protocol freeze.
