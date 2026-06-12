"""Tests for timestamp_parser.py"""
import pytest
from analyzer.parser.timestamp_parser import decode_timestamp, is_valid_timestamp


class TestDecodeTimestamp:
    def test_valid_timestamp(self):
        result = decode_timestamp(bytes([0x03, 0x02, 0x0C, 0x00]))
        assert result["month"] == 3
        assert result["day"] == 2
        assert result["hour"] == 12
        assert result["reserved"] == 0
        assert result["iso"] == "2026-03-02T12:00:00"

    def test_midnight(self):
        result = decode_timestamp(bytes([0x03, 0x01, 0x00, 0x00]))
        assert result["hour"] == 0
        assert result["iso"] == "2026-03-01T00:00:00"

    def test_last_hour(self):
        result = decode_timestamp(bytes([0x03, 0x01, 0x17, 0x00]))
        assert result["hour"] == 23
        assert result["iso"] == "2026-03-01T23:00:00"

    def test_invalid_month_zero(self):
        result = decode_timestamp(bytes([0x00, 0x01, 0x0C, 0x00]))
        assert result["datetime"] is None

    def test_invalid_hour(self):
        result = decode_timestamp(bytes([0x03, 0x01, 0xFF, 0x00]))
        assert result["datetime"] is None

    def test_wrong_length_raises(self):
        with pytest.raises(ValueError):
            decode_timestamp(bytes([0x03, 0x02, 0x0C]))


class TestIsValidTimestamp:
    def test_valid(self):
        assert is_valid_timestamp(bytes([0x03, 0x02, 0x0C, 0x00]))

    def test_invalid_month(self):
        assert not is_valid_timestamp(bytes([0x0D, 0x02, 0x0C, 0x00]))

    def test_invalid_hour(self):
        assert not is_valid_timestamp(bytes([0x03, 0x02, 0x18, 0x00]))

    def test_wrong_length(self):
        assert not is_valid_timestamp(bytes([0x03, 0x02]))
