from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CampusUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_active")
    list_filter = ("role", "is_active")
    fieldsets = UserAdmin.fieldsets + (("CSRMS role", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("CSRMS role", {"fields": ("role",)}),)
