"""DATA6 orchestration for universal/LTA structural and model evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, TYPE_CHECKING

from .progress_timing import format_progress_fraction
from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .difficulty import (
    BlindedEvaluationPredictionCatalog,
    TrainingDifficultyFeatureCatalog,
    build_model_evidence_catalogs,
)
if TYPE_CHECKING:
    from .lta_selection import LtaSelectionFeatureCatalog, LtaSelectionPolicy
from .model_features import (
    AtomicModelPrediction,
    AtomicModelProvider,
    MaceDescriptorManifest,
    MaceDescriptorPolicy,
    ModelCheckpointIdentity,
    build_mace_descriptor_manifest,
)
from .partition import OuterRole
from .production_model_sweep import (
    AtomicModelPredictionManifest,
    Data6ModelSweepArtifacts,
    Data6ModelSweepPlan,
)
from .profile_extensions import (
    ProfileFeatureCatalog, ProfileFeatureStage, find_profile_feature,
    normalize_profile_feature_catalogs, wrap_lta_selection_features,
)
from .phase_geometry_profiles import (
    PhaseGeometrySelectionPlan,
    derive_phase_geometry_selection_plan,
    universal_structural_policy_from_plan,
)
from .structural_selection import (
    AtomGroupMembershipProvider,
    StructuralSelectionProvider,
    UniversalStructuralFeatureCatalog,
    UniversalStructuralSelectionPolicy,
    UniversalStructuralSelectionProvider,
)

DATA6_POLICY_SCHEMA = "mdstats.data6-policy.v2"
DATA6_POLICY_LEGACY_SCHEMA = "mdstats.data6-policy.v1"
DATA6_FEATURE_BUNDLE_SCHEMA = "mdstats.data6-feature-bundle.v5"
DATA6_FEATURE_BUNDLE_V4_SCHEMA = "mdstats.data6-feature-bundle.v4"
DATA6_FEATURE_BUNDLE_V3_SCHEMA = "mdstats.data6-feature-bundle.v3"
DATA6_FEATURE_BUNDLE_V2_SCHEMA = "mdstats.data6-feature-bundle.v2"
DATA6_FEATURE_BUNDLE_LEGACY_SCHEMA = "mdstats.data6-feature-bundle.v1"
DATA6_POLICY_VERSION = "mdstats.mlff-data6.bundle.2026-07.v2"
MLFF_DATA6_PARSER_VERSION = "0.20.53a0"
MLFF_DATA6_V4_PARSER_VERSION = "0.20.50a0"
MLFF_DATA6_V3_PARSER_VERSION = "0.20.49a0"
MLFF_DATA6_V2_PARSER_VERSION = "0.20.48a0"
MLFF_DATA6_LEGACY_PARSER_VERSION = "0.20.34a0"



def _decode_legacy_lta_selection_features(payload: Any) -> "LtaSelectionFeatureCatalog | None":
    if payload is None:
        return None
    from .lta_selection import LtaSelectionFeatureCatalog

    return LtaSelectionFeatureCatalog.from_dict(payload)


@dataclass(frozen=True, slots=True)
class Data6Policy:
    build_universal_structural_features: bool = False
    build_lta_selection_features: bool = False
    build_mace_descriptors: bool = False
    build_training_difficulty: bool = False
    build_blinded_predictions: bool = False
    universal_structural_roles: tuple[str, ...] = (OuterRole.DEVELOPMENT.value,)
    descriptor_roles: tuple[str, ...] = (
        OuterRole.DEVELOPMENT.value,
        OuterRole.OUTER_MONITOR.value,
        OuterRole.UNCERTAINTY_CALIBRATION.value,
    )
    policy_version: str = DATA6_POLICY_VERSION

    def __post_init__(self) -> None:
        universal_roles = tuple(sorted(set(OuterRole(v).value for v in self.universal_structural_roles)))
        descriptor_roles = tuple(sorted(set(OuterRole(v).value for v in self.descriptor_roles)))
        forbidden = {
            OuterRole.LOCKED_INTERPOLATION_TEST.value,
            OuterRole.PURGED.value,
            OuterRole.EXCLUDED.value,
        }
        if set(universal_roles) & forbidden:
            raise TrainingDataInputError("Universal structural features cannot materialize sealed or provenance-only roles.")
        if set(descriptor_roles) & forbidden:
            raise TrainingDataInputError("DATA6 descriptors cannot materialize sealed or provenance-only roles.")
        if self.build_universal_structural_features and not universal_roles:
            raise TrainingDataInputError("Universal structural features require at least one admissible role.")
        if not self.policy_version.strip():
            raise TrainingDataInputError("policy_version must be non-empty.")
        object.__setattr__(self, "universal_structural_roles", universal_roles)
        object.__setattr__(self, "descriptor_roles", descriptor_roles)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": DATA6_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "build_universal_structural_features": self.build_universal_structural_features,
            "build_lta_selection_features": self.build_lta_selection_features,
            "build_mace_descriptors": self.build_mace_descriptors,
            "build_training_difficulty": self.build_training_difficulty,
            "build_blinded_predictions": self.build_blinded_predictions,
            "universal_structural_roles": list(self.universal_structural_roles),
            "descriptor_roles": list(self.descriptor_roles),
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Data6Policy":
        schema = payload.get("schema")
        if schema not in {DATA6_POLICY_SCHEMA, DATA6_POLICY_LEGACY_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported DATA6 policy schema.")
        if schema == DATA6_POLICY_LEGACY_SCHEMA and payload.get("policy_digest") not in (
            None,
            digest({key: value for key, value in payload.items() if key != "policy_digest"}),
        ):
            raise TrainingDataSerializationError("Legacy DATA6 policy digest mismatch.")
        result = cls(
            build_universal_structural_features=bool(payload.get("build_universal_structural_features", False)),
            build_lta_selection_features=bool(payload["build_lta_selection_features"]),
            build_mace_descriptors=bool(payload["build_mace_descriptors"]),
            build_training_difficulty=bool(payload["build_training_difficulty"]),
            build_blinded_predictions=bool(payload["build_blinded_predictions"]),
            universal_structural_roles=tuple(str(v) for v in payload.get("universal_structural_roles", (OuterRole.DEVELOPMENT.value,))),
            descriptor_roles=tuple(str(v) for v in payload["descriptor_roles"]),
            policy_version=(
                DATA6_POLICY_VERSION if schema == DATA6_POLICY_LEGACY_SCHEMA else str(payload["policy_version"])
            ),
        )
        if schema == DATA6_POLICY_SCHEMA and payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("DATA6 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class Data6FeatureBundle:
    dataset_id: str
    source_catalog_digest: str
    frame_catalog_digest: str
    data4_bundle_digest: str
    data5_bundle_digest: str
    policy: Data6Policy
    lta_selection_features: "LtaSelectionFeatureCatalog | None"
    checkpoint_identity: ModelCheckpointIdentity | None
    mace_descriptor_manifest: MaceDescriptorManifest | None
    training_difficulty_catalogs: tuple[TrainingDifficultyFeatureCatalog, ...]
    blinded_prediction_catalogs: tuple[BlindedEvaluationPredictionCatalog, ...]
    model_sweep_plan: Data6ModelSweepPlan | None = None
    prediction_manifest: AtomicModelPredictionManifest | None = None
    model_sweep_checkpoint_digest: str | None = None
    universal_structural_features: tuple[UniversalStructuralFeatureCatalog, ...] = ()
    phase_geometry_profile_plan: PhaseGeometrySelectionPlan | None = None
    profile_selection_features: tuple[ProfileFeatureCatalog, ...] = ()
    notes: tuple[str, ...] = ()
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)
    _training_difficulty_by_domain_key: dict[tuple[str, str, int | None], TrainingDifficultyFeatureCatalog] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _blinded_prediction_by_domain_key: dict[tuple[str, str, int | None], BlindedEvaluationPredictionCatalog] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in (
            "source_catalog_digest", "frame_catalog_digest", "data4_bundle_digest",
            "data5_bundle_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        structural = tuple(sorted(self.universal_structural_features, key=lambda item: item.provider_identity.content_digest))
        if len({item.provider_identity.content_digest for item in structural}) != len(structural):
            raise TrainingDataInputError("DATA6 structural provider catalogs must be unique.")
        for catalog in structural:
            if catalog.frame_catalog_digest != self.frame_catalog_digest:
                raise TrainingDataInputError("DATA6 structural feature/frame lineage mismatch.")
            if catalog.data4_bundle_digest != self.data4_bundle_digest:
                raise TrainingDataInputError("DATA6 structural feature/DATA4 lineage mismatch.")
        object.__setattr__(self, "universal_structural_features", structural)
        if self.phase_geometry_profile_plan is not None:
            for catalog in structural:
                if catalog.policy.phase_geometry_plan_digest != self.phase_geometry_profile_plan.content_digest:
                    raise TrainingDataInputError("DATA6 structural catalog/phase-geometry plan mismatch.")
                if catalog.material_profile_contracts_digest != self.phase_geometry_profile_plan.material_profile_contracts_digest:
                    raise TrainingDataInputError("DATA6 phase-geometry plan/material-profile lineage mismatch.")
        elif any(catalog.policy.phase_geometry_plan_digest is not None for catalog in structural):
            raise TrainingDataInputError("DATA6 structural catalogs declare a phase/geometry plan that is absent from the bundle.")
        profile_catalogs = tuple(self.profile_selection_features)
        lta_catalog = self.lta_selection_features
        existing_lta = find_profile_feature(profile_catalogs, "lta")
        if lta_catalog is None and existing_lta is not None:
            # Standalone/public JSON embeds the provider payload. Resolve it
            # once, then canonicalize the in-memory DATA6 reference to a
            # digest-only wrapper so the scientific catalog is not duplicated.
            lta_catalog = existing_lta.as_lta_selection()
            object.__setattr__(self, "lta_selection_features", lta_catalog)
        if lta_catalog is not None:
            if lta_catalog.frame_catalog_digest != self.frame_catalog_digest:
                raise TrainingDataInputError("DATA6 LTA feature/frame lineage mismatch.")
            if lta_catalog.data4_bundle_digest != self.data4_bundle_digest:
                raise TrainingDataInputError("DATA6 LTA feature/DATA4 lineage mismatch.")
            if (
                existing_lta is not None
                and existing_lta.scientific_payload_digest
                != lta_catalog.content_digest
            ):
                raise TrainingDataInputError(
                    "Legacy and generic LTA selection feature evidence disagree."
                )
            canonical_lta = wrap_lta_selection_features(
                lta_catalog,
                data4_bundle_digest=self.data4_bundle_digest,
                embed_payload=False,
            )
            profile_catalogs = tuple(
                item for item in profile_catalogs if item.extension_id != "lta"
            ) + (canonical_lta,)
        # DATA6 carries the derived plan rather than the full contracts.  The
        # profile-extension activation was already checked in DATA4; validate
        # stage and lineage here without reinterpreting the extension payload.
        if profile_catalogs:
            profile_catalogs = tuple(sorted(profile_catalogs, key=lambda item: (item.extension_id, item.provider_identity.content_digest)))
            if len({(item.extension_id, item.provider_identity.content_digest) for item in profile_catalogs}) != len(profile_catalogs):
                raise TrainingDataInputError("DATA6 profile selection catalogs must be unique.")
            for catalog in profile_catalogs:
                if catalog.stage is not ProfileFeatureStage.SELECTION:
                    raise TrainingDataInputError("DATA6 received a non-selection profile feature catalog.")
                if catalog.frame_catalog_digest != self.frame_catalog_digest:
                    raise TrainingDataInputError("DATA6 profile selection feature/frame lineage mismatch.")
                if catalog.parent_bundle_digest != self.data4_bundle_digest:
                    raise TrainingDataInputError("DATA6 profile selection feature/DATA4 lineage mismatch.")
            object.__setattr__(self, "profile_selection_features", profile_catalogs)
        if self.model_sweep_checkpoint_digest is not None:
            object.__setattr__(self, "model_sweep_checkpoint_digest", validate_digest(self.model_sweep_checkpoint_digest, name="model_sweep_checkpoint_digest"))
        has_model_artifacts = (
            self.mace_descriptor_manifest is not None
            or self.prediction_manifest is not None
            or self.model_sweep_plan is not None
            or bool(self.training_difficulty_catalogs)
            or bool(self.blinded_prediction_catalogs)
        )
        if (self.checkpoint_identity is None) == has_model_artifacts:
            raise TrainingDataInputError("DATA6 model artifacts require one checkpoint identity, and model-free bundles must not declare one.")
        if self.mace_descriptor_manifest is not None:
            if self.checkpoint_identity is None or self.mace_descriptor_manifest.checkpoint_identity.content_digest != self.checkpoint_identity.content_digest:
                raise TrainingDataInputError("DATA6 descriptor checkpoint mismatch.")
            if self.mace_descriptor_manifest.frame_catalog_digest != self.frame_catalog_digest or self.mace_descriptor_manifest.data5_bundle_digest != self.data5_bundle_digest:
                raise TrainingDataInputError("DATA6 descriptor lineage mismatch.")
            if self.model_sweep_plan is not None and tuple(item.frame_uid for item in self.mace_descriptor_manifest.records) != self.model_sweep_plan.descriptor_frame_uids:
                raise TrainingDataInputError("DATA6 descriptor manifest does not realize the exact model-sweep descriptor set.")
        if self.model_sweep_plan is not None:
            if self.model_sweep_plan.frame_catalog_digest != self.frame_catalog_digest or self.model_sweep_plan.data5_bundle_digest != self.data5_bundle_digest:
                raise TrainingDataInputError("DATA6 model-sweep plan lineage mismatch.")
            if self.model_sweep_plan.data6_policy_digest != self.policy.policy_digest:
                raise TrainingDataInputError("DATA6 model-sweep plan/policy mismatch.")
            if self.checkpoint_identity is None or self.model_sweep_plan.checkpoint_identity.content_digest != self.checkpoint_identity.content_digest:
                raise TrainingDataInputError("DATA6 model-sweep plan/checkpoint mismatch.")
            if self.model_sweep_checkpoint_digest is None:
                raise TrainingDataInputError("DATA6 model-sweep plan requires checkpoint evidence.")
        elif self.model_sweep_checkpoint_digest is not None or self.prediction_manifest is not None:
            raise TrainingDataInputError("DATA6 sweep checkpoint/prediction evidence requires a model-sweep plan.")
        if self.prediction_manifest is not None:
            if self.checkpoint_identity is None or self.prediction_manifest.checkpoint_identity.content_digest != self.checkpoint_identity.content_digest:
                raise TrainingDataInputError("DATA6 prediction-manifest checkpoint mismatch.")
            if self.prediction_manifest.frame_catalog_digest != self.frame_catalog_digest or self.prediction_manifest.data5_bundle_digest != self.data5_bundle_digest:
                raise TrainingDataInputError("DATA6 prediction-manifest lineage mismatch.")
            if self.model_sweep_plan is None or tuple(item.frame_uid for item in self.prediction_manifest.records) != self.model_sweep_plan.prediction_frame_uids:
                raise TrainingDataInputError("DATA6 prediction manifest does not realize the exact model-sweep prediction set.")
        difficulty = tuple(sorted(self.training_difficulty_catalogs, key=lambda item: item.domain.content_digest))
        blinded = tuple(sorted(self.blinded_prediction_catalogs, key=lambda item: item.domain.content_digest))
        for catalog in (*difficulty, *blinded):
            if catalog.frame_catalog_digest != self.frame_catalog_digest:
                raise TrainingDataInputError("DATA6 prediction catalog/frame lineage mismatch.")
            if self.checkpoint_identity is None or catalog.checkpoint_identity.content_digest != self.checkpoint_identity.content_digest:
                raise TrainingDataInputError("DATA6 prediction checkpoint mismatch.")
        object.__setattr__(self, "training_difficulty_catalogs", difficulty)
        object.__setattr__(self, "blinded_prediction_catalogs", blinded)
        object.__setattr__(
            self,
            "_training_difficulty_by_domain_key",
            {
                self._domain_key(item.domain): item
                for item in difficulty
            },
        )
        object.__setattr__(
            self,
            "_blinded_prediction_by_domain_key",
            {
                self._domain_key(item.domain): item
                for item in blinded
            },
        )
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))

    @staticmethod
    def _domain_key(domain: Any) -> tuple[str, str, int | None]:
        kind = getattr(domain.kind, "value", domain.kind)
        return (str(domain.label_domain_id), str(kind), domain.fold_index)

    def training_difficulty_for_domain(self, domain: Any) -> TrainingDifficultyFeatureCatalog | None:
        """Return matching training-difficulty evidence in O(1)."""

        return self._training_difficulty_by_domain_key.get(self._domain_key(domain))

    def blinded_prediction_for_domain(self, domain: Any) -> BlindedEvaluationPredictionCatalog | None:
        """Return matching blinded prediction evidence in O(1)."""

        return self._blinded_prediction_by_domain_key.get(self._domain_key(domain))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": DATA6_FEATURE_BUNDLE_SCHEMA,
            "parser_version": MLFF_DATA6_PARSER_VERSION,
            "dataset_id": self.dataset_id,
            "source_catalog_digest": self.source_catalog_digest,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data4_bundle_digest": self.data4_bundle_digest,
            "data5_bundle_digest": self.data5_bundle_digest,
            "policy": self.policy.to_dict(),
            "universal_structural_features": [item.to_dict() for item in self.universal_structural_features],
            "phase_geometry_profile_plan": None if self.phase_geometry_profile_plan is None else self.phase_geometry_profile_plan.to_dict(),
            "profile_selection_features": [
                (
                    wrap_lta_selection_features(
                        self.lta_selection_features,
                        data4_bundle_digest=self.data4_bundle_digest,
                        embed_payload=True,
                    ).to_dict()
                    if (
                        item.extension_id == "lta"
                        and not item.payload_embedded
                        and self.lta_selection_features is not None
                    )
                    else item.to_dict()
                )
                for item in self.profile_selection_features
            ],
            "checkpoint_identity": None if self.checkpoint_identity is None else self.checkpoint_identity.to_dict(),
            "mace_descriptor_manifest": None if self.mace_descriptor_manifest is None else self.mace_descriptor_manifest.to_dict(),
            "model_sweep_plan": None if self.model_sweep_plan is None else self.model_sweep_plan.to_dict(),
            "prediction_manifest": None if self.prediction_manifest is None else self.prediction_manifest.to_dict(),
            "model_sweep_checkpoint_digest": self.model_sweep_checkpoint_digest,
            "training_difficulty_catalogs": [item.to_dict() for item in self.training_difficulty_catalogs],
            "blinded_prediction_catalogs": [item.to_dict() for item in self.blinded_prediction_catalogs],
            "notes": list(self.notes),
        }

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": DATA6_FEATURE_BUNDLE_SCHEMA,
            "parser_version": MLFF_DATA6_PARSER_VERSION,
            "dataset_id": self.dataset_id,
            "source_catalog_digest": self.source_catalog_digest,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data4_bundle_digest": self.data4_bundle_digest,
            "data5_bundle_digest": self.data5_bundle_digest,
            "policy_digest": self.policy.policy_digest,
            "universal_structural_feature_digests": [item.content_digest for item in self.universal_structural_features],
            "phase_geometry_profile_plan_digest": None if self.phase_geometry_profile_plan is None else self.phase_geometry_profile_plan.content_digest,
            "profile_selection_feature_digests": [item.content_digest for item in self.profile_selection_features],
            "checkpoint_identity_digest": None if self.checkpoint_identity is None else self.checkpoint_identity.content_digest,
            "mace_descriptor_manifest_digest": None if self.mace_descriptor_manifest is None else self.mace_descriptor_manifest.content_digest,
            "model_sweep_plan_digest": None if self.model_sweep_plan is None else self.model_sweep_plan.content_digest,
            "prediction_manifest_digest": None if self.prediction_manifest is None else self.prediction_manifest.content_digest,
            "model_sweep_checkpoint_digest": self.model_sweep_checkpoint_digest,
            "training_difficulty_catalog_digests": [item.content_digest for item in self.training_difficulty_catalogs],
            "blinded_prediction_catalog_digests": [item.content_digest for item in self.blinded_prediction_catalogs],
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        value = self._content_digest_cache or digest(self._digest_payload())
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Data6FeatureBundle":
        schema = payload.get("schema")
        if schema not in {DATA6_FEATURE_BUNDLE_SCHEMA, DATA6_FEATURE_BUNDLE_V4_SCHEMA, DATA6_FEATURE_BUNDLE_V3_SCHEMA, DATA6_FEATURE_BUNDLE_V2_SCHEMA, DATA6_FEATURE_BUNDLE_LEGACY_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported DATA6 feature-bundle schema.")
        parser_version = payload.get("parser_version")
        if parser_version not in (None, MLFF_DATA6_PARSER_VERSION, MLFF_DATA6_V4_PARSER_VERSION, MLFF_DATA6_V3_PARSER_VERSION, MLFF_DATA6_V2_PARSER_VERSION, MLFF_DATA6_LEGACY_PARSER_VERSION):
            raise TrainingDataSerializationError("Unsupported DATA6 parser version.")
        if schema == DATA6_FEATURE_BUNDLE_LEGACY_SCHEMA and payload.get("content_digest") not in (
            None,
            digest({key: value for key, value in payload.items() if key != "content_digest"}),
        ):
            raise TrainingDataSerializationError("Legacy DATA6 feature-bundle digest mismatch.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            source_catalog_digest=str(payload["source_catalog_digest"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            data4_bundle_digest=str(payload["data4_bundle_digest"]),
            data5_bundle_digest=str(payload["data5_bundle_digest"]),
            policy=Data6Policy.from_dict(payload["policy"]),
            universal_structural_features=tuple(
                UniversalStructuralFeatureCatalog.from_dict(item)
                for item in payload.get("universal_structural_features", ())
            ),
            phase_geometry_profile_plan=None if payload.get("phase_geometry_profile_plan") is None else PhaseGeometrySelectionPlan.from_dict(payload["phase_geometry_profile_plan"]),
            lta_selection_features=_decode_legacy_lta_selection_features(payload.get("lta_selection_features")),
            profile_selection_features=tuple(ProfileFeatureCatalog.from_dict(item) for item in payload.get("profile_selection_features", ())),
            checkpoint_identity=None if payload.get("checkpoint_identity") is None else ModelCheckpointIdentity.from_dict(payload["checkpoint_identity"]),
            mace_descriptor_manifest=None if payload.get("mace_descriptor_manifest") is None else MaceDescriptorManifest.from_dict(payload["mace_descriptor_manifest"]),
            model_sweep_plan=None if payload.get("model_sweep_plan") is None else Data6ModelSweepPlan.from_dict(payload["model_sweep_plan"]),
            prediction_manifest=None if payload.get("prediction_manifest") is None else AtomicModelPredictionManifest.from_dict(payload["prediction_manifest"]),
            model_sweep_checkpoint_digest=None if payload.get("model_sweep_checkpoint_digest") is None else str(payload["model_sweep_checkpoint_digest"]),
            training_difficulty_catalogs=tuple(TrainingDifficultyFeatureCatalog.from_dict(item) for item in payload["training_difficulty_catalogs"]),
            blinded_prediction_catalogs=tuple(BlindedEvaluationPredictionCatalog.from_dict(item) for item in payload["blinded_prediction_catalogs"]),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if schema == DATA6_FEATURE_BUNDLE_SCHEMA:
            supplied = payload.get("content_digest")
            legacy_digest = digest({key: value for key, value in payload.items() if key != "content_digest"})
            if supplied not in (None, result.content_digest, legacy_digest):
                raise TrainingDataSerializationError("DATA6 feature-bundle digest mismatch.")
        if schema in {DATA6_FEATURE_BUNDLE_V4_SCHEMA, DATA6_FEATURE_BUNDLE_V3_SCHEMA, DATA6_FEATURE_BUNDLE_V2_SCHEMA} and payload.get("content_digest") not in (
            None,
            digest({key: value for key, value in payload.items() if key != "content_digest"}),
        ):
            raise TrainingDataSerializationError(f"{schema} feature-bundle digest mismatch.")
        return result


def _descriptor_frame_uids(data5_bundle: Any, roles: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    selected_units: list[str] = []
    excluded_units: list[str] = []
    role_set = {OuterRole(v) for v in roles}
    for outer in data5_bundle.outer_partitions:
        for assignment in outer.assignments:
            if assignment.role in role_set:
                selected_units.append(assignment.unit_id)
            else:
                excluded_units.append(assignment.unit_id)

    def frames(unit_ids: list[str]) -> tuple[str, ...]:
        result: list[str] = []
        for unit_id in unit_ids:
            result.extend(data5_bundle.unit_catalog.unit(unit_id).frame_uids)
        return tuple(sorted(set(result)))

    return frames(selected_units), frames(excluded_units)


def build_data6_feature_bundle(
    source_catalog: Any,
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    data4_bundle: Any,
    data5_bundle: Any,
    *,
    policy: Data6Policy | None = None,
    universal_structural_policy: UniversalStructuralSelectionPolicy | None = None,
    structural_provider: StructuralSelectionProvider | None = None,
    atom_group_membership_provider: AtomGroupMembershipProvider | None = None,
    lta_selection_policy: "LtaSelectionPolicy | None" = None,
    model_provider: AtomicModelProvider | None = None,
    descriptor_output_directory: str | Path | None = None,
    descriptor_policy: MaceDescriptorPolicy | None = None,
    model_sweep_artifacts: Data6ModelSweepArtifacts | None = None,
    progress_callback: Callable[[str], None] | None = None,
    structural_max_workers: int = 0,
) -> Data6FeatureBundle:
    """Build raw selection/model evidence without fitting statistical transforms."""

    active = (
        Data6Policy(
            build_universal_structural_features=data4_bundle.material_profile_contracts is not None,
            build_lta_selection_features=data4_bundle.lta_partition_features is not None,
            build_mace_descriptors=model_provider is not None,
            build_training_difficulty=model_provider is not None,
            build_blinded_predictions=model_provider is not None,
        )
        if policy is None
        else policy
    )
    if source_catalog.content_digest != data5_bundle.source_catalog_digest:
        raise TrainingDataInputError("DATA6 source/DATA5 lineage mismatch.")
    if frame_catalog.content_digest != data5_bundle.frame_catalog_digest:
        raise TrainingDataInputError("DATA6 frame/DATA5 lineage mismatch.")
    if data4_bundle.content_digest != data5_bundle.data4_bundle_digest:
        raise TrainingDataInputError("DATA6 DATA4/DATA5 lineage mismatch.")

    phase_geometry_plan = None
    effective_structural_policy = universal_structural_policy
    if active.build_universal_structural_features and data4_bundle.material_profile_contracts is not None:
        phase_geometry_plan = derive_phase_geometry_selection_plan(data4_bundle.material_profile_contracts)
        effective_structural_policy = universal_structural_policy_from_plan(
            phase_geometry_plan,
            override=universal_structural_policy,
        )

    structural_catalogs: list[UniversalStructuralFeatureCatalog] = []
    if active.build_universal_structural_features:
        if progress_callback is not None:
            progress_callback("status=phase; phase=building-universal-structural-selection-features")
        selected, _ = _descriptor_frame_uids(data5_bundle, active.universal_structural_roles)
        provider = UniversalStructuralSelectionProvider() if structural_provider is None else structural_provider
        if not callable(getattr(provider, "build_catalog", None)) or not str(getattr(provider, "provider_id", "")).strip():
            raise TrainingDataInputError("structural_provider must expose provider_id and build_catalog().")
        structural_kwargs = {
            "frame_uids": selected,
            "policy": effective_structural_policy,
            "membership_provider": atom_group_membership_provider,
        }
        if isinstance(provider, UniversalStructuralSelectionProvider):
            structural_kwargs["progress_callback"] = progress_callback
            structural_kwargs["max_workers"] = structural_max_workers
        structural_catalogs.append(
            provider.build_catalog(
                frame_catalog,
                frame_data_by_run,
                data4_bundle,
                **structural_kwargs,
            )
        )

    lta = None
    if active.build_lta_selection_features:
        if progress_callback is not None:
            progress_callback("status=phase; phase=building-LTA-selection-features")
        from .lta_selection import build_lta_selection_feature_catalog

        if data4_bundle.lta_partition_features is None:
            raise TrainingDataInputError("LTA selection features were requested without DATA4 LTA partition features.")
        development_frame_uids, _ = _descriptor_frame_uids(
            data5_bundle,
            (OuterRole.DEVELOPMENT.value,),
        )
        lta = build_lta_selection_feature_catalog(
            frame_catalog,
            frame_data_by_run,
            data4_bundle,
            policy=lta_selection_policy,
            frame_uids=development_frame_uids,
            progress_callback=progress_callback,
        )

    profile_selection_features = () if lta is None else (
        wrap_lta_selection_features(
            lta,
            data4_bundle_digest=data4_bundle.content_digest,
            embed_payload=False,
        ),
    )

    descriptor_manifest = None
    difficulty_catalogs: list[TrainingDifficultyFeatureCatalog] = []
    blinded_catalogs: list[BlindedEvaluationPredictionCatalog] = []
    checkpoint = None
    model_sweep_plan = None
    prediction_manifest = None
    model_sweep_checkpoint_digest = None
    if model_provider is not None:
        checkpoint = model_provider.checkpoint_identity
        if model_sweep_artifacts is not None:
            if not model_sweep_artifacts.complete:
                raise TrainingDataInputError("DATA6 requires a complete production model sweep.")
            model_sweep_plan = model_sweep_artifacts.checkpoint.plan
            if model_sweep_plan.data6_policy_digest != active.policy_digest:
                raise TrainingDataInputError("DATA6 production model-sweep policy mismatch.")
            if model_sweep_plan.checkpoint_identity.content_digest != checkpoint.content_digest:
                raise TrainingDataInputError("DATA6 production model-sweep checkpoint mismatch.")
            if model_sweep_plan.frame_catalog_digest != frame_catalog.content_digest or model_sweep_plan.data5_bundle_digest != data5_bundle.content_digest:
                raise TrainingDataInputError("DATA6 production model-sweep lineage mismatch.")
            descriptor_manifest = model_sweep_artifacts.descriptor_manifest
            prediction_manifest = model_sweep_artifacts.prediction_manifest
            model_sweep_checkpoint_digest = model_sweep_artifacts.checkpoint.content_digest
            prediction_cache = model_sweep_artifacts.prediction_cache() if prediction_manifest is not None else {}
        else:
            prediction_cache: dict[str, AtomicModelPrediction] = {}
        if active.build_mace_descriptors and descriptor_manifest is None:
            if descriptor_output_directory is None:
                raise TrainingDataInputError("descriptor_output_directory is required for MACE descriptors.")
            selected, excluded = _descriptor_frame_uids(data5_bundle, active.descriptor_roles)
            descriptor_manifest = build_mace_descriptor_manifest(
                frame_catalog,
                frame_data_by_run,
                data5_bundle,
                model_provider,
                descriptor_output_directory,
                frame_uids=selected,
                excluded_frame_uids=excluded,
                policy=descriptor_policy,
            )
        if active.build_training_difficulty or active.build_blinded_predictions:
            if progress_callback is not None:
                progress_callback(
                    "status=phase; phase=assembling-DATA6-model-evidence; shared_frame_index=on"
                )

            def report_model_evidence(completed: int, total: int, frame_uid: str) -> None:
                if progress_callback is None:
                    return
                if completed == total or completed == 1 or completed % 500 == 0:
                    progress_callback(
                        f"model evidence; status=progress; progress={format_progress_fraction(completed, total)}; frame={frame_uid[:12]}"
                    )

            difficulty_values, blinded_values = build_model_evidence_catalogs(
                frame_catalog,
                frame_data_by_run,
                data5_bundle,
                model_provider,
                build_training_difficulty=active.build_training_difficulty,
                build_blinded_predictions=active.build_blinded_predictions,
                prediction_cache=prediction_cache,
                progress_callback=report_model_evidence,
            )
            difficulty_catalogs.extend(difficulty_values)
            blinded_catalogs.extend(blinded_values)
    elif model_sweep_artifacts is not None:
        raise TrainingDataInputError("A model provider is required to bind production model-sweep evidence.")
    elif active.build_mace_descriptors or active.build_training_difficulty or active.build_blinded_predictions:
        raise TrainingDataInputError("A model provider is required by the active DATA6 model-feature policy.")

    return Data6FeatureBundle(
        dataset_id=frame_catalog.dataset_id,
        source_catalog_digest=source_catalog.content_digest,
        frame_catalog_digest=frame_catalog.content_digest,
        data4_bundle_digest=data4_bundle.content_digest,
        data5_bundle_digest=data5_bundle.content_digest,
        policy=active,
        universal_structural_features=tuple(structural_catalogs),
        phase_geometry_profile_plan=phase_geometry_plan,
        lta_selection_features=lta,
        profile_selection_features=profile_selection_features,
        checkpoint_identity=checkpoint,
        mace_descriptor_manifest=descriptor_manifest,
        model_sweep_plan=model_sweep_plan,
        prediction_manifest=prediction_manifest,
        model_sweep_checkpoint_digest=model_sweep_checkpoint_digest,
        training_difficulty_catalogs=tuple(difficulty_catalogs),
        blinded_prediction_catalogs=tuple(blinded_catalogs),
        notes=(
            "DATA6 publishes raw analysis-owned universal geometry, optional material-specific features, and model evidence; DATA7 owns fitted transforms and selection.",
        ),
    )
