"""
AutoHire Agent - data model.

Design notes
------------
* JobPosting / Candidate / Application are the recruitment domain.
* ResumeChunk is the vector store (pgvector) used by the Self-RAG retriever.
* AgentRun / AgentStep give you a full audit trail of every node the graph
  executed - this is what makes the "autonomous" agent reviewable later.
* ApprovalCheckpoint is the human-in-the-loop gate. The agent runs on its own
  until it creates a checkpoint, then it parks itself in WAITING_APPROVAL.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone
from account.models import User

from pgvector.django import VectorField, HnswIndex

EMBEDDING_DIM = 1536  


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class JobPosting(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        OPEN = "OPEN", "Open"
        ON_HOLD = "ON_HOLD", "On hold"
        CLOSED = "CLOSED", "Closed"

    job_code = models.CharField(max_length=20, unique=True, blank=True)
    title = models.CharField(max_length=150)
    department = models.ForeignKey(
        "employee_app.Department", on_delete=models.PROTECT, related_name="job_postings"
    )
    designation = models.ForeignKey(
        "employee_app.Designation", on_delete=models.PROTECT,
        related_name="job_postings", null=True, blank=True,
    )
    description = models.TextField(help_text="Full JD text. Used as agent context.")
    must_have_skills = models.JSONField(default=list, blank=True)
    good_to_have_skills = models.JSONField(default=list, blank=True)
    min_experience_years = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    max_experience_years = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    location = models.CharField(max_length=100, blank=True)
    openings = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    hiring_manager = models.ForeignKey("employee_app.Employee", on_delete=models.SET_NULL, null=True, blank=True,related_name="job_postings",)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,related_name="created_jobs",)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.job_code or 'JOB'} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.job_code:
            last = JobPosting.objects.order_by("-id").first()
            nxt = (last.id + 1) if last else 1
            self.job_code = f"JOB{nxt:04d}"
        super().save(*args, **kwargs)

    @property
    def requirement_summary(self):
        must = ", ".join(self.must_have_skills or []) or "-"
        good = ", ".join(self.good_to_have_skills or []) or "-"
        return (
            f"Title: {self.title}\n"
            f"Department: {self.department.department_name}\n"
            f"Experience: {self.min_experience_years} - "
            f"{self.max_experience_years or 'any'} years\n"
            f"Must have: {must}\n"
            f"Good to have: {good}\n"
            f"Location: {self.location or '-'}\n\n"
            f"Job description:\n{self.description}"
        )


class Candidate(TimeStampedModel):
    class Source(models.TextChoices):
        PORTAL = "PORTAL", "Careers portal"
        REFERRAL = "REFERRAL", "Referral"
        AGENCY = "AGENCY", "Agency"
        MANUAL = "MANUAL", "Manual upload"

    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    mobile = models.CharField(max_length=15, blank=True)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.MANUAL)
    resume_file = models.FileField(upload_to="resumes/")
    resume_text = models.TextField(blank=True)
    total_experience_years = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    extracted_skills = models.JSONField(default=list, blank=True)
    is_indexed = models.BooleanField(default=False)
    indexed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="uploaded_candidates",
    )

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(models.functions.Lower("email"), name="uniq_candidate_email")
        ]

    def __str__(self):
        return f"{self.full_name} <{self.email}>"


class ResumeChunk(models.Model):
    """One embedded slice of a resume. This is the RAG corpus."""
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.PositiveIntegerField()
    section = models.CharField(max_length=50, blank=True)
    content = models.TextField()
    embedding = VectorField(dimensions=EMBEDDING_DIM)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("candidate_id", "chunk_index")
        unique_together = ("candidate", "chunk_index")
        indexes = [
            HnswIndex(
                name="resumechunk_embed_idx",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            )
        ]

    def __str__(self):
        return f"{self.candidate_id}#{self.chunk_index}"


class Application(TimeStampedModel):
    class Stage(models.TextChoices):
        NEW = "NEW", "New"
        SCREENING = "SCREENING", "Screening in progress"
        SCREENED = "SCREENED", "Screened - awaiting decision"
        SHORTLISTED = "SHORTLISTED", "Shortlisted"
        INTERVIEW = "INTERVIEW", "Interview scheduled"
        OFFER = "OFFER", "Offer"
        HIRED = "HIRED", "Hired"
        REJECTED = "REJECTED", "Rejected"

    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name="applications")
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="applications")
    stage = models.CharField(max_length=15, choices=Stage.choices, default=Stage.NEW)
    match_score = models.PositiveSmallIntegerField(null=True, blank=True)  # 0-100
    agent_summary = models.TextField(blank=True)
    agent_strengths = models.JSONField(default=list, blank=True)
    agent_gaps = models.JSONField(default=list, blank=True)
    decided_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="decided_applications",
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-match_score", "-created_at")
        unique_together = ("job", "candidate")

    def __str__(self):
        return f"{self.candidate.full_name} -> {self.job.title}"

    def mark_decided(self, user, stage):
        self.stage = stage
        self.decided_by = user
        self.decided_at = timezone.now()
        self.save(update_fields=["stage", "decided_by", "decided_at", "updated_at"])


class AgentRun(TimeStampedModel):
    class Status(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        RUNNING = "RUNNING", "Running"
        WAITING_APPROVAL = "WAITING", "Waiting for approval"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    class RunType(models.TextChoices):
        SCREENING = "SCREENING", "Resume screening"
        INTERVIEW_KIT = "INTERVIEW_KIT", "Interview question kit"

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="runs")
    run_type = models.CharField(max_length=20, choices=RunType.choices, default=RunType.SCREENING)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)
    state = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    triggered_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="agent_runs",
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Run#{self.pk} {self.run_type} ({self.status})"


class AgentStep(models.Model):
    """Audit row per Self-RAG node execution."""
    run = models.ForeignKey(AgentRun, on_delete=models.CASCADE, related_name="steps")
    iteration = models.PositiveSmallIntegerField(default=0)
    node = models.CharField(max_length=40)
    detail = models.JSONField(default=dict, blank=True)
    latency_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("id",)

    def __str__(self):
        return f"{self.run_id}:{self.node}"


class ApprovalCheckpoint(TimeStampedModel):
    class Kind(models.TextChoices):
        SHORTLIST = "SHORTLIST", "Shortlist candidate"
        REJECT = "REJECT", "Reject candidate"
        INTERVIEW_INVITE = "INTERVIEW_INVITE", "Send interview invite"
        OFFER = "OFFER", "Release offer"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    run = models.ForeignKey(AgentRun, on_delete=models.CASCADE, related_name="checkpoints")
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="checkpoints"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    proposal = models.JSONField(default=dict, blank=True, help_text="What the agent wants to do")
    rationale = models.TextField(blank=True)
    citations = models.JSONField(default=list, blank=True)
    decided_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="agent_decisions",
    )
    comment = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.kind} for {self.application} ({self.status})"

    @property
    def is_open(self):
        return self.status == self.Status.PENDING