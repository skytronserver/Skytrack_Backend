# skytron_api/views.py
from rest_framework.authtoken.models import Token 
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate, login
from rest_framework.response import Response
from rest_framework import status
from .models import User as UserModel
from .serializers import UserSerializer
import random
from django.contrib.auth.hashers import make_password 
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import User as UserModel
from .serializers import UserSerializer
import random
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import User as UserModel, Session,Confirmation
from .serializers import UserSerializer, SessionSerializer
from django.contrib.auth.hashers import make_password, check_password



from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404


from .serializers import ConfirmationSerializer

@api_view(['POST'])
def validate_email_confirmation(request):
    user = request.data.get('user', None)
    confirmation_token = request.data.get('confirmation_token', None)

    if not confirmation_token:
        return Response({'error': 'Confirmation token not provided'}, status=400)
    if not user:
        return Response({'error': 'User not provided'}, status=400)

    # Validate the email confirmation link
    email_confirmation = get_object_or_404(Confirmation, user=user, token=confirmation_token)
    if email_confirmation.is_valid():
        # Perform actions when the email is confirmed (e.g., update user model)
        user.email_confirmed = True
        user.save()

        # Delete the email confirmation entry
        email_confirmation.delete()

        return Response({'status': 'Email confirmed successfully'}, status=200)
    else:
        return Response({'error': 'Invalid email confirmation link'}, status=400)



@api_view(['POST']) 
def send_email_confirmation(request):
    
    user = request.data.get('user', None) 
    if not user:
        return Response({'error': 'User not provided'}, status=400)
    # Generate a unique token for email confirmation
    confirmation_token = get_random_string(length=32)

    # Save the email confirmation data to the model
    email_confirmation_data = {'user': user.id, 'token': confirmation_token}
    email_confirmation_serializer = ConfirmationSerializer(data=email_confirmation_data)
    if email_confirmation_serializer.is_valid():
        email_confirmation_serializer.save()

        # Send confirmation email
        send_mail(
            'Email Confirmation',
            f'Click the link to confirm your email: http://yourdomain.com/confirm-email/{confirmation_token}',
            'from@example.com',
            [user.email],
            fail_silently=False,
        )

        return Response({'status': 'Email confirmation link sent successfully'}, status=200)
    else:
        return Response({'error': 'Failed to send email confirmation link'}, status=500)


@api_view(['POST'])
def validate_pwrst_confirmation(request):
    user = request.data.get('user', None)
    confirmation_token = request.data.get('confirmation_token', None)

    if not confirmation_token:
        return Response({'error': 'Confirmation token not provided'}, status=400)
    if not user:
        return Response({'error': 'User not provided'}, status=400)

    # Validate the email confirmation link
    email_confirmation = get_object_or_404(Confirmation, user=user, token=confirmation_token)
    if email_confirmation.is_valid():
        # Perform actions when the email is confirmed (e.g., update user model)
        user.email_confirmed = True
        user.save()

        # Delete the email confirmation entry
        email_confirmation.delete()

        return Response({'status': 'Email confirmed successfully'}, status=200)
    else:
        return Response({'error': 'Invalid email confirmation link'}, status=400)


@api_view(['POST']) 
def send_pwrst_confirmation(request):
    
    user = request.data.get('user', None) 
    if not user:
        return Response({'error': 'User not provided'}, status=400)

    # Generate a unique token for email confirmation
    confirmation_token = get_random_string(length=32)

    # Save the email confirmation data to the model
    email_confirmation_data = {'user': user.id, 'token': confirmation_token}
    email_confirmation_serializer = ConfirmationSerializer(data=email_confirmation_data)
    if email_confirmation_serializer.is_valid():
        email_confirmation_serializer.save()

        # Send confirmation email
        send_mail(
            'Email Confirmation',
            f'Click the link to confirm your email: http://yourdomain.com/confirm-email/{confirmation_token}',
            'from@example.com',
            [user.email],
            fail_silently=False,
        )

        return Response({'status': 'Email confirmation link sent successfully'}, status=200)
    else:
        return Response({'error': 'Failed to send email confirmation link'}, status=500)



@api_view(['POST'])
def validate_sms_confirmation(request):
    user = request.data.get('user', None)
    confirmation_token = request.data.get('confirmation_token', None)

    if not confirmation_token:
        return Response({'error': 'Confirmation token not provided'}, status=400)
    if not user:
        return Response({'error': 'User not provided'}, status=400)

    # Validate the email confirmation link
    email_confirmation = get_object_or_404(Confirmation, user=user, token=confirmation_token)
    if email_confirmation.is_valid():
        # Perform actions when the email is confirmed (e.g., update user model)
        user.email_confirmed = True
        user.save()

        # Delete the email confirmation entry
        email_confirmation.delete()

        return Response({'status': 'Email confirmed successfully'}, status=200)
    else:
        return Response({'error': 'Invalid email confirmation link'}, status=400)


@api_view(['POST']) 
def send_sms_confirmation(request):
    user = request.data.get('user', None) 
    if not user:
        return Response({'error': 'User not provided'}, status=400)

    # Generate a unique token for email confirmation
    confirmation_token = get_random_string(length=32)

    # Save the email confirmation data to the model
    email_confirmation_data = {'user': user.id, 'token': confirmation_token}
    email_confirmation_serializer = ConfirmationSerializer(data=email_confirmation_data)
    if email_confirmation_serializer.is_valid():
        email_confirmation_serializer.save()

        # Send confirmation email
        send_mail(
            'Email Confirmation',
            f'Click the link to confirm your email: http://yourdomain.com/confirm-email/{confirmation_token}',
            'from@example.com',
            [user.email],
            fail_silently=False,
        )

        return Response({'status': 'Email confirmation link sent successfully'}, status=200)
    else:
        return Response({'error': 'Failed to send email confirmation link'}, status=500)





class DeleteAllUsersView(APIView):
    def delete(self, request, *args, **kwargs):
        try:
            # Get the custom user model
            User = get_user_model()

            # Delete all users
            #User.objects.all().delete()

            return Response({'message': 'All users deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['POST'])
def create_user(request):
    """
    Create a new user.
    """
    serializer_class = UserSerializer
    if request.method == 'POST':
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user(request, user_id):
    """
    Update user details.
    """
    try:
        user = UserModel.objects.get(id=user_id)
    except UserModel.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['POST'])
def password_reset(request):
    """
    Reset user password.
    """
    if request.method == 'POST':
        email = request.data.get('email', None)

        if not email:
            return Response({'error': 'Email not provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Generate a random password, set and hash it
        new_password = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=12))
        hashed_password = make_password(new_password)
        user.password = hashed_password
        user.save()

        return Response({'message': 'Password reset successfully', 'new_password': new_password})



@csrf_exempt
@api_view(['POST'])
def send_email_otp(request):
    """
    Send OTP to the user's email.
    """
    if request.method == 'POST':
        email = request.data.get('email', None)

        if not email:
            return Response({'error': 'Email not provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Generate and send OTP via email (Implementation depends on your email service)

        return Response({'message': 'Email OTP sent successfully'})

@csrf_exempt
@api_view(['POST'])
def send_sms_otp(request):
    """
    Send OTP to the user's mobile.
    """
    if request.method == 'POST':
        mobile = request.data.get('mobile', None)

        if not mobile:
            return Response({'error': 'Mobile not provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = UserModel.objects.get(mobile=mobile)
        except UserModel.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Generate and send OTP via SMS (Implementation depends on your SMS service)

        return Response({'message': 'SMS OTP sent successfully'})


@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the login endpoint
def user_login(request):
    if request.method == 'POST':
        username = request.data.get('username', None)
        password = request.data.get('password', None)

        if not username or not password:
            return Response({'error': 'Username or password not provided'}, status=status.HTTP_400_BAD_REQUEST)

        user = UserModel.objects.filter(email=username).first() or UserModel.objects.filter(mobile=username).first()
        #print(user,password, user.password)
        #print(check_password(password, user.password), )
 
        if not user or not  check_password(password, user.password):
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        # Check for an existing active session
        existing_session = Session.objects.filter(user=user.id, status='login').first()

        #if existing_session:
        #    return Response({'token': existing_session.token}, status=status.HTTP_200_OK)

        # Generate an OTP and a unique token
        otp = str(random.randint(100000, 999999))
        #token = get_random_string(length=32)
        token, created = Token.objects.get_or_create(user=user)

        # Create a new session entry
        session_data = {
            'user': user.id,
            'token': str(token.key),
            'otp': otp,
            'status': 'otpsent',
            'login_time': timezone.now(),
        }
        print(session_data)

        session_serializer = SessionSerializer(data=session_data)  # Replace with your actual SessionSerializer
        if session_serializer.is_valid():
            session_serializer.save()

            # Send OTP to the user's email
             
            send_mail(
                'Login OTP',
                f'Your login OTP is: {otp}',
                'test@skytrack.tech',
                [user.email],
                fail_silently=False,
            ) 
            
            return Response({'status':'Email OTP Sent to '+str(user.email),'token': token.key}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Failed to create session'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
@permission_classes([AllowAny])  # Allow any user, as this is the OTP validation endpoint
def validate_otp(request):
    if request.method == 'POST':
        otp = request.data.get('otp', None)
        token = request.data.get('token', None)

        if not otp or not token:
            return Response({'error': 'OTP or session token not provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Find the session based on the provided token
        session = Session.objects.filter(token=token).first()

        if not session:
            return Response({'error': 'Invalid session token'}, status=status.HTTP_404_NOT_FOUND)

        if session.status == 'login':
            return Response({'status':'Login Successful','token': session.token}, status=status.HTTP_200_OK)

        # Validate the OTP
        print(otp,session.otp)
        if str(otp) == str(session.otp):
            # OTP is valid, change session status to 'login'
            session.status = 'login'
            session.save()

            return Response({'status':'Login Successful','token': session.token}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid OTP'}, status=status.HTTP_401_UNAUTHORIZED)
            
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_logout(request):
    """
    User logout.
    """
    if request.method == 'POST':
        token = request.data.get('token', None)

        if  not token:
            return Response({'error': 'Session token not provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Find the session based on the provided token
        session = Session.objects.filter(token=token).first()

        if not session:
            return Response({'error': 'Invalid session token'}, status=status.HTTP_404_NOT_FOUND)

        session.status = 'logout'
        session.save()


        return Response({'status': 'Logout successful'})

@csrf_exempt
@api_view(['GET'])
def user_get_parent(request, user_id):
    """
    Get parent user details.
    """
    try:
        user = UserModel.objects.get(id=user_id)
    except UserModel.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    parent_id = user.parent

    if not parent_id:
        return Response({'message': 'User has no parent'})

    try:
        parent_user = UserModel.objects.get(id=parent_id)
    except UserModel.DoesNotExist:
        return Response({'error': 'Parent user not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = UserSerializer(parent_user)
    return Response(serializer.data)

@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_list(request):
    """
    Get a list of users.
    """
    users = UserModel.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data ,status=status.HTTP_200_OK)

@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_details(request, user_id):
    """
    Get details of a specific user.
    """
    try:
        user = UserModel.objects.get(id=user_id)
    except UserModel.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = UserSerializer(user)
    return Response(serializer.data)
