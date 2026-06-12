"""CSV export for ALT device datasets.

Exports decoded records and summary reports to CSV format.
"""

import csv
import io
from typing import Optional

from ..analysis.device_schema import DeviceDataset
from ..analysis.battery_analysis import (
    compute_battery_metrics,
    compute_dataset_metrics,
    compute_daily_voltages,
)
from ..analysis.validation_analysis import run_validations


def export_records_csv(dataset: DeviceDataset) -> str:
    """Export all decoded records for a device as CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "device_id", "timestamp", "month", "day", "hour",
        "eeprom", "flash", "battery_mv", "battery_v", "register_index"
    ])

    for r in dataset.records:
        writer.writerow([
            dataset.device_id,
            r.iso or "",
            r.month,
            r.day,
            r.hour,
            r.eeprom,
            r.flash,
            r.battery_mv,
            r.battery_v,
            r.register_index,
        ])

    return output.getvalue()


def export_summary_csv(datasets: list[DeviceDataset]) -> str:
    """Export per-device summary metrics as CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "device_id", "record_count", "start_time", "end_time",
        "start_voltage_v", "end_voltage_v", "min_voltage_v", "max_voltage_v",
        "avg_voltage_v", "voltage_drop_mv", "daily_loss_mv",
        "eeprom_failures", "flash_failures",
        "register_stable", "validation_errors", "validation_warnings",
    ])

    for ds in datasets:
        bm = compute_battery_metrics(ds)
        dm = compute_dataset_metrics(ds)
        vr = run_validations(ds)

        writer.writerow([
            ds.device_id,
            ds.record_count,
            ds.start_time.isoformat() if ds.start_time else "",
            ds.end_time.isoformat() if ds.end_time else "",
            bm.get("start_voltage_v", ""),
            bm.get("end_voltage_v", ""),
            bm.get("min_voltage_v", ""),
            bm.get("max_voltage_v", ""),
            bm.get("avg_voltage_v", ""),
            bm.get("voltage_drop_mv", ""),
            bm.get("daily_loss_mv", ""),
            dm.get("eeprom_failures", ""),
            dm.get("flash_failures", ""),
            len(set(ds.register_values)) == 1,
            len(vr.errors),
            len(vr.warnings),
        ])

    return output.getvalue()


def export_daily_csv(dataset: DeviceDataset) -> str:
    """Export daily average voltages as CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["device_id", "date", "avg_voltage_v", "min_v", "max_v"])

    daily = compute_daily_voltages(dataset)
    for d in daily:
        writer.writerow([
            dataset.device_id,
            d["date"],
            d["avg_voltage"],
            d["min"],
            d["max"],
        ])

    return output.getvalue()


def export_voltage_chart_csv(dataset: DeviceDataset) -> str:
    """Export the plot points from the Voltage vs Time chart as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "voltage_v"])
    records = [r for r in dataset.records if r.timestamp is not None and r.battery_v > 0]
    records.sort(key=lambda r: r.timestamp)
    for r in records:
        writer.writerow([r.iso or "", r.battery_v])
    return output.getvalue()


def export_decay_trend_csv(dataset: DeviceDataset) -> str:
    """Export the plot points from the Voltage Decay Trend chart as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "voltage_v", "hours_elapsed", "trend_voltage_v"])
    records = [r for r in dataset.records if r.timestamp is not None and r.battery_v > 0]
    records.sort(key=lambda r: r.timestamp)
    import numpy as np
    x = [(r.timestamp - records[0].timestamp).total_seconds() / 3600.0 for r in records]
    y = [r.battery_v for r in records]
    coeffs = np.polyfit(x, y, 1)
    trend = np.poly1d(coeffs)
    for i, r in enumerate(records):
        writer.writerow([r.iso or "", r.battery_v, round(x[i], 4), round(trend(x[i]), 4)])
    return output.getvalue()


def export_daily_avg_chart_csv(dataset: DeviceDataset) -> str:
    """Export the plot points from the Daily Average Voltage chart as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "avg_voltage_v", "min_voltage_v", "max_voltage_v"])
    for d in compute_daily_voltages(dataset):
        writer.writerow([d["date"], d["avg_voltage"], d["min"], d["max"]])
    return output.getvalue()


def export_register_chart_csv(dataset: DeviceDataset) -> str:
    """Export the plot points from the Register Index chart as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "register_index"])
    records = [r for r in dataset.records if r.timestamp is not None]
    records.sort(key=lambda r: r.timestamp)
    for r in records:
        writer.writerow([r.iso or "", r.register_index])
    return output.getvalue()


def write_file(content: str, filepath: str) -> None:
    """Write CSV content to a file."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        f.write(content)
