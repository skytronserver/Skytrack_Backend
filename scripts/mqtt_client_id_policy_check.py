#!/usr/bin/env python3
import argparse
import re
import subprocess
from collections import Counter


def run_journal(since: str, unit: str) -> str:
    cmd = [
        "sudo",
        "journalctl",
        "-u",
        unit,
        "--since",
        since,
        "--no-pager",
    ]
    return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check duplicate MQTT client_id churn from mosquitto logs")
    parser.add_argument("--since", default="2 hours ago")
    parser.add_argument("--unit", default="mosquitto")
    parser.add_argument("--top", type=int, default=30)
    args = parser.parse_args()

    try:
        logs = run_journal(args.since, args.unit)
    except subprocess.CalledProcessError as exc:
        print(exc.output)
        return 1

    dup_pattern = re.compile(r"Client\s+([^\s]+)\s+already connected, closing old connection")
    eof_pattern = re.compile(r"unexpected eof while reading", re.IGNORECASE)

    dup_ids = dup_pattern.findall(logs)
    dup_counter = Counter(dup_ids)

    eof_count = len(eof_pattern.findall(logs))

    print(f"[info] unit={args.unit} since={args.since}")
    print(f"[info] duplicate-client events={sum(dup_counter.values())}")
    print(f"[info] unique duplicate client_ids={len(dup_counter)}")
    print(f"[info] tls unexpected-eof events={eof_count}")

    print("\nTop duplicate client_ids:")
    for cid, cnt in dup_counter.most_common(args.top):
        print(f"{cnt:6d}  {cid}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
