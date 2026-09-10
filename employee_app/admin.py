from django.contrib import admin
from .models import Department, Designation, EmploymentType, Shift, Employee, LeaveApproval, LeaveRequest

admin.site.register(Department)
admin.site.register(Designation)
admin.site.register(EmploymentType)
admin.site.register(Shift)
admin.site.register(Employee)


class LeaveApprovalInline(admin.TabularInline):
    model = LeaveApproval
    extra = 0
    readonly_fields = ("acted_by", "actor_role", "action", "comment", "acted_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "employee", "leave_type", "start_date", "end_date", "status")
    list_filter = ("status", "leave_type")
    search_fields = ("employee__employee_code", "employee__user__first_name", "employee__user__last_name")
    inlines = (LeaveApprovalInline,)

# Register your models here.
