#!/usr/bin/env python3
"""
API latency/load report from Nginx access logs.

What it does:
- Reads /var/log/nginx/access.log* (plain + .gz)
- Filters API requests (/api/...)
- Builds reports for last 24h, 3h, 1h, and 5m

If log timing fields are present (e.g., $request_time), it ranks by latency.
If timing fields are missing, it falls back to timeout/error-based ranking.

Usage:
  python3 scripts/api_latency_report.py
  python3 scripts/api_latency_report.py --top 10
  python3 scripts/api_latency_report.py --logs '/var/log/nginx/access.log*'
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import gzip
import io
import os
import re
import sys
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple


LINE_RE = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<ts>[^\]]+)\]\s+"(?P<req>[^"]*)"\s+(?P<status>\d{3}|-)\s+(?P<body>\d+|-)\s+"(?P<ref>[^"]*)"\s+"(?P<ua>[^"]*)"(?P<rest>.*)$'
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate API latency/load report from Nginx logs")
    p.add_argument("--logs", default="/var/log/nginx/access.log*", help="Glob pattern for access logs")
    p.add_argument("--top", type=int, default=8, help="Top APIs per window")
    return p.parse_args()


def open_log_file(path: str):
    if path.endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", errors="replace")
    return open(path, "r", encoding="utf-8", errors="replace")


def parse_timestamp(ts: str) -> Optional[dt.datetime]:
    # Example: 14/May/2026:03:57:31 +0000
    try:
        return dt.datetime.strptime(ts, "%d/%b/%Y:%H:%M:%S %z")
    except ValueError:
        return None


def parse_request(request_line: str) -> Tuple[str, str]:
    # "GET /api/x HTTP/1.1" -> (GET, /api/x)
    parts = request_line.split()
    if len(parts) < 2:
        return "", ""
    method = parts[0]
    raw_path = parts[1]
    path = raw_path.split("?", 1)[0]
    return method, path


def parse_optional_request_time(rest: str) -> Optional[float]:
    # Tries to parse first numeric token after user-agent, typical for $request_time.
    # Example rest values:
    #   " 0.123"
    #   " 0.123 0.120"
    #   ""
    #   " -"
    tokens = rest.strip().split()
    if not tokens:
        return None
    token = tokens[0]
    if token == "-":
        return None
    try:
        return float(token)
    except ValueError:
        return None


def iter_records(log_glob: str) -> Iterable[Dict[str, object]]:
    paths = sorted(glob.glob(log_glob), key=os.path.getmtime)
    for path in paths:
        try:
            with open_log_file(path) as f:
                for line in f:
                    m = LINE_RE.match(line.rstrip("\n"))
                    if not m:
                        continue

                    ts = parse_timestamp(m.group("ts"))
                    if ts is None:
                        continue

                    method, path_only = parse_request(m.group("req"))
                    if not path_only.startswith("/api/"):
                        continue

                    status_raw = m.group("status")
                    body_raw = m.group("body")
                    req_time = parse_optional_request_time(m.group("rest"))

                    try:
                        status = int(status_raw)
                    except ValueError:
                        status = 0

                    try:
                        body_bytes = int(body_raw)
                    except ValueError:
                        body_bytes = 0

                    yield {
                        "ts": ts,
                        "method": method,
                        "path": path_only,
                        "status": status,
                        "body_bytes": body_bytes,
                        "request_time": req_time,
                    }
        except (FileNotFoundError, PermissionError, OSError):
            continue


def aggregate(records: Iterable[Dict[str, object]], start_time: dt.datetime):
    by_api = defaultdict(lambda: {
        "count": 0,
        "timeout_like": 0,   # 499/504 are common timeout symptom codes
        "server_err": 0,     # 5xx
        "client_err": 0,     # 4xx
        "bytes_total": 0,
        "rt_count": 0,
        "rt_sum": 0.0,
        "rt_max": 0.0,
        "rt_4xx_count": 0,
        "rt_4xx_sum": 0.0,
    })

    total = 0
    timing_seen = False

    for r in records:
        ts = r["ts"]
        if not isinstance(ts, dt.datetime) or ts < start_time:
            continue

        total += 1
        api = str(r["path"])
        status = int(r["status"])
        body = int(r["body_bytes"])
        rt = r["request_time"]

        s = by_api[api]
        s["count"] += 1
        s["bytes_total"] += body

        if status in (499, 504):
            s["timeout_like"] += 1
        if 500 <= status <= 599:
            s["server_err"] += 1
        if 400 <= status <= 499:
            s["client_err"] += 1

        if isinstance(rt, float):
            timing_seen = True
            s["rt_count"] += 1
            s["rt_sum"] += rt
            if rt > s["rt_max"]:
                s["rt_max"] = rt
            if 400 <= status <= 499:
                s["rt_4xx_count"] += 1
                s["rt_4xx_sum"] += rt

    return total, timing_seen, by_api


def format_table(headers: List[str], rows: List[List[str]]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def line() -> str:
        return "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    out = [line()]
    out.append("| " + " | ".join(headers[i].ljust(widths[i]) for i in range(len(headers))) + " |")
    out.append(line())
    for row in rows:
        out.append("| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(headers))) + " |")
    out.append(line())
    return "\n".join(out)


def build_rows(timing_seen: bool, by_api: Dict[str, Dict[str, object]], top: int) -> Tuple[List[str], List[List[str]]]:
    if timing_seen:
        ranked = sorted(
            by_api.items(),
            key=lambda kv: (
                float(kv[1]["rt_max"]),
                float(kv[1]["rt_sum"]) / max(int(kv[1]["rt_count"]), 1),
                int(kv[1]["count"]),
            ),
            reverse=True,
        )[:top]

        headers = ["API", "Req", "Max Time(s)", "Avg Time(s)", "Avg 4xx Time(s)", "499/504", "5xx"]
        rows: List[List[str]] = []
        for api, s in ranked:
            avg = float(s["rt_sum"]) / max(int(s["rt_count"]), 1)
            avg_4xx = "N/A"
            if int(s["rt_4xx_count"]) > 0:
                avg_4xx = f"{(float(s['rt_4xx_sum']) / int(s['rt_4xx_count'])):.3f}"
            rows.append([
                api,
                str(s["count"]),
                f"{float(s['rt_max']):.3f}",
                f"{avg:.3f}",
                avg_4xx,
                str(s["timeout_like"]),
                str(s["server_err"]),
            ])
        return headers, rows

    # Fallback mode: no timing in logs, rank by timeout/error signal and request volume.
    ranked = sorted(
        by_api.items(),
        key=lambda kv: (
            int(kv[1]["timeout_like"]),
            int(kv[1]["server_err"]),
            int(kv[1]["client_err"]),
            int(kv[1]["count"]),
        ),
        reverse=True,
    )[:top]

    headers = ["API", "Req", "499/504", "5xx", "4xx", "Bytes(MB)"]
    rows = []
    for api, s in ranked:
        rows.append([
            api,
            str(s["count"]),
            str(s["timeout_like"]),
            str(s["server_err"]),
            str(s["client_err"]),
            f"{int(s['bytes_total']) / (1024.0 * 1024.0):.1f}",
        ])
    return headers, rows


def main() -> int:
    args = parse_args()

    all_records = list(iter_records(args.logs))
    if not all_records:
        print("No API records found in logs.")
        return 1

    now = max(r["ts"] for r in all_records if isinstance(r.get("ts"), dt.datetime))
    assert isinstance(now, dt.datetime)

    windows = [
        ("Last 24 Hours", dt.timedelta(hours=24)),
        ("Last 3 Hours", dt.timedelta(hours=3)),
        ("Last 1 Hour", dt.timedelta(hours=1)),
        ("Last 5 Minutes", dt.timedelta(minutes=5)),
    ]

    print("API Latency/Load Report")
    print(f"Log Pattern: {args.logs}")
    print(f"Reference Time: {now.isoformat()}")
    print()

    any_timing = any(isinstance(r.get("request_time"), float) for r in all_records)
    if not any_timing:
        print("Note: request_time field not found in current log format.")
        print("Ranking below uses timeout/error signals (499/504, 5xx, 4xx) as load proxy.")
        print("To get exact latency ranking, include $request_time in Nginx access_log format.")
        print()

    for title, delta in windows:
        start_time = now - delta
        total, timing_seen, by_api = aggregate(all_records, start_time)
        print(f"=== {title} ===")
        print(f"Total API Requests: {total}")

        if not by_api:
            print("No API requests in this window.\n")
            continue

        headers, rows = build_rows(timing_seen, by_api, args.top)
        print(format_table(headers, rows))
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
