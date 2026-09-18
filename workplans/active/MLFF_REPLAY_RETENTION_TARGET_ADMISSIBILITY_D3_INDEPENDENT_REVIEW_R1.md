---
kind: independent-d3-review
protocol_version: 6.4.0
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
branch: design/mlff-replay-retention-target-admissibility-rework
review_date: 2026-09-18
review_target: 119c4067b1852be127134d6b0fb1aae6cace4bd6
review_target_tree: 6ebb6c13b0dd58b07cd04cec4ff3cbeb2dece594
parent_d1_target: d761171f3c86c3c79b87a90cfc02ac324c261b1a
parent_d1_blob: 612294ec4680db01a18085e13fbfe5dcfa9fb7ed
parent_d2_target: 32508991d472c1c6e4bd8b818b38d0880401845f
parent_d2_blob: 30e6e6336cf41a05879650a3a2d7d583c4ef713a
disposition: NO_PASS
serious_challenge: PROPOSED_D3_ONLY
---

# MLFF replay-retention / target-admissibility D3 independent Review R1

## 1. Review disposition

**NO-PASS.**

**SERIOUS CHALLENGE to the proposed D3 candidate only.** The ratified D1/D2 parents are coherent on the reviewed surface. The blocker is that the proposed D3/D4 concretization is internally contradictory and, on one storage surface, weaker than accepted-current D3.

The reviewed target is immutable commit `119c4067b1852be127134d6b0fb1aae6cace4bd6`. This record is a descendant review artifact and does not mutate that candidate.

## 2. Governing parents reconstructed independently

The review reconstructed the following ratified requirements directly from D2 rather than inheriting the design author's conclusions:

- fixed-budget TRAIN2 is independent of checkpoint warning/hard thresholds, role target thresholds, and D2.DEF.059A/059B ordering policy;
- exact continuation/reuse must authenticate every trajectory-generating coordinate and the exact fitted/prepared training state while excluding assessment-only policy from training identity;
- future numerical measurement identity must be independent of assessment thresholds/full role-plan ancestry;
- D2.DEF.059A freezes each run representative before D2.DEF.059B performs any cross-seed publication ordering;
- D2.AX.004 moves only the corresponding representative/publication descendants for 059A/059B policy changes;
- current CV authorization is required before current final assessment/publication;
- historical evidence is never rewritten into a new current verdict.

Accepted-current D3 side constraints were also reconstructed from the pre-candidate architecture and actual P5/storage owners: one acyclic plan/preparation/materialization direction, one existing CampaignStore evidence/pointer plane, owner-local P5 run-activity exclusion, and the retained typed topology + compact completion anchor with race-safe no-follow authentication and cold-storage-safe idempotent reuse.

## 3. Blocking findings

### R1-D3-1 — `TrainingTrajectoryIdentity` is cyclic with fitted preparation

**Earliest owner:** proposed D3.

The candidate states in `docs/arch_manuals/mlff_training_data/40_training_evaluation.md` that `TrainingTrajectoryIdentity` binds the “fitted/prepared training state” while the same architecture graph makes `PostSelectionFittedPreparation` a descendant of `TrainingTrajectoryIdentity`. The proposed D4 contract then makes the cycle explicit: the role training position exists first and the fitted preparation binds `TrainingTrajectoryIdentity`.

That is not a harmless wording issue. Current executable ownership is acyclic: `PostSelectionFittedPreparation` presently binds its authorizing plan, and `PostSelectionMaterialization` binds the preparation digest. A content identity cannot both require the fitted-preparation result and be the parent that authorizes/identifies that fitted preparation.

The repository has already encountered and repaired this exact architecture failure family: the archived P5 restoration review rejected a plan/preparation back-edge with the explicit conclusion that a plan cannot both own and descend from its fitted preparation. That history is supporting evidence, not authority; the current candidate independently reproduces the same contradiction.

**Required repair:** derive `TrainingTrajectoryIdentity` only from already-available training-bearing inputs/policies/memberships and deterministic preparation inputs. Make fitted preparation a descendant that binds that identity. Continuation must separately authenticate the exact fitted-preparation/result digest needed by D2.DEF.060. Do not add a placeholder, reverse edge, wrapper, or second identity graph.

### R1-D3-2 — legacy-root immutability is contradictory

**Earliest owner:** proposed D3/D4 persistence contract.

The implementation workplan says historical roots are read-only, yet both the same workplan and D4 section 17 require a terminal legacy root lacking the old assessment-coupled completion proof to be “sealed” under the new training-completion rule. The accepted completion proof is stored in the run root as a topology manifest plus completion anchor, so that instruction necessarily adds files to the root.

The candidate therefore gives the implementer two incompatible obligations.

**Required repair:** freeze one explicit migration rule. Preferred minimal concretization: already sealed historical roots remain strictly read-only; a terminal-but-unsealed legacy root may receive exactly one append-only topology/anchor proof under the existing P5 run-activity owner after exact authentication, while every pre-existing checkpoint/config/runtime/summary byte remains immutable. If D3 instead chooses an external proof, it must reuse an accepted owner and must not create a second completion/currentness plane.

### R1-D3-3 — per-seed final assessment is over-bound to cross-seed publication policy

**Earliest owner:** proposed D3/D4 currentness graph.

D4 section 13 makes the final-production plan bind both D2.DEF.059A and the publication mode / D2.DEF.059B identity. The D3 assessment locator is keyed by the current final assessment-plan digest. Therefore a change confined to D2.DEF.059B or publication mode moves each seed's assessment position even though D2.DEF.059B is defined only after every required seed has already frozen its representative under D2.DEF.059A.

This violates the candidate's own narrow-currentness objective and D2.AX.004's “corresponding representative/publication descendants” separation.

**Required repair:** retain one final plan object if convenient, but expose a canonical per-seed assessment projection containing final hard-decision policy + D2.DEF.059A + seed position and excluding publication mode/059B. Key the final-seed assessment locator by that projection. Bind publication mode/059B only at the aggregate publication decision that consumes frozen seed representatives.

### R1-D3-4 — accepted P5 completion/storage safety semantics were weakened

**Earliest owner:** proposed D3 storage architecture.

The candidate rewrote the P5 completion paragraph in `60_execution_performance.md` and removed material accepted constraints:

- authority-record open with `O_NOFOLLOW` plus regular-file verification by `fstat` on the opened descriptor, avoiding a separate `lstat`/rename race;
- topology manifest and completion anchor are owner infrastructure and never reclaimable members;
- completion remains certified by the anchor even when terminal assessment evidence has already been moved cold;
- republication verifies/reuses the existing proof rather than deriving a new proof from a tree storage may already have depleted;
- tampered, copied, or self-inconsistent completion proof is non-certifiable.

The replacement phrase “no-follow regular-file verification” is too weak: a D4 implementation could satisfy it with a check-then-open sequence and reintroduce the TOCTOU race that accepted D3 explicitly excluded.

**Required repair:** restore those invariants verbatim or replace them with equal-or-stronger race-safe architectural statements. The new TRAIN2-before-EVAL2 terminal boundary may change what the proof binds; it does not authorize weakening how that proof is authenticated, retained, reused, or protected from storage races.

## 4. Challenge pass

No serious challenge is raised to ratified D1 or D2. Their dependency/currentness semantics are mutually coherent and concretizable.

The serious challenge is confined to the proposed D3 candidate because R1-D3-1 is an actual dependency cycle and R1-D3-2 is a direct persistence contradiction. R1-D3-3 and R1-D3-4 are additional blocking abstraction/currentness regressions.

## 5. Evidence and applicability

Executed review evidence:

- exact immutable D3/D4 candidate inspection at `119c4067b1852be127134d6b0fb1aae6cace4bd6`;
- direct comparison with ratified D2 definitions/axioms on selection, currentness, continuation, and measurement equivalence;
- direct inspection of current P5 executable owners:
  - `mdstats/training_data/post_selection_execution.py` — fitted preparation, materialization, EVAL2 role identity, run evidence;
  - `mdstats/training_data/campaign_post_selection_runtime.py` — run activity lease, terminal evidence, completion/topology owner, CV/final root publication;
  - `mdstats/training_data/post_selection_store.py` — existing immutable evidence store and CampaignStore pointer seam;
  - `mdstats/training_data/post_selection_cv_acceptance.py` — current complete candidate-set fold evidence;
- accepted-current D3 completion/storage semantics at the pre-candidate parent;
- project PEM/HAS as supporting recurrence/simplification evidence only;
- archived prior plan/preparation-cycle incident as supporting evidence only.

No runtime test was required to establish these D3 contradictions because the reviewed artifact is an authority/specification candidate with no D4 implementation changes. Runtime evidence becomes required after the architecture is coherent and implementation begins.

## 6. Impact closure and handoff

Gate D remains open. Gate E remains blocked. Candidate `119c4067b1852be127134d6b0fb1aae6cace4bd6` must not be handed to the implementer as accepted authority.

A repaired candidate must close R1-D3-1 through R1-D3-4, preserve all unaffected D3 text/side constraints, update the D4 specification/workplan consistently, and then undergo a fresh independent D3 Review on a new immutable target.

No production code was modified by this review.
