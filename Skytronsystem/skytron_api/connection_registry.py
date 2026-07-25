"""
Redis-backed live device connection registry and cross-process TCP command queue.

Tracks which device IMEIs are currently connected over which transport (TCP to
the GPS server on port 6000, TCP to the EM/emergency server on port 5001, or
MQTT) and provides a queue-based mechanism for sending raw commands down to a
live TCP connection that is held open by a *different* process than the one
issuing the command (the Django API process does not own the socket).

Every function here fails open: on any Redis error it logs and returns
None/empty/a safe default instead of raising, so a Redis outage degrades
connection-visibility/command-delivery features without breaking packet
ingestion or the API.

Key layout (all prefixed ``sk:`` for this feature):
    sk:conn:tcp:{imei}        JSON state, TTL 210s   (GPS TCP server, port 6000)
    sk:conn:tcpem:{imei}      JSON state, TTL 210s   (EM TCP server, port 5001)
    sk:conn:mqtt:{imei}       JSON state, TTL 300s   (no per-socket visibility,
                                                       only last-seen-message time)
    sk:tcpcmd:queue:gps       Redis list -- work queue for the GPS TCP dispatcher
    sk:tcpcmd:queue:em        Redis list -- work queue for the EM TCP dispatcher
    sk:tcpcmd:ack:{request_id}  Redis list -- one-shot delivery ack for a command
    sk:cmdhist:{imei}         Redis list, capped to 20 entries, TTL 30 days

A Redis list (not pub/sub) is used for command delivery because pub/sub
silently drops a message if no subscriber is listening at that exact instant
(a real risk during a container restart), whereas a list is at-least-
available-until-popped.
"""
import functools
import json
import logging
import time
import uuid

from django_redis import get_redis_connection

logger = logging.getLogger(__name__)

TCP_CONN_TTL = 210          # seconds; refreshed on every packet
MQTT_CONN_TTL = 300         # seconds; MQTT has no per-socket disconnect signal
CMD_HISTORY_MAX = 20
CMD_HISTORY_TTL = 30 * 24 * 3600   # 30 days
COMMAND_STALE_SECONDS = 30
ACK_LIST_TTL = 15           # one-shot ack list only needs to outlive the BLPOP wait

TRANSPORT_PORTS = {"tcp": 6000, "tcpem": 5001}
TRANSPORT_QUEUES = {"tcp": "sk:tcpcmd:queue:gps", "tcpem": "sk:tcpcmd:queue:em"}


def _conn_key(imei, transport):
    return f"sk:conn:{transport}:{imei}"


def _ack_key(request_id):
    return f"sk:tcpcmd:ack:{request_id}"


def _cmdhist_key(imei):
    return f"sk:cmdhist:{imei}"


def _fail_open(default=None):
    """Decorator: never let a Redis/serialization error escape this module."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                logger.warning("connection_registry.%s failed open: %s", func.__name__, exc)
                return default() if callable(default) else default
        return wrapper
    return decorator


def _load_existing_connected_at(conn, key, now):
    """Preserve connected_at across refreshes; first sighting sets it."""
    raw = conn.get(key)
    if not raw:
        return now
    try:
        existing = json.loads(raw)
        return existing.get("connected_at", now)
    except (ValueError, TypeError):
        return now


@_fail_open(default=None)
def record_tcp_connect(imei, client_ip, client_port, transport):
    """Record/refresh a live TCP(-EM) connection. Called on connect AND on
    every packet seen on that connection, so it doubles as the TTL refresh."""
    if transport not in TRANSPORT_PORTS:
        return None
    conn = get_redis_connection("default")
    key = _conn_key(imei, transport)
    now = time.time()
    state = {
        "protocol": transport,
        "port": TRANSPORT_PORTS[transport],
        "client_ip": client_ip,
        "client_port": client_port,
        "connected_at": _load_existing_connected_at(conn, key, now),
        "last_seen": now,
    }
    conn.setex(key, TCP_CONN_TTL, json.dumps(state))
    return state


@_fail_open(default=None)
def record_tcp_disconnect(imei, transport):
    if transport not in TRANSPORT_PORTS:
        return None
    conn = get_redis_connection("default")
    conn.delete(_conn_key(imei, transport))
    return True


@_fail_open(default=None)
def record_mqtt_seen(imei, topic):
    conn = get_redis_connection("default")
    key = _conn_key(imei, "mqtt")
    now = time.time()
    state = {
        "protocol": "mqtt",
        "topic": topic,
        "connected_at": _load_existing_connected_at(conn, key, now),
        "last_seen": now,
    }
    conn.setex(key, MQTT_CONN_TTL, json.dumps(state))
    return state


def _empty_connection_state(imei):
    return {
        "imei": imei,
        "live": False,
        "primary_transport": None,
        "primary_state": None,
        "other_transports": [],
    }


@_fail_open(default=None)
def get_connection_state(imei):
    """Check all three transports and return whichever was seen most
    recently, plus any other transports also currently live (dual-homed
    devices e.g. TCP + MQTT at once)."""
    conn = get_redis_connection("default")
    seen = []
    for transport in ("tcp", "tcpem", "mqtt"):
        raw = conn.get(_conn_key(imei, transport))
        if not raw:
            continue
        try:
            state = json.loads(raw)
        except (ValueError, TypeError):
            continue
        seen.append((transport, state))

    if not seen:
        return _empty_connection_state(imei)

    seen.sort(key=lambda pair: pair[1].get("last_seen", 0), reverse=True)
    primary_transport, primary_state = seen[0]
    return {
        "imei": imei,
        "live": True,
        "primary_transport": primary_transport,
        "primary_state": primary_state,
        "other_transports": [{"transport": t, "state": s} for t, s in seen[1:]],
    }


@_fail_open(default=lambda: 0)
def scan_live_count(transport):
    """Approximate count of IMEIs currently live on `transport`, using SCAN
    (never blocking KEYS) since this may run against a large keyspace."""
    conn = get_redis_connection("default")
    count = 0
    for _ in conn.scan_iter(match=f"sk:conn:{transport}:*", count=200):
        count += 1
    return count


@_fail_open(default=lambda: [])
def get_command_history(imei, limit=20):
    conn = get_redis_connection("default")
    raw_entries = conn.lrange(_cmdhist_key(imei), 0, limit - 1)
    entries = []
    for raw in raw_entries:
        try:
            entries.append(json.loads(raw))
        except (ValueError, TypeError):
            continue
    return entries


@_fail_open(default=None)
def push_command_history(imei, request_id, transport, payload, status, detail=""):
    conn = get_redis_connection("default")
    key = _cmdhist_key(imei)
    entry = json.dumps({
        "request_id": request_id,
        "transport": transport,
        "payload": payload,
        "status": status,
        "detail": detail,
        "ts": time.time(),
    })
    conn.lpush(key, entry)
    conn.ltrim(key, 0, CMD_HISTORY_MAX - 1)
    conn.expire(key, CMD_HISTORY_TTL)
    return True


@_fail_open(default=lambda: ("failed", "connection registry unavailable"))
def enqueue_tcp_command(imei, payload, transport, ack_timeout=5):
    """Push a command onto the relevant TCP dispatcher queue and block up to
    `ack_timeout` seconds waiting for delivery confirmation.

    Returns (result, detail) where result is one of:
        "delivered"     -- dispatcher sendall()'d the bytes and acked "sent"
        "queued_no_ack" -- pushed to the queue, but no ack arrived in time
        "no_connection" -- no live connection for this IMEI on this transport
        "failed"        -- unknown transport, or dispatcher acked an error
    """
    if transport not in TRANSPORT_QUEUES:
        return "failed", f"Unknown transport '{transport}'"

    conn = get_redis_connection("default")

    if not conn.exists(_conn_key(imei, transport)):
        return "no_connection", f"No live {transport} connection for IMEI {imei}"

    request_id = uuid.uuid4().hex
    item = {
        "request_id": request_id,
        "imei": imei,
        "payload": payload,
        "encoding": "utf-8",
        "issued_at": time.time(),
    }
    conn.rpush(TRANSPORT_QUEUES[transport], json.dumps(item))

    ack_timeout = max(1, int(ack_timeout))
    result = conn.blpop(_ack_key(request_id), timeout=ack_timeout)
    if not result:
        return (
            "queued_no_ack",
            f"Command queued (request_id={request_id}) but no delivery "
            f"confirmation within {ack_timeout}s",
        )

    _, raw_ack = result
    try:
        ack = json.loads(raw_ack)
    except (ValueError, TypeError):
        return "queued_no_ack", "Command queued but ack payload was unparseable"

    if ack.get("status") == "sent":
        return "delivered", f"Delivered {ack.get('bytes_sent', 0)} bytes (request_id={request_id})"
    return "failed", ack.get("error") or f"Dispatcher reported failure (request_id={request_id})"


# ---------------------------------------------------------------------------
# Dispatcher-side helpers -- used inside the TCP/EM server processes, not the
# API process.
# ---------------------------------------------------------------------------

@_fail_open(default=None)
def pop_command_for_dispatch(transport, timeout=1):
    """Blocking pop off the command queue for `transport`. Returns the
    command item dict, or None on timeout/error."""
    if transport not in TRANSPORT_QUEUES:
        return None
    conn = get_redis_connection("default")
    result = conn.blpop(TRANSPORT_QUEUES[transport], timeout=timeout)
    if not result:
        return None
    _, raw_item = result
    try:
        return json.loads(raw_item)
    except (ValueError, TypeError):
        return None


def is_command_stale(item):
    """True if `item` is missing an issued_at, or was issued more than
    COMMAND_STALE_SECONDS ago -- protects against executing a command after a
    long outage/restart froze the dispatcher."""
    if not item:
        return True
    issued_at = item.get("issued_at")
    if not issued_at:
        return True
    return (time.time() - issued_at) > COMMAND_STALE_SECONDS


@_fail_open(default=None)
def push_command_ack(request_id, ack_status, bytes_sent=0, error=""):
    conn = get_redis_connection("default")
    payload = json.dumps({
        "status": ack_status,
        "bytes_sent": bytes_sent,
        "error": error,
        "acked_at": time.time(),
    })
    key = _ack_key(request_id)
    conn.rpush(key, payload)
    conn.expire(key, ACK_LIST_TTL)
    return True
