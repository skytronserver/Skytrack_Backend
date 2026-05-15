#!/usr/bin/env python3
"""
Prints a table with IO load, RAM load, and CPU load.

Metrics per sample:
- CPU% (active CPU utilization)
- IOwait% (from /proc/stat)
- RAM% (used/total from /proc/meminfo)
- RAM Used/Total (GiB)
- Read KB/s (from /proc/diskstats)
- Write KB/s (from /proc/diskstats)
- Disk Busy% (time spent doing IO)

Usage:
  python3 scripts/system_load_table.py
  python3 scripts/system_load_table.py --samples 5 --interval 1
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import time
from typing import Dict, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print IO/RAM/CPU load table")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between samples")
    parser.add_argument("--samples", type=int, default=1, help="Number of samples")
    return parser.parse_args()


def read_proc_stat_cpu() -> Tuple[int, int, int]:
    # Returns (total_jiffies, idle_jiffies, iowait_jiffies)
    with open("/proc/stat", "r", encoding="utf-8") as f:
        first = f.readline().strip().split()
    if len(first) < 6 or first[0] != "cpu":
        raise RuntimeError("Unexpected /proc/stat format")

    values = [int(x) for x in first[1:]]
    total = sum(values)
    idle = values[3]  # idle
    iowait = values[4]  # iowait
    return total, idle, iowait


def list_physical_disks() -> List[str]:
    # Pick physical block devices only.
    devices: List[str] = []
    for name in os.listdir("/sys/block"):
        if name.startswith(("loop", "ram", "dm-", "md")):
            continue
        devices.append(name)
    return sorted(devices)


def read_diskstats(devices: List[str]) -> Tuple[int, int, int]:
    # Returns (sectors_read, sectors_written, io_ms)
    sectors_read = 0
    sectors_written = 0
    io_ms = 0

    wanted = set(devices)
    with open("/proc/diskstats", "r", encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 14:
                continue
            name = parts[2]
            if name not in wanted:
                continue
            sectors_read += int(parts[5])
            sectors_written += int(parts[9])
            io_ms += int(parts[12])

    return sectors_read, sectors_written, io_ms


def read_meminfo() -> Tuple[float, float, float]:
    # Returns (total_gib, used_gib, used_percent)
    mem = {}
    with open("/proc/meminfo", "r", encoding="utf-8") as f:
        for line in f:
            key, value = line.split(":", 1)
            mem[key] = int(value.strip().split()[0])  # kB

    total_kb = float(mem.get("MemTotal", 0))
    available_kb = float(mem.get("MemAvailable", 0))
    used_kb = max(total_kb - available_kb, 0.0)

    total_gib = total_kb / (1024.0 * 1024.0)
    used_gib = used_kb / (1024.0 * 1024.0)
    used_pct = (used_kb / total_kb * 100.0) if total_kb else 0.0
    return total_gib, used_gib, used_pct


def fmt_table(rows: List[Dict[str, float]]) -> str:
    headers = [
        "Time",
        "CPU%",
        "IOwait%",
        "RAM%",
        "RAM Used/Total (GiB)",
        "Read KB/s",
        "Write KB/s",
        "Disk Busy%",
    ]

    data = []
    for r in rows:
        data.append(
            [
                r["time"],
                f"{r['cpu']:.1f}",
                f"{r['iowait']:.1f}",
                f"{r['ram_pct']:.1f}",
                f"{r['ram_used']:.2f}/{r['ram_total']:.2f}",
                f"{r['read_kbs']:.1f}",
                f"{r['write_kbs']:.1f}",
                f"{r['disk_busy']:.1f}",
            ]
        )

    widths = [len(h) for h in headers]
    for row in data:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def hline(sep: str = "+", fill: str = "-") -> str:
        return sep + sep.join(fill * (w + 2) for w in widths) + sep

    out = [hline()]
    out.append("| " + " | ".join(headers[i].ljust(widths[i]) for i in range(len(headers))) + " |")
    out.append(hline())
    for row in data:
        out.append("| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(headers))) + " |")
    out.append(hline())
    return "\n".join(out)


def average_rows(rows: List[Dict[str, float]]) -> Dict[str, float]:
    n = len(rows)
    if n == 0:
        raise ValueError("No rows to average")
    return {
        "time": "AVG",
        "cpu": sum(r["cpu"] for r in rows) / n,
        "iowait": sum(r["iowait"] for r in rows) / n,
        "ram_pct": sum(r["ram_pct"] for r in rows) / n,
        "ram_used": sum(r["ram_used"] for r in rows) / n,
        "ram_total": sum(r["ram_total"] for r in rows) / n,
        "read_kbs": sum(r["read_kbs"] for r in rows) / n,
        "write_kbs": sum(r["write_kbs"] for r in rows) / n,
        "disk_busy": sum(r["disk_busy"] for r in rows) / n,
    }


def collect_sample(interval: float, devices: List[str]) -> Dict[str, float]:
    c1_total, c1_idle, c1_iowait = read_proc_stat_cpu()
    d1_read, d1_write, d1_io_ms = read_diskstats(devices)
    time.sleep(interval)
    c2_total, c2_idle, c2_iowait = read_proc_stat_cpu()
    d2_read, d2_write, d2_io_ms = read_diskstats(devices)

    total_delta = max(c2_total - c1_total, 1)
    idle_delta = max(c2_idle - c1_idle, 0)
    iowait_delta = max(c2_iowait - c1_iowait, 0)

    cpu_pct = max((total_delta - idle_delta) / total_delta * 100.0, 0.0)
    iowait_pct = max(iowait_delta / total_delta * 100.0, 0.0)

    read_delta_sectors = max(d2_read - d1_read, 0)
    write_delta_sectors = max(d2_write - d1_write, 0)
    # Linux sectors are 512 bytes.
    read_kbs = (read_delta_sectors * 512.0 / 1024.0) / interval
    write_kbs = (write_delta_sectors * 512.0 / 1024.0) / interval

    io_ms_delta = max(d2_io_ms - d1_io_ms, 0)
    disk_busy_pct = min((io_ms_delta / (interval * 1000.0)) * 100.0, 100.0)

    ram_total, ram_used, ram_pct = read_meminfo()

    return {
        "time": dt.datetime.now().strftime("%H:%M:%S"),
        "cpu": cpu_pct,
        "iowait": iowait_pct,
        "ram_pct": ram_pct,
        "ram_used": ram_used,
        "ram_total": ram_total,
        "read_kbs": read_kbs,
        "write_kbs": write_kbs,
        "disk_busy": disk_busy_pct,
    }


def main() -> None:
    args = parse_args()
    if args.samples < 1:
        raise SystemExit("--samples must be >= 1")
    if args.interval <= 0:
        raise SystemExit("--interval must be > 0")

    devices = list_physical_disks()
    if not devices:
        raise SystemExit("No physical disk devices found under /sys/block")

    print("Collecting system load samples...")
    print(f"Devices: {', '.join(devices)}")
    print(f"Samples: {args.samples}, Interval: {args.interval:.2f}s")
    print()

    rows: List[Dict[str, float]] = []
    for _ in range(args.samples):
        rows.append(collect_sample(args.interval, devices))

    display_rows = rows[:]
    if len(rows) > 1:
        display_rows.append(average_rows(rows))

    print(fmt_table(display_rows))


if __name__ == "__main__":
    main()
