"""
Global API rate limit (VAPT: insufficient rate limiting).

Applies to every /api/ request - DRF views, plain Django views, and views that
set their own @throttle_classes - before any view code runs. Counts per
client: the bearer token when one is sent (so users behind one office NAT do
not share a budget), otherwise the client IP. Fixed one-minute windows in the
shared Redis cache, so all gunicorn workers share the count.

Settings (env):
    API_RATE_LIMIT        requests per minute per client (default 300; 0 = off)
    DISABLE_THROTTLE      true turns this off (load tests only)
    LOAD_TEST_SECRET      requests with a matching X-Load-Test-Token are exempt
"""
import hashlib
import ipaddress
import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 60

# Internal callers (MQTT broker auth hooks) - they are not user traffic.
EXEMPT_PATH_PREFIXES = (
    '/api/mqtt/validate-connection/',
    '/api/mqtt/validate-acl/',
)


def _client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR') or ''


def _is_internal(request):
    """A direct call from a private address (no proxy in between) - service-to-service."""
    if request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('HTTP_X_REAL_IP'):
        return False
    try:
        ip = ipaddress.ip_address(request.META.get('REMOTE_ADDR', ''))
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback


def _client_key(request):
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if auth:
        return 'tok:' + hashlib.sha256(auth.encode()).hexdigest()[:32]
    return 'ip:' + _client_ip(request)


class ApiRateLimitMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response
        self.limit = int(getattr(settings, 'API_RATE_LIMIT', 300) or 0)

    def __call__(self, request):
        blocked = self._check(request)
        if blocked is not None:
            return blocked
        return self.get_response(request)

    def _check(self, request):
        if self.limit <= 0 or not request.path.startswith('/api/'):
            return None
        if request.method == 'OPTIONS' or request.path.startswith(EXEMPT_PATH_PREFIXES):
            return None
        if getattr(settings, 'DISABLE_THROTTLE', False):
            return None
        secret = getattr(settings, 'LOAD_TEST_SECRET', '')
        if secret and request.META.get('HTTP_X_LOAD_TEST_TOKEN') == secret:
            return None
        if _is_internal(request):
            return None

        now = int(time.time())
        window = now // WINDOW_SECONDS
        key = f"api_rl:{_client_key(request)}:{window}"
        try:
            # add() is a no-op if the key exists; incr() is atomic in Redis.
            cache.add(key, 0, WINDOW_SECONDS + 5)
            count = cache.incr(key)
        except Exception as e:
            # Fail open: a cache outage must not take the whole API down.
            logger.error(f"API rate limit cache error: {e}")
            return None

        if count > self.limit:
            retry_after = WINDOW_SECONDS - (now % WINDOW_SECONDS)
            if count == self.limit + 1:
                logger.warning(f"API rate limit exceeded: {_client_key(request)[:12]}... ip={_client_ip(request)} path={request.path}")
            response = JsonResponse(
                {'error': 'Too many requests. Please try again later.'},
                status=429,
            )
            response['Retry-After'] = str(retry_after)
            return response
        return None
