from rest_framework.permissions import BasePermission
from django.core.exceptions import PermissionDenied


class CustomPermissionsApi(BasePermission):

    def _is_authenticated(self, request):
        """Helper method to check if the user is authenticated."""
        return request.user and request.user.is_authenticated

    def has_permission(self, request, view):
        return self._is_authenticated(request)

    def has_object_permission(self, request, view, obj):
        return self._is_authenticated(request)