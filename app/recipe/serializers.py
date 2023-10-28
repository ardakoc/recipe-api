"""
Serializers for the recipe api view.
"""
from rest_framework import serializers

from core.models import Recipe, Tag


class RecipeSerializer(serializers.ModelSerializer):
    """
    Serializer for the recipes.
    """

    class Meta:
        model = Recipe
        fields = ['id', 'title', 'time_minutes', 'price', 'link']
        read_only_fields = ['id']


class RecipeDetailSerializer(RecipeSerializer):
    """
    Serializer for the recipe detail.
    """

    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + ['description']


class TagSerializer(serializers.ModelSerializer):
    """
    Serializer for the tags.
    """

    class Meta:
        model = Tag
        fields = ['id', 'name']
        read_only_fields = ['id']
