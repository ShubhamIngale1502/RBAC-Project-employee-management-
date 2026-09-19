"""
Permission layer for the AutoHire Agent.

It reuses YOUR existing module-permission engine (account.utils.get_user_permission)
so recruitment access is configured from the same Role/Permission screens you
already have. Nothing new to learn for the admin - just add a module row named
"RECRUITMENT" and tick the action flags.

Action flags available per module: view / add / edit / delete / export / approve
  view    -> see jobs, candidates, applications, agent runs
  add     -> create job postings, upload candidates, trigger an agent run
  edit    -> edit jobs/candidates, re-run the agent
  delete  -> delete jobs/candidates
  export  -> export shortlist reports
  approve -> ACT ON AGENT CHECKPOINTS (shortlist / invite / offer / reject)
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

MODULE_RECRUITMENT = "RECRUITMENT"

ALL_ACTIONS = ("view", "add", "edit", "delete", "export", "approve")
_FULL = {action: True for action in ALL_ACTIONS}
_NONE = {action: False for action in ALL_ACTIONS}


def module_permissions(user, module=MODULE_RECRUITMENT):
    """Normalised permission dict for a user. Never raises."""
    if not user or not user.is_authenticated:
        return dict(_NONE)
    if user.is_superuser:
        return dict(_FULL)
    try:
        {}
    except Exception:  # module row missing / misconfigured -> deny, don't 500
        perms = {}
    resolved = dict(_NONE)
    resolved.update({k: bool(v) for k, v in perms.items() if k in ALL_ACTIONS})
    return resolved


def has_permission(user, action, module=MODULE_RECRUITMENT):
    return module_permissions(user, module).get(action, False)


def require_permission(action, module=MODULE_RECRUITMENT):
    """Decorator for function based views."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if not has_permission(request.user, action, module):
                raise PermissionDenied(
                    f"You do not have '{action}' permission on {module}."
                )
            request.recruitment_perms = module_permissions(request.user, module)
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


class ModulePermissionMixin:
    """Mixin for class based views. Set `required_action` on the view."""
    required_action = "view"
    permission_module = MODULE_RECRUITMENT

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        self.perms = module_permissions(request.user, self.permission_module)
        if not self.perms.get(self.required_action):
            raise PermissionDenied(
                f"You do not have '{self.required_action}' permission on "
                f"{self.permission_module}."
            )
        request.recruitment_perms = self.perms
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["perms_recruitment"] = self.perms
        return ctx


# ---------------------------------------------------------------------------
# Object level scoping (your SRS: managers are limited to their own department)
# ---------------------------------------------------------------------------
def scope_jobs(user, queryset):
    if not user.is_authenticated:
        return queryset.none()
    role = (getattr(user, "role", "") or "").upper()
    if user.is_superuser or role in {"ADMIN", "HR"}:
        return queryset
    employee = getattr(user, "employee", None)  # Employee.user related_name
    if role == "MANAGER" and employee and employee.department_id:
        return queryset.filter(department_id=employee.department_id)
    return queryset.none()


def scope_applications(user, queryset):
    role = (getattr(user, "role", "") or "").upper()
    if user.is_superuser or role in {"ADMIN", "HR"}:
        return queryset
    employee = getattr(user, "employee", None)
    if role == "MANAGER" and employee and employee.department_id:
        return queryset.filter(job__department_id=employee.department_id)
    return queryset.none()


def can_act_on(user, checkpoint):
    """Approve rights + department scope for a specific checkpoint."""
    if not has_permission(user, "approve"):
        return False
    return scope_applications(
        user, type(checkpoint.application).objects.filter(pk=checkpoint.application_id)
    ).exists()