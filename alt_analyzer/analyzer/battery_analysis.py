"""Battery and register analytics for ALT device datasets.

Calculates:
    - Start/end/min/max/avg voltage
    - Voltage drop, daily loss rate, hourly loss rate
    - Register metrics (drift, unique values)
"""

from datetime import datetime, timedelta
from .device_schema import DeviceDataset


def compute_battery_metrics(dataset: DeviceDataset) -> dict:
    """Compute comprehensive battery metrics for a device."""
    if not dataset.records:
        return _empty_battery_metrics()

    valid = [r for r in dataset.records if r.timestamp is not None and r.battery_v > 0]
    if not valid:
        return _empty_battery_metrics()

    valid.sort(key=lambda r: r.timestamp)

    voltages = [r.battery_v for r in valid]
    millivolts = [r.battery_mv for r in valid]

    start_v = valid[0].battery_v
    end_v = valid[-1].battery_v
    min_v = min(voltages)
    max_v = max(voltages)
    avg_v = sum(voltages) / len(voltages)
    voltage_drop_mv = valid[0].battery_mv - valid[-1].battery_mv

    hours_span = _hours_between(valid[0].timestamp, valid[-1].timestamp)
    days_span = hours_span / 24.0 if hours_span else 0

    hourly_loss = voltage_drop_mv / hours_span if hours_span > 0 else 0
    daily_loss = hourly_loss * 24

    return {
        "start_voltage_v": round(start_v, 3),
        "end_voltage_v": round(end_v, 3),
        "min_voltage_v": round(min_v, 3),
        "max_voltage_v": round(max_v, 3),
        "avg_voltage_v": round(avg_v, 3),
        "voltage_drop_mv": voltage_drop_mv,
        "voltage_drop_v": round(voltage_drop_mv / 1000.0, 3),
        "duration_hours": hours_span,
        "duration_days": round(days_span, 1),
        "hourly_loss_mv": round(hourly_loss, 4),
        "daily_loss_mv": round(daily_loss, 2),
    }


def compute_register_metrics(dataset: DeviceDataset) -> dict:
    """Compute register stability metrics."""
    if not dataset.records:
        return _empty_register_metrics()

    values = dataset.register_values
    unique = sorted(set(values))

    return {
        "unique_values": unique,
        "unique_count": len(unique),
        "stable": len(unique) == 1,
        "base_value": values[0] if values else None,
        "drift_count": len(values) - values.count(values[0]) if values else 0,
    }


def compute_dataset_metrics(dataset: DeviceDataset) -> dict:
    """Compute overall dataset health metrics."""
    if not dataset.records:
        return _empty_dataset_metrics()

    valid_ts = [r for r in dataset.records if r.timestamp is not None]

    expected = 0
    if len(valid_ts) >= 2:
        valid_ts.sort(key=lambda r: r.timestamp)
        hours = _hours_between(valid_ts[0].timestamp, valid_ts[-1].timestamp)
        expected = hours + 1

    completeness = (len(dataset.records) / expected * 100) if expected > 0 else 0

    return {
        "total_records": dataset.record_count,
        "expected_records": expected,
        "missing_records": max(0, expected - dataset.record_count),
        "completeness_pct": round(completeness, 1),
        "eeprom_failures": dataset.eeprom_failures,
        "flash_failures": dataset.flash_failures,
    }


def compute_daily_voltages(dataset: DeviceDataset) -> list[dict]:
    """Compute daily average voltages for charting."""
    if not dataset.records:
        return []

    by_day: dict[str, list[float]] = {}
    for r in dataset.records:
        if r.timestamp is None:
            continue
        day_key = r.timestamp.strftime("%Y-%m-%d")
        by_day.setdefault(day_key, []).append(r.battery_v)

    return [
        {"date": day, "avg_voltage": round(sum(volts) / len(volts), 3),
         "min": round(min(volts), 3), "max": round(max(volts), 3)}
        for day, volts in sorted(by_day.items())
    ]


def _hours_between(start: datetime, end: datetime) -> int:
    return max(0, int((end - start).total_seconds() / 3600))


def _empty_battery_metrics() -> dict:
    return {k: None for k in [
        "start_voltage_v", "end_voltage_v", "min_voltage_v", "max_voltage_v",
        "avg_voltage_v", "voltage_drop_mv", "voltage_drop_v",
        "duration_hours", "duration_days", "hourly_loss_mv", "daily_loss_mv"
    ]}


def _empty_register_metrics() -> dict:
    return {"unique_values": [], "unique_count": 0, "stable": True,
            "base_value": None, "drift_count": 0}


def _empty_dataset_metrics() -> dict:
    return {"total_records": 0, "expected_records": 0, "missing_records": 0,
            "completeness_pct": 0, "eeprom_failures": 0, "flash_failures": 0}
