"""Unified data structure representing a single device's full ALT dataset."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..parser.record_parser import DecodedRecord


@dataclass
class DeviceDataset:
    """Complete dataset for one device across all uploaded files.

    Records are stored chronologically sorted with duplicates removed.
    """
    device_id: str
    records: list[DecodedRecord] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)

    @property
    def start_time(self) -> Optional[datetime]:
        if not self.records:
            return None
        valid = [r.timestamp for r in self.records if r.timestamp is not None]
        return min(valid) if valid else None

    @property
    def end_time(self) -> Optional[datetime]:
        if not self.records:
            return None
        valid = [r.timestamp for r in self.records if r.timestamp is not None]
        return max(valid) if valid else None

    @property
    def record_count(self) -> int:
        return len(self.records)

    @property
    def voltage_range(self) -> tuple[float, float]:
        voltages = [r.battery_v for r in self.records]
        return (min(voltages), max(voltages))

    @property
    def avg_voltage(self) -> float:
        voltages = [r.battery_v for r in self.records]
        return sum(voltages) / len(voltages) if voltages else 0.0

    @property
    def eeprom_failures(self) -> int:
        return sum(1 for r in self.records if r.eeprom == "FAIL")

    @property
    def flash_failures(self) -> int:
        return sum(1 for r in self.records if r.flash == "FAIL")

    @property
    def register_values(self) -> list[int]:
        return [r.register_index for r in self.records]

    def summary(self) -> dict:
        return {
            "device_id": self.device_id,
            "record_count": self.record_count,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "voltage_range": self.voltage_range,
            "avg_voltage": round(self.avg_voltage, 3),
            "eeprom_failures": self.eeprom_failures,
            "flash_failures": self.flash_failures,
            "unique_registers": len(set(self.register_values)),
            "source_files": self.source_files,
        }
