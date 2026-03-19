# Dashboard APIs Quick Reference

## Base URL
https://api.gromed.in/api

## Access
All dashboard APIs are public (no authentication required).

## Endpoints

1. Vehicle Monitoring
- GET, POST
- /dashboard/vehicle-monitoring/

Example:
curl -X GET "https://api.gromed.in/api/dashboard/vehicle-monitoring/"

2. Filter Options
- GET
- /dashboard/filter-options/

Example:
curl -X GET "https://api.gromed.in/api/dashboard/filter-options/"

3. Area-wise Device Count (4-level drilldown)
- GET, POST
- /dashboard/areawise-device-count/

Examples:
curl -X GET "https://api.gromed.in/api/dashboard/areawise-device-count/"

curl -X POST "https://api.gromed.in/api/dashboard/areawise-device-count/" \
  -H "Content-Type: application/json" \
  -d '{"district_name":"Kamrup"}'

curl -X POST "https://api.gromed.in/api/dashboard/areawise-device-count/" \
  -H "Content-Type: application/json" \
  -d '{"district_name":"Kamrup","city_name":"Rangia"}'

curl -X POST "https://api.gromed.in/api/dashboard/areawise-device-count/" \
  -H "Content-Type: application/json" \
  -d '{"district_name":"Kamrup","city_name":"Rangia","locality_name":"Ward No. 5"}'

4. Latest Vehicle Locations
- GET, POST
- /dashboard/vehicle-locations/

Example:
curl -X GET "https://api.gromed.in/api/dashboard/vehicle-locations/?district_name=Kamrup&city_name=Rangia&locality_name=Ward%20No.%205&limit=50"

5. ERSS Summary
- GET, POST
- /dashboard/erss-summary/

Example:
curl -X GET "https://api.gromed.in/api/dashboard/erss-summary/?state_id=1"

6. SOS Analysis
- GET, POST
- /dashboard/sos-analysis/

Example:
curl -X GET "https://api.gromed.in/api/dashboard/sos-analysis/?state_id=1"

7. SOS Monitoring
- GET, POST
- /dashboard/sos-monitoring/

Example:
curl -X GET "https://api.gromed.in/api/dashboard/sos-monitoring/?state_id=1"

## Main Documentation
See CENTRAL_DASHBOARD_API_DOCUMENTATION.md for full request and response field details.
