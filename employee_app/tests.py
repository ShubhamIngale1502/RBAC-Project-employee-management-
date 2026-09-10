from django.test import TestCase

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
