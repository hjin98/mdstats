---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
protocol_version: 5.8.0
revision: 13.6
status: reopened
frozen_executable_commit: 97fa48fc4a8e5be0da8cbcd22ba10248fa37acee
frozen_executable_tree: 9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6
frozen_source_digest: 7772ad5f0329aa1d42f96cf89bbf178252981902e9d4d5468f10ff1312da9ed6
reviewed_evidence_head: 90a19ce67dbf5d6147b0d4cabaab6028adb448e5
review_verdict: NO-PASS
current_amendment: P7_REVISION_13_6_REAL_PRODUCTION_OWNER_AND_DFT_PROVENANCE_CLOSURE_AMENDMENT.md
current_review_evidence: P7_REVISION_13_6_REVIEW_EVIDENCE.md
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
---

# P7 revision 13.6 — authoritative reopened workplan

The frozen parent `MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the controlling scientific/architectural authority.

The executable remains accepted and frozen at commit `97fa48fc4a8e5be0da8cbcd22ba10248fa37acee`, tree `9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6`, source digest `7772ad5f0329aa1d42f96cf89bbf178252981902e9d4d5468f10ff1312da9ed6`. No executable source change is authorized by this revision.

Independent review of evidence head `90a19ce67dbf5d6147b0d4cabaab6028adb448e5` remains **NO-PASS**. R13.5 successfully proves exact interpreter identity, selected KOKKOS/mliappy MACE execution, assembled `RELEASE_QUALIFIED` mechanics, locked closure mechanics, and fresh-process reauthentication. It does not prove that final B11 consumed the operator's pre-existing production campaign, and it does not establish reproducible independent DFT provenance behind the supplied reference values.

## Authority precedence

1. frozen parent scientific workplan;
2. accepted/reclosed P1-P6 authorities;
3. `P7_REVISION_13_6_REAL_PRODUCTION_OWNER_AND_DFT_PROVENANCE_CLOSURE_AMENDMENT.md` — current residual closure authority;
4. R13.5 production-identity/final-reference amendment where not superseded;
5. accepted R13.4/R13.3/R13.2/R13.1/R13/R12/R11/R10/base-P7 contracts where non-conflicting;
6. `P7_REVISION_2_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md` for the storage-neutral successor boundary.

## Accepted surfaces — preserve

Do not redesign or rerun without an affected reason:

- exact qualifying interpreter identity now resolves the intended checkout/version/source;
- generic LAMMPS probes are non-authoritative; exact selected `cuda:N` identity is enforced;
- P5 publication ownership, target-head identity, stress semantics/provenance, resource lineage, exact PBC/cell evidence, release/reference/resource integrity, and one-shot locked semantics remain accepted;
- selected isolated KOKKOS/mliappy MACE worker and abnormal-exit blocking remain accepted;
- the assembled qualification path can reach `RELEASE_QUALIFIED` and a genuinely new interpreter can reauthenticate a final graph;
- affected P7 regression `155 passed, 1 skipped` remains reusable while executable source is unchanged.

## Current blockers

### R13.6-B11G — final B11 still used campaign state created for qualification

The R13.5 evidence records campaign root `/tmp/mdstats_p7_r13_5_production` and says that campaign completed the full production lifecycle during the closure exercise. It again reports `N=4`, `seed-5`, and checkpoint SHA `44297de809ab54e4604524ceb5b463ea21ca1336a2ab1e88fff062aba7d8cabb`, identical to the previously rejected bounded tiny-MACE lineage.

Final B11 must consume an operator-supplied **already-existing** production config/workspace whose selected binding, CV, final production and P5 publication existed before the P7 qualification attempt. R13.6 final qualification may create only P7 descendant evidence; it may not create or regenerate campaign/P1-P6/P5 product state. If no such production publication exists, P7 remains unavailable/blocking.

### R13.6-B12J — independent external DFT origin remains unproven

The R13.5 evidence records a `dft-pbe-ts-reference.v1` bundle hash and source declaration but no external electronic-structure code/version, DFT input/output artifact hashes, immutable job/result manifest, or equivalent reproducible provenance showing that the E/F/reference observations came from independent first-principles calculations.

The reference bundle authenticates request/protocol/data integrity; a self-declared protocol/source string alone does not prove physical origin. Final B12 must record reproducible independent DFT source-artifact provenance mapped one-to-one to the frozen request geometries, including parser/import identity and the already-required stress conversion provenance. Large/private raw artifacts need not be committed, but stable identities and provenance must be available to the review boundary.

## Binding completion sequence

```text
R13.6-P1  keep executable 97fa48fc... frozen
R13.6-P2  resolve operator-supplied pre-existing production config/workspace; create no campaign state
R13.6-P3  record its already-existing selected/CV/final-production/P5 publication identities before P7 descendant work
R13.6-P4  execute B11 on that publication through production deployment parity + selected KOKKOS/MACE
R13.6-P5  fulfil that exact production reference request with independently generated DFT results and reproducible source-artifact provenance
R13.6-P6  complete mandatory components + explicit one-shot locked result to RELEASE_QUALIFIED
R13.6-P7  terminate process and reauthenticate the final graph in a new process
R13.6-P8  record exact production/reference provenance and request independent Design closure
```

No executable edit is permitted unless this genuine production run exposes a source defect. If source changes, rerun affected regression/integration, freeze a new candidate, and repeat each affected real gate.

## Closure gate

P7 may PASS only when the exact frozen executable is running; no P1-P6/P5 product state was manufactured for final qualification; B11 consumes the operator's pre-existing current production publication; the external reference bundle is backed by independently generated and reproducibly identified first-principles artifacts; all mandatory components plus the explicit locked result succeed; terminal verdict is `RELEASE_QUALIFIED`; a new process reauthenticates the same complete graph; and independent Software Design review finds no remaining genuine blocker.

Until then P7 remains **REOPENED / NO-PASS** and `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` remains blocked.
