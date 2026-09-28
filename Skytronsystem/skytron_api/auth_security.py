"""
Authentication hardening helpers (VAPT: token reuse / OTP bypass via
response manipulation).

- is_master_otp(): the fixed test OTP, controlled only by MASTER_OTP_ENABLED
  (not by DEBUG), so production can run with DEBUG=False.
- remember_login_txn() / consume_login_txn(): bind the access token issued by
  validate_otp to the login transaction (the pre-OTP token) that produced it.
  The frontend proves the binding once via /api/session/verify/, so a token
  replayed from an older login into a manipulated response is rejected.
"""
import hashlib
import hmac
import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# How long the frontend has to confirm a freshly issued token.
LOGIN_TXN_TTL_SECONDS = 120


def is_master_otp(otp):
    """True when the fixed test OTP is switched on and `otp` matches it."""
    if not getattr(settings, 'MASTER_OTP_ENABLED', False):
        return False
    master = str(getattr(settings, 'MASTER_OTP', '') or '')
    if not master or otp is None:
        return False
    matched = hmac.compare_digest(master, str(otp))
    if matched:
        logger.warning("Master OTP accepted")
    return matched


def _digest(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


def _txn_key(pre_otp_token):
    return f"login_txn:{_digest(pre_otp_token)}"


def remember_login_txn(pre_otp_token, access_token):
    """Record that `access_token` was issued for this login transaction."""
    try:
        cache.set(_txn_key(pre_otp_token), _digest(access_token), LOGIN_TXN_TTL_SECONDS)
    except Exception as e:
        logger.error(f"Could not store login transaction: {e}")


def consume_login_txn(pre_otp_token, access_token):
    """
    One-time check that `access_token` is the token issued for the login
    transaction `pre_otp_token`. The record is deleted on first use.
    """
    if not pre_otp_token or not access_token:
        return False
    key = _txn_key(pre_otp_token)
    try:
        expected = cache.get(key)
        cache.delete(key)
    except Exception as e:
        logger.error(f"Could not read login transaction: {e}")
        return False
    return bool(expected) and hmac.compare_digest(expected, _digest(access_token))
