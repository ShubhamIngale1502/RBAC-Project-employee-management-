from .models import (
    UserPermission,
    RolePermission,
)


def get_user_permission(user, module):

    # --------------------------------
    # USER SPECIFIC PERMISSION
    # --------------------------------

    user_permission = UserPermission.objects.filter(
        user=user,
        module=module
    ).first()

    if user_permission:

        return {
            "view": user_permission.can_view,
            "add": user_permission.can_add,
            "edit": user_permission.can_edit,
            "delete": user_permission.can_delete,
            "export": user_permission.can_export,
            "approve": user_permission.can_approve,
        }


    # --------------------------------
    # ROLE PERMISSION
    # --------------------------------

    role_permissions = RolePermission.objects.filter(
        role__users__user=user,
        role__users__is_active=True,
        module=module
    )


    return {
        "view": role_permissions.filter(
            can_view=True
        ).exists(),

        "add": role_permissions.filter(
            can_add=True
        ).exists(),

        "edit": role_permissions.filter(
            can_edit=True
        ).exists(),

        "delete": role_permissions.filter(
            can_delete=True
        ).exists(),

        "export": role_permissions.filter(
            can_export=True
        ).exists(),

        "approve": role_permissions.filter(
            can_approve=True
        ).exists(),
    }