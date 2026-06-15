# RBAC Module Access Reference

**Generated:** 2026-06-15  
**Source:** `RolePermissionConfig` table (live DB)  
**Actions legend:** V = View · C = Create · U = Update · D = Delete · F = Filter  
**Scope legend:** `national` → all data · `state` → assigned state · `manufacturer` → own company · `district` → assigned district · `dealer` → own handled · `owner` → own vehicles · `self` → own records only

> Legacy API-enforcement modules (`gps_tracking`, `gps_history`, `gps_clustering`, `reports`,
> `settings_management`, etc.) are kept alongside the new UI-navigation modules and are both shown below.
> A module with **no rows marked V** for a role means that role cannot see or use it.

---

## 1. System Admin (`superadmin`)

**Data scope:** National — all data  
**Total modules:** 142 (full CRUD on every module)

### 1.1 Dashboards
| Module | Actions | Scope |
|---|---|---|
| `dashboard` | V,C,U,D,F | national |
| `dashboard_north` | V,C,U,D,F | national |
| `dashboard_central` | V,C,U,D,F | national |

### 1.2 School Bus System
| Module | Actions | Scope |
|---|---|---|
| `sbs_dashboard` | V,C,U,D,F | national |
| `sbs_bus_tagging` | V,C,U,D,F | national |
| `sbs_route_mgmt` | V,C,U,D,F | national |
| `sbs_bus_assignment` | V,C,U,D,F | national |
| `sbs_profile_mgmt` | V,C,U,D,F | national |
| `sbs_school_reports` | V,C,U,D,F | national |
| `sbs_create_school` | V,C,U,D,F | national |
| `sbs_approve_school` | V,C,U,D,F | national |
| `sbs_bus_tracking` | V,C,U,D,F | national |
| `sbs_create_trip` | V,C,U,D,F | national |
| `sbs_parent_tracking` | V,C,U,D,F | national |

### 1.3 Test Agency
| Module | Actions | Scope |
|---|---|---|
| `ta_create_agency` | V,C,U,D,F | national |
| `ta_agency_list` | V,C,U,D,F | national |
| `ta_create_user` | V,C,U,D,F | national |
| `ta_user_list` | V,C,U,D,F | national |
| `ta_view_models` | V,C,U,D,F | national |

### 1.4 Create New
| Module | Actions | Scope |
|---|---|---|
| `cn_state_admin` | V,C,U,D,F | national |
| `cn_m2m_provider` | V,C,U,D,F | national |
| `cn_manufacturer` | V,C,U,D,F | national |
| `cn_sos_admin` | V,C,U,D,F | national |
| `cn_system_admin` | V,C,U,D,F | national |
| `cn_dto` | V,C,U,D,F | national |
| `cn_dealer` | V,C,U,D,F | national |
| `cn_sos_user` | V,C,U,D,F | national |
| `cn_vehicle_owner` | V,C,U,D,F | national |

### 1.5 M2M & Manufacturer Requests
| Module | Actions | Scope |
|---|---|---|
| `m2m_registration` | V,C,U,D,F | national |
| `m2m_pending` | V,C,U,D,F | national |
| `m2m_rejected` | V,C,U,D,F | national |
| `m2m_accepted` | V,C,U,D,F | national |
| `mfr_vlt_requests` | V,C,U,D,F | national |
| `mfr_ais140_requests` | V,C,U,D,F | national |

### 1.6 Technical Onboarding
| Module | Actions | Scope |
|---|---|---|
| `tech_onboarding` | V,C,U,D,F | national |
| `tech_onboarding_final` | V,C,U,D,F | national |
| `mfr_onboarding_new` | V,C,U,D,F | national |
| `mfr_onboarding_list` | V,C,U,D,F | national |

### 1.7 Tracking & Playback
| Module | Actions | Scope |
|---|---|---|
| `route_fixing` | V,C,U,D,F | national |
| `live_tracking` | V,C,U,D,F | national |
| `gps_tracking` | V,C,U,D,F | national |
| `gps_history` | V,C,U,D,F | national |
| `gps_clustering` | V,C,U,D,F | national |
| `history_playback` | V,C,U,D,F | national |
| `trip_viewer` | V,C,U,D,F | national |
| `trip_monitor` | V,C,U,D,F | national |
| `trip_management` | V,C,U,D,F | national |
| `route_management` | V,C,U,D,F | national |

### 1.8 VLTD Approval
| Module | Actions | Scope |
|---|---|---|
| `vltd_pending_model` | V,C,U,D,F | national |
| `vltd_pending_cop` | V,C,U,D,F | national |
| `vltd_approved_models` | V,C,U,D,F | national |
| `vltd_approved_cops` | V,C,U,D,F | national |

### 1.9 Whitelist & KYC
| Module | Actions | Scope |
|---|---|---|
| `wkyc_requests` | V,C,U,D,F | national |
| `wkyc_device_dashboard` | V,C,U,D,F | national |

### 1.10 POI
| Module | Actions | Scope |
|---|---|---|
| `poi_viewer` | V,C,U,D,F | national |
| `poi_management` | V,C,U,D,F | national |

### 1.11 Reports
| Module | Actions | Scope |
|---|---|---|
| `reports` | V,C,U,D,F | national |
| `report_sos` | V,C,U,D,F | national |
| `report_notices` | V,C,U,D,F | national |
| `report_users` | V,C,U,D,F | national |
| `report_state_admin` | V,C,U,D,F | national |
| `report_manufacturer` | V,C,U,D,F | national |
| `report_sos_admin` | V,C,U,D,F | national |
| `report_m2m_provider` | V,C,U,D,F | national |
| `report_dealers` | V,C,U,D,F | national |
| `report_vehicle_owner` | V,C,U,D,F | national |
| `report_dto` | V,C,U,D,F | national |
| `report_gps_log` | V,C,U,D,F | national |
| `report_activation_log` | V,C,U,D,F | national |
| `report_emergency_data` | V,C,U,D,F | national |
| `report_health_packet` | V,C,U,D,F | national |
| `report_event_data` | V,C,U,D,F | national |
| `report_activated_device` | V,C,U,D,F | national |
| `report_alert` | V,C,U,D,F | national |
| `report_poi` | V,C,U,D,F | national |
| `report_incident` | V,C,U,D,F | national |
| `report_device_health` | V,C,U,D,F | national |
| `report_user_stats` | V,C,U,D,F | national |
| `report_violation` | V,C,U,D,F | national |
| `report_sos_users` | V,C,U,D,F | national |
| `report_sos_call_list` | V,C,U,D,F | national |
| `report_stock` | V,C,U,D,F | national |
| `report_fitment` | V,C,U,D,F | national |
| `report_device` | V,C,U,D,F | national |

### 1.12 Settings
| Module | Actions | Scope |
|---|---|---|
| `settings_management` | V,C,U,D,F | national |
| `settings_notice` | V,C,U,D,F | national |
| `settings_send_command` | V,C,U,D,F | national |
| `settings_vehicle_type` | V,C,U,D,F | national |
| `settings_vehicle_category` | V,C,U,D,F | national |
| `settings_alert_notif` | V,C,U,D,F | national |
| `settings_state_district` | V,C,U,D,F | national |
| `settings_ota_firmware` | V,C,U,D,F | national |
| `settings_archive_restore` | V,C,U,D,F | national |
| `settings_ip` | V,C,U,D,F | national |
| `settings_login` | V,C,U,D,F | national |
| `settings_permit_cond` | V,C,U,D,F | national |
| `settings_custom_alerts` | V,C,U,D,F | national |

### 1.13 Passenger Info System
| Module | Actions | Scope |
|---|---|---|
| `pis_bus_stops` | V,C,U,D,F | national |
| `pis_bus_routes` | V,C,U,D,F | national |
| `pis_bus_schedules` | V,C,U,D,F | national |

### 1.14 State Transport Analytics
| Module | Actions | Scope |
|---|---|---|
| `sta_trip_analysis` | V,C,U,D,F | national |
| `sta_driving_patterns` | V,C,U,D,F | national |
| `sta_vehicle_alerts` | V,C,U,D,F | national |
| `sta_pis_summary` | V,C,U,D,F | national |
| `sta_operational` | V,C,U,D,F | national |
| `sta_comparative` | V,C,U,D,F | national |
| `sta_resource_perf` | V,C,U,D,F | national |

### 1.15 Custom User Module
| Module | Actions | Scope |
|---|---|---|
| `cum_custom_roles` | V,C,U,D,F | national |
| `cum_feature_perms` | V,C,U,D,F | national |
| `cum_user_mgmt` | V,C,U,D,F | national |

### 1.16 Complaint Tickets
| Module | Actions | Scope |
|---|---|---|
| `complaint` | V,C,U,D,F | national |
| `ct_my_dashboard` | V,C,U,D,F | national |
| `ct_create` | V,C,U,D,F | national |
| `ct_all_tickets` | V,C,U,D,F | national |
| `ct_escalated` | V,C,U,D,F | national |

### 1.17 Device, Stock & Management
| Module | Actions | Scope |
|---|---|---|
| `device_management` | V,C,U,D,F | national |
| `device_stock` | V,C,U,D,F | national |
| `dm_create_model` | V,C,U,D,F | national |
| `dm_tac_cop` | V,C,U,D,F | national |
| `ds_individual` | V,C,U,D,F | national |
| `ds_bulk` | V,C,U,D,F | national |
| `ds_assign` | V,C,U,D,F | national |
| `dealer_m2m_status` | V,C,U,D,F | national |
| `dealer_request_m2m` | V,C,U,D,F | national |
| `dealer_tag_device` | V,C,U,D,F | national |
| `dealer_untagged` | V,C,U,D,F | national |
| `dealer_download_cert` | V,C,U,D,F | national |
| `dealer_management` | V,C,U,D,F | national |
| `vehicle_tagging` | V,C,U,D,F | national |
| `driver_management` | V,C,U,D,F | national |
| `owner_management` | V,C,U,D,F | national |
| `manufacturer_management` | V,C,U,D,F | national |
| `esim_management` | V,C,U,D,F | national |

### 1.18 Emergency & SOS
| Module | Actions | Scope |
|---|---|---|
| `emergency_management` | V,C,U,D,F | national |
| `emergency_teams` | V,C,U,D,F | national |
| `em_team_create` | V,C,U,D,F | national |
| `em_team_list` | V,C,U,D,F | national |
| `sos_call_list` | V,C,U,D,F | national |

### 1.19 Other Management
| Module | Actions | Scope |
|---|---|---|
| `alerts` | V,C,U,D,F | national |
| `notice_management` | V,C,U,D,F | national |
| `user_management` | V,C,U,D,F | national |

---

## 2. State Admin (`stateadmin`)

**Data scope:** State — assigned state only  
**Total modules:** 33

| Module | Actions | Scope |
|---|---|---|
| `dashboard` | V,F | state |
| `dashboard_central` | V,F | state |
| `cn_dto` | V,C,F | state |
| `tech_onboarding_final` | V,C,F | state |
| `route_fixing` | V,F | state |
| `live_tracking` | V,F | state |
| `gps_tracking` | V,F | state |
| `gps_clustering` | V,F | state |
| `alerts` | V,F | state |
| `notice_management` | V,C,U,F | state |
| `report_dealers` | V,F | state |
| `report_vehicle_owner` | V,F | state |
| `report_dto` | V,F | state |
| `report_activated_device` | V,F | state |
| `report_alert` | V,F | state |
| `report_device_health` | V,F | state |
| `reports` | V,F | state |
| `wkyc_requests` | V,C,F | state |
| `wkyc_device_dashboard` | V,F | state |
| `sta_trip_analysis` | V,F | state |
| `sta_driving_patterns` | V,F | state |
| `sta_vehicle_alerts` | V,F | state |
| `sta_pis_summary` | V,F | state |
| `sta_operational` | V,F | state |
| `sta_comparative` | V,F | state |
| `sta_resource_perf` | V,F | state |
| `pis_bus_stops` | V,C,U,F | state |
| `pis_bus_routes` | V,C,U,F | state |
| `pis_bus_schedules` | V,C,U,F | state |
| `driver_management` | V,F | state |
| `complaint` | V,U,F | national |
| `user_management` | V,F | state |
| `settings_management` | V,F | state |

---

## 3. M2M Provider (`esimprovider`)

**Data scope:** Manufacturer — own company's records  
**Total modules:** 10

| Module | Actions | Scope |
|---|---|---|
| `dashboard` | V | national |
| `m2m_pending` | V,U,F | manufacturer |
| `m2m_rejected` | V,F | manufacturer |
| `m2m_accepted` | V,F | manufacturer |
| `wkyc_requests` | V,C,F | manufacturer |
| `wkyc_device_dashboard` | V,F | manufacturer |
| `device_stock` | V,U,F | national |
| `esim_management` | V,C,U,F | national |
| `reports` | V,F | national |
| `notice_management` | V | national |

---

## 4. Manufacturer (`devicemanufacture`)

**Data scope:** Manufacturer — own company's devices  
**Total modules:** 29

| Module | Actions | Scope |
|---|---|---|
| `dashboard` | V | manufacturer |
| `cn_dealer` | V,C,F | manufacturer |
| `dm_create_model` | V,C,U,F | manufacturer |
| `dm_tac_cop` | V,C,U,F | manufacturer |
| `mfr_onboarding_new` | V,C,F | manufacturer |
| `mfr_onboarding_list` | V,F | manufacturer |
| `ds_individual` | V,C,U,F | manufacturer |
| `ds_bulk` | V,C,U,F | manufacturer |
| `ds_assign` | V,C,F | manufacturer |
| `report_dealers` | V,F | manufacturer |
| `report_device` | V,F | manufacturer |
| `report_alert` | V,F | manufacturer |
| `reports` | V,F | manufacturer |
| `settings_ota_firmware` | V,U,F | manufacturer |
| `settings_management` | V | manufacturer |
| `ct_my_dashboard` | V,F | manufacturer |
| `ct_create` | V,C,F | manufacturer |
| `ct_all_tickets` | V,F | manufacturer |
| `ct_escalated` | V,F | manufacturer |
| `complaint` | V | manufacturer |
| `wkyc_requests` | V,C,F | manufacturer |
| `wkyc_device_dashboard` | V,F | manufacturer |
| `device_management` | V,C,U,F | manufacturer |
| `device_stock` | V,C,U,F | manufacturer |
| `manufacturer_management` | V,C,U,D,F | manufacturer |
| `alerts` | V,F | manufacturer |
| `notice_management` | V | manufacturer |
| `user_management` | V,C,F | manufacturer |
| `vehicle_tagging` | V | manufacturer |

---

## 5. SOS Admin (`sosadmin`)

**Data scope:** National for SOS functions; State for tracking  
**Total modules:** 24

| Module | Actions | Scope |
|---|---|---|
| `dashboard` | V | state |
| `dashboard_central` | V,F | national |
| `cn_sos_user` | V,C,F | national |
| `em_team_create` | V,C,U,D,F | national |
| `em_team_list` | V,F | national |
| `report_sos_users` | V,F | national |
| `report_sos` | V,F | national |
| `report_sos_call_list` | V,F | national |
| `ct_my_dashboard` | V,F | national |
| `ct_create` | V,C,F | national |
| `ct_all_tickets` | V,F | national |
| `ct_escalated` | V,F | national |
| `complaint` | V,U,F | national |
| `emergency_management` | V,C,U,F | state |
| `emergency_teams` | V,C,U,F | state |
| `gps_tracking` | V,F | state |
| `gps_history` | V,F | state |
| `gps_clustering` | V,F | state |
| `poi_management` | V,F | state |
| `alerts` | V,F | state |
| `reports` | V,F | state |
| `notice_management` | V,C | state |
| `user_management` | V,C,F | state |
| `vehicle_tagging` | V | state |

---

## 6. DTO (`dtorto`)

**Data scope:** District — assigned district  
**Total modules:** 19

| Module | Actions | Scope |
|---|---|---|
| `dashboard` | V | district |
| `route_fixing` | V,F | district |
| `live_tracking` | V,F | district |
| `gps_tracking` | V,F | district |
| `gps_history` | V,F | district |
| `gps_clustering` | V,F | district |
| `history_playback` | V,F | district |
| `trip_viewer` | V,F | district |
| `report_device` | V,F | district |
| `report_activated_device` | V,F | district |
| `report_alert` | V,F | district |
| `reports` | V,F | district |
| `pis_bus_stops` | V,F | district |
| `pis_bus_routes` | V,F | district |
| `pis_bus_schedules` | V,F | district |
| `poi_management` | V,F | district |
| `alerts` | V,F | district |
| `notice_management` | V | district |
| `vehicle_tagging` | V,F | district |

---

## 7. Dealer (`dealer`)

**Data scope:** Dealer — own handled devices  
**Total modules:** 21

| Module | Actions | Scope |
|---|---|---|
| `dashboard` | V | dealer |
| `cn_vehicle_owner` | V,C,F | dealer |
| `dealer_m2m_status` | V,F | dealer |
| `dealer_request_m2m` | V,C,F | dealer |
| `dealer_tag_device` | V,C,U,F | dealer |
| `dealer_untagged` | V,F | dealer |
| `dealer_download_cert` | V,F | dealer |
| `report_stock` | V,F | dealer |
| `report_fitment` | V,F | dealer |
| `report_vehicle_owner` | V,F | dealer |
| `reports` | V,F | dealer |
| `settings_ip` | V,U,F | dealer |
| `settings_management` | V | dealer |
| `wkyc_requests` | V,C,F | dealer |
| `wkyc_device_dashboard` | V,F | dealer |
| `dealer_management` | V | dealer |
| `owner_management` | V,C,F | dealer |
| `gps_clustering` | V,F | dealer |
| `alerts` | V,F | dealer |
| `notice_management` | V | dealer |
| `user_management` | V,C,F | dealer |

---

## 8. Vehicle Owner (`owner`)

**Data scope:** Owner — own vehicles only  
**Total modules:** 22

| Module | Actions | Scope |
|---|---|---|
| `dashboard` | V | owner |
| `route_fixing` | V,F | owner |
| `trip_monitor` | V,F | owner |
| `live_tracking` | V,F | owner |
| `gps_tracking` | V,F | owner |
| `gps_history` | V,F | owner |
| `gps_clustering` | V,F | owner |
| `history_playback` | V,F | owner |
| `trip_viewer` | V,F | owner |
| `trip_management` | V,C,U,F | owner |
| `route_management` | V,C,U,F | owner |
| `poi_viewer` | V,F | owner |
| `poi_management` | V,C,U,F | owner |
| `report_alert` | V,F | owner |
| `report_poi` | V,F | owner |
| `reports` | V,F | owner |
| `pis_bus_schedules` | V,F | owner |
| `driver_management` | V,C,U,F | owner |
| `alerts` | V,F | owner |
| `notice_management` | V | owner |
| `owner_management` | V | owner |
| `vehicle_tagging` | V,F | owner |

---

## 9. Team Lead (`teamleader`)

**Data scope:** State for SOS / complaint; Self for core functions  
**Total modules:** 12

| Module | Actions | Scope |
|---|---|---|
| `dashboard` | V | self |
| `sos_call_list` | V,F | state |
| `ct_my_dashboard` | V,F | state |
| `ct_create` | V,C,F | state |
| `ct_all_tickets` | V,F | state |
| `ct_escalated` | V,F | state |
| `complaint` | V,U,F | national |
| `gps_tracking` | V,F | state |
| `emergency_management` | V,U,F | self |
| `emergency_teams` | V | self |
| `alerts` | V | self |
| `manufacturer_management` | V,F | national |

---

## 10. Desk Executive (`sosexecutive`)

**Data scope:** Self  
**Total modules:** 9

| Module | Actions | Scope |
|---|---|---|
| `dashboard` | V | self |
| `sos_call_list` | V,F | self |
| `complaint` | V,U,F | national |
| `gps_tracking` | V,F | state |
| `gps_history` | V | state |
| `gps_clustering` | V | state |
| `emergency_management` | V,U | self |
| `alerts` | V | self |
| `manufacturer_management` | V,F | national |

---

## 11. Test Agency (`filment`)

**Data scope:** Self / National  
**Total modules:** 5

| Module | Actions | Scope |
|---|---|---|
| `dashboard` | V | national |
| `ta_view_models` | V,F | self |
| `device_stock` | V,C,U,F | national |
| `vehicle_tagging` | V,F | national |
| `notice_management` | V | national |

---

## 12. School Admin (`schooladmin`)

**Data scope:** Self for school modules; Owner scope for shared tracking  
**Total modules:** 17

| Module | Actions | Scope |
|---|---|---|
| `dashboard` | V | owner |
| `sbs_dashboard` | V,F | self |
| `sbs_bus_tagging` | V,C,U,F | self |
| `sbs_bus_tracking` | V,F | self |
| `sbs_route_mgmt` | V,C,U,F | self |
| `sbs_bus_assignment` | V,C,U,F | self |
| `sbs_profile_mgmt` | V,U,F | self |
| `sbs_create_trip` | V,C,F | self |
| `sbs_school_reports` | V,F | self |
| `gps_tracking` | V,F | owner |
| `gps_history` | V,F | owner |
| `driver_management` | V,C,U,F | owner |
| `trip_management` | V,F | owner |
| `vehicle_tagging` | V,F | owner |
| `alerts` | V,F | owner |
| `reports` | V,F | owner |
| `notice_management` | V | owner |

---

## 13. Parent User (`parentuser`)

**Data scope:** Self  
**Total modules:** 2

| Module | Actions | Scope |
|---|---|---|
| `dashboard` | V | owner |
| `sbs_parent_tracking` | V | self |

---

## 14. Cross-Role Module Access Matrix

The table below shows which builtin roles can **view** each module.  
`SA`=System Admin · `STA`=State Admin · `M2M`=M2M Provider · `MFR`=Manufacturer · `SOS`=SOS Admin · `DTO`=DTO · `DLR`=Dealer · `OWN`=Owner · `TL`=Team Lead · `DEX`=Desk Executive · `TA`=Test Agency · `SCH`=School Admin · `PAR`=Parent User

| Module | SA | STA | M2M | MFR | SOS | DTO | DLR | OWN | TL | DEX | TA | SCH | PAR |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `dashboard` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `dashboard_north` | ✓ | | | | | | | | | | | | |
| `dashboard_central` | ✓ | ✓ | | | ✓ | | | | | | | | |
| **School Bus System** | | | | | | | | | | | | | |
| `sbs_dashboard` | ✓ | | | | | | | | | | | ✓ | |
| `sbs_bus_tagging` | ✓ | | | | | | | | | | | ✓ | |
| `sbs_route_mgmt` | ✓ | | | | | | | | | | | ✓ | |
| `sbs_bus_assignment` | ✓ | | | | | | | | | | | ✓ | |
| `sbs_profile_mgmt` | ✓ | | | | | | | | | | | ✓ | |
| `sbs_school_reports` | ✓ | | | | | | | | | | | ✓ | |
| `sbs_create_school` | ✓ | | | | | | | | | | | | |
| `sbs_approve_school` | ✓ | | | | | | | | | | | | |
| `sbs_bus_tracking` | ✓ | | | | | | | | | | | ✓ | |
| `sbs_create_trip` | ✓ | | | | | | | | | | | ✓ | |
| `sbs_parent_tracking` | ✓ | | | | | | | | | | | | ✓ |
| **Test Agency** | | | | | | | | | | | | | |
| `ta_create_agency` | ✓ | | | | | | | | | | | | |
| `ta_agency_list` | ✓ | | | | | | | | | | | | |
| `ta_create_user` | ✓ | | | | | | | | | | | | |
| `ta_user_list` | ✓ | | | | | | | | | | | | |
| `ta_view_models` | ✓ | | | | | | | | | | ✓ | | |
| **Create New** | | | | | | | | | | | | | |
| `cn_state_admin` | ✓ | | | | | | | | | | | | |
| `cn_m2m_provider` | ✓ | | | | | | | | | | | | |
| `cn_manufacturer` | ✓ | | | | | | | | | | | | |
| `cn_sos_admin` | ✓ | | | | | | | | | | | | |
| `cn_system_admin` | ✓ | | | | | | | | | | | | |
| `cn_dto` | ✓ | ✓ | | | | | | | | | | | |
| `cn_dealer` | ✓ | | | ✓ | | | | | | | | | |
| `cn_sos_user` | ✓ | | | | ✓ | | | | | | | | |
| `cn_vehicle_owner` | ✓ | | | | | | ✓ | | | | | | |
| **M2M** | | | | | | | | | | | | | |
| `m2m_registration` | ✓ | | | | | | | | | | | | |
| `m2m_pending` | ✓ | | ✓ | | | | | | | | | | |
| `m2m_rejected` | ✓ | | ✓ | | | | | | | | | | |
| `m2m_accepted` | ✓ | | ✓ | | | | | | | | | | |
| `mfr_vlt_requests` | ✓ | | | | | | | | | | | | |
| `mfr_ais140_requests` | ✓ | | | | | | | | | | | | |
| **Technical Onboarding** | | | | | | | | | | | | | |
| `tech_onboarding` | ✓ | | | | | | | | | | | | |
| `tech_onboarding_final` | ✓ | ✓ | | | | | | | | | | | |
| `mfr_onboarding_new` | ✓ | | | ✓ | | | | | | | | | |
| `mfr_onboarding_list` | ✓ | | | ✓ | | | | | | | | | |
| **Tracking** | | | | | | | | | | | | | |
| `route_fixing` | ✓ | ✓ | | | | ✓ | | ✓ | | | | | |
| `live_tracking` | ✓ | ✓ | | | | ✓ | | ✓ | | | | | |
| `history_playback` | ✓ | | | | | ✓ | | ✓ | | | | | |
| `trip_viewer` | ✓ | | | | | ✓ | | ✓ | | | | | |
| `trip_monitor` | ✓ | | | | | | | ✓ | | | | | |
| `gps_tracking` | ✓ | ✓ | | | ✓ | ✓ | | ✓ | ✓ | ✓ | | ✓ | |
| `gps_history` | ✓ | | | | ✓ | ✓ | | ✓ | | ✓ | | ✓ | |
| `gps_clustering` | ✓ | ✓ | | | ✓ | ✓ | ✓ | ✓ | | ✓ | | | |
| `route_management` | ✓ | | | | | | | ✓ | | | | | |
| `trip_management` | ✓ | | | | | | | ✓ | | | ✓ | | |
| **VLTD Approval** | | | | | | | | | | | | | |
| `vltd_pending_model` | ✓ | | | | | | | | | | | | |
| `vltd_pending_cop` | ✓ | | | | | | | | | | | | |
| `vltd_approved_models` | ✓ | | | | | | | | | | | | |
| `vltd_approved_cops` | ✓ | | | | | | | | | | | | |
| **Whitelist & KYC** | | | | | | | | | | | | | |
| `wkyc_requests` | ✓ | ✓ | ✓ | ✓ | | | ✓ | | | | | | |
| `wkyc_device_dashboard` | ✓ | ✓ | ✓ | ✓ | | | ✓ | | | | | | |
| **POI** | | | | | | | | | | | | | |
| `poi_viewer` | ✓ | | | | | | | ✓ | | | | | |
| `poi_management` | ✓ | | | | ✓ | ✓ | | ✓ | | | | | |
| **Reports** | | | | | | | | | | | | | |
| `reports` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | | | | ✓ | |
| `report_sos` | ✓ | | | | ✓ | | | | | | | | |
| `report_notices` | ✓ | | | | | | | | | | | | |
| `report_users` | ✓ | | | | | | | | | | | | |
| `report_state_admin` | ✓ | | | | | | | | | | | | |
| `report_manufacturer` | ✓ | | | | | | | | | | | | |
| `report_sos_admin` | ✓ | | | | | | | | | | | | |
| `report_m2m_provider` | ✓ | | | | | | | | | | | | |
| `report_dealers` | ✓ | ✓ | | ✓ | | | | | | | | | |
| `report_vehicle_owner` | ✓ | ✓ | | | | | ✓ | | | | | | |
| `report_dto` | ✓ | ✓ | | | | | | | | | | | |
| `report_gps_log` | ✓ | | | | | | | | | | | | |
| `report_activation_log` | ✓ | | | | | | | | | | | | |
| `report_emergency_data` | ✓ | | | | | | | | | | | | |
| `report_health_packet` | ✓ | | | | | | | | | | | | |
| `report_event_data` | ✓ | | | | | | | | | | | | |
| `report_activated_device` | ✓ | ✓ | | | | ✓ | | | | | | | |
| `report_alert` | ✓ | ✓ | | ✓ | | ✓ | | ✓ | | | | | |
| `report_poi` | ✓ | | | | | | | ✓ | | | | | |
| `report_incident` | ✓ | | | | | | | | | | | | |
| `report_device_health` | ✓ | ✓ | | | | | | | | | | | |
| `report_user_stats` | ✓ | | | | | | | | | | | | |
| `report_violation` | ✓ | | | | | | | | | | | | |
| `report_sos_users` | ✓ | | | | ✓ | | | | | | | | |
| `report_sos_call_list` | ✓ | | | | ✓ | | | | | | | | |
| `report_stock` | ✓ | | | | | | ✓ | | | | | | |
| `report_fitment` | ✓ | | | | | | ✓ | | | | | | |
| `report_device` | ✓ | | | ✓ | | ✓ | | | | | | | |
| **Settings** | | | | | | | | | | | | | |
| `settings_management` | ✓ | ✓ | | ✓ | | | ✓ | | | | | | |
| `settings_notice` | ✓ | | | | | | | | | | | | |
| `settings_send_command` | ✓ | | | | | | | | | | | | |
| `settings_vehicle_type` | ✓ | | | | | | | | | | | | |
| `settings_vehicle_category` | ✓ | | | | | | | | | | | | |
| `settings_alert_notif` | ✓ | | | | | | | | | | | | |
| `settings_state_district` | ✓ | | | | | | | | | | | | |
| `settings_ota_firmware` | ✓ | | | ✓ | | | | | | | | | |
| `settings_archive_restore` | ✓ | | | | | | | | | | | | |
| `settings_ip` | ✓ | | | | | | ✓ | | | | | | |
| `settings_login` | ✓ | | | | | | | | | | | | |
| `settings_permit_cond` | ✓ | | | | | | | | | | | | |
| `settings_custom_alerts` | ✓ | | | | | | | | | | | | |
| **PIS** | | | | | | | | | | | | | |
| `pis_bus_stops` | ✓ | ✓ | | | | ✓ | | | | | | | |
| `pis_bus_routes` | ✓ | ✓ | | | | ✓ | | | | | | | |
| `pis_bus_schedules` | ✓ | ✓ | | | | ✓ | | ✓ | | | | | |
| **State Transport Analytics** | | | | | | | | | | | | | |
| `sta_trip_analysis` | ✓ | ✓ | | | | | | | | | | | |
| `sta_driving_patterns` | ✓ | ✓ | | | | | | | | | | | |
| `sta_vehicle_alerts` | ✓ | ✓ | | | | | | | | | | | |
| `sta_pis_summary` | ✓ | ✓ | | | | | | | | | | | |
| `sta_operational` | ✓ | ✓ | | | | | | | | | | | |
| `sta_comparative` | ✓ | ✓ | | | | | | | | | | | |
| `sta_resource_perf` | ✓ | ✓ | | | | | | | | | | | |
| **Custom User Module** | | | | | | | | | | | | | |
| `cum_custom_roles` | ✓ | | | | | | | | | | | | |
| `cum_feature_perms` | ✓ | | | | | | | | | | | | |
| `cum_user_mgmt` | ✓ | | | | | | | | | | | | |
| **Complaint Tickets** | | | | | | | | | | | | | |
| `complaint` | ✓ | ✓ | | ✓ | ✓ | | | | ✓ | ✓ | | | |
| `ct_my_dashboard` | ✓ | | | ✓ | ✓ | | | | ✓ | | | | |
| `ct_create` | ✓ | | | ✓ | ✓ | | | | ✓ | | | | |
| `ct_all_tickets` | ✓ | | | ✓ | ✓ | | | | ✓ | | | | |
| `ct_escalated` | ✓ | | | ✓ | ✓ | | | | ✓ | | | | |
| **Device Model & Stock** | | | | | | | | | | | | | |
| `device_management` | ✓ | | | ✓ | | | | | | | | | |
| `device_stock` | ✓ | | ✓ | ✓ | | | | | | | ✓ | | |
| `dm_create_model` | ✓ | | | ✓ | | | | | | | | | |
| `dm_tac_cop` | ✓ | | | ✓ | | | | | | | | | |
| `ds_individual` | ✓ | | | ✓ | | | | | | | | | |
| `ds_bulk` | ✓ | | | ✓ | | | | | | | | | |
| `ds_assign` | ✓ | | | ✓ | | | | | | | | | |
| **Dealer** | | | | | | | | | | | | | |
| `dealer_management` | ✓ | | | | | | ✓ | | | | | | |
| `dealer_m2m_status` | ✓ | | | | | | ✓ | | | | | | |
| `dealer_request_m2m` | ✓ | | | | | | ✓ | | | | | | |
| `dealer_tag_device` | ✓ | | | | | | ✓ | | | | | | |
| `dealer_untagged` | ✓ | | | | | | ✓ | | | | | | |
| `dealer_download_cert` | ✓ | | | | | | ✓ | | | | | | |
| **Emergency & SOS** | | | | | | | | | | | | | |
| `emergency_management` | ✓ | | | | ✓ | | | | ✓ | ✓ | | | |
| `emergency_teams` | ✓ | | | | ✓ | | | | ✓ | | | | |
| `em_team_create` | ✓ | | | | ✓ | | | | | | | | |
| `em_team_list` | ✓ | | | | ✓ | | | | | | | | |
| `sos_call_list` | ✓ | | | | | | | | ✓ | ✓ | | | |
| **Other** | | | | | | | | | | | | | |
| `alerts` | ✓ | ✓ | | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | | ✓ | |
| `notice_management` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | | | ✓ | ✓ | |
| `user_management` | ✓ | ✓ | | ✓ | ✓ | | ✓ | | | | | | |
| `vehicle_tagging` | ✓ | | | ✓ | ✓ | ✓ | | ✓ | | | ✓ | ✓ | |
| `driver_management` | ✓ | ✓ | | | | | | ✓ | | | | ✓ | |
| `owner_management` | ✓ | | | | | | ✓ | ✓ | | | | | |
| `manufacturer_management` | ✓ | | | ✓ | | | | | ✓ | ✓ | | | |
| `esim_management` | ✓ | | ✓ | | | | | | | | | | |
| `stateadmin_management` | — | — | — | — | — | — | — | — | — | — | — | — | — |

---

## 15. Modules Not Yet Assigned to Any Non-Superadmin User

These modules exist in the system but are currently **only accessible by System Admin**. They represent functionality reserved for superadmin-only operation or features where non-superadmin access has not yet been configured.

### 15.1 Completely Unassigned (no role has access, including superadmin)
| Module | Display Name | Notes |
|---|---|---|
| `stateadmin_management` | State Admin Management | Legacy module — superseded by `cn_state_admin` + `stateadmin` role management; no active permissions |

### 15.2 Superadmin-Only Modules (pending role assignment)
> These are fully implemented UI modules. Grant access via the RBAC management API: `POST /api/rbac/roles/permissions/update/`

| Module | Display Name | Likely Candidate Role(s) |
|---|---|---|
| `dashboard_north` | North Dashboard | *System Admin exclusive* |
| `ta_create_agency` | Create Agency Details | System Admin only |
| `ta_agency_list` | Test Agency Details List | System Admin only |
| `ta_create_user` | Create Agency User | System Admin only |
| `ta_user_list` | Test Agency User List | System Admin only |
| `cn_state_admin` | Create State Admin | System Admin only |
| `cn_m2m_provider` | Create M2M Service Provider | System Admin only |
| `cn_manufacturer` | Create Manufacturer | System Admin only |
| `cn_sos_admin` | Create SOS Admin | System Admin only |
| `cn_system_admin` | Create System Admin | System Admin only |
| `m2m_registration` | M2M Registration Requests | System Admin only |
| `mfr_vlt_requests` | Vehicle Manufacturer Requests | System Admin only |
| `mfr_ais140_requests` | AIS-140 Manufacturer Requests | System Admin only |
| `tech_onboarding` | Technical Onboarding Requests | System Admin only |
| `vltd_pending_model` | VLTD — Pending Model Approval | System Admin only |
| `vltd_pending_cop` | VLTD — Pending COP | System Admin only |
| `vltd_approved_models` | VLTD — Approved Models | System Admin only |
| `vltd_approved_cops` | VLTD — Approved COPs | System Admin only |
| `report_notices` | Report — Notices | System Admin only |
| `report_users` | Report — Users | System Admin only |
| `report_state_admin` | Report — State Admin | System Admin only |
| `report_manufacturer` | Report — Manufacturer | System Admin only |
| `report_sos_admin` | Report — SOS Admin | System Admin only |
| `report_m2m_provider` | Report — M2M Provider | System Admin only |
| `report_gps_log` | Report — GPS Data Log | System Admin only |
| `report_activation_log` | Report — Activation Log | System Admin only |
| `report_emergency_data` | Report — Emergency Data Logs | System Admin only |
| `report_health_packet` | Report — Health Packet Log | System Admin only |
| `report_event_data` | Report — Event Data Log | System Admin only |
| `report_incident` | Report — Incident | System Admin only |
| `report_user_stats` | Report — User Statistics | System Admin only |
| `report_violation` | Report — Violation | System Admin only |
| `settings_notice` | Settings — Notice | System Admin only |
| `settings_send_command` | Settings — Send Command | System Admin only |
| `settings_vehicle_type` | Settings — Vehicle Type | System Admin only |
| `settings_vehicle_category` | Settings — Vehicle Category Code | System Admin only |
| `settings_alert_notif` | Settings — Alert Notification Mode | System Admin only |
| `settings_state_district` | Settings — State & District | System Admin only |
| `settings_archive_restore` | Settings — Archive & Restore | System Admin only |
| `settings_login` | Settings — Login Settings | System Admin only |
| `settings_permit_cond` | Settings — Permit Conditions | System Admin only |
| `settings_custom_alerts` | Settings — Custom Alerts | System Admin only |
| `cum_custom_roles` | Custom User — Role Management | System Admin only |
| `cum_feature_perms` | Custom User — Feature Permissions | System Admin only |
| `cum_user_mgmt` | Custom User — User Management | System Admin only |
| `sbs_create_school` | School Bus — Create School | System Admin only |
| `sbs_approve_school` | School Bus — Approve School | System Admin only |
| `trip_monitor` | Trip Monitor | Currently Owner only ✓ |

---

*To grant any of the above to another role, use the runtime API:*
```
POST /api/rbac/roles/permissions/update/
{
  "role_code": "<code>",
  "module": "<module_code>",
  "can_view": true,
  "can_create": false,
  "can_update": false,
  "can_delete": false,
  "can_filter": true,
  "show_in_menu": true,
  "data_scope": "<scope>"
}
```
