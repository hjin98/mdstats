# MLFF MVQUAL independent prefix-qualification specification

**Status:** current normative independent hard-qualification contract  
**Architecture:** revision 105

## 1. Authority

MVQUAL independently recomputes the hard multi-view coverage and obligation predicates for repaired target-subset prefixes. Its purpose is to verify scientific hard requirements without trusting MVSEL2/REPAIR2 internal counters.

MVQUAL is not a legacy-versus-current comparator and is not a target-size selector. `TargetSizeStudyPolicy` consumes its current prefix pass/fail evidence.

## 2. Inputs

A qualification request binds:

- one canonical DATA5 gradient-training domain;
- current DATA7 `TargetSubsetInputBundle` identity;
- current FEAS1/MVIDX1 primitive identities;
- one current REPAIR2 repaired master-order identity;
- requested prefix size `N`;
- exact hard-coverage/obligation policy identity;
- current MVQUAL schema/policy identity.

The selected prefix is exactly the first `N` entries of the repaired master order. MVQUAL SHALL reject a caller-supplied membership list that does not authenticate as that prefix.

## 3. Independent recomputation

MVQUAL may reuse authenticated primitive sparse neighborhood/obligation inputs from MVIDX1. It SHALL recompute the qualification predicates independently of selector/repair mutable counters.

For each required family and obligation class, it records the current policy-defined evidence, including as applicable:

- weighted family coverage;
- hard deficit `D_m(N)` and worst-view deficit `D_max(N)`;
- uncovered witness count and weighted mass;
- required extent/stratum/obligation predicates;
- unique-support and redundancy diagnostics;
- correlation/provenance/run/condition diversity diagnostics;
- exact pass/fail reasons.

Secondary diagnostics cannot compensate for failure of a mandatory hard family or obligation.

## 4. Hard pass

A prefix passes only when every hard predicate defined by the bound current policy passes. No historical selector/ladder result is part of this comparison.

Locked-test, held-out CV, and calibration evidence cannot tune the qualification policy or satisfy a hard predicate.

## 5. Monotonicity invariant

Required target-size rungs are nested prefixes of one repaired master order. Under the current positive hard-coverage/obligation predicates, adding candidates cannot remove already covered witness mass or unsatisfy an already satisfied positive obligation.

Therefore, across increasing materializable nominal sizes, the hard-pass sequence SHALL be monotone: once a prefix passes, all larger prefixes under the identical scientific input/policy identity must also pass.

A pass/fail/pass or pass/fail suffix is an invariant violation. MVQUAL SHALL report the inconsistency and target-size preparation SHALL fail closed.

## 6. Result record

`MultiViewQualificationRecord` (or the current implementation-equivalent schema) binds:

- domain and prefix size;
- repaired-order identity;
- DATA7/FEAS1/MVIDX1 identities;
- hard policy and MVQUAL policy identities;
- independently recomputed per-family/obligation evidence;
- deterministic pass/fail result and reason codes;
- current schema/version identity.

Execution worker count, queue completion order, cache location, and equivalent runtime choices do not enter the scientific result identity.

## 7. Parallel execution

Qualification of different domains or prefix sizes may execute concurrently under bounded resource admission. Completion order is non-authoritative; persisted result ordering is canonical.

Parallelism cannot change the primitive sparse relation, FP64 predicate arithmetic, hard thresholds, or pass/fail result.

## 8. Relationship to target-size study

The target-size study defines:

```text
qualified_sizes = {
  N in materializable_sizes :
  MVQUAL(d,N).hard_pass for every required training domain d
}
```

MVQUAL supplies only the independent hard evidence for that definition. It does not train models, rank qualified sizes by learning performance, inspect held-out folds, or choose `N_selected`.

## 9. Failure conditions

MVQUAL fails closed when:

- primitive MVIDX/policy identity does not match the repaired order;
- requested membership is not the authenticated repaired prefix;
- selector/repair counters are supplied as a substitute for independent recomputation;
- a required hard predicate cannot be evaluated exactly;
- forbidden held-out/calibration/locked evidence enters the qualification policy;
- nested-prefix qualification violates monotonicity;
- persisted qualification evidence is stale, corrupt, or incompatible.

Unsupported historical qualification/comparison schemas are non-current evidence and do not define current acceptance behavior.
