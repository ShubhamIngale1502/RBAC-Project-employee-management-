from django.urls import path

from . import views

urlpatterns = [
    path("", views.recruitment_dashboard, name="autohire-dashboard"),

    path("jobs/", views.job_list, name="autohire-job-list"),
    path("jobs/new/", views.job_create, name="autohire-job-create"),
    path("jobs/<int:pk>/edit/", views.job_update, name="autohire-job-update"),
    path("jobs/<int:pk>/delete/", views.job_delete, name="autohire-job-delete"),
    path("jobs/<int:pk>/bulk-screen/", views.job_bulk_screen, name="autohire-job-bulk-screen"),

    path("candidates/new/", views.candidate_upload, name="autohire-candidate-create"),

    path("applications/", views.application_list, name="autohire-application-list"),
    path("applications/<int:pk>/", views.application_detail, name="autohire-application-detail"),
    path("applications/<int:pk>/rescreen/", views.application_rescreen, name="autohire-application-rescreen"),

    path("approvals/", views.approval_inbox, name="autohire-approval-inbox"),
    path("approvals/<int:pk>/decide/", views.checkpoint_decide, name="autohire-checkpoint-decide"),

    path("runs/<int:pk>/status/", views.run_status, name="autohire-run-status"),
]