# Honeywell V200HL ALT Analyzer

**Decode, analyze, and export Accelerated Life Test log data from Honeywell V200HL water meters.**

---

## Prerequisites

| Requirement | Why |
|---|---|
| Python 3.11+ | Core runtime |
| pip (comes with Python) | Package installer |

---

## Setup — First Time Only

Open a terminal in the project root (where this README lives) and run:

```bash
pip install -r alt_analyzer/requirements.txt
```

That installs: **Streamlit**, **Pandas**, **Plotly**, **NumPy**, **openpyxl**, and **pytest**.

---

## Running the App (GUI)

```bash
streamlit run alt_analyzer/app.py
```

This starts a local web server. Open the URL that appears (usually `http://localhost:8501`) in your browser.

The app has three pages:

| Page | What it does |
|---|---|
| **Upload** | Drag and drop `.txt` log files. Auto-groups by device serial number. |
| **Dashboard** | Battery metrics, interactive charts, hardware fault summary, record table. |
| **Export** | Download CSV files: all records, daily averages, device summary, and chart plot data. |

---

## Running the CLI Decoder

```bash
python -m alt_analyzer.decode sample_data/ --summary
```

Options:

| Flag | What it does |
|---|---|
| `--summary` | Print only the device summary, not individual records |
| `--csv report.csv` | Export all records to a CSV file |
| `--json report.json` | Export all records to a JSON file |

You can pass individual files or a whole directory. Files are automatically grouped by device ID (the 6-digit number in the filename).

---

## Expected File Names

Files must follow this pattern:

```
DEVICEID_SEGMENT.txt
```

Examples:
- `300001_10.txt` → device **300001**, segment **10**
- `300001_20.txt` → device **300001**, segment **20**
- `300002_10.txt` → device **300002**, segment **10**

The app rejects files that don't match.

---

## Running Tests

```bash
python -m pytest alt_analyzer/tests/ -v
```

All 38 unit tests should pass. These cover:
- Packet extraction from raw hex data
- Timestamp decoding (month/day/hour)
- Voltage decoding (4-byte little-endian to mV/V)
- Full 14-byte record decoding
- Edge cases (corrupt data, all-zeros pages, invalid timestamps)

---

## Project Structure

```
alt_analyzer/
├── app.py                 Streamlit GUI entry point
├── decode.py              CLI entry point
├── requirements.txt       Python dependencies
├── parser/
│   ├── packet_parser.py   Extract packets from raw log lines
│   ├── timestamp_parser.py  Decode 4-byte timestamps
│   ├── voltage_parser.py    Decode 4-byte battery voltage
│   ├── record_parser.py     Decode full 14-byte ALT records
│   └── file_discovery.py    Parse filenames, group by device
├── analyzer/
│   ├── device_schema.py      DeviceDataset data structure
│   ├── timeline_builder.py   Merge, sort, deduplicate records
│   ├── validation_analysis.py  EEPROM/Flash, register, completeness checks
│   └── battery_analysis.py   Voltage metrics, daily loss, daily averages
├── visualization/
│   └── voltage_charts.py     5 Plotly charts (HTML/CSV exportable)
├── reports/
│   └── csv_export.py         CSV generators for records, summaries, chart data
├── tests/
│   ├── test_packet_parser.py
│   ├── test_timestamp_parser.py
│   ├── test_voltage_parser.py
│   └── test_record_parser.py
└── sample_data/
    ├── 300001_10.txt
    ├── 300001_20.txt
    ├── 300001_30.txt
    └── 300001_40.txt
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'alt_analyzer'` | Run the app from the project root directory (`Project_Byri/`), not from inside `alt_analyzer/` |
| `streamlit: command not found` | Run `pip install streamlit` or use `python -m streamlit run alt_analyzer/app.py` |
| Charts show "Plotly not installed" | Run `pip install plotly` |
| Decay trend shows "NumPy not installed" | Run `pip install numpy` |
| "Files must follow pattern" error | Rename your files to `DEVICEID_SEGMENT.txt` format |
