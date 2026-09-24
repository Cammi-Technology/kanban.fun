from __future__ import annotations

from django.contrib import admin

from kanban.projects.models import Comment, Mention, Post, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin[Project]):
    list_display = ("name", "account", "created_at")
    search_fields = ("name",)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin[Post]):
    list_display = ("title", "project", "author", "published", "created_at")
    list_filter = ("published",)
    search_fields = ("title",)
    raw_id_fields = ("author", "project")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin[Comment]):
    list_display = ("id", "post", "author", "created_at")
    raw_id_fields = ("author", "post")


@admin.register(Mention)
class MentionAdmin(admin.ModelAdmin[Mention]):
    list_display = ("id", "post", "comment", "mentioned", "created_at")
