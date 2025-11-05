"""
MQTT Authentication Helper Views
Provides endpoints to prepare MQTT authentication for JWT token-based clients

Supports dual authentication modes:
1. JWT Token Only (no username) - Validates JWT and creates MQTT user
2. Username + Password - Uses existing dynamic-security credentials
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from .secure_token import verify_jwt_token, decode_jwt_token
import subprocess
import hashlib
import logging
from django.conf import settings
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()

# MQTT Configuration
MQTT_ADMIN_USER = getattr(settings, 'MQTT_ADMIN_USER', 'admin')
MQTT_ADMIN_PASS = getattr(settings, 'MQTT_ADMIN_PASS', 'adminpass')
MQTT_HOST = getattr(settings, 'MQTT_HOST', '127.0.0.1')
MQTT_PORT = getattr(settings, 'MQTT_PORT', '8883')
MQTT_CA_FILE = getattr(settings, 'MQTT_CA_FILE', '/etc/mosquitto/certs/ca.crt')


def create_mqtt_user_credentials(user, jwt_token=None):
    """
    Create or update MQTT user in dynamic security
    
    Args:
        user: Django User object
        jwt_token: JWT token string (optional, for deterministic password)
    
    Returns:
        dict: {'username': str, 'password': str, 'success': bool}
    """
    try:
        # Determine MQTT username
        username = getattr(user, 'mobile', None) or str(user.id)
        
        # Generate password
        if jwt_token:
            # Use hash of JWT token as password
            password = hashlib.sha256(jwt_token.encode()).hexdigest()[:32]
        else:
            # Use user ID + mobile hash as password
            password_source = f"{user.id}_{username}_{settings.SECRET_KEY}"
            password = hashlib.sha256(password_source.encode()).hexdigest()[:32]
        
        # Create/update user in Mosquitto dynamic security
        cmd = [
            "mosquitto_ctrl",
            "--cafile", MQTT_CA_FILE,
            "-h", MQTT_HOST,
            "-p", MQTT_PORT,
            "-u", MQTT_ADMIN_USER,
            "-P", MQTT_ADMIN_PASS,
            "dynsec", "setClientPassword",
            username, password
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            logger.info(f"Created/updated MQTT user: {username}")
            return {
                'username': username,
                'password': password,
                'success': True,
                'message': 'MQTT credentials prepared successfully'
            }
        else:
            logger.error(f"Failed to create MQTT user {username}: {result.stderr}")
            return {
                'username': username,
                'password': None,
                'success': False,
                'message': f'Failed to create MQTT user: {result.stderr}'
            }
            
    except Exception as e:
        logger.error(f"Error creating MQTT credentials: {e}")
        return {
            'username': None,
            'password': None,
            'success': False,
            'message': f'Error: {str(e)}'
        }


@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
def prepare_mqtt_auth(request):
    """
    Prepare MQTT authentication credentials for the authenticated user
    
    This endpoint:
    1. Takes a JWT token from the request (or uses the authenticated user)
    2. Creates/updates MQTT user in dynamic security
    3. Returns MQTT connection credentials
    
    POST Parameters:
        jwt_token (optional): JWT token string
    
    Returns:
        {
            'mqtt_username': str,
            'mqtt_password': str,
            'mqtt_host': str,
            'mqtt_port': int,
            'mqtt_use_tls': bool,
            'mqtt_ca_file': str (optional),
            'success': bool
        }
    """
    try:
        user = request.user
        jwt_token = request.data.get('jwt_token') if request.method == 'POST' else None
        
        # If no JWT token provided, check Authorization header
        if not jwt_token and request.headers.get('Authorization'):
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                jwt_token = auth_header[7:]
            elif auth_header.startswith('Token '):
                jwt_token = auth_header[6:]
        
        # Create MQTT credentials
        creds = create_mqtt_user_credentials(user, jwt_token)
        
        if creds['success']:
            return Response({
                'success': True,
                'mqtt_username': creds['username'],
                'mqtt_password': creds['password'],
                'mqtt_host': MQTT_HOST,
                'mqtt_port': int(MQTT_PORT),
                'mqtt_use_tls': True,
                'mqtt_ca_cert': MQTT_CA_FILE,
                'message': 'MQTT credentials prepared. Use these to connect to MQTT broker.'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': creds['message']
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"Error in prepare_mqtt_auth: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def prepare_mqtt_auth_with_token(request):
    """
    Prepare MQTT authentication using JWT token (no session required)
    
    This endpoint validates a JWT token and prepares MQTT credentials
    without requiring an authenticated session.
    
    POST Parameters:
        jwt_token (required): JWT token string
    
    Returns:
        {
            'mqtt_username': str,
            'mqtt_password': str,
            'mqtt_host': str,
            'mqtt_port': int,
            'success': bool
        }
    """
    try:
        from skytron_api.secure_token import verify_jwt_token, decode_jwt_token
        
        jwt_token = request.data.get('jwt_token')
        if not jwt_token:
            return Response({
                'success': False,
                'error': 'jwt_token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify JWT token
        if not verify_jwt_token(jwt_token):
            return Response({
                'success': False,
                'error': 'Invalid or expired JWT token'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Decode token to get user info
        payload = decode_jwt_token(jwt_token)
        if not payload or not payload.get('user_id'):
            return Response({
                'success': False,
                'error': 'Invalid token payload'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Get user from database
        from django.contrib.auth.models import User
        try:
            user = User.objects.get(id=payload['user_id'], is_active=True)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': 'User not found or inactive'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Create MQTT credentials
        creds = create_mqtt_user_credentials(user, jwt_token)
        
        if creds['success']:
            return Response({
                'success': True,
                'mqtt_username': creds['username'],
                'mqtt_password': creds['password'],
                'mqtt_host': MQTT_HOST,
                'mqtt_port': int(MQTT_PORT),
                'mqtt_use_tls': True,
                'mqtt_ca_cert': MQTT_CA_FILE,
                'user_id': user.id,
                'mobile': getattr(user, 'mobile', None),
                'message': 'MQTT credentials prepared. Connect using these credentials.'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': creds['message']
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        logger.error(f"Error in prepare_mqtt_auth_with_token: {str(e)}")
        return Response({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def mqtt_dual_auth(request):
    """
    MQTT Dual Authentication Endpoint
    
    Supports two authentication modes:
    
    MODE 1 - JWT Token Only (no username):
    POST /mqtt/dual-auth/
    {
        "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
    
    MODE 2 - Username + Password:
    POST /mqtt/dual-auth/
    {
        "username": "1000000001",
        "password": "myStaticPassword"
    }
    
    Returns:
    {
        "success": true,
        "auth_mode": "jwt" or "username_password",
        "username": "1000000001",
        "password": "token_or_password",
        "mqtt_host": "127.0.0.1",
        "mqtt_port": 8883,
        "message": "..."
    }
    """
    try:
        # MODE 1: JWT Token Only (no username provided)
        if 'token' in request.data and not request.data.get('username'):
            jwt_token = request.data.get('token')
            
            logger.info(f"MQTT Dual Auth: JWT mode - token length={len(jwt_token)}")
            
            # Verify JWT signature and expiration
            if not verify_jwt_token(jwt_token):
                logger.warning("MQTT Dual Auth: JWT verification failed")
                return Response({
                    'success': False,
                    'error': 'Invalid or expired JWT token',
                    'auth_mode': 'jwt'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Decode JWT to extract user information
            payload = decode_jwt_token(jwt_token)
            if not payload or not payload.get('user_id'):
                logger.warning("MQTT Dual Auth: JWT decode failed")
                return Response({
                    'success': False,
                    'error': 'Unable to decode JWT token',
                    'auth_mode': 'jwt'
                }, status=status.HTTP_403_FORBIDDEN)
            
            user_id = payload.get('user_id')
            user_mobile = payload.get('user_mobile')
            
            logger.info(f"MQTT Dual Auth: JWT decoded - user_id={user_id}, mobile={user_mobile}")
            
            # Lookup user in Django database
            try:
                user = User.objects.get(id=user_id, is_active=True)
            except User.DoesNotExist:
                logger.warning(f"MQTT Dual Auth: User not found - user_id={user_id}")
                return Response({
                    'success': False,
                    'error': 'User not found or inactive',
                    'auth_mode': 'jwt'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Use mobile number as MQTT username
            mqtt_username = user.mobile
            
            # Create/update MQTT user with JWT token as password
            try:
                cmd = [
                    "mosquitto_ctrl",
                    "--cafile", MQTT_CA_FILE,
                    "-h", MQTT_HOST,
                    "-p", MQTT_PORT,
                    "-u", MQTT_ADMIN_USER,
                    "-P", MQTT_ADMIN_PASS,
                    "dynsec", "setClientPassword",
                    mqtt_username, jwt_token
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    logger.info(f"MQTT Dual Auth: JWT mode success - username={mqtt_username}")
                    return Response({
                        'success': True,
                        'auth_mode': 'jwt',
                        'username': mqtt_username,
                        'password': jwt_token,
                        'mqtt_host': MQTT_HOST,
                        'mqtt_port': int(MQTT_PORT),
                        'mqtt_use_tls': True,
                        'mqtt_ca_cert': MQTT_CA_FILE,
                        'user_id': user.id,
                        'mobile': user.mobile,
                        'message': 'JWT validated. MQTT user created/updated. Connect with provided credentials.'
                    }, status=status.HTTP_200_OK)
                else:
                    logger.error(f"MQTT Dual Auth: Failed to create MQTT user - {result.stderr}")
                    return Response({
                        'success': False,
                        'error': f'Failed to create MQTT user: {result.stderr}',
                        'auth_mode': 'jwt'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
            except subprocess.TimeoutExpired:
                logger.error("MQTT Dual Auth: mosquitto_ctrl timeout")
                return Response({
                    'success': False,
                    'error': 'MQTT control command timeout',
                    'auth_mode': 'jwt'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                logger.error(f"MQTT Dual Auth: Exception creating MQTT user - {str(e)}")
                return Response({
                    'success': False,
                    'error': f'Error creating MQTT user: {str(e)}',
                    'auth_mode': 'jwt'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # MODE 2: Username + Password (traditional dynamic-security)
        elif 'username' in request.data and 'password' in request.data:
            username = request.data.get('username')
            password = request.data.get('password')
            
            logger.info(f"MQTT Dual Auth: Username/Password mode - username={username}")
            
            if not username or not password:
                return Response({
                    'success': False,
                    'error': 'Username and password are required',
                    'auth_mode': 'username_password'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Return credentials for client to use with dynamic-security
            # No need to create user - they should already exist in dynamic-security.json
            logger.info(f"MQTT Dual Auth: Username/Password mode - delegating to dynamic-security for {username}")
            return Response({
                'success': True,
                'auth_mode': 'username_password',
                'username': username,
                'password': password,
                'mqtt_host': MQTT_HOST,
                'mqtt_port': int(MQTT_PORT),
                'mqtt_use_tls': True,
                'mqtt_ca_cert': MQTT_CA_FILE,
                'message': 'Use provided credentials to connect. Authentication via dynamic-security.'
            }, status=status.HTTP_200_OK)
        
        else:
            return Response({
                'success': False,
                'error': 'Invalid request. Provide either "token" (JWT mode) or "username" + "password" (traditional mode)',
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"MQTT Dual Auth: Unexpected error - {str(e)}")
        return Response({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"Error in prepare_mqtt_auth_with_token: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
