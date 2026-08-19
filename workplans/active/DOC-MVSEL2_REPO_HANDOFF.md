# DOC-MVSEL2 Repository Handoff State

This file records current coordination state for the MVSEL2 branch. It is not scientific authority and is excluded from candidate product identity.

## Governing authority

- Active implementation workplan: `workplans/active/DOC-MVSEL2_HARDEN1_V3.md`
- Workplan ID/revision: `DOC-MVSEL2-HARDEN1-V3` / `1`
- Workplan SHA-256: `ac674abd68dcc43f0fe8f559aecbe913b6e9ae79194e5ff7327b2de531e2716b`
- Protocol: `3.0.0`
- Analysis base: `e24d5168ce01bf2d773339e1a91d5ded4871a57f`
- Target branch: `feat/mvsel2-forward-lazy`
- Source-lineage workplan: `workplans/active/DOC-MVSEL2_HARDEN1.md` revision 1 / protocol 2.0.1
- Original implementation workplan: `workplans/archive/DOC-MVSEL2_forward_lazy_selector.md` revision 4
- Gate approval: `AUTO`
- Merge status: **DO NOT MERGE** until Protocol-v3 qualification and independent verification pass.

## Current state

The v3 hardening implementation for H0-H4 is source-prepared. `PREPARED` is not a qualification or acceptance PASS. H5 target qualification has not run. H6 may finalize candidate documentation/generated product artifacts before qualification, but final evidence claims, workplan completion, archive movement, and merge-readiness remain downstream verification responsibilities.

The frozen scientific/algorithmic design remains unchanged: REPAIR2 mirrors REPAIR1 scientific semantics, v2 campaign execution uses native forward-only MVIDX state, interrupted MVSEL2 resumes from authenticated MVSTATE2 with exact fallback/rebase behavior, REPAIR2 reuses selector state only before divergence, rejected repair proposals do not clone full forward state, and production hardening requires the materializable fixed-eight ladder through rank 16,384.

## Division of responsibility

Repository-local implementation closeout is owned by the implementation authority and should be completed before consuming target-environment qualification capacity. This includes source/test/harness construction, documentation and release-metadata truthfulness, permanent generated product artifacts, removal of temporary diagnostics, cheap/available structural checks, and candidate-freeze preparation.

Codex on the user's local workstation is reserved for the Qualification Handoff only: materialize the exact frozen candidate in the prescribed `mace` environment, prove a clean start state and candidate content identity, execute the enumerated target-environment/production-data checks, record evidence, and return exact failures to implementation. Codex must not redesign or broadly continue the workplan.

## Qualification barrier

Before the first qualification test, implementation must establish and bind:

```text
candidate_ref
candidate_commit
candidate_content_identity
candidate_identity_policy
Qualification Handoff
```

Qualification then runs with `product_source_mutation: FORBIDDEN`. Any required product/source correction returns to implementation, produces a new candidate identity, and invalidates dependent evidence as defined by the handoff.

GPU qualification remains `DEFERRED_NOT_RUN` unless it is genuinely executed on supported hardware.
