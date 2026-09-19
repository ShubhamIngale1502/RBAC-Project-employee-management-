# """Celery tasks. All slow work (parsing, embeddings, LLM calls) lives here."""
# import logging

# from celery import shared_task
# from django.core.mail import send_mail
# from django.conf import settings
# from autohire.ingest import index_candidate
# from autohire.orchestrator import execute_screening
# from autohire.models import Application
# from account.models import User
# from autohire.models import Application
# from autohire.orchestrator import trigger_screening

# logger = logging.getLogger(__name__)


# @shared_task(bind=True, max_retries=3, default_retry_delay=30)
# def ingest_resume_task(self, candidate_id: int):
#     try:
#         count = index_candidate(candidate_id)
#         logger.info("Indexed candidate %s into %s chunks", candidate_id, count)
#         return count
#     except Exception as exc:  # noqa: BLE001
#         raise self.retry(exc=exc)


# @shared_task(bind=True, max_retries=2, default_retry_delay=60)
# def run_screening_task(self, run_id: int):
#     execute_screening(run_id)


# @shared_task
# def bulk_screen_job_task(job_id: int, user_id: int):
#     """Screen every un-screened application on a job posting."""
   

#     user = User.objects.filter(pk=user_id).first()
#     applications = Application.objects.filter(job_id=job_id, stage=Application.Stage.NEW)
#     for application in applications:
#         trigger_screening(application, user)
#     return applications.count()


# @shared_task
# def send_candidate_email_task(application_id: int, kind: str):

#     application = Application.objects.select_related("candidate", "job").get(pk=application_id)
#     templates = {
#         "SHORTLISTED": (
#             "You have been shortlisted for {title}",
#             "Hi {name},\n\nYour profile has been shortlisted for the {title} role. "
#             "Our team will reach out with the next steps shortly.\n\nRegards,\nHR Team",
#         ),
#         "INTERVIEW": (
#             "Interview invitation - {title}",
#             "Hi {name},\n\nWe would like to invite you for an interview for the {title} "
#             "role. Please reply with your availability.\n\nRegards,\nHR Team",
#         ),
#     }
#     if kind not in templates:
#         return
#     subject, body = templates[kind]
#     context = {"name": application.candidate.full_name, "title": application.job.title}
#     send_mail(
#         subject.format(**context),
#         body.format(**context),
#         settings.DEFAULT_FROM_EMAIL,
#         [application.candidate.email],
#         fail_silently=True,
#     )

"""Celery tasks. All slow work (parsing, embeddings, LLM calls) lives here."""
import logging

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from autohire.ingest import index_candidate

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def ingest_resume_task(self, candidate_id: int):
    
    try:
        count = index_candidate(candidate_id)
        logger.info("Indexed candidate %s into %s chunks", candidate_id, count)
        return count
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def run_screening_task(self, run_id: int):
    from autohire.orchestrator import execute_screening
    execute_screening(run_id)


@shared_task
def bulk_screen_job_task(job_id: int, user_id: int):
    """Screen every un-screened application on a job posting."""
    from account.models import User
    from autohire.models import Application
    from autohire.orchestrator import trigger_screening

    user = User.objects.filter(pk=user_id).first()
    applications = Application.objects.filter(job_id=job_id, stage=Application.Stage.NEW)
    for application in applications:
        trigger_screening(application, user)
    return applications.count()


@shared_task
def send_candidate_email_task(application_id: int, kind: str):
    from autohire.models import Application

    application = Application.objects.select_related("candidate", "job").get(pk=application_id)
    templates = {
        "SHORTLISTED": (
            "You have been shortlisted for {title}",
            "Hi {name},\n\nYour profile has been shortlisted for the {title} role. "
            "Our team will reach out with the next steps shortly.\n\nRegards,\nHR Team",
        ),
        "INTERVIEW": (
            "Interview invitation - {title}",
            "Hi {name},\n\nWe would like to invite you for an interview for the {title} "
            "role. Please reply with your availability.\n\nRegards,\nHR Team",
        ),
    }
    if kind not in templates:
        return
    subject, body = templates[kind]
    context = {"name": application.candidate.full_name, "title": application.job.title}
    send_mail(
        subject.format(**context),
        body.format(**context),
        settings.DEFAULT_FROM_EMAIL,
        [application.candidate.email],
        fail_silently=True,
    )