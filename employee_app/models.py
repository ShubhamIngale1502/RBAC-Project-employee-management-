from django.db import models
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import F, Q
from django.utils import timezone
from django.conf import settings
from account.models import User


class Department(models.Model):

    department_code = models.CharField(max_length=10,unique=True, db_index=True)
    department_name = models.CharField(max_length=100,unique=True,db_index=True)
    description = models.TextField(blank=True,null=True)
    status = models.BooleanField(default=True)
    created_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="created_departments")
    updated_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="updated_departments")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.department_name

    def save(self, *args, **kwargs):
        if not self.department_code:
            self.department_code = self.generate_department_code()
        super().save(*args, **kwargs)

    def generate_department_code(self):
        last_department = Department.objects.order_by('-id').first()
        if last_department and last_department.department_code:
            last_code = last_department.department_code
            try:
                number = int(last_code[3:]) + 1
            except ValueError:
                number = 1
        else:
            number = 1
        return f"DEP{number:03d}"


class Designation(models.Model):

    designation_code = models.CharField(
        max_length=10,
        unique=True,
        db_index=True
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="designations"
    )

    designation_name = models.CharField(
        max_length=100
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    status = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_designations"
    )

    updated_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="updated_designations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.designation_name

    def save(self, *args, **kwargs):
        if not self.designation_code:
            last = Designation.objects.order_by("-id").first()
            try:
                number = int(last.designation_code[3:]) + 1 if last else 1
            except (TypeError, ValueError):
                number = 1
            self.designation_code = f"DES{number:03d}"
        super().save(*args, **kwargs)

class EmploymentType(models.Model):

    employment_type = models.CharField(
        max_length=50,
        unique=True
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return self.employment_type

class LeaveType(models.Model):

    leave_name = models.CharField(
        max_length=50,
        unique=True
    )

    allowed_days = models.PositiveIntegerField()

    is_paid = models.BooleanField(
        default=True
    )

    is_active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return self.leave_name

class Holiday(models.Model):

    holiday_name = models.CharField(max_length=100)

    holiday_date = models.DateField()

    description = models.TextField(
        blank=True,
        null=True
    )

    def __str__(self):
        return self.holiday_name


class Shift(models.Model):

    shift_name = models.CharField(max_length=50)

    start_time = models.TimeField()

    end_time = models.TimeField()

    grace_time = models.IntegerField(
        default=10,
        help_text="Grace period in minutes"
    )

    def __str__(self):
        return self.shift_name


class Employee(models.Model):

    class Gender(models.TextChoices):
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"
        OTHER = "OTHER", "Other"

    class MaritalStatus(models.TextChoices):
        SINGLE = "SINGLE", "Single"
        MARRIED = "MARRIED", "Married"

    class EmployeeStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        NOTICE = "NOTICE", "Notice Period"
        RESIGNED = "RESIGNED", "Resigned"
        TERMINATED = "TERMINATED", "Terminated"

    employee_code = models.CharField(max_length=15,unique=True,db_index=True)
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name="employee")
    department = models.ForeignKey(Department,on_delete=models.PROTECT,related_name="employees")

    designation = models.ForeignKey(
        Designation,
        on_delete=models.PROTECT,
        related_name="employees"
    )

    employment_type = models.ForeignKey(
        EmploymentType,
        on_delete=models.PROTECT,
        related_name="employees"
    )

    shift = models.ForeignKey(
        Shift,
        on_delete=models.PROTECT,
        related_name="employees"
    )

    manager = models.ForeignKey("self",on_delete=models.SET_NULL,null=True,blank=True,related_name="team_members")
    blood_group = models.CharField(max_length=10,null=True,blank=True)
    gender = models.CharField(max_length=10,choices=Gender.choices)
    marital_status = models.CharField(max_length=20,choices=MaritalStatus.choices,default=MaritalStatus.SINGLE)

    date_of_birth = models.DateField()

    joining_date = models.DateField()

    confirmation_date = models.DateField(
        null=True,
        blank=True
    )

    relieving_date = models.DateField(
        null=True,
        blank=True
    )

    experience_years = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0
    )

    salary = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    pan_number = models.CharField(
        max_length=20,
        blank=True
    )

    aadhaar_number = models.CharField(
        max_length=20,
        blank=True
    )

    passport_number = models.CharField(
        max_length=20,
        blank=True
    )

    emergency_contact_name = models.CharField(
        max_length=100,
        null=True,blank=True
    )

    emergency_contact_number = models.CharField(
        max_length=15,
        null=True,blank=True
    )

    emergency_contact_relation = models.CharField(
        max_length=50,
        null=True,blank=True
    )

    bank_name = models.CharField(
        max_length=100,
        blank=True
    )

    account_number = models.CharField(
        max_length=30,
        blank=True
    )

    ifsc_code = models.CharField(
        max_length=20,
        blank=True
    )

    office_email = models.EmailField(
        unique=True
    )

    personal_email = models.EmailField(
        blank=True
    )

    official_mobile = models.CharField(
        max_length=15,
        blank=True
    )

    alternate_mobile = models.CharField(
        max_length=15,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=EmployeeStatus.choices,
        default=EmployeeStatus.ACTIVE
    )

    remarks = models.TextField(
        blank=True
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="employees_created"
    )

    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="employees_updated"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )


    def get_full_name(self):
        full_name = f"{self.user.first_name}  {self.user.last_name}"
        return full_name

    def save(self, *args, **kwargs):
        if not self.employee_code:
            last_employee = Employee.objects.order_by("-id").first()
            try:
                number = int(last_employee.employee_code[3:]) + 1 if last_employee else 1
            except (TypeError, ValueError):
                number = 1
            self.employee_code = f"EMP{number:03d}"
        super().save(*args, **kwargs)

    # def clean(self):
    #     if self.department_id and self.designation_id and self.designation.department_id != self.department_id:
    #         raise ValidationError({"designation": "The designation must belong to the selected department."})
    #     if self.manager_id == self.id:
    #         raise ValidationError({"manager": "An employee cannot be their own manager."})
    # def __str__(self):
    #     return f"{self.employee_code} - {self.user.get_full_name()}"


class LeaveRequest(models.Model):
    """A leave application and its manager/HR approval state."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING_MANAGER = "PENDING_MANAGER", "Pending manager approval"
        PENDING_HR = "PENDING_HR", "Pending HR approval"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="leave_requests")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="leave_requests")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    manager_approved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="manager_approved_leave_requests"
    )
    hr_approved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="hr_approved_leave_requests"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="leave_request_end_on_or_after_start",
            )
        ]
        permissions = [
            ("approve_leaverequest", "Can approve or reject leave requests"),
        ]

    def clean(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date must be on or after start date."})
        if self.leave_type_id and not self.leave_type.is_active:
            raise ValidationError({"leave_type": "This leave type is inactive."})

    def submit(self, actor):
        if actor != self.employee.user:
            raise PermissionDenied("Only the employee who created this request can submit it.")
        if self.status != self.Status.DRAFT:
            raise ValidationError("Only draft leave requests can be submitted.")
        self.full_clean()
        self.status = self.Status.PENDING_MANAGER if self.employee.manager_id else self.Status.PENDING_HR
        self.submitted_at = timezone.now()
        self.save(update_fields=["status", "submitted_at", "updated_at"])
        LeaveApproval.objects.create(
            leave_request=self, acted_by=actor, actor_role=LeaveApproval.role_for(actor),
            action=LeaveApproval.Action.SUBMITTED,
        )

    def review(self, actor, action, comment=""):
        action = action.upper()
        if action not in {LeaveApproval.Action.APPROVED, LeaveApproval.Action.REJECTED}:
            raise ValidationError("A review action must be APPROVED or REJECTED.")
        role = LeaveApproval.role_for(actor)
        is_admin = actor.is_superuser or role == LeaveApproval.ActorRole.ADMIN
        if self.status == self.Status.PENDING_MANAGER:
            if not (is_admin or (self.employee.manager_id and actor == self.employee.manager.user)):
                raise PermissionDenied("Only this employee's manager may review this request.")
            self.manager_approved_by = actor
            self.status = self.Status.PENDING_HR if action == LeaveApproval.Action.APPROVED else self.Status.REJECTED
        elif self.status == self.Status.PENDING_HR:
            if not (is_admin or role == LeaveApproval.ActorRole.HR):
                raise PermissionDenied("Only HR may complete this leave request.")
            self.hr_approved_by = actor
            self.status = self.Status.APPROVED if action == LeaveApproval.Action.APPROVED else self.Status.REJECTED
        else:
            raise ValidationError("This leave request is not awaiting review.")
        self.decided_at = timezone.now() if self.status in {self.Status.APPROVED, self.Status.REJECTED} else None
        self.save()
        LeaveApproval.objects.create(
            leave_request=self, acted_by=actor, actor_role=role, action=action, comment=comment
        )

    def cancel(self, actor, comment=""):
        if actor != self.employee.user and not actor.is_superuser:
            raise PermissionDenied("Only the requesting employee can cancel this leave request.")
        if self.status not in {self.Status.DRAFT, self.Status.PENDING_MANAGER, self.Status.PENDING_HR}:
            raise ValidationError("This leave request can no longer be cancelled.")
        self.status = self.Status.CANCELLED
        self.save(update_fields=["status", "updated_at"])
        LeaveApproval.objects.create(
            leave_request=self, acted_by=actor, actor_role=LeaveApproval.role_for(actor),
            action=LeaveApproval.Action.CANCELLED, comment=comment,
        )

    def __str__(self):
        return f"{self.employee} — {self.leave_type} ({self.start_date} to {self.end_date})"


class LeaveApproval(models.Model):
    class ActorRole(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        MANAGER = "MANAGER", "Manager"
        HR = "HR", "HR"
        EMPLOYEE = "EMPLOYEE", "Employee"

    class Action(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="approval_history")
    acted_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="leave_actions")
    actor_role = models.CharField(max_length=20, choices=ActorRole.choices)
    action = models.CharField(max_length=20, choices=Action.choices)
    comment = models.TextField(blank=True)
    acted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["acted_at"]

    @classmethod
    def role_for(cls, user):
        if user.is_superuser or (user.role or "").upper() == cls.ActorRole.ADMIN:
            return cls.ActorRole.ADMIN
        if (user.role or "").upper() == cls.ActorRole.HR:
            return cls.ActorRole.HR
        if (user.role or "").upper() == cls.ActorRole.MANAGER:
            return cls.ActorRole.MANAGER
        return cls.ActorRole.EMPLOYEE

class LeaveBalance(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="leave_balances"
    )

    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name="leave_balances"
    )

    allocated_days = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("employee", "leave_type")

    def __str__(self):
        return (
            f"{self.employee} - "
            f"{self.leave_type.leave_name}"
        )
    