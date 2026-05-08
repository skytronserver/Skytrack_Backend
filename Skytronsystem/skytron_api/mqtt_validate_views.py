"""
MQTT Connection Validation Endpoint for mosquitto-go-auth
Handles direct MQTT authentication with JWT-only mode support.

Security features:
- Mode 1 (JWT): Validates RS256 JWT signature + active DB user lookup
- Mode 2 (username+password): Verifies DRF token or derived-key; rejects unknown users
- ACL: Topic ownership enforcement — each identity can only access topics containing
  their own username/mobile/IMEI as a path segment
- Throttling: Redis-backed — 3 failed auth attempts per clientid within 30 min
  triggers a 30-min block for that clientid
- Format pre-check: Garbage credentials (wrong format) are rejected before any DB query
"""
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .secure_token import verify_jwt_token, decode_jwt_token
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.conf import settings
import hashlib
import re
import time
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

# --- Throttle constants ---
MQTT_FAIL_MAX = 3           # max failures before block
MQTT_FAIL_WINDOW = 1800     # 30 min window (seconds)
MQTT_BLOCK_DURATION = 1800  # 30 min block (seconds)

# One active session per IMEI lease settings.
MQTT_IMEI_SESSION_ENFORCE = True
MQTT_IMEI_SESSION_TTL = 300  # seconds; refreshed on ACL checks

# MQTT superuser that bypasses ACL (set in settings/env)
MQTT_SUPERUSER = getattr(settings, 'MQTT_ADMIN_USER', '')
MQTT_ADMIN_PASS = getattr(settings, 'MQTT_ADMIN_PASS', '')

# Pre-compiled format validators (zero DB/network cost)
_RE_JWT_PART = re.compile(r'^[A-Za-z0-9_-]+$')
_RE_MOBILE   = re.compile(r'^\d{10}$')
_RE_IMEI     = re.compile(r'^\d{15,16}$')
_RE_DRF_TOK  = re.compile(r'^[0-9a-f]{40}$')
_RE_DERIVED  = re.compile(r'^[0-9a-f]{32}$')

# Default MQTT password for devices whose DeviceModel.mqtt_pw is null/empty
DEFAULT_DEVICE_MQTT_PW = "isjihiuhguish57hgh58ghh4ghg7h75ihgshgs8hs854h98h9hgruhgrh89w959hguh985h"

# If True, skip password check for IMEI-based device connections (dev/test mode)
ALLOW_ALL_DEV_MQTT = getattr(settings, 'ALLOW_ALL_DEV_MQTT', False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _throttle_key(clientid):
    """Cache key for the fail counter for a given clientid."""
    safe = clientid.replace(' ', '_')[:64]
    return f"mqtt:fail:{safe}"


def _jwt_session_key(clientid):
    """Cache key for JWT token stored during Mode 1 CONNECT, used in ACL checks."""
    safe = clientid.replace(' ', '_')[:64]
    return f"mqtt:jwt:{safe}"


def _cache_jwt_for_client(clientid, raw_jwt, payload):
    """Store the raw JWT + user mobile in Redis keyed by clientid, expiring when the JWT expires."""
    try:
        exp = payload.get('exp')
        if exp:
            ttl = max(int(exp) - int(time.time()), 60)  # at least 60s
        else:
            ttl = 86400  # 24h default if no exp claim
        data = {
            'jwt': raw_jwt,
            'mobile': str(payload.get('user_mobile', '')),
        }
        cache.set(_jwt_session_key(clientid), data, timeout=ttl)
        logger.debug(f"MQTT JWT session cached for clientid='{clientid}', ttl={ttl}s")
    except Exception as e:
        logger.error(f"MQTT JWT session cache write error for clientid='{clientid}': {e}")


def _block_key(clientid):
    """Cache key for the block flag for a given clientid."""
    safe = clientid.replace(' ', '_')[:64]
    return f"mqtt:block:{safe}"


def _imei_session_key(imei):
    safe = str(imei).replace(' ', '_')[:32]
    return f"mqtt:imei:session:{safe}"


def _imei_session_kind(clientid):
    """Classify IMEI session type from clientid.

    Current deployed patterns typically use `_emergency` suffix for emergency channel.
    Everything else is treated as tracking.
    """
    cid = str(clientid or '').lower()
    if 'emergency' in cid or '_em_' in cid or cid.endswith('_em'):
        return 'emergency'
    return 'tracking'


def _clientid_matches_imei(clientid, imei):
    """
    Backward-compatible matching for deployed device clientids.
    Accepts exact IMEI and common prefixed/suffixed forms containing IMEI
    as a token separated by underscores.
    """
    cid = str(clientid or '').strip()
    i = str(imei or '').strip()
    if not cid or not i:
        return False
    if cid == i:
        return True
    parts = [p for p in cid.split('_') if p]
    return i in parts


def _acquire_or_refresh_imei_session(imei, clientid):
    """
    Enforce up to two active sessions per IMEI, one per session kind:
    - tracking: 1 active clientid
    - emergency: 1 active clientid

    A different clientid for the same kind is rejected while lease is active.
    """
    key = _imei_session_key(imei)
    cid = str(clientid or '').strip()
    kind = _imei_session_kind(cid)
    slot_key = f"{kind}_clientid"
    try:
        current = cache.get(key)

        # Backward compatibility with older single-slot cache format.
        if isinstance(current, dict):
            active_cid = str(current.get(slot_key, '')).strip()
            if not active_cid and 'clientid' in current:
                # Legacy key existed: map it to tracking slot.
                legacy = str(current.get('clientid', '')).strip()
                if legacy and kind == 'tracking':
                    active_cid = legacy
                current = {
                    'tracking_clientid': legacy,
                    'emergency_clientid': str(current.get('emergency_clientid', '')).strip(),
                }
        else:
            # Legacy non-dict value: treat as tracking slot.
            legacy = str(current or '').strip()
            active_cid = legacy if kind == 'tracking' else ''
            current = {
                'tracking_clientid': legacy,
                'emergency_clientid': '',
            }

        if active_cid and active_cid != cid:
            return False, active_cid

        current[slot_key] = cid
        cache.set(key, current, timeout=MQTT_IMEI_SESSION_TTL)
        return True, active_cid or cid
    except Exception as e:
        logger.error(f"MQTT IMEI session lease error imei='{imei}' clientid='{cid}': {e}")
        # Fail-open to avoid auth outage on cache issues.
        return True, cid


def _record_failure(clientid):
    """Increment fail counter. If >= MQTT_FAIL_MAX, set block."""
    fkey = _throttle_key(clientid)
    bkey = _block_key(clientid)
    try:
        count = cache.get(fkey, 0) + 1
        cache.set(fkey, count, timeout=MQTT_FAIL_WINDOW)
        if count >= MQTT_FAIL_MAX:
            cache.set(bkey, True, timeout=MQTT_BLOCK_DURATION)
            logger.warning(
                f"MQTT Throttle: clientid '{clientid}' blocked after {count} failures"
            )
    except Exception as e:
        logger.error(f"MQTT Throttle: cache write error - {e}")


def _clear_failure(clientid):
    """Reset fail counter on successful auth."""
    try:
        cache.delete(_throttle_key(clientid))
    except Exception:
        pass


def _is_blocked(clientid):
    """Return True if this clientid is currently in the block window."""
    try:
        return bool(cache.get(_block_key(clientid)))
    except Exception:
        return False


def _looks_like_jwt(value):
    """
    Zero-cost format check: is this value shaped like a JWT?
    A JWT has exactly 3 base64url parts separated by '.'.
    Checks format only — no cryptographic work.
    Rejects garbage passwords before any DB query.
    """
    parts = value.split('.')
    if len(parts) != 3:
        return False
    return all(_RE_JWT_PART.match(p) for p in parts)


def _looks_like_valid_username(value):
    """
    Is this a plausible MQTT username?
    Accepts 10-digit mobile numbers and 15-16 digit IMEIs.
    Anything else (script kiddies sending 'admin', 'root', random strings) 
    is rejected without a DB query.
    """
    return bool(_RE_MOBILE.match(value) or _RE_IMEI.match(value))


def _verify_device_password(imei, password):
    """
    Verify MQTT password for a device connecting by IMEI.
    Looks up DeviceStock -> DeviceModel -> mqtt_pw.
    Falls back to DEFAULT_DEVICE_MQTT_PW if mqtt_pw is null/blank/empty.
    Returns (True, device_stock) on success, (False, None) on failure.
    """
    try:
        from .models import DeviceStock
        device_stock = DeviceStock.objects.select_related('model').get(imei=imei)
        expected_pw = device_stock.model.mqtt_pw
        if not expected_pw:
            expected_pw = DEFAULT_DEVICE_MQTT_PW
        if password == expected_pw:
            return True, device_stock
        return False, None
    except DeviceStock.DoesNotExist:
        logger.warning(f"MQTT Device Auth: IMEI '{imei}' not found in DeviceStock")
        return False, None
    except Exception as e:
        logger.error(f"MQTT Device Auth: error looking up IMEI '{imei}': {e}")
        return False, None


def _looks_like_valid_password(value):
    """
    Is this a plausible Mode 2 (user) password?
    Accepts 40-char DRF token (hex) or 32-char derived key (hex).
    Note: Device IMEI passwords skip this check — they are validated directly
    against DeviceModel.mqtt_pw.
    """
    return bool(_RE_DRF_TOK.match(value) or _RE_DERIVED.match(value))


def _verify_mode2_password(user, password):
    """
    Verify Mode 2 password.  Accepts in order of preference:
    1. DRF Token (40-char hex string)
    2. Derived key  = SHA256(user_id_mobile_SECRET_KEY)[:32]
    Returns True if the password matches any accepted form.
    """
    # Check DRF token
    try:
        from rest_framework.authtoken.models import Token
        if Token.objects.filter(key=password, user=user).exists():
            return True
    except Exception:
        pass

    # Check derived key (used by prepare_mqtt_auth)
    try:
        mobile = getattr(user, 'mobile', None) or str(user.id)
        source = f"{user.id}_{mobile}_{settings.SECRET_KEY}"
        derived = hashlib.sha256(source.encode()).hexdigest()[:32]
        if password == derived:
            return True
    except Exception:
        pass

    return False


# acc values from go-auth
_ACC_READ  = 1  # subscribe
_ACC_WRITE = 2  # publish


def _topic_allowed(username, topic, acc):
    """
    Enforce topic ownership and access direction.

    Rules:
    - Superuser / admin: full access
    - $SYS/# topics: denied for all non-superusers
    - '<prefix>/<token>/server' topics: subscribe (read) only — server publishes, clients listen
    - '<prefix>/<token>' topics: publish + subscribe allowed if token matches user's identifier
    """
    if not username:
        return False

    # Admin / superuser bypass
    if username == MQTT_SUPERUSER:
        return True

    # Block $SYS topics for regular users
    if topic.startswith('$SYS/'):
        logger.warning(f"MQTT ACL: $SYS topic denied for {username}")
        return False

    segments = topic.split('/')

    # '/server' suffix topics: clients may only subscribe, not publish
    # Format: <prefix>/<token>/server
    if len(segments) == 3 and segments[-1] == 'server':
        if int(acc) == _ACC_WRITE:
            logger.warning(f"MQTT ACL: publish to /server topic denied for '{username}', topic='{topic}'")
            return False
        # Allow subscribe only if user's identifier is the middle segment
        if username == segments[1]:
            return True
        logger.warning(f"MQTT ACL: /server topic denied for '{username}', topic='{topic}'")
        return False

    # Standard topics: user's identifier must appear as a segment
    if username in segments:
        return True

    logger.warning(f"MQTT ACL: topic '{topic}' denied for '{username}'")
    return False


def _topic_allowed_for_client(clientid, topic, acc):
    """
    Secondary ACL check for JWT-authenticated clients.
    Looks up the cached {jwt, mobile} for this clientid and checks whether:
    1. The raw JWT token appears as the token segment of the topic
    2. The user's mobile number appears as the token segment of the topic
    '/server' suffix topics: subscribe only — publish denied for non-admin.
    """
    if not clientid:
        return False
    try:
        cached = cache.get(_jwt_session_key(clientid))
        if not cached:
            return False
        segments = topic.split('/')

        # '/server' topics: clients may only subscribe
        is_server_topic = len(segments) == 3 and segments[-1] == 'server'
        if is_server_topic and int(acc) == _ACC_WRITE:
            logger.warning(f"MQTT ACL: publish to /server topic denied for clientid='{clientid}', topic='{topic}'")
            return False

        # The token segment to check against: for /server topics it's segments[1], else any segment
        check_segments = [segments[1]] if is_server_topic else segments

        # Support both new dict format and legacy string format
        if isinstance(cached, str):
            if cached in check_segments:
                logger.info(f"MQTT ACL: JWT segment match (legacy) for clientid='{clientid}', topic='{topic}'")
                return True
            return False

        jwt_token = cached.get('jwt', '')
        mobile = cached.get('mobile', '')
        if jwt_token and jwt_token in check_segments:
            logger.info(f"MQTT ACL: JWT segment match for clientid='{clientid}', topic='{topic}'")
            return True
        if mobile and mobile in check_segments:
            logger.info(f"MQTT ACL: Mobile segment match for clientid='{clientid}', mobile={mobile}, topic='{topic}'")
            return True
    except Exception as e:
        logger.error(f"MQTT ACL: JWT session lookup error for clientid='{clientid}': {e}")
    return False


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([])
def mqtt_validate_connection(request):
    """
    Validate MQTT connection for mosquitto-go-auth plugin.

    Mode 1 — JWT-only (empty / placeholder username):
        username: "" | "jwt" | "token" | "bearer"
        password: <JWT token string>

    Mode 2 — Username + Password:
        username: <10-digit mobile OR device IMEI>
        password: <DRF token key OR SHA256-derived key>

    Returns 200 on success, 403 on failure.
    """
    try:
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '').strip()
        clientid = request.data.get('clientid', username or 'unknown')

        logger.info(
            f"MQTT Auth: username={'[empty]' if not username else username}, clientid={clientid}"
        )

        # --- Throttle gate (Redis only, zero DB cost) ---
        if _is_blocked(clientid):
            logger.warning(f"MQTT Auth: clientid '{clientid}' is currently blocked (throttle)")
            return Response({'error': 'Too many failed attempts. Try again later.'},
                            status=status.HTTP_403_FORBIDDEN)

        # --- MODE 1: JWT-only ---
        # Mobile apps may send the JWT as username (with any password) or as password (with empty/placeholder username)
        jwt_in_username = bool(username and _looks_like_jwt(username))
        is_jwt_mode = jwt_in_username or ((not username or username.lower() in ['jwt', 'token', 'bearer']) and password)
        jwt_token = username if jwt_in_username else password
        if is_jwt_mode:
            logger.info(f"MQTT Auth: JWT-only mode detected (token field: {'username' if jwt_in_username else 'password'})")

            # *** EARLY FORMAT CHECK — no DB hit for obviously bad tokens ***
            if not _looks_like_jwt(jwt_token):
                logger.warning(f"MQTT Auth: password rejected by format check (not a JWT), clientid={clientid}")
                _record_failure(clientid)
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_403_FORBIDDEN)

            if not verify_jwt_token(jwt_token):
                logger.warning("MQTT Auth: JWT verification failed")
                _record_failure(clientid)
                return Response({'error': 'Invalid JWT'}, status=status.HTTP_403_FORBIDDEN)

            payload = decode_jwt_token(jwt_token)
            if not payload:
                logger.warning("MQTT Auth: JWT decode failed")
                _record_failure(clientid)
                return Response({'error': 'Invalid JWT payload'}, status=status.HTTP_403_FORBIDDEN)

            user_id = payload.get('user_id')
            try:
                user = User.objects.get(id=user_id, is_active=True)
                _clear_failure(clientid)
                # Cache raw JWT keyed by clientid so ACL can match JWT-based topic segments
                _cache_jwt_for_client(clientid, jwt_token, payload)
                logger.info(f"MQTT Auth: JWT mode SUCCESS - user_id={user.id}, mobile={user.mobile}")
                return Response({'ok': True, 'user_id': user.id, 'username': user.mobile},
                                status=status.HTTP_200_OK)
            except User.DoesNotExist:
                logger.warning(f"MQTT Auth: User not found - user_id={user_id}")
                _record_failure(clientid)
                return Response({'error': 'User not found'}, status=status.HTTP_403_FORBIDDEN)

        # --- MODE 2 / MODE 3: Username + Password ---
        elif username and password and not jwt_in_username:
            logger.info(f"MQTT Auth: Username/Password mode - username={username}")

            # --- ADMIN BYPASS: Check admin credentials before format check ---
            if MQTT_SUPERUSER and username == MQTT_SUPERUSER:
                if MQTT_ADMIN_PASS and password == MQTT_ADMIN_PASS:
                    _clear_failure(clientid)
                    logger.info(f"MQTT Auth: Admin bypass SUCCESS - username={username}")
                    return Response({'ok': True, 'username': username}, status=status.HTTP_200_OK)
                else:
                    logger.warning(f"MQTT Auth: Admin password mismatch for '{username}'")
                    _record_failure(clientid)
                    return Response({'error': 'Authentication failed'}, status=status.HTTP_403_FORBIDDEN)

            # *** EARLY FORMAT CHECK — no DB hit for obviously bad credentials ***
            if not _looks_like_valid_username(username):
                logger.warning(f"MQTT Auth: username '{username}' rejected by format check (not mobile/IMEI)")
                _record_failure(clientid)
                return Response({'error': 'Authentication failed'}, status=status.HTTP_403_FORBIDDEN)

            # --- MODE 3: Device IMEI auth ---
            # IMEI passwords are device-model-specific strings (not hex DRF tokens),
            # so we skip the hex password format check and go straight to DB.
            if _RE_IMEI.match(username):
                logger.info(f"MQTT Auth: Device IMEI mode - imei={username}")

                # Backward-compatible clientid policy:
                # accept existing deployed patterns if they embed the same IMEI,
                # then enforce one active session per IMEI via Redis lease.
                if not _clientid_matches_imei(clientid, username):
                    logger.warning(
                        f"MQTT Auth: Device IMEI rejected due to clientid mismatch "
                        f"(imei={username}, clientid={clientid})"
                    )
                    _record_failure(clientid)
                    return Response(
                        {'error': 'For IMEI auth, clientid must include the same IMEI'},
                        status=status.HTTP_403_FORBIDDEN,
                    )

                if MQTT_IMEI_SESSION_ENFORCE:
                    ok, active_cid = _acquire_or_refresh_imei_session(username, clientid)
                    if not ok:
                        logger.warning(
                            f"MQTT Auth: Device IMEI rejected due to active session "
                            f"(imei={username}, clientid={clientid}, active_clientid={active_cid})"
                        )
                        _record_failure(clientid)
                        return Response(
                            {'error': f'Another session is active for IMEI {username}'},
                            status=status.HTTP_403_FORBIDDEN,
                        )

                if ALLOW_ALL_DEV_MQTT:
                    logger.info(f"MQTT Auth: ALLOWALLDEVMQTT=true — skipping password check for IMEI '{username}'")
                    _clear_failure(clientid)
                    return Response({'ok': True, 'username': username}, status=status.HTTP_200_OK)
                success, device_stock = _verify_device_password(username, password)
                if not success:
                    logger.warning(f"MQTT Auth: Device auth failed for IMEI '{username}'")
                    _record_failure(clientid)
                    return Response({'error': 'Authentication failed'}, status=status.HTTP_403_FORBIDDEN)
                _clear_failure(clientid)
                logger.info(f"MQTT Auth: Device IMEI mode SUCCESS - imei={username}, esn={device_stock.device_esn}")
                return Response({'ok': True, 'username': username}, status=status.HTTP_200_OK)

            # --- MODE 2: User mobile auth ---
            if not _looks_like_valid_password(password):
                logger.warning(f"MQTT Auth: password rejected by format check for '{username}'")
                _record_failure(clientid)
                return Response({'error': 'Authentication failed'}, status=status.HTTP_403_FORBIDDEN)

            try:
                user = User.objects.get(mobile=username, is_active=True)
            except User.DoesNotExist:
                # Strict: reject unknown users — do not leak user existence either
                logger.warning(f"MQTT Auth: Unknown username '{username}' — rejected")
                _record_failure(clientid)
                return Response({'error': 'Authentication failed'}, status=status.HTTP_403_FORBIDDEN)

            if not _verify_mode2_password(user, password):
                logger.warning(f"MQTT Auth: Invalid password for '{username}'")
                _record_failure(clientid)
                return Response({'error': 'Authentication failed'}, status=status.HTTP_403_FORBIDDEN)

            _clear_failure(clientid)
            logger.info(f"MQTT Auth: Username/Password mode SUCCESS - username={username}")
            return Response({'ok': True, 'username': username}, status=status.HTTP_200_OK)

        else:
            logger.warning("MQTT Auth: No credentials provided")
            _record_failure(clientid)
            return Response({'error': 'No credentials'}, status=status.HTTP_403_FORBIDDEN)

    except Exception as e:
        logger.error(f"MQTT Auth: Exception - {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([])
def mqtt_validate_acl(request):
    """
    Validate MQTT topic ACL for mosquitto-go-auth.

    Request fields: username, clientid, topic, acc (1=read, 2=write, 3=readwrite)

    Rules:
    - Admin/superuser: full access
    - $SYS/# topics: denied for all non-superusers
    - Regular users: topic must contain their username as a path segment
      e.g. 'deviceResponse/1000000002' is allowed only for user '1000000002'
    """
    try:
        username = request.data.get('username', '')
        clientid = request.data.get('clientid', '')
        topic = request.data.get('topic', '')
        acc = request.data.get('acc', 1)

        logger.info(f"MQTT ACL: username={username}, clientid={clientid}, topic={topic}, acc={acc}")

        # For JWT users, go-auth may pass the original JWT as username.
        # Resolve it to the mobile number using the Redis-cached session.
        effective_username = username
        if _looks_like_jwt(username):
            try:
                cached = cache.get(_jwt_session_key(clientid))
                if cached and isinstance(cached, dict) and cached.get('mobile'):
                    effective_username = cached['mobile']
                    logger.debug(f"MQTT ACL: resolved JWT username → mobile={effective_username}")
            except Exception:
                pass

        # Primary check: effective username (mobile or original) appears as a topic segment
        if _topic_allowed(effective_username, topic, acc):
            if MQTT_IMEI_SESSION_ENFORCE and _RE_IMEI.match(str(effective_username or '')):
                _acquire_or_refresh_imei_session(effective_username, clientid)
            return Response({'ok': True}, status=status.HTTP_200_OK)

        # If original username was a JWT and differs from mobile, also check the JWT directly as a segment
        if effective_username != username and _topic_allowed(username, topic, acc):
            if MQTT_IMEI_SESSION_ENFORCE and _RE_IMEI.match(str(effective_username or '')):
                _acquire_or_refresh_imei_session(effective_username, clientid)
            return Response({'ok': True}, status=status.HTTP_200_OK)

        # Secondary check: JWT token OR mobile (cached at CONNECT time) appears as a segment
        # Covers topics like 'sosEx/<jwt>', 'owner/<jwt>', 'dtorto/<mobile>', etc.
        if _topic_allowed_for_client(clientid, topic, acc):
            if MQTT_IMEI_SESSION_ENFORCE and _RE_IMEI.match(str(effective_username or '')):
                _acquire_or_refresh_imei_session(effective_username, clientid)
            return Response({'ok': True}, status=status.HTTP_200_OK)

        logger.warning(f"MQTT ACL: DENIED — username={username}, clientid={clientid}, topic={topic}")
        return Response({'error': 'Topic access denied'}, status=status.HTTP_403_FORBIDDEN)

    except Exception as e:
        logger.error(f"MQTT ACL: Exception - {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
