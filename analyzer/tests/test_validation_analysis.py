import pytest
from analyzer.analysis.validation_analysis import validate_eeprom_flash
from analyzer.analysis.device_schema import DeviceDataset
from analyzer.parser.record_parser import DecodedRecord


class TestUnknownEepromFlashDetection:
    def test_unknown_eeprom_detected(self):
        r = DecodedRecord()
        r.eeprom = 'UNKNOWN(09)'
        r.flash = 'PASS'
        r.battery_mv = 3680
        r.iso = '2026-03-02T12:00:00'
        ds = DeviceDataset(device_id='300001', records=[r])
        issues = validate_eeprom_flash(ds)
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].category == "eeprom"
        assert "corrupt" in issues[0].message.lower()

    def test_unknown_flash_detected(self):
        r = DecodedRecord()
        r.eeprom = 'PASS'
        r.flash = 'UNKNOWN(FF)'
        r.battery_mv = 3680
        r.iso = '2026-03-02T12:00:00'
        ds = DeviceDataset(device_id='300001', records=[r])
        issues = validate_eeprom_flash(ds)
        assert len(issues) == 1
        assert issues[0].category == "flash"

    def test_both_unknown_detected(self):
        r = DecodedRecord()
        r.eeprom = 'UNKNOWN(09)'
        r.flash = 'UNKNOWN(09)'
        r.battery_mv = 3680
        r.iso = '2026-03-02T12:00:00'
        ds = DeviceDataset(device_id='300001', records=[r])
        issues = validate_eeprom_flash(ds)
        assert len(issues) == 2

    def test_normal_pass_not_flagged(self):
        r = DecodedRecord()
        r.eeprom = 'PASS'
        r.flash = 'PASS'
        r.battery_mv = 3680
        r.iso = '2026-03-02T12:00:00'
        ds = DeviceDataset(device_id='300001', records=[r])
        issues = validate_eeprom_flash(ds)
        assert len(issues) == 0

    def test_fail_still_detected(self):
        r = DecodedRecord()
        r.eeprom = 'FAIL'
        r.flash = 'FAIL'
        r.battery_mv = 3680
        r.iso = '2026-03-02T12:00:00'
        ds = DeviceDataset(device_id='300001', records=[r])
        issues = validate_eeprom_flash(ds)
        assert len(issues) == 2
