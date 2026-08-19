---
kind: implementation-workplan
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 3
status: READY_FOR_IMPLEMENTATION
protocol_version: 3.0.0
analysis_base_commit: 73853e1766a5e6408b05e73663daada64f2a056a
candidate_commit: a9cb41ad9b1c6305de195f1a88b71ea098e582b7
supersedes: workplans/active/DOC-MVSEL2_HARDEN1_V3_REV2.md
---

# MVSEL2 Post-Implementation Hardening — Materiality-First Qualification Workplan

## Objective

Finish qualification of the already-implemented MVSEL2/REPAIR2 hardening candidate by testing the software behaviors that matter, without restarting qualification for protocol metadata, report formatting, historical-test-tree mismatch, or harmless harness/path errors.

The frozen product candidate remains:

`a9cb41ad9b1c6305de195f1a88b71ea098e582b7`

No product-source change is planned. Product code changes are justified only if the remaining substantive checks expose a real defect.

## Diagnosis

Two previous qualification attempts failed without demonstrating an MVSEL2 product defect.

1. **Q3 regression oracle was unsound for this repository.** The revision-2 historical baseline `e24d5168...` cannot collect the same broad suite because its historical test tree lacks later test data/import structure. The candidate itself completed the non-slow suite with 3,187 passed, 307 failed, 16 skipped, and 20 deselected. The failures include known historical version/spec/bootstrap/compatibility contracts outside the MVSEL2 hardening surface. Reconstructing another historical/counterfactual tree would add process complexity without improving confidence in MVSEL2.
2. **Q5/Q7 were blocked by a qualification path error.** The driver inferred `campaign.toml` under `mlff-campaign/`, while the intended production configuration is `$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/campaign.toml`. This is an execution-harness defect, not a product-design issue. Q6 never ran because it depends on the Q5 clone.

Previously executed evidence already established:

- Q1 focused MVSEL2/REPAIR2 tests: **40 passed**;
- Q2 adjacent MVSEL1 compatibility: **10 passed**;
- Q4 isolated wheel/build/install/import/package-content check: **PASS**.

The current coordination head differs from the frozen product candidate only in `.gitignore`, `workplans/`, and `qualification/` surfaces. No `mdstats/`, `tests/`, `benchmarks/`, package, specification, or release product surface changed after the candidate.

## Frozen material design

The product design from revisions 1–2 remains unchanged:

- REPAIR2 policy/default/validation mirrors REPAIR1 except v2 authority/schema identity.
- REPAIR2 persisted trace and terminal order remain equivalent to the accepted REPAIR1 oracle on shared fixtures/policies.
- Production v2 execution uses the native forward-only MVIDX path without inverse-array mapping in the v2 execution boundary.
- Interrupted MVSEL2 resumes from the highest valid compatible MVSTATE2 checkpoint and produces the exact uninterrupted result.
- REPAIR2 may use compatible selector checkpoint state only before repair divergence; later pure-selector state must not overwrite divergent repair history.
- Rejected repair proposals use no full forward-state clone; analytical hypothetical scoring is exact and accepted mutation occurs only for the chosen proposal.
- The production performance target remains an end-to-end **>=10x** v2 selector+repair speedup over v1 on the same host, production input, configuration, and materially comparable resource policy.

Revision 3 changes qualification policy only:

1. The repository-wide non-slow suite is a **regression-attribution check**, not a globally-green zero-failure gate, because this repository is not presently maintained as globally green on that suite.
2. No historical/counterfactual broad-suite baseline is required. Existing candidate JUnit evidence is reviewed first; rerun the candidate suite only if attribution needs additional evidence.
3. Qualification may correct cwd, activation, quoting, scratch/log paths, and the unambiguous intended production config path locally without creating a new workplan/handoff.
4. Valid Q1/Q2/Q4 evidence is reused because the candidate and the material surfaces those checks exercise have not changed.
5. Workplan IDs, revision numbers, report hashes, evidence hashes, and benchmark metadata fields are not independent software acceptance criteria. They may remain as diagnostic metadata where existing harnesses require them.

## Acceptance-critical requirements

- **A1 — Focused correctness.** The focused MVSEL2/MVSTATE2/REPAIR2/migration regression set passes for the frozen candidate.
- **A2 — Adjacent compatibility.** The adjacent MVSEL1/REPAIR1 consumer regression remains passing.
- **A3 — No candidate-caused broad regression.** Broad non-slow failures must be reviewed for attribution. Any failure plausibly caused by the MVSEL2 hardening or an affected consumer is blocking until focused evidence resolves it. Clearly unrelated pre-existing/stale failures are repository-health findings, not MVSEL2 acceptance failures.
- **A4 — Installed artifact works.** A wheel built from the candidate installs into an isolated target and imports from that installed target outside the source checkout; `workplans/` is not shipped in the wheel.
- **A5 — Real recovery works.** On the production-sized campaign clone, corrupting the newest MVSTATE2 causes the runtime to select the immediately preceding valid checkpoint as the resume pointer, and the resumed final selection digest exactly equals uninterrupted execution.
- **A6 — Production REPAIR2 resource behavior is correct.** On 36,408 candidates / 165 families, the fixed-eight ladder through 16,384 executes; rejected proposals make zero full forward-state copies; inverse mutation is false; the native forward-only path remains in use.
- **A7 — Performance target is met.** On the same workstation, production input/configuration, and materially comparable resource policy, the end-to-end v2 selector+repair chain is at least 10x faster than v1.
- **A8 — Production inputs are immutable.** Qualification does not modify the production campaign database or production `campaign.toml`.
- **A9 — Candidate remains the tested product.** Qualification does not introduce or depend on later product/runtime/test/package changes while claiming results for `a9cb41ad...`.

## Expected change surface / non-goals

### Expected implementation/coordination surface

- `workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_RUN_CARD_SIMPLIFIED.md`
- `workplans/active/DOC-MVSEL2_HARDEN1_V3_Q5_RECOVERY_CHECK.py`
- existing qualification driver/benchmark only if a real harness defect prevents a material check from executing
- `qualification/` evidence outputs

The existing simplified run card and strengthened Q5 recovery harness are already suitable starting assets.

### Non-goals

- redesign MVSEL2 or REPAIR2;
- manufacture a historical green broad-suite baseline;
- make the entire repository test suite green as part of this hardening task;
- rerun valid Q1/Q2/Q4 solely because the workplan changed;
- synchronize advisory workplan/report/hash metadata merely for cosmetic consistency;
- perform GPU qualification in this gate sequence.

GPU qualification remains a separate final-release obligation and is not required for the present CPU/workstation acceptance.

## Material execution constraints

Production inputs:

```text
Database:
$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/.mdstats/campaign.sqlite3

Configuration:
$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/campaign.toml

Label domain:
label-domain-5aa1ee5d50cd0b23

Expected candidates: 36,408
Expected families: 165
```

- Treat production DB/config as read-only. Q5–Q7 operate on qualification-local clones/scratch.
- Record enough before/after identity to detect unexpected production-input mutation; SHA-256 is appropriate here because these are real external content boundaries.
- Q7 must compare v1 and v2 on the same host/input/configuration and materially comparable resource settings. Do not preserve the 10x claim using a non-comparable measurement.
- Qualification may change shell/cwd/scratch/log details when the material check remains the same.

## Gates

| Gate | Status | Purpose |
|---|---|---|
| G0 — candidate/evidence revalidation | PREPARED | Confirm frozen candidate/product boundary and reuse Q1/Q2/Q4 evidence |
| G1 — broad regression attribution | PENDING | Review existing candidate broad-suite evidence; run focused/candidate-only follow-up only if attribution is ambiguous |
| G2 — production recovery | PREPARED | Execute strengthened Q5 corrupt-newest fallback/resume check on the workstation |
| G3 — production REPAIR2 scale/resources | PREPARED | Execute Q6 fixed-eight production ladder and zero-copy/inverse assertions |
| G4 — production performance | PREPARED | Execute same-host Q7 v1/v2 chain comparison and enforce >=10x |
| G5 — evidence summary / verification handoff | PENDING | Summarize substantive results and route to `software-verification` |

### G0 — candidate/evidence revalidation

Implementation should confirm that later coordination commits still do not modify product-defining paths. If unchanged, retain the existing Q1/Q2/Q4 PASS evidence. Administrative changes do not invalidate it.

### G1 — broad regression attribution

Use `qualification/evidence/q3_candidate.xml` and the prior qualification report first. Group failures by test file/failure class and identify whether they touch the MVSEL2 change surface or affected consumers.

- Clearly unrelated historical version/spec/bootstrap/documentation failures are nonblocking repository-health findings.
- Any failure with a plausible MVSEL2 causal path requires focused investigation and must be resolved before acceptance.
- If existing structured evidence is insufficient, rerun the candidate `pytest -q -m 'not slow'` suite on the workstation. Do not build another historical baseline.

### G2 — production recovery

Use `DOC-MVSEL2_HARDEN1_V3_Q5_RECOVERY_CHECK.py` with the explicit production DB/config above. The check must demonstrate the actual fallback pointer, not only final digest equality.

A failure of checkpoint validation/fallback/resumed equivalence is a real product or harness defect and routes accordingly.

### G3 — production REPAIR2 scale/resources

Consume the qualification-local Q5 clone and run the production REPAIR2 benchmark through all eight materializable rungs. The measured software assertions in A6 are blocking. Workplan metadata fields emitted by the benchmark are advisory.

### G4 — production performance

Use fresh independent v1/v2 qualification clones and the explicit production config. Enforce the frozen >=10x end-to-end floor. If resource conditions make the comparison materially unfair, fix the harness/environment or report `BLOCKED`; do not manufacture comparability through metadata.

### G5 — verification handoff

Produce a compact evidence summary containing candidate commit, material inputs/environment, Q1–Q7 substantive results, broad-failure attribution, production-input immutability result, and material limitations. Then invoke `software-verification`.

Do not create another qualification revision solely to correct report formatting or metadata.

## External qualification needs

G2–G4 require the `local-user-ProBuild` workstation and the production campaign DB/configuration listed above. G1 may also require that workstation only if the existing JUnit evidence cannot resolve attribution.

The inability of the current agent environment to access that workstation is a genuine execution-capability boundary, not a product or design failure.

## Failure routing

- `RETURN_TO_IMPLEMENTATION`: real candidate/test/harness defect affecting A1–A9.
- `DESIGN_REVISION_REQUIRED`: only if passing requires materially changing the frozen MVSEL2/REPAIR2 semantics or the accepted >=10x target.
- `BLOCKED`: required workstation/input/capability genuinely unavailable or a fair material measurement cannot currently be made.
- Harmless cwd/path/quoting/log/report/metadata defects: correct locally and continue.

## Design-revision triggers

Return to design only if evidence requires changing one of these material targets:

- REPAIR1/REPAIR2 semantic equivalence;
- native forward-only v2 execution contract;
- MVSTATE2 compatibility/fallback/recovery semantics;
- zero-full-state-copy / no-inverse-mutation repair contract;
- fixed production ladder or production input semantics;
- the >=10x end-to-end performance requirement;
- a candidate-attributable regression whose correct fix contradicts the frozen product design.

Do not return to design for historical baseline problems, workplan/report hashes, evidence filenames, workplan revision fields, cwd, shell syntax, or unambiguous external path corrections.
