"""Decode 4-byte timestamp fields from ALT records.

Timestamp format: Month Day Hour Reserved
Example: 03 02 0C 00 -> March 2, 12:00
"""

from datetime import datetime


def decode_timestamp(timestamp_bytes: bytes) -> dict:
    """Decode a 4-byte timestamp into structured fields.

    Args:
        timestamp_bytes: 4 bytes [Month, Day, Hour, Reserved]

    Returns:
        dict with month, day, hour, reserved, and iso datetime string
    """
    if len(timestamp_bytes) != 4:
        raise ValueError(f"Timestamp must be 4 bytes, got {len(timestamp_bytes)}")

    month = timestamp_bytes[0]
    day = timestamp_bytes[1]
    hour = timestamp_bytes[2]
    reserved = timestamp_bytes[3]

    dt = None
    iso_string = None

    if 1 <= month <= 12 and 1 <= day <= 31 and 0 <= hour <= 23:
        try:
            dt = datetime(2026, month, day, hour)
            iso_string = dt.isoformat()
        except ValueError:
            iso_string = f"2026-{month:02d}-{day:02d}T{hour:02d}:00:00(invalid)"

    return {
        "month": month,
        "day": day,
        "hour": hour,
        "reserved": reserved,
        "datetime": dt,
        "iso": iso_string,
    }


def is_valid_timestamp(timestamp_bytes: bytes) -> bool:
    """Check if 4 bytes represent a valid timestamp."""
    if len(timestamp_bytes) != 4:
        return False
    month = timestamp_bytes[0]
    day = timestamp_bytes[1]
    hour = timestamp_bytes[2]
    return 1 <= month <= 12 and 1 <= day <= 31 and 0 <= hour <= 23
