from django.urls import path

from . import views
from .views import *


urlpatterns = [
    path('', views.user_list, name='user-list'),
    path('create/', views.user_create, name='user-create'),
    path('multi-step/1/', views.multi_step_one, name='multi-step-1'),
    path('multi-step/2/', views.multi_step_two, name='multi-step-2'),
    path('<int:pk>/update/', views.user_update, name='user-update'),
    path('<int:pk>/delete/', views.user_delete, name='user-delete'),
    path("ajax/load-states/",load_states,name="ajax-load-states"),
    path("ajax/load-cities/",load_cities,name="ajax-load-cities"),
    path('api/token/blacklist/', views.blacklist_token, name='token_blacklist'),
    path('roles/', RoleListView.as_view(), name='role-list'),
    path('roles/create/', CreateRoleView.as_view(), name='role-create'),
    path('roles/<int:pk>/', UpdateRoleView.as_view(), name='role-update'),
    path('roles/update-permission/', UpdatePermissionAJAXView.as_view(), name='update-permission-ajax'),
    path('delete-group/<int:pk>/', DeleteGroup.as_view(), name='delete-group'),
    path("login/",login_view,name="login"),
    path("logout/",logout_view,name="logout"),
    path("toggle-user-status/<int:pk>/", ToggleUserStatusView.as_view(), name="toggle-user-status"),
]   
    