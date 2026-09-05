"""The public post-production qualification command family.

The semantic split is frozen: ``run`` executes or resumes nonlocked
qualification and may stop truthfully in ``waiting_for_reference``; ``status`` is
observational and mutates nothing; ``activate-locked`` is the only path that
opens locked evidence, and it is never reached automatically from ``advance``.
"""

from __future__ import annotations

from typing import Any

from ..campaign_post_selection import PostSelectionError
from .components import ComponentStatus
from .errors import QualificationError, QualificationUnavailableError
from .record import QualificationVerdict
from .runtime import (
    activate_locked_test,
    build_qualification_session,
    execute_nonlocked_components,
    resolve_current_locked_activation,
    resolve_current_qualification_verdict,
    run_qualification,
)

QUALIFICATION_STAGE = "post_production_qualification"


def _seams(args: Any) -> dict[str, Any]:
    """Bounded numerical seams, all strictly below the owner boundary."""

    return {
        "trainer": getattr(args, "_external_post_selection_trainer", None),
        "inference_evaluator": getattr(args, "_external_inference_evaluator", None),
        "deployment_exporter": getattr(args, "_external_deployment_exporter", None),
        "mliap_builder": getattr(args, "_external_mliap_builder", None),
        "deployed_evaluator": getattr(args, "_external_deployed_evaluator", None),
        "dynamics_runner": getattr(args, "_external_dynamics_runner", None),
        "case_workers": int(getattr(args, "case_workers", 1) or 1),
    }


def _no_publication_message() -> str:
    return (
        "No current final-production publication exists yet. Qualification "
        "consumes an already frozen product; run `train-production` first."
    )


def execute_qualification_run(args: Any) -> int:
    """`qualification run`: execute/resume nonlocked publication qualification."""

    from .._campaign_cli_core import (
        CampaignStore,
        StageState,
        _load_config,
        _mark_stage,
        _ok,
        _print_header,
        _warn,
    )

    cfg, paths = _load_config(args.config)
    store = CampaignStore(paths.state_db)
    _print_header("Post-production qualification of the frozen final publication")
    session = build_qualification_session(cfg, paths, store, **_seams(args))
    if session is None:
        raise QualificationError(_no_publication_message())
    _mark_stage(
        store,
        paths,
        QUALIFICATION_STAGE,
        StageState.RUNNING,
        f"qualifying publication {session.binding.publication_digest[:12]}",
    )
    try:
        record, components = run_qualification(session, store, paths)
    except QualificationUnavailableError as exc:
        _mark_stage(store, paths, QUALIFICATION_STAGE, StageState.FAILED, str(exc))
        raise
    except Exception as exc:
        _mark_stage(store, paths, QUALIFICATION_STAGE, StageState.FAILED, str(exc))
        raise
    for evidence in components:
        line = f"  {evidence.component:<24} {evidence.status.value:<22} {evidence.reason_code}"
        print(line, flush=True)
    if record.verdict is QualificationVerdict.WAITING_FOR_REFERENCE:
        _warn(
            "qualification is waiting for external reference evidence; the exact "
            f"request is published under {session.reference_root!s}"
        )
        _mark_stage(store, paths, QUALIFICATION_STAGE, StageState.RUNNING, record.reason_code)
        print("Next: supply the requested reference bundle, then rerun `qualification run`.", flush=True)
        return 0
    if record.verdict is QualificationVerdict.REJECTED:
        _mark_stage(store, paths, QUALIFICATION_STAGE, StageState.FAILED, record.reason_code)
        raise QualificationError(
            "Post-production qualification rejected the exact frozen publication "
            f"({record.reason_code}). This is a release result for that exact "
            "product: no target size, cross-validation acceptance, production "
            "member, or threshold is changed by it."
        )
    if record.verdict is QualificationVerdict.INCOMPLETE:
        _mark_stage(store, paths, QUALIFICATION_STAGE, StageState.RUNNING, record.reason_code)
        _ok("every completed nonlocked component satisfied the frozen policy")
        print("Next: `qualification activate-locked` to open the one-shot locked test.", flush=True)
        return 0
    _mark_stage(store, paths, QUALIFICATION_STAGE, StageState.COMPLETE, record.reason_code)
    _ok(f"release qualification verdict: {record.verdict.value}")
    return 0


def execute_qualification_status(args: Any) -> int:
    """`qualification status`: observational only; mutates no scientific state.

    The command runs entirely under the observational capability, so the store
    is opened read-only, path resolution creates nothing, and no nested owner
    can write.  It reports what durable qualification evidence says rather than
    building a session to find out -- describing a qualification must not be a
    way of performing one.
    """

    from .._campaign_cli_core import (
        CampaignStore,
        _load_config,
        _ok,
        _print_header,
        _warn,
        observational_campaign_state,
    )
    from ..campaign_lifecycle import campaign_owner_snapshot
    from .observation import observe_current_qualification
    from .spec import resolve_qualification_spec_identity

    with observational_campaign_state():
        cfg, paths = _load_config(args.config, ensure=False)
        _print_header("Post-production qualification status")
        if not paths.state_db.is_file():
            _warn(_no_publication_message())
            return 0
        store = CampaignStore(paths.state_db, create=False)
        try:
            # One read transaction spans the target-size revision, the binding
            # derived from it, and every P7 pointer row this answer interprets,
            # so the qualification state reported is one ancestry that existed.
            _revision, binding, pointers = campaign_owner_snapshot(store)
            if binding is None:
                _warn(_no_publication_message())
                return 0
            observation = observe_current_qualification(
                paths,
                binding,
                pointers,
                specification_digest=resolve_qualification_spec_identity(
                    cfg
                ).content_digest,
            )
        finally:
            store.close()

    print(f"  canonical generation   {observation.generation}", flush=True)
    print(f"  selected binding       {observation.binding_digest[:16]}", flush=True)
    if not observation.started:
        _warn(
            "no qualification plan is current for this publication; run "
            "`qualification run` to open one"
        )
        return 0
    print(f"  qualification plan     {str(observation.plan_digest)[:16]}", flush=True)
    # The attempt is named by the authenticated plan; an unauthenticated plan
    # names no attempt, and status says so rather than guessing a directory.
    print(
        "  attempt identity       "
        + (
            observation.attempt_identity[:16]
            if observation.attempt_identity is not None
            else "unresolved (the current plan does not authenticate)"
        ),
        flush=True,
    )
    if observation.attempt_state is not None:
        print(f"  attempt state          {observation.attempt_state}", flush=True)
    for component, state in observation.component_states:
        print(f"  {component:<24} {state}", flush=True)
    from .observation import ABSENT, UNREADABLE

    # "not activated" is a claim about irreversible disclosure, so it is said
    # only when no activation pointer exists at all.  A pointer whose object
    # does not authenticate is reported as unreadable, never as absent.
    locked = {
        ABSENT: "not activated",
        UNREADABLE: "pointer present but the activation object is unreadable",
    }.get(
        observation.locked_state,
        f"activated {observation.locked_activated_at}",
    )
    print(f"  locked activation      {locked}", flush=True)
    release = {
        ABSENT: "none published",
        UNREADABLE: "pointer present but the release index is unreadable",
    }.get(
        observation.release_state,
        str(observation.release_evidence_digest)[:16],
    )
    print(f"  release evidence       {release}", flush=True)
    if observation.blocked_detail is not None:
        _warn(
            "current qualification evidence is incomplete or corrupt: "
            f"{observation.blocked_detail}"
        )
    if observation.superseded_detail is not None:
        _warn(
            "no current terminal qualification record: "
            f"{observation.superseded_detail}. The existing record stays "
            "historical evidence; rerun `qualification run` under the current "
            "specification."
        )
    elif observation.verdict is None:
        _warn("no current terminal qualification record has been published yet")
    else:
        _ok(
            f"current verdict: {observation.verdict} "
            f"({observation.verdict_reason or 'no reason code'})"
        )
    return 0


def execute_qualification_activate_locked(args: Any) -> int:
    """`qualification activate-locked`: the explicit one-shot locked opening."""

    from .._campaign_cli_core import (
        CampaignStore,
        StageState,
        _load_config,
        _mark_stage,
        _ok,
        _print_header,
    )

    cfg, paths = _load_config(args.config)
    store = CampaignStore(paths.state_db)
    _print_header("Explicit one-shot locked-test activation")
    session = build_qualification_session(cfg, paths, store, **_seams(args))
    if session is None:
        raise QualificationError(_no_publication_message())
    if not bool(getattr(args, "confirm", False)):
        raise QualificationError(
            "Locked activation is irreversible: it permanently reveals the reserved "
            "LOCKED_INTERPOLATION_TEST cohort for this exact publication. Re-run with "
            "`--confirm` to activate."
        )
    try:
        record, locked = activate_locked_test(session, store, paths)
    except Exception as exc:
        _mark_stage(store, paths, QUALIFICATION_STAGE, StageState.FAILED, str(exc))
        raise
    print(f"  locked test              {locked.status.value:<22} {locked.reason_code}", flush=True)
    if record.verdict is QualificationVerdict.REJECTED:
        _mark_stage(store, paths, QUALIFICATION_STAGE, StageState.FAILED, record.reason_code)
        raise QualificationError(
            "The locked interpolation test rejected the exact published product "
            f"({record.reason_code}). The revealed cohort cannot be reused as a fresh "
            "locked test, and no alternate member may be selected in its place."
        )
    _mark_stage(store, paths, QUALIFICATION_STAGE, StageState.COMPLETE, record.reason_code)
    _ok(f"release qualification verdict: {record.verdict.value}")
    return 0


__all__ = [
    "QUALIFICATION_STAGE",
    "execute_qualification_activate_locked",
    "execute_qualification_run",
    "execute_qualification_status",
]
