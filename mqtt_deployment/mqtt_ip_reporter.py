#!/usr/bin/env python3
"""
Runs on the MQTT BROKER VM. Follows the Mosquitto log and reports each device's
public IP to the backend, so packets the MQTT client stores in GPSDataLog /
GPSemDataLog carry source_ip.

    1791346448: New client connected from 106.222.247.168:58430 as mapwala_866192070567555 (p2, c0, k30, u'866192070567555').
        -> {"imei": "866192070567555", "ip": "106.222.247.168", "ts": 1791346448}

Python 3 standard library only. Config via environment (see mqtt-ip-reporter.service):

    MQTT_IP_REPORT_URL   e.g. http://10.192.136.175:2000/api/mqtt/client-ip/report/
                         (same backend host:port go-auth's auth_opt_http_host points at)
    MQTT_IP_REPORT_KEY   must equal MQTT_IP_REPORT_KEY in the backend .env
    MQTT_BROKER_LOG_PATH default /var/log/mosquitto/mosquitto.log

On start it replays mosquitto.log.1 and mosquitto.log, so devices that connected
before the reporter restarted are still covered. Every RESEND_SECONDS it re-sends
every IMEI it knows, so a backend redeploy that recreates Redis is healed within
minutes without waiting for devices to reconnect. Unsent entries are retried;
only the latest IP per IMEI is kept while the backend is unreachable.
"""
import ipaddress
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

REPORT_URL = os.environ.get("MQTT_IP_REPORT_URL", "")
REPORT_KEY = os.environ.get("MQTT_IP_REPORT_KEY", "")
LOG_PATH = os.environ.get("MQTT_BROKER_LOG_PATH", "/var/log/mosquitto/mosquitto.log")

POLL_SECONDS = 0.5
FLUSH_SECONDS = 1.0
BATCH_MAX = 1000          # backend accepts up to 2000 per request
HTTP_TIMEOUT = 10
RESEND_SECONDS = 300      # full re-send of `known`; backend ignores entries older than what it has

_CONNECT_RE = re.compile(
    r"^(?P<ts>\d+): New client connected from (?P<addr>\S+) as (?P<clientid>\S+) \(.*?u'(?P<username>[^']*)'"
)
_IMEI_RE = re.compile(r"(\d{14,17})$")

# Never send this internal call through an HTTP(S) proxy from the environment.
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

known = {}     # imei -> {"imei", "ip", "ts"}; latest connect seen per IMEI
pending = {}   # subset of `known` not yet delivered


def log(msg):
    print(f"[mqtt-ip-reporter] {msg}", flush=True)


def parse_ip(addr):
    """'1.2.3.4:5678' / '::1:5678' / '[::1]:5678' -> '1.2.3.4' / '::1'."""
    host = addr.rsplit(":", 1)[0].strip("[]")
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        return None


def handle_line(line):
    if "New client connected" not in line:
        return
    m = _CONNECT_RE.search(line)
    if not m:
        return
    ip = parse_ip(m.group("addr"))
    if not ip:
        return
    ts = int(m.group("ts"))
    imeis = set()
    if _IMEI_RE.fullmatch(m.group("username")):
        imeis.add(m.group("username"))
    cid = _IMEI_RE.search(m.group("clientid"))
    if cid:
        imeis.add(cid.group(1))
    for imei in imeis:
        cur = known.get(imei)
        if cur is None or ts >= cur["ts"]:
            entry = {"imei": imei, "ip": ip, "ts": ts}
            known[imei] = entry
            pending[imei] = entry


def flush():
    """Send pending entries in batches. Returns False if the backend is unreachable."""
    while pending:
        batch = list(pending.values())[:BATCH_MAX]
        req = urllib.request.Request(
            REPORT_URL,
            data=json.dumps({"entries": batch}).encode(),
            headers={"Content-Type": "application/json", "X-MQTT-IP-Key": REPORT_KEY},
            method="POST",
        )
        try:
            with _opener.open(req, timeout=HTTP_TIMEOUT) as resp:
                resp.read()
        except urllib.error.HTTPError as e:
            log(f"backend rejected batch: HTTP {e.code} {e.read()[:200]!r}")
            if e.code in (400, 403):
                # Bad key / bad payload won't fix itself by retrying this batch.
                for entry in batch:
                    pending.pop(entry["imei"], None)
            return False
        except Exception as e:
            log(f"backend unreachable: {e}")
            return False
        for entry in batch:
            # Drop only if no newer entry arrived for this IMEI meanwhile.
            if pending.get(entry["imei"]) is entry:
                del pending[entry["imei"]]
    return True


def replay(path):
    try:
        with open(path, "r", errors="replace") as fh:
            for line in fh:
                handle_line(line)
    except OSError:
        pass


def main():
    if not REPORT_URL or not REPORT_KEY:
        log("MQTT_IP_REPORT_URL and MQTT_IP_REPORT_KEY must be set")
        sys.exit(2)

    replay(LOG_PATH + ".1")
    fh, inode = None, None
    last_flush, backoff_until = 0.0, 0.0
    last_resend = time.monotonic()
    while True:
        try:
            if fh is None:
                fh = open(LOG_PATH, "r", errors="replace")
                inode = os.fstat(fh.fileno()).st_ino
                for line in fh:            # replay current file, leaves us at EOF
                    handle_line(line)
                log(f"following {LOG_PATH}; {len(pending)} devices queued")

            line = fh.readline()
            if line:
                handle_line(line)

            # Checked every line, not just at EOF: with log_type all the log
            # rarely sits at EOF, and connects must still go out within ~1s.
            now = time.monotonic()
            if now - last_resend >= RESEND_SECONDS:
                last_resend = now
                pending.update(known)
            due = now - last_flush >= FLUSH_SECONDS or len(pending) >= BATCH_MAX
            if pending and due and now >= backoff_until:
                last_flush = now
                if not flush():
                    backoff_until = now + 10

            if not line:
                # EOF: detect logrotate (new inode) or copytruncate (file shrank).
                time.sleep(POLL_SECONDS)
                st = os.stat(LOG_PATH)
                if st.st_ino != inode:
                    fh.close()
                    fh = open(LOG_PATH, "r", errors="replace")
                    inode = os.fstat(fh.fileno()).st_ino
                elif st.st_size < fh.tell():
                    fh.seek(0)
        except OSError as e:
            log(f"cannot read {LOG_PATH}: {e}; retrying in 30s")
            if fh is not None:
                fh.close()
                fh = None
            time.sleep(30)


if __name__ == "__main__":
    main()
