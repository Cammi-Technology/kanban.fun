"""Small cross-cutting middleware."""

from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponseBase
from django.utils.cache import patch_vary_headers


class HtmxMiddleware:
    """Mark responses as varying on ``HX-Request``.

    The same URL returns a full page for a normal request and a fragment for
    an HTMX request, so shared caches must key on the header.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponseBase]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        response = self.get_response(request)
        patch_vary_headers(response, ("HX-Request",))
        return response
