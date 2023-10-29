"""
Tests for the recipe api.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer


RECIPES_URL = reverse('recipe:recipe-list')


# The reason we define a method, but not a variable for detail url is, we have
# different urls for each recipe, and we must give a recipe_id parameter to the reverse
# method.
def detail_url(recipe_id):
    """
    Create and return a recipe detail url.
    """
    return reverse('recipe:recipe-detail', args=[recipe_id])


def create_recipe(user, **params):
    """
    Create and return a sample recipe.
    """
    defaults = {
        'title': 'Sample recipe title',
        'description': 'Sample description',
        'time_minutes': 22,
        'price': Decimal('5.25'),
        'link': 'http://example.com/recipe.pdf',
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    """
    Create and return a new user.
    """
    return get_user_model().objects.create_user(**params)


class PublicRecipeAPITests(TestCase):
    """
    Test unauthenticated api requests.
    """

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """
        Test auth is required to call api.
        """
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITests(TestCase):
    """
    Test authenticated api requests.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='user@example.com', password='testpass123')
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """
        Test retrieving a list of recipes.
        """
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        response = self.client.get(RECIPES_URL)

        # Get all recipes with the reverse order by id. That means, we will return the
        # list with newer recipes first:
        recipes = Recipe.objects.all().order_by('-id')
        # Serializers can either return a detail, which is just one item, or we can
        # return a list of items. When we pass many=True, tells it that we want to pass
        # in a list of items:
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        """
        Test list of recipes is limited to authenticated user.
        """
        other_user = create_user(email='other@example.com', password='testpass123')
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        response = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user).order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_get_recipe_detail(self):
        """
        Test get recipe detail.
        """
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)

        response = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(response.data, serializer.data)

    def test_create_recipe(self):
        """
        Test create a recipe.
        """
        new_user = {
            'title': 'Sample recipe',
            'time_minutes': 30,
            'price': Decimal('5.99'),
        }
        response = self.client.post(RECIPES_URL, new_user)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=response.data['id'])

        for k, v in new_user.items():
            # Get a named attribute from an object; getattr(recipe, k) is equivalent to
            # recipe.k. In this case recipe.k must be equal to v
            # (e.g. recipe.title = 'Sample recipe'):
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """
        Test partial update of a recipe.
        """
        original_link = 'https://example.com/recipe.pdf'
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe title',
            link=original_link
        )
        payload = {'title': 'New recipe title', }
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """
        Test full update of a recipe.
        """
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe title',
            description='Sample recipe description',
            link='https://example.com/recipe.pdf'
        )

        payload = {
            'title': 'New recipe title',
            'description': 'New recipe description',
            'link': 'https://example.com/new-recipe.pdf',
            'time_minutes': 10,
            'price': Decimal('2.50'),
        }
        url = detail_url(recipe.id)
        response = self.client.put(url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """
        Test changing the recipe user results in an error.
        """
        new_user = create_user(email='user2@example.com', password='testpass123')
        recipe = create_recipe(user=self.user)

        payload = {'user': new_user.id}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)
        recipe.refresh_from_db()

        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """
        Test deleting a recipe successful.
        """
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_recipe_of_another_user(self):
        """
        Test deleting another user's recipe gives error.
        """
        new_user = create_user(email='user2@example.com', password='testpass123')
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        """
        Test creating a recipe with new tags.
        """
        payload = {
            'title': 'Recipe title',
            'time_minutes': 30,
            'price': Decimal('2.50'),
            'tags': [{'name': 'Tag name 1'}, {'name': 'Tag name 2'}]
        }
        response = self.client.post(RECIPES_URL, payload, format='json')
        recipes = Recipe.objects.filter(user=self.user)
        recipe = recipes[0]

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(recipes.count(), 1)
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            tag_exists = recipe.tags.filter(user=self.user, name=tag['name']).exists()
            self.assertTrue(tag_exists)

    def test_create_recipe_with_existing_tags(self):
        """
        Test creating a recipe with existing tags.
        """
        tag_1 = Tag.objects.create(user=self.user, name='Tag name 1')
        payload = {
            'title': 'Recipe title',
            'time_minutes': 30,
            'price': Decimal('2.50'),
            'tags': [{'name': 'Tag name 1'}, {'name': 'Tag name 2'}]
        }
        response = self.client.post(RECIPES_URL, payload, format='json')
        recipes = Recipe.objects.filter(user=self.user)
        recipe = recipes[0]

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(recipes.count(), 1)
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_1, recipe.tags.all())
        for tag in payload['tags']:
            tag_exists = recipe.tags.filter(user=self.user, name=tag['name']).exists()
            self.assertTrue(tag_exists)

    def test_create_tag_on_update_recipe(self):
        """
        Test creating tag when updating a recipe.
        """
        recipe = create_recipe(user=self.user)
        payload = {'tags': [{'name': 'Tag name'}]}
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='Tag name')
        self.assertIn(new_tag, recipe.tags.all())
                      
    def test_assign_existing_tag_on_update_recipe(self):
        """
        Test assigning an existing tag when updating a recipe.
        """
        tag_1 = Tag.objects.create(user=self.user, name='Tag name 1')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_1)

        tag_2 = Tag.objects.create(user=self.user, name='Tag name 2')
        payload = {'tags': [{'name': 'Tag name 2'}]}
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(tag_2, recipe.tags.all())
        self.assertNotIn(tag_1, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """
        Test clearing a recipe's tags.
        """
        tag = Tag.objects.create(user=self.user, name='Tag name 1')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)

        payload = {'tags': []}
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)
