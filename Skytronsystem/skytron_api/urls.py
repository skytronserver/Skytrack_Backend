from django.urls import path
from .views import create_user, update_user, password_reset, send_email_otp, send_sms_otp, user_login, user_logout, user_get_parent, get_list, get_details, validate_otp
from .views import  FileUploadView,DeleteAllUsersView ,validate_email_confirmation,send_email_confirmation,validate_sms_confirmation,  send_sms_confirmation, validate_pwrst_confirmation,send_pwrst_confirmation 
from .views import create_manufacturer, create_retailer, create_device, create_device_model
from .views import update_manufacturer, update_retailer, update_device, update_device_model
from .views import delete_manufacturer, delete_retailer, delete_device, delete_device_model
from .views import list_manufacturers, list_retailers, list_devices, list_device_models
from .views import manufacturer_details, retailer_details, device_details, device_model_details
from .views import create_vehicle, update_vehicle, delete_vehicle, list_vehicles, vehicle_details
from .views import COPCreate,COPAwaitingStateApproval,COPSendStateAdminOtp,COPVerifyStateAdminOtp,COPManufacturerOtpVerify
from .views import (
    create_device_model,
    list_devicemodel,filter_devicemodel,details_devicemodel,
    DeviceVerifyStateAdminOtp,DeviceSendStateAdminOtp, 
    DeviceModelAwaitingStateApproval,   
    DeviceCreateManufacturerOtpVerify,
    deviceStockCreate,
    deviceStockCreateBulk,
    deviceStockFilter,
    StockAssignToRetailer,
    SellFitDevice,
    SellListAvailableDeviceStock,
    TagDevice2Vehicle,TagAwaitingOwnerApproval ,  TagSendOwnerOtp ,  
    TagVerifyOwnerOtp ,TagVerifyDealerOtp,
 
)
from .views import SellFitDevice, ActivateESIMRequest, ConfirmESIMActivation, ConfigureIPPort, ConfigureSOSGateway, ConfigureSMSGateway, MarkDeviceDefective, ReturnToDeviceManufacturer

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
    path('delete_all_users/', DeleteAllUsersView.as_view(), name='delete_all_users'),
    
    
    path('validate_email_confirmation',  validate_email_confirmation, name='validate_email_confirmation'),
    path('send_email_confirmation',  send_email_confirmation, name='send_email_confirmation'),
    path('validate_sms_confirmation',  validate_sms_confirmation, name='validate_sms_confirmation'),
    path('send_sms_confirmation',  send_sms_confirmation, name='send_sms_confirmation'),
    path('validate_pwrst_confirmation',  validate_pwrst_confirmation, name='validate_pwrst_confirmation'),
    path('send_pwrst_confirmation',  send_pwrst_confirmation, name='send_pwrst_confirmation'),

    path('devicemodel/devicemodelCreate/', create_device_model, name='devicemodel-create'),
    path('devicemodel/devicemodelList/', list_devicemodel, name='devicemodel-list'),
    path('devicemodel/devicemodleVerifyStateAdminOtp/', DeviceVerifyStateAdminOtp, name='device_verify_state_admin_otp'),
    path('devicemodel/devicemodelSendStateAdminOtp/', DeviceSendStateAdminOtp, name='device_send_state_admin_otp'),
    path('devicemodel/devicemodelAwaitingStateApproval/', DeviceModelAwaitingStateApproval, name='device_model_awaiting_state_approval'),
    path('devicemodel/devicemodelManufacturerOtpVerify/', DeviceCreateManufacturerOtpVerify, name='device_create_manufacturer_otp_verify'),
    path('devicemodel/COPUpload/', COPCreate, name='COPCreate'),
    path('devicemodel/COPAwaitingStateApproval/', COPAwaitingStateApproval, name='COPAwaitingStateApproval'),
    path('devicemodel/COPSendStateAdminOtp/', COPSendStateAdminOtp, name='COPSendStateAdminOtp'),
    path('devicemodel/COPVerifyStateAdminOtp/', COPVerifyStateAdminOtp, name='COPVerifyStateAdminOtp'),
    path('devicemodel/COPManufacturerOtpVerify/', COPManufacturerOtpVerify, name='COPManufacturerOtpVerify'),
    path('devicemodel/devicemodelFilter/', filter_devicemodel, name='devicemodel-filter'),
    path('devicemodel/devicemodelDetails/', details_devicemodel, name='devicemodel-detail'),
    
    path('devicestock/deviceStockCreate/', deviceStockCreate, name='deviceStockCreate'),
    path('devicestock/deviceStockCreateBulk/', deviceStockCreateBulk, name='deviceStockCreateBulk'),
    path('devicestock/deviceStockFilter/', deviceStockFilter, name='deviceStockFilter'),
    path('devicestock/StockAssignToRetailer/', StockAssignToRetailer, name='StockAssignToRetailer'),
 
    path('sell/SellFitDevice/', SellFitDevice, name='SellFitDevice'),
    path('sell/SellListAvailableDeviceStock/', SellListAvailableDeviceStock, name='SellListAvailableDeviceStock'),
    path('sell/activate_esim_request/', ActivateESIMRequest, name='activate_esim_request'),
    path('sell/confirm_esim_activation/', ConfirmESIMActivation, name='confirm_esim_activation'),
    path('sell/configure_ip_port/', ConfigureIPPort, name='configure_ip_port'),
    path('sell/configure_sos_gateway/', ConfigureSOSGateway, name='configure_sos_gateway'),
    path('sell/configure_sms_gateway/', ConfigureSMSGateway, name='configure_sms_gateway'),
    path('sell/mark_device_defective/', MarkDeviceDefective, name='mark_device_defective'),
    path('sell/return_to_manufacturer/', ReturnToDeviceManufacturer, name='return_to_manufacturer'),
    
    path('tag/TagDevice2Vehicle/', TagDevice2Vehicle, name='TagDevice2Vehicle'),
    path('tag/TagAwaitingOwnerApproval/', TagAwaitingOwnerApproval, name='TagAwaitingOwnerApproval'),
    path('tag/TagSendOwnerOtp/', TagSendOwnerOtp, name='TagSendOwnerOtp'),
    path('tag/TagVerifyOwnerOtp/', TagVerifyOwnerOtp, name='TagVerifyOwnerOtpe'),
    path('tag/TagVerifyDealerOtp/', TagVerifyDealerOtp, name='TagVerifyDealerOtp'),
    

    # Add other paths for the remaining APIs
]



 