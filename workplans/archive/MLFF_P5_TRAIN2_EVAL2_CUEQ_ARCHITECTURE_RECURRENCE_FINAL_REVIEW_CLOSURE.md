---
kind: implementation-workplan-final-review-closure
workplan_id: CODE-MLFF-P5-TRAIN2-EVAL2-CUEQ-ARCHITECTURE-RECURRENCE-FINAL-REVIEW-CLOSURE
parent_workplan: workplans/archive/MLFF_P5_TRAIN2_EVAL2_CUEQ_ARCHITECTURE_RECURRENCE_REPAIR_WORKPLAN.md
predecessor_reviews:
  - workplans/archive/MLFF_P5_TRAIN2_EVAL2_CUEQ_ARCHITECTURE_RECURRENCE_INDEPENDENT_REVIEW_REOPEN.md
protocol_version: 6.3.0
status: closed-pass
review_verdict: pass
implementation_branch: fix/mlff-p5-train2-eval2-cueq-architecture-recurrence
accepted_project_baseline: b65fa3b02807815d8eca758bc04fb70d514d1f45
reviewed_executable_candidate: 81b84c8eaab5775fc816b8c2726f38f8591bc421
reviewed_executable_tree: 984dd3969ec42c0dffac1e061f6b04d71022c929
predecessor_reopen_commit: e2050d0cabac72c2505407fc9bbfc357803072ea
highest_affected_domain: D4 implementation/concretization under unchanged accepted P5 TRAIN2/EVAL2 phase-separated CuEq architecture
serious_challenge: none
precedence: This independent SSDP 6.3 closure supersedes the active/reopened lifecycle states recorded inside the parent workplan and predecessor review snapshots. The workplan is closed PASS. Those files are historical coordination/evidence records after archival; accepted current architecture remains owned by the permanent MLFF architecture/specification authorities.
---

# P5 TRAIN2 -> EVAL2 CuEq architecture recurrence — final SSDP 6.3 Review closure

## 0. Disposition

**PASS / CLOSED.**

No genuine blocking issue remains on reviewed executable candidate `81b84c8eaab5775fc816b8c2726f38f8591bc421` / tree `984dd3969ec42c0dffac1e061f6b04d71022c929`.

The accepted D3 architecture remains coherent and unchanged:

```text
source / DATA6 / pseudolabel / evaluation / verification = portable e3nn
TRAIN2                                                  = configured transient realization (CuEq here)
only_cueq=false                                         = portable e3nn downstream representation required
```

The previous review rejected a premature D3 escalation because pinned MACE already exposed a dependency-native CuEq -> e3nn `transfer_weights(source_model, target_model, ...)` operation that could populate the existing authorized portable shell. The final candidate uses exactly that lower-level owner. It does not redefine portable identity, weaken the architecture digest, bypass checkpoint authentication, introduce a migration/compatibility representation, or reimplement the MACE converter.

## 1. Independent review scope

The final review reconstructed and challenged:

- the parent recurrence workplan and G0-G10;
- the independent D4 reopen R1-R6;
- accepted phase-separated CuEq specifications and P5/TRAIN2 recovery relatives;
- the canonical MACE execution-architecture descriptor and reconstruction owner;
- `realize_mace_training_model()` and `restore_mace_portable_model()`;
- `authenticate_train2_checkpoint_provider()` and the P5 provider-authentication route;
- pinned `mace-torch==0.3.16` e3nn<->CuEq converter source, including `transfer_weights()`;
- focused real-CUDA parity/authentication/lifetime tests;
- assembled P5 `campaign cross-validate` restart coverage;
- affected-regression disposition against accepted baseline;
- the candidate Project Engineering Memory (PEM) as non-authoritative historical evidence.

Serena and Semgrep were requested as optional understanding aids. Neither is exposed/installed on the independent review host. Under SSDP 6.3 this is not an acceptance failure. The review used exact GitHub commit/tree inspection, candidate/base comparison, repository-wide symbol/text search, changed-source tracing, and direct pinned-dependency source inspection. No conclusion depends on unavailable tool output.

## 2. Core implementation findings

### C1 — H1 portable-construction drift: CLOSED

The earlier independent reconstruction omitted replay-head-only elements. The repaired shared reconstruction owner reads the P5 replay head through pinned MACE dataset semantics and builds the same target-plus-replay element table as real `run_train`.

The real-owner fixture captures actual pinned MACE immediately before CuEq conversion and proves actual portable precursor A equals independent reconstruction B, including a replay-only element. The correction remains in the shared construction owner rather than a P5 exception.

### C2 — H2 CuEq realization drift: CLOSED

Actual MACE `run_train` passes the converter the `torch.device` produced by `mace.tools.init_device`; the old independent path passed a string, changing device-sensitive CuEq realization. The candidate delegates through `init_device` and the real-owner test establishes C == D == F for actual and repeated independent realizations.

No parallel converter or persistent realization identity was introduced.

### C3 — portable projection into the authorized shell: CLOSED

The predecessor candidate used `convert_cueq_e3nn.run()`, which constructs a new e3nn shell from extracted configuration. Foundation-backed models then differed from the already-authorized shell in parameter/buffer registration and static architecture-derived state.

The final repair alters the existing `restore_mace_portable_model()` owner. For CuEq it:

1. receives the already-reconstructed canonical portable model;
2. obtains converter parameters through pinned MACE `extract_config_mace_model()`;
3. delegates state remapping to pinned MACE `convert_cueq_e3nn.transfer_weights()`;
4. transfers into the canonical shell in place;
5. leaves exact post-transfer canonical architecture authentication in the production provider owner.

This is the minimum-complexity D4 correction requested by the reopen: existing owner + existing dependency-native transfer, with the converter-created alternate shell removed from the production CuEq route.

### C4 — fail-closed state/architecture provenance: PASS

`authenticate_train2_checkpoint_provider()` still reconstructs and authenticates the exact TRAIN2 realization before raw checkpoint state controls inference. Raw checkpoint bytes, epoch boundaries, latest companion, live/EMA state digests, materialization/run ancestry and architecture identity remain distinct checks.

For a transient realization, the portable shell digest is captured before transfer and recomputed after transfer. A deliberately mutated post-transfer architecture still raises at the portable guard. There is no warning downgrade, digest tolerance, state-shape-only acceptance, expected-digest substitution, or e3nn fallback.

### C5 — numerical semantics of the target-shell transfer: PASS

Focused CUDA evidence covers foundation-backed FP32, foundation-backed FP64 and scratch FP32, with both live-like and EMA-like trained states. The transferred canonical-shell parameters equal the state produced by pinned MACE's ordinary native projection for the corresponding learned parameters, while the canonical shell retains its authorized architecture.

The portable result is also compared against the CuEq realization under the already accepted `MaceAccelerationParityPolicy`; no repair-specific numerical tolerance was added. Production checkpoint authentication followed by bounded provider inference succeeds without a forward override and agrees with the CuEq reference under that existing authority.

### C6 — lifetime and sibling behavior: PASS

Accepted and rejected authentication paths are exercised repeatedly on CUDA and do not accumulate allocator-resident model ownership. `only_cueq=true` remains outside the phase-separated conversion path, and OEq was not mechanically broadened into this repair without evidence.

## 3. Existing stakeholder TRAIN2 work

The candidate-bound G5/R3 evidence reauthenticates all five expensive completed stakeholder TRAIN2 runs through the corrected production owner rather than deleting or retraining them. It checks latest-companion and earlier-boundary semantics, EMA state, exact training architecture, exact portable architecture, and finite provider forwards.

A subsequent stakeholder `cross-validate` run with TRAIN2 relaunch prohibited reused the existing five runs and entered EVAL2 with zero TRAIN2 launches. Its eventual typed scientific inadmissibility is a downstream method outcome (replay-retention/target threshold), independently corroborated against the saved MACE model, not an architecture/projection failure. This workplan does not change those scientific thresholds to manufacture acceptance.

## 4. Focused and assembled acceptance

The final focused CUDA suite removes the predecessor strict xfail and covers the materially required G6/R4 cases:

- A == B portable construction;
- C == D == F CuEq realization and determinism;
- real checkpoint authentication;
- native transfer into the authorized portable shell;
- real bounded EVAL2 inference with no provider/forward override;
- dtype, replay-element, foundation and frozen-normalization negatives before inference;
- deliberate post-projection architecture drift rejection;
- live-like and EMA-like transfer semantics;
- success/failure accelerator-lifetime behavior;
- `only_cueq=true` regression behavior.

The assembled P5 test parametrizes e3nn and CuEq. The CuEq case uses the real CLI/parser, production P5 materialization, qualified wrapper, pinned MACE TRAIN2 on CUDA, durable summary/checkpoint, serial EVAL2 provider authentication, canonical projection, and real provider forwards. It interrupts at the TRAIN2/EVAL2 boundary and verifies that the resumed invocation performs EVAL2 without relaunching completed TRAIN2 jobs. The bounded harness continues to own only downstream toy-science statistics; the real provider is actually invoked on every resumed EVAL2 chunk, while a separate focused no-override test proves the production inference path using the real returned predictions.

Together those two evidence layers satisfy the real-owner boundary without making the tiny fixture's unrelated scientific admissibility a prerequisite for the execution/authentication claim.

## 5. Affected regression and baseline discrimination

The candidate records the final affected surface as:

```text
1930 passed, 2 skipped, 1 failed, 0 xfailed
```

The one failure is named:

```text
tests/test_mlff_target_size_p5f_structure.py::
  test_p5f_no_screening_continuation_owner_is_reachable_from_post_selection
```

This is not a candidate regression. The test file has identical blob identity on candidate and accepted baseline, and the `post_selection_execution.py` source it scans also has identical blob identity on candidate and accepted baseline. The structural oracle forbids the literal `restart_latest` marker even though the accepted baseline already contains the authorized post-selection continuation seam. No product code or oracle is changed merely to obtain a green count.

There are no required strict xfails remaining. GitHub exposes no commit-status checks for the candidate; the repository's only workflow is documentation-PDF publication for `docs/**` paths, which is not a code-CI authority for the changed executable files. The absence of a status check is therefore not reclassified as a product failure.

## 6. Parent invariant assessment

1. **Fail-closed architecture authentication — PASS.** Exact training-realization equality precedes checkpoint-state admission; exact portable equality follows projection.
2. **Actual TRAIN2 identity — PASS.** Runtime summary continues to represent the state-owning transient training realization.
3. **Phase-separated CuEq — PASS.** CuEq remains TRAIN2-only for this qualified route; EVAL2 receives canonical portable e3nn.
4. **Frozen scientific method — PASS.** No target/replay membership, foundation/head, optimizer/loss/LR, EMA, precision, batch/exposure, fold/seed/horizon, ranking or threshold semantics changed.
5. **Canonical normalization — PASS.** No fold-local `avg_num_neighbors` recomputation is introduced.
6. **State provenance — PASS.** Architecture, raw checkpoint, boundary, continuation and live/EMA identities remain separately authenticated.
7. **Portable projection proof — PASS.** State is dependency-natively remapped into the authorized shell and exact architecture is checked afterward.
8. **Lifetime ownership — PASS.** Temporary accelerator owners are retired on success and failure paths.
9. **Scheduler phase ownership — PASS.** EVAL2 remains outside TRAIN admission slots.
10. **Non-destructive recovery — PASS.** Existing completed runs are reauthenticated and reused rather than deleted.

No forbidden repair strategy from the parent workplan was introduced.

## 7. Architecture / Serious Challenge disposition

**No Serious Challenge.**

The earlier shell mismatch did not prove the accepted portable identity contract impossible. Once the dependency-native lower-level transfer was applied to the existing canonical target shell, exact architecture and accepted numerical semantics were both preservable. The problem therefore remains correctly classified as D4 concretization drift under coherent D3.

Permanent architecture/specification documents correctly remain unchanged.

## 8. Project Engineering Memory closeout

The candidate PEM correctly keeps this episode out of FF-001 recurrence counts because the strict Protocol 6.3 accepted-repair chronology needed to promote a later event into a confirmed recurrence has not been established merely by similarity.

`NT-001` may remain `REVIEW_REQUIRED` until this candidate becomes part of the accepted project base; after this independent PASS its reason should be interpreted as integration/accepted-base reconciliation rather than unresolved D4 correctness. On accepted-base integration, refresh the notice/evidence route and retire or resolve it without manufacturing an additional recurrence occurrence.

The strongest bounded positive lesson from this cycle is consistent with existing SP-001/SP-002/SP-003/SP-004: preserve strict fail-closed identity boundaries, diagnose with the real dependency owner, and repair duplicated/rebuilt representation at the owner by reduction/rewiring. Here, transferring authenticated state into the already-authorized shell solved the problem with less machinery than introducing a new portable identity or weakening the descriptor.

## 9. Deferred qualification and nonblocking residuals

Broad production-scale/final-release GPU qualification remains deferred under standing project policy. The bounded real-CUDA evidence in this workplan is defect-specific functional evidence needed to establish the CuEq construction/projection claim; it is not represented as final production-scale GPU qualification.

The pre-existing P5-F structural-oracle failure noted in section 5 remains a separate baseline test-maintenance issue. It does not falsify this repair and should not be 'fixed' inside this workplan by removing the accepted restart seam.

## 10. Final closeout

**PASS. No further reopen.**

The parent workplan and predecessor review are closed by this record and should be treated as archived historical coordination/evidence snapshots. Future reopening of this architecture requires new evidence that falsifies an accepted invariant—for example, a governed MACE realization whose dependency-native state transfer cannot preserve canonical portable semantics, a state-provenance bypass, a real lifetime leak, or a recurrence of construction drift outside the shared owner repaired here.
