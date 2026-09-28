"""
Custom throttle classes for Skytrack API
"""
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle, SimpleRateThrottle
from django.core.cache import cache
from django.conf import settings
import time


class LoadTestBypassMixin:
    """Skip throttle when the request carries a valid load-test token.

    Set LOAD_TEST_SECRET (non-empty) in the environment to activate.
    JMeter requests must include: X-Load-Test-Token: <secret>
    """

    def allow_request(self, request, view):
        if getattr(settings, 'DISABLE_THROTTLE', False):
            return True
        secret = getattr(settings, 'LOAD_TEST_SECRET', '')
        if secret and request.META.get('HTTP_X_LOAD_TEST_TOKEN') == secret:
            return True
        return super().allow_request(request, view)


class AuthRateThrottle(LoadTestBypassMixin, AnonRateThrottle):
    """
    Throttle for authentication endpoints - 5 requests per minute
    After 5 requests in 1 minute, block for 5 minutes
    """
    scope = 'auth'

    def allow_request(self, request, view):
        """
        Custom throttle logic with IP blocking.
        Important: Always invoke super().allow_request first so DRF sets
        internal state like `self.history` used by wait().
        """
        if self.get_rate() is None:
            return True

        # Always call the parent to initialize self.history/self.duration
        allowed = super().allow_request(request, view)

        # Get client IP (after initializing parent state)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        # Enforce IP block window
        blocked_key = f"auth_blocked_{ip}"
        if cache.get(blocked_key):
            return False

        # If throttle limit exceeded, set a temporary IP block
        if not allowed:
            cache.set(blocked_key, True, 300)  # 5 minutes
            return False

        return True


class LoginRateThrottle(LoadTestBypassMixin, AnonRateThrottle):
    """
    Throttle for login endpoints - 5 requests per minute
    """
    scope = 'login'

    def allow_request(self, request, view):
        if self.get_rate() is None:
            return True

        # Always call parent first to set `self.history` for wait()
        allowed = super().allow_request(request, view)

        # Get client IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        # Enforce IP block window
        blocked_key = f"login_blocked_{ip}"
        if cache.get(blocked_key):
            return False

        # If throttle limit exceeded, block IP for 5 minutes
        if not allowed:
            cache.set(blocked_key, True, 300)
            return False

        return True


class OTPRateThrottle(LoadTestBypassMixin, AnonRateThrottle):
    """
    Throttle for OTP endpoints - 5 requests per minute
    """
    scope = 'otp'

    def allow_request(self, request, view):
        if self.get_rate() is None:
            return True

        # Initialize parent state (self.history) for wait()
        allowed = super().allow_request(request, view)

        # Get client IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        # Enforce IP block window
        blocked_key = f"otp_blocked_{ip}"
        if cache.get(blocked_key):
            return False

        # If throttle limit exceeded, block IP for 5 minutes
        if not allowed:
            cache.set(blocked_key, True, 300)
            return False

        return True


class PasswordResetRateThrottle(LoadTestBypassMixin, AnonRateThrottle):
    """
    Throttle for password reset endpoints - 3 requests per minute (stricter)
    """
    scope = 'password_reset'

    def allow_request(self, request, view):
        if self.get_rate() is None:
            return True

        # Initialize parent state (self.history) for wait()
        allowed = super().allow_request(request, view)

        # Get client IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        # Enforce IP block window
        blocked_key = f"password_reset_blocked_{ip}"
        if cache.get(blocked_key):
            return False

        # If throttle limit exceeded, block IP for 5 minutes
        if not allowed:
            cache.set(blocked_key, True, 300)
            return False

        return True


class AlertStatsRateThrottle(LoadTestBypassMixin, UserRateThrottle):
    """Throttle for the alert-statistics dashboard/summary endpoints."""
    scope = 'alert_stats'


class DeviceCommandRateThrottle(LoadTestBypassMixin, UserRateThrottle):
    """Conservative throttle for sending raw commands down to a live device."""
    scope = 'device_command'


class ServerHealthRateThrottle(LoadTestBypassMixin, UserRateThrottle):
    """Throttle for the internal server-health dashboard (superadmin only)."""
    scope = 'server_health'


class DeviceDataHealthRateThrottle(LoadTestBypassMixin, UserRateThrottle):
    """Throttle for the device-data-health lookup (bounded raw-log scans per request)."""
    scope = 'device_data_health'


class VehicleOBDStatusRateThrottle(LoadTestBypassMixin, UserRateThrottle):
    """Throttle for the vehicle OBD/GPS status lookup (bounded raw-log scans per request)."""
    scope = 'vehicle_obd_status'


class IPViolationDummyRateThrottle(LoadTestBypassMixin, AnonRateThrottle):
    """Throttle for the public dummy IP-violation list endpoint."""
    scope = 'ip_violation_dummy'


class _TripThrottleMixin(LoadTestBypassMixin):
    """
    Per-caller throttle for the trip APIs (VAPT: no rate limiting on trip
    creation). Keyed on the logged-in user, else the temp-user `sessionid`
    header, else the client IP - these views are AllowAny.
    """

    def get_cache_key(self, request, view):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            ident = f"user_{user.pk}"
        elif request.headers.get('sessionid'):
            ident = f"temp_{request.headers.get('sessionid')[:64]}"
        else:
            ident = f"ip_{self.get_ident(request)}"
        return self.cache_format % {'scope': self.scope, 'ident': ident}


class TripCreateRateThrottle(_TripThrottleMixin, SimpleRateThrottle):
    scope = 'trip_create'


class TripCreateDailyThrottle(_TripThrottleMixin, SimpleRateThrottle):
    scope = 'trip_create_daily'


class TripWriteRateThrottle(_TripThrottleMixin, SimpleRateThrottle):
    """update / end / cancel"""
    scope = 'trip_write'
