# rbac/urls.py
from django.urls import path
from .views import permission_matrix, update_permission, update_user_permission

urlpatterns = [
    path("matrix/", permission_matrix, name="permission_matrix"),
    path("update-permission/", update_permission, name="update_permission"),
path("update-user-permission/",update_user_permission,name="update_user_permission"),

]