---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P6
protocol_version: 5.8.0
revision: 13
status: active
amended_date: 2026-08-31
current_authority_pointer: true
latest_reviewed_candidate_commit: 84b2af7ba1117065c33f58f504a852e3000dbe8a
latest_reviewed_candidate_tree: 5f5fb7d5fb6e255ecd47e20c05477b2d58cc1589
precedence: this file is the current revision-13 authority pointer; read the composed revision-13 authority plus the final-candidate binding addendum below as one contract
---

# P6 revision 13 — current authority pointer

Implementation and review must treat the following supplied files as one current P6 revision-13 contract:

1. `P6_REVISION_13_AUTHORITY.md` — composed P6 revisions 3-13 authority and frozen R13 proxy-proof/acceptance contract.
2. `P6_REVISION_13_FINAL_PROXY_PROOF_AND_EXECUTION_EVIDENCE_CLOSURE_AMENDMENT.md` — R13 proxy-proof and executable-evidence closure requirements.
3. `P6_REVISION_13_FINAL_CANDIDATE_IDENTITY_AND_EVIDENCE_BINDING_ADDENDUM.md` — latest independent-review correction governing final executable candidate identity, `normalize.py`/`tests/conftest.py` reconciliation, post-test mutation rules, exact `-n 16` final regression, and evidence binding.

The third file has precedence only where it explicitly tightens or replaces final-candidate/evidence-binding details. It does **not** reopen or replace accepted scientific, multi-seed P5, storage, P3/P5 owner, A/B/C, parser-lifecycle, or documentation semantics from the composed P6 authority.

## Current disposition

P6 revision 13 remains **active / NO PASS pending implementation closure**.

The accepted R13-A receipt and R13-B real-external-pointer proxy-test designs are frozen. The remaining implementation work is exactly the bounded final-candidate/evidence-binding closure in `P6_REVISION_13_FINAL_CANDIDATE_IDENTITY_AND_EVIDENCE_BINDING_ADDENDUM.md`.

Do not create P6 revision 14 unless a stated Design-reopen trigger in that addendum fires.

P7 remains planned and may begin only after independent P6 revision-13 PASS. The post-P7 storage/I-O reset remains gated behind P6 revision-13 PASS and the current P7 predecessor authority.
