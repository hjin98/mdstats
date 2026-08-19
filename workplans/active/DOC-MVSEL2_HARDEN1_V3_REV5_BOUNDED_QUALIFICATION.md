---
kind: implementation-workplan
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 5
status: READY_FOR_QUALIFICATION
protocol_version: 3.0.0
supersedes: workplans/active/DOC-MVSEL2_HARDEN1_V3_REV4_MATERIALITY.md
qualification_driver: scripts/mvsel2_bounded_qualification.py
---

# MVSEL2 hardening — resource-bounded standalone qualification

## Decision

The REV4 workstation qualification procedure is retired. It is not acceptable to clone the complete production `.mdstats` tree for Q5/Q6/Q7. On the LTA production graph this expanded shared/file-backed sparse state into roughly 130 GB of qualification scratch, created severe RAM/page-cache pressure, and tied multi-hour qualification to an interactive Codex session.

This revision changes qualification execution only. The frozen MVSEL2/REPAIR2 scientific semantics and product candidate remain unchanged unless the new bounded checks expose a substantive defect.

## Operating requirements

Every production-scale workstation check MUST satisfy all of the following:

1. Codex/ChatGPT availability is not required after the command is launched.
2. Production campaign inputs are read-only authority.
3. The complete production `.mdstats` tree is never copied, hard-linked, reflinked, or mirrored into qualification scratch.
4. Immutable production MVIDX/reference arrays are consumed in place through authenticated read-only/native readers.
5. Mutable qualification state is isolated below one qualification root.
6. A parent watchdog enforces explicit worker RSS, physical scratch-byte, stage wall-time, and total wall-time ceilings.
7. A sustained ceiling violation terminates the worker and records a fail-closed resource-limit result.
8. Qualification state is restartable; already-passed stages may be reused only when production input identity is unchanged.
9. Production database/config hashes are checked across material stages; qualification must not mutate them.
10. Expensive historical work is reused when it is already bound to the exact same production graph and is conservative for the claimed acceptance threshold.

## Default workstation envelope

The standalone driver defaults are:

- worker RSS ceiling: 48 GiB;
- qualification scratch ceiling: 8 GiB physical blocks;
- Q5 wall limit: 90 minutes;
- Q6 wall limit: 90 minutes;
- total qualification wall limit: 3 hours;
- native BLAS/OpenMP thread defaults: one thread in supervised workers.

These are execution defaults and may be lowered. Raising them should require a deliberate operator choice. A stage that cannot execute within a reasonable bounded envelope is a scaling/design finding; the default response is not to consume all available workstation resources.

## Q5 — recovery without production-tree cloning

Q5 MUST NOT regenerate a fresh full selector authority merely to establish an oracle.

Procedure:

1. authenticate the existing production `target_multi_view_selection_v2` authority;
2. open target reference and MVIDX through native read-only readers;
3. enumerate production MVSTATE2 checkpoint pointers;
4. copy only the MVSTATE2 checkpoint bundles required for recovery testing into bounded scratch;
5. independently validate the newest checkpoint and highest older compatible checkpoint;
6. corrupt only the scratch record for the newest checkpoint;
7. require runtime fallback selection to choose the prevalidated highest older compatible checkpoint;
8. resume selector execution from that checkpoint;
9. require the resumed final selection digest to equal the authenticated production selection digest exactly.

This proves the material recovery contract while avoiding both a full `.mdstats` copy and a redundant uninterrupted rank-zero production selection.

## Q6 — REPAIR2 scale directly against read-only production state

Use `benchmarks/benchmark_mlff_mvsel2_harden1_v3_repair2_production.py` directly against the production campaign database.

The benchmark already consumes authenticated selection/MVSTATE2 records and opens MVIDX through the native forward-only reader without updating the campaign database. It must remain externally supervised by the bounded driver.

PASS continues to require the fixed-eight ladder through 16,384, zero rejected-proposal full-state copies, no inverse mutation, and the required production identity.

## Q7 — conservative performance evidence reuse

Do not launch a fresh full MVSEL1 production replay merely to reproduce an already-large performance margin when doing so can take hours to days and requires the bidirectional multi-billion-edge runtime.

The existing production-density benchmark may be reused only when:

- its MVIDX1 content digest equals the current production MVIDX1 content digest;
- candidate count and family count match the production graph;
- its projection method remains conservative;
- the recorded projected speedup remains at least 10x.

Current accepted evidence records a conservative full-order projection of approximately 69x for the same 36,408-candidate / 165-family production graph. If graph identity changes or the evidence no longer clears the 10x threshold, Q7 becomes BLOCKED/RETURN_TO_IMPLEMENTATION for a newly designed bounded comparator; it must not silently fall back to an unbounded V1 replay.

## Standalone driver

Authority for workstation execution:

`scripts/mvsel2_bounded_qualification.py`

The driver:

- records production DB/config SHA-256 identity;
- preflights free disk headroom;
- supervises expensive child processes;
- monitors worker RSS and physical qualification scratch usage;
- terminates runaway stages on resource/time ceilings;
- persists `state.json` after every stage;
- supports restart by skipping PASS stages when production identity is unchanged;
- removes transient Q5 checkpoint scratch after PASS;
- writes compact Q5/Q6/Q7 JSON evidence plus a final `summary.json`;
- requires no agent session after launch.

## Acceptance

The bounded qualification passes when:

- Q5 exact recovery/fallback/digest equivalence passes;
- Q6 production REPAIR2 scale/resource assertions pass;
- Q7 same-production conservative evidence remains bound and >=10x;
- no configured resource/time ceiling is exceeded;
- production input identity is unchanged;
- the final qualification root remains within the configured scratch ceiling.

A resource-limit termination is evidence, not an invitation to automatically increase limits. Investigate algorithm/storage behavior first.

## Superseded behavior

The following REV4 behaviors are explicitly forbidden for future qualification:

- `shutil.copytree()` of the complete production `.mdstats` tree;
- one full production snapshot per Q5/Q6 check;
- two to six full production snapshots for paired Q7 measurements;
- regenerating the complete uninterrupted production selector solely to create a Q5 oracle when an authenticated canonical authority already exists;
- requiring Codex to remain active while a production qualification job runs.

## Future storage-design item

MVIDX1 still persists both witness-to-candidate and candidate-to-witness relations. MVSEL2/REPAIR2 use only the forward candidate-to-witness relation. A separate MVIDX2 design pass should evaluate making forward incidence primary and making inverse storage optional/on-demand for legacy consumers. This is not required to execute REV5 qualification, but the current multi-billion-edge persistent footprint warrants that redesign.
