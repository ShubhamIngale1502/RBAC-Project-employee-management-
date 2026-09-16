import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from rest_framework import status
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import Http404
from django.urls import reverse

from .models import Department, Designation, Employee, LeaveBalance, LeaveRequest, LeaveType,EmploymentType, Holiday, Shift
from .serializers import (DepartmentSerializer, DesignationSerializer, EmployeeSerializer,
                          LeaveRequestSerializer, LeaveTypeSerializer)
from .forms import (
    DepartmentForm, DesignationForm, EmployeeForm, EmploymentTypeForm, HolidayForm,
    LeaveRequestForm, LeaveReviewForm, LeaveTypeForm, ShiftForm,
)

logger = logging.getLogger(__name__)


def _is_hr_or_admin(user):
    return user.is_superuser or (user.role or "").upper() in {"HR", "ADMIN"}


def _leave_queryset_for(user):
    qs = LeaveRequest.objects.select_related("employee__user", "employee__manager__user", "leave_type")
    if _is_hr_or_admin(user):
        return qs
    try:
        employee = user.employee
    except Employee.DoesNotExist:
        return qs.none()
    if (user.role or "").upper() == "MANAGER":
        return qs.filter(employee__manager=employee) | qs.filter(employee=employee)
    return qs.filter(employee=employee)


class SafeAPIView(APIView):
    """Returns useful expected errors and logs unexpected server failures."""
    permission_classes = [IsAuthenticated]

    def handle_exception(self, exc):
        if isinstance(exc, PermissionDenied):
            exc = DRFPermissionDenied(str(exc))
        if isinstance(exc, DjangoValidationError):
            return Response({"detail": getattr(exc, "message_dict", None) or exc.messages}, status=400)
        if isinstance(exc, IntegrityError):
            logger.warning("Database constraint rejected leave operation", exc_info=exc)
            return Response({"detail": "The request conflicts with existing data."}, status=409)
        logger.exception("Unhandled leave API error", exc_info=exc)
        return super().handle_exception(exc)


class DepartmentView(SafeAPIView):
    def get(self, request):
        return Response(DepartmentSerializer(Department.objects.all(), many=True).data)

    def post(self, request):
        serializer = DepartmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        department = serializer.save()
        return Response(DepartmentSerializer(department).data, status=status.HTTP_201_CREATED)


class DesignationView(SafeAPIView):
    def get(self, request):
        return Response(DesignationSerializer(Designation.objects.all(), many=True).data)

    def post(self, request):
        serializer = DesignationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        designation = serializer.save()
        return Response(DesignationSerializer(designation).data, status=status.HTTP_201_CREATED)


class EmployeeView(SafeAPIView):
    def get(self, request):
        return Response(EmployeeSerializer(Employee.objects.all(), many=True).data)

    def post(self, request):
        serializer = EmployeeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = serializer.save()
        return Response(EmployeeSerializer(employee).data, status=status.HTTP_201_CREATED)


class LeaveTypeListCreateView(SafeAPIView):
    def get(self, request):
        return Response(LeaveTypeSerializer(LeaveType.objects.all(), many=True).data)

    def post(self, request):
        if not _is_hr_or_admin(request.user) and not request.user.has_perm("employee_app.add_leavetype"):
            raise DRFPermissionDenied("Only HR or an administrator can create leave types.")
        serializer = LeaveTypeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leave_type = serializer.save()
        return Response(LeaveTypeSerializer(leave_type).data, status=status.HTTP_201_CREATED)


class LeaveTypeDetailView(SafeAPIView):
    def get_object(self, pk):
        return get_object_or_404(LeaveType, pk=pk)

    def get(self, request, pk):
        return Response(LeaveTypeSerializer(self.get_object(pk)).data)

    def put(self, request, pk):
        return self._update(request, pk, False)

    def patch(self, request, pk):
        return self._update(request, pk, True)

    def _update(self, request, pk, partial):
        if not _is_hr_or_admin(request.user) and not request.user.has_perm("employee_app.change_leavetype"):
            raise DRFPermissionDenied("Only HR or an administrator can change leave types.")
        serializer = LeaveTypeSerializer(self.get_object(pk), data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        return Response(LeaveTypeSerializer(serializer.save()).data)

    def delete(self, request, pk):
        if not _is_hr_or_admin(request.user) and not request.user.has_perm("employee_app.delete_leavetype"):
            raise DRFPermissionDenied("Only HR or an administrator can delete leave types.")
        self.get_object(pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeaveRequestListCreateView(SafeAPIView):
    def get(self, request):
        return Response(LeaveRequestSerializer(_leave_queryset_for(request.user), many=True).data)

    def post(self, request):
        try:
            employee = request.user.employee
        except Employee.DoesNotExist:
            raise DRFPermissionDenied("Only an employee profile can create a leave request.")
        serializer = LeaveRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            leave_request = serializer.save(employee=employee)
        return Response(LeaveRequestSerializer(leave_request).data, status=status.HTTP_201_CREATED)


class LeaveRequestDetailView(SafeAPIView):
    def get_object(self, user, pk):
        return get_object_or_404(_leave_queryset_for(user), pk=pk)

    def get(self, request, pk):
        return Response(LeaveRequestSerializer(self.get_object(request.user, pk)).data)

    def put(self, request, pk):
        return self._update(request, pk, False)

    def patch(self, request, pk):
        return self._update(request, pk, True)

    def _update(self, request, pk, partial):
        leave_request = self.get_object(request.user, pk)
        if leave_request.employee.user_id != request.user.id or leave_request.status != LeaveRequest.Status.DRAFT:
            raise DRFPermissionDenied("Only your draft leave requests can be edited.")
        serializer = LeaveRequestSerializer(leave_request, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        return Response(LeaveRequestSerializer(serializer.save()).data)

    def delete(self, request, pk):
        leave_request = self.get_object(request.user, pk)
        if leave_request.employee.user_id != request.user.id or leave_request.status != LeaveRequest.Status.DRAFT:
            raise DRFPermissionDenied("Only your draft leave requests can be deleted.")
        leave_request.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeaveRequestActionView(SafeAPIView):
    def post(self, request, pk, action):
        with transaction.atomic():
            leave_request = get_object_or_404(LeaveRequest.objects.select_for_update(), pk=pk)
            if action == "submit":
                leave_request.submit(request.user)
            elif action == "cancel":
                leave_request.cancel(request.user, request.data.get("comment", ""))
            elif action == "review":
                leave_request.review(request.user, request.data.get("action", ""), request.data.get("comment", ""))
            else:
                return Response({"detail": "Unknown leave action."}, status=400)
        return Response(LeaveRequestSerializer(leave_request).data)

def calculate_leave_days(start_date, end_date):
    return (end_date - start_date).days + 1

def get_used_leave_days(employee, leave_type):
    approved_leaves = LeaveRequest.objects.filter(
        employee=employee,
        leave_type=leave_type,
        status=LeaveRequest.Status.APPROVED,
    )

    total_used = 0

    for leave in approved_leaves:
        total_used += calculate_leave_days(
            leave.start_date,
            leave.end_date
        )

    return total_used

def get_remaining_leave_days(employee, leave_type):
    balance = LeaveBalance.objects.filter(
        employee=employee,
        leave_type=leave_type
    ).first()

    if not balance:
        return 0

    used_days = get_used_leave_days(
        employee,
        leave_type
    )

    return max(
        balance.allocated_days - used_days,
        0
    )

@login_required
def leave_request_page(request):

    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        employee = None

    leave_balances = []

    if employee:

        balances = (
            LeaveBalance.objects
            .filter(employee=employee)
            .select_related("leave_type")
        )

        for balance in balances:

            used_days = get_used_leave_days(
                employee,
                balance.leave_type
            )

            remaining_days = max(
                balance.allocated_days - used_days,
                0
            )

            leave_balances.append({
                "leave_type": balance.leave_type,
                "allocated_days": balance.allocated_days,
                "used_days": used_days,
                "remaining_days": remaining_days,
            })

    return render(
        request,
        "employee_app/leave_request_list.html",
        {
            "leave_requests": _leave_queryset_for(request.user),

            "form": LeaveRequestForm(),

            "leave_balances": leave_balances,

            "can_review": (
                _is_hr_or_admin(request.user)
                or (request.user.role or "").upper() == "MANAGER"
            ),
        }
    )


@login_required
def leave_request_create(request):

    try:
        employee = request.user.employee

    except Employee.DoesNotExist:
        messages.error(
            request,
            "An employee profile is required before requesting leave."
        )

        return redirect("leave-request-page")

    form = LeaveRequestForm(request.POST or None)

    if request.method == "POST" and form.is_valid():

        try:

            leave_request = form.save(commit=False)

            leave_request.employee = employee

            leave_request.full_clean()

            leave_type = leave_request.leave_type

            requested_days = calculate_leave_days(
                leave_request.start_date,
                leave_request.end_date
            )

            balance = LeaveBalance.objects.filter(
                employee=employee,
                leave_type=leave_type
            ).first()

            if not balance:

                form.add_error(
                    "leave_type",
                    "No leave balance has been assigned for this leave type."
                )

            else:

                used_days = get_used_leave_days(
                    employee,
                    leave_type
                )

                remaining_days = max(
                    balance.allocated_days - used_days,
                    0
                )

                if requested_days > remaining_days:

                    form.add_error(
                        "leave_type",
                        (
                            f"You can request only "
                            f"{remaining_days} day(s) of "
                            f"{leave_type.leave_name}. "
                            f"You requested {requested_days} day(s)."
                        )
                    )

                else:

                    leave_request.save()

                    messages.success(
                        request,
                        "Leave request saved as a draft."
                    )

                    return redirect("leave-request-page")

        except (
            DjangoValidationError,
            IntegrityError
        ) as exc:

            form.add_error(
                None,
                "Could not save this request. "
                "Please verify the dates and leave type."
            )

            logger.warning(
                "Invalid leave request: %s",
                exc
            )

    return render(
        request,
        "employee_app/leave_request_form.html",
        {
            "form": form,
            "title": "Request leave",
        }
    )


@login_required
def leave_request_edit(request, pk):
    leave_request = get_object_or_404(LeaveRequest, pk=pk, employee__user=request.user, status=LeaveRequest.Status.DRAFT)
    form = LeaveRequestForm(request.POST or None, instance=leave_request)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
            messages.success(request, "Draft leave request updated.")
            return redirect("leave-request-page")
        except (DjangoValidationError, IntegrityError):
            form.add_error(None, "Could not update this request.")
    return render(request, "employee_app/leave_request_form.html", {"form": form, "title": "Edit draft leave request"})


@login_required
@require_POST
def leave_request_delete(request, pk):
    leave_request = get_object_or_404(LeaveRequest, pk=pk, employee__user=request.user, status=LeaveRequest.Status.DRAFT)
    try:
        leave_request.delete()
        messages.success(request, "Draft leave request deleted.")
    except IntegrityError:
        messages.error(request, "This leave request could not be deleted.")
    return redirect("leave-request-page")


@login_required
@require_POST
def leave_request_submit(request, pk):

    leave_request = get_object_or_404(
        LeaveRequest,
        pk=pk,
        employee__user=request.user,
        status=LeaveRequest.Status.DRAFT
    )

    try:

        employee = leave_request.employee
        leave_type = leave_request.leave_type

        requested_days = calculate_leave_days(
            leave_request.start_date,
            leave_request.end_date
        )

        balance = LeaveBalance.objects.filter(
            employee=employee,
            leave_type=leave_type
        ).first()

        if not balance:

            raise DjangoValidationError(
                "No leave balance has been assigned "
                "for this leave type."
            )

        used_days = get_used_leave_days(
            employee,
            leave_type
        )

        remaining_days = max(
            balance.allocated_days - used_days,
            0
        )

        if requested_days > remaining_days:

            raise DjangoValidationError(
                (
                    f"Insufficient leave balance. "
                    f"Available: {remaining_days} day(s), "
                    f"Requested: {requested_days} day(s)."
                )
            )

        with transaction.atomic():

            leave_request.submit(request.user)

        messages.success(
            request,
            "Leave request submitted for approval."
        )

    except (
        PermissionDenied,
        DjangoValidationError
    ) as exc:

        messages.error(
            request,
            str(exc)
        )

    return redirect("leave-request-page")


@login_required
def leave_request_review(request, pk):
    leave_request = get_object_or_404(_leave_queryset_for(request.user), pk=pk)
    form = LeaveReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                leave_request.review(request.user, form.cleaned_data["action"], form.cleaned_data["comment"])
            messages.success(request, "Leave request reviewed.")
            return redirect("leave-request-page")
        except (PermissionDenied, DjangoValidationError) as exc:
            form.add_error(None, str(exc))
    return render(request, "employee_app/leave_review_form.html", {"form": form, "leave_request": leave_request})


# Server-rendered CRUD for company master data and employee records.
MANAGEMENT_MODELS = {
    "departments": (Department, DepartmentForm, "Departments", ("department_name", "status")),
    "designations": (Designation, DesignationForm, "Designations", ( "designation_name", "department", "status")),
    "employment-types": (EmploymentType, EmploymentTypeForm, "Employment types", ("employment_type", "is_active")),
    "leave-types": (LeaveType, LeaveTypeForm, "Leave types", ("leave_name", "allowed_days", "is_paid", "is_active")),
    "holidays": (Holiday, HolidayForm, "Holidays", ("holiday_name", "holiday_date")),
    "shifts": (Shift, ShiftForm, "Shifts", ("shift_name", "start_time", "end_time", "grace_time")),
    "employees": (Employee, EmployeeForm, "Employees", ("user", "department", "designation", "status")),
}


class ManagementMixin(LoginRequiredMixin, PermissionRequiredMixin):
    raise_exception = True
    template_name = "employee_app/management_form.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            self.model, self.form_class, self.page_title, self.display_fields = MANAGEMENT_MODELS[kwargs["model_key"]]
        except KeyError:

            raise Http404("Unknown management section")

    def get_permission_required(self):
        return (f"employee_app.{self.permission_action}_{self.model._meta.model_name}",)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"page_title": self.page_title, "model_key": self.kwargs["model_key"]})
        return context

    def form_valid(self, form):
        instance = form.instance
        if hasattr(instance, "created_by") and not instance.pk:
            instance.created_by = self.request.user
        if hasattr(instance, "updated_by"):
            instance.updated_by = self.request.user
        # ModelForm.is_valid() already runs model validation. Calling full_clean()
        # again here would validate omitted, auto-generated code fields as blank.
        return super().form_valid(form)

    def get_success_url(self):

        return reverse("management-list", kwargs={"model_key": self.kwargs["model_key"]})


class ManagementListView(ManagementMixin, ListView):
    template_name = "employee_app/management_list.html"
    permission_action = "view"
    paginate_by = 20

    def get_queryset(self):
        return self.model.objects.all().order_by("-pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rows = []
        for obj in context["object_list"]:
            rows.append({"object": obj, "cells": [getattr(obj, field) for field in self.display_fields]})
        context.update({"rows": rows, "headers": [field.replace("_", " ").title() for field in self.display_fields]})
        return context


class ManagementCreateView(ManagementMixin, CreateView):
    permission_action = "add"

    def form_valid(self, form):
        messages.success(self.request, f"{self.page_title[:-1]} created successfully.")
        return super().form_valid(form)


class ManagementUpdateView(ManagementMixin, UpdateView):
    permission_action = "change"

    def form_valid(self, form):
        messages.success(self.request, f"{self.page_title[:-1]} updated successfully.")
        return super().form_valid(form)


class ManagementDeleteView(ManagementMixin, DeleteView):
    template_name = "employee_app/management_confirm_delete.html"
    permission_action = "delete"

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, f"{self.page_title[:-1]} deleted successfully.")
            return response
        except IntegrityError:
            messages.error(self.request, "This record is in use and cannot be deleted.")
            return redirect(self.get_success_url())
