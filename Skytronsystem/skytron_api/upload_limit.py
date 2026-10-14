"""
Blanket per-file upload size limit.

Rejects any multipart request carrying a file larger than MAX_UPLOAD_FILE_SIZE
before view code runs, so every upload endpoint gets the same limit and a
clear error instead of each view checking (or silently failing) on its own.

Settings (env):
    MAX_UPLOAD_FILE_SIZE  bytes per file (default 2 MB)
"""
from django.conf import settings
from django.http import JsonResponse


def _limit_label(limit):
    mb = limit / (1024 * 1024)
    return f"{mb:g} MB"


class UploadSizeLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        content_type = request.META.get('CONTENT_TYPE', '')
        if request.method in ('POST', 'PUT', 'PATCH') and content_type.startswith('multipart/form-data'):
            limit = settings.MAX_UPLOAD_FILE_SIZE
            # Parsing here is safe for DRF views: when the stream has already
            # been read, DRF uses request.POST / request.FILES as parsed here.
            for field, files in request.FILES.lists():
                for uploaded in files:
                    if uploaded.size > limit:
                        return JsonResponse(
                            {
                                'error': f"File '{uploaded.name}' is larger than {_limit_label(limit)}.",
                                'errors': {field: f'File size must not exceed {_limit_label(limit)}.'},
                            },
                            status=400,
                        )
        return self.get_response(request)
