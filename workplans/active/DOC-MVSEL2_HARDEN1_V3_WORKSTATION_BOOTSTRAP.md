---
kind: qualification-bootstrap
bootstrap_id: DOC-MVSEL2-HARDEN1-V3-WORKSTATION-BOOTSTRAP-1
protocol_version: 3.0.0
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 1
workplan_sha256: ac674abd68dcc43f0fe8f559aecbe913b6e9ae79194e5ff7327b2de531e2716b
candidate_ref: a9cb41ad9b1c6305de195f1a88b71ea098e582b7
candidate_commit: a9cb41ad9b1c6305de195f1a88b71ea098e582b7
candidate_content_identity: PENDING_CLEAN_WORKSTATION_PREFLIGHT
candidate_identity_policy: mdstats.mvsel2-harden1-v3.candidate-identity.v1
status: BOOTSTRAP_REQUIRED_BEFORE_QUALIFICATION
product_source_mutation: FORBIDDEN
---

# DOC-MVSEL2-HARDEN1-V3 workstation qualification bootstrap

This file is an implementation-owned bootstrap contract, not yet the final Protocol-v3 Qualification Handoff. Its only purpose is to bind the workstation-only clean-checkout candidate content identity and instantiate the exact handoff. Do not begin qualification checks until the bootstrap completes successfully.

## Frozen authority

- Candidate commit/ref: `a9cb41ad9b1c6305de195f1a88b71ea098e582b7`
- Candidate branch provenance: `feat/mvsel2-forward-lazy`
- Workplan: `workplans/active/DOC-MVSEL2_HARDEN1_V3.md`, revision 1
- Workplan SHA-256: `ac674abd68dcc43f0fe8f559aecbe913b6e9ae79194e5ff7327b2de531e2716b`
- Protocol: `3.0.0`
- Candidate identity policy: `mdstats.mvsel2-harden1-v3.candidate-identity.v1`
- Candidate identity implementation: `scripts/mvsel2_harden1_v3_candidate_identity.py`
- Target environment: user's local workstation, Conda environment `mace`
- Product source mutation: `FORBIDDEN`
- GitHub-hosted Actions are not an authorized substitute for this workstation qualification.

## Bootstrap preflight — implementation authority only

Run from the repository root. The checkout must contain the frozen candidate itself, not the later coordination-only branch HEAD.

```bash
git checkout --detach a9cb41ad9b1c6305de195f1a88b71ea098e582b7
git rev-parse HEAD
git status --porcelain=v1 --untracked-files=all
sha256sum workplans/active/DOC-MVSEL2_HARDEN1_V3.md
```

Required observations:

- `git rev-parse HEAD` is exactly `a9cb41ad9b1c6305de195f1a88b71ea098e582b7`;
- `git status --porcelain=v1 --untracked-files=all` is empty before qualification outputs are created;
- no undeclared untracked/shadowing source, alternate checkout, editable install, or import path can supersede the candidate;
- workplan digest is exactly `ac674abd68dcc43f0fe8f559aecbe913b6e9ae79194e5ff7327b2de531e2716b`.

If any condition fails, STOP. Do not qualify an ambiguous or dirty candidate.

Create qualification output directories only after the clean-state observation, then compute the candidate identity:

```bash
mkdir -p qualification/evidence qualification/tmp
conda run -n mace python scripts/mvsel2_harden1_v3_candidate_identity.py \
  --repo . \
  --manifest workplans/active/DOC-MVSEL2_HARDEN1_V3_CANDIDATE_IDENTITY.json
```

The emitted object must report:

- `candidate_commit = a9cb41ad9b1c6305de195f1a88b71ea098e582b7`;
- `candidate_identity_policy = mdstats.mvsel2-harden1-v3.candidate-identity.v1`;
- a concrete `candidate_content_identity` beginning with `sha256:`.

The identity script excludes declared coordination/evidence surfaces but does not itself reject untracked `??` entries. The explicit full `git status --porcelain=v1 --untracked-files=all` check above is therefore mandatory.

## Instantiate the exact Qualification Handoff

Still acting as implementation authority, copy/fill the Protocol-v3 `qualification_handoff_template.md` into:

`workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_HANDOFF.md`

Bind the exact value emitted by the identity script and retain all frozen fields above. The final handoff must use:

```yaml
status: PREPARED_FOR_QUALIFICATION
product_source_mutation: FORBIDDEN
allowed_write_paths:
  - qualification/evidence/
  - qualification/tmp/
  - build/
  - dist/
```

`build/` and `dist/` are ephemeral qualification outputs only for clean build/install verification. Do not adopt or commit their products as candidate content during qualification.

Before switching roles, compute and record the SHA-256 digest of the completed handoff. From this point forward, product source/tests/specifications/configuration/package metadata/tracked generated candidate outputs are immutable.

## Required qualification checks to encode in the exact handoff

The final handoff must enumerate these checks separately with exact commands, evidence paths, retry modes, and dependencies. Missing target data/environment yields `BLOCKED`, not PASS.

### Q1 — focused v2 hardening regressions

```bash
conda run -n mace pytest -q \
  tests/test_mlff_repair2.py \
  tests/test_mlff_mvstate2.py \
  tests/test_mlff_mvsel2_forward.py \
  tests/test_mlff_mvmigrate2.py \
  tests/test_mlff_mvsel2_hardening.py
```

Expected: exit 0. Mandatory for current acceptance. Retry: `CLEAN_RETRY`, at most one retry after removing only declared ephemeral pytest/build cache/output state.

### Q2 — adjacent v1 regression

```bash
conda run -n mace pytest -q tests/test_mlff_target_data2c_repair1.py
```

Expected: exit 0. Mandatory for current acceptance. Retry: `CLEAN_RETRY`, at most one retry limited to ephemeral cache/output cleanup.

### Q3 — full non-slow suite

```bash
conda run -n mace pytest -q -m 'not slow'
```

Expected: exit 0. Mandatory for current acceptance. Retry: `CLEAN_RETRY`, at most one retry limited to ephemeral cache/output cleanup.

### Q4 — clean build/install/import/package-content verification

The exact handoff must bind the repository's existing build backend and use a clean ephemeral build/install location under the allowed paths. It must verify at minimum:

- wheel build succeeds from the frozen candidate;
- installation succeeds in an isolated qualification target/environment;
- `mdstats` imports from the installed artifact rather than the source tree;
- reported package/version identity is correct for the candidate;
- `workplans/` is absent from the built wheel/install surface;
- no tracked candidate file changes.

Do not modify packaging metadata to make this check pass. A packaging/source defect is `RETURN_TO_IMPLEMENTATION`.

### Q5 — production MVSEL2 / MVSTATE2 continuation and selector evidence

Bind the real production campaign database/input identities before execution. Exercise the authenticated MVSEL2 authority and interrupted/resumed MVSTATE2 continuation required by the workplan, including corrupt/newest-checkpoint fallback and exact resumed/uninterrupted equivalence where the production workflow exposes those paths. Record code SHA, input/campaign identity, wall/resource telemetry, state mode, and exact persisted authority/digest comparisons.

Missing production data is `BLOCKED`, never substituted with a smaller fixture.

### Q6 — full-eight-rung production REPAIR2 harness

Bind `<CAMPAIGN_DATABASE>` and `<DOMAIN>` to the real 36,408-candidate / 165-family production graph before execution, then run:

```bash
conda run -n mace python benchmarks/benchmark_mlff_mvsel2_harden1_v3_repair2_production.py \
  <CAMPAIGN_DATABASE> \
  --domain <DOMAIN> \
  --workplan-sha256 ac674abd68dcc43f0fe8f559aecbe913b6e9ae79194e5ff7327b2de531e2716b \
  --expected-candidate-count 36408 \
  --expected-family-count 165 \
  --output qualification/evidence/mvsel2_harden1_v3_repair2_production.json
```

Expected: exit 0 and all materializable fixed-eight rungs `(128, 256, 512, 1024, 2048, 4096, 8192, 16384)` measured. Evidence must show default REPAIR2 policy, per-rung wall/proposals/shortlist/swaps/state mode/RSS, `proposal_full_state_copies_zero=true`, forward-only reader behavior, and `inverse_mutation_false=true`.

Retry: `NONE` unless the exact handoff explicitly permits an identical or resumable retry without changing candidate/input/scientific/resource policy.

### Q7 — StageResourceScope-wrapped production campaign integration and performance floor

The standalone Q6 harness is not sufficient for this check. Execute the real campaign integration path under its existing `StageResourceScope` boundary against the same bound production inputs. Capture resource telemetry and the selector + checkpoint/resume + repair chain measurement required to establish the governing same-host at-least-10x floor versus the frozen MVSEL1 baseline/projection.

The final handoff must bind the exact existing campaign CLI/config invocation after inspecting the workstation's already-established production campaign command/config; do not invent or alter scientific/resource configuration merely to obtain a PASS. Missing required baseline/input/environment is `BLOCKED`.

### Q8 — GPU status

Record `DEFERRED_NOT_RUN` unless GPU qualification is genuinely and explicitly executed. GPU is not to be inferred from CPU evidence.

## Qualification role switch

Only after the exact handoff has a concrete candidate content identity and digest should Codex switch to `software-qualification` and execute it. Qualification must not perform repository-wide design reconnaissance or source cleanup.

Every check result is exactly one of `PASS`, `FAIL`, `BLOCKED`, `NOT RUN`, or `DEFERRED`. `overall_status: PASS` is permitted only when every check mandatory for current acceptance has actually passed.

## Postflight

After all attempted checks:

1. recompute `candidate_content_identity` and require exact equality with the preflight value;
2. verify tracked candidate surfaces remain unchanged;
3. record the complete postflight dirty/untracked state and confirm changes are confined to declared ephemeral/evidence paths;
4. produce the Protocol-v3 Qualification Report bound to the exact handoff digest and candidate identity;
5. do not declare `MERGE_READY`; route the evidence to independent `software-verification`.

## Failure routing

- product source/test-contract defect -> `RETURN_TO_IMPLEMENTATION`;
- frozen-design contradiction -> `DESIGN_REVISION_REQUIRED`;
- missing production input/environment/hardware -> `BLOCKED`;
- dirty/ambiguous candidate identity -> stop before qualification;
- no silent source patching, package-metadata editing, threshold changes, dataset reductions, or backend/resource-policy substitutions are permitted.
