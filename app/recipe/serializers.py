"""
Serializers for the recipe api view.
"""
from rest_framework import serializers

from core.models import Recipe, Tag


class TagSerializer(serializers.ModelSerializer):
    """
    Serializer for the tags.
    """

    class Meta:
        model = Tag
        fields = ['id', 'name']
        read_only_fields = ['id']


class RecipeSerializer(serializers.ModelSerializer):
    """
    Serializer for the recipes.
    """
    tags = TagSerializer(many=True, required=False)

    class Meta:
        model = Recipe
        fields = ['id', 'title', 'time_minutes', 'price', 'link', 'tags']
        read_only_fields = ['id']

    def create(self, validated_data):
        """
        Create a recipe.
        """
        tags = validated_data.pop('tags', [])
        recipe = Recipe.objects.create(**validated_data)
        authenticated_user = self.context['request'].user
        for tag in tags:
            tag_object, created = Tag.objects.get_or_create(
                user=authenticated_user, **tag
            )
            recipe.tags.add(tag_object)
        return recipe


class RecipeDetailSerializer(RecipeSerializer):
    """
    Serializer for the recipe detail.
    """

    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + ['description']
