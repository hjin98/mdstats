"""Aluminosilicate/LTA scientific provider used by the universal GFX3D CLI.

GFX3D-4 exposes the qualified framework/connectivity/trajectory/density results
through product-level dependency keys while retaining the owning scientific
algorithms migrated from ``examples/plot_lta_mixed_alkali_density.py``.
"""
from __future__ import annotations

import hashlib
import json
import time
import threading
import warnings
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np
from ase.data import chemical_symbols

from .contracts import GraphicsDependencyKey, GraphicsScene3DRequest
from .context import GraphicsSceneContext
from .errors import Graphics3DDependencyError
from .identity import identity_digest
from .providers import (
    CONNECTIVITY_PRODUCT_PROVIDER,
    DENSITY_PRODUCT_PROVIDER,
    FRAMEWORK_PRODUCT_PROVIDER,
    PRODUCT_PROVIDER_TYPES,
    TRAJECTORY_PRODUCT_PROVIDER,
    GraphicsDensityProduct,
    GraphicsScientificProduct,
)

from mdstats import (
    AtomicDensityOptions,
    AtomicDensitySelection,
    AtomicMeanGraphOptions,
    FrameworkAtomRole,
    FrameworkDynamicsOptions,
    FrameworkDynamicsResources,
    FrameworkMapping,
    FrameworkPathRule,
    FrameworkTopology,
    HystereticDistanceConnectivity,
    PairCutoffRegistry,
    NeighborSearchOptions,
    SpatialRegistrationMode,
    TopologyCatalog,
    TrajectoryAtomSelection,
    build_topology_catalog,
    compute_atomic_connectivity,
    project_atomic_connectivity_subset,
    prepare_framework_dynamics_scene,
    read_lammps_frames,
    read_vasp_frames,
)

from mdstats.progress import ProgressEmitter, resolve_progress_port

FRAMEWORK_SPECIES_ORDER = ("Si", "Al", "O")
MOBILE_SPECIES_ORDER = ("Li", "Na", "K")
MOBILE_OXYGEN_CUTOFFS = {"Li": 2.6, "Na": 2.9, "K": 3.3}
TOPOLOGY_CACHE_SUFFIX = "_topology_catalog.json"
TOPOLOGY_CACHE_SCHEMA = "mdstats.graphics3d.topology-cache.v2"


def framework_mapping() -> FrameworkMapping:
    return FrameworkMapping.from_symbol_roles(
        {
            "Si": FrameworkAtomRole.VERTEX,
            "Al": FrameworkAtomRole.VERTEX,
            "O": FrameworkAtomRole.LINKER,
            "Li": FrameworkAtomRole.SPECTATOR,
            "Na": FrameworkAtomRole.SPECTATOR,
            "K": FrameworkAtomRole.SPECTATOR,
        },
        path_rules=(FrameworkPathRule.from_symbols("T-O-T", ("O",), edge_kind="oxygen_bridge"),),
    )


def detect_present_species(trajectory) -> tuple[str, ...]:
    present = {chemical_symbols[int(z)] for z in trajectory.atomic_numbers}
    return tuple(
        symbol for symbol in FRAMEWORK_SPECIES_ORDER + MOBILE_SPECIES_ORDER if symbol in present
    )


def detect_mobile_species(trajectory) -> tuple[str, ...]:
    present = set(detect_present_species(trajectory))
    return tuple(symbol for symbol in MOBILE_SPECIES_ORDER if symbol in present)


def _strip_compression_suffix(name: str) -> str:
    lowered = name.lower()
    for suffix in (".gz", ".bz2", ".xz", ".lzma"):
        if lowered.endswith(suffix):
            return name[: -len(suffix)]
    return name


def infer_trajectory_format(path: Path, explicit_format: str = "auto") -> str:
    if explicit_format != "auto":
        return explicit_format
    base_name = _strip_compression_suffix(path.name)
    upper_name = base_name.upper()
    lower_name = base_name.lower()
    suffix = Path(base_name).suffix.lower()
    if suffix == ".xml":
        return "vasp-xml"
    if upper_name.endswith("XDATCAR"):
        return "vasp-xdatcar"
    if upper_name == "TRAJECTORY" or upper_name.endswith(".TRAJECTORY"):
        return "vasp-contcar-trajectory"
    if suffix in {".lammpstrj", ".dump", ".lammpsdump"} or lower_name.startswith("dump.") or lower_name == "dump":
        return "lammps-dump"
    raise ValueError(
        f"Cannot infer trajectory format from {path!s}. Use --format with one of "
        "vasp-xml, vasp-xdatcar, vasp-contcar-trajectory, or lammps-dump."
    )


def parse_lammps_type_map(value: str | Mapping[int, str] | None) -> dict[int, str] | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return {int(key): str(symbol) for key, symbol in value.items()}
    mapping: dict[int, str] = {}
    for entry in str(value).split(","):
        entry = entry.strip()
        if not entry:
            continue
        if "=" not in entry:
            raise ValueError(f"LAMMPS type-map entry {entry!r} must use TYPE=ELEMENT syntax.")
        raw_type, raw_symbol = entry.split("=", 1)
        atom_type = int(raw_type.strip())
        symbol = raw_symbol.strip()
        if atom_type < 1 or not symbol:
            raise ValueError(f"Invalid LAMMPS type-map entry {entry!r}.")
        if atom_type in mapping:
            raise ValueError(f"LAMMPS atom type {atom_type} is mapped more than once.")
        mapping[atom_type] = symbol
    if not mapping:
        raise ValueError("LAMMPS type map did not contain any mappings.")
    return mapping


def read_input_trajectory(path: str | Path, options: Mapping[str, Any]):
    source = Path(path)
    source_format = infer_trajectory_format(source, str(options.get("format", "auto")))
    stride = int(options.get("stride", 1))
    if stride < 1:
        raise ValueError("Trajectory stride must be >= 1.")
    if source_format == "lammps-dump":
        trajectory = read_lammps_frames(
            str(source),
            log_file=None if options.get("lammps_log") is None else str(options["lammps_log"]),
            units=options.get("lammps_units"),
            timestep=options.get("lammps_timestep"),
            type_map=parse_lammps_type_map(options.get("lammps_type_map")),
            stride=stride,
        )
        return trajectory, source_format
    timestep_fs = options.get("timestep_fs")
    if source_format == "vasp-contcar-trajectory" and timestep_fs is None:
        timestep_fs = 1.0
    trajectory = read_vasp_frames(
        str(source), format=source_format, stride=stride, timestep_fs=timestep_fs
    )
    return trajectory, source_format


def _sample_framework_bond_distances(trajectory, left_symbol: str, coordination_number: int = 4) -> list[float]:
    from ase.geometry import find_mic
    symbols = [chemical_symbols[int(z)] for z in trajectory.atomic_numbers]
    left = np.asarray([i for i, value in enumerate(symbols) if value == left_symbol], dtype=np.int64)
    oxygen = np.asarray([i for i, value in enumerate(symbols) if value == "O"], dtype=np.int64)
    if left.size == 0 or oxygen.size < coordination_number:
        return []
    sample_count = min(96, trajectory.n_frames)
    frame_indices = np.unique(np.linspace(0, trajectory.n_frames - 1, sample_count).round().astype(int))
    values: list[float] = []
    for frame in frame_indices:
        cell = np.asarray(trajectory.cells[frame], dtype=float)
        cart = np.asarray(trajectory.fractional_positions[frame], dtype=float) @ cell
        delta = cart[oxygen][None, :, :] - cart[left][:, None, :]
        _mic, distances = find_mic(delta.reshape(-1, 3), cell, pbc=trajectory.pbc)
        matrix = np.asarray(distances, dtype=float).reshape(left.size, oxygen.size)
        shell = np.partition(matrix, kth=coordination_number - 1, axis=1)[:, :coordination_number]
        values.extend(float(value) for value in shell.reshape(-1) if np.isfinite(value))
    return values


def framework_connectivity_definition(
    trajectory, *, formation_override: float | None = None, breaking_override: float | None = None
) -> tuple[HystereticDistanceConnectivity, dict[str, dict[str, float]]]:
    present = set(detect_present_species(trajectory))
    formation: dict[tuple[str, str], float] = {}
    breaking: dict[tuple[str, str], float] = {}
    audit: dict[str, dict[str, float]] = {}
    lower_bounds = {"Si": 1.90, "Al": 1.95}
    formation_caps = {"Si": 2.12, "Al": 2.18}
    breaking_caps = {"Si": 2.38, "Al": 2.45}
    for symbol in ("Si", "Al"):
        if symbol not in present:
            continue
        sampled = np.asarray(_sample_framework_bond_distances(trajectory, symbol), dtype=float)
        if sampled.size:
            q995 = float(np.quantile(sampled, 0.995))
            q999 = float(np.quantile(sampled, 0.999))
            form = float(np.clip(q995 + 0.03, lower_bounds[symbol], formation_caps[symbol]))
            retain = float(np.clip(max(form + 0.18, q999 + 0.10), form + 0.12, breaking_caps[symbol]))
        else:
            q995 = q999 = float("nan")
            form = 2.05 if symbol == "Si" else 2.10
            retain = 2.30 if symbol == "Si" else 2.38
        if formation_override is not None:
            form = float(formation_override)
        if breaking_override is not None:
            retain = float(breaking_override)
        if not form < retain:
            raise ValueError(f"Framework hysteresis requires formation < breaking for {symbol}-O.")
        formation[(symbol, "O")] = form
        breaking[(symbol, "O")] = retain
        audit[symbol] = {
            "formation_cutoff_angstrom": form,
            "breaking_cutoff_angstrom": retain,
            "sample_q995_angstrom": q995,
            "sample_q999_angstrom": q999,
            "sample_count": float(sampled.size),
        }
    if not formation:
        raise ValueError(
            "The current GFX3D-3 framework provider requires Si/Al-O framework atoms. "
            "Generic raw-source providers are a GFX3D-4 deliverable."
        )
    return (
        HystereticDistanceConnectivity(
            formation_cutoffs=PairCutoffRegistry.from_mapping(formation),
            breaking_cutoffs=PairCutoffRegistry.from_mapping(breaking),
        ),
        audit,
    )


def atomic_connectivity_definition(trajectory, framework_definition: HystereticDistanceConnectivity):
    formation = {pair: float(cutoff.radius) for pair, cutoff in framework_definition.formation_cutoffs.cutoffs.items()}
    breaking = {pair: float(cutoff.radius) for pair, cutoff in framework_definition.breaking_cutoffs.cutoffs.items()}
    present = set(detect_present_species(trajectory))
    for symbol in MOBILE_SPECIES_ORDER:
        if symbol in present:
            formation[(symbol, "O")] = MOBILE_OXYGEN_CUTOFFS[symbol]
            breaking[(symbol, "O")] = MOBILE_OXYGEN_CUTOFFS[symbol] + 0.25
    return HystereticDistanceConnectivity(
        formation_cutoffs=PairCutoffRegistry.from_mapping(formation),
        breaking_cutoffs=PairCutoffRegistry.from_mapping(breaking),
    )


def _density_species_from_request(request, present_species: Sequence[str]) -> tuple[str, ...]:
    needed: list[str] = []
    present = set(present_species)
    for layer in request.enabled_layers:
        if layer.layer_type != "density":
            continue
        if not layer.selection.species:
            raise ValueError(
                f"Density layer {layer.name!r} needs an explicit species selection in GFX3D-3."
            )
        for symbol in layer.selection.species:
            if symbol not in present:
                raise ValueError(f"Density layer {layer.name!r} selects absent species {symbol!r}.")
            if symbol not in needed:
                needed.append(symbol)
    return tuple(needed)


def _trajectory_species_from_request(request, present_species: Sequence[str]) -> tuple[str, ...]:
    selected: list[str] = []
    present = tuple(present_species)
    for layer in request.enabled_layers:
        if layer.layer_type != "trajectory":
            continue
        species = layer.selection.species or present
        for symbol in species:
            if symbol not in selected:
                selected.append(symbol)
    return tuple(selected)




def _hash_array(digest: "hashlib._Hash", value: Any, *, dtype: str, label: str) -> None:
    array = np.ascontiguousarray(np.asarray(value, dtype=np.dtype(dtype)))
    digest.update(label.encode("utf8") + b"\0")
    digest.update(str(array.shape).encode("ascii") + b"\0")
    digest.update(memoryview(array).cast("B"))


def _trajectory_topology_identity(trajectory: Any) -> str:
    """Return an exact geometry/identity hash for topology-cache authentication."""

    digest = hashlib.sha256()
    digest.update(b"mdstats.graphics3d.topology-trajectory.v1\0")
    _hash_array(digest, trajectory.atomic_numbers, dtype="<i8", label="atomic_numbers")
    _hash_array(digest, trajectory.frame_ids, dtype="<i8", label="frame_ids")
    _hash_array(digest, trajectory.cells, dtype="<f8", label="cells")
    _hash_array(digest, trajectory.fractional_positions, dtype="<f8", label="fractional_positions")
    _hash_array(digest, trajectory.pbc, dtype="u1", label="pbc")
    digest.update(str(getattr(trajectory, "frame_semantics", "")).encode("utf8"))
    return digest.hexdigest()


def _topology_cache_path(input_options: Mapping[str, Any], output_path: Path) -> Path:
    cache = input_options.get("topology_cache")
    return Path(cache) if cache else output_path.with_name(output_path.stem + TOPOLOGY_CACHE_SUFFIX)


def _topology_cache_authority(
    trajectory: Any,
    framework_definition: HystereticDistanceConnectivity,
) -> dict[str, Any]:
    return {
        "trajectory_topology_identity": _trajectory_topology_identity(trajectory),
        "framework_definition_identity": identity_digest(
            "mdstats.graphics3d.framework-connectivity-definition.v1",
            framework_definition.to_dict(),
        ),
        "framework_mapping_digest": framework_mapping().digest,
        "frame_count": int(trajectory.n_frames),
        "atom_count": int(trajectory.n_atoms),
    }


def _load_authenticated_topology_cache(
    path: Path,
    *,
    trajectory: Any,
    framework_definition: HystereticDistanceConnectivity,
) -> tuple[TopologyCatalog | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None, "unreadable"
    if payload.get("schema_version") != TOPOLOGY_CACHE_SCHEMA or "catalog" not in payload:
        return None, "legacy_or_unauthenticated"
    authority = _topology_cache_authority(trajectory, framework_definition)
    for key, expected in authority.items():
        if payload.get(key) != expected:
            return None, f"authority_mismatch:{key}"
    try:
        catalog = TopologyCatalog.from_dict(payload["catalog"])
    except Exception:
        return None, "catalog_invalid"
    expected_frames = np.arange(int(trajectory.n_frames), dtype=np.int64)
    if not np.array_equal(catalog.frame_indices, expected_frames):
        return None, "frame_indices_mismatch"
    if not np.array_equal(catalog.frame_ids, np.asarray(trajectory.frame_ids, dtype=np.int64)):
        return None, "frame_ids_mismatch"
    if catalog.mapping.digest != framework_mapping().digest:
        return None, "mapping_mismatch"
    return catalog, None


def _write_authenticated_topology_cache(
    path: Path,
    *,
    trajectory: Any,
    framework_definition: HystereticDistanceConnectivity,
    topology: TopologyCatalog,
) -> None:
    payload = {
        "schema_version": TOPOLOGY_CACHE_SCHEMA,
        **_topology_cache_authority(trajectory, framework_definition),
        "catalog_digest": topology.digest,
        "catalog": topology.to_dict(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n")
    temporary.replace(path)


def _catalog_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if payload.get("schema_version") == TOPOLOGY_CACHE_SCHEMA and "catalog" in payload:
        catalog = payload["catalog"]
        if not isinstance(catalog, Mapping):
            raise ValueError("Authenticated topology-cache catalog payload is malformed.")
        return catalog
    return payload


def _file_identity(path_value: Any) -> Mapping[str, Any] | None:
    if path_value is None:
        return None
    path = Path(path_value)
    if not path.exists() or not path.is_file():
        return {"path": str(path)}
    import hashlib
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "size_bytes": int(path.stat().st_size)}


def _lta_source_scientific_identity(
    trajectory: Any,
    request: GraphicsScene3DRequest,
    input_options: Mapping[str, Any],
    source_identity: str | None,
) -> str:
    """Scientific identity of the current LTA raw-source provider.

    Cache/storage/output choices are deliberately excluded.  Source parsing and
    topology/connectivity choices that can change a scientific product are
    included even when they originate from CLI input options rather than the
    scene request.
    """
    scientific_input = {
        "source_identity": source_identity,
        "n_frames": int(trajectory.n_frames),
        "n_atoms": int(trajectory.n_atoms),
        "stride": input_options.get("stride"),
        "timestep_fs": input_options.get("timestep_fs"),
        "lammps_units": input_options.get("lammps_units"),
        "lammps_timestep": input_options.get("lammps_timestep"),
        "lammps_type_map": input_options.get("lammps_type_map"),
        "framework_formation_cutoff": input_options.get("framework_formation_cutoff"),
        "framework_breaking_cutoff": input_options.get("framework_breaking_cutoff"),
        "topology_override": _file_identity(input_options.get("topology")),
        "lammps_log": _file_identity(input_options.get("lammps_log")),
        "scene_scientific_identity": request.scientific_identity,
    }
    return identity_digest("mdstats.graphics3d.lta-source-science.gfx3d4.v1", scientific_input)


@dataclass(slots=True)
class LTAGraphics3DDependencySource:
    """GFX3D-4 product-level provider for the current LTA CLI science.

    The qualified framework-dynamics implementation still owns the numerical
    preparation.  This provider batches that owner's joint work once, then
    exposes independent framework/connectivity/trajectory/density products to
    the universal dependency DAG.  Layers therefore no longer depend on a
    monolithic ``FrameworkDynamicsScene`` key.
    """

    trajectory: Any
    request: GraphicsScene3DRequest
    input_options: Mapping[str, Any]
    output_path: Path
    source_identity: str | None = None
    progress: Any = None
    _scene: Any = field(default=None, init=False, repr=False)
    _topology_metadata: Mapping[str, Any] = field(default_factory=dict, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    _failure: Exception | None = field(default=None, init=False, repr=False)
    _preparation_count: int = field(default=0, init=False, repr=False)
    _preparation_attempt_count: int = field(default=0, init=False, repr=False)
    _preparation_wall_seconds: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.request, GraphicsScene3DRequest):
            raise TypeError("request must be GraphicsScene3DRequest.")
        self.input_options = MappingProxyType(dict(self.input_options))
        self.output_path = Path(self.output_path)

    @property
    def scientific_identity(self) -> str:
        return _lta_source_scientific_identity(
            self.trajectory, self.request, self.input_options, self.source_identity
        )

    def dependency_key(self, provider_type: str) -> GraphicsDependencyKey:
        provider = str(provider_type).strip().lower()
        if provider not in PRODUCT_PROVIDER_TYPES:
            raise Graphics3DDependencyError(
                f"LTA GFX3D source does not provide {provider!r}."
            )
        return GraphicsDependencyKey(
            provider,
            {
                "source_scientific_identity": self.scientific_identity,
                "product_schema": "mdstats.graphics3d.lta-product.gfx3d4.v1",
            },
        )

    def _prepare_once(self) -> Any:
        """Prepare the legacy owner exactly once, including failure single-flight.

        Product dependencies have distinct GFX3D keys, so scene-context single-flight
        alone cannot prevent a failed monolithic owner preparation from being retried
        by the next product key.  Latch the first source-level failure here and replay
        it to every dependent product.
        """
        with self._lock:
            if self._scene is not None:
                return self._scene
            if self._failure is not None:
                error = self._failure
                raise Graphics3DDependencyError(
                    "LTA GFX3D source preparation previously failed: "
                    f"{type(error).__name__}: {error}"
                ) from error

            started = time.perf_counter()
            self._preparation_attempt_count += 1
            try:
                scene, topology_metadata = prepare_legacy_source_scene(
                    self.trajectory,
                    self.request,
                    input_options=self.input_options,
                    output_path=self.output_path,
                    progress=self.progress,
                )
                scene = replace(
                    scene,
                    metadata={
                        **dict(scene.metadata),
                        "gfx3d_atomic_number_by_atom": {
                            str(index): int(z)
                            for index, z in enumerate(self.trajectory.atomic_numbers)
                        },
                        "gfx3d_provider_gate": "GFX3D-4",
                        "gfx3d_dependency_source_identity": self.scientific_identity,
                        "gfx3d_topology_resolution": dict(topology_metadata),
                    },
                )
            except Exception as error:
                self._failure = error
                self._preparation_wall_seconds += float(time.perf_counter() - started)
                raise Graphics3DDependencyError(
                    "LTA GFX3D source preparation failed: "
                    f"{type(error).__name__}: {error}"
                ) from error

            self._scene = scene
            self._topology_metadata = MappingProxyType(dict(topology_metadata))
            self._preparation_count += 1
            self._preparation_wall_seconds += float(time.perf_counter() - started)
            return scene

    def resolve_graphics3d_dependency(
        self, key: GraphicsDependencyKey, context: GraphicsSceneContext
    ) -> GraphicsScientificProduct:
        del context
        if key.provider_type not in PRODUCT_PROVIDER_TYPES:
            raise Graphics3DDependencyError(
                f"LTA GFX3D source cannot resolve {key.provider_type!r}."
            )
        expected = self.dependency_key(key.provider_type)
        if expected.identity != key.identity:
            raise Graphics3DDependencyError(
                f"GFX3D dependency key for {key.provider_type!r} does not match this source authority."
            )
        scene = self._prepare_once()
        if key.provider_type == FRAMEWORK_PRODUCT_PROVIDER:
            value = scene.mean_framework
        elif key.provider_type == CONNECTIVITY_PRODUCT_PROVIDER:
            value = scene.atomic_mean_graph
            if value is None:
                raise Graphics3DDependencyError(
                    "Atomic-connectivity product was requested but not prepared by the source plan."
                )
        elif key.provider_type == TRAJECTORY_PRODUCT_PROVIDER:
            value = scene.trajectory_paths
            if value is None:
                raise Graphics3DDependencyError(
                    "Atomic-trajectory product was requested but not prepared by the source plan."
                )
        else:
            value = GraphicsDensityProduct(
                atomic_density_fields=tuple(scene.atomic_density_fields),
                framework_density_fields=scene.framework_density_fields,
                atomic_number_by_atom={
                    int(index): int(z) for index, z in enumerate(self.trajectory.atomic_numbers)
                },
            )
            if not value.atomic_density_fields and value.framework_density_fields is None:
                raise Graphics3DDependencyError(
                    "Density product was requested but the source plan prepared no density fields."
                )
        return GraphicsScientificProduct(
            provider_type=key.provider_type,
            value=value,
            display_cell=(None if getattr(scene, "display_cell", None) is None else np.asarray(scene.display_cell, dtype=np.float64)),
            frame_indices=tuple(int(v) for v in getattr(scene, "frame_indices", ())),
            provenance={
                "provider_gate": "GFX3D-HARDEN1",
                "source_scientific_identity": self.scientific_identity,
                "batched_owner": "mdstats.plotting.framework_dynamics",
                "scientific_identity_includes_cache_state": False,
                "source_scene_schema": scene.metadata.get("schema_version"),
                "source_framework_topology_digest": scene.metadata.get("source_framework_topology_digest"),
                "registration_mode": scene.metadata.get("registration_mode"),
                "display_cell_policy": scene.metadata.get("display_cell_policy"),
            },
        )

    @property
    def topology_metadata(self) -> Mapping[str, Any]:
        return self._topology_metadata

    def preparation_report(self) -> Mapping[str, Any]:
        with self._lock:
            return MappingProxyType(
                {
                    "schema_version": "mdstats.graphics3d.lta-provider-report.gfx3d4.v1",
                    "preparation_count": int(self._preparation_count),
                    "preparation_attempt_count": int(self._preparation_attempt_count),
                    "preparation_wall_seconds": float(self._preparation_wall_seconds),
                    "prepared": self._scene is not None,
                    "failed": self._failure is not None,
                    "failure_type": None if self._failure is None else type(self._failure).__name__,
                    "scientific_identity": self.scientific_identity,
                    "cache_policy": "scene_context_in_memory_single_flight",
                    "durable_product_cache": False,
                }
            )


def _lta_connectivity_neighbor_options(trajectory) -> NeighborSearchOptions | None:
    """Prefer the exact cached cell-list path for fixed fully periodic LTA MD."""

    pbc = np.asarray(trajectory.pbc, dtype=bool)
    cells = np.asarray(trajectory.cells, dtype=np.float64)
    if bool(np.all(pbc)) and cells.ndim == 3 and cells.shape[0] > 0 and np.array_equal(
        cells, np.broadcast_to(cells[0], cells.shape)
    ):
        return NeighborSearchOptions(backend="cell_list", cache_mode="none")
    return None


def prepare_legacy_source_scene(
    trajectory,
    request,
    *,
    input_options: Mapping[str, Any],
    output_path: Path,
    progress=None,
):
    """Prepare the GFX3D-3 compatibility ``FrameworkDynamicsScene`` once."""
    progress_port = resolve_progress_port(progress)
    reporter = ProgressEmitter(progress_port, source="graphics3d.lta")
    present_species = detect_present_species(trajectory)
    reporter.started(
        "framework_calibration",
        "calibrating Si/Al-O hysteretic framework cutoffs",
        metadata={"frame_count": int(trajectory.n_frames), "species": ",".join(present_species)},
    )
    framework_definition, hysteresis_audit = framework_connectivity_definition(
        trajectory,
        formation_override=input_options.get("framework_formation_cutoff"),
        breaking_override=input_options.get("framework_breaking_cutoff"),
    )
    reporter.completed(
        "framework_calibration",
        "resolved framework hysteresis calibration",
        metadata={"audit": json.dumps(hysteresis_audit, sort_keys=True)},
    )
    suspicious_framework_species: list[str] = []
    for symbol, audit in hysteresis_audit.items():
        q995 = float(audit.get("sample_q995_angstrom", float("nan")))
        breaking = float(audit.get("breaking_cutoff_angstrom", float("nan")))
        if np.isfinite(q995) and np.isfinite(breaking) and q995 > breaking + 0.20:
            suspicious_framework_species.append(str(symbol))
    if suspicious_framework_species:
        message = (
            "tetrahedral-neighbor distances for "
            + ", ".join(suspicious_framework_species)
            + " extend well beyond the allowed Si/Al-O hysteresis range; check "
              "--lammps-type-map and/or framework integrity before interpreting "
              "topology partitions"
        )
        reporter.warning(
            "framework_calibration",
            message,
            metadata={"species": ",".join(suspicious_framework_species)},
        )
        if progress is None:
            warnings.warn(message, RuntimeWarning, stacklevel=2)
    needs_connectivity = any(layer.layer_type == "connectivity" for layer in request.enabled_layers)
    full_definition = (
        atomic_connectivity_definition(trajectory, framework_definition)
        if needs_connectivity
        else None
    )
    connectivity = None
    framework_connectivity = None
    connectivity_neighbor_options = _lta_connectivity_neighbor_options(trajectory)

    topology_path = input_options.get("topology")
    if topology_path:
        payload = json.loads(Path(topology_path).read_text())
        catalog_payload = _catalog_payload(payload)
        topology = (
            TopologyCatalog.from_dict(catalog_payload)
            if "frame_topology_ids" in catalog_payload and "topologies" in catalog_payload
            else FrameworkTopology.from_dict(catalog_payload)
        )
        topology_metadata = {"source": "user_supplied", "path": str(topology_path)}
    else:
        topology = None
        topology_metadata = {
            "framework_hysteresis_calibration": hysteresis_audit,
            "cache_policy": "authenticated_exact_geometry_v2",
        }
        cache_path = _topology_cache_path(input_options, output_path)
        if not bool(input_options.get("no_topology_cache", False)):
            topology, rejection = _load_authenticated_topology_cache(
                cache_path,
                trajectory=trajectory,
                framework_definition=framework_definition,
            )
            if topology is not None:
                topology_metadata.update(
                    {
                        "source": "authenticated_topology_cache",
                        "cache_reused": str(cache_path),
                        "cache_authentication": "passed",
                        "n_topologies": len(topology.topologies),
                        "catalog_consistency": topology.consistency.value,
                    }
                )
            else:
                topology_metadata["cache_reuse_rejected"] = rejection

        if topology is None:
            if needs_connectivity and full_definition is not None:
                reporter.started(
                    "atomic_connectivity",
                    "computing full atomic connectivity once for atomic and framework products",
                    metadata={"frame_count": int(trajectory.n_frames)},
                )
                connectivity = compute_atomic_connectivity(
                    trajectory,
                    full_definition,
                    neighbor_search_options=connectivity_neighbor_options,
                    progress_callback=lambda current, total: reporter.update(
                        "atomic_connectivity",
                        "computing full atomic connectivity",
                        current=current,
                        total=total,
                        unit="frames",
                    ),
                )
                reporter.completed(
                    "atomic_connectivity",
                    f"resolved {connectivity.n_states} atomic connectivity states",
                    metadata={
                        "execution_strategy": "single_broad_pass_then_exact_framework_projection"
                    },
                )
                if full_definition.to_dict() == framework_definition.to_dict():
                    framework_connectivity = connectivity
                    topology_metadata["framework_connectivity_source"] = "full_connectivity_identical_definition"
                else:
                    reporter.started(
                        "framework_connectivity",
                        "projecting exact framework pair subset from full atomic connectivity",
                        metadata={"source_state_count": int(connectivity.n_states)},
                    )
                    framework_connectivity = project_atomic_connectivity_subset(
                        trajectory,
                        connectivity,
                        framework_definition,
                    )
                    reporter.completed(
                        "framework_connectivity",
                        f"resolved {framework_connectivity.n_states} framework connectivity states without a second neighbor pass",
                        metadata={
                            "execution_strategy": "exact_hysteretic_pair_subset_projection_v1"
                        },
                    )
                    topology_metadata["framework_connectivity_source"] = "projected_from_full_atomic_connectivity"
            else:
                reporter.started(
                    "framework_connectivity",
                    "computing hysteretic framework connectivity",
                    metadata={"frame_count": int(trajectory.n_frames)},
                )
                framework_connectivity = compute_atomic_connectivity(
                    trajectory,
                    framework_definition,
                    neighbor_search_options=connectivity_neighbor_options,
                    progress_callback=lambda current, total: reporter.update(
                        "framework_connectivity",
                        "computing hysteretic framework connectivity",
                        current=current,
                        total=total,
                        unit="frames",
                    ),
                )
                reporter.completed(
                    "framework_connectivity",
                    f"resolved {framework_connectivity.n_states} framework connectivity states",
                )
                topology_metadata["framework_connectivity_source"] = "direct_framework_only_pass"

            reporter.started(
                "framework_topology",
                f"building topology catalog from {framework_connectivity.n_states} connectivity states",
            )
            topology = build_topology_catalog(trajectory, framework_connectivity, framework_mapping())
            reporter.completed(
                "framework_topology",
                f"resolved {len(topology.topologies)} framework topologies",
                metadata={"catalog_consistency": topology.consistency.value},
            )
            topology_fraction = float(len(topology.topologies)) / float(max(1, trajectory.n_frames))
            topology_metadata["topology_count_per_frame"] = topology_fraction
            if len(topology.topologies) >= 8 and topology_fraction >= 0.25:
                message = (
                    f"framework topology is highly fragmented: {len(topology.topologies)} "
                    f"distinct topologies across {trajectory.n_frames} selected frames. "
                    "This often indicates an incorrect atom-type map, cutoff saturation, "
                    "or a physically damaged framework."
                )
                reporter.warning(
                    "framework_topology",
                    message,
                    metadata={
                        "n_topologies": int(len(topology.topologies)),
                        "frame_count": int(trajectory.n_frames),
                        "topology_fraction": topology_fraction,
                    },
                )
                if progress is None:
                    warnings.warn(message, RuntimeWarning, stacklevel=2)
            topology_metadata.update(
                {
                    "source": "inferred_hysteretic_catalog",
                    "n_topologies": len(topology.topologies),
                    "catalog_consistency": topology.consistency.value,
                }
            )
            if not bool(input_options.get("no_topology_cache", False)):
                _write_authenticated_topology_cache(
                    cache_path,
                    trajectory=trajectory,
                    framework_definition=framework_definition,
                    topology=topology,
                )
                topology_metadata["cache_written"] = str(cache_path)
                topology_metadata["cache_authentication"] = "written_v2"

    # A supplied/reused topology bypasses framework-connectivity construction,
    # but an explicit atomic-connectivity layer still needs the broad graph.
    if needs_connectivity and connectivity is None:
        assert full_definition is not None
        reporter.started(
            "atomic_connectivity",
            "computing full atomic connectivity",
            metadata={"frame_count": int(trajectory.n_frames)},
        )
        connectivity = compute_atomic_connectivity(
            trajectory,
            full_definition,
            neighbor_search_options=connectivity_neighbor_options,
            progress_callback=lambda current, total: reporter.update(
                "atomic_connectivity",
                "computing full atomic connectivity",
                current=current,
                total=total,
                unit="frames",
            ),
        )
        reporter.completed(
            "atomic_connectivity",
            f"resolved {connectivity.n_states} atomic connectivity states",
            metadata={"execution_strategy": "single_full_connectivity_pass"},
        )

    topology_metadata["connectivity_execution"] = {
        "strategy": (
            "single_broad_pass_then_exact_framework_projection"
            if needs_connectivity and topology_metadata.get("framework_connectivity_source") == "projected_from_full_atomic_connectivity"
            else "direct_or_cached_topology"
        ),
        "cross_pass_geometry_cache": False,
        "bounded_memory_by_frame_count": True,
    }

    trajectory_species = _trajectory_species_from_request(request, present_species)
    density_species = _density_species_from_request(request, present_species)
    density_selections = tuple(
        AtomicDensitySelection(species=(symbol,), label=f"{symbol} density")
        for symbol in density_species
    )
    scene_options = dict(request.scene_options)
    resources = FrameworkDynamicsResources(
        max_memory_bytes=request.resources.get("max_memory"),
        max_threads=request.resources.get("max_threads"),
        max_wall_time_seconds=request.resources.get("wall_time_target"),
    )
    reporter.started(
        "scene_preparation",
        "preparing registered framework/trajectory/density products",
        metadata={
            "trajectory_species": ",".join(trajectory_species),
            "density_species": ",".join(density_species),
        },
    )
    source_scene = prepare_framework_dynamics_scene(
        trajectory,
        topology,
        trajectory_selection=(
            None
            if not trajectory_species
            else TrajectoryAtomSelection(species=trajectory_species, label="GFX3D trajectories")
        ),
        atomic_connectivity=connectivity,
        atomic_mean_graph_options=(
            AtomicMeanGraphOptions(
                mode=str(scene_options.get("connectivity_mode", "occupancy")),
                occupancy_threshold=float(scene_options.get("occupancy_threshold", 0.95)),
            )
            if needs_connectivity
            else None
        ),
        atomic_density_selections=density_selections,
        atomic_density_options=(
            AtomicDensityOptions(
                grid_interval=float(scene_options.get("density_grid_interval", 0.20)),
                gaussian_to_grid_ratio=float(scene_options.get("density_gaussian_to_grid_ratio", 2.0)),
                adaptive_smearing=bool(scene_options.get("density_adaptive_smearing", True)),
                max_smearing_to_sample_sd_ratio=float(scene_options.get("density_max_smearing_to_sample_sd_ratio", 0.50)),
                sample_sd_quantile=float(scene_options.get("density_sample_sd_quantile", 0.10)),
            )
            if density_selections
            else None
        ),
        options=FrameworkDynamicsOptions(
            registration_mode=SpatialRegistrationMode(
                str(scene_options.get("registration", "framework_registered"))
            ),
            trajectory_display_mode=str(scene_options.get("trajectory_display_mode", "folded")),
            display_cell=str(scene_options.get("display_cell", "reference")),
        ),
        resources=resources,
        progress=progress,
        _topology_category_mode="dominant_only",
    )
    reporter.completed(
        "scene_preparation",
        "completed registered source-scene preparation",
    )
    return source_scene, topology_metadata
