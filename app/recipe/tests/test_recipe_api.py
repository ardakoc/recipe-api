"""
Tests for the recipe api.
"""
from decimal import Decimal
from rest_framework.test import APIClient

from core.models import Recipe


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
