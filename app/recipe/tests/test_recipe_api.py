"""
Tests for the recipe api.
"""
import tempfile
import os

from decimal import Decimal
from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient
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


def image_upload_url(recipe_id):
    """
    Create and return a image upload url.
    """
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


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

    def test_create_recipe_with_new_ingredients(self):
        """
        Test creating a recipe with new ingredients.
        """
        payload = {
            'title': 'Recipe title',
            'time_minutes': 30,
            'price': Decimal('2.50'),
            'ingredients': [
                {'name': 'Ingredient name 1'},
                {'name': 'Ingredient name 2'}
            ]
        }
        response = self.client.post(RECIPES_URL, payload, format='json')
        recipes = Recipe.objects.filter(user=self.user)
        recipe = recipes[0]

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(recipes.count(), 1)
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload['ingredients']:
            ingredient_exists = recipe.ingredients.filter(
                user=self.user,
                name=ingredient['name']
            ).exists()
            self.assertTrue(ingredient_exists)

    def test_create_recipe_with_existing_ingredients(self):
        """
        Test creating a recipe with existing ingredients.
        """
        ingredient_1 = Ingredient.objects.create(
            user=self.user,
            name='Ingredient name 1'
        )
        payload = {
            'title': 'Recipe title',
            'time_minutes': 30,
            'price': Decimal('2.50'),
            'ingredients': [
                {'name': 'Ingredient name 1'},
                {'name': 'Ingredient name 2'}
            ]
        }
        response = self.client.post(RECIPES_URL, payload, format='json')
        recipes = Recipe.objects.filter(user=self.user)
        recipe = recipes[0]

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(recipes.count(), 1)
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient_1, recipe.ingredients.all())
        for ingredient in payload['ingredients']:
            ingredient_exists = recipe.ingredients.filter(
                user=self.user,
                name=ingredient['name']
            ).exists()
            self.assertTrue(ingredient_exists)

    def test_create_ingredient_on_update_recipe(self):
        """
        Test creating ingredient when updating a recipe.
        """
        recipe = create_recipe(user=self.user)
        payload = {'ingredients': [{'name': 'Ingredient name'}]}
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(user=self.user, name='Ingredient name')
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_assign_existing_ingredient_on_update_recipe(self):
        """
        Test assigning an existing ingredient when updating a recipe.
        """
        ingredient_1 = Ingredient.objects.create(
            user=self.user,
            name='Ingredient name 1'
        )
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient_1)

        ingredient_2 = Ingredient.objects.create(
            user=self.user,
            name='Ingredient name 2'
        )
        payload = {'ingredients': [{'name': 'Ingredient name 2'}]}
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient_2, recipe.ingredients.all())
        self.assertNotIn(ingredient_1, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        """
        Test clearing a recipe's ingredients.
        """
        ingredient = Ingredient.objects.create(user=self.user, name='Ingredient name')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        payload = {'ingredients': []}
        url = detail_url(recipe.id)
        response = self.client.patch(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)

    def test_filter_by_tags(self):
        """
        Test filtering recipes by tags.
        """
        recipe_1 = create_recipe(user=self.user, title='Recipe 1')
        recipe_2 = create_recipe(user=self.user, title='Recipe 2')
        recipe_3 = create_recipe(user=self.user, title='Recipe 3')

        tag_1 = Tag.objects.create(user=self.user, name='Tag 1')
        tag_2 = Tag.objects.create(user=self.user, name='Tag 2')

        recipe_1.tags.add(tag_1)
        recipe_2.tags.add(tag_2)

        params = {'tags': f'{tag_1.id},{tag_2.id}'}
        response = self.client.get(RECIPES_URL, params)

        serializer_1 = RecipeSerializer(recipe_1)
        serializer_2 = RecipeSerializer(recipe_2)
        serializer_3 = RecipeSerializer(recipe_3)

        self.assertIn(serializer_1.data, response.data)
        self.assertIn(serializer_2.data, response.data)
        self.assertNotIn(serializer_3.data, response.data)

    def test_filter_by_ingredients(self):
        """
        Test filtering recipes by ingredients.
        """
        recipe_1 = create_recipe(user=self.user, title='Recipe 1')
        recipe_2 = create_recipe(user=self.user, title='Recipe 2')
        recipe_3 = create_recipe(user=self.user, title='Recipe 3')

        ingredient_1 = Ingredient.objects.create(user=self.user, name='Ingredient 1')
        ingredient_2 = Ingredient.objects.create(user=self.user, name='Ingredient 2')

        recipe_1.ingredients.add(ingredient_1)
        recipe_2.ingredients.add(ingredient_2)

        params = {'ingredients': f'{ingredient_1.id},{ingredient_2.id}'}
        response = self.client.get(RECIPES_URL, params)

        serializer_1 = RecipeSerializer(recipe_1)
        serializer_2 = RecipeSerializer(recipe_2)
        serializer_3 = RecipeSerializer(recipe_3)

        self.assertIn(serializer_1.data, response.data)
        self.assertIn(serializer_2.data, response.data)
        self.assertNotIn(serializer_3.data, response.data)


class ImageUploadTests(TestCase):
    """
    Tests for the image upload api.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='user@example.com', password='testpass123')
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        """
        Test uploading an image to a recipe.
        """
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            payload = {'image': image_file}
            response = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('image', response.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """
        Test uploading an invalid image.
        """
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'Not an image'}
        response = self.client.post(url, payload, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
