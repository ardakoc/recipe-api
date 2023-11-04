"""
Tests for the tags api.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag, Recipe
from recipe.serializers import TagSerializer


TAGS_URL = reverse('recipe:tag-list')


def detail_url(tag_id):
    """
    Create and return a tag detail url.
    """
    return reverse('recipe:tag-detail', args=[tag_id])


def create_user(email='user@example.com', password='testpass123'):
    """
    Create and return a new user.
    """
    return get_user_model().objects.create_user(email, password)


class PublicTagsApiTests(TestCase):
    """
    Test unauthenticated api requests.
    """

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """
        Test auth is required to call api.
        """
        response = self.client.get(TAGS_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsAPITests(TestCase):
    """
    Test authenticated api requests.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """
        Test retrieving a list of tags.
        """
        Tag.objects.create(user=self.user, name='Sample tag 1')
        Tag.objects.create(user=self.user, name='Sample tag 2')

        response = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_tags_limited_to_user(self):
        """
        Test list of tags is limited to authenticated user.
        """
        other_user = create_user(email='other@example.com', password='testpass123')
        Tag.objects.create(user=other_user, name='Sample tag 1')
        tag = Tag.objects.create(user=self.user, name='Sample tag 2')

        response = self.client.get(TAGS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], tag.name)
        self.assertEqual(response.data[0]['id'], tag.id)

    def test_update_tag(self):
        """
        Test updating a tag.
        """
        tag = Tag.objects.create(user=self.user, name='Sample tag name')
        payload = {'name': 'New name'}
        url = detail_url(tag.id)
        response = self.client.patch(url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])
        self.assertEqual(tag.user, self.user)

    def test_update_user_returns_error(self):
        """
        Test changing the tag user results in an error.
        """
        new_user = create_user(email='user2@example.com', password='testpass123')
        tag = Tag.objects.create(user=self.user, name='Sample tag')

        payload = {'user': new_user.id}
        url = detail_url(tag.id)
        self.client.patch(url, payload)
        tag.refresh_from_db()

        self.assertEqual(tag.user, self.user)

    def test_delete_tag(self):
        """
        Test deleting a tag successful.
        """
        tag = Tag.objects.create(user=self.user)

        url = detail_url(tag.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Tag.objects.filter(id=tag.id).exists())

    def test_delete_recipe_of_another_user(self):
        """
        Test deleting another user's tag gives error.
        """
        new_user = create_user(email='user2@example.com', password='testpass123')
        tag = Tag.objects.create(user=new_user)

        url = detail_url(tag.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Tag.objects.filter(id=tag.id).exists())

    def test_filter_tags_assigned_to_recipes(self):
        """
        Test listing tags to those assigned to recipes.
        """
        tag_1 = Tag.objects.create(user=self.user, name='Tag 1')
        tag_2 = Tag.objects.create(user=self.user, name='Tag 2')

        recipe = Recipe.objects.create(
            user=self.user,
            title='Recipe',
            time_minutes=5,
            price=Decimal('4.50')
        )
        recipe.tags.add(tag_1)

        response = self.client.get(TAGS_URL, {'assigned_only': 1})

        serializer_1 = TagSerializer(tag_1)
        serializer_2 = TagSerializer(tag_2)

        self.assertIn(serializer_1.data, response.data)
        self.assertNotIn(serializer_2.data, response.data)

    def test_filtered_tags_is_unique(self):
        """
        Test filtered tags returns a unique list.
        """
        tag = Tag.objects.create(user=self.user, name='Tag 1')
        Tag.objects.create(user=self.user, name='Tag 2')

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

        recipe_1.tags.add(tag)
        recipe_2.tags.add(tag)

        response = self.client.get(TAGS_URL, {'assigned_only': 1})

        self.assertEqual(len(response.data), 1)
