"""
Database models.
"""
import uuid
import os

from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)
from django.conf import settings


def recipe_image_file_path(instance, filename):
    """
    Generate file path for new recipe image.
    """
    # Extracting the extension(.jpg/.png) of the file name:
    extension = os.path.splitext(filename)[1]
    # Creating our own file name by creating UUID, and appending the extracted
    # extension to the end:
    filename = f'{uuid.uuid4()}{extension}'
    # By using the os.path.join method, we consider path spelling differences in
    # operating systems (e.g. in Windows it'll be uploads\recipe\{filename}, and in
    # Linux it'll be uploads/recipe/{filename}):
    return os.path.join('uploads', 'recipe', filename)


class UserManager(BaseUserManager):
    """
    Manager for users.
    """

    def create_user(self, email, password=None, **extra_fields):
        """
        Create, save, and return a new user.
        """
        if not email:
            raise ValueError('User must have an email address.')
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        """
        Create and return a new superuser.
        """
        user = self.create_user(email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    """
    User in the system.
    """
    email = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'


class Recipe(models.Model):
    """
    Recipe object.
    """
    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    time_minutes = models.IntegerField()
    price = models.DecimalField(max_digits=5, decimal_places=2)
    link = models.CharField(max_length=1023, blank=True)
    tags = models.ManyToManyField(to='Tag')
    ingredients = models.ManyToManyField(to='Ingredient')
    image = models.ImageField(null=True, upload_to=recipe_image_file_path)

    def __str__(self):
        return self.title


class Tag(models.Model):
    """
    Tag object for filtering recipes.
    """
    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=63)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """
    Ingredient object for filtering recipes.
    """
    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name
