"""
Views for the recipe api.
"""
from rest_framework import viewsets, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import Recipe, Tag, Ingredient
from recipe import serializers


class RecipeViewSet(viewsets.ModelViewSet):
    """
    Viewset for manage recipe apis.
    """
    queryset = Recipe.objects.all()
    serializer_class = serializers.RecipeDetailSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Retrieve recipes for authenticated user.
        """
        return self.queryset.filter(user=self.request.user).order_by('-id')

    def get_serializer_class(self):
        """
        Return the serializer class for request.
        """
        if self.action == 'list':
            return serializers.RecipeSerializer
        elif self.action == 'upload_image':
            return serializers.RecipeImageSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        """
        Create a new recipe.
        """
        serializer.save(user=self.request.user)

    @action(methods=['POST'], detail=True, url_path='upload-image')
    def upload_image(self, request, pk=None):
         """
         Upload an image to recipe.
         """
         recipe = self.get_object()
         serializer = self.get_serializer(recipe, data=request.data)

         if serializer.is_valid():
             serializer.save()
             return Response(serializer.data, status.HTTP_200_OK)
         return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)


class BaseRecipeAttrViewSet(viewsets.ModelViewSet):
    """
    Base viewset for manage recipe attributes.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter queryset to authenticated user.
        """
        return self.queryset.filter(user=self.request.user).order_by('-name')


class TagViewSet(BaseRecipeAttrViewSet):
    """
    Viewset for manage tags apis.
    """
    queryset = Tag.objects.all()
    serializer_class = serializers.TagSerializer


class IngredientViewSet(BaseRecipeAttrViewSet):
    """
    Viewset for manage ingredients apis.
    """
    queryset = Ingredient.objects.all()
    serializer_class = serializers.IngredientSerializer
