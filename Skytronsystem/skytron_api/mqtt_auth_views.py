"""
MQTT Authentication Helper Views
Provides endpoints to prepare MQTT authentication for JWT token-based clients
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import subprocess
import hashlib
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

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
        logger.error(f"Error in prepare_mqtt_auth_with_token: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
