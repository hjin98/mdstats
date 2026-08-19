# DOC-MVSEL2 Repository Handoff State

This file records current coordination state for the MVSEL2 branch. It is not scientific authority and is excluded from candidate product identity.

## Governing authority

- Active implementation workplan: `workplans/active/DOC-MVSEL2_HARDEN1_V3.md`
- Workplan ID/revision: `DOC-MVSEL2-HARDEN1-V3` / `1`
- Workplan SHA-256: `ac674abd68dcc43f0fe8f559aecbe913b6e9ae79194e5ff7327b2de531e2716b`
- Protocol: `3.0.0`
- Analysis base: `e24d5168ce01bf2d773339e1a91d5ded4871a57f`
- Target branch: `feat/mvsel2-forward-lazy`
- Frozen candidate commit/ref: `a9cb41ad9b1c6305de195f1a88b71ea098e582b7`
- Candidate identity policy: `mdstats.mvsel2-harden1-v3.candidate-identity.v1`
- Candidate content identity: pending clean-workstation bootstrap
- Source-lineage workplan: `workplans/active/DOC-MVSEL2_HARDEN1.md` revision 1 / protocol 2.0.1
- Original implementation workplan: `workplans/archive/DOC-MVSEL2_forward_lazy_selector.md` revision 4
- Gate approval: `AUTO`
- Merge status: **DO NOT MERGE** until Protocol-v3 qualification and independent verification pass.

## Current state

H0-H4 are implementation `PREPARED`; no unexecuted qualification check is promoted to PASS. Deterministic H6 candidate closeout is `PREPARED`: permanent Markdown/PDF/provenance, release-status truthfulness, historical-evidence wording, diagnostic-workflow removal, and handoff cleanup have been completed before the product candidate freeze.

The product/release candidate is frozen at `a9cb41ad9b1c6305de195f1a88b71ea098e582b7`. Later changes under `workplans/`, `qualification/`, and other declared coordination/evidence-only exclusions do not alter candidate content identity under the candidate policy.

The frozen scientific/algorithmic design remains unchanged: REPAIR2 mirrors REPAIR1 scientific semantics, v2 campaign execution uses native forward-only MVIDX state, interrupted MVSEL2 resumes from authenticated MVSTATE2 with exact fallback/rebase behavior, REPAIR2 reuses selector state only before divergence, rejected repair proposals do not clone full forward state, and production hardening requires the materializable fixed-eight ladder through rank 16,384.

## Division of responsibility

The implementation authority has completed deterministic repository-local closeout. Codex on the user's local workstation is now reserved for the minimum unavoidable bootstrap plus Qualification Handoff execution:

1. materialize the exact frozen candidate;
2. prove the complete clean start state, including untracked/shadowing-source review;
3. compute `candidate_content_identity` under `mdstats.mvsel2-harden1-v3.candidate-identity.v1`;
4. instantiate the exact Protocol-v3 Qualification Handoff from the prepared bootstrap contract;
5. switch to qualification authority and execute only the enumerated workstation/production-data checks;
6. record evidence and return exact failures without redesign or source mutation.

Codex must not perform general repository cleanup, documentation editing, speculative refactoring, or broad workplan continuation. Any candidate-source/test-contract defect returns to implementation and requires a new candidate identity plus dependency-appropriate requalification.

## Qualification barrier

The exact Qualification Handoff cannot be finalized until the workstation computes the candidate content identity from a clean checkout. The implementation-owned bootstrap contract is:

`qualification/handoffs/DOC-MVSEL2-HARDEN1-V3_WORKSTATION_BOOTSTRAP.md`

Qualification must not begin until that bootstrap has bound:

```text
candidate_ref = a9cb41ad9b1c6305de195f1a88b71ea098e582b7
candidate_commit = a9cb41ad9b1c6305de195f1a88b71ea098e582b7
candidate_content_identity = <recomputed clean-workstation value>
candidate_identity_policy = mdstats.mvsel2-harden1-v3.candidate-identity.v1
Qualification Handoff = exact candidate-bound handoff
```

Qualification then runs with `product_source_mutation: FORBIDDEN`. GPU qualification remains `DEFERRED_NOT_RUN` unless it is genuinely executed on supported hardware.
