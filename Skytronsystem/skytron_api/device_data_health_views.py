"""
Device data health: for a given IMEI, show the last available raw packet
per category (login, health, tracking, emergency, and the raw "packet"
catch-all), validated against a selectable device protocol format.

Green  = a packet for that category was found and fully validates.
Yellow = no packet for that category was found in the lookback window.
Red    = a packet was found but failed validation (wrong field count/type,
         bad checksum, etc).
Gray   = the selected protocol format isn't implemented yet (Amendment3).
"""
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponse

from . import protocol_formats as pf
from .alert_stats_views import _scope_device_tags
from .device_inspector_views import _find_device_tag
from .models import GPSDataLog, GPSemDataLog
from .throttles import DeviceDataHealthRateThrottle

DEFAULT_LOOKBACK_DAYS = 3
MAX_LOOKBACK_DAYS = 30
MAX_ROWS_SCANNED = 300  # per source table, bounds raw_data__contains cost


def _split_packets(raw_data):
    """Mirror data_processor.process_device_tracking_data's own splitting:
    one row's raw_data can contain multiple $-delimited packets."""
    fragments = []
    for part in raw_data.split('$'):
        if not part:
            continue
        frag = '$' + part
        if len(frag) > 4:
            fragments.append(frag)
    return fragments


def _scan_for_category(rows, category, imei, protocol_format):
    """rows: iterable of (timestamp, raw_data), newest first. Returns the
    most recent matching ValidationResult + timestamp + raw fragment, or None."""
    for ts, raw_data in rows:
        for frag in _split_packets(raw_data):
            result = pf.classify_and_validate(frag, category, imei=imei, protocol_format=protocol_format)
            if result is not None and result.matched:
                return ts, frag, result
    return None


def _category_entry(category, found, format_implemented):
    if not format_implemented:
        return {
            'category': category,
            'status': 'format_not_implemented',
            'color': 'gray',
            'received_at': None,
            'raw': None,
            'fields': None,
            'errors': [],
            'checksum_ok': None,
        }
    if not found:
        return {
            'category': category,
            'status': 'not_available',
            'color': 'yellow',
            'received_at': None,
            'raw': None,
            'fields': None,
            'errors': [],
            'checksum_ok': None,
        }
    ts, raw, result = found
    return {
        'category': category,
        'status': 'available' if result.valid else 'invalid',
        'color': 'green' if result.valid else 'red',
        'received_at': ts,
        'raw': raw,
        'fields': result.fields,
        'errors': result.errors,
        'checksum_ok': result.checksum_ok,
    }


@api_view(['GET'])
@permission_classes([AllowAny])
def device_data_health_format_options(request):
    options = [
        {'value': fmt_id, 'label': meta['label'], 'implemented': meta['implemented']}
        for fmt_id, meta in pf.PROTOCOL_FORMATS.items()
    ]
    return Response({
        'status': 'success',
        'current_server_format': pf.ARAI_FORMAT_ID,
        'options': options,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([DeviceDataHealthRateThrottle])
def device_data_health_lookup(request):
    imei = (request.GET.get('imei') or '').strip()
    if not imei:
        return Response({'status': 'error', 'message': 'imei is required'}, status=status.HTTP_400_BAD_REQUEST)

    protocol_format = request.GET.get('protocol_format', pf.ARAI_FORMAT_ID)
    if protocol_format not in pf.PROTOCOL_FORMATS:
        return Response(
            {'status': 'error', 'message': f"Unknown protocol_format {protocol_format!r}"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    format_implemented = pf.PROTOCOL_FORMATS[protocol_format]['implemented']

    try:
        lookback_days = int(request.GET.get('lookback_days', DEFAULT_LOOKBACK_DAYS))
    except (TypeError, ValueError):
        lookback_days = DEFAULT_LOOKBACK_DAYS
    lookback_days = max(1, min(lookback_days, MAX_LOOKBACK_DAYS))

    device_tags_qs, err = _scope_device_tags(request.user, allow_state_district=True)
    if err:
        return err
    device_tag = _find_device_tag(device_tags_qs, imei)
    if not device_tag:
        return Response(
            {'status': 'error', 'message': f'No device found for IMEI {imei} in your scope'},
            status=status.HTTP_404_NOT_FOUND,
        )
    # H-3: only superadmin may search logs by part of an IMEI. Everyone else
    # gets logs only for the full IMEI of the device found in their own scope.
    if getattr(request.user, 'role', None) != 'superadmin' and device_tag.device:
        imei = device_tag.device.imei

    cutoff = timezone.now() - timedelta(days=lookback_days)

    gps_rows = list(
        GPSDataLog.objects
        .filter(raw_data__contains=imei, timestamp__gte=cutoff)
        .order_by('-timestamp')
        .values_list('timestamp', 'raw_data')[:MAX_ROWS_SCANNED]
    )
    em_rows = list(
        GPSemDataLog.objects
        .filter(raw_data__contains=imei, timestamp__gte=cutoff)
        .order_by('-timestamp')
        .values_list('timestamp', 'raw_data')[:MAX_ROWS_SCANNED]
    )

    packet_entry = {
        'category': 'packet',
        'status': 'available' if gps_rows else 'not_available',
        'color': 'green' if gps_rows else 'yellow',
        'received_at': gps_rows[0][0] if gps_rows else None,
        'raw': gps_rows[0][1] if gps_rows else None,
        'fields': None,
        'errors': [],
        'checksum_ok': None,
    }

    categories = {}
    alert_reference = []
    if format_implemented:
        for category in ('login', 'health', 'tracking'):
            found = _scan_for_category(gps_rows, category, imei, protocol_format)
            categories[category] = _category_entry(category, found, format_implemented)
        found = _scan_for_category(em_rows, 'emergency', imei, protocol_format)
        categories['emergency'] = _category_entry('emergency', found, format_implemented)

        seen_combos = pf.scan_tracking_alert_combinations(gps_rows, _split_packets, imei, protocol_format)
        for entry in pf.ALERT_TYPE_REFERENCE:
            if entry['applies_to'] not in ('both', protocol_format):
                continue
            key = (entry['packet_type'], entry['alert_id'])
            last_seen = seen_combos.get(key)
            alert_reference.append({
                'packet_type': entry['packet_type'],
                'alert_id': entry['alert_id'],
                'trigger': entry['trigger'],
                'available': last_seen is not None,
                'last_seen': last_seen,
            })
    else:
        for category in ('login', 'health', 'tracking', 'emergency'):
            categories[category] = _category_entry(category, None, format_implemented)

    return Response({
        'status': 'success',
        'imei': imei,
        'protocol_format': protocol_format,
        'format_implemented': format_implemented,
        'current_server_format': pf.ARAI_FORMAT_ID,
        'lookback_days': lookback_days,
        'checked_at': timezone.now(),
        'categories': {
            'login': categories['login'],
            'health': categories['health'],
            'tracking': categories['tracking'],
            'emergency': categories['emergency'],
            'packet': packet_entry,
        },
        'alert_reference': alert_reference,
    })


_DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Device Data Health</title>
<style>
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 20px; color: #1a1a1a; background: #f7f7f8; }
  h1 { font-size: 20px; margin-bottom: 4px; }
  h2 { font-size: 15px; margin: 0 0 8px; }
  .box { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 14px 16px; margin-bottom: 16px; }
  input, select { padding: 6px 8px; font-size: 13px; }
  button.primary { background: #2563eb; color: #fff; border: none; padding: 7px 14px; border-radius: 6px; cursor: pointer; }
  .row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; margin-top: 10px; }
  .card { border-radius: 8px; padding: 12px; color: #fff; cursor: pointer; }
  .card.green { background: #16a34a; }
  .card.yellow { background: #ca8a04; }
  .card.red { background: #dc2626; }
  .card.gray { background: #6b7280; }
  .card.selected { outline: 3px solid #1e293b; outline-offset: 2px; }
  .card h3 { margin: 0 0 6px; font-size: 14px; text-transform: uppercase; }
  .card .ts { font-size: 12px; opacity: 0.9; }
  .card .status { font-size: 13px; font-weight: 600; margin-top: 4px; }
  .card .note { font-size: 11px; opacity: 0.85; margin-top: 4px; }
  .rawbox { margin-top: 14px; background: #0d0d0d; color: #d1d5db; padding: 10px 12px; border-radius: 6px; font: 12px/1.5 'SF Mono', ui-monospace, monospace; white-space: pre-wrap; word-break: break-all; display: none; }
  .rawbox.show { display: block; }
  table { border-collapse: collapse; width: 100%; margin-top: 10px; }
  th, td { border: 1px solid #e5e5e5; padding: 6px 10px; font-size: 12px; text-align: left; }
  th { background: #f0f0f2; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; color: #fff; }
  .badge.green { background: #16a34a; }
  .badge.red { background: #dc2626; }
  .badge.yellow { background: #ca8a04; color: #1a1a1a; }
  #status { font-size: 12px; color: #666; margin-top: 6px; }
  #fieldTableWrap { display: none; margin-top: 16px; }
  #fieldTableWrap.show { display: block; }
  #refTableWrap { display: none; margin-top: 16px; }
  #refTableWrap.show { display: block; }
</style>
</head>
<body>
<h1>Device Data Health</h1>

<div class="box token-box">
  <label>Bearer token: <input id="token" type="text" style="width:360px" placeholder="paste auth token here"></label>
  <button class="primary" onclick="saveToken()">Save</button>
  <span id="tokenStatus" style="margin-left:8px;font-size:12px;color:#666;"></span>
</div>

<div class="box">
  <div class="row">
    <input id="imeiInput" type="text" placeholder="IMEI" style="width:220px">
    <label>Protocol format: <select id="formatSelect"></select></label>
    <label>Lookback days: <input id="lookbackInput" type="number" value="3" min="1" max="30" style="width:70px"></label>
    <button class="primary" onclick="lookup()">Check</button>
  </div>
  <div id="status"></div>
</div>

<div class="box">
  <h2>Packet categories</h2>
  <div id="cards" class="cards"></div>

  <div id="fieldTableWrap">
    <h2 id="fieldTableTitle" style="margin-top:14px;"></h2>
    <table>
      <thead><tr><th>Field</th><th>Value</th><th>Status</th><th>Note</th></tr></thead>
      <tbody id="fieldTableBody"></tbody>
    </table>
    <pre id="rawbox" class="rawbox"></pre>
  </div>
</div>

<div id="refTableWrap" class="box">
  <h2>Alert type / packet type reference</h2>
  <table>
    <thead><tr><th>Packet Type</th><th>Alert ID</th><th>Trigger</th><th>Available for this device</th><th>Last seen</th></tr></thead>
    <tbody id="refTableBody"></tbody>
  </table>
</div>

<script>
const API_BASE = '/api/device-data-health';

function getToken() { return localStorage.getItem('deviceDataHealthToken') || ''; }
function saveToken() {
  localStorage.setItem('deviceDataHealthToken', document.getElementById('token').value.trim());
  document.getElementById('tokenStatus').textContent = 'Saved.';
}
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
  const seededFromLink = seedTokenFromQuery('deviceDataHealthToken');
  const t = getToken();
  if (t) {
    document.getElementById('token').value = t;
    document.getElementById('tokenStatus').textContent = seededFromLink ? 'Loaded from shared link.' : 'Loaded from storage.';
  }
})();
function authHeaders() {
  const t = getToken();
  return t ? { 'Authorization': 'Token ' + t } : {};
}

async function loadFormats() {
  const res = await fetch(`${API_BASE}/formats/`);
  const data = await res.json();
  const sel = document.getElementById('formatSelect');
  sel.innerHTML = '';
  (data.options || []).forEach(opt => {
    const o = document.createElement('option');
    o.value = opt.value;
    o.textContent = opt.label + (opt.implemented ? '' : ' (not yet implemented)');
    sel.appendChild(o);
  });
}

const CATEGORY_LABELS = { login: 'Login', health: 'Health', tracking: 'Tracking', emergency: 'Emergency', packet: 'Packet' };

async function lookup() {
  const imei = document.getElementById('imeiInput').value.trim();
  if (!imei) return;
  const protocol_format = document.getElementById('formatSelect').value;
  const lookback_days = document.getElementById('lookbackInput').value;
  const statusEl = document.getElementById('status');
  statusEl.textContent = 'Checking...';
  document.getElementById('fieldTableWrap').classList.remove('show');
  document.getElementById('refTableWrap').classList.remove('show');
  try {
    const params = new URLSearchParams({ imei, protocol_format, lookback_days });
    const res = await fetch(`${API_BASE}/lookup/?${params}`, { headers: authHeaders() });
    const data = await res.json();
    if (!res.ok) {
      statusEl.textContent = 'Error: ' + (data.message || res.status);
      document.getElementById('cards').innerHTML = '';
      return;
    }
    statusEl.textContent = `Checked at ${data.checked_at} — server currently speaks ${data.current_server_format}`;
    renderCards(data.categories);
    renderAlertReference(data.alert_reference || []);
  } catch (e) {
    statusEl.textContent = 'Request failed: ' + e;
  }
}

function renderCards(categories) {
  const container = document.getElementById('cards');
  container.innerHTML = '';
  ['login', 'health', 'tracking', 'emergency', 'packet'].forEach(cat => {
    const entry = categories[cat];
    const card = document.createElement('div');
    card.className = 'card ' + entry.color;
    const ts = entry.received_at ? new Date(entry.received_at).toLocaleString() : '—';
    let note = '';
    if (cat === 'packet') note = '<div class="note">raw availability, format-independent</div>';
    card.innerHTML = `<h3>${CATEGORY_LABELS[cat]}</h3><div class="ts">${ts}</div><div class="status">${entry.status.replace(/_/g, ' ')}</div>${note}`;
    card.addEventListener('click', () => {
      document.querySelectorAll('.card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      showDetail(cat, entry);
    });
    container.appendChild(card);
  });
}

function showDetail(cat, entry) {
  const wrap = document.getElementById('fieldTableWrap');
  const title = document.getElementById('fieldTableTitle');
  const tbody = document.getElementById('fieldTableBody');
  const rawbox = document.getElementById('rawbox');
  title.textContent = CATEGORY_LABELS[cat] + ' — field breakdown';
  tbody.innerHTML = '';

  if (!entry.fields) {
    tbody.innerHTML = `<tr><td colspan="4">No field-level breakdown for this category (${entry.status.replace(/_/g,' ')}).</td></tr>`;
  } else {
    Object.entries(entry.fields).forEach(([name, f]) => {
      const tr = document.createElement('tr');
      const val = f.value === null || f.value === undefined ? '' : f.value;
      tr.innerHTML = `<td>${name}</td><td>${val}</td><td><span class="badge ${f.status}">${f.status}</span></td><td>${f.error || ''}</td>`;
      tbody.appendChild(tr);
    });
  }

  if (entry.raw) {
    rawbox.textContent = entry.raw;
    rawbox.classList.add('show');
  } else {
    rawbox.classList.remove('show');
  }
  wrap.classList.add('show');
}

function renderAlertReference(rows) {
  const wrap = document.getElementById('refTableWrap');
  const tbody = document.getElementById('refTableBody');
  tbody.innerHTML = '';
  if (!rows.length) {
    wrap.classList.remove('show');
    return;
  }
  rows.forEach(r => {
    const tr = document.createElement('tr');
    const badge = r.available ? '<span class="badge green">available</span>' : '<span class="badge yellow">not available</span>';
    const ts = r.last_seen ? new Date(r.last_seen).toLocaleString() : '—';
    tr.innerHTML = `<td>${r.packet_type}</td><td>${r.alert_id}</td><td>${r.trigger}</td><td>${badge}</td><td>${ts}</td>`;
    tbody.appendChild(tr);
  });
  wrap.classList.add('show');
}

loadFormats();
</script>
</body>
</html>
"""


def device_data_health_dashboard(request):
    return HttpResponse(_DASHBOARD_HTML)
