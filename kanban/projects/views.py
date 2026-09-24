"""Project, post and comment views.

Normal browser requests get full pages and 303 redirects after a successful
form submission. HTMX requests get htpy fragments; invalid HTMX submissions
get the form fragment back with HTTP 422.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.middleware.csrf import get_token
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from kanban.accounts.access import require_membership, require_project
from kanban.cable.broadcast import post_topic, project_topic
from kanban.core import tiptap
from kanban.core.htmx import redirect, wants_fragment
from kanban.projects import components, policies, services
from kanban.projects.forms import CommentForm, PostForm, ProjectForm
from kanban.projects.models import Comment, Post
from kanban.ui.http import html_response, render_page

UNPROCESSABLE = 422


@require_GET
@login_required
def project_new(request: HttpRequest, account_id: int) -> HttpResponse:
    member = require_membership(request, account_id)
    return render_page(
        request,
        "New Project",
        components.project_new(
            ProjectForm(), account_id=account_id, csrf_token=get_token(request)
        ),
        membership=member,
    )


@require_POST
@login_required
def project_create(request: HttpRequest, account_id: int) -> HttpResponse:
    member = require_membership(request, account_id)
    form = ProjectForm(request.POST)
    if not form.is_valid():
        if wants_fragment(request):
            return html_response(
                components.project_form(
                    form, account_id=account_id, csrf_token=get_token(request)
                ),
                status=UNPROCESSABLE,
            )
        return render_page(
            request,
            "New Project",
            components.project_new(
                form, account_id=account_id, csrf_token=get_token(request)
            ),
            membership=member,
            status=UNPROCESSABLE,
        )
    project = services.create_project(
        member,
        name=form.cleaned_data["name"],
        description=form.cleaned_data["description"],
    )
    messages.success(request, "Your Project was successfully created. Good Luck!")
    return redirect(request, reverse("projects:show", args=[account_id, project.pk]))


@require_GET
@login_required
def project_show(
    request: HttpRequest, account_id: int, project_id: int
) -> HttpResponse:
    member = require_membership(request, account_id)
    project = require_project(member, project_id)
    return render_page(
        request,
        project.name,
        components.project_show(project),
        membership=member,
        project=project,
    )


@require_GET
@login_required
def post_index(request: HttpRequest, account_id: int, project_id: int) -> HttpResponse:
    member = require_membership(request, account_id)
    project = require_project(member, project_id)
    category = request.GET.get("category") or None
    posts = services.published_posts_with_counts(project, category)
    drafts = services.drafts_with_counts(project, member)
    content = components.posts_index(
        project, posts, drafts, services.categories(project), category
    )
    return render_page(
        request,
        "Message Board",
        content,
        membership=member,
        project=project,
        streams=[project_topic(project.pk)],
    )


def _editor_page(
    request: HttpRequest,
    *,
    member_title: str,
    form: PostForm,
    post: Post | None,
    doc: tiptap.Doc,
    status: int = 200,
    account_id: int,
    project_id: int,
) -> HttpResponse:
    member = require_membership(request, account_id)
    project = require_project(member, project_id)
    kwargs = {
        "project": project,
        "post": post,
        "doc": doc,
        "categories": services.categories(project),
        "csrf_token": get_token(request),
    }
    if status == UNPROCESSABLE and wants_fragment(request):
        return html_response(components.post_form(form, **kwargs), status=status)  # type: ignore[arg-type]
    return render_page(
        request,
        member_title,
        components.post_editor(form, **kwargs),  # type: ignore[arg-type]
        membership=member,
        project=project,
        status=status,
    )


@require_GET
@login_required
def post_new(request: HttpRequest, account_id: int, project_id: int) -> HttpResponse:
    member = require_membership(request, account_id)
    project = require_project(member, project_id)
    if not policies.can_create_post(member, project):
        raise Http404
    return _editor_page(
        request,
        member_title="Add a Post",
        form=PostForm(),
        post=None,
        doc=tiptap.empty_doc(),
        account_id=account_id,
        project_id=project_id,
    )


@require_POST
@login_required
def post_create(request: HttpRequest, account_id: int, project_id: int) -> HttpResponse:
    member = require_membership(request, account_id)
    project = require_project(member, project_id)
    if not policies.can_create_post(member, project):
        raise Http404
    form = PostForm(request.POST)
    if not form.is_valid():
        return _editor_page(
            request,
            member_title="Add a Post",
            form=form,
            post=None,
            doc=PostForm(request.POST).parsed_content(),
            status=UNPROCESSABLE,
            account_id=account_id,
            project_id=project_id,
        )
    data = form.cleaned_data
    post = services.save_post(
        member,
        project,
        post=None,
        title=data["title"],
        category=data["category"],
        doc=data["doc"],
        publish=bool(data["published"]),
    )
    messages.success(
        request, "Your Post was successful" if post.published else "Draft saved"
    )
    return redirect(
        request, reverse("posts:show", args=[account_id, project_id, post.pk])
    )


def _post_or_404(project_id: int, post_id: int) -> Post:
    post = (
        Post.objects.select_related("author__user", "project__account")
        .filter(pk=post_id, project_id=project_id)
        .first()
    )
    if post is None:
        raise Http404("No such post")
    return post


@require_GET
@login_required
def post_show(
    request: HttpRequest, account_id: int, project_id: int, post_id: int
) -> HttpResponse:
    member = require_membership(request, account_id)
    project = require_project(member, project_id)
    post = _post_or_404(project.pk, post_id)
    if not policies.can_view_post(member, post):
        raise Http404
    return render_page(
        request,
        post.title,
        components.post_show(
            post,
            services.post_comments(post),
            can_comment=policies.can_comment(member, post),
            csrf_token=get_token(request),
        ),
        membership=member,
        project=project,
        streams=[post_topic(post.pk)],
    )


@require_GET
@login_required
def post_edit(
    request: HttpRequest, account_id: int, project_id: int, post_id: int
) -> HttpResponse:
    member = require_membership(request, account_id)
    project = require_project(member, project_id)
    post = _post_or_404(project.pk, post_id)
    if not policies.can_edit_post(member, post):
        raise Http404
    form = PostForm(initial={"title": post.title, "category": post.category})
    return _editor_page(
        request,
        member_title="Edit Post",
        form=form,
        post=post,
        doc=post.content,
        account_id=account_id,
        project_id=project_id,
    )


@require_http_methods(["POST", "PATCH"])
@login_required
def post_update(
    request: HttpRequest, account_id: int, project_id: int, post_id: int
) -> HttpResponse:
    member = require_membership(request, account_id)
    project = require_project(member, project_id)
    post = _post_or_404(project.pk, post_id)
    if not policies.can_edit_post(member, post):
        raise Http404
    form = PostForm(request.POST)
    if not form.is_valid():
        return _editor_page(
            request,
            member_title="Edit Post",
            form=form,
            post=post,
            doc=PostForm(request.POST).parsed_content(),
            status=UNPROCESSABLE,
            account_id=account_id,
            project_id=project_id,
        )
    data = form.cleaned_data
    services.save_post(
        member,
        project,
        post=post,
        title=data["title"],
        category=data["category"],
        doc=data["doc"],
        publish=bool(data["published"]),
    )
    messages.success(request, "Your Post was successfully updated")
    return redirect(
        request, reverse("posts:show", args=[account_id, project_id, post.pk])
    )


@require_POST
@login_required
def comment_create(
    request: HttpRequest, account_id: int, project_id: int, post_id: int
) -> HttpResponse:
    member = require_membership(request, account_id)
    project = require_project(member, project_id)
    post = _post_or_404(project.pk, post_id)
    if not policies.can_view_post(member, post):
        raise Http404
    if not policies.can_comment(member, post):
        return HttpResponse("Comments are closed on drafts", status=403)
    form = CommentForm(request.POST)
    csrf = get_token(request)
    if not form.is_valid():
        if wants_fragment(request):
            return html_response(
                components.comment_form(
                    post, form, doc=form.parsed_content(), csrf_token=csrf
                ),
                status=UNPROCESSABLE,
            )
        messages.error(request, "Comment can't be blank")
        return redirect(
            request, reverse("posts:show", args=[account_id, project_id, post.pk])
        )
    services.add_comment(member, post, form.cleaned_data["doc"])
    if wants_fragment(request):
        comments = services.post_comments(post)
        return html_response(
            [
                components.comment_form(post, None, csrf_token=csrf),
                *components.comments_broadcast(post, comments),  # type: ignore[misc]
            ]
        )
    messages.success(request, "Your Comment was successfully created")
    return redirect(
        request, reverse("posts:show", args=[account_id, project_id, post.pk])
    )


@require_http_methods(["POST", "DELETE"])
@login_required
def comment_delete(
    request: HttpRequest,
    account_id: int,
    project_id: int,
    post_id: int,
    comment_id: int,
) -> HttpResponse:
    member = require_membership(request, account_id)
    project = require_project(member, project_id)
    post = _post_or_404(project.pk, post_id)
    comment = (
        Comment.objects.select_related("author", "post")
        .filter(pk=comment_id, post=post)
        .first()
    )
    if comment is None or not policies.can_view_post(member, post):
        raise Http404
    if not policies.can_delete_comment(member, comment):
        return HttpResponse("You can't delete this comment", status=403)
    services.delete_comment(comment)
    if wants_fragment(request):
        comments = services.post_comments(post)
        return html_response(components.comment_heading(post, len(comments), oob=True))
    messages.success(request, "Your Comment was successfully removed")
    return redirect(
        request, reverse("posts:show", args=[account_id, project_id, post.pk])
    )
