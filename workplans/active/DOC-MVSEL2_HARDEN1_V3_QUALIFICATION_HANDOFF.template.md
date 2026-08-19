---
kind: qualification-handoff
handoff_id: DOC-MVSEL2-HARDEN1-V3-QUAL-1
protocol_version: 3.0.0
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 1
workplan_sha256: ac674abd68dcc43f0fe8f559aecbe913b6e9ae79194e5ff7327b2de531e2716b
candidate_ref: a9cb41ad9b1c6305de195f1a88b71ea098e582b7
candidate_commit: a9cb41ad9b1c6305de195f1a88b71ea098e582b7
candidate_content_identity: __CANDIDATE_CONTENT_IDENTITY__
candidate_identity_policy: mdstats.mvsel2-harden1-v3.candidate-identity.v1
status: PREPARED_FOR_QUALIFICATION
product_source_mutation: FORBIDDEN
allowed_write_paths:
  - qualification/evidence/
  - qualification/tmp/
  - build/
  - dist/
---

# DOC-MVSEL2-HARDEN1-V3 Qualification Handoff

This is the implementation-owned Protocol-v3 execution contract for the frozen MVSEL2 hardening candidate. The workstation bootstrap binds the five unique tokens in this template and emits `workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_HANDOFF.md`. Qualification must consume only the bound artifact and its recorded SHA-256.

## Prepared candidate

- Candidate commit/ref: `a9cb41ad9b1c6305de195f1a88b71ea098e582b7`
- Workplan: `workplans/active/DOC-MVSEL2_HARDEN1_V3.md`, revision 1
- Workplan SHA-256: `ac674abd68dcc43f0fe8f559aecbe913b6e9ae79194e5ff7327b2de531e2716b`
- Candidate identity policy: `mdstats.mvsel2-harden1-v3.candidate-identity.v1`
- Prepared gates: H0-H4 implementation `PREPARED`; H6 deterministic closeout `PREPARED`; H5 qualification `NOT_RUN`.
- Environment: user's workstation, Conda environment `mace`.
- GitHub Actions are not an authorized substitute for workstation qualification.

## Bound production inputs

The exact production graph binding used by Q5-Q7 is:

```bash
MVSEL2_CAMPAIGN_DATABASE='__CAMPAIGN_DATABASE__'
MVSEL2_DOMAIN='__DOMAIN__'
```

These values must identify the real 36,408-candidate / 165-family production campaign. The bootstrap must refuse to emit the final handoff if either value is absent or still contains placeholder syntax.

## Candidate preflight

Require before Q1:

- `HEAD == a9cb41ad9b1c6305de195f1a88b71ea098e582b7`;
- recomputed candidate content identity equals the bound value in the front matter;
- no staged/tracked candidate changes;
- no undeclared untracked/shadowing files can affect import/build/runtime;
- cwd is repository root and import/source origins are controlled;
- workplan digest equals the value above.

Any mismatch stops qualification as a stale or ambiguous candidate.

## Output policy

`qualification/evidence/`, `qualification/tmp/`, `build/`, and `dist/` are `EPHEMERAL_QUALIFICATION_OUTPUT`. Product source, tests, specs, configuration, packaging metadata, release metadata, and tracked generated candidate artifacts are immutable. Any required candidate correction is `RETURN_TO_IMPLEMENTATION`.

## Q1 — focused v2 hardening regressions

- Gates: H1-H4
- Mandatory: yes
- Capability: `TARGET_RUNTIME`
- Working directory: repository root
- Command:

```bash
conda run -n mace pytest -q \
  tests/test_mlff_repair2.py \
  tests/test_mlff_mvstate2.py \
  tests/test_mlff_mvsel2_forward.py \
  tests/test_mlff_mvmigrate2.py \
  tests/test_mlff_mvsel2_hardening.py
```

- Expected: exit 0.
- Evidence: `qualification/evidence/q1_focused_v2.log`
- Retry: `CLEAN_RETRY`, maximum 1; cleanup limited to declared ephemeral pytest/build state.
- Dependencies: exact candidate identity; `mace` runtime; listed tests and their product-source dependencies.

## Q2 — adjacent v1 regression

```bash
conda run -n mace pytest -q tests/test_mlff_target_data2c_repair1.py
```

- Mandatory: yes; capability `TARGET_RUNTIME`; expected exit 0.
- Evidence: `qualification/evidence/q2_adjacent_v1.log`
- Retry: `CLEAN_RETRY`, maximum 1, ephemeral cleanup only.
- Dependencies: exact candidate identity and REPAIR1/REPAIR2 compatibility surfaces.

## Q3 — full non-slow suite

```bash
conda run -n mace pytest -q -m 'not slow'
```

- Mandatory: yes; capability `TARGET_RUNTIME`; expected exit 0.
- Evidence: `qualification/evidence/q3_full_non_slow.log`
- Retry: `CLEAN_RETRY`, maximum 1, ephemeral cleanup only.
- Dependencies: entire candidate identity and workstation Python/runtime environment.

## Q4 — clean wheel/install/import/package-content qualification

Use the frozen candidate and `setuptools.build_meta` backend declared in `pyproject.toml`:

```bash
rm -rf qualification/tmp/wheel-install build dist
mkdir -p qualification/tmp/wheel-install
conda run -n mace python -m build --wheel --outdir dist
conda run -n mace python -m pip install --no-deps --target qualification/tmp/wheel-install dist/mdstats-0.20.242a0-*.whl
PYTHONPATH="$PWD/qualification/tmp/wheel-install" conda run -n mace python -c 'import mdstats, pathlib; p=pathlib.Path(mdstats.__file__).resolve(); print(p); assert "qualification/tmp/wheel-install" in str(p); print(mdstats.__version__)'
conda run -n mace python -c 'import glob,zipfile; w=glob.glob("dist/mdstats-0.20.242a0-*.whl"); assert len(w)==1, w; n=zipfile.ZipFile(w[0]).namelist(); assert not any(x.startswith("workplans/") for x in n); print(len(n))'
```

- Mandatory: yes; capability `TARGET_RUNTIME`; expected all commands exit 0, installed import originates from isolated target, version is `0.20.242a0`, and wheel excludes `workplans/`.
- Evidence: `qualification/evidence/q4_wheel_install.log` plus wheel filename/hash.
- Retry: `CLEAN_RETRY`, maximum 1; may delete only `build/`, `dist/`, and `qualification/tmp/wheel-install/`.
- Dependencies: exact candidate identity, build backend/tool versions, Python ABI/platform.

## Q5 — production MVSEL2/MVSTATE2 selector and continuation

- Mandatory: yes; capabilities `TARGET_RUNTIME`, `PRODUCTION_DATA`.
- Exact pre-existing production invocation bound during bootstrap:

```bash
__Q5_PRODUCTION_COMMAND__
```

- The bound command must use the production campaign/database/domain identified above without altering scientific or resource policy.
- Exercise authenticated MVSEL2 authority and interrupted/resumed MVSTATE2 continuation required by the workplan, including newest-corrupt checkpoint fallback where applicable and exact resumed/uninterrupted persisted-result equivalence.
- Record candidate SHA, campaign/input identities, exact invocation/config, wall/resource telemetry, restore/replay mode, checkpoint identities, persisted digests, and comparison result.
- Evidence: `qualification/evidence/q5_mvsel2_mvstate2_production.*`
- Retry: `RESUME_RETRY` only where the bound production command's existing checkpoint semantics permit exact continuation; otherwise `NONE`.
- Missing production data/config is `BLOCKED`, not substituted by fixtures.

## Q6 — full-eight-rung production REPAIR2

Using the exact production binding above:

```bash
conda run -n mace python benchmarks/benchmark_mlff_mvsel2_harden1_v3_repair2_production.py \
  "$MVSEL2_CAMPAIGN_DATABASE" \
  --domain "$MVSEL2_DOMAIN" \
  --workplan-sha256 ac674abd68dcc43f0fe8f559aecbe913b6e9ae79194e5ff7327b2de531e2716b \
  --expected-candidate-count 36408 \
  --expected-family-count 165 \
  --output qualification/evidence/mvsel2_harden1_v3_repair2_production.json
```

- Mandatory: yes; capabilities `TARGET_RUNTIME`, `PRODUCTION_DATA`.
- Expected: exit 0; every materializable rung `(128,256,512,1024,2048,4096,8192,16384)` measured; default REPAIR2 policy; per-rung wall/proposals/shortlist/swaps/state mode/RSS; `proposal_full_state_copies_zero=true`; forward-only reader; `inverse_mutation_false=true`.
- Retry: `NONE` unless an identical/resumable retry preserves candidate, inputs, scientific policy, and resource policy.
- Evidence dependency: exact candidate identity, campaign DB/domain/digests, host/runtime/resource configuration.

## Q7 — StageResourceScope campaign integration and >=10x floor

- Mandatory: yes; capabilities `TARGET_RUNTIME`, `PRODUCTION_DATA`.
- Exact pre-existing StageResourceScope-wrapped campaign invocation bound during bootstrap:

```bash
__Q7_PRODUCTION_COMMAND__
```

- The bound command must execute the real campaign path under its existing `StageResourceScope` boundary against the same production inputs as Q5/Q6; do not alter scientific/resource configuration to obtain PASS.
- Capture selector + checkpoint/resume + repair-chain wall/resource telemetry and compare against the frozen same-host MVSEL1 baseline/projection using the workplan's >=10x combined-chain floor.
- Evidence: `qualification/evidence/q7_stage_resource_scope_performance.*`
- Expected: resource boundary exercised and comparable combined speedup >=10x.
- Retry: `IDENTICAL_RETRY` maximum 1 only for transient measurement failure; no policy/input/candidate change.
- Missing comparable baseline or production environment is `BLOCKED`.

## Q8 — GPU status

Record `DEFERRED_NOT_RUN` unless GPU qualification is genuinely executed. GPU evidence is not required for current CPU/workstation acceptance and must not be inferred from CPU results.

## Postflight

After attempted checks:

1. recompute candidate content identity and require equality with the bound preflight identity;
2. verify no tracked candidate surface changed;
3. record `git status --porcelain=v1 --untracked-files=all` and ensure changes are confined to declared ephemeral/evidence paths plus the generated workplan coordination artifacts;
4. produce a Protocol-v3 Qualification Report bound to this handoff's SHA-256 and candidate identity;
5. do not declare `MERGE_READY`; send the report/evidence to `software-verification`.

## Failure routing

- product/source/test-contract defect -> `RETURN_TO_IMPLEMENTATION`;
- frozen design/acceptance contradiction -> `DESIGN_REVISION_REQUIRED`;
- missing required environment/data or inability to establish exact Q5/Q7 production invocation -> `BLOCKED`;
- identity/dirty-tree mismatch -> stop as stale/ambiguous candidate;
- no silent patching, threshold changes, dataset reductions, backend substitutions, or resource-policy changes.
