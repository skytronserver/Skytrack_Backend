# Alert Types Reference

Complete reference for all alert types supported by the Skytrack system.

---

## Driver Behaviour Alerts

| Type Code | Display Name | Status | Description | Trigger |
|-----------|-------------|--------|-------------|---------|
| `HarshBreak` | Harsh Braking | in | Sudden hard braking detected — driver behaviour alert | Device data |
| `HarshTurn` | Harsh Turn | in | Abrupt sharp turn detected — driver behaviour alert | Device data |
| `HarshAcceleration` | Harsh Acceleration | Sudden aggressive acceleration detected — driver behaviour alert | Device data |
| `Tilt` | Tilt | in | Device or vehicle tilted beyond normal angle — possible accident or tampering | Device data |

---

## Speed Alerts

| Type Code | Display Name | Status | Description | Trigger |
|-----------|-------------|--------|-------------|---------|
| `OverSpeed` | Over Speed | in | Vehicle exceeded the maximum allowed speed limit for its category | Device data |
| `Route_overspeed` | Route Overspeed | in | Vehicle exceeded the speed limit specific to its assigned route | Speed exceeds route speed limit from device data |

---

## Route & Stop Alerts

| Type Code | Display Name | Status | Description | Trigger |
|-----------|-------------|--------|-------------|---------|
| `Route` | Route Deviation | in/out | Vehicle deviated from or violated its assigned route | Route table and device data |
| `UnauthorizedStop` | Unauthorized Stop | in | Vehicle stopped at a location not part of its approved schedule | Location is over 5 min in a stop-restricted POI |
| `UnauthorizedSkip` | Unauthorized Skip | in | Vehicle skipped a mandatory stop or checkpoint without halting (e.g. bus stop) | Location is not static for min 30 sec at a required stop POI |
| `UnauthorizedParking` | Unauthorized Parking | in/out | Vehicle stopped or parked at a NoParking zone | Device location in no-parking POI for threshold duration |
| `Overtime` | Overtime | in | Vehicle operated beyond its permitted working hours | Vehicle type and engine status from device data |
| `Idling` | Idling | in | Vehicle has been stationary for too long with engine on | Device data |

---

## Geofence & Border Crossing Alerts

| Type Code | Display Name | Status | Description | Trigger |
|-----------|-------------|--------|-------------|---------|
| `Geofence` | Geofence | in/out | Vehicle entered or exited a POI (state, district, city, restricted area) | Geofence boundary and device data |
| `state_border_cross` | State Border Cross | in/out | Vehicle crossed from one state into another | State boundary geofence and device data |
| `district_border_cross` | District Border Cross | in/out | Vehicle crossed from one district into another | District boundary geofence and device data |
| `city_border_cross` | City Border Cross | in/out | Vehicle crossed the boundary of a city | City boundary geofence and device data |
| `Prohibited_Area` | Prohibited Area | in/out | Vehicle entered a restricted or prohibited geographic zone | Device location in prohibited area POI |
| `Permit_3day` | Permit Expiring Soon | in | Vehicle in non-permitted district for more than 3 days | Permit check and location data |
| `Permit` | Permit | in | Vehicle permit check alert | Permit validation |

---

## Emergency Alerts

| Type Code | Display Name | Status | Description | Trigger |
|-----------|-------------|--------|-------------|---------|
| `Em` | Emergency SOS | in | Emergency or SOS alert triggered by the device | Emergency button on device |
| `EmPublicApp` | Emergency (Public App) | in | Emergency triggered via public app without login | `emergency_public_app` |
| `EmRegisteredApp` | Emergency (Registered App) | in | Emergency triggered via registered account app | `emergency_registered_app` |
| `EmMonitorTripSOS` | Monitor Trip SOS | in | SOS triggered during a monitored trip from the app | `monitor_trip_sos` |
| `EmMonitorTripInvalidPw` | Monitor Trip Invalid Password | in | Invalid password entered during a monitored trip | `monitor_trip_invalid_pw` |
| `EmMonitorTripBLEDisconnect` | Monitor Trip BLE Disconnect | out | BLE device disconnected during a monitored trip | `monitor_trip_ble_disconnect` |
| `EmMonitorTripDeviated` | Monitor Trip Deviated | in | Trip route deviation detected during a monitored trip | `monitor_trip_deviated` |
| `Incident` | Incident | in | Incident reported by public or enforcement (accident etc.) | `incident_detected` |

---

## Device Hardware Alerts

| Type Code | Display Name | Status | Description | Trigger |
|-----------|-------------|--------|-------------|---------|
| `Eng` | Engine Status | in/out | Engine turned on or off — ignition event detected by the device | Device data |
| `GPSLoss` | GPS Loss | in/out | Device lost GPS signal — location data unavailable | Device data with no GPS fix |
| `NetworkLoss` | Network Loss | in/out | Device lost network connectivity with server | Continuous scan for devices with no data for last 5 min |
| `OfflineDevice` | Offline Device | out | Device went offline — no communication received | Continuous scan for devices with no data for last 15 min |
| `LowIntBat` | Low Internal Battery | in/out | Internal backup battery of the GPS device is running low | Device data |
| `LowExtBat` | Low External Battery | in/out | External or vehicle battery voltage dropped below safe threshold | Device data |
| `ExtBatDiscnt` | External Battery Disconnected | in/out | External battery or vehicle power supply disconnected from device | Device data |
| `BoxTemp` | Box Temperature | in | Device box opened / tampering detected | Device data |
| `EmTemp` | Emergency Temperature | in | Tampering with emergency cable detected | Device data |

---

## Status Values

| Value | Meaning |
|-------|---------|
| `in` | Alert condition started / entered |
| `out` | Alert condition ended / exited |
| `in/out` | Alert fires on both entry and exit |
