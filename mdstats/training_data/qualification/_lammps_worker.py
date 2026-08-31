"""Out-of-process LAMMPS/ML-IAP execution worker for P7 qualification.

The worker exists so that the supported simulation runtime runs under its own
process group.  A crashing or hanging MD run then cannot corrupt the campaign
process, and the parent releases the runtime deterministically on success and on
exception alike.  The worker itself makes no scientific decision: it receives a
frozen request, executes it, and writes raw observations back.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from .stress import canonical_stress_tensor


def _minimum_pair_distance(positions: np.ndarray, cell: np.ndarray, pbc: bool) -> float:
    count = positions.shape[0]
    if count < 2:
        return float("inf")
    best = float("inf")
    inverse = np.linalg.inv(cell) if pbc else None
    for index in range(count - 1):
        delta = positions[index + 1 :] - positions[index]
        if pbc:
            fractional = delta @ inverse
            fractional -= np.round(fractional)
            delta = fractional @ cell
        distances = np.sqrt(np.sum(delta * delta, axis=1))
        local = float(np.min(distances))
        if local < best:
            best = local
    return best


def _local_arrays(instance) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Owned-atom positions/forces/ids, in canonical LAMMPS tag order.

    ``extract_atom`` exposes the allocated per-atom arrays, which are larger
    than the owned-atom count; taking them whole would silently mix in ghost and
    unused slots.
    """

    count = int(instance.extract_global("nlocal"))
    positions = np.array(instance.numpy.extract_atom("x"), dtype=np.float64, copy=True)[:count]
    forces = np.array(instance.numpy.extract_atom("f"), dtype=np.float64, copy=True)[:count]
    tags = np.array(instance.numpy.extract_atom("id"), dtype=np.int64, copy=True)[:count]
    order = np.argsort(tags)
    return positions[order], forces[order], tags[order]


def _cell_from_instance(instance) -> np.ndarray:
    box = instance.extract_box()
    lower, upper = np.asarray(box[0], dtype=np.float64), np.asarray(box[1], dtype=np.float64)
    xy, yz, xz = float(box[2]), float(box[3]), float(box[4])
    lengths = upper - lower
    return np.array(
        [
            [lengths[0], 0.0, 0.0],
            [xy, lengths[1], 0.0],
            [xz, yz, lengths[2]],
        ],
        dtype=np.float64,
    )


def _stress_from_instance(instance, request: dict[str, Any]) -> list[list[float]] | None:
    if not bool(request.get("include_stress", False)):
        return None
    try:
        # LAMMPS metal pressure is an intensive bar quantity.  Fetch by named
        # component, then present values in the caller's declared Voigt order
        # so the canonical converter owns permutation and sign semantics.
        source = {
            "xx": float(instance.get_thermo("pxx")),
            "yy": float(instance.get_thermo("pyy")),
            "zz": float(instance.get_thermo("pzz")),
            "xy": float(instance.get_thermo("pxy")),
            "xz": float(instance.get_thermo("pxz")),
            "yz": float(instance.get_thermo("pyz")),
        }
        order = tuple(
            str(value).lower()
            for value in request.get(
                "stress_voigt_order", ("xx", "yy", "zz", "xy", "yz", "xz")
            )
        )
        values = [source[name] for name in order]
    except Exception:
        return None
    return canonical_stress_tensor(
        np.asarray(values, dtype=np.float64),
        units="gpa",
        voigt_order=order,
        sign=float(request.get("stress_sign", 1.0)),
    ).tolist()


def _load_deployed_model(artifact_path: str) -> Any:
    """Load the exact deployed ML-IAP artifact, whatever its serialization is.

    MACE writes its unified ML-IAP model with ``torch.save``; a plain pickled
    ``MLIAPUnified`` is equally valid.  Both are accepted, and neither is
    reconstructed or repaired: the bytes on disk are what LAMMPS runs.
    """

    import pickle

    try:
        with open(artifact_path, "rb") as handle:
            return pickle.load(handle)
    except Exception:
        import torch

        return torch.load(artifact_path, map_location="cpu", weights_only=False)


def _build(request: dict[str, Any]):
    from lammps import lammps, mliap

    instance = lammps(cmdargs=["-log", "none", "-screen", "none", "-nocite"])
    mliap.activate_mliappy(instance)
    # The unified model must be resident before `pair_style ... EXISTS` runs;
    # LAMMPS resolves the already loaded object rather than a file path.
    model = _load_deployed_model(request["artifact_path"])
    mliap.load_unified(model)

    commands = [
        "units metal",
        "atom_style atomic",
        "atom_modify map array sort 0 0.0",
        "boundary p p p" if request.get("periodic", True) else "boundary f f f",
        f"read_data {request['data_path']}",
        "pair_style mliap unified EXISTS 0",
        "pair_coeff * * " + " ".join(str(v) for v in request["element_types"]),
        "neighbor 1.0 bin",
        "neigh_modify every 1 delay 0 check yes",
    ]
    for line in commands:
        instance.command(line)
    return instance


def _run(request: dict[str, Any]) -> dict[str, Any]:
    instance = _build(request)
    try:
        mode = str(request["mode"])
        if mode == "static":
            instance.command("run 0 post no")
            energy = float(instance.get_thermo("pe"))
            positions, forces, tags = _local_arrays(instance)
            return {
                "mode": "static",
                "potential_energy_ev": energy,
                "forces_ev_per_angstrom": forces.tolist(),
                "positions_angstrom": positions.tolist(),
                "atom_count": int(tags.size),
                "stress_ev_per_angstrom3": _stress_from_instance(instance, request),
            }
        if mode == "dynamics":
            timestep = float(request["timestep_femtoseconds"]) / 1000.0
            instance.command(f"timestep {timestep}")
            temperature = float(request["temperature_kelvin"])
            seed = int(request["velocity_seed"])
            instance.command(
                f"velocity all create {temperature} {seed} mom yes rot yes dist gaussian"
            )
            damping = float(request["thermostat_damping_femtoseconds"]) / 1000.0
            instance.command(
                f"fix nvt_stage all nvt temp {temperature} {temperature} {damping}"
            )
            samples: list[dict[str, float]] = []
            interval = int(request["sample_interval_steps"])
            warmup = int(request["warmup_steps"])
            for _ in range(max(1, warmup // interval)):
                instance.command(f"run {interval} pre no post no")
                positions, forces, _tags = _local_arrays(instance)
                samples.append(
                    {
                        "stage": 0.0,
                        "temperature_kelvin": float(instance.get_thermo("temp")),
                        "potential_energy_ev": float(instance.get_thermo("pe")),
                        "kinetic_energy_ev": float(instance.get_thermo("ke")),
                        "total_energy_ev": float(instance.get_thermo("etotal")),
                        "positions_angstrom": positions.tolist(),
                        "forces_ev_per_angstrom": forces.tolist(),
                        "cell_angstrom": _cell_from_instance(instance).tolist(),
                        "pbc": [bool(request.get("periodic", True))] * 3,
                        "stress_ev_per_angstrom3": _stress_from_instance(instance, request),
                    }
                )
            instance.command("unfix nvt_stage")
            instance.command("fix nve_stage all nve")
            propagation = int(request["propagation_steps"])
            nve: list[dict[str, float]] = []
            minimum_distance = float("inf")
            maximum_force = 0.0
            for _ in range(max(1, propagation // interval)):
                instance.command(f"run {interval} pre no post no")
                positions, forces, _tags = _local_arrays(instance)
                cell = _cell_from_instance(instance)
                minimum_distance = min(
                    minimum_distance,
                    _minimum_pair_distance(positions, cell, bool(request.get("periodic", True))),
                )
                maximum_force = max(
                    maximum_force,
                    float(np.max(np.linalg.norm(forces, axis=1)))
                    if forces.size
                    else 0.0,
                )
                nve.append(
                    {
                        "stage": 1.0,
                        "temperature_kelvin": float(instance.get_thermo("temp")),
                        "potential_energy_ev": float(instance.get_thermo("pe")),
                        "kinetic_energy_ev": float(instance.get_thermo("ke")),
                        "total_energy_ev": float(instance.get_thermo("etotal")),
                        "nve_temperature_kelvin": float(instance.get_thermo("temp")),
                        "positions_angstrom": positions.tolist(),
                        "forces_ev_per_angstrom": forces.tolist(),
                        "cell_angstrom": cell.tolist(),
                        "pbc": [bool(request.get("periodic", True))] * 3,
                        "stress_ev_per_angstrom3": _stress_from_instance(instance, request),
                    }
                )
            positions, _forces, tags = _local_arrays(instance)
            return {
                "mode": "dynamics",
                "warmup_samples": samples,
                "propagation_samples": nve,
                "minimum_pair_distance_angstrom": float(minimum_distance),
                "maximum_force_ev_per_angstrom": float(maximum_force),
                "final_positions_angstrom": positions.tolist(),
                "atom_count": int(tags.size),
            }
        raise ValueError(f"Unsupported LAMMPS worker mode {mode!r}.")
    finally:
        try:
            instance.close()
        except Exception:
            pass


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: _lammps_worker REQUEST_JSON RESPONSE_JSON", file=sys.stderr)
        return 2
    request = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    try:
        payload = {"ok": True, "result": _run(request)}
    except BaseException as exc:  # noqa: BLE001 - the parent must see the reason
        payload = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    Path(argv[2]).write_text(json.dumps(payload), encoding="utf-8")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":  # pragma: no cover - process entry point
    raise SystemExit(main(sys.argv))
