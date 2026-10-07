# Device Source IP APIs

Each raw packet stored in `GPSDataLog` (tracking) and `GPSemDataLog` (emergency) now records:

| Field          | Meaning                                                                                       |
|----------------|-----------------------------------------------------------------------------------------------|
| `source_ip`    | The device's public IP. For TCP it comes from the socket. For MQTT it is reported from the broker VM (see [Broker VM setup](#broker-vm-setup-mqtt-ip)). `null` if unknown. |
| `imei`         | The IMEI from the packet (PVT/T field 7, EPB field 3). `null` if the packet can't be parsed.   |
| `network_name` | The network operator from the packet (PVT/T field 22, e.g. `AIRTEL`, `JIO`). EPB emergency packets have no operator field, so this is `null` for them. |

Only packets received **after deployment** have these values. Older rows stay `null`.

All APIs on this page are **superadmin only**. Any other role gets `403`.

```bash
BASE=https://api.skytron.in/api      # dev: https://api.gromed.in/api
TOKEN=<superadmin access token>
```

### Common query parameters (new `device-ip/*` APIs)

| Param       | Default | Allowed            | Notes                                        |
|-------------|---------|--------------------|----------------------------------------------|
| `source`    | `all`   | `gps`, `em`, `all` | `gps` = GPSDataLog, `em` = GPSemDataLog       |
| `days`      | `7`     | `1`–`90`           | Look-back window, based on server receive time |
| `page`      | `1`     | ≥ 1                |                                              |
| `page_size` | `50`    | `1`–`200`          |                                              |

Each result row includes `packet_count`, `first_seen`, `last_seen`, `network_names` (every operator seen) and `seen_in` (`["gps"]`, `["em"]` or both). Rows are sorted by `last_seen`, newest first.

---

## 1. Tracking raw log (existing API, now with IP)

`GET /api/gps-data-log-table/`

Returns the latest 200 rows. New optional filters: `ip` and `imei`. They can be combined with the existing `search`.

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE/gps-data-log-table/?ip=106.222.247.168&imei=866192070567555"
```

```json
{
  "data": "[{\"model\": \"skytron_api.gpsdatalog\", \"pk\": 25146301, \"fields\": {\"timestamp\": \"2026-10-07T04:20:33.120Z\", \"raw_data\": \"$,PVT,MAPW,1.0.8,NR,01,L,866192070567555,...,AIRTEL,...\", \"source_ip\": \"106.222.247.168\", \"imei\": \"866192070567555\", \"network_name\": \"AIRTEL\"}}]",
  "search_query": "",
  "ip": "106.222.247.168",
  "imei": "866192070567555"
}
```

As before, `data` is a JSON **string**, so parse it with `JSON.parse`. Each row's `fields` now includes `source_ip`, `imei` and `network_name`. An invalid `ip` returns `400`.

## 2. Emergency raw log (existing API, now with IP)

`GET /api/gps-em-data-log-table/` has the same filters and response shape as #1.

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE/gps-em-data-log-table/?imei=866192070567555"
```

---

## 3. Unique IP addresses

`GET /api/device-ip/unique/`

Lists every distinct source IP in the window. Extra param: `search` filters by IP prefix (e.g. `106.222`).

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE/device-ip/unique/?source=all&days=7&page=1&page_size=50"

# only IPs starting with 106.222, tracking packets only
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE/device-ip/unique/?source=gps&search=106.222"
```

```json
{
  "status": "success",
  "source": "gps+em",
  "days": 7,
  "pagination": { "page": 1, "page_size": 50, "total": 1, "total_pages": 1 },
  "data": [
    {
      "source_ip": "106.222.247.168",
      "packet_count": 3,
      "first_seen": "2026-10-07T04:33:42.932804Z",
      "last_seen": "2026-10-07T04:33:42.941920Z",
      "network_names": ["AIRTEL"],
      "seen_in": ["gps", "em"],
      "imei_count": 2
    }
  ]
}
```

## 4. IMEIs that sent from an IP (paginated)

`GET /api/device-ip/imeis/?ip=<ip>`

`ip` is required (IPv4 or IPv6).

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE/device-ip/imeis/?ip=106.222.247.168&days=30&page=1&page_size=50"
```

```json
{
  "status": "success",
  "ip": "106.222.247.168",
  "source": "gps+em",
  "days": 30,
  "pagination": { "page": 1, "page_size": 50, "total": 2, "total_pages": 1 },
  "data": [
    {
      "imei": "866192070567555",
      "packet_count": 2,
      "first_seen": "2026-10-07T04:33:42.932804Z",
      "last_seen": "2026-10-07T04:33:42.941920Z",
      "network_names": ["AIRTEL"],
      "seen_in": ["gps", "em"]
    }
  ]
}
```

## 5. IPs used by an IMEI

`GET /api/device-ip/by-imei/?imei=<imei>`

`imei` is required (14–17 digits). Results are paginated with the same params.

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE/device-ip/by-imei/?imei=866192070567555&days=30"
```

```json
{
  "status": "success",
  "imei": "866192070567555",
  "source": "gps+em",
  "days": 30,
  "pagination": { "page": 1, "page_size": 50, "total": 2, "total_pages": 1 },
  "data": [
    {
      "source_ip": "106.222.247.168",
      "packet_count": 2,
      "first_seen": "2026-10-07T04:33:42.932804Z",
      "last_seen": "2026-10-07T04:33:42.941920Z",
      "network_names": ["AIRTEL"],
      "seen_in": ["gps", "em"]
    },
    {
      "source_ip": "106.222.1.2",
      "packet_count": 1,
      "first_seen": "2026-10-07T04:33:42.933980Z",
      "last_seen": "2026-10-07T04:33:42.933980Z",
      "network_names": ["JIO"],
      "seen_in": ["gps"]
    }
  ]
}
```

---

## Errors

| HTTP | Body                                                                          | Cause                              |
|------|-------------------------------------------------------------------------------|------------------------------------|
| 400  | `{"status":"error","message":"days must be between 1 and 90."}`              | Bad `days` / `page` / `page_size`  |
| 400  | `{"status":"error","message":"source must be one of: gps, em, all."}`        | Bad `source`                       |
| 400  | `{"status":"error","message":"ip is required and must be a valid IPv4/IPv6 address."}` | Missing or invalid `ip` (#4) |
| 400  | `{"status":"error","message":"imei is required and must be 14-17 digits."}`  | Missing or invalid `imei` (#5)     |
| 401  | `{"detail":"Authentication credentials were not provided."}`                  | No or expired token                |
| 403  | `{"status":"error","message":"Only superadmin can access this."}`            | Caller is not superadmin           |

---

## Broker VM setup (MQTT IP)

An MQTT subscriber never sees a device's IP. Only the broker does, and it writes the IP to its log on each connect:

```
1791346448: New client connected from 106.222.247.168:58430 as mapwala_866192070567555 (p2, c0, k30, u'866192070567555').
```

The broker and the backend run on different VMs, so the data flows like this:

```
Broker VM                                   Backend VM
mosquitto.log ──▶ mqtt_ip_reporter.py ──POST──▶ /api/mqtt/client-ip/report/ ──▶ Redis sk:mqttip:{imei}
                  (systemd, stdlib only)                                           │
                                                 MQTT client container ◀── lookup ─┘
                                                 (stores source_ip on each packet)
```

Deploy in this order: backend first, then broker. Run `git pull` on both VMs first.

### 1. Backend VM: `deploy_device_ip_backend.sh`

```bash
cd ~/backendapi/SkytronInog_20260226/Skytrack_Backend   # repo checkout
git pull
sudo ./deploy_device_ip_backend.sh
```

The script:
1. Adds `MQTT_IP_REPORT_KEY` to `.env` if it's missing. It generates a 64-hex-character key and backs up `.env` first. If a key is already set, it keeps it.
2. Rebuilds the API container and runs `manage.py migrate`. Migration 0106 builds its indexes `CONCURRENTLY`, which can take a few minutes on the large log tables.
3. Rebuilds the MQTT client (`run_mqtt.sh`) and the TCP GPS/EM servers (`run_tcp.sh`).
4. Checks that 0106 is applied, that the API container has the key, and that all containers are running.
5. Prints the exact command to run on the broker VM, including the key.

Use `ENV_FILE=/path/to/file` to use an env file other than `.env`.

### 2. Broker VM: `install_mqtt_ip_reporter.sh`

```bash
cd <repo checkout on the broker VM>      # only install_mqtt_ip_reporter.sh + mqtt_deployment/ are needed
git pull
sudo ./install_mqtt_ip_reporter.sh --check --key <key printed by step 1>   # optional dry run
sudo ./install_mqtt_ip_reporter.sh --key <key printed by step 1>
```

The script:
1. Builds the backend URL from go-auth's `auth_opt_http_host` / `auth_opt_http_port`. That's the same backend the broker already calls, so it's reachable and in `ALLOWED_HOSTS`. Override it with `--url http://<backend>:2000/api/mqtt/client-ip/report/`.
2. Finds the broker log from `log_dest file` in the Mosquitto config (override with `--log`). It warns if `log_type` would skip connect lines, and shows the last 3 connects so you can see which IPs will be stored.
3. Sends an empty test batch to the backend, so that a wrong key (403), host not allowed (400), backend not deployed yet (404) or a network problem is caught before installing.
4. Installs `/opt/skytrack/mqtt_ip_reporter.py`, the systemd unit, and `/etc/skytrack/mqtt-ip-reporter.env` (mode 600, holds the key). Then it starts the `mqtt-ip-reporter` service and shows its log.

It never edits or restarts Mosquitto. If Mosquitto isn't logging to a file, the script stops and tells you which lines to add. Re-running the script is safe; it updates the files and restarts the reporter.

```bash
sudo journalctl -u mqtt-ip-reporter -f
# expect: [mqtt-ip-reporter] following /var/log/mosquitto/mosquitto.log; N devices queued
```

**Same-VM setups** (broker and backend on one VM, like dev): run both scripts on that VM.

The reporter needs only `python3` (standard library). It ignores `http_proxy`, survives logrotate, and replays the current and previous log on start. While the backend is down it keeps the latest IP per IMEI and retries every 10 s.

**Load balancer note:** if devices reach Mosquitto through a TCP load balancer or NAT, the broker logs the balancer's address, and that is what gets stored. Check with `grep "New client connected" mosquitto.log | tail`: you should see public device IPs.

**Timing note:** an IP reaches the backend about 1–2 s after the device connects. The first packet sent right after a connect or reconnect may be stored with the previous IP, or with `null` for a device seen for the first time.

### Report endpoint (called only by the reporter)

`POST /api/mqtt/client-ip/report/`, with header `X-MQTT-IP-Key: <MQTT_IP_REPORT_KEY>`. At most 2000 entries per call.

```bash
curl -s -X POST "http://10.192.136.175:2000/api/mqtt/client-ip/report/" \
  -H "Content-Type: application/json" \
  -H "X-MQTT-IP-Key: $MQTT_IP_REPORT_KEY" \
  -d '{"entries":[{"imei":"866192070567555","ip":"106.222.247.168","ts":1791346448}]}'
```

```json
{ "status": "success", "accepted": 1, "written": 1, "rejected": 0 }
```

`ts` is the broker log's epoch timestamp. An entry older than the IP already stored for that IMEI is ignored. A wrong or missing key returns `403 {"status":"error","message":"Forbidden."}`.
