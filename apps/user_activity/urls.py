from django.urls import path

from apps.user_activity import views

urlpatterns = [
    path("associations", views.AssociationListCreateView.as_view(), name="associations"),
    path("associations/<int:association_id>", views.AssociationDetailView.as_view(), name="association_detail"),
    path("users/register", views.register_user, name="register_user"),
    path("users/superadmin", views.create_superadmin, name="create_superadmin"),
    path("users", views.list_users, name="list_users"),
    path("users/<int:user_id>/role", views.assign_user_role, name="assign_user_role"),
    path("roles", views.roles_list_create, name="roles_list_create"),
    path("roles/<int:role_id>", views.role_detail, name="role_detail"),
    path("users/admin-create", views.admin_create_user, name="admin_create_user"),
    path("users/<int:user_id>", views.UserDetailView.as_view(), name="user_detail"),
    path("users/login", views.login, name="login"),
    path("users/forgot-password", views.forgot_password, name="forgot_password"),
    path("users/reset-password", views.reset_password, name="reset_password"),
    path("logbooks", views.create_logbook, name="create_logbook"),
    path("logbooks/me", views.list_my_logbooks, name="list_my_logbooks"),
    path("logbooks/<int:logbook_id>", views.logbook_detail, name="logbook_detail"),
    path("chat", views.chat_with_assistant, name="chat_with_assistant"),
    path("whatsapp", views.whatsapp_webhook, name="whatsapp_webhook"),
]
