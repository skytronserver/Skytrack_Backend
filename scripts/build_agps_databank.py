#!/usr/bin/env python3
"""
Build the A-GPS cell databank (Skytronsystem/skytron_api/data/agps_cell_databank.json)
from the BLE SOS app logs, where each phone reports its GPS fix together with
its serving cell (MCC/MNC/TAC/CID/PCI/EARFCN).

The backend reads that file through skytron_api/agps.py and reloads it when it
changes, so re-running this script and redeploying the file is all an update needs.

Usage:
    # pull straight from the API (superadmin access token)
    python3 scripts/build_agps_databank.py --api https://api.skytron.in --token <JWT>

    # or from saved pages of /api/ble-sos/app-log/list/ (each a JSON response,
    # or a plain JSON list of log rows)
    python3 scripts/build_agps_databank.py --from-json page1.json page2.json

    --out <path>   write somewhere else (default: the repo databank file)

Only the serving cell is used: the app reports neighbour cells with dBm only,
which cannot be keyed. Serving cells without a CID/TAC (Jio 5G NR today) are
skipped, as are cells listed in BLACKLIST.
"""
import argparse
import json
import math
import os
import statistics
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(REPO, 'Skytronsystem', 'skytron_api', 'data', 'agps_cell_databank.json')

# Network name -> PLMNs (MCC-MNC) and the operator names phones/devices report.
# Only PLMNs seen so far are listed; add more as new circles show up.
NETWORKS = {
    'airtel': {'name': 'Airtel', 'plmns': ['405-56', '404-92'],
               'aliases': ['airtel', 'bharti airtel', 'ind airtel', 'airtel 4g', 'airtel 5g']},
    'jio': {'name': 'Jio', 'plmns': ['405-855'],
            'aliases': ['jio', 'jio 4g', 'jio true5g', 'reliance jio', 'jio 5g']},
    'vi': {'name': 'Vi (Vodafone Idea)', 'plmns': ['405-751'],
           'aliases': ['vi', 'vodafone', 'vodafone in', 'idea', 'vi india', 'vodafone idea']},
    'bsnl': {'name': 'BSNL', 'plmns': ['404-38'],
             'aliases': ['bsnl', 'cellone', 'bsnl mobile', 'bsnl 4g']},
}
PLMN_NETWORK = {p: key for key, n in NETWORKS.items() for p in n['plmns']}

# (mcc, mnc, cid) of cells whose reports are not trusted.
BLACKLIST = [
    {'mcc': '404', 'mnc': '38', 'cid': 222979861,
     'reason': 'BSNL phone reported this cell for 3 h over a 9 km drive on 2026-10-31 while its dBm '
               'kept changing: a frozen identity. The CID (0xD4A6715) is an Airtel cell in TAC 7130 '
               '(Airtel devices report 6715/1BDA as a neighbour).'},
]
BLACKLIST_KEYS = {(b['mcc'], b['mnc'], b['cid']) for b in BLACKLIST}

GRID_DECIMALS = 3  # ~110 m squares


def lte_band(earfcn):
    for lo, hi, band in [(0, 599, 1), (1200, 1949, 3), (2400, 2649, 5), (3450, 3799, 8),
                         (38650, 39649, 40), (39650, 41589, 41)]:
        if earfcn is not None and lo <= earfcn <= hi:
            return band
    return None


def haversine_m(lat1, lon1, lat2, lon2):
    p = math.radians
    a = (math.sin(p(lat2 - lat1) / 2) ** 2
         + math.cos(p(lat1)) * math.cos(p(lat2)) * math.sin(p(lon2 - lon1) / 2) ** 2)
    return 2 * 6371000 * math.asin(math.sqrt(a))


def signal_weight(dbm):
    """Stronger readings are assumed closer to the site."""
    return 10 ** ((max(dbm if dbm is not None else -120, -130) + 130) / 20)


def fetch_api(api, token):
    rows, page = [], 1
    while True:
        req = urllib.request.Request(
            f'{api.rstrip("/")}/api/ble-sos/app-log/list/?page={page}&page_size=200',
            headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.load(resp)
        rows += body['data']
        if page >= body['pagination']['total_pages']:
            return rows
        page += 1


def load_json(paths):
    rows = []
    for path in paths:
        with open(path) as f:
            body = json.load(f)
        rows += body['data'] if isinstance(body, dict) else body
    return rows


def observations(rows, rejected):
    obs = {}
    for r in rows:
        cells = r.get('cell_ids') or []
        if not cells:
            rejected['event without cell info'] += 1
        for c in cells:
            if not c.get('registered'):
                continue
            if not c.get('cid') or c.get('tac') is None or not c.get('mcc') or not c.get('mnc'):
                rejected['serving cell without CID/TAC (%s)' % c.get('type')] += 1
                continue
            mcc, mnc, cid = str(c['mcc']), str(c['mnc']), int(c['cid'])
            if (mcc, mnc, cid) in BLACKLIST_KEYS:
                rejected['blacklisted cell'] += 1
                continue
            lat, lon = r.get('latitude'), r.get('longitude')
            if lat is None or lon is None or not (6 <= lat <= 38 and 68 <= lon <= 98):
                rejected['GPS missing or outside India'] += 1
                continue
            o = {
                'event_id': r['id'], 'time': r['event_time'], 'lat': lat, 'lon': lon,
                'mcc': mcc, 'mnc': mnc, 'tac': int(c['tac']), 'cid': cid,
                'radio': 'NR' if c.get('type') == 'CellInfoNr' else 'LTE' if c.get('earfcn') is not None else 'GSM',
                'operator_label': c.get('operator'), 'pci': c.get('pci'), 'earfcn': c.get('earfcn'),
                'dbm': c.get('dbm'),
            }
            # A dual-SIM phone can list the same cell twice in one event: keep the stronger.
            key = (r['id'], mcc, mnc, cid)
            if key not in obs or (o['dbm'] or -999) > (obs[key]['dbm'] or -999):
                obs[key] = o
    return sorted(obs.values(), key=lambda o: o['time'])


def build_cells(obs):
    by_cell = defaultdict(list)
    for o in obs:
        by_cell[(o['mcc'], o['mnc'], o['tac'], o['cid'])].append(o)

    cells = []
    for (mcc, mnc, tac, cid), group in by_cell.items():
        # Repeated SOS taps at one spot count once, so a parked phone doesn't dominate.
        points = {}
        for o in group:
            key = (round(o['lat'], 5), round(o['lon'], 5))
            points[key] = max(points.get(key, -999), o['dbm'] if o['dbm'] is not None else -120)
        wsum = sum(signal_weight(d) for d in points.values())
        lat = sum(p[0] * signal_weight(d) for p, d in points.items()) / wsum
        lon = sum(p[1] * signal_weight(d) for p, d in points.items()) / wsum
        dists = sorted(haversine_m(lat, lon, *p) for p in points)
        p90 = dists[min(len(dists) - 1, int(0.9 * len(dists)))]
        n = len(points)
        # We only know where testers stood, not the mast: with few distinct
        # points fall back to a typical urban LTE cell radius.
        if n >= 5:
            accuracy, confidence = max(300, 1.5 * p90), 'high'
        elif n >= 2:
            accuracy, confidence = max(750, 2 * p90), 'medium'
        else:
            accuracy, confidence = 1500, 'low'
        dbms = [o['dbm'] for o in group if o['dbm'] is not None]
        earfcn = statistics.mode(o['earfcn'] for o in group)
        cells.append({
            'network': PLMN_NETWORK.get(f'{mcc}-{mnc}'), 'operator_label': group[0]['operator_label'],
            'radio': group[0]['radio'], 'mcc': mcc, 'mnc': mnc,
            'tac': tac, 'tac_hex': format(tac, '04X'),
            'cid': cid, 'cid_hex': format(cid, 'X'), 'cid16': cid & 0xFFFF, 'cid16_hex': format(cid & 0xFFFF, '04X'),
            'enb_id': cid >> 8, 'local_cell': cid & 0xFF,
            'pci': statistics.mode(o['pci'] for o in group), 'earfcn': earfcn, 'band': lte_band(earfcn),
            'lat': round(lat, 6), 'lon': round(lon, 6), 'accuracy_m': int(accuracy), 'confidence': confidence,
            'observations': len(group), 'unique_points': n,
            'spread_p90_m': int(p90), 'spread_max_m': int(dists[-1]),
            'dbm_min': min(dbms) if dbms else None, 'dbm_max': max(dbms) if dbms else None,
            'dbm_avg': round(sum(dbms) / len(dbms), 1) if dbms else None,
            'first_seen': group[0]['time'], 'last_seen': group[-1]['time'],
        })
    cells.sort(key=lambda c: (c['network'] or '', c['mcc'], c['mnc'], c['tac'], c['cid']))
    return cells


def build_grid(obs):
    """~110 m squares -> the serving cells each network used there."""
    grid = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for o in obs:
        square = (round(o['lat'], GRID_DECIMALS), round(o['lon'], GRID_DECIMALS))
        network = PLMN_NETWORK.get(f"{o['mcc']}-{o['mnc']}") or f"{o['mcc']}-{o['mnc']}"
        grid[square][network][(o['mcc'], o['mnc'], o['tac'], o['cid'])].append(o['dbm'] if o['dbm'] is not None else -120)
    out = []
    for (lat, lon), networks in sorted(grid.items()):
        entry = {'lat': lat, 'lon': lon, 'networks': {}}
        for network, cells in sorted(networks.items()):
            entry['networks'][network] = [
                {'mcc': k[0], 'mnc': k[1], 'tac': k[2], 'cid': k[3], 'samples': len(d), 'dbm_best': max(d),
                 'dbm_avg': round(sum(d) / len(d), 1)}
                for k, d in sorted(cells.items(), key=lambda kv: -max(kv[1]))
            ]
        out.append(entry)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--api', help='API base URL, e.g. https://api.skytron.in')
    src.add_argument('--from-json', nargs='+', metavar='FILE')
    ap.add_argument('--token', default=os.environ.get('SKYTRON_TOKEN'), help='superadmin JWT (or env SKYTRON_TOKEN)')
    ap.add_argument('--out', default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.api:
        if not args.token:
            ap.error('--api needs --token or SKYTRON_TOKEN')
        rows = fetch_api(args.api, args.token)
    else:
        rows = load_json(args.from_json)

    rejected = defaultdict(int)
    obs = observations(rows, rejected)
    cells = build_cells(obs)
    times = sorted(r['event_time'] for r in rows if r.get('event_time'))
    databank = {
        'version': 1,
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'source': {
            'api': '/api/ble-sos/app-log/list/', 'events': len(rows),
            'event_time_from': times[0] if times else None, 'event_time_to': times[-1] if times else None,
            'serving_cell_observations': len(obs), 'rejected': dict(rejected),
        },
        'method': {
            'position': 'signal-weighted centroid of distinct GPS fixes (5 decimal places) where the phone '
                        'was served by the cell; weight = 10^((dBm+130)/20)',
            'accuracy_m': '>=5 distinct points: max(300, 1.5 x p90 spread) [high]; 2-4: max(750, 2 x p90) '
                          '[medium]; 1: 1500 [low]',
            'cid16': 'low 16 bits of the 28-bit LTE ECI; Skytron devices report LAC/TAC and this value '
                     'in hex in PVT packets',
            'grid_decimals': GRID_DECIMALS,
        },
        'networks': NETWORKS,
        'blacklist': BLACKLIST,
        'cells': cells,
        'grid': build_grid(obs),
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, 'w') as f:
        json.dump(databank, f, indent=1)
        f.write('\n')

    print(f'{len(rows)} events -> {len(obs)} observations -> {len(cells)} cells, '
          f'{len(databank["grid"])} grid squares; rejected {dict(rejected)}')
    for key in NETWORKS:
        n = [c for c in cells if c['network'] == key]
        print(f'  {key:7s} {len(n):4d} cells  (high {sum(c["confidence"] == "high" for c in n)}, '
              f'medium {sum(c["confidence"] == "medium" for c in n)}, low {sum(c["confidence"] == "low" for c in n)})')
    print('wrote', args.out)


if __name__ == '__main__':
    sys.exit(main())
