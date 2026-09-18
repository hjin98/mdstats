---
kind: author-repair-closure
protocol_version: 6.4.0
status: READY_FOR_FRESH_INDEPENDENT_R4_REVIEW
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
accepted_basis: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
prior_review: workplans/active/MLFF_D1_D2_SSDP64_INDEPENDENT_REVIEW_R3.md
prior_immutable_target: 045cb5a052fdb83b6c6cd561142b24fdf5d023b5
primary_d4_evidence_commit: dbe6c552b216d583caf9230d2c1e0879b68f8c3e
primary_d4_evidence_run: 35300235175
confirmatory_d4_evidence_commit: 17af93877ba312600ab1bf7a2f1f2990c9c2ef00
confirmatory_d4_evidence_run: 35300268107
pem_basis: hjin98/mdstats@b5d101d8f73d3efd63ef4e70b3913e7d281406ce:PROJECT-ENGINEERING-MEMORY.md
---

# MLFF D1/D2 Protocol-6.4 R4 repair closure

## 1. Author-side disposition

Independent R3 review returned **NO-PASS** on immutable target
`045cb5a052fdb83b6c6cd561142b24fdf5d023b5` without a Serious Challenge to
accepted D1/D2. R4 repairs only the two R3 blockers:

1. incomplete direct semantic dependency representation; and
2. missing current affected-surface D4 executable acceptance evidence.

No accepted D1 or D2 scientific/numerical meaning is changed. The exact R3 D1
and D2 kernel blobs are reused unchanged:

- D1 blob `dc05bc0a8fe5790b6ffe91bfacbd2bb25360a498`;
- D2 blob `74c0c0588617b7f48fd93bc21e534f538f037ef8`.

The direct D4 weighted-quantile owner and focused regression are also unchanged
from the R3 reviewed source:

- `coverage_reference.py` blob `15d20eae5a7b481d636d20fc2281c743e9abe0df`;
- focused FP64 regression blob `8da42708ac601b335dfb3c9d818c302baccb1a78`.

The R4 representation repair is
`workplans/active/MLFF_D1_D2_SSDP64_DEFINITION_DEPENDENCY_TRACE_R4_FINAL.md`.
The R3 trace is superseded authoring history and no longer composes with R4.

## 2. R3-B1 — direct dependency completeness: closed author-side

R3's clearest falsifier was the typed-failure object `D2.DEF.062`, whose direct
trace omitted owners of non-finite P3 outcomes, reducer insufficiency, checkpoint
admissibility, P5 objective and P5 exposure. R4 did not patch only those five
witnesses. It re-walked every formal object in the bounded D1/D2 candidate.

The repaired trace adds direct semantic edges where changing the prerequisite
can directly change the subject's denotation, validity, failure classification,
comparison relation or interpretation. Additional omissions found and repaired
during the complete pass include selector winner/oracle, repair, MVQUAL,
reducer/restart, replay/production and authenticated-continuation surfaces.

The R3 required `D2.DEF.062` edges are all explicit in R4, including:

- `D2.DEF.045` — foundation-P5 objective;
- `D2.DEF.047` — P3 estimator and finite complete-seed score;
- `D2.DEF.049` — structural funnel/comparison sufficiency;
- `D2.DEF.053` — combined corpus/update geometry;
- `D2.DEF.058` — role-effective checkpoint admissibility.

Author-side structural checks over the complete R4 trace found:

- 106 candidate formal subjects;
- 106 subjects represented exactly once;
- no unresolved prerequisite endpoint;
- every prerequisite resolving to a candidate object or exact basis-pinned
  import/root;
- no object-to-object cycle.

The audit explicitly challenged currentness, continuation and equivalence rather
than treating their R3 rows as presumptively complete. `D2.DEF.060A` remains a
relation-selection registry rather than a dependency shortcut to every
value-producing definition; locally owned nonzero tolerance/guard relations and
basis-pinned source-owned relations remain the direct prerequisites.

These checks are author evidence only. Fresh R4 review must independently
reconstruct directness and reverse-impact closure.

## 3. R3-B2 — D4 executable acceptance: closed author-side

The D4 source repair itself was accepted numerically by R3 but lacked executed
affected-surface real-owner evidence. R4 executed both required commands through
GitHub Actions on the actual repository owner chain.

Primary passing evidence is commit
`dbe6c552b216d583caf9230d2c1e0879b68f8c3e`, workflow run
`35300235175`:

```text
pytest -q tests/test_mlff_target_order_weighted_quantiles_fp64.py
pytest -q tests/test_mlff_target_order_real_owner.py
```

Both steps completed successfully.

The validation environment is CPU-only Python 3.11 with the supported MLFF
runtime: CPU PyTorch, `mace-torch==0.3.16`, `ase==3.29.0`, project
`.[manifest]`, pytest and Hypothesis. The workflow's
`Record validation environment` step records the resolved package versions in
the immutable Actions run. No GPU qualification was executed or required.

A confirmatory run on descendant evidence commit
`17af93877ba312600ab1bf7a2f1f2990c9c2ef00`, workflow run
`35300268107`, independently completed the same two required test commands
successfully after installing the supported CPU MACE stack plus Hypothesis.

### Diagnostic evidence retained rather than hidden

Earlier validation attempts are not treated as product failures or discarded:

- a minimal project-only environment passed the focused FP64 regression but the
  assembled real-owner suite reached optional MLFF runtime imports absent from
  that environment;
- adding CPU PyTorch exposed missing `torch_ema`;
- installing the supported MACE 0.3.16 runtime supplied that dependency and
  exposed the real-owner suite's property-test dependency `hypothesis`;
- once the supported runtime and test dependency were present, the exact
  required suite passed.

The same real-owner tests had also passed one-by-one in fresh processes before
the complete environment was installed. Those isolated passes were correctly
not substituted for the required shared-process full-file command.

No product code, numerical tolerance, test oracle or acceptance predicate was
weakened to obtain the pass.

## 4. R4 candidate scope

The proposed R4 assembled candidate consists of:

- unchanged R3 D1 kernel
  `MLFF_D1_SSDP64_AXIOMATIC_AUTHORITY_R3_REPAIRED.md`;
- unchanged R3 D2 kernel
  `MLFF_D2_SSDP64_AXIOMATIC_AUTHORITY_R3_REPAIRED.md`;
- repaired R4 direct dependency trace
  `MLFF_D1_D2_SSDP64_DEFINITION_DEPENDENCY_TRACE_R4_FINAL.md`;
- the already-reviewed direct D4 weighted-quantile repair;
- its corrected FP64 falsification regression;
- the accepted renderer-only scoped-D2 formula correction;
- prior review/repair records needed to challenge the candidate.

The temporary `.github/workflows/r4-target-order-validation.yml` exists only as
execution evidence machinery and is removed from the R4 semantic target. It is
not product architecture, D4 authority, or a permanent CI addition.

## 5. R4 gate

The next commit after this closure is the new immutable R4 semantic target. A
descendant handoff must bind that exact SHA.

Fresh independent R4 review must review the entire assembled candidate against
accepted basis `cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`, not merely confirm
R3-B1/R3-B2. It must reattempt prior blocker classes, challenge the complete R4
trace and inspect the current executable evidence independently.

A fresh **PASS** remains prerequisite to stakeholder ratification and canonical
promotion. This author closure is not a review verdict and does not self-ratify
the candidate.
