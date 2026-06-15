"""
Seed RolePermissionConfig rows for all new UI-navigation modules introduced
in the granular menu redesign.

New modules are laid out in four groups:
  - Dashboard variants (north, central)
  - School Bus System sub-menus  (sbs_*)
  - Test Agency sub-menus        (ta_*)
  - Create-New user provisioning  (cn_*)
  - M2M lifecycle                 (m2m_*)
  - Manufacturer requests         (mfr_*)
  - Technical onboarding          (tech_*, mfr_onboarding_*)
  - Tracking / playback           (route_fixing, live_tracking, …)
  - VLTD Approval                 (vltd_*)
  - Whitelist & KYC               (wkyc_*)
  - POI Viewer
  - Report sub-modules            (report_*)
  - Settings sub-modules          (settings_*)
  - Passenger Info System         (pis_*)
  - State Transport Analytics     (sta_*)
  - Custom User Module            (cum_*)
  - Complaint Ticket sub-menus    (ct_*)
  - Device Model / Stock          (dm_*, ds_*)
  - Dealer-specific               (dealer_*)
  - EM Team                       (em_team_*)
  - SOS Call List                 (sos_call_list)

Role → access mapping
─────────────────────
superadmin          national, full CRUD on every new module
stateadmin          state scope, selected modules
esimprovider (M2M)  manufacturer scope, M2M lifecycle + KYC
devicemanufacture   manufacturer scope, device / stock / onboarding / tickets
sosadmin            national scope, SOS-specific modules
dtorto (DTO)        district scope, tracking + reports + PIS
dealer              dealer scope, tagging / M2M / reports / KYC
owner               owner scope, tracking / playback / viewer
teamleader          state scope, SOS call list + complaint tickets
sosexecutive        self scope, SOS call list
filment (Test Agcy) self scope, view assigned models
schooladmin         self scope, school bus sub-menus
parentuser          self scope, parent tracking
"""

from django.db import migrations

# ── New module codes only (already added to MODEL_CHOICES in models.py) ───────
# Columns: role_code, module, view, create, update, delete, filter, menu, scope

# ── Superadmin: national / full access on ALL new modules ─────────────────────
_SA_ALL = [
    # Dashboard
    'dashboard_north', 'dashboard_central',
    # School Bus System
    'sbs_dashboard', 'sbs_bus_tagging', 'sbs_route_mgmt', 'sbs_bus_assignment',
    'sbs_profile_mgmt', 'sbs_school_reports', 'sbs_create_school',
    'sbs_approve_school', 'sbs_bus_tracking', 'sbs_create_trip',
    'sbs_parent_tracking',
    # Test Agency
    'ta_create_agency', 'ta_agency_list', 'ta_create_user', 'ta_user_list',
    'ta_view_models',
    # Create New
    'cn_state_admin', 'cn_m2m_provider', 'cn_manufacturer', 'cn_sos_admin',
    'cn_system_admin', 'cn_dto', 'cn_dealer', 'cn_sos_user', 'cn_vehicle_owner',
    # M2M
    'm2m_registration', 'm2m_pending', 'm2m_rejected', 'm2m_accepted',
    # Manufacturer / AIS-140 Requests
    'mfr_vlt_requests', 'mfr_ais140_requests',
    # Technical Onboarding
    'tech_onboarding', 'tech_onboarding_final',
    'mfr_onboarding_new', 'mfr_onboarding_list',
    # Tracking
    'route_fixing', 'live_tracking', 'history_playback', 'trip_viewer',
    'trip_monitor',
    # VLTD
    'vltd_pending_model', 'vltd_pending_cop', 'vltd_approved_models',
    'vltd_approved_cops',
    # Whitelist & KYC
    'wkyc_requests', 'wkyc_device_dashboard',
    # POI
    'poi_viewer',
    # Reports
    'report_sos', 'report_notices', 'report_users', 'report_state_admin',
    'report_manufacturer', 'report_sos_admin', 'report_m2m_provider',
    'report_dealers', 'report_vehicle_owner', 'report_dto', 'report_gps_log',
    'report_activation_log', 'report_emergency_data', 'report_health_packet',
    'report_event_data', 'report_activated_device', 'report_alert', 'report_poi',
    'report_incident', 'report_device_health', 'report_user_stats',
    'report_violation', 'report_sos_users', 'report_sos_call_list',
    'report_stock', 'report_fitment', 'report_device',
    # Settings
    'settings_notice', 'settings_send_command', 'settings_vehicle_type',
    'settings_vehicle_category', 'settings_alert_notif', 'settings_state_district',
    'settings_ota_firmware', 'settings_archive_restore', 'settings_ip',
    'settings_login', 'settings_permit_cond', 'settings_custom_alerts',
    # PIS
    'pis_bus_stops', 'pis_bus_routes', 'pis_bus_schedules',
    # Analytics
    'sta_trip_analysis', 'sta_driving_patterns', 'sta_vehicle_alerts',
    'sta_pis_summary', 'sta_operational', 'sta_comparative', 'sta_resource_perf',
    # Custom User Module
    'cum_custom_roles', 'cum_feature_perms', 'cum_user_mgmt',
    # Complaint Tickets
    'ct_my_dashboard', 'ct_create', 'ct_all_tickets', 'ct_escalated',
    # Device Model & Stock
    'dm_create_model', 'dm_tac_cop',
    'ds_individual', 'ds_bulk', 'ds_assign',
    # Dealer
    'dealer_m2m_status', 'dealer_request_m2m', 'dealer_tag_device',
    'dealer_untagged', 'dealer_download_cert',
    # EM Team
    'em_team_create', 'em_team_list',
    # SOS
    'sos_call_list',
]

# Columns: role_code, module, view, create, update, delete, filter, menu, scope
PERMISSIONS = []

# Expand superadmin full-access rows
for _mod in _SA_ALL:
    PERMISSIONS.append(
        ('superadmin', _mod, True, True, True, True, True, True, 'national')
    )

# ── State Admin ───────────────────────────────────────────────────────────────
PERMISSIONS += [
    ('stateadmin', 'dashboard_central',       True, False, False, False, True, True, 'state'),
    ('stateadmin', 'cn_dto',                  True, True,  False, False, True, True, 'state'),
    ('stateadmin', 'tech_onboarding_final',   True, True,  False, False, True, True, 'state'),
    ('stateadmin', 'route_fixing',            True, False, False, False, True, True, 'state'),
    ('stateadmin', 'live_tracking',           True, False, False, False, True, True, 'state'),
    ('stateadmin', 'report_dealers',          True, False, False, False, True, True, 'state'),
    ('stateadmin', 'report_vehicle_owner',    True, False, False, False, True, True, 'state'),
    ('stateadmin', 'report_dto',              True, False, False, False, True, True, 'state'),
    ('stateadmin', 'report_activated_device', True, False, False, False, True, True, 'state'),
    ('stateadmin', 'report_alert',            True, False, False, False, True, True, 'state'),
    ('stateadmin', 'report_device_health',    True, False, False, False, True, True, 'state'),
    ('stateadmin', 'wkyc_requests',           True, True,  False, False, True, True, 'state'),
    ('stateadmin', 'wkyc_device_dashboard',   True, False, False, False, True, True, 'state'),
    ('stateadmin', 'sta_trip_analysis',       True, False, False, False, True, True, 'state'),
    ('stateadmin', 'sta_driving_patterns',    True, False, False, False, True, True, 'state'),
    ('stateadmin', 'sta_vehicle_alerts',      True, False, False, False, True, True, 'state'),
    ('stateadmin', 'sta_pis_summary',         True, False, False, False, True, True, 'state'),
    ('stateadmin', 'sta_operational',         True, False, False, False, True, True, 'state'),
    ('stateadmin', 'sta_comparative',         True, False, False, False, True, True, 'state'),
    ('stateadmin', 'sta_resource_perf',       True, False, False, False, True, True, 'state'),
    ('stateadmin', 'pis_bus_stops',           True, True,  True,  False, True, True, 'state'),
    ('stateadmin', 'pis_bus_routes',          True, True,  True,  False, True, True, 'state'),
    ('stateadmin', 'pis_bus_schedules',       True, True,  True,  False, True, True, 'state'),
]

# ── M2M / eSIM Provider ───────────────────────────────────────────────────────
PERMISSIONS += [
    ('esimprovider', 'm2m_pending',           True, False, True,  False, True, True, 'manufacturer'),
    ('esimprovider', 'm2m_rejected',          True, False, False, False, True, True, 'manufacturer'),
    ('esimprovider', 'm2m_accepted',          True, False, False, False, True, True, 'manufacturer'),
    ('esimprovider', 'wkyc_requests',         True, True,  False, False, True, True, 'manufacturer'),
    ('esimprovider', 'wkyc_device_dashboard', True, False, False, False, True, True, 'manufacturer'),
]

# ── Manufacturer ──────────────────────────────────────────────────────────────
PERMISSIONS += [
    ('devicemanufacture', 'cn_dealer',            True, True,  False, False, True, True, 'manufacturer'),
    ('devicemanufacture', 'dm_create_model',      True, True,  True,  False, True, True, 'manufacturer'),
    ('devicemanufacture', 'dm_tac_cop',           True, True,  True,  False, True, True, 'manufacturer'),
    ('devicemanufacture', 'mfr_onboarding_new',   True, True,  False, False, True, True, 'manufacturer'),
    ('devicemanufacture', 'mfr_onboarding_list',  True, False, False, False, True, True, 'manufacturer'),
    ('devicemanufacture', 'ds_individual',        True, True,  True,  False, True, True, 'manufacturer'),
    ('devicemanufacture', 'ds_bulk',              True, True,  True,  False, True, True, 'manufacturer'),
    ('devicemanufacture', 'ds_assign',            True, True,  False, False, True, True, 'manufacturer'),
    ('devicemanufacture', 'report_dealers',       True, False, False, False, True, True, 'manufacturer'),
    ('devicemanufacture', 'report_device',        True, False, False, False, True, True, 'manufacturer'),
    ('devicemanufacture', 'report_alert',         True, False, False, False, True, True, 'manufacturer'),
    ('devicemanufacture', 'settings_ota_firmware',True, False, True,  False, True, True, 'manufacturer'),
    ('devicemanufacture', 'ct_my_dashboard',      True, False, False, False, True, True, 'manufacturer'),
    ('devicemanufacture', 'ct_create',            True, True,  False, False, True, True, 'manufacturer'),
    ('devicemanufacture', 'ct_all_tickets',       True, False, False, False, True, True, 'manufacturer'),
    ('devicemanufacture', 'ct_escalated',         True, False, False, False, True, True, 'manufacturer'),
    ('devicemanufacture', 'wkyc_requests',        True, True,  False, False, True, True, 'manufacturer'),
    ('devicemanufacture', 'wkyc_device_dashboard',True, False, False, False, True, True, 'manufacturer'),
]

# ── SOS Admin ─────────────────────────────────────────────────────────────────
PERMISSIONS += [
    ('sosadmin', 'dashboard_central',    True, False, False, False, True, True, 'national'),
    ('sosadmin', 'cn_sos_user',          True, True,  False, False, True, True, 'national'),
    ('sosadmin', 'em_team_create',       True, True,  True,  True,  True, True, 'national'),
    ('sosadmin', 'em_team_list',         True, False, False, False, True, True, 'national'),
    ('sosadmin', 'report_sos_users',     True, False, False, False, True, True, 'national'),
    ('sosadmin', 'report_sos',           True, False, False, False, True, True, 'national'),
    ('sosadmin', 'report_sos_call_list', True, False, False, False, True, True, 'national'),
    ('sosadmin', 'ct_my_dashboard',      True, False, False, False, True, True, 'national'),
    ('sosadmin', 'ct_create',            True, True,  False, False, True, True, 'national'),
    ('sosadmin', 'ct_all_tickets',       True, False, False, False, True, True, 'national'),
    ('sosadmin', 'ct_escalated',         True, False, False, False, True, True, 'national'),
]

# ── DTO / RTO ─────────────────────────────────────────────────────────────────
PERMISSIONS += [
    ('dtorto', 'route_fixing',           True, False, False, False, True, True, 'district'),
    ('dtorto', 'live_tracking',          True, False, False, False, True, True, 'district'),
    ('dtorto', 'history_playback',       True, False, False, False, True, True, 'district'),
    ('dtorto', 'trip_viewer',            True, False, False, False, True, True, 'district'),
    ('dtorto', 'report_device',          True, False, False, False, True, True, 'district'),
    ('dtorto', 'report_activated_device',True, False, False, False, True, True, 'district'),
    ('dtorto', 'report_alert',           True, False, False, False, True, True, 'district'),
    ('dtorto', 'pis_bus_stops',          True, False, False, False, True, True, 'district'),
    ('dtorto', 'pis_bus_routes',         True, False, False, False, True, True, 'district'),
    ('dtorto', 'pis_bus_schedules',      True, False, False, False, True, True, 'district'),
]

# ── Dealer ────────────────────────────────────────────────────────────────────
PERMISSIONS += [
    ('dealer', 'cn_vehicle_owner',       True, True,  False, False, True, True, 'dealer'),
    ('dealer', 'dealer_m2m_status',      True, False, False, False, True, True, 'dealer'),
    ('dealer', 'dealer_request_m2m',     True, True,  False, False, True, True, 'dealer'),
    ('dealer', 'dealer_tag_device',      True, True,  True,  False, True, True, 'dealer'),
    ('dealer', 'dealer_untagged',        True, False, False, False, True, True, 'dealer'),
    ('dealer', 'dealer_download_cert',   True, False, False, False, True, True, 'dealer'),
    ('dealer', 'report_stock',           True, False, False, False, True, True, 'dealer'),
    ('dealer', 'report_fitment',         True, False, False, False, True, True, 'dealer'),
    ('dealer', 'report_vehicle_owner',   True, False, False, False, True, True, 'dealer'),
    ('dealer', 'settings_ip',            True, False, True,  False, True, True, 'dealer'),
    ('dealer', 'wkyc_requests',          True, True,  False, False, True, True, 'dealer'),
    ('dealer', 'wkyc_device_dashboard',  True, False, False, False, True, True, 'dealer'),
]

# ── Vehicle Owner ─────────────────────────────────────────────────────────────
PERMISSIONS += [
    ('owner', 'route_fixing',            True, False, False, False, True, True, 'owner'),
    ('owner', 'trip_monitor',            True, False, False, False, True, True, 'owner'),
    ('owner', 'live_tracking',           True, False, False, False, True, True, 'owner'),
    ('owner', 'history_playback',        True, False, False, False, True, True, 'owner'),
    ('owner', 'trip_viewer',             True, False, False, False, True, True, 'owner'),
    ('owner', 'poi_viewer',              True, False, False, False, True, True, 'owner'),
    ('owner', 'report_alert',            True, False, False, False, True, True, 'owner'),
    ('owner', 'report_poi',              True, False, False, False, True, True, 'owner'),
    ('owner', 'pis_bus_schedules',       True, False, False, False, True, True, 'owner'),
]

# ── Team Leader ───────────────────────────────────────────────────────────────
PERMISSIONS += [
    ('teamleader', 'sos_call_list',      True, False, False, False, True, True, 'state'),
    ('teamleader', 'ct_my_dashboard',    True, False, False, False, True, True, 'state'),
    ('teamleader', 'ct_create',          True, True,  False, False, True, True, 'state'),
    ('teamleader', 'ct_all_tickets',     True, False, False, False, True, True, 'state'),
    ('teamleader', 'ct_escalated',       True, False, False, False, True, True, 'state'),
]

# ── Desk Executive (sosexecutive) ─────────────────────────────────────────────
PERMISSIONS += [
    ('sosexecutive', 'sos_call_list',    True, False, False, False, True, True, 'self'),
]

# ── Test Agency (filment) ─────────────────────────────────────────────────────
PERMISSIONS += [
    ('filment', 'ta_view_models',        True, False, False, False, True, True, 'self'),
]

# ── School Admin ──────────────────────────────────────────────────────────────
PERMISSIONS += [
    ('schooladmin', 'sbs_dashboard',     True, False, False, False, True, True, 'self'),
    ('schooladmin', 'sbs_bus_tagging',   True, True,  True,  False, True, True, 'self'),
    ('schooladmin', 'sbs_bus_tracking',  True, False, False, False, True, True, 'self'),
    ('schooladmin', 'sbs_route_mgmt',    True, True,  True,  False, True, True, 'self'),
    ('schooladmin', 'sbs_bus_assignment',True, True,  True,  False, True, True, 'self'),
    ('schooladmin', 'sbs_profile_mgmt',  True, False, True,  False, True, True, 'self'),
    ('schooladmin', 'sbs_create_trip',   True, True,  False, False, True, True, 'self'),
    ('schooladmin', 'sbs_school_reports',True, False, False, False, True, True, 'self'),
]

# ── Parent User ───────────────────────────────────────────────────────────────
PERMISSIONS += [
    ('parentuser', 'sbs_parent_tracking', True, False, False, False, False, True, 'self'),
]


def seed(apps, schema_editor):
    UserRoleType = apps.get_model('skytron_api', 'UserRoleType')
    RolePermissionConfig = apps.get_model('skytron_api', 'RolePermissionConfig')

    for (role_code, module,
         can_view, can_create, can_update, can_delete,
         can_filter, show_in_menu, data_scope) in PERMISSIONS:

        role = UserRoleType.objects.filter(code=role_code).first()
        if role is None:
            continue  # skip unknown custom roles

        RolePermissionConfig.objects.get_or_create(
            role=role,
            module=module,
            defaults={
                'can_view':      can_view,
                'can_create':    can_create,
                'can_update':    can_update,
                'can_delete':    can_delete,
                'can_filter':    can_filter,
                'show_in_menu':  show_in_menu,
                'data_scope':    data_scope,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('skytron_api', '0059_settings_permitmaster'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
