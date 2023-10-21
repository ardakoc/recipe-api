"""
Tests for the user api.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status


CREATE_USER_URL = reverse('user:create')

def create_user(**params):
    """
    Create and return a new user.
    """
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(TestCase):
    """
    Test the public features of the user api.
    """

    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        """
        Test creating a user is successful.
        """
        user_info = {
            'email':'test@example.com',
            'password': 'testpass123',
            'name': 'Test Name',
        }
        response = self.client.post(CREATE_USER_URL, user_info)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=user_info['email'])
        self.assertTrue(user.check_password(user_info['password']))
        # We should never send the password hash back to the user:
        self.assertNotIn('password', response.data)

    def test_user_with_email_exists_error(self):
        """
        Test error returned if user with email exists.
        """
        user_info = {
            'email':'test@example.com',
            'password': 'testpass123',
            'name': 'Test Name',
        }
        create_user(**user_info)
        response = self.client.post(CREATE_USER_URL, user_info)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short_error(self):
        """
        Test error returned if password less than 5 characters.
        """
        user_info = {
            'email':'test@example.com',
            'password': 'pw',
            'name': 'Test Name',
        }
        response = self.client.post(CREATE_USER_URL, user_info)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(
            email=user_info['email']
        ).exists()
        self.assertFalse(user_exists)
