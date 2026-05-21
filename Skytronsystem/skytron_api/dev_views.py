"""
DEV-ONLY views — never exposed in production (DEBUG=False guard on every endpoint).

These endpoints exist solely to make local development and automated Postman/JMeter
testing easier by bypassing the captcha + RSA-encrypted-password + OTP login flow.
"""

from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import check_password

from .models import User, Session
from .serializers import UserSerializer2
from .secure_token import generate_jwt_token
from .login_settings_cache import get_session_expiry_minutes


def _dev_only(fn):
    """Decorator: return 403 immediately when DEBUG is False."""
    def wrapper(request, *args, **kwargs):
        if not getattr(settings, "DEBUG", False):
            return Response(
                {"error": "This endpoint is only available in DEBUG mode."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return fn(request, *args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


@api_view(["POST"])
@permission_classes([AllowAny])
@_dev_only
def dev_get_token(request):
    """
    DEV-ONLY — Obtain a JWT without going through captcha / OTP.

    Request body (plain JSON, no RSA encryption needed):
        {
            "username": "<mobile number>",
            "password": "<plain-text password>"
        }

    Response:
        {
            "status": "Login Successful",
            "token": "<JWT>",
            "role": "<user role>",
            "user": { ...UserSerializer2 fields... }
        }
    """
    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return Response(
            {"error": "username and password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.filter(mobile=username, is_active=True).last()
    if not user or not check_password(password, user.password):
        return Response(
            {"error": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    session_expiry_mins = get_session_expiry_minutes(user.role)

    jwt_token = generate_jwt_token(
        user_id=user.id,
        user_mobile=user.mobile,
        session_data={
            "login_type": "dev_bypass",
            "status": "authenticated",
            "role": user.role,
            "login_time": timezone.now().isoformat(),
        },
        expiry_minutes=session_expiry_mins,
    )

    # Upsert a Session so protected views that look up Session.status=='login' work.
    Session.objects.filter(user=user, status="login").delete()
    Session.objects.create(
        user=user,
        token=jwt_token,
        otp=685472,
        status="login",
        loginTime=timezone.now(),
        lastactivity=timezone.now(),
    )

    user.login = True
    user.save(update_fields=["login"])

    return Response(
        {
            "status": "Login Successful",
            "token": jwt_token,
            "role": user.role,
            "user": UserSerializer2(user).data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
@_dev_only
def dev_list_users(request):
    """
    DEV-ONLY — List available test accounts grouped by role.
    Useful for seeding Postman environment variables.

    Returns mobile numbers + roles (never passwords).
    """
    users = User.objects.filter(is_active=True).values("id", "name", "mobile", "role")
    by_role: dict = {}
    for u in users:
        by_role.setdefault(u["role"], []).append(
            {"id": u["id"], "name": u["name"], "mobile": u["mobile"]}
        )
    return Response({"users_by_role": by_role}, status=status.HTTP_200_OK)
