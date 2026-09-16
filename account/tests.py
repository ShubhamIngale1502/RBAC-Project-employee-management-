from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from .models import City, Country, State, User


class UserCrudViewsTests(TestCase):
    def setUp(self):
        self.developer = Group.objects.create(name='Developer')
        self.manager = Group.objects.create(name='Manager')
        self.country = Country.objects.create(country_name='India')
        self.state = State.objects.create(state_name='Karnataka')
        self.city = City.objects.create(city_name='Bengaluru')

    def test_user_list_page_renders(self):
        user = User.objects.create_superuser(username='alice', email='alice@example.com', password='secret123')
        self.client.force_login(user)

        response = self.client.get(reverse('user-list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'alice')

    def test_create_user_saves_and_redirects(self):
        admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='secret123')
        self.client.force_login(admin)

        response = self.client.post(
            reverse('multi-step-1'),
            {
                'first_name': 'Bob',
                'last_name': 'Smith',
                'email': 'bob@example.com',
                'mobile': '1234567890',
                'password': 'StrongPass123',
                'password2': 'StrongPass123',
                'role': 'Developer',
            },
        )
        self.assertRedirects(response, reverse('multi-step-2'))

        response = self.client.post(
            reverse('multi-step-2'),
            {
                'country': self.country.pk,
                'state': self.state.pk,
                'city': self.city.pk,
                'address': 'Main Street',
                'pin_code': '560001',
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username='bob@example.com')
        self.assertEqual(user.role, 'Developer')

    def test_update_form_preselects_and_saves_role(self):
        user = User.objects.create_superuser(
            username='alice', email='alice@example.com', password='secret123', role='Developer'
        )
        self.client.force_login(user)

        response = self.client.get(reverse('user-update', args=[user.pk]))
        self.assertEqual(response.context['form'].initial['role'], 'Developer')

        response = self.client.post(
            reverse('user-update', args=[user.pk]),
            {
                'first_name': 'Alice',
                'last_name': 'Smith',
                'email': 'alice@example.com',
                'mobile': '1234567890',
                'role': 'Manager',
                'country': self.country.pk,
                'state': self.state.pk,
                'city': self.city.pk,
                'address': 'Main Street',
                'pin_code': '560001',
            },
        )

        self.assertRedirects(response, reverse('user-list'))
        user.refresh_from_db()
        self.assertEqual(user.role, 'Manager')

    def test_toggle_user_status_view(self):
        admin = User.objects.create_superuser(username='admin_toggle', email='admin_toggle@example.com', password='secret123')
        target_user = User.objects.create_user(username='target_user', email='target@example.com', password='secret123', is_active=True)
        self.client.force_login(admin)

        response = self.client.post(reverse('toggle-user-status', args=[target_user.pk]), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        target_user.refresh_from_db()
        self.assertFalse(target_user.is_active)

        response = self.client.post(reverse('toggle-user-status', args=[target_user.pk]), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        target_user.refresh_from_db()
        self.assertTrue(target_user.is_active)


class JwtAuthenticationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='StrongPass123',
            role='Manager',
        )
        self.client = APIClient()

    def test_token_endpoint_issues_tokens_with_employee_claims(self):
        response = self.client.post(
            reverse('token_obtain_pair'),
            {'username': 'manager', 'password': 'StrongPass123'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_blacklist_requires_a_valid_access_token(self):
        response = self.client.post(reverse('token_blacklist'), {'refresh': 'invalid'}, format='json')
        self.assertEqual(response.status_code, 401)

    def test_any_active_user_can_log_in(self):
        response = self.client.post(
            reverse('user_login'),
            {'username': 'manager', 'password': 'StrongPass123'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data['data'])
        self.assertIn('refresh', response.data['data'])
