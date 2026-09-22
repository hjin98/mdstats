"""Materialize, publish and resolve the P5 selected-checkpoint full models.

P5 already decides the product; what it did not do is hand the operator a file
they can load.  MACE's own terminal ``.model`` is written from the trainer's
last epoch, and the P5-selected representative is routinely an earlier one -
the motivating N=512 run selected epoch 17 while MACE saved epoch 29.  Copying
or renaming that terminal artifact would ship a different model under the
product's name, so it is never a source here.

This module owns the representation only.  It reconstructs each decided member
through the *existing* authenticated TRAIN2 checkpoint provider, serializes the
exact portable e3nn model that provider exposes, and records what it did in the
subordinate :class:`FinalProductionModelPublication`.  It ranks nothing, adds
no member, and has no API that could.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

from ._common import canonical_json
from .campaign_post_selection import PostSelectionError
from .model_artifact_trust import (
    ModelArtifactTrustError,
    authenticate_descriptor_leaf,
    authenticate_model_artifact,
    open_publication_directory,
    place_immutable_file,
    stage_authenticated_model,
)
from .post_selection_model_publication import (
    FinalProductionModelPublication,
    MODEL_SERIALIZER_IDENTITY,
    PUBLICATION_PROJECTION_FILENAME,
    PUBLICATION_PROJECTION_SCHEMA,
    PublishedModelMember,
    SERIALIZATION_FORMAT_TORCH_FULL_MODEL,
    decision_directory_relative_path,
    fresh_locator_token,
    model_artifact_basename,
    production_models_relative_root,
    validate_model_publication_against_decision,
)


class ModelPublicationError(PostSelectionError):
    """The selected representative could not be materialized or authenticated."""


class ModelRepresentationIncompatible(ModelPublicationError):
    """Existing product bytes cannot be loaded by the current supported loader.

    Distinct from a scientific failure on purpose: the selected checkpoint may
    still reconstruct the exact accepted state, in which case the correct
    repair is a fresh representation at a new locator with zero TRAIN2/EVAL2.
    """


# ---------------------------------------------------------------------------
# Shared selected-representative reconstruction
# ---------------------------------------------------------------------------


@contextmanager
def selected_representative_provider(
    context: Any,
    *,
    run_identity: str,
    checkpoint_relative_path: str,
    representative_checkpoint_sha256: str,
    materialization_digest: str,
    optimizer_seed: int,
    allow_forward_override: bool,
) -> Iterator[tuple[Any, str]]:
    """Reconstruct one decided member through the existing provider owner.

    There is exactly one MACE checkpoint reconstruction path in this
    repository, and this is a thin arrangement of its inputs, not a second
    implementation: byte-SHA authentication, TRAIN2 runtime-summary/boundary
    authentication, historical nonterminal checkpoint loading, live versus EMA
    selection, architecture authentication, foundation reconstruction, target
    multihead replay construction and the transient-CuEq to portable-e3nn
    restoration are all the provider owner's behaviour.

    The returned ``evaluated_model_state_digest`` is the provider's own; a
    publication binds that exact value rather than re-deriving a state
    convention from a filename.  The provider is retired on every exit path,
    because a model-scale accelerator owner must not outlive its block.
    """

    from .campaign_post_selection_runtime import (
        authenticated_training_materialization,
        resolve_post_selection_evaluation_model_state,
    )
    from .post_selection_execution import authenticate_post_selection_provider
    from .train2_runtime import load_train2_runtime_summary

    run_root = context.run_root(str(run_identity))
    materialization = authenticated_training_materialization(
        run_root, expected_digest=str(materialization_digest)
    )
    checkpoint_directory = run_root / "checkpoints"
    summary = load_train2_runtime_summary(checkpoint_directory)
    evaluation_model_state = resolve_post_selection_evaluation_model_state(
        context,
        seed=int(optimizer_seed),
        planned_epochs=context.production_policy.production_max_num_epochs,
    )
    provider, evaluated_digest = authenticate_post_selection_provider(
        materialization=materialization,
        materialization_directory=run_root / "materialization",
        checkpoint_directory=checkpoint_directory,
        checkpoint_name=Path(str(checkpoint_relative_path)).name,
        checkpoint_sha256=str(representative_checkpoint_sha256),
        summary=summary,
        evaluation_model_state=evaluation_model_state,
        allow_forward_override=bool(allow_forward_override),
        foundation_model_path=context.method_policies.foundation_model,
    )
    try:
        yield provider, evaluated_digest
    finally:
        retire_provider(provider)


def retire_provider(provider: Any) -> None:
    """Release one provider's accelerator/model residency at its real owner."""

    for name in ("retire", "close", "release"):
        method = getattr(provider, name, None)
        if callable(method):
            try:
                method()
            except Exception:  # noqa: BLE001 - retirement never masks the outcome
                pass
            return


def evaluation_model_state_for(context: Any, *, optimizer_seed: int) -> str:
    from .campaign_post_selection_runtime import (
        resolve_post_selection_evaluation_model_state,
    )

    return resolve_post_selection_evaluation_model_state(
        context,
        seed=int(optimizer_seed),
        planned_epochs=context.production_policy.production_max_num_epochs,
    )


# ---------------------------------------------------------------------------
# Portable model realization
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PortableModelRealization:
    """What a reconstructed selected representative is, before serialization."""

    state_sha256: str
    execution_architecture_digest: str
    dtype: str
    head_inventory: tuple[str, ...]


def _uniform_learned_dtype(model: Any) -> str:
    import torch

    observed: set[str] = set()
    for _name, tensor in model.named_parameters():
        if torch.is_floating_point(tensor):
            observed.add(str(tensor.dtype).replace("torch.", ""))
    if len(observed) != 1:
        raise ModelPublicationError(
            "A published production model must carry one uniform learned dtype; "
            f"observed {sorted(observed)}."
        )
    return observed.pop()


def _require_inference_mode(model: Any, *, where: str) -> None:
    """Training/eval mode is object state the tensor state dict cannot show."""

    if getattr(model, "training", False):
        raise ModelPublicationError(
            f"The published production model is in training mode {where}."
        )
    children = getattr(model, "modules", None)
    if callable(children):
        for module in children():
            if getattr(module, "training", False):
                raise ModelPublicationError(
                    "A submodule of the published production model is in training "
                    f"mode {where}."
                )


def realize_portable_publication_model(provider: Any, *, target_head_name: str) -> tuple[Any, PortableModelRealization]:
    """Move the authenticated portable model to CPU inference mode, and identify it.

    Device relocation is representation only: it must not change a learned
    value, the dtype, the head inventory, the buffers or the execution
    architecture, and the assertions below are what make that a checked
    property rather than an assumption.  A transient CuEq/OEq or compiled
    training realization is never the published object - the provider has
    already restored the portable e3nn model by the time it gets here.
    """

    from .model_features import (
        mace_model_execution_architecture_digest,
        mace_model_state_digest,
        mace_model_state_dict_clone,
    )

    model = getattr(provider, "model", None)
    if model is None or not hasattr(model, "state_dict"):
        raise ModelPublicationError(
            "The authenticated provider exposes no MACE model to publish."
        )
    before_architecture = mace_model_execution_architecture_digest(model)
    before_state = mace_model_state_digest(mace_model_state_dict_clone(model))
    model = model.to("cpu")
    model.eval()
    _require_inference_mode(model, where="before serialization")
    architecture = mace_model_execution_architecture_digest(model)
    state_sha256 = mace_model_state_digest(mace_model_state_dict_clone(model))
    if architecture != before_architecture or state_sha256 != before_state:
        raise ModelPublicationError(
            "Relocating the authenticated model to CPU changed its learned state or "
            "execution architecture; that is not a representation change and is "
            "never published."
        )
    heads = tuple(str(value) for value in (getattr(model, "heads", ()) or ()))
    if heads and str(target_head_name) not in heads:
        raise ModelPublicationError(
            f"The published target head {target_head_name!r} is absent from the "
            f"reconstructed model, whose heads are {list(heads)}."
        )
    realization = PortableModelRealization(
        state_sha256=state_sha256,
        execution_architecture_digest=architecture,
        dtype=_uniform_learned_dtype(model),
        head_inventory=heads,
    )
    return model, realization


def serialization_runtime_metadata() -> dict[str, Any]:
    """Representation-compatibility metadata, never scientific identity.

    A Torch/MACE/e3nn/Python change does not by itself invalidate a product.
    It forces a compatibility *decision* before consequential reuse, and this
    is the material that decision is taken against.
    """

    import platform
    import sys

    def _version(name: str) -> str | None:
        try:
            module = __import__(name)
        except Exception:  # noqa: BLE001 - absence is metadata, not failure
            return None
        return str(getattr(module, "__version__", "") or "") or None

    return {
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "torch": _version("torch"),
        "mace": _version("mace"),
        "e3nn": _version("e3nn"),
        "pickle_protocol": int(getattr(__import__("pickle"), "DEFAULT_PROTOCOL", 0)),
        "sys_platform": sys.platform,
    }


def current_runtime_compatibility_established(record: FinalProductionModelPublication) -> bool:
    """Whether the recorded serializer/runtime still proves the current loader.

    When it does, byte/SHA/state authentication is sufficient.  When it does
    not - a different Torch, MACE, e3nn or Python - the producer owes an actual
    load through the current supported loader before it may call the product
    reusable.  Status never performs that proof and must say so rather than
    pretend the mismatch was tested.
    """

    if record.serialization_format != SERIALIZATION_FORMAT_TORCH_FULL_MODEL:
        return False
    if record.serializer_identity != MODEL_SERIALIZER_IDENTITY:
        return False
    recorded = dict(record.serialization_runtime)
    current = serialization_runtime_metadata()
    for key in ("python", "torch", "mace", "e3nn"):
        if recorded.get(key) != current.get(key):
            return False
    return True


# ---------------------------------------------------------------------------
# Durable placement
# ---------------------------------------------------------------------------


def campaign_models_root(context: Any) -> Path:
    root = Path(context.paths.models)
    root.mkdir(parents=True, exist_ok=True)
    return root


@dataclass(frozen=True, slots=True)
class _PlacedArtifact:
    relative_path: str
    locator_token: str
    sha256: str
    size_bytes: int


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _serialize_portable_model(model: Any, destination: Path) -> None:
    import torch

    torch.save(model, destination)
    _fsync_file(destination)


def _verify_reloaded_product(
    path: Path,
    *,
    realization: PortableModelRealization,
    target_head_name: str,
) -> None:
    """Reload through the supported full-model loader and require exact equality."""

    import torch

    from .model_features import (
        mace_model_execution_architecture_digest,
        mace_model_state_digest,
        mace_model_state_dict_clone,
    )

    reloaded = torch.load(path, map_location="cpu", weights_only=False)
    try:
        if isinstance(reloaded, Mapping):
            raise ModelPublicationError(
                "A published production model must be a complete MACE model object, "
                "not a checkpoint dictionary or state dict."
            )
        if not hasattr(reloaded, "state_dict"):
            raise ModelPublicationError(
                "The reloaded published product is not a torch module."
            )
        _require_inference_mode(reloaded, where="after reload")
        state = mace_model_state_dict_clone(reloaded)
        if mace_model_state_digest(state) != realization.state_sha256:
            raise ModelPublicationError(
                "The reloaded published product does not reproduce the exact "
                "authenticated model state."
            )
        if mace_model_execution_architecture_digest(reloaded) != (
            realization.execution_architecture_digest
        ):
            raise ModelPublicationError(
                "The reloaded published product has a different execution architecture."
            )
        heads = tuple(str(value) for value in (getattr(reloaded, "heads", ()) or ()))
        if heads != realization.head_inventory:
            raise ModelPublicationError(
                f"The reloaded product's head inventory {list(heads)} differs from the "
                f"serialized model's {list(realization.head_inventory)}."
            )
        if heads and str(target_head_name) not in heads:
            raise ModelPublicationError(
                "The reloaded product does not expose the published target head."
            )
        if _uniform_learned_dtype(reloaded) != realization.dtype:
            raise ModelPublicationError(
                "The reloaded product does not carry the accepted learned-model dtype."
            )
    finally:
        del reloaded


def place_member_model(
    context: Any,
    *,
    model: Any,
    member_id: str,
    realization: PortableModelRealization,
    target_head_name: str,
    decision_relative_directory: str,
    reserve: "PublicationDiskReserve | None" = None,
) -> _PlacedArtifact:
    """Serialize, verify and durably publish one member model, create-once.

    The temp lives on the destination filesystem so the final placement is a
    link, not a copy, and so the reserve recheck below sees the real cost.
    Placement is ``os.link``: an immutable model artifact is never published
    through an overwrite-capable primitive, and an occupied locator is
    authenticated rather than clobbered.  A leaf that is occupied by different
    bytes yields to a *fresh* locator, which is what keeps a corrupted leaf
    from permanently wedging reclosure even when the rebuild reproduces the
    identical model SHA.
    """

    models_root = campaign_models_root(context)
    with open_publication_directory(
        models_root, decision_relative_directory, create=True
    ) as directory_fd:
        temporary_name = f".publish-{os.getpid()}-{fresh_locator_token()}.tmp"
        directory_path = models_root / decision_relative_directory
        temporary_path = directory_path / temporary_name
        try:
            _serialize_portable_model(model, temporary_path)
            _verify_reloaded_product(
                temporary_path,
                realization=realization,
                target_head_name=target_head_name,
            )
            observed = authenticate_descriptor_leaf(directory_fd, temporary_name)
            if reserve is not None:
                reserve.recheck_after_actual(observed.size_bytes)
            for _attempt in range(8):
                token = fresh_locator_token()
                final_name = model_artifact_basename(
                    member_id=member_id,
                    model_sha256=observed.sha256,
                    artifact_locator_token=token,
                )
                try:
                    place_immutable_file(directory_fd, temporary_name, final_name)
                except FileExistsError:
                    # An occupied locator is never overwritten.  Exact expected
                    # bytes could be reused, but a fresh token is both correct
                    # and strictly simpler than deserializing what is there.
                    continue
                return _PlacedArtifact(
                    relative_path=f"{decision_relative_directory}/{final_name}",
                    locator_token=token,
                    sha256=observed.sha256,
                    size_bytes=observed.size_bytes,
                )
            raise ModelPublicationError(
                "No fresh artifact locator could be claimed for the published model."
            )
        finally:
            # Only the private temp this attempt owns is ever removed.
            temporary_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Disk admission
# ---------------------------------------------------------------------------


@dataclass
class PublicationDiskReserve:
    """The campaign's configured free-space floor, applied to this write path.

    Publication does not become a second storage scheduler: it reuses the
    accepted ``[execution].minimum_free_disk_gib`` semantics and only asks
    whether *this* incremental write still leaves the configured reserve.  The
    preflight estimate is conservative, and because serialization is serial the
    real cost is rechecked once the actual bytes exist - an estimate that
    turned out low aborts before commit rather than being accepted as success.
    """

    destination: Path
    minimum_free_bytes: int
    remaining_members: int
    estimated_member_bytes: int

    def _free_bytes(self) -> int:
        usage = shutil.disk_usage(str(self.destination))
        return int(usage.free)

    def _require(self, needed: int, detail: str) -> None:
        free = self._free_bytes()
        if free - needed < self.minimum_free_bytes:
            raise ModelPublicationError(
                "Publishing the selected production model(s) would leave "
                f"{(free - needed) / 1024 ** 3:.2f} GiB free, below the configured "
                f"{self.minimum_free_bytes / 1024 ** 3:.2f} GiB reserve ({detail}). "
                "No pointer was changed and the previous current product is intact."
            )

    def admit_preflight(self) -> None:
        self._require(
            self.remaining_members * self.estimated_member_bytes,
            f"preflight estimate for {self.remaining_members} member(s)",
        )

    def recheck_after_actual(self, actual_bytes: int) -> None:
        """Recheck once this member's real serialized cost is known.

        The temp already lives on the destination filesystem and placement is a
        link, so those bytes are not double-counted; what is counted is the
        remaining members conservatively sized by the larger of the estimate
        and the member just observed.
        """

        self.remaining_members = max(0, self.remaining_members - 1)
        self.estimated_member_bytes = max(self.estimated_member_bytes, int(actual_bytes))
        self._require(
            self.remaining_members * self.estimated_member_bytes,
            f"actual-size recheck with {self.remaining_members} member(s) remaining",
        )


def build_disk_reserve(
    context: Any, *, member_count: int, estimated_member_bytes: int
) -> PublicationDiskReserve:
    from ._campaign_cli_core import _cfg

    gib = float(_cfg(context.cfg, "execution", "minimum_free_disk_gib", 20.0) or 0.0)
    return PublicationDiskReserve(
        destination=campaign_models_root(context),
        minimum_free_bytes=max(0, int(gib * 1024**3)),
        remaining_members=int(member_count),
        estimated_member_bytes=max(1, int(estimated_member_bytes)),
    )


def estimate_member_model_bytes(context: Any, decision: Any) -> int:
    """Conservative per-member estimate from authenticated checkpoint size."""

    largest = 0
    for evidence in decision.published_seed_evidence:
        checkpoint = (
            context.run_root(evidence.run_identity)
            / "checkpoints"
            / Path(evidence.checkpoint_relative_path).name
        )
        try:
            largest = max(largest, int(checkpoint.stat().st_size))
        except OSError:
            continue
    # A full model pickle carries the same tensors plus module structure.
    return max(64 * 1024 * 1024, 2 * largest)


__all__ = [
    "ModelPublicationError",
    "ModelRepresentationIncompatible",
    "PortableModelRealization",
    "PublicationDiskReserve",
    "build_disk_reserve",
    "campaign_models_root",
    "current_runtime_compatibility_established",
    "estimate_member_model_bytes",
    "evaluation_model_state_for",
    "place_member_model",
    "realize_portable_publication_model",
    "retire_provider",
    "selected_representative_provider",
    "serialization_runtime_metadata",
]


# ---------------------------------------------------------------------------
# Publication-set coordination
# ---------------------------------------------------------------------------

#: Internal P5 coordination namespace.  Deliberately *not* in the operator
#: models tree: a lock file under ``models/`` would look like a product.
MODEL_PUBLICATION_LOCK_DIRECTORY = "model-publication-locks"


@contextmanager
def model_publication_set_lock(context: Any, decision: Any) -> Iterator[None]:
    """One stable lock for the whole ordered committee of one decision.

    Full PyTorch model serialization is not byte-deterministic, so two
    concurrent builders of the same logical committee cannot converge by
    content address the way immutable JSON evidence does.  Per-member locks
    would let them interleave and assemble a mixed artifact set, so the lock is
    derived from the *decision* identity - known before any serialization -
    rather than from a model SHA that only exists afterwards.

    Lock order is fixed repository-wide and never acquired in reverse:

        decision/publication-set lock
            -> generation P5 publication barrier
                -> CampaignStore exclusive transaction
    """

    from .persistence import artifact_publication_lock
    from .post_selection_store import post_selection_root

    root = (
        post_selection_root(
            context.paths, context.selected.binding.campaign_generation
        )
        / MODEL_PUBLICATION_LOCK_DIRECTORY
    )
    root.mkdir(parents=True, exist_ok=True)
    with artifact_publication_lock(root / str(decision.content_digest)):
        yield


def authenticate_model_publication_artifacts(
    context: Any, record: FinalProductionModelPublication
) -> None:
    """Prove every current member's confined bytes, without deserializing them.

    This is the status-safe authentication: descriptor-confined, no-follow,
    regular-file, recorded size and streaming SHA-256.  It does not
    ``torch.load`` anything, so an observer never reconstructs MACE, and a
    missing, wrong-kind, wrong-size or mutated product is reported rather than
    executed.
    """

    models_root = campaign_models_root(context)
    for member in record.members:
        authenticate_model_artifact(
            models_root,
            member.model_relative_path,
            expected_sha256=member.model_sha256,
            expected_size_bytes=member.model_size_bytes,
        )


def prove_existing_representation_reusable(
    context: Any, record: FinalProductionModelPublication, decision: Any
) -> None:
    """Load the existing product under the current loader and prove it is the state.

    Reached when the recorded serializer/runtime no longer positively proves
    the current loader boundary, or when the predecessor executable changed.  A
    byte/SHA match alone cannot answer "does this still load here?", and
    pretending it can is how a campaign discovers an unusable product at
    release time.

    Raises :class:`ModelRepresentationIncompatible` when the old pickle cannot
    be loaded - the caller may then publish a fresh representation from the
    same selected checkpoint with zero TRAIN2/EVAL2.  A *scientific*
    disagreement, where the provider reconstructs a different state or
    architecture, raises :class:`ModelPublicationError` instead: that is
    lineage corruption and is never laundered as a serialization repair.
    """

    import torch

    from .model_features import (
        mace_model_execution_architecture_digest,
        mace_model_state_digest,
        mace_model_state_dict_clone,
    )
    from .post_selection_execution import PostSelectionRunEvidence

    models_root = campaign_models_root(context)
    with tempfile.TemporaryDirectory(prefix="mdstats-p5-model-compat-") as scratch:
        for member, evidence in zip(
            record.members, decision.published_seed_evidence, strict=True
        ):
            run_evidence = context.evidence_store.get(
                evidence.run_evidence_digest, PostSelectionRunEvidence.from_dict
            )
            with stage_authenticated_model(
                models_root,
                member.model_relative_path,
                expected_sha256=member.model_sha256,
                expected_size_bytes=member.model_size_bytes,
                scratch_directory=Path(scratch) / member.member_id,
            ) as staged:
                try:
                    reloaded = torch.load(staged, map_location="cpu", weights_only=False)
                except Exception as exc:  # noqa: BLE001 - loader boundary probe
                    raise ModelRepresentationIncompatible(
                        f"The published model for {member.member_id} cannot be loaded "
                        f"by the current supported loader: {exc}"
                    ) from exc
                try:
                    reloaded_state = mace_model_state_digest(
                        mace_model_state_dict_clone(reloaded)
                    )
                    reloaded_architecture = mace_model_execution_architecture_digest(
                        reloaded
                    )
                    reloaded_heads = tuple(
                        str(value) for value in (getattr(reloaded, "heads", ()) or ())
                    )
                    reloaded_dtype = _uniform_learned_dtype(reloaded)
                    _require_inference_mode(
                        reloaded, where="in the existing published product"
                    )
                finally:
                    del reloaded
            with selected_representative_provider(
                context,
                run_identity=evidence.run_identity,
                checkpoint_relative_path=evidence.checkpoint_relative_path,
                representative_checkpoint_sha256=(
                    evidence.representative_checkpoint_sha256
                ),
                materialization_digest=run_evidence.materialization_digest,
                optimizer_seed=evidence.optimizer_seed,
                allow_forward_override=False,
            ) as (provider, evaluated_digest):
                model, realization = realize_portable_publication_model(
                    provider, target_head_name=decision.target_head_name
                )
                del model
                scientific = {
                    "evaluated_model_state_digest": (
                        member.evaluated_model_state_digest,
                        evaluated_digest,
                    ),
                    "model_state_sha256": (
                        member.model_state_sha256,
                        realization.state_sha256,
                    ),
                    "model_execution_architecture_digest": (
                        member.model_execution_architecture_digest,
                        realization.execution_architecture_digest,
                    ),
                    "model_dtype": (member.model_dtype, realization.dtype),
                }
                drifted = sorted(
                    name for name, (left, right) in scientific.items() if left != right
                )
                if drifted:
                    raise ModelPublicationError(
                        f"Reconstructing member {member.member_id} from its exact "
                        f"selected checkpoint no longer reproduces {drifted}. This is "
                        "an upstream scientific/provider change, not a serialization "
                        "repair; the product fails closed."
                    )
            representation = {
                "model_state_sha256": (reloaded_state, realization.state_sha256),
                "model_execution_architecture_digest": (
                    reloaded_architecture,
                    realization.execution_architecture_digest,
                ),
                "model_dtype": (reloaded_dtype, realization.dtype),
            }
            bad = sorted(
                name for name, (left, right) in representation.items() if left != right
            )
            if bad or (
                reloaded_heads and str(decision.target_head_name) not in reloaded_heads
            ):
                raise ModelRepresentationIncompatible(
                    f"The existing published model for {member.member_id} loads but "
                    f"does not equal the selected provider realization ({bad or 'head'}); "
                    "a fresh representation is required."
                )


def materialize_model_publication(
    context: Any, decision: Any
) -> FinalProductionModelPublication:
    """Build the complete ordered artifact set and its subordinate record.

    Members are processed serially in canonical decision order so exactly one
    provider is resident at a time and the disk reserve can be rechecked
    against real bytes.  Every provider is retired in the shared reconstruction
    owner's ``finally``, on success and on failure alike.
    """

    from .post_selection_execution import PostSelectionRunEvidence

    ordered = decision.published_seed_evidence
    reserve = build_disk_reserve(
        context,
        member_count=len(ordered),
        estimated_member_bytes=estimate_member_model_bytes(context, decision),
    )
    reserve.admit_preflight()
    relative_directory = decision_directory_relative_path(
        context.selected.binding.campaign_generation,
        context.selected.n_selected,
        decision.content_digest,
    )
    members: list[PublishedModelMember] = []
    for evidence in ordered:
        run_evidence = context.evidence_store.get(
            evidence.run_evidence_digest, PostSelectionRunEvidence.from_dict
        )
        if run_evidence.training_root_identity != evidence.run_identity:
            raise ModelPublicationError(
                f"Member {evidence.member_id} run evidence does not name the training "
                "root the decision published."
            )
        if run_evidence.representative_checkpoint_sha256 != (
            evidence.representative_checkpoint_sha256
        ):
            raise ModelPublicationError(
                f"Member {evidence.member_id} run evidence does not bind its own "
                "representative checkpoint."
            )
        with selected_representative_provider(
            context,
            run_identity=evidence.run_identity,
            checkpoint_relative_path=evidence.checkpoint_relative_path,
            representative_checkpoint_sha256=evidence.representative_checkpoint_sha256,
            materialization_digest=run_evidence.materialization_digest,
            optimizer_seed=evidence.optimizer_seed,
            allow_forward_override=False,
        ) as (provider, evaluated_digest):
            model, realization = realize_portable_publication_model(
                provider, target_head_name=decision.target_head_name
            )
            placed = place_member_model(
                context,
                model=model,
                member_id=evidence.member_id,
                realization=realization,
                target_head_name=decision.target_head_name,
                decision_relative_directory=relative_directory,
                reserve=reserve,
            )
            del model
        members.append(
            PublishedModelMember(
                member_id=evidence.member_id,
                optimizer_seed=evidence.optimizer_seed,
                run_identity=evidence.run_identity,
                representative_checkpoint_relative_path=(
                    evidence.checkpoint_relative_path
                ),
                representative_checkpoint_sha256=(
                    evidence.representative_checkpoint_sha256
                ),
                evaluation_model_state=evaluation_model_state_for(
                    context, optimizer_seed=evidence.optimizer_seed
                ),
                evaluated_model_state_digest=evaluated_digest,
                model_execution_architecture_digest=(
                    realization.execution_architecture_digest
                ),
                model_state_sha256=realization.state_sha256,
                model_dtype=realization.dtype,
                artifact_locator_token=placed.locator_token,
                model_relative_path=placed.relative_path,
                model_sha256=placed.sha256,
                model_size_bytes=placed.size_bytes,
            )
        )
    # One last reserve observation with the complete immutable set durable, so
    # a shortfall aborts before any pointer moves rather than after.
    reserve.remaining_members = 0
    reserve.recheck_after_actual(0)
    record = FinalProductionModelPublication(
        selected_binding_digest=decision.binding.content_digest,
        final_publication_decision_digest=decision.content_digest,
        final_publication_member_digest=decision.member_digest,
        target_head_name=decision.target_head_name,
        members=tuple(members),
        serialization_format=SERIALIZATION_FORMAT_TORCH_FULL_MODEL,
        serializer_identity=MODEL_SERIALIZER_IDENTITY,
        serialization_runtime=serialization_runtime_metadata(),
        published_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    validate_model_publication_against_decision(record, decision)
    return record


def write_publication_projection(
    context: Any,
    *,
    decision: Any,
    record: FinalProductionModelPublication,
    reclosure: Any,
) -> None:
    """Refresh the non-authoritative operator projection, after authoritative commit.

    ``publication.json`` is a convenience locator and never participates in a
    currentness decision.  It is written relative to the authenticated
    ``N_<size>`` directory descriptor - a planted symlink at the projection
    name or above it cannot redirect the write - and only after the three
    product pointers are committed, while the caller still holds the generation
    barrier.  A crash between commit and refresh leaves the projection stale or
    absent; status still resolves the canonical records and reports the right
    product, and a later ``train-production`` repairs the projection alone.
    """

    models_root = campaign_models_root(context)
    relative = production_models_relative_root(
        context.selected.binding.campaign_generation, context.selected.n_selected
    )
    payload = {
        "schema": PUBLICATION_PROJECTION_SCHEMA,
        "authority": "non_authoritative_operator_projection",
        "n_selected": int(context.selected.n_selected),
        "campaign_generation": int(context.selected.binding.campaign_generation),
        "selected_binding_digest": decision.binding.content_digest,
        "final_publication_decision_digest": decision.content_digest,
        "final_publication_member_digest": decision.member_digest,
        "model_publication_digest": record.content_digest,
        "model_artifact_set_digest": record.model_artifact_set_digest,
        "predecessor_reclosure_digest": str(reclosure.content_digest),
        "target_head_name": record.target_head_name,
        "committee_policy": decision.committee_policy,
        "members": [
            {
                "member_id": member.member_id,
                "optimizer_seed": member.optimizer_seed,
                "model_relative_path": member.model_relative_path,
                "model_sha256": member.model_sha256,
                "model_size_bytes": member.model_size_bytes,
                "representative_checkpoint_sha256": (
                    member.representative_checkpoint_sha256
                ),
                "evaluation_model_state": member.evaluation_model_state,
            }
            for member in record.members
        ],
        "published_at": record.published_at,
    }
    temporary_name = f".{PUBLICATION_PROJECTION_FILENAME}.{os.getpid()}.tmp"
    with open_publication_directory(models_root, relative, create=True) as directory_fd:
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
        handle = os.open(temporary_name, flags, 0o644, dir_fd=directory_fd)
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(canonical_json(payload))
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            try:
                os.unlink(temporary_name, dir_fd=directory_fd)
            except OSError:
                pass
            raise
        try:
            os.replace(
                temporary_name,
                PUBLICATION_PROJECTION_FILENAME,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
            )
            os.fsync(directory_fd)
        except BaseException:
            try:
                os.unlink(temporary_name, dir_fd=directory_fd)
            except OSError:
                pass
            raise


def publish_final_production_model_products(
    context: Any,
    campaign_store: Any,
    decision: Any,
    *,
    existing_reclosure: Any | None = None,
    existing_model_publication: FinalProductionModelPublication | None = None,
) -> tuple[FinalProductionModelPublication, Any]:
    """Materialize (or reuse) the product set and commit the three pointers atomically.

    The expensive work - reconstruction and serialization - happens under the
    publication-set lock but outside the generation barrier and outside any
    SQLite transaction.  Only the object-to-pointer window is guarded by the
    barrier, and only the three-row pointer change is inside the transaction.

    The three pointers move together or not at all.  A crash after advancing
    the model/reclosure pointers but before ``FINAL_PUBLICATION`` would
    otherwise strand the previous current product behind a hybrid pointer set,
    which no observer could describe truthfully.
    """

    from .post_selection_reclosure import build_predecessor_reclosure
    from .post_selection_store import (
        POINTER_FINAL_MODEL_PUBLICATION,
        POINTER_FINAL_PUBLICATION,
        POINTER_PREDECESSOR_RECLOSURE,
        post_selection_publication_barrier,
        publish_current_post_selection_pointer_set,
    )

    record = existing_model_publication
    if record is None:
        record = materialize_model_publication(context, decision)
    else:
        validate_model_publication_against_decision(record, decision)
        authenticate_model_publication_artifacts(context, record)
    reclosure = existing_reclosure
    if reclosure is None:
        reclosure = build_predecessor_reclosure(context, decision)
    store = context.evidence_store
    with post_selection_publication_barrier(
        context.paths, context.selected.binding.campaign_generation
    ):
        store.put(decision)
        store.put(record)
        store.put(reclosure)
        publish_current_post_selection_pointer_set(
            campaign_store,
            binding=context.selected.binding,
            rows={
                POINTER_FINAL_MODEL_PUBLICATION: record.content_digest,
                POINTER_PREDECESSOR_RECLOSURE: reclosure.content_digest,
                POINTER_FINAL_PUBLICATION: decision.content_digest,
            },
        )
        # Still under the generation barrier: an older concurrent publisher
        # cannot overwrite the projection after a newer publication became
        # authoritative.
        try:
            write_publication_projection(
                context, decision=decision, record=record, reclosure=reclosure
            )
        except (OSError, ModelArtifactTrustError) as exc:
            # The product is already authoritative and current.  A projection
            # failure is repairable by a later `train-production` and is never
            # scientific product loss.
            print(
                "[P5 publication] the operator projection could not be refreshed "
                f"({exc}); the published product remains authoritative and current",
                flush=True,
            )
    return record, reclosure


def resolve_current_final_production_model_publication(
    context: Any, decision: Any
) -> FinalProductionModelPublication | None:
    """Resolve the current subordinate product record for an exact decision."""

    from .post_selection_store import (
        POINTER_FINAL_MODEL_PUBLICATION,
        resolve_current_post_selection_record,
    )

    record = resolve_current_post_selection_record(
        context.store,
        context.paths,
        context.selected,
        kind=POINTER_FINAL_MODEL_PUBLICATION,
        deserializer=FinalProductionModelPublication.from_dict,
    )
    if record is None:
        return None
    validate_model_publication_against_decision(record, decision)
    return record


__all__ += [
    "MODEL_PUBLICATION_LOCK_DIRECTORY",
    "authenticate_model_publication_artifacts",
    "materialize_model_publication",
    "model_publication_set_lock",
    "prove_existing_representation_reusable",
    "publish_final_production_model_products",
    "resolve_current_final_production_model_publication",
    "write_publication_projection",
]
