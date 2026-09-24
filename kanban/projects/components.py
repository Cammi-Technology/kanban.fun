"""htpy components for projects, the message board and comments.

Components here are request-independent so the same function renders the
first page load, the HTMX fragment and the WebSocket broadcast. Anything
viewer-specific (CSRF tokens, "is this mine?") is passed in or handled by the
``owner-only`` CSS convention described in ``kanban.ui.layout.owner_styles``.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from django.forms import Form
from django.urls import reverse
from htpy import (
    Element,
    Node,
    VoidElement,
    a,
    article,
    button,
    datalist,
    div,
    footer,
    form,
    h1,
    h2,
    header,
    input,
    label,
    li,
    nav,
    option,
    p,
    section,
    span,
    textarea,
    ul,
)

from kanban.accounts.models import Account
from kanban.core import tiptap
from kanban.projects.mentions import mention_link
from kanban.projects.models import Comment, Post, Project
from kanban.ui.components import (
    avatar,
    content_shell,
    form_errors,
    primary_button,
    quick_action_tile,
)
from kanban.ui.icons import icon

EXCERPT_LIMIT = 180


def excerpt(text: str) -> str:
    """Squish whitespace and cut to 177 characters + "..." (PR #106)."""
    squished = " ".join(text.split())
    if len(squished) > EXCERPT_LIMIT:
        return squished[: EXCERPT_LIMIT - 3] + "..."
    return squished


def short_date(post: Post) -> str:
    when = post.published_at or post.created_at
    return f"{when:%b} {when.day}"


def csrf_field(token: str | None) -> VoidElement | None:
    if token is None:
        return None
    return input(type="hidden", name="csrfmiddlewaretoken", value=token)


# ---------------------------------------------------------------- projects


def dashboard_project_list(
    account: Account, projects: Sequence[Project], *, oob: bool = False
) -> Element:
    return ul(
        id=f"account-{account.pk}-projects",
        class_="dashboard-projects__list",
        hx_swap_oob="morph" if oob else None,
    )[
        (
            li(class_="dashboard-projects__item", id=f"project-{project.pk}")[
                a(
                    href=reverse("projects:show", args=[account.pk, project.pk]),
                    class_="dashboard-projects__link",
                )[project.name]
            ]
            for project in projects
        )
    ]


def dashboard(account: Account, projects: Sequence[Project]) -> Element:
    return div(class_="dashboard-projects")[
        h1(class_="dashboard-projects__title")[account.name],
        div(class_="dashboard-projects__actions")[
            a(
                href=reverse("projects:new", args=[account.pk]),
                class_="dashboard-projects__new-project",
            )[
                span(class_="dashboard-projects__new-project-icon", aria_hidden="true")[
                    icon("plus-lg")
                ],
                "Make a new project",
            ],
        ],
        dashboard_project_list(account, projects),
        None
        if projects
        else p(class_="dashboard-projects__empty")[
            "No projects yet. Make one to get your team talking."
        ],
    ]


def project_show(project: Project) -> Element:
    return content_shell(
        div(class_="project-show__header")[
            h1(class_="project-show__title")[project.name],
            p(class_="project-show__description")[project.description]
            if project.description
            else None,
        ],
        nav(
            aria_label="Project tools",
            class_="project-dropdown__quick-actions project-show__tiles",
        )[
            quick_action_tile(
                href=reverse("posts:index", args=[project.account_id, project.pk]),
                icon_name="file-post",
                label_text="Posts",
            )
        ],
        width="narrow",
        extra_class="project-show",
    )


def project_form(form_obj: Form, *, account_id: int, csrf_token: str | None) -> Element:
    name = form_obj["name"]
    description = form_obj["description"]
    return form(
        id="project-form",
        class_="project-new__form",
        method="post",
        action=reverse("projects:create", args=[account_id]),
        hx_post=reverse("projects:create", args=[account_id]),
        hx_target="this",
        hx_swap="morph",
    )[
        csrf_field(csrf_token),
        div(class_="project-new__panel surface-panel")[
            h1(class_="sr-only")["New Project"],
            form_errors(form_obj),
            div(class_="project-new__fields")[
                div(class_="project-new__field")[
                    label(for_="project_name", class_="project-new__label")["Name"],
                    input(
                        id="project_name",
                        name=name.html_name,
                        value=name.value() or "",
                        required=True,
                        maxlength="200",
                        placeholder="Type a title",
                        class_="project-new__name",
                        autofocus=True,
                    ),
                ],
                div(class_="project-new__field")[
                    label(for_="project_description", class_="project-new__label")[
                        "Description"
                    ],
                    textarea(
                        id="project_description",
                        name=description.html_name,
                        rows="12",
                        placeholder="e.g. Plans for the next launch",
                        class_="project-new__description",
                    )[description.value() or ""],
                ],
            ],
            footer(class_="project-new__footer")[primary_button("Create Project")],
        ],
    ]


def project_new(form_obj: Form, *, account_id: int, csrf_token: str | None) -> Element:
    return content_shell(
        project_form(form_obj, account_id=account_id, csrf_token=csrf_token),
        width="narrow",
        extra_class="project-new",
    )


# ------------------------------------------------------------------- posts


def comment_count_badge(post: Post, count: int) -> Element | None:
    if not count:
        return None
    return span(class_="posts-index__count", aria_label=f"{count} comments")[str(count)]


def post_row(post: Post, comment_count: int) -> Element:
    author_name = post.author.user.name
    return li(class_="posts-index__item", id=f"post-row-{post.pk}")[
        a(
            href=reverse(
                "posts:show", args=[post.project.account_id, post.project_id, post.pk]
            ),
            class_="posts-index__link",
        )[
            avatar(author_name, size="lg"),
            div(class_="posts-index__body")[
                h2(class_="posts-index__post-title")[
                    post.title,
                    span(class_="post-category")[post.category]
                    if post.category
                    else None,
                    None if post.published else span(class_="post-draft")["Draft"],
                ],
                p(class_="posts-index__meta")[f"{author_name} • {short_date(post)}"],
                p(class_="posts-index__excerpt")[excerpt(post.plain_text())],
            ],
            comment_count_badge(post, comment_count),
        ]
    ]


def post_list(
    project: Project,
    posts: Sequence[tuple[Post, int]],
    *,
    list_id: str | None = None,
    oob: bool = False,
) -> Element:
    return ul(
        id=list_id or f"project-{project.pk}-posts",
        class_="posts-index__list",
        hx_swap_oob="morph" if oob else None,
    )[(post_row(post, count) for post, count in posts)]


def category_filter(
    project: Project, categories: Sequence[str], current: str | None
) -> Element | None:
    if not categories:
        return None
    base = reverse("posts:index", args=[project.account_id, project.pk])
    return nav(class_="posts-index__categories", aria_label="Categories")[
        a(
            href=base,
            class_="category-chip",
            aria_current="page" if not current else None,
            hx_get=base,
            hx_target="#posts-index",
            hx_select="#posts-index",
            hx_swap="morph",
            hx_push_url="true",
        )["All"],
        (
            a(
                href=f"{base}?category={category}",
                class_="category-chip",
                aria_current="page" if category == current else None,
                hx_get=f"{base}?category={category}",
                hx_target="#posts-index",
                hx_select="#posts-index",
                hx_swap="morph",
                hx_push_url="true",
            )[category]
            for category in categories
        ),
    ]


def posts_index(
    project: Project,
    posts: Sequence[tuple[Post, int]],
    drafts: Sequence[tuple[Post, int]],
    categories: Sequence[str],
    current_category: str | None,
) -> Element:
    account_id = project.account_id
    return content_shell(
        div(class_="posts-index__topbar")[
            p(class_="posts-index__project-name")[
                a(href=reverse("projects:show", args=[account_id, project.pk]))[
                    project.name
                ]
            ]
        ],
        div(class_="posts-index__panel surface-panel")[
            div(class_="posts-index__header")[
                h1["Message Board"],
                p["Send messages to your team!"],
            ],
            div(class_="posts-index__actions")[
                a(
                    href=reverse("posts:new", args=[account_id, project.pk]),
                    class_="posts-index__new-post primary-button",
                )[icon("plus-lg"), "New Post"],
                category_filter(project, categories, current_category),
            ],
            section(class_="posts-index__drafts", aria_label="Your drafts")[
                h2(class_="posts-index__section-title")["Your drafts"],
                post_list(project, drafts, list_id=f"project-{project.pk}-drafts"),
            ]
            if drafts
            else None,
            post_list(project, posts),
            div(class_="posts-index__empty")[
                p(class_="posts-index__empty-copy")["No posts yet."]
            ]
            if not posts
            else None,
        ],
        width="wide",
        extra_class="posts-index",
        id="posts-index",
    )


def rich_text_editor(
    *,
    name: str,
    doc: tiptap.Doc,
    mention_url: str,
    label_text: str,
    field_id: str,
    extra_class: str = "",
    placeholder: str = "Write away…",
    required: bool = False,
) -> Element:
    """A Tiptap editor that degrades to a plain textarea without JavaScript."""
    return div(
        class_=["rich-text", extra_class or None],
        data_rich_text="",
        data_mention_url=mention_url,
        data_initial=json.dumps(doc),
        data_placeholder=placeholder,
    )[
        label(for_=field_id, class_="sr-only")[label_text],
        textarea(
            id=field_id,
            name=name,
            rows="8",
            class_="rich-text__fallback",
            placeholder=placeholder,
            required=required,
        )[tiptap.plain_text(doc)],
    ]


def post_form(
    form_obj: Form,
    *,
    project: Project,
    post: Post | None,
    doc: tiptap.Doc,
    categories: Sequence[str],
    csrf_token: str | None,
) -> Element:
    account_id = project.account_id
    action = (
        reverse("posts:update", args=[account_id, project.pk, post.pk])
        if post is not None
        else reverse("posts:create", args=[account_id, project.pk])
    )
    title = form_obj["title"]
    category = form_obj["category"]
    submit_text = "Update this message" if post is not None else "Post this message"
    return form(
        id="post-form",
        class_="post-editor__form",
        method="post",
        action=action,
        hx_post=action,
        hx_target="this",
        hx_swap="morph",
    )[
        csrf_field(csrf_token),
        div(class_="surface-panel")[
            h1(class_="sr-only")["Edit Post" if post is not None else "Add a Post"],
            form_errors(form_obj),
            div(class_="post-editor__fields")[
                label(for_="post_title", class_="sr-only")["Title"],
                input(
                    id="post_title",
                    name=title.html_name,
                    value=title.value() or "",
                    required=True,
                    maxlength="200",
                    placeholder="Type a title…",
                    class_="post-editor__title",
                    autofocus=post is None,
                ),
                label(for_="post_category", class_="sr-only")["Category"],
                input(
                    id="post_category",
                    name=category.html_name,
                    value=category.value() or "",
                    maxlength="60",
                    placeholder="Category (optional)",
                    list="post-categories",
                    class_="post-editor__category",
                ),
                datalist(id="post-categories")[
                    (option(value=value) for value in categories)
                ],
                rich_text_editor(
                    name="content",
                    doc=doc,
                    mention_url=reverse("accounts:member_search", args=[account_id]),
                    label_text="Content",
                    field_id="post_content",
                    extra_class="post-editor__content",
                ),
            ],
            footer(class_="post-editor__footer")[
                button(
                    type="submit",
                    name="published",
                    value="false",
                    class_="secondary-button",
                )["Save as draft"]
                if post is None or not post.published
                else None,
                primary_button(submit_text, name="published", value="true"),
            ],
        ],
    ]


def breadcrumb(project: Project) -> Element:
    account_id = project.account_id
    return p(class_="post-editor__breadcrumb")[
        a(href=reverse("projects:show", args=[account_id, project.pk]))[project.name],
        span(aria_hidden="true")["  <  "],
        a(href=reverse("posts:index", args=[account_id, project.pk]))["Posts"],
    ]


def post_editor(
    form_obj: Form,
    *,
    project: Project,
    post: Post | None,
    doc: tiptap.Doc,
    categories: Sequence[str],
    csrf_token: str | None,
) -> Element:
    return content_shell(
        breadcrumb(project),
        post_form(
            form_obj,
            project=project,
            post=post,
            doc=doc,
            categories=categories,
            csrf_token=csrf_token,
        ),
        width="wide",
        extra_class="post-editor",
    )


def post_body(post: Post, *, oob: bool = False) -> Element:
    """Title, meta and content. Broadcast to ``post:<id>`` on every edit."""
    account_id = post.project.account_id
    return div(
        id=f"post-{post.pk}-body",
        class_="posts-show__body",
        hx_swap_oob="morph" if oob else None,
    )[
        header(class_="posts-show__header")[
            h1[post.title],
            p(class_="posts-show__meta")[
                f"{post.author.user.name} • {short_date(post)}",
                span(class_="post-category")[post.category] if post.category else None,
                None if post.published else span(class_="post-draft")["Draft"],
            ],
        ],
        div(class_="posts-show__content rich-content", data_highlight="")[
            tiptap.render(post.content, mention_link(account_id))
        ],
    ]


def comment_item(comment: Comment, *, account_id: int) -> Element:
    post = comment.post
    delete_url = reverse(
        "comments:delete", args=[account_id, post.project_id, post.pk, comment.pk]
    )
    name = comment.author.user.name
    return li(
        class_="posts-show__comment",
        id=comment.dom_id,
        data_owner=str(comment.author_id),
    )[
        avatar(name, size="md"),
        div(class_="posts-show__comment-body")[
            div(class_="posts-show__comment-meta")[
                span[f"{name} • {comment.created_at:%b} {comment.created_at.day}"],
                button(
                    type="button",
                    class_="comment-delete admin-or-owner",
                    hx_delete=delete_url,
                    hx_confirm="Delete this comment?",
                    hx_target=f"#{comment.dom_id}",
                    hx_swap="delete",
                    title="Delete comment",
                )[icon("trash"), span(class_="sr-only")["Delete comment"]],
            ],
            div(class_="posts-show__comment-content rich-content", data_highlight="")[
                tiptap.render(comment.content, mention_link(account_id))
            ],
        ],
    ]


def comment_list(
    post: Post, comments: Sequence[Comment], *, oob: bool = False
) -> Element:
    account_id = post.project.account_id
    return ul(
        id=f"post-{post.pk}-comments",
        class_="posts-show__comments-list",
        hx_swap_oob="morph" if oob else None,
    )[(comment_item(comment, account_id=account_id) for comment in comments)]


def comment_heading(post: Post, count: int, *, oob: bool = False) -> Element:
    return h2(
        id=f"post-{post.pk}-comments-heading",
        hx_swap_oob="morph" if oob else None,
    )[
        "Comments",
        span(class_="posts-show__comment-count")[f" ({count})"] if count else None,
    ]


def comment_form(
    post: Post,
    form_obj: Form | None,
    *,
    doc: tiptap.Doc | None = None,
    csrf_token: str | None,
) -> Element:
    account_id = post.project.account_id
    action = reverse("comments:create", args=[account_id, post.project_id, post.pk])
    return form(
        id=f"post-{post.pk}-comment-form",
        class_="posts-show__comment-form",
        method="post",
        action=action,
        hx_post=action,
        hx_target="this",
        hx_swap="morph",
    )[
        csrf_field(csrf_token),
        form_errors(form_obj) if form_obj is not None else None,
        rich_text_editor(
            name="content",
            doc=doc or tiptap.empty_doc(),
            mention_url=reverse("accounts:member_search", args=[account_id]),
            label_text="Comment",
            field_id=f"post-{post.pk}-comment-content",
            placeholder="Add a comment…",
            required=True,
        ),
        div[primary_button("Add Comment")],
    ]


def post_show(
    post: Post,
    comments: Sequence[Comment],
    *,
    can_comment: bool,
    csrf_token: str | None,
) -> Element:
    project = post.project
    account_id = project.account_id
    return content_shell(
        div(class_="posts-show__topbar", data_owner=str(post.author_id))[
            breadcrumb(project),
            a(
                href=reverse("posts:edit", args=[account_id, project.pk, post.pk]),
                class_="posts-show__edit owner-only",
            )["Edit"],
        ],
        article(class_="posts-show__panel surface-panel", id=post.dom_id)[
            post_body(post),
            section(
                class_="posts-show__comments",
                aria_labelledby=f"post-{post.pk}-comments-heading",
            )[
                comment_heading(post, len(comments)),
                comment_list(post, comments),
                div(class_="posts-show__comment-form-wrap")[
                    comment_form(post, None, csrf_token=csrf_token)
                ]
                if can_comment
                else p(class_="posts-show__comments-closed")[
                    "Publish this post to open comments."
                ],
            ],
        ],
        width="wide",
        extra_class="posts-show",
    )


def comments_broadcast(post: Post, comments: Sequence[Comment]) -> Node:
    return [
        comment_list(post, comments, oob=True),
        comment_heading(post, len(comments), oob=True),
    ]


def post_body_broadcast(post: Post) -> Node:
    return post_body(post, oob=True)


def post_list_broadcast(project: Project, posts: Sequence[tuple[Post, int]]) -> Node:
    return post_list(project, posts, oob=True)


def project_list_broadcast(account: Account, projects: Sequence[Project]) -> Node:
    return dashboard_project_list(account, projects, oob=True)
