"""Tests for record_parser.py"""
import pytest
from alt_analyzer.parser.record_parser import decode_record


class TestDecodeRecord:
    def test_valid_record(self):
        raw = bytes([0x01, 0x01, 0x60, 0x0E, 0x00, 0x00, 0x31, 0x01, 0x00, 0x00, 0x03, 0x02, 0x0C, 0x00])
        record = decode_record(raw)
        assert record is not None
        assert record.eeprom == "PASS"
        assert record.flash == "PASS"
        assert record.battery_mv == 3680
        assert record.battery_v == 3.680
        assert record.register_index == 305
        assert record.month == 3
        assert record.day == 2
        assert record.hour == 12
        assert record.iso == "2026-03-02T12:00:00"

    def test_eeprom_fail(self):
        raw = bytes([0x02, 0x01, 0x60, 0x0E, 0x00, 0x00, 0x31, 0x01, 0x00, 0x00, 0x03, 0x02, 0x0C, 0x00])
        record = decode_record(raw)
        assert record.eeprom == "FAIL"

    def test_flash_fail(self):
        raw = bytes([0x01, 0x02, 0x60, 0x0E, 0x00, 0x00, 0x31, 0x01, 0x00, 0x00, 0x03, 0x02, 0x0C, 0x00])
        record = decode_record(raw)
        assert record.flash == "FAIL"

    def test_all_zeros_returns_none(self):
        raw = bytes([0x00] * 14)
        assert decode_record(raw) is None

    def test_wrong_length_raises(self):
        with pytest.raises(ValueError):
            decode_record(bytes([0x01] * 10))

    def test_to_dict(self):
        raw = bytes([0x01, 0x01, 0x60, 0x0E, 0x00, 0x00, 0x31, 0x01, 0x00, 0x00, 0x03, 0x02, 0x0C, 0x00])
        record = decode_record(raw)
        d = record.to_dict()
        assert d["timestamp"] == "2026-03-02T12:00:00"
        assert d["eeprom"] == "PASS"
        assert d["flash"] == "PASS"
        assert d["battery_mv"] == 3680
        assert d["battery_v"] == 3.680
        assert d["register_index"] == 305

    def test_unknown_eeprom_value(self):
        raw = bytes([0xFF, 0x01, 0x60, 0x0E, 0x00, 0x00, 0x31, 0x01, 0x00, 0x00, 0x03, 0x02, 0x0C, 0x00])
        record = decode_record(raw)
        assert "UNKNOWN" in record.eeprom
