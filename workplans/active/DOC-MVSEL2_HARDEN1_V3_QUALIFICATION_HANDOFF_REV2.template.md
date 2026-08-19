# DOC-MVSEL2-HARDEN1-V3 revision-2 handoff template

Instantiate this template only from `DOC-MVSEL2_HARDEN1_V3_REV2.md` and preserve failed revision-1 handoffs/reports as historical evidence.

Required bindings:

- protocol version `3.0.0`;
- workplan ID `DOC-MVSEL2-HARDEN1-V3`, revision 2, exact SHA-256;
- exact candidate ref/commit/content identity and identity policy;
- Q3 baseline commit `e24d5168ce01bf2d773339e1a91d5ded4871a57f`;
- Q3 comparator policy `mdstats.mvsel2-harden1-v3.q3-diff.v1` and exact comparator blob SHA;
- production DB/domain and expected 36,408-candidate/165-family identity;
- `product_source_mutation: FORBIDDEN`;
- declared qualification/evidence/scratch write paths only.

The instantiated handoff MUST retain these acceptance semantics:

1. Q1 and Q2 are absolute PASS checks.
2. Q3 runs the exact baseline and candidate in the same material target environment, emits legacy-family JUnit XML for both, and passes only when the deterministic comparator reports zero candidate-only failure/error signatures and zero baseline-PASS-to-candidate-FAIL/ERROR regressions. Pytest exit 1 is valid differential input; infrastructure/collection aborts are not.
3. Q4 builds/installs the wheel and performs installed-origin import from outside repository root using an absolute target `PYTHONPATH`; wheel contents must exclude `workplans/`.
4. Q5-Q7 retain the revision-1 absolute production continuation, full-ladder REPAIR2, StageResourceScope, production-input immutability, and >=10x combined-chain requirements.
5. Q8 remains nonblocking `DEFERRED_NOT_RUN` unless genuinely executed.
6. Postflight recomputes candidate identity and forbids candidate/source mutation.

Evidence reuse is dependency-bound. Revision-1 Q3 is diagnostic only and cannot become revision-2 PASS evidence without the required structured baseline/candidate differential artifacts. Revision-1 Q4 is invalidated and must rerun.
