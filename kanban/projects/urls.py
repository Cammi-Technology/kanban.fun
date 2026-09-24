from django.urls import path

from kanban.projects import views

projects = (
    [
        path("new/", views.project_new, name="new"),
        path("create/", views.project_create, name="create"),
        path("<int:project_id>/", views.project_show, name="show"),
    ],
    "projects",
)

posts = (
    [
        path("", views.post_index, name="index"),
        path("new/", views.post_new, name="new"),
        path("create/", views.post_create, name="create"),
        path("<int:post_id>/", views.post_show, name="show"),
        path("<int:post_id>/edit/", views.post_edit, name="edit"),
        path("<int:post_id>/update/", views.post_update, name="update"),
    ],
    "posts",
)

comments = (
    [
        path("", views.comment_create, name="create"),
        path("<int:comment_id>/", views.comment_delete, name="delete"),
    ],
    "comments",
)
