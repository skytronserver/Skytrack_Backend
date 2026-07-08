# RBAC Module Access Reference with Routes

**Generated:** 2026-06-15  
**Source:** `RolePermissionConfig` table (live DB)  
**Actions legend:** V = View · C = Create · U = Update · D = Delete · F = Filter  
**Scope legend:** `national` → all data · `state` → assigned state · `manufacturer` → own company · `district` → assigned district · `dealer` → own handled · `owner` → own vehicles · `self` → own records only

---

## 1. System Admin (`superadmin`)

**Data scope:** National — all data  
**Total modules:** 142 (full CRUD on every module)

### 1.1 Dashboards
| Module | Actions | Scope | Route |
|---|---|---|---|
| `dashboard` | V,C,U,D,F | national | `/dashboard` |
| `dashboard_morth` | V,C,U,D,F | national | `/morth-dashboard` |
| `dashboard_central` | V,C,U,D,F | national | `/superadmin-dashboard` |

### 1.2 School Bus System
| Module | Actions | Scope | Route |
|---|---|---|---|
| `sbs_dashboard` | V,C,U,D,F | national | `/schoolbus` |
| `sbs_bus_tagging` | V,C,U,D,F | national | `/schoolbus/bus-tagging` |
| `sbs_route_mgmt` | V,C,U,D,F | national | `/schoolbus/route-management` |
| `sbs_bus_assignment` | V,C,U,D,F | national | `/schoolbus/bus-assignment` |
| `sbs_profile_mgmt` | V,C,U,D,F | national | `/schoolbus/profile-management` |
| `sbs_school_reports` | V,C,U,D,F | national | `/schoolbus/reports` |
| `sbs_create_school` | V,C,U,D,F | national | `/schoolbus/Create-School` |
| `sbs_approve_school` | V,C,U,D,F | national | `/schoolbus/Approve-School` |
| `sbs_bus_tracking` | V,C,U,D,F | national | `/schoolbus/bus-tracking` |
| `sbs_create_trip` | V,C,U,D,F | national | `/schoolbus/create-trip` |
| `sbs_parent_tracking` | V,C,U,D,F | national | `/schoolbus/parent-tracking` |

### 1.3 Test Agency
| Module | Actions | Scope | Route |
|---|---|---|---|
| `ta_create_agency` | V,C,U,D,F | national | `/new/test-agency` |
| `ta_agency_list` | V,C,U,D,F | national | `/test-agency/list` |
| `ta_create_user` | V,C,U,D,F | national | `/new/test-agency-details` |
| `ta_user_list` | V,C,U,D,F | national | `/test-agency/details-list` |
| `ta_view_models` | V,C,U,D,F | national | `/test-agency/assigned-models` |

### 1.4 Create New
| Module | Actions | Scope | Route |
|---|---|---|---|
| `cn_state_admin` | V,C,U,D,F | national | `/user/newStateAdmin` |
| `cn_m2m_provider` | V,C,U,D,F | national | `/user/newM2MUser` |
| `cn_manufacturer` | V,C,U,D,F | national | `/manufacturer/new` |
| `cn_sos_admin` | V,C,U,D,F | national | `/new/sos-admin` |
| `cn_system_admin` | V,C,U,D,F | national | `/new/system-admin` |
| `cn_dto` | V,C,U,D,F | national | `/user/newDto` |
| `cn_dealer` | V,C,U,D,F | national | `/user/newDealerAccount` |
| `cn_sos_user` | V,C,U,D,F | national | `/new/sos-user` |
| `cn_vehicle_owner` | V,C,U,D,F | national | `/new/vehicleOwner` |

### 1.5 M2M & Manufacturer Requests
| Module | Actions | Scope | Route |
|---|---|---|---|
| `m2m_registration` | V,C,U,D,F | national | `/superadmin-dashboard/m2m-registration-requests` |
| `m2m_pending` | V,C,U,D,F | national | `/device/m2m-status` |
| `m2m_rejected` | V,C,U,D,F | national | `/device/m2m-status` |
| `m2m_accepted` | V,C,U,D,F | national | `/device/m2m-status` |
| `mfr_vlt_requests` | V,C,U,D,F | national | `/superadmin-dashboard/vehicle-manufacturer-registration-requests` |
| `mfr_ais140_requests` | V,C,U,D,F | national | `/superadmin-dashboard/ais-140-device-manufacturer-registration-requests` |

### 1.6 Technical Onboarding
| Module | Actions | Scope | Route |
|---|---|---|---|
| `tech_onboarding` | V,C,U,D,F | national | `/superadmin-dashboard/technical-onboarding-requests` |
| `tech_onboarding_final` | V,C,U,D,F | national | `/stateadmin-dashboard/technical-onboarding-requests` |
| `mfr_onboarding_new` | V,C,U,D,F | national | `/manufacturer/technical-onboarding/create` |
| `mfr_onboarding_list` | V,C,U,D,F | national | `/manufacturer/technical-onboarding/list` |

### 1.7 Tracking & Playback
| Module | Actions | Scope | Route |
|---|---|---|---|
| `route_fixing` | V,C,U,D,F | national | `/route-fixing` |
| `live_tracking` | V,C,U,D,F | national | `/live-tracking` |
| `gps_tracking` | V,C,U,D,F | national | `/vehicle-tracking-report` |
| `gps_history` | V,C,U,D,F | national | `/vehicle-history` |
| `gps_clustering` | V,C,U,D,F | national | `/live-tracking` |
| `history_playback` | V,C,U,D,F | national | `/history-playback` |
| `trip_viewer` | V,C,U,D,F | national | `/trip-viewer` |
| `trip_monitor` | V,C,U,D,F | national | `/trip-planning` |
| `trip_management` | V,C,U,D,F | national | `/trip-planning` |
| `route_management` | V,C,U,D,F | national | `/route-fixing` |

### 1.8 VLTD Approval
| Module | Actions | Scope | Route |
|---|---|---|---|
| `vltd_pending_model` | V,C,U,D,F | national | `/device/list` |
| `vltd_pending_cop` | V,C,U,D,F | national | `/deviceCOP/list` |
| `vltd_approved_models` | V,C,U,D,F | national | `/device/approved-models` |
| `vltd_approved_cops` | V,C,U,D,F | national | `/device/approved-cops` |

### 1.9 Whitelist & KYC
| Module | Actions | Scope | Route |
|---|---|---|---|
| `wkyc_requests` | V,C,U,D,F | national | `/device/whitelist/requests` |
| `wkyc_device_dashboard` | V,C,U,D,F | national | `/device/whitelist/dashboard` |

### 1.10 POI
| Module | Actions | Scope | Route |
|---|---|---|---|
| `poi_viewer` | V,C,U,D,F | national | `/poi-viewer` |
| `poi_management` | V,C,U,D,F | national | `/reports/poi-report` |

### 1.11 Reports
| Module | Actions | Scope | Route |
|---|---|---|---|
| `reports` | V,C,U,D,F | national | `/reports/*` |
| `report_sos` | V,C,U,D,F | national | `/sos-report` |
| `report_notices` | V,C,U,D,F | national | `/notice/all-notice-list` |
| `report_users` | V,C,U,D,F | national | `/user/registeredUser` |
| `report_state_admin` | V,C,U,D,F | national | `/user/state-admin-list` |
| `report_manufacturer` | V,C,U,D,F | national | `/user/manufacturer-list` |
| `report_sos_admin` | V,C,U,D,F | national | `/user/sos-other-list` |
| `report_m2m_provider` | V,C,U,D,F | national | `/user/m2m-provider-list` |
| `report_dealers` | V,C,U,D,F | national | `/user/dealerList` |
| `report_vehicle_owner` | V,C,U,D,F | national | `/user/vehicle-owner-list` |
| `report_dto` | V,C,U,D,F | national | `/user/dto-user-list` |
| `report_gps_log` | V,C,U,D,F | national | `/reports/gps-data-log` |
| `report_activation_log` | V,C,U,D,F | national | `/reports/activation-log-report` |
| `report_emergency_data` | V,C,U,D,F | national | `/reports/emergency-data-logs` |
| `report_health_packet` | V,C,U,D,F | national | `/reports/health-packet-log` |
| `report_event_data` | V,C,U,D,F | national | `/reports/api-data-log` |
| `report_activated_device` | V,C,U,D,F | national | `/reports/activated-device-report` |
| `report_alert` | V,C,U,D,F | national | `/reports/alert-report` |
| `report_poi` | V,C,U,D,F | national | `/reports/poi-report` |
| `report_incident` | V,C,U,D,F | national | `/reports/incident-report` |
| `report_device_health` | V,C,U,D,F | national | `/reports/device-health-report` |
| `report_user_stats` | V,C,U,D,F | national | `/reports/user-statistics-report` |
| `report_violation` | V,C,U,D,F | national | `/reports/violation-report` |
| `report_sos_users` | V,C,U,D,F | national | `/user/sos-user-list` |
| `report_sos_call_list` | V,C,U,D,F | national | `/sos-call-list` |
| `report_stock` | V,C,U,D,F | national | `/device/combined-stock-report` |
| `report_fitment` | V,C,U,D,F | national | `/device/fit-device` |
| `report_device` | V,C,U,D,F | national | `/device/all-tagged-devices` |

### 1.12 Settings
| Module | Actions | Scope | Route |
|---|---|---|---|
| `settings_management` | V,C,U,D,F | national | `/setting/*` |
| `settings_notice` | V,C,U,D,F | national | `/setting/notice` |
| `settings_send_command` | V,C,U,D,F | national | `/setting/send-command` |
| `settings_vehicle_type` | V,C,U,D,F | national | `/setting/vehicle-category` |
| `settings_vehicle_category` | V,C,U,D,F | national | `/setting/vehicle-category-code` |
| `settings_alert_notif` | V,C,U,D,F | national | `/setting/notification-preferences` |
| `settings_state_district` | V,C,U,D,F | national | `/setting/state-district` |
| `settings_ota_firmware` | V,C,U,D,F | national | `/setting/frequency-firmware` |
| `settings_archive_restore` | V,C,U,D,F | national | `/setting/archive-restore` |
| `settings_ip` | V,C,U,D,F | national | `/setting/ip-settings` |
| `settings_login` | V,C,U,D,F | national | `/setting/login-settings` |
| `settings_permit_cond` | V,C,U,D,F | national | `/setting/permit-conditions` |
| `settings_custom_alerts` | V,C,U,D,F | national | `/setting/custom-alerts` |

### 1.13 Passenger Info System
| Module | Actions | Scope | Route |
|---|---|---|---|
| `pis_bus_stops` | V,C,U,D,F | national | `/pis/bus-stops` |
| `pis_bus_routes` | V,C,U,D,F | national | `/pis/bus-routes` |
| `pis_bus_schedules` | V,C,U,D,F | national | `/pis/bus-schedules` |

### 1.14 State Transport Analytics
| Module | Actions | Scope | Route |
|---|---|---|---|
| `sta_trip_analysis` | V,C,U,D,F | national | `/analytics/trip-analysis` |
| `sta_driving_patterns` | V,C,U,D,F | national | `/analytics/driving-alerts` |
| `sta_vehicle_alerts` | V,C,U,D,F | national | `/analytics/vehicle-alerts` |
| `sta_pis_summary` | V,C,U,D,F | national | `/analytics/pis-summary` |
| `sta_operational` | V,C,U,D,F | national | `/analytics/operational` |
| `sta_comparative` | V,C,U,D,F | national | `/analytics/comparative-analysis` |
| `sta_resource_perf` | V,C,U,D,F | national | `/analytics/resource-performance` |

### 1.15 Custom User Module
| Module | Actions | Scope | Route |
|---|---|---|---|
| `cum_custom_roles` | V,C,U,D,F | national | `/setting/rbac/roles` |
| `cum_feature_perms` | V,C,U,D,F | national | `/setting/rbac/permissions` |
| `cum_user_mgmt` | V,C,U,D,F | national | `/setting/rbac/custom-users` |

### 1.16 Complaint Tickets
| Module | Actions | Scope | Route |
|---|---|---|---|
| `complaint` | V,C,U,D,F | national | `/helpdesk/tickets` |
| `ct_my_dashboard` | V,C,U,D,F | national | `/helpdesk/tickets` |
| `ct_create` | V,C,U,D,F | national | `/helpdesk/tickets/new` |
| `ct_all_tickets` | V,C,U,D,F | national | `/staff/tickets` |
| `ct_escalated` | V,C,U,D,F | national | `/helpdesk/tickets` |

### 1.17 Device, Stock & Management
| Module | Actions | Scope | Route |
|---|---|---|---|
| `device_management` | V,C,U,D,F | national | `/device/new` |
| `device_stock` | V,C,U,D,F | national | `/device/show-available-device` |
| `dm_create_model` | V,C,U,D,F | national | `/deviceModel/new` |
| `dm_tac_cop` | V,C,U,D,F | national | `/deviceModel/extension` |
| `ds_individual` | V,C,U,D,F | national | `/device/show-device` |
| `ds_bulk` | V,C,U,D,F | national | `/device/bulkupload` |
| `ds_assign` | V,C,U,D,F | national | `/device/bulk-assign` |
| `dealer_m2m_status` | V,C,U,D,F | national | `/device/m2m-status` |
| `dealer_request_m2m` | V,C,U,D,F | national | `/device/m2m-activation` |
| `dealer_tag_device` | V,C,U,D,F | national | `/device/fit-device` |
| `dealer_untagged` | V,C,U,D,F | national | `/device/show-available-device` |
| `dealer_download_cert` | V,C,U,D,F | national | `/device/show-tagged-device` |
| `dealer_management` | V,C,U,D,F | national | `/user/dealerList` |
| `vehicle_tagging` | V,C,U,D,F | national | `/device/fit-device` |
| `driver_management` | V,C,U,D,F | national | `/new/otherUser` |
| `owner_management` | V,C,U,D,F | national | `/user/vehicle-owner-list` |
| `manufacturer_management` | V,C,U,D,F | national | `/user/manufacturer-list` |
| `esim_management` | V,C,U,D,F | national | `/device/activation-request/:deviceStatus` |

### 1.18 Emergency & SOS
| Module | Actions | Scope | Route |
|---|---|---|---|
| `emergency_management` | V,C,U,D,F | national | `/sos-alert` |
| `emergency_teams` | V,C,U,D,F | national | `/list/em-team` |
| `em_team_create` | V,C,U,D,F | national | `/new/em-team` |
| `em_team_list` | V,C,U,D,F | national | `/list/em-team` |
| `sos_call_list` | V,C,U,D,F | national | `/sos-call-list` |

### 1.19 Other Management
| Module | Actions | Scope | Route |
|---|---|---|---|
| `alerts` | V,C,U,D,F | national | `/alert-list` |
| `notice_management` | V,C,U,D,F | national | `/notice/all-notice-list` |
| `user_management` | V,C,U,D,F | national | `/user/list` |

---

## 2. State Admin (`stateadmin`)

**Data scope:** State — assigned state only  
**Total modules:** 33

| Module | Actions | Scope | Route |
|---|---|---|---|
| `dashboard` | V,F | state | `/dashboard` |
| `dashboard_central` | V,F | state | `/superadmin-dashboard` |
| `cn_dto` | V,C,F | state | `/user/newDto` |
| `tech_onboarding_final` | V,C,F | state | `/stateadmin-dashboard/technical-onboarding-requests` |
| `route_fixing` | V,F | state | `/route-fixing` |
| `live_tracking` | V,F | state | `/live-tracking` |
| `gps_tracking` | V,F | state | `/vehicle-tracking-report` |
| `gps_clustering` | V,F | state | `/live-tracking` |
| `alerts` | V,F | state | `/alert-list` |
| `notice_management` | V,C,U,F | state | `/notice/all-notice-list` |
| `report_dealers` | V,F | state | `/user/dealerList` |
| `report_vehicle_owner` | V,F | state | `/user/vehicle-owner-list` |
| `report_dto` | V,F | state | `/user/dto-user-list` |
| `report_activated_device` | V,F | state | `/reports/activated-device-report` |
| `report_alert` | V,F | state | `/reports/alert-report` |
| `report_device_health` | V,F | state | `/reports/device-health-report` |
| `reports` | V,F | state | `/reports/*` |
| `wkyc_requests` | V,C,F | state | `/device/whitelist/requests` |
| `wkyc_device_dashboard` | V,F | state | `/device/whitelist/dashboard` |
| `sta_trip_analysis` | V,F | state | `/analytics/trip-analysis` |
| `sta_driving_patterns` | V,F | state | `/analytics/driving-alerts` |
| `sta_vehicle_alerts` | V,F | state | `/analytics/vehicle-alerts` |
| `sta_pis_summary` | V,F | state | `/analytics/pis-summary` |
| `sta_operational` | V,F | state | `/analytics/operational` |
| `sta_comparative` | V,F | state | `/analytics/comparative-analysis` |
| `sta_resource_perf` | V,F | state | `/analytics/resource-performance` |
| `pis_bus_stops` | V,C,U,F | state | `/pis/bus-stops` |
| `pis_bus_routes` | V,C,U,F | state | `/pis/bus-routes` |
| `pis_bus_schedules` | V,C,U,F | state | `/pis/bus-schedules` |
| `driver_management` | V,F | state | `/new/otherUser` |
| `complaint` | V,U,F | national | `/helpdesk/tickets` |
| `user_management` | V,F | state | `/user/list` |
| `settings_management` | V,F | state | `/setting/*` |

---

## 3. M2M Provider (`esimprovider`)

**Data scope:** Manufacturer — own company's records  
**Total modules:** 10

| Module | Actions | Scope | Route |
|---|---|---|---|
| `dashboard` | V | national | `/dashboard` |
| `m2m_pending` | V,U,F | manufacturer | `/device/m2m-status` |
| `m2m_rejected` | V,F | manufacturer | `/device/m2m-status` |
| `m2m_accepted` | V,F | manufacturer | `/device/m2m-status` |
| `wkyc_requests` | V,C,F | manufacturer | `/device/whitelist/requests` |
| `wkyc_device_dashboard` | V,F | manufacturer | `/device/whitelist/dashboard` |
| `device_stock` | V,U,F | national | `/device/show-available-device` |
| `esim_management` | V,C,U,F | national | `/device/activation-request/:deviceStatus` |
| `reports` | V,F | national | `/reports/*` |
| `notice_management` | V | national | `/notice/all-notice-list` |

---

## 4. Manufacturer (`devicemanufacture`)

**Data scope:** Manufacturer — own company's devices  
**Total modules:** 29

| Module | Actions | Scope | Route |
|---|---|---|---|
| `dashboard` | V | manufacturer | `/dashboard` |
| `cn_dealer` | V,C,F | manufacturer | `/user/newDealerAccount` |
| `dm_create_model` | V,C,U,F | manufacturer | `/deviceModel/new` |
| `dm_tac_cop` | V,C,U,F | manufacturer | `/deviceModel/extension` |
| `mfr_onboarding_new` | V,C,F | manufacturer | `/manufacturer/technical-onboarding/create` |
| `mfr_onboarding_list` | V,F | manufacturer | `/manufacturer/technical-onboarding/list` |
| `ds_individual` | V,C,U,F | manufacturer | `/device/show-device` |
| `ds_bulk` | V,C,U,F | manufacturer | `/device/bulkupload` |
| `ds_assign` | V,C,F | manufacturer | `/device/bulk-assign` |
| `report_dealers` | V,F | manufacturer | `/user/dealerList` |
| `report_device` | V,F | manufacturer | `/device/all-tagged-devices` |
| `report_alert` | V,F | manufacturer | `/reports/alert-report` |
| `reports` | V,F | manufacturer | `/reports/*` |
| `settings_ota_firmware` | V,U,F | manufacturer | `/setting/frequency-firmware` |
| `settings_management` | V | manufacturer | `/setting/*` |
| `ct_my_dashboard` | V,F | manufacturer | `/helpdesk/tickets` |
| `ct_create` | V,C,F | manufacturer | `/helpdesk/tickets/new` |
| `ct_all_tickets` | V,F | manufacturer | `/staff/tickets` |
| `ct_escalated` | V,F | manufacturer | `/helpdesk/tickets` |
| `complaint` | V | manufacturer | `/helpdesk/tickets` |
| `wkyc_requests` | V,C,F | manufacturer | `/device/whitelist/requests` |
| `wkyc_device_dashboard` | V,F | manufacturer | `/device/whitelist/dashboard` |
| `device_management` | V,C,U,F | manufacturer | `/device/new` |
| `device_stock` | V,C,U,F | manufacturer | `/device/show-available-device` |
| `manufacturer_management` | V,C,U,D,F | manufacturer | `/user/manufacturer-list` |
| `alerts` | V,F | manufacturer | `/alert-list` |
| `notice_management` | V | manufacturer | `/notice/all-notice-list` |
| `user_management` | V,C,F | manufacturer | `/user/list` |
| `vehicle_tagging` | V | manufacturer | `/device/fit-device` |

---

## 5. SOS Admin (`sosadmin`)

**Data scope:** National for SOS functions; State for tracking  
**Total modules:** 24

| Module | Actions | Scope | Route |
|---|---|---|---|
| `dashboard` | V | state | `/dashboard` |
| `dashboard_central` | V,F | national | `/superadmin-dashboard` |
| `cn_sos_user` | V,C,F | national | `/new/sos-user` |
| `em_team_create` | V,C,U,D,F | national | `/new/em-team` |
| `em_team_list` | V,F | national | `/list/em-team` |
| `report_sos_users` | V,F | national | `/user/sos-user-list` |
| `report_sos` | V,F | national | `/sos-report` |
| `report_sos_call_list` | V,F | national | `/sos-call-list` |
| `ct_my_dashboard` | V,F | national | `/helpdesk/tickets` |
| `ct_create` | V,C,F | national | `/helpdesk/tickets/new` |
| `ct_all_tickets` | V,F | national | `/staff/tickets` |
| `ct_escalated` | V,F | national | `/helpdesk/tickets` |
| `complaint` | V,U,F | national | `/helpdesk/tickets` |
| `emergency_management` | V,C,U,F | state | `/sos-alert` |
| `emergency_teams` | V,C,U,F | state | `/list/em-team` |
| `gps_tracking` | V,F | state | `/vehicle-tracking-report` |
| `gps_history` | V,F | state | `/vehicle-history` |
| `gps_clustering` | V,F | state | `/live-tracking` |
| `poi_management` | V,F | state | `/reports/poi-report` |
| `alerts` | V,F | state | `/alert-list` |
| `reports` | V,F | state | `/reports/*` |
| `notice_management` | V,C | state | `/notice/all-notice-list` |
| `user_management` | V,C,F | state | `/user/list` |
| `vehicle_tagging` | V | state | `/device/fit-device` |

---

## 6. DTO (`dtorto`)

**Data scope:** District — assigned district  
**Total modules:** 19

| Module | Actions | Scope | Route |
|---|---|---|---|
| `dashboard` | V | district | `/dashboard` |
| `route_fixing` | V,F | district | `/route-fixing` |
| `live_tracking` | V,F | district | `/live-tracking` |
| `gps_tracking` | V,F | district | `/vehicle-tracking-report` |
| `gps_history` | V,F | district | `/vehicle-history` |
| `gps_clustering` | V,F | district | `/live-tracking` |
| `history_playback` | V,F | district | `/history-playback` |
| `trip_viewer` | V,F | district | `/trip-viewer` |
| `report_device` | V,F | district | `/device/all-tagged-devices` |
| `report_activated_device` | V,F | district | `/reports/activated-device-report` |
| `report_alert` | V,F | district | `/reports/alert-report` |
| `reports` | V,F | district | `/reports/*` |
| `pis_bus_stops` | V,F | district | `/pis/bus-stops` |
| `pis_bus_routes` | V,F | district | `/pis/bus-routes` |
| `pis_bus_schedules` | V,F | district | `/pis/bus-schedules` |
| `poi_management` | V,F | district | `/reports/poi-report` |
| `alerts` | V,F | district | `/alert-list` |
| `notice_management` | V | district | `/notice/all-notice-list` |
| `vehicle_tagging` | V,F | district | `/device/fit-device` |

---

## 7. Dealer (`dealer`)

**Data scope:** Dealer — own handled devices  
**Total modules:** 21

| Module | Actions | Scope | Route |
|---|---|---|---|
| `dashboard` | V | dealer | `/dashboard` |
| `cn_vehicle_owner` | V,C,F | dealer | `/new/vehicleOwner` |
| `dealer_m2m_status` | V,F | dealer | `/device/m2m-status` |
| `dealer_request_m2m` | V,C,F | dealer | `/device/m2m-activation` |
| `dealer_tag_device` | V,C,U,F | dealer | `/device/fit-device` |
| `dealer_untagged` | V,F | dealer | `/device/show-available-device` |
| `dealer_download_cert` | V,F | dealer | `/device/show-tagged-device` |
| `report_stock` | V,F | dealer | `/device/combined-stock-report` |
| `report_fitment` | V,F | dealer | `/device/fit-device` |
| `report_vehicle_owner` | V,F | dealer | `/user/vehicle-owner-list` |
| `reports` | V,F | dealer | `/reports/*` |
| `settings_ip` | V,U,F | dealer | `/setting/ip-settings` |
| `settings_management` | V | dealer | `/setting/*` |
| `wkyc_requests` | V,C,F | dealer | `/device/whitelist/requests` |
| `wkyc_device_dashboard` | V,F | dealer | `/device/whitelist/dashboard` |
| `dealer_management` | V | dealer | `/user/dealerList` |
| `owner_management` | V,C,F | dealer | `/user/vehicle-owner-list` |
| `gps_clustering` | V,F | dealer | `/live-tracking` |
| `alerts` | V,F | dealer | `/alert-list` |
| `notice_management` | V | dealer | `/notice/all-notice-list` |
| `user_management` | V,C,F | dealer | `/user/list` |

---

## 8. Vehicle Owner (`owner`)

**Data scope:** Owner — own vehicles only  
**Total modules:** 22

| Module | Actions | Scope | Route |
|---|---|---|---|
| `dashboard` | V | owner | `/dashboard` |
| `route_fixing` | V,F | owner | `/route-fixing` |
| `trip_monitor` | V,F | owner | `/trip-planning` |
| `live_tracking` | V,F | owner | `/live-tracking` |
| `gps_tracking` | V,F | owner | `/vehicle-tracking-report` |
| `gps_history` | V,F | owner | `/vehicle-history` |
| `gps_clustering` | V,F | owner | `/live-tracking` |
| `history_playback` | V,F | owner | `/history-playback` |
| `trip_viewer` | V,F | owner | `/trip-viewer` |
| `trip_management` | V,C,U,F | owner | `/trip-planning` |
| `route_management` | V,C,U,F | owner | `/route-fixing` |
| `poi_viewer` | V,F | owner | `/poi-viewer` |
| `poi_management` | V,C,U,F | owner | `/reports/poi-report` |
| `report_alert` | V,F | owner | `/reports/alert-report` |
| `report_poi` | V,F | owner | `/reports/poi-report` |
| `reports` | V,F | owner | `/reports/*` |
| `pis_bus_schedules` | V,F | owner | `/pis/bus-schedules` |
| `driver_management` | V,C,U,F | owner | `/new/otherUser` |
| `alerts` | V,F | owner | `/alert-list` |
| `notice_management` | V | owner | `/notice/all-notice-list` |
| `owner_management` | V | owner | `/user/vehicle-owner-list` |
| `vehicle_tagging` | V,F | owner | `/device/fit-device` |

---

## 9. Team Lead (`teamleader`)

**Data scope:** State for SOS / complaint; Self for core functions  
**Total modules:** 12

| Module | Actions | Scope | Route |
|---|---|---|---|
| `dashboard` | V | self | `/dashboard` |
| `sos_call_list` | V,F | state | `/sos-call-list` |
| `ct_my_dashboard` | V,F | state | `/helpdesk/tickets` |
| `ct_create` | V,C,F | state | `/helpdesk/tickets/new` |
| `ct_all_tickets` | V,F | state | `/staff/tickets` |
| `ct_escalated` | V,F | state | `/helpdesk/tickets` |
| `complaint` | V,U,F | national | `/helpdesk/tickets` |
| `gps_tracking` | V,F | state | `/vehicle-tracking-report` |
| `emergency_management` | V,U,F | self | `/sos-alert` |
| `emergency_teams` | V | self | `/list/em-team` |
| `alerts` | V | self | `/alert-list` |
| `manufacturer_management` | V,F | national | `/user/manufacturer-list` |

---

## 10. Desk Executive (`sosexecutive`)

**Data scope:** Self  
**Total modules:** 9

| Module | Actions | Scope | Route |
|---|---|---|---|
| `dashboard` | V | self | `/dashboard` |
| `sos_call_list` | V,F | self | `/sos-call-list` |
| `complaint` | V,U,F | national | `/helpdesk/tickets` |
| `gps_tracking` | V,F | state | `/vehicle-tracking-report` |
| `gps_history` | V | state | `/vehicle-history` |
| `gps_clustering` | V | state | `/live-tracking` |
| `emergency_management` | V,U | self | `/sos-alert` |
| `alerts` | V | self | `/alert-list` |
| `manufacturer_management` | V,F | national | `/user/manufacturer-list` |

---

## 11. Test Agency (`filment`)

**Data scope:** Self / National  
**Total modules:** 5

| Module | Actions | Scope | Route |
|---|---|---|---|
| `dashboard` | V | national | `/dashboard` |
| `ta_view_models` | V,F | self | `/test-agency/assigned-models` |
| `device_stock` | V,C,U,F | national | `/device/show-available-device` |
| `vehicle_tagging` | V,F | national | `/device/fit-device` |
| `notice_management` | V | national | `/notice/all-notice-list` |

---

## 12. School Admin (`schooladmin`)

**Data scope:** Self for school modules; Owner scope for shared tracking  
**Total modules:** 17

| Module | Actions | Scope | Route |
|---|---|---|---|
| `dashboard` | V | owner | `/dashboard` |
| `sbs_dashboard` | V,F | self | `/schoolbus` |
| `sbs_bus_tagging` | V,C,U,F | self | `/schoolbus/bus-tagging` |
| `sbs_bus_tracking` | V,F | self | `/schoolbus/bus-tracking` |
| `sbs_route_mgmt` | V,C,U,F | self | `/schoolbus/route-management` |
| `sbs_bus_assignment` | V,C,U,F | self | `/schoolbus/bus-assignment` |
| `sbs_profile_mgmt` | V,U,F | self | `/schoolbus/profile-management` |
| `sbs_create_trip` | V,C,F | self | `/schoolbus/create-trip` |
| `sbs_school_reports` | V,F | self | `/schoolbus/reports` |
| `gps_tracking` | V,F | owner | `/vehicle-tracking-report` |
| `gps_history` | V,F | owner | `/vehicle-history` |
| `driver_management` | V,C,U,F | owner | `/new/otherUser` |
| `trip_management` | V,F | owner | `/trip-planning` |
| `vehicle_tagging` | V,F | owner | `/device/fit-device` |
| `alerts` | V,F | owner | `/alert-list` |
| `reports` | V,F | owner | `/reports/*` |
| `notice_management` | V | owner | `/notice/all-notice-list` |

---

## 13. Parent User (`parentuser`)

**Data scope:** Self  
**Total modules:** 2

| Module | Actions | Scope | Route |
|---|---|---|---|
| `dashboard` | V | owner | `/dashboard` |
| `sbs_parent_tracking` | V | self | `/schoolbus/parent-tracking` |

---

## Appendix: Route → API Endpoints Reference

> **Base URL**: All `/api/...` paths are relative to `REACT_APP_BASE_URL` via the shared axios instance (`src/services/axiosInstance.js` / `http-common.js`).  
> **School bus API**: `school/api/...` paths use `REACT_APP_SCHOOL_BUS_API_URL`.  
> **External calls**: Several `/superadmin-dashboard` sub-tabs call `https://api.gromed.in/` directly via `fetch()`, bypassing the axios instance.  
> **Mock flag**: School bus routes respect `REACT_APP_USE_SCHOOLBUS_MOCK` — real API paths are listed; mock in-memory data is used when the flag is `true`.

---

### A.1 Dashboards & Central

| Route | API Endpoints |
|---|---|
| `/dashboard` | `POST /api/homepageandstat/homepage/`<br>`POST /api/homepageandstat/homepage_stateAdmin/`<br>`POST /api/homepageandstat/homepage_DTO/`<br>`POST /api/homepageandstat/homepage_VehicleOwner/`<br>`POST /api/homepageandstat/homepage_Dealer/`<br>`POST /api/homepageandstat/homepage_Manufacturer/`<br>`POST /api/homepageandstat/homepage_esimProvider/`<br>`GET /api/SOS/SOS_Admin_report/`<br>`GET /api/SOS/SOS_TL_report/`<br>`GET /api/SOS/SOS_EX_report/`<br>`GET /api/Statistics/vehicle_alert_statistics/` |
| `/morth-dashboard` | `GET /api/central_api/` |
| `/superadmin-dashboard` | `GET /api/gps_track_data_api` *(transport tab)*<br>`GET /api/police_fleet_metrics/` *(public safety tab)*<br>`GET /api/ambulance_fleet_metrics/` *(public safety tab)*<br>`POST https://api.gromed.in/api/dashboard/areawise-device-count/` *(vehicle monitoring)*<br>`POST https://api.gromed.in/api/dashboard/vehicle-monitoring/` *(vehicle monitoring)*<br>`POST https://api.gromed.in/api/dashboard_ERSS/areawise-device-count/` *(ERSS)*<br>`POST https://api.gromed.in/api/dashboard/erss-summary/` *(ERSS)*<br>`POST https://api.gromed.in/api/dashboard_SOS/areawise-device-count/` *(SOS monitoring)*<br>`POST https://api.gromed.in/api/dashboard/sos-monitoring/` *(SOS monitoring)*<br>`POST /api/EM/DEx/updateCaseMeta/` *(SOS monitoring)*<br>`GET /api/vehicle_status_metrics/` *(SOS analytics)*<br>`GET /api/SOS/SOS_Admin_report/` *(SOS analytics)*<br>`GET /api/SOS/SOS_TL_report/` *(SOS analytics)*<br>`POST /api/EM/DEx/getPendingCallList/` *(SOS analytics)* |

---

### A.2 School Bus System

| Route | API Endpoints |
|---|---|
| `/schoolbus` | `GET school/api/admin/school/overview/` |
| `/schoolbus/bus-tagging` | `GET school/api/admin/buses/tag/history/`<br>`POST school/api/admin/buses/tag/initiate/`<br>`POST school/api/admin/buses/tag/{tagId}/verify-otp/`<br>`POST school/api/admin/buses/tag/{tagId}/documents/` *(multipart)* |
| `/schoolbus/route-management` | `GET school/api/admin/routes/`<br>`POST school/api/admin/routes/`<br>`POST school/api/admin/routes/{id}/update/`<br>`POST school/api/admin/routes/{id}/delete/`<br>`POST school/api/admin/routes/{routeId}/stops/add/`<br>`POST school/api/admin/bus-stops/{stopId}/update/`<br>`POST school/api/admin/routes/{routeId}/stops/{stopId}/remove/` |
| `/schoolbus/bus-assignment` | `GET school/api/admin/buses/available/`<br>`GET school/api/admin/routes/{routeId}/buses/`<br>`POST /api/schoolbus/assign`<br>`PUT /api/schoolbus/reassign/{busId}`<br>`DELETE /api/schoolbus/untag/{busId}` |
| `/schoolbus/profile-management` | `GET school/api/admin/parents/`<br>`POST school/api/admin/parents/`<br>`GET school/api/admin/students/`<br>`POST school/api/admin/students/`<br>`POST /api/Settings/filter_settings_State/`<br>`POST /api/Settings/filter_settings_District/`<br>`POST /api/resend_usercreation_otp/`<br>`POST /api/resend_parent_activation_otp/` |
| `/schoolbus/reports` | `GET school/api/admin/trips/attendance/raw/`<br>`GET school/api/admin/trips/`<br>`GET /api/schoolbus/reports/traffic`<br>`GET /api/schoolbus/reports/unplanned-usage`<br>`GET /api/schoolbus/alerts/feed` |
| `/schoolbus/Create-School` | `POST school/api/schools/apply/` *(multipart)* |
| `/schoolbus/Approve-School` | `GET school/api/state-admin/schools/`<br>`POST school/api/state-admin/schools/{applicationId}/decision/` |
| `/schoolbus/bus-tracking` | `GET /api/gps_track_data_api` |
| `/schoolbus/create-trip` | `POST school/api/admin/trips/`<br>`GET school/api/admin/routes/assignments/`<br>`POST school/api/admin/trips/validate-holidays/`<br>`POST school/api/admin/trips/{tripId}/attendance/init/`<br>`GET school/api/admin/trips/{tripId}/attendance/raw/`<br>`POST school/api/admin/trips/{tripId}/attendance/pickup/`<br>`POST school/api/admin/trips/{tripId}/attendance/drop/` |
| `/schoolbus/parent-tracking` | `GET school/api/parents/students/live-location/` |

---

### A.3 Test Agency

| Route | API Endpoints |
|---|---|
| `/new/test-agency` | `POST /api/testAgency/name_list/`<br>`POST /api/testAgency/create_testAgency/` *(multipart)* |
| `/test-agency/list` | `POST /api/testAgency/list/`<br>`POST /api/testAgency/update_testAgency/` *(multipart)* |
| `/new/test-agency-details` | `POST /api/testAgency/details/create/` |
| `/test-agency/details-list` | `GET /api/testAgency/details/list/` |
| `/test-agency/assigned-models` | `POST /api/testAgency/device_models/` |

---

### A.4 User / Account Creation

| Route | API Endpoints |
|---|---|
| `/user/newStateAdmin` | `POST /api/StateAdmin/create_StateAdmin/` *(multipart)*<br>`POST /api/resend_usercreation_otp/` |
| `/user/newM2MUser` | `POST /api/eSimProvider/create_eSimProvider/` *(multipart)* |
| `/manufacturer/new` | `POST /api/devicestock/deviceStockCreate/` *(multipart)* |
| `/new/sos-admin` | `POST /api/SOSAdmin/create_SOSAdmin/` *(multipart)* |
| `/new/system-admin` | `POST /api/create_systemadmin/` |
| `/user/newDto` | `POST /api/DTO_RTO/create_DTO_RTO/` *(multipart)* |
| `/user/newDealerAccount` | `POST /api/dealer/filter_dealer/`<br>`POST /api/dealer/create_dealer/` *(multipart)* |
| `/new/sos-user` | `POST /api/SOSuser/create_SOSuser/` *(multipart)* |
| `/new/vehicleOwner` | `POST /api/VehicleOwner/filter_VehicleOwner/`<br>`POST /api/VehicleOwner/create_VehicleOwner/` *(multipart)*<br>`POST /api/VehicleOwner/update_VehicleOwner/` *(multipart)* |
| `/new/otherUser` | `POST /api/create_user/` |

---

### A.5 M2M & Manufacturer Requests

| Route | API Endpoints |
|---|---|
| `/superadmin-dashboard/m2m-registration-requests` | `POST /api/eSimProvider/filter_eSimProvider/?all_user=true`<br>`POST /api/eSimProvider/update_eSimProvider/` |
| `/superadmin-dashboard/vehicle-manufacturer-registration-requests` | `POST /api/manufacturer/filter_manufacturers/?all_user=true`<br>`POST /api/manufacturer/update_manufacturer/` |
| `/superadmin-dashboard/ais-140-device-manufacturer-registration-requests` | `POST /api/manufacturer/filter_manufacturers/?all_user=true`<br>`POST /api/manufacturer/update_manufacturer/` |
| `/device/m2m-status` | `POST /api/dealer/check_esim_status/` |
| `/device/m2m-activation` | `POST /api/esimActivateReq/create/` |
| `/device/activation-request/:deviceStatus` | `POST /api/esimActivateReq/filter/`<br>`POST /api/esimActivateReq/update/` |

---

### A.6 Technical Onboarding

| Route | API Endpoints |
|---|---|
| `/superadmin-dashboard/technical-onboarding-requests` | `POST /api/devicemodel/technical-onboarding/superadmin/list/`<br>`POST /api/manufacturer/filter_TechOnboardmanufacturers/`<br>`POST /api/devicemodel/technical-onboarding/superadmin/mark-ongoing/`<br>`POST /api/devicemodel/technical-onboarding/superadmin/finalize/` *(multipart)*<br>`POST /api/manufacturer/approve_tech_onboarding/` |
| `/stateadmin-dashboard/technical-onboarding-requests` | `POST /api/devicemodel/technical-onboarding/superadmin/list/`<br>`POST /api/manufacturer/filter_TechOnboardmanufacturers/`<br>`POST /api/devicemodel/technical-onboarding/superadmin/mark-ongoing/`<br>`POST /api/devicemodel/technical-onboarding/superadmin/finalize/` *(multipart)*<br>`POST /api/manufacturer/approve_tech_onboarding/` |
| `/manufacturer/technical-onboarding/create` | `POST /api/devicemodel/devicemodelFilter/`<br>`POST /api/devicemodel/technical-onboarding/manufacturer/list/`<br>`POST /api/devicemodel/technical-onboarding/create/` *(multipart)* |
| `/manufacturer/technical-onboarding/list` | `POST /api/devicemodel/technical-onboarding/manufacturer/list/` |

---

### A.7 Tracking & Playback

| Route | API Endpoints |
|---|---|
| `/live-tracking` | `GET /api/gps_track_data_api`<br>`GET /api/gps-data-map/`<br>`POST /api/get_live_vehicle_no/`<br>`GET /api/poi/types/`<br>`GET /api/poi/list/`<br>`GET school/api/map/school-bus/routes/`<br>`GET school/api/map/pis/routes/`<br>`GET school/api/map/school-bus/buses/`<br>`GET school/api/map/pis/buses/`<br>`GET school/api/map/pis/bus-stops/`<br>`GET /api/emuser-locations/`<br>`POST /api/incident/filter/`<br>`POST /api/cell_location/`<br>`GET /api/geocode/` |
| `/vehicle-tracking-report` | `GET /api/gps_track_data_api`<br>`GET /api/poi/types/`<br>`GET /api/poi/list/` |
| `/vehicle-history` | `GET /api/gps_track_data_api`<br>`GET /api/poi/types/`<br>`GET /api/poi/list/`<br>`GET school/api/map/school-bus/routes/`<br>`GET school/api/map/pis/routes/`<br>`GET /api/emuser-locations/`<br>`POST /api/incident/filter/`<br>`POST /api/cell_location/`<br>`GET /api/geocode/` |
| `/history-playback` | `POST /api/get_live_vehicle_no/`<br>`GET /api/gps_history_map/`<br>`GET /api/poi/types/`<br>`GET /api/poi/list/`<br>`GET /api/gps_track_data_api` |
| `/trip-viewer` | `POST /api/tag/tag_ownerlist/` |
| `/trip-planning` | `GET /api/trip/`<br>`POST /api/trip/create/`<br>`PUT /api/trip/{tripId}/update/`<br>`POST /api/trip/{tripId}/end/`<br>`POST /api/trip/{tripId}/cancel/`<br>`POST /api/getRoute/`<br>`POST /api/saveRoute/`<br>`POST /api/delRoute/` |
| `/route-fixing` | `POST /api/getRoute/`<br>`POST /api/get_routePath/`<br>`POST /api/saveRoute/`<br>`POST /api/delRoute/` |

---

### A.8 VLTD Approval

| Route | API Endpoints |
|---|---|
| `/device/list` | `GET /api/devicemodel/devicemodelAwaitingStateApproval/` |
| `/deviceCOP/list` | `GET /api/devicemodel/COPAwaitingStateApproval/` |
| `/device/approved-models` | `POST /api/stateadmin/reports/approved-models/` |
| `/device/approved-cops` | `POST /api/stateadmin/reports/approved-cops/` |

---

### A.9 Whitelist & KYC

| Route | API Endpoints |
|---|---|
| `/device/whitelist/requests` | `GET /api/whitelist/request/list/`<br>`GET /api/whitelist/request/esim/all/`<br>`GET /api/whitelist/active/list/`<br>`POST /api/whitelist/request/create/`<br>`POST /api/whitelist/request/{id}/approve/`<br>`POST /api/whitelist/request/{id}/deny/` |
| `/device/whitelist/dashboard` | `GET /api/whitelist/device/dashboard/`<br>`GET /api/whitelist/device/{id}/detail/`<br>`POST /api/whitelist/device/{id}/kyc/update/` |

---

### A.10 POI

| Route | API Endpoints |
|---|---|
| `/poi-viewer` | `GET /api/poi/list/`<br>`POST /api/poi/create/` *(multipart)*<br>`POST /api/poi/update/` *(multipart)*<br>`POST /api/poi/delete/`<br>`POST /api/get_routePath/`<br>`GET /api/geocode/` |
| `/reports/poi-report` | `GET /api/poi/list/` |

---

### A.11 Reports

| Route | API Endpoints |
|---|---|
| `/sos-report` | `GET /api/SOS/report/` |
| `/notice/all-notice-list` | `POST /api/notice/list/`<br>`POST /api/notice/delete/` |
| `/user/registeredUser` | `GET /api/get_list/`<br>`POST /api/deactivateUser/`<br>`POST /api/activateUser/`<br>`POST /api/resend_usercreation_otp/` |
| `/user/state-admin-list` | `POST /api/StateAdmin/filter_StateAdmin/` |
| `/user/manufacturer-list` | `POST /api/manufacturer/filter_manufacturers/?all_user=true` |
| `/user/sos-other-list` | `POST /api/SOSuser/filter_SOSuser/` |
| `/user/m2m-provider-list` | `POST /api/eSimProvider/filter_eSimProvider/?all_user=true` |
| `/user/dealerList` | `POST /api/dealer/filter_dealer/` |
| `/user/vehicle-owner-list` | `POST /api/VehicleOwner/filter_VehicleOwner/`<br>`POST /api/update_vehicle_owner_expiry/` |
| `/user/dto-user-list` | `POST /api/DTO_RTO/filter_DTO_RTO/` |
| `/user/sos-user-list` | `POST /api/SOSAdmin/filter_SOSAdmin/` |
| `/sos-call-list` | `POST /api/EM/DEx/getPendingCallList/`<br>`POST /api/EM/DEx/replyCall/` |
| `/device/combined-stock-report` | `POST /api/devicestock/combined/` |
| `/device/fit-device` | `GET /api/sell/SellListAvailableDeviceStock/`<br>`PATCH /api/sell/SellFitDevice/`<br>`PATCH /api/sell/configure_sms_gateway/`<br>`PATCH /api/sell/configure_sos_gateway/`<br>`PATCH /api/sell/configure_ip_port/` |
| `/device/all-tagged-devices` | `POST /api/tag/StateAdmin_view_all_tagging/` |
| `/reports/gps-data-log` | `GET /api/gps-data-log-table/` |
| `/reports/activation-log-report` | `GET /api/gps-data-log-table/` |
| `/reports/emergency-data-logs` | `GET /api/gps-em-data-log-table/` |
| `/reports/health-packet-log` | `GET /api/gps-data-log-table/`<br>`GET /api/gps-em-data-log-table/` |
| `/reports/api-data-log` | `POST /api/apiLog/?page={page}&per_page={per_page}` |
| `/reports/activated-device-report` | `POST /api/device/activated_device_list/` |
| `/reports/alert-report` | `POST /api/alertlog/filter/` |
| `/reports/incident-report` | `POST /api/incident/filter/` |
| `/reports/device-health-report` | `GET /api/device-health-status/` |
| `/reports/user-statistics-report` | `GET /api/Statistics/user_statistics/` |
| `/reports/violation-report` | `POST /api/Settings/filter_settings_VehicleCategory/`<br>`GET school/api/enforcement/permit-conditions/list/`<br>`GET school/api/enforcement/violations/` |
| `/alert-list` | `POST /api/list-alerts/` |

---

### A.12 Settings

| Route | API Endpoints |
|---|---|
| `/setting/notice` | `POST /api/notice/filter/`<br>`POST /api/notice/create/` *(multipart)*<br>`POST /api/notice/update/` *(multipart)* |
| `/setting/send-command` | `POST /api/mqtt/send_command/` |
| `/setting/vehicle-category` | `POST /api/Settings/filter_settings_VehicleCategory/`<br>`POST /api/Settings/create_settings_VehicleCategory/` |
| `/setting/vehicle-category-code` | `POST /api/Settings/vehicle_category_code/list/`<br>`POST /api/Settings/vehicle_category_code/create/`<br>`POST /api/Settings/vehicle_category_code/edit/` |
| `/setting/notification-preferences` | `GET /api/user/notification-preferences/`<br>`POST /api/user/notification-preferences/` |
| `/setting/state-district` | `POST /api/Settings/filter_settings_State/`<br>`POST /api/Settings/filter_settings_District/`<br>`POST /api/Settings/create_settings_State/`<br>`POST /api/Settings/create_settings_District/` |
| `/setting/frequency-firmware` | `POST /api/Settings/filter_settings_hp_freq/`<br>`POST /api/Settings/create_settings_hp_freq/`<br>`POST /api/ota/filter/`<br>`POST /api/ota/create/`<br>`POST /api/Settings/filter_settings_firmware/`<br>`POST /api/Settings/create_settings_firmware/` |
| `/setting/archive-restore` | `GET /api/gpsdata/archives/list/`<br>`POST /api/gpsdata/archive/`<br>`POST /api/gpsdata/restore/` |
| `/setting/ip-settings` | `POST /api/Settings/filter_settings_ip/`<br>`POST /api/Settings/create_settings_ip/` |
| `/setting/login-settings` | `POST /api/set_login_settings/` |
| `/setting/permit-conditions` | `POST /api/Settings/filter_settings_VehicleCategory/`<br>`GET school/api/enforcement/permit-conditions/list/`<br>`POST school/api/enforcement/permit-conditions/`<br>`POST school/api/enforcement/permit-conditions/{id}/update/` |
| `/setting/custom-alerts` | `GET school/api/custom-alerts/parameters/`<br>`GET school/api/custom-alerts/rules/`<br>`POST school/api/custom-alerts/rules/`<br>`POST school/api/custom-alerts/rules/{id}/update/`<br>`POST school/api/custom-alerts/rules/{id}/delete/` |

---

### A.13 Passenger Info System (PIS)

| Route | API Endpoints |
|---|---|
| `/pis/bus-stops` | `GET school/api/pis/bus-stops/`<br>`POST school/api/pis/bus-stops/`<br>`POST school/api/pis/bus-stops/{id}/update/`<br>`POST school/api/pis/bus-stops/{id}/toggle/` |
| `/pis/bus-routes` | `GET school/api/pis/routes/`<br>`GET school/api/pis/bus-stops/`<br>`POST school/api/pis/routes/`<br>`POST school/api/pis/routes/{id}/update/`<br>`POST school/api/pis/routes/{id}/toggle/` |
| `/pis/bus-schedules` | `GET school/api/pis/schedules/`<br>`GET school/api/pis/routes/`<br>`GET school/api/pis/bus-stops/`<br>`GET school/api/pis/available-buses/`<br>`POST school/api/pis/schedules/`<br>`POST school/api/pis/schedules/{scheduleId}/update-status/` |

---

### A.14 State Transport Analytics

| Route | API Endpoints |
|---|---|
| `/analytics/trip-analysis` | `GET school/api/analytics/trips/` |
| `/analytics/driving-alerts` | `GET school/api/analytics/driving-pattern-alerts/` |
| `/analytics/vehicle-alerts` | `GET school/api/analytics/vehicle-alert-summary/` |
| `/analytics/pis-summary` | `GET school/api/analytics/pis-summary/` |
| `/analytics/operational` | `GET school/api/analytics/operational/` |
| `/analytics/comparative-analysis` | `GET school/api/pis/routes/`<br>`GET school/api/analytics/comparative-analysis/` |
| `/analytics/resource-performance` | `GET school/api/analytics/resource-performance/` |

---

### A.15 Custom User Module (RBAC)

| Route | API Endpoints |
|---|---|
| `/setting/rbac/roles` | `GET /api/rbac/roles/`<br>`POST /api/rbac/roles/create/`<br>`POST /api/rbac/roles/update/`<br>`POST /api/rbac/roles/deactivate/` |
| `/setting/rbac/permissions` | `GET /api/rbac/roles/active/`<br>`GET /api/rbac/modules/`<br>`GET /api/rbac/roles/permissions/?role_code={roleCode}`<br>`POST /api/rbac/roles/permissions/update/` |
| `/setting/rbac/custom-users` | `GET /api/rbac/roles/active/`<br>`GET /api/rbac/users/`<br>`POST /api/rbac/users/create/` *(multipart)*<br>`POST /api/rbac/users/update/` *(multipart)*<br>`POST /api/rbac/users/assign-role/` |

---

### A.16 Complaint Tickets / Helpdesk

| Route | API Endpoints |
|---|---|
| `/helpdesk/tickets` | `GET /api/complaint/list/`<br>`GET /api/complaint/list/?status={status}` |
| `/helpdesk/tickets/new` | `GET /api/complaint/device-imei/?q={query}`<br>`POST /api/complaint/create/` *(multipart)* |
| `/staff/tickets` | `GET /api/complaint/list/` |

---

### A.17 Device, Stock & Management

| Route | API Endpoints |
|---|---|
| `/device/new` | `POST /api/devicestock/deviceStockCreate/` *(multipart)*<br>`POST /api/devicemodel/devicemodelDetails/` |
| `/device/show-available-device` | `GET /api/sell/SellListAvailableDeviceStock/` |
| `/deviceModel/new` | `POST /api/devicemodel/devicemodelCreate/` *(multipart)*<br>`POST /api/devicemodel/COPUpload/` *(multipart)* |
| `/deviceModel/extension` | `POST /api/devicemodel/devicemodelDetails/`<br>`POST /api/devicemodel/COPUpload/` *(multipart)* |
| `/device/show-device` | `POST /api/devicestock/deviceStockFilter/` |
| `/device/bulkupload` | `POST /api/devicestock/deviceStockCreateBulk/` *(multipart)*<br>`GET /api/devicestock/deviceStockBulkSample/` |
| `/device/bulk-assign` | `POST /api/dealer/filter_dealer/`<br>`POST /api/devicestock/StockAssignToDealer/`<br>`GET /api/devicestock/deviceStockBulkSample/` |
| `/device/show-tagged-device` | `POST /api/devicestock/deviceStockFilter/`<br>`POST /api/tag/untag/`<br>`POST /api/tag/retag/`<br>`POST /api/tag/update-temp-registration/` *(multipart)* |

---

### A.18 Emergency & SOS

| Route | API Endpoints |
|---|---|
| `/sos-alert` | `GET /api/emergency-call-listener-admin/` |
| `/list/em-team` | `POST /api/EM/list_EMteam/`<br>`POST /api/EM/remove_EMteam/`<br>`POST /api/EM/activate_EMteam/` |
| `/new/em-team` | `POST /api/EM/get_EMteam/`<br>`POST /api/EM/create_EMteam/`<br>`POST /api/EM/edit_EMteam/` |

---

### A.19 Other Management

| Route | API Endpoints |
|---|---|
| `/user/list` | `GET /api/get_list/` |
