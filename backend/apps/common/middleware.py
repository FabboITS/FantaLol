"""CORS permissivo sulle API (equivalente alla configurazione Spring ``allowedOriginPatterns=*``)."""

from django.http import HttpResponse


class ApiCorsMiddleware:
    allowed_methods = "GET, POST, PUT, DELETE, OPTIONS"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_api = request.path.startswith("/api/")
        if is_api and request.method == "OPTIONS" and "HTTP_ACCESS_CONTROL_REQUEST_METHOD" in request.META:
            response = HttpResponse(status=200)
        else:
            response = self.get_response(request)
        origin = request.META.get("HTTP_ORIGIN")
        if is_api and origin:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Allow-Methods"] = self.allowed_methods
            response["Access-Control-Allow-Headers"] = request.META.get(
                "HTTP_ACCESS_CONTROL_REQUEST_HEADERS", "Authorization, Content-Type"
            )
            response["Vary"] = "Origin"
        return response
