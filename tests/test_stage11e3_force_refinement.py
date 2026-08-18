from __future__ import annotations

import copy
import numpy as np
import pytest

import mdstats
from mdstats.analysis.density import (
    AttractorGeometry, AttractorLocalChart, CurvatureClass, DensityAttractor,
    DensityAttractorCatalog, DensityAttractorOptions, DensityAttractorResourcePolicy,
    ForceEvidenceStatus, ForceRefinementCatalog, ForceRefinementInputError,
    ForceRefinementResourceError, GaussianKernelCovariance, LocalChartKind,
    LocalMeanForceOptions, LocalMeanForceResourcePolicy, PeriodicDensityDomain,
    SpeciesDensityOptions, SpeciesDensityResourcePolicy, prepare_density_attractor_catalog,
    prepare_force_refinement_catalog, prepare_periodic_species_density,
)
from mdstats.analysis.site_samples import (
    EquilibriumStatus, PMFTemperatureProvenance, SamplingStateProvenance,
    StationarityStatus, prepare_framework_aligned_ion_sample_catalog,
)
from mdstats.collection import AtomisticFrameCollection
from mdstats.coordinates import (
    EvidenceState, ForceSourceProvenance, FrameRegistrationPolicy,
    prepare_frame_registration, prepare_source_coordinate_contract,
)
from mdstats.provenance import FrameCollectionProvenance


def _pipeline(K=np.diag([4.0, 6.0, 8.0]), *, force=True, pmf=True, n=72):
    t=np.arange(n,dtype=float)
    off=np.column_stack([0.045*np.sin(2*np.pi*t/17),0.035*np.cos(2*np.pi*t/19),0.025*np.sin(2*np.pi*t/23+0.4)])
    pos=np.zeros((n,2,3)); pos[:,0]=[0.1,0.1,0.1]; pos[:,1]=0.5+off
    forces=None
    if force:
        forces=np.zeros_like(pos); forces[:,1]=-(off@np.asarray(K,float))
    c=AtomisticFrameCollection(
        frame_semantics='trajectory', frame_ids=np.arange(n,dtype=np.int64),
        atomic_numbers=np.array([8,11],np.int32), masses=np.array([15.999,22.989769]),
        pbc=np.ones(3,bool), steps=np.arange(n,dtype=np.int64), times=np.arange(n,dtype=float),
        cells=np.repeat(np.eye(3)[None],n,axis=0), origins=np.zeros((n,3)),
        fractional_positions=pos, velocities=np.zeros_like(pos), forces=forces,
        provenance=FrameCollectionProvenance(source_format='synthetic-e3',source_files=('synthetic',),
            velocity_source='synthetic',coordinate_normalization='native',stress_source=None,units_source='internal'))
    fp=ForceSourceProvenance(
        physical_force_complete=EvidenceState.PRESENT if force else EvidenceState.ABSENT,
        bias_or_constraint_force=EvidenceState.ABSENT,
        stochastic_or_thermostat_force=EvidenceState.ABSENT)
    source=prepare_source_coordinate_contract(c,force_provenance=fp)
    reg=prepare_frame_registration(c,policy=FrameRegistrationPolicy(spatial_policy='physical',require_fixed_registered_cell=True),source_contract=source)
    state=SamplingStateProvenance(EquilibriumStatus.DECLARED_EQUILIBRIUM,StationarityStatus.TESTED_STATIONARY,'synthetic') if pmf else SamplingStateProvenance()
    temp=PMFTemperatureProvenance.declared_constant(300,source='synthetic') if pmf else PMFTemperatureProvenance()
    cat=prepare_framework_aligned_ion_sample_catalog(c,reg,species_atomic_number=11,species_label='Na',sampling_state=state,pmf_temperature=temp)
    dom=PeriodicDensityDomain(cell=np.eye(3),registration_signature=reg.signature)
    kernel=GaussianKernelCovariance.isotropic_cartesian(0.06,dom)
    estimate=prepare_periodic_species_density(cat,dom,kernel,
        options=SpeciesDensityOptions(grid_shape=(12,12,12),minimum_effective_samples=1,query_batch_size=256,sample_batch_size=72),
        resources=SpeciesDensityResourcePolicy(max_grid_nodes=5000,max_samples=1000,max_image_terms=100_000_000,max_workspace_bytes=128*1024**2,max_output_bytes=128*1024**2,max_blocks=5000))
    attractors=prepare_density_attractor_catalog(estimate,
        options=DensityAttractorOptions(minimum_point_curvature=0.0,ridge_density_fraction=0.6,minimum_ridge_nodes=10),
        resources=DensityAttractorResourcePolicy(max_grid_nodes=5000,max_neighbor_edges=200_000,max_attractors=20,max_serialized_nodes=5000))
    return cat,estimate,attractors


def _run(cat,estimate,attractors, **kwargs):
    options=LocalMeanForceOptions(minimum_effective_samples=2,minimum_fit_samples=12,minimum_stiffness=1e-6,
                                  chart_radius_factor=2.0,uncertainty_blocks=4,**kwargs)
    resources=LocalMeanForceResourcePolicy(max_grid_nodes=5000,max_force_samples=1000,max_kernel_terms=100_000_000,
                                            max_workspace_bytes=128*1024**2,max_output_bytes=128*1024**2,max_attractors=20)
    return prepare_force_refinement_catalog(cat,estimate,attractors,options=options,resources=resources)


def test_harmonic_well_recovers_center_stiffness_and_matched_field():
    K=np.diag([4.0,6.0,8.0]); cat,estimate,attractors=_pipeline(K)
    result=_run(cat,estimate,attractors)
    assert len(result.refinements)==len(attractors.attractors)==1
    fit=result.refinements[0]
    assert fit.evidence_status is ForceEvidenceStatus.RESOLVED
    assert fit.curvature_class is CurvatureClass.STABLE_POINT
    np.testing.assert_allclose(fit.stiffness_eigenvalues,[4,6,8],rtol=2e-12,atol=2e-12)
    np.testing.assert_allclose(fit.force_center_fractional,[0.5,0.5,0.5],atol=2e-12)
    assert fit.center_within_chart is True and fit.fit_rank==9
    assert result.mean_force_field is not None
    assert np.count_nonzero(result.mean_force_field.support_mask)>0
    assert result.mean_force_field.standard_error_covector is not None
    assert fit.residence_covariance_orthonormal is not None
    assert fit.harmonic_covariance_orthonormal is not None
    assert fit.density_force_residual_norm is not None


def test_unstable_force_curvature_is_not_reported_as_stable_well():
    cat,estimate,attractors=_pipeline(np.diag([-2.0,5.0,7.0]))
    fit=_run(cat,estimate,attractors).refinements[0]
    assert fit.evidence_status is ForceEvidenceStatus.RESOLVED
    assert fit.curvature_class is CurvatureClass.SADDLE_OR_UNSTABLE
    assert fit.force_center_fractional is not None


def test_annular_geometry_preserves_soft_direction_without_imposing_point_center():
    cat,estimate,base=_pipeline(np.diag([0.0,5.0,7.0]))
    old=base.attractors[0]
    nodes=np.asarray([old.representative_node_index],dtype=np.int64)
    chart=AttractorLocalChart(LocalChartKind.ANNULAR,old.anchor_fractional,nodes,0.2,np.asarray([0.0]))
    ridge=DensityAttractor(old.attractor_id,AttractorGeometry.RIDGE_OR_MANIFOLD,old.anchor_fractional,
        old.representative_node_index,nodes,old.peak_density,old.basin_probability,1,
        old.orthonormal_hessian_eigenvalues,True,chart)
    altered=DensityAttractorCatalog(base.density_estimate_signature,base.domain_signature,base.covariance_signature,
        base.options,base.cell_complex,(ridge,),base.saddles,base.provisional_cores,base.topology_certificate,base.refinement_history,base.metadata)
    fit=_run(cat,estimate,altered).refinements[0]
    assert fit.curvature_class is CurvatureClass.SOFT_MANIFOLD
    assert fit.force_center_fractional is None
    assert fit.stiffness_eigenvalues[0]==pytest.approx(0.0,abs=1e-11)


def test_missing_or_inadmissible_forces_preserve_spatial_attractors():
    cat,estimate,attractors=_pipeline(force=False,pmf=False)
    result=_run(cat,estimate,attractors)
    assert result.mean_force_field is None
    assert len(result.refinements)==len(attractors.attractors)
    assert result.refinements[0].evidence_status is ForceEvidenceStatus.FORCE_UNAVAILABLE
    cat2,estimate2,attractors2=_pipeline(force=True,pmf=False)
    result2=_run(cat2,estimate2,attractors2)
    assert result2.mean_force_field is None
    assert result2.refinements[0].evidence_status is ForceEvidenceStatus.PMF_PROVENANCE_REJECTED


def test_rank_failure_lowers_force_status_without_deleting_candidate():
    cat,estimate,attractors=_pipeline(n=10)
    result=prepare_force_refinement_catalog(cat,estimate,attractors,
        options=LocalMeanForceOptions(minimum_fit_samples=12,minimum_effective_samples=1),
        resources=LocalMeanForceResourcePolicy(max_grid_nodes=5000,max_force_samples=1000,max_kernel_terms=100_000_000,max_workspace_bytes=128*1024**2,max_output_bytes=128*1024**2,max_attractors=20))
    assert len(result.refinements)==1
    assert result.refinements[0].evidence_status is ForceEvidenceStatus.INSUFFICIENT_LOCAL_SUPPORT


def test_serialization_replay_and_tamper_rejection():
    cat,estimate,attractors=_pipeline(); result=_run(cat,estimate,attractors)
    replay=ForceRefinementCatalog.from_dict(result.to_dict())
    assert replay.signature==result.signature
    payload=copy.deepcopy(result.to_dict()); payload['refinements'][0]['fit_rank']=8
    with pytest.raises(ForceRefinementInputError): ForceRefinementCatalog.from_dict(payload)


def test_resource_preflight_and_source_binding_fail_closed():
    cat,estimate,attractors=_pipeline()
    with pytest.raises(ForceRefinementResourceError):
        prepare_force_refinement_catalog(cat,estimate,attractors,resources=LocalMeanForceResourcePolicy(max_grid_nodes=10))
    altered=copy.copy(estimate); object.__setattr__(altered,'catalog_signature','f'*64)
    with pytest.raises(ForceRefinementInputError): prepare_force_refinement_catalog(cat,altered,attractors)


def test_public_api_and_stage_metadata_are_stable():
    assert mdstats.FORCE_REFINEMENT_STAGE=='11E3'
    assert mdstats.prepare_force_refinement_catalog is prepare_force_refinement_catalog
    cat,estimate,attractors=_pipeline(); result=_run(cat,estimate,attractors)
    assert result.metadata['spatial_attractors_preserved'] is True
    assert result.metadata['global_pmf_reconstruction_performed'] is False
