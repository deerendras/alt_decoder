"""Extract 14-byte ALT records from raw log file lines.

Each ReadALTTestLog line contains:
- Packet header: 4F A9 BB XX (4 bytes)
- N records of 14 bytes each
- Packet footer: CC 0D (2 bytes)

This module strips the header/footer and splits records at exact 14-byte boundaries.
"""

from dataclasses import dataclass
from typing import Optional


HEADER = bytes([0x4F, 0xA9])
FOOTER = bytes([0xCC, 0x0D])
RECORD_SIZE = 14
HEADER_SIZE = 4
FOOTER_SIZE = 2


@dataclass
class Packet:
    """A parsed ReadALTTestLog packet."""
    page: int
    raw_data: bytes
    source_line: int


def hex_to_bytes(hex_string: str) -> bytes:
    """Convert space-separated hex string to bytes."""
    hex_parts = hex_string.strip().split()
    return bytes.fromhex("".join(hex_parts))


def extract_hex_output(line: str) -> Optional[str]:
    """Extract hex Output field from a log line.

    Returns the hex string after 'Output: ' or None if not found.
    """
    marker = "Output: "
    idx = line.find(marker)
    if idx == -1:
        return None
    return line[idx + len(marker):].strip()


def parse_packet(line: str, line_number: int) -> Optional[Packet]:
    """Parse a single log line into a Packet.

    Only processes ReadALTTestLog lines. Skips StopALTREDTest lines and headers.

    Returns None for lines that don't contain valid records.
    """
    if "ReadALTTestLog" not in line:
        return None

    hex_str = extract_hex_output(line)
    if not hex_str:
        return None

    raw = hex_to_bytes(hex_str)

    # Need at minimum header + footer
    if len(raw) < HEADER_SIZE + FOOTER_SIZE:
        return None

    # Validate header magic bytes
    if raw[:2] != HEADER:
        return None

    # Validate command byte (must be 0xBB for ReadALTTestLog)
    if raw[2] != 0xBB:
        return None

    # Extract page from header (byte 3, after 4F A9 BB)
    page = raw[3]

    # Strip header and footer
    payload = raw[HEADER_SIZE:len(raw) - FOOTER_SIZE]

    return Packet(page=page, raw_data=payload, source_line=line_number)


def split_records(packet: Packet) -> list[bytes]:
    """Split packet payload into 14-byte records.

    Only returns complete records. Any trailing bytes that don't form a full
    14-byte record are discarded.
    """
    records = []
    data = packet.raw_data

    for i in range(0, len(data) - RECORD_SIZE + 1, RECORD_SIZE):
        record = data[i:i + RECORD_SIZE]
        records.append(record)

    return records
