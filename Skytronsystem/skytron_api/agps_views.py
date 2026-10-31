"""
A-GPS location lookup from cell towers (logic and data file: agps.py).

    GET|POST /api/agps/locate/      any logged-in user

One cell (GET query params or POST JSON):
    network=airtel  tac=7130  cell_id=248579851  [dbm=-95]  [mcc=405 mnc=56]  [id_format=dec|hex]

Several cells (POST JSON), each may carry its own mcc/mnc/dbm:
    {"network": "jio", "cells": [{"tac": 1, "cell_id": 592915, "dbm": -98}, {"tac": 1, "cell_id": 391193}]}

A device PVT packet (POST JSON), serving + neighbour cells read from it, IDs in hex:
    {"raw_packet": "$,PVT,MAPW,...,AIRTEL,...,405,56,1BDA,075B,671F,1BDA,1,..."}

network is a name or operator label (airtel, Jio 4G, CELLONE, Vodafone, ...);
it is optional when mcc/mnc are given. id_format=hex reads tac/cell_id as hex
(the form devices send, e.g. tac=1BDA cell_id=0711); '0x' always means hex.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from . import agps
from .views import _packet_fields

MAX_CELLS = 16
MAX_PACKET_LENGTH = 2000


class _Invalid(Exception):
    pass


def _err(message, code):
    return Response({'status': 'error', 'message': message}, status=code)


def _number(value, name, hex_format, required=False):
    try:
        n = agps.parse_number(value, hex_format)
    except (TypeError, ValueError):
        raise _Invalid(f'{name} must be a {"hex" if hex_format else "decimal"} number')
    if n is None and required:
        raise _Invalid(f'{name} is required')
    if n is not None and not (0 <= n < 2 ** 36):
        raise _Invalid(f'{name} is out of range')
    return n


def _plmn_part(value, name):
    if value in (None, ''):
        return None
    s = str(value).strip()
    if not s.isdigit() or len(s) > 3:
        raise _Invalid(f'{name} must be 2-3 digits')
    return s


def _query_cell(item, hex_format, role):
    if not isinstance(item, dict):
        raise _Invalid('each cell must be an object')
    dbm = item.get('dbm')
    if dbm not in (None, ''):
        try:
            dbm = int(dbm)
        except (TypeError, ValueError):
            raise _Invalid('dbm must be an integer')
        if not -150 <= dbm <= 0:
            raise _Invalid('dbm must be between -150 and 0')
    else:
        dbm = None
    return {
        'role': role,
        'mcc': _plmn_part(item.get('mcc'), 'mcc'),
        'mnc': _plmn_part(item.get('mnc'), 'mnc'),
        'tac': _number(item.get('tac', item.get('lac')), 'tac', hex_format),
        'cid': _number(item.get('cell_id', item.get('cid')), 'cell_id', hex_format, required=True),
        'dbm': dbm,
    }


def _parse_request(data):
    """(network, mcc, mnc, cells, source) from the request data."""
    network = (str(data.get('network') or '').strip() or None)
    if network and len(network) > 64:
        raise _Invalid('network is too long')
    mcc, mnc = _plmn_part(data.get('mcc'), 'mcc'), _plmn_part(data.get('mnc'), 'mnc')
    if bool(mcc) != bool(mnc):
        raise _Invalid('give both mcc and mnc, or neither')

    raw_packet = data.get('raw_packet')
    if raw_packet:
        if not isinstance(raw_packet, str) or len(raw_packet) > MAX_PACKET_LENGTH:
            raise _Invalid('raw_packet must be a PVT packet string')
        parts = _packet_fields(raw_packet)
        idx = next((i for i, p in enumerate(parts[:3]) if p.upper() == 'PVT'), None)
        if idx is None:
            raise _Invalid('raw_packet is not a PVT packet')
        operator, cells = agps.cells_from_pvt(parts, idx)
        if not cells:
            raise _Invalid('raw_packet has no cell tower information')
        # The packet's cells carry their own MCC/MNC; the operator label is only informative.
        return network or operator, mcc, mnc, cells, 'raw_packet'

    id_format = str(data.get('id_format') or 'dec').strip().lower()
    if id_format not in ('dec', 'hex'):
        raise _Invalid("id_format must be 'dec' or 'hex'")
    hex_format = id_format == 'hex'

    if data.get('cells') is not None:
        items = data.get('cells')
        if not isinstance(items, list) or not items:
            raise _Invalid('cells must be a non-empty list')
        if len(items) > MAX_CELLS:
            raise _Invalid(f'at most {MAX_CELLS} cells')
        cells = [_query_cell(item, hex_format, 'serving' if i == 0 else f'cell_{i + 1}') for i, item in enumerate(items)]
        return network, mcc, mnc, cells, 'cells'

    return network, mcc, mnc, [_query_cell(data, hex_format, 'serving')], 'single_cell'


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([UserRateThrottle])
def agps_locate(request):
    data = request.data if request.method == 'POST' else request.GET
    if not hasattr(data, 'get'):
        return _err('Request body must be a JSON object.', status.HTTP_400_BAD_REQUEST)
    try:
        network, mcc, mnc, cells, source = _parse_request(data)
    except _Invalid as e:
        return _err(str(e), status.HTTP_400_BAD_REQUEST)

    try:
        result = agps.locate(cells, network=network, mcc=mcc, mnc=mnc)
    except agps.DatabankUnavailable as e:
        return _err(str(e), status.HTTP_503_SERVICE_UNAVAILABLE)

    if network and not result['network'] and not mcc and source != 'raw_packet':
        return _err(f"Unknown network '{network}'. Known: {', '.join(result['databank']['networks'])}.",
                    status.HTTP_400_BAD_REQUEST)

    result['input'] = source
    return Response({
        'status': 'success' if result['found'] else 'not_found',
        'message': None if result['found'] else 'None of the given cells or their TAC areas are in the A-GPS databank.',
        **result,
    })
