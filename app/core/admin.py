"""
Django admin customization.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from core import models


class UserAdmin(BaseUserAdmin):
    """
    Define the admin pages for users.
    """
    # Order the list by id:
    ordering = ['id']
    # Fields that we want to display in the list:
    list_display = ['email', 'name']
    # Divide the page into headings and set the fields for each heading
    # (Check the pattern of this attribute: django.contrib.auth.admin.UserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('name',)}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser',),
        }),
        (_('Important dates'), {'fields': ('last_login',)}),
    )
    readonly_fields = ['last_login']
    # Fields that we want to display in the add page
    # (Check the pattern of this attribute: django.contrib.auth.admin.UserAdmin):
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'name',
                'password1',
                'password2',
                'is_active',
                'is_staff',
                'is_superuser',
            ),
        }),
    )


admin.site.register(models.User, admin_class=UserAdmin)
admin.site.register(models.Recipe)
admin.site.register(models.Tag)
