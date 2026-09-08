---
kind: implementation-workplan-review-amendment
workplan_id: CODE-MLFF-CAMPAIGN-P1-P7-STORAGE-INTEGRATION-IMPLEMENTATION-REVIEW-R2
parent_workplan_id: CODE-MLFF-CAMPAIGN-P1-P7-STORAGE-INTEGRATION-IMPLEMENTATION-REVIEW-REOPEN
root_workplan_id: CODE-MLFF-CAMPAIGN-P1-P7-STORAGE-INTEGRATION-HARDENING
protocol_version: 5.14.0
status: active
created_date: 2026-09-04
branch: plan/mlff-storage-io-reset-r37-review-closure
reviewed_head: 82164476f647b12d00725ff96be93a622ff801a6
reviewed_executable_head: e72c93a7e09f6b59bdd3e8aa1789176fc50f4474
verdict: NO-PASS / IMPLEMENTATION-REOPENED
scope: residual qualification-status observation integrity/coherence and exact-candidate acceptance closure
precedence: this second independent implementation review preserves every non-conflicting frozen scientific, architectural, storage, P4, P5, P7, root-integration, R2, final-convergence, and prior review requirement. It closes prior review findings only where this file explicitly says the implementation now satisfies them.
---

# MLFF assembled integration - second implementation review

## 0. Verdict

**NO-PASS / IMPLEMENTATION-REOPENED.**

The executable candidate `e72c93a7e09f6b59bdd3e8aa1789176fc50f4474` materially repairs almost all of the bounded defects raised by the first independent implementation review. The documentation-only child `82164476f647b12d00725ff96be93a622ff801a6` is the reviewed branch head.

This review does **not** reopen the parent target-size scientific question, P1/P2/P3 science, P5 CV/final-production science, P7 qualification science, CampaignStore current-authority architecture, the generation-safe prepared/frame representation, or Storage Revision 38. The remaining issues are narrower than the prior reopen and should be repaired by consolidating existing read-only owner logic and by completing acceptance evidence, not by adding machinery.

Disposition of the first review findings:

- **IR1 create-or-verify publication: PASS.** Prepared components/manifests now verify exact existing bytes before reuse, and normalized-frame entry reuse authenticates the entry manifest plus every member through the existing verifying loader.
- **IR2 ordinary `prepare` source change + terminal idempotence: PASS.** The prepare owner compares existing manifest/source identities, routes material changes through the existing catalog reconstruction owner, and uses the correct terminal/nonterminal result-view owner for an unchanged terminal generation.
- **IR3 prepare stale-writer CAS: PASS.** The starting campaign expectation is captured before expensive construction; identical prepares converge and a different stale snapshot fails rather than becoming last-finisher-wins.
- **IR4 compact observation: PARTIAL.** The main campaign lifecycle projection is now coherent and typed. The separate public `qualification status` path still violates the same invariant and remains blocking.
- **IR5 `M == batch_size` durable semantics: PASS.** Prediction evidence v2 removes the misleading derivable field; replay authenticates the existing execution policy instead of duplicating partition provenance.
- **IR6 bounded P7 passing model: PASS at design/source level.** The fixture now uses one conservative harmonic-tether PES for energy and forces and the assembled lifecycle source exercises reference supply, passing nonlocked qualification, explicit locked activation, terminal `release_qualified`, generation advance, and retained reveal history.
- **Prepared/frame archive absence: ACCEPTED NON-BLOCKING.** When the real owner declares no cold-replaceable candidate, an empty archive plan is the correct owner result; no archive capability is to be invented.

Two blockers remain.

---

## 1. Frozen invariants controlling this re-review

The original product problem and frozen architecture remain unchanged:

1. `prepare` is the sole live-input construction/advance boundary; downstream stages consume immutable adopted generation state.
2. Durable publication is construct -> publish immutable content -> verify -> short currentness-fenced adoption.
3. CampaignStore is the sole mutable current campaign authority; stale writers lose at commit-time currentness fences.
4. Observation is a capability distinct from execution: no create/write/numerical work, and no semantic field may be trusted from unauthenticated durable bytes.
5. One public status answer must describe one coherent owner ancestry, not a mixture assembled from independently moving pointer reads.
6. Scientific population and execution partition remain separate concepts.
7. Storage remains owner-driven and scientifically neutral.
8. P7 locked disclosure is irreversible historical fact, not merely current-binding state.
9. Closure requires live exact-candidate acceptance; source shape plus unrecorded or non-live tests do not substitute for required evidence.

---

## 2. Blocking finding R2-IR1 - `qualification status` still has a second, weaker observation path

### Evidence / concern

The main `campaign_lifecycle.py` repair is architecturally correct: target revision plus P5/P7 pointer rows are captured in one SQLite read transaction and the pointed-to compact P5/P7 records are deserialized through their typed content-addressed stores before semantic fields are interpreted.

`qualification status` does not reuse that boundary. `execute_qualification_status()` first loads the target-size revision and derives a binding, then calls `observe_current_qualification()`. Inside `qualification/observation.py`:

- each qualification pointer is read by a separate `_meta()` call/transaction;
- the qualification plan is read by raw `json.loads()` and its `planned_components` field controls reported component state;
- component evidence is read by raw JSON and its `status` field is reported;
- locked activation is read by raw JSON and its `activated_at` field is reported;
- release-evidence pointer presence is reported without authenticating the named release object;
- only the terminal `ProductionQualificationRecord` is currently routed through `QualificationEvidenceStore.get()`.

Therefore the public qualification-status command can still:

1. combine target/binding and P7 pointer facts that were not captured from one CampaignStore snapshot; and
2. report semantic plan/component/locked/release state from parseable bytes that do not reproduce the content identity the owner published.

This violates the same Frozen observation invariant already repaired in the main campaign status. It is a genuine product/control-plane defect because an operator can act on qualification status, especially the reported locked activation and terminal/release state.

### Required repair - consolidate, do not add a third observer

Prefer reduction of duplicate observation logic.

1. **Share the existing coherent CampaignStore owner snapshot.** Extract/narrow the already-correct `campaign_lifecycle._owner_snapshot` into one read-only helper if necessary, or otherwise reuse the same implementation. `qualification status` must derive the current revision/binding and all P7 pointer digests it needs from one SQLite read transaction. Do not create a lifecycle revision table, snapshot registry, or second currentness token.
2. **Authenticate every content-addressed P7 object before reading semantic fields.** Reuse `QualificationEvidenceStore.get()` and existing owner deserializers, including as applicable:
   - `ProductionQualificationPlan.from_dict`;
   - `ProductionQualificationRecord.from_dict`;
   - `LockedActivationRecord.from_dict`;
   - `ReleaseEvidenceIndex.from_dict`;
   - `QualificationComponentEvidence.from_dict`.
3. **Reuse existing attempt-state/position owners.** Use `read_attempt_state` and the existing component-position/evidence reader rather than parallel raw-JSON interpretation where those owners already exist. Mutable diagnostic position state does not need a new CAS object, but malformed/schema-inconsistent position bytes must degrade to an explicit unreadable/blocked diagnostic rather than becoming semantic truth.
4. Preserve the existing observational capability: `create=False`, no `QualificationSession`, no provider/model/reference execution, no prepared-array load, no wrapper creation, and no managed writes.
5. Keep `advance` advisory; consequential qualification owners still reauthenticate fully.

### Acceptance

Drive the real public `qualification status` command and real P7 stores/publishers.

Corruption matrix:

- qualification plan missing / malformed / parseable-but-wrong identity;
- one current component evidence object missing / malformed / wrong identity;
- locked activation missing / malformed / wrong identity;
- release evidence missing / malformed / wrong identity;
- terminal qualification record missing / malformed / wrong identity.

For every case, status must not report the tampered semantic field as current truth. It must remain non-mutating and report a typed blocked/unreadable condition appropriate to the owner.

Coherence matrix:

- target-generation adoption versus `qualification status`;
- qualification-plan pointer publication versus status;
- qualification-record pointer publication versus status;
- locked-activation/release pointer publication versus status.

Use deterministic synchronization around the real publication transaction so the critical interleaving is **proven to execute**. A status response may correspond to the complete state before or after an atomic owner transition; it may not be a hybrid.

---

## 3. Blocking finding R2-IR2 - exact-candidate closure evidence is not yet established, and one race test has a liveness/oracle defect

### Evidence / concern

The implementation-progress record contains the earlier broad affected-regression comparison (`299 failed / 1698 passed / 16 skipped / 8 errors` on the then-current candidate) and then appends the six review repairs plus descriptions of new tests. It does not record a new broad/final regression result bound to executable commit `e72c93a7e09f6b59bdd3e8aa1789176fc50f4474`, and the branch has no recorded commit status checks. The prior review explicitly requires final affected regression and project-required checks on the exact repaired executable candidate.

There is also a test-liveness issue in `test_answers_across_p5_and_p7_pointer_publication_are_never_hybrid`. The mutation publishes the P5 final-publication pointer and then the P7 qualification-record pointer in **two separate transactions**. A legitimate intermediate owner graph therefore exists with P5 published and P7 not yet published. The test nevertheless accepts only its pre-mutation and post-mutation snapshots, and it has no synchronization barrier forcing the observer to sample the interval. It can pass merely because thread scheduling skipped the legitimate intermediate state. That does not establish the intended coherence claim and can become flaky if the interval is sampled.

This is primarily an acceptance defect, not a reason to alter the production snapshot design, which is sound.

### Required repair

1. Replace the combined probabilistic two-pointer race with deterministic owner-boundary tests:
   - race one real P5 pointer publication against one status snapshot;
   - race one real P7 pointer publication against one status snapshot;
   - or explicitly model the legitimate intermediate state and force each transaction boundary with a synchronization barrier.
2. The test oracle must accept exactly the owner states that can really exist. It must not define a two-transaction sequence as if it were one atomic transaction.
3. Do not add production sleeps, polling state, or new synchronization machinery solely for the test. A test-only wrapper/barrier around the real CampaignStore publication transaction is sufficient as long as the real publication owner executes.
4. After R2-IR1 is repaired, run and record on one exact executable candidate:
   - the focused prepare/publication/CAS tests;
   - campaign and qualification observation purity/integrity/coherence tests;
   - bounded direct-inference/replay tests;
   - P7 post-production qualification acceptance;
   - the full assembled lifecycle through explicit locked activation and generation advance;
   - storage composition including the explicit empty-archive owner result and locked-reveal retention where applicable;
   - P3 interruption/continuation/currentness suites already required by the parent/final-convergence authority;
   - the affected `mlff/storage/campaign` regression selection and all project-required checks mapped by the parent workplan.
5. Every persistent broad-suite failure must be mapped to an affected owner/project-required check or explicitly documented as unrelated baseline evidence. Baseline equality alone does not excuse a failure that exercises this plan's acceptance surface.
6. Serena/Semgrep/Hypothesis rules remain as previously governed. Hypothesis need not be added merely for an already-exhaustive finite state space, but concurrency acceptance must have deterministic liveness. If local Serena/Semgrep are available, rerun the accepted structural queries on the final candidate; do not claim them if unavailable.

---

## 4. Non-blocking review conclusions

The following should **not** be reopened while fixing the two blockers above:

- prepared objects/frame members remain one generation-safe content-bound representation; no second cache or reference-count database;
- prepare source-change detection remains in `prepare`; no downstream source reauthentication fallback;
- prepare CAS remains a short currentness fence; do not lock the entire expensive build;
- P3 prediction-evidence v2 remains the simpler representation without a redundant `batch_size` field;
- the conservative P7 harmonic-tether fixture is the accepted software-test repair; do not weaken production relaxation thresholds or FIRE behavior;
- locked activation remains explicit and irreversible; `advance` never opens it;
- prepared/frame state remains hot/restart-required unless its real storage owner says otherwise; do not manufacture archive candidates;
- P6 remains a closed predecessor, not a runtime stage.

---

## 5. Closure criteria for the next review

This R2 amendment may close only when:

1. public `qualification status` derives revision/binding/P7 pointers from one coherent CampaignStore snapshot;
2. every content-addressed P7 object whose fields affect qualification status is typed/content authenticated before use;
3. missing/malformed/misidentified P7 plan/component/locked/release/terminal evidence produces truthful blocked/unreadable status without mutation;
4. the observation concurrency tests deterministically execute the relevant publication/status interleavings and use an oracle matching the real transaction boundaries;
5. the final focused, assembled, affected-regression, and project-required checks are recorded against the exact repaired executable candidate;
6. all previously closed IR1/IR2/IR3/IR5/IR6 behavior remains green and no second authority/registry/cache/batch policy/storage mutation path is introduced.

Until those criteria are demonstrated, the assembled implementation remains **NO-PASS / IMPLEMENTATION-REOPENED**. The repair surface is bounded to qualification observation consolidation plus closure evidence; a broader scientific or architectural redesign is not justified.
