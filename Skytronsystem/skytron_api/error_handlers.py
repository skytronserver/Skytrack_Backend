"""
Controlled error responses (VAPT: improper error handling).

Unhandled exceptions must never reach the client as HTML, stack traces,
paths or framework details. Details go to the server log; the client gets a
short JSON message.
"""
import logging

from django.db import DataError, IntegrityError
from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler, set_rollback

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    """DRF EXCEPTION_HANDLER: DRF's own errors as usual, everything else as JSON."""
    response = exception_handler(exc, context)
    if response is not None:
        return response

    view = context.get('view')
    request = context.get('request')
    where = f"{view.__class__.__name__} {getattr(request, 'method', '')} {getattr(request, 'path', '')}"
    set_rollback()

    # Bad input that only the database caught (value too long, bad
    # encoding, duplicate) - the client's fault, not a server error.
    if isinstance(exc, (DataError, IntegrityError, ValueError)):
        logger.warning(f"Invalid input rejected by database in {where}: {exc!r}")
        return Response({'error': 'Invalid input. Please check the values and try again.'},
                        status=status.HTTP_400_BAD_REQUEST)

    logger.exception(f"Unhandled error in {where}", exc_info=exc)
    return Response({'error': 'Something went wrong. Please try again later.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Django-level handlers (non-DRF views and errors raised outside views).
# Only used when DEBUG=False.

def handler400(request, exception=None):
    return JsonResponse({'error': 'Bad request.'}, status=400)


def handler403(request, exception=None):
    return JsonResponse({'error': 'Access denied.'}, status=403)


def handler404(request, exception=None):
    return JsonResponse({'error': 'Not found.'}, status=404)


def handler500(request):
    return JsonResponse({'error': 'Something went wrong. Please try again later.'}, status=500)
