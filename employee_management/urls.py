"""
URL configuration for employee_management project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from account.serializers import EmployeeTokenObtainPairSerializer
from account.views import UserLoginAPIView


class EmployeeTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmployeeTokenObtainPairSerializer

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', EmployeeTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/token/blacklist/', include('account.token_urls')),
    path('api/auth/login/', UserLoginAPIView.as_view(), name='user_login'),
    path('', include('dashboard.urls')),
    path('users/', include('account.urls')),
    path('api/', include('employee_app.urls')),
    path('leaves/', include('employee_app.web_urls')),
    path("recruitment/", include("autohire.web_urls")),
]
