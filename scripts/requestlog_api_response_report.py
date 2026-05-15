#!/usr/bin/env python3
"""
Report API response-time stats from RequestLog table.

Targets:
- /api/gps_track_data_api/
- /api/tag/tag_ownerlist/
- /api/alart_list/

Windows:
- Last 24h
- Last 3h
- Last 1h
- Last 5m

Usage:
  python3 scripts/requestlog_api_response_report.py
  python3 scripts/requestlog_api_response_report.py --top 3
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import timedelta


def setup_django() -> None:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_root = os.path.join(repo_root, "Skytronsystem")
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Skytronsystem.settings")

    import django

    django.setup()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RequestLog response-time report for key APIs")
    parser.add_argument("--top", type=int, default=3, help="Number of top APIs to show per window")
    return parser.parse_args()


def format_table(headers, rows):
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    line = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    out = [line]
    out.append("| " + " | ".join(headers[i].ljust(widths[i]) for i in range(len(headers))) + " |")
    out.append(line)
    for row in rows:
        out.append("| " + " | ".join(str(row[i]).ljust(widths[i]) for i in range(len(headers))) + " |")
    out.append(line)
    return "\n".join(out)


def main() -> int:
    args = parse_args()
    setup_django()

    from django.db.models import Avg, Max, Count
    from django.utils import timezone
    from skytron_api.models import RequestLog

    endpoints = [
        "/api/gps_track_data_api/",
        "/api/tag/tag_ownerlist/",
        "/api/alart_list/",
    ]

    now = timezone.now()
    windows = [
        ("Last 24 Hours", timedelta(hours=24)),
        ("Last 3 Hours", timedelta(hours=3)),
        ("Last 1 Hour", timedelta(hours=1)),
        ("Last 5 Minutes", timedelta(minutes=5)),
    ]

    print("RequestLog API Response-Time Report")
    print("Source: skytron_api_requestlog.response_time_ms")
    print(f"Reference Time: {now.isoformat()}")
    print()

    for title, delta in windows:
        since = now - delta

        rows = []
        for ep in endpoints:
            qs = RequestLog.objects.filter(
                timestamp__gte=since,
                request_url__contains=ep,
            )

            total_count = qs.count()
            timed_qs = qs.filter(response_time_ms__isnull=False)
            timed_stats = timed_qs.aggregate(
                avg_ms=Avg("response_time_ms"),
                max_ms=Max("response_time_ms"),
                timed_count=Count("id"),
            )

            timed_count = int(timed_stats["timed_count"] or 0)
            avg_ms = timed_stats["avg_ms"]
            max_ms = timed_stats["max_ms"]

            rows.append([
                ep,
                total_count,
                timed_count,
                f"{avg_ms:.1f}" if avg_ms is not None else "N/A",
                int(max_ms) if max_ms is not None else "N/A",
            ])

        # Rank by avg response time (N/A -> last)
        rows.sort(key=lambda r: float(r[3]) if r[3] != "N/A" else -1.0, reverse=True)
        rows = rows[: max(1, args.top)]

        print(f"=== {title} ===")
        print(
            format_table(
                ["API", "Total Reqs", "Timed Reqs", "Avg Resp (ms)", "Max Resp (ms)"],
                rows,
            )
        )
        print()

    print("Note:")
    print("- If Timed Reqs is 0/N/A, run migrations and collect fresh traffic first.")
    print("- response_time_ms is populated by RequestLoggerMiddleware after this update.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
