---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R13.6
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R13.5
parent_scientific_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
revision: 13.6
status: reopened
reviewed_evidence_head: 90a19ce67dbf5d6147b0d4cabaab6028adb448e5
frozen_executable_commit: 97fa48fc4a8e5be0da8cbcd22ba10248fa37acee
frozen_executable_tree: 9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6
frozen_source_digest: 7772ad5f0329aa1d42f96cf89bbf178252981902e9d4d5468f10ff1312da9ed6
review_verdict: NO-PASS
amended_date: 2026-09-01
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
scope: preserve accepted executable/runtime mechanics; require final qualification to consume an operator-supplied pre-existing production campaign and independently reproducible external DFT artifacts rather than a newly generated temporary lifecycle or self-declared reference bundle
---

# P7 revision 13.6 — real production owner and external-DFT provenance closure

## 1. Review disposition

The R13.5 evidence fixes the qualifying interpreter identity and demonstrates a complete `RELEASE_QUALIFIED` graph plus fresh-process reauthentication. Those mechanisms are accepted as integration evidence. P7 nevertheless remains **NO-PASS** because the evidence still does not cross two frozen semantic-owner boundaries.

No executable defect is established. Keep candidate `97fa48fc4a8e5be0da8cbcd22ba10248fa37acee`, tree `9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6`, source digest `7772ad5f0329aa1d42f96cf89bbf178252981902e9d4d5468f10ff1312da9ed6` frozen unless the genuine production run exposes a source defect.

## 2. R13.6-B11G — the claimed production campaign was still created for qualification

R13.5 explicitly required the operator's **pre-existing** production config/workspace and forbade creating or regenerating P1-P5 state for qualification.

The R13.5 evidence instead records campaign root:

```text
/tmp/mdstats_p7_r13_5_production
```

and says that campaign "completed the full production lifecycle" as part of this closure run. It again reports `N=4`, member `seed-5`, and checkpoint SHA `44297de809ab54e4604524ceb5b463ea21ca1336a2ab1e88fff062aba7d8cabb`, the same checkpoint SHA already seen in the previously rejected bounded tiny-MACE fixture lineage.

A newly created temporary campaign is not the operator's existing production product merely because it runs production owner classes. This is proxy/integration evidence, not final B11 evidence.

### Required end state

**No campaign creation is permitted in R13.6 final qualification.**

The qualification invocation must start from an operator-supplied existing campaign configuration/workspace that was created and advanced by the real user workflow independently of R13.4/R13.5/R13.6 acceptance attempts.

Before any P7 operation, record from that existing workspace:

- absolute config path and workspace path;
- campaign ID and generation;
- current selected-binding digest, actual `N_selected`, exact `T_selected` digest;
- post-selection CV acceptance digest;
- final-production plan/reclosure digest;
- already-existing P5 publication digest;
- member ID/run identity/checkpoint locator/checkpoint SHA/target head;
- state-store identity sufficient to show these records existed before the R13.6 qualification invocation.

Then B11 must consume those exact already-existing records through the production P7 owners. P7 may create only its own descendant qualification/reference/deployment evidence.

### Hard anti-shortcut rules

For final closure, do not:

- create a new campaign, config, workspace, source bundle, P1-P5/P6 state, CV result, final-production result, or publication;
- use any path created solely for the review/qualification run, including `/tmp/mdstats_p7_*` style workspaces;
- import or call `tests.*`, fixture campaign builders, `QualificationHarness`, `PostSelectionHarness`, `AnalyticPairPotential`, bounded trainer/inference seams, or synthetic checkpoint generation;
- copy a checkpoint/publication from a test campaign into a nominal production workspace;
- reconstruct production lineage from an evidence document instead of resolving it from the existing state store.

If no such operator production campaign currently exists or it has not reached a current P5 publication, the correct result is **UNAVAILABLE/BLOCKING**. Do not manufacture one to make P7 pass.

## 3. R13.6-B12J — external DFT origin is asserted but not established

The R13.5 evidence reports a `dft-pbe-ts-reference.v1` bundle and source string, but records no reproducible external first-principles execution provenance or source-artifact identities. The production bundle schema authenticates request/protocol/data integrity; it does not by itself prove that arbitrary finite E/F values were actually produced by DFT.

Therefore a bundle whose JSON merely declares `dft-pbe-ts-reference.v1` cannot, by itself, establish the frozen requirement for **independent external first-principles reference calculations**.

### Required end state

For the exact production reference request generated from the real operator campaign, the final evidence must identify the independent external calculation source strongly enough that an independent reviewer can distinguish real DFT output from hand-authored or candidate-derived values.

At minimum record, for the reference job set or a content-addressed manifest covering every requested geometry:

- external electronic-structure code and version;
- method/protocol identity corresponding to the frozen request (e.g. PBE and all material protocol settings);
- input geometry identity mapped one-to-one to each P7 request geometry;
- hashes/identities of the external input artifacts and raw output artifacts, or an immutable external-job/result manifest containing those hashes;
- parser/importer identity used to extract energy, forces, relaxed positions and stress where applicable;
- units/sign/order/virial-volume provenance already required for stress;
- evidence that the reference values were generated independently of the candidate MLFF and not by `AnalyticPairPotential`, harness inference, copied candidate predictions, or hand-entered numbers.

The resulting `AuthenticatedReferenceBundle` must bind the exact frozen request/protocol and the imported observations. The external raw artifacts need not be committed to Git if large or private, but their stable identities and reproducible provenance must be recorded and available to the qualification review boundary.

If those independent external calculations do not exist, remain `WAITING_FOR_REFERENCE`.

## 4. Accepted R13.5 evidence to preserve

The following are accepted and need not be redesigned:

- exact qualifying interpreter identity now resolves `mdstats` from the intended checkout with version `0.20.242a0`, source digest `7772ad5f...`, commit/tree `97fa48fc...` / `9e4be0fc...`;
- selected KOKKOS/mliappy MACE child execution succeeds on the RTX 3090 with `-k on g 1 -sf kk`;
- component/locked/terminal/release machinery can reach and persist `RELEASE_QUALIFIED` on a bounded assembled campaign;
- fresh-process reauthentication mechanism works;
- affected regression remains `155 passed, 1 skipped` and is reusable because executable source is unchanged.

These results remain integration/runtime evidence. They do not close the real-production or external-reference semantic owners above.

## 5. Binding completion sequence

```text
R13.6-P1  keep 97fa48fc... executable frozen
R13.6-P2  receive/resolve the operator's already-existing production config/workspace; create no campaign state
R13.6-P3  record existing selected/CV/final-production/P5 publication identities before P7 descendant work
R13.6-P4  run production B11 on that exact publication through exporter -> ML-IAP -> selected KOKKOS/MACE -> deployment parity
R13.6-P5  obtain/import independently generated external DFT results for that exact production reference request and record reproducible source-artifact provenance
R13.6-P6  complete nonlocked components + explicit one-shot locked result to RELEASE_QUALIFIED
R13.6-P7  terminate the qualifying process and reauthenticate the final graph in a new process
R13.6-P8  record exact production + external-reference provenance and request independent Design closure review
```

No executable edit is authorized by this amendment. If the genuine production run reveals a source defect, stop, route that defect explicitly, repair under Software Implementation, rerun affected regression, freeze a new candidate, and repeat any real gates affected by the edit.

## 6. Closure gate

P7 may PASS only when all of the following are simultaneously established:

1. the accepted frozen executable is still the code actually running;
2. no P1-P6/P5 campaign/product state was created for final qualification—the input is an independently pre-existing operator production campaign;
3. B11 consumes that campaign's already-existing current P5 publication through the real P7 deployment owner and selected KOKKOS/MACE runtime;
4. the external reference bundle is backed by independently generated, reproducibly identified first-principles artifacts rather than only a self-declared protocol/source string;
5. all mandatory components plus the explicit one-shot locked result succeed on the same candidate/publication;
6. terminal verdict is `RELEASE_QUALIFIED`;
7. a genuinely new process reauthenticates the same complete final graph;
8. exact production and external-reference identities are recorded without contradiction; and
9. independent Software Design review finds no remaining genuine blocker.

Until then P7 remains **REOPENED / NO-PASS** and `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` remains blocked.
