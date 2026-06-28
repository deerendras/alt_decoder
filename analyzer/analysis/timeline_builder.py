"""Merge decoded records from multiple files into a chronologically sorted,
deduplicated device timeline.

The timestamp is authoritative — never trust filename ordering alone.
"""

from .device_schema import DeviceDataset
from ..parser.file_discovery import FileInfo
from ..parser.record_parser import decode_file, DecodedRecord


def _record_key(record: DecodedRecord) -> tuple:
    """Sort key: timestamp descending to None at end, then source_line."""
    if record.timestamp is None:
        return (1, "", 0, 0)  
    return (0, record.iso or "", record.source_line, record.record_index)


def build_timeline(file_infos: list[FileInfo], device_id: str) -> DeviceDataset:
    """Decode all files for a device and produce a merged, sorted timeline.

    Deduplication: records with the same (month, day, hour) are de-duplicated,
    keeping the first occurrence (earliest file/line).

    Args:
        file_infos: List of FileInfo objects for one device
        device_id: The device identifier

    Returns:
        DeviceDataset with records sorted chronologically
    """
    dataset = DeviceDataset(device_id=device_id)

    all_records: list[DecodedRecord] = []
    seen_files: list[str] = []

    for fi in file_infos:
        records = decode_file(str(fi.path))
        all_records.extend(records)
        seen_files.append(fi.name)

    all_records.sort(key=_record_key)

    deduped: list[DecodedRecord] = []
    seen_timestamps: dict[tuple[int, int, int], int] = {}

    for r in all_records:
        key = (r.month, r.day, r.hour)
        if key in seen_timestamps:
            existing_idx = seen_timestamps[key]
            existing = deduped[existing_idx]
            if (r.eeprom != "PASS" and r.eeprom != existing.eeprom) or \
               (r.flash != "PASS" and r.flash != existing.flash):
                deduped[existing_idx] = r
            continue
        seen_timestamps[key] = len(deduped)
        deduped.append(r)

    dataset.records = deduped
    dataset.source_files = seen_files

    return dataset


def build_all_timelines(
    devices: dict[str, list[FileInfo]]
) -> list[DeviceDataset]:
    """Build timelines for all discovered devices.

    Args:
        devices: Dict mapping device_id -> list of FileInfo

    Returns:
        List of DeviceDataset, one per device
    """
    datasets = []
    for device_id, file_infos in devices.items():
        dataset = build_timeline(file_infos, device_id)
        datasets.append(dataset)
    return datasets
