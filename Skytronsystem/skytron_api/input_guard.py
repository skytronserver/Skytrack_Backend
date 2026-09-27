"""
Global server-side input guard (VAPT: improper input validation).

Every request's query parameters, JSON body and form fields are scanned
(recursively) before any view runs. A value containing markup/script or a
well-known injection payload is rejected with HTTP 400, so it can never be
stored and later rendered (the frontend shows some stored values through
innerHTML, e.g. map overlays), nor reach any other sink.

This is a baseline for all ~600 endpoints; endpoint serializers still apply
their own field-specific validation on top (e.g. PublicBusStopSerializer).

Settings (environment):
  INPUT_GUARD_MODE          block (default) | log | off
  INPUT_GUARD_EXEMPT_PATHS  comma-separated path prefixes to skip
"""
import json
import logging
import os
import re

from django.http import JsonResponse

logger = logging.getLogger(__name__)

# High-signal patterns only - chosen so that normal names, addresses,
# registration numbers, device commands etc. are never matched.
_PATTERNS = [
    ('html_tag',          r'<\s*/?\s*[a-z!?]'),                  # <script, <img, </b>, <!--, <?xml
    ('script_uri',        r'(?:java|vb)script\s*:|data\s*:\s*text/html'),
    ('event_handler',     r'\bon(?:error|load|click|dblclick|mouse\w+|key\w+|focus\w*|blur|change|submit|input|'
                          r'toggle|animation\w+|transition\w+|pointer\w+|touch\w+|drag\w*|drop|wheel|scroll|'
                          r'resize|begin|end|beforeprint|afterprint)\s*='),
    ('template_injection', r'\{\{|\{%|\$\{|#\{'),
    ('sql_injection',     r"'\s*(?:or|and)\s+'?\w+'?\s*=\s*'?\w+|\bunion\s+(?:all\s+)?select\b|"
                          r";\s*(?:drop|truncate|delete|insert|update|alter)\s+\w|\bsleep\s*\(\s*\d|"
                          r"\bwaitfor\s+delay\b|\bpg_sleep\s*\("),
    ('path_traversal',    r'(?:\.\.[/\\])|%2e%2e[/\\%]'),
    ('null_byte',         r'\x00|%00'),
]
_REGEX = [(name, re.compile(p, re.IGNORECASE)) for name, p in _PATTERNS]

# Secret / opaque values: may legitimately contain any character (passwords)
# or are verified by other means (tokens, OTP, captcha). Never scanned.
_EXEMPT_KEY_RE = re.compile(r'pass(?:word|wd)?|pwd|secret|token|otp|captcha|signature|jwt', re.IGNORECASE)

_MAX_BODY_SCAN = 5 * 1024 * 1024   # don't parse bodies above 5 MB (uploads are form/multipart anyway)


def _find_violation(value, key=''):
    """Return (field, rule) for the first offending value, else None."""
    if isinstance(value, dict):
        for k, v in value.items():
            k = str(k)
            if _EXEMPT_KEY_RE.search(k):
                continue
            hit = _check_str(k, k) or _find_violation(v, k)
            if hit:
                return hit
        return None
    if isinstance(value, (list, tuple)):
        for v in value:
            hit = _find_violation(v, key)
            if hit:
                return hit
        return None
    if isinstance(value, str):
        return _check_str(value, key)
    return None


def _check_str(value, key):
    for name, rx in _REGEX:
        if rx.search(value):
            return key or '(unnamed)', name
    return None


class InputGuardMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.mode = os.environ.get('INPUT_GUARD_MODE', 'block').strip().lower()
        self.exempt = tuple(
            p.strip() for p in os.environ.get('INPUT_GUARD_EXEMPT_PATHS', '').split(',') if p.strip()
        )

    def __call__(self, request):
        if self.mode != 'off' and not request.path.startswith(self.exempt or ('\0',)):
            hit = self._scan(request)
            if hit:
                field, rule = hit
                logger.warning(
                    "InputGuard %s: %s %s field=%s rule=%s ip=%s",
                    'BLOCKED' if self.mode == 'block' else 'DETECTED',
                    request.method, request.path, field, rule,
                    request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR'),
                )
                if self.mode == 'block':
                    # Do not echo the submitted value back.
                    return JsonResponse(
                        {'error': f"Invalid input in '{field}': contains characters or patterns that are not allowed."},
                        status=400,
                    )
        return self.get_response(request)

    def _scan(self, request):
        hit = _find_violation({k: request.GET.getlist(k) for k in request.GET.keys()})
        if hit:
            return hit
        if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
            return None

        content_type = (request.META.get('CONTENT_TYPE') or '').lower()
        try:
            length = int(request.META.get('CONTENT_LENGTH') or 0)
        except ValueError:
            length = 0

        if 'application/json' in content_type:
            if not length or length > _MAX_BODY_SCAN:
                return None
            try:
                data = json.loads(request.body.decode('utf-8') or 'null')
            except (ValueError, UnicodeDecodeError):
                return None   # malformed JSON is rejected by the parser later
            return _find_violation(data)

        if 'multipart/form-data' in content_type or 'application/x-www-form-urlencoded' in content_type:
            # request.POST holds only the text fields; uploaded files are not scanned.
            return _find_violation({k: request.POST.getlist(k) for k in request.POST.keys()})

        return None
