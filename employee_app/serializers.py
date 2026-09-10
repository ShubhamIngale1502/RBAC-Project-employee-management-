from rest_framework import serializers
from .models import Employee,EmploymentType,Designation,Shift,Department

class EmployementTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmploymentType
        fields = "__all__"

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["department_name", "description"]
        extra_kwargs = {
            "department_code": {"required": False, "read_only": True},
        }

    def create(self, validated_data):
        department = Department(**validated_data)
        department.save()
        return department

class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designation
        fields = ["designation_name","description","status"]

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = "__all__"

class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = "__all__"