# Technical Onboarding Test APIs — Reference

**Base URL:** `https://api.gromed.in/api/`
**Authentication:** `Authorization: Bearer <access token>` (superadmin) on every endpoint
**Content type:** `application/json` — all endpoints are `POST`
**Version:** test plan of 2026-10-14 (migrations `0111` + `0112`)

---

## Table of Contents

1. [What changed](#1-what-changed)
2. [Test run flow](#2-test-run-flow)
3. [Common errors](#3-common-errors)
4. [Test case catalog](#4-test-case-catalog)
   - 4.1 [List test cases](#41-list-test-cases)
   - 4.2 [Create / update a test case](#42-create--update-a-test-case)
5. [Running a test](#5-running-a-test)
   - 5.1 [Test board](#51-test-board)
   - 5.2 [Start a test](#52-start-a-test)
   - 5.3 [Heartbeat](#53-heartbeat)
   - 5.4 [Refresh the test log](#54-refresh-the-test-log)
   - 5.5 [Complete a test](#55-complete-a-test)
6. [Device commands (MQTT)](#6-device-commands-mqtt)
   - 6.1 [List commands for a test](#61-list-commands-for-a-test)
   - 6.2 [Send a command](#62-send-a-command)
7. [Test log snapshot reference](#7-test-log-snapshot-reference)
8. [Test catalog: criteria per test](#8-test-catalog-criteria-per-test)
9. [Reference packet format](#9-reference-packet-format)
10. [`check_config` reference](#10-check_config-reference)
11. [Deployment](#11-deployment)

---

## 1. What changed

All changes are **additive** — no existing field or endpoint was removed or renamed.

| Area | Change |
|---|---|
| Catalog | Test **#23** (Satellite/GPS signal loss) removed — deactivated (`active=false`) so numbers 24–41 match the test plan. |
| Catalog | **#40 ↔ #41 swapped**: #40 = PVT packet drop test, #41 = Activation command + reply. |
| Test case fields | New: `category`, `test_environment`, `requires_map`, `requires_command`, `requires_physical_test`, `procedure`, `expected_result`, `commands`, `check_config`. `requires_manual_confirmation` is now set from the test plan. |
| Pass criteria | Every test re-pointed at the test plan's "Expected Result" — see [section 8](#8-test-catalog-criteria-per-test). |
| Test log | Failures carry a plain-language `reason`; samples carry parsed packet fields (`packet`) and a `role`; new mode-specific keys (`route`, `checks`, `stretches`, …); every snapshot includes `commands_sent`. |
| Refresh log | Optional `geofence_in` / `geofence_out` for the geofence test (#16). |
| **New API** | `superadmin/test-commands/` — commands configured for a test + commands sent + device replies. |
| **New API** | `superadmin/test-send-command/` — send a command to the demo device over MQTT. |
| Protocol | Packets are validated against the format of reference test device **AS01AA0005**; checksum mismatch is a hard failure — see [section 9](#9-reference-packet-format). |

---

## 2. Test run flow

```
test-board ──► test-start ──► (test-send-command)* ──► test-refresh-log (repeat) ──► test-complete
                   │                                      ▲
                   └──── test-heartbeat every ≤ 30 s ─────┘
```

1. **Board** – load all tests × demo devices with their current status.
2. **Start** – starts the attempt; the test window begins at `started_at`.
3. **Heartbeat** – send every ≤ 30 s while the test page is open. An `in_progress` test with **no heartbeat for 45 s is auto-marked `incomplete`** (sending a command also counts as a heartbeat).
4. **Commands** (tests with `requires_command: true`) – send the command(s) to the device.
5. **Refresh** – re-runs the automated check and returns the snapshot; call as often as needed.
6. **Complete** – needs at least one refresh after start; the result is the last snapshot's `pass` (plus the tester's `manual_result` when `requires_manual_confirmation` is true).

Tests unlock in `serial_no` order: test *N* can only start once test *N−1* is `complete` for every demo device (optional tests are skipped by the lock).

---

## 3. Common errors

All errors return HTTP `400` unless noted.

| Response | Cause |
|---|---|
| `{"error": "Request must be from superadmin."}` | Caller isn't a superadmin. |
| `{"error": "Invalid execution_id."}` | No such execution. |
| `{"error": "Test is incomplete, not in progress.", "status": "incomplete"}` | Test timed out (no heartbeat) or was completed — start it again. |
| `{"execution_id": ["This field is required."]}` | Body validation error (field → messages). |
| `401` `{"detail": "Given token not valid for any token type", ...}` | Missing / expired token. |
| `403` | Role lacks the `tech_onboarding` page permission. |

---

## 4. Test case catalog

### 4.1 List test cases

```
POST /api/devicemodel/technical-onboarding/test-cases/list/
```

Returns every **active** test case, ordered by `serial_no`.

```bash
curl -X POST 'https://api.gromed.in/api/devicemodel/technical-onboarding/test-cases/list/' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{}'
```

**Response `200`** (one element shown)

```json
[
  {
    "id": 4,
    "serial_no": 4,
    "name": "App SOS -> Tracking Server (Start + NR SOS=1)",
    "description": "Verify that, after initiating SOS from the BLE mobile application, ...",
    "source_table": "packet_sequence",
    "regex_pattern": null,
    "min_match_count": 1,
    "max_interval_seconds": null,
    "scan_window_seconds": 300,
    "requires_manual_confirmation": false,
    "is_optional": false,
    "active": true,
    "category": "SOS",
    "test_environment": "Indoor",
    "requires_map": false,
    "requires_command": true,
    "requires_physical_test": false,
    "procedure": "1. Power the device and confirm it is connected to the Tracking Server.\n2. Trigger SOS from the mobile app.\n3. Observe the Tracking Server raw data.\n4. After verification, send the SOS stop command from the server.",
    "expected_result": "SOS Start packet (EA,10) with the App/BLE flag received on the Tracking Server, followed by 10 NR packets with SOS flag = 1 within one minute.",
    "commands": [
      {"key": "sos_stop", "label": "SOS stop", "command": "SETSOSDIS-1"}
    ],
    "check_config": {
      "trigger_regex": ",EA,10,.*\\{SOS_PUB_",
      "trigger_label": "App SOS start alert (EA,10 + BLE flag)",
      "after": {"packet_type": "NR", "field": "emergency_status", "equals": "1", "label": "SOS flag"},
      "after_count": 10,
      "within_seconds": 60
    },
    "created_at": "2026-08-20T06:11:02.118204Z",
    "updated_at": "2026-10-14T12:30:00.000000Z"
  }
]
```

**New fields**

| Field | Type | Meaning |
|---|---|---|
| `category` | string | Test plan category, e.g. `SOS`, `Power`, `Protocol Validation`. |
| `test_environment` | string | `Indoor` or `Outdoor (Road Test)`. |
| `requires_manual_confirmation` | bool | Tester must confirm the result (`manual_result` on complete). *(existing field, now set from the test plan)* |
| `requires_map` | bool | Show the map — samples carry `latitude`/`longitude`; some tests also return a `route`. |
| `requires_command` | bool | A command must be sent from the server during the test (see [section 6](#6-device-commands-mqtt)). |
| `requires_physical_test` | bool | The tester performs a physical action on the device. |
| `procedure` | string | Step-by-step procedure (newline-separated). |
| `expected_result` | string | Pass criteria in plain words. |
| `commands` | array | Commands configured for this test (empty when not known — send a custom command). |
| `check_config` | object | Thresholds read by the automated check (see [section 10](#10-check_config-reference)). |

### 4.2 Create / update a test case

```
POST /api/devicemodel/technical-onboarding/test-cases/upsert/
```

With `id` → partial update; without `id` → create. Any test case field can be sent. Use this to add command strings or tune `check_config` without a deploy.

**Example — add a reboot command to test #38**

```bash
curl -X POST 'https://api.gromed.in/api/devicemodel/technical-onboarding/test-cases/upsert/' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "id": 37,
    "commands": [
      {"key": "reboot", "label": "Reboot device", "command": "SETRESET-1"}
    ]
  }'
```

**Response `200`** — the full updated test case (same shape as 4.1).

**`commands` item format**

| Key | Required | Meaning |
|---|---|---|
| `key` | yes | Identifier used by `test-send-command` (`command_key`). Use `reboot` for test #38 so the reboot check finds it. |
| `label` | no | Button text. |
| `command` | yes | Command body. `{value}` is replaced by the `value` sent with the request. The `@…*` framing is added automatically. |
| `value_hint` | no | Placeholder text for the value input. |
| `value_regex` | no | The value must fully match this regex. |

---

## 5. Running a test

### 5.1 Test board

```
POST /api/devicemodel/technical-onboarding/superadmin/test-board/
```

```bash
curl -X POST 'https://api.gromed.in/api/devicemodel/technical-onboarding/superadmin/test-board/' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"onboarding_request_id": 12}'
```

**Response `200`**

```json
{
  "onboarding_request_id": 12,
  "status": "ongoing_evaluation",
  "current_unlocked_serial_no": 4,
  "rows": [
    {
      "test_case": { "id": 4, "serial_no": 4, "name": "App SOS -> Tracking Server (Start + NR SOS=1)", "...": "..." },
      "executions": [
        {
          "id": 7752,
          "test_case": { "...": "..." },
          "demo_device": { "id": 31, "imei": "866192070567555", "device_serial_no": "...", "...": "..." },
          "status": "not_started",
          "attempt_number": 0,
          "started_at": null,
          "last_heartbeat_at": null,
          "completed_at": null,
          "test_log_snapshot": null,
          "last_refreshed_at": null,
          "manual_result": null,
          "manual_notes": null
        }
      ]
    }
  ]
}
```

`status` per execution: `not_started` | `in_progress` | `complete` | `incomplete`.

### 5.2 Start a test

```
POST /api/devicemodel/technical-onboarding/superadmin/test-start/
```

```bash
curl -X POST 'https://api.gromed.in/api/devicemodel/technical-onboarding/superadmin/test-start/' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"onboarding_request_id": 12, "demo_device_id": 31, "test_case_id": 43}'
```

**Response `200`** — the execution (same shape as a board execution) with `"status": "in_progress"`, `started_at` set, `attempt_number` incremented and `test_log_snapshot: null`.

**Errors**

```json
{"error": "Test #40 is locked. Complete test #39 for all IMEIs first."}
{"error": "This test is already in_progress for this IMEI."}
{"error": "Testing is only available once all stock has been received."}
```

### 5.3 Heartbeat

```
POST /api/devicemodel/technical-onboarding/superadmin/test-heartbeat/
```

```bash
curl -X POST 'https://api.gromed.in/api/devicemodel/technical-onboarding/superadmin/test-heartbeat/' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"execution_id": 7752}'
```

**Response `200`**

```json
{"status": "ok", "last_heartbeat_at": "2026-10-14T08:31:30.512345Z"}
```

> Keep the test page open and heartbeat every ≤ 30 s. For the 15-minute PVT packet drop test (#40) this is essential.

### 5.4 Refresh the test log

```
POST /api/devicemodel/technical-onboarding/superadmin/test-refresh-log/
```

Runs the automated check for the execution's test and stores/returns the snapshot.

**Body**

| Field | Required | Meaning |
|---|---|---|
| `execution_id` | yes | Execution to check. |
| `geofence_in` | no | **Test #16 only.** The geofence IN point marked on the map: `{"timestamp": "<ISO>"}` (nearest packet in time) **or** `{"latitude": .., "longitude": ..}` (nearest packet on the route). |
| `geofence_out` | no | **Test #16 only.** The geofence OUT point, same format. |

Marked geofence points are remembered for the rest of the attempt — later refreshes don't need to resend them; sending a new one replaces it.

**Example — normal refresh**

```bash
curl -X POST 'https://api.gromed.in/api/devicemodel/technical-onboarding/superadmin/test-refresh-log/' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"execution_id": 7752}'
```

**Response `200` — passed (test #3, physical SOS → tracking server)**

```json
{
  "mode": "packet_sequence",
  "matched_count": 10,
  "required": 10,
  "pass": true,
  "reason": null,
  "samples": [
    {
      "raw_data": "$,PVT,MAPW,1.0.8,EA,10,L,866192070567555,AS01AA0005,1,12102026,050337,26.192993,N,91.752930,E,...",
      "timestamp": "2026-10-12T05:03:37+00:00",
      "packet": {
        "packet_type": "EA", "alert_id": "10", "packet_status": "L",
        "vehicle_reg_no": "AS01AA0005", "firmware": "1.0.8", "gps_fix": "1",
        "latitude": 26.192993, "longitude": 91.75293, "speed": 0.0, "heading": 28.0,
        "network_operator": "AIRTEL", "ignition": "0", "main_power": "1",
        "external_voltage": "11.20", "internal_voltage": "3.50",
        "emergency_status": "1", "box_tamper": "C",
        "mcc": "405", "mnc": "56", "lac": "1BDA", "cell_id": "075B"
      },
      "role": "trigger"
    },
    {
      "raw_data": "$,PVT,MAPW,1.0.8,NR,01,L,866192070567555,AS01AA0005,1,12102026,050340,...",
      "timestamp": "2026-10-12T05:03:40+00:00",
      "packet": { "packet_type": "NR", "emergency_status": "1", "...": "..." },
      "role": "after"
    }
  ],
  "trigger_count": 1,
  "window_start": "2026-10-12T05:02:50.104411+00:00",
  "refreshed_at": "2026-10-12T05:04:41.551200+00:00",
  "commands_sent": []
}
```

**Response `200` — failed (test #9, ignition ON)**

```json
{
  "mode": "packet_sequence",
  "matched_count": 3,
  "required": 9,
  "pass": false,
  "reason": "Only 2 of the 8 ignition = 1 packet(s) needed after the Ignition ON alert (IN,07) (10:32:15 IST) arrived within 1m 0s; 6 packet(s) show ignition = 0 (first at 10:32:25 IST).",
  "samples": [
    {"raw_data": "...NR,01...", "timestamp": "2026-10-12T05:02:10+00:00", "packet": {"ignition": "0", "...": "..."}, "role": "before"},
    {"raw_data": "...IN,07...", "timestamp": "2026-10-12T05:02:15+00:00", "packet": {"ignition": "1", "...": "..."}, "role": "trigger"},
    {"raw_data": "...NR,01...", "timestamp": "2026-10-12T05:02:15+00:00", "packet": {"ignition": "1", "...": "..."}, "role": "after"}
  ],
  "trigger_count": 1,
  "window_start": "2026-10-12T05:01:30+00:00",
  "refreshed_at": "2026-10-12T05:03:30+00:00",
  "commands_sent": []
}
```

**Example — geofence test (#16) with marked points**

```bash
curl -X POST 'https://api.gromed.in/api/devicemodel/technical-onboarding/superadmin/test-refresh-log/' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "execution_id": 7790,
    "geofence_in":  {"timestamp": "2026-10-14T10:35:00Z"},
    "geofence_out": {"latitude": 26.1943, "longitude": 91.7543}
  }'
```

**Response `200`** (failed — points too close)

```json
{
  "mode": "geofence_crossing",
  "matched_count": 0,
  "required": 1,
  "pass": false,
  "reason": "The geofence IN point (16:05:02 IST) and OUT point (16:48:28 IST) are 203 m apart; they must be 950-1050 m apart.",
  "samples": [
    {"raw_data": "$,PVT,...", "timestamp": "2026-10-14T10:35:02+00:00", "packet": {"latitude": 26.192942, "longitude": 91.752861, "...": "..."}, "role": "geofence_in"},
    {"raw_data": "$,PVT,...", "timestamp": "2026-10-14T11:18:28+00:00", "packet": {"latitude": 26.194258, "longitude": 91.754288, "...": "..."}, "role": "geofence_out"}
  ],
  "detection": "marked",
  "geofence_points": {
    "in":  {"timestamp": "2026-10-14T10:35:00+00:00"},
    "out": {"latitude": 26.1943, "longitude": 91.7543}
  },
  "entry_exit_distance_m": 203.1,
  "criteria": {"distance_range_m": [950, 1050]},
  "route": [
    {"latitude": 26.192942, "longitude": 91.752861, "timestamp": "2026-10-14T10:35:02+00:00", "speed": 12.4}
  ],
  "window_start": "2026-10-14T10:30:00+00:00",
  "refreshed_at": "2026-10-14T11:20:00+00:00",
  "commands_sent": []
}
```

Before any point is marked, `reason` is: `"Geofence IN and OUT point not marked yet. Mark the IN and OUT points on the map (they must be about 1 km apart), then refresh."` — draw `route` on the map for the tester to pick from.

**Errors**

```json
{"geofence_in": {"non_field_errors": ["Give a timestamp or a latitude + longitude."]}}
{"error": "Test is complete, not in progress.", "status": "complete"}
```

### 5.5 Complete a test

```
POST /api/devicemodel/technical-onboarding/superadmin/test-complete/
```

| Field | Required | Meaning |
|---|---|---|
| `execution_id` | yes | |
| `manual_result` | no | `pass` \| `fail` — the tester's verdict for tests with `requires_manual_confirmation: true` (defaults to `pass`). |
| `manual_notes` | no | Free text. |

```bash
curl -X POST 'https://api.gromed.in/api/devicemodel/technical-onboarding/superadmin/test-complete/' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"execution_id": 7752, "manual_result": "pass", "manual_notes": "Voltages matched the bench supply."}'
```

**Response `200`** — the execution with `"status": "complete"` (passed) or `"status": "incomplete"` (failed — start again to retry).

**Result rules**

- Automated test: `complete` when the last snapshot's `pass` is `true`.
- `requires_manual_confirmation: true`: the automated check must have passed first, then `manual_result` decides (`fail` → `incomplete`).

**Errors**

```json
{"error": "Refresh the test log at least once before completing this test."}
{"error": "The required packet has not been found in GPSDataLog yet. Trigger the event on the device, refresh the test log, and confirm once it shows up.", "snapshot": {"...": "..."}}
{"error": "Test is already incomplete (likely due to an inactive session). Start the test again to retry.", "status": "incomplete"}
```

---

## 6. Device commands (MQTT)

Commands are published to the demo device on MQTT topic `deviceResponse/<IMEI>` as:

```json
{"keys": "@<command>*"}
```

Every send is logged per execution and shown in `commands_sent` (on the refresh snapshot and the list endpoint) together with the device's replies.

### 6.1 List commands for a test

```
POST /api/devicemodel/technical-onboarding/superadmin/test-commands/
```

Returns the commands configured for the execution's test case and every command already sent in the current attempt, with device replies.

```bash
curl -X POST 'https://api.gromed.in/api/devicemodel/technical-onboarding/superadmin/test-commands/' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"execution_id": 7801}'
```

**Response `200`**

```json
{
  "execution_id": 7801,
  "imei": "866192070567555",
  "requires_command": true,
  "commands": [
    {
      "key": "set_reg_no",
      "label": "Set vehicle registration number",
      "command": "SETREGNO-{value}",
      "value_hint": "AS01AA0001",
      "value_regex": "^[A-Za-z0-9]{4,15}$"
    }
  ],
  "commands_sent": [
    {
      "id": 15,
      "command_key": "set_reg_no",
      "command_label": "Set vehicle registration number",
      "command_sent": "@SETREGNO-AS01AA0009*",
      "value": "AS01AA0009",
      "send_status": "queued",
      "error": null,
      "sent_at": "2026-10-14T11:16:40.120034+00:00",
      "replies": [
        {"raw_data": "SET SUCCESSFULLY REGNO-AS01AA0009", "timestamp": "2026-10-14T11:16:53.371361+00:00"},
        {"raw_data": "$,PVT,MAPW,1.0.8,OT,12,L,866192070567555,AS01AA0009,...,SERVER,20.244.106.211:6000,SETREGNO-AS01AA0009,SET SUCCESSFULLY REGNO-AS01AA0009,...", "timestamp": "2026-10-14T11:16:53.454408+00:00"}
      ]
    }
  ]
}
```

**`commands_sent[].replies`** — what the device sent back within **2 minutes** of the command:

- plain-text replies (`SET SUCCESSFULLY ...`, `SOS DISABLED`, `ERR:BAD_SET_FORMAT`, `DEV RESET SEQUENCE STARTED`, …) — matched by the device's connection IP, since these carry no IMEI;
- `OT,12` acknowledgement packets for the IMEI (they echo the command received).

`commands` is empty for tests whose command string isn't configured yet — send a custom command (6.2, example C).

### 6.2 Send a command

```
POST /api/devicemodel/technical-onboarding/superadmin/test-send-command/
```

The execution must be `in_progress` (start the test first). Sending also refreshes the heartbeat.

**Body** — give **either** `command_key` **or** `command`:

| Field | Required | Meaning |
|---|---|---|
| `execution_id` | yes | Running execution; the command goes to its demo device's IMEI. |
| `command_key` | one of | Key of a command configured on the test case (`commands[].key`). |
| `value` | with `{value}` | Value substituted into a configured command containing `{value}`; checked against `value_regex`. |
| `command` | one of | **Custom command** body, e.g. `SETSOSDIS-1`. Use this for commands not configured on the test case. |

`@` and `*` are added if missing — `SETSOSDIS-1` and `@SETSOSDIS-1*` send the same thing.

**Example A — configured command (SOS stop, tests #2, #4, #5, #31)**

```bash
curl -X POST 'https://api.gromed.in/api/devicemodel/technical-onboarding/superadmin/test-send-command/' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"execution_id": 7760, "command_key": "sos_stop"}'
```

**Response `200`**

```json
{
  "id": 14,
  "execution_id": 7760,
  "imei": "866192070567555",
  "command_key": "sos_stop",
  "command_label": "SOS stop",
  "command_sent": "@SETSOSDIS-1*",
  "value": null,
  "send_status": "queued",
  "error": null,
  "sent_at": "2026-10-14T10:42:05.881020+00:00"
}
```

**Example B — configured command with a value (set registration number, test #39)**

```bash
curl -X POST 'https://api.gromed.in/api/devicemodel/technical-onboarding/superadmin/test-send-command/' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"execution_id": 7801, "command_key": "set_reg_no", "value": "AS01AA0009"}'
```

**Response `200`**

```json
{
  "id": 15,
  "execution_id": 7801,
  "imei": "866192070567555",
  "command_key": "set_reg_no",
  "command_label": "Set vehicle registration number",
  "command_sent": "@SETREGNO-AS01AA0009*",
  "value": "AS01AA0009",
  "send_status": "queued",
  "error": null,
  "sent_at": "2026-10-14T11:16:40.120034+00:00"
}
```

The value sent here is what test #39 expects to see in the next NR packets.

**Example C — custom command (any test, e.g. eSIM switch #24)**

```bash
curl -X POST 'https://api.gromed.in/api/devicemodel/technical-onboarding/superadmin/test-send-command/' \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"execution_id": 7795, "command": "SETPROFILE-2"}'
```

**Response `200`**

```json
{
  "id": 16,
  "execution_id": 7795,
  "imei": "866192070567555",
  "command_key": "",
  "command_label": "Custom command",
  "command_sent": "@SETPROFILE-2*",
  "value": null,
  "send_status": "queued",
  "error": null,
  "sent_at": "2026-10-14T11:30:12.004511+00:00"
}
```

> For the reboot test (#38), either configure a command with `"key": "reboot"` on the test case, or send a custom command whose text contains `reboot` or `reset` (the test's `regex_pattern` is `(?i)reboot|reset`) — that's how the check finds the time the reboot was sent.

**Errors**

| Status | Response | Cause |
|---|---|---|
| 400 | `{"non_field_errors": ["Provide command_key (a configured command) or command (a custom command)."]}` | Neither given. |
| 400 | `{"error": "Command 'reboot' is not configured for this test."}` | Unknown `command_key`. |
| 400 | `{"error": "A value is required for 'Set vehicle registration number'."}` | Command has `{value}` but no `value` sent. |
| 400 | `{"error": "Value 'AS 01' is not in the expected format for 'Set vehicle registration number'."}` | `value` fails `value_regex`. |
| 400 | `{"error": "Test is incomplete, not in progress. Start the test before sending commands.", "status": "incomplete"}` | Test not running. |
| 502 | `{... "send_status": "failed", "error": "Could not publish the command to the MQTT broker."}` | Broker publish failed (logged anyway). |

`send_status: "queued"` means the command was handed to the MQTT broker — confirm delivery from `replies`.

---

## 7. Test log snapshot reference

Returned by `test-refresh-log` and stored on the execution as `test_log_snapshot`.

### Keys present on every snapshot

| Key | Type | Meaning |
|---|---|---|
| `mode` | string | The test's `source_table` (check type). |
| `pass` | bool \| null | Automated verdict (`null` for `manual` tests). |
| `reason` | string \| null | **Why it failed**, in plain words with IST times; `null` when passed. Several failures are numbered: `"Failed 2 checks: 1) ... 2) ..."`. |
| `matched_count` / `required` | int | Progress counter (what was found vs needed). |
| `samples` | array | Evidence packets — see below. |
| `window_start` | ISO time | Start of the scanned window. |
| `refreshed_at` | ISO time | When this check ran. |
| `commands_sent` | array | Commands sent in this attempt, with replies (same as 6.1). |

### Sample object

```json
{
  "raw_data": "$,PVT,MAPW,1.0.8,NR,01,L,866192070567555,AS01AA0005,...",
  "timestamp": "2026-10-14T10:59:37+00:00",
  "packet": { "packet_type": "NR", "alert_id": "01", "latitude": 26.19, "longitude": 91.75, "...": "..." },
  "role": "after"
}
```

- `timestamp` is the device time from the packet when plausible (buffered history packets appear at the time they cover), otherwise the server receive time.
- `packet` (PVT packets only): `packet_type`, `alert_id`, `packet_status` (L/H), `vehicle_reg_no`, `firmware`, `gps_fix`, `latitude`, `longitude`, `speed`, `heading`, `network_operator`, `ignition`, `main_power`, `external_voltage`, `internal_voltage`, `emergency_status`, `box_tamper`, `mcc`, `mnc`, `lac`, `cell_id`.
- `role` tells the sample's place in the evidence: `before`, `trigger`, `after`, `tracking_stop`, `emergency_stop`, `geofence_in`, `geofence_out`, `before_switch`, `after_switch`, `before_upgrade`, `after_upgrade`, `first_history`, `last_history`, `ot_ack`, `nr_with_new_reg_no`, `login`, `health`, `tracking`.

### Mode-specific keys

| Mode | Extra keys |
|---|---|
| `packet_sequence` | `trigger_count` |
| `protocol_packet` | samples carry `protocol_format`, `valid`, `errors` (list of field errors) and `validation` (field-by-field: `{"fields": {"<name>": {"value", "status": "green\|red\|yellow", "error"}}, "checksum_ok", ...}`) |
| `speed_accuracy` | `stretches` — per target speed: `target_speed_kmph`, `passed`, `duration_seconds`, `packet_count`, `average_speed_kmph`, `min_speed_kmph`, `max_speed_kmph`, `start` / `end` (samples, for the map); `criteria` |
| `geofence_crossing` | `detection` (`marked` \| `centre`), `geofence_points`, `entry_exit_distance_m`, `criteria`, `route` |
| `history_coverage` | `history_coverage_seconds`, `criteria` |
| `unique_cell_towers` | `operators_seen`; samples = one packet per unique tower |
| `voltage_internal` / `voltage_external` | `values_seen`; samples = one packet per unique voltage (sample has `voltage`) |
| `firmware_diff` | `versions_seen`; samples = last packet on the old version + first on the new |
| `esim_*` | `networks_seen` (`[old, new]`) |
| `vehicle_registration_diff` | `baseline_value`, `expected_value` |
| `reboot_restart_gap` | `command_sent_at` |
| `pvt_packet_drop` | see below |

### PVT packet drop test (#40) snapshot

Fixed 15-minute window from start; never passes before the window ends.

```json
{
  "mode": "pvt_packet_drop",
  "matched_count": 178,
  "pass": false,
  "reason": "Failed 1 of 9 checks: 1) 2 Emergency (EPB) gap(s) longer than the 3m 0s limit: first packet only at 10:47:07 IST, 4m 23s after the test started; stopped sending at 10:52:07 IST, 5m 37s before the test ended.",
  "checks": [
    {"check": "pvt_received", "label": "PVT packets received", "passed": true, "detail": null},
    {"check": "pvt_average_gap", "label": "PVT average gap 4-6s", "passed": true, "detail": null},
    {"check": "pvt_max_single_gap", "label": "No PVT gap longer than 3m 0s", "passed": true, "detail": null},
    {"check": "pvt_valid_gps", "label": "All PVT packets have a valid GPS fix and coordinate", "passed": true, "detail": null},
    {"check": "emergency_received", "label": "Emergency (EPB) packets received", "passed": true, "detail": null},
    {"check": "emergency_average_gap", "label": "Emergency (EPB) average gap 4-6s", "passed": true, "detail": null},
    {"check": "emergency_max_single_gap", "label": "No Emergency (EPB) gap longer than 3m 0s", "passed": false, "detail": "2 Emergency (EPB) gap(s) longer than ..."},
    {"check": "emergency_valid_gps", "label": "All Emergency (EPB) packets have a valid GPS fix and coordinate", "passed": true, "detail": null},
    {"check": "moving_share", "label": "At least 70% of PVT packets above 10 km/h", "passed": true, "detail": null}
  ],
  "failed_checks": ["emergency_max_single_gap"],
  "window_complete": true,
  "window_seconds": 900,
  "remaining_seconds": 0,
  "criteria": {
    "average_gap_seconds_range": [4, 6],
    "max_single_gap_seconds": 180,
    "all_packets_valid_gps": true,
    "moving_speed_kmph": 10,
    "min_moving_share": 0.7
  },
  "pvt": {
    "label": "PVT", "packet_count": 180, "average_gap_seconds": 4.97, "average_gap_ok": true,
    "longest_gap": {"seconds": 6.0, "from": "...", "to": "..."},
    "over_max_gap_count": 0, "over_max_gap_samples": [],
    "invalid_gps_count": 0, "invalid_gps_samples": [],
    "gap_stats": {"packet_count": 180, "average_gap_seconds": 5.0, "median_gap_seconds": 5.0, "min_gap_seconds": 4.0, "max_gap_seconds": 6.0, "...": "..."}
  },
  "emergency": { "label": "Emergency (EPB)", "packet_count": 178, "...": "..." },
  "moving_share": 0.83,
  "moving_ok": true,
  "route": [{"latitude": 26.19, "longitude": 91.75, "timestamp": "...", "speed": 32.5}],
  "window_start": "2026-10-14T10:42:44+00:00",
  "window_end": "2026-10-14T10:57:44+00:00",
  "refreshed_at": "2026-10-14T10:58:02+00:00",
  "commands_sent": []
}
```

While running, `reason` reads: `"Test still running -- 11m 0s left (ends at 16:54:16 IST). Keep the browser page open and the vehicle moving above 10 km/h with emergency ON, then refresh after it ends. Problems so far: ..."`.

---

## 8. Test catalog: criteria per test

Flags: **M** = manual confirmation, **Map** = map needed, **Cmd** = command needed, **Phy** = physical test.

| # | Test | Mode | Pass criteria (automated) | Flags | Configured commands |
|---|---|---|---|---|---|
| 1 | Physical SOS → Emergency Server | `gpsem` | 10 emergency (EMR, non-BLE) packets in a row, each ≤ 7 s apart, within 60 s | Phy | — |
| 2 | App SOS → Emergency Server | `gpsem` | 10 EMR packets with BLE flag in a row, each ≤ 7 s apart, within 60 s | Cmd | `sos_stop` |
| 3 | Physical SOS → Tracking Server | `packet_sequence` | EA,10 start packet + 9 NR packets with SOS flag = 1 within 60 s (10 total) | Phy | — |
| 4 | App SOS → Tracking Server | `packet_sequence` | EA,10 + BLE flag, then 10 NR packets with SOS flag = 1 within 60 s | Cmd | `sos_stop` |
| 5 | SOS stop on both servers | `sos_stop_both` | EA,11 on tracking **and** EPB SEM on emergency server; next NR has SOS flag = 0 | Cmd | `sos_stop` |
| 6 | FOTA upgrade A → B | `firmware_diff` | Firmware version changes during the window (A before, B after) | Cmd | — (custom) |
| 7 | Internal battery voltage | `voltage_internal` | 3 distinct internal voltage levels; every unique-level packet listed | M, Phy | — |
| 8 | External supply voltage | `voltage_external` | 3 distinct external voltage levels; every unique-level packet listed | M, Phy | — |
| 9 | Ignition ON status | `packet_sequence` | Last packet ignition = 0 → IN,07 alert → 8 packets ignition = 1 within 60 s | Phy | — |
| 10 | Ignition OFF status | `packet_sequence` | Last packet ignition = 1 → IF,08 alert → 8 packets ignition = 0 within 60 s | Phy | — |
| 11 | Harsh braking | `gps` | 3 HB,13 packets | M, Map, Phy | — |
| 12 | Harsh acceleration | `gps` | 3 HA,14 packets | M, Map, Phy | — |
| 13 | Rush turning | `gps` | 6 RT,15 packets (left/right confirmed manually) | M, Map, Phy | — |
| 14 | Tilt | `gps` | 3 TL,22 packets | M, Phy | — |
| 15 | GPS speed accuracy | `speed_accuracy` | 20, 40 and 70 km/h each held ±5 km/h for ≥ 60 s within 10 min | Map, Phy | — |
| 16 | Geofence entry/exit | `geofence_crossing` | Tester-marked IN and OUT points 950–1050 m apart | M, Map, Phy | — |
| 17 | External power disconnection | `packet_sequence` | Last packet main power = 1 → BD,03 alert → 8 packets main power = 0 | M, Phy | — |
| 18 | SOS harness disconnection | `gps` | 1 TA,16 packet | M, Phy | — |
| 19 | Device-box tamper *(optional)* | `gps` | 1 TA,09 packet | M, Phy | — |
| 20 | History data (Faraday box) | `history_coverage` | History (H) packets cover ≥ 2 min of the no-network period | M, Phy | — |
| 21 | A-GPS primary profile | `unique_cell_towers` | 3 unique cell towers; every unique-tower packet listed | M, Map, Cmd | — (custom) |
| 22 | A-GPS secondary profile | `unique_cell_towers` | 3 unique cell towers; every unique-tower packet listed | M, Map, Cmd | — (custom) |
| ~~23~~ | *removed* | | | | |
| 24 | eSIM primary → secondary | `esim_primary_to_secondary` | Last 2 packets on the old network, next 2 on the new one; order mirrors #25 | Cmd | — (custom) |
| 25 | eSIM secondary → primary | `esim_secondary_to_primary` | Same, reverse direction | Cmd | — (custom) |
| 26 | Login packet protocol | `protocol_packet` | 1 login packet, all fields valid, non-zero location | Cmd | — (custom) |
| 27 | Health packet protocol | `protocol_packet` | 1 health packet, all fields valid | Cmd | — (custom) |
| 28 | Emergency start packet protocol | `protocol_packet` | 1 EA,10 (non-BLE) packet, all fields + checksum valid | Phy | — |
| 29 | BLE emergency packet protocol | `protocol_packet` | 1 EA,10 + BLE flag packet, all fields + checksum valid | Phy | — |
| 30 | Tracking/NR packet protocol | `protocol_packet` | 1 NR packet, all fields + checksum valid | Cmd | — (custom) |
| 31 | Emergency stop packet protocol | `protocol_packet` | 1 EA,11 packet, all fields + checksum valid | Cmd | `sos_stop` |
| 32 | Main Battery Disconnected | `gps` | 1 BD,03 packet | Phy | — |
| 33 | Low Battery Disconnected | `gps` | 1 BL,04 packet | Phy | — |
| 34 | Low Battery Removed/Cleared | `gps` | 1 BH,05 / BL,05 packet | Phy | — |
| 35 | Main Battery Reconnected | `gps` | 1 BR,06 packet | Phy | — |
| 36 | Ignition ON alert | `gps` | 1 IN,07 packet | Cmd | — (custom) |
| 37 | Ignition OFF alert | `gps` | 1 IF,08 packet | Cmd | — (custom) |
| 38 | OT reboot command | `reboot_restart_gap` | After the reboot command: login → health → NR packet, in that order | M, Cmd | — (custom; key `reboot` or text with reboot/reset) |
| 39 | OT set vehicle registration no. | `vehicle_registration_diff` | OT,12 acknowledgement + NR packet carrying the number sent | Cmd | `set_reg_no` |
| 40 | PVT packet drop test (15 min) | `pvt_packet_drop` | Over 15 min: PVT and EPB average gap 4–6 s each, no gap > 3 min, every packet valid GPS, ≥ 70 % of PVT packets above 10 km/h | M, Map, Phy | — |
| 41 | Activation command + reply | `activation_command` | Activation SMS reply received matching the key sent | Cmd | — (SMS activation flow) |

The test window is `max(started_at, now − scan_window_seconds)` — 300 s by default; 600 s for #15, 900 s for #16/#20/#40, 3600 s for #21/#22.

---

## 9. Reference packet format

Protocol tests (#26–31) validate against the format sent by reference test device **AS01AA0005** (IMEI `866192070567555`, ARAI layout). A device whose packets differ fails with a reason such as:

> `packet layout does not match the reference format (test device AS01AA0005): it starts '$PVT,MAPW,1....' but a tracking packet must look like '$,PVT,...'`

| Packet | Reference example |
|---|---|
| Login | `$AS01AA0005,$866192070567555,$1.0.8,$1.0.4,$26.193007N91.752853E` |
| Health | `$,HLM,MAPW,1.0.8,866192070567555,100,10,0,5,5,0011,11.2 4.20,*` |
| Tracking (PVT) | `$,PVT,MAPW,1.0.8,NR,01,L,866192070567555,AS01AA0005,1,14102026,162615,26.192966,N,91.752884,E,0.0,301.64,24,62.9,0.9,0.6,AIRTEL,0,1,11.2,4.2,0,C,27,405,56,1BDA,6715,0000,0000,0,0000,0000,0,0000,0000,0,0000,0000,0,0011,00,333796,2F,*` |
| Emergency (EPB) | `$,EPB,SEM,866192070567555,NM,14102026052007,A,26.193026,N,91.752861,E,70.3,0.0,0.000,G,AS01AA0005,7635975659,*,18` |

**Checksums (hard failure on mismatch)** — 2 hex digits, XOR of the ASCII bytes:

- **PVT:** everything from `PVT` up to and including the frame number — i.e. between `$,` and the comma before the checksum (`PVT,MAPW,...,333796` → `2F`).
- **EPB:** everything from `EPB` up to and including `*` and any trailing extras such as the BLE `{SOS_PUB_...}` marker — i.e. between `$,` and the comma before the checksum.

**EPB date/time:** 14 digits, `DDMMYYYYHHMMSS`.

PVT field order after `$,PVT`: vendor, firmware, packet type, alert ID, packet status (L/H), IMEI, vehicle reg. no., GPS fix, date, time, latitude, N/S, longitude, E/W, speed, heading, satellites, altitude, PDOP, HDOP, operator, ignition, main power, external voltage, internal voltage, emergency status, box tamper, CSQ, MCC, MNC, LAC, cell ID, 4 × NMR (cell, LAC, signal), digital input, digital output, frame number, checksum, `*`.

**Alert codes used by the tests**

| Code | Meaning | Code | Meaning |
|---|---|---|---|
| NR,01 / NR,02 | Normal (live / history) | BD,03 | Main power disconnected |
| BL,04 | Low internal battery | BH,05 / BL,05 | Low battery recovered |
| BR,06 | Main power reconnected | IN,07 / IF,08 | Ignition ON / OFF |
| TA,09 | Box tamper | EA,10 / EA,11 | SOS start / SOS stop |
| OT,12 | Command acknowledgement | HB,13 / HA,14 | Harsh braking / acceleration |
| RT,15 | Rush turning | TA,16 | SOS harness (wire) cut |
| TL,22 | Tilt | | |

---

## 10. `check_config` reference

Editable per test via the upsert API (4.2). Unlisted keys are ignored.

| Mode | Key | Default | Meaning |
|---|---|---|---|
| `gps`, `gpsem` | `run_within_seconds` | — | With `max_interval_seconds`: the `min_match_count` packets in a row must fit in this span. |
| | `packet_label` | `matching` | Name used in reasons. |
| | `sample_limit` | 5 | Max samples returned. |
| `packet_sequence` | `trigger_regex` | — | Regex the alert packet must match. |
| | `trigger_label` | `alert` | Name used in reasons. |
| | `before` | — | `{"field", "equals", "label"}` the packet before the alert must satisfy (omit = not checked). |
| | `after` | — | `{"field", "equals", "label", "packet_type"}` the packets after must satisfy. |
| | `after_count` | 0 | Packets needed after the alert. |
| | `within_seconds` | — | They must arrive within this long of the alert. |
| `sos_stop_both` | `nr_after_count` | 1 | NR packets with SOS flag = 0 needed after EA,11. |
| `protocol_packet` | `category` | `tracking` | `login` \| `health` \| `tracking` \| `emergency`. |
| | `packet_label` | — | Name used in reasons. |
| | `require_location` | false | Location must be non-zero. |
| `speed_accuracy` | `target_speeds_kmph` | `[20, 40, 70]` | |
| | `tolerance_kmph` | 5 | |
| | `min_duration_seconds` | 60 | |
| | `max_packet_gap_seconds` | 15 | A longer gap breaks a stretch. |
| `geofence_crossing` | `expected_distance_m` | 1000 | |
| | `tolerance_pct` | 5 | |
| | `center_lat`, `center_lon`, `radius_m` | — | Optional: auto-detect entry/exit when no points are marked. |
| `history_coverage` | `min_coverage_seconds` | 120 | |
| | `max_gap_seconds` | 60 | Longer gap between H packets splits the stretch. |
| `esim_*` | `packets_each_side` | 2 | |
| `vehicle_registration_diff` | `require_ot_ack` | true | |

Fields `packet` names usable in `before`/`after.field`: any key of the sample `packet` object (e.g. `ignition`, `main_power`, `emergency_status`, `box_tamper`).

---

## 11. Deployment

```bash
python manage.py migrate skytron_api
```

| Migration | Does |
|---|---|
| `0111_onboarding_pvt_drop_fixed_window` | PVT packet drop test → 15-minute fixed window. |
| `0112_onboarding_test_plan_sheet` | New test case fields; `TechnicalOnboardingCommandDispatch` table; deactivates #23; swaps #40/#41; applies the test plan to every test. |

Executions already started keep their history; tests whose criteria changed should be re-run. Reversing `0112` restores #23 and the #40/#41 order but not the earlier per-test criteria.
