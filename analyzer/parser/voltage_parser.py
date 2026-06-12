"""Decode 4-byte little-endian battery voltage fields.

Voltage format: 4-byte little-endian integer (millivolts)
Example: 60 0E 00 00 -> 0E60 -> 3680 mV -> 3.680 V
"""

import struct


def decode_voltage(voltage_bytes: bytes) -> dict:
    """Decode 4-byte little-endian battery voltage.

    Args:
        voltage_bytes: 4 bytes in little-endian order

    Returns:
        dict with millivolts and volts
    """
    if len(voltage_bytes) != 4:
        raise ValueError(f"Voltage must be 4 bytes, got {len(voltage_bytes)}")

    millivolts = struct.unpack("<I", voltage_bytes)[0]
    volts = millivolts / 1000.0

    return {
        "millivolts": millivolts,
        "volts": round(volts, 3),
    }


def is_valid_voltage(voltage_bytes: bytes, max_mv: int = 5000) -> bool:
    """Check if voltage value is within reasonable range for a battery."""
    if len(voltage_bytes) != 4:
        return False
    millivolts = struct.unpack("<I", voltage_bytes)[0]
    return 0 < millivolts <= max_mv
