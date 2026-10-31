"""
A-GPS / coarse location from cell towers, using the cell databank file
data/agps_cell_databank.json (built by scripts/build_agps_databank.py from
the BLE SOS app logs).

The file is re-read whenever its modification time changes, so replacing it
updates the lookups without a restart. AGPS_DATABANK_PATH (env) points the
backend at a different copy, e.g. one on host storage.

Cell IDs: phones report the full 28-bit LTE ECI; Skytron devices report the
LAC/TAC and only the low 16 bits of the cell ID, in hex, in PVT packets.
A query cell ID that fits in 16 bits is tried as a full ID first, then as the
low 16 bits of a known cell in the same network and TAC.
"""
import json
import math
import os
import threading

DEFAULT_DATABANK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'agps_cell_databank.json')

# Signal assumed for a cell given without one (weights only, not distances).
DEFAULT_DBM = -100
# Smallest accuracy radius returned; it also grows to cover every matched cell.
MIN_ACCURACY_M = 300

# PVT field offsets relative to the 'PVT' token (same layout the onboarding checks use).
PVT_OFFSET_NETWORK_OPERATOR = 21
PVT_OFFSET_GSM_SIGNAL = 28      # CSQ 0-31
PVT_OFFSET_MCC = 29             # then MNC, LAC, cell ID
PVT_OFFSET_NEIGHBOURS = 33      # 4 x (cell ID, LAC, signal)
PVT_NEIGHBOUR_COUNT = 4

_lock = threading.Lock()
_cache = {'path': None, 'mtime': None, 'db': None}


class DatabankUnavailable(Exception):
    pass


def databank_path():
    return (os.environ.get('AGPS_DATABANK_PATH') or '').strip() or DEFAULT_DATABANK_PATH


def _index(raw):
    networks = raw.get('networks') or {}
    aliases = {}
    for key, net in networks.items():
        for name in [key, net.get('name', '')] + list(net.get('aliases', [])):
            if name:
                aliases[_norm(name)] = key
    by_full, by_cid16, by_cid, by_tac = {}, {}, {}, {}
    for c in raw.get('cells', []):
        plmn = (str(c['mcc']), str(c['mnc']))
        by_full[plmn + (c['tac'], c['cid'])] = c
        by_cid16.setdefault(plmn + (c['tac'], c['cid'] & 0xFFFF), []).append(c)
        by_cid.setdefault(plmn + (c['cid'],), []).append(c)
        by_cid.setdefault(plmn + ('16', c['cid'] & 0xFFFF), []).append(c)
        by_tac.setdefault(plmn + (c['tac'],), []).append(c)
    return {
        'raw': raw, 'networks': networks, 'aliases': aliases,
        'by_full': by_full, 'by_cid16': by_cid16, 'by_cid': by_cid, 'by_tac': by_tac,
    }


def get_databank():
    """The indexed databank, reloaded if the file changed. Raises DatabankUnavailable."""
    path = databank_path()
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        raise DatabankUnavailable(f'A-GPS databank file not found: {path}')
    with _lock:
        if _cache['db'] is None or _cache['path'] != path or _cache['mtime'] != mtime:
            try:
                with open(path) as f:
                    raw = json.load(f)
            except (OSError, ValueError) as e:
                raise DatabankUnavailable(f'A-GPS databank file unreadable: {e}')
            _cache.update(path=path, mtime=mtime, db=_index(raw))
        return _cache['db']


def databank_info(db):
    raw = db['raw']
    return {
        'version': raw.get('version'),
        'generated_at': raw.get('generated_at'),
        'cells': len(raw.get('cells', [])),
        'networks': {k: n.get('name') for k, n in db['networks'].items()},
    }


def _norm(name):
    return ' '.join(str(name).strip().lower().replace('_', ' ').replace('-', ' ').split())


def resolve_network(db, name):
    """Network key ('airtel', 'jio', ...) for a name/operator label, or None."""
    if not name:
        return None
    n = _norm(name)
    if n in db['aliases']:
        return db['aliases'][n]
    # Operator strings such as 'IND airtel' or 'Jio 4G LTE': match on a known word.
    for alias, key in db['aliases'].items():
        if len(alias) >= 3 and (alias in n.split() or n.startswith(alias + ' ')):
            return key
    return None


def network_plmns(db, key):
    return [tuple(p.split('-')) for p in db['networks'].get(key, {}).get('plmns', [])]


def parse_number(value, hex_format=False):
    """int from an int / decimal string / hex string ('0x' prefix always means hex). None if blank."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    s = str(value).strip()
    if not s:
        return None
    if s.lower().startswith('0x'):
        return int(s, 16)
    return int(s, 16) if hex_format else int(s)


def haversine_m(lat1, lon1, lat2, lon2):
    p = math.radians
    a = (math.sin(p(lat2 - lat1) / 2) ** 2
         + math.cos(p(lat1)) * math.cos(p(lat2)) * math.sin(p(lon2 - lon1) / 2) ** 2)
    return 2 * 6371000 * math.asin(math.sqrt(a))


def _weight(dbm):
    return 10 ** ((max(dbm if dbm is not None else DEFAULT_DBM, -130) + 130) / 20)


def _public_cell(c):
    keys = ('network', 'radio', 'mcc', 'mnc', 'tac', 'tac_hex', 'cid', 'cid_hex', 'cid16_hex', 'enb_id', 'local_cell',
            'pci', 'earfcn', 'band', 'lat', 'lon', 'accuracy_m', 'confidence', 'observations', 'unique_points',
            'last_seen')
    return {k: c.get(k) for k in keys}


def _match_cell(db, plmns, tac, cid):
    """(databank cell, match_type) for one query cell, or (None, None)."""
    # Full ID first (phones; also GSM / small IDs), then low 16 bits (devices).
    for plmn in plmns:
        if tac is not None and plmn + (tac, cid) in db['by_full']:
            return db['by_full'][plmn + (tac, cid)], 'exact'
    candidates = []
    for plmn in plmns:
        if tac is not None:
            candidates += db['by_cid16'].get(plmn + (tac, cid), []) if cid <= 0xFFFF else []
        else:
            candidates += db['by_cid'].get(plmn + (cid,), [])
            if cid <= 0xFFFF:
                candidates += db['by_cid'].get(plmn + ('16', cid), [])
    if not candidates:
        return None, None
    best = max(candidates, key=lambda c: c['observations'])
    if tac is None:
        kind = 'cid_without_tac'
    else:
        kind = 'cid16'
    if len({(c['tac'], c['cid']) for c in candidates}) > 1:
        kind += '_ambiguous'
    return best, kind


def locate(cells, network=None, mcc=None, mnc=None):
    """
    Estimate a position from cells.

    cells:   [{'tac': int|None, 'cid': int, 'dbm': int|None, 'mcc': str|None, 'mnc': str|None, 'role': str}]
    network: network name ('airtel', 'Jio 4G', 'CELLONE', ...) limiting the search to its PLMNs.
    mcc/mnc: PLMN for cells that don't carry their own.

    Returns a dict: found (bool), location {lat, lon, accuracy_m} or None,
    method ('cell' | 'multi_cell' | 'tac_area' | None), matched / unmatched cells.
    Raises DatabankUnavailable.
    """
    db = get_databank()
    network_key = resolve_network(db, network) if network else None
    default_plmns = (
        [(str(mcc), str(mnc))] if mcc and mnc else
        network_plmns(db, network_key) if network_key else
        [tuple(p.split('-')) for n in db['networks'].values() for p in n.get('plmns', [])]
    )

    matched, unmatched = [], []
    for q in cells:
        plmns = [(str(q['mcc']), str(q['mnc']))] if q.get('mcc') and q.get('mnc') else default_plmns
        cell, kind = _match_cell(db, plmns, q.get('tac'), q['cid'])
        query = {k: q.get(k) for k in ('role', 'mcc', 'mnc', 'tac', 'cid', 'dbm')}
        if cell:
            matched.append({'query': query, 'match': kind, 'cell': cell, 'dbm': q.get('dbm')})
        else:
            unmatched.append(query)

    result = {
        'found': False, 'location': None, 'method': None, 'confidence': None,
        'network': network_key, 'network_name': db['networks'].get(network_key, {}).get('name') if network_key else None,
        'matched_cells': [{'query': m['query'], 'match': m['match'], 'cell': _public_cell(m['cell'])} for m in matched],
        'unmatched_cells': unmatched,
        'databank': databank_info(db),
    }

    if matched:
        # Signal-weighted, and well-known cells (small accuracy) count more.
        ws = [_weight(m['dbm']) / m['cell']['accuracy_m'] for m in matched]
        lat = sum(m['cell']['lat'] * w for m, w in zip(matched, ws)) / sum(ws)
        lon = sum(m['cell']['lon'] * w for m, w in zip(matched, ws)) / sum(ws)
        spread = max(haversine_m(lat, lon, m['cell']['lat'], m['cell']['lon']) for m in matched)
        accuracy = max(MIN_ACCURACY_M, min(m['cell']['accuracy_m'] for m in matched), spread)
        conf_rank = {'low': 0, 'medium': 1, 'high': 2}
        best_conf = max((m['cell']['confidence'] for m in matched), key=lambda c: conf_rank.get(c, 0))
        if any(m['match'].endswith('_ambiguous') for m in matched):
            best_conf = 'low'
        result.update(found=True, method='cell' if len(matched) == 1 else 'multi_cell', confidence=best_conf,
                      location={'lat': round(lat, 6), 'lon': round(lon, 6), 'accuracy_m': int(accuracy)})
        return result

    # No known cell: fall back to the area of known cells in the same TAC.
    for q in cells:
        if q.get('tac') is None:
            continue
        plmns = [(str(q['mcc']), str(q['mnc']))] if q.get('mcc') and q.get('mnc') else default_plmns
        area = [c for plmn in plmns for c in db['by_tac'].get(plmn + (q['tac'],), [])]
        if not area:
            continue
        ws = [1 / c['accuracy_m'] for c in area]
        lat = sum(c['lat'] * w for c, w in zip(area, ws)) / sum(ws)
        lon = sum(c['lon'] * w for c, w in zip(area, ws)) / sum(ws)
        accuracy = max(haversine_m(lat, lon, c['lat'], c['lon']) + c['accuracy_m'] for c in area)
        result.update(found=True, method='tac_area', confidence='low',
                      location={'lat': round(lat, 6), 'lon': round(lon, 6), 'accuracy_m': int(accuracy)},
                      tac_area={'tac': q['tac'], 'known_cells_in_tac': len(area)})
        return result
    return result


def cells_from_pvt(parts, idx):
    """
    (network operator, cells) from a split PVT packet whose 'PVT' token is at
    parts[idx]: the serving cell then up to 4 neighbours, IDs in hex. Blank /
    all-zero cells are left out; neighbours inherit the serving MCC/MNC.
    """
    def field(offset):
        pos = idx + offset
        return parts[pos].strip() if len(parts) > pos else ''

    def hex_or_none(value):
        try:
            n = parse_number(value, hex_format=True)
        except ValueError:
            return None
        return n or None  # 0 / 0000 = no cell

    operator = field(PVT_OFFSET_NETWORK_OPERATOR) or None
    mcc, mnc = field(PVT_OFFSET_MCC) or None, field(PVT_OFFSET_MCC + 1) or None
    if mcc in ('0', '000'):
        mcc = mnc = None
    cells = []
    try:
        csq = int(field(PVT_OFFSET_GSM_SIGNAL))
        serving_dbm = -113 + 2 * csq if 0 <= csq <= 31 else None
    except ValueError:
        serving_dbm = None
    serving_cid = hex_or_none(field(PVT_OFFSET_MCC + 3))
    if serving_cid:
        cells.append({'role': 'serving', 'mcc': mcc, 'mnc': mnc, 'tac': hex_or_none(field(PVT_OFFSET_MCC + 2)),
                      'cid': serving_cid, 'dbm': serving_dbm})
    for i in range(PVT_NEIGHBOUR_COUNT):
        base = PVT_OFFSET_NEIGHBOURS + 3 * i
        cid = hex_or_none(field(base))
        if cid:
            # Neighbour signal units are not documented; leave it unweighted (below serving).
            cells.append({'role': f'neighbour_{i + 1}', 'mcc': mcc, 'mnc': mnc, 'tac': hex_or_none(field(base + 1)),
                          'cid': cid, 'dbm': (serving_dbm - 10) if serving_dbm is not None else None})
    return operator, cells
