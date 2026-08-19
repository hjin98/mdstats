# DOC-MVSEL2-HARDEN1-V3 implementation return after failed qualification

Status: DESIGN_REVISION_REQUIRED for Q3; Q4 handoff defect identified and corrected command frozen below.

## Bound failed qualification

- candidate_commit: `a9cb41ad9b1c6305de195f1a88b71ea098e582b7`
- candidate_content_identity: `56fdec9a708e99119cd3ba3708f3cf26f95867e648ca1729c890ca40d0feb956`
- failed handoff SHA-256: `a20302ce1ed5c6cd0a5cc269eba2f6b440e523370dde61418dfb37bab03e8cff`
- workplan: `DOC-MVSEL2-HARDEN1-V3` rev 1
- workplan SHA-256: `ac674abd68dcc43f0fe8f559aecbe913b6e9ae79194e5ff7327b2de531e2716b`

Qualification results: Q1 PASS, Q2 PASS, Q3 FAIL, Q4 FAIL, Q5-Q7 NOT RUN, Q8 DEFERRED_NOT_RUN.

## Q3 diagnosis and routing

The authoritative full non-slow run completed rather than failing collection: 3,187 passed, 307 failed, 16 skipped, 20 deselected. The qualification report identifies broad failure classes outside the MVSEL2 hardening change surface, including historical package-version assertions, stale specification/architecture expectations, example/bootstrap and compatibility-launcher/API contracts, and campaign/runtime/documentation synchronization.

The frozen H5 acceptance contract requires the complete non-slow suite to pass. Replacing that requirement with a baseline-relative/no-new-failures criterion, excluding unrelated suites, or mass-revising historical contracts solely to make this candidate pass would materially change the frozen acceptance semantics. Software implementation therefore must not do so. Route Q3 to `software-design` as `DESIGN_REVISION_REQUIRED` to define the repository-wide regression baseline/acceptance semantics. Until that revision exists, no new qualification handoff may claim Q3 is satisfiable by a narrowed command.

## Q4 root cause and corrected command

The wheel built and installed successfully. The installed-origin assertion failed because it was executed with the repository root as the current working directory; Python's empty-path entry therefore resolved the source checkout before the target installation despite `PYTHONPATH`.

A future handoff must use an absolute install target and execute the installed-artifact import from outside the repository checkout:

```bash
rm -rf qualification/tmp/wheel-install build dist
mkdir -p qualification/tmp/wheel-install
conda run -n mace python -m build --wheel --outdir dist
conda run -n mace python -m pip install --no-deps --target qualification/tmp/wheel-install dist/mdstats-0.20.242a0-*.whl
REPO_ROOT="$PWD"
INSTALL_ROOT="$PWD/qualification/tmp/wheel-install"
(
  cd qualification/tmp
  PYTHONPATH="$INSTALL_ROOT" conda run -n mace python -c 'import mdstats,pathlib; p=pathlib.Path(mdstats.__file__).resolve(); root=pathlib.Path("'"$INSTALL_ROOT"'").resolve(); print(p); assert p.is_relative_to(root), (p,root); assert mdstats.__version__=="0.20.242a0"'
)
conda run -n mace python -c 'import glob,zipfile; w=glob.glob("dist/mdstats-0.20.242a0-*.whl"); assert len(w)==1,w; n=zipfile.ZipFile(w[0]).namelist(); assert not any(x.startswith("workplans/") for x in n); print(w[0],len(n))'
sha256sum dist/mdstats-0.20.242a0-*.whl | tee qualification/evidence/q4_wheel_sha256.txt
```

The Q4 correction is coordination-only and does not change candidate content identity. Q4 evidence from the failed handoff is invalid for acceptance and must rerun under the next exact handoff.

## Evidence invalidation

- Q1 PASS and Q2 PASS remain historical evidence bound to the unchanged candidate, but a future design revision decides whether they may be reused.
- Q3 FAIL remains authoritative evidence demonstrating the current absolute full-suite acceptance contract is unsatisfied.
- Q4 FAIL is invalidated by the corrected execution-origin command and must rerun.
- Q5-Q7 remain NOT RUN and require execution after a valid revised handoff.
- Q8 remains nonblocking `DEFERRED_NOT_RUN` under the current workplan.

No product/runtime/test/spec/package/release candidate file is changed by this implementation return record.