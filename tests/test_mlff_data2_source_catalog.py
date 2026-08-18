from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

import mdstats


def _atominfo(elements: tuple[str, ...]) -> str:
    unique: list[str] = []
    for symbol in elements:
        if symbol not in unique:
            unique.append(symbol)
    type_index = {symbol: index + 1 for index, symbol in enumerate(unique)}
    atoms = "".join(
        f"<rc><c>{symbol}</c><c>{type_index[symbol]}</c></rc>"
        for symbol in elements
    )
    types = "".join(
        f"<rc><c>{elements.count(symbol)}</c><c>{symbol}</c><c>1.0</c><c>1</c>"
        f"<c>PAW_PBE {symbol} test</c></rc>"
        for symbol in unique
    )
    return f'''<atominfo><atoms>{len(elements)}</atoms><types>{len(unique)}</types>
      <array name="atoms"><set>{atoms}</set></array>
      <array name="atomtypes"><set>{types}</set></array>
    </atominfo>'''


def _vectors(elements: tuple[str, ...], *, value: str) -> str:
    return "".join(f"<v>{value}</v>" for _ in elements)


def _vasprun(
    elements: tuple[str, ...],
    *,
    gga: str = "PE",
    ediff: float = 1.0e-5,
    isym: int = 0,
    second_energy: bool = True,
) -> str:
    calculation_2 = "" if not second_energy else f'''
  <calculation>
    <scstep><energy><i name="e_fr_energy">-9.9</i><i name="e_0_energy">-9.8</i></energy></scstep>
    <structure><crystal><varray name="basis"><v>10 0 0</v><v>0 10 0</v><v>0 0 10</v></varray></crystal>
      <varray name="positions">{_vectors(elements, value="0.1 0 0")}</varray></structure>
    <varray name="forces">{_vectors(elements, value="0.1 0 0")}</varray>
    <varray name="stress"><v>-100 0 0</v><v>0 -100 0</v><v>0 0 -100</v></varray>
    <energy><i name="e_fr_energy">-9.9</i><i name="e_0_energy">-9.8</i><i name="e_wo_entrp">-9.85</i>
      <i name="kinetic">0.5</i><i name="nosepot">0</i><i name="nosekinetic">0</i>
      <i name="lattice kinetic">0</i><i name="total">-9.4</i></energy>
  </calculation>'''
    nsw = 2 if second_energy else 1
    gamma = " ".join("10" for _ in sorted(set(elements)))
    return f'''<?xml version="1.0"?>
<modeling>
  <generator><i name="program" type="string">vasp</i><i name="version" type="string">6.4.2</i><i name="subversion" type="string">test</i></generator>
  <incar>
    <i name="IBRION" type="int">0</i><i name="MDALGO" type="int">3</i><i name="SMASS">-3</i><i name="ISIF" type="int">2</i>
    <v name="LANGEVIN_GAMMA">{gamma}</v><i name="GGA" type="string">{gga}</i>
    <i name="ISMEAR" type="int">0</i><i name="SIGMA">0.05</i><i name="ISPIN" type="int">1</i>
    <i name="LDAU" type="logical">F</i><i name="ENCUT">520</i><i name="LASPH" type="logical">T</i>
    <i name="PREC" type="string">Accurate</i><i name="LREAL" type="logical">F</i>
  </incar>
  <kpoints><generation param="Gamma"><v name="divisions">1 1 1</v></generation>
    <varray name="kpointlist"><v>0 0 0</v></varray><varray name="weights"><v>1</v></varray></kpoints>
  <parameters>
    <separator name="electronic"><i name="EDIFF">{ediff}</i><i name="NELM" type="int">100</i>
      <i name="NELMIN" type="int">2</i><i name="ALGO" type="string">Normal</i>
      <i name="GGA" type="string">{gga}</i><i name="ISMEAR" type="int">0</i><i name="SIGMA">0.05</i>
      <i name="ISPIN" type="int">1</i><i name="LDAU" type="logical">F</i>
      <i name="ENCUT">520</i><i name="LASPH" type="logical">T</i>
      <i name="PREC" type="string">Accurate</i><i name="LREAL" type="logical">F</i>
    </separator>
    <separator name="ionic"><i name="IBRION" type="int">0</i><i name="NSW" type="int">{nsw}</i><i name="POTIM">1</i>
      <i name="MDALGO" type="int">3</i><i name="SMASS">-3</i><i name="ISIF" type="int">2</i><i name="ISYM" type="int">{isym}</i>
      <v name="LANGEVIN_GAMMA">{gamma}</v>
    </separator>
  </parameters>
  {_atominfo(elements)}
  <structure name="initialpos"><crystal><varray name="basis"><v>10 0 0</v><v>0 10 0</v><v>0 0 10</v></varray></crystal>
    <varray name="positions">{_vectors(elements, value="0 0 0")}</varray></structure>
  <calculation>
    <scstep><energy><i name="e_fr_energy">-10</i><i name="e_0_energy">-9.9</i></energy></scstep>
    <structure><crystal><varray name="basis"><v>10 0 0</v><v>0 10 0</v><v>0 0 10</v></varray></crystal>
      <varray name="positions">{_vectors(elements, value="0 0 0")}</varray></structure>
    <varray name="forces">{_vectors(elements, value="0.1 0 0")}</varray>
    <varray name="stress"><v>-100 0 0</v><v>0 -100 0</v><v>0 0 -100</v></varray>
    <energy><i name="e_fr_energy">-10</i><i name="e_0_energy">-9.9</i><i name="e_wo_entrp">-9.95</i>
      <i name="kinetic">0.5</i><i name="nosepot">0</i><i name="nosekinetic">0</i>
      <i name="lattice kinetic">0</i><i name="total">-9.5</i></energy>
  </calculation>{calculation_2}
</modeling>'''


def _write(root: Path, name: str, elements: tuple[str, ...], **kwargs) -> Path:
    directory = root / name
    directory.mkdir(parents=True)
    path = directory / "vasprun.xml"
    path.write_text(_vasprun(elements, **kwargs), encoding="utf-8")
    return path


def test_manifest_discovery_is_deterministic_and_does_not_infer_conditions(tmp_path: Path) -> None:
    _write(tmp_path, "Li_300K", ("Li", "O"))
    _write(tmp_path, "Na_700K", ("Na", "O"))
    first = mdstats.discover_vasp_manifest(tmp_path, dataset_id="example", system_profile="lta")
    second = mdstats.discover_vasp_manifest(tmp_path, dataset_id="example", system_profile="lta")
    assert first == second
    assert first.content_digest == second.content_digest
    assert tuple(run.run_id for run in first.runs) == ("Li_300K", "Na_700K")
    assert all(not run.assertions for run in first.runs)
    assert mdstats.TrainingDataManifest.from_dict(first.to_dict()) == first



def test_manifest_yaml_load_round_trip(tmp_path: Path) -> None:
    yaml = pytest.importorskip("yaml")
    _write(tmp_path, "run", ("Li", "O"))
    manifest = mdstats.discover_vasp_manifest(tmp_path, dataset_id="yaml-example")
    path = tmp_path / "dataset.yaml"
    path.write_text(yaml.safe_dump(manifest.to_dict(), sort_keys=True), encoding="utf-8")
    loaded = mdstats.TrainingDataManifest.load(path)
    assert loaded == manifest
    assert loaded.content_digest == manifest.content_digest

def test_named_energy_policy_rejects_missing_or_incomplete_channel(tmp_path: Path) -> None:
    path = _write(tmp_path, "run", ("Li", "O"))
    bundle = mdstats.read_vasp_run_controls(path)
    selected = mdstats.select_vasp_energy_channel(
        bundle.energy_catalog,
        source_control_bundle_signature=bundle.signature,
    )
    assert selected.source_name == "e_fr_energy"
    assert selected.output_key == "REF_energy"
    assert selected.frame_count == 2

    policy = mdstats.VaspEnergyLabelPolicy(channel="not-present")
    with pytest.raises(mdstats.TrainingDataInputError, match="absent"):
        mdstats.select_vasp_energy_channel(
            bundle.energy_catalog,
            source_control_bundle_signature=bundle.signature,
            policy=policy,
        )


def test_source_catalog_groups_quality_variants_and_splits_theory_domains(tmp_path: Path) -> None:
    _write(tmp_path, "li", ("Li", "Al", "Si", "O", "O"), ediff=1e-5)
    _write(tmp_path, "na", ("Na", "Al", "Si", "O", "O"), ediff=1e-6)
    _write(tmp_path, "k_lda", ("K", "Al", "Si", "O", "O"), gga="91")
    manifest = mdstats.discover_vasp_manifest(tmp_path, dataset_id="lta", system_profile="lta")
    catalog = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)

    assert len(catalog.sources) == 3
    assert len(catalog.label_domains.domains) == 2
    li_domain = catalog.source("li").label_domain_id
    na_domain = catalog.source("na").label_domain_id
    k_domain = catalog.source("k_lda").label_domain_id
    assert li_domain == na_domain
    assert k_domain != li_domain
    shared = next(domain for domain in catalog.label_domains.domains if domain.domain_id == li_domain)
    assert "numerical_quality_variants" in shared.quality_flags
    assert catalog.source("li").ensemble == "NVT"
    assert catalog.source("li").composition.as_dict()["Li"] == 1
    assert len(catalog.atomic_reference_identifiability.domain_reports) == 2
    atomic_report = catalog.atomic_reference_identifiability.report_for_domain(li_domain)
    assert atomic_report.null_space_dimension > 0
    assert atomic_report.outcome.value == (
        "rank_deficient_but_fixed_domain_usable"
    )

    rebuilt = mdstats.TrainingDataSourceCatalog.from_dict(catalog.to_dict())
    assert rebuilt == catalog
    assert rebuilt.content_digest == catalog.content_digest


def test_unresolved_theory_fails_closed_by_default(tmp_path: Path) -> None:
    path = _write(tmp_path, "run", ("Li", "O"))
    text = path.read_text(encoding="utf-8").replace(
        '<i name="GGA" type="string">PE</i>', ""
    )
    path.write_text(text, encoding="utf-8")
    manifest = mdstats.discover_vasp_manifest(tmp_path, dataset_id="unresolved")
    with pytest.raises(mdstats.TrainingDataInputError, match="Unresolved label domains"):
        mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)

    catalog = mdstats.build_training_data_source_catalog(
        manifest,
        base_directory=tmp_path,
        source_policy=mdstats.SourceAuditPolicy(fail_on_unresolved_label_domain=False),
    )
    assert catalog.label_domains.unresolved_source_ids == ("run",)
    assert catalog.source("run").label_domain_id is None


def test_atomic_reference_identifiability_full_rank_and_tamper_rejection() -> None:
    full = mdstats.analyze_atomic_reference_identifiability(
        {"h": {"H": 2}, "o": {"O": 2}}
    )
    assert full.rank == 2
    assert full.null_space_dimension == 0
    assert full.outcome.value == "identified"
    assert full.condition_number == pytest.approx(1.0)

    deficient = mdstats.analyze_atomic_reference_identifiability(
        {"a": {"Al": 2, "Si": 2, "O": 8}, "b": {"Al": 2, "Si": 2, "O": 8}}
    )
    assert deficient.rank == 1
    assert deficient.null_space_dimension == 2
    assert deficient.condition_number is None
    payload = deficient.to_dict()
    assert mdstats.AtomicReferenceIdentifiabilityReport.from_dict(payload) == deficient
    tampered = deepcopy(payload)
    tampered["rank"] = 2
    with pytest.raises((mdstats.TrainingDataInputError, mdstats.TrainingDataSerializationError)):
        mdstats.AtomicReferenceIdentifiabilityReport.from_dict(tampered)


def test_label_compatibility_decision_distinguishes_quality_and_theory(tmp_path: Path) -> None:
    p1 = _write(tmp_path, "a", ("Li", "O"), ediff=1e-5)
    p2 = _write(tmp_path, "b", ("Li", "O"), ediff=1e-6)
    p3 = _write(tmp_path, "c", ("Li", "O"), gga="91")
    manifest = mdstats.discover_vasp_manifest(tmp_path, dataset_id="compat")
    catalog = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)
    a = catalog.source("a").electronic_structure
    b = catalog.source("b").electronic_structure
    c = catalog.source("c").electronic_structure
    assert mdstats.compare_label_fingerprints(a, b).outcome.value == (
        "compatible_with_quality_flag"
    )
    assert mdstats.compare_label_fingerprints(a, c).outcome.value == (
        "separate_label_domain"
    )


def test_overlapping_paw_dataset_conflict_forces_separate_domain(tmp_path: Path) -> None:
    _write(tmp_path, "standard", ("Li", "O"))
    path = _write(tmp_path, "alternate", ("Li", "O"))
    text = path.read_text(encoding="utf-8").replace(
        "PAW_PBE Li test", "PAW_PBE Li_sv test"
    )
    path.write_text(text, encoding="utf-8")

    manifest = mdstats.discover_vasp_manifest(tmp_path, dataset_id="paw-conflict")
    catalog = mdstats.build_training_data_source_catalog(manifest, base_directory=tmp_path)

    assert len(catalog.label_domains.domains) == 2
    standard = catalog.source("standard")
    alternate = catalog.source("alternate")
    decision = mdstats.compare_label_fingerprints(
        standard.electronic_structure,
        alternate.electronic_structure,
    )
    assert decision.outcome.value == "separate_label_domain"
    assert "PAW" in " ".join(decision.reasons)


def test_manifest_discovery_preserves_flat_named_xml_identity(tmp_path: Path) -> None:
    (tmp_path / "LTA_Li.300K.init.xml").write_text(_vasprun(("Li", "O")), encoding="utf-8")
    (tmp_path / "LTA_Na.700K.init.xml").write_text(_vasprun(("Na", "O")), encoding="utf-8")
    manifest = mdstats.discover_vasp_manifest(
        tmp_path,
        dataset_id="flat-archive",
        system_profile="lta",
        pattern="*.xml",
    )
    assert tuple(run.run_id for run in manifest.runs) == (
        "LTA_Li.300K.init",
        "LTA_Na.700K.init",
    )
    assert tuple(run.vasprun for run in manifest.runs) == (
        "LTA_Li.300K.init.xml",
        "LTA_Na.700K.init.xml",
    )


def test_manifest_discovery_keeps_root_vasprun_legacy_identity(tmp_path: Path) -> None:
    (tmp_path / "vasprun.xml").write_text(_vasprun(("Li", "O")), encoding="utf-8")
    manifest = mdstats.discover_vasp_manifest(tmp_path, dataset_id="root-vasprun")
    assert tuple(run.run_id for run in manifest.runs) == ("run",)
    assert tuple(run.vasprun for run in manifest.runs) == ("vasprun.xml",)


def test_source_catalog_accepts_trailing_interrupted_vasprun_and_records_warning(tmp_path: Path) -> None:
    path = _write(tmp_path, "interrupted", ("K", "Al", "Si", "O", "O"))
    text = path.read_text(encoding="utf-8")
    marker = "  </calculation>\n</modeling>"
    assert text.endswith(marker)
    path.write_text(text[: -len(marker)], encoding="utf-8")

    manifest = mdstats.discover_vasp_manifest(tmp_path, dataset_id="interrupted-source")
    with pytest.warns(UserWarning, match="interrupted VASP XML"):
        catalog = mdstats.build_training_data_source_catalog(
            manifest,
            base_directory=tmp_path,
        )

    source = catalog.source("interrupted")
    assert source.frame_count == 2
    assert source.composition.reduced_formula == "AlKO2Si"
    assert any("Interrupted vasprun.xml" in note for note in source.assessment_notes)
