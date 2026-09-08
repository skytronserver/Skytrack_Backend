from django.urls import path
from .views import *
from .views import create_trip, get_trip, update_trip, end_trip, cancel_trip
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from .mqtt_auth_views import prepare_mqtt_auth, prepare_mqtt_auth_with_token, mqtt_dual_auth
from .mqtt_validate_views import mqtt_validate_connection, mqtt_validate_acl
from .dev_views import dev_get_token, dev_list_users
from .complaint_views import (
    create_ticket,
    list_tickets,
    device_imei_lookup,
    ticket_detail,
    update_ticket_status,
    escalate_ticket,
    submit_final_report,
    add_comment,
    ticket_activity_log,
    public_track_ticket,
)
from .whitelist_views import (
    create_whitelist_request,
    list_whitelist_requests,
    esim_list_whitelist_requests,
    approve_whitelist_request,
    deny_whitelist_request,
    list_active_whitelist,
    update_device_kyc,
    device_dashboard,
    device_detail,
)
from .activation_views import (
    receive_activation_command_reply,
    send_activation_command,
    get_activation_status,
    list_pending_activations,
)
from .technical_onboarding_testing_views import (
    manufacturer_update_courier_tracking,
    superadmin_confirm_demo_device_receipt,
    technical_onboarding_test_case_list,
    technical_onboarding_test_case_upsert,
    superadmin_get_onboarding_test_board,
    superadmin_start_test,
    superadmin_test_heartbeat,
    superadmin_refresh_test_log,
    superadmin_complete_test,
    technical_onboarding_demo_page,
    technical_onboarding_test_catalog_page,
    technical_onboarding_test_requirements_page,
    dev_force_pass_test,
)
from .alert_stats_views import (
    alert_stats_type_options,
    alert_stats_summary,
    alert_stats_dashboard,
)
from .device_inspector_views import (
    device_inspector_lookup,
    device_inspector_logs,
    device_inspector_send_command,
    device_inspector_command_history,
    device_inspector_dashboard,
)
from .server_health_views import (
    server_health_summary,
    server_health_dashboard,
)
from .device_data_health_views import (
    device_data_health_format_options,
    device_data_health_lookup,
    device_data_health_dashboard,
)
from django.urls import path

 
from .views import * #SellFitDevice, ActivateESIMRequest, ConfirmESIMActivation, ConfigureIPPort, ConfigureSOSGateway, ConfigureSMSGateway, MarkDeviceDefective, ReturnToDeviceManufacturer
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from .mqtt_auth_views import prepare_mqtt_auth, prepare_mqtt_auth_with_token, mqtt_dual_auth
from .mqtt_validate_views import mqtt_validate_connection, mqtt_validate_acl


# ... the rest of your URLconf goes here ...


urlpatterns = [
    ## INUSE by Manufacturer, Owner, StateAdmin
    path('emuser-locations/', get_latest_emuser_locations, name='get_latest_emuser_locations'),
    ## INUSE by Owner
    path('trip/create/', create_trip, name='create_trip'),
    ## INUSE by Owner
    path('trip/<int:trip_id>/', get_trip, name='get_trip'),
    ## INUSE by Owner
    path('trip/', get_trip, name='get_trips'),
    ## INUSE by Owner
    path('trip/<int:trip_id>/update/', update_trip, name='update_trip'),
    ## INUSE by Owner
    path('trip/<int:trip_id>/end/', end_trip, name='end_trip'),
    ## INUSE by Owner
    path('trip/<int:trip_id>/cancel/', cancel_trip, name='cancel_trip'),
    
    path('cell_location/', cell_location_average, name='cell_location_average'),


    ## INUSE by Owner, StateAdmin
    ## PUBLIC
    path('geocode/', geocode_poi, name='geocode_poi'),
    ## INUSE by Owner, StateAdmin
    ## PUBLIC
    path('reverse_geocode/', reverse_geocode_poi, name='reverse_geocode_poi'),

    # SOS monthly metrics (unauthenticated)
    path('SOS/monthly_metrics/', sos_monthly_metrics, name='sos_monthly_metrics'),

    # Fleet metrics (unauthenticated)
    path('ambulance_fleet_metrics/', ambulace_fleet_metrics, name='ambulance_fleet_metrics'),
    path('ambulance_fleet_metrics222/', ambulance_fleet_metrics, name='ambulance_fleet_metrics'),
    path('police_fleet_metrics/', police_fleet_metrics, name='police_fleet_metrics'),

    # Vehicle status metrics (unauthenticated)
    ## INUSE by StateAdmin, SOSAdmin
    path('vehicle_status_metrics/', vehicle_status_metrics, name='vehicle_status_metrics'),

    # Public onboarding + device inventory dashboard metrics
    path('public/device_onboarding_dashboard/', public_device_onboarding_dashboard, name='public_device_onboarding_dashboard'),

    path('set_login_settings/', set_login_settings, name='set_login_settings'),
    path('get_login_settings/', get_login_settings, name='get_login_settings'),
    path('get_settings/', get_settings, name='settings'),
    
    path('EM/DEx/get-media/', DEx_getMedia, name='get_media'),
    path('generate-captcha/', generate_captcha_api, name='generate_captcha'),
    path('verify-captcha/', verify_captcha_api, name='verify_captcha'),

    path('validate_otp/', validate_otp, name='validate_otp'),
    path('password_reset/', password_reset, name='password_reset'),
    path('send_email_otp/', send_email_otp, name='send_email_otp'),
    path('send_sms_otp/', send_sms_otp, name='send_sms_otp'),
    path('resend_usercreation_otp/', resend_usercreation_otp, name='resend_usercreation_otp'),
    path('resend_parent_activation_otp/', resend_parent_activation_otp, name='resend_parent_activation_otp'),
    path('user_login/', user_login, name='user_login'),
    path('user_login_sosexecutive_direct/', user_login_sosexecutive_direct, name='user_login_sosexecutive_direct'),
    path('user_login_app/', user_login_app, name='user_login_app'),
    path('reset_password_request/', reset_password, name='reset_password'),
     
    path('deactivateUser/', deactivate_user, name='user_dactivate'),
    path('activateUser/', activate_user, name='user_activate'),
    path('user_logout/', user_logout, name='user_logout'),
    path('create_systemadmin/', create_superuser, name='create_superuser'),
    #path('user_get_parent/<int:user_id>/', user_get_parent, name='user_get_parent'),
    path('get_list/', get_list, name='get_list'),
    #path('get_details/<int:user_id>/', get_details, name='get_details'),
    path('kyc_upload/', FileUploadView.as_view() , name='FileUploadView'),
    #path('delete_all_users/', DeleteAllUsersView.as_view(), name='delete_all_users'),
    
    
    path('validate_email_confirmation',  validate_email_confirmation, name='validate_email_confirmation'),
    path('send_email_confirmation',  send_email_confirmation, name='send_email_confirmation'),
    path('validate_sms_confirmation',  validate_sms_confirmation, name='validate_sms_confirmation'),
    path('send_sms_confirmation',  send_sms_confirmation, name='send_sms_confirmation'),
    path('validate_pwrst_confirmation',  validate_pwrst_confirmation, name='validate_pwrst_confirmation'),
    path('send_pwrst_confirmation',  send_pwrst_confirmation, name='send_pwrst_confirmation'),
    path('dealer/delete_dealer/<int:dealer_id>/', delete_dealer, name='delete_dealer'),
    path('eSimProvider/delete_eSimProvider/<int:esimProvider_id>/', delete_eSimProvider, name='delete_eSimProvider'),
    path('VehicleOwner/delete_VehicleOwner/<int:vo_id>/', delete_VehicleOwner, name='delete_VehicleOwner'),
    
    path('holiday/create/', create_holiday, name='create_holiday'),
    path('holiday/update/<int:holiday_id>/', update_holiday, name='update_holiday'),
    path('holiday/delete/<int:holiday_id>/', delete_holiday, name='delete_holiday'),
    path('holiday/list/', list_holidays, name='list_holidays'),


    path('apiLog/', search_request_logs, name='apilog'),
    path('pub/apiLog/insights/', public_api_log_insights, name='public_api_log_insights'),
    
    path('driver/add_driver/', driver_add, name='add_driver'),
    path('driver/remove_driver/', driver_remove, name='remove_driver'),

    ## INUSE by Owner
    path('poi/create/', create_poi, name='create_poi'),
    path('poi/update/', update_poi, name='update_poi'),
    path('poi/delete/', delete_poi, name='delete_poi'),
    ## INUSE by Manufacturer, Owner, StateAdmin, SOSAdmin, SOSExecutive
    path('poi/list/', list_pois, name='list_pois'),
    ## INUSE by Manufacturer, Owner, StateAdmin, SOSAdmin
    path('poi/types/', list_poi_types, name='list_poi_types'),
    path('mqtt/send_command/', send_mqtt_command, name='send_mqtt_command'),

    
    path('manufacturer/create_manufacturer/', create_manufacturer, name='create_manufacturer'),
    path('pub/manufacturer/create_manufacturer/', create_manufacturer_pub, name='create_manufacturer_pub'),
    path('manufacturer/update_manufacturer/', update_manufacturer, name='update_manufacturer'),
    path('manufacturer/approve_tech_onboarding/', approve_manufacturer_tech_onboarding, name='approve_manufacturer_tech_onboarding'),
    ## INUSE by Owner, StateAdmin
    path('manufacturer/filter_manufacturers/', filter_manufacturers, name='filter_manufacturers'),
    ## INUSE by StateAdmin
    path('manufacturer/filter_TechOnboardmanufacturers/', filter_TechOnboardmanufacturers, name='filter_TechOnboardmanufacturers'),
    path('manufacturer/delete_manufacturer/<int:manufacturer_id>/', delete_manufacturer, name='delete_manufacturer'),
    ## INUSE by Manufacturer
    path('dealer/create_dealer/', create_dealer, name='create_dealer'),    
    path('dealer/update_dealer/', update_dealer, name='update_dealer'),
    ## INUSE by Manufacturer, StateAdmin
    path('dealer/filter_dealer/', filter_dealer, name='filter_dealer'),
    path('eSimProvider/create_eSimProvider/', create_eSimProvider, name='create_eSimProvider'),
    path('pub/eSimProvider/create_eSimProvider/', create_eSimProvider_pub, name='create_eSimProvider_pub'),
    path('eSimProvider/update_eSimProvider/', update_eSimProvider, name='update_eSimProvider'),
    path('pub/eSimProvider/filter_eSimProvider/', filter_eSimProvider_pub, name='filter_eSimProvider_pub'),
    ## INUSE by Manufacturer
    path('eSimProvider/filter_eSimProvider/', filter_eSimProvider, name='filter_eSimProvider'),

    path('testAgency/create_testAgency/', create_testAgency, name='create_testAgency'),
    path('testAgency/update_testAgency/', update_testAgency, name='update_testAgency'),
    path('testAgency/list/', get_testAgency_list, name='get_testAgency_list'),
    ## INUSE by Manufacturer
    path('testAgency/name_list/', get_testAgency_name_list, name='get_testAgency_name_list'),
    path('testAgency/details/list/', public_testAgencyDetails_list, name='public_testAgencyDetails_list'),
    path('testAgency/details/create/', create_testAgencyDetails, name='create_testAgencyDetails'),
    path('testAgency/details/update/', update_testAgencyDetails, name='update_testAgencyDetails'),
    path('testAgency/device_models/', get_testAgency_device_models, name='get_testAgency_device_models'),

    ## INUSE by Dealer
    path('VehicleOwner/create_VehicleOwner/', create_VehicleOwner, name='create_VehicleOwner'),
    path('VehicleOwner/update_VehicleOwner/', update_VehicleOwner, name='update_VehicleOwner'),
    ## INUSE by Dealer, StateAdmin, Analytics
    path('VehicleOwner/filter_VehicleOwner/', filter_VehicleOwner, name='filter_VehicleOwner'),



    path('Settings/create_settings_hp_freq/', create_Settings_hp_freq, name='create_settings_hp_freq'),
    ## INUSE by Manufacturer
    path('Settings/filter_settings_hp_freq/', filter_Settings_hp_freq, name='filter_settings_hp_freq'),

    path('Settings/create_settings_ip/', create_Settings_ip, name='create_settings_ip'),
    path('Settings/filter_settings_ip/', filter_Settings_ip, name='filter_settings_ip'),

    path('Settings/create_settings_State/', create_Settings_State, name='create_settings_state'),
    ## INUSE by Manufacturer, Owner, StateAdmin, PIS, Analytics, SOSAdmin
    path('Settings/filter_settings_State/', filter_Settings_State, name='filter_settings_state'),
    path('pub/Settings/filter_settings_State_pub/', filter_Settings_State_pub, name='filter_settings_state_pub'),
    

    path('Settings/create_settings_District/', create_Settings_District, name='create_settings_District'),
    ## INUSE by Manufacturer, StateAdmin, PIS, Analytics, SOSAdmin
    ## PUBLIC
    path('Settings/filter_settings_District/', filter_Settings_District, name='filter_settings_District'), 

    path('Settings/create_settings_VehicleCategory/', create_Settings_VehicleCategory, name='create_settings_VehicleCategory'),
    ## INUSE by Analytics
    path('Settings/filter_settings_VehicleCategory/', filter_Settings_VehicleCategory, name='filter_settings_VehicleCategory'),

    path('pub/Settings/vehicle_category_code/', pub_list_vehicle_category_code, name='pub_list_vehicle_category_code'),
    path('Settings/vehicle_category_code/create/', create_vehicle_category_code, name='create_vehicle_category_code'),
    path('Settings/vehicle_category_code/edit/', edit_vehicle_category_code, name='edit_vehicle_category_code'),
    path('Settings/vehicle_category_code/list/', list_all_vehicle_category_code, name='list_all_vehicle_category_code'),

    path('Settings/permit_master/list/', list_permit_master, name='list_permit_master'),
    path('Settings/permit_master/create/', create_permit_master, name='create_permit_master'),
    path('Settings/permit_master/edit/', edit_permit_master, name='edit_permit_master'),
    path('Settings/permit_master/list_all/', list_all_permit_master, name='list_all_permit_master'),

    path('Statistics/manufacturer_model_stock_statistics/', manufacturer_model_stock_statistics, name='manufacturer_model_stock_statistics'),
    path('Statistics/user_statistics/', user_statistics, name='user_statistics'),
    ## INUSE by SOSAdmin
    path('Statistics/vehicle_alert_statistics/', vehicle_alert_statistics, name='vehicle_alert_statistics'),

    ## INUSE by Manufacturer
    path('Settings/create_settings_firmware/', create_Settings_firmware, name='create_settings_firmware'),
    path('Settings/filter_settings_firmware/', filter_Settings_firmware, name='filter_settings_firmware'), 

    path('StateAdmin/create_StateAdmin/', create_StateAdmin, name='create_StateAdmin'),
    path('StateAdmin/update_StateAdmin/', update_StateAdmin, name='update_StateAdmin'),
    path('StateAdmin/filter_StateAdmin/', filter_StateAdmin, name='filter_StateAdmin'),
    ## INUSE by StateAdmin
    path('DTO_RTO/create_DTO_RTO/', create_DTO_RTO, name='create_DTO_RTO'),
    path('DTO_RTO/update_DTO_RTO/', update_DTO_RTO, name='update_DTO_RTO'),
    ## INUSE by StateAdmin
    path('DTO_RTO/filter_DTO_RTO/', filter_DTO_RTO, name='filter_DTO_RTO'),
    path('DTO_RTO/getDistrictList/', getDistrictList, name='getDistrictList'),
    path('DTO_RTO/transfer_DTO_RTO/', transfer_DTO_RTO, name='transfer_DTO_RTO'),
    

    path('SOSAdmin/create_SOSAdmin/', create_SOS_admin, name='create_SOSAdmin'),
    path('SOSAdmin/filter_SOSAdmin/', filter_SOS_admin, name='filter_SOSAdmin'),
      
    ## INUSE by SOSAdmin
    path('SOSuser/create_SOSuser/', create_SOS_user, name='create_SOSuser'),
    ## INUSE by SOSAdmin
    path('SOSuser/filter_SOSuser/', filter_SOS_user, name='filter_SOSuser'),


    path('homepageandstat/homepage_DTO/', homepage_DTO, name='homepage_DTO'),
    ## INUSE by Manufacturer
    path('homepageandstat/homepage_Manufacturer/', homepage_Manufacturer, name='homepage_Manufacturer'),
    path('homepageandstat/homepage_DTO/', homepage_DTO, name='homepage_DTO'),
    ## INUSE by Owner
    path('homepageandstat/homepage_VehicleOwner/', homepage_VehicleOwner, name='homepage_VehicleOwner'),
    ## INUSE by Dealer
    path('homepageandstat/homepage_Dealer/', homepage_Dealer, name='homepage_Dealer'),
    ## INUSE by StateAdmin
    path('homepageandstat/homepage_stateAdmin/', homepage_stateAdmin, name='homepage_stateAdmin'),
    ## INUSE by M2MProvider
    path('homepageandstat/homepage_esimProvider/', homepage_esimProvider, name='homepage_esimProvider'),
    
    path('homepageandstat/homepage/', homepage, name='homepage'),
    ## INUSE by SOSAdmin
    path('SOS/SOS_Admin_report/', SOS_adminreport2, name='SOS_adminreport'),
    path('SOS/SOS_Admin_report2/', SOS_adminreport, name='SOS_adminreport'),
    path('SOS/SOS_TL_report/', SOS_TLreport, name='SOS_TLreport'),
    ## INUSE by SOSExecutive
    path('SOS/SOS_EX_report/', SOS_EXreport, name='SOS_EXreport'),
    ## INUSE by SOSAdmin
    path('SOS/report/', SOS_detailed_report, name='SOS_detailed_report'),
    
    path('SOS/SOS_TL_report2/', SOS_TLreport2, name='SOS_TLreport'),

    
    path('homepageandstat/homepage_user1/', homepage_user1, name='homepage_user1'),
    path('homepageandstat/homepage_user2/', homepage_user2, name='homepage_user2'),
    path('homepageandstat/homepage_device2/', homepage_device2, name='homepage_device2'),
    path('homepageandstat/homepage_device1/', homepage_device1, name='homepage_device1'),

    path('homepageandstat/homepage_alart/', homepage_alart, name='homepage_alart'),
    path('homepageandstat/homepage_state/', homepage_state, name='homepage_state'),
    path('alart_list/',alart_list, name='alart_list'),
    path('device_tag_alerts/', get_device_tag_alerts, name='get_device_tag_alerts'),
    path('device_tags_search/', get_device_tags, name='get_device_tags'),



    ## INUSE by SOSAdmin
    path('EM/create_EMteam/', create_EM_team, name='create_EMteam'),
    ## INUSE by SOSAdmin
    path('EM/activate_EMteam/', activate_EM_team, name='activate_EM_team'),
    ## INUSE by SOSAdmin
    path('EM/remove_EMteam/', remove_EM_team, name='remove_EM_team'),
    ## INUSE by SOSAdmin
    path('EM/edit_EMteam/', edit_EM_team, name='edit_EM_team'),
    ## INUSE by SOSAdmin
    path('EM/get_EMteam/', get_EM_team, name='get_EM_team'),
    ## INUSE by SOSAdmin
    path('EM/list_EMteam/', list_EM_team, name='list_EM_team'),
    
    # Activated Device List
    ## INUSE by StateAdmin
    path('device/activated_device_list/', activated_device_list, name='activated_device_list'),

    ## INUSE by SOSAdmin, SOSExecutive
    path('EM/DEx/getPendingCallList/', DEx_getPendingCallList, name='DEx_getPendingCallList'),
    
    path('EM/DEx/getCallList/', DEx_getCallList, name='DEx_getCallList'),
    
    
    path('EM/DEx/getLiveCallList/', DEx_getLiveCallList, name='DEx_getLiveCallList'),
    
    path('EM/DExTL/getPendingCallList/', DEx_getPendingCallListTL, name='DEx_getPendingCallList'),
    
    
    ## INUSE by SOSAdmin, SOSExecutive
    path('EM/DEx/replyCall/', DEx_replyCall, name='DEx_replyCall'),

    ## INUSE by SOSAdmin, SOSExecutive
    path('EM/DEx/broadcast/', DEx_broadcast, name='DEx_broadcast'),
    path('checklive/', CheckLive, name='DEx_broadcast'),
    

    path('EM/DEx/listBroadcast/', DEx_broadcastlist, name='DEx_broadcastlist'),
    ## INUSE by SOSAdmin, SOSExecutive
    path('EM/DEx/closeCase/', DEx_closeCase, name='DEx_closeCase'),
    #path('EM/DEx/closeCase/', DEx_closeCase, name='DEx_closeCase'),
    ## INUSE by SOSAdmin, SOSExecutive
    path('EM/DEx/sendMsg/', DEx_sendMsg, name='DEx_sendMsg'),
    ## INUSE by SOSAdmin, SOSExecutive
    path('EM/DEx/rcvMsg/', DEx_rcvMsg, name='DEx_rcvMsg'),
    path('EM/DEx/commentFE/', DEx_commentFE, name='DEx_commentFE'),
    ## INUSE by SOSAdmin, SOSExecutive
    path('EM/DEx/getCallAllLoc/', DEx_getloc, name='DEx_getCallAllLoc'),
    path('EM/DEx/get-media/', DEx_getMedia, name='get_media'),
   

    path('api/device_media_upload', upload_media_file, name='upload_media_file'),
    path('api/dummy-insert-data', dummy_insert_data, name='dummy_insert_data'),
    
    
    path('EM/FEx/listBroadcast/', FEx_broadcastlist, name='FEx_broadcastlist'),
    path('EM/FEx/acceptBroadcast/', FEx_broadcastaccept, name='FEx_broadcastaccept'),
    path('EM/FEx/sendMsg/', DEx_sendMsg, name='FEx_sendMsg'),
    path('EM/FEx/rcvMsg/', DEx_rcvMsg, name='FEx_rcvMsg'),
    path('EM/FEx/getCallLoc/', FEx_getloc, name='FEx_getCallLoc'),

    path('EM/FEx/updateLoc/', FEx_updateLoc, name='FEx_updateLoc'),
    path('EM/FEx/updateStatus/', FEx_updateStatus, name='FEx_updateStatus'),
    path('EM/FEx/reqBackup/', FEx_reqBackup, name='FEx_reqBackup'),
    #path('EM/FEx/reqBackup/', FEx_reqBackup, name='FEx_reqBackup'),
    
    path('EM/DEx/listBackup/', DEx_listBackup, name='DEx_listBackup'),
    path('EM/DEx/acceptBackup/', DEx_acceptBackup, name='DEx_acceptBackup'), 



    path('EM/TLEEx/getAllCallList/', TLEx_getPendingCallList, name='TLEx_getAllCallList'),
    path('EM/TLEEx/getloc/', DEx_getloc, name='TLEx_getloc'),
    path('EM/TLEEx/reassign/', TLEx_reassign, name='TLEx_reassign'),




    
    ## INUSE by StateAdmin
    path('gps-data-log-table/', gps_data_log_table, name='gps_data_log_table'),
    path('gps-em-data-log-table/', gps_em_data_log_table, name='gps_em_data_log_table'),
    path('gps-packet-health-summary/', gps_packet_health_summary, name='gps_packet_health_summary'),
    path('gps-packet-dashboard/', gps_packet_dashboard, name='gps_packet_dashboard'),
    

  

    
    
    
    
    #path('SOS/filter_SOSteam/', filter_SOS_team, name='filter_SOSteam'),


    path('list-alerts/', list_alert_logs, name='list_alert_logs'), 
    # Global dashboard aggregated summary
    path('central_api/', global_counts_summary, name='global_counts_summary'),
    path('gps_history_map_data/',gps_history_map_data , name='gps_history_map_data'),
    
    ## INUSE by Owner, StateAdmin
    path('get_live_vehicle_no/',get_live_vehicle_no , name='get_live_vehicle_no'),#
      
    path('pub/gps_track_data_api/',gps_track_data_api_pub, name='gps_track_data_api_pub'),
    path('pub/gps_by_imei/', gps_by_imei, name='gps_by_imei'),  # public: latest GPS by IMEI
    path('pub/vahan_by_imei/', vahan_by_imei, name='vahan_by_imei'),      # public: Parivahan lookup by IMEI
    path('pub/vahan_by_regno/', vahan_by_regno, name='vahan_by_regno'),  # public: Parivahan lookup by regno+chassis
    ## INUSE by Manufacturer, Owner, StateAdmin, SOSAdmin
    path('gps_track_data_api/',gps_track_data_api, name='gps_track_data_api'),  # live tracking api
    path('gps_track_lite/', gps_track_lite_api, name='gps_track_lite_api'),             # lightweight tracking api
    path('gps_track_lite_options/', gps_track_lite_options_api, name='gps_track_lite_options_api'),  # available filter values
    path('gps_cluster/', gps_cluster_api, name='gps_cluster_api'),             # cluster summary api
    path('gps_grid_cluster/', gps_grid_cluster_api, name='gps_grid_cluster_api'),  # grid-based cluster api
    ## INUSE by Owner, StateAdmin
    path('saveRoute/',saveRoute, name='saveRout'), 
    ## INUSE by Owner, StateAdmin
    path('delRoute/',delRoute, name='delRout'), 
    ## INUSE by Owner, StateAdmin
    path('getRoute/',getRoute, name='getRout'), 
    ## INUSE by Manufacturer, Owner, StateAdmin
    ## PUBLIC
    path('get_routePath/',get_routePath, name='get_routePath'), 
    path('temp_user_login/',temp_user_login, name='temp_user_login'),
    path('temp_user_resendOTP/',temp_user_resendOTP, name='temp_user_resendOTP'),
    path('temp_user_OTPValidate/',temp_user_OTPValidate, name='temp_user_OTPValidate'),
    path('temp_user_BLEValidate/',temp_user_BLEValidate, name='temp_user_BLEValidate'), 
    path('temp_user_logout/',temp_user_logout, name='temp_user_logout'), 
    path('temp_user_emcall/',temp_user_emcall, name='temp_user_emcall'), 
    path('temp_user_Feedback/',temp_user_Feedback, name='temp_user_Feedback'), 
    
    
    #path('emergency-call-listener-admin/',emergency_call_listener_admin, name='emergency-call-listener-admin'), 

 
    #path('SOSTeamLead/create_SOSTeamLead/', create_SOSTeamLead, name='create_SOSTeamLead'),
    #path('SOSTeamLead/filter_SOSTeamLead/', filter_SOSTeamLead, name='filter_SOSTeamLead'),



    #path('SOSExecutive_desk/create_SOSExecutive_desk/', create_SOSExecutive_desk, name='create_SOSExecutive_desk'),
    #path('SOSExecutive_desk/filter_SOSExecutive_desk/', filter_SOSExecutive_desk, name='filter_SOSExecutive_desk'),



    #path('SOSExecutive_desk/create_SOSExecutive_field/', create_SOSExecutive_field, name='create_SOSExecutive_field'),
    #path('SOSExecutive_desk/filter_SOSExecutive_field/', filter_SOSExecutive_field, name='filter_SOSExecutive_field'),

    #path('SOSTeam/create_SOSTeam/', create_SOSTeam, name='create_SOSTeam'),
    #path('SOSTeam/filter_SOSTeam/', filter_SOSTeam, name='filter_SOSTeam'),
    
   
 
    
    



    #esimActivateReq
    ## INUSE by Dealer
    path('esimActivateReq/create/', create_esim_activation_request, name='esimActivateReq-create'),
    path('esimActivateReq/filter/', filter_esim_activation_request, name='esimActivateReq-filter'),
    path('esimActivateReq/update/', update_esim_activation_request, name='esimActivateReq-update'),



    #device model
    ## INUSE by Manufacturer
    path('devicemodel/devicemodelCreate/', create_device_model, name='devicemodel-create'),
    path('devicemodel/devicemodelList/', list_devicemodel, name='devicemodel-list'),
    path('devicemodel/devicemodleVerifyStateAdminOtp/', DeviceVerifyStateAdminOtp, name='device_verify_state_admin_otp'),
    path('devicemodel/devicemodelSendStateAdminOtp/', DeviceSendStateAdminOtp, name='device_send_state_admin_otp'),
    path('devicemodel/devicemodelAwaitingStateApproval/', DeviceModelAwaitingStateApproval, name='device_model_awaiting_state_approval'),
    ## INUSE by Manufacturer
    path('devicemodel/devicemodelManufacturerOtpVerify/', DeviceCreateManufacturerOtpVerify, name='device_create_manufacturer_otp_verify'),
    ## INUSE by Manufacturer
    path('devicemodel/COPUpload/', COPCreate, name='COPCreate'),
    path('devicemodel/COPAwaitingStateApproval/', COPAwaitingStateApproval, name='COPAwaitingStateApproval'),
    path('devicemodel/COPSendStateAdminOtp/', COPSendStateAdminOtp, name='COPSendStateAdminOtp'),
    path('devicemodel/COPVerifyStateAdminOtp/', COPVerifyStateAdminOtp, name='COPVerifyStateAdminOtp'),
    ## INUSE by Manufacturer
    path('devicemodel/COPManufacturerOtpVerify/', COPManufacturerOtpVerify, name='COPManufacturerOtpVerify'),
    ## INUSE by Manufacturer
    path('devicemodel/devicemodelFilter/', filter_devicemodel, name='devicemodel-filter'),
    ## INUSE by Manufacturer
    path('devicemodel/devicemodelDetails/', details_devicemodel, name='devicemodel-detail'),

    # device model technical onboarding request
    path(
        'devicemodel/technical-onboarding/create/',
        create_device_model_technical_onboarding_request,
        name='create_device_model_technical_onboarding_request'
    ),
    path(
        'devicemodel/technical-onboarding/superadmin/list/',
        superadmin_list_device_model_technical_onboarding_requests,
        name='superadmin_list_device_model_technical_onboarding_requests'
    ),
    path(
        'devicemodel/technical-onboarding/superadmin/mark-ongoing/',
        superadmin_mark_technical_onboarding_ongoing_evaluation,
        name='superadmin_mark_technical_onboarding_ongoing_evaluation'
    ),
    path(
        'devicemodel/technical-onboarding/superadmin/finalize/',
        superadmin_finalize_technical_onboarding_request,
        name='superadmin_finalize_technical_onboarding_request'
    ),
    path(
        'devicemodel/technical-onboarding/manufacturer/list/',
        manufacturer_list_own_device_model_technical_onboarding_requests,
        name='manufacturer_list_own_device_model_technical_onboarding_requests'
    ),

    # technical onboarding testing: courier tracking, receipt, test catalog + execution engine
    path(
        'devicemodel/technical-onboarding/manufacturer/courier-tracking/',
        manufacturer_update_courier_tracking,
        name='manufacturer_update_courier_tracking'
    ),
    path(
        'devicemodel/technical-onboarding/superadmin/confirm-receipt/',
        superadmin_confirm_demo_device_receipt,
        name='superadmin_confirm_demo_device_receipt'
    ),
    path(
        'devicemodel/technical-onboarding/test-cases/list/',
        technical_onboarding_test_case_list,
        name='technical_onboarding_test_case_list'
    ),
    path(
        'devicemodel/technical-onboarding/test-cases/upsert/',
        technical_onboarding_test_case_upsert,
        name='technical_onboarding_test_case_upsert'
    ),
    path(
        'devicemodel/technical-onboarding/superadmin/test-board/',
        superadmin_get_onboarding_test_board,
        name='superadmin_get_onboarding_test_board'
    ),
    path(
        'devicemodel/technical-onboarding/superadmin/test-start/',
        superadmin_start_test,
        name='superadmin_start_test'
    ),
    path(
        'devicemodel/technical-onboarding/superadmin/test-heartbeat/',
        superadmin_test_heartbeat,
        name='superadmin_test_heartbeat'
    ),
    path(
        'devicemodel/technical-onboarding/superadmin/test-refresh-log/',
        superadmin_refresh_test_log,
        name='superadmin_refresh_test_log'
    ),
    path(
        'devicemodel/technical-onboarding/superadmin/test-complete/',
        superadmin_complete_test,
        name='superadmin_complete_test'
    ),
    path(
        'devicemodel/technical-onboarding/demo/',
        technical_onboarding_demo_page,
        name='technical_onboarding_demo_page'
    ),
    path(
        'devicemodel/technical-onboarding/test-catalog/',
        technical_onboarding_test_catalog_page,
        name='technical_onboarding_test_catalog_page'
    ),
    path(
        'devicemodel/technical-onboarding/test-requirements/',
        technical_onboarding_test_requirements_page,
        name='technical_onboarding_test_requirements_page'
    ),


    #devicestock
    
    ## INUSE by Manufacturer, Dealer, M2MProvider
    path('devicestock/esim_provider_list/', esim_provider_list, name='esim_provider_list'),
    ## INUSE by Manufacturer
    path('devicestock/deviceStockCreate/', deviceStockCreate, name='deviceStockCreate'),
    ## INUSE by Manufacturer
    ## PUBLIC
    path('devicestock/deviceStockBulkSample/', download_static_file, name='download_static_file'),
    ## INUSE by Manufacturer
    path('devicestock/deviceStockCreateBulk/', deviceStockCreateBulk, name='deviceStockCreateBulk'),
    ## INUSE by Manufacturer, Dealer, StateAdmin
    path('devicestock/deviceStockFilter/', deviceStockFilter, name='deviceStockFilter'),
    ## INUSE by Manufacturer
    path('devicestock/deviceStockUntaggedFilter/', deviceStockUntaggedFilter, name='deviceStockUntaggedFilter'),
    ## INUSE by Manufacturer
    path('devicestock/deviceStockSoftDelete/', deviceStockSoftDelete, name='deviceStockSoftDelete'),
    ## INUSE by Manufacturer
    path('devicestock/StockAssignToDealer/', StockAssignToDealer, name='StockAssignToDealer'),
    ## INUSE by Manufacturer
    path('devicestock/combined/', combined_device_stock, name='combined_device_stock'),
    
    #sell
    ## path('sell/SellFitDevice/', SellFitDevice, name='SellFitDevice'),
    ## INUSE by Dealer
    path('sell/SellListAvailableDeviceStock/', SellListAvailableDeviceStock, name='SellListAvailableDeviceStock'),
    #path('sell/activate_esim_request/', ActivateESIMRequest, name='activate_esim_request'),
    ##path('sell/confirm_esim_activation/', ConfirmESIMActivation, name='confirm_esim_activation'),
    #path('sell/configure_ip_port/', ConfigureIPPort, name='configure_ip_port'),
    #path('sell/configure_sos_gateway/', ConfigureSOSGateway, name='configure_sos_gateway'),
    #path('sell/configure_sms_gateway/', ConfigureSMSGateway, name='configure_sms_gateway'),
    path('sell/mark_device_defective/', MarkDeviceDefective, name='mark_device_defective'),
    path('sell/return_to_manufacturer/', ReturnToDeviceManufacturer, name='return_to_manufacturer'),
    
    # Dealer eSIM status check
    ## INUSE by Dealer
    path('dealer/check_esim_status/', dealer_check_esim_status, name='dealer_check_esim_status'),
    
    #Devicetag
    path('tag/TagDevice2Vehicle/', TagDevice2Vehicle, name='TagDevice2Vehicle'),
    path('tag/update-temp-registration/', update_temp_tag_registration, name='update_temp_tag_registration'),
    path('tag/cancelTagDevice2Vehicle/', deleteTagDevice2Vehicle, name='cancelTagDevice2Vehicle'),
    path('validate_ble/', validate_ble, name='validate_ble'),
    
    
    ## INUSE by Dealer
    path('tag/untag/', unTagDevice2Vehicle, name='unTagDevice2Vehicle'),
    ## INUSE by Dealer
    path('tag/retag/', reTagDevice2Vehicle, name='reTagDevice2Vehicle'),
    path('tag/TagAwaitingOwnerApproval/', TagAwaitingOwnerApproval, name='TagAwaitingOwnerApproval'),
    path('tag/TagSendOwnerOtp/', TagSendOwnerOtp, name='TagSendOwnerOtp'),
    path('tag/TagVerifyOwnerOtp/', TagVerifyOwnerOtp, name='TagVerifyOwnerOtpe'),
    path('tag/TagAwaitingActivateTag/',TagAwaitingActivateTag, name='TagAwaitingOwnerApproval'),
    path('tag/getVehicle/',TagGetVehicle, name='TagGetVehicle'),
    
    path('tag/GetVahanAPIInfo/',GetVahanAPIInfo, name='GetVahanAPIInfo'),
    path('tag/GetVahanAPIInfoByRegnNo/', GetVahanAPIInfoByRegnNo, name='GetVahanAPIInfoByRegnNo'),
    path('tag/ActivateTag/',ActivateTag, name='ActivateTag'),
    
    path('tag/TagAwaitingOwnerApprovalFinal/', TagAwaitingOwnerApprovalFinal, name='TagAwaitingOwnerApprovalFinal'),
    path('tag/TagSendOwnerOtpFinal/',  TagSendOwnerOtpFinal, name='TagSendOwnerOtpFinal'),
    path('tag/TagResendOwnerOtpFinal/', TagResendOwnerOtpFinal, name='TagResendOwnerOtpFinal'),
    path('tag/TagVerifyOwnerOtpFinal/', TagVerifyOwnerOtpFinal, name='TagVerifyOwnerOtpFinal'),





    path('tag/TagVerifyDealerOtp/', TagVerifyDealerOtp, name='TagVerifyDealerOtp'),
    path('tag/TagResendDealerOtp/', TagResendDealerOtp, name='TagResendDealerOtp'),
    path('tag/TagResendOwnerOtp/', TagResendOwnerOtp, name='TagResendOwnerOtp'),
    #path('tag/TagVerifyDTOOtp/', TagVerifyDTOOtp, name='TagVerifyDTOOtp'),
    path('tag/download_receiptPDF/', download_receiptPDF, name='download_receiptPDF'),
    path('tag/upload_receiptPDF/', upload_receiptPDF, name='upload_receiptPDF'),
    
    path('tag/tag_status/', Tag_status, name='tag_status'),
    ## INUSE by Owner, StateAdmin
    path('tag/tag_ownerlist/', Tag_ownerlist, name='tag_ownerlist'),
    path('tag/StateAdmin_view_all_tagging/', StateAdmin_view_all_tagging, name='StateAdmin_view_all_tagging'),
   

    ## INUSE by Manufacturer, StateAdmin, SOSAdmin
    path('download/', downloadfile, name='download'),
    path('sms/rcv', sms_received, name='sms_received'),
    path('sms/send', sms_send, name='sms_send'),
    path('sms/que', sms_queue, name='sms_queue'),
    path('sms/que_add', sms_queue_add, name='sms_queue_add'),


    path('notice/create/', create_notice, name='create_notice'),
    path('notice/update/', update_notice, name='update_notice'),
    path('notice/filter/', filter_notice, name='filter_notice'),
    path('notice/delete/', delete_notice, name='delete_notice'),
    
    path('notice/list/', list_notice, name='list_notice'),
    
    # Debug endpoint for checking file paths
    path('debug/check_file_paths/', check_file_paths, name='check_file_paths'),
    
    # State Admin Reports APIs
    ## INUSE by StateAdmin
    path('stateadmin/reports/approved-models/', state_admin_approved_models_report, name='state_admin_approved_models_report'),
    ## INUSE by StateAdmin
    path('stateadmin/reports/approved-cops/', state_admin_approved_cops_report, name='state_admin_approved_cops_report'),
    path('stateadmin/reports/combined-approval/', state_admin_combined_approval_report, name='state_admin_combined_approval_report'),
    ## INUSE by Owner
    path('device-trip-details/', get_device_trip_details, name='get_device_trip_details'),
    ## INUSE by Owner, StateAdmin
    path('device-health-status/', get_device_health_status, name='get_device_health_status'),
    
    # MQTT Authentication endpoints
    path('mqtt/prepare-auth/', prepare_mqtt_auth, name='prepare_mqtt_auth'),
    path('mqtt/prepare-auth-token/', prepare_mqtt_auth_with_token, name='prepare_mqtt_auth_with_token'),
    path('mqtt/dual-auth/', mqtt_dual_auth, name='mqtt_dual_auth'),  # NEW: Dual authentication mode
    path('mqtt/validate-connection/', mqtt_validate_connection, name='mqtt_validate_connection'),  # For mosquitto-go-auth
    path('mqtt/validate-acl/', mqtt_validate_acl, name='mqtt_validate_acl'),  # For mosquitto-go-auth ACL

    # Module access check
    path('check-module-access/', check_module_access, name='check_module_access'),
    path('check-user-access/', check_user_type, name='check_user_type'),

    # RBAC management (superadmin only)
    path('rbac/modules/', rbac_list_modules, name='rbac_list_modules'),
    path('rbac/roles/', rbac_list_roles, name='rbac_list_roles'),
    path('rbac/roles/active/', rbac_active_roles, name='rbac_active_roles'),
    path('rbac/roles/create/', rbac_create_custom_role, name='rbac_create_custom_role'),
    path('rbac/roles/update/', rbac_update_role, name='rbac_update_role'),
    path('rbac/roles/permissions/', rbac_get_role_permissions, name='rbac_get_role_permissions'),
    path('rbac/roles/permissions/update/', rbac_update_role_permissions, name='rbac_update_role_permissions'),
    path('rbac/roles/deactivate/', rbac_deactivate_role, name='rbac_deactivate_role'),

    # RBAC user management (superadmin only, except active roles list)
    path('rbac/users/', rbac_list_users, name='rbac_list_users'),
    path('rbac/users/create/', rbac_create_user, name='rbac_create_user'),
    path('rbac/users/update/', rbac_update_user, name='rbac_update_user'),
    path('rbac/users/assign-role/', rbac_assign_role, name='rbac_assign_role'),

    # Bus Stand APIs
    path('busstand/set/', set_bus_stand, name='set_bus_stand'),
    path('busstand/activate-deactivate/', activate_deactivate_bus_stand, name='activate_deactivate_bus_stand'),
    path('busstand/filter/', filter_bus_stand, name='filter_bus_stand'),
    
    # OTA Settings APIs
    path('ota/create/', create_ota_settings, name='create_ota_settings'),
    path('ota/update/', update_ota_settings, name='update_ota_settings'),
    path('ota/filter/', filter_ota_settings, name='filter_ota_settings'),

    # OTA Command Definitions (Page 1)
    path('ota/command/create/', create_ota_command_definition, name='create_ota_command_definition'),
    path('ota/command/update/', update_ota_command_definition, name='update_ota_command_definition'),
    path('ota/command/filter/', filter_ota_command_definitions, name='filter_ota_command_definitions'),

    # OTA Command History & Send Command (Page 2)
    path('ota/command/history/filter/', filter_ota_command_history, name='filter_ota_command_history'),
    path('ota/command/history/update/', update_ota_command_history, name='update_ota_command_history'),
    path('ota/command/send/', send_ota_command, name='send_ota_command'),
    path('ota/command/device-search/', search_devices_for_ota_command, name='search_devices_for_ota_command'),

    # OTA Command Value Suggestions
    path('ota/command/value-suggestions/', get_ota_command_value_suggestions, name='get_ota_command_value_suggestions'),

    # Incident Register APIs
    path('incident/register/', register_incident, name='register_incident'),
    ## INUSE by Manufacturer, StateAdmin, SOSAdmin, SOSExecutive
    path('incident/filter/', filter_incident, name='filter_incident'),
    path('incident/update/', update_incident, name='update_incident'),
    
    # AlertsLog APIs
    path('alertlog/create/', create_alert_log, name='create_alert_log'),
    path('alertlog/update/', update_alert_log, name='update_alert_log'),
    ## INUSE by Manufacturer, Owner, StateAdmin
    path('alertlog/filter/', filter_alert_log, name='filter_alert_log'),
    
    # Notification Preferences API
    path('user/notification-preferences/', update_notification_preferences, name='update_notification_preferences'),
    
    # GPS Data Archive/Restore APIs
    path('gpsdata/archive/', archive_gps_data_log, name='archive_gps_data_log'),
    path('gpsdata/restore/', restore_gps_data_log, name='restore_gps_data_log'),
    path('gpsdata/archives/list/', list_gps_data_archives, name='list_gps_data_archives'),

    # IMEI Continuity Analysis  /api/vltddata/imei-continuity/
    path('vltddata/imei-continuity/', gps_imei_continuity_api, name='gps_imei_continuity_api'),
    path('vltddata/imei-continuity/view/', gps_imei_continuity_page, name='gps_imei_continuity_page'),
    
    # Cell Tower Information API
    path('gpsdata/agps-info/', get_cell_tower_info, name='get_cell_tower_info'),
    
    # Public Contact Form API
    path('public/user_registration/', public_contact_form, name='public_contact_form'),
    
    # Logged-in Users List API
    path('users/logged-in/', list_logged_in_users, name='list_logged_in_users'),
    
    # Login Settings Management APIs
    path('login-settings/set/', set_login_settings, name='set_login_settings'),
    path('login-settings/get/', get_login_settings, name='get_login_settings'),

    ## INUSE by StateAdmin
    path('update_vehicle_owner_expiry/', update_vehicle_owner_expiry, name='update_vehicle_owner_expiry'),
    
    # Central Dashboard APIs for Vehicle Monitoring
    ## INUSE by StateAdmin, SOSAdmin
    path('dashboard/vehicle-monitoring/', vehicle_monitoring_dashboard, name='vehicle_monitoring_dashboard'),
    path('dashboard/filter-options/', get_dashboard_filter_options, name='get_dashboard_filter_options'),
    ## INUSE by StateAdmin, SOSAdmin
    path('dashboard/areawise-device-count/', get_areawise_device_tag_count, name='get_areawise_device_tag_count'),
    path('dashboard/vehicle-locations/', get_latest_vehicle_locations, name='get_latest_vehicle_locations'),
    
    ## INUSE by StateAdmin, SOSAdmin
    path('dashboard_SOS/areawise-device-count/', get_areawise_device_tag_count, name='get_areawise_device_tag_count'),
    path('dashboard_SOS/vehicle-locations/', get_latest_vehicle_locations, name='get_latest_vehicle_locations'),
    
    ## INUSE by StateAdmin, SOSAdmin
    path('dashboard_ERSS/areawise-device-count/', get_areawise_device_tag_count, name='get_areawise_device_tag_count'),
    path('dashboard_ERSS/vehicle-locations/', get_latest_vehicle_locations, name='get_latest_vehicle_locations'),
    
    ## INUSE by StateAdmin, SOSAdmin
    path('dashboard/erss-summary/', erss_dashboard_summary, name='erss_dashboard_summary'),
    ## INUSE by StateAdmin, SOSAdmin
    path('dashboard/sos-analysis/', sos_analysis_dashboard, name='sos_analysis_dashboard'),
    ## INUSE by StateAdmin, SOSAdmin
    path('dashboard/sos-monitoring/', sos_monitoring_dashboard, name='sos_monitoring_dashboard'),

    # IMEI Comparison Tool (public)
    path('imei-comparison/', imei_comparison_page, name='imei_comparison_page'),
    path('imei-comparison/data/', imei_comparison_data, name='imei_comparison_data'),

    # DEV-ONLY endpoints (return 403 in production when DEBUG=False)
    path('dev/token/', dev_get_token, name='dev_get_token'),
    path('dev/users/', dev_list_users, name='dev_list_users'),
    path(
        'dev/technical-onboarding/force-pass-test/',
        dev_force_pass_test,
        name='dev_force_pass_test'
    ),

    # Complaint Management
    ## INUSE by Manufacturer, SOSAdmin
    ## PUBLIC
    path('complaint/create/', create_ticket, name='complaint_create'),
    ## INUSE by Manufacturer, SOSAdmin
    path('complaint/list/', list_tickets, name='complaint_list'),
    ## INUSE by SOSAdmin
    path('complaint/device-imei/', device_imei_lookup, name='complaint_device_imei_lookup'),
    path('complaint/track/<str:ticket_ref>/', public_track_ticket, name='complaint_public_track'),
    ## INUSE by Manufacturer, SOSAdmin
    path('complaint/<int:pk>/', ticket_detail, name='complaint_detail'),
    ## INUSE by SOSAdmin
    path('complaint/<int:pk>/update-status/', update_ticket_status, name='complaint_update_status'),
    path('complaint/<int:pk>/escalate/', escalate_ticket, name='complaint_escalate'),
    ## INUSE by SOSAdmin
    path('complaint/<int:pk>/final-report/', submit_final_report, name='complaint_final_report'),
    ## INUSE by SOSAdmin
    path('complaint/<int:pk>/comment/', add_comment, name='complaint_add_comment'),
    ## INUSE by Manufacturer, SOSAdmin
    path('complaint/<int:pk>/activity/', ticket_activity_log, name='complaint_activity_log'),

    # Whitelist Request Management
    ## INUSE by Manufacturer, Dealer, M2MProvider
    path('whitelist/request/create/', create_whitelist_request, name='whitelist_request_create'),
    ## INUSE by Manufacturer, Dealer, M2MProvider
    path('whitelist/request/list/', list_whitelist_requests, name='whitelist_request_list'),
    path('whitelist/request/esim/all/', esim_list_whitelist_requests, name='whitelist_esim_list'),
    ## INUSE by Manufacturer, Dealer, M2MProvider
    path('whitelist/request/<int:pk>/approve/', approve_whitelist_request, name='whitelist_request_approve'),
    ## INUSE by Manufacturer, Dealer, M2MProvider
    path('whitelist/request/<int:pk>/deny/', deny_whitelist_request, name='whitelist_request_deny'),
    ## INUSE by Manufacturer, Dealer, StateAdmin, M2MProvider
    path('whitelist/active/list/', list_active_whitelist, name='whitelist_active_list'),

    # Device Dashboard, KYC, and Detail
    ## INUSE by Manufacturer, Dealer, StateAdmin, M2MProvider
    path('whitelist/device/dashboard/', device_dashboard, name='whitelist_device_dashboard'),
    ## INUSE by Manufacturer, Dealer, StateAdmin
    path('whitelist/device/<int:pk>/detail/', device_detail, name='whitelist_device_detail'),
    path('whitelist/device/<int:pk>/kyc/update/', update_device_kyc, name='whitelist_device_kyc_update'),

    # Activation command reply (public – called by SMS gateway)
    path('device/activation-reply/', receive_activation_command_reply, name='device_activation_reply'),
    ## INUSE by Dealer
    path('device/send-activation-command/', send_activation_command, name='send_activation_command'),
    ## INUSE by Dealer
    path('device/activation-status/', get_activation_status, name='get_activation_status'),
    ## INUSE by Dealer
    path('device/pending-activations/', list_pending_activations, name='list_pending_activations'),

    # Alert Statistics Dashboard
    path('alert-stats/types/', alert_stats_type_options, name='alert_stats_type_options'),
    ## INUSE by StateAdmin
    path('alert-stats/summary/', alert_stats_summary, name='alert_stats_summary'),
    path('alert-stats/dashboard/', alert_stats_dashboard, name='alert_stats_dashboard'),

    # Device Inspector: lookup, logs, command console
    path('device-inspector/lookup/', device_inspector_lookup, name='device_inspector_lookup'),
    path('device-inspector/logs/', device_inspector_logs, name='device_inspector_logs'),
    path('device-inspector/command/send/', device_inspector_send_command, name='device_inspector_send_command'),
    path('device-inspector/command/history/', device_inspector_command_history, name='device_inspector_command_history'),
    path('device-inspector/dashboard/', device_inspector_dashboard, name='device_inspector_dashboard'),

    # Server Health (superadmin only)
    path('server-health/summary/', server_health_summary, name='server_health_summary'),
    path('server-health/dashboard/', server_health_dashboard, name='server_health_dashboard'),

    # Device Data Health: last packet per category, validated against a protocol format
    ## INUSE by Manufacturer, Dealer, StateAdmin
    ## PUBLIC
    path('device-data-health/formats/', device_data_health_format_options, name='device_data_health_format_options'),
    ## INUSE by Manufacturer, Dealer, StateAdmin
    path('device-data-health/lookup/', device_data_health_lookup, name='device_data_health_lookup'),
    path('device-data-health/dashboard/', device_data_health_dashboard, name='device_data_health_dashboard'),
]



 

urlpatterns += staticfiles_urlpatterns()

# Public firmware download — no auth required
# GET /api/fota/SKTN/<devicemodel_id>/<filename>
urlpatterns += [
    path('fota/SKTN/<path:filepath>', serve_firmware_file, name='serve_firmware_file'),
]













urlpatterns += [

    # =========================
    # School Onboarding
    # =========================


    path("schools/apply/", SchoolApplicationSubmitAPIView.as_view(), name="school-apply"),
    path("state-admin/schools/", StateAdminSchoolApplicationListAPIView.as_view(), name="state-admin-school-list"),
    path("state-admin/schools/<int:pk>/", StateAdminSchoolApplicationDetailAPIView.as_view(), name="state-admin-school-detail"),
    path("state-admin/schools/<int:pk>/decision/", StateAdminSchoolApplicationDecisionAPIView.as_view(), name="state-admin-school-decision"),
    # path("state-admin/schools/<int:pk>/send-setup-link/", StateAdminSendSetupLinkAPIView.as_view(), name="state-admin-school-send-setup-link"),
    path("state-admin/active-schools/", StateAdminSchoolListAPIView.as_view(), name="state-admin-active-schools"),
   
    # ==========================================
    # State Admin – Bus Tagging Decision (NEW)
    # ==========================================

    path("state-admin/bus-tags/<int:tag_id>/decision/", BusTagDecisionAPIView.as_view(), name="bus-tag-decision"),

    # =========================
    # Student CRUD (Admin)
    # =========================

    path("admin/students/", StudentListCreateAPIView.as_view(), name="admin-student-list-create"),
    path("admin/students/<int:student_id>/", StudentDetailAPIView.as_view(), name="admin-student-detail"),
   
    path("admin/students/<int:student_id>/update/", StudentUpdateAPIView.as_view()),
    path("admin/students/<int:student_id>/delete/", StudentDeleteAPIView.as_view()),

    # =========================
    # Parent CRUD (Admin)
    # =========================

    path("admin/parents/", ParentListCreateAPIView.as_view(), name="admin-parent-list-create"),
    path("admin/parents/<int:pk>/", ParentDetailAPIView.as_view(), name="admin-parent-detail"),
    
    path("admin/parents/<int:pk>/update/", ParentUpdateAPIView.as_view()),
    path("admin/parents/<int:pk>/delete/", ParentDeleteAPIView.as_view()),

    # =========================
    # Parent Student Link (Admin)
    # =========================

    path("admin/parents/<int:parent_id>/students/", ParentStudentLinkAPIView.as_view(), name="admin-parent-student-link"),
    path("admin/parents/students/", AdminParentStudentMappingAPIView.as_view(), name="admin-parent-student-mapping"),
    path("admin/parents/<int:parent_id>/students/view/", AdminParentStudentsAPIView.as_view(), name="admin-parent-wise-students"),
    
    path("admin/parents/<int:parent_id>/students/link/", ParentStudentLinkAPIView.as_view()),
    path("admin/parents/<int:parent_id>/students/unlink/", ParentStudentUnlinkAPIView.as_view()),


    # =========================
    # Parent APIs
    # =========================

    path("parents/<int:parent_id>/students/", ParentStudentsAPIView.as_view(), name="parent-students"),
    path("parents/me/drop-locations/", ParentDropLocationsAPIView.as_view(), name="parent-drop-locations"),
    path("parents/me/", ParentMeAPIView.as_view(), name="parent-me"),
    path("parents/me/students/", ParentMyStudentsAPIView.as_view(), name="parent-my-students"),
    path("parents/tracking/", ParentBusTrackingAPIView.as_view(), name="parent-tracking"),
    # path("parents/alerts/", ParentAlertsAPIView.as_view(), name="parent-alerts"),
    path("parents/students/<int:student_id>/attendance/", ParentStudentAttendanceAPIView.as_view(), name="parent-student-attendance"),
    path("parents/trips/active/", ParentActiveTripAPIView.as_view(), name="parent-active-trip"),
    path("parents/trip/history/",ParentTripHistoryAPIView.as_view(), name="parent-trip-history"),
    
    # =========================
    # Alert Capture
    # =========================

    path("alerts/<str:alert_type>/", CaptureBusAlertAPIView.as_view(), name="capture-alert"),

    # =========================
    # Student Bus Allocation
    # =========================

    path("students/<int:student_id>/bus-allocation/", StudentBusAllocationCreateAPIView.as_view(), name="student-bus-allocation"),
    path("admin/bus-allocations/", StudentBusAllocationListAPIView.as_view(), name="student-bus-allocation-list"),

    # =========================
    # School Admin – Master Data
    # =========================


    path("admin/routes/", RouteListCreateAPIView.as_view(), name="route-list-create"),
    path("admin/routes/<int:pk>/", RouteDetailAPIView.as_view(), name="route-detail"),
    
    path("admin/routes/<int:pk>/update/", RouteUpdateAPIView.as_view()),
    path("admin/routes/<int:pk>/delete/", RouteDeleteAPIView.as_view()),
    

    path("admin/bus-stops/", BusStopListCreateAPIView.as_view(), name="bus-stop-list-create"),
    path("admin/bus-stops/<int:pk>/", BusStopDetailAPIView.as_view(), name="bus-stop-detail"),
    
    path("admin/bus-stops/<int:pk>/update/", BusStopUpdateAPIView.as_view()),
    path("admin/bus-stops/<int:pk>/delete/", BusStopDeleteAPIView.as_view()),
    
    path("admin/routes/<int:route_id>/stops/add/", RouteCreateAndAddStopAPIView.as_view(), name="route-add-stop"),
    path("admin/routes/<int:route_id>/stops/<int:stop_id>/remove/", RouteRemoveStopAPIView.as_view(), name="route-remove-stop"),

    path("admin/holidays/", SchoolHolidayListCreateAPIView.as_view(), name="holiday-list-create"),
    path("admin/holidays/<int:pk>/", SchoolHolidayDetailAPIView.as_view(), name="holiday-detail"),
    
    path("admin/holidays/<int:pk>/update/", SchoolHolidayUpdateAPIView.as_view()),
    path("admin/holidays/<int:pk>/delete/", SchoolHolidayDeleteAPIView.as_view()),

    # =========================
    # Bus Documents
    # =========================

    path("admin/buses/<int:bus_id>/documents/", SchoolBusDocumentUploadAPIView.as_view(), name="bus-document-upload"),
    path("admin/buses/<int:bus_id>/documents/list/", SchoolBusDocumentListAPIView.as_view(), name="bus-document-list"),
    path("admin/bus-documents/<int:document_id>/download/", SchoolBusDocumentDownloadAPIView.as_view(), name="bus-document-download"),
    path("admin/bus-documents/<int:document_id>/delete/", SchoolBusDocumentDeleteAPIView.as_view(), name="bus-document-delete"),

    # =================================
    # Trips & Attendance & Reports
    # =================================

    path("admin/trips/", SchoolBusTripListCreateAPIView.as_view(), name="school-trip-list-create"),
    path("admin/trips/active/", ActiveTripAPIView.as_view(), name="active-trip"),
    path("admin/trips/validate-holidays/", HolidayTripValidationAPIView.as_view(), name="holiday-trip-validation"),
    path("admin/trips/<int:trip_id>/attendance/init/", TripAttendanceInitAPIView.as_view(), name="trip-attendance-init"),
    path("admin/trips/<int:trip_id>/attendance/pickup/", StudentPickupAPIView.as_view(), name="student-pickup"),
    path("admin/trips/<int:trip_id>/attendance/drop/", StudentDropAPIView.as_view(), name="student-drop"),
    path("admin/trips/<int:trip_id>/attendance/raw/", TripRawAttendanceAPIView.as_view(), name="trip-raw-attendance"),

    # =========================
    # Reports
    # =========================

    path("admin/reports/unplanned-trips/", UnplannedTripListAPIView.as_view(), name="unplanned-trip-list"),
    path("admin/reports/unplanned-trips/summary/", UnplannedTripReportAPIView.as_view(), name="unplanned-trip-report"),
    path("admin/reports/trips/<int:trip_id>/attendance/", TripAttendanceReportAPIView.as_view(), name="trip-attendance-report"),
    path("admin/reports/trips/<int:trip_id>/student-status/", TripStudentStatusAPIView.as_view(), name="trip-student-status"),
    path("admin/reports/trips/<int:trip_id>/stops/<int:stop_id>/students/", TripStopStudentsAPIView.as_view(), name="trip-stop-students"),
    path("admin/reports/students/<int:student_id>/attendance/", StudentAttendanceReportAPIView.as_view(), name="student-attendance-report"),
    path("admin/reports/routes/<int:route_id>/attendance/", RouteAttendanceReportAPIView.as_view(), name="route-attendance-report"),
    path("admin/reports/stops/<int:stop_id>/attendance/", StopAttendanceReportAPIView.as_view(), name="stop-attendance-report"),

    # =========================
    # Alerts
    # =========================

    # path("admin/alerts/", AdminAlertsAPIView.as_view(), name="admin-alerts"),

    # =============================================
    # School Bus Tagging — 4-Step Workflow (NEW)
    # =============================================

    # Step 1 — Initiate tagging request (select vehicle reg no)
    path("admin/buses/tag/initiate/", BusTagInitiateAPIView.as_view(), name="bus-tag-initiate"),

    # Step 2 — OTP: resend + verify
    path("admin/buses/tag/<int:tag_id>/send-otp/", BusTagSendOTPAPIView.as_view(), name="bus-tag-send-otp"),
    path("admin/buses/tag/<int:tag_id>/verify-otp/", BusTagVerifyOTPAPIView.as_view(), name="bus-tag-verify-otp"),

    # Step 3 — Upload documents (one per call) + final submit (submit=true)
    path("admin/buses/tag/<int:tag_id>/documents/", BusTagSubmitDocumentsAPIView.as_view(), name="bus-tag-documents"),

    # Tagging history table — school admin sees own school, state admin sees all
    path("admin/buses/tag/history/", BusTagHistoryAPIView.as_view(), name="bus-tag-history"),

    # NOTE: order matters — specific paths before parameterised paths
    # "tag/initiate/" and "tag/history/" must come before "<int:bus_id>/untag/"
    # and "available/" must come before "<int:bus_id>/" — Django matches top-down

    # Approved buses list for this school
    path("admin/buses/", SchoolBusTagListAPIView.as_view(), name="school-bus-list"),

    # Available (untagged) buses — powers Step 1 dropdown
    path("admin/buses/available/", AvailableVLTDVehiclesAPIView.as_view(), name="available-vltd-buses"),

    # Untag a bus
    path("admin/buses/<int:bus_id>/untag/", SchoolBusUnTagAPIView.as_view(), name="school-bus-untag"),

    # =========================
    # Bus – Route Assignment
    # =========================

    path("admin/routes/assign-bus/", AssignBusToRouteAPIView.as_view(), name="assign-bus-to-route"),
    path("admin/routes/<int:bus_id>/reassign/", ReassignBusToRouteAPIView.as_view(), name="reassign-bus-route"),
    path("admin/routes/<int:bus_id>/remove-bus/", RemoveBusFromRouteAPIView.as_view(), name="remove-bus-from-route"),
    path("admin/routes/<int:route_id>/buses/", RouteBusesAPIView.as_view(), name="route-buses"),
    path("admin/routes/assignments/", RouteBusAssignmentListAPIView.as_view(), name="route-bus-assignment-list"),

    # =========================
    # Dev Utility
    # =========================

    path("dev/create-user/", CreateTestUserAPIView.as_view(), name="dev-create-user"),

    # =========================
    # Dashboard
    # =========================

    path("dashboard/", DashboardAPIView.as_view(), name="dashboard"),
    path("school-distribution/", SchoolWiseDistributionAPIView.as_view(), name="school-distribution"),
    path("active-trips/", ActiveTripMonitorAPIView.as_view(), name="active-trips"),
    path("bus-operational-status/", BusOperationalStatusAPIView.as_view(), name="bus-operational-status"),
    path("live-alerts/", LiveAlertsFeedAPIView.as_view(), name="live-alerts"),
    
    path("parents/alerts/geofence/", ParentGeofenceAlertsAPIView.as_view(), name="parent-geofence-alerts"),
    
    path("parents/students/live-location/", ParentStudentLiveLocationAPIView.as_view(), name="parent-student-live-location"),
    
    
    # =============================================
    # School Application Documents
    # =============================================
 
    # State admin — any school by pk
    path("state-admin/schools/<int:pk>/documents/", SchoolDocumentListAPIView.as_view(), name="state-admin-school-document-list"),
    path("state-admin/schools/<int:pk>/documents/<str:doc_type>/download/", SchoolDocumentDownloadAPIView.as_view(), name="state-admin-school-document-download"),
 
    # School admin — own school only (no pk in URL)
    path("admin/school/documents/", SchoolDocumentListAPIView.as_view(), name="school-admin-document-list"),
    path("admin/school/documents/<str:doc_type>/download/", SchoolDocumentDownloadAPIView.as_view(), name="school-admin-document-download"),
    
    path("admin/school/overview/", SchoolOverviewAPIView.as_view(), name="school-fleet-overview"),
    
    # =====================================================
    # Permit Enforcement
    # =====================================================
    
    path('enforcement/permit-conditions/', PermitConditionCreateAPIView.as_view(), name='permit-condition-create'),
    path('enforcement/permit-conditions/list/', PermitConditionListAPIView.as_view(), name='permit-condition-list'),
    path('enforcement/permit-conditions/<int:pk>/update/', PermitConditionUpdateAPIView.as_view(), name='permit-condition-update'),
    path('enforcement/violations/', ViolationReportListAPIView.as_view(), name='violation-list'),
    
    # =====================================================
    # Passenger Information System — Admin APIs
    # =====================================================

    # Bus Stops
    ## INUSE by PIS
    path('pis/bus-stops/', PISBusStopListCreateAPIView.as_view(), name='pis-bus-stop-list-create'),
    ## INUSE by PIS
    path('pis/bus-stops/<int:pk>/', PISBusStopDetailAPIView.as_view(), name='pis-bus-stop-detail'),
    ## INUSE by PIS
    path('pis/bus-stops/<int:pk>/update/', PISBusStopUpdateAPIView.as_view(), name='pis-bus-stop-update'),
    ## INUSE by PIS
    path('pis/bus-stops/<int:pk>/toggle/', PISBusStopToggleAPIView.as_view(), name='pis-bus-stop-toggle'),

    # Bus Routes
    ## INUSE by PIS, Analytics
    path('pis/routes/', PISBusRouteListCreateAPIView.as_view(), name='pis-route-list-create'),
    ## INUSE by PIS
    path('pis/routes/<int:pk>/', PISBusRouteDetailAPIView.as_view(), name='pis-route-detail'),
    ## INUSE by PIS
    path('pis/routes/<int:pk>/update/', PISBusRouteUpdateAPIView.as_view(), name='pis-route-update'),
    ## INUSE by PIS
    path('pis/routes/<int:pk>/toggle/', PISBusRouteToggleAPIView.as_view(), name='pis-route-toggle'),

    # Bus Schedules
    ## INUSE by PIS
    path('pis/schedules/', PISBusScheduleListCreateAPIView.as_view(), name='pis-schedule-list-create'),
    path('pis/schedules/<int:pk>/', PISBusScheduleDetailAPIView.as_view(), name='pis-schedule-detail'),
    ## INUSE by PIS
    path('pis/schedules/<int:pk>/update-status/', PISBusScheduleUpdateStatusAPIView.as_view(), name='pis-schedule-update-status'),

    # Available buses dropdown
    ## INUSE by PIS
    path('pis/available-buses/', PISAvailableBusListAPIView.as_view(), name='pis-available-buses'),
    
    path("admin/reports/unplanned-movement/", SchoolBusUnplannedMovementAPIView.as_view(), name="unplanned-movement-report"),
    
    path("admin/school/alerts/", SchoolBusAlertsListAPIView.as_view(), name="school-bus-alerts-list"),

    # =====================================================
    # Passenger Information System — Public APIs (No Auth)
    # =====================================================

    path('pis/public/bus-stops/', PISPublicBusStopListAPIView.as_view(), name='pis-public-bus-stops'),
    path('pis/public/routes/', PISPublicBusRouteListAPIView.as_view(), name='pis-public-routes'),
    path('pis/public/schedules/', PISPublicScheduleStatusAPIView.as_view(), name='pis-public-schedules'),
    
    
    
    # ------------------------------------------------------------------
    # API 1 — School Bus Module: all routes (across all schools)
    # ------------------------------------------------------------------
    ## INUSE by Manufacturer, StateAdmin
    path('map/school-bus/routes/',MapSchoolBusRoutesAPIView.as_view(),name='map-school-bus-routes',),
 
    # ------------------------------------------------------------------
    # API 2 — PIS: all public bus routes with stops
    # ------------------------------------------------------------------
    path('map/pis/routes/',MapPISRoutesAPIView.as_view(),name='map-pis-routes',),
 
    # ------------------------------------------------------------------
    # API 3 — School Bus live locations (map pins)
    # ------------------------------------------------------------------
    path('map/school-bus/buses/',MapSchoolBusLocationsAPIView.as_view(),name='map-school-bus-locations',),
 
    # ------------------------------------------------------------------
    # API 4 — PIS (Public) Bus live locations (map pins)
    # ------------------------------------------------------------------
    path('map/pis/buses/',MapPISBusLocationsAPIView.as_view(),name='map-pis-bus-locations',),
 
    # ------------------------------------------------------------------
    # API 5 — PIS Bus Stops (map pins)
    # ------------------------------------------------------------------
    path('map/pis/bus-stops/', MapPISBusStopsAPIView.as_view(), name='map-pis-bus-stops',),
    
    # ----------------------------------------------------------------
    #  4.1 State Transport Analytics Platform 
    # ----------------------------------------------------------------
    
    ## INUSE by Analytics
    path('analytics/trips/', TripAnalyticsAPIView.as_view(), name='analytics-trips'),
    
    ## INUSE by Analytics
    path('analytics/driving-pattern-alerts/', DrivingPatternAlertsAPIView.as_view(),name='analytics-driving-pattern-alerts',),
    
    ## INUSE by Analytics
    path('analytics/vehicle-alert-summary/',VehicleAlertSummaryAPIView.as_view(),name='analytics-vehicle-alert-summary',),
    
    ## INUSE by Analytics
    path('analytics/pis-summary/',PISAnalyticsSummaryAPIView.as_view(),name='analytics-pis-summary',),
    
    ## INUSE by Analytics
    path('analytics/resource-performance/', ResourcePerformanceAPIView.as_view(), name='analytics-resource-performance'),
    
    ## INUSE by Analytics
    path('analytics/operational/', OperationalAnalyticsAPIView.as_view(), name='analytics-operational'),
    
    ## INUSE by Analytics
    path('analytics/comparative-analysis/',ComparativeAnalysisAPIView.as_view(),name='analytics-comparative-analysis',),
    
    
    ## INUSE by Owner, StateAdmin
    path("analytics/alert-heatmap/",AlertHeatmapAPIView.as_view(),name="alert-heatmap",),
    
    
    path("favorites/",FavoriteListCreateAPIView.as_view(),name="favorite-list-create",),

    path("favorites/<uuid:pk>/",FavoriteDetailAPIView.as_view(),name="favorite-detail",),

    path("favorites/<uuid:pk>/update/",FavoriteUpdateAPIView.as_view(),name="favorite-update",),

    path("favorites/<uuid:pk>/delete/",FavoriteDeleteAPIView.as_view(),name="favorite-delete",),

    # path("favorites/bulk-delete/",FavoriteBulkDeleteAPIView.as_view(),name="favorite-bulk-delete",),
    
    ## INUSE by Manufacturer, Dealer, StateAdmin, M2MProvider, SOSAdmin, SOSExecutive
    path('admin/users/login-report/', UserLoginReportAPIView.as_view(), name='user-login-report'),
    
    
    # =====================================================
    # Custom Alert Rules
    # =====================================================
 
    # Metadata — available parameters and operators 
    path('custom-alerts/parameters/', CustomAlertParameterListAPIView.as_view(), name='custom-alert-parameters'),
 
    # Rule CRUD
    path('custom-alerts/rules/', CustomAlertRuleListCreateAPIView.as_view(), name='custom-alert-rule-list-create'),
    path('custom-alerts/rules/<int:pk>/', CustomAlertRuleDetailAPIView.as_view(), name='custom-alert-rule-detail'),
    path('custom-alerts/rules/<int:pk>/update/', CustomAlertRuleUpdateAPIView.as_view(), name='custom-alert-rule-update'),
    path('custom-alerts/rules/<int:pk>/delete/', CustomAlertRuleDeleteAPIView.as_view(), name='custom-alert-rule-delete'),
 
    # Fired alert logs
    path('custom-alerts/logs/', CustomAlertLogListAPIView.as_view(), name='custom-alert-log-list'),
    
    path('pis/public/bus-stops/near/', PISPublicBusStopsNearbyAPIView.as_view(), name='pis-public-bus-stops-near'),
    
    path('pis/public/buses/search-between-stops/', PISPublicBusesBetweenStopsAPIView.as_view(), name='pis-public-buses-between-stops'),
    
    path('pis/public/buses/live-location/', PISPublicBusLiveLocationByRegNoAPIView.as_view(), name='pis-public-bus-live-location'),
    
    ## INUSE by M2MProvider
    path('esim-provider/m2m-config/', m2m_config_create_update, name='m2m_config_create_update'),
    path('esim-provider/m2m-config/test/', m2m_config_test, name='m2m_config_test'),
    
    
    ## INUSE by Dealer
    path('device-tagging/step1/', device_tagging_step1_create, name='device-tagging-step1'),
    ## INUSE by Dealer
    path('device-tagging/step2/', device_tagging_step2_esim,   name='device-tagging-step2'),
    
    ## INUSE by Dealer
    path('device-tagging/step3/resend-otp/', device_tagging_step3_resend_otp, name='device-tagging-step3-resend'),
    ## INUSE by Dealer
    path('device-tagging/step3/verify-otp/', device_tagging_step3_verify_otp, name='device-tagging-step3-verify'),
    
    ## INUSE by Dealer
    path('device-tagging/step4/', device_tagging_step4_packet_check, name='device-tagging-step4'),
    
    ## INUSE by Dealer
    path('device-tagging/step5/send-otp/',   device_tagging_step5_send_owner_otp,   name='device-tagging-step5-send'),
    ## INUSE by Dealer
    path('device-tagging/step5/verify-otp/', device_tagging_step5_verify_owner_otp, name='device-tagging-step5-verify'),
    
    
    ## INUSE by Dealer
    path('device-tagging/my-entries/',      device_tagging_my_entries,      name='device-tagging-my-entries'),
    ## INUSE by Dealer
    path('device-tagging/my-manufacturer/', device_tagging_my_manufacturer, name='device-tagging-my-manufacturer'),
    
    ## INUSE by Dealer
    path('device-tagging/certificate/',      device_tagging_certificate,      name='device-tagging-certificate'),
    ## INUSE by Dealer
    path('device-tagging/certificate-list/', device_tagging_certificate_list, name='device-tagging-certificate-list'),
       
    # device model IP / whitelist configuration
    path('devicemodel/ip-config/superadmin/list/',superadmin_device_model_ip_config_list,name='superadmin_device_model_ip_config_list'),
    path('devicemodel/ip-config/esim-provider/list/',esim_provider_device_model_ip_config_list,name='esim_provider_device_model_ip_config_list'),
    
    path('sms-gateway/health/', sms_gateway_health_status, name='sms-gateway-health'),
    
    ## INUSE by M2MProvider
    path('esim-provider/ip-range/add/',  esim_provider_ip_range_add,  name='esim-provider-ip-range-add'),
    ## INUSE by M2MProvider
    path('esim-provider/ip-range/list/', esim_provider_ip_range_list, name='esim-provider-ip-range-list'),
    
    ## INUSE by M2MProvider
    path('esim-provider/ip-range/update/', esim_provider_ip_range_update, name='esim-provider-ip-range-update'),
    ## INUSE by M2MProvider
    path('esim-provider/ip-range/delete/', esim_provider_ip_range_delete, name='esim-provider-ip-range-delete'),
    
    path('m2m/ip-scan/', m2m_provider_ip_scan, name='m2m-ip-scan'),
]
