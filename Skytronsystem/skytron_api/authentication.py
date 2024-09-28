# skytron_api/authentication.py
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from datetime import timedelta
#from .models import CustomToken  # Import the custom token model

class CustomTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.select_related('user').get(key=key)
        except model.DoesNotExist:
            raise AuthenticationFailed('Invalid token.')

        if not token.is_active:
            raise AuthenticationFailed('Token inactive or expired.')

        # Check for inactivity
        if timezone.now() - token.last_activity > timedelta(minutes=5):
            token.delete()
            raise AuthenticationFailed('Token expired due to inactivity.')

        token.last_activity = timezone.now()
        token.save()
        
        if not token.user.is_active:
            raise AuthenticationFailed('User inactive or deleted.')

        return (token.user, token)