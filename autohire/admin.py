from django.contrib import admin

from .models import (
    AgentRun, AgentStep, Application, ApprovalCheckpoint, Candidate, JobPosting, ResumeChunk,
)


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ("job_code", "title", "department", "status", "openings", "created_at")
    list_filter = ("status", "department")
    search_fields = ("job_code", "title")


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "source", "is_indexed", "indexed_at")
    list_filter = ("source", "is_indexed")
    search_fields = ("full_name", "email")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "candidate", "job", "stage", "match_score", "decided_by")
    list_filter = ("stage", "job")
    search_fields = ("candidate__full_name", "candidate__email")


class AgentStepInline(admin.TabularInline):
    model = AgentStep
    extra = 0
    readonly_fields = ("iteration", "node", "detail", "latency_ms", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(AgentRun)
class AgentRunAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "run_type", "status", "started_at", "finished_at")
    list_filter = ("status", "run_type")
    inlines = (AgentStepInline,)


@admin.register(ApprovalCheckpoint)
class ApprovalCheckpointAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "kind", "status", "decided_by", "decided_at")
    list_filter = ("kind", "status")


admin.site.register(ResumeChunk)