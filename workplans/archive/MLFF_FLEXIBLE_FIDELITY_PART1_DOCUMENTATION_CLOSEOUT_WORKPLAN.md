---
kind: implementation-workplan
workplan_id: DOC-MLFF-FLEXIBLE-FIDELITY-PART1-CLOSEOUT-V1
protocol_version: 5.4.0
status: completed
---

# MLFF Flexible-Fidelity Part 1 Documentation Closeout Workplan

## Objective

Close Part 1 of the flexible-fidelity redesign without changing executable MLFF behavior. The repository must end Part 1 with current documentation and examples describing the actual fixed target-size-v5 runtime, while the accepted configurable `(n1,n2,n3)` / independent full-horizon `n` design remains proposed implementation authority only in `CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1` until Part 2 executes and passes acceptance.

## Diagnosis and protected concerns

The original documentation-first workplan attempted to publish the future flexible-fidelity contract into current architecture/specification/example surfaces before the parser/runtime implemented it. Independent review found three classes of remaining closure risk:

1. current-product documentation or examples could advertise proposed Part 2 semantics or unsupported configuration;
2. older active workplans could continue to impose fixed `3/10/30` requirements during Part 2 unless precedence becomes explicit at implementation start;
3. the Stage-11 SIZE-FIDELITY1 graph could overstate a diagnostic/consequential winner-recall value as an independent hard predicate beyond the executable v2 policy.

The closeout therefore protects truthful current-state authority, one unambiguous future-transition authority, executable-truthful examples, and regression-test strength.

## Frozen end state

- No executable MLFF behavior changes in Part 1.
- Current architecture/specifications/guides/examples describe the existing fixed target-size-v5 runtime, including fixed `3/10/30` target-size screening where relevant.
- Proposed `(n1,n2,n3)` flexible-fidelity semantics are not current product authority before Part 2; they remain owned by `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK_WORKPLAN.md`.
- `campaign.toml.example` must not expose target-size controls that the current parser/runtime ignores or rejects.
- Current SIZE-FIDELITY1 documentation must match the implemented target-size-v5 v2 calibration contract and may preserve historical material separately.
- Stage-11 must describe actual SIZE-FIDELITY1 v2 configurable calibration dimensions and hard predicates. Winner recall may be recorded/derived under the default finalist-recall policy but is not an independent universal hard requirement unless executable policy makes it one.
- Permanent tests must continue to exercise the real package/public API. Missing optional dependencies are reported as unavailable validation; tests must not be weakened into source-text substitutes merely to run in a constrained environment.
- Part 2 precedence begins when implementation under `CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1` begins. It supersedes older active-workplan requirements only on the target-size fidelity epoch/state/schema/configuration surface; unrelated requirements remain authoritative.
- Completed/superseded Part 1 workplans are archived. The Part 2 codebase workplan remains active.

## Delegated mechanics

Exact prose, local test organization, and whether transition precedence is repeated in each older plan or centralized in the active-workplan index are implementation-local, provided there is exactly one unambiguous effective rule and no competing current authority.

## Reopen only on evidence

Reopen design only if repository evidence shows that current runtime/configuration ownership differs materially from the reviewed target-size-v5 v2 implementation, that a supposedly current document is actually release-pinned/historical, or that the Stage-11 graph semantics cannot be reconciled with executable SIZE-FIDELITY1 policy without changing product behavior. Do not reopen the accepted flexible-fidelity scientific design merely because it is not yet implemented.

## Implementation obligations

### C1 - Restore current-vs-proposed documentation authority

- Remove Part 2 implementation chronology/proposed flexible-fidelity semantics from permanent current-product documents and current configuration examples.
- Keep current fixed-runtime behavior coherent and readable.
- Preserve the future flexible-fidelity contract in the Part 2 workplan rather than duplicating it into current specs.

Acceptance:
- current docs/examples contain no claim that `(1,3,10)/n` flexible fidelity is already implemented;
- current docs do not point users to an active workplan as required runtime configuration guidance.

### C2 - Make `campaign.toml.example` executable-truthful

- Remove target-size epoch/ladder/survivor/monitor/seed controls that current target-size-v5 code does not read or explicitly rejects.
- Retain only size-convergence keys consumed by the current parser/runtime plus the actual TRAIN2 horizon authority under `[training]`.
- Do not introduce the future `fidelity_epochs` key in Part 1.

Acceptance:
- TOML parses;
- negative assertions cover retired/ignored/rejected target-size controls;
- `[training].max_num_epochs` remains the current full-horizon setting.

### C3 - Reconcile current SIZE-FIDELITY1 authority

- Add/maintain one current SIZE-FIDELITY1 specification matching `mdstats.size-fidelity1.coarse-screen-calibration.target-size-v5.2026-08.v2`.
- Describe current coarse endpoint candidates, short endpoint, full/final reference endpoint, monitor/equivalence candidates, diagnostics, finalist-recall thresholds, zero boundary-finalist misses, and uninterrupted trajectory identity as implemented.
- Preserve historical sources separately.
- Do not discuss the proposed flexible Part 2 transition in this current spec.

Acceptance:
- current spec and public `SIZE_FIDELITY_VERSION` agree;
- current spec contains no `(1,3,10)/n` or Part 2 implementation claim.

### C4 - Correct Stage-11 SIZE-FIDELITY1 semantics

- Synchronize authority version and calibration dimensions with target-size-v5 v2.
- Represent the executable hard predicates: conditional monitor/full-promotion equivalence, configured coarse and short finalist-recall thresholds, zero boundary-finalist misses, and uninterrupted seed-size trajectory identity.
- Remove `winner_recall_equals_1` as an independent universal hard predicate.

Acceptance:
- graph JSON parses;
- graph authority version equals exported runtime version;
- graph hard requirements match executable policy semantics.

### C5 - Preserve regression strength

- Keep package/public-export assertions rather than replacing them with source-string checks.
- Update only stale release/revision expectations and add current documentation/configuration assertions needed for this closeout.
- Treat unavailable ASE-dependent collection as unexecuted, not passed.

Acceptance:
- touched tests compile;
- when dependencies are available, the affected documentation tests must import the real package and exercise public exports;
- no test is weakened solely to accommodate the current environment.

### C6 - Establish Part 2 precedence and close lifecycle

- Establish the implementation-start precedence rule centrally in `workplans/active/README.md` or equivalently without duplicating mutable authority unnecessarily.
- Archive `DOC-MLFF-FLEXIBLE-FIDELITY-EPOCH-CONTRACT-V1` as superseded by this truthful-staging closeout.
- Archive this closeout workplan after its obligations are satisfied.
- Keep `CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1` active and unchanged in scientific/runtime target semantics.

Acceptance:
- neither Part 1 workplan remains under `workplans/active/`;
- Part 2 workplan remains active;
- active-workplan precedence is unambiguous at the moment Part 2 implementation begins.

## Final acceptance

Before closeout:

1. run `git diff --check` for the assembled candidate;
2. parse affected TOML and JSON;
3. compile touched Python tests;
4. verify current/proposed authority separation by negative search;
5. verify changed Markdown links;
6. verify canonical architecture assembly and tracked architecture PDF manifest/source hashes remain consistent when those artifacts are unchanged;
7. attempt the affected real package tests and report missing ASE or another dependency as unavailable rather than weakening them;
8. verify archived/active workplan placement and Part 2 precedence;
9. re-read the final diff for unintended executable changes.

Production/GPU qualification is not required because Part 1 changes documentation, examples, tests, graph metadata, and workplan lifecycle only; it must not change MLFF execution behavior.

## Completion disposition

Completed Part 1 leaves the fixed target-size-v5 runtime as current product truth and the configurable flexible-fidelity design as the sole active Part 2 implementation target. After this workplan is archived, implementation may proceed directly under `CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1` without another Part 1 architecture review unless new evidence triggers redesign.
