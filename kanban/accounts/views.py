"""Accounts, dashboards, members, profiles, invitations and member search."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import password_validation
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from kanban.accounts import components, policies, services
from kanban.accounts.access import require_membership
from kanban.accounts.forms import (
    AcceptInvitationForm,
    AccountForm,
    InvitationForm,
    ProfileForm,
    RoleForm,
)
from kanban.accounts.models import Account, AccountUser, Invitation, User
from kanban.cable.broadcast import account_topic
from kanban.core.htmx import redirect, wants_fragment
from kanban.identity.services import current_user, optional_user, sign_in
from kanban.projects import components as project_components
from kanban.projects.mentions import membership_changed, search_members
from kanban.projects.models import Project
from kanban.ui.http import html_response, render_page

UNPROCESSABLE = 422


@require_GET
@login_required
def index(request: HttpRequest) -> HttpResponse:
    user = current_user(request)
    accounts = list(
        Account.objects.filter(memberships__user=user, memberships__is_active=True)
    )
    if not accounts:
        return redirect(request, reverse("accounts:new"))
    if len(accounts) == 1:
        return redirect(request, reverse("accounts:dashboard", args=[accounts[0].pk]))
    return render_page(request, "Accounts", components.account_index(accounts))


@require_GET
@login_required
def new(request: HttpRequest) -> HttpResponse:
    return render_page(
        request,
        "Create a new Account",
        components.account_new(AccountForm(), get_token(request)),
    )


@require_POST
@login_required
def create(request: HttpRequest) -> HttpResponse:
    form = AccountForm(request.POST)
    if not form.is_valid():
        if wants_fragment(request):
            return html_response(
                components.account_form(form, get_token(request)), status=UNPROCESSABLE
            )
        messages.error(
            request,
            "There was an error creating your account. "
            "Please review the information below.",
        )
        return render_page(
            request,
            "Create a new Account",
            components.account_new(form, get_token(request)),
            status=UNPROCESSABLE,
        )
    account = services.create_account(current_user(request), form.cleaned_data["name"])
    messages.success(request, "Your Account was successfully created")
    return redirect(request, reverse("accounts:dashboard", args=[account.pk]))


@require_GET
@login_required
def dashboard(request: HttpRequest, account_id: int) -> HttpResponse:
    member = require_membership(request, account_id)
    projects = list(Project.objects.filter(account_id=account_id))
    return render_page(
        request,
        member.account.name,
        project_components.dashboard(member.account, projects),
        membership=member,
        streams=[account_topic(account_id)],
    )


def _members(account_id: int) -> list[AccountUser]:
    return list(
        AccountUser.objects.filter(account_id=account_id, is_active=True)
        .select_related("user", "account")
        .order_by("user__first_name", "user__last_name")
    )


def _pending(account_id: int) -> list[Invitation]:
    from django.utils import timezone

    return list(
        Invitation.objects.filter(
            account_id=account_id,
            accepted_at__isnull=True,
            expires_at__gt=timezone.now(),
        )
    )


def _members_page(
    request: HttpRequest,
    member: AccountUser,
    invite_form: InvitationForm | None = None,
    status: int = 200,
) -> HttpResponse:
    return render_page(
        request,
        "Members",
        components.members_page(
            member.account,
            _members(member.account_id),
            _pending(member.account_id),
            member,
            invite_form,
            get_token(request),
        ),
        membership=member,
        status=status,
    )


@require_GET
@login_required
def members(request: HttpRequest, account_id: int) -> HttpResponse:
    return _members_page(request, require_membership(request, account_id))


@require_GET
@login_required
def member(request: HttpRequest, account_id: int, member_id: int) -> HttpResponse:
    viewer = require_membership(request, account_id)
    target = (
        AccountUser.objects.select_related("user", "account")
        .filter(pk=member_id, account_id=account_id)
        .first()
    )
    if target is None:
        raise Http404
    return render_page(
        request, target.user.name, components.member_profile(target), membership=viewer
    )


@require_GET
@login_required
def member_search(request: HttpRequest, account_id: int) -> JsonResponse:
    """Async mention suggestions: ``[{"id": "42", "label": "Rachel Jones"}]``."""
    require_membership(request, account_id)
    results = search_members(account_id, request.GET.get("q", ""))
    return JsonResponse(results, safe=False)


@require_POST
@login_required
def member_role(request: HttpRequest, account_id: int, member_id: int) -> HttpResponse:
    viewer = require_membership(request, account_id)
    target = (
        AccountUser.objects.select_related("user")
        .filter(pk=member_id, account_id=account_id, is_active=True)
        .first()
    )
    form = RoleForm(request.POST)
    if target is None or not form.is_valid():
        raise Http404
    role = form.cleaned_data["role"]
    if not policies.can_change_role(viewer, target, role):
        return HttpResponse("You can't change that member's role", status=403)
    services.change_role(target, role)
    if wants_fragment(request):
        return html_response(components.member_row(target, viewer, get_token(request)))
    messages.success(request, f"{target.user.name} is now {target.get_role_display()}")
    return redirect(request, reverse("accounts:members", args=[account_id]))


@require_POST
@login_required
def member_remove(
    request: HttpRequest, account_id: int, member_id: int
) -> HttpResponse:
    viewer = require_membership(request, account_id)
    target = (
        AccountUser.objects.select_related("user")
        .filter(pk=member_id, account_id=account_id, is_active=True)
        .first()
    )
    if target is None:
        raise Http404
    if not policies.can_remove_member(viewer, target):
        return HttpResponse("You can't remove that member", status=403)
    services.remove_member(target)
    if target.pk == viewer.pk:
        messages.success(request, f"You left {viewer.account.name}")
        return redirect(request, reverse("accounts:index"))
    messages.success(request, f"{target.user.name} was removed")
    return redirect(request, reverse("accounts:members", args=[account_id]))


INVITE_SENT = "If {email} isn't already a member, an invitation is on its way."


@require_POST
@login_required
def invitation_create(request: HttpRequest, account_id: int) -> HttpResponse:
    viewer = require_membership(request, account_id)
    if not policies.can_invite(viewer):
        return HttpResponse("Only admins can invite people", status=403)
    form = InvitationForm(request.POST)
    if not form.is_valid():
        if wants_fragment(request):
            return html_response(
                components.invitation_form(viewer.account, form, get_token(request)),
                status=UNPROCESSABLE,
            )
        messages.error(request, "There was an error sending the invitation")
        return _members_page(request, viewer, form, status=UNPROCESSABLE)
    email = form.cleaned_data["email"]
    try:
        services.invite(viewer, email, form.cleaned_data["role"])
    except services.InvitationLimitError:
        messages.error(request, "This account has too many pending invitations")
        return redirect(request, reverse("accounts:members", args=[account_id]))
    messages.success(request, INVITE_SENT.format(email=email))
    return redirect(request, reverse("accounts:members", args=[account_id]))


@require_http_methods(["GET", "POST"])
def invitation_accept(request: HttpRequest, token: str) -> HttpResponse:
    invitation = services.pending_invitation(token)
    if invitation is None:
        messages.error(request, "That invitation is invalid or has expired")
        return redirect(request, reverse("identity:sign_in"))
    user = optional_user(request)
    csrf_token = get_token(request)
    if user is not None:
        if user.email != invitation.email.lower():
            messages.error(
                request,
                f"This invitation is for {invitation.email}. Sign out to accept it.",
            )
            return redirect(request, reverse("accounts:index"))
        if request.method == "POST":
            services.accept_invitation(invitation, user)
            messages.success(request, f"Welcome to {invitation.account.name}!")
            return redirect(
                request, reverse("accounts:dashboard", args=[invitation.account_id])
            )
        return render_page(
            request,
            "Accept invitation",
            components.invitation_accept(
                invitation,
                signed_in_email=user.email,
                form_obj=None,
                csrf_token=csrf_token,
            ),
        )

    if User.objects.filter(email__iexact=invitation.email).exists():
        messages.info(request, "Sign in to accept your invitation")
        return redirect(
            request,
            reverse("identity:sign_in") + "?next=" + request.path,
        )

    form = AcceptInvitationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        candidate = User(
            email=invitation.email.lower(),
            first_name=form.cleaned_data["first_name"],
            last_name=form.cleaned_data["last_name"],
        )
        try:
            password_validation.validate_password(
                form.cleaned_data["password"], candidate
            )
        except ValidationError as error:
            form.add_error("password", error)
        else:
            new_user = User.objects.create_user(
                candidate.email,
                form.cleaned_data["password"],
                first_name=candidate.first_name,
                last_name=candidate.last_name,
                verified=True,
            )
            services.accept_invitation(invitation, new_user)
            sign_in(request, new_user)
            messages.success(request, f"Welcome to {invitation.account.name}!")
            return redirect(
                request, reverse("accounts:dashboard", args=[invitation.account_id])
            )
    status = UNPROCESSABLE if request.method == "POST" else 200
    return render_page(
        request,
        "Accept invitation",
        components.invitation_accept(
            invitation, signed_in_email=None, form_obj=form, csrf_token=csrf_token
        ),
        status=status,
    )


@require_http_methods(["GET", "POST"])
@login_required
def profile(request: HttpRequest) -> HttpResponse:
    user = current_user(request)
    if request.method == "POST":
        form = ProfileForm(request.POST)
        if form.is_valid():
            user.first_name = form.cleaned_data["first_name"]
            user.last_name = form.cleaned_data["last_name"]
            user.save(update_fields=["first_name", "last_name", "updated_at"])
            for account_id in user.memberships.values_list("account_id", flat=True):
                membership_changed(account_id)
            messages.success(request, "Your profile was updated")
            return redirect(request, reverse("accounts:profile"))
        status = UNPROCESSABLE
    else:
        form = ProfileForm(
            initial={"first_name": user.first_name, "last_name": user.last_name}
        )
        status = 200
    return render_page(
        request,
        "Your profile",
        components.profile_form(form, get_token(request)),
        status=status,
    )
