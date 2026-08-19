---
kind: qualification-handoff
handoff_id: DOC-MVSEL2-HARDEN1-V3-QUAL-REV2-1
protocol_version: 3.0.0
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 2
workplan_sha256: 42a9075ecd96eb16a36ab9fc1d09c8bd4522022ef1749f6554dfa153c0faa52c
candidate_ref: a9cb41ad9b1c6305de195f1a88b71ea098e582b7
candidate_commit: a9cb41ad9b1c6305de195f1a88b71ea098e582b7
candidate_content_identity: 56fdec9a708e99119cd3ba3708f3cf26f95867e648ca1729c890ca40d0feb956
candidate_identity_policy: mdstats.mvsel2-harden1-v3.candidate-identity.v1
q3_baseline_commit: e24d5168ce01bf2d773339e1a91d5ded4871a57f
q3_comparator_policy: mdstats.mvsel2-harden1-v3.q3-diff.v1
q3_comparator_blob_sha: 8816669d3a0dc6ad862bff47ff113470e271835b
status: PREPARED_FOR_QUALIFICATION
product_source_mutation: FORBIDDEN
allowed_write_paths:
  - qualification/evidence/
  - qualification/tmp/
  - build/
  - dist/
  - /tmp/mdstats-mvsel2-q3-baseline-e24d5168/
---

# DOC-MVSEL2-HARDEN1-V3 revision-2 Qualification Handoff

This handoff supersedes the failed revision-1 qualification contract for future execution only. The prior handoff/report remain historical evidence and MUST NOT be rewritten.

## Bound authority

- Workplan: `workplans/active/DOC-MVSEL2_HARDEN1_V3_REV2.md`, revision 2.
- Workplan SHA-256: `42a9075ecd96eb16a36ab9fc1d09c8bd4522022ef1749f6554dfa153c0faa52c`.
- Frozen product candidate: `a9cb41ad9b1c6305de195f1a88b71ea098e582b7`.
- Candidate content identity: `56fdec9a708e99119cd3ba3708f3cf26f95867e648ca1729c890ca40d0feb956`.
- Q3 regression baseline: `e24d5168ce01bf2d773339e1a91d5ded4871a57f`.
- Q3 comparator: `workplans/active/DOC-MVSEL2_HARDEN1_V3_Q3_DIFF.py`, Git blob `8816669d3a0dc6ad862bff47ff113470e271835b`, policy `mdstats.mvsel2-harden1-v3.q3-diff.v1`.
- Production DB: `$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/.mdstats/campaign.sqlite3`.
- Production domain: `label-domain-5aa1ee5d50cd0b23`.
- Expected graph: 36,408 candidates / 165 families.
- Runtime: workstation Conda environment `mace`.

## Preflight

Before qualification, detach/check out the exact candidate and require:

1. `HEAD == a9cb41ad9b1c6305de195f1a88b71ea098e582b7`.
2. Candidate identity recomputes to the bound value.
3. Tracked/staged state is clean and no undeclared untracked/shadowing source affects import/build/runtime.
4. `mdstats` source origin resolves to the candidate checkout for source tests.
5. Revision-2 workplan SHA-256 matches the bound value.
6. Copy the bound comparator from the coordination branch into `qualification/tmp/DOC-MVSEL2_HARDEN1_V3_Q3_DIFF.py` and verify Git blob `8816669d3a0dc6ad862bff47ff113470e271835b` before use.
7. Record Python, pytest, dependency/environment identity and material test environment variables in `qualification/evidence/q3_environment.txt`.

A mismatch stops as stale/ambiguous candidate.

## Evidence reuse from failed revision-1 qualification

Q1 and Q2 may be reused as PASS only if the candidate identity and material `mace` environment are unchanged and the qualification report records that dependency check. Otherwise rerun them. Revision-1 Q3 is diagnostic only; it lacks required JUnit structure and is not revision-2 PASS evidence. Revision-1 Q4 is invalidated and MUST rerun. Q5-Q7 remain NOT RUN. Q8 remains nonblocking `DEFERRED_NOT_RUN`.

## Q1 — focused v2 hardening regressions

Absolute PASS requirement.

```bash
conda run -n mace pytest -q \
  tests/test_mlff_repair2.py \
  tests/test_mlff_mvstate2.py \
  tests/test_mlff_mvsel2_forward.py \
  tests/test_mlff_mvmigrate2.py \
  tests/test_mlff_mvsel2_hardening.py \
  2>&1 | tee qualification/evidence/q1_focused_v2_rev2.log
```

Expected: pytest exit 0. Retry: `CLEAN_RETRY`, maximum 1.

## Q2 — adjacent v1 regression

Absolute PASS requirement.

```bash
conda run -n mace pytest -q tests/test_mlff_target_data2c_repair1.py \
  2>&1 | tee qualification/evidence/q2_adjacent_v1_rev2.log
```

Expected: pytest exit 0. Retry: `CLEAN_RETRY`, maximum 1.

## Q3 — authenticated differential full non-slow regression

Q3 compares exact analysis-base commit `e24d5168...` against the exact candidate in the same environment. Pytest exit 1 due test failures is valid comparator input; exit 2 or greater is an infrastructure/collection failure and blocks Q3.

```bash
set -u
CAND_ROOT="$PWD"
BASE_ROOT='/tmp/mdstats-mvsel2-q3-baseline-e24d5168'
BASE_SHA='e24d5168ce01bf2d773339e1a91d5ded4871a57f'
CAND_SHA='a9cb41ad9b1c6305de195f1a88b71ea098e582b7'
rm -rf "$BASE_ROOT"
git clone --no-hardlinks "$CAND_ROOT" "$BASE_ROOT"
git -C "$BASE_ROOT" checkout --detach "$BASE_SHA"
test "$(git -C "$BASE_ROOT" rev-parse HEAD)" = "$BASE_SHA"
test -z "$(git -C "$BASE_ROOT" status --porcelain=v1 --untracked-files=all)"

(
  cd "$BASE_ROOT"
  conda run -n mace python -c 'import mdstats,pathlib; p=pathlib.Path(mdstats.__file__).resolve(); r=pathlib.Path.cwd().resolve(); print(p); assert p.is_relative_to(r), (p,r)'
)
conda run -n mace python -c 'import mdstats,pathlib; p=pathlib.Path(mdstats.__file__).resolve(); r=pathlib.Path.cwd().resolve(); print(p); assert p.is_relative_to(r), (p,r)'

set +e
(
  cd "$BASE_ROOT"
  conda run -n mace pytest -q -m 'not slow' -o junit_family=legacy --junitxml="$CAND_ROOT/qualification/evidence/q3_baseline.xml"
) 2>&1 | tee qualification/evidence/q3_baseline.log
BASE_RC=${PIPESTATUS[0]}
conda run -n mace pytest -q -m 'not slow' -o junit_family=legacy --junitxml=qualification/evidence/q3_candidate.xml \
  2>&1 | tee qualification/evidence/q3_candidate.log
CAND_RC=${PIPESTATUS[0]}
set -e
if [ "$BASE_RC" -gt 1 ] || [ "$CAND_RC" -gt 1 ]; then exit 2; fi

conda run -n mace python qualification/tmp/DOC-MVSEL2_HARDEN1_V3_Q3_DIFF.py \
  --baseline-xml qualification/evidence/q3_baseline.xml \
  --candidate-xml qualification/evidence/q3_candidate.xml \
  --baseline-root "$BASE_ROOT" \
  --candidate-root "$CAND_ROOT" \
  --baseline-commit "$BASE_SHA" \
  --candidate-commit "$CAND_SHA" \
  --output qualification/evidence/q3_differential.json \
  2>&1 | tee qualification/evidence/q3_differential.log
```

Mandatory: yes. Capability: `TARGET_RUNTIME`. Expected: comparator exit 0 and JSON `pass: true`; zero candidate-only failure/error signatures, zero baseline-PASS-to-candidate-FAIL/ERROR regressions, and no failing/error candidate-only tests. Retry: `CLEAN_RETRY`, maximum 1, limited to the external baseline clone plus Q3 evidence.

## Q4 — clean wheel/install/import/package-content

Absolute PASS requirement. Import validation MUST execute outside repository root.

```bash
rm -rf qualification/tmp/wheel-install build dist
mkdir -p qualification/tmp/wheel-install
conda run -n mace python -m build --wheel --outdir dist
conda run -n mace python -m pip install --no-deps --target qualification/tmp/wheel-install dist/mdstats-0.20.242a0-*.whl
INSTALL_ROOT="$PWD/qualification/tmp/wheel-install"
(
  cd qualification/tmp
  PYTHONPATH="$INSTALL_ROOT" conda run -n mace python -c 'import mdstats,pathlib,os; p=pathlib.Path(mdstats.__file__).resolve(); r=pathlib.Path(os.environ["PYTHONPATH"]).resolve(); print(p); assert p.is_relative_to(r), (p,r); assert mdstats.__version__=="0.20.242a0"'
)
conda run -n mace python -c 'import glob,zipfile; w=glob.glob("dist/mdstats-0.20.242a0-*.whl"); assert len(w)==1,w; n=zipfile.ZipFile(w[0]).namelist(); assert not any(x.startswith("workplans/") for x in n); print(w[0],len(n))'
sha256sum dist/mdstats-0.20.242a0-*.whl | tee qualification/evidence/q4_wheel_sha256_rev2.txt
```

Expected: all commands exit 0; installed import is beneath the isolated target; version exact; wheel excludes `workplans/`. Retry: `CLEAN_RETRY`, maximum 1.

## Q5 — production MVSEL2/MVSTATE2 continuation and corrupt-newest fallback

Use the existing bound qualification driver copied to `qualification/tmp/`. Operate only on an ephemeral clone of production state.

```bash
PROD_DB='$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/.mdstats/campaign.sqlite3'
DOMAIN='label-domain-5aa1ee5d50cd0b23'
DRIVER='qualification/tmp/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_DRIVER.py'
PROD_SHA_BEFORE=$(sha256sum "$PROD_DB" | awk '{print $1}')
rm -rf qualification/tmp/mvsel2-q5
conda run -n mace python "$DRIVER" q5 --production-db "$PROD_DB" --domain "$DOMAIN" --clone-root qualification/tmp/mvsel2-q5 --output qualification/evidence/q5_mvsel2_mvstate2_production_rev2.json 2>&1 | tee qualification/evidence/q5_mvsel2_mvstate2_production_rev2.log
PROD_SHA_AFTER=$(sha256sum "$PROD_DB" | awk '{print $1}')
test "$PROD_SHA_BEFORE" = "$PROD_SHA_AFTER"
```

Expected: absolute PASS of revision-1 Q5 semantics, including exact resume/fallback equivalence, native forward-only execution, and unchanged production DB. Retry: `CLEAN_RETRY`, maximum 1.

## Q6 — full-eight-rung production REPAIR2

```bash
Q5_DB="$PWD/qualification/tmp/mvsel2-q5/.mdstats/campaign.sqlite3"
DOMAIN='label-domain-5aa1ee5d50cd0b23'
test -f "$Q5_DB"
conda run -n mace python benchmarks/benchmark_mlff_mvsel2_harden1_v3_repair2_production.py "$Q5_DB" \
  --domain "$DOMAIN" \
  --workplan-sha256 42a9075ecd96eb16a36ab9fc1d09c8bd4522022ef1749f6554dfa153c0faa52c \
  --expected-candidate-count 36408 --expected-family-count 165 \
  --output qualification/evidence/mvsel2_harden1_v3_repair2_production_rev2.json \
  2>&1 | tee qualification/evidence/q6_repair2_production_rev2.log
```

Expected: absolute PASS of all materializable rungs `(128,256,512,1024,2048,4096,8192,16384)`, required telemetry, zero proposal full-state copies, inverse mutation false. Retry: `NONE` except strictly identical transient-infrastructure retry.

## Q7 — StageResourceScope same-host v1/v2 chain comparison

```bash
PROD_DB='$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/.mdstats/campaign.sqlite3'
DOMAIN='label-domain-5aa1ee5d50cd0b23'
DRIVER='qualification/tmp/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_DRIVER.py'
PROD_SHA_BEFORE=$(sha256sum "$PROD_DB" | awk '{print $1}')
rm -rf qualification/tmp/mvsel2-q7
conda run -n mace python "$DRIVER" q7 --production-db "$PROD_DB" --domain "$DOMAIN" --clone-root qualification/tmp/mvsel2-q7 --output qualification/evidence/q7_stage_resource_scope_performance_rev2.json 2>&1 | tee qualification/evidence/q7_stage_resource_scope_performance_rev2.log
PROD_SHA_AFTER=$(sha256sum "$PROD_DB" | awk '{print $1}')
test "$PROD_SHA_BEFORE" = "$PROD_SHA_AFTER"
```

Expected: absolute PASS; both chains traverse StageResourceScope on same host/input/config and `combined_chain_speedup >= 10.0`; production DB unchanged. Retry: `IDENTICAL_RETRY`, maximum 1 for transient measurement failure only.

## Q8 — GPU

Record `DEFERRED_NOT_RUN`, nonblocking for current acceptance.

## Postflight

After all attempted checks, recompute candidate identity, require exact equality, verify no tracked candidate changes, verify production DB SHA unchanged, and record status showing writes only in declared coordination/evidence/scratch paths. Produce a new Protocol-v3 Qualification Report bound to this exact handoff digest. Qualification MUST NOT declare `MERGE_READY`.

## Failure routing

- candidate-only Q3 signature or other product/test defect -> `RETURN_TO_IMPLEMENTATION` with exact evidence;
- baseline comparability/oracle contradiction -> `DESIGN_REVISION_REQUIRED`;
- missing target runtime/data -> `BLOCKED`;
- identity/dirty/source-origin mismatch -> stop as stale/ambiguous candidate.
