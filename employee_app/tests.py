from datetime import date

from django.test import TestCase

from account.models import User
from .models import Department, Designation, Employee, EmploymentType, LeaveRequest, LeaveType, Shift


class LeaveRequestWorkflowTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(department_code="DEP001", department_name="Engineering")
        self.designation = Designation.objects.create(
            designation_code="DES001", designation_name="Developer", department=self.department
        )
        self.employment_type = EmploymentType.objects.create(employment_type="Full time")
        self.shift = Shift.objects.create(shift_name="General", start_time="09:00", end_time="18:00")
        self.leave_type = LeaveType.objects.create(leave_name="Annual", allowed_days=20)
        self.manager = self.make_employee("Manager", "MANAGER", "EMP001")
        self.employee = self.make_employee("Employee", "EMPLOYEE", "EMP002", manager=self.manager)
        self.hr_user = self.make_user("HR", "HR")

    def make_user(self, name, role):
        return User.objects.create_user(
            username=f"{name.lower()}@example.com", email=f"{name.lower()}@example.com",
            first_name=name, last_name="User", role=role, password="safe-password"
        )

    def make_employee(self, name, role, code, manager=None):
        return Employee.objects.create(
            employee_code=code, user=self.make_user(name, role), department=self.department,
            designation=self.designation, employment_type=self.employment_type, shift=self.shift,
            manager=manager, gender=Employee.Gender.OTHER, date_of_birth=date(1990, 1, 1),
            joining_date=date(2025, 1, 1), salary=10000, office_email=f"{code.lower()}@example.com",
        )

    def test_employee_manager_hr_approval_flow(self):
        request = LeaveRequest.objects.create(
            employee=self.employee, leave_type=self.leave_type,
            start_date=date(2026, 10, 1), end_date=date(2026, 10, 2), reason="Family event",
        )

        request.submit(self.employee.user)
        self.assertEqual(request.status, LeaveRequest.Status.PENDING_MANAGER)
        request.review(self.manager.user, "APPROVED", "Team coverage is arranged.")
        self.assertEqual(request.status, LeaveRequest.Status.PENDING_HR)
        request.review(self.hr_user, "APPROVED", "Approved.")

        self.assertEqual(request.status, LeaveRequest.Status.APPROVED)
        self.assertEqual(request.approval_history.count(), 3)

from .models import Department
from .serializers import DepartmentSerializer


class DepartmentSerializerTests(TestCase):
    def test_create_department_generates_department_code(self):
        data = {
            "department_name": "Human Resources",
            "description": "HR department",
            "status": True,
        }

        serializer = DepartmentSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        department = serializer.save()

        self.assertEqual(department.department_code, "DEP001")
        self.assertTrue(Department.objects.filter(pk=department.pk).exists())
