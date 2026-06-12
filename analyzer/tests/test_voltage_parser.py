"""Tests for voltage_parser.py"""
import pytest
from analyzer.parser.voltage_parser import decode_voltage, is_valid_voltage


class TestDecodeVoltage:
    def test_3680mv(self):
        result = decode_voltage(bytes([0x60, 0x0E, 0x00, 0x00]))
        assert result["millivolts"] == 3680
        assert result["volts"] == 3.680

    def test_3600mv(self):
        result = decode_voltage(bytes([0x10, 0x0E, 0x00, 0x00]))
        assert result["millivolts"] == 3600
        assert result["volts"] == 3.600

    def test_3712mv(self):
        result = decode_voltage(bytes([0x80, 0x0E, 0x00, 0x00]))
        assert result["millivolts"] == 3712
        assert result["volts"] == 3.712

    def test_high_voltage(self):
        result = decode_voltage(bytes([0x88, 0x13, 0x00, 0x00]))
        assert result["millivolts"] == 5000
        assert result["volts"] == 5.000

    def test_low_voltage(self):
        result = decode_voltage(bytes([0xE8, 0x03, 0x00, 0x00]))
        assert result["millivolts"] == 1000
        assert result["volts"] == 1.000

    def test_wrong_length_raises(self):
        with pytest.raises(ValueError):
            decode_voltage(bytes([0x60, 0x0E]))


class TestIsValidVoltage:
    def test_valid(self):
        assert is_valid_voltage(bytes([0x60, 0x0E, 0x00, 0x00]))

    def test_zero(self):
        assert not is_valid_voltage(bytes([0x00, 0x00, 0x00, 0x00]))

    def test_exceeds_max(self):
        assert not is_valid_voltage(bytes([0x88, 0x13, 0x00, 0x00]), max_mv=4000)

    def test_wrong_length(self):
        assert not is_valid_voltage(bytes([0x60]))
