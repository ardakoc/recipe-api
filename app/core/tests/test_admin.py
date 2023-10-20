"""
Tests for the Django admin modifications.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import Client


class AdminSiteTests(TestCase):
    """
    Tests for Django admin.
    """

    def setUp(self):
        """
        Create user and client.
        """
        self.client = Client()
        self.admin_user = get_user_model().objects.create_superuser(
            email='admin@example.com',
            password='testpass123',
        )
        self.client.force_login(self.admin_user)
        self.user = get_user_model().objects.create_user(
            email='user@example.com',
            password='testpass123',
            name='Test User',
        )

    def test_users_list(self):
        """
        Test users are listed on page.
        """
        # According to this page:
        # https://docs.djangoproject.com/en/4.2/ref/contrib/admin/#reversing-admin-urls
        # the layout of the reverse url method of the list (changelist) page must be
        # {{ app_label }}_{{ model_name }}_changelist:
        url = reverse('admin:core_user_changelist')
        response = self.client.get(url)

        self.assertContains(response, self.user.name)
        self.assertContains(response, self.user.email)

    def test_edit_user_page(self):
        """
        Test the edit user page works.
        """
        # According to this page:
        # https://docs.djangoproject.com/en/4.2/ref/contrib/admin/#reversing-admin-urls
        # the layout of the reverse url method of the edit page must be
        # {{ app_label }}_{{ model_name }}_change and the object_id parameter:
        url = reverse('admin:core_user_change', args=[self.user.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
