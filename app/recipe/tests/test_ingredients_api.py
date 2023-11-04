"""
Tests for the ingredients api.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient, Recipe
from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse('recipe:ingredient-list')


def detail_url(ingredient_id):
    """
    Create and return an ingredient detail url.
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
        Test updating an ingredient.
        """
        ingredient = Ingredient.objects.create(
            user=self.user,
            name='Sample ingredient name'
        )
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
        ingredient = Ingredient.objects.create(
            user=self.user,
            name='Sample ingredient'
        )

        payload = {'user': new_user.id}
        url = detail_url(ingredient.id)
        self.client.patch(url, payload)
        ingredient.refresh_from_db()

        self.assertEqual(ingredient.user, self.user)

    def test_delete_ingredient(self):
        """
        Test deleting an ingredient successful.
        """
        ingredient = Ingredient.objects.create(user=self.user)

        url = detail_url(ingredient.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ingredient.objects.filter(id=ingredient.id).exists())

    def test_delete_recipe_of_another_user(self):
        """
        Test deleting another user's ingredient gives error.
        """
        new_user = create_user(email='user2@example.com', password='testpass123')
        ingredient = Ingredient.objects.create(user=new_user)

        url = detail_url(ingredient.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Ingredient.objects.filter(id=ingredient.id).exists())

    def test_filter_ingredients_assigned_to_recipes(self):
        """
        Test listing ingredients to those assigned to recipes.
        """
        ingredient_1 = Ingredient.objects.create(user=self.user, name='Ingredient 1')
        ingredient_2 = Ingredient.objects.create(user=self.user, name='Ingredient 2')

        recipe = Recipe.objects.create(
            user=self.user,
            title='Recipe',
            time_minutes=5,
            price=Decimal('4.50')
        )
        recipe.ingredients.add(ingredient_1)

        response = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        serializer_1 = IngredientSerializer(ingredient_1)
        serializer_2 = IngredientSerializer(ingredient_2)

        self.assertIn(serializer_1.data, response.data)
        self.assertNotIn(serializer_2.data, response.data)

    def test_filtered_ingredients_is_unique(self):
        """
        Test filtered ingredients returns a unique list.
        """
        ingredient = Ingredient.objects.create(user=self.user, name='Ingredient 1')
        Ingredient.objects.create(user=self.user, name='Ingredient 2')

        recipe_1 = Recipe.objects.create(
            user=self.user,
            title='Recipe 1',
            time_minutes=60,
            price=Decimal('7.50')
        )
        recipe_2 = Recipe.objects.create(
            user=self.user,
            title='Recipe 2',
            time_minutes=45,
            price=Decimal('6.25')
        )

        recipe_1.ingredients.add(ingredient)
        recipe_2.ingredients.add(ingredient)

        response = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(len(response.data), 1)
