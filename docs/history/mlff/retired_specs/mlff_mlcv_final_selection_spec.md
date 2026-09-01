# MLFF final-seed selection and committee specification

**Status:** current normative final-development selection contract  
**Architecture:** revision 105

## 1. Purpose

This specification converts accepted protocol-validation evidence plus final-development checkpoint evidence into the production-eligible model pool and final committee. Cross-validation fold models are validation evidence only and are permanently excluded from production/committee export.

## 2. Protocol-level CV gate

When cross-validation is configured, final selection requires the current CV policy to accept the complete frozen `TrainingProtocolIdentity`. A protocol that fails CV produces no production/committee authority even if an individual final-development seed has attractive development metrics.

An explicitly configured zero-fold protocol may record `cv_not_performed` when the current campaign policy permits it; that state does not imply CV robustness.

The final-development runs SHALL bind the same protocol-defining identities validated by CV, including `N_selected`. A change to target size, target-membership policy, replay, objective, stopping/LR, precision/backend, or another protocol-defining field requires new protocol-matched validation.

## 3. Final-development candidate domain

Final candidates are representatives from independent final-development optimizer-seed runs. Comparable seeds share:

- one frozen `TrainingProtocolIdentity`;
- one protocol-global selected target size;
- one final-development domain-local target-prefix identity;
- common target/replay monitor identities;
- one checkpoint/admissibility policy identity;
- the same intended exposure semantics and runtime lock.

Fold representatives passed into this layer fail closed.

## 4. Hard admissibility before ranking

A final seed is eligible only if its representative satisfies every mandatory current constraint, including as applicable:

- target force metric;
- declared focus-group/species force metrics;
- energy/stress constraints;
- worst-condition constraints;
- replay-retention constraint;
- numerical finiteness/stability;
- physical/structural integrity;
- relaxation/deployment integrity;
- required protocol/CV evidence.

Failed final seeds are omitted. Committee cardinality is never padded with an inadmissible model.

Replay retention and integrity are hard constraints, not positive score bonuses by default.

## 5. Deterministic ranking

After hard filtering, admissible final representatives are ranked by the current target-oriented primary policy. The default conceptual ordering is:

1. lower authoritative primary target metric;
2. lower declared secondary target/focus metrics as serialized by policy;
3. deterministic optimizer-seed tie;
4. deterministic checkpoint epoch/digest tie.

Replay degradation and absolute replay error remain separately reported physical diagnostics/constraints. They do not lower a candidate's ranking score merely for exceeding the required retention margin unless an explicit future scientific policy changes that rule.

The first ranked admissible candidate is the production-best **verification candidate**. Final selection does not itself assert that deployment verification has passed.

## 6. Committee construction

Every admissible final seed selected for committee membership is exported as an exact target-head deployment artifact under the current committee identity.

A committee member binds at least:

- final candidate/run identity;
- frozen protocol and selected-size identities;
- final-domain target-prefix identity;
- checkpoint digest/epoch;
- current target/focus/replay/integrity evidence;
- target-head identity;
- exported artifact digest/size/runtime identity.

Committee membership contains final-development seeds only. The best member remains subject to the current deployment/physical verification contract.

## 7. Seed semantics

Optimizer seeds alter stochastic training while partition identity remains separately controlled. Any mode that also changes CV partition identity must record that distinction explicitly and cannot be described as final-model training diversity unless it actually changes final-development training evidence under a separately accepted protocol.

Target-size study and final training use their own frozen ordered seed policies. Seed labels alone are not sufficient identity; protocol and parent lineage must match.

## 8. Restart and immutability

Final selection is deterministic from authenticated current protocol/CV and final-run records. Existing final selection/committee records are reusable only when all bound identities and exported artifacts verify.

A restart cannot substitute another checkpoint, target size, membership prefix, monitor, or replay lineage under the same immutable final-selection identity.

## 9. Failure conditions

Final selection fails closed when:

- protocol-level CV is required but not accepted;
- final runs do not match the validated complete protocol identity;
- a fold model is supplied as a production candidate;
- no final representative satisfies all mandatory constraints;
- ranking uses replay/integrity as an undeclared positive bonus;
- exported target-head identity or artifact digest does not match the selected checkpoint;
- committee membership is padded with failed/incompatible candidates;
- historical migration aliases are required to interpret a supposedly current result.

Unsupported older final-selection schemas remain historical evidence and do not define current production authority.
