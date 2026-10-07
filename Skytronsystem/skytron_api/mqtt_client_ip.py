"""
IMEI -> public IP for MQTT devices, kept in Redis.

An MQTT subscriber never sees the publisher's address -- the broker does not
forward it, and mosquitto-go-auth's HTTP backend doesn't send it either. The
one place it is recorded is the broker's own connect line:

    1791346448: New client connected from 106.222.247.168:58430 as mapwala_866192070567555 (p2, c0, k30, u'866192070567555').

The broker usually runs on a different VM, so mqtt_deployment/mqtt_ip_reporter.py
runs there, follows that log, and POSTs {imei, ip, ts} batches to
/api/mqtt/client-ip/report/ (device_ip_views.mqtt_client_ip_report), which
calls record_many() here. The MQTT client calls lookup() for each packet.

Key layout:
    sk:mqttip:{imei}   JSON {"ip": "...", "ts": <broker epoch>}, TTL 7 days

Fails open: on a Redis error lookup() returns None and the packet is stored
without an IP.
"""
import json
import logging
import threading
import time

from django_redis import get_redis_connection

logger = logging.getLogger(__name__)

KEY_TTL = 7 * 24 * 3600
LOCAL_CACHE_SECONDS = 10   # bounds Redis GETs per packet; a reconnect from a new IP shows up within this

_local = {}                # imei -> (ip, fetched_at)
_local_lock = threading.Lock()


def _key(imei):
    return f"sk:mqttip:{imei}"


def record_many(entries):
    """entries: iterable of (imei, ip, ts). Keeps the newest ts per IMEI, so a
    reporter replaying an old log after a restart can't overwrite a newer IP.
    Returns the number of keys written."""
    latest = {}
    for imei, ip, ts in entries:
        if imei not in latest or ts >= latest[imei][1]:
            latest[imei] = (ip, ts)
    if not latest:
        return 0

    conn = get_redis_connection("default")
    imeis = list(latest)
    existing = conn.mget([_key(i) for i in imeis])
    pipe = conn.pipeline(transaction=False)
    written = 0
    for imei, raw in zip(imeis, existing):
        ip, ts = latest[imei]
        if raw:
            try:
                if json.loads(raw).get("ts", 0) > ts:
                    continue
            except (ValueError, TypeError):
                pass
        pipe.setex(_key(imei), KEY_TTL, json.dumps({"ip": ip, "ts": ts}))
        written += 1
    pipe.execute()
    return written


def lookup(imei):
    if not imei:
        return None
    now = time.monotonic()
    with _local_lock:
        hit = _local.get(imei)
    if hit and now - hit[1] < LOCAL_CACHE_SECONDS:
        return hit[0]
    try:
        raw = get_redis_connection("default").get(_key(imei))
        ip = json.loads(raw)["ip"] if raw else None
    except Exception as exc:
        logger.warning("mqtt_client_ip.lookup failed open: %s", exc)
        ip = hit[0] if hit else None
    with _local_lock:
        _local[imei] = (ip, now)
    return ip
