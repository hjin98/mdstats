---
kind: qualification-handoff
handoff_id: DOC-MVSEL2-HARDEN1-V3-QUAL-2
protocol_version: 3.0.0
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 1
workplan_sha256: ac674abd68dcc43f0fe8f559aecbe913b6e9ae79194e5ff7327b2de531e2716b
candidate_ref: a9cb41ad9b1c6305de195f1a88b71ea098e582b7
candidate_commit: a9cb41ad9b1c6305de195f1a88b71ea098e582b7
candidate_content_identity: 56fdec9a708e99119cd3ba3708f3cf26f95867e648ca1729c890ca40d0feb956
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

This is the exact Protocol-v3 qualification contract for the frozen MVSEL2 hardening candidate after the pre-qualification bootstrap binds the single candidate-content-identity token. No other runtime placeholders are permitted.

## Prepared candidate and fixed production binding

- Candidate commit/ref: `a9cb41ad9b1c6305de195f1a88b71ea098e582b7`
- Workplan: `workplans/active/DOC-MVSEL2_HARDEN1_V3.md`, revision 1
- Workplan SHA-256: `ac674abd68dcc43f0fe8f559aecbe913b6e9ae79194e5ff7327b2de531e2716b`
- Candidate identity policy: `mdstats.mvsel2-harden1-v3.candidate-identity.v1`
- Production campaign DB: `$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/.mdstats/campaign.sqlite3`
- Production domain: `label-domain-5aa1ee5d50cd0b23`
- Expected production graph: 36,408 candidates / 165 families.
- Qualification driver source: `workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_DRIVER.py`
- Qualification driver Git blob SHA: `fe649742674ecdff7286452ced5ecf044402098e`
- Environment: user's workstation, Conda environment `mace`.
- Prepared gates: H0-H4 implementation `PREPARED`; H6 deterministic closeout `PREPARED`; H5 qualification `NOT_RUN`.

The production `.mdstats` tree is an input only. Q5-Q7 must operate on ephemeral clones under `qualification/tmp/`; they must not write the production campaign DB or production record directory.

## Candidate preflight

Before Q1 require:

- `HEAD == a9cb41ad9b1c6305de195f1a88b71ea098e582b7`;
- recomputed candidate content identity equals the bound front-matter value;
- no staged/tracked candidate changes;
- no undeclared untracked/shadowing source can affect import/build/runtime;
- cwd is repository root;
- workplan digest equals the declared value;
- `qualification/tmp/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_DRIVER.py` has Git blob SHA `fe649742674ecdff7286452ced5ecf044402098e`.

Any mismatch stops qualification as stale/ambiguous candidate.

## Q1 — focused v2 hardening regressions

```bash
conda run -n mace pytest -q \
  tests/test_mlff_repair2.py \
  tests/test_mlff_mvstate2.py \
  tests/test_mlff_mvsel2_forward.py \
  tests/test_mlff_mvmigrate2.py \
  tests/test_mlff_mvsel2_hardening.py \
  2>&1 | tee qualification/evidence/q1_focused_v2.log
```

Mandatory: yes. Capability: `TARGET_RUNTIME`. Expected: exit 0. Retry: `CLEAN_RETRY`, maximum 1, ephemeral cache/output cleanup only.

## Q2 — adjacent v1 regression

```bash
conda run -n mace pytest -q tests/test_mlff_target_data2c_repair1.py \
  2>&1 | tee qualification/evidence/q2_adjacent_v1.log
```

Mandatory: yes. Capability: `TARGET_RUNTIME`. Expected: exit 0. Retry: `CLEAN_RETRY`, maximum 1.

## Q3 — full non-slow suite

```bash
conda run -n mace pytest -q -m 'not slow' \
  2>&1 | tee qualification/evidence/q3_full_non_slow.log
```

Mandatory: yes. Capability: `TARGET_RUNTIME`. Expected: exit 0. Retry: `CLEAN_RETRY`, maximum 1.

## Q4 — clean wheel/install/import/package-content qualification

```bash
rm -rf qualification/tmp/wheel-install build dist
mkdir -p qualification/tmp/wheel-install
conda run -n mace python -m build --wheel --outdir dist
conda run -n mace python -m pip install --no-deps --target qualification/tmp/wheel-install dist/mdstats-0.20.242a0-*.whl
PYTHONPATH="$PWD/qualification/tmp/wheel-install" conda run -n mace python -c 'import mdstats,pathlib; p=pathlib.Path(mdstats.__file__).resolve(); print(p); assert "qualification/tmp/wheel-install" in str(p); assert mdstats.__version__=="0.20.242a0"'
conda run -n mace python -c 'import glob,zipfile; w=glob.glob("dist/mdstats-0.20.242a0-*.whl"); assert len(w)==1,w; n=zipfile.ZipFile(w[0]).namelist(); assert not any(x.startswith("workplans/") for x in n); print(w[0],len(n))'
sha256sum dist/mdstats-0.20.242a0-*.whl | tee qualification/evidence/q4_wheel_sha256.txt
```

Mandatory: yes. Capability: `TARGET_RUNTIME`. Expected: all commands exit 0; installed import originates from isolated target; wheel excludes `workplans/`. Retry: `CLEAN_RETRY`, maximum 1, limited to `build/`, `dist/`, and `qualification/tmp/wheel-install/`.

## Q5 — production MVSEL2/MVSTATE2 continuation and corrupt-newest fallback

This check creates a fresh ephemeral clone of the production `.mdstats` tree, builds uninterrupted MVSEL2/MVSTATE2 authority there through the candidate's actual hardened campaign orchestration, deletes only the ephemeral final MVSEL2 authority, corrupts only the newest ephemeral MVSTATE2 pointer for the bound domain, then rebuilds through the highest-valid earlier checkpoint. The uninterrupted and resumed authority digests must be identical.

```bash
PROD_DB='$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/.mdstats/campaign.sqlite3'
DOMAIN='label-domain-5aa1ee5d50cd0b23'
DRIVER='qualification/tmp/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_DRIVER.py'
PROD_SHA_BEFORE=$(sha256sum "$PROD_DB" | awk '{print $1}')
rm -rf qualification/tmp/mvsel2-q5
conda run -n mace python "$DRIVER" q5 \
  --production-db "$PROD_DB" \
  --domain "$DOMAIN" \
  --clone-root qualification/tmp/mvsel2-q5 \
  --output qualification/evidence/q5_mvsel2_mvstate2_production.json \
  2>&1 | tee qualification/evidence/q5_mvsel2_mvstate2_production.log
PROD_SHA_AFTER=$(sha256sum "$PROD_DB" | awk '{print $1}')
test "$PROD_SHA_BEFORE" = "$PROD_SHA_AFTER"
```

Mandatory: yes. Capabilities: `TARGET_RUNTIME`, `PRODUCTION_DATA`. Expected: exit 0; 36,408/165 production identity verified; native forward-only runtime used; corrupt-newest checkpoint falls back to an earlier valid checkpoint; resumed and uninterrupted selection digests are identical; production DB SHA-256 unchanged. Retry: `CLEAN_RETRY`, maximum 1, by deleting only `qualification/tmp/mvsel2-q5/` and Q5 evidence.

## Q6 — full-eight-rung production REPAIR2

Q6 consumes the Q5 ephemeral campaign clone, which now contains validated MVSEL2/MVSTATE2 authority. It must not point at the original production DB, which intentionally contains no `target_multi_view*` authority.

```bash
Q5_DB="$PWD/qualification/tmp/mvsel2-q5/.mdstats/campaign.sqlite3"
DOMAIN='label-domain-5aa1ee5d50cd0b23'
test -f "$Q5_DB"
conda run -n mace python benchmarks/benchmark_mlff_mvsel2_harden1_v3_repair2_production.py \
  "$Q5_DB" \
  --domain "$DOMAIN" \
  --workplan-sha256 ac674abd68dcc43f0fe8f559aecbe913b6e9ae79194e5ff7327b2de531e2716b \
  --expected-candidate-count 36408 \
  --expected-family-count 165 \
  --output qualification/evidence/mvsel2_harden1_v3_repair2_production.json \
  2>&1 | tee qualification/evidence/q6_repair2_production.log
```

Mandatory: yes. Capabilities: `TARGET_RUNTIME`, `PRODUCTION_DATA`. Expected: exit 0; all materializable rungs `(128,256,512,1024,2048,4096,8192,16384)` measured; default REPAIR2 policy; per-rung wall/proposals/shortlist/swaps/state mode/RSS; zero proposal full-state copies; inverse mutation false. Retry: `NONE` unless a strictly identical rerun is needed for transient infrastructure failure.

## Q7 — StageResourceScope-wrapped same-host v1/v2 chain comparison

This check creates two independent ephemeral clones from the same production input. On one clone it executes the existing MVSEL1 + REPAIR1 campaign orchestration; on the other it executes hardened MVSEL2 + REPAIR2. Both paths use the candidate's existing `StageResourceScope` wrappers and the same campaign configuration/resource policy. The measured same-host combined-chain speedup must be at least 10x.

```bash
PROD_DB='$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/.mdstats/campaign.sqlite3'
DOMAIN='label-domain-5aa1ee5d50cd0b23'
DRIVER='qualification/tmp/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_DRIVER.py'
PROD_SHA_BEFORE=$(sha256sum "$PROD_DB" | awk '{print $1}')
rm -rf qualification/tmp/mvsel2-q7
conda run -n mace python "$DRIVER" q7 \
  --production-db "$PROD_DB" \
  --domain "$DOMAIN" \
  --clone-root qualification/tmp/mvsel2-q7 \
  --output qualification/evidence/q7_stage_resource_scope_performance.json \
  2>&1 | tee qualification/evidence/q7_stage_resource_scope_performance.log
PROD_SHA_AFTER=$(sha256sum "$PROD_DB" | awk '{print $1}')
test "$PROD_SHA_BEFORE" = "$PROD_SHA_AFTER"
```

Mandatory: yes. Capabilities: `TARGET_RUNTIME`, `PRODUCTION_DATA`. Expected: exit 0; both chains execute through their campaign `StageResourceScope` boundaries on the same host/input/config; `combined_chain_speedup >= 10.0`; production DB SHA-256 unchanged. Retry: `IDENTICAL_RETRY`, maximum 1 only for transient measurement failure; no candidate/input/config/resource-policy changes.

## Q8 — GPU status

Record `DEFERRED_NOT_RUN`. GPU evidence is not required for current CPU/workstation acceptance and must not be inferred from CPU results.

## Evidence dependencies

Q1-Q4 depend on the exact candidate identity and `mace` runtime. Q5-Q7 additionally depend on the fixed production DB/domain above, its referenced immutable `.mdstats/records` content, the candidate campaign configuration at the production workspace, host CPU/RAM resource resolution, and the exact qualification-driver blob SHA. Q6 depends on successful Q5 output. Q7 is independent of Q5/Q6 except for shared candidate/input/environment identity.

## Postflight

After attempted checks:

1. recompute candidate content identity and require exact equality with the bound preflight identity;
2. verify no tracked candidate surface changed;
3. verify the production DB SHA-256 is unchanged from pre-qualification evidence;
4. record `git status --porcelain=v1 --untracked-files=all` and ensure changes are confined to declared workplan coordination plus `qualification/`, `build/`, and `dist/` outputs;
5. produce a Protocol-v3 Qualification Report bound to this handoff SHA-256 and candidate identity;
6. do not declare `MERGE_READY`; route to independent `software-verification`.

## Failure routing

- product/source/test-contract defect -> `RETURN_TO_IMPLEMENTATION`;
- frozen design/acceptance contradiction -> `DESIGN_REVISION_REQUIRED`;
- missing production input/config/environment -> `BLOCKED`;
- identity/dirty-tree mismatch -> stop as stale/ambiguous candidate;
- no silent patching, threshold changes, dataset reductions, backend substitutions, or resource-policy changes.

