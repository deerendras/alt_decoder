"""Plotly voltage visualization charts for ALT device datasets."""

from ..analyzer.device_schema import DeviceDataset
from ..analyzer.battery_analysis import compute_battery_metrics, compute_daily_voltages


def build_voltage_chart(dataset: DeviceDataset):
    """Voltage vs Time line chart."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        return _error_message("Plotly not installed")

    records = [r for r in dataset.records if r.timestamp is not None and r.battery_v > 0]
    if not records:
        return _error_message("No valid voltage records")

    records.sort(key=lambda r: r.timestamp)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[r.timestamp for r in records],
        y=[r.battery_v for r in records],
        mode="lines+markers",
        name="Voltage",
        line=dict(color="#1f77b4", width=1.5),
        marker=dict(size=3),
    ))
    fig.update_layout(
        title=f"Device {dataset.device_id} — Battery Voltage vs Time",
        xaxis_title="Timestamp",
        yaxis_title="Voltage (V)",
        template="plotly_white",
        height=400,
    )
    return fig


def build_daily_avg_chart(dataset: DeviceDataset):
    """Daily Average Voltage bar/line chart."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        return _error_message("Plotly not installed")

    daily = compute_daily_voltages(dataset)
    if not daily:
        return _error_message("No daily data available")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[d["date"] for d in daily],
        y=[d["avg_voltage"] for d in daily],
        name="Daily Avg",
        marker_color="#2ca02c",
        opacity=0.7,
    ))
    fig.add_trace(go.Scatter(
        x=[d["date"] for d in daily],
        y=[d["avg_voltage"] for d in daily],
        mode="lines+markers",
        name="Trend",
        line=dict(color="#d62728", width=2),
        marker=dict(size=5),
    ))
    fig.update_layout(
        title=f"Device {dataset.device_id} — Daily Average Voltage",
        xaxis_title="Date",
        yaxis_title="Average Voltage (V)",
        template="plotly_white",
        height=400,
    )
    return fig


def build_decay_trend_chart(dataset: DeviceDataset):
    """Voltage Decay Trend with linear regression."""
    try:
        import plotly.graph_objects as go
        import numpy as np
    except ImportError:
        return _error_message("Plotly/NumPy not installed")

    records = [r for r in dataset.records if r.timestamp is not None and r.battery_v > 0]
    if len(records) < 2:
        return _error_message("Not enough records for trend line")

    records.sort(key=lambda r: r.timestamp)

    x = [(r.timestamp - records[0].timestamp).total_seconds() / 3600.0 for r in records]
    y = [r.battery_v for r in records]

    coeffs = np.polyfit(x, y, 1)
    trend = np.poly1d(coeffs)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[r.timestamp for r in records],
        y=y,
        mode="markers",
        name="Voltage",
        marker=dict(size=3, color="#1f77b4"),
        opacity=0.5,
    ))
    fig.add_trace(go.Scatter(
        x=[r.timestamp for r in records],
        y=[trend(xi) for xi in x],
        mode="lines",
        name=f"Trend (slope={coeffs[0]:.5f} V/h)",
        line=dict(color="#d62728", width=2),
    ))
    fig.update_layout(
        title=f"Device {dataset.device_id} — Voltage Decay Trend",
        xaxis_title="Timestamp",
        yaxis_title="Voltage (V)",
        template="plotly_white",
        height=400,
    )
    return fig


def build_register_chart(dataset: DeviceDataset):
    """Register Index vs Time — expected flat line."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        return _error_message("Plotly not installed")

    records = [r for r in dataset.records if r.timestamp is not None]
    if not records:
        return _error_message("No valid records")

    records.sort(key=lambda r: r.timestamp)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[r.timestamp for r in records],
        y=[r.register_index for r in records],
        mode="lines+markers",
        name="Register Index",
        line=dict(color="#9467bd", width=1.5),
        marker=dict(size=3),
    ))
    fig.update_layout(
        title=f"Device {dataset.device_id} — Register Index vs Time",
        xaxis_title="Timestamp",
        yaxis_title="Register Index",
        template="plotly_white",
        height=400,
    )
    return fig


def build_validation_timeline(dataset: DeviceDataset):
    """Timeline of validation events (EEPROM/Flash failures)."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        return _error_message("Plotly not installed")

    eeprom_fails = [(r.timestamp, "EEPROM FAIL") for r in dataset.records
                    if r.eeprom == "FAIL" and r.timestamp]
    flash_fails = [(r.timestamp, "Flash FAIL") for r in dataset.records
                   if r.flash == "FAIL" and r.timestamp]

    if not eeprom_fails and not flash_fails:
        return None

    fig = go.Figure()
    for ts, label in eeprom_fails:
        fig.add_trace(go.Scatter(
            x=[ts], y=[1],
            mode="markers",
            name=label,
            marker=dict(color="#d62728", size=10, symbol="x"),
            showlegend=False,
        ))
    for ts, label in flash_fails:
        fig.add_trace(go.Scatter(
            x=[ts], y=[2],
            mode="markers",
            name=label,
            marker=dict(color="#ff7f0e", size=10, symbol="x"),
            showlegend=False,
        ))

    fig.update_layout(
        title=f"Device {dataset.device_id} — Validation Events",
        xaxis_title="Timestamp",
        yaxis=dict(tickmode="array", tickvals=[1, 2],
                    ticktext=["EEPROM", "Flash"]),
        template="plotly_white",
        height=300,
    )
    return fig


def _error_message(msg: str):
    return msg
