---
kind: independent-review-handoff
protocol_version: 6.4.0
status: AWAITING_FRESH_INDEPENDENT_R4_REVIEW
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
accepted_basis: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
immutable_candidate_target: 86fa8acec3cfc84584bfbd380163545d80de7a27
prior_candidate_target: 045cb5a052fdb83b6c6cd561142b24fdf5d023b5
prior_review_result: R3_NO_PASS
primary_d4_evidence_commit: dbe6c552b216d583caf9230d2c1e0879b68f8c3e
primary_d4_evidence_run: 35300235175
confirmatory_d4_evidence_commit: 17af93877ba312600ab1bf7a2f1f2990c9c2ef00
confirmatory_d4_evidence_run: 35300268107
branch: design/mlff-d1-d2-ssdp64-axiomatic-formalization
pem_basis: hjin98/mdstats@b5d101d8f73d3efd63ef4e70b3913e7d281406ce:PROJECT-ENGINEERING-MEMORY.md
---

# Independent Review R4 handoff — MLFF D1/D2 Protocol-6.4 formalization

## 1. Binding target and independence

Perform a fresh independent Protocol-6.4 assembled-candidate Review of immutable
target

`86fa8acec3cfc84584bfbd380163545d80de7a27`

against accepted basis

`cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`.

This is a full-candidate review, not a delta acceptance of R4 author closure.
Treat `MLFF_D1_D2_SSDP64_R4_REPAIR_CLOSURE.md`, all earlier reviews/handoffs,
PR comments, implementation behavior and Actions results as evidence/challenges
only. Do not inherit their conclusions.

At handoff creation `main` still resolves exactly to the accepted basis above.
Re-resolve it before verdict.

No Serious Challenge was raised by R3 against accepted D1/D2. If fresh review
finds accepted authority itself materially false, contradictory, ambiguous or
impossible to concretize, raise the Challenge at the owning layer rather than
silently repairing the proposal.

## 2. Exact R4 candidate surface

Proposed D1/D2 kernels are the exact R3-reviewed blobs, unchanged in R4:

- `workplans/active/MLFF_D1_SSDP64_AXIOMATIC_AUTHORITY_R3_REPAIRED.md`,
  blob `dc05bc0a8fe5790b6ffe91bfacbd2bb25360a498`;
- `workplans/active/MLFF_D2_SSDP64_AXIOMATIC_AUTHORITY_R3_REPAIRED.md`,
  blob `74c0c0588617b7f48fd93bc21e534f538f037ef8`.

R4 replaces only the derived direct-dependency representation:

- `workplans/active/MLFF_D1_D2_SSDP64_DEFINITION_DEPENDENCY_TRACE_R4_FINAL.md`,
  blob `c9b0ebf193845fe24b3c3cfb22a5389a18704e4a`.

Executable descendant and focused oracle remain byte-identical to R3:

- `mdstats/training_data/target_order/coverage_reference.py`,
  blob `15d20eae5a7b481d636d20fc2281c743e9abe0df`;
- `tests/test_mlff_target_order_weighted_quantiles_fp64.py`,
  blob `8da42708ac601b335dfb3c9d818c302baccb1a78`.

The candidate also retains the accepted renderer-only scoped-D2 formula repair
and all prior review/repair records required to reconstruct history. The
temporary R4 validation workflow is absent from the immutable target.

## 3. Required full assembled review

Reconstruct accepted D1/D2 independently from the four canonical method papers
at `cb07d683...`; do not use the proposed kernels as source of truth.

Reattempt every material D1/D2 surface reviewed in R3 and all previous blocker
classes. In particular reattempt R1 B1-B9, R2 B1-B4, and both R3 blockers.
Prior closure statements are evidence only.

R4 intentionally leaves the R3 D1/D2 kernels unchanged. A newly observed
semantic defect in those kernels is therefore a fresh candidate finding, not
something waived by the narrow R4 repair scope.

## 4. R3-B1 falsification target — R4 dependency trace

Independently inspect all 106 formal subjects. Do not accept the R4 author audit
count as proof.

For every subject ask whether changing a claimed prerequisite can directly
change the subject's denotation, domain, validity, failure classification,
comparison relation or interpretation, and whether every such direct
prerequisite is represented. Keep transitive-only prerequisites omitted.

At minimum challenge:

- `D2.DEF.030-032` selector decision/oracle dependencies;
- `D2.DEF.035-037` and `D2.AX.002` repair/reconstruction dependencies;
- `D2.DEF.038` independent MVQUAL metric/radius/adjacency dependencies;
- `D2.DEF.049-050` and `D2.AX.003` P3 funnel/score/restart dependencies;
- `D2.DEF.051A` selected-head versus target-E0 distinction;
- `D2.AX.004-005` currentness/fresh-production ownership;
- `D2.DEF.060` authenticated continuation boundary;
- `D2.DEF.060A-061` equivalence-relation ownership without a generic
  equality/tolerance escape hatch;
- `D2.DEF.062` typed failure set.

For `D2.DEF.062`, verify direct reachability includes at least
`D2.DEF.045`, `D2.DEF.047`, `D2.DEF.049`, `D2.DEF.053`, and
`D2.DEF.058`, the five concrete R3 falsifiers.

Also independently verify every formal subject occurs exactly once, every
prerequisite resolves, D1 has no downward D2 dependency, no accidental SCC
exists, parameter/source reverse-impact closure is adequate, and no generic
policy/provider/equality/tolerance endpoint has reappeared.

## 5. R3-B2 falsification target — D4 real-owner evidence

Verify the real weighted-quantile owner still consumes once-normalized stored
weights with direct `q` comparison and contains no second normalization,
tolerance widening or fallback path.

Primary current executable evidence:

- commit `dbe6c552b216d583caf9230d2c1e0879b68f8c3e`;
- Actions run `35300235175`;
- Python 3.11, CPU PyTorch, `mace-torch==0.3.16`,
  `ase==3.29.0`, project `.[manifest]`, pytest and Hypothesis;
- resolved package versions are emitted by the workflow environment-record step;
- both required commands passed:

```text
pytest -q tests/test_mlff_target_order_weighted_quantiles_fp64.py
pytest -q tests/test_mlff_target_order_real_owner.py
```

Confirmatory evidence:

- commit `17af93877ba312600ab1bf7a2f1f2990c9c2ef00`;
- Actions run `35300268107`;
- both required commands passed again in the supported CPU MLFF/test stack.

Review the diagnostic history rather than hiding it. Earlier minimal
environments exposed missing runtime/test dependencies (`torch`,
`torch_ema`, then `hypothesis`); no production code, numerical tolerance,
oracle or test predicate was changed to obtain the passing evidence.

The validation workflow is intentionally absent from immutable target
`86fa8ace...`; it was evidence machinery only. The D4 source/test blobs tested
by the passing evidence are unchanged in this target.

GPU qualification remains outside this cycle.

## 6. Renderer, PEM/HAS and currentness

Recheck the scoped-D2 renderer correction and the prior unsupported syntax
classes. Re-resolve accepted `main`, Project Engineering Memory and Historical
Applicability Set before verdict.

Carry forward only after independent challenge:

```yaml
has:
  - {id: SP-001, disposition: APPLICABLE}
  - {id: SP-002, disposition: APPLICABLE}
  - {id: SP-003, disposition: APPLICABLE}
  - {id: SP-004, disposition: APPLICABLE}
  - {id: FF-001, disposition: APPLICABLE}
  - {id: FF-002, disposition: APPLICABLE}
  - {id: FF-003, disposition: NOT_APPLICABLE}
  - {id: FF-004, disposition: NOT_APPLICABLE}
  - {id: FF-005, disposition: APPLICABLE}
```

PEM/HAS remain evidence/history, not semantic authority.

## 7. Verdict and lifecycle

Return **PASS** only if the complete immutable R4 target is losslessly
equivalent to accepted D1/D2, definition/source/dependency closed,
renderer-safe, and its D4 descendant is cleanly integrated with current
real-owner evidence. Otherwise return **NO-PASS** with precise owner-level
repair instructions and keep the workplan reopened.

A PASS does not ratify or promote the proposal. Stakeholder ratification of the
exact reviewed target remains required before canonical D1/D2
promotion/reconciliation.
