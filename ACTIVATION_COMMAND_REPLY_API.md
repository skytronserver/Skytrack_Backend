# Activation Command Reply API Documentation

**Base URL:** `http://<your-server>/api/`  
**Authentication:** None (public endpoint — called by SMS gateway)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Endpoint](#2-endpoint)
3. [Request Body](#3-request-body)
4. [Raw Message Format (ACTVR)](#4-raw-message-format-actvr)
5. [Validation Logic](#5-validation-logic)
6. [Responses](#6-responses)
7. [What Gets Stored](#7-what-gets-stored)
8. [cURL Example](#8-curl-example)

---

## 1. Overview

This endpoint is called by the SMS gateway when a device sends an `ACTVR` (activation command reply) message back to the server after receiving an activation SMS command.

The endpoint:
- Parses the raw ACTVR message
- Validates the device by matching IMEI + ESN code against `DeviceStock`
- Optionally validates the incoming phone number against the device's registered MSISDNs (`msisdn1` / `msisdn2`)
- Logs the reply in the `ActivationCommandReply` table, linked to the latest active `DeviceTag` for the device
- Returns all parsed message fields in the response

---

## 2. Endpoint

```
POST /api/device/activation-reply/
```

---

## 3. Request Body

**Content-Type:** `application/json`

| Field | Type | Required | Description |
|---|---|---|---|
| `raw_message` | string | **Yes** | Full message from the SMS gateway — includes the `From` header and the ACTVR data line (see formats below) |
| `incoming_from_no` | string | No | Explicit phone number override. If provided, takes precedence over the number extracted from the `From` header. If neither source provides a number, `0000000000` is stored and MSISDN validation is skipped |

### Accepted `raw_message` formats

**New format (From-header embedded — primary):**
```
From : +919101033201()
ACTVR,348752,MAPW,1.0.4,866192076850302,1,26.192982,N,91.752884,E,1,20062026 055205,137.55,0.00,27,405,56,1BDA,1,0,11.20,000064,0
```

**Legacy format (bare ACTVR line):**
```
ACTVR,348752,MAPW,1.0.4,866192076850302,1,26.192982,N,91.752884,E,1,20062026 055205,137.55,0.00,27,405,56,1BDA,1,0,11.20,000064,0
```

### Phone number extraction (From-header)

The `From` line is parsed as follows:
1. Everything after `:` is taken as the raw phone string — e.g. `+919101033201()`
2. If the string starts with `+91`, those 3 characters are stripped
3. All non-digit characters (spaces, `+`, `(`, `)`) are removed
4. Result is stored as `incoming_from_no` — e.g. `9101033201`

The number may be 10 digits or longer depending on the originating network.

**Example request body (new format):**
```json
{
    "raw_message": "From : +919101033201()\nACTVR,348752,MAPW,1.0.4,866192076850302,1,26.192982,N,91.752884,E,1,20062026 055205,137.55,0.00,27,405,56,1BDA,1,0,11.20,000064,0"
}
```

**Example request body (legacy format):**
```json
{
    "raw_message": "ACTVR,348752,MAPW,1.0.4,866192076850302,1,26.192982,N,91.752884,E,1,20062026 055205,137.55,0.00,27,405,56,1BDA,1,0,11.20,000064,0",
    "incoming_from_no": "+919401633421"
}
```

---

## 4. Raw Message Format (ACTVR)

The `raw_message` is a comma-separated string. Minimum 12 fields required. `fields[0]` must be `ACTVR`.

```
ACTVR,<esn>,<server_id>,<firmware>,<imei>,<gps_fix>,<lat_val>,<lat_dir>,<lon_val>,<lon_dir>,<flag>,<timestamp>,<altitude>,<speed>,<satellites>,<mcc>,<mnc>,<cell_id>,<f18>,<f19>,<battery>,<f21>,<f22>
```

| Index | Sample Value | Field Name | Type | Description |
|---|---|---|---|---|
| 0 | `ACTVR` | command | string | Command identifier. Must be `ACTVR` |
| 1 | `348752` | activation_code | string | Activation code echoed by the device. Stored in `raw_message` for reference only — not validated against the database |
| 2 | `MAPW` | server_id | string | Server / protocol identifier |
| 3 | `1.0.4` | firmware_version | string | Device firmware version |
| 4 | `866192076850302` | imei | string | 15-digit IMEI — matched against `DeviceStock.imei` |
| 5 | `1` | gps_fix | int | GPS fix status (`1` = fixed, `0` = no fix) |
| 6 | `26.192982` | latitude value | float | Latitude magnitude |
| 7 | `N` | latitude direction | string | `N` = positive (north), `S` = negative (south) |
| 8 | `91.752884` | longitude value | float | Longitude magnitude |
| 9 | `E` | longitude direction | string | `E` = positive (east), `W` = negative (west) |
| 10 | `1` | flag | int | Status flag |
| 11 | `20062026 055205` | timestamp_raw | string | Device timestamp — format `DDMMYYYY HHMMSS` |
| 12 | `137.55` | altitude_m | float | Altitude in metres |
| 13 | `0.00` | speed | float | Speed (unit per device config) |
| 14 | `27` | satellites | int | Number of satellites in view |
| 15 | `405` | mcc | int | Mobile Country Code |
| 16 | `56` | mnc | int | Mobile Network Code |
| 17 | `1BDA` | cell_id_hex | string | Cell tower ID (hexadecimal) |
| 18 | `1` | field_18 | string | Reserved |
| 19 | `0` | field_19 | string | Reserved |
| 20 | `11.20` | battery_voltage | float | Battery / input voltage in Volts |
| 21 | `000064` | field_21 | string | Reserved |
| 22 | `0` | field_22 | string | Reserved |

> **Note:** `latitude` and `longitude` in the response are sign-corrected (S/W become negative values).

---

## 5. Validation Logic

| Step | Rule |
|---|---|
| 1 | `fields[0]` must be `ACTVR` and the message must contain at least 12 fields |
| 2 | `fields[11]` must be a valid datetime string in `DDMMYYYY HHMMSS` format |
| 3 | A `DeviceStock` record must exist with `imei = fields[4]` |
| 4 | If `incoming_from_no` is provided (not `0000000000`): it must match `msisdn1` or `msisdn2` of the matched device. Matching is digit-only and country-code-prefix tolerant (suffix match) |

---

## 6. Responses

### `201 Created` — Success

```json
{
    "id": 1,
    "imei": "866192076850302",
    "device_tag_id": 42,
    "timestamp": "2026-06-20T05:52:05Z",
    "incoming_from_no": "+919401633421",
    "message": "Activation reply recorded.",
    "parsed_message": {
        "command":          "ACTVR",
        "esn_code":         "348752",
        "server_id":        "MAPW",
        "firmware_version": "1.0.4",
        "imei":             "866192076850302",
        "gps_fix":          1,
        "latitude":         26.192982,
        "longitude":        91.752884,
        "flag":             1,
        "timestamp_raw":    "20062026 055205",
        "altitude_m":       137.55,
        "speed":            0.00,
        "satellites":       27,
        "mcc":              405,
        "mnc":              56,
        "cell_id_hex":      "1BDA",
        "field_18":         "1",
        "field_19":         "0",
        "battery_voltage":  11.20,
        "field_21":         "000064",
        "field_22":         "0"
    }
}
```

> `device_tag_id` is `null` if no active `DeviceTag` exists for the device at the time of the request.

---

### `400 Bad Request` — Missing or invalid input

```json
{ "error": "raw_message is required." }
```
```json
{ "error": "No ACTVR line found in message." }
```
```json
{ "error": "Invalid ACTVR message format." }
```
```json
{ "error": "Invalid or missing timestamp in message." }
```

---

### `403 Forbidden` — Phone number mismatch

```json
{ "error": "Incoming number does not match any MSISDN for this device." }
```

---

### `404 Not Found` — Device not found

```json
{ "error": "No device found matching the given IMEI and code." }
```

---

## 7. What Gets Stored

A new row is created in the `ActivationCommandReply` table on every successful request:

| Column | Value Stored |
|---|---|
| `id` | Auto-generated primary key |
| `imei` | `fields[4]` from the raw message |
| `device_tag` | Latest non-deleted `DeviceTag` linked to the matched `DeviceStock` (or `null`) |
| `raw_message` | Full original message string, unchanged |
| `timestamp` | Parsed from `fields[11]`, stored as UTC |
| `incoming_from_no` | Provided value, or `0000000000` if not supplied |

`DeviceTag` lookup excludes statuses `TagDeleted` and `untaged_after_failed_taging`, and selects the most recently tagged record.

---

## 8. cURL Examples

### New format — From-header embedded (phone extracted automatically)
```bash
curl -X POST http://<your-server>/api/device/activation-reply/ \
  -H "Content-Type: application/json" \
  -d '{
    "raw_message": "From : +919101033201()\nACTVR,348752,MAPW,1.0.4,866192076850302,1,26.192982,N,91.752884,E,1,20062026 055205,137.55,0.00,27,405,56,1BDA,1,0,11.20,000064,0"
  }'
```

### Legacy format — phone passed as separate field
```bash
curl -X POST http://<your-server>/api/device/activation-reply/ \
  -H "Content-Type: application/json" \
  -d '{
    "raw_message": "ACTVR,348752,MAPW,1.0.4,866192076850302,1,26.192982,N,91.752884,E,1,20062026 055205,137.55,0.00,27,405,56,1BDA,1,0,11.20,000064,0",
    "incoming_from_no": "+919401633421"
  }'
```

### No phone number available (MSISDN validation skipped, stores 0000000000)
```bash
curl -X POST http://<your-server>/api/device/activation-reply/ \
  -H "Content-Type: application/json" \
  -d '{
    "raw_message": "ACTVR,348752,MAPW,1.0.4,866192076850302,1,26.192982,N,91.752884,E,1,20062026 055205,137.55,0.00,27,405,56,1BDA,1,0,11.20,000064,0"
  }'
```
