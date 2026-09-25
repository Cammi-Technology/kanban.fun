"""Helpers for HTMX-aware views."""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse, HttpResponseRedirect


def is_htmx(request: HttpRequest) -> bool:
    return request.headers.get("HX-Request") == "true"


def is_boosted(request: HttpRequest) -> bool:
    return request.headers.get("HX-Boosted") == "true"


def wants_fragment(request: HttpRequest) -> bool:
    """HTMX requests that are not boosted page navigations want fragments."""
    return is_htmx(request) and not is_boosted(request)


def redirect(request: HttpRequest, url: str) -> HttpResponse:
    """Redirect after a successful form submission.

    Normal browsers get a 303; HTMX gets ``HX-Location`` so it performs a
    client-side navigation without a full reload.
    """
    if wants_fragment(request):
        response = HttpResponse(status=204)
        response["HX-Location"] = url
        return response
    return HttpResponseRedirect(url, status=303)
