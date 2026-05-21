# Skytrack · JMeter Load Testing Guide

## Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Apache JMeter | 5.6+ | https://jmeter.apache.org/download_jmeter.cgi |
| Java JDK | 11+ | Required to run JMeter |
| JMeter Plugins Manager | Latest | https://jmeter-plugins.org/install/Install/ |

### Install JMeter on Ubuntu/Azure VM
```bash
sudo apt-get install -y default-jdk
wget https://dlcdn.apache.org/jmeter/binaries/apache-jmeter-5.6.3.tgz
tar -xzf apache-jmeter-5.6.3.tgz
export JMETER_HOME=~/apache-jmeter-5.6.3
export PATH=$JMETER_HOME/bin:$PATH
```

---

## Quick Setup

### 1. Ensure the server is running in DEBUG mode
The JMX tests use `POST /api/dev/token/` for authentication.  
This endpoint returns **403** when `DEBUG=False`.

```bash
# In Skytronsystem/skytron_api/views.py, confirm:
REMOVE_OTP_CAP = False   # leave as-is
STATIC_OTP_CAP = False   # leave as-is
# Django settings: DEBUG = True (set in .env or settings.py)
```

### 2. Verify the server is accessible
```bash
curl -s -X POST http://localhost:8000/api/generate-captcha/ \
     -H "Content-Type: application/json" -d '{}' | python3 -m json.tool
# Should return: {"key": "...", "captcha": "...base64..."}
```

---

## Test 1 · Captcha Generation (`captcha_load_test.jmx`)

### What it tests
`POST /api/generate-captcha/` — measures throughput and latency when many
concurrent users request captchas simultaneously.

### SLAs enforced
- HTTP 200 on every request
- Response body contains `"key"` and `"captcha"` fields
- Response time < **2000 ms** (assertion fails the sample if exceeded)

### Run (GUI mode — for setup/debugging)
```bash
$JMETER_HOME/bin/jmeter -t captcha_load_test.jmx
```

### Run (CLI/non-GUI mode — for actual load testing)
```bash
$JMETER_HOME/bin/jmeter \
  -n \
  -t captcha_load_test.jmx \
  -l results/captcha_results.jtl \
  -e -o results/captcha_report/ \
  -JTARGET_HOST=localhost \
  -JTARGET_PORT=8000 \
  -JTHREADS=50 \
  -JRAMP_UP=30 \
  -JDURATION=120
```

### Key parameters (all overridable via `-J<param>=<value>`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `TARGET_HOST` | `localhost` | Server hostname or IP |
| `TARGET_PORT` | `8000` | Server port |
| `THREADS` | `50` | Concurrent virtual users |
| `RAMP_UP` | `30` | Seconds to ramp from 0 → THREADS |
| `DURATION` | `120` | Total test duration (seconds) |

### Typical baseline targets (single-server Django)

| Metric | Target | Notes |
|--------|--------|-------|
| Throughput | ≥ 200 req/s | Django dev server = ~20 req/s; Gunicorn+Nginx = 200+ |
| p95 latency | < 500 ms | |
| Error rate | < 1% | |

### Interpreting results
```bash
# Generate HTML report after run:
$JMETER_HOME/bin/jmeter -g results/captcha_results.jtl -o results/captcha_report/
# Open results/captcha_report/index.html in browser
```

---

## Test 2 · Live Tracking (`live_tracking_load_test.jmx`)

### What it tests
Simulates N concurrent dashboard operators polling GPS data in a loop:
1. **SETUP (once)**: `POST /api/dev/token/` → stores JWT in a shared JMeter property
2. **Main loop** (per user, for DURATION seconds):
   - `POST /api/gps_track_data_api/` — full GPS dataset (page_size = 50)
   - Wait POLL_INTERVAL_MS ms
   - `POST /api/gps_track_lite/` — lightweight fields only
   - `POST /api/gps_cluster/` — cluster summary for map overview
   - Wait 200 ms

### SLAs enforced
| Endpoint | SLA |
|----------|-----|
| `/api/gps_track_data_api/` | < 3000 ms |
| `/api/gps_track_lite/` | < 2000 ms |
| `/api/gps_cluster/` | < 3000 ms |

### Run (CLI)
```bash
mkdir -p results

$JMETER_HOME/bin/jmeter \
  -n \
  -t live_tracking_load_test.jmx \
  -l results/tracking_results.jtl \
  -e -o results/tracking_report/ \
  -JTARGET_HOST=localhost \
  -JTARGET_PORT=8000 \
  -JLOGIN_USERNAME=9999999999 \
  -JLOGIN_PASSWORD=YourPlainTextPassword \
  -JTHREADS=30 \
  -JRAMP_UP=60 \
  -JDURATION=180 \
  -JPOLL_INTERVAL_MS=3000 \
  -JPAGE_SIZE=50
```

### Key parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `TARGET_HOST` | `localhost` | Server host |
| `TARGET_PORT` | `8000` | Server port |
| `LOGIN_USERNAME` | `9999999999` | Test user mobile |
| `LOGIN_PASSWORD` | `YourPlainTextPassword` | Plain-text password |
| `THREADS` | `30` | Concurrent dashboard users |
| `RAMP_UP` | `60` | Ramp-up seconds |
| `DURATION` | `180` | Test duration (seconds) |
| `POLL_INTERVAL_MS` | `3000` | ms between GPS polls |
| `PAGE_SIZE` | `50` | Vehicles per page |

---

## Recommended Test Progression

Run in this order to avoid overwhelming the server immediately:

```
Step 1:  THREADS=5,  DURATION=60   → baseline sanity check
Step 2:  THREADS=10, DURATION=120  → light load
Step 3:  THREADS=25, DURATION=120  → moderate load
Step 4:  THREADS=50, DURATION=180  → stress test
Step 5:  THREADS=100, DURATION=180 → spike test (find breaking point)
```

---

## Monitoring the Server During Tests

Open a second terminal and run:

```bash
# CPU + Memory
watch -n 2 "free -m && top -b -n1 | head -20"

# Django logs (if running via gunicorn)
tail -f /var/log/gunicorn/access.log

# PostgreSQL active queries
watch -n 5 "psql -U dbadmin -d skytrondb_main -c \"SELECT pid, now()-query_start AS dur, left(query,80) FROM pg_stat_activity WHERE state='active';\""

# Redis connections
redis-cli info clients

# Django request rate (from journal)
journalctl -fu gunicorn --since "1 min ago" | grep "POST /api/gps"
```

---

## Adding More Load Test Scenarios

You can extend the existing JMX files or create new ones for:

### SOS Call List Polling
```
POST /api/EM/DEx/getPendingCallList/
POST /api/EM/DEx/getLiveCallList/
```
Scenario: 10 dispatch operators polling every 2 seconds.

### Dashboard Load
```
POST /api/dashboard/vehicle-monitoring/
POST /api/dashboard/erss-summary/
POST /api/central_api/
```
Scenario: 20 concurrent superadmin users viewing dashboards.

### Device Tagging Flow
```
POST /api/tag/TagDevice2Vehicle/
POST /api/tag/TagSendOwnerOtp/
POST /api/tag/TagVerifyOwnerOtp/
```
Scenario: 5 concurrent dealers completing tagging workflows.

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `403 Forbidden` on `/api/dev/token/` | `DEBUG=False` on server | Set `DEBUG=True` for test env |
| `401 Unauthorized` on GPS endpoints | JWT not stored | Check SETUP thread succeeded |
| `Connection refused` | Server not running | Start Django: `python manage.py runserver` |
| Very high latency | Django dev server (single-threaded) | Switch to Gunicorn: `gunicorn --workers 4 Skytronsystem.wsgi` |
| `Too Many Requests` (429) | DRF throttle: `user: 1000/hour` | Increase throttle in settings.py or disable for load test |
| Out of memory in JMeter | Large response data | Disable "Save Response Data" in result collectors |

### Disable DRF throttling for load tests
In `Skytronsystem/Skytronsystem/settings.py`:
```python
# Temporarily remove throttle classes for load testing:
REST_FRAMEWORK = {
    ...
    # 'DEFAULT_THROTTLE_CLASSES': [...],  # comment out
    # 'DEFAULT_THROTTLE_RATES': {...},    # comment out
}
```
**Remember to re-enable before deploying to production.**

---

## Generating HTML Report from Existing .jtl

```bash
$JMETER_HOME/bin/jmeter \
  -g results/captcha_results.jtl \
  -o results/captcha_html_report/
```

Open `results/captcha_html_report/index.html` — includes:
- Response time percentiles (p50/p90/p95/p99)
- Throughput over time
- Error rate
- Active threads over time
- Response time distribution histogram
