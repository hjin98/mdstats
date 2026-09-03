---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 12
status: reopened
amended_date: 2026-09-01
current_authority_pointer: true
reviewed_candidate_head: 86ca3aab960c11a97e0c659f13d342c858c41ae8
reviewed_candidate_tree: 195db51777ece1d61141d6f404a776eba92d2bae
reviewed_executable_commit: 53edc1c75c5b7c9df8f414914534ce915c34f303
reviewed_executable_tree: 8d24e6326b67c38e69a1fe1383be7b975788cac5
review_verdict: NO-PASS
authoritative_rework_amendment: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md
precedence: this authority supersedes earlier mlff-storage-io-reset authority pointers; the current contract is STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md + STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md + AUTHORITY_REVISION_11.md archive-boundary corrections + STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md + this authority pointer; the frozen parent target-size V7 workplan remains the scientific and architectural verdict
---

# Storage/I-O reset package authority — revision 12 implementation review reopen

## Verdict

Independent Software Design review of the implemented storage reset is **NO-PASS**. The workplan is reopened for bounded implementation repair.

The reviewed executable candidate is:

```text
commit 53edc1c75c5b7c9df8f414914534ce915c34f303
tree   8d24e6326b67c38e69a1fe1383be7b975788cac5
```

The reviewed branch head is:

```text
commit 86ca3aab960c11a97e0c659f13d342c858c41ae8
tree   195db51777ece1d61141d6f404a776eba92d2bae
```

The head-only delta is documentation/PDF regeneration and does not close the executable findings.

## Current implementation contract

Implementation must read these supplied artifacts together:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md`;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md`;
3. `AUTHORITY_REVISION_11.md` for the final archive locator and crash-durability constraints;
4. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md` for the exact implementation-review blockers and repair contract;
5. this revision-12 authority pointer.

Earlier authority revisions remain provenance only.

## Blocking surfaces

The global owner-driven architecture is retained. Rework is limited to the following genuine blockers:

- archive create/reclaim/restore do not yet carry the exact owner-bound plan + fresh semantic revalidation strength required of consequential mutation;
- `archive create --root` can widen one eligible child root into an ineligible parent subtree;
- dedup apply uses an old inventory snapshot rather than a freshly revalidated exact owner-bound plan;
- positive frame-cache eviction lacks a real active-consumer/builder liveness seam;
- superseded P5 `runs/` are classified immutable/archive/dedup eligible without proving that a stale long-running P5 writer has stopped;
- storage-native dedup CAS and incomplete archive representations lack a complete explicit lifecycle, permitting retained orphan bytes;
- archive representation identity permits an attempted re-encoding to overwrite a previously retained blob/manifest identity before new terminality, so interruption can invalidate an existing archive;
- plan owner binding omits exact same-generation P3/P4/P5/P7 currentness identities required to stale an unapplied plan;
- normal `storage report` still recursively scans owner subtrees, defeating the required fast-report versus deep-audit separation;
- CampaignStore `VACUUM` runs after every applied cleanup rather than only under measurable benefit;
- executable functional/regression/integration evidence is not established for the reviewed candidate: the implementation commit has a successful docs check, not a storage/P1-P7 regression check.

The precise corrected end states, permitted implementation choices, real-owner acceptance boundaries, and tests are in `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md` and are binding.

## Preserved accepted implementation

This No-Pass does **not** invalidate the parts that already conform. Preserve, unless a repair requires a local compatible refactor:

- transitive cross-owner dependency closure;
- post-terminal P7 -> P5 checkpoint retention and waiting lineage;
- existing P5/P7 publication barriers;
- cleanup's plan/resnapshot/revalidation/executor path;
- physical ownership/external-input/symlink/P3/P7 retention fences;
- canonical storage policy identity;
- bounded archive verification/restoration and archive-locator containment;
- durable publication ordering helpers;
- hardlink metadata checks/atomic replacement;
- storage archive catalog/journal/audit ownership.

Accepted P3/P4 stale-generation semantics are preserved; they are not redesigned by the P5 liveness finding.

## Rework entry and closure

Resume at `R12-S0` in the implementation-review amendment, then proceed through `R12-S1` to `R12-S4`. Stage-local semantic/conformance and affected-regression closure is required before dependent stages.

Final closure requires a fresh assembled candidate with:

- every IR12 blocker reconciled against source;
- actual focused + affected regression + real-owner integration execution evidence;
- final affected-surface re-derivation;
- repository-required checks;
- independent Software Design re-review.

A test file existing in source is not evidence that the test executed.

Full external-DFT scientific qualification, long GPU production qualification, and environment-specific HPC/storage qualification remain deferred under the frozen parent/P7 authority and are not reintroduced as rework gates.

## Authority boundary

No target-size, CV, final-production, publication, qualification, calibration, locked-test, or release-science decision is reopened. The frozen parent V7 workplan remains the verdict. This revision reopens only storage implementation fidelity and functional acceptance.