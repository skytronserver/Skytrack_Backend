from django.urls import path
from .views import create_user, update_user, password_reset, send_email_otp, send_sms_otp, user_login, user_logout, user_get_parent, get_list, get_details, validate_otp
from .views import  FileUploadView,DeleteAllUsersView ,validate_email_confirmation,send_email_confirmation,validate_sms_confirmation,  send_sms_confirmation, validate_pwrst_confirmation,send_pwrst_confirmation 
from .views import create_manufacturer, create_retailer, create_device, create_device_model
from .views import update_manufacturer, update_retailer, update_device, update_device_model
from .views import delete_manufacturer, delete_retailer, delete_device, delete_device_model
from .views import list_manufacturers, list_retailers, list_devices, list_device_models
from .views import manufacturer_details, retailer_details, device_details, device_model_details
from .views import create_vehicle, update_vehicle, delete_vehicle, list_vehicles, vehicle_details

urlpatterns = [
    
    path('vehicles/', list_vehicles, name='list_vehicles'),
    path('vehicles/create/', create_vehicle, name='create_vehicle'),
    path('vehicles/<int:vehicle_id>/', vehicle_details, name='vehicle_details'),
    path('vehicles/<int:vehicle_id>/update/', update_vehicle, name='update_vehicle'),
    path('vehicles/<int:vehicle_id>/delete/', delete_vehicle, name='delete_vehicle'),

    path('manufacturer_details/<int:manufacturer_id>/', manufacturer_details, name='manufacturer_details'),
    path('retailer_details/<int:retailer_id>/', retailer_details, name='retailer_details'),
    path('device_details/<int:device_id>/', device_details, name='device_details'),
    path('device_model_details/<int:device_model_id>/', device_model_details, name='device_model_details'),
    
    path('list_manufacturers/', list_manufacturers, name='list_manufacturers'),
    path('list_retailers/', list_retailers, name='list_retailers'),
    path('list_devices/', list_devices, name='list_devices'),
    path('list_device_models/', list_device_models, name='list_device_models'),
   
    path('delete_manufacturer/<int:pk>/', delete_manufacturer, name='delete_manufacturer'),
    path('delete_retailer/<int:pk>/', delete_retailer, name='delete_retailer'),
    path('delete_device/<int:pk>/', delete_device, name='delete_device'),
    path('delete_device_model/<int:pk>/', delete_device_model, name='delete_device_model'),
   
    path('update_manufacturer/<int:pk>/', update_manufacturer, name='update_manufacturer'),
    path('update_retailer/<int:pk>/', update_retailer, name='update_retailer'),
    path('update_device/<int:pk>/', update_device, name='update_device'),
    path('update_device_model/<int:pk>/', update_device_model, name='update_device_model'),
  
    path('create_manufacturer/', create_manufacturer, name='create_manufacturer'),
    path('create_retailer/', create_retailer, name='create_retailer'),
    path('create_device/', create_device, name='create_device'),
    path('create_device_model/', create_device_model, name='create_device_model'),
    
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
    path('kyc_upload/', FileUploadView.as_view() , name='FileUploadView'),
    #path('delete_all_users/', DeleteAllUsersView.as_view(), name='delete_all_users'),
    
    
    path('validate_email_confirmation',  validate_email_confirmation, name='validate_email_confirmation'),
    path('send_email_confirmation',  send_email_confirmation, name='send_email_confirmation'),
    path('validate_sms_confirmation',  validate_sms_confirmation, name='validate_sms_confirmation'),
    path('send_sms_confirmation',  send_sms_confirmation, name='send_sms_confirmation'),
    path('validate_pwrst_confirmation',  validate_pwrst_confirmation, name='validate_pwrst_confirmation'),
    path('send_pwrst_confirmation',  send_pwrst_confirmation, name='send_pwrst_confirmation'),

 
    # Add other paths for the remaining APIs
]