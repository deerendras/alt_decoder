"""CLI entry point for the ALT Log Analyzer.

Usage:
    python -m alt_analyzer.decode sample_data/
    python -m alt_analyzer.decode sample_data/300001_10.txt sample_data/300001_20.txt
    python -m alt_analyzer.decode sample_data/ --csv report.csv
"""

import argparse
import csv
import json
import sys
from pathlib import Path

from alt_analyzer.parser.file_discovery import discover_files, group_files, parse_filename
from alt_analyzer.analyzer.timeline_builder import build_all_timelines


def main():
    parser = argparse.ArgumentParser(
        description="Decode Honeywell V200HL ALT log files into structured records."
    )
    parser.add_argument(
        "input", nargs="+",
        help="ALT log file(s) or a directory containing them"
    )
    parser.add_argument("--csv", help="Export all records to CSV file")
    parser.add_argument("--json", help="Export all records to JSON file")
    parser.add_argument("--summary", action="store_true", help="Print summary only")

    args = parser.parse_args()

    paths = [Path(p) for p in args.input]
    devices = {}

    for p in paths:
        if p.is_dir():
            found = discover_files(str(p))
            for dev_id, files in found.items():
                devices.setdefault(dev_id, []).extend(files)
        elif p.is_file():
            info = parse_filename(str(p))
            if info is None:
                print(f"Warning: '{p.name}' doesn't match expected pattern, skipping",
                      file=sys.stderr)
                continue
            devices.setdefault(info.device_id, []).append(info)
        else:
            print(f"Warning: '{p}' not found, skipping", file=sys.stderr)

    if not devices:
        print("Error: No valid ALT log files found.", file=sys.stderr)
        sys.exit(1)

    datasets = build_all_timelines(devices)

    all_records = []

    for ds in datasets:
        all_records.extend(ds.records)

        print(f"\n=== Device {ds.device_id} ({ds.record_count} records) ===")
        print(f"  Files: {', '.join(ds.source_files)}")
        print(f"  Timeline: {ds.start_time} -> {ds.end_time}")
        vr = ds.voltage_range
        print(f"  Voltage: {vr[0]:.3f}V - {vr[1]:.3f}V  |  Avg: {ds.avg_voltage:.3f}V")

        failures = []
        if ds.eeprom_failures:
            failures.append(f"EEPROM={ds.eeprom_failures}")
        if ds.flash_failures:
            failures.append(f"Flash={ds.flash_failures}")
        if failures:
            print(f"  Failures: {', '.join(failures)}")

        registers = set(ds.register_values)
        if len(registers) > 1:
            print(f"  WARNING: Register drift detected ({len(registers)} unique values): "
                  f"{sorted(registers)}")

        if not args.summary:
            print()
            for r in ds.records[:5]:
                print(
                    f"  {r.iso:25s}  EEPROM={r.eeprom:5s}  FLASH={r.flash:5s}  "
                    f"Battery={r.battery_v:5.3f}V  Register={r.register_index}"
                )
            if len(ds.records) > 5:
                print(f"  ... and {len(ds.records) - 5} more records")

    if args.csv and all_records:
        with open(args.csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "device_id", "timestamp", "eeprom", "flash", "battery_mv",
                "battery_v", "register_index"
            ])
            writer.writeheader()
            for ds in datasets:
                for r in ds.records:
                    row = r.to_dict()
                    row["device_id"] = ds.device_id
                    writer.writerow(row)
        print(f"\nExported to {args.csv}")

    if args.json and all_records:
        output = {ds.device_id: ds.summary() for ds in datasets}
        output["_records"] = []
        for ds in datasets:
            for r in ds.records:
                rec = r.to_dict()
                rec["device_id"] = ds.device_id
                output["_records"].append(rec)
        with open(args.json, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\nExported to {args.json}")


if __name__ == "__main__":
    main()
