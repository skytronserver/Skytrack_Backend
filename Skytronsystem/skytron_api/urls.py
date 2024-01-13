from django.urls import path
from .views import create_user, update_user, password_reset, send_email_otp, send_sms_otp, user_login, user_logout, user_get_parent, get_list, get_details, validate_otp
from .views import  DeleteAllUsersView ,validate_email_confirmation,send_email_confirmation,validate_sms_confirmation,  send_sms_confirmation, validate_pwrst_confirmation,send_pwrst_confirmation 
urlpatterns = [
    # ... other URL patterns ...
    path('validate_otp/', validate_otp, name='validate_otp'),
    path('user_login/', user_login, name='user_login'),

    path('create_user/', create_user, name='create_user'),
    path('update_user/<int:user_id>/', update_user, name='update_user'),
    path('password_reset/', password_reset, name='password_reset'),
    path('send_email_otp/', send_email_otp, name='send_email_otp'),
    path('send_sms_otp/', send_sms_otp, name='send_sms_otp'),
    path('user_login/', user_login, name='user_login'),
    path('user_logout/', user_logout, name='user_logout'),
    path('user_get_parent/<int:user_id>/', user_get_parent, name='user_get_parent'),
    path('get_list/', get_list, name='get_list'),
    path('get_details/<int:user_id>/', get_details, name='get_details'),
    #path('delete_all_users/', DeleteAllUsersView.as_view(), name='delete_all_users'),
    
    path('validate_email_confirmation',  validate_email_confirmation, name='validate_email_confirmation'),
    path('send_email_confirmation',  send_email_confirmation, name='send_email_confirmation'),
    path('validate_sms_confirmation',  validate_sms_confirmation, name='validate_sms_confirmation'),
    path('send_sms_confirmation',  send_sms_confirmation, name='send_sms_confirmation'),
    path('validate_pwrst_confirmation',  validate_pwrst_confirmation, name='validate_pwrst_confirmation'),
    path('send_pwrst_confirmation',  send_pwrst_confirmation, name='send_pwrst_confirmation'),

 
    # Add other paths for the remaining APIs
]