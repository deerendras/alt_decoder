"""Parse ALT log filenames to extract device ID and file segment.

Expected patterns:
    300001_10.txt  -> device=300001, segment=10
    300001_20.txt  -> device=300001, segment=20
    300002_10.txt  -> device=300002, segment=10
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

FILENAME_PATTERN = re.compile(r"^(\d{6})_(\d{2})\.txt$", re.IGNORECASE)
MIN_SEGMENT = 0
MAX_SEGMENT = 99


@dataclass
class FileInfo:
    """Metadata extracted from an ALT log filename."""
    path: Path
    device_id: str
    segment: int
    name: str


def parse_filename(filepath: str) -> Optional[FileInfo]:
    """Extract device ID and segment number from a filename.

    Returns None if the filename doesn't match the expected pattern.
    """
    path = Path(filepath)
    match = FILENAME_PATTERN.match(path.name)
    if not match:
        return None

    segment = int(match.group(2))
    if not (MIN_SEGMENT <= segment <= MAX_SEGMENT):
        return None

    return FileInfo(
        path=path,
        device_id=match.group(1),
        segment=segment,
        name=path.name,
    )


def discover_files(directory: str) -> dict[str, list[FileInfo]]:
    """Scan a directory for ALT log files and group them by device ID.

    Args:
        directory: Path to directory containing log files

    Returns:
        Dict mapping device_id -> list of FileInfo objects
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    devices: dict[str, list[FileInfo]] = {}

    for filepath in sorted(dir_path.glob("*.txt")):
        info = parse_filename(str(filepath))
        if info is None:
            continue
        if filepath.stat().st_size == 0:
            continue

        if info.device_id not in devices:
            devices[info.device_id] = []
        devices[info.device_id].append(info)

    return devices


def group_files(filepaths: list[str]) -> dict[str, list[FileInfo]]:
    """Group explicit file paths by device ID.

    Args:
        filepaths: List of file paths to ALT log files

    Returns:
        Dict mapping device_id -> list of FileInfo objects
    """
    devices: dict[str, list[FileInfo]] = {}

    for fp in filepaths:
        path = Path(fp)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {fp}")
        if path.stat().st_size == 0:
            raise ValueError(f"File is empty: {fp}")

        info = parse_filename(fp)
        if info is None:
            raise ValueError(
                f"Filename '{fp}' does not match expected pattern: "
                f"DEVICEID_SEGMENT.txt (e.g. 300001_10.txt)"
            )

        if info.device_id not in devices:
            devices[info.device_id] = []
        devices[info.device_id].append(info)

    return devices
