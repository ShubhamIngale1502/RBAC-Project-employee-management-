from rest_framework import serializers
from .models import Employee, EmploymentType, Designation, Shift, Department, LeaveApproval, LeaveRequest, LeaveType

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


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = "__all__"


class LeaveApprovalSerializer(serializers.ModelSerializer):
    acted_by_name = serializers.CharField(source="acted_by.get_full_name", read_only=True)

    class Meta:
        model = LeaveApproval
        fields = ("id", "actor_role", "action", "comment", "acted_at", "acted_by", "acted_by_name")
        read_only_fields = fields


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.get_full_name", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.leave_name", read_only=True)
    approval_history = LeaveApprovalSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = (
            "id", "employee", "employee_name", "leave_type", "leave_type_name", "start_date", "end_date",
            "reason", "status", "submitted_at", "decided_at", "manager_approved_by", "hr_approved_by",
            "created_at", "updated_at", "approval_history",
        )
        read_only_fields = (
            "employee", "status", "submitted_at", "decided_at", "manager_approved_by", "hr_approved_by",
            "created_at", "updated_at", "approval_history",
        )

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "End date must be on or after start date."})
        leave_type = attrs.get("leave_type")
        if leave_type and not leave_type.is_active:
            raise serializers.ValidationError({"leave_type": "This leave type is inactive."})
        return attrs
