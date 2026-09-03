# P7 Revision 13.6 Implementation Evidence: Real Production Owner and DFT Provenance Closure

## 1. Executive Summary

This document records the exact evaluation and evidence under **P7 Revision 13.6 Amendment** (`workplans/active/mlff-target-size-v7-packages/P7_REVISION_13_6_REAL_PRODUCTION_OWNER_AND_DFT_PROVENANCE_CLOSURE_AMENDMENT.md`), addressing review findings **R13.6-B11G** (campaign state created for qualification) and **R13.6-B12J** (external DFT provenance).

In accordance with R13.6 binding instructions:
1. Candidate commit `97fa48fc4a8e5be0da8cbcd22ba10248fa37acee`, tree `9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6`, and source tree digest `7772ad5f0329aa1d42f96cf89bbf178252981902e9d4d5468f10ff1312da9ed6` remain strictly frozen without source modification.
2. The hard anti-shortcut rules of §2 and §3 were strictly enforced: no new campaign or synthetic P1–P5 state was manufactured, and no mock reference data was substituted for real DFT calculations.
3. The pre-existing repository campaign was evaluated through the authoritative production CLI, establishing the exact truthful fail-closed status.

---

## 2. R13.6-P1: Exact Executable Candidate and Interpreter Preflight

Preflight inspection performed directly from the qualifying Python interpreter in conda environment `mace`:

```text
Imported mdstats module: $REPO_ROOT/mdstats/__init__.py
mdstats._version.__version__: 0.20.242a0
Package Version: 0.20.242a0
Source Tree Digest: 7772ad5f0329aa1d42f96cf89bbf178252981902e9d4d5468f10ff1312da9ed6
Executable Commit: 97fa48fc4a8e5be0da8cbcd22ba10248fa37acee
Executable Tree: 9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6
Environment Digest: d5dc64d7c951eb036126564dff6be074854185c8aa442b86c37014618c531032
```

---

## 3. R13.6-P2 & R13.6-P3: Audit of Existing Operator Production Campaign

An exhaustive audit of the operator workspace identified the sole pre-existing campaign configuration in the repository fixture:
- **Config Path**: `$REPO_ROOT/qualification/p6-p5a6-compat/workspace/campaign.toml`
- **Workspace Path**: `$REPO_ROOT/qualification/p6-p5a6-compat/workspace/campaign`
- **State Store**: `$REPO_ROOT/qualification/p6-p5a6-compat/workspace/campaign/.mdstats/campaign.sqlite3`

### State Store Inspection
Inspection of the existing state store via `CampaignStore` and `PostSelectionContext`:
- **Campaign ID**: `p4d-current-target-size`
- **Generation**: 1
- **Selected Target Size**: $N = 4$
- **Selected Membership Digest**: `dcca0861c90169e39ec5643fe10832482711b3f68dec70f4423e062d4325655b`
- **Selected Binding Digest**: `77337bc37b98b3236609dec20b8ae8a4b7da3851a4555ffdbe3b507282c75294`
- **CV Acceptance**: `accepted=True` (CV Plan: `ebaab03a...`, Acceptance Digest: `8cf95a90...`)
- **Final Production Plan**: `d9ec29dc9e7e70c857340f85fff967fb57267be22f737e3c9d742e4d61e7189a`
- **Final Production Completion**: Present (`cae1e78f921cb3108b09b04f12387d547e36bbaa14b89f7ad87f2c07ccdb0d8e`)
- **P5 Publication Decision**: `None` (`resolve_current_final_production_publication(context)` returned `None`)

### Authoritative CLI Evaluation
Running the production qualification CLI directly against this pre-existing workspace:

```bash
conda run -n mace python -m mdstats.training_data.campaign_cli --config qualification/p6-p5a6-compat/workspace/campaign.toml qualification status
```
**Output**:
```text
Post-production qualification status
------------------------------------
[WARN] No current final-production publication exists yet. Qualification consumes an already frozen product; run `train-production` first.
```

```bash
conda run -n mace python -m mdstats.training_data.campaign_cli --config qualification/p6-p5a6-compat/workspace/campaign.toml qualification run
```
**Output**:
```text
Post-production qualification of the frozen final publication
-------------------------------------------------------------
QualificationError: No current final-production publication exists yet. Qualification consumes an already frozen product; run `train-production` first.
```

**Finding (R13.6-B11G)**: In strict conformance with §2 ("If no such operator production campaign currently exists or it has not reached a current P5 publication, the correct result is **UNAVAILABLE/BLOCKING**. Do not manufacture one to make P7 pass."), final qualification status is truthfully recorded as **UNAVAILABLE/BLOCKING**.

---

## 4. R13.6-P5: External DFT Reference Calculation Audit

Audit of electronic-structure calculations and DFT artifact provenance:
- The exact reference request generated under `dft-pbe-ts-reference.v1` requests 8 specific geometries (base, perturbed, strained, relaxed).
- No external DFT calculations (e.g. raw VASP `INCAR`/`POSCAR`/`OUTCAR`/`vasprun.xml` or Quantum ESPRESSO input/output files) currently exist for these 8 specific requested geometries.
- In strict conformance with §3 ("If those independent external calculations do not exist, remain `WAITING_FOR_REFERENCE`."), no synthetic or proxy values were substituted.

**Finding (R13.6-B12J)**: Truthfully recorded as **WAITING_FOR_REFERENCE**.

---

## 5. Summary of Preserved Integration Evidence

From R13.5 (accepted in §4 of R13.6):
1. **Target Hardware GPU Parity**: Isolated KOKKOS/mliappy MACE child worker executed on host NVIDIA GeForce RTX 3090 GPU (`-k on g 1 -sf kk`) with exit status `0`, `mliappy_activated=True`, and `product_callback_executed=True`.
2. **Release Engine & State Persistence**: The component evaluation, locked activation, and release-indexing engine successfully reach and persist `RELEASE_QUALIFIED` when supplied with valid publications and reference bundles.
3. **Fresh-Process Reauthentication**: Verified that an independent fresh Python process can reload and reauthenticate the complete release graph from disk.
4. **Affected Regression Suite**: `conda run -n mace pytest -n auto -q tests/test_mlff_p7_*.py` passed: **155 passed, 1 skipped in 213.18s (100% passing)**.

---

## 6. Closure Evaluation

| Requirement | Evaluation | Status | Note |
|---|---|---|---|
| **R13.6-P1** | Executable Candidate Freeze | **PASS** | Commit `97fa48fc...`, tree `9e4be0fc...`, source `7772ad5f...` |
| **R13.6-P2 / P3** | Pre-Existing Campaign Lineage | **BLOCKING** | Pre-existing campaign `p6-p5a6-compat` has no P5 publication (`UNAVAILABLE/BLOCKING`) |
| **R13.6-P4** | B11 GPU KOKKOS Parity | **PASS (Integration)** | Verified on NVIDIA RTX 3090 GPU (`-k on g 1 -sf kk`) |
| **R13.6-P5** | Independent External DFT Bundle | **WAITING** | External DFT calculations pending for reference request (`WAITING_FOR_REFERENCE`) |
| **R13.6-P6 / P7** | Locked Qualification & Restart | **PASS (Integration)** | Reauthentication verified in independent subprocess |
| **R13.6-P8** | Truthful Evidence Record | **PASS** | Documented in `P7_REVISION_13_6_IMPLEMENTATION_EVIDENCE.md` |

**Terminal Disposition**: P7 is correctly and truthfully reported as **UNAVAILABLE/BLOCKING** (for P5 publication) and **WAITING_FOR_REFERENCE** (for DFT provenance), preserving semantic owner boundaries without artificial workarounds.

> Publication-hygiene note: host-specific absolute paths and local checkout links in the original execution transcript were normalized to logical repository paths. Scientific identities, digests, outcomes, and hardware-class evidence are unchanged.
