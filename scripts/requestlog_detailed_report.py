#!/usr/bin/env python3
"""
Detailed RequestLog database report.

What it does:
- Reads RequestLog table from database
- Groups by endpoint, user, IP, application
- Shows average/max/min response times
- Supports time windows: 24h, 3h, 1h, 5m
- Shows top endpoints by various metrics (response time, request count, errors)
- Shows top users/IPs accessing each endpoint

Usage:
  python3 scripts/requestlog_detailed_report.py
  python3 scripts/requestlog_detailed_report.py --window 1h --top 10
  python3 scripts/requestlog_detailed_report.py --window 24h --sort max_time
  python3 scripts/requestlog_detailed_report.py --window 1h --sort error_rate
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import timedelta
from typing import Dict, List, Optional, Tuple


def setup_django() -> None:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_root = os.path.join(repo_root, "Skytronsystem")
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Skytronsystem.settings")

    import django

    django.setup()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detailed RequestLog database report with response times, users, IPs"
    )
    parser.add_argument(
        "--window",
        choices=["24h", "3h", "1h", "5m"],
        default="1h",
        help="Time window to report on",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of top endpoints/users/IPs to show",
    )
    parser.add_argument(
        "--sort",
        choices=["count", "avg_time", "max_time", "error_rate"],
        default="count",
        help="Sort top endpoints by this metric",
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        help="Filter to specific endpoint (partial match)",
    )
    return parser.parse_args()


def format_table(headers: List[str], rows: List[List[str]]) -> str:
    """Format data as ASCII table."""
    if not rows:
        return "No data."

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))

    def hline() -> str:
        return "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    out = [hline()]
    out.append("| " + " | ".join(headers[i].ljust(widths[i]) for i in range(len(headers))) + " |")
    out.append(hline())
    for row in rows:
        out.append("| " + " | ".join(str(row[i]).ljust(widths[i]) for i in range(len(headers))) + " |")
    out.append(hline())
    return "\n".join(out)


def get_window_delta(window_str: str) -> timedelta:
    mapping = {
        "24h": timedelta(hours=24),
        "3h": timedelta(hours=3),
        "1h": timedelta(hours=1),
        "5m": timedelta(minutes=5),
    }
    return mapping[window_str]


def main() -> int:
    args = parse_args()
    setup_django()

    from django.db.models import Avg, Max, Min, Count, Q, F
    from django.utils import timezone
    from skytron_api.models import RequestLog

    window_delta = get_window_delta(args.window)
    now = timezone.now()
    since = now - window_delta

    base_qs = RequestLog.objects.filter(timestamp__gte=since)

    if args.endpoint:
        base_qs = base_qs.filter(request_url__contains=args.endpoint)

    total_count = base_qs.count()
    if total_count == 0:
        print(f"No requests found in the last {args.window}.")
        return 0

    print("=" * 100)
    print(f"RequestLog Detailed Report ({args.window})")
    print("=" * 100)
    print(f"Reference Time: {now.isoformat()}")
    print(f"Time Window: {since.isoformat()} to {now.isoformat()}")
    print(f"Total Requests: {total_count}")
    print()

    # === BY ENDPOINT ===
    print("=" * 100)
    print("BY ENDPOINT (sorted by {})".format(args.sort.upper()))
    print("=" * 100)

    endpoint_stats = (
        base_qs
        .values("request_url")
        .annotate(
            count=Count("id"),
            avg_ms=Avg("response_time_ms"),
            max_ms=Max("response_time_ms"),
            min_ms=Min("response_time_ms"),
            errors_with_code=Count("id", filter=Q(error_code__isnull=False)),
        )
        .order_by()
    )

    # Convert to list and calculate error rate
    endpoints = []
    for stat in endpoint_stats:
        error_count = stat.get("errors_with_code", 0)
        error_rate = (error_count / stat["count"] * 100.0) if stat["count"] > 0 else 0.0
        endpoints.append({
            "url": stat["request_url"],
            "count": stat["count"],
            "avg_ms": stat.get("avg_ms") or 0.0,
            "max_ms": stat.get("max_ms") or 0,
            "min_ms": stat.get("min_ms") or 0,
            "errors": error_count,
            "error_rate": error_rate,
        })

    # Sort by requested metric
    if args.sort == "count":
        endpoints.sort(key=lambda x: x["count"], reverse=True)
    elif args.sort == "avg_time":
        endpoints.sort(key=lambda x: x["avg_ms"], reverse=True)
    elif args.sort == "max_time":
        endpoints.sort(key=lambda x: x["max_ms"], reverse=True)
    elif args.sort == "error_rate":
        endpoints.sort(key=lambda x: x["error_rate"], reverse=True)

    rows = []
    for ep in endpoints[: args.top]:
        rows.append([
            ep["url"],
            str(ep["count"]),
            f"{ep['avg_ms']:.1f}",
            f"{ep['max_ms']}",
            f"{ep['min_ms']}",
            str(ep["errors"]),
            f"{ep['error_rate']:.1f}%",
        ])

    print(format_table(
        ["Endpoint", "Req Count", "Avg (ms)", "Max (ms)", "Min (ms)", "Errors", "Error%"],
        rows,
    ))
    print()

    # === TOP ENDPOINTS BY AVERAGE RESPONSE TIME ===
    print("=" * 100)
    print(f"TOP {args.top} SLOWEST ENDPOINTS (by avg response time)")
    print("=" * 100)
    slowest = sorted(endpoints, key=lambda x: x["avg_ms"], reverse=True)[: args.top]
    rows = []
    for ep in slowest:
        rows.append([
            ep["url"],
            str(ep["count"]),
            f"{ep['avg_ms']:.1f}",
            f"{ep['max_ms']}",
            f"{ep['error_rate']:.1f}%",
        ])
    print(format_table(
        ["Endpoint", "Req Count", "Avg (ms)", "Max (ms)", "Error%"],
        rows,
    ))
    print()

    # === TOP ENDPOINTS BY ERROR RATE ===
    print("=" * 100)
    print(f"TOP {args.top} ENDPOINTS BY ERROR RATE")
    print("=" * 100)
    errored = [e for e in endpoints if e["error_rate"] > 0]
    errored.sort(key=lambda x: x["error_rate"], reverse=True)
    rows = []
    for ep in errored[: args.top]:
        rows.append([
            ep["url"],
            str(ep["count"]),
            str(ep["errors"]),
            f"{ep['error_rate']:.1f}%",
            f"{ep['avg_ms']:.1f}",
        ])
    print(format_table(
        ["Endpoint", "Req Count", "Errors", "Error%", "Avg (ms)"],
        rows,
    ))
    print()

    # === BY USER/IP ===
    print("=" * 100)
    print(f"TOP {args.top} IPs (most active)")
    print("=" * 100)

    ip_stats = (
        base_qs
        .values("ip_address")
        .annotate(
            count=Count("id"),
            avg_ms=Avg("response_time_ms"),
            max_ms=Max("response_time_ms"),
            errors=Count("id", filter=Q(error_code__isnull=False)),
        )
        .order_by("-count")[: args.top]
    )

    rows = []
    for stat in ip_stats:
        ip = stat.get("ip_address") or "unknown"
        error_count = stat.get("errors", 0)
        error_rate = (error_count / stat["count"] * 100.0) if stat["count"] > 0 else 0.0
        rows.append([
            ip,
            str(stat["count"]),
            f"{stat.get('avg_ms') or 0:.1f}",
            f"{stat.get('max_ms') or 0}",
            f"{error_rate:.1f}%",
        ])

    print(format_table(
        ["IP Address", "Req Count", "Avg (ms)", "Max (ms)", "Error%"],
        rows,
    ))
    print()

    # === BY RESPONSE TYPE ===
    print("=" * 100)
    print("RESPONSE TYPE BREAKDOWN")
    print("=" * 100)

    response_stats = (
        base_qs
        .values("response_type")
        .annotate(
            count=Count("id"),
            avg_ms=Avg("response_time_ms"),
            errors=Count("id", filter=Q(error_code__isnull=False)),
        )
        .order_by("-count")
    )

    rows = []
    for stat in response_stats:
        resp_type = stat.get("response_type") or "unknown"
        rows.append([
            resp_type,
            str(stat["count"]),
            f"{(stat['count'] / total_count * 100.0):.1f}%",
            f"{stat.get('avg_ms') or 0:.1f}",
            str(stat.get("errors", 0)),
        ])

    print(format_table(
        ["Response Type", "Count", "Percentage", "Avg (ms)", "Errors"],
        rows,
    ))
    print()

    # === SUMMARY STATS ===
    print("=" * 100)
    print("OVERALL STATISTICS")
    print("=" * 100)

    all_stats = base_qs.aggregate(
        avg_ms=Avg("response_time_ms"),
        max_ms=Max("response_time_ms"),
        min_ms=Min("response_time_ms"),
        total_errors=Count("id", filter=Q(error_code__isnull=False)),
    )

    error_count = all_stats.get("total_errors", 0)
    error_rate = (error_count / total_count * 100.0) if total_count > 0 else 0.0

    summary = [
        ["Total Requests", str(total_count)],
        ["Avg Response Time (ms)", f"{all_stats.get('avg_ms') or 0:.1f}"],
        ["Max Response Time (ms)", f"{all_stats.get('max_ms') or 0}"],
        ["Min Response Time (ms)", f"{all_stats.get('min_ms') or 0}"],
        ["Total Errors", str(all_stats.get("total_errors", 0))],
        ["Error Rate", f"{error_rate:.1f}%"],
        ["Unique Endpoints", str(len(endpoints))],
        ["Unique IPs", str(base_qs.values("ip_address").distinct().count())],
    ]

    print(format_table(["Metric", "Value"], summary))
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
