# D3/D4 second-review amendment — post-selection method restoration

**Parent workplan:** `workplans/active/MLFF_POST_SELECTION_UNIVERSAL_LOSS_MONITOR_AND_CV_METHOD_RESTORATION_WORKPLAN.md`  
**Status:** binding amendment to the active parent until folded into that file; it does not create a second implementation authority  
**Protocol:** SSDP 6.3  

## 1. Review disposition

The parent workplan remains architecturally sound, but a second pass against the accepted D1/D2 authority and the actual current D3/D4 owners found four residual handoff/staging ambiguities that must be closed before G1A/G1B may PASS. These are plan defects, not reasons to reopen D1/D2.

This amendment is intentionally narrow. It changes no scientific/numerical method and introduces no new method, monitor, E0, publication, or currentness owner. It only makes the parent plan executable without contradictory stage dependencies or schema latitude.

## 2. Finding A — monitor-dependent work was scheduled before the common monitor exists

The parent Stage A currently lists G9 together with G2/G3/G3A/G8, while G9 requires target-side stopping/checkpoint evidence to consume the campaign-common `M_mon`. The common monitor is not constructed and authenticated until G5/G6 in Stage C. Implementing the G9 routing in Stage A would therefore require either a temporary monitor path, retention of the superseded fold/M3 path, or a second later rewrite. All three violate the reductive owner-rewiring strategy.

### Binding repair

Interpret/replace the Stage A staging sentence as:

```text
Implementation Stage A — method/exposure/config/identity cutover

After G1A/G1B PASS, implement G2, G3, G3A, G8 and the
method/exposure portions of G10. Preserve and regression-protect the existing
G9 score/admissibility policy constants here, but do not claim or implement the
current target-monitor-parent routing until the common monitor exists.
```

Interpret/replace the Stage C staging sentence as:

```text
Implementation Stage C — common monitor and CV/final topology

Implement G5, G6, G7, the target-monitor-routing portion of G9, and the
common-monitor binding completion of G4 as one topology/integration stage.
```

G9 itself is therefore split only by implementation dependency, not by ownership:

- Stage A preserves `target_score_weight`, `replay_score_weight`, replay baseline/degradation and admissibility semantics and proves head-scalar retirement does not alter them.
- Stage C rewires the target evidence consumed by the existing checkpoint/adaptive-stop owner to the exact authenticated common `M_mon` and removes all fold/final/M3 target-parent construction.

No temporary target-monitor owner or compatibility wrapper is permitted.

## 3. Finding B — G4 cannot fully close before the actual `M_mon` composition set exists

Accepted D1/D2 requires composition-transfer identifiability for every governed target composition whose energy is consumed by fold training, common-monitor checkpoint control, and held-out evaluation; final production requires complete `T_selected` plus common-monitor compositions. The parent Stage B schedules G4 before Stage C constructs the exact common monitor. A validator can be implemented and falsified with manufactured composition sets in Stage B, but the current P5 fitted-preparation result cannot be authenticated without the actual common-monitor record.

### Binding repair

Stage B may implement and test:

- training-mode resolution of `FOUNDATION_RESIDUAL` versus scratch fitting;
- exact selected-foundation-head prediction/reference-E0 acquisition;
- the existing residual-fit owner wiring;
- numerical rank/null-space/anchor evidence;
- the `c^T v = 0` transfer validator;
- held-out/training composition extraction from authorized geometry only; and
- the wrong-head, label-leakage, rank-deficient and absent-element falsification cases already listed in G4.

However, **G4 is not current-run complete in Stage B**. No foundation-P5 `PostSelectionFittedPreparation`, materialization, restart, or run may authenticate as current until Stage C has produced the exact common-monitor record and the preparation has bound and validated the required composition set derived from that record.

Manufactured monitor composition sets are test oracles only. They cannot substitute for current common-monitor ancestry.

Stage C must therefore complete G4 by:

1. resolving the exact common-monitor record from G5;
2. deriving its canonical required composition classes from geometry/count evidence without consuming monitor labels for fitting;
3. binding the common-monitor record/composition-set ancestry into the fold/final fitted-preparation transfer evidence;
4. rerunning transfer feasibility against the combined required composition set; and
5. refusing plan/run admission if transfer is not identifiable.

This does not make the common monitor an E0-fit label source; it is only a required-composition consumer.

## 4. Finding C — the D4 freeze did not fully specify the replacement foundation-P5 fitted-preparation shape

Current D4 `PostSelectionFittedPreparation` is a weight-bearing P3-derived shape: it binds `common_training_policy_digest`, serializes `objective_policy`, requires `fitted_weights_digest`, and requires `fitted_frame_weights` covering the fit membership. `fit_post_selection_preparation()` also defaults through `TargetSizeCommonTrainingPolicy`, fits configuration weights, and only activates residual fitting when the generic policy already says so.

The parent correctly requires removal of whole-P3-policy coupling and inert configuration weighting, but G1B leaves enough latitude for an implementation to retain the old fields as null/default compatibility baggage. That would preserve a false currentness parent and an inert scientific-looking identity.

### Binding D4 handoff

Before executable code changes, G1B must freeze a current foundation-adaptation preparation representation with these externally visible invariants:

```text
owner plan/run ancestry                 required
preparation kind / training mode        explicit and authenticated
P5 preparation-policy digest            required; not TargetSizeCommonTrainingPolicy.content_digest
exact fit membership + digest           required
atomic-reference fit record/result      required
selected foundation checkpoint/head     required for foundation modes
foundation prediction/E0 input identity required for foundation modes
required composition-set digest         required for foundation modes
rank/null-space/tolerance/anchor evidence required for foundation modes
composition-transfer result             required for foundation modes
P3 objective_policy payload             forbidden as a foundation-P5 preparation parent
fitted configuration-weight identity    forbidden for foundation modes
fitted_weights_digest/frame-weight table forbidden for foundation modes unless a future accepted method consumes them
```

The fixed foundation-P5 UniversalLoss objective belongs to `PostSelectionMethodIdentity` / the P5 method-policy projection and executable MACE evidence; it is not inherited through the P3 `objective_policy` field of fitted preparation.

If D4 keeps one preparation dataclass for both scratch and foundation modes, it must behave as a tagged/mode-disjoint representation with fail-closed invariants:

- scratch may carry its separately accepted weight-bearing/from-scratch fields;
- foundation modes may carry only their residual-E0/transfer fields plus shared ancestry;
- fields forbidden for one mode cannot be silently populated, defaulted, ignored, or included in the content digest; and
- deserializing a historical weight-bearing foundation preparation does not make it current.

A cleaner mode-specific schema is also admissible. The architectural requirement is semantic separation, not a particular class decomposition.

Historical preparation payloads may remain available as historical evidence through the repository's accepted compatibility mechanism, but the current execution/currentness loader must never reinterpret them as the new foundation-adaptation preparation merely because their bytes deserialize.

## 5. Finding D — final single-best publication ordering needs an exact D4 owner contract

The parent correctly removes M3 and requires `single_best_final_seed` to use the already-frozen representatives' common-monitor target evidence. Current code uses the accepted target-only EVAL2 ordering machinery over M3 records, including primary force-RMSE bands, uncertainty/bootstrap logic, secondary target metrics, maturity/tie rules and deterministic seed material. Saying only “common-monitor target metric” leaves room for an implementer to replace that ordering with a scalar `min(RMSE)` sort.

### Binding repair

G1B/G6 must specify that `single_best_final_seed`:

- consumes **only already-frozen admissible final representatives**;
- consumes each representative's already-authenticated target metric record on the exact shared common `M_mon`;
- reuses the accepted target-only ordering policy/semantics that governs representative target ordering, including its deterministic tie/uncertainty semantics where applicable;
- derives any ordering seed material deterministically from current final-plan/publication ancestry, not process/completion order;
- performs **no second target evaluation** and no M3 evaluation for publication selection; and
- records enough ordering-policy and metric-record lineage to reproduce the published member decision.

`all_qualified_final_seeds` continues to publish the already-admissible required seeds without cross-seed ranking.

If the accepted target-only ordering machinery cannot operate over the common-monitor records without changing its numerical meaning, that is a D2/D3 challenge; D4 must not silently substitute a simpler ranking rule.

## 6. D3 source census correction

`docs/arch_manuals/mlff_training_data/30_statistical_design.md` is a mandatory G1A surface, not merely an optional search hit. It currently states that a fold checkpoint monitor is one of the post-selection fold-local interfaces. Under restored authority the target checkpoint monitor is external campaign-common evidence; only gradient training, held-out outer evaluation and accepted purge/exclusion remain selected-fold membership.

G1A must therefore reconcile at least:

```text
docs/arch_manuals/mlff_training_data/30_statistical_design.md
docs/arch_manuals/mlff_training_data/40_training_evaluation.md
docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md
docs/arch_manuals/mlff_training_data_architecture.md   # generated aggregate
```

The generated aggregate remains derived output and is regenerated from canonical chapters; it is not edited as an independent D3 authority.

## 7. G1B versus Stage D documentation boundary

The parent contains both a pre-code G1B specification freeze and a later Stage D specification/documentation reconciliation. Their roles are now explicit:

- **G1B before code:** freeze normative D4 contract—schemas, field presence/absence, failure behavior, currentness/invalidation, public/config semantics, and owner-facing interfaces required for deterministic implementation.
- **Stage D after Stages A-C:** reconcile implementation-derived examples, generated views, user guides, semantic history, and any non-normative explanatory text; verify the implementation still matches the frozen G1B contract.

A Stage D discovery that requires changing method-bearing schema/failure/currentness semantics reopens G1B (and G1A/D1/D2 if the owning layer is upstream). Stage D is not permission to redesign the contract after implementation.

## 8. Added falsification obligations

Append these cases to G11:

57. Stage A claims common-monitor checkpoint routing before an authenticated common-monitor record exists;
58. a manufactured/test monitor composition set authorizes current foundation-P5 transfer evidence;
59. current foundation-P5 preparation still serializes or digests the P3 `objective_policy`, `common_training_policy_digest`, fitted configuration-weight table, or inert `fitted_weights_digest`;
60. a shared scratch/foundation preparation schema permits forbidden cross-mode fields to be silently ignored/defaulted rather than failing closed;
61. an old weight-bearing foundation preparation deserializes and becomes current under the restored method;
62. final single-best publication replaces the accepted target-only ordering with a raw scalar-RMSE sort;
63. final publication reruns target evaluation or M3 evaluation instead of consuming frozen common-monitor representative evidence;
64. `30_statistical_design.md` or another accepted D3 source still describes the target checkpoint monitor as selected fold-local membership after G1A PASS; and
65. Stage D changes a frozen method-bearing D4 contract without reopening G1B.

## 9. Gate/closeout effect

The parent workplan remains **active**. G0 remains CLOSED/PASS. G1/G1A/G1B may close only after these amendments are folded into their review evidence and the canonical parent workplan at the next writable reconciliation point.

No implementation stage may be considered started merely because isolated code corresponding to one repaired clause exists. Executable implementation is admitted only after G1A and G1B PASS on the combined parent + this amendment contract.

The central closure invariant is strengthened by two dependency-order requirements:

```text
common monitor record exists/authenticates
    before current G9 target routing
    and before G4 foundation-transfer evidence can authorize a current run

foundation-P5 fitted preparation
    contains only semantically consumed foundation-P5 ancestry/evidence
    and cannot carry inert P3 weighting/objective authority
```

These changes close the remaining second-pass D3/D4 workplan gaps without adding implementation machinery or changing accepted D1/D2 semantics.
