from django.urls import include, path

from kanban.accounts import views
from kanban.projects import urls as project_urls

app_name = "accounts"

urlpatterns = [
    path("", views.index, name="index"),
    path("new/", views.new, name="new"),
    path("create/", views.create, name="create"),
    path("profile/", views.profile, name="profile"),
    path("invitations/<str:token>/", views.invitation_accept, name="invitation_accept"),
    path("<int:account_id>/", views.dashboard, name="dashboard"),
    path("<int:account_id>/members/", views.members, name="members"),
    path("<int:account_id>/members/search/", views.member_search, name="member_search"),
    path("<int:account_id>/members/<int:member_id>/", views.member, name="member"),
    path(
        "<int:account_id>/members/<int:member_id>/role/",
        views.member_role,
        name="member_role",
    ),
    path(
        "<int:account_id>/members/<int:member_id>/remove/",
        views.member_remove,
        name="member_remove",
    ),
    path(
        "<int:account_id>/invitations/",
        views.invitation_create,
        name="invitation_create",
    ),
]

# Project, post and comment routes are nested under an account, but live in
# their own namespaces ("projects:", "posts:", "comments:").
nested = [
    path("<int:account_id>/projects/", include(project_urls.projects)),
    path(
        "<int:account_id>/projects/<int:project_id>/posts/", include(project_urls.posts)
    ),
    path(
        "<int:account_id>/projects/<int:project_id>/posts/<int:post_id>/comments/",
        include(project_urls.comments),
    ),
]
