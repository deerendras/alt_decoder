"""Decode 14-byte ALT records into structured output.

Record structure (14 bytes):
    Bytes 0-0:  EEPROM Validation (01=PASS, 02=FAIL)
    Bytes 1-1:  Flash Validation  (01=PASS, 02=FAIL)
    Bytes 2-5:  Battery Voltage (4-byte little-endian, millivolts)
    Bytes 6-9:  Register Index (4-byte little-endian)
    Bytes 10-13: Timestamp (Month, Day, Hour, Reserved)
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from .packet_parser import parse_packet, split_records, hex_to_bytes
from .timestamp_parser import decode_timestamp, is_valid_timestamp
from .voltage_parser import decode_voltage, is_valid_voltage

RECORD_SIZE = 14
MAX_REGISTER_INDEX = 0xFFFF


@dataclass
class DecodedRecord:
    """A fully decoded ALT record."""
    timestamp: Optional[datetime] = None
    iso: Optional[str] = None
    month: int = 0
    day: int = 0
    hour: int = 0
    eeprom: str = ""
    flash: str = ""
    battery_mv: int = 0
    battery_v: float = 0.0
    register_index: int = 0
    raw_hex: str = ""
    source_line: int = 0
    page: int = 0
    record_index: int = 0

    _EEPROM_MAP = {0x01: "PASS", 0x02: "FAIL"}
    _FLASH_MAP = {0x01: "PASS", 0x02: "FAIL"}

    def to_dict(self) -> dict:
        return {
            "timestamp": self.iso,
            "eeprom": self.eeprom,
            "flash": self.flash,
            "battery_mv": self.battery_mv,
            "battery_v": self.battery_v,
            "register_index": self.register_index,
        }


def decode_record(raw: bytes) -> Optional[DecodedRecord]:
    """Decode a single 14-byte record.

    Returns None if the record is all zeros (empty/corrupt page).
    """
    if len(raw) != RECORD_SIZE:
        raise ValueError(f"Record must be {RECORD_SIZE} bytes, got {len(raw)}")

    if raw == b"\x00" * RECORD_SIZE:
        return None

    from .voltage_parser import is_valid_voltage
    from .timestamp_parser import is_valid_timestamp

    if not is_valid_voltage(raw[2:6]):
        return None

    if not is_valid_timestamp(raw[10:14]):
        return None

    record = DecodedRecord()
    record.raw_hex = raw.hex(" ").upper()

    eeprom_byte = raw[0]
    flash_byte = raw[1]

    record.eeprom = DecodedRecord._EEPROM_MAP.get(eeprom_byte, f"UNKNOWN({eeprom_byte:02X})")
    record.flash = DecodedRecord._FLASH_MAP.get(flash_byte, f"UNKNOWN({flash_byte:02X})")

    voltage_result = decode_voltage(raw[2:6])
    record.battery_mv = voltage_result["millivolts"]
    record.battery_v = voltage_result["volts"]

    register_bytes = raw[6:10]
    import struct
    record.register_index = struct.unpack("<I", register_bytes)[0]
    if record.register_index > MAX_REGISTER_INDEX:
        return None

    ts_result = decode_timestamp(raw[10:14])
    record.month = ts_result["month"]
    record.day = ts_result["day"]
    record.hour = ts_result["hour"]
    record.timestamp = ts_result["datetime"]
    record.iso = ts_result["iso"]

    return record


def decode_file(filepath: str) -> list[DecodedRecord]:
    """Parse an ALT log file and return all decoded records.

    Args:
        filepath: Path to the log file

    Returns:
        List of DecodedRecord objects, ordered by appearance in the file.
    """
    fp = Path(filepath)
    if not fp.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    if not fp.is_file():
        raise IsADirectoryError(f"Expected a file, got directory: {filepath}")
    if fp.stat().st_size == 0:
        raise ValueError(f"File is empty: {filepath}")

    records = []

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        return records

    for line_num, line in enumerate(lines, start=1):
        packet = parse_packet(line, line_num)
        if packet is None:
            continue

        if 0xC0 <= packet.page <= 0xCF or packet.page == 0xFC:
            continue

        raw_records = split_records(packet)
        for idx, raw in enumerate(raw_records):
            decoded = decode_record(raw)
            if decoded is not None:
                decoded.source_line = line_num
                decoded.page = packet.page
                decoded.record_index = idx
                records.append(decoded)

    return records
