---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 9
status: active
amended_date: 2026-09-01
current_authority_pointer: true
authoritative_workplan: STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md
implementation_intake_commit: 45b85e5dfb98bed4abbfee47cdb020bb2bd401c8
implementation_intake_tree: 3efc6297c31c1d233a733ec792f0fba08aea10a1
entry_condition: satisfied by P6 revision 13 independent PASS and P7 revision 13.7 software/functional closure PASS
precedence: this authority and the revision-2 substantive workplan supersede all earlier mlff-storage-io-reset authority revisions and STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md for current task-local semantics; the frozen parent target-size V7 workplan remains the scientific and architectural verdict
---

# Storage/I-O reset package authority — revision 9

The current implementation handoff is:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md`

The package is now **active / implementation-ready**. Its predecessor gate is closed:

```text
CODE-MLFF-TARGET-SIZE-V7-P6 revision 13 -> independent PASS
CODE-MLFF-TARGET-SIZE-V7-P7 revision 13.7 -> software implementation + functional acceptance PASS
```

P7 revision 13.7 explicitly defers actual real-campaign external-DFT scientific qualification and long target-machine production/resource qualification. Those deferred activities are not storage-entry prerequisites and must not be reintroduced as acceptance gates by this package.

Implementation intake is bound to merged `main` commit `45b85e5dfb98bed4abbfee47cdb020bb2bd401c8`, tree `3efc6297c31c1d233a733ec792f0fba08aea10a1`. The accepted P7 executable source remains `97fa48fc4a8e5be0da8cbcd22ba10248fa37acee`, tree `9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6`; subsequent merged changes through the intake head are P7 workplan/evidence authority changes, not executable-product edits.

Revision 9 is a substantive P1-P7 realignment, not another gate-only amendment. The revised handoff incorporates the implemented current owner model, including:

- P2 as an explicit persisted statistical-authority surface;
- P3/P4 authenticated head adoption and publish-before-adopt retention fence;
- conservative P5 currentness/restart ownership without invented positive cache deletion authority;
- P7's canonical `.mdstats/qualification/g<generation>` evidence/attempt owner and qualification retention fence;
- the existing composite campaign deletion boundary that combines lifecycle fences with external-input, containment, and symlink safety;
- separate reusable-cache semantics for SHA/validation receipts rather than treating the receipt store as scientific provenance;
- preservation of P7 `waiting_for_reference` request/publication/resume lineage through cleanup/archive/restore;
- replacement of retired STOR candidate-selection/protocol-freeze gates with owner inventory -> immutable plan -> revalidation -> execution.

No target-size, CV, publication, qualification, calibration, locked-test, or release-science decision is reopened. The frozen parent workplan remains the verdict.