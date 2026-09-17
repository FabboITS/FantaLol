"""CORS minimale, equivalente alla `CorsConfigurationSource` di SecurityConfig."""
from __future__ import annotations

import os

ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("CORS_ALLOWED_ORIGINS", "*").split(",") if o.strip()]


class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS" and "HTTP_ACCESS_CONTROL_REQUEST_METHOD" in request.META:
            from django.http import HttpResponse

            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)
        origin = request.META.get("HTTP_ORIGIN")
        if origin and ("*" in ALLOWED_ORIGINS or origin in ALLOWED_ORIGINS):
            response["Access-Control-Allow-Origin"] = origin
            response["Vary"] = "Origin"
        elif "*" in ALLOWED_ORIGINS:
            response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response["Access-Control-Max-Age"] = "3600"
        return response
