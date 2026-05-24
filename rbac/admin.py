

# Register your models here.
from django.contrib import admin
from .models import Menu, RoleMenuPermission

admin.site.register(Menu)
admin.site.register(RoleMenuPermission)