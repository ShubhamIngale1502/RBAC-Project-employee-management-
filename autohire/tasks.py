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


EMAIL_TEMPLATES = {
    "SHORTLISTED": (
        "You have been shortlisted for {title}",
        "Hi {name},\n\n"
        "Good news - your profile has been shortlisted for the {title} role. "
        "Our team will reach out shortly to schedule the next round.\n\n"
        "Regards,\nHR Team",
    ),
    "REJECTED": (
        "Update on your application for {title}",
        "Hi {name},\n\n"
        "Thank you for taking the time to apply for the {title} role and for "
        "sharing your background with us. After careful review, we will not be "
        "moving forward with your application at this time.\n\n"
        "This decision reflects our current requirements for this specific role "
        "and not the value of your experience. We encourage you to apply for "
        "other openings with us in the future.\n\n"
        "We wish you the very best in your job search.\n\n"
        "Regards,\nHR Team",
    ),
}

@shared_task
def send_candidate_email_task(application_id: int, kind: str):
    """Generic stage-change emails: SHORTLISTED, REJECTED.
 
    Interview invites carry a specific date/time/link and are sent by
    send_interview_invite_task instead, once a round is actually scheduled.
    """
    from autohire.models import Application
 
    if kind not in EMAIL_TEMPLATES:
        logger.warning("send_candidate_email_task called with unknown kind=%s", kind)
        return
 
    application = Application.objects.select_related("candidate", "job").get(pk=application_id)
    subject_tpl, body_tpl = EMAIL_TEMPLATES[kind]
    context = {"name": application.candidate.full_name, "title": application.job.title}
 
    send_mail(
        subject_tpl.format(**context),
        body_tpl.format(**context),
        settings.DEFAULT_FROM_EMAIL,
        [application.candidate.email],
        fail_silently=True,
    )
    logger.info("Sent %s email for application %s", kind, application_id)
 
 
@shared_task
def send_interview_invite_task(interview_id: int):
    """Sends the candidate their actual interview date/time/link/location."""
    from autohire.models import InterviewRound
 
    interview = (
        InterviewRound.objects
        .select_related("application__candidate", "application__job", "interviewer")
        .get(pk=interview_id)
    )
    application = interview.application
    candidate = application.candidate
 
    when = interview.scheduled_at.strftime("%A, %d %B %Y at %I:%M %p")
    mode_line = {
        InterviewRound.Mode.ONLINE: f"This will be a video call. Join here: {interview.meeting_link}",
        InterviewRound.Mode.ONSITE: f"This will be an in-person interview at: {interview.location}",
        InterviewRound.Mode.PHONE: "We will call you on your registered mobile number.",
    }.get(interview.mode, "")
 
    interviewer_line = ""
    if interview.interviewer:
        interviewer_line = f"You will be interviewing with {interview.interviewer.get_full_name() if hasattr(interview.interviewer, 'get_full_name') else interview.interviewer}.\n\n"
 
    subject = f"Interview scheduled - {application.job.title} (Round {interview.round_number})"
    body = (
        f"Hi {candidate.full_name},\n\n"
        f"Your Round {interview.round_number} interview for the {application.job.title} "
        f"role has been scheduled.\n\n"
        f"Date & time: {when}\n"
        f"Duration: approximately {interview.duration_minutes} minutes\n"
        f"{mode_line}\n\n"
        f"{interviewer_line}"
        f"Please reply to this email if the timing does not work for you and we will "
        f"help you reschedule.\n\n"
        f"Regards,\nHR Team"
    )
 
    send_mail(
        subject, body, settings.DEFAULT_FROM_EMAIL, [candidate.email], fail_silently=True,
    )
    logger.info("Sent interview invite for interview %s", interview_id)
 