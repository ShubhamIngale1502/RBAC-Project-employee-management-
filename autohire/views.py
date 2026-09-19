"""
Server rendered views (same style as your employee_app web views).
Every view is gated by the RECRUITMENT module flags in permissions.py.
"""
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .orchestrator import apply_decision, trigger_screening
from .forms import (
    ApplicationFilterForm, CandidateForm, CheckpointDecisionForm, JobPostingForm,
)
from .models import AgentRun, Application, ApprovalCheckpoint, Candidate, JobPosting
from .permissions import (can_act_on, module_permissions, require_permission, scope_applications, scope_jobs,)
from .tasks import bulk_screen_job_task, ingest_resume_task


# ------------------------------- dashboard --------------------------------
@require_permission("view")
def recruitment_dashboard(request):
    jobs = scope_jobs(request.user, JobPosting.objects.all())
    applications = scope_applications(request.user, Application.objects.all())
    pending = ApprovalCheckpoint.objects.filter(
        status=ApprovalCheckpoint.Status.PENDING,
        application__in=applications,
    ).select_related("application__candidate", "application__job")[:10]

    context = {
        "open_jobs": jobs.filter(status=JobPosting.Status.OPEN).count(),
        "total_applications": applications.count(),
        "awaiting_approval": pending.count() if hasattr(pending, "count") else len(pending),
        "stage_counts": applications.values("stage").annotate(total=Count("id")),
        "pending_checkpoints": pending,
        "perms": request.recruitment_perms,
    }
    return render(request, "autohire/dashboard.html", context)


# ------------------------------- job posting ------------------------------
@require_permission("view")
def job_list(request):
    jobs = scope_jobs(request.user, JobPosting.objects.select_related("department")).annotate(
        application_count=Count("applications"),
        shortlisted=Count("applications", filter=Q(applications__stage=Application.Stage.SHORTLISTED)),
    )
    return render(request, "autohire/job_list.html",
                  {"jobs": jobs, "perms": request.recruitment_perms})


@require_permission("add")
def job_create(request):
    form = JobPostingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        job = form.save(commit=False)
        job.created_by = request.user
        job.save()
        messages.success(request, f"Job posting {job.job_code} created.")
        return redirect("autohire-job-list")
    return render(request, "autohire/job_form.html", {"form": form, "title": "New job posting"})


@require_permission("edit")
def job_update(request, pk):
    job = get_object_or_404(scope_jobs(request.user, JobPosting.objects.all()), pk=pk)
    form = JobPostingForm(request.POST or None, instance=job)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Job posting updated.")
        return redirect("autohire-job-list")
    return render(request, "autohire/job_form.html", {"form": form, "title": f"Edit {job.job_code}"})


@require_permission("delete")
def job_delete(request, pk):
    job = get_object_or_404(scope_jobs(request.user, JobPosting.objects.all()), pk=pk)
    if request.method == "POST":
        job.delete()
        messages.success(request, "Job posting deleted.")
        return redirect("autohire-job-list")
    return render(request, "autohire/confirm_delete.html", {"object": job})


# ------------------------------- candidates -------------------------------
@require_permission("add")
def candidate_upload(request):
    form = CandidateForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            candidate = form.save(commit=False)
            candidate.created_by = request.user
            candidate.save()

            application, created = Application.objects.get_or_create(
                job=form.cleaned_data["job"], candidate=candidate,
            )
            transaction.on_commit(lambda: ingest_resume_task.delay(candidate.id))

            if form.cleaned_data["run_agent_now"] and created:
                trigger_screening(application, request.user)

        messages.success(
            request,
            f"{candidate.full_name} added. The agent will screen the resume in the background.",
        )
        return redirect("autohire-application-list")
    return render(request, "autohire/candidate_form.html", {"form": form})


# ------------------------------ applications ------------------------------
@require_permission("view")
def application_list(request):
    applications = scope_applications(
        request.user,
        Application.objects.select_related("candidate", "job"),
    )
    filter_form = ApplicationFilterForm(request.GET or None)
    if filter_form.is_valid():
        if filter_form.cleaned_data.get("stage"):
            applications = applications.filter(stage=filter_form.cleaned_data["stage"])
        if filter_form.cleaned_data.get("min_score") is not None:
            applications = applications.filter(match_score__gte=filter_form.cleaned_data["min_score"])
    return render(request, "autohire/application_list.html", {
        "applications": applications,
        "filter_form": filter_form,
        "perms": request.recruitment_perms,
    })


@require_permission("view")
def application_detail(request, pk):
    application = get_object_or_404(
        scope_applications(request.user, Application.objects.select_related("candidate", "job")),
        pk=pk,
    )
    runs = application.runs.prefetch_related("steps", "checkpoints")
    return render(request, "autohire/application_detail.html", {
        "application": application,
        "runs": runs,
        "open_checkpoints": application.checkpoints.filter(
            status=ApprovalCheckpoint.Status.PENDING
        ),
        "perms": request.recruitment_perms,
    })


@require_permission("edit")
def application_rescreen(request, pk):
    application = get_object_or_404(scope_applications(request.user, Application.objects.all()), pk=pk)
    if request.method != "POST":
        return redirect("autohire-application-detail", pk=pk)
    trigger_screening(application, request.user)
    messages.info(request, "Agent re-screening queued.")
    return redirect("autohire-application-detail", pk=pk)


@require_permission("add")
def job_bulk_screen(request, pk):
    job = get_object_or_404(scope_jobs(request.user, JobPosting.objects.all()), pk=pk)
    if request.method == "POST":
        bulk_screen_job_task.delay(job.id, request.user.id)
        messages.info(request, "Bulk screening queued for all new applications.")
    return redirect("autohire-job-list")


# --------------------------- approval checkpoints -------------------------
@require_permission("view")
def approval_inbox(request):
    applications = scope_applications(request.user, Application.objects.all())
    checkpoints = (
        ApprovalCheckpoint.objects
        .filter(status=ApprovalCheckpoint.Status.PENDING, application__in=applications)
        .select_related("application__candidate", "application__job", "run")
    )
    return render(request, "autohire/approval_inbox.html", {
        "checkpoints": checkpoints,
        "can_approve": module_permissions(request.user)["approve"],
    })


@require_permission("approve")
def checkpoint_decide(request, pk):
    checkpoint = get_object_or_404(
        ApprovalCheckpoint.objects.select_related("application__candidate", "application__job", "run"),
        pk=pk,
    )
    if not can_act_on(request.user, checkpoint):
        messages.error(request, "This candidate is outside your department scope.")
        return redirect("autohire-approval-inbox")

    form = CheckpointDecisionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        apply_decision(
            checkpoint.id,
            request.user,
            approved=form.cleaned_data["decision"] == "APPROVE",
            comment=form.cleaned_data["comment"],
        )
        messages.success(request, "Decision recorded.")
        return redirect("autohire-approval-inbox")

    return render(request, "autohire/checkpoint_detail.html", {
        "checkpoint": checkpoint, "form": form,
    })


# ------------------------------- run status -------------------------------
@require_permission("view")
def run_status(request, pk):
    """Small polling endpoint for the 'agent is thinking...' spinner.

    Plain Django JsonResponse - this is AJAX for our own page, not a public API,
    so it needs no DRF, no serializer and no token auth. The session cookie and
    @require_permission("view") already secure it.
    """
    run = get_object_or_404(
        AgentRun.objects.filter(application__in=scope_applications(request.user, Application.objects.all())),
        pk=pk,
    )
    return JsonResponse({
        "status": run.status,
        "steps": list(run.steps.values("node", "detail", "latency_ms", "created_at")),
        "verdict": run.state.get("verdict"),
        "error": run.error,
    })