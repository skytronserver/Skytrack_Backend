# Dashboard APIs Documentation

## Base URL
https://api.gromed.in/api

## Access
All dashboard APIs listed below are publicly accessible (no authentication token required).

## Common Notes
- Methods supported are mentioned per API.
- GET query params and POST JSON body are both supported for most dashboard APIs.
- Time values are ISO-8601 timestamps.
- Vehicle online/offline logic uses the latest GPS timestamp with a 15-minute threshold.

---

## 1) Vehicle Monitoring Dashboard

### Endpoint
- GET, POST
- /dashboard/vehicle-monitoring/

### Purpose
Returns top-level vehicle monitoring KPIs.

### Inputs
- state_id (optional, integer)
- district_id (optional, integer)
- vehicle_category_id (optional, integer)

### Response Shape
- filters_applied
- dashboard_metrics
  - total_active_device_tags
  - online_device_tags
  - offline_device_tags
  - total_emergency_alerts_today
  - total_other_alerts_today
- timestamp

### Curl (GET)
curl -X GET "https://api.gromed.in/api/dashboard/vehicle-monitoring/?state_id=1&district_id=5&vehicle_category_id=2"

### Curl (POST)
curl -X POST "https://api.gromed.in/api/dashboard/vehicle-monitoring/" \
  -H "Content-Type: application/json" \
  -d '{
    "state_id": 1,
    "district_id": 5,
    "vehicle_category_id": 2
  }'

---

## 2) Dashboard Filter Options

### Endpoint
- GET
- /dashboard/filter-options/

### Purpose
Returns filter dropdown data for frontend.

### Inputs
None

### Response Shape
- states[]: id, name
- districts[]: id, name, code, state_id, state_name
- vehicle_categories[]: id, name, max_speed, warn_speed
- timestamp

### Curl
curl -X GET "https://api.gromed.in/api/dashboard/filter-options/"

---

## 3) Area-wise Device Tag Count (Drilldown)

### Endpoint
- GET, POST
- /dashboard/areawise-device-count/

### Purpose
Single endpoint supporting district -> city -> locality -> device drilldown.

### Common Optional Filters (all levels)
- state_id (optional, integer)
- vehicle_category_id (optional, integer)

### Level 1: District List

#### Input
No district_name/city_name/locality_name

#### Response Shape
Array of:
- district_name
- latitude
- longitude
- total_vehicle_count

#### Curl
curl -X GET "https://api.gromed.in/api/dashboard/areawise-device-count/"

### Level 2: City List in District

#### Input
- district_name (required)

#### Response Shape
- district_name
- total_locations
- locations[]
  - location_type
  - city_village_name
  - lat
  - lon
  - total_vehicle_count

#### Curl
curl -X POST "https://api.gromed.in/api/dashboard/areawise-device-count/" \
  -H "Content-Type: application/json" \
  -d '{
    "district_name": "Kamrup"
  }'

### Level 3: Localities in City

#### Input
- district_name (required)
- city_name (required)

#### Response Shape
- district_name
- city_name
- city_center_lat
- city_center_lon
- total_localities
- localities[]
  - locality_type
  - locality_name
  - lat
  - lon
  - total_vehicle_count

#### Curl
curl -X POST "https://api.gromed.in/api/dashboard/areawise-device-count/" \
  -H "Content-Type: application/json" \
  -d '{
    "district_name": "Kamrup",
    "city_name": "Rangia"
  }'

### Level 4: Devices in Locality

#### Input
- district_name (required)
- city_name (required)
- locality_name (required)

#### Response Shape
- district_name
- city_name
- locality_name
- locality_center_lat
- locality_center_lon
- total_devices
- devices[]
  - device_id
  - vehicle_reg_no
  - vehicle_type
  - status (online, idle, offline)
  - lat
  - lon
  - last_seen
  - speed_kmph

#### Curl
curl -X POST "https://api.gromed.in/api/dashboard/areawise-device-count/" \
  -H "Content-Type: application/json" \
  -d '{
    "district_name": "Kamrup",
    "city_name": "Rangia",
    "locality_name": "Ward No. 5"
  }'

---

## 4) Latest Vehicle Locations

### Endpoint
- GET, POST
- /dashboard/vehicle-locations/

### Purpose
Returns latest location and status for vehicles filtered by ID-based and name-based filters.

### Inputs
- state_id (optional, integer)
- district_id (optional, integer)
- vehicle_category_id (optional, integer)
- district_name (optional, string)
- city_name (optional, string)
- locality_name (optional, string)
- limit (optional, integer, default 100, max 1000)

### Response Shape
- filters_applied
- total_vehicles
- vehicle_locations[]
  - device_id
  - vehicle_reg_no
  - vehicle_type
  - vehicle_make
  - vehicle_model
  - imei
  - status (online, idle, offline)
  - lat
  - lon
  - last_seen
  - speed_kmph
  - heading
  - city
  - district
  - state
  - satellites
  - ignition_status
- timestamp

### Curl (GET)
curl -X GET "https://api.gromed.in/api/dashboard/vehicle-locations/?district_name=Kamrup&city_name=Rangia&locality_name=Ward%20No.%205&limit=50"

### Curl (POST)
curl -X POST "https://api.gromed.in/api/dashboard/vehicle-locations/" \
  -H "Content-Type: application/json" \
  -d '{
    "district_name": "Kamrup",
    "city_name": "Rangia",
    "locality_name": "Ward No. 5",
    "limit": 50
  }'

---

## 5) ERSS Dashboard Summary

### Endpoint
- GET, POST
- /dashboard/erss-summary/

### Purpose
ERSS high-level KPIs for devices, active emergency calls, and SOS executives.

### Inputs
- state_id (optional, integer)
- district_id (optional, integer)
- vehicle_category_id (optional, integer)

### Response Shape
- filters_applied
- erss_dashboard_metrics
  - total_tagged_device_count
  - online_device_count
  - offline_device_count
  - active_emergency_calls_count
  - total_police_sos_executive_count
  - total_ambulance_sos_executive_count
  - total_police_and_ambulance_sos_executive_count
  - police_executive_with_latest_location_within_5_min_count
  - ambulance_executive_with_latest_location_within_5_min_count
  - total_executive_with_latest_location_within_5_min_count
- timestamp

### Curl (GET)
curl -X GET "https://api.gromed.in/api/dashboard/erss-summary/?state_id=1"

### Curl (POST)
curl -X POST "https://api.gromed.in/api/dashboard/erss-summary/" \
  -H "Content-Type: application/json" \
  -d '{
    "state_id": 1,
    "district_id": 5
  }'

---

## 6) SOS Analysis Dashboard (Last 1 Year)

### Endpoint
- GET, POST
- /dashboard/sos-analysis/

### Purpose
Analytics over the last one year by month, hour of day, and district.

### Inputs
- state_id (optional, integer)
- district_id (optional, integer)

### Response Shape
- time_window
  - from
  - to
  - label
- overall_metrics
  - total_calls_count
  - total_police_broadcast_count
  - total_ambulance_broadcast_count
  - total_police_accepted_count
  - total_ambulance_accepted_count
  - total_fake_call_close
  - total_unattended_calls
- month_wise_metrics[]
  - month
  - total_calls_count
  - total_police_broadcast_count
  - total_ambulance_broadcast_count
  - total_police_accepted_count
  - total_ambulance_accepted_count
  - total_fake_call_close
  - total_unattended_calls
- hour_of_day_wise_metrics[]
  - hour_of_day
  - total_calls_count
  - total_police_broadcast_count
  - total_ambulance_broadcast_count
  - total_police_accepted_count
  - total_ambulance_accepted_count
  - total_fake_call_close
  - total_unattended_calls
- district_wise_metrics[]
  - district_name
  - total_calls_count
  - total_police_broadcast_count
  - total_ambulance_broadcast_count
  - total_police_accepted_count
  - total_ambulance_accepted_count
  - total_fake_call_close
  - total_unattended_calls
- filters_applied

### Curl (GET)
curl -X GET "https://api.gromed.in/api/dashboard/sos-analysis/?state_id=1"

### Curl (POST)
curl -X POST "https://api.gromed.in/api/dashboard/sos-analysis/" \
  -H "Content-Type: application/json" \
  -d '{
    "state_id": 1,
    "district_id": 5
  }'

---

## 7) SOS Monitoring Dashboard

### Endpoint
- GET, POST
- /dashboard/sos-monitoring/

### Purpose
Near-real-time operational SOS KPIs for current day.

### Inputs
- state_id (optional, integer)
- district_id (optional, integer)

### Response Shape
- filters_applied
- sos_monitoring_metrics
  - total_emergency_calls_today
  - total_live_calls_now
  - total_unattended_calls_now
  - total_closed_calls_today
  - average_time_to_accept_by_desk_executive_seconds
  - average_time_to_accept_broadcast_by_police_seconds
  - average_time_to_accept_broadcast_by_ambulance_seconds
  - calls_accepted_by_team_lead_total
  - calls_accepted_by_team_lead_percent_of_total_calls
- timestamp

### Curl (GET)
curl -X GET "https://api.gromed.in/api/dashboard/sos-monitoring/?state_id=1"

### Curl (POST)
curl -X POST "https://api.gromed.in/api/dashboard/sos-monitoring/" \
  -H "Content-Type: application/json" \
  -d '{
    "state_id": 1,
    "district_id": 5
  }'

---

## Full Endpoint List (Quick Copy)
- https://api.gromed.in/api/dashboard/vehicle-monitoring/
- https://api.gromed.in/api/dashboard/filter-options/
- https://api.gromed.in/api/dashboard/areawise-device-count/
- https://api.gromed.in/api/dashboard/vehicle-locations/
- https://api.gromed.in/api/dashboard/erss-summary/
- https://api.gromed.in/api/dashboard/sos-analysis/
- https://api.gromed.in/api/dashboard/sos-monitoring/

---

## Error Response Format
{
  "error": "An error occurred: <reason>"
}
