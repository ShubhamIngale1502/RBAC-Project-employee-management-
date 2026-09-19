# """
# The autonomous layer.

# Flow:
#   trigger_screening()  -> creates AgentRun (QUEUED) + queues Celery task
#   execute_screening()  -> runs the Self-RAG graph, writes AgentStep audit rows,
#                           stores the verdict on the Application, then OPENS AN
#                           ApprovalCheckpoint and parks the run in WAITING.
#   apply_decision()     -> a human with 'approve' rights accepts/declines the
#                           proposal; only then does the side effect happen
#                           (stage change + invite mail).
# """
# import logging
# import time

# from django.db import transaction
# from django.utils import timezone
# from autohire.tasks import send_candidate_email_task
# from autohire.tasks import run_screening_task
# from autohire.ingest import index_candidate
# from autohire.models import (
#     AgentRun, AgentStep, Application, ApprovalCheckpoint,
# )
# from autohire.self_rag import SCREENING_GRAPH

# logger = logging.getLogger(__name__)

# SHORTLIST_THRESHOLD = 70
# REJECT_THRESHOLD = 40


# def build_question(application: Application) -> str:
#     job = application.job
#     must = ", ".join(job.must_have_skills or []) or "the listed requirements"
#     return (
#         f"Assess this candidate for the role of {job.title}. "
#         f"Verify hands-on experience with {must}, total years of relevant experience "
#         f"(required {job.min_experience_years}+ years), project ownership and any "
#         f"obvious gaps. Return a fit score, a recommendation and the evidence."
#     )


# def trigger_screening(application: Application, user) -> AgentRun:
#     run = AgentRun.objects.create(
#         application=application,
#         run_type=AgentRun.RunType.SCREENING,
#         status=AgentRun.Status.QUEUED,
#         triggered_by=user,
#     )
#     application.stage = Application.Stage.SCREENING
#     application.save(update_fields=["stage", "updated_at"])

#     transaction.on_commit(lambda: run_screening_task.delay(run.id))
#     return run


# def _make_recorder(run: AgentRun):
#     counter = {"i": 0}

#     def recorder(node: str, detail: dict, latency_ms: int):
#         counter["i"] += 1
#         AgentStep.objects.create(
#             run=run, iteration=counter["i"], node=node,
#             detail=detail, latency_ms=latency_ms,
#         )
#     return recorder


# def execute_screening(run_id: int) -> None:
#     run = AgentRun.objects.select_related("application__job", "application__candidate").get(pk=run_id)
#     application = run.application
#     candidate = application.candidate

#     run.status = AgentRun.Status.RUNNING
#     run.started_at = timezone.now()
#     run.save(update_fields=["status", "started_at", "updated_at"])

#     started = time.time()
#     try:
#         if not candidate.is_indexed:
            
#             index_candidate(candidate.id)

#         question = build_question(application)
#         final_state = SCREENING_GRAPH.invoke({
#             "candidate_id": candidate.id,
#             "job_context": application.job.requirement_summary,
#             "question": question,
#             "original_question": question,
#             "documents": [],
#             "retrieval_loops": 0,
#             "generation_loops": 0,
#             "recorder": _make_recorder(run),
#         })

#         verdict = final_state.get("generation") or {}
#         _persist_verdict(application, verdict)
#         checkpoint = _open_checkpoint(run, application, verdict)

#         run.state = {
#             "verdict": verdict,
#             "final_query": final_state.get("question"),
#             "checkpoint_id": checkpoint.id,
#         }
#         run.status = AgentRun.Status.WAITING_APPROVAL
#         run.finished_at = timezone.now()
#         run.save(update_fields=["state", "status", "finished_at", "updated_at"])
#         logger.info("Screening run %s finished in %.1fs", run_id, time.time() - started)

#     except Exception as exc:  # noqa: BLE001 - we want the failure recorded
#         logger.exception("Screening run %s failed", run_id)
#         run.status = AgentRun.Status.FAILED
#         run.error = str(exc)
#         run.finished_at = timezone.now()
#         run.save(update_fields=["status", "error", "finished_at", "updated_at"])
#         Application.objects.filter(pk=application.pk, stage=Application.Stage.SCREENING).update(
#             stage=Application.Stage.NEW
#         )


# def _persist_verdict(application: Application, verdict: dict) -> None:
#     application.match_score = verdict.get("match_score")
#     application.agent_summary = verdict.get("summary", "")
#     application.agent_strengths = verdict.get("strengths", [])
#     application.agent_gaps = verdict.get("gaps", [])
#     application.stage = Application.Stage.SCREENED
#     application.save(update_fields=[
#         "match_score", "agent_summary", "agent_strengths",
#         "agent_gaps", "stage", "updated_at",
#     ])


# def _proposed_kind(verdict: dict) -> str:
#     score = verdict.get("match_score") or 0
#     recommendation = verdict.get("recommendation")
#     if recommendation == "SHORTLIST" or score >= SHORTLIST_THRESHOLD:
#         return ApprovalCheckpoint.Kind.SHORTLIST
#     if recommendation == "REJECT" and score < REJECT_THRESHOLD:
#         return ApprovalCheckpoint.Kind.REJECT
#     return ApprovalCheckpoint.Kind.SHORTLIST  # borderline -> let the human decide


# def _open_checkpoint(run, application, verdict) -> ApprovalCheckpoint:
#     return ApprovalCheckpoint.objects.create(
#         run=run,
#         application=application,
#         kind=_proposed_kind(verdict),
#         proposal={
#             "match_score": verdict.get("match_score"),
#             "recommendation": verdict.get("recommendation"),
#             "strengths": verdict.get("strengths", []),
#             "gaps": verdict.get("gaps", []),
#         },
#         rationale=verdict.get("summary", ""),
#         citations=verdict.get("evidence", []),
#     )


# # ---------------------------------------------------------------------------
# # Human decision
# # ---------------------------------------------------------------------------
# @transaction.atomic
# def apply_decision(checkpoint_id: int, user, approved: bool, comment: str = "") -> ApprovalCheckpoint:
#     checkpoint = (
#         ApprovalCheckpoint.objects
#         .select_for_update()
#         .select_related("run", "application")
#         .get(pk=checkpoint_id)
#     )
#     if not checkpoint.is_open:
#         return checkpoint

#     checkpoint.status = (
#         ApprovalCheckpoint.Status.APPROVED if approved else ApprovalCheckpoint.Status.REJECTED
#     )
#     checkpoint.decided_by = user
#     checkpoint.comment = comment
#     checkpoint.decided_at = timezone.now()
#     checkpoint.save(update_fields=["status", "decided_by", "comment", "decided_at", "updated_at"])

#     application = checkpoint.application
#     if approved:
#         if checkpoint.kind == ApprovalCheckpoint.Kind.SHORTLIST:
#             application.mark_decided(user, Application.Stage.SHORTLISTED)
#             transaction.on_commit(
#                 lambda: send_candidate_email_task.delay(application.id, "SHORTLISTED")
#             )
#         elif checkpoint.kind == ApprovalCheckpoint.Kind.REJECT:
#             application.mark_decided(user, Application.Stage.REJECTED)
#         elif checkpoint.kind == ApprovalCheckpoint.Kind.INTERVIEW_INVITE:
#             application.mark_decided(user, Application.Stage.INTERVIEW)
#             transaction.on_commit(
#                 lambda: send_candidate_email_task.delay(application.id, "INTERVIEW")
#             )
#         elif checkpoint.kind == ApprovalCheckpoint.Kind.OFFER:
#             application.mark_decided(user, Application.Stage.OFFER)
#     else:
#         # Human overruled the agent - park the application, no side effects.
#         application.mark_decided(user, Application.Stage.SCREENED)

#     run = checkpoint.run
#     if not run.checkpoints.filter(status=ApprovalCheckpoint.Status.PENDING).exists():
#         run.status = AgentRun.Status.COMPLETED
#         run.save(update_fields=["status", "updated_at"])

#     AgentStep.objects.create(
#         run=run,
#         node="human_decision",
#         detail={
#             "checkpoint": checkpoint.kind,
#             "approved": approved,
#             "by": getattr(user, "user_id", None) or user.get_username(),
#             "comment": comment,
#         },
#     )

#     return checkpoint


"""
The autonomous layer.

Flow:
  trigger_screening()  -> creates AgentRun (QUEUED) + queues Celery task
  execute_screening()  -> runs the Self-RAG graph, writes AgentStep audit rows,
                          stores the verdict on the Application, then OPENS AN
                          ApprovalCheckpoint and parks the run in WAITING.
  apply_decision()     -> a human with 'approve' rights accepts/declines the
                          proposal; only then does the side effect happen
                          (stage change + invite mail).
"""
import logging
import time

from django.db import transaction
from django.utils import timezone

from autohire.models import (
    AgentRun, AgentStep, Application, ApprovalCheckpoint,
)
from autohire.self_rag import SCREENING_GRAPH
from autohire.ingest import index_candidate

logger = logging.getLogger(__name__)

SHORTLIST_THRESHOLD = 70
REJECT_THRESHOLD = 40


def build_question(application: Application) -> str:
    job = application.job
    must = ", ".join(job.must_have_skills or []) or "the listed requirements"
    return (
        f"Assess this candidate for the role of {job.title}. "
        f"Verify hands-on experience with {must}, total years of relevant experience "
        f"(required {job.min_experience_years}+ years), project ownership and any "
        f"obvious gaps. Return a fit score, a recommendation and the evidence."
    )


def trigger_screening(application: Application, user) -> AgentRun:
    run = AgentRun.objects.create(
        application=application,
        run_type=AgentRun.RunType.SCREENING,
        status=AgentRun.Status.QUEUED,
        triggered_by=user,
    )
    application.stage = Application.Stage.SCREENING
    application.save(update_fields=["stage", "updated_at"])

    from autohire.tasks import run_screening_task
    transaction.on_commit(lambda: run_screening_task.delay(run.id))
    return run


def _make_recorder(run: AgentRun):
    counter = {"i": 0}

    def recorder(node: str, detail: dict, latency_ms: int):
        counter["i"] += 1
        AgentStep.objects.create(
            run=run, iteration=counter["i"], node=node,
            detail=detail, latency_ms=latency_ms,
        )
    return recorder


def execute_screening(run_id: int) -> None:
    run = AgentRun.objects.select_related("application__job", "application__candidate").get(pk=run_id)
    application = run.application
    candidate = application.candidate

    run.status = AgentRun.Status.RUNNING
    run.started_at = timezone.now()
    run.save(update_fields=["status", "started_at", "updated_at"])

    started = time.time()
    try:
        if not candidate.is_indexed:
            
            index_candidate(candidate.id)

        question = build_question(application)
        final_state = SCREENING_GRAPH.invoke({
            "candidate_id": candidate.id,
            "job_context": application.job.requirement_summary,
            "question": question,
            "original_question": question,
            "documents": [],
            "retrieval_loops": 0,
            "generation_loops": 0,
            "recorder": _make_recorder(run),
        })

        verdict = final_state.get("generation") or {}
        _persist_verdict(application, verdict)
        checkpoint = _open_checkpoint(run, application, verdict)

        run.state = {
            "verdict": verdict,
            "final_query": final_state.get("question"),
            "checkpoint_id": checkpoint.id,
        }
        run.status = AgentRun.Status.WAITING_APPROVAL
        run.finished_at = timezone.now()
        run.save(update_fields=["state", "status", "finished_at", "updated_at"])
        logger.info("Screening run %s finished in %.1fs", run_id, time.time() - started)

    except Exception as exc:  # noqa: BLE001 - we want the failure recorded
        logger.exception("Screening run %s failed", run_id)
        run.status = AgentRun.Status.FAILED
        run.error = str(exc)
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "error", "finished_at", "updated_at"])
        Application.objects.filter(pk=application.pk, stage=Application.Stage.SCREENING).update(
            stage=Application.Stage.NEW
        )


def _persist_verdict(application: Application, verdict: dict) -> None:
    application.match_score = verdict.get("match_score")
    application.agent_summary = verdict.get("summary", "")
    application.agent_strengths = verdict.get("strengths", [])
    application.agent_gaps = verdict.get("gaps", [])
    application.stage = Application.Stage.SCREENED
    application.save(update_fields=[
        "match_score", "agent_summary", "agent_strengths",
        "agent_gaps", "stage", "updated_at",
    ])


def _proposed_kind(verdict: dict) -> str:
    score = verdict.get("match_score") or 0
    recommendation = verdict.get("recommendation")
    if recommendation == "SHORTLIST" or score >= SHORTLIST_THRESHOLD:
        return ApprovalCheckpoint.Kind.SHORTLIST
    if recommendation == "REJECT" and score < REJECT_THRESHOLD:
        return ApprovalCheckpoint.Kind.REJECT
    return ApprovalCheckpoint.Kind.SHORTLIST  # borderline -> let the human decide


def _open_checkpoint(run, application, verdict) -> ApprovalCheckpoint:
    return ApprovalCheckpoint.objects.create(
        run=run,
        application=application,
        kind=_proposed_kind(verdict),
        proposal={
            "match_score": verdict.get("match_score"),
            "recommendation": verdict.get("recommendation"),
            "strengths": verdict.get("strengths", []),
            "gaps": verdict.get("gaps", []),
        },
        rationale=verdict.get("summary", ""),
        citations=verdict.get("evidence", []),
    )


@transaction.atomic
def apply_decision(checkpoint_id: int, user, approved: bool, comment: str = "") -> ApprovalCheckpoint:
    checkpoint = (
        ApprovalCheckpoint.objects
        .select_for_update()
        .select_related("run", "application")
        .get(pk=checkpoint_id)
    )
    if not checkpoint.is_open:
        return checkpoint

    checkpoint.status = (
        ApprovalCheckpoint.Status.APPROVED if approved else ApprovalCheckpoint.Status.REJECTED
    )
    checkpoint.decided_by = user
    checkpoint.comment = comment
    checkpoint.decided_at = timezone.now()
    checkpoint.save(update_fields=["status", "decided_by", "comment", "decided_at", "updated_at"])

    application = checkpoint.application
    if approved:
        if checkpoint.kind == ApprovalCheckpoint.Kind.SHORTLIST:
            application.mark_decided(user, Application.Stage.SHORTLISTED)
            from autohire.tasks import send_candidate_email_task
            transaction.on_commit(
                lambda: send_candidate_email_task.delay(application.id, "SHORTLISTED")
            )
        elif checkpoint.kind == ApprovalCheckpoint.Kind.REJECT:
            application.mark_decided(user, Application.Stage.REJECTED)
        elif checkpoint.kind == ApprovalCheckpoint.Kind.INTERVIEW_INVITE:
            application.mark_decided(user, Application.Stage.INTERVIEW)
            from autohire.tasks import send_candidate_email_task
            transaction.on_commit(
                lambda: send_candidate_email_task.delay(application.id, "INTERVIEW")
            )
        elif checkpoint.kind == ApprovalCheckpoint.Kind.OFFER:
            application.mark_decided(user, Application.Stage.OFFER)
    else:
        # Human overruled the agent - park the application, no side effects.
        application.mark_decided(user, Application.Stage.SCREENED)

    run = checkpoint.run
    if not run.checkpoints.filter(status=ApprovalCheckpoint.Status.PENDING).exists():
        run.status = AgentRun.Status.COMPLETED
        run.save(update_fields=["status", "updated_at"])

    AgentStep.objects.create(
        run=run,
        node="human_decision",
        detail={
            "checkpoint": checkpoint.kind,
            "approved": approved,
            "by": getattr(user, "user_id", None) or user.get_username(),
            "comment": comment,
        },
    )
    return checkpoint