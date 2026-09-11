from django.urls import path

from . import views

urlpatterns = [
    path("", views.leave_request_page, name="leave-request-page"),
    path("new/", views.leave_request_create, name="leave-request-create"),
    path("<int:pk>/edit/", views.leave_request_edit, name="leave-request-edit"),
    path("<int:pk>/delete/", views.leave_request_delete, name="leave-request-delete"),
    path("<int:pk>/submit/", views.leave_request_submit, name="leave-request-submit"),
    path("<int:pk>/review/", views.leave_request_review, name="leave-request-review"),
    path("manage/<str:model_key>/", views.ManagementListView.as_view(), name="management-list"),
    path("manage/<str:model_key>/new/", views.ManagementCreateView.as_view(), name="management-create"),
    path("manage/<str:model_key>/<int:pk>/edit/", views.ManagementUpdateView.as_view(), name="management-update"),
    path("manage/<str:model_key>/<int:pk>/delete/", views.ManagementDeleteView.as_view(), name="management-delete"),
]
