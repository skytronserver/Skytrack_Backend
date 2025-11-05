"""
MQTT Connection Validation Endpoint for mosquitto-go-auth
Handles direct MQTT authentication with JWT-only mode support
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .secure_token import verify_jwt_token, decode_jwt_token
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def mqtt_validate_connection(request):
    """
    Validate MQTT connection for mosquitto-go-auth plugin
    
    Supports two modes:
    1. Username + Password (traditional)
    2. Password-only (JWT token)
    
    Request from mosquitto-go-auth:
    {
        "username": "1000000002" or "",
        "password": "static_password" or "JWT_TOKEN",
        "clientid": "client_id",
        "topic": "",
        "acc": 1
    }
    
    Returns:
    - 200 OK: Authentication successful
    - 403 Forbidden: Authentication failed
    """
    try:
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '').strip()
        clientid = request.data.get('clientid', '')
        
        logger.info(f"MQTT Auth: username={'[empty]' if not username else username}, clientid={clientid}")
        
        # MODE 1: Password-only (JWT token mode)
        if not username and password:
            logger.info("MQTT Auth: JWT-only mode detected")
            
            # Verify JWT signature (RS256)
            if not verify_jwt_token(password):
                logger.warning("MQTT Auth: JWT verification failed")
                return Response({'error': 'Invalid JWT'}, status=status.HTTP_403_FORBIDDEN)
            
            # Decode JWT
            payload = decode_jwt_token(password)
            if not payload:
                logger.warning("MQTT Auth: JWT decode failed")
                return Response({'error': 'Invalid JWT payload'}, status=status.HTTP_403_FORBIDDEN)
            
            user_id = payload.get('user_id')
            user_mobile = payload.get('user_mobile')
            
            logger.info(f"MQTT Auth: JWT decoded - user_id={user_id}, mobile={user_mobile}")
            
            # Lookup user
            try:
                user = User.objects.get(id=user_id, is_active=True)
                logger.info(f"MQTT Auth: JWT mode SUCCESS - user_id={user.id}, mobile={user.mobile}")
                return Response({
                    'ok': True,
                    'user_id': user.id,
                    'username': user.mobile
                }, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                logger.warning(f"MQTT Auth: User not found - user_id={user_id}")
                return Response({'error': 'User not found'}, status=status.HTTP_403_FORBIDDEN)
        
        # MODE 2: Username + Password (traditional dynamic-security)
        elif username and password:
            logger.info(f"MQTT Auth: Username/Password mode - username={username}")
            
            # Check if user exists in Django
            try:
                user = User.objects.get(mobile=username, is_active=True)
                
                # For now, we delegate to dynamic-security for password verification
                # You can add password verification here if needed
                logger.info(f"MQTT Auth: User exists - {username}, delegating to dynamic-security")
                
                # Return 200 to allow, mosquitto will still check dynamic-security
                # OR implement password check here and return 403 if invalid
                return Response({
                    'ok': True,
                    'username': username
                }, status=status.HTTP_200_OK)
                
            except User.DoesNotExist:
                logger.warning(f"MQTT Auth: User not found - {username}")
                # Still return 200 to let dynamic-security handle it
                # Change to 403 if you want to block unknown users
                return Response({
                    'ok': True,
                    'username': username
                }, status=status.HTTP_200_OK)
        
        else:
            logger.warning("MQTT Auth: No credentials provided")
            return Response({'error': 'No credentials'}, status=status.HTTP_403_FORBIDDEN)
    
    except Exception as e:
        logger.error(f"MQTT Auth: Exception - {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def mqtt_validate_acl(request):
    """
    Validate MQTT ACL (topic access control) for mosquitto-go-auth
    
    Request:
    {
        "username": "1000000002",
        "clientid": "client_id",
        "topic": "test/topic",
        "acc": 1  # 1=read, 2=write, 3=readwrite
    }
    
    Returns:
    - 200 OK: Access granted
    - 403 Forbidden: Access denied
    """
    try:
        username = request.data.get('username', '')
        topic = request.data.get('topic', '')
        acc = request.data.get('acc', 1)
        
        logger.info(f"MQTT ACL: username={username}, topic={topic}, acc={acc}")
        
        # For now, allow all access
        # TODO: Implement topic-based access control here
        return Response({'ok': True}, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"MQTT ACL: Exception - {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
