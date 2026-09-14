# MLFF post-selection restoration — independent implementation Review R2

**Date:** 2026-09-14  
**Protocol:** SSDP 6.3  
**Reviewed candidate:** `cd0c3a16d08f218ac31030d061178bf25d2aed25` on `fix/mlff-post-selection-method-restoration`  
**Workplan:** `workplans/active/MLFF_POST_SELECTION_UNIVERSAL_LOSS_MONITOR_AND_CV_METHOD_RESTORATION_WORKPLAN.md`  
**Disposition:** **NO-PASS — implementation/specification blockers from R1 are closed; G13 qualification remains blocking**

## 1. Challenge disposition

No Serious Challenge is raised to current D1, D2, or D3. The accepted architecture remains coherent and acyclic. The earlier G1B contradiction was a D4 specification defect, not a defect in the D3 dependency model.

## 2. R1 blocker reconciliation

### 2.1 G1B ancestry contradiction — CLOSED / PASS

The current P5 D4 specification now states the same dependency direction as accepted D3:

```text
owning role/run plan
  -> PostSelectionFittedPreparation
  -> PostSelectionMaterialization / run evidence
```

The CV-plan and final-production-plan parent lists no longer contain fitted-preparation ancestry. The specification explicitly forbids current CV/final plans from binding a fitted-preparation digest and states that materialization/run evidence bind the downstream preparation instead.

The executable representation already conforms: `PostSelectionCvPlan` and `FinalProductionPlan` have no fitted-preparation parent field; `PostSelectionFittedPreparation` binds `owner_plan_digest` and, for foundation modes, `common_monitor_record_digest` plus composition-transfer evidence; `PostSelectionMaterialization` binds `preparation_digest`. No product-runtime source was added or changed for the G1B repair.

The added negative/positive owner tests exercise the actual representations rather than introducing a compliance wrapper. This closes the prior D4 blocker without changing D1/D2/D3.

### 2.2 Candidate-bound G11/G12 evidence — CLOSED / PASS for functional implementation acceptance

The R1 evidence-applicability blocker is resolved. The implementation/spec/test state exercised before commit was `10d09f4d192b5788f67f75e0a84bd139c8802b00` plus the exact four-file spec/test delta recorded in the workplan. Commit `cd0c3a16d08f218ac31030d061178bf25d2aed25` packages exactly those four files plus the evidence/workplan note; no product-runtime source changed between the tested executable candidate and committed candidate.

Recorded focused/affected evidence is therefore applicable to `cd0c3a16...`:

- P5 method-owner / G1B / Hypothesis suite: 24 passed;
- CV identity/publication owner suites: 33 passed;
- assembled P5-G lifecycle: 3 passed;
- affected implementation matrix: 554 passed, 17 CUDA-specific skipped;
- MACE execution + replay/MACE P5 recovery owners: 28 passed;
- direct P5 materialization/CV/memory/context owners: 61 passed;
- real-owner assembled MACE qualification: 5 passed, 1 CUDA-specific skipped;
- pinned MACE source qualification resolved `mace-torch==0.3.16`, source-tree digest `0a59f3411759db89f7dc37aeb635078ef2d02781ba0b64e74e36ed1e2d646c1f`, and native `mace.modules.loss.UniversalLoss`.

The failed exploratory 16-worker run of the small assembled-MACE suite does not invalidate the serial real-owner result because concurrent pytest execution is not the governed MACE semantic claim, the larger affected xdist suites passed, and this narrow D4 repair changed no product import/runtime source. The broader `tests/test_mlff_*.py` exploratory sweep is likewise not used as positive acceptance evidence; its known release/document/version-drift failures are not being averaged into a pass.

GitHub automation at this candidate only proves documentation generation, not functional qualification; the functional acceptance above remains the candidate-bound local evidence recorded by the workplan. That distinction is preserved rather than treating CI absence as either pass or failure.

Serena and Semgrep were not available in the Review environment; a direct capability probe found no local executables, and the implementation record states its configured analyzer/cache locations were read-only. Symbol/owner and structural claims were therefore cross-checked through repository source, exact candidate diff, dataclass/payload ownership, and real-owner tests. Tool absence does not relax the claims and is not itself a blocker.

## 3. Additional drift found in R2

`workplans/active/README.md` still described the pre-adjudication state: it claimed current D1 required weighted energy+forces+stress with fold-local monitoring and that the repaired method papers remained merely proposed. This contradicted the accepted D1/D2 state and the active workplan. The active-work index is updated in the same review commit to describe the current accepted method and remaining G13 state.

This was coordination/documentation drift, not product behavior and not a reason to add runtime machinery.

## 4. Remaining blocker — G13

G13 remains genuinely unexecuted for the current candidate. The repository record explicitly states that available prior LTA campaign evidence predates this restoration, lacks current-candidate identity/writable run evidence, and had rejected checkpoints. It therefore cannot be promoted into current-candidate scientific qualification.

Before final PASS, execute the existing G13 contract without changing the method or weakening gates:

1. run a bounded current-candidate pilot on representative real LTA data using the restored P5 method;
2. persist a true pre-update foundation baseline and the initial restored checkpoint evidence;
3. record common-monitor target RMSE, TRUE_DFT replay RMSE/degradation, resolved UniversalLoss/dimensional-threshold/exposure identity, selected-head residual-E0 identity, composition-transfer result, corpus counts/order, and exact common-monitor identity;
4. if the pilot passes without material replay forgetting comparable to the prior failure regime, run the required three-fold affected qualification under the accepted method;
5. preserve final production-scale GPU qualification for the final complete release package as already required by project policy; and
6. if the correctly restored method still materially forgets replay, reopen D1/D2 rather than adding a D4 compensating mechanism.

This is an evidence/qualification blocker. No further code repair is authorized by this Review unless G13 exposes a concrete D4 nonconformance.

## 5. Impact and closeout state

Current implementation/specification conformance, G1B, G11, and G12 pass this Review. The workplan remains active because closeout condition 10 (bounded pilot + required three-fold qualification) is not met. Documentation/history/dependency and closeout-learning reconciliation remain final closeout obligations after G13; production-scale GPU qualification remains deferred to the final release package.

**Final R2 verdict: NO-PASS, solely because required G13 current-candidate scientific qualification remains unavailable.**
