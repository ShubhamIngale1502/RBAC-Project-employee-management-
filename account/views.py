from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from .forms import UserForm, UserProfileForm, UserUpdateForm,StepOneForm,StepTwoForm
from .models import User,State,City
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from .serializers import UserLoginSerializer
from django.contrib.auth import authenticate, logout,login
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.decorators import login_required,permission_required
from django.contrib.auth.models import update_last_login, Group, Permission
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views import View
from django.db.models import Count
import pandas as pd
import io
from django.utils import timezone
from django.db import transaction


def user_list(request):
    users = User.objects.order_by('-created_date')
    return render(request, 'account/user_list.html', {'users': users})

def user_create(request):
    return redirect('multi-step-1')


@login_required
@permission_required('account.add_user', raise_exception=True)
def multi_step_one(request):
    if request.method == 'POST':
        form = StepOneForm(request.POST)
        if form.is_valid():
            request.session['step_one_data'] = {
                'first_name': form.cleaned_data['first_name'],
                'last_name': form.cleaned_data['last_name'],
                'email': form.cleaned_data['email'],
                'mobile': form.cleaned_data['mobile'],
                'role': form.cleaned_data['role'],
                'password': form.cleaned_data['password'],
            }
            return redirect('multi-step-2')
    else:
        form = StepOneForm()

    return render(request, 'account/multi_step_form.html', {
        'form': form,
        'step': 1,
        'title': 'Step 1: Personal Details',
    })

@login_required
@permission_required('account.add_user', raise_exception=True)
@transaction.atomic
def multi_step_two(request):

    step_one_data = request.session.get('step_one_data')

    if not step_one_data:
        return redirect('multi-step-1')

    if request.method == 'POST':

        form = StepTwoForm(request.POST)

        if form.is_valid():

            user = User(
                username=step_one_data['email'],
                first_name=step_one_data['first_name'],
                last_name=step_one_data['last_name'],
                email=step_one_data['email'],
                mobile=step_one_data['mobile'],
                role=step_one_data.get('role'),
                is_active=True,
            )

            user.set_password(
                step_one_data['password']
            )
            user.save()
            role_name = step_one_data.get('role')

            if role_name:

                try:

                    role = Group.objects.get(
                        name=role_name
                    )

                    user.groups.add(role)

                except Group.DoesNotExist:

                    messages.error(
                        request,
                        f"Role '{role_name}' does not exist."
                    )
                    raise

         
            profile = form.save(
                commit=False
            )

            profile.user = user

            profile.save()

           
            request.session.pop(
                'step_one_data',
                None
            )

            messages.success(
                request,
                'User created successfully.'
            )

            return redirect('user-list')

    else:

        form = StepTwoForm()

    return render(
        request,
        'account/multi_step_form.html',
        {
            'form': form,
            'step': 2,
            'title': 'Step 2: Profile Details',
        }
    )

# def user_create(request):
#     if request.method == 'POST':
#         form = UserForm(request.POST, request.FILES)
#         profile_form = UserProfileForm(request.POST)

#         if form.is_valid() and profile_form.is_valid():
#             user = form.save(commit=False)
#             user.username = form.cleaned_data['email']
#             password = form.cleaned_data['password']
#             if password:
#                 user.set_password(password)
#             user.is_active = True
#             user.save()

#             profile_data = profile_form.cleaned_data
#             if any([
#                 profile_data.get('country'),
#                 profile_data.get('state'),
#                 profile_data.get('city'),
#                 profile_data.get('address'),
#                 profile_data.get('pin_code'),
#             ]):
#                 profile = profile_form.save(commit=False)
#                 profile.user = user
#                 profile.save()

#             messages.success(request, 'User created successfully.')
#             return redirect('user-list')
#     else:
#         form = UserForm()
#         profile_form = UserProfileForm()
#         print("Errors",form.errors,profile_form.errors)

#     return render(request, 'account/user_form.html', {
#         'form': form,
#         'profile_form': profile_form,
#         'is_update': False,
#     })


@permission_required('account.change_user', raise_exception=True)
def user_update(request, pk):
    user = get_object_or_404(User, pk=pk)
    profile = getattr(user, 'user_profile', None)

    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=user)
        profile_form = UserProfileForm(request.POST, instance=profile)

        if form.is_valid() and profile_form.is_valid():
            form.save()
            profile_obj = profile_form.save(commit=False)
            profile_obj.user = user
            profile_obj.save()
            messages.success(request, 'User updated successfully.')
            return redirect('user-list')
    else:
        form = UserUpdateForm(instance=user)
        profile_form = UserProfileForm(instance=profile)

    return render(request, 'account/user_form.html', {
        'form': form,
        'profile_form': profile_form,
        'is_update': True,
        'user': user,
    })


def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        user.delete()
        messages.success(request, 'User deleted successfully.')
        return redirect('user-list')

    return render(request, 'account/user_confirm_delete.html', {'user': user})

def load_states(request):
    country_id  = request.GET.get("country")
    states = State.objects.filter(country_id=country_id).order_by('state_name')
    return JsonResponse(list(states.values('id', 'state_name')), safe=False)

def load_cities(request):
    state_id  = request.GET.get("state")
    cities = City.objects.filter(state_id=state_id).order_by('city_name')
    return JsonResponse(list(cities.values('id', 'city_name')), safe=False)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def blacklist_token(request):
    """Blacklist a provided refresh token (logout).

    Expects JSON: {"refresh": "<refresh_token>"}
    """
    refresh_token = request.data.get('refresh')
    if not refresh_token:
        return Response({'detail': 'Refresh token required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'detail': 'Token blacklisted.'}, status=status.HTTP_200_OK)
    except TokenError:
        return Response({'detail': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)


class UserLoginAPIView(APIView):
    """Issue JWT credentials to any active user with valid credentials."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "status": False,
                    "message": "Invalid data",
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        user = authenticate(
            username=username,
            password=password
        )

        if not user:
            return Response(
                {
                    "status": False,
                    "message": "Invalid username or password"
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)
        refresh['username'] = user.username
        refresh['email'] = user.email
        refresh['role'] = user.role or ''

        return Response(
            {
                "status": True,
                "message": "Login successful",
                "data": {
                    "user_id": user.id,
                    "username": user.username,
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                }   
            },
            status=status.HTTP_200_OK
        )


class RoleListView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "auth.view_group"
    template_name = 'account/role_list.html'

    def has_permission(self):
        return self.request.user.has_perm("auth.view_group") or self.request.user.has_perm("auth.view_permission")

    def get(self, request):
        # Query all roles (Groups) with member user counts
        roles = Group.objects.annotate(user_count=Count('user')).order_by('name')
        
        # Prefetch roles' permission IDs for efficient mapping
        group_permissions = {}
        for role in roles:
            group_permissions[role.id] = set(role.permissions.values_list('id', flat=True))
            
        # Get permissions - come from a filterable/query-based list
        exclude_apps = ['admin', 'contenttypes', 'sessions', 'authtoken', 'debug_toolbar', 'fcm_django']
        permissions = Permission.objects.exclude(content_type__app_label__in=exclude_apps).select_related('content_type').order_by('content_type__app_label', 'codename')
        
        allowed_permissions = {
            "account.add_user", "account.change_user",
            "account.delete_user", "account.view_user",
            "account.toggle_user_status", "account.activate_user", "account.deactivate_user",
            "account.manage_content_management",
            "account.main_dashboard_view",
            "auth.add_group", "auth.change_group", "auth.delete_group", "auth.view_group", "auth.view_permission",
            "employee_app.add_employee", "employee_app.change_employee", "employee_app.delete_employee", "employee_app.view_employee",
            "employee_app.add_leaverequest", "employee_app.change_leaverequest", "employee_app.delete_leaverequest", "employee_app.view_leaverequest",
            "employee_app.add_leavetype", "employee_app.change_leavetype", "employee_app.delete_leavetype", "employee_app.view_leavetype",
            "employee_app.add_approval", "employee_app.change_approval", "employee_app.delete_approval", "employee_app.view_approval",
        }

        app_module_map = {
            'account': 'User Management',
            'auth': 'Authentication & Authorization',
            'employee_app': 'Employee Management',
        }
        
        formatted_permissions = []
        for perm in permissions:
            codename = perm.codename
            app_label = perm.content_type.app_label
            if f"{app_label}.{codename}" not in allowed_permissions:
                continue
            module_name = app_module_map.get(app_label, app_label.title())
            
            # Determine category based on permission action
            if codename.startswith('add_'):
                category = 'Create'
            elif codename.startswith('change_') or 'toggle' in codename or 'activate' in codename or 'deactivate' in codename:
                category = 'Edit'
            elif codename.startswith('delete_'):
                category = 'Delete'
            elif codename.startswith('view_') or codename.startswith('view'):
                category = 'View'
            else:
                category = 'Other'
                
            # Clean permission name
            clean_name = perm.name
            if clean_name.startswith("Can "):
                clean_name = clean_name[4:]
            if clean_name.lower().startswith("add "):
                clean_name = "Create " + clean_name[4:]
            elif clean_name.lower().startswith("change "):
                clean_name = "Edit " + clean_name[7:]
            clean_name = clean_name.title()
            
            # Map role IDs to Boolean (whether they have this permission)
            roles_mapping = {}
            for role in roles:
                roles_mapping[role.id] = perm.id in group_permissions.get(role.id, set())
                
            formatted_permissions.append({
                'id': perm.id,
                'name': clean_name,
                'codename': f"{app_label}.{codename}",
                'app_label': app_label,
                'module': module_name,
                'category': category,
                'roles_mapping': roles_mapping
            })
            
        # Check export request
        if request.GET.get('export') == 'true':
            search_q = request.GET.get('search', '').strip().lower()
            module_f = request.GET.get('module', '').strip()
            category_f = request.GET.get('category', '').strip()
            status_f = request.GET.get('status', '').strip()

            filtered_permissions = []
            for perm in formatted_permissions:
                if search_q:
                    if search_q not in perm['name'].lower() and search_q not in perm['codename'].lower():
                        continue
                if module_f and perm['module'] != module_f:
                    continue
                if category_f and perm['category'] != category_f:
                    continue
                if status_f:
                    has_any_role = any(perm['roles_mapping'].values())
                    if status_f == 'Active' and not has_any_role:
                        continue
                    if status_f == 'Inactive' and has_any_role:
                        continue
                filtered_permissions.append(perm)

            export_data = []
            for perm in filtered_permissions:
                row_dict = {
                    "Permission": perm['name'],
                    "Module": perm['module'],
                }
                for role in roles:
                    has_perm = bool(perm['roles_mapping'].get(role.id, False))
                    row_dict[role.name] = "True" if has_perm else "False"
                export_data.append(row_dict)

            df = pd.DataFrame(export_data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Roles & Permissions")
            output.seek(0)

            response = HttpResponse(
                output.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            filename = f"roles_permissions_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        filter_modules = sorted(list(set(p['module'] for p in formatted_permissions)))
        filter_categories = sorted(list(set(p['category'] for p in formatted_permissions)))
        
        view_all = request.GET.get('view_all') == 'true'

        context = {
            'roles': roles,
            'permissions': formatted_permissions,
            'modules': filter_modules,
            'categories': filter_categories,
            'view_all': view_all,
        }
        return render(request, self.template_name, context)


class DeleteGroup(LoginRequiredMixin, PermissionRequiredMixin, View):
    login_url = 'login'
    permission_required = 'auth.delete_group'

    def post(self, request, pk, *args, **kwargs):
        # Get the group to be deleted
        group_obj = get_object_or_404(Group, id=pk)
        
        # Get all users who are members of the group
        users_in_group = User.objects.filter(groups=group_obj)

        # Remove the group from each user and mark them as deleted (soft delete)
        for user in users_in_group:
            user.groups.remove(group_obj)
            user.is_deleted = True
            user.user_type = "_"
            user.save()

        # Soft delete the group by deleting its associated users' memberships
        group_obj.delete()

        # Return a success message
        messages.success(self.request, 'Role deleted successfully.')
        return JsonResponse({'success': True})

    def handle_no_permission(self):
        return JsonResponse({'error': 'Permission Denied'}, status=403)

class CreateRoleView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "auth.add_group"

    def has_permission(self):
        return self.request.user.has_perm("auth.add_group") or self.request.user.has_perm("account.add_customrole")

    def get(self, request):
        return redirect('role-list')

    def post(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.POST.get('ajax') == 'true':
            name = request.POST.get('name')
            if not name:
                return JsonResponse({'success': False, 'message': 'Role name is required.'}, status=400)
            
            if Group.objects.filter(name__iexact=name).exists():
                return JsonResponse({'success': False, 'message': f'Role with name "{name}" already exists.'}, status=400)
            
            group = Group.objects.create(name=name)
            return JsonResponse({'success': True, 'message': f'Role "{name}" created successfully.', 'id': group.id})
            
        # Fallback
        name = request.POST.get('name')
        if name:
            Group.objects.create(name=name)
            messages.success(request, "Role created successfully")
        return redirect('role-list')

class UpdateRoleView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "auth.change_group"

    def get(self, request, pk):
        return redirect('role-list')

    def post(self, request, pk):
        role = get_object_or_404(Group, pk=pk)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.POST.get('ajax') == 'true':
            name = request.POST.get('name')
            if not name:
                return JsonResponse({'success': False, 'message': 'Role name is required.'}, status=400)
            
            if Group.objects.filter(name__iexact=name).exclude(pk=pk).exists():
                return JsonResponse({'success': False, 'message': f'Another role with name "{name}" already exists.'}, status=400)
            
            old_name = role.name
            role.name = name
            role.save()
            return JsonResponse({'success': True, 'message': f'Role "{old_name}" renamed to "{name}" successfully.'})
            
        # Fallback
        name = request.POST.get('name')
        if name:
            role.name = name
            role.save()
            messages.success(request, "Role updated successfully")
        return redirect('role-list')

class UpdatePermissionAJAXView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "auth.change_group"

    def post(self, request):
        role_id = request.POST.get('role_id')
        permission_id = request.POST.get('permission_id')
        action = request.POST.get('action')  # 'grant' or 'revoke'
        
        if not all([role_id, permission_id, action]):
            return JsonResponse({'success': False, 'message': 'Missing required fields.'}, status=400)
            
        role = get_object_or_404(Group, pk=role_id)
        permission = get_object_or_404(Permission, pk=permission_id)
        
        with transaction.atomic():
            if action == 'grant':
                role.permissions.add(permission)
                msg = f"Permission '{permission.name}' granted to role '{role.name}'."
            elif action == 'revoke':
                role.permissions.remove(permission)
                msg = f"Permission '{permission.name}' revoked from role '{role.name}'."
            else:
                return JsonResponse({'success': False, 'message': 'Invalid action.'}, status=400)
                
        return JsonResponse({'success': True, 'message': msg})

def login_view(request):

    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":

        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        if not username or not password:

            messages.error(
                request,
                "Username and password are required."
            )

            return render(
                request,
                "account/login.html"
            )

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            if not user.is_active:

                messages.error(
                    request,
                    "Your account is inactive. Please contact the administrator."
                )

                return render(
                    request,
                    "account/login.html"
                )

            login(request, user)

            return redirect("/")

        messages.error(
            request,
            "Invalid username or password."
        )

    return render(
        request,
        "account/login.html"
    )

def logout_view(request):

    logout(request)

    messages.success(
        request,
        "You have been logged out successfully."
    )

    return redirect("login")

class ToggleUserStatusView(LoginRequiredMixin, View):
    def post(self, request, pk):
        # Permission check: allow if user has toggle_user_status, activate_user, deactivate_user, change_user or is superuser
        has_perm = (
            request.user.is_superuser or
            request.user.has_perm("account.toggle_user_status") or
            request.user.has_perm("account.activate_user") or
            request.user.has_perm("account.deactivate_user") or
            request.user.has_perm("account.change_user")
        )
        if not has_perm:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.META.get('HTTP_ACCEPT', ''):
                return JsonResponse({'success': False, 'message': 'Permission denied.'}, status=403)
            messages.error(request, 'Permission denied.')
            return redirect('user-list')

        user = get_object_or_404(User, pk=pk)

        # Prevent user deactivating self
        if user == request.user and user.is_active:
            msg = "You cannot deactivate your own account while logged in."
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.META.get('HTTP_ACCEPT', ''):
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
            return redirect('user-list')

        # Prevent non-superuser deactivating superuser
        if user.is_superuser and not request.user.is_superuser:
            msg = "Only superusers can toggle superuser status."
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.META.get('HTTP_ACCEPT', ''):
                return JsonResponse({'success': False, 'message': msg}, status=403)
            messages.error(request, msg)
            return redirect('user-list')

        user.is_active = not user.is_active
        user.save()

        status_str = "activated" if user.is_active else "deactivated"
        msg = f"User {user.get_full_name() or user.username} has been {status_str} successfully."
        messages.success(request, msg)

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.META.get('HTTP_ACCEPT', ''):
            return JsonResponse({
                'success': True,
                'is_active': user.is_active,
                'status': status_str,
                'message': msg
            })

        return redirect('user-list')