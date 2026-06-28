"""Tests for timeline_builder.py — especially corruption-preserving dedup."""
import pytest
from pathlib import Path
from analyzer.analysis.timeline_builder import build_timeline
from analyzer.parser.file_discovery import FileInfo
import analyzer.analysis.timeline_builder as tb_module


def _make_record(month=3, day=2, hour=12, eeprom="PASS", flash="PASS",
                 battery_mv=3680, register_index=305, iso=None):
    from analyzer.parser.record_parser import DecodedRecord
    from datetime import datetime
    r = DecodedRecord()
    r.month = month
    r.day = day
    r.hour = hour
    r.eeprom = eeprom
    r.flash = flash
    r.battery_mv = battery_mv
    r.register_index = register_index
    if iso:
        r.iso = iso
        r.timestamp = datetime.fromisoformat(iso)
    return r


def _make_file_info(name, path=None):
    if path is None:
        path = Path(f"sample_data/{name}")
    return FileInfo(path=path, device_id="300001", segment=10, name=name)


class TestCorruptionPreservingDedup:
    """When duplicate timestamps exist, corruption must not be lost."""

    def test_corrupt_eeprom_on_duplicate_replaces_clean(self, monkeypatch):
        """Duplicate timestamp: second record has corrupt EEPROM -> keep corrupt."""
        r1 = _make_record(month=3, day=2, hour=12, eeprom="PASS", flash="PASS",
                          iso="2026-03-02T12:00:00")
        r2 = _make_record(month=3, day=2, hour=12, eeprom="UNKNOWN(09)", flash="PASS",
                          iso="2026-03-02T12:00:00")

        monkeypatch.setattr(tb_module, "decode_file", lambda fp: [r1, r2])

        fi = _make_file_info("300001_10.txt")
        ds = build_timeline([fi], "300001")
        assert len(ds.records) == 1
        assert ds.records[0].eeprom == "UNKNOWN(09)"
        assert ds.records[0].flash == "PASS"

    def test_corrupt_flash_on_duplicate_replaces_clean(self, monkeypatch):
        """Duplicate timestamp: second record has corrupt Flash -> keep corrupt."""
        r1 = _make_record(month=3, day=2, hour=12, eeprom="PASS", flash="PASS",
                          iso="2026-03-02T12:00:00")
        r2 = _make_record(month=3, day=2, hour=12, eeprom="PASS", flash="UNKNOWN(FF)",
                          iso="2026-03-02T12:00:00")

        monkeypatch.setattr(tb_module, "decode_file", lambda fp: [r1, r2])

        fi = _make_file_info("300001_10.txt")
        ds = build_timeline([fi], "300001")
        assert len(ds.records) == 1
        assert ds.records[0].eeprom == "PASS"
        assert ds.records[0].flash == "UNKNOWN(FF)"

    def test_both_corrupt_on_duplicate_replaces_clean(self, monkeypatch):
        """Duplicate timestamp: second record has both corrupt -> keep both corrupt."""
        r1 = _make_record(month=3, day=2, hour=12, eeprom="PASS", flash="PASS",
                          iso="2026-03-02T12:00:00")
        r2 = _make_record(month=3, day=2, hour=12, eeprom="UNKNOWN(09)", flash="UNKNOWN(FF)",
                          iso="2026-03-02T12:00:00")

        monkeypatch.setattr(tb_module, "decode_file", lambda fp: [r1, r2])

        fi = _make_file_info("300001_10.txt")
        ds = build_timeline([fi], "300001")
        assert len(ds.records) == 1
        assert ds.records[0].eeprom == "UNKNOWN(09)"
        assert ds.records[0].flash == "UNKNOWN(FF)"

    def test_corrupt_first_then_clean_does_not_replace(self, monkeypatch):
        """If corrupt comes first, clean duplicate should not overwrite it."""
        r1 = _make_record(month=3, day=2, hour=12, eeprom="UNKNOWN(09)", flash="PASS",
                          iso="2026-03-02T12:00:00")
        r2 = _make_record(month=3, day=2, hour=12, eeprom="PASS", flash="PASS",
                          iso="2026-03-02T12:00:00")

        monkeypatch.setattr(tb_module, "decode_file", lambda fp: [r1, r2])

        fi = _make_file_info("300001_10.txt")
        ds = build_timeline([fi], "300001")
        assert len(ds.records) == 1
        assert ds.records[0].eeprom == "UNKNOWN(09)"

    def test_same_values_on_duplicate_no_change(self, monkeypatch):
        """Duplicate with same PASS values respects first-come."""
        r1 = _make_record(month=3, day=2, hour=12, eeprom="PASS", flash="PASS",
                          iso="2026-03-02T12:00:00", battery_mv=3680)
        r2 = _make_record(month=3, day=2, hour=12, eeprom="PASS", flash="PASS",
                          iso="2026-03-02T12:00:00", battery_mv=3700)

        monkeypatch.setattr(tb_module, "decode_file", lambda fp: [r1, r2])

        fi = _make_file_info("300001_10.txt")
        ds = build_timeline([fi], "300001")
        assert len(ds.records) == 1
        assert ds.records[0].battery_mv == 3680

    def test_same_corrupt_on_both_duplicates_no_unnecessary_replace(self, monkeypatch):
        """Both duplicates have same corruption -> keep first."""
        r1 = _make_record(month=3, day=2, hour=12, eeprom="UNKNOWN(09)", flash="PASS",
                          iso="2026-03-02T12:00:00", battery_mv=3680)
        r2 = _make_record(month=3, day=2, hour=12, eeprom="UNKNOWN(09)", flash="PASS",
                          iso="2026-03-02T12:00:00", battery_mv=3700)

        monkeypatch.setattr(tb_module, "decode_file", lambda fp: [r1, r2])

        fi = _make_file_info("300001_10.txt")
        ds = build_timeline([fi], "300001")
        assert len(ds.records) == 1
        assert ds.records[0].battery_mv == 3680
