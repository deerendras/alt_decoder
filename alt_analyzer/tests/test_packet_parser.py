"""Tests for packet_parser.py"""
import pytest
from alt_analyzer.parser.packet_parser import (
    parse_packet, split_records, hex_to_bytes, extract_hex_output,
    HEADER, FOOTER, RECORD_SIZE
)


class TestHexToBytes:
    def test_simple(self):
        result = hex_to_bytes("4F A9 BB 0C")
        assert result == bytes([0x4F, 0xA9, 0xBB, 0x0C])

    def test_with_extra_spaces(self):
        result = hex_to_bytes("01  02   03")
        assert result == bytes([0x01, 0x02, 0x03])


class TestExtractHexOutput:
    def test_extracts_output(self):
        line = "Command:   ReadALTTestLog,  Status:   True,  Output: 4F A9 BB 0C CC 0D"
        result = extract_hex_output(line)
        assert result == "4F A9 BB 0C CC 0D"

    def test_no_output_returns_none(self):
        line = "Command:   StopALTREDTest,  Status:   True"
        assert extract_hex_output(line) is None


class TestParsePacket:
    def test_parses_valid_packet(self):
        line = "Command:   ReadALTTestLog,  Status:   True,  Output: 4F A9 BB 0C 01 01 60 0E 00 00 31 01 00 00 03 02 0C 00 CC 0D"
        packet = parse_packet(line, 1)
        assert packet is not None
        assert packet.page == 0x0C
        assert packet.source_line == 1
        assert len(packet.raw_data) == 14

    def test_skips_stop_command(self):
        line = "Command:   StopALTREDTest,  Status:   True,  Output: 4F 01 BB 00 CC 0D"
        assert parse_packet(line, 1) is None

    def test_skips_non_binary_header(self):
        line = "Command:   ReadALTTestLog,  Status:   True,  Output: FF FF FF FF CC 0D"
        assert parse_packet(line, 1) is None


class TestSplitRecords:
    def test_single_record(self):
        from alt_analyzer.parser.packet_parser import Packet
        data = bytes([0x01, 0x01, 0x60, 0x0E, 0x00, 0x00, 0x31, 0x01, 0x00, 0x00, 0x03, 0x02, 0x0C, 0x00])
        packet = Packet(page=0x0C, raw_data=data, source_line=1)
        records = split_records(packet)
        assert len(records) == 1
        assert records[0] == data

    def test_multiple_records(self):
        from alt_analyzer.parser.packet_parser import Packet
        data = bytes([0x01, 0x01, 0x60, 0x0E, 0x00, 0x00, 0x31, 0x01, 0x00, 0x00, 0x03, 0x02, 0x0C, 0x00] * 3)
        packet = Packet(page=0x0C, raw_data=data, source_line=1)
        records = split_records(packet)
        assert len(records) == 3

    def test_partial_record_discarded(self):
        from alt_analyzer.parser.packet_parser import Packet
        data = bytes([0x01, 0x01, 0x60, 0x0E, 0x00, 0x00, 0x31, 0x01, 0x00, 0x00, 0x03, 0x02, 0x0C, 0x00, 0xFF, 0xFF])
        packet = Packet(page=0x0C, raw_data=data, source_line=1)
        records = split_records(packet)
        assert len(records) == 1

    def test_all_zeros_records(self):
        from alt_analyzer.parser.packet_parser import Packet
        data = bytes([0x00] * 14 * 5)
        packet = Packet(page=0xFC, raw_data=data, source_line=2)
        records = split_records(packet)
        assert len(records) == 5
