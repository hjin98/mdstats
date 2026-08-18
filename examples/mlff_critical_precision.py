"""Attach an FP32-body/critical-FP64 MACE model to an ASE MD state."""

from ase.io import read
from ase.md.velocitydistribution import MaxwellBoltzmannDistribution

from mdstats import (
    audit_ase_md_state_precision,
    build_mace_critical_precision_calculator,
)

MODEL_PATH = "fine_tuned.model"
STRUCTURE_PATH = "POSCAR"

atoms = read(STRUCTURE_PATH)
MaxwellBoltzmannDistribution(atoms, temperature_K=700.0)

state_audit = audit_ase_md_state_precision(atoms, require_momenta=True)
calculator = build_mace_critical_precision_calculator(
    MODEL_PATH,
    model_dtype="float32",  # change to float64 for a full-FP64 model body
    device="cuda",
)
atoms.calc = calculator

print(state_audit.to_dict())
print("Energy dtype and forces are critical-FP64 under the mdstats adapter.")
