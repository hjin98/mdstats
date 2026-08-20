---
kind: implementation-workplan
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 11
status: PRODUCTION_QUALIFICATION
protocol_version: 3.0.0
lineage:
  source_workplan_id: DOC-MVSEL2-HARDEN1
  source_plan_revision: 1
  source_protocol_version: 2.0.1
analysis_base_ref: feat/mvsel2-forward-lazy
analysis_base_commit: e24d5168ce01bf2d773339e1a91d5ded4871a57f
default_gate_approval: AUTO
---

# DOC-MVSEL2-HARDEN1-V3 — MVSEL2 post-implementation hardening

## 1. Authority and reset

This workplan preserves the product design and hardening requirements inherited from `DOC-MVSEL2-HARDEN1`. Revision 11 supersedes the removed qualification-only REV2–REV10 coordination artifacts.

The bounded/lightweight qualification harness, qualification-owned production-state reconstruction, candidate-identity capsules, qualification runners, admission ladders, evidence-salvage/finalization scripts, and separate workstation/Codex handoffs are not product authority and are no longer part of the workflow.

## 2. Objective

Harden and exercise the real `feat/mvsel2-forward-lazy` implementation under the real MLFF campaign. Correctness problems and performance problems discovered by the production campaign are product issues to diagnose and fix directly.

## 3. Frozen product requirements

The implementation must continue to satisfy the underlying product contracts:

1. REPAIR2 policy/default/validation is a semantic mirror of REPAIR1 except for v2 authority/schema identity.
2. Complete persisted REPAIR2 swap records and terminal order match REPAIR1 for shared fixtures and policies.
3. Production MVSEL2/REPAIR2 execution obtains MVIDX runtime state through the native forward-only reader without inverse-array mapping inside the v2 execution boundary.
4. Interrupted campaign selection resumes from the highest valid compatible MVSTATE2 checkpoint, reconstructs historical entries by selected-candidate-only forward replay, and performs one exact Phase-B frontier rebase after restore when needed.
5. REPAIR2 consumes MVSTATE2 at selector-to-repair boundaries, uses selected-prefix forward replay only as fallback, and never restores later pure-selector state after the first accepted repair divergence.
6. REPAIR2 rejected proposals use no full forward-state clones; proposal scoring uses the exact analytical hypothetical and accepted mutation happens exactly once after the winner is chosen.

Existing focused unit/regression tests remain useful engineering checks for these contracts. They are not a substitute for the production campaign.

## 4. Qualification policy

**The actual production campaign is the qualification.**

Qualification means running the normal program against the intended production campaign database, configuration, domain, and real target/replay data in the intended environment. The normal campaign's own logs, persisted records, checkpoints, telemetry, outputs, and restart behavior are the evidence.

The following qualification-only mechanisms are explicitly retired:

- reconstructing a production selector prefix solely to manufacture qualification state;
- qualification-owned MVSTATE2 checkpoints when the real campaign has not produced them;
- 128/256/512/1024 qualification ladders unrelated to useful campaign progress;
- special wall-time admission/projection rules deciding whether a qualification rung may run;
- synthetic attempts to force REPAIR2 proposals merely for qualification;
- separate supervisor/worker qualifier implementations and source-patching shims;
- candidate-identity/evidence capsules used only to coordinate the qualifier;
- evidence-salvage/finalization passes over failed qualification runs;
- a second production-scale run whose only purpose is to certify the first one.

When the real campaign exposes a defect, unacceptable scaling, excess memory use, an invalid scientific result, or a restart/recovery failure, diagnose that behavior in the product, apply focused tests as appropriate, and resume or rerun the real campaign.

## 5. Remaining acceptance path

### Product regression checks

Keep the focused tests that directly protect selector, repair, MVIDX forward-only, checkpoint/resume, and campaign-routing behavior. Ordinary package tests may be run when useful for a code change; there is no separate qualification gate requiring unrelated repository-wide tests merely to permit a production run.

### Production campaign

Run the actual campaign normally. In particular, production execution should demonstrate in useful work rather than in a disposable qualifier that:

- the authenticated production inputs open and route correctly;
- MVSEL2 progresses through the requested real selection sizes;
- checkpoints are created and can resume real interrupted work;
- REPAIR2 operates at the real selector-to-repair boundaries when proposals actually exist;
- inverse arrays remain outside the v2 runtime boundary as designed;
- memory and wall-time scaling are acceptable on the actual workstation/server;
- final persisted selections/repairs and downstream campaign behavior are scientifically valid.

The frozen performance objective remains a product goal, but performance is judged from actual campaign execution and useful completed work rather than from a separate projected qualification benchmark.

### Closeout

Merge readiness is decided from the real campaign outcome plus the focused product regressions relevant to any fixes made during that campaign. No separate qualification handoff, qualification runner, evidence finalizer, or Codex qualification pass is required.

## 6. Design-revision triggers

A design revision is still required if solving a production failure would change frozen MVSEL2/REPAIR scientific semantics, weaken complete repair-trace equivalence, change MVIDX1 scientific schema/content, restore pure-selector state after repair divergence, introduce approximate/stochastic repair where exact behavior is required, or require a materially different algorithm to meet acceptable production scaling.

Those decisions should be driven by observed real-campaign behavior rather than by failures of a qualification-only harness.
