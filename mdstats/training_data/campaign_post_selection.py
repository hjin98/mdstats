"""Current selected-training entry for all post-selection work.

Everything downstream of the target-size decision - cross-validation of the
training method and the fresh final-production run - starts here.  This module
owns exactly one thing: projecting the frozen target-size design admitted at
``cross-validate`` into the small set of facts downstream owners need, and
recording that projection as immutable per-size lineage records.

The frozen design is an ordered collection of distinct sizes, so this owns an
ordered collection of contexts.  The size dimension is one more post-selection
experiment dimension over one shared prepared generation: there is one context
per selected ``N``, and nothing here is per-campaign scalar any more.

It is deliberately not an authority.  Each ``N_selected`` and its exact
``T_selected`` membership are re-established on every current exposure through
the accepted P4 freeze owner, which re-derives them from the authenticated P2
training order.  The automatic screen's execution head and reducer are *not*
part of this ancestry: a campaign that never ran the diagnostic reaches
post-selection work by exactly the same path as one that did.

A persisted binding is a dependency snapshot that lets a descendant prove
*which* selected target it descends from; it can never make a retired
generation current again.  Descendants published by the scalar-selection
predecessor carry that predecessor's binding schema, so they stay valid under
their own exact ancestry rather than being re-parented onto a design that
merely happens to share ``N``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ._common import (
    TrainingDataError,
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
#: The corrected binding schema.  It names the *target* the descendant trained
#: on and nothing else: no role horizon, no selection provenance, and no digest
#: of a record that carries them.  See :class:`PostSelectionBinding`.
POST_SELECTION_BINDING_SCHEMA = "mdstats.post-selection-binding.v3"
#: The scalar-selection predecessor schema.  It additionally hashed the whole
#: frozen selection record, which transitively pulled the production horizon and
#: the manual/auto provenance into every descendant identity.  Rows written
#: under it are still read and stay current under their exact legacy ancestry;
#: no new binding is ever written under it.
POST_SELECTION_BINDING_V2_SCHEMA = "mdstats.post-selection-binding.v2"
#: The pre-rework schema.  Rows written under it carry the legacy P4/P5 lineage
#: including the legacy adopted execution head and reducer state digests.
POST_SELECTION_BINDING_V1_SCHEMA = "mdstats.post-selection-binding.v1"



class PostSelectionError(TrainingDataError):
    """A post-selection owner refused to treat state as current or valid."""


class PostSelectionStaleBindingError(PostSelectionError):
    """A persisted post-selection binding no longer descends from current P4 state."""


@dataclass(frozen=True, slots=True)
class PostSelectionBinding:
    """The *target* a descendant trained on: one per-size scientific lineage.

    This record answers exactly one question - which selected training target,
    under which prepared scientific substrate, does this evidence descend from -
    and it is deliberately incapable of answering any other.  It names the
    canonical generation, the accepted P1/P2 lineage, ``N_selected`` and the
    exact ``T_selected`` membership identity.

    What it does **not** name is as load-bearing as what it does.  The
    cross-validation horizon belongs to the CV policy, the production horizon
    belongs to the final-production policy, and manual-versus-automatic
    provenance belongs to the audit record.  None of them describes the target,
    so none of them may change this identity - directly *or* through a digest of
    a record that happens to carry them.  Editing the production budget must not
    invalidate accepted CV evidence, and choosing the same size by hand rather
    than by diagnostic must not fork one experiment into two.

    Sibling sizes are equally absent.  A per-size identity that hashed the whole
    frozen collection would change every size's evidence whenever another size
    was added, which is exactly the contamination a multi-size design must not
    have.

    The record is content-addressed and carries no mutable state.  Comparing it
    against a freshly resolved current context is the only supported way to ask
    "is this descendant still current?"; the record never answers that itself.

    ``legacy_frozen_selection_digest`` exists only for reading descendants
    published by the scalar-selection predecessor, whose binding did hash the
    whole frozen record.  Such a binding keeps its own bytes and its own
    identity so evidence accepted under it stays current; nothing new is ever
    constructed with it set.
    """

    campaign_generation: int
    experiment_definition_digest: str
    training_order_digest: str
    frame_authority_digest: str
    neutral_statistical_base_digest: str
    split_exclusion_digest: str
    target_size_policy_digest: str
    aggregate_digest: str
    n_selected: int
    selected_membership_digest: str
    legacy_frozen_selection_digest: str | None = None
    legacy_v1_campaign_state_revision: str | None = None
    legacy_v1_execution_head_digest: str | None = None
    legacy_v1_reducer_state_digest: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "experiment_definition_digest",
            "training_order_digest",
            "frame_authority_digest",
            "neutral_statistical_base_digest",
            "split_exclusion_digest",
            "target_size_policy_digest",
            "aggregate_digest",
            "selected_membership_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        if self.legacy_frozen_selection_digest is not None:
            object.__setattr__(
                self,
                "legacy_frozen_selection_digest",
                validate_digest(
                    self.legacy_frozen_selection_digest,
                    name="legacy_frozen_selection_digest",
                ),
            )
        if self.legacy_v1_campaign_state_revision is not None:
            object.__setattr__(
                self,
                "legacy_v1_campaign_state_revision",
                validate_digest(
                    self.legacy_v1_campaign_state_revision,
                    name="legacy_v1_campaign_state_revision",
                ),
            )
        if self.legacy_v1_execution_head_digest is not None:
            object.__setattr__(
                self,
                "legacy_v1_execution_head_digest",
                validate_digest(
                    self.legacy_v1_execution_head_digest,
                    name="legacy_v1_execution_head_digest",
                ),
            )
        if self.legacy_v1_reducer_state_digest is not None:
            object.__setattr__(
                self,
                "legacy_v1_reducer_state_digest",
                validate_digest(
                    self.legacy_v1_reducer_state_digest,
                    name="legacy_v1_reducer_state_digest",
                ),
            )
        generation = int(self.campaign_generation)
        if generation < 0:
            raise TrainingDataInputError(
                "A post-selection binding requires a nonnegative canonical generation."
            )
        object.__setattr__(self, "campaign_generation", generation)
        n_selected = int(self.n_selected)
        if n_selected <= 0:
            raise TrainingDataInputError(
                "A post-selection binding requires a positive selected size."
            )
        object.__setattr__(self, "n_selected", n_selected)

    @property
    def is_v1_legacy_schema(self) -> bool:
        return self.legacy_v1_execution_head_digest is not None

    @property
    def is_legacy_schema(self) -> bool:
        return (
            self.legacy_frozen_selection_digest is not None
            or self.is_v1_legacy_schema
        )

    def _payload(self) -> dict[str, Any]:
        if self.is_v1_legacy_schema:
            return {
                "schema": POST_SELECTION_BINDING_V1_SCHEMA,
                "campaign_generation": self.campaign_generation,
                "campaign_state_revision": self.legacy_v1_campaign_state_revision,
                "experiment_definition_digest": self.experiment_definition_digest,
                "training_order_digest": self.training_order_digest,
                "frame_authority_digest": self.frame_authority_digest,
                "neutral_statistical_base_digest": self.neutral_statistical_base_digest,
                "split_exclusion_digest": self.split_exclusion_digest,
                "target_size_policy_digest": self.target_size_policy_digest,
                "aggregate_digest": self.aggregate_digest,
                "adopted_execution_head_digest": self.legacy_v1_execution_head_digest,
                "adopted_reducer_state_digest": self.legacy_v1_reducer_state_digest,
                "n_selected": self.n_selected,
                "selected_membership_digest": self.selected_membership_digest,
            }
        payload = {
            "schema": (
                POST_SELECTION_BINDING_V2_SCHEMA
                if self.legacy_frozen_selection_digest is not None
                else POST_SELECTION_BINDING_SCHEMA
            ),
            "campaign_generation": self.campaign_generation,
            "experiment_definition_digest": self.experiment_definition_digest,
            "training_order_digest": self.training_order_digest,
            "frame_authority_digest": self.frame_authority_digest,
            "neutral_statistical_base_digest": self.neutral_statistical_base_digest,
            "split_exclusion_digest": self.split_exclusion_digest,
            "target_size_policy_digest": self.target_size_policy_digest,
            "aggregate_digest": self.aggregate_digest,
            "n_selected": self.n_selected,
            "selected_membership_digest": self.selected_membership_digest,
        }
        if self.legacy_frozen_selection_digest is not None:
            # Reproduced in the predecessor's exact bytes, so a descendant
            # published under it still authenticates and stays reachable.
            payload["frozen_selection_digest"] = self.legacy_frozen_selection_digest
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PostSelectionBinding":
        schema = payload.get("schema")
        if schema not in (
            POST_SELECTION_BINDING_SCHEMA,
            POST_SELECTION_BINDING_V2_SCHEMA,
            POST_SELECTION_BINDING_V1_SCHEMA,
        ):
            raise TrainingDataSerializationError(
                "Unsupported post-selection binding schema."
            )
        if schema == POST_SELECTION_BINDING_V1_SCHEMA:
            result = cls(
                campaign_generation=int(payload["campaign_generation"]),
                experiment_definition_digest=str(payload["experiment_definition_digest"]),
                training_order_digest=str(payload["training_order_digest"]),
                frame_authority_digest=str(payload["frame_authority_digest"]),
                neutral_statistical_base_digest=str(
                    payload["neutral_statistical_base_digest"]
                ),
                split_exclusion_digest=str(payload["split_exclusion_digest"]),
                target_size_policy_digest=str(payload["target_size_policy_digest"]),
                aggregate_digest=str(payload["aggregate_digest"]),
                n_selected=int(payload["n_selected"]),
                selected_membership_digest=str(payload["selected_membership_digest"]),
                legacy_frozen_selection_digest=None,
                legacy_v1_campaign_state_revision=(
                    str(payload["campaign_state_revision"])
                    if payload.get("campaign_state_revision") is not None
                    else None
                ),
                legacy_v1_execution_head_digest=(
                    str(payload["adopted_execution_head_digest"])
                    if payload.get("adopted_execution_head_digest") is not None
                    else None
                ),
                legacy_v1_reducer_state_digest=(
                    str(payload["adopted_reducer_state_digest"])
                    if payload.get("adopted_reducer_state_digest") is not None
                    else None
                ),
            )
        else:
            result = cls(
                campaign_generation=int(payload["campaign_generation"]),
                experiment_definition_digest=str(payload["experiment_definition_digest"]),
                training_order_digest=str(payload["training_order_digest"]),
                frame_authority_digest=str(payload["frame_authority_digest"]),
                neutral_statistical_base_digest=str(
                    payload["neutral_statistical_base_digest"]
                ),
                split_exclusion_digest=str(payload["split_exclusion_digest"]),
                target_size_policy_digest=str(payload["target_size_policy_digest"]),
                aggregate_digest=str(payload["aggregate_digest"]),
                n_selected=int(payload["n_selected"]),
                selected_membership_digest=str(payload["selected_membership_digest"]),
                legacy_frozen_selection_digest=(
                    str(payload["frozen_selection_digest"])
                    if schema == POST_SELECTION_BINDING_V2_SCHEMA
                    else None
                ),
            )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Post-selection binding digest mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class CurrentSelectedTrainingContext:
    """The authenticated frozen selection, projected for downstream owners.

    Only ``binding`` and ``selected_membership`` carry the *target* identity.
    ``frozen`` additionally carries the two effective role horizons that were
    admitted with it, which is how a CV or production policy resolver reads a
    budget the operator fixed rather than whatever the config file says today.
    The reconstructed authority bundle travels along as an opaque reference so
    downstream owners can reach real P1/P2 data without this adapter duplicating
    any of their validation.
    """

    binding: PostSelectionBinding
    selected_membership: tuple[str, ...]
    frozen: Any = field(compare=False, repr=False)
    authorities: Any = field(compare=False, repr=False)

    def __post_init__(self) -> None:
        membership = tuple(str(v) for v in self.selected_membership)
        if len(membership) != self.binding.n_selected or len(set(membership)) != len(
            membership
        ):
            raise TrainingDataInputError(
                "T_selected must contain exactly N_selected unique frames."
            )
        object.__setattr__(self, "selected_membership", membership)

    @property
    def n_selected(self) -> int:
        return self.binding.n_selected

    @property
    def selected_membership_digest(self) -> str:
        return self.binding.selected_membership_digest

    @property
    def campaign_generation(self) -> int:
        return self.binding.campaign_generation

    @property
    def content_digest(self) -> str:
        return self.binding.content_digest

    @property
    def definition(self) -> Any:
        return self.authorities.aggregate.definition

    @property
    def split_exclusion(self) -> Any:
        return self.authorities.split_exclusion

    def require_binding(self, binding: PostSelectionBinding) -> None:
        """Fail closed unless *binding* is the current selection lineage.

        Descendant evidence proves currency by matching the freshly resolved
        binding.  It is never enough for a stored binding to be internally
        consistent: an earlier generation's binding is perfectly well formed
        and is exactly what must be rejected here.
        """

        if not isinstance(binding, PostSelectionBinding):
            raise TrainingDataInputError(
                "A post-selection currentness check requires a PostSelectionBinding."
            )
        if binding.content_digest != self.binding.content_digest:
            raise PostSelectionStaleBindingError(
                "This post-selection evidence descends from target-size generation "
                f"{binding.campaign_generation} (binding "
                f"{binding.content_digest[:12]}...), but the current authenticated "
                f"selection is generation {self.binding.campaign_generation} (binding "
                f"{self.binding.content_digest[:12]}...). Stale descendants are never "
                "republished as current."
            )


def target_size_binding(state: Any, frozen_entry: Any) -> PostSelectionBinding:
    """Project one frozen per-size entry into its descendant target lineage.

    This is the single owner of that projection.  Freeze admission, P5 pointer
    publication, storage reachability and public observation all derive their
    bindings here, so no second, weaker derivation can exist beside it and drift.

    Selection *provenance* - manual choice or adopted automatic recommendation -
    and both role horizons are deliberately absent.  The same ``N`` on the same
    substrate is the same downstream scientific target however the operator
    arrived at it and whatever budgets its roles were given.
    """

    return PostSelectionBinding(
        campaign_generation=state.generation,
        experiment_definition_digest=state.experiment_definition_digest,
        training_order_digest=frozen_entry.training_order_digest,
        frame_authority_digest=state.frame_authority_digest,
        neutral_statistical_base_digest=state.neutral_statistical_base_digest,
        split_exclusion_digest=state.split_exclusion_digest,
        target_size_policy_digest=state.policy_digest,
        aggregate_digest=state.aggregate_digest,
        n_selected=int(frozen_entry.n_selected),
        selected_membership_digest=str(frozen_entry.selected_membership_digest),
        legacy_frozen_selection_digest=(
            frozen_entry.content_digest if state.legacy_scalar_binding else None
        ),
    )


def current_target_size_bindings(state: Any) -> tuple[PostSelectionBinding, ...]:
    """Every current per-size descendant binding, in frozen selection order.

    Before the freeze there are none, which is exactly right: a provisional
    design has no descendants.
    """

    if not getattr(state, "frozen_entries", None):
        return ()
    return tuple(target_size_binding(state, entry) for entry in state.frozen_entries)


def build_post_selection_binding(admitted: Any) -> PostSelectionBinding:
    """Project one authenticated admitted per-size selection into its lineage."""

    frozen = admitted.frozen
    if frozen is None:
        raise PostSelectionError(
            "A post-selection binding requires a frozen target selection."
        )
    state = admitted.revision.state
    if not state.frozen_entries:
        raise PostSelectionError(
            "A post-selection binding requires a frozen target-size design."
        )
    return target_size_binding(state, frozen)


def load_current_selected_training_contexts(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    *,
    admit: bool = False,
) -> tuple[CurrentSelectedTrainingContext, ...]:
    """Resolve every current per-size training context, in frozen order.

    This is the one production-owned enumeration of the frozen design.  Callers
    - including test harnesses - iterate what this returns rather than
    reassembling a loop out of raw campaign state, so the membership, order and
    authentication every size receives are the ones the product actually
    applies.

    ``admit`` is the freeze authority and belongs to ``cross-validate`` alone.
    Every other consumer requires a freeze that already happened, so merely
    describing or continuing downstream work can never commit the experiment.
    """

    from .campaign_target_size_cutover import require_current_target_size_runtime
    from .campaign_target_size_selection import resolve_frozen_target_design

    revision = require_current_target_size_runtime(store)
    if revision.state.is_prerework_schema:
        return _load_legacy_prerework_training_contexts(cfg, paths, store, revision)

    admitted_design = resolve_frozen_target_design(cfg, paths, store, admit=admit)
    return tuple(
        _selected_training_context(admitted)
        for admitted in admitted_design.per_size
    )


@dataclass(frozen=True, slots=True)
class _LegacyEvaluationOrder:
    digest_value: str

    def membership_digest(self, evaluation_size: int) -> str:
        return self.digest_value


@dataclass(frozen=True, slots=True)
class _LegacyExperimentDefinition:
    content_digest: str
    training_order: Any = None
    policy: Any = None
    m3_membership: tuple[str, ...] = ()
    m3_digest: str = ""

    def evaluation_membership(self, evaluation_size: int) -> tuple[str, ...]:
        return self.m3_membership

    @property
    def evaluation_order(self) -> Any:
        return _LegacyEvaluationOrder(digest_value=self.m3_digest)


@dataclass(frozen=True, slots=True)
class _LegacyTargetSizeAggregate:
    content_digest: str
    definition: _LegacyExperimentDefinition


def _load_legacy_prerework_training_contexts(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    revision: Any,
) -> tuple[CurrentSelectedTrainingContext, ...]:
    import json
    import mdstats
    from ._campaign_cli_core import (
        _ensure_manifest,
        _load_or_rebuild_frame_data,
        _path_cfg,
    )
    from ._frame_access import build_frame_array_index
    from .campaign_target_size_runtime import (
        CurrentTargetSizeAuthorities,
        resolve_neutral_partition_policy,
    )
    from .neutral_substrate import (
        authenticate_vasp_source_authority,
        authenticated_vasp_temperature_targets,
        build_canonical_frame_authority,
        build_neutral_feature_evidence_from_data4_bundle,
        build_neutral_split_exclusion_evidence,
        build_neutral_statistical_base,
        build_source_authority_from_data2_catalog,
    )
    from .post_selection_cv_plan import PostSelectionCvPlan
    from .post_selection_production import FinalProductionPlan
    from .post_selection_run_identity import (
        PostSelectionRunRole,
        post_selection_run_identity,
    )
    from .post_selection_store import (
        POINTER_CV_PLAN,
        POINTER_FINAL_PLAN,
        open_post_selection_store,
        post_selection_root,
        read_current_post_selection_pointer,
    )
    from .target_size_experiment import (
        resolve_target_size_policy_from_config,
        target_training_prefix_digest,
    )

    state = revision.state
    terminal = state.auto_diagnostic
    if terminal is None or not terminal.has_recommendation:
        raise PostSelectionError(
            "Pre-rework campaign state does not contain a terminal target-size selection."
        )

    binding = PostSelectionBinding(
        campaign_generation=state.generation,
        experiment_definition_digest=state.experiment_definition_digest,
        training_order_digest=terminal.training_order_digest,
        frame_authority_digest=state.frame_authority_digest,
        neutral_statistical_base_digest=state.neutral_statistical_base_digest,
        split_exclusion_digest=state.split_exclusion_digest,
        target_size_policy_digest=state.policy_digest,
        aggregate_digest=state.aggregate_digest,
        n_selected=terminal.recommended_target_size,
        selected_membership_digest=terminal.recommended_membership_digest,
        legacy_v1_campaign_state_revision=revision.state_revision,
        legacy_v1_execution_head_digest=state.adopted_execution_head_digest,
        legacy_v1_reducer_state_digest=state.adopted_reducer_state_digest,
    )

    evidence_store = open_post_selection_store(paths, binding, create=False)
    cv_plan_digest = read_current_post_selection_pointer(
        store, binding=binding, kind=POINTER_CV_PLAN
    )
    if cv_plan_digest is None or not evidence_store.has(cv_plan_digest):
        raise PostSelectionError(
            "Pre-rework campaign state is missing its published CV plan."
        )
    cv_plan = evidence_store.get(cv_plan_digest, PostSelectionCvPlan.from_dict)
    first_fold = cv_plan.folds[0]
    membership = tuple(
        sorted(
            first_fold.training_frame_uids
            + first_fold.checkpoint_monitor_frame_uids
            + first_fold.outer_evaluation_frame_uids
            + first_fold.purged_frame_uids
        )
    )
    if (
        len(membership) != binding.n_selected
        or target_training_prefix_digest(
            binding.training_order_digest,
            binding.n_selected,
            membership,
        )
        != binding.selected_membership_digest
    ):
        raise PostSelectionError(
            "Legacy CV plan frame membership does not reproduce the selected membership digest."
        )

    training_root = _path_cfg(cfg, paths, "training_root")
    manifest = _ensure_manifest(cfg, paths, approve=False)
    source_catalog = store.get_record(
        "source_catalog", mdstats.TrainingDataSourceCatalog
    )
    data4 = store.get_record("data4", mdstats.Data4FeatureBundle)
    frame_catalog = store.get_record("frame_catalog", mdstats.TrainingFrameCatalog)
    frame_data_by_run, frame_records = _load_or_rebuild_frame_data(
        cfg, paths, source_catalog
    )
    source_authority = build_source_authority_from_data2_catalog(
        source_catalog, manifest=manifest
    )
    authenticated = authenticate_vasp_source_authority(
        source_authority, base_directory=training_root
    )
    frame_authority = build_canonical_frame_authority(
        source_authority,
        frame_data_by_run,
        temperature_targets_by_run=authenticated_vasp_temperature_targets(
            authenticated
        ),
    )
    feature_evidence = build_neutral_feature_evidence_from_data4_bundle(
        source_authority, frame_authority, data4
    )
    neutral_base = build_neutral_statistical_base(
        source_authority,
        frame_authority,
        feature_evidence,
        policy=resolve_neutral_partition_policy(cfg),
    )
    split_exclusion = build_neutral_split_exclusion_evidence(
        frame_authority, neutral_base
    )
    frame_array_index = build_frame_array_index(frame_catalog, frame_data_by_run)

    if frame_authority.content_digest != state.frame_authority_digest:
        raise PostSelectionError("Frame authority digest mismatch in legacy workspace.")
    if neutral_base.content_digest != state.neutral_statistical_base_digest:
        raise PostSelectionError(
            "Neutral statistical base digest mismatch in legacy workspace."
        )
    if split_exclusion.content_digest != state.split_exclusion_digest:
        raise PostSelectionError(
            "Split exclusion digest mismatch in legacy workspace."
        )

    target_size_policy = resolve_target_size_policy_from_config(cfg)
    m3_frames: tuple[str, ...] = ()
    m3_digest = ""
    final_plan_digest = read_current_post_selection_pointer(
        store, binding=binding, kind=POINTER_FINAL_PLAN
    )
    if final_plan_digest is not None and evidence_store.has(final_plan_digest):
        final_plan = evidence_store.get(
            final_plan_digest, FinalProductionPlan.from_dict
        )
        m3_digest = final_plan.m3_membership_digest
        if final_plan.required_final_seeds:
            seed = final_plan.required_final_seeds[0]
            run_id = post_selection_run_identity(
                role=PostSelectionRunRole.FINAL_PRODUCTION,
                plan_digest=final_plan.content_digest,
                optimizer_seed=seed,
            )
            mat_path = (
                post_selection_root(paths, binding.campaign_generation)
                / "runs"
                / run_id
                / "materialization"
                / "materialization.json"
            )
            if mat_path.is_file():
                mat_data = json.loads(mat_path.read_text(encoding="utf-8"))
                mon = mat_data.get("checkpoint_monitor_artifact")
                if mon and "frame_uids" in mon:
                    m3_frames = tuple(str(x) for x in mon["frame_uids"])

    authorities = CurrentTargetSizeAuthorities(
        manifest=manifest,
        source_catalog=source_catalog,
        source_authority=source_authority,
        frame_authority=frame_authority,
        feature_evidence=feature_evidence,
        neutral_base=neutral_base,
        split_exclusion=split_exclusion,
        aggregate=_LegacyTargetSizeAggregate(
            content_digest=state.aggregate_digest,
            definition=_LegacyExperimentDefinition(
                content_digest=state.experiment_definition_digest,
                policy=target_size_policy,
                m3_membership=m3_frames,
                m3_digest=m3_digest,
            ),
        ),
        common=None,
        frame_catalog=frame_catalog,
        frame_data_by_run=frame_data_by_run,
        frame_array_index=frame_array_index,
        frame_records=frame_records,
    )
    return (
        CurrentSelectedTrainingContext(
            binding=binding,
            selected_membership=membership,
            frozen=None,
            authorities=authorities,
        ),
    )


def _selected_training_context(admitted: Any) -> CurrentSelectedTrainingContext:
    binding = build_post_selection_binding(admitted)
    definition = admitted.definition
    membership = definition.training_order.candidate_membership(binding.n_selected)
    if (
        definition.training_order.candidate_digest(binding.n_selected)
        != binding.selected_membership_digest
    ):
        raise PostSelectionError(
            "The exact pi_train prefix does not reproduce the authenticated "
            "T_selected membership digest."
        )
    return CurrentSelectedTrainingContext(
        binding=binding,
        selected_membership=membership,
        frozen=admitted.frozen,
        authorities=admitted.authorities,
    )


def load_current_selected_training_context(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    *,
    admit: bool = False,
    n_selected: int | None = None,
) -> CurrentSelectedTrainingContext:
    """Resolve exactly one current per-size training context.

    It is a *selector* over :func:`load_current_selected_training_contexts`, not
    a second authority: the collection owner does all the resolution and this
    only picks the requested member.  ``n_selected`` may be omitted only when
    the frozen design has exactly one size, because for a multi-size design
    "the campaign's selected size" is not a fact and guessing one would silently
    turn an all-sizes experiment into a single-size one.
    """

    contexts = load_current_selected_training_contexts(
        cfg, paths, store, admit=admit
    )
    return select_selected_training_context(contexts, n_selected=n_selected)


def select_selected_training_context(
    contexts: "tuple[CurrentSelectedTrainingContext, ...]",
    *,
    n_selected: int | None = None,
) -> CurrentSelectedTrainingContext:
    """Pick one member of an already-resolved ordered per-size collection."""

    if n_selected is None:
        if len(contexts) == 1:
            return contexts[0]
        raise PostSelectionError(
            "The frozen target-size design contains "
            f"{len(contexts)} selected sizes "
            f"{[item.n_selected for item in contexts]}; name the size explicitly. "
            "There is no single 'the' selected size for a multi-size experiment."
        )
    size = int(n_selected)
    for context in contexts:
        if context.n_selected == size:
            return context
    raise PostSelectionError(
        f"Target size {size} is not part of the current frozen design "
        f"{[item.n_selected for item in contexts]}."
    )


__all__ = [
    "POST_SELECTION_BINDING_SCHEMA",
    "POST_SELECTION_BINDING_V2_SCHEMA",
    "POST_SELECTION_BINDING_V1_SCHEMA",
    "CurrentSelectedTrainingContext",
    "PostSelectionBinding",
    "PostSelectionError",
    "PostSelectionStaleBindingError",
    "build_post_selection_binding",
    "current_target_size_bindings",
    "load_current_selected_training_context",
    "load_current_selected_training_contexts",
    "select_selected_training_context",
    "target_size_binding",
]
