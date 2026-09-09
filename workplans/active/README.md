# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

There is currently one active MLFF implementation workplan:

- `workplans/active/MLFF_REPLAY_MACE_EXECUTION_MEMBERSHIP_IDENTITY_REPAIR_WORKPLAN.md`

It is governed by **Scientific Software Development Protocol 6.0.0** and coordinates a bounded D4 repair beneath unchanged accepted D3 replay/MACE architecture.

Observed failure: post-selection `cross-validate` with valid single-source replay can fail before TRAIN2 because the strengthened MACE execution-membership adapter requires replay `frame_uid`, while supported single-source replay views are authorized by replay geometry/source/split identity and need not carry target-domain `frame_uid` metadata.

The active plan requires an adapter-level identity-owner correction, not a replay-science redesign: preserve exact target `frame_uid` membership, bind replay execution to the existing replay membership authority, preserve replay source/split/view/method/lineage identity in the already-prepared workspace, preserve exact TRAIN2 continuation authentication, and do not introduce a new replay identity/registry/migration/state machine/wrapper.

Implementation/review coordination is on:

- `fix/mlff-replay-mace-membership-identity`

Planning base and previously accepted executable:

- closeout/planning base: `9abb2b89930b48d9e2771addb5f59879bfec1001`
- executable baseline containing the defect: `13859556cd4d472837a9e171c2be32e59d5e6d82`

The prior downstream-integration closure remains archived and is not reopened wholesale:

- `workplans/archive/MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_WORKPLAN.md`
- `workplans/archive/MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_REVIEW_REOPEN.md`
- `workplans/archive/MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_FINAL_REVIEW.md`

Full long-running real-data/GPU/CuEq/LAMMPS/MLIAP target-machine qualification remains deferred until the final release qualification package.
