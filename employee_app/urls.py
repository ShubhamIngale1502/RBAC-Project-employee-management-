from django.urls import path
from .views import DepartmentView, DesignationView, EmployeeView

urlpatterns = [
    path('departments/', DepartmentView.as_view(), name='department-list'),
    path('designations/', DesignationView.as_view(), name='designation-list'),
    path('employees/', EmployeeView.as_view(), name='employee-list'),
]