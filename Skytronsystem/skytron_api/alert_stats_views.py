"""
Alert-statistics dashboard: per-device alert counts/breakdowns over a
selectable date range, plus a self-contained HTML dashboard for ops use.
"""
import json
from datetime import datetime, timedelta

from django.db.models import Count, Max
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import AlertsLog, DeviceTag
from .throttles import AlertStatsRateThrottle
from .views import get_user_object

# TYPE_CHOICES stores (value, label) pairs. The label for harsh acceleration
# is misspelled ("HarshAccileration") in this model, but the value actually
# written to the database is spelled correctly ("HarshAcceleration") -- so
# filtering/defaults below use stored values, never labels.
DEFAULT_ALERT_TYPES = [
    'HarshAcceleration',
    'HarshBreak',
    'HarshTurn',
    'OverSpeed',
    'Route_overspeed',
]

VALID_RANGES = {'today', 'this_week', 'this_month', 'this_year', 'since_beginning', 'custom'}
SORT_FIELD_MAP = {
    'alert_count': 'alert_count',
    'vehicle_reg_no': 'deviceTag__vehicle_reg_no',
    'last_alert_at': 'last_alert_at',
}


def _scope_device_tags(user):
    """Role-scope a DeviceTag queryset the same way get_device_health_status does.

    Returns (queryset, error_response). error_response is None on success.
    """
    device_tags_query = DeviceTag.objects.all()

    if user.role == 'devicemanufacture':
        manufacturer = get_user_object(user, 'devicemanufacture')
        if not manufacturer:
            return None, Response(
                {'status': 'error', 'message': 'Manufacturer profile not found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        device_tags_query = device_tags_query.filter(
            device__model__created_by__in=manufacturer.users.all()
        )
    elif user.role == 'sosadmin':
        pass
    elif user.role == 'owner':
        owner = get_user_object(user, 'owner')
        if not owner:
            return None, Response(
                {'status': 'error', 'message': 'Owner profile not found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        device_tags_query = device_tags_query.filter(vehicle_owner=owner)
    elif user.role == 'dealer':
        dealer = get_user_object(user, 'dealer')
        if dealer:
            device_tags_query = device_tags_query.filter(device__dealer=dealer)
    # superadmin, stateadmin, dtorto see everything -- no additional filter

    return device_tags_query, None


def _resolve_date_range(range_param, date_from, date_to):
    """Returns (start, end) tz-aware datetimes, or raises ValueError."""
    now = timezone.now()

    if range_param not in VALID_RANGES:
        raise ValueError(
            f"Invalid range '{range_param}'. Must be one of: {', '.join(sorted(VALID_RANGES))}"
        )

    if range_param == 'custom':
        if not date_from or not date_to:
            raise ValueError("date_from and date_to are required when range=custom")
        try:
            start = timezone.make_aware(datetime.strptime(date_from, '%Y-%m-%d'))
            end = timezone.make_aware(
                datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1) - timedelta(microseconds=1)
            )
        except ValueError:
            raise ValueError("date_from/date_to must be in YYYY-MM-DD format")
        return start, end

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if range_param == 'today':
        start = today_start
    elif range_param == 'this_week':
        start = today_start - timedelta(days=today_start.weekday())
    elif range_param == 'this_month':
        start = today_start.replace(day=1)
    elif range_param == 'this_year':
        start = today_start.replace(month=1, day=1)
    else:  # since_beginning
        start = None

    return start, now


@api_view(['GET'])
@permission_classes([AllowAny])
def alert_stats_type_options(request):
    """List every AlertsLog alert type, flagged with whether it's part of the
    default multi-select selection, to drive a dropdown on the frontend."""
    options = [
        {
            'value': value,
            'label': label,
            'default_selected': value in DEFAULT_ALERT_TYPES,
        }
        for value, label in AlertsLog.TYPE_CHOICES
    ]
    return Response({
        'status': 'success',
        'default_types': DEFAULT_ALERT_TYPES,
        'options': options,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([AlertStatsRateThrottle])
def alert_stats_summary(request):
    """Per-device alert counts/breakdown over a date range, role-scoped and paginated."""
    user = request.user
    p = request.GET

    types_param = p.get('types', '')
    types = [t.strip() for t in types_param.split(',') if t.strip()] if types_param else list(DEFAULT_ALERT_TYPES)

    range_param = p.get('range', 'this_month')
    try:
        start, end = _resolve_date_range(range_param, p.get('date_from'), p.get('date_to'))
    except ValueError as e:
        return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    device_tags_qs, err = _scope_device_tags(user)
    if err:
        return err

    device_tag_id = p.get('device_tag_id')
    vehicle_reg_no = p.get('vehicle_reg_no')
    imei = p.get('imei')

    if device_tag_id:
        device_tags_qs = device_tags_qs.filter(id=device_tag_id)
    if vehicle_reg_no:
        device_tags_qs = device_tags_qs.filter(vehicle_reg_no__icontains=vehicle_reg_no)
    if imei:
        device_tags_qs = device_tags_qs.filter(device__imei__icontains=imei)

    alerts_qs = AlertsLog.objects.filter(deviceTag__in=device_tags_qs, type__in=types)
    if start:
        alerts_qs = alerts_qs.filter(timestamp__gte=start)
    alerts_qs = alerts_qs.filter(timestamp__lte=end)

    summary_qs = (
        alerts_qs
        .values('deviceTag_id', 'deviceTag__vehicle_reg_no', 'deviceTag__device__imei')
        .annotate(alert_count=Count('id'), last_alert_at=Max('timestamp'))
    )

    sort_by = p.get('sort_by', 'alert_count')
    sort_dir = p.get('sort_dir', 'desc')
    order_field = SORT_FIELD_MAP.get(sort_by, 'alert_count')
    if sort_dir == 'desc':
        order_field = f'-{order_field}'
    summary_qs = summary_qs.order_by(order_field)

    try:
        page = max(1, int(p.get('page', 1)))
        page_size = max(1, int(p.get('page_size', 20)))
    except (TypeError, ValueError):
        page, page_size = 1, 20

    total_count = summary_qs.count()
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_rows = list(summary_qs[start_idx:end_idx])

    device_tag_ids = [row['deviceTag_id'] for row in page_rows]
    breakdown_map = {}
    if device_tag_ids:
        breakdown_qs = (
            alerts_qs
            .filter(deviceTag_id__in=device_tag_ids)
            .values('deviceTag_id', 'type')
            .annotate(count=Count('id'))
        )
        for row in breakdown_qs:
            breakdown_map.setdefault(row['deviceTag_id'], {})[row['type']] = row['count']

    devices = [
        {
            'device_tag_id': row['deviceTag_id'],
            'vehicle_reg_no': row['deviceTag__vehicle_reg_no'],
            'imei': row['deviceTag__device__imei'],
            'alert_count': row['alert_count'],
            'last_alert_at': row['last_alert_at'],
            'breakdown': {t: breakdown_map.get(row['deviceTag_id'], {}).get(t, 0) for t in types},
        }
        for row in page_rows
    ]

    total_pages = (total_count + page_size - 1) // page_size if page_size else 0

    return Response({
        'status': 'success',
        'range': range_param,
        'date_from': start,
        'date_to': end,
        'types': types,
        'total_devices': total_count,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
        'devices': devices,
    })


_DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Alert Stats Dashboard</title>
<style>
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 20px; color: #1a1a1a; background: #f7f7f8; }
  h1 { font-size: 20px; margin-bottom: 4px; }
  .box { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 14px 16px; margin-bottom: 16px; }
  .token-box input { width: 360px; padding: 6px 8px; }
  .types-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 4px 12px; max-height: 160px; overflow-y: auto; }
  .types-grid label { font-size: 13px; }
  .links a { cursor: pointer; color: #2563eb; font-size: 13px; margin-right: 12px; }
  .range-group button { padding: 6px 12px; margin-right: 6px; border: 1px solid #ccc; background: #fff; border-radius: 6px; cursor: pointer; }
  .range-group button.active { background: #2563eb; color: #fff; border-color: #2563eb; }
  .custom-dates { margin-top: 8px; display: none; }
  .custom-dates.show { display: block; }
  table { border-collapse: collapse; width: 100%; background: #fff; }
  th, td { border: 1px solid #e5e5e5; padding: 6px 10px; font-size: 13px; text-align: left; }
  th { cursor: pointer; background: #f0f0f2; user-select: none; }
  th.sorted::after { content: " " attr(data-dir); }
  .pager { margin-top: 10px; display: flex; align-items: center; gap: 10px; }
  .pager button { padding: 4px 10px; }
  #status { font-size: 12px; color: #666; margin-top: 6px; }
  button.primary { background: #2563eb; color: #fff; border: none; padding: 7px 14px; border-radius: 6px; cursor: pointer; }
</style>
</head>
<body>
<h1>Alert Statistics</h1>

<div class="box token-box">
  <label>Bearer token: <input id="token" type="text" placeholder="paste auth token here"></label>
  <button class="primary" onclick="saveToken()">Save</button>
  <span id="tokenStatus" style="margin-left:8px;font-size:12px;color:#666;"></span>
</div>

<div class="box">
  <div class="links">
    <a onclick="selectAllTypes()">Select all</a>
    <a onclick="resetDefaultTypes()">Reset to defaults</a>
  </div>
  <div id="typesGrid" class="types-grid">Loading alert types...</div>
</div>

<div class="box">
  <div class="range-group" id="rangeGroup">
    <button data-range="today">Today</button>
    <button data-range="this_week">This Week</button>
    <button data-range="this_month" class="active">This Month</button>
    <button data-range="this_year">This Year</button>
    <button data-range="since_beginning">Since Beginning</button>
    <button data-range="custom">Custom</button>
  </div>
  <div class="custom-dates" id="customDates">
    From <input type="date" id="dateFrom"> To <input type="date" id="dateTo">
  </div>
</div>

<div class="box">
  <button class="primary" onclick="loadPage(1)">Apply</button>
  <span id="status"></span>
</div>

<div class="box">
  <table id="resultsTable">
    <thead>
      <tr>
        <th data-sort="vehicle_reg_no">Vehicle Reg No</th>
        <th>IMEI</th>
        <th data-sort="alert_count">Alert Count</th>
        <th data-sort="last_alert_at">Last Alert</th>
        <th>Breakdown</th>
      </tr>
    </thead>
    <tbody id="resultsBody"></tbody>
  </table>
  <div class="pager">
    <button onclick="prevPage()">Prev</button>
    <span id="pageInfo"></span>
    <button onclick="nextPage()">Next</button>
  </div>
</div>

<script>
const API_BASE = '/api/alert-stats';
let state = {
  types: [],
  defaults: [],
  range: 'this_month',
  page: 1,
  pageSize: 20,
  totalPages: 0,
  sortBy: 'alert_count',
  sortDir: 'desc',
};

function getToken() { return localStorage.getItem('alertStatsToken') || ''; }
function saveToken() {
  localStorage.setItem('alertStatsToken', document.getElementById('token').value.trim());
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
  const seededFromLink = seedTokenFromQuery('alertStatsToken');
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

function selectAllTypes() {
  document.querySelectorAll('#typesGrid input[type=checkbox]').forEach(cb => cb.checked = true);
}
function resetDefaultTypes() {
  document.querySelectorAll('#typesGrid input[type=checkbox]').forEach(cb => {
    cb.checked = state.defaults.includes(cb.value);
  });
}
function selectedTypes() {
  return Array.from(document.querySelectorAll('#typesGrid input[type=checkbox]:checked')).map(cb => cb.value);
}

async function loadTypeOptions() {
  const res = await fetch(`${API_BASE}/types/`);
  const data = await res.json();
  state.defaults = data.default_types || [];
  const grid = document.getElementById('typesGrid');
  grid.innerHTML = '';
  (data.options || []).forEach(opt => {
    const id = 'type_' + opt.value;
    const label = document.createElement('label');
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.value = opt.value;
    cb.id = id;
    cb.checked = !!opt.default_selected;
    label.appendChild(cb);
    label.appendChild(document.createTextNode(' ' + opt.label));
    grid.appendChild(label);
  });
}

document.getElementById('rangeGroup').addEventListener('click', (e) => {
  if (e.target.tagName !== 'BUTTON') return;
  document.querySelectorAll('#rangeGroup button').forEach(b => b.classList.remove('active'));
  e.target.classList.add('active');
  state.range = e.target.dataset.range;
  document.getElementById('customDates').classList.toggle('show', state.range === 'custom');
});

document.querySelectorAll('#resultsTable th[data-sort]').forEach(th => {
  th.addEventListener('click', () => {
    const field = th.dataset.sort;
    if (state.sortBy === field) {
      state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
    } else {
      state.sortBy = field;
      state.sortDir = 'desc';
    }
    document.querySelectorAll('#resultsTable th').forEach(h => { h.classList.remove('sorted'); h.removeAttribute('data-dir'); });
    th.classList.add('sorted');
    th.setAttribute('data-dir', state.sortDir === 'asc' ? '↑' : '↓');
    loadPage(1);
  });
});

function buildQuery() {
  const params = new URLSearchParams();
  params.set('types', selectedTypes().join(','));
  params.set('range', state.range);
  if (state.range === 'custom') {
    params.set('date_from', document.getElementById('dateFrom').value);
    params.set('date_to', document.getElementById('dateTo').value);
  }
  params.set('sort_by', state.sortBy);
  params.set('sort_dir', state.sortDir);
  params.set('page', state.page);
  params.set('page_size', state.pageSize);
  return params.toString();
}

async function loadPage(page) {
  state.page = page;
  const statusEl = document.getElementById('status');
  statusEl.textContent = 'Loading...';
  try {
    const res = await fetch(`${API_BASE}/summary/?${buildQuery()}`, { headers: authHeaders() });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      statusEl.textContent = 'Error: ' + (err.message || res.status);
      return;
    }
    const data = await res.json();
    state.totalPages = data.total_pages || 0;
    renderRows(data.devices || [], data.types || []);
    document.getElementById('pageInfo').textContent = `Page ${data.page} of ${data.total_pages} (${data.total_devices} devices)`;
    statusEl.textContent = '';
  } catch (e) {
    statusEl.textContent = 'Request failed: ' + e;
  }
}

function renderRows(devices, types) {
  const tbody = document.getElementById('resultsBody');
  tbody.innerHTML = '';
  devices.forEach(d => {
    const tr = document.createElement('tr');
    const breakdown = types.map(t => `${t}: ${d.breakdown[t] || 0}`).join(', ');
    tr.innerHTML = `<td>${d.vehicle_reg_no || ''}</td><td>${d.imei || ''}</td><td>${d.alert_count}</td><td>${d.last_alert_at || ''}</td><td>${breakdown}</td>`;
    tbody.appendChild(tr);
  });
}

function prevPage() { if (state.page > 1) loadPage(state.page - 1); }
function nextPage() { if (state.page < state.totalPages) loadPage(state.page + 1); }

loadTypeOptions();
</script>
</body>
</html>
"""


def alert_stats_dashboard(request):
    return HttpResponse(_DASHBOARD_HTML)
