from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .utils import iso, now


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Health check pubblico (sostituisce ``/actuator/health``)."""
    database = "UP"
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:  # pragma: no cover - dipende dall'infrastruttura
        database = "DOWN"
    status = "UP" if database == "UP" else "DOWN"
    return Response(
        {"status": status, "components": {"db": {"status": database}}, "time": iso(now())},
        status=200 if status == "UP" else 503,
    )
