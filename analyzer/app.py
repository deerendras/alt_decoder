"""ALT Decoder — Streamlit App

Three pages:
    1. Upload — drag and drop ALT log files, auto-detect devices
    2. Dashboard — battery metrics, interactive charts, validation summary
    3. Export — download CSV reports and chart data
"""

import csv
import io
import sys
import tempfile
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _APP_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024

try:
    import streamlit as st
except ImportError:
    print("Streamlit not installed. Run: pip install streamlit", file=sys.stderr)
    sys.exit(1)

from analyzer.parser.file_discovery import group_files
from analyzer.analysis.timeline_builder import build_all_timelines
from analyzer.analysis.battery_analysis import (
    compute_battery_metrics,
    compute_dataset_metrics,
    compute_daily_voltages,
)
from analyzer.analysis.validation_analysis import run_validations
from analyzer.visualization.voltage_charts import (
    build_voltage_chart,
    build_daily_avg_chart,
    build_decay_trend_chart,
    build_register_chart,
    build_validation_timeline,
)
from analyzer.reports.csv_export import (
    export_records_csv,
    export_summary_csv,
    export_daily_csv,
    export_voltage_chart_csv,
    export_decay_trend_csv,
    export_daily_avg_chart_csv,
    export_register_chart_csv,
)

# Note: export_voltage_chart_csv, export_decay_trend_csv, export_daily_avg_chart_csv,
# and export_register_chart_csv are used on the Export page only.


st.set_page_config(
    page_title="ALT Decoder",
    layout="wide",
)

st.title("ALT Decoder")
st.caption("Decode, analyze, and export Accelerated Life Test log data from smart meters.")


def init_session():
    defaults = {
        "datasets": None,
        "uploaded_files": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def process_files(uploaded_files) -> bool:
    if not uploaded_files:
        return False

    for uf in uploaded_files:
        if uf.size > MAX_FILE_SIZE:
            st.error(f"File '{uf.name}' exceeds {MAX_FILE_SIZE_MB}MB size limit ({uf.size / 1024 / 1024:.1f}MB)")
            return False
        if uf.size == 0:
            st.error(f"File '{uf.name}' is empty")
            return False
        if not uf.name.lower().endswith(".txt"):
            st.error(f"File '{uf.name}' is not a .txt file")
            return False

    with tempfile.TemporaryDirectory() as tmpdir:
        saved = []
        for uf in uploaded_files:
            content = uf.getvalue()
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                st.error(f"File '{uf.name}' is not valid UTF-8 text")
                return False
            if "ReadALTTestLog" not in text:
                st.warning(f"File '{uf.name}' does not contain ReadALTTestLog entries")
            fpath = Path(tmpdir) / uf.name
            fpath.write_bytes(content)
            saved.append(str(fpath))

        try:
            devices = group_files(saved)
        except ValueError:
            st.error("File names must follow the pattern: DeviceID_Segment.txt (e.g. 300001_10.txt)")
            return False

        if not devices:
            st.warning("No valid ALT log files found. Expected file naming: 300001_10.txt")
            return False

        st.session_state.datasets = build_all_timelines(devices)
        st.session_state.uploaded_files = uploaded_files
        st.success(f"Loaded {len(uploaded_files)} file(s) across {len(devices)} device(s).")
        return True


# ---------------------------------------------------------------------------
# Page 1 — Upload
# ---------------------------------------------------------------------------
def upload_page():
    st.header("Upload ALT Log Files")
    st.caption(
        "Select one or more `.txt` log files from the smart meter. "
        "Files are automatically grouped by the device serial number embedded in the file name "
        "(e.g. `300001_10.txt` → device **300001**, data segment **10**)."
    )

    uploaded = st.file_uploader(
        "Choose ALT log files",
        type=["txt"],
        accept_multiple_files=True,
        key="file_uploader",
        label_visibility="collapsed",
    )

    if uploaded and uploaded != st.session_state.get("_last_upload"):
        st.session_state["_last_upload"] = uploaded
        process_files(uploaded)

    datasets = st.session_state.datasets
    if not datasets:
        st.info("Drag and drop your log files above to begin.")
        return

    st.divider()
    st.subheader("Devices Found")

    cols = st.columns(4)
    for i, ds in enumerate(datasets):
        with cols[i % 4]:
            st.metric(
                f"Device {ds.device_id}",
                f"{ds.record_count} hourly readings",
            )


# ---------------------------------------------------------------------------
# Page 2 — Dashboard
# ---------------------------------------------------------------------------
def dashboard_page():
    st.header("Device Dashboard")

    datasets = st.session_state.datasets
    if not datasets:
        st.info("Go to the **Upload** page and add your log files first.")
        return

    device_ids = [ds.device_id for ds in datasets]
    selected = st.selectbox("Choose a device to inspect", device_ids, key="device_selector")

    ds = next(d for d in datasets if d.device_id == selected)

    bm = compute_battery_metrics(ds)
    dm = compute_dataset_metrics(ds)
    vr_report = run_validations(ds)

    # ---- Summary metrics ----
    st.subheader(f"Device {selected} — Key Metrics")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            "Total Hourly Readings",
            dm["total_records"],
            help="Number of unique hourly voltage records after merging and deduplication.",
        )
    with c2:
        drop = bm.get("voltage_drop_mv")
        st.metric(
            "Total Voltage Drop",
            f"{drop} mV" if drop is not None else "N/A",
            help="Difference between the first and last recorded battery voltage.",
        )
    with c3:
        st.metric(
            "EEPROM Memory Faults",
            dm["eeprom_failures"],
            delta=None,
            help="Count of records where the EEPROM internal memory reported a failure.",
        )
    with c4:
        st.metric(
            "Flash Memory Faults",
            dm["flash_failures"],
            delta=None,
            help="Count of records where the flash memory reported a failure.",
        )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            "Starting Battery Voltage",
            f"{bm.get('start_voltage_v', 'N/A')} V",
            help="Battery voltage at the earliest recorded timestamp.",
        )
    with c2:
        st.metric(
            "Ending Battery Voltage",
            f"{bm.get('end_voltage_v', 'N/A')} V",
            help="Battery voltage at the latest recorded timestamp.",
        )
    with c3:
        st.metric(
            "Average Battery Voltage",
            f"{bm.get('avg_voltage_v', 'N/A')} V",
            help="Mean voltage across all hourly readings.",
        )
    with c4:
        daily = bm.get("daily_loss_mv")
        st.metric(
            "Estimated Daily Voltage Loss",
            f"{daily} mV/day" if daily is not None else "N/A",
            help="Average voltage lost per calendar day over the test duration.",
        )

    # ---- Validation banner ----
    if not vr_report.is_healthy:
        st.error(f"{len(vr_report.errors)} hardware or data-quality issue(s) detected.")
    elif vr_report.warnings:
        st.warning(f"{len(vr_report.warnings)} minor warning(s) — see details below.")
    else:
        st.success("All validation checks passed. No hardware faults or data issues found.")

    # ---- Charts ----
    st.divider()
    st.subheader("Charts")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Hourly Voltage", "Daily Averages", "Voltage Decay Trend",
        "Register Stability", "Hardware Fault Events"
    ])

    with tab1:
        chart = build_voltage_chart(ds)
        if isinstance(chart, str):
            st.warning(chart)
        else:
            st.caption(
                "Every hourly voltage reading plotted over time. "
                "Use the toolbar on the chart to zoom, pan, or download as a PNG image."
            )
            st.plotly_chart(chart, use_container_width=True, key="chart_voltage_time")

    with tab2:
        chart = build_daily_avg_chart(ds)
        if isinstance(chart, str):
            st.warning(chart)
        else:
            st.caption(
                "Bar chart shows average voltage per calendar day. "
                "The red line overlays the daily trend."
            )
            st.plotly_chart(chart, use_container_width=True, key="chart_daily_avg")

    with tab3:
        chart = build_decay_trend_chart(ds)
        if isinstance(chart, str):
            st.warning(chart)
        else:
            st.caption(
                "Scatter plot of all voltage readings with a linear regression trend line. "
                "The slope tells you how fast the battery is draining per hour."
            )
            st.plotly_chart(chart, use_container_width=True, key="chart_decay")

            st.divider()
            st.subheader("Voltage Decay Calculation")

            _render_decay_calculation(ds)

    with tab4:
        chart = build_register_chart(ds)
        if isinstance(chart, str):
            st.warning(chart)
        else:
            st.caption(
                "Tracks the meter's internal register index over time. "
                "In a healthy device this line should be flat — any sudden change indicates "
                "a possible firmware or EEPROM write issue."
            )
            st.plotly_chart(chart, use_container_width=True, key="chart_register")

    with tab5:
        chart = build_validation_timeline(ds)
        if chart is None:
            st.success(
                "No hardware fault events detected. "
                "EEPROM and Flash memory both reported PASS across all readings."
            )
        elif isinstance(chart, str):
            st.warning(chart)
        else:
            st.caption(
                "Each marker represents a timestamp where the meter reported an EEPROM or "
                "Flash memory failure."
            )
            st.plotly_chart(chart, use_container_width=True, key="chart_validation")

    # ---- Records table ----
    st.divider()
    st.subheader("Last 20 Hourly Readings")
    st.caption(
        "Most recent decoded records. Each row represents one hourly voltage reading "
        "from the meter."
    )
    records_data = []
    for r in ds.records[-20:]:
        records_data.append({
            "Timestamp": r.iso or "N/A",
            "EEPROM Status": r.eeprom,
            "Flash Status": r.flash,
            "Battery Voltage (V)": r.battery_v,
            "Register Index": r.register_index,
        })
    st.dataframe(records_data, use_container_width=True, hide_index=True)


def _render_decay_calculation(ds):
    """Render the decay calculation methodology for the report."""
    records = [r for r in ds.records if r.timestamp is not None and r.battery_v > 0]
    if len(records) < 2:
        st.info("Not enough data points for a decay calculation.")
        return

    records.sort(key=lambda r: r.timestamp)
    import numpy as np

    x_hours = [(r.timestamp - records[0].timestamp).total_seconds() / 3600.0 for r in records]
    y_volts = [r.battery_v for r in records]

    n = len(records)
    coeffs = np.polyfit(x_hours, y_volts, 1)
    slope_v_per_h = coeffs[0]
    intercept_v = coeffs[1]

    x_mean = sum(x_hours) / n
    y_mean = sum(y_volts) / n
    ss_res = sum((y_volts[i] - (slope_v_per_h * x_hours[i] + intercept_v)) ** 2 for i in range(n))
    ss_tot = sum((yi - y_mean) ** 2 for yi in y_volts)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    total_hours = x_hours[-1]
    total_days = total_hours / 24.0
    start_v = y_volts[0]
    end_v = y_volts[-1]
    total_drop_mv = (start_v - end_v) * 1000
    model_voltage_drop_v = abs(slope_v_per_h) * total_hours
    model_daily_loss_mv = abs(slope_v_per_h) * 24 * 1000

    st.markdown("**Linear Regression: Voltage = a×t + b**")
    st.markdown(
        f"- **a (slope):** {slope_v_per_h:.6f} V/hour "
        f"= {slope_v_per_h * 1000:.4f} mV/hour "
        f"= {model_daily_loss_mv:.2f} mV/day"
    )
    st.markdown(f"- **b (intercept):** {intercept_v:.3f} V (modeled starting voltage)")
    st.markdown(f"- **R² (goodness of fit):** {r_squared:.4f}")
    st.divider()
    st.markdown("**Measured Values vs. Model:**")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"- Measured start voltage: **{start_v:.3f} V**")
        st.markdown(f"- Measured end voltage: **{end_v:.3f} V**")
        st.markdown(f"- Measured total drop: **{total_drop_mv:.0f} mV**")
    with c2:
        st.markdown(f"- Total duration: **{total_hours:.0f} hours ({total_days:.1f} days)**")
        st.markdown(f"- Model voltage drop: **{model_voltage_drop_v * 1000:.0f} mV**")
        st.markdown(f"- Model daily loss: **{model_daily_loss_mv:.2f} mV/day**")
    st.caption(
        "The linear regression fits a straight line through all voltage readings over time. "
        "The slope **a** represents the average voltage decay rate. "
        "**R²** close to 1.0 means the decay is highly linear; lower values suggest the decay "
        "rate changes over time or the data has significant noise. "
        "The model daily loss is the best-fit estimate — compare with the measured daily loss "
        "from the key metrics above."
    )


# ---------------------------------------------------------------------------
# Page 3 — Export
# ---------------------------------------------------------------------------
def export_page():
    st.header("Export Data & Reports")

    datasets = st.session_state.datasets
    if not datasets:
        st.info("Go to the **Upload** page and add your log files first.")
        return

    st.caption(
        "Download your decoded data in CSV format. All files open directly in Excel, "
        "Google Sheets, or any spreadsheet application."
    )

    st.divider()
    st.subheader("Decoded Records")

    c1, c2 = st.columns(2)

    with c1:
        all_csv = ""
        for ds in datasets:
            all_csv += export_records_csv(ds)

        st.download_button(
            "Download All Records (CSV)",
            data=all_csv,
            file_name="alt_all_records.csv",
            mime="text/csv",
            help="Every decoded hourly reading: timestamp, EEPROM/Flash status, "
                 "battery voltage (mV and V), and register index.",
            use_container_width=True,
        )
        st.caption("One row per hourly reading. Includes all devices.")

    with c2:
        daily = ""
        for ds in datasets:
            daily += export_daily_csv(ds)
        st.download_button(
            "Download Daily Averages (CSV)",
            data=daily,
            file_name="alt_daily_averages.csv",
            mime="text/csv",
            help="Average, minimum, and maximum voltage for each calendar day.",
            use_container_width=True,
        )
        st.caption("Summarized per calendar day across all devices.")

    st.divider()
    st.subheader("Summary Report")

    summary = export_summary_csv(datasets)
    st.download_button(
        "Download Device Summary (CSV)",
        data=summary,
        file_name="alt_device_summary.csv",
        mime="text/csv",
        help="One row per device. Key metrics: voltage range, voltage drop, daily loss, "
             "EEPROM/Flash failures, data completeness.",
        use_container_width=True,
    )
    st.caption("One row per device with all key metrics condensed.")

    st.divider()
    st.subheader("Chart Plot Data")
    st.caption(
        "Each CSV below contains the exact data points used to draw the corresponding chart "
        "on the Dashboard. Use these to recreate or customize charts in your own tools."
    )

    for ds in datasets:
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                f"Voltage vs Time Data — Device {ds.device_id}",
                data=export_voltage_chart_csv(ds),
                file_name=f"alt_{ds.device_id}_voltage_chart.csv",
                mime="text/csv",
                use_container_width=True,
            )
            st.download_button(
                f"Decay Trend Data — Device {ds.device_id}",
                data=export_decay_trend_csv(ds),
                file_name=f"alt_{ds.device_id}_decay_trend.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with c2:
            st.download_button(
                f"Daily Average Data — Device {ds.device_id}",
                data=export_daily_avg_chart_csv(ds),
                file_name=f"alt_{ds.device_id}_daily_avg.csv",
                mime="text/csv",
                use_container_width=True,
            )
            st.download_button(
                f"Register Index Data — Device {ds.device_id}",
                data=export_register_chart_csv(ds),
                file_name=f"alt_{ds.device_id}_register_index.csv",
                mime="text/csv",
                use_container_width=True,
            )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    init_session()

    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["Upload", "Dashboard", "Export"],
        key="nav",
    )

    if page == "Upload":
        upload_page()
    elif page == "Dashboard":
        dashboard_page()
    else:
        export_page()


if __name__ == "__main__":
    main()
