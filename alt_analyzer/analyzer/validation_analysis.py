"""Automatic validation checks for ALT device datasets.

Checks:
    - EEPROM/Flash failures
    - Register stability
    - Missing records (expected 24/day)
    - Battery sanity (impossible values, sudden jumps)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from .device_schema import DeviceDataset


@dataclass
class ValidationIssue:
    """A single validation finding."""
    severity: str  
    category: str  
    message: str
    timestamp: Optional[str] = None
    value: Optional[str] = None


@dataclass
class ValidationReport:
    device_id: str
    issues: list[ValidationIssue] = field(default_factory=list)

    def add(self, severity: str, category: str, message: str,
            timestamp: Optional[str] = None, value: Optional[str] = None):
        self.issues.append(ValidationIssue(severity, category, message, timestamp, value))

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def is_healthy(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> dict:
        return {
            "device_id": self.device_id,
            "total_issues": len(self.issues),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "healthy": self.is_healthy,
            "issues": [
                {"severity": i.severity, "category": i.category, "message": i.message,
                 "timestamp": i.timestamp, "value": i.value}
                for i in self.issues
            ]
        }


def validate_eeprom_flash(dataset: DeviceDataset) -> list[ValidationIssue]:
    issues = []
    for r in dataset.records:
        if r.eeprom == "FAIL":
            issues.append(ValidationIssue(
                "error", "eeprom",
                f"EEPROM FAIL at {r.iso}",
                timestamp=r.iso
            ))
        if r.flash == "FAIL":
            issues.append(ValidationIssue(
                "error", "flash",
                f"Flash FAIL at {r.iso}",
                timestamp=r.iso
            ))
    return issues


def validate_register_stability(dataset: DeviceDataset) -> list[ValidationIssue]:
    issues = []
    if not dataset.records:
        return issues

    registers = [(r.register_index, r.iso) for r in dataset.records]
    unique = sorted(set(r for r, _ in registers))

    if len(unique) > 1:
        for reg_val, iso in registers:
            if reg_val != registers[0][0]:
                issues.append(ValidationIssue(
                    "error", "register",
                    f"Register value changed: {registers[0][0]} -> {reg_val} at {iso}",
                    timestamp=iso, value=str(reg_val)
                ))
    return issues


def validate_missing_records(dataset: DeviceDataset) -> list[ValidationIssue]:
    issues = []
    if not dataset.records:
        return issues

    valid = [r for r in dataset.records if r.timestamp is not None]
    if not valid:
        return issues

    valid.sort(key=lambda r: r.timestamp)
    seen = set()

    for r in valid:
        key = (r.timestamp.year, r.month, r.day, r.hour)
        seen.add(key)

    expected_hours = 0
    start = valid[0].timestamp
    end = valid[-1].timestamp

    current = start
    while current <= end:
        expected_hours += 1
        current += timedelta(hours=1)

    missing = expected_hours - len(seen)
    if missing > 0:
        issues.append(ValidationIssue(
            "warning" if missing < 10 else "error",
            "completeness",
            f"Data completeness: {len(seen)} out of {expected_hours} expected hourly records "
            f"({100 * len(seen) / expected_hours:.1f}%) — {missing} missing"
        ))

    return issues


def validate_battery_sanity(dataset: DeviceDataset) -> list[ValidationIssue]:
    issues = []
    if not dataset.records:
        return issues

    valid = [r for r in dataset.records if r.timestamp is not None]
    valid.sort(key=lambda r: r.timestamp)

    for r in dataset.records:
        if r.battery_mv <= 0 or r.battery_mv > 4500:
            issues.append(ValidationIssue(
                "error", "battery_sanity",
                f"Impossible voltage: {r.battery_mv}mV at {r.iso}",
                timestamp=r.iso, value=str(r.battery_mv)
            ))

    for i in range(1, len(valid)):
        prev = valid[i - 1]
        curr = valid[i]
        drop = prev.battery_mv - curr.battery_mv
        if drop > 100:
            issues.append(ValidationIssue(
                "warning", "battery_drop",
                f"Sudden voltage drop: {prev.battery_v:.3f}V -> {curr.battery_v:.3f}V "
                f"({drop}mV) at {curr.iso}",
                timestamp=curr.iso, value=str(drop)
            ))

    return issues


def run_validations(dataset: DeviceDataset) -> ValidationReport:
    report = ValidationReport(device_id=dataset.device_id)
    report.issues.extend(validate_eeprom_flash(dataset))
    report.issues.extend(validate_register_stability(dataset))
    report.issues.extend(validate_missing_records(dataset))
    report.issues.extend(validate_battery_sanity(dataset))
    return report
