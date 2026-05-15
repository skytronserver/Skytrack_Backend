#!/usr/bin/env python3
"""
VM disk I/O pressure diagnostic.

This script complements system_load_table.py with per-device I/O health indicators
that are useful during intermittent API timeout incidents.

Metrics are computed from /proc/diskstats deltas:
- util%          : percent time device is busy
- r/s, w/s       : read/write operations per second
- rkB/s, wkB/s   : read/write throughput in KiB/s
- await_ms       : average completion time per request
- svctm_ms       : average service time per request
- avgqu_sz       : estimated average queue depth

Usage examples:
  python3 scripts/vm_io_diagnose.py
  python3 scripts/vm_io_diagnose.py --samples 6 --interval 1
  python3 scripts/vm_io_diagnose.py --devices sda,sdb --samples 10 --interval 0.5
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Sequence


@dataclass
class DiskCounters:
    reads_completed: int
    reads_merged: int
    sectors_read: int
    ms_reading: int
    writes_completed: int
    writes_merged: int
    sectors_written: int
    ms_writing: int
    ios_in_progress: int
    ms_doing_io: int
    weighted_ms_doing_io: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose VM disk I/O pressure")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between samples")
    parser.add_argument("--samples", type=int, default=3, help="Number of samples to collect")
    parser.add_argument(
        "--devices",
        type=str,
        default="",
        help="Comma-separated block devices (default: auto-detect physical devices)",
    )
    parser.add_argument(
        "--hide-idle",
        action="store_true",
        help="Hide rows where util%%, IO rates, and queue are all near zero",
    )
    return parser.parse_args()


def list_physical_disks() -> List[str]:
    devices: List[str] = []
    for name in os.listdir("/sys/block"):
        if name.startswith(("loop", "ram", "dm-", "md", "sr")):
            continue
        devices.append(name)
    return sorted(devices)


def resolve_devices(arg_devices: str) -> List[str]:
    if not arg_devices.strip():
        return list_physical_disks()

    available = set(os.listdir("/sys/block"))
    wanted = [d.strip() for d in arg_devices.split(",") if d.strip()]
    unknown = [d for d in wanted if d not in available]
    if unknown:
        raise SystemExit(f"Unknown devices: {', '.join(unknown)}")
    return wanted


def read_diskstats(devices: Sequence[str]) -> Dict[str, DiskCounters]:
    wanted = set(devices)
    result: Dict[str, DiskCounters] = {}

    with open("/proc/diskstats", "r", encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 14:
                continue
            dev = parts[2]
            if dev not in wanted:
                continue

            result[dev] = DiskCounters(
                reads_completed=int(parts[3]),
                reads_merged=int(parts[4]),
                sectors_read=int(parts[5]),
                ms_reading=int(parts[6]),
                writes_completed=int(parts[7]),
                writes_merged=int(parts[8]),
                sectors_written=int(parts[9]),
                ms_writing=int(parts[10]),
                ios_in_progress=int(parts[11]),
                ms_doing_io=int(parts[12]),
                weighted_ms_doing_io=int(parts[13]),
            )

    return result


def safe_div(num: float, den: float) -> float:
    if den <= 0:
        return 0.0
    return num / den


def pressure_level(util_pct: float, await_ms: float, avgqu_sz: float) -> str:
    if util_pct >= 90.0 or await_ms >= 80.0 or avgqu_sz >= 4.0:
        return "HIGH"
    if util_pct >= 70.0 or await_ms >= 30.0 or avgqu_sz >= 1.5:
        return "MEDIUM"
    return "LOW"


def collect_sample(interval: float, devices: Sequence[str]) -> List[Dict[str, float | str]]:
    d1 = read_diskstats(devices)
    time.sleep(interval)
    d2 = read_diskstats(devices)

    now = dt.datetime.now().strftime("%H:%M:%S")
    rows: List[Dict[str, float | str]] = []

    for dev in devices:
        c1 = d1.get(dev)
        c2 = d2.get(dev)
        if c1 is None or c2 is None:
            continue

        d_reads = max(c2.reads_completed - c1.reads_completed, 0)
        d_writes = max(c2.writes_completed - c1.writes_completed, 0)
        d_sectors_read = max(c2.sectors_read - c1.sectors_read, 0)
        d_sectors_written = max(c2.sectors_written - c1.sectors_written, 0)
        d_ms_read = max(c2.ms_reading - c1.ms_reading, 0)
        d_ms_write = max(c2.ms_writing - c1.ms_writing, 0)
        d_ms_io = max(c2.ms_doing_io - c1.ms_doing_io, 0)
        d_weighted_ms_io = max(c2.weighted_ms_doing_io - c1.weighted_ms_doing_io, 0)

        io_count = d_reads + d_writes
        io_time_ms = d_ms_read + d_ms_write

        util_pct = min((d_ms_io / (interval * 1000.0)) * 100.0, 100.0)
        rps = d_reads / interval
        wps = d_writes / interval

        # Kernel sectors are 512 bytes.
        rkbs = (d_sectors_read * 512.0 / 1024.0) / interval
        wkbs = (d_sectors_written * 512.0 / 1024.0) / interval

        await_ms = safe_div(io_time_ms, io_count)
        svctm_ms = safe_div(d_ms_io, io_count)
        avgqu_sz = d_weighted_ms_io / (interval * 1000.0)

        rows.append(
            {
                "time": now,
                "device": dev,
                "util_pct": util_pct,
                "rps": rps,
                "wps": wps,
                "rkbs": rkbs,
                "wkbs": wkbs,
                "await_ms": await_ms,
                "svctm_ms": svctm_ms,
                "avgqu_sz": avgqu_sz,
                "pressure": pressure_level(util_pct, await_ms, avgqu_sz),
            }
        )

    return rows


def fmt_table(rows: List[Dict[str, float | str]], hide_idle: bool) -> str:
    headers = [
        "Time",
        "Dev",
        "util%",
        "r/s",
        "w/s",
        "rkB/s",
        "wkB/s",
        "await_ms",
        "svctm_ms",
        "avgqu_sz",
        "Pressure",
    ]

    data: List[List[str]] = []
    for r in rows:
        if hide_idle:
            near_idle = (
                float(r["util_pct"]) < 0.1
                and float(r["rps"]) < 0.1
                and float(r["wps"]) < 0.1
                and float(r["avgqu_sz"]) < 0.1
            )
            if near_idle:
                continue

        data.append(
            [
                str(r["time"]),
                str(r["device"]),
                f"{float(r['util_pct']):.1f}",
                f"{float(r['rps']):.1f}",
                f"{float(r['wps']):.1f}",
                f"{float(r['rkbs']):.1f}",
                f"{float(r['wkbs']):.1f}",
                f"{float(r['await_ms']):.2f}",
                f"{float(r['svctm_ms']):.2f}",
                f"{float(r['avgqu_sz']):.2f}",
                str(r["pressure"]),
            ]
        )

    if not data:
        return "No non-idle rows to display."

    widths = [len(h) for h in headers]
    for row in data:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def hline() -> str:
        return "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    out = [hline()]
    out.append("| " + " | ".join(headers[i].ljust(widths[i]) for i in range(len(headers))) + " |")
    out.append(hline())
    for row in data:
        out.append("| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(headers))) + " |")
    out.append(hline())
    return "\n".join(out)


def summarize(rows: List[Dict[str, float | str]]) -> str:
    if not rows:
        return "No data collected."

    max_util = max(float(r["util_pct"]) for r in rows)
    max_await = max(float(r["await_ms"]) for r in rows)
    max_q = max(float(r["avgqu_sz"]) for r in rows)

    high = any(str(r["pressure"]) == "HIGH" for r in rows)
    medium = any(str(r["pressure"]) == "MEDIUM" for r in rows)
    overall = "HIGH" if high else ("MEDIUM" if medium else "LOW")

    return (
        f"Overall I/O pressure: {overall} | "
        f"max util={max_util:.1f}% | "
        f"max await={max_await:.2f}ms | "
        f"max avgqu_sz={max_q:.2f}"
    )


def main() -> None:
    args = parse_args()
    if args.samples < 1:
        raise SystemExit("--samples must be >= 1")
    if args.interval <= 0:
        raise SystemExit("--interval must be > 0")

    devices = resolve_devices(args.devices)
    if not devices:
        raise SystemExit("No block devices found")

    print("Collecting VM I/O diagnostics...")
    print(f"Devices: {', '.join(devices)}")
    print(f"Samples: {args.samples}, Interval: {args.interval:.2f}s")
    print()

    all_rows: List[Dict[str, float | str]] = []
    for _ in range(args.samples):
        all_rows.extend(collect_sample(args.interval, devices))

    print(fmt_table(all_rows, hide_idle=args.hide_idle))
    print()
    print(summarize(all_rows))
    print("Thresholds: HIGH if util>=90% or await>=80ms or avgqu_sz>=4")


if __name__ == "__main__":
    main()
