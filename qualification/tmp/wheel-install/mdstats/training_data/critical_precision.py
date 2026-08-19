"""Critical-FP64 execution support for MACE 0.3.16.

The expensive equivariant body remains in the model-selected dtype (float32 or
float64).  Per-atom reference and interaction energies are converted before
system reduction, so total energies are accumulated in float64 and forces are
differentiated from that same float64 scalar.  Virials/stresses are reduced
from edge derivatives and edge vectors in float64.  Returned global
observables are float64 even when the model body is float32.

This is a deliberately version-locked runtime patch for ``ScaleShiftMACE`` in
mace-torch 0.3.16.  It is installed explicitly by mdstats wrappers and never
silently changes an arbitrary MACE environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import os

from .mace_compatibility import mace_runtime_warning_handled

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest

MACE_CRITICAL_PRECISION_POLICY_SCHEMA = "mdstats.mace-critical-precision-policy.v2"
MACE_CRITICAL_PRECISION_POLICY_V1_SCHEMA = "mdstats.mace-critical-precision-policy.v1"
MACE_CRITICAL_PRECISION_AUDIT_SCHEMA = "mdstats.mace-critical-precision-audit.v2"
MACE_CRITICAL_PRECISION_AUDIT_V1_SCHEMA = "mdstats.mace-critical-precision-audit.v1"
ASE_MD_STATE_PRECISION_AUDIT_SCHEMA = "mdstats.ase-md-state-precision-audit.v1"
SUPPORTED_MACE_VERSION = "0.3.16"
PATCH_ENVIRONMENT_VARIABLE = "MDSTATS_MACE_CRITICAL_FP64"
CRITICAL_PRECISION_POLICY_ENVIRONMENT_VARIABLE = "MDSTATS_MACE_CRITICAL_PRECISION_POLICY"


@dataclass(frozen=True, slots=True)
class MaceCriticalPrecisionPolicy:
    """Precision split between the MACE body and critical global operations."""

    energy_accumulation_dtype: str = "float64"
    virial_accumulation_dtype: str = "float64"
    observable_output_dtype: str = "float64"
    md_state_dtype: str = "float64"
    allow_tf32: bool = False
    differentiate_from_accumulated_energy: bool = True
    training_force_jacobian_dtype: str = "model"
    strategy: str = "scaleshift_mace_0.3.16_runtime_patch_v1"

    def __post_init__(self) -> None:
        dtype_values = tuple(
            getattr(self, name)
            for name in (
                "energy_accumulation_dtype",
                "virial_accumulation_dtype",
                "observable_output_dtype",
                "md_state_dtype",
            )
        )
        if self.strategy == "scaleshift_mace_0.3.16_runtime_patch_v1":
            if any(value != "float64" for value in dtype_values):
                raise TrainingDataInputError(
                    "The qualified ScaleShiftMACE critical-precision patch requires FP64 global operations."
                )
        elif self.strategy == "native_model_precision_v1":
            if any(value != "float32" for value in dtype_values):
                raise TrainingDataInputError(
                    "Canonical native single-precision critical operations must be uniformly FP32."
                )
        else:
            raise TrainingDataInputError("Unsupported critical-precision strategy.")
        if self.allow_tf32:
            raise TrainingDataInputError("TF32 is disabled by the precision policy.")
        if not self.differentiate_from_accumulated_energy:
            raise TrainingDataInputError(
                "Inference forces must be differentiated from the same accumulated energy."
            )
        if self.training_force_jacobian_dtype != "model":
            raise TrainingDataInputError(
                "MACE 0.3.16 force training is locked to the selected model dtype."
            )

    @property
    def canonical_dtype(self) -> str:
        return self.energy_accumulation_dtype

    @classmethod
    def for_dtype(cls, dtype: str) -> "MaceCriticalPrecisionPolicy":
        if dtype == "float64":
            return cls()
        if dtype == "float32":
            return cls(
                energy_accumulation_dtype="float32",
                virial_accumulation_dtype="float32",
                observable_output_dtype="float32",
                md_state_dtype="float32",
                strategy="native_model_precision_v1",
            )
        raise TrainingDataInputError(f"Unsupported critical-operation dtype {dtype!r}.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                MACE_CRITICAL_PRECISION_POLICY_V1_SCHEMA
                if self.strategy == "scaleshift_mace_0.3.16_runtime_patch_v1"
                else MACE_CRITICAL_PRECISION_POLICY_SCHEMA
            ),
            "energy_accumulation_dtype": self.energy_accumulation_dtype,
            "virial_accumulation_dtype": self.virial_accumulation_dtype,
            "observable_output_dtype": self.observable_output_dtype,
            "md_state_dtype": self.md_state_dtype,
            "allow_tf32": self.allow_tf32,
            "differentiate_from_accumulated_energy": self.differentiate_from_accumulated_energy,
            "training_force_jacobian_dtype": self.training_force_jacobian_dtype,
            "strategy": self.strategy,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceCriticalPrecisionPolicy":
        if payload.get("schema") not in {
            MACE_CRITICAL_PRECISION_POLICY_SCHEMA,
            MACE_CRITICAL_PRECISION_POLICY_V1_SCHEMA,
        }:
            raise TrainingDataSerializationError("Unsupported critical-precision policy schema.")
        result = cls(
            energy_accumulation_dtype=str(payload["energy_accumulation_dtype"]),
            virial_accumulation_dtype=str(payload["virial_accumulation_dtype"]),
            observable_output_dtype=str(payload["observable_output_dtype"]),
            md_state_dtype=str(payload["md_state_dtype"]),
            allow_tf32=bool(payload["allow_tf32"]),
            differentiate_from_accumulated_energy=bool(
                payload["differentiate_from_accumulated_energy"]
            ),
            training_force_jacobian_dtype=str(
                payload.get("training_force_jacobian_dtype", "model")
            ),
            strategy=str(payload["strategy"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Critical-precision policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceCriticalPrecisionAudit:
    mace_version: str
    model_class: str
    model_dtype: str
    energy_dtype: str
    force_dtype: str | None
    virial_dtype: str | None
    stress_dtype: str | None
    patch_installed: bool
    tf32_allowed: bool
    policy_digest: str
    expected_observable_dtype: str = "float64"
    expected_patch_installed: bool = True

    def __post_init__(self) -> None:
        if self.expected_observable_dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("Critical-precision audit expected dtype must be float32 or float64.")

    @property
    def passed(self) -> bool:
        expected = self.expected_observable_dtype
        return (
            self.mace_version == SUPPORTED_MACE_VERSION
            and self.model_class.endswith("ScaleShiftMACE")
            and self.model_dtype in {"float32", "float64"}
            and self.energy_dtype == expected
            and self.force_dtype in {None, expected}
            and self.virial_dtype in {None, expected}
            and self.stress_dtype in {None, expected}
            and self.patch_installed == self.expected_patch_installed
            and not self.tf32_allowed
        )

    def _payload(self) -> dict[str, Any]:
        legacy = self.expected_observable_dtype == "float64" and self.expected_patch_installed
        payload = {
            "schema": MACE_CRITICAL_PRECISION_AUDIT_V1_SCHEMA if legacy else MACE_CRITICAL_PRECISION_AUDIT_SCHEMA,
            "mace_version": self.mace_version,
            "model_class": self.model_class,
            "model_dtype": self.model_dtype,
            "energy_dtype": self.energy_dtype,
            "force_dtype": self.force_dtype,
            "virial_dtype": self.virial_dtype,
            "stress_dtype": self.stress_dtype,
            "patch_installed": self.patch_installed,
            "tf32_allowed": self.tf32_allowed,
            "policy_digest": self.policy_digest,
            "passed": self.passed,
        }
        if not legacy:
            payload["expected_observable_dtype"] = self.expected_observable_dtype
            payload["expected_patch_installed"] = self.expected_patch_installed
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceCriticalPrecisionAudit":
        if payload.get("schema") not in {MACE_CRITICAL_PRECISION_AUDIT_SCHEMA, MACE_CRITICAL_PRECISION_AUDIT_V1_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported critical-precision audit schema.")
        legacy = payload.get("schema") == MACE_CRITICAL_PRECISION_AUDIT_V1_SCHEMA
        result = cls(
            mace_version=str(payload["mace_version"]),
            model_class=str(payload["model_class"]),
            model_dtype=str(payload["model_dtype"]),
            energy_dtype=str(payload["energy_dtype"]),
            force_dtype=None if payload.get("force_dtype") is None else str(payload["force_dtype"]),
            virial_dtype=None if payload.get("virial_dtype") is None else str(payload["virial_dtype"]),
            stress_dtype=None if payload.get("stress_dtype") is None else str(payload["stress_dtype"]),
            patch_installed=bool(payload["patch_installed"]),
            tf32_allowed=bool(payload["tf32_allowed"]),
            policy_digest=str(payload["policy_digest"]),
            expected_observable_dtype=("float64" if legacy else str(payload["expected_observable_dtype"])),
            expected_patch_installed=(True if legacy else bool(payload["expected_patch_installed"])),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Critical-precision audit digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class AseMdStatePrecisionAudit:
    """Audit the persistent ASE MD state before attaching the MACE calculator."""

    positions_dtype: str
    cell_dtype: str
    masses_dtype: str
    momenta_dtype: str | None
    require_momenta: bool

    @property
    def passed(self) -> bool:
        return (
            self.positions_dtype == "float64"
            and self.cell_dtype == "float64"
            and self.masses_dtype == "float64"
            and (self.momenta_dtype is None or self.momenta_dtype == "float64")
            and (not self.require_momenta or self.momenta_dtype == "float64")
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ASE_MD_STATE_PRECISION_AUDIT_SCHEMA,
            "positions_dtype": self.positions_dtype,
            "cell_dtype": self.cell_dtype,
            "masses_dtype": self.masses_dtype,
            "momenta_dtype": self.momenta_dtype,
            "require_momenta": self.require_momenta,
            "passed": self.passed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AseMdStatePrecisionAudit":
        if payload.get("schema") != ASE_MD_STATE_PRECISION_AUDIT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported ASE MD-state precision schema.")
        result = cls(
            positions_dtype=str(payload["positions_dtype"]),
            cell_dtype=str(payload["cell_dtype"]),
            masses_dtype=str(payload["masses_dtype"]),
            momenta_dtype=(
                None if payload.get("momenta_dtype") is None else str(payload["momenta_dtype"])
            ),
            require_momenta=bool(payload["require_momenta"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("ASE MD-state precision digest mismatch.")
        return result


def audit_ase_md_state_precision(
    atoms: Any,
    *,
    require_momenta: bool = False,
    fail_closed: bool = True,
) -> AseMdStatePrecisionAudit:
    """Require the persistent ASE state to remain FP64 before MD execution."""

    import numpy as np

    momenta = atoms.arrays.get("momenta")
    result = AseMdStatePrecisionAudit(
        positions_dtype=np.asarray(atoms.arrays["positions"]).dtype.name,
        cell_dtype=np.asarray(atoms.cell.array).dtype.name,
        masses_dtype=np.asarray(atoms.get_masses()).dtype.name,
        momenta_dtype=None if momenta is None else np.asarray(momenta).dtype.name,
        require_momenta=bool(require_momenta),
    )
    if fail_closed and not result.passed:
        raise TrainingDataInputError(
            f"ASE MD state is not uniformly FP64: {result.to_dict()!r}"
        )
    return result


@mace_runtime_warning_handled("critical-FP64 MACE calculator construction")
def build_mace_critical_precision_calculator(
    model_path: str,
    *,
    model_dtype: str = "float32",
    device: str = "cuda",
    policy: MaceCriticalPrecisionPolicy | None = None,
    **calculator_kwargs: Any,
) -> Any:
    """Build a Python/ASE MACE calculator with selected body dtype and FP64 globals."""

    if model_dtype not in {"float32", "float64"}:
        raise TrainingDataInputError("MACE model_dtype must be float32 or float64.")
    install_mace_critical_fp64_patch(policy)
    try:
        from mace.calculators import MACECalculator
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise TrainingDataInputError("MACE calculator construction requires mace-torch.") from exc
    return MACECalculator(
        model_paths=str(model_path),
        device=device,
        default_dtype=model_dtype,
        **calculator_kwargs,
    )


_ORIGINAL_FORWARD: Any | None = None
_ORIGINAL_CONDITIONAL_HUBER_FORCES: Any | None = None
_PATCH_INSTALLED = False


def _segment_sum_fp64(src: Any, ptr: Any) -> Any:
    """Deterministic FP64 reduction for graph-contiguous atomic values."""

    import torch

    values = src.to(dtype=torch.float64)
    pieces = [
        values[int(ptr[i].item()) : int(ptr[i + 1].item())].sum(dim=0, dtype=torch.float64)
        for i in range(int(ptr.numel() - 1))
    ]
    if pieces:
        return torch.stack(pieces, dim=0)
    out_shape = [0, *values.shape[1:]]
    return torch.empty(out_shape, dtype=torch.float64, device=values.device)


def _scatter_sum_fp64(src: Any, index: Any, *, dim_size: int) -> Any:
    import torch

    values = src.to(dtype=torch.float64)
    out_shape = list(values.shape)
    out_shape[0] = dim_size
    out = torch.zeros(out_shape, dtype=torch.float64, device=values.device)
    expanded = index
    while expanded.dim() < values.dim():
        expanded = expanded.unsqueeze(-1)
    expanded = expanded.expand_as(values)
    return out.scatter_add_(0, expanded, values)


def _critical_fp64_scale_shift_forward(
    self: Any,
    data: dict[str, Any],
    training: bool = False,
    compute_force: bool = True,
    compute_virials: bool = False,
    compute_stress: bool = False,
    compute_displacement: bool = False,
    compute_hessian: bool = False,
    compute_edge_forces: bool = False,
    compute_atomic_stresses: bool = False,
    lammps_mliap: bool = False,
) -> dict[str, Any]:
    """ScaleShiftMACE forward with FP64 global reductions and outputs."""

    import torch
    from mace.modules.utils import prepare_graph, get_outputs

    # Force training needs second derivatives through the force expression.
    # MACE/e3nn 0.3.16 does not support an FP64 scalar seed through an FP32
    # force-Jacobian path.  Optimization therefore remains entirely in the
    # user-selected model dtype.  Validation, standalone evaluation, and MD
    # use the full critical-FP64 path below, where forces are differentiated
    # from the same FP64-accumulated energy scalar.
    if training:
        if _ORIGINAL_FORWARD is None:  # pragma: no cover - installation guard
            raise RuntimeError("Critical-FP64 patch was not installed correctly.")
        return _ORIGINAL_FORWARD(
            self,
            data,
            training=training,
            compute_force=compute_force,
            compute_virials=compute_virials,
            compute_stress=compute_stress,
            compute_displacement=compute_displacement,
            compute_hessian=compute_hessian,
            compute_edge_forces=compute_edge_forces,
            compute_atomic_stresses=compute_atomic_stresses,
            lammps_mliap=lammps_mliap,
        )

    ctx = prepare_graph(
        data,
        compute_virials=False,
        compute_stress=False,
        compute_displacement=compute_displacement,
        lammps_mliap=lammps_mliap,
    )
    is_lammps = ctx.is_lammps
    num_atoms_arange = ctx.num_atoms_arange.to(torch.int64)
    num_graphs = ctx.num_graphs
    displacement = ctx.displacement
    positions = ctx.positions
    vectors = ctx.vectors
    lengths = ctx.lengths
    cell = ctx.cell
    node_heads = ctx.node_heads.to(torch.int64)
    interaction_kwargs = ctx.interaction_kwargs
    lammps_natoms = interaction_kwargs.lammps_natoms
    lammps_class = interaction_kwargs.lammps_class

    node_e0 = self.atomic_energies_fn(data["node_attrs"])[num_atoms_arange, node_heads]
    node_reference_terms = [node_e0]

    node_feats = self.node_embedding(data["node_attrs"])
    edge_attrs = self.spherical_harmonics(vectors)
    edge_feats, cutoff = self.radial_embedding(
        lengths, data["node_attrs"], data["edge_index"], self.atomic_numbers
    )

    if hasattr(self, "pair_repulsion"):
        pair_node_energy = self.pair_repulsion_fn(
            lengths, data["node_attrs"], data["edge_index"], self.atomic_numbers
        )
        if is_lammps:
            pair_node_energy = pair_node_energy[: lammps_natoms[0]]
    else:
        pair_node_energy = torch.zeros_like(node_e0)

    if hasattr(self, "joint_embedding"):
        embedding_features: dict[str, Any] = {}
        for name, _ in self.embedding_specs.items():
            embedding_features[name] = data[name]
        node_feats += self.joint_embedding(data["batch"], embedding_features)
        if hasattr(self, "embedding_readout"):
            embedding_node_energy = torch.atleast_1d(
                self.embedding_readout(node_feats, node_heads)[
                    num_atoms_arange, node_heads
                ].squeeze(-1)
            )
            node_reference_terms.append(embedding_node_energy)

    node_es_list = [pair_node_energy]
    node_feats_list: list[Any] = []
    for i, (interaction, product) in enumerate(zip(self.interactions, self.products)):
        node_attrs_slice = data["node_attrs"]
        if is_lammps and i > 0:
            node_attrs_slice = node_attrs_slice[: lammps_natoms[0]]
        node_feats, sc = interaction(
            node_attrs=node_attrs_slice,
            node_feats=node_feats,
            edge_attrs=edge_attrs,
            edge_feats=edge_feats,
            edge_index=data["edge_index"],
            cutoff=cutoff,
            first_layer=(i == 0),
            lammps_class=lammps_class,
            lammps_natoms=lammps_natoms,
        )
        if is_lammps and i == 0:
            node_attrs_slice = node_attrs_slice[: lammps_natoms[0]]
        node_feats = product(node_feats=node_feats, sc=sc, node_attrs=node_attrs_slice)
        node_feats_list.append(node_feats)

    for i, readout in enumerate(self.readouts):
        feat_idx = -1 if len(self.readouts) == 1 else i
        node_es_list.append(
            readout(node_feats_list[feat_idx], node_heads)[num_atoms_arange, node_heads]
        )

    node_feats_out = torch.cat(node_feats_list, dim=-1)
    node_inter_es = torch.sum(torch.stack(node_es_list, dim=0), dim=0)
    node_inter_es = self.scale_shift(node_inter_es, node_heads)

    node_reference = torch.sum(torch.stack(node_reference_terms, dim=0), dim=0)
    e0_64 = _segment_sum_fp64(node_reference, data["ptr"])
    inter_e_64 = _segment_sum_fp64(node_inter_es, data["ptr"])
    total_energy_64 = e0_64 + inter_e_64
    node_energy_64 = node_reference.to(torch.float64) + node_inter_es.to(torch.float64)

    need_edge_forces = (
        compute_edge_forces
        or compute_atomic_stresses
        or compute_virials
        or compute_stress
    )
    if compute_hessian:
        # Hessian evaluation is uncommon and retains the upstream helper. The
        # normal MD path below obtains atomic and edge derivatives in one
        # autograd call, avoiding a second network backward traversal.
        forces, _, _, hessian, edge_forces = get_outputs(
            energy=total_energy_64,
            positions=positions,
            displacement=displacement,
            vectors=vectors,
            cell=cell,
            training=False,
            compute_force=compute_force,
            compute_virials=False,
            compute_stress=False,
            compute_hessian=True,
            compute_edge_forces=need_edge_forces,
        )
    elif compute_force or need_edge_forces:
        inputs = []
        if compute_force:
            inputs.append(positions)
        if need_edge_forces:
            inputs.append(vectors)
        gradients = torch.autograd.grad(
            outputs=[total_energy_64],
            inputs=inputs,
            grad_outputs=[torch.ones_like(total_energy_64)],
            retain_graph=False,
            create_graph=False,
            allow_unused=True,
        )
        offset = 0
        forces = None
        edge_forces = None
        if compute_force:
            gradient = gradients[offset]
            forces = torch.zeros_like(positions) if gradient is None else -gradient
            offset += 1
        if need_edge_forces:
            gradient = gradients[offset]
            # MACE/LAMMPS edge-force convention is +dE/d(edge_vector).
            edge_forces = torch.zeros_like(vectors) if gradient is None else gradient
        hessian = None
    else:
        forces = None
        edge_forces = None
        hessian = None

    forces_64 = None if forces is None else forces.to(torch.float64)
    edge_forces_64 = None if edge_forces is None else edge_forces.to(torch.float64)
    virials_64 = None
    stress_64 = None
    atomic_virials_64 = None
    atomic_stresses_64 = None

    if edge_forces_64 is not None and (compute_virials or compute_stress or compute_atomic_stresses):
        vectors_64 = vectors.to(torch.float64)
        raw_edge_virial = torch.einsum("zi,zj->zij", edge_forces_64, vectors_64)
        raw_edge_virial = 0.5 * (raw_edge_virial + raw_edge_virial.transpose(-1, -2))
        edge_graph = data["batch"][data["edge_index"][0]]
        raw_graph_virial = _scatter_sum_fp64(
            raw_edge_virial, edge_graph, dim_size=num_graphs
        )
        virials_64 = -raw_graph_virial
        cell_64 = cell.view(-1, 3, 3).to(torch.float64)
        volume_64 = torch.linalg.det(cell_64).abs().view(-1, 1, 1)
        stress_64 = raw_graph_virial / volume_64
        stress_64 = torch.where(
            torch.abs(stress_64) < 1.0e10,
            stress_64,
            torch.zeros_like(stress_64),
        )

        if compute_atomic_stresses:
            num_atoms = positions.shape[0]
            sender = data["edge_index"][0]
            receiver = data["edge_index"][1]
            sender_sum = _scatter_sum_fp64(raw_edge_virial, sender, dim_size=num_atoms)
            receiver_sum = _scatter_sum_fp64(raw_edge_virial, receiver, dim_size=num_atoms)
            raw_atomic = 0.5 * (sender_sum + receiver_sum)
            raw_atomic = 0.5 * (raw_atomic + raw_atomic.transpose(-1, -2))
            atomic_virials_64 = -raw_atomic
            atom_volume = volume_64[data["batch"]].view(-1, 1, 1)
            atomic_stresses_64 = raw_atomic / atom_volume
            atomic_stresses_64 = torch.where(
                torch.abs(atomic_stresses_64) < 1.0e10,
                atomic_stresses_64,
                torch.zeros_like(atomic_stresses_64),
            )

    # MACE 0.3.16's force/stress loss implementation assumes predictions and
    # reference tensors share the model dtype.  Critical reductions remain
    # FP64, but differentiable training outputs are cast back only at the loss
    # boundary.  Inference/MD outputs stay FP64.
    output_forces = forces if training else forces_64
    output_edge_forces = edge_forces if training else edge_forces_64
    output_virials = (
        None
        if virials_64 is None
        else virials_64.to(dtype=positions.dtype) if training else virials_64
    )
    output_stress = (
        None
        if stress_64 is None
        else stress_64.to(dtype=positions.dtype) if training else stress_64
    )
    output_atomic_virials = (
        None
        if atomic_virials_64 is None
        else atomic_virials_64.to(dtype=positions.dtype)
        if training
        else atomic_virials_64
    )
    output_atomic_stresses = (
        None
        if atomic_stresses_64 is None
        else atomic_stresses_64.to(dtype=positions.dtype)
        if training
        else atomic_stresses_64
    )

    return {
        "energy": total_energy_64,
        "node_energy": node_energy_64,
        "interaction_energy": inter_e_64,
        "forces": output_forces,
        "edge_forces": output_edge_forces,
        "virials": output_virials,
        "stress": output_stress,
        "atomic_virials": output_atomic_virials,
        "atomic_stresses": output_atomic_stresses,
        "hessian": hessian,
        "displacement": displacement,
        "node_feats": node_feats_out,
    }


def configure_torch_critical_precision(policy: MaceCriticalPrecisionPolicy | None = None) -> None:
    """Disable TF32/reduced-FP32 matmul paths for scientific MACE execution."""

    active = MaceCriticalPrecisionPolicy() if policy is None else policy
    import torch

    torch.set_float32_matmul_precision("highest")
    if hasattr(torch.backends, "cuda") and hasattr(torch.backends.cuda, "matmul"):
        torch.backends.cuda.matmul.allow_tf32 = False
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.allow_tf32 = False
    if active.strategy == "scaleshift_mace_0.3.16_runtime_patch_v1":
        os.environ[PATCH_ENVIRONMENT_VARIABLE] = "1"
    else:
        os.environ.pop(PATCH_ENVIRONMENT_VARIABLE, None)


def install_mace_critical_fp64_patch(
    policy: MaceCriticalPrecisionPolicy | None = None,
) -> None:
    """Install the explicit MACE 0.3.16 ScaleShiftMACE runtime patch."""

    global _ORIGINAL_FORWARD, _ORIGINAL_CONDITIONAL_HUBER_FORCES, _PATCH_INSTALLED
    active = MaceCriticalPrecisionPolicy() if policy is None else policy
    configure_torch_critical_precision(active)
    try:
        import mace
        from mace.modules.models import ScaleShiftMACE
        from mace.modules import loss as mace_loss
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise TrainingDataInputError("Critical-FP64 execution requires mace-torch.") from exc
    if str(getattr(mace, "__version__", "")) != SUPPORTED_MACE_VERSION:
        raise TrainingDataInputError(
            f"Critical-FP64 patch supports mace-torch=={SUPPORTED_MACE_VERSION} only."
        )
    if not _PATCH_INSTALLED:
        _ORIGINAL_FORWARD = ScaleShiftMACE.forward
        ScaleShiftMACE.forward = _critical_fp64_scale_shift_forward
        _ORIGINAL_CONDITIONAL_HUBER_FORCES = mace_loss.conditional_huber_forces

        def _mixed_dtype_conditional_huber_forces(
            ref_forces: Any,
            pred_forces: Any,
            huber_delta: float,
            ddp: Any = None,
        ) -> Any:
            # MACE 0.3.16 allocates the work tensor from pred_forces but may
            # produce source values in the reference dtype.  Promote the
            # reference explicitly so FP64 observable outputs remain valid in
            # both training and validation loss paths.
            return _ORIGINAL_CONDITIONAL_HUBER_FORCES(
                ref_forces.to(dtype=pred_forces.dtype),
                pred_forces,
                huber_delta,
                ddp,
            )

        mace_loss.conditional_huber_forces = _mixed_dtype_conditional_huber_forces
        _PATCH_INSTALLED = True


def activate_mace_critical_precision_policy(
    policy: MaceCriticalPrecisionPolicy | None = None,
) -> None:
    """Activate one explicit profile-bound critical-precision policy.

    Historical/legacy execution uses the qualified FP64 reduction patch.  Canonical
    ``single`` instead restores native MACE arithmetic, disables TF32, and leaves
    critical/global observables in the model's FP32 dtype.
    """

    active = MaceCriticalPrecisionPolicy() if policy is None else policy
    if active.strategy == "scaleshift_mace_0.3.16_runtime_patch_v1":
        install_mace_critical_fp64_patch(active)
        return
    if active.strategy == "native_model_precision_v1":
        uninstall_mace_critical_fp64_patch()
        configure_torch_critical_precision(active)
        return
    raise TrainingDataInputError(f"Unsupported critical-precision strategy {active.strategy!r}.")


def uninstall_mace_critical_fp64_patch() -> None:
    global _ORIGINAL_FORWARD, _ORIGINAL_CONDITIONAL_HUBER_FORCES, _PATCH_INSTALLED
    if not _PATCH_INSTALLED:
        return
    from mace.modules.models import ScaleShiftMACE
    from mace.modules import loss as mace_loss

    ScaleShiftMACE.forward = _ORIGINAL_FORWARD
    mace_loss.conditional_huber_forces = _ORIGINAL_CONDITIONAL_HUBER_FORCES
    _ORIGINAL_FORWARD = None
    _ORIGINAL_CONDITIONAL_HUBER_FORCES = None
    _PATCH_INSTALLED = False
    os.environ.pop(PATCH_ENVIRONMENT_VARIABLE, None)


def mace_critical_fp64_patch_installed() -> bool:
    return bool(_PATCH_INSTALLED and os.environ.get(PATCH_ENVIRONMENT_VARIABLE) == "1")


def audit_mace_critical_precision(
    model: Any,
    output: Mapping[str, Any],
    policy: MaceCriticalPrecisionPolicy | None = None,
) -> MaceCriticalPrecisionAudit:
    active = MaceCriticalPrecisionPolicy() if policy is None else policy
    try:
        import mace
        import torch
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("Precision auditing requires mace-torch and torch.") from exc
    try:
        parameter = next(model.parameters())
    except StopIteration as exc:
        raise TrainingDataInputError("MACE model has no parameters to inspect.") from exc

    def dtype_name(value: Any) -> str | None:
        if value is None:
            return None
        if not torch.is_tensor(value):
            raise TrainingDataInputError("MACE precision audit expects tensor outputs.")
        return str(value.dtype).removeprefix("torch.")

    audit = MaceCriticalPrecisionAudit(
        mace_version=str(getattr(mace, "__version__", "unknown")),
        model_class=f"{type(model).__module__}.{type(model).__qualname__}",
        model_dtype=str(parameter.dtype).removeprefix("torch."),
        energy_dtype=dtype_name(output.get("energy")) or "",
        force_dtype=dtype_name(output.get("forces")),
        virial_dtype=dtype_name(output.get("virials")),
        stress_dtype=dtype_name(output.get("stress")),
        patch_installed=mace_critical_fp64_patch_installed(),
        tf32_allowed=bool(
            getattr(getattr(torch.backends, "cuda", object()), "matmul", object()).allow_tf32
            if hasattr(getattr(torch.backends, "cuda", object()), "matmul")
            else False
        ),
        policy_digest=active.policy_digest,
        expected_observable_dtype=active.observable_output_dtype,
        expected_patch_installed=(active.strategy == "scaleshift_mace_0.3.16_runtime_patch_v1"),
    )
    if not audit.passed:
        raise TrainingDataInputError(f"Critical-precision audit failed: {audit.to_dict()!r}")
    return audit
