"""
Device lookup and command console: find a device by IMEI, see which
transport it's currently live on, browse its recent raw log lines, and send
a raw command down to whichever transport it's connected over.
"""
import os
import ssl
import uuid
from datetime import timedelta

import paho.mqtt.client as mqtt
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import connection_registry
from .alert_stats_views import _scope_device_tags
from .models import GPSDataLog, GPSemDataLog
from .throttles import DeviceCommandRateThrottle

VALID_LOG_TYPES = {'tracking', 'emergency', 'both'}
VALID_TRANSPORTS = {'auto', 'tcp', 'tcpem', 'mqtt'}
RESULT_HTTP_STATUS = {
    'delivered': status.HTTP_200_OK,
    'queued_no_ack': status.HTTP_202_ACCEPTED,
    'no_connection': status.HTTP_404_NOT_FOUND,
    'failed': status.HTTP_502_BAD_GATEWAY,
}


def _find_device_tag(device_tags_qs, imei):
    device_tag = device_tags_qs.filter(device__imei=imei).select_related(
        'device', 'device__model', 'vehicle_owner'
    ).first()
    if device_tag:
        return device_tag
    return device_tags_qs.filter(device__imei__icontains=imei).select_related(
        'device', 'device__model', 'vehicle_owner'
    ).first()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def device_inspector_lookup(request):
    imei = (request.GET.get('imei') or '').strip()
    if not imei:
        return Response({'status': 'error', 'message': 'imei is required'}, status=status.HTTP_400_BAD_REQUEST)

    device_tags_qs, err = _scope_device_tags(request.user)
    if err:
        return err

    device_tag = _find_device_tag(device_tags_qs, imei)
    if not device_tag:
        return Response(
            {'status': 'error', 'message': f'No device found for IMEI {imei}'},
            status=status.HTTP_404_NOT_FOUND,
        )

    real_imei = device_tag.device.imei if device_tag.device else imei

    return Response({
        'status': 'success',
        'device_tag_id': device_tag.id,
        'vehicle_reg_no': device_tag.vehicle_reg_no,
        'device_status': device_tag.status,
        'imei': real_imei,
        'device_stock_id': device_tag.device.id if device_tag.device else None,
        'device_esn': device_tag.device.device_esn if device_tag.device else None,
        'vehicle_owner': device_tag.vehicle_owner.company_name if device_tag.vehicle_owner else None,
        'connection': connection_registry.get_connection_state(real_imei),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def device_inspector_logs(request):
    imei = (request.GET.get('imei') or '').strip()
    if not imei:
        return Response({'status': 'error', 'message': 'imei is required'}, status=status.HTTP_400_BAD_REQUEST)

    log_type = request.GET.get('log_type', 'both')
    if log_type not in VALID_LOG_TYPES:
        return Response(
            {'status': 'error', 'message': f"log_type must be one of {sorted(VALID_LOG_TYPES)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        page = max(1, int(request.GET.get('page', 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(request.GET.get('page_size', 20))
    except (TypeError, ValueError):
        page_size = 20
    page_size = max(1, min(page_size, 100))
    try:
        lookback_days = max(1, int(request.GET.get('lookback_days', 7)))
    except (TypeError, ValueError):
        lookback_days = 7

    device_tags_qs, err = _scope_device_tags(request.user)
    if err:
        return err
    if not _find_device_tag(device_tags_qs, imei):
        return Response(
            {'status': 'error', 'message': f'No device found for IMEI {imei} in your scope'},
            status=status.HTTP_404_NOT_FOUND,
        )

    cutoff = timezone.now() - timedelta(days=lookback_days)
    # Bound the per-table fetch so a deep page on a chatty device can't scan
    # unbounded rows -- neither log table has an IMEI column, so every row
    # here already cost a raw_data__contains scan within the lookback window.
    fetch_limit = min(page * page_size, 1000)

    def _fetch(model, type_label):
        qs = model.objects.filter(raw_data__contains=imei, timestamp__gte=cutoff).order_by('-timestamp')
        total = qs.count()
        rows = [
            {'log_type': type_label, 'id': row.id, 'timestamp': row.timestamp, 'raw_data': row.raw_data}
            for row in qs[:fetch_limit]
        ]
        return rows, total

    if log_type == 'tracking':
        rows, total = _fetch(GPSDataLog, 'tracking')
    elif log_type == 'emergency':
        rows, total = _fetch(GPSemDataLog, 'emergency')
    else:
        tracking_rows, tracking_total = _fetch(GPSDataLog, 'tracking')
        emergency_rows, emergency_total = _fetch(GPSemDataLog, 'emergency')
        rows = sorted(tracking_rows + emergency_rows, key=lambda r: r['timestamp'], reverse=True)
        total = tracking_total + emergency_total

    start = (page - 1) * page_size
    page_rows = rows[start:start + page_size]
    total_pages = (total + page_size - 1) // page_size if page_size else 0

    return Response({
        'status': 'success',
        'imei': imei,
        'log_type': log_type,
        'lookback_days': lookback_days,
        'page': page,
        'page_size': page_size,
        'total_count': total,
        'total_pages': total_pages,
        'logs': page_rows,
    })


def _mqtt_publish_command(imei, payload):
    """Open a short-lived MQTT client, publish a raw command, and disconnect.

    Deliberately does NOT import mqttClienttrack.py -- that module opens a
    blocking loop_forever() MQTT connection as a side effect of being
    imported, which would break the Django process.
    """
    try:
        broker_host = os.getenv('MQTT_BROKER_HOST', 'localhost')
        broker_port = int(os.getenv('MQTT_BROKER_PORT', '8883'))
        username = os.getenv('MQTT_USERNAME', '')
        password = os.getenv('MQTT_PASSWORD', '')
        ca_cert = '/app/keys/ca.crt'

        client = mqtt.Client()
        client.username_pw_set(username, password)
        client.tls_set(ca_certs=ca_cert, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
        client.connect(broker_host, broker_port, 60)
        # loop_start() is required -- without it nothing reads the socket, so
        # the broker's PUBACK is never processed and wait_for_publish() times
        # out even though the publish actually succeeded.
        client.loop_start()

        topic = f'deviceCommand/{imei}'
        result = client.publish(topic, payload, qos=1)
        result.wait_for_publish(timeout=5)
        published = result.is_published()

        client.loop_stop()
        client.disconnect()

        if published:
            return True, f'Published to {topic}'
        return False, f'Publish to {topic} did not confirm within timeout'
    except Exception as e:
        return False, f'MQTT publish error: {e}'


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([DeviceCommandRateThrottle])
def device_inspector_send_command(request):
    imei = (request.data.get('imei') or '').strip()
    payload = request.data.get('payload')
    transport = request.data.get('transport', 'auto')

    if not imei or not payload:
        return Response(
            {'status': 'error', 'message': 'imei and payload are required'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if transport not in VALID_TRANSPORTS:
        return Response(
            {'status': 'error', 'message': f"transport must be one of {sorted(VALID_TRANSPORTS)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    device_tags_qs, err = _scope_device_tags(request.user)
    if err:
        return err
    if not _find_device_tag(device_tags_qs, imei):
        return Response(
            {'status': 'error', 'message': f'No device found for IMEI {imei} in your scope'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if transport == 'auto':
        conn_state = connection_registry.get_connection_state(imei) or {}
        if not conn_state.get('live'):
            return Response(
                {'status': 'error', 'message': f'No live connection for IMEI {imei} on any transport'},
                status=status.HTTP_404_NOT_FOUND,
            )
        transport = conn_state['primary_transport']

    if transport == 'mqtt':
        ok, detail = _mqtt_publish_command(imei, payload)
        result = 'delivered' if ok else 'failed'
    else:
        result, detail = connection_registry.enqueue_tcp_command(imei, payload, transport)

    request_id = uuid.uuid4().hex
    connection_registry.push_command_history(imei, request_id, transport, payload, result, detail)

    http_status = RESULT_HTTP_STATUS.get(result, status.HTTP_200_OK)
    return Response({
        'status': 'success' if result in ('delivered', 'queued_no_ack') else 'error',
        'result': result,
        'detail': detail,
        'transport': transport,
        'request_id': request_id,
    }, status=http_status)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def device_inspector_command_history(request):
    imei = (request.GET.get('imei') or '').strip()
    if not imei:
        return Response({'status': 'error', 'message': 'imei is required'}, status=status.HTTP_400_BAD_REQUEST)
    return Response({
        'status': 'success',
        'imei': imei,
        'history': connection_registry.get_command_history(imei, limit=20),
    })


_DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Device Inspector</title>
<style>
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 20px; color: #1a1a1a; background: #f7f7f8; }
  h1 { font-size: 20px; margin-bottom: 4px; }
  .box { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 14px 16px; margin-bottom: 16px; }
  input, select, textarea { padding: 6px 8px; font-family: inherit; font-size: 13px; }
  textarea { width: 100%; box-sizing: border-box; min-height: 70px; }
  button.primary { background: #2563eb; color: #fff; border: none; padding: 7px 14px; border-radius: 6px; cursor: pointer; }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
  .badge.live { background: #dcfce7; color: #166534; }
  .badge.offline { background: #fee2e2; color: #991b1b; }
  .tabs button { padding: 6px 12px; margin-right: 6px; border: 1px solid #ccc; background: #fff; border-radius: 6px; cursor: pointer; }
  .tabs button.active { background: #2563eb; color: #fff; border-color: #2563eb; }
  table { border-collapse: collapse; width: 100%; background: #fff; margin-top: 10px; }
  th, td { border: 1px solid #e5e5e5; padding: 6px 10px; font-size: 12px; text-align: left; word-break: break-all; }
  th { background: #f0f0f2; }
  .pager { margin-top: 10px; display: flex; align-items: center; gap: 10px; }
  #status { font-size: 12px; color: #666; margin-top: 6px; }
  .row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
</style>
</head>
<body>
<h1>Device Inspector</h1>

<div class="box token-box">
  <label>Bearer token: <input id="token" type="text" style="width:360px" placeholder="paste auth token here"></label>
  <button class="primary" onclick="saveToken()">Save</button>
  <span id="tokenStatus" style="margin-left:8px;font-size:12px;color:#666;"></span>
</div>

<div class="box">
  <div class="row">
    <input id="imeiInput" type="text" placeholder="IMEI" style="width:220px">
    <button class="primary" onclick="lookup()">Search</button>
    <span id="connBadge"></span>
  </div>
  <div id="deviceInfo" style="margin-top:10px;font-size:13px;"></div>
</div>

<div class="box">
  <div class="tabs" id="logTabs">
    <button data-type="both" class="active">Both</button>
    <button data-type="tracking">Tracking</button>
    <button data-type="emergency">Emergency</button>
  </div>
  <table>
    <thead><tr><th>Type</th><th>Timestamp</th><th>Raw Data</th></tr></thead>
    <tbody id="logsBody"></tbody>
  </table>
  <div class="pager">
    <button onclick="prevLogPage()">Prev</button>
    <span id="logPageInfo"></span>
    <button onclick="nextLogPage()">Next</button>
  </div>
</div>

<div class="box">
  <div class="row">
    <label>Transport:
      <select id="transportSelect">
        <option value="auto">auto</option>
        <option value="tcp">tcp</option>
        <option value="tcpem">tcpem</option>
        <option value="mqtt">mqtt</option>
      </select>
    </label>
    <label>History:
      <select id="historySelect" onchange="fillFromHistory()">
        <option value="">-- reuse a previous command --</option>
      </select>
    </label>
  </div>
  <textarea id="payloadInput" placeholder="raw command payload"></textarea>
  <div class="row" style="margin-top:8px;">
    <button class="primary" onclick="sendCommand()">Send</button>
    <span id="sendStatus"></span>
  </div>
</div>

<script>
const API_BASE = '/api/device-inspector';
let currentImei = '';
let logState = { type: 'both', page: 1, totalPages: 0 };
let historyCache = [];

function getToken() { return localStorage.getItem('deviceInspectorToken') || ''; }
function saveToken() {
  localStorage.setItem('deviceInspectorToken', document.getElementById('token').value.trim());
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
  const seededFromLink = seedTokenFromQuery('deviceInspectorToken');
  const t = getToken();
  if (t) {
    document.getElementById('token').value = t;
    document.getElementById('tokenStatus').textContent = seededFromLink ? 'Loaded from shared link.' : 'Loaded from storage.';
  }
})();
function authHeaders(json) {
  const t = getToken();
  const h = t ? { 'Authorization': 'Token ' + t } : {};
  if (json) h['Content-Type'] = 'application/json';
  return h;
}

async function lookup() {
  currentImei = document.getElementById('imeiInput').value.trim();
  if (!currentImei) return;
  const res = await fetch(`${API_BASE}/lookup/?imei=${encodeURIComponent(currentImei)}`, { headers: authHeaders() });
  const data = await res.json();
  if (!res.ok) {
    document.getElementById('deviceInfo').textContent = 'Error: ' + (data.message || res.status);
    document.getElementById('connBadge').innerHTML = '';
    return;
  }
  const conn = data.connection || {};
  document.getElementById('connBadge').innerHTML = conn.live
    ? `<span class="badge live">LIVE via ${conn.primary_transport}</span>`
    : `<span class="badge offline">OFFLINE</span>`;
  document.getElementById('deviceInfo').innerHTML =
    `Vehicle: <b>${data.vehicle_reg_no || ''}</b> &nbsp; Status: ${data.device_status || ''} &nbsp; Owner: ${data.vehicle_owner || ''}`;
  logState = { type: logState.type, page: 1, totalPages: 0 };
  loadLogs();
  loadHistory();
}

document.getElementById('logTabs').addEventListener('click', (e) => {
  if (e.target.tagName !== 'BUTTON') return;
  document.querySelectorAll('#logTabs button').forEach(b => b.classList.remove('active'));
  e.target.classList.add('active');
  logState.type = e.target.dataset.type;
  logState.page = 1;
  loadLogs();
});

async function loadLogs() {
  if (!currentImei) return;
  const params = new URLSearchParams({ imei: currentImei, log_type: logState.type, page: logState.page, page_size: 20 });
  const res = await fetch(`${API_BASE}/logs/?${params}`, { headers: authHeaders() });
  const data = await res.json();
  if (!res.ok) return;
  logState.totalPages = data.total_pages || 0;
  const tbody = document.getElementById('logsBody');
  tbody.innerHTML = '';
  (data.logs || []).forEach(l => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${l.log_type}</td><td>${l.timestamp}</td><td>${l.raw_data}</td>`;
    tbody.appendChild(tr);
  });
  document.getElementById('logPageInfo').textContent = `Page ${data.page} of ${data.total_pages}`;
}
function prevLogPage() { if (logState.page > 1) { logState.page--; loadLogs(); } }
function nextLogPage() { if (logState.page < logState.totalPages) { logState.page++; loadLogs(); } }

async function loadHistory() {
  const res = await fetch(`${API_BASE}/command/history/?imei=${encodeURIComponent(currentImei)}`, { headers: authHeaders() });
  const data = await res.json();
  historyCache = (data.history || []);
  const sel = document.getElementById('historySelect');
  sel.innerHTML = '<option value="">-- reuse a previous command --</option>';
  historyCache.forEach((h, idx) => {
    const opt = document.createElement('option');
    opt.value = idx;
    opt.textContent = `[${h.status}] ${h.transport}: ${h.payload}`.slice(0, 80);
    sel.appendChild(opt);
  });
}
function fillFromHistory() {
  const idx = document.getElementById('historySelect').value;
  if (idx === '') return;
  const entry = historyCache[idx];
  if (!entry) return;
  document.getElementById('payloadInput').value = entry.payload;
  document.getElementById('transportSelect').value = entry.transport;
}

async function sendCommand() {
  if (!currentImei) { document.getElementById('sendStatus').textContent = 'Search for a device first.'; return; }
  const payload = document.getElementById('payloadInput').value;
  const transport = document.getElementById('transportSelect').value;
  document.getElementById('sendStatus').textContent = 'Sending...';
  try {
    const res = await fetch(`${API_BASE}/command/send/`, {
      method: 'POST',
      headers: authHeaders(true),
      body: JSON.stringify({ imei: currentImei, payload, transport }),
    });
    const data = await res.json();
    document.getElementById('sendStatus').textContent = `${data.result}: ${data.detail}`;
    loadHistory();
  } catch (e) {
    document.getElementById('sendStatus').textContent = 'Request failed: ' + e;
  }
}
</script>
</body>
</html>
"""


def device_inspector_dashboard(request):
    return HttpResponse(_DASHBOARD_HTML)
