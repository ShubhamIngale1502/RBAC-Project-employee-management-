from django.db import models
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
    def __str__(self):
        return f"{self.employee_code} - {self.user.get_full_name()}"