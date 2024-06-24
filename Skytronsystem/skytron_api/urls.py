from django.urls import path

 
from .views import *#SellFitDevice, ActivateESIMRequest, ConfirmESIMActivation, ConfigureIPPort, ConfigureSOSGateway, ConfigureSMSGateway, MarkDeviceDefective, ReturnToDeviceManufacturer
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

# ... the rest of your URLconf goes here ...


urlpatterns = [
    
    path('generate-captcha/', generate_captcha_api, name='generate_captcha'),
    path('verify-captcha/', verify_captcha_api, name='verify_captcha'),

    path('validate_otp/', validate_otp, name='validate_otp'),
    #path('user_login/', user_login, name='user_login'),

    #path('create_user/', create_user, name='create_user'),
    #path('update_user/<int:user_id>/', update_user, name='update_user'),
    path('password_reset/', password_reset, name='password_reset'),
    path('send_email_otp/', send_email_otp, name='send_email_otp'),
    path('send_sms_otp/', send_sms_otp, name='send_sms_otp'),
    path('user_login/', user_login, name='user_login'),
    path('reset_password_request/', reset_password, name='reset_password'),
     
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
    path('dealer/delete_dealer/<int:dealer_id>/', delete_dealer, name='delete_dealer'),
    path('eSimProvider/delete_eSimProvider/<int:esimProvider_id>/', delete_eSimProvider, name='delete_eSimProvider'),
    path('VehicleOwner/delete_VehicleOwner/<int:vo_id>/', delete_VehicleOwner, name='delete_VehicleOwner'),
    
    path('manufacturer/create_manufacturer/', create_manufacturer, name='create_manufacturer'),
    path('manufacturer/filter_manufacturers/', filter_manufacturers, name='filter_manufacturers'),
    path('manufacturer/delete_manufacturer/<int:manufacturer_id>/', delete_manufacturer, name='delete_manufacturer'),
    path('dealer/create_dealer/', create_dealer, name='create_dealer'),
    path('dealer/filter_dealer/', filter_dealer, name='filter_dealer'),
    path('eSimProvider/create_eSimProvider/', create_eSimProvider, name='create_eSimProvider'),
    path('eSimProvider/filter_eSimProvider/', filter_eSimProvider, name='filter_eSimProvider'),
    path('VehicleOwner/create_VehicleOwner/', create_VehicleOwner, name='create_VehicleOwner'),
    path('VehicleOwner/filter_VehicleOwner/', filter_VehicleOwner, name='filter_VehicleOwner'),



    path('Settings/create_settings_hp_freq/', create_Settings_hp_freq, name='create_settings_hp_freq'),
    path('Settings/filter_settings_hp_freq/', filter_Settings_hp_freq, name='filter_settings_hp_freq'),

    path('Settings/create_settings_ip/', create_Settings_ip, name='create_settings_ip'),
    path('Settings/filter_settings_ip/', filter_Settings_ip, name='filter_settings_ip'),

    path('Settings/create_settings_State/', create_Settings_State, name='create_settings_state'),
    path('Settings/filter_settings_State/', filter_Settings_State, name='filter_settings_state'),

    path('Settings/create_settings_District/', create_Settings_District, name='create_settings_District'),
    path('Settings/filter_settings_District/', filter_Settings_District, name='filter_settings_District'),


    path('Settings/create_settings_VehicleCategory/', create_Settings_VehicleCategory, name='create_settings_VehicleCategory'),
    path('Settings/filter_settings_VehicleCategory/', filter_Settings_VehicleCategory, name='filter_settings_VehicleCategory'),

    path('Settings/create_settings_firmware/', create_Settings_firmware, name='create_settings_firmware'),
    path('Settings/filter_settings_firmware/', filter_Settings_firmware, name='filter_settings_firmware'),
    
    
    

    path('StateAdmin/create_StateAdmin/', create_StateAdmin, name='create_StateAdmin'),
    path('StateAdmin/filter_StateAdmin/', filter_StateAdmin, name='filter_StateAdmin'),
    path('DTO_RTO/create_DTO_RTO/', create_DTO_RTO, name='create_DTO_RTO'),
    path('DTO_RTO/filter_DTO_RTO/', filter_DTO_RTO, name='filter_DTO_RTO'),
    path('DTO_RTO/getDistrictList/', getDistrictList, name='getDistrictList'),
    path('DTO_RTO/transfer_DTO_RTO/', transfer_DTO_RTO, name='transfer_DTO_RTO'),
    

    path('SOSAdmin/create_SOSAdmin/', create_SOS_admin, name='create_SOSAdmin'),
    path('SOSAdmin/filter_SOSAdmin/', filter_SOS_admin, name='filter_SOSAdmin'),
      

    path('homepageandstat/homepage/', homepage, name='homepage'),
    path('homepageandstat/homepage_user1/', homepage_user1, name='homepage_user1'),
    path('homepageandstat/homepage_user2/', homepage_user2, name='homepage_user2'),
    path('homepageandstat/homepage_device2/', homepage_device2, name='homepage_device2'),
    path('homepageandstat/homepage_device1/', homepage_device1, name='homepage_device1'),

    path('homepageandstat/homepage_alart/', homepage_alart, name='homepage_alart'),
    path('homepageandstat/homepage_state/', homepage_state, name='homepage_state'),


    path('SOSuser/create_SOSuser/', create_SOS_user, name='create_SOSuser'),
    path('SOSuser/filter_SOSuser/', filter_SOS_user, name='filter_SOSuser'),


    path('SOS/create_SOSteam/', create_SOS_team, name='create_SOSteam'),
    path('SOS/filter_SOSteam/', filter_SOS_team, name='filter_SOSteam'),


    path('list-alerts/', list_alert_logs, name='list_alert_logs'),
    path('gps-data-table/', gps_data_table, name='gps_data_table'),
    path('gps_history_map/',gps_history_map , name='gps_history_map'),
    path('gps_history_map_data/',gps_history_map_data , name='gps_history_map_data'),
    
    path('get_live_vehicle_no/',get_live_vehicle_no , name='get_live_vehicle_no'),#
    path('gps-data-map/',gps_data_allmap , name='gps_data_map'),
    path('gps-data-log-table/', gps_data_log_table, name='gps_data_log_table'),
    path('gps-em-data-log-table/', gps_em_data_log_table, name='gps_em_data_log_table'),
    path('gps_track_data_api/',gps_track_data_api, name='gps_track_data_api'),
    #emergency_call_listener_admin
    path('emergency-call-listener-admin/',emergency_call_listener_admin, name='emergency-call-listener-admin'), 
    path('emergency-call-listener-deskexecutive/',setRout, name='emergency-call-listener-deskexecutive'), 
    path('emergency-call-listener-team-lead/',emergency_call_listener_admin, name='emergency-call-listener-team-lead'), 
    path('setRout/',setRout, name='setRout'), 
    path('saveRout/',saveRout, name='saveRout'), 
    path('delRout/',delRout, name='delRout'), 
    path('getRout/',getRout, name='getRout'), 
    #path('emergency-call-listener-admin/',emergency_call_listener_admin, name='emergency-call-listener-admin'), 


    
    path('latest/', latest_gps, name='latest_gps'),
    path('emergency-call-listener/', emergency_call_listener, name='emergency_call_listener'),
    path('emergency-call-listener-field/', emergency_call_listener_field, name='emergency_call_listener_field'),
    path('get-live-call/', get_live_call, name='get_live_call'),
    path('get-all-call/', get_all_call, name='get_all_call'),
    path('get-live-call-field/', get_live_call_field, name='get_live_call_field'),
    path('emergency-call-details-google/<int:emergency_call_id>/', emergency_call_details, name='emergency_call_details'),
    path('emergency-call-details/<int:emergency_call_id>/', map2, name='emergency_call_details'),
    path('emergency-call-details-field/<int:emergency_call_id>/', emergency_call_details_field, name='emergency_call_details_field'),
    path('get-latest-gps-location/<int:emergency_call_id>/', get_latest_gps_location, name='get_latest_gps_location'),
    path('update-location/', update_location, name='update_location'),
    path('update-field-status/<str:field_ex>/', update_status, name='update_field_status'),
    path('broadcast-help/', Broadcast_help, name='assign_help'),
    path('submit_status/', SubmitStatus, name='SubmitStatus'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('login2/', Login2, name='login2'), 
    path('loginAndroid/', LoginAndroid, name='loginandroid'),
    path('map2/<int:emergency_call_id>/',  map2, name='map2'),
    path('', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    


    #path('SOSTeamLead/create_SOSTeamLead/', create_SOSTeamLead, name='create_SOSTeamLead'),
    #path('SOSTeamLead/filter_SOSTeamLead/', filter_SOSTeamLead, name='filter_SOSTeamLead'),



    #path('SOSExecutive_desk/create_SOSExecutive_desk/', create_SOSExecutive_desk, name='create_SOSExecutive_desk'),
    #path('SOSExecutive_desk/filter_SOSExecutive_desk/', filter_SOSExecutive_desk, name='filter_SOSExecutive_desk'),



    #path('SOSExecutive_desk/create_SOSExecutive_field/', create_SOSExecutive_field, name='create_SOSExecutive_field'),
    #path('SOSExecutive_desk/filter_SOSExecutive_field/', filter_SOSExecutive_field, name='filter_SOSExecutive_field'),

    #path('SOSTeam/create_SOSTeam/', create_SOSTeam, name='create_SOSTeam'),
    #path('SOSTeam/filter_SOSTeam/', filter_SOSTeam, name='filter_SOSTeam'),
    
   
 
    
    




    #device model
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
    
    #devicestock
    
    path('devicestock/esim_provider_list/', esim_provider_list, name='esim_provider_list'),
    path('devicestock/deviceStockCreate/', deviceStockCreate, name='deviceStockCreate'),
    path('devicestock/deviceStockBulkSample/', download_static_file, name='download_static_file'),
    path('devicestock/deviceStockCreateBulk/', deviceStockCreateBulk, name='deviceStockCreateBulk'),
    path('devicestock/deviceStockFilter/', deviceStockFilter, name='deviceStockFilter'),
    path('devicestock/StockAssignToRetailer/', StockAssignToRetailer, name='StockAssignToRetailer'),
    
    #sell
    path('sell/SellFitDevice/', SellFitDevice, name='SellFitDevice'),
    path('sell/SellListAvailableDeviceStock/', SellListAvailableDeviceStock, name='SellListAvailableDeviceStock'),
    path('sell/activate_esim_request/', ActivateESIMRequest, name='activate_esim_request'),
    path('sell/confirm_esim_activation/', ConfirmESIMActivation, name='confirm_esim_activation'),
    path('sell/configure_ip_port/', ConfigureIPPort, name='configure_ip_port'),
    path('sell/configure_sos_gateway/', ConfigureSOSGateway, name='configure_sos_gateway'),
    path('sell/configure_sms_gateway/', ConfigureSMSGateway, name='configure_sms_gateway'),
    path('sell/mark_device_defective/', MarkDeviceDefective, name='mark_device_defective'),
    path('sell/return_to_manufacturer/', ReturnToDeviceManufacturer, name='return_to_manufacturer'),
    
    #Devicetag
    path('tag/TagDevice2Vehicle/', TagDevice2Vehicle, name='TagDevice2Vehicle'),
    path('tag/untag/', unTagDevice2Vehicle, name='unTagDevice2Vehicle'),
    path('tag/TagAwaitingOwnerApproval/', TagAwaitingOwnerApproval, name='TagAwaitingOwnerApproval'),
    path('tag/TagSendOwnerOtp/', TagSendOwnerOtp, name='TagSendOwnerOtp'),
    path('tag/TagVerifyOwnerOtp/', TagVerifyOwnerOtp, name='TagVerifyOwnerOtpe'),
    path('tag/TagVerifyDealerOtp/', TagVerifyDealerOtp, name='TagVerifyDealerOtp'),
    path('tag/TagVerifyDTOOtp/', TagVerifyDTOOtp, name='TagVerifyDTOOtp'),
    path('tag/download_receiptPDF/', download_receiptPDF, name='download_receiptPDF'),
    path('tag/upload_receiptPDF/', upload_receiptPDF, name='upload_receiptPDF'),
   

    path('download/', downloadfile, name='download'),
    path('sms/rcv', sms_received, name='sms_received'),
    path('sms/que', sms_queue, name='sms_queue'),
    path('sms/send', sms_send, name='sms_send'),

]
'''
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
'''

    # Add other paths for the remaining APIs
 



 

urlpatterns += staticfiles_urlpatterns()