from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import Group, Permission

# rbac/models.py
class Menu(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True)  # fa fa-user
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)
    url = models.CharField(max_length=200, blank=True)
    order = models.IntegerField(default=0)
    permissions = models.ManyToManyField(Permission, blank=True)

    def __str__(self):
        return self.name

class RoleMenuPermission(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE)

    # Optional fine-grained control
    can_view = models.BooleanField(default=True)
    can_add = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.group.name} → {self.menu.name}"
from django.contrib.auth.models import User
from django.db import models


class UserMenuPermission(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="menu_permissions"
    )

    menu = models.ForeignKey(
        Menu,
        on_delete=models.CASCADE
    )

    can_view = models.BooleanField(
        default=True
    )

    class Meta:

        unique_together = (
            "user",
            "menu"
        )

    def __str__(self):

        return (
            f"{self.user.username}"
            f" - "
            f"{self.menu.name}"
        )