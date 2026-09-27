#!/usr/bin/env python3
"""
Custom JWT Authentication for Django REST Framework
Provides secure JWT token-based authentication for API endpoints

Usage:
    In views.py:
    from .jwt_authentication import JWTAuthentication
    
    @authentication_classes([JWTAuthentication])
    @permission_classes([IsAuthenticated])
    def secure_view(request):
        # Access user from request.user
        return Response({'user_id': request.user.id})
"""

from rest_framework.authentication import BaseAuthentication
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from .secure_token import verify_jwt_token, decode_jwt_token
from .models import TokenBlacklist, Session
import logging

logger = logging.getLogger(__name__)

class JWTAuthentication(BaseAuthentication):
    """
    Custom JWT Authentication class for DRF
    """
    
    def authenticate(self, request):
        """
        Authenticate the request using JWT token
        
        Returns:
            tuple: (user, token) if authentication successful, None otherwise
        """
        # Get token from Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        if not auth_header:
            # Also check for token in request data (for backward compatibility)
            token = request.data.get('token') or request.GET.get('token')
            if not token:
                return None
        else:
            # Extract token from "Bearer <token>" format
            try:
                auth_parts = auth_header.split()
                if len(auth_parts) != 2 or auth_parts[0].lower() != 'bearer':
                    # Try direct token without Bearer prefix for backward compatibility
                    token = auth_header
                else:
                    token = auth_parts[1]
            except:
                return None
        
        return self.authenticate_token(token)
    
    def authenticate_token(self, token):
        """
        Authenticate using the provided token.

        This method must never raise AuthenticationFailed for a merely
        *unauthorized* token (wrong type, wrong session state, blacklisted,
        unknown user, etc.) - only for genuinely malformed input. The
        'token' field is reused across this codebase both as a bearer
        credential AND as an application-level lookup key on several
        AllowAny endpoints (e.g. OTP verification reads the same field from
        request.data). HybridAuthentication runs on every request, and DRF
        aborts the whole request with a hard 401 the instant any
        authenticator raises - regardless of that view's permission_classes.
        So an "unauthorized token" here must resolve to `return None`
        (not authenticated via this scheme) and let permission_classes
        (IsAuthenticated) do the actual gatekeeping on protected views,
        rather than raising and breaking unrelated AllowAny endpoints.

        Returns:
            tuple: (user, token) if successful, None otherwise
        """
        try:
            # Token has been explicitly invalidated (logout, security event)
            if TokenBlacklist.is_blacklisted(token):
                logger.warning(f"JWT token is blacklisted")
                return None

            # Verify the token signature and expiration
            if not verify_jwt_token(token):
                logger.warning(f"JWT token verification failed")
                return None

            # Decode the token to get user information
            payload = decode_jwt_token(token)
            if not payload:
                logger.warning(f"JWT token decode failed")
                return None

            # Extract user ID from payload
            user_id = payload.get('user_id')
            if not user_id:
                logger.warning(f"No user_id in JWT token payload")
                return None

            # Get user from database
            User = get_user_model()
            try:
                user = User.objects.get(id=user_id, is_active=True)
            except User.DoesNotExist:
                logger.warning(f"User {user_id} not found or inactive")
                return None

            # Only a fully-issued access token may authenticate general API
            # calls. Tokens minted for an intermediate step (e.g.
            # token_type="otp_pending", issued before OTP verification) must
            # not grant access anywhere else.
            token_type = payload.get('token_type', 'access')
            if token_type != 'access':
                logger.warning(f"Rejected non-access token_type for general API auth: {token_type}")
                return None

            # Verify the session backing this token is fully logged in. This
            # is allow-list (only 'login' passes) rather than deny-list, so a
            # token minted for an intermediate/unfinished auth step can never
            # be used to reach a general API even if its token_type were
            # ever mis-set to "access". A token with no Session row at all is
            # also rejected: every login flow persists its issued token in a
            # Session, so an orphan token (never logged in, or its session was
            # removed) must not be reusable just because its signature is valid.
            session = Session.objects.filter(token=token, user=user).last()
            if not session:
                logger.warning(f"No session found for JWT of user {user_id}")
                return None
            if session.status != 'login':
                logger.warning(f"Session not fully authenticated (status={session.status}) for user {user_id}")
                return None

            # Log successful authentication for security audit
            logger.info(f"JWT authentication successful for user {user_id}")

            return (user, token)

        except Exception as e:
            logger.error(f"JWT authentication error: {e}")
            return None
    
    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response.
        """
        return 'Bearer'


class LegacyTokenAuthentication(BaseAuthentication):
    """
    Fallback authentication for existing non-JWT tokens
    Gradually migrate to JWT-only authentication
    """
    
    def authenticate(self, request):
        """
        Authenticate using legacy Django tokens (for backward compatibility)
        """
        from rest_framework.authtoken.models import Token
        
        # Get token from various sources
        token_key = None
        
        # Check Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if auth_header:
            try:
                auth_parts = auth_header.split()
                if len(auth_parts) == 2 and auth_parts[0].lower() == 'token':
                    token_key = auth_parts[1]
            except:
                pass
        
        # Check request data
        if not token_key:
            token_key = request.data.get('token') or request.GET.get('token')
        
        if not token_key:
            return None
        
        # First try JWT authentication
        jwt_auth = JWTAuthentication()
        jwt_result = jwt_auth.authenticate_token(token_key)
        if jwt_result:
            return jwt_result
        
        # Fallback to legacy token authentication. Same rule as JWTAuthentication:
        # an unmatched/invalid credential here must return None, not raise -
        # this authenticator runs on every request (including AllowAny ones),
        # and raising here aborts the whole request with a hard 401 regardless
        # of that view's permission_classes.
        try:
            token = Token.objects.get(key=token_key)
            user = token.user

            if not user.is_active:
                logger.warning(f"Legacy token authentication rejected: user {user.id} inactive")
                return None

            logger.info(f"Legacy token authentication for user {user.id}")
            return (user, token_key)

        except Token.DoesNotExist:
            logger.warning(f"Invalid legacy token: {token_key[:10]}...")
            return None
        except Exception as e:
            logger.error(f"Legacy authentication error: {e}")
            return None


# Hybrid authentication class that tries JWT first, then falls back to legacy
class HybridAuthentication(BaseAuthentication):
    """
    Hybrid authentication that supports both JWT and legacy tokens
    Use this during migration period
    """
    
    def authenticate(self, request):
        """
        Try JWT authentication first, then legacy token authentication
        """
        # Try JWT authentication
        jwt_auth = JWTAuthentication()
        jwt_result = jwt_auth.authenticate(request)
        if jwt_result:
            return jwt_result
        
        # Try legacy authentication
        legacy_auth = LegacyTokenAuthentication()
        legacy_result = legacy_auth.authenticate(request)
        if legacy_result:
            return legacy_result
        
        return None