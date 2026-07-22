from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpResponse


class LocalDevelopmentCorsMiddleware:
    """Allow Flutter web dev servers to call the local Django API."""

    ALLOWED_HOSTS = {"localhost", "127.0.0.1"}
    ALLOWED_HEADERS = "Authorization, Content-Type, Accept, X-CSRFToken"
    ALLOWED_METHODS = "GET, POST, PUT, PATCH, DELETE, OPTIONS"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin", "")
        allow_origin = self._is_allowed(origin)

        if request.method == "OPTIONS" and allow_origin:
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        if allow_origin:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Headers"] = self.ALLOWED_HEADERS
            response["Access-Control-Allow-Methods"] = self.ALLOWED_METHODS
            response["Access-Control-Max-Age"] = "86400"
            response["Vary"] = "Origin"
        return response

    @classmethod
    def _is_allowed(cls, origin):
        if not settings.DEBUG or not origin:
            return False
        parsed = urlparse(origin)
        return parsed.scheme in {"http", "https"} and parsed.hostname in cls.ALLOWED_HOSTS
