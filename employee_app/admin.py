from django.contrib import admin
from .models import Department, Designation, EmploymentType, Shift, Employee

admin.site.register(Department)
admin.site.register(Designation)
admin.site.register(EmploymentType)
admin.site.register(Shift)
admin.site.register(Employee)

# Register your models here.
