---
kind: implementation-workplan
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 4
status: READY_FOR_IMPLEMENTATION
protocol_version: 3.0.0
analysis_base_commit: ccb4f9c472ca296d9fcacb800638a077b32ee107
candidate_commit: a9cb41ad9b1c6305de195f1a88b71ea098e582b7
supersedes: workplans/active/DOC-MVSEL2_HARDEN1_V3_REV3_MATERIALITY.md
---

# MVSEL2 Post-Implementation Hardening — Final Materiality-First Qualification Workplan

## Objective

Finish qualification of the already-implemented MVSEL2/REPAIR2 hardening candidate by exercising only software behaviors and material execution conditions that affect acceptance, while preventing harmless harness/path/report errors from restarting the workflow.

Frozen product candidate:

`a9cb41ad9b1c6305de195f1a88b71ea098e582b7`

No product-source change is planned. Product code changes are justified only if substantive qualification exposes a real defect.

## Diagnosis

The previous qualification failures did not demonstrate an MVSEL2 product defect:

- the historical Q3 baseline could not collect the same modern test tree and was therefore not a useful regression oracle;
- Q5/Q7 used an incorrect inferred `campaign.toml` path;
- Q6 never ran because it was coupled to the Q5 scratch clone.

Revision 3 removed the metadata-heavy failure modes, but final review found three additional material harness risks that must be corrected before workstation execution:

1. **Q5/Q7 clone helpers hard-link non-database `.mdstats` files back to production.** Qualification scratch must be physically independent so no accidental in-place write can propagate to production.
2. **Q5 assumes the second-highest checkpoint is the expected fallback without first proving it is valid and compatible.** The product contract is to resume from the highest remaining valid compatible checkpoint.
3. **Q6 was specified to consume the deliberately corrupted Q5 clone.** Scale/resource qualification must use independent clean scratch state so recovery fault injection cannot contaminate REPAIR2 qualification.

These are qualification-harness corrections only. They do not change the frozen MVSEL2/REPAIR2 product design.

## Frozen material design

The product target remains unchanged:

- REPAIR2 policy/default/validation mirrors REPAIR1 except v2 authority/schema identity.
- Persisted REPAIR2 trace and terminal order remain equivalent to the accepted REPAIR1 oracle on shared fixtures/policies.
- Production v2 execution uses the native forward-only MVIDX path without inverse-array mapping inside the v2 execution boundary.
- Interrupted MVSEL2 resumes from the highest valid compatible MVSTATE2 checkpoint and produces the exact uninterrupted result.
- REPAIR2 may use compatible selector checkpoint state only before repair divergence; later pure-selector state must not overwrite divergent repair history.
- Rejected repair proposals make no full forward-state clone; analytical hypothetical scoring is exact and accepted mutation occurs only for the chosen proposal.
- The production performance target remains end-to-end **>=10x** v2 selector+repair speedup over v1 on the same host, production input, configuration, and materially comparable resource policy.

Qualification policy remains materiality-first:

- broad-suite failures are attributed to the candidate rather than treated as a globally-green gate;
- no historical/counterfactual test-tree baseline is required;
- harmless cwd, activation, quoting, scratch/log, unambiguous path, and report corrections may be made locally;
- valid Q1/Q2/Q4 evidence may be reused because the candidate and material exercised surfaces have not changed;
- workplan/report/hash/version metadata are advisory unless they materially affect an executed claim.

## Acceptance-critical requirements

- **A1 — Focused correctness.** The focused MVSEL2/MVSTATE2/REPAIR2/migration regression set passes for the frozen candidate.
- **A2 — Adjacent compatibility.** The adjacent MVSEL1/REPAIR1 consumer regression remains passing.
- **A3 — No candidate-caused broad regression.** A broad-suite failure blocks only when there is a plausible causal connection to the MVSEL2 hardening/affected consumers or focused follow-up demonstrates such a connection. Mere inability to prove historical pre-existence is not itself blocking.
- **A4 — Installed artifact works.** A wheel built from the candidate installs into an isolated target and imports from that target outside the source checkout; `workplans/` is not shipped.
- **A5 — Real recovery works.** On an independent production-sized scratch snapshot, after corrupting the newest MVSTATE2 checkpoint, the runtime resumes from the **highest remaining valid compatible checkpoint** and the final selection digest exactly equals uninterrupted execution.
- **A6 — Production REPAIR2 resource behavior is correct.** On an independent clean scratch snapshot with 36,408 candidates / 165 families, the fixed-eight ladder through 16,384 executes; rejected proposals make zero full forward-state copies; inverse mutation is false; the native forward-only path remains in use.
- **A7 — Performance target is met.** On the same workstation, production input/configuration, and materially comparable resource policy, the end-to-end v2 selector+repair chain is at least 10x faster than v1.
- **A8 — Production inputs are protected.** Qualification opens production inputs only for read/snapshot purposes and performs all mutation/fault injection on physically independent qualification-local copies. Qualification must not create hard links or symlinks from mutable scratch state back to production.
- **A9 — Candidate remains the tested product.** Qualification does not introduce or depend on later product/runtime/test/package changes while claiming results for `a9cb41ad...`.

## Expected implementation / coordination surface

Before target qualification, implementation may modify only qualification coordination/harness surfaces needed to satisfy this workplan, principally:

- `workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_RUN_CARD_SIMPLIFIED.md`
- `workplans/active/DOC-MVSEL2_HARDEN1_V3_Q5_RECOVERY_CHECK.py`
- `workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_DRIVER.py`
- an additional qualification-only Q6 snapshot/preparation helper if that is cleaner than extending an existing helper
- `qualification/` evidence/scratch outputs

Do not modify `mdstats/`, product tests, package/build metadata, specifications, or release product surfaces unless a real product defect is found.

The production REPAIR2 benchmark may be invoked as-is. Its workplan metadata arguments are diagnostic fields, not acceptance criteria; do not modify product/benchmark semantics merely to synchronize those fields.

## Non-goals

- redesign MVSEL2 or REPAIR2;
- manufacture a historical green test baseline;
- make the entire repository suite green;
- rerun valid Q1/Q2/Q4 solely because coordination documents changed;
- synchronize advisory hashes/revision fields/report metadata for cosmetic consistency;
- perform GPU qualification in this gate sequence.

GPU qualification remains a separate final-release obligation.

## Material production inputs

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

The explicit config path is the intended input. If it has moved, qualification may correct the path without design/implementation cycling when exactly one unambiguous campaign configuration for this FP32 campaign can be identified. Ambiguous competing configurations are a real input blocker.

Production inputs must be treated read-only. If an external process changes them during qualification, invalidate that affected snapshot/attempt and rerun from a stable fresh snapshot; do not classify externally concurrent mutation as a candidate failure.

## Qualification snapshot rule

Q5, Q6, and Q7 must use independent qualification-local scratch roots.

- Copy mutable `.mdstats` content with ordinary physical copies (`copy2`/equivalent), not hard links or symlinks.
- Scratch roots must resolve outside the production campaign tree.
- Q5 fault injection may modify only the Q5 snapshot.
- Q6 must **not** consume the corrupted Q5 snapshot. Prepare a fresh clean Q6 snapshot and ensure the required v2 selection authority/checkpoints exist there before the REPAIR2 benchmark.
- Q7 uses fresh independent v1 and v2 snapshots for each valid comparison attempt.

A snapshot/copy-path mistake is a harness defect: correct it locally and restart only the affected check.

## Gates

| Gate | Status | Purpose |
|---|---|---|
| G0 — candidate/evidence revalidation | PREPARED | Confirm product boundary and applicable Q1/Q2/Q4 evidence |
| G1 — qualification harness hardening | PENDING | Make Q5–Q7 scratch state independent and recovery expectation correct |
| G2 — broad regression attribution | PENDING | Attribute existing candidate broad-suite failures; targeted follow-up only when needed |
| G3 — production recovery | PENDING | Execute Q5 corrupt-newest/highest-valid fallback check |
| G4 — production REPAIR2 scale/resources | PENDING | Execute Q6 on a fresh clean snapshot |
| G5 — production performance | PENDING | Execute fair same-host Q7 comparison with noise-safe retry handling |
| G6 — evidence summary / verification handoff | PENDING | Summarize substantive evidence and invoke `software-verification` |

### G0 — candidate/evidence revalidation

Confirm the coordination head still has no changes under product-defining paths relative to `a9cb41ad...`. If so, retain existing Q1/Q2/Q4 PASS evidence. A report containing credible exact-candidate results is sufficient; advisory evidence-file/hash completeness is not required.

### G1 — qualification harness hardening

Before workstation execution:

1. Replace hard-link clone behavior in the Q5/Q7 qualification helpers with physical copies.
2. Make Q5 determine the expected fallback **before fault injection** by validating checkpoints individually and selecting the highest compatible checkpoint below the one to be corrupted. The expected result must not be inferred from the resume outcome itself.
3. Update the Q5 assertion to compare the actual resume pointer against that pre-established highest-valid expectation.
4. Make Q6 use a fresh clean snapshot, not Q5 state. Prepare/verify the required v2 selection authority and compatible checkpoints on that Q6 snapshot before measuring REPAIR2.
5. Keep Q7 fresh v1/v2 snapshots independent of Q5/Q6 and each other.
6. Update the simplified run card to describe these material rules and remove any Q6 dependency on the Q5 clone.

Run cheap syntax/import checks on changed qualification helpers. These are harness changes, not a new product candidate.

### G2 — broad regression attribution

Use the existing candidate JUnit/report first.

Attribution rule:

- A failure is **candidate-relevant** when its failing test/trace/contract exercises an MVSEL2/REPAIR2 changed module, a directly affected campaign consumer, or a public/persisted contract changed by this hardening.
- A failure is **nonblocking repository health** when it is clearly outside that dependency surface (for example unrelated historical version/spec/bootstrap/documentation contracts).
- If static attribution is genuinely ambiguous, run the smallest focused failing test/file or affected-consumer set needed to resolve causality.
- Rerun the entire candidate non-slow suite only if the existing structured evidence is insufficient to identify the relevant failures; do not build a historical baseline.

Do not block merely because a failure cannot be proven to have existed historically. Block when evidence gives a plausible causal path to the candidate and focused follow-up does not clear it.

### G3 — production recovery

Use the strengthened Q5 helper on a physically independent scratch snapshot.

Before corrupting anything, identify the newest checkpoint and independently establish the highest older checkpoint that is valid/compatible. Then corrupt only the newest checkpoint in scratch and require:

- actual reported resume pointer equals that pre-established highest-valid fallback;
- resumed selection digest equals uninterrupted selection digest;
- native forward-only runtime path is used;
- production inputs remain untouched by qualification.

If the immediate previous rung is invalid, falling farther back is correct when it is the highest remaining valid compatible checkpoint; the harness must not fail a correct implementation merely because it assumed every prior checkpoint was valid.

### G4 — production REPAIR2 scale/resources

Create a **fresh Q6 snapshot** from production. Do not inherit Q5 corruption or recovery mutations.

On that clean snapshot, prepare or verify the v2 selection authority/checkpoint state required by the benchmark, then measure all fixed-eight materializable rungs through 16,384. Require A6.

A missing authority caused only by snapshot preparation is a harness/preparation problem; repair preparation and rerun G4. A failure of the actual REPAIR2 ladder/resource assertions is substantive.

### G5 — production performance

Use fresh independent v1/v2 snapshots and the explicit config. Keep materially relevant resource settings identical.

Measurement policy:

1. A valid comparable pair with speedup >=10x passes A7.
2. If the first valid pair is <10x, do **not** immediately declare a product failure. First check for material measurement invalidity such as competing load, differing worker/thread policy, wrong config/input, or failed fresh-snapshot preparation.
3. If the first pair was materially invalid, discard it with the reason and rerun a fresh pair.
4. If the first pair was materially valid but below 10x, run two additional fresh comparable pairs and use the median of the three valid speedups for the gate decision.
5. Median <10x after three valid comparable pairs is a substantive performance failure.

Do not discard a valid slow run merely because it misses the target, and do not change the resource policy to manufacture a pass.

### G6 — verification handoff

Produce a compact evidence summary containing:

- frozen candidate commit;
- material workstation/input/config/resource conditions;
- Q1/Q2/Q4 reused results;
- G2 attribution conclusion;
- Q5 recovery result;
- Q6 scale/resource result;
- Q7 performance measurements/decision;
- any true limitations or external-input instability.

Then invoke `software-verification`.

Do not create another workplan or qualification revision solely for report formatting, hashes, filenames, timestamps, or equivalent administrative corrections.

## Evidence reuse

Q1/Q2/Q4 may be reused because the frozen candidate and the material code/package surfaces they exercised are unchanged. Reuse does not depend on matching workplan hashes or revision labels.

Q3 historical-baseline evidence is diagnostic only and is not required for acceptance.

Q5–Q7 have not produced substantive PASS evidence and must execute under the revised material rules above.

## Failure routing

- `RETURN_TO_IMPLEMENTATION`: a real candidate defect or qualification-harness defect that materially prevents/checks the intended behavior. Harness-only fixes remain coordination changes and rerun only affected gates.
- `DESIGN_REVISION_REQUIRED`: only when passing requires changing frozen MVSEL2/REPAIR2 semantics or the accepted >=10x product target.
- `BLOCKED`: a required workstation/input/capability is genuinely unavailable, production input is ambiguously identified, or a fair measurement cannot currently be made.
- harmless cwd/path/quoting/log/report/metadata issue: correct locally and continue.

## External qualification needs

G3–G5 require the `local-user-ProBuild` workstation and production campaign inputs above. G2 may use existing evidence without workstation execution unless targeted reruns are needed.

## Design-revision triggers

Return to design only if evidence requires changing one of these material targets:

- REPAIR1/REPAIR2 semantic equivalence;
- native forward-only v2 execution contract;
- MVSTATE2 compatibility/fallback/recovery semantics;
- zero-full-state-copy / no-inverse-mutation repair contract;
- fixed production ladder/input semantics;
- the >=10x end-to-end performance requirement;
- a candidate-attributable regression whose correct fix contradicts the frozen product design.

Do not return to design for historical baseline problems, scratch/snapshot implementation, config-path spelling, workplan/report hashes, evidence filenames, revision fields, cwd, shell syntax, or other non-material coordination corrections.
