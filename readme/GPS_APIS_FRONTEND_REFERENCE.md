# GPS Tracking APIs — Frontend Developer Reference

**Base URL:** `https://api.gromed.in/api/`  
**Authentication:** All endpoints require `Authorization: Bearer <JWT_TOKEN>` header  
**Method:** All endpoints are `GET`

---

## Contents

1. [Authentication Note](#authentication)
2. [Role-Based Data Scoping](#role-scoping)
3. [Changed API: `gps_track_data_api` — Pagination Added](#1-gps_track_data_api-changed)
4. [New API: `gps_track_lite` — Fast Vehicle List](#2-gps_track_lite-new)
5. [New API: `gps_cluster` — Named Location Clusters](#3-gps_cluster-new)
6. [New API: `gps_grid_cluster` — Geographic Grid Clusters](#4-gps_grid_cluster-new)
7. [Common Filter Parameters](#common-filters)
8. [Status Definitions](#status-definitions)

---

## Authentication

All GPS APIs require a valid JWT token in the header:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Unauthenticated requests return:
```json
{ "detail": "Authentication credentials were not provided." }
```

---

## Role-Based Data Scoping

**All GPS APIs automatically scope data to the logged-in user's role.** The frontend does not need to send any extra role parameters — the backend enforces this automatically.

| Role | Data visible |
|------|-------------|
| `superadmin` | All devices in the system |
| `stateadmin` | Devices in their assigned state only |
| `sosadmin` | Devices in their assigned state only |
| `sosexecutive` | Devices in their assigned state only |
| `dtorto` | Devices in their assigned district only |
| `dealer` | Devices tagged/registered by that dealer |
| `owner` | Only the owner's own vehicles |

---

## 1. `gps_track_data_api` — CHANGED

**Endpoint:** `GET /api/gps_track_data_api/`

> **What changed:** Pagination has been added. The `data` array is unchanged. A new `pagination` object is now appended to every response.

### Request Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | `0` | Page number (0-indexed) |
| `page_length` | integer | `100` | Number of records per page |
| `imei` | string | — | Filter by IMEI (partial match) |
| `regno` | string | — | Filter by vehicle registration number (partial match) |
| `make` | string | — | Filter by vehicle make (partial match) |
| `category` | string/int | — | Filter by vehicle category (ID or name) |
| `district_id` | integer | — | Filter by district ID |
| `district` | string | — | Filter by district name (partial match) |
| `manufacturer_id` | integer | — | Filter by manufacturer ID |
| `speed_limit` | integer | — | Filter vehicles whose category max speed equals this value |
| `owner` | string | — | Filter by owner name (partial match) |
| `route_id` | integer | — | Filter vehicles within 100m of this route (geofence) |
| `poi_id` | integer | — | Filter vehicles near this POI (geofence) |
| `polygon` | JSON string | — | Filter within custom polygon: `[[lat,lon],[lat,lon],...]` |
| `in_range` | boolean | `true` | `true` = inside geofence, `false` = outside geofence |
| `poi_t` | string | — | Filter by road or city name in latest GPS entry |

### Response Structure

```json
{
  "data": [
    {
      "id": 123456,
      "entry_time": "2026-04-22T10:30:00+05:30",
      "latitude": 26.1445,
      "longitude": 91.7362,
      "speed": 42.5,
      "gps_status": 1,
      "emergency_status": "0",
      "district": "Kamrup",
      "state": "Assam",
      "city": "Guwahati",
      "road": "NH-27",
      "vehicle_registration_number": "AS01AB1234",
      "imei": "123456789012345",
      "device_tag_info": {
        "id": 78,
        "vehicle_reg_no": "AS01AB1234",
        "vehicle_make": "Tata",
        "category": { "id": 2, "category": "Bus" },
        "district": { "id": 5, "district": "Kamrup" },
        "device_info": {
          "id": 45,
          "imei": "123456789012345",
          "dealer": { "id": 3, "company_name": "ABC Dealers" },
          "manufacturer": { "id": 1, "company_name": "XYZ Tech" }
        },
        "vehicle_owner": {
          "id": 12,
          "users": [{ "id": 7, "name": "Ramesh Kumar", "phone": "9876543210" }]
        }
      },
      "nearest_poi": {
        "data": { "id": 4, "name": "Guwahati Bus Terminal", "use_type": "bus_stand" },
        "distance_meters": 380
      },
      "nearest_police": {
        "data": { "id": 9, "name": "Dispur PS", "use_type": "police" },
        "distance_meters": 1240
      },
      "nearby_routes_within_100m": [
        {
          "data": { "id": 2, "name": "Route GHY-JORHAT" },
          "min_distance_meters": 45
        }
      ]
    }
  ],
  "pagination": {
    "total": 1240,
    "page": 0,
    "page_length": 100,
    "total_pages": 13
  }
}
```

### Pagination Usage

```
// Page 1 (first 100 records)
GET /api/gps_track_data_api/?page=0&page_length=100

// Page 2
GET /api/gps_track_data_api/?page=1&page_length=100

// Smaller pages for mobile
GET /api/gps_track_data_api/?page=0&page_length=20
```

---

## 2. `gps_track_lite` — NEW

**Endpoint:** `GET /api/gps_track_lite/`

**Purpose:** High-performance vehicle list for **live map rendering and dashboards**. Returns only the essential fields needed to place a pin on a map. No heavy POI/route computation. Designed to handle 30–50K requests/min.

**Use this instead of `gps_track_data_api` for:**
- Map marker rendering (polling every 5–10 seconds)
- Vehicle list panels with lat/lon, speed, status
- Any use-case where POI proximity data is not needed

### Request Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | `0` | Page number (0-indexed) |
| `page_length` | integer | `100` | Records per page |
| `count` | boolean | `true` | Set `false` to skip the total count query — **use for polling/map use-cases to reduce DB load** |
| `imei` | string | — | Filter by IMEI (partial match) |
| `regno` | string | — | Filter by vehicle reg number (partial match) |
| `district_id` | integer | — | Filter by district ID |
| `district` | string | — | Filter by district name (partial match) |
| `state` | string | — | Filter by state name (partial match) |

### Response Structure

```json
{
  "data": [
    {
      "device_tag_id": 78,
      "vehicle_reg_no": "AS01AB1234",
      "device_stock_id": 45,
      "imei": "123456789012345",
      "owner_name": "Ramesh Kumar",
      "owner_id": 12,
      "last_seen": "2026-04-22T10:30:00+05:30",
      "emergency_status": "0",
      "speed": 42.5,
      "latitude": 26.1445,
      "longitude": 91.7362,
      "gps_status": 1,
      "district": "Kamrup",
      "state": "Assam",
      "city": "Guwahati"
    }
  ],
  "pagination": {
    "total": 1240,
    "page": 0,
    "page_length": 100,
    "total_pages": 13
  }
}
```

> When `count=false` is passed, `total` and `total_pages` will be `null` in the pagination object. Use this mode for map polling where you don't need to show "Page X of Y".

### Recommended Polling Pattern

```javascript
// For a live map that refreshes every 10 seconds:
// Use count=false — skip the heavy COUNT query
const response = await fetch(
  '/api/gps_track_lite/?page=0&page_length=500&count=false',
  { headers: { Authorization: `Bearer ${token}` } }
);

// For a paginated vehicle list table with "Page 1 of 13":
// Use count=true (default)
const response = await fetch(
  '/api/gps_track_lite/?page=0&page_length=100',
  { headers: { Authorization: `Bearer ${token}` } }
);
```

---

## 3. `gps_cluster` — NEW

**Endpoint:** `GET /api/gps_cluster/`

**Purpose:** Returns aggregated vehicle counts grouped by a named geographic level (district, state, city, or road). Use this to render **choropleth maps**, **summary dashboards**, or **heat-map overlays** without fetching individual vehicle data.

**Important:** This API uses each vehicle's **last known position** — offline vehicles are included and counted as `offline`. Only devices that have sent at least one GPS record appear.

### Request Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | string | `district` | Grouping level: `district`, `state`, `city`, or `road` |
| `imei` | string | — | Pre-filter by IMEI |
| `regno` | string | — | Pre-filter by vehicle reg number |
| `district_id` | integer | — | Pre-filter by district ID |
| `district` | string | — | Pre-filter by district name |
| `state` | string | — | Pre-filter by state name |

### Response Structure

```json
{
  "level": "district",
  "total_clusters": 24,
  "data": [
    {
      "cluster_name": "Kamrup",
      "level": "district",
      "total": 450,
      "online": 120,
      "offline": 330,
      "emergency": 3,
      "moving": 87,
      "stationary": 363,
      "avg_lat": 26.1445,
      "avg_lon": 91.7362
    },
    {
      "cluster_name": "Jorhat",
      "level": "district",
      "total": 210,
      "online": 45,
      "offline": 165,
      "emergency": 0,
      "moving": 22,
      "stationary": 188,
      "avg_lat": 26.7447,
      "avg_lon": 94.2190
    }
  ]
}
```

### Field Definitions

| Field | Description |
|-------|-------------|
| `cluster_name` | Name of the district/state/city/road |
| `total` | Total devices with a GPS record in this area |
| `online` | Devices with last GPS entry within the **last 10 minutes** |
| `offline` | Devices with last GPS entry **older than 10 minutes** |
| `emergency` | Devices with active emergency/SOS flag |
| `moving` | Devices with speed > 2 km/h at last known position |
| `stationary` | `total - moving` |
| `avg_lat` / `avg_lon` | Average latitude/longitude of all devices in this cluster — use as map label pin point |

### Example Requests

```
// All districts
GET /api/gps_cluster/?level=district

// All states
GET /api/gps_cluster/?level=state

// All cities
GET /api/gps_cluster/?level=city

// All roads
GET /api/gps_cluster/?level=road

// Districts filtered to Assam only
GET /api/gps_cluster/?level=district&state=Assam
```

> Clusters are sorted by `total` (highest first).

---

## 4. `gps_grid_cluster` — NEW

**Endpoint:** `GET /api/gps_grid_cluster/`

**Purpose:** Divides the map into a uniform geographic grid and returns vehicle counts per cell. Use for **zoom-level-aware clustering on maps** (e.g. Leaflet, Google Maps, Mapbox). As the user zooms in, switch to a smaller grid size to reveal finer detail.

**Important:** Covers all verified devices (online + offline) based on last known position.

### Request Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `grid` | integer | `100` | Grid cell size in **square km**. Must be one of the allowed values. |
| `imei` | string | — | Pre-filter by IMEI |
| `regno` | string | — | Pre-filter by vehicle reg number |
| `district_id` | integer | — | Pre-filter by district ID |
| `district` | string | — | Pre-filter by district name |
| `state` | string | — | Pre-filter by state name |

### Allowed Grid Sizes

| `grid` value | Approx cell side | Recommended map zoom | Use case |
|-------------|-----------------|---------------------|----------|
| `1000000`   | ~1000 × 1000 km | Zoom 4–5 | Country/continental overview |
| `40000`     | ~200 × 200 km   | Zoom 6–7 | Multi-state view |
| `2500`      | ~50 × 50 km     | Zoom 8–9 | State overview |
| `100`       | ~10 × 10 km     | Zoom 10–11 | District view (default) |
| `25`        | ~5 × 5 km       | Zoom 12–13 | City/block view |
| `1`         | ~1 × 1 km       | Zoom 14+ | Street-level detail |

### Response Structure

```json
{
  "grid_sq_km": 100,
  "cell_deg": 0.0898315,
  "total_cells": 47,
  "data": [
    {
      "grid_lat": 26.1449157,
      "grid_lon": 91.7898315,
      "grid_sq_km": 100,
      "cell_deg": 0.0898315,
      "total": 312,
      "online": 89,
      "offline": 223,
      "emergency": 2,
      "moving": 45,
      "stationary": 267
    },
    {
      "grid_lat": 26.2347472,
      "grid_lon": 91.8796630,
      "grid_sq_km": 100,
      "cell_deg": 0.0898315,
      "total": 178,
      "online": 34,
      "offline": 144,
      "emergency": 0,
      "moving": 18,
      "stationary": 160
    }
  ]
}
```

### Field Definitions

| Field | Description |
|-------|-------------|
| `grid_lat` / `grid_lon` | **Centre point** of the grid cell — use this as the map marker position |
| `grid_sq_km` | The grid size requested (echoed back) |
| `cell_deg` | Cell side length in degrees |
| `total` | Total devices with last known position in this cell |
| `online` | Last GPS within 10 minutes |
| `offline` | Last GPS older than 10 minutes |
| `emergency` | Active SOS/emergency flag |
| `moving` | Speed > 2 km/h at last position |
| `stationary` | `total - moving` |

Cells are sorted by `total` (highest first — renders most busy areas first).

### Zoom-Level Switching Pattern

```javascript
function getGridSize(zoomLevel) {
  if (zoomLevel <= 5)  return 1000000;
  if (zoomLevel <= 7)  return 40000;
  if (zoomLevel <= 9)  return 2500;
  if (zoomLevel <= 11) return 100;
  if (zoomLevel <= 13) return 25;
  return 1;
}

// On map zoom change:
map.on('zoomend', async () => {
  const grid = getGridSize(map.getZoom());
  const res = await fetch(`/api/gps_grid_cluster/?grid=${grid}`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  const json = await res.json();
  renderClusters(json.data);  // place markers at grid_lat, grid_lon
});
```

---

## Common Filters

The following filters work identically across `gps_track_lite`, `gps_cluster`, and `gps_grid_cluster`:

| Parameter | Matches field | Match type |
|-----------|--------------|------------|
| `imei` | Device IMEI number | Case-insensitive partial |
| `regno` | Vehicle registration number | Case-insensitive partial |
| `district_id` | District database ID | Exact |
| `district` | District name | Case-insensitive partial |
| `state` | State name | Case-insensitive partial |

---

## Status Definitions

### `online` vs `offline`
- **online**: The device's last GPS record was received within the **last 10 minutes**
- **offline**: The device's last GPS record is **older than 10 minutes**

### `emergency_status`
- `"0"` or `"0000"` — Normal, no emergency
- `"1"` or `"0001"` or `"1111"` — Emergency / SOS active

### `gps_status`
- `1` — GPS fix is active
- `0` — No GPS fix (device present but no valid position)

### `speed`
- Value in **km/h**
- `0` = stationary
- `> 2` = considered "moving" in cluster APIs

---

## Error Responses

| HTTP Status | Meaning |
|-------------|---------|
| `400` | Bad request — invalid parameter value |
| `401` | Token missing or expired |
| `403` | User role not authorised for this API |

```json
// 400 example
{ "error": "Invalid level. Choose from: district, state, city, road" }

// 400 role error
{ "error": "User not Authorised for this api." }

// 401
{ "detail": "Authentication credentials were not provided." }
```
