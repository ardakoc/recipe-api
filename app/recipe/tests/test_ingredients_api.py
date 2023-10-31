"""
Tests for the ingredients api.
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient
from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse('recipe:ingredient-list')


def detail_url(ingredient_id):
    """
    Create and return a ingredient detail url.
    """
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


def create_user(email='user@example.com', password='testpass123'):
    """
    Create and return a new user.
    """
    return get_user_model().objects.create_user(email, password)


class PublicIngredientsApiTests(TestCase):
    """
    Test unauthenticated api requests.
    """

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """
        Test auth is required to call api.
        """
        response = self.client.get(INGREDIENTS_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsAPITests(TestCase):
    """
    Test authenticated api requests.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        """
        Test retrieving a list of ingredients.
        """
        Ingredient.objects.create(user=self.user, name='Sample ingredient 1')
        Ingredient.objects.create(user=self.user, name='Sample ingredient 2')

        response = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """
        Test list of ingredients is limited to authenticated user.
        """
        other_user = create_user(email='other@example.com', password='testpass123')
        Ingredient.objects.create(user=other_user, name='Sample ingredient 1')
        ingredient = Ingredient.objects.create(
            user=self.user,
            name='Sample ingredient 2'
        )

        response = self.client.get(INGREDIENTS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], ingredient.name)
        self.assertEqual(response.data[0]['id'], ingredient.id)

    def test_update_ingredient(self):
        """
        Test updating a ingredient.
        """
        ingredient = Ingredient.objects.create(user=self.user, name='Sample ingredient name')
        payload = {'name': 'New name'}
        url = detail_url(ingredient.id)
        response = self.client.patch(url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])
        self.assertEqual(ingredient.user, self.user)

    def test_update_user_returns_error(self):
        """
        Test changing the ingredient user results in an error.
        """
        new_user = create_user(email='user2@example.com', password='testpass123')
        ingredient = Ingredient.objects.create(user=self.user, name='Sample ingredient')

        payload = {'user': new_user.id}
        url = detail_url(ingredient.id)
        self.client.patch(url, payload)
        ingredient.refresh_from_db()

        self.assertEqual(ingredient.user, self.user)
