"""
Internal server-health snapshot: host resources, Postgres connection
pressure, Mosquitto $SYS stats, and live TCP connection counts from the
connection registry. Superadmin-only, click-to-reload (no polling).
"""
import os
import socket
import ssl
import threading

import paho.mqtt.client as mqtt
import psutil
from django.db import connection as db_connection, transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import connection_registry
from .throttles import ServerHealthRateThrottle

_SYS_KEYS_OF_INTEREST = {
    '$SYS/broker/clients/connected': 'clients_connected',
    '$SYS/broker/load/messages/received/1min': 'messages_per_min_in',
    '$SYS/broker/load/messages/sent/1min': 'messages_per_min_out',
    '$SYS/broker/bytes/received': 'bytes_received_total',
    '$SYS/broker/bytes/sent': 'bytes_sent_total',
    '$SYS/broker/uptime': 'uptime',
}


def _collect_host_stats():
    try:
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        try:
            load1, load5, load15 = os.getloadavg()
        except (OSError, AttributeError):
            load1 = load5 = load15 = None

        hostname = socket.gethostname()
        try:
            ip_address = socket.gethostbyname(hostname)
        except socket.gaierror:
            ip_address = None

        return {
            'ok': True,
            'hostname': hostname,
            'ip_address': ip_address,
            'cpu_percent': psutil.cpu_percent(interval=0.3),
            'cpu_count': psutil.cpu_count(),
            'load_avg_1m': load1,
            'load_avg_5m': load5,
            'load_avg_15m': load15,
            'memory_total_mb': round(vm.total / (1024 * 1024), 1),
            'memory_used_mb': round(vm.used / (1024 * 1024), 1),
            'memory_percent': vm.percent,
            'disk_total_gb': round(disk.total / (1024 ** 3), 2),
            'disk_used_gb': round(disk.used / (1024 ** 3), 2),
            'disk_percent': disk.percent,
        }
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def _collect_postgres_stats():
    """SET LOCAL statement_timeout so this can never itself hang the request,
    even if pg_stat_activity is under heavy contention."""
    try:
        with transaction.atomic():
            with db_connection.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout = '3000ms'")
                cursor.execute(
                    """
                    SELECT state, query, now() - query_start AS duration
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                    """
                )
                rows = cursor.fetchall()
                cursor.execute("SHOW max_connections")
                max_connections = cursor.fetchone()[0]

        active = idle = idle_in_tx = 0
        longest_query = None
        longest_seconds = None
        for state, query, duration in rows:
            if state == 'active':
                active += 1
                if query and (longest_seconds is None or duration.total_seconds() > longest_seconds):
                    longest_query = query
                    longest_seconds = duration.total_seconds()
            elif state == 'idle':
                idle += 1
            elif state and state.startswith('idle in transaction'):
                idle_in_tx += 1

        return {
            'ok': True,
            'total_connections': len(rows),
            'active_connections': active,
            'idle_connections': idle,
            'idle_in_transaction_connections': idle_in_tx,
            'longest_running_active_query': longest_query,
            'longest_running_active_query_seconds': longest_seconds,
            'max_connections': int(max_connections),
        }
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def _collect_mqtt_sys_stats(timeout_seconds=2.5):
    """Mosquitto only republishes $SYS topics periodically, so a short
    collection window can legitimately miss some -- hence `partial`."""
    collected = {}
    try:
        broker_host = os.getenv('MQTT_BROKER_HOST', 'localhost')
        broker_port = int(os.getenv('MQTT_BROKER_PORT', '8883'))
        username = os.getenv('MQTT_USERNAME', '')
        password = os.getenv('MQTT_PASSWORD', '')
        ca_cert = '/app/keys/ca.crt'

        all_collected = threading.Event()

        def _on_message(client, userdata, msg):
            try:
                collected[msg.topic] = msg.payload.decode('utf-8', errors='replace')
            except Exception:
                pass
            if all(topic in collected for topic in _SYS_KEYS_OF_INTEREST):
                all_collected.set()

        client = mqtt.Client()
        client.username_pw_set(username, password)
        client.tls_set(ca_certs=ca_cert, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
        client.on_message = _on_message
        client.connect(broker_host, broker_port, 60)
        # Only the topics we report, and stop as soon as all have arrived
        # (they are retained, so normally immediately) instead of always
        # sleeping for the full window.
        client.subscribe([(topic, 0) for topic in _SYS_KEYS_OF_INTEREST])
        client.loop_start()
        all_collected.wait(timeout_seconds)
        # Disconnect first: it wakes the network loop, so loop_stop() returns
        # at once instead of waiting out the loop's 1s select timeout.
        client.disconnect()
        client.loop_stop()

        stats = {
            key: collected[topic]
            for topic, key in _SYS_KEYS_OF_INTEREST.items()
            if topic in collected
        }
        return {
            'ok': True,
            'partial': len(stats) < len(_SYS_KEYS_OF_INTEREST),
            'collected_keys': len(stats),
            'expected_keys': len(_SYS_KEYS_OF_INTEREST),
            **stats,
        }
    except Exception as e:
        return {'ok': False, 'partial': True, 'error': str(e)}


def _collect_tcp_stats():
    return {
        'tcp_live_count': connection_registry.scan_live_count('tcp'),
        'tcpem_live_count': connection_registry.scan_live_count('tcpem'),
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([ServerHealthRateThrottle])
def server_health_summary(request):
    if getattr(request.user, 'role', None) != 'superadmin':
        return Response(
            {'status': 'error', 'message': 'Forbidden: this endpoint exposes internal infrastructure details and is superadmin-only'},
            status=status.HTTP_403_FORBIDDEN,
        )

    # The MQTT collection is a network wait, so run it alongside the others.
    # It touches no Django DB connection, which keeps it safe in a thread.
    mqtt_stats = {}
    mqtt_thread = threading.Thread(target=lambda: mqtt_stats.update(_collect_mqtt_sys_stats()), daemon=True)
    mqtt_thread.start()

    collected_at = timezone.now()
    host_stats = _collect_host_stats()
    postgres_stats = _collect_postgres_stats()
    tcp_stats = _collect_tcp_stats()
    mqtt_thread.join()

    return Response({
        'status': 'success',
        'collected_at': collected_at,
        'host': host_stats,
        'postgres': postgres_stats,
        'mqtt': mqtt_stats,
        'tcp': tcp_stats,
    })


_DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Server Health</title>
<style>
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 20px; color: #1a1a1a; background: #f7f7f8; }
  h1 { font-size: 20px; margin-bottom: 4px; }
  .box { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 14px 16px; margin-bottom: 16px; }
  button.primary { background: #2563eb; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; }
  table { border-collapse: collapse; width: 100%; margin-top: 8px; }
  th, td { border: 1px solid #e5e5e5; padding: 6px 10px; font-size: 13px; text-align: left; }
  th { background: #f0f0f2; width: 260px; }
  .placeholder { color: #888; font-size: 13px; padding: 20px 0; text-align: center; }
  .warn { color: #b45309; font-size: 12px; }
  .err { color: #b91c1c; font-size: 12px; }
</style>
</head>
<body>
<h1>Server Health</h1>

<div class="box token-box">
  <label>Bearer token: <input id="token" type="text" style="width:360px" placeholder="paste auth token here"></label>
  <button class="primary" onclick="saveToken()">Save</button>
  <span id="tokenStatus" style="margin-left:8px;font-size:12px;color:#666;"></span>
</div>

<div class="box">
  <button class="primary" onclick="reload()">Reload</button>
  <span id="lastFetched" style="margin-left:10px;font-size:12px;color:#666;"></span>
</div>

<div id="content" class="box">
  <div class="placeholder">Click Reload to fetch current server health. This page never auto-refreshes.</div>
</div>

<script>
const API_URL = '/api/server-health/summary/';

function getToken() { return localStorage.getItem('serverHealthToken') || ''; }
function saveToken() {
  localStorage.setItem('serverHealthToken', document.getElementById('token').value.trim());
  document.getElementById('tokenStatus').textContent = 'Saved.';
}
// Shareable pre-authenticated links: ?token=... seeds localStorage once, then
// is stripped from the address bar so it doesn't linger there afterward.
function seedTokenFromQuery(storageKey) {
  const params = new URLSearchParams(window.location.search);
  const qToken = params.get('token');
  if (!qToken) return false;
  localStorage.setItem(storageKey, qToken);
  params.delete('token');
  const newSearch = params.toString();
  window.history.replaceState({}, '', window.location.pathname + (newSearch ? '?' + newSearch : '') + window.location.hash);
  return true;
}
(function initToken() {
  const seededFromLink = seedTokenFromQuery('serverHealthToken');
  const t = getToken();
  if (t) {
    document.getElementById('token').value = t;
    document.getElementById('tokenStatus').textContent = seededFromLink ? 'Loaded from shared link.' : 'Loaded from storage.';
  }
})();

function kvTable(title, obj) {
  if (!obj) return '';
  let rows = Object.entries(obj).map(([k, v]) => `<tr><th>${k}</th><td>${v === null || v === undefined ? '' : v}</td></tr>`).join('');
  return `<h3>${title}</h3><table>${rows}</table>`;
}

async function reload() {
  const content = document.getElementById('content');
  content.innerHTML = '<div class="placeholder">Loading...</div>';
  const t = getToken();
  const headers = t ? { 'Authorization': 'Token ' + t } : {};
  try {
    const res = await fetch(API_URL, { headers });
    const data = await res.json();
    if (!res.ok) {
      content.innerHTML = `<div class="err">Error ${res.status}: ${data.message || 'request failed'}</div>`;
      return;
    }
    let html = '';
    html += kvTable('Host', data.host);
    if (data.postgres && !data.postgres.ok) html += `<div class="err">Postgres: ${data.postgres.error}</div>`;
    html += kvTable('Postgres', data.postgres);
    if (data.mqtt && data.mqtt.partial) html += `<div class="warn">MQTT $SYS collection was partial (${data.mqtt.collected_keys}/${data.mqtt.expected_keys} keys)</div>`;
    html += kvTable('MQTT Broker', data.mqtt);
    html += kvTable('Live TCP Connections', data.tcp);
    content.innerHTML = html;
    document.getElementById('lastFetched').textContent = 'Last fetched: ' + new Date(data.collected_at).toLocaleString();
  } catch (e) {
    content.innerHTML = `<div class="err">Request failed: ${e}</div>`;
  }
}
</script>
</body>
</html>
"""


def server_health_dashboard(request):
    return HttpResponse(_DASHBOARD_HTML)
