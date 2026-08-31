# MLFF current multi-view target-subset chain specification

**Status:** current normative FEAS1/MVIDX1/MVSEL2/REPAIR2/MVSTATE2/MVQUAL integration contract  
**Architecture:** revision 105

## 1. Scope

This specification owns the current integrated multi-view target-subset construction chain after DATA7 fitted preparation. It defines the exact scientific relationship among FEAS1, MVIDX1, MVSEL2, REPAIR2, MVSTATE2, and MVQUAL and the current forward/lazy execution invariants.

Target-size screening after prefix qualification is owned by `mlff_target_subset_size_study_spec.md`.

There is no alternate current MVSEL1, REPAIR1, MVSTATE-REUSE1, migration, or rescue path.

## 2. Scientific input contract

For each canonical DATA5 fold/final gradient-training domain, the chain consumes one current DATA7 `TargetSubsetInputBundle` containing the fitted feature/metric, weights, conditions/provenance/correlation identities, hard obligations, representative/diversity evidence, event/environment/focus evidence, and training-domain difficulty inputs required by the selector policy.

No held-out CV, calibration, or locked-test evidence may enter these fitted inputs or target membership.

Scientific calculations use FP64 decision arithmetic unless a narrower current specification explicitly defines an exact-equivalent representation.

## 3. Exact hard-coverage contract

For feature family `m`, candidate `c`, witness `w`, fitted scaling `D_m`, and frozen witness radius `r_w^(m)`, exact adjacency is

```text
A[m,w,c] = 1 iff ||D_m (x_w^(m) - x_c^(m))||_2 <= r_w^(m)
```

The current default hard family coverage threshold is exactly:

```text
0.95
```

unless an explicitly identified material/profile policy defines another threshold for a named family. Any such override is part of scientific policy identity.

The current default floating contender tolerance for the selector/repair policy is exactly:

```text
1e-14
```

and every best-relative floating filter uses the inclusive form

```text
value >= best - tolerance
```

under the canonical FP64 reduction semantics.

Candidate, witness, family, obligation, correlation-unit, and stable UID ordering are scientific identity.

## 4. FEAS1

FEAS1 evaluates the complete eligible candidate/reference pool before progressive selection. It SHALL:

- validate exact expected support/self-support as required by the current coverage policy;
- measure candidate/witness support and fragile low-support witness mass;
- evaluate mandatory hard-obligation feasibility;
- identify capacity limitations relevant to the nominal target-size population;
- preserve candidate/reference/family/policy identities in its evidence.

FEAS1 does not relax hard coverage or invent candidate sizes when support is insufficient.

## 5. MVIDX1

MVIDX1 owns one authenticated exact sparse relation for the semantic neighborhood inputs. Its scientific identity binds at least:

- domain/candidate/reference identities and canonical ordering;
- family identities and fitted scaling/distance/radius semantics;
- exact typed sparse arrays/cardinalities;
- hard-obligation incidence and correlation-code lineage where packaged with the runtime projection;
- current schema/cache semantic version.

MVIDX1 may persist witness-oriented and candidate-oriented sparse views. The MVSEL2/REPAIR2 runtime consumes only the candidate-to-witness, candidate-to-obligation, and correlation-code projection required by the current algorithm.

Worker count, chunk size, queue order, in-memory versus file-backed inversion, mmap path, and similar execution choices are non-semantic when the authoritative sparse content is identical.

## 6. MVSEL2 sole ordering authority

MVSEL2 produces one deterministic progressive target order per canonical training domain.

### 6.1 Hard-coverage phase

During the hard-coverage phase, candidate comparison follows the current staged exact lexicographic authority:

1. maximum hard gain;
2. first canonical minimum-coverage/bottleneck family;
3. best relative bottleneck-family gain;
4. total coverage gain;
5. least-selected correlation-unit balance;
6. harmonic representative gain;
7. sparse diversity;
8. stable UID.

An implementation MAY apply exact staged scans/filters so long as every eliminated candidate is provably unable to win under the same lexicographic policy and inclusive tolerance semantics.

### 6.2 Representative phase

Once hard coverage is satisfied, the current representative-fill authority orders contenders by:

1. representative gain;
2. correlation balance;
3. diversity;
4. stable UID,

with the same current tolerance/tie semantics.

### 6.3 Forward/lazy execution

MVSEL2 uses candidate-forward sparse rows rather than complete eager inverse candidate-marginal propagation.

After the hard phase, the implementation performs an exact all-candidate rebase before constructing the certified lazy representative frontier. Cached stale scores are outward-rounded conservative upper bounds. A candidate may remain unrefreshed only while its bound proves it cannot beat the best exact contender under the frozen tolerance. Otherwise it is refreshed exactly.

Full-forward exact scoring is the correctness oracle and bounded fallback. Lazy/frontier scheduling does not change scientific rank authority.

The selected order SHALL be invariant under qualified worker count, batch size, queue order, cache location, restart point, or frontier-rebuild schedule.

## 7. REPAIR2 sole repair authority

REPAIR2 consumes the MVSEL2 order and current forward state. It preserves:

- active-shell-only repair;
- immutable protected lower prefixes;
- zero-unique/hard-safe removal admission;
- exact deficit/frontier replacement scoring;
- hard-obligation safety;
- strict no-hard-coverage regression;
- current objective/tolerance/tie hierarchy;
- rank inheritance and deterministic future displacement;
- bounded passes/swaps/shortlist behavior as defined by current repair policy;
- deterministic accepted/rejected repair trace.

Hypothetical proposal scoring may execute concurrently within one immutable pre-swap state. Authoritative winner comparison and accepted state mutation remain deterministic.

REPAIR2 publishes one repaired master order per domain. Candidate target sizes are prefixes of this single order; independent per-rung repair is prohibited.

## 8. MVSTATE2 current continuation state

Current continuation-state records use the MVSTATE2 family. A state record binds at least:

- dataset/domain identity;
- canonical candidate UID and family order;
- DATA7/FEAS1/MVIDX1 identities;
- witness weights and hard obligations;
- correlation-unit identities;
- selector/repair policy identity;
- exact selected prefix/order state;
- current schema/version identity.

The durable compact payload contains the exact continuation quantities required by the current algorithm, including witness multiplicity, family covered mass, obligation counts, correlation counts, and representative utility/state.

Complete per-candidate marginal arrays and ephemeral lazy-heap contents are not durable authority.

Publication SHALL be transactional/authenticated. Restoration SHALL validate manifest/payload integrity and recompute continuation invariants from the selected prefix before use.

An artifact that does not validate as current MVSTATE2 is rejected/reconstructed or requires campaign re-preparation. Historical state is not migrated into current authority.

## 9. MVQUAL independent qualification

MVQUAL independently recomputes the hard coverage/obligation evidence for required repaired prefixes using authenticated primitive sparse inputs.

It SHALL NOT accept MVSEL2/REPAIR2 internal counters as independent qualification evidence.

A qualification record binds the requested domain/prefix size and current identities and reports, as applicable:

- per-family coverage and deficit;
- uncovered weighted mass/count;
- mandatory-obligation satisfaction;
- redundancy and unique-support diagnostics;
- provenance/correlation diagnostics;
- current pass/fail result.

MVQUAL completion order may be parallel/non-authoritative; persisted result ordering and scientific predicates are deterministic.

## 10. Nested-prefix invariant

For repaired master order `pi[d]`,

```text
D[d,N] = pi[d][:N]
```

and for `N2 > N1`,

```text
D[d,N1] is a strict prefix/subset of D[d,N2].
```

Under the fixed positive hard coverage/obligation predicates, hard satisfaction cannot regress as `N` grows. A pass/fail/pass qualification sequence is a hard invariant failure and SHALL stop target-size preparation.

## 11. Resource contract

The chain SHALL be realizable at target scale with one product-scale sparse/selection authority per semantic domain identity rather than one copy per target-size rung.

Current execution MUST NOT require:

- witness-to-candidate inverse arrays to be mapped by MVSEL2/REPAIR2 normal execution;
- complete per-candidate marginal arrays as durable selector state;
- an independent descriptor/MVIDX/selector/repair copy for each nominal target size.

Out-of-core sparse inversion, mmap/file-backed arrays, chunking, queue backpressure, and reconstructible caches are permitted exact execution realizations under their current runtime specifications.

## 12. Qualification requirements

A release implementation of this current chain requires evidence covering, as applicable:

- exact MVIDX sparse-array validation;
- deterministic order/repair equality across qualified worker/batch/restart/frontier schedules;
- lazy-versus-full-forward oracle equality;
- MVSTATE2 corruption/staleness/restart checks;
- independent MVQUAL equality to its current predicate definitions;
- nesting and hard-coverage monotonicity over the nominal/materializable prefixes used by the size-study policy;
- bounded RAM/scratch/restart behavior at representative target scale;
- performance evidence demonstrating that the exact forward/lazy realization is suitable for production-scale selection.

Performance qualification does not authorize a scientific-policy change, and GPU qualification is not implied by CPU/sparse-chain qualification.

## 13. Unsupported historical artifacts

Current new-campaign schemas/identities are the current MVSEL2/REPAIR2/MVSTATE2/MVQUAL families defined by the implementation specifications. Old MVSEL1, REPAIR1, MVSTATE-REUSE1, generated-size rescue, and migration records are non-current historical evidence only.

There is no requirement that current readers preserve their construction/runtime semantics. If an old campaign cannot validate against the current generation, the user must re-prepare it.
