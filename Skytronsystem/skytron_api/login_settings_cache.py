"""
Redis cache utilities for LoginSettings.
This module handles caching and retrieval of login settings from Redis.
"""

from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta, time
import json
import logging

logger = logging.getLogger(__name__)

# Cache key prefix
LOGIN_SETTINGS_PREFIX = "login_settings:"
USER_LOGIN_COUNT_PREFIX = "user_login_count:"
USER_SESSION_PREFIX = "user_session:"
CACHE_TIMEOUT = None  # No expiry - permanent cache


def get_login_settings_cache_key(user_role):
    """Generate Redis cache key for login settings."""
    return f"{LOGIN_SETTINGS_PREFIX}{user_role}"


def get_user_login_count_key(user_id, date=None):
    """Generate Redis cache key for daily login count."""
    if date is None:
        date = timezone.now().date()
    return f"{USER_LOGIN_COUNT_PREFIX}{user_id}:{date.isoformat()}"


def get_user_session_key(user_id, session_token):
    """Generate Redis cache key for active session."""
    return f"{USER_SESSION_PREFIX}{user_id}:{session_token}"


def get_user_sessions_pattern(user_id):
    """Get pattern for all sessions of a user."""
    return f"{USER_SESSION_PREFIX}{user_id}:*"


def cache_login_settings(login_settings):
    """
    Cache a LoginSettings object in Redis.
    
    Args:
        login_settings: LoginSettings model instance
    
    Returns:
        bool: True if cached successfully, False otherwise
    """
    try:
        cache_key = get_login_settings_cache_key(login_settings.user_role)
        
        # Convert model to dictionary
        settings_data = {
            'user_role': login_settings.user_role,
            'daily_login_limit': login_settings.daily_login_limit,
            'session_expiry_minutes': login_settings.session_expiry_minutes,
            'max_simultaneous_sessions': login_settings.max_simultaneous_sessions,
            'login_start_time': login_settings.login_start_time.strftime('%H:%M:%S'),
            'login_end_time': login_settings.login_end_time.strftime('%H:%M:%S'),
            'enforce_time_boundary': login_settings.enforce_time_boundary,
            'is_active': login_settings.is_active,
        }
        
        # Store in Redis permanently (no timeout)
        cache.set(cache_key, json.dumps(settings_data), timeout=None)
        logger.info(f"Cached login settings for role: {login_settings.user_role}")
        return True
        
    except Exception as e:
        logger.error(f"Error caching login settings: {str(e)}")
        return False


def get_login_settings_from_cache(user_role):
    """
    Retrieve login settings from Redis cache.
    
    Args:
        user_role: The user role to get settings for
    
    Returns:
        dict: Settings dictionary or None if not found
    """
    try:
        cache_key = get_login_settings_cache_key(user_role)
        cached_data = cache.get(cache_key)
        
        if cached_data:
            settings = json.loads(cached_data)
            logger.debug(f"Retrieved login settings from cache for role: {user_role}")
            return settings
        
        # Try default settings if specific role not found
        if user_role != 'default':
            logger.debug(f"No cached settings for {user_role}, trying default")
            return get_login_settings_from_cache('default')
        
        logger.warning(f"No login settings found in cache for role: {user_role}")
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving login settings from cache: {str(e)}")
        return None


def invalidate_login_settings_cache(user_role):
    """
    Remove login settings from cache.
    
    Args:
        user_role: The user role to invalidate
    
    Returns:
        bool: True if invalidated successfully
    """
    try:
        cache_key = get_login_settings_cache_key(user_role)
        cache.delete(cache_key)
        logger.info(f"Invalidated cache for role: {user_role}")
        return True
    except Exception as e:
        logger.error(f"Error invalidating cache: {str(e)}")
        return False


def load_all_login_settings_to_cache():
    """
    Load all LoginSettings from database to Redis cache.
    Should be called on application startup.
    
    Returns:
        int: Number of settings loaded
    """
    try:
        from .models import LoginSettings
        
        settings_list = LoginSettings.objects.filter(is_active=True)
        count = 0
        
        for settings in settings_list:
            if cache_login_settings(settings):
                count += 1
        
        logger.info(f"Loaded {count} login settings to cache on startup")
        return count
        
    except Exception as e:
        logger.error(f"Error loading login settings to cache: {str(e)}")
        return 0


# ==================== Session Tracking Functions ====================

def increment_daily_login_count(user_id):
    """
    Increment the daily login count for a user.
    
    Args:
        user_id: The user ID
    
    Returns:
        int: Current login count for today
    """
    try:
        cache_key = get_user_login_count_key(user_id)
        count = cache.get(cache_key, 0)
        count += 1
        
        # Set expiry to end of day
        now = timezone.now()
        end_of_day = now.replace(hour=23, minute=59, second=59)
        seconds_until_eod = (end_of_day - now).total_seconds()
        
        cache.set(cache_key, count, timeout=int(seconds_until_eod))
        logger.debug(f"Login count for user {user_id}: {count}")
        return count
        
    except Exception as e:
        logger.error(f"Error incrementing login count: {str(e)}")
        return 0


def get_daily_login_count(user_id):
    """
    Get the current daily login count for a user.
    
    Args:
        user_id: The user ID
    
    Returns:
        int: Current login count for today
    """
    try:
        cache_key = get_user_login_count_key(user_id)
        count = cache.get(cache_key, 0)
        return count
    except Exception as e:
        logger.error(f"Error getting login count: {str(e)}")
        return 0


def add_active_session(user_id, session_token, expiry_minutes):
    """
    Add an active session to Redis.
    
    Args:
        user_id: The user ID
        session_token: The session token
        expiry_minutes: Session expiry time in minutes
    
    Returns:
        bool: True if session added successfully
    """
    try:
        cache_key = get_user_session_key(user_id, session_token)
        session_data = {
            'user_id': user_id,
            'token': session_token,
            'created_at': timezone.now().isoformat(),
        }
        
        timeout = expiry_minutes * 60  # Convert to seconds
        cache.set(cache_key, json.dumps(session_data), timeout=timeout)
        logger.debug(f"Added active session for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error adding active session: {str(e)}")
        return False


def remove_active_session(user_id, session_token):
    """
    Remove an active session from Redis.
    
    Args:
        user_id: The user ID
        session_token: The session token
    
    Returns:
        bool: True if session removed successfully
    """
    try:
        cache_key = get_user_session_key(user_id, session_token)
        cache.delete(cache_key)
        logger.debug(f"Removed active session for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error removing active session: {str(e)}")
        return False


def get_active_session_count(user_id):
    """
    Get the number of active sessions for a user.
    
    Args:
        user_id: The user ID
    
    Returns:
        int: Number of active sessions
    """
    try:
        # Use the cache API's keys() rather than a raw Redis KEYS call: keys
        # written through django.core.cache are stored with Django's key
        # prefix/version (":1:user_session:..."), so a raw pattern of
        # "user_session:..." never matched and the count was always 0.
        keys = cache.keys(get_user_sessions_pattern(user_id))

        count = len(keys) if keys else 0
        logger.debug(f"Active session count for user {user_id}: {count}")
        return count

    except Exception as e:
        logger.error(f"Error getting active session count: {str(e)}")
        # Signal "unknown" with -1 rather than 0. Returning 0 here would make
        # the concurrent-session limit fail OPEN (silently allow unlimited
        # logins) whenever Redis is unreachable. Callers that enforce a
        # max_simultaneous_sessions limit must treat -1 as "deny" (fail closed).
        return -1


def enforce_session_limit(user_id, user_role, keep_token):
    """
    Enforce max_simultaneous_sessions for a user right after a login completes.

    Keeps the newest `max_simultaneous_sessions` logged-in sessions (always
    including `keep_token`, the one just issued) and terminates the rest:
    Session.status -> 'logout' (JWTAuthentication only accepts 'login'),
    token blacklisted, and removed from Redis session tracking.
    max_simultaneous_sessions = 0 means unlimited.

    Returns:
        int: number of older sessions terminated
    """
    from .models import Session, TokenBlacklist
    from .secure_token import decode_jwt_token

    try:
        settings = get_login_settings_from_cache(user_role) or {}
        max_sessions = int(settings.get('max_simultaneous_sessions', 1))
        if max_sessions <= 0:
            return 0

        others = (Session.objects
                  .filter(user_id=user_id, status='login')
                  .exclude(token=keep_token)
                  .order_by('-loginTime', '-id'))
        to_end = list(others[max_sessions - 1:])

        for session in to_end:
            token = session.token
            if token:
                try:
                    payload = decode_jwt_token(token)
                    if payload:
                        TokenBlacklist.blacklist_token(
                            token=token,
                            user_id=user_id,
                            jti=payload.get('jti', f"session_limit_{user_id}_{session.id}"),
                            expires_at=timezone.make_aware(datetime.fromtimestamp(payload.get('exp', 0))),
                            reason="session_limit"
                        )
                except Exception as e:
                    logger.error(f"Error blacklisting token for user {user_id}: {e}")
                remove_active_session(user_id, token)
            session.status = 'logout'
            session.save(update_fields=['status'])

        if to_end:
            logger.info(f"Session limit ({max_sessions}) for user {user_id}: ended {len(to_end)} older session(s)")
        return len(to_end)

    except Exception as e:
        logger.error(f"Error enforcing session limit for user {user_id}: {e}")
        return 0


# ==================== Validation Functions ====================

def validate_login_allowed(user_id, user_role):
    """
    Validate if a user is allowed to login based on cached settings.
    
    Args:
        user_id: The user ID
        user_role: The user's role
    
    Returns:
        tuple: (is_allowed: bool, error_message: str or None)
    """
    try:
        # Get settings from cache
        settings = get_login_settings_from_cache(user_role)
        
        if not settings:
            logger.info(f"No login settings found for role: {user_role}, allowing login with defaults")
            return True, None
        
        # Check if settings are active
        if not settings.get('is_active', True):
            return False, "Login settings are not active for your user role"
        
        # 1. Check time boundary
        if settings.get('enforce_time_boundary', False):
            current_time = timezone.now().time()
            start_time = datetime.strptime(settings['login_start_time'], '%H:%M:%S').time()
            end_time = datetime.strptime(settings['login_end_time'], '%H:%M:%S').time()
            
            # Handle time ranges that cross midnight
            if start_time <= end_time:
                # Normal range (e.g., 08:00 to 18:00)
                if not (start_time <= current_time <= end_time):
                    return False, f"Login allowed only between {settings['login_start_time']} and {settings['login_end_time']}"
            else:
                # Range crosses midnight (e.g., 22:00 to 06:00)
                if not (current_time >= start_time or current_time <= end_time):
                    return False, f"Login allowed only between {settings['login_start_time']} and {settings['login_end_time']}"
        
        # 2. Check daily login limit
        daily_limit = settings.get('daily_login_limit', 0)
        if daily_limit > 0:
            current_count = get_daily_login_count(user_id)
            if current_count >= daily_limit:
                return False, f"Daily login limit ({daily_limit}) reached. Please try again tomorrow"
        
        # 3. Simultaneous sessions limit is NOT checked here. It is enforced
        # when a login completes (enforce_session_limit), by ending the
        # user's oldest sessions. Refusing the new login instead would let
        # a stale/abandoned session (or an attacker who logged in first)
        # lock the legitimate user out until that token expires.

        # All checks passed
        return True, None
        
    except Exception as e:
        logger.error(f"Error validating login: {str(e)}")
        # On error, allow login to avoid blocking users
        return True, None


def get_session_expiry_minutes(user_role):
    """
    Get session expiry time for a user role from cache.
    If no settings defined, defaults to 1440 minutes (24 hours).
    
    Args:
        user_role: The user's role
    
    Returns:
        int: Session expiry in minutes (default 1440 = 24 hours)
    """
    try:
        settings = get_login_settings_from_cache(user_role)
        if settings:
            return settings.get('session_expiry_minutes', 1440)
        return 1440  # Default 24 hours if no settings found
    except Exception as e:
        logger.error(f"Error getting session expiry: {str(e)}")
        return 1440  # Default 24 hours on error
