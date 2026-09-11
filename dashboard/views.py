from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.shortcuts import render

from account.models import User


def dashboard_home(request):
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    managers = User.objects.filter(role__iexact="MANAGER").count()
    employees = User.objects.filter(role__iexact="EMPLOYEE").count()
    hr_users = User.objects.filter(role__iexact="HR").count()
    inactive_users = total_users - active_users

    role_counts = (
        User.objects
        .values('role')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    month_data = (
        User.objects
        .annotate(month=TruncMonth('created_date'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

    chart_months = [item['month'].strftime('%b %Y') for item in month_data]
    chart_signups = [item['count'] for item in month_data]
    chart_roles = [item['role'] or 'Unassigned' for item in role_counts]
    chart_roles_count = [item['count'] for item in role_counts]

    context = {
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'chart_months': chart_months,
        'chart_signups': chart_signups,
        'chart_roles': chart_roles,
        'chart_roles_count': chart_roles_count,
        'managers': managers,
        'employees': employees,
        'hr_users': hr_users,
    }
    return render(request, 'dashboard/dashboard.html', context)
