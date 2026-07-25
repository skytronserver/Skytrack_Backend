"""
rbac_api_map.py
---------------
Maps every Django URL *name* (from urls.py) to the list of RBAC module codes
that grant access to it.

Logic: a user may call the endpoint if their role has the **view** permission
on ANY one module in the list.  This mirrors the frontend rule – multiple
sidebar items can share the same underlying API.

Source: RBAC_MODULE_ACCESS_REFERENCE.md (sections 1-13 cross-referenced with
        the Route→API appendix A.1-A.19).

How to maintain:
  • When you add a new URL in urls.py, add an entry here.
  • When you add a new module to the reference doc, update the lists below.
  • URL names that are intentionally public (login, OTP, etc.) should NOT
    appear here; they are allowed through automatically.
"""

# fmt: off
API_MODULE_MAP: dict[str, list[str]] = {

    # ── A.1  Dashboards & Central ─────────────────────────────────────────────
    "homepage":                   ["dashboard"],
    "homepage_stateAdmin":        ["dashboard"],
    "homepage_DTO":               ["dashboard"],
    "homepage_VehicleOwner":      ["dashboard"],
    "homepage_Dealer":            ["dashboard"],
    "homepage_Manufacturer":      ["dashboard"],
    "homepage_esimProvider":      ["dashboard"],
    "vehicle_alert_statistics":   ["dashboard"],

    # SOS reports appear on both /dashboard and /superadmin-dashboard
    "SOS_adminreport":            ["dashboard", "dashboard_central", "report_sos"],
    "SOS_TLreport":               ["dashboard", "dashboard_central", "sos_call_list"],
    "SOS_EXreport":               ["dashboard"],
    "SOS_detailed_report":        ["report_sos"],

    # MORTH dashboard
    "global_counts_summary":      ["dashboard_morth"],

    # Central / superadmin dashboard sub-APIs
    "vehicle_monitoring_dashboard":       ["dashboard_central"],
    "get_dashboard_filter_options":       ["dashboard_central"],
    "get_areawise_device_tag_count":      ["dashboard_central"],
    "get_latest_vehicle_locations":       ["dashboard_central"],
    "erss_dashboard_summary":             ["dashboard_central"],
    "sos_monitoring_dashboard":           ["dashboard_central"],
    "sos_analysis_dashboard":             ["dashboard_central"],
    "vehicle_status_metrics":             ["dashboard_central"],
    "ambulance_fleet_metrics":            ["dashboard_central"],
    "ambulance_fleet_metrics222":         ["dashboard_central"],  # legacy alias
    "police_fleet_metrics":               ["dashboard_central"],

    # SOS pending-call list appears on /superadmin-dashboard AND /sos-call-list
    "DEx_getPendingCallList":     ["dashboard_central", "sos_call_list", "report_sos_call_list"],
    "DEx_replyCall":              ["sos_call_list", "report_sos_call_list"],
    "DEx_getCallList":            ["sos_call_list", "emergency_management"],
    "DEx_getLiveCallList":        ["sos_call_list", "emergency_management"],
    "DEx_getPendingCallList":     ["dashboard_central", "sos_call_list", "report_sos_call_list"],
    "DEx_closeCase":              ["sos_call_list", "emergency_management"],
    "DEx_sendMsg":                ["sos_call_list", "emergency_management"],
    "DEx_rcvMsg":                 ["sos_call_list", "emergency_management"],
    "DEx_commentFE":              ["sos_call_list", "emergency_management"],
    "DEx_getCallAllLoc":          ["sos_call_list", "emergency_management"],
    "DEx_broadcastlist":          ["sos_call_list", "emergency_management"],
    "DEx_broadcast":              ["sos_call_list", "emergency_management"],
    "DEx_listBackup":             ["emergency_management"],
    "DEx_acceptBackup":           ["emergency_management"],
    "TLEx_getAllCallList":         ["sos_call_list", "emergency_management"],
    "TLEx_reassign":              ["emergency_management"],

    # ── A.2  School Bus System ────────────────────────────────────────────────
    # (school/api/... endpoints live in a separate microservice and are not
    #  registered in this Django urls.py, so only the shared Django APIs appear)

    # /schoolbus/bus-tracking shares gps_track_data_api
    # (covered below under A.7 Tracking)

    # ── A.3  Test Agency ──────────────────────────────────────────────────────
    "get_testAgency_name_list":          ["ta_create_agency"],
    "create_testAgency":                 ["ta_create_agency"],
    "get_testAgency_list":               ["ta_agency_list"],
    "update_testAgency":                 ["ta_agency_list"],
    "create_testAgencyDetails":          ["ta_create_user"],
    "public_testAgencyDetails_list":     ["ta_user_list"],
    "update_testAgencyDetails":          ["ta_user_list"],
    "get_testAgency_device_models":      ["ta_view_models"],

    # ── A.4  User / Account Creation ──────────────────────────────────────────
    "create_StateAdmin":          ["cn_state_admin"],
    "update_StateAdmin":          ["cn_state_admin", "report_state_admin"],
    "resend_usercreation_otp":    ["cn_state_admin", "sbs_profile_mgmt"],
    "resend_parent_activation_otp": ["sbs_profile_mgmt"],
    "create_eSimProvider":        ["cn_m2m_provider"],
    "update_eSimProvider":        ["cn_m2m_provider", "m2m_registration"],
    "create_SOSAdmin":            ["cn_sos_admin"],
    "create_superuser":           ["cn_system_admin"],
    "create_DTO_RTO":             ["cn_dto"],
    "update_DTO_RTO":             ["cn_dto"],
    "transfer_DTO_RTO":           ["cn_dto"],
    "getDistrictList":            ["cn_dto", "settings_state_district"],
    "create_dealer":              ["cn_dealer"],
    "update_dealer":              ["cn_dealer", "dealer_management"],
    "create_SOSuser":             ["cn_sos_user"],
    "create_VehicleOwner":        ["cn_vehicle_owner"],
    "update_VehicleOwner":        ["cn_vehicle_owner", "owner_management"],
    "filter_VehicleOwner":        ["cn_vehicle_owner", "report_vehicle_owner", "owner_management"],
    "update_vehicle_owner_expiry": ["report_vehicle_owner", "owner_management"],

    # ── A.5  M2M & Manufacturer Requests ─────────────────────────────────────
    "filter_eSimProvider":        ["m2m_registration", "report_m2m_provider"],
    "filter_manufacturers":       [
        "mfr_vlt_requests", "mfr_ais140_requests",
        "report_manufacturer", "manufacturer_management",
    ],
    "update_manufacturer":        ["mfr_vlt_requests", "mfr_ais140_requests", "manufacturer_management"],
    "approve_manufacturer_tech_onboarding": [
        "tech_onboarding", "tech_onboarding_final",
    ],
    "dealer_check_esim_status":   ["dealer_m2m_status", "m2m_pending", "m2m_rejected", "m2m_accepted"],
    "esimActivateReq-create":     ["dealer_request_m2m"],
    "esimActivateReq-filter":     ["esim_management"],
    "esimActivateReq-update":     ["esim_management"],

    # ── A.6  Technical Onboarding ─────────────────────────────────────────────
    "superadmin_list_device_model_technical_onboarding_requests": [
        "tech_onboarding", "tech_onboarding_final",
    ],
    "filter_TechOnboardmanufacturers": ["tech_onboarding", "tech_onboarding_final"],
    "superadmin_mark_technical_onboarding_ongoing_evaluation": [
        "tech_onboarding", "tech_onboarding_final",
    ],
    "superadmin_finalize_technical_onboarding_request": [
        "tech_onboarding", "tech_onboarding_final",
    ],
    "devicemodel-filter":                    ["mfr_onboarding_new", "device_management"],
    "manufacturer_list_own_device_model_technical_onboarding_requests": [
        "mfr_onboarding_new", "mfr_onboarding_list",
    ],
    "create_device_model_technical_onboarding_request": ["mfr_onboarding_new"],

    # ── A.7  Tracking & Playback ──────────────────────────────────────────────
    # gps_track_data_api is called from many routes / many modules
    "gps_track_data_api": [
        "dashboard_central", "sbs_bus_tracking",
        "live_tracking", "gps_clustering",
        "gps_tracking", "gps_history", "history_playback",
    ],
    "gps_track_data_api_pub":     ["live_tracking", "gps_tracking"],  # public variant

    "gps_track_lite_api":         ["live_tracking", "gps_tracking", "gps_clustering"],
    "gps_track_lite_options_api": ["live_tracking", "gps_tracking", "gps_clustering"],
    "gps_cluster_api":            ["live_tracking", "gps_clustering"],
    "gps_grid_cluster_api":       ["live_tracking", "gps_clustering"],

    "get_live_vehicle_no":        ["live_tracking", "history_playback"],
    "get_latest_emuser_locations":["live_tracking", "gps_history"],
    "cell_location_average":      ["live_tracking", "gps_history"],
    "geocode_poi":                ["live_tracking", "gps_history", "poi_viewer", "poi_management"],
    "reverse_geocode_poi":        ["live_tracking", "gps_history", "poi_viewer"],

    "list_poi_types": [
        "live_tracking", "gps_tracking", "gps_history", "history_playback",
        "poi_viewer", "poi_management",
    ],
    "list_pois": [
        "live_tracking", "gps_tracking", "gps_history", "history_playback",
        "poi_viewer", "poi_management", "report_poi",
    ],

    "gps_history_map_data":       ["gps_history", "history_playback"],

    "tag_ownerlist":              ["trip_viewer", "vehicle_tagging"],
    "get_trip":                   ["trip_monitor", "trip_management"],
    "create_trip":                ["trip_management"],
    "update_trip":                ["trip_management"],
    "end_trip":                   ["trip_management"],
    "cancel_trip":                ["trip_management"],

    "getRoute":                   ["trip_management", "route_management", "route_fixing"],
    "saveRoute":                  ["trip_management", "route_management", "route_fixing"],
    "delRoute":                   ["trip_management", "route_management", "route_fixing"],
    "get_routePath":              ["route_fixing", "poi_viewer"],

    # ── A.8  VLTD Approval ────────────────────────────────────────────────────
    "device_model_awaiting_state_approval": ["vltd_pending_model"],
    "device_send_state_admin_otp":          ["vltd_pending_model"],
    "device_verify_state_admin_otp":        ["vltd_pending_model"],
    "device_create_manufacturer_otp_verify": ["vltd_pending_model", "dm_create_model"],
    "COPAwaitingStateApproval":             ["vltd_pending_cop"],
    "COPSendStateAdminOtp":                 ["vltd_pending_cop"],
    "COPVerifyStateAdminOtp":               ["vltd_pending_cop"],
    "COPManufacturerOtpVerify":             ["vltd_pending_cop", "dm_tac_cop"],
    "state_admin_approved_models_report":   ["vltd_approved_models"],
    "state_admin_approved_cops_report":     ["vltd_approved_cops"],
    "state_admin_combined_approval_report": ["vltd_approved_models", "vltd_approved_cops"],
    "devicemodel-list":                     ["vltd_pending_model", "vltd_approved_models", "dm_create_model"],

    # ── A.9  Whitelist & KYC ─────────────────────────────────────────────────
    "whitelist_request_list":     ["wkyc_requests"],
    "whitelist_esim_list":        ["wkyc_requests"],
    "whitelist_active_list":      ["wkyc_requests"],
    "whitelist_request_create":   ["wkyc_requests"],
    "whitelist_request_approve":  ["wkyc_requests"],
    "whitelist_request_deny":     ["wkyc_requests"],
    "whitelist_device_dashboard": ["wkyc_device_dashboard"],
    "whitelist_device_detail":    ["wkyc_device_dashboard"],
    "whitelist_device_kyc_update":["wkyc_device_dashboard"],

    # ── A.10 POI ──────────────────────────────────────────────────────────────
    "create_poi":  ["poi_viewer"],
    "update_poi":  ["poi_viewer"],
    "delete_poi":  ["poi_viewer"],
    # list_pois / list_poi_types already covered under A.7

    # ── A.11 Reports ──────────────────────────────────────────────────────────
    "list_notice":                ["report_notices", "notice_management"],
    "delete_notice":              ["report_notices", "notice_management"],
    "get_list":                   ["report_users", "user_management"],
    "user_dactivate":             ["report_users"],
    "user_activate":              ["report_users"],
    "filter_StateAdmin":          ["report_state_admin"],
    "filter_SOSuser":             ["report_sos_admin"],
    "filter_DTO_RTO":             ["report_dto"],
    "filter_SOS_admin":           ["report_sos_users"],
    "filter_dealer":              ["report_dealers", "dealer_management", "cn_dealer", "ds_assign"],
    "combined_device_stock":      ["report_stock"],
    "SellListAvailableDeviceStock": [
        "device_stock", "dealer_untagged", "dealer_tag_device", "report_fitment",
    ],
    "deviceStockFilter":          ["ds_individual", "dealer_download_cert"],
    "deviceStockUntaggedFilter":  ["ds_individual", "ds_assign"],
    "deviceStockSoftDelete":      ["device_stock", "ds_individual"],
    "unTagDevice2Vehicle":        ["dealer_download_cert"],
    "reTagDevice2Vehicle":        ["dealer_download_cert"],
    "update_temp_tag_registration": ["dealer_download_cert"],
    "StateAdmin_view_all_tagging": ["report_device"],
    "gps_data_log_table":         ["report_gps_log", "report_activation_log", "report_health_packet"],
    "gps_em_data_log_table":      ["report_emergency_data", "report_health_packet"],
    "apilog":                     ["report_event_data"],
    "activated_device_list":      ["report_activated_device"],
    "filter_alert_log":           ["report_alert"],
    "register_incident":          ["report_incident", "emergency_management"],
    "filter_incident":            ["live_tracking", "gps_history", "report_incident"],
    "update_incident":            ["report_incident", "emergency_management"],
    "get_device_health_status":   ["report_device_health"],
    "user_statistics":            ["report_user_stats"],
    "filter_settings_VehicleCategory": [
        "settings_vehicle_type", "report_violation", "settings_permit_cond",
    ],
    "list_alert_logs":            ["alerts", "report_alert"],
    "get_device_tag_alerts":      ["alerts"],
    "get_device_tags":            ["alerts", "report_alert"],
    "get_device_trip_details":    ["trip_viewer", "gps_history"],
    "gps_packet_health_summary":  ["report_health_packet", "report_device_health"],
    "gps_packet_dashboard":       ["report_health_packet", "report_device_health"],
    "gps_imei_continuity_api":    ["report_device_health", "report_activated_device"],

    # ── A.12 Settings ─────────────────────────────────────────────────────────
    "filter_notice":              ["settings_notice"],
    "create_notice":              ["settings_notice", "notice_management"],
    "update_notice":              ["settings_notice", "notice_management"],
    "send_mqtt_command":          ["settings_send_command"],
    "create_settings_VehicleCategory": ["settings_vehicle_type"],
    "list_all_vehicle_category_code":  ["settings_vehicle_category"],
    "create_vehicle_category_code":    ["settings_vehicle_category"],
    "edit_vehicle_category_code":      ["settings_vehicle_category"],
    "list_permit_master":              ["settings_permit_cond"],
    "create_permit_master":            ["settings_permit_cond"],
    "edit_permit_master":              ["settings_permit_cond"],
    "list_all_permit_master":          ["settings_permit_cond"],
    "update_notification_preferences": ["settings_alert_notif"],
    "filter_settings_State":      ["settings_state_district", "sbs_profile_mgmt"],
    "filter_settings_District":   ["settings_state_district", "sbs_profile_mgmt"],
    "create_settings_State":      ["settings_state_district"],
    "create_settings_District":   ["settings_state_district"],
    "filter_settings_hp_freq":    ["settings_ota_firmware"],
    "create_settings_hp_freq":    ["settings_ota_firmware"],
    "filter_ota_settings":        ["settings_ota_firmware"],
    "create_ota_settings":        ["settings_ota_firmware"],
    "update_ota_settings":        ["settings_ota_firmware"],

    # OTA Command Management
    "create_ota_command_definition":       ["ota_command_definition"],
    "update_ota_command_definition":       ["ota_command_definition"],
    "filter_ota_command_definitions":      ["ota_command_definition"],
    "filter_ota_command_history":          ["ota_command_history"],
    "update_ota_command_history":          ["ota_command_history"],
    "send_ota_command":                    ["ota_command_history"],
    "search_devices_for_ota_command":      ["ota_command_history"],
    "get_ota_command_value_suggestions":   ["ota_value_suggestion"],
    "filter_settings_firmware":   ["settings_ota_firmware"],
    "create_settings_firmware":   ["settings_ota_firmware"],
    "list_gps_data_archives":     ["settings_archive_restore"],
    "archive_gps_data_log":       ["settings_archive_restore"],
    "restore_gps_data_log":       ["settings_archive_restore"],
    "filter_settings_ip":         ["settings_ip"],
    "create_settings_ip":         ["settings_ip"],
    "set_login_settings":         ["settings_login"],

    # ── A.13 Passenger Info System ────────────────────────────────────────────
    # (school/api/pis/... is a separate microservice; no entries here)

    # ── A.14 State Transport Analytics ───────────────────────────────────────
    # (school/api/analytics/... is a separate microservice; no entries here)

    # ── A.15 Custom User Module (RBAC) ────────────────────────────────────────
    "rbac_list_roles":            ["cum_custom_roles"],
    "rbac_create_custom_role":    ["cum_custom_roles"],
    "rbac_update_role":           ["cum_custom_roles"],
    "rbac_deactivate_role":       ["cum_custom_roles"],
    "rbac_active_roles":          ["cum_feature_perms", "cum_user_mgmt"],
    "rbac_list_modules":          ["cum_feature_perms"],
    "rbac_get_role_permissions":  ["cum_feature_perms"],
    "rbac_update_role_permissions": ["cum_feature_perms"],
    "rbac_list_users":            ["cum_user_mgmt"],
    "rbac_create_user":           ["cum_user_mgmt"],
    "rbac_update_user":           ["cum_user_mgmt"],
    "rbac_assign_role":           ["cum_user_mgmt"],

    # ── A.16 Complaint Tickets / Helpdesk ─────────────────────────────────────
    "complaint_list":             ["complaint", "ct_my_dashboard", "ct_all_tickets", "ct_escalated"],
    "complaint_device_imei_lookup": ["ct_create"],
    "complaint_create":           ["ct_create"],
    "complaint_detail":           ["complaint", "ct_my_dashboard", "ct_all_tickets", "ct_escalated"],
    "complaint_update_status":    ["complaint"],
    "complaint_escalate":         ["complaint"],
    "complaint_final_report":     ["complaint"],
    "complaint_add_comment":      ["complaint", "ct_create"],
    "complaint_activity_log":     ["complaint", "ct_my_dashboard"],

    # ── A.17 Device, Stock & Management ──────────────────────────────────────
    "deviceStockCreate":          ["device_management", "cn_manufacturer"],
    "devicemodel-detail":         ["device_management", "dm_tac_cop"],
    "devicemodel-create":         ["dm_create_model"],
    "COPCreate":                  ["dm_create_model", "dm_tac_cop"],
    "download_static_file":       ["ds_bulk", "ds_assign"],
    "deviceStockCreateBulk":      ["ds_bulk"],
    "StockAssignToDealer":        ["ds_assign"],
    "esim_provider_list":         ["ds_assign", "device_management"],

    # Vehicle tagging
    "TagDevice2Vehicle":          ["dealer_tag_device", "vehicle_tagging"],
    "tag_status":                 ["dealer_tag_device", "vehicle_tagging"],
    "TagAwaitingOwnerApproval":   ["dealer_tag_device", "vehicle_tagging"],
    "TagSendOwnerOtp":            ["dealer_tag_device", "vehicle_tagging"],
    "TagVerifyOwnerOtp":          ["dealer_tag_device", "vehicle_tagging"],
    "TagAwaitingActivateTag":     ["dealer_tag_device", "vehicle_tagging"],
    "TagGetVehicle":              ["dealer_tag_device", "vehicle_tagging"],
    "GetVahanAPIInfo":            ["dealer_tag_device", "vehicle_tagging"],
    "ActivateTag":                ["dealer_tag_device", "vehicle_tagging"],
    "TagAwaitingOwnerApprovalFinal": ["dealer_tag_device", "vehicle_tagging"],
    "TagSendOwnerOtpFinal":       ["dealer_tag_device", "vehicle_tagging"],
    "TagResendOwnerOtpFinal":     ["dealer_tag_device", "vehicle_tagging"],
    "TagVerifyOwnerOtpFinal":     ["dealer_tag_device", "vehicle_tagging"],
    "TagVerifyDealerOtp":         ["dealer_tag_device", "vehicle_tagging"],
    "TagResendDealerOtp":         ["dealer_tag_device", "vehicle_tagging"],
    "TagResendOwnerOtp":          ["dealer_tag_device", "vehicle_tagging"],
    "cancelTagDevice2Vehicle":    ["dealer_tag_device", "vehicle_tagging"],
    "download_receiptPDF":        ["dealer_download_cert", "vehicle_tagging"],
    "upload_receiptPDF":          ["dealer_tag_device", "vehicle_tagging"],

    # Driver management
    "add_driver":                 ["driver_management"],
    "remove_driver":              ["driver_management"],

    # Owner / Manufacturer / Dealer management
    "filter_SOS_user":            ["report_sos_admin", "cn_sos_user"],
    "create_manufacturer":        ["cn_manufacturer", "manufacturer_management"],
    "delete_manufacturer":        ["manufacturer_management"],
    "delete_dealer":              ["dealer_management"],
    "delete_VehicleOwner":        ["owner_management"],
    "delete_eSimProvider":        ["m2m_registration"],

    # ── A.18 Emergency & SOS ─────────────────────────────────────────────────
    # emergency-call-listener-admin is currently commented out in urls.py
    "list_EM_team":               ["emergency_teams", "em_team_list"],
    "remove_EM_team":             ["emergency_teams", "em_team_list"],
    "activate_EM_team":           ["emergency_teams", "em_team_list"],
    "get_EM_team":                ["em_team_create"],
    "create_EM_team":             ["em_team_create"],
    "edit_EM_team":               ["em_team_create"],

    # Field-executive SOS operations (FEx)
    "FEx_broadcastlist":          ["emergency_management"],
    "FEx_broadcastaccept":        ["emergency_management"],
    "FEx_getCallLoc":             ["emergency_management"],
    "FEx_updateLoc":              ["emergency_management"],
    "FEx_updateStatus":           ["emergency_management"],
    "FEx_reqBackup":              ["emergency_management"],
    "TLEx_getloc":                ["emergency_management", "sos_call_list"],

    # ── A.19 Other Management ─────────────────────────────────────────────────
    # get_list / list_notice already covered above

    # Busstand (not in reference doc but gated to settings-level access)
    "set_bus_stand":              ["settings_state_district"],
    "activate_deactivate_bus_stand": ["settings_state_district"],
    "filter_bus_stand":           ["settings_state_district", "route_fixing"],

    # Misc stats
    "manufacturer_model_stock_statistics": ["report_device", "manufacturer_management"],
    "user_statistics":            ["report_user_stats"],
    "vehicle_alert_statistics":   ["dashboard"],
    "gps_imei_continuity_api":    ["report_device_health", "report_activated_device"],

    # Holiday management (used internally by school bus system / state admin)
    "create_holiday":             ["settings_management"],
    "update_holiday":             ["settings_management"],
    "delete_holiday":             ["settings_management"],
    "list_holidays":              ["settings_management", "sbs_create_trip"],

    # Logged-in users list (admin utility)
    "list_logged_in_users":       ["user_management", "settings_management"],
}
# fmt: on


# ---------------------------------------------------------------------------
# HTTP method → default RBAC action
# ---------------------------------------------------------------------------
# Most POST endpoints in this backend are filter/list operations (they take
# query params in the body rather than creating a resource), so POST defaults
# to 'view'.  Actual create/update/delete endpoints are overridden below.
# ---------------------------------------------------------------------------
_METHOD_TO_ACTION: dict[str, str] = {
    'GET':     'filter',
    'HEAD':    'filter',
    'OPTIONS': 'filter',
    'POST':    'filter',
    'PUT':     'update',
    'PATCH':   'update',
    'DELETE':  'delete',
}

# ---------------------------------------------------------------------------
# Per-URL action override
# ---------------------------------------------------------------------------
# These take precedence over the HTTP-method default above.
# Use this for:
#   • POST endpoints that specifically CREATE a resource → 'create'
#   • POST endpoints that require explicit filter permission → 'filter'
#   • Any endpoint where the default method→action mapping is wrong
# ---------------------------------------------------------------------------
API_ACTION_OVERRIDE: dict[str, str] = {
    # ── filter permission required (explicit, same as the new default) ───────
    # Listed here for clarity; they were previously special-cased as 'view'.
    "tag_ownerlist":              "filter",
    "get_device_health_status":   "filter",

    # ── create permission required ──────────────────────────────────────────
    "create_StateAdmin":          "create",
    "create_eSimProvider":        "create",
    "create_SOSAdmin":            "create",
    "create_superuser":           "create",
    "create_DTO_RTO":             "create",
    "create_dealer":              "create",
    "create_SOSuser":             "create",
    "create_VehicleOwner":        "create",
    "create_testAgency":          "create",
    "create_testAgencyDetails":   "create",
    "create_device_model_technical_onboarding_request": "create",
    "esimActivateReq-create":     "create",
    "deviceStockCreate":          "create",
    "deviceStockCreateBulk":      "create",
    "devicemodel-create":         "create",
    "COPCreate":                  "create",
    "create_poi":                 "create",
    "create_notice":              "create",
    "complaint_create":           "create",
    "whitelist_request_create":   "create",
    "create_trip":                "create",
    "create_EM_team":             "create",
    "create_manufacturer":        "create",
    "saveRoute":                  "create",
    "register_incident":          "create",
    "create_settings_VehicleCategory": "create",
    "create_vehicle_category_code":    "create",
    "create_settings_State":      "create",
    "create_settings_District":   "create",
    "create_settings_ip":         "create",
    "create_settings_hp_freq":    "create",
    "create_settings_firmware":   "create",
    "create_ota_settings":        "create",
    "create_permit_master":       "create",
    "rbac_create_custom_role":    "create",
    "rbac_create_user":           "create",
    "TagDevice2Vehicle":          "create",
    "StockAssignToDealer":        "create",
    "archive_gps_data_log":       "create",

    # ── update permission required ──────────────────────────────────────────
    "update_StateAdmin":          "update",
    "update_eSimProvider":        "update",
    "update_DTO_RTO":             "update",
    "update_dealer":              "update",
    "update_VehicleOwner":        "update",
    "update_manufacturer":        "update",
    "update_testAgency":          "update",
    "update_notice":              "update",
    "update_trip":                "update",
    "update_incident":            "update",
    "edit_EM_team":               "update",
    "update_ota_settings":        "update",
    "edit_vehicle_category_code": "update",
    "edit_permit_master":         "update",
    "rbac_update_role":           "update",
    "rbac_update_user":           "update",
    "rbac_update_role_permissions": "update",
    "rbac_assign_role":           "update",
    "complaint_update_status":    "update",
    "complaint_escalate":         "update",
    "complaint_final_report":     "update",
    "whitelist_request_approve":  "update",
    "whitelist_request_deny":     "update",
    "whitelist_device_kyc_update":"update",
    "update_notification_preferences": "update",
    "update_vehicle_owner_expiry":"update",
    "superadmin_mark_technical_onboarding_ongoing_evaluation": "update",
    "superadmin_finalize_technical_onboarding_request":        "update",
    "approve_manufacturer_tech_onboarding":                    "update",
    "esimActivateReq-update":     "update",
    "restore_gps_data_log":       "update",
    "send_mqtt_command":          "update",

    # ── delete permission required ──────────────────────────────────────────
    "delete_notice":              "delete",
    "delete_poi":                 "delete",
    "rbac_deactivate_role":       "delete",
    "delete_manufacturer":        "delete",
    "delete_dealer":              "delete",
    "delete_VehicleOwner":        "delete",
    "delete_eSimProvider":        "delete",
    "delRoute":                   "delete",
    "unTagDevice2Vehicle":        "delete",
    "deviceStockSoftDelete":      "delete",
    "remove_EM_team":             "delete",
    "end_trip":                   "delete",
    "cancel_trip":                "delete",
}


def get_modules_for_url(url_name: str) -> list[str]:
    """Return the list of modules that grant access to *url_name*, or []."""
    return API_MODULE_MAP.get(url_name, [])


def get_action_for_url(url_name: str, method: str = 'GET') -> str:
    """
    Return the RBAC action to check for *url_name* + HTTP *method*.

    Priority:
      1. Explicit per-URL override in API_ACTION_OVERRIDE
      2. HTTP method default from _METHOD_TO_ACTION
    """
    if url_name in API_ACTION_OVERRIDE:
        return API_ACTION_OVERRIDE[url_name]
    return _METHOD_TO_ACTION.get(method.upper(), 'view')
