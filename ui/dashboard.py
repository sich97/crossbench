"""
Streamlit Dashboard - Interactive exploration and comparison of benchmark results.

Features:
- Automatic detection of new variables
- Cross-run comparison support
- Export to Markdown, CSV, PNG
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
from typing import List, Dict, Any, Optional
import sqlite3
from pathlib import Path


def load_data_from_database(db_path: str) -> pd.DataFrame:
    """
    Load all benchmarks from SQLite database into DataFrame.

    Args:
        db_path: Path to SQLite database

    Returns:
        Pandas DataFrame with all benchmark results
    """
    conn = sqlite3.connect(db_path)

    query = """
        SELECT 
            id,
            config_hash,
            model_path,
            model_group,
            backend_name,
            backend_version,
            rendered_command,
            variables_json,
            ttft_ms,
            tpot_ms,
            throughput_toks_s,
            peak_vram_mb,
            peak_system_ram_mb,
            hardware_metadata_json,
            timestamp
        FROM benchmarks
        ORDER BY timestamp DESC
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    # Parse JSON columns
    if "variables_json" in df.columns:
        df["variables"] = df["variables_json"].apply(
            lambda x: json.loads(x) if x else {}
        )

    if "hardware_metadata_json" in df.columns:
        df["hardware_metadata"] = df["hardware_metadata_json"].apply(
            lambda x: json.loads(x) if x else {}
        )

    return df


def get_all_variable_names(df: pd.DataFrame) -> List[str]:
    """
    Extract all unique variable names from DataFrame.

    Args:
        df: DataFrame with 'variables' column

    Returns:
        List of all variable names
    """
    variable_names = set()

    if "variables" in df.columns:
        for variables in df["variables"]:
            if isinstance(variables, dict):
                variable_names.update(variables.keys())

    return sorted(list(variable_names))


def filter_dataframe(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    """
    Filter DataFrame based on user selections.

    Args:
        df: Original DataFrame
        filters: Dictionary of filters

    Returns:
        Filtered DataFrame
    """
    filtered = df.copy()

    if "model_group" in filters and filters["model_group"]:
        filtered = filtered[filtered["model_group"] == filters["model_group"]]

    if "backend_name" in filters and filters["backend_name"]:
        filtered = filtered[filtered["backend_name"] == filters["backend_name"]]

    if "model_path" in filters and filters["model_path"]:
        filtered = filtered[filtered["model_path"] == filters["model_path"]]

    # Filter by variable values
    if "variable_filters" in filters:
        for var_name, var_value in filters["variable_filters"].items():
            if var_value:
                filtered = filtered[
                    filtered["variables"].apply(lambda x: x.get(var_name) == var_value)
                ]

    return filtered


def create_comparison_chart(
    df: pd.DataFrame, x_variable: str, y_metric: str, group_by: str = "model_group"
) -> go.Figure:
    """
    Create interactive comparison chart.

    Args:
        df: Filtered DataFrame
        x_variable: Variable to use for X-axis
        y_metric: Metric to use for Y-axis
        group_by: Column to group by

    Returns:
        Plotly Figure
    """
    # Extract variable values and metrics
    data_points = []

    for _, row in df.iterrows():
        variables = row.get("variables", {})
        x_value = variables.get(x_variable, "N/A")
        y_value = row.get(y_metric)

        if y_value is not None and not pd.isna(y_value):
            data_points.append(
                {
                    "x": x_value,
                    "y": y_value,
                    group_by: row.get(group_by, "Unknown"),
                    "model": row.get("model_path", "Unknown"),
                }
            )

    if not data_points:
        return go.Figure().add_annotation(text="No data available", showarrow=False)

    df_plot = pd.DataFrame(data_points)

    # Create figure
    fig = px.bar(
        df_plot,
        x="x",
        y="y",
        color=group_by,
        barmode="group",
        title=f"{y_metric} by {x_variable}",
        labels={"x": x_variable, "y": y_metric},
    )

    fig.update_layout(hovermode="x unified", height=500, legend_title_text=group_by)

    return fig


def create_timeline_chart(df: pd.DataFrame, benchmark_id: int) -> go.Figure:
    """
    Create timeline view for individual benchmark run.

    Args:
        df: DataFrame
        benchmark_id: Benchmark ID

    Returns:
        Plotly Figure
    """
    # Get single benchmark
    benchmark = df[df["id"] == benchmark_id]

    if benchmark.empty:
        return go.Figure().add_annotation(text="Benchmark not found", showarrow=False)

    row = benchmark.iloc[0]
    variables = row.get("variables", {})

    # Create timeline data
    x_values = list(variables.keys())
    y_values = list(variables.values())

    fig = go.Figure()

    fig.add_trace(go.Bar(x=x_values, y=y_values, name="Variables"))

    fig.update_layout(
        title=f"Benchmark #{benchmark_id} - Variable Values",
        xaxis_title="Variable",
        yaxis_title="Value",
        height=400,
    )

    return fig


def create_scatter_chart(
    df: pd.DataFrame, x_metric: str, y_metric: str, color_by: str = "model_group"
) -> go.Figure:
    """
    Create scatter plot comparing two metrics.

    Args:
        df: Filtered DataFrame
        x_metric: Metric for X-axis
        y_metric: Metric for Y-axis
        color_by: Column to color by

    Returns:
        Plotly Figure
    """
    # Filter rows with valid metrics
    valid_rows = df[df[x_metric].notna() & df[y_metric].notna()].copy()

    if valid_rows.empty:
        return go.Figure().add_annotation(text="No data available", showarrow=False)

    fig = px.scatter(
        valid_rows,
        x=x_metric,
        y=y_metric,
        color=color_by,
        size=y_metric,
        hover_data=["model_path", "backend_name"],
        title=f"{y_metric} vs {x_metric}",
        labels={x_metric: x_metric, y_metric: y_metric},
    )

    fig.update_layout(height=500, legend_title_text=color_by)

    return fig


def export_to_csv(df: pd.DataFrame, path: str) -> bool:
    """
    Export DataFrame to CSV file.

    Args:
        df: DataFrame to export
        path: Output file path

    Returns:
        True if successful
    """
    try:
        df.to_csv(path, index=False)
        return True
    except Exception as e:
        st.error(f"Export error: {e}")
        return False


def export_to_markdown(df: pd.DataFrame, path: str) -> bool:
    """
    Export DataFrame to Markdown file.

    Args:
        df: DataFrame to export
        path: Output file path

    Returns:
        True if successful
    """
    try:
        # Create markdown report
        with open(path, "w") as f:
            f.write("# CrossBench Results Report\n\n")
            f.write(f"Generated: {pd.Timestamp.now()}\n\n")
            f.write(f"Total Benchmarks: {len(df)}\n\n")

            # Summary table
            f.write("## Summary\n\n")
            f.write(
                df[
                    [
                        "model_group",
                        "backend_name",
                        "ttft_ms",
                        "tpot_ms",
                        "throughput_toks_s",
                    ]
                ].to_markdown(index=False)
            )

        return True
    except Exception as e:
        st.error(f"Export error: {e}")
        return False


def save_chart_as_png(fig: go.Figure, path: str) -> bool:
    """
    Save Plotly figure as PNG image.

    Args:
        fig: Plotly Figure
        path: Output file path

    Returns:
        True if successful
    """
    try:
        fig.write_image(path)
        return True
    except Exception as e:
        st.error(f"Save error: {e}")
        return False


def run_dashboard(db_path: str):
    """
    Run Streamlit dashboard.

    Args:
        db_path: Path to SQLite database
    """
    st.set_page_config(page_title="CrossBench Dashboard", page_icon="📊", layout="wide")

    st.title("📊 CrossBench Dashboard")

    # Load data
    @st.cache_data
    def load_data():
        return load_data_from_database(db_path)

    df = load_data()

    if df.empty:
        st.warning("No benchmark results found. Run benchmarks first.")
        return

    # Sidebar filters
    st.sidebar.header("Filters")

    # Get unique values for filters
    model_groups = (
        sorted(df["model_group"].unique()) if "model_group" in df.columns else []
    )
    backends = (
        sorted(df["backend_name"].unique()) if "backend_name" in df.columns else []
    )
    backend_versions = (
        sorted(df["backend_version"].unique())
        if "backend_version" in df.columns
        else []
    )

    # Filter out NaN values
    model_groups = [g for g in model_groups if pd.notna(g)]
    backends = [b for b in backends if pd.notna(b)]
    backend_versions = [v for v in backend_versions if pd.notna(v)]

    selected_groups = st.sidebar.multiselect(
        "Model Groups", options=model_groups, default=model_groups
    )

    selected_backends = st.sidebar.multiselect(
        "Backends", options=backends, default=backends
    )

    selected_versions = st.sidebar.multiselect(
        "Backend Versions", options=backend_versions, default=backend_versions
    )

    # Filter data
    filtered_df = df[
        (df["model_group"].isin(selected_groups))
        & (df["backend_name"].isin(selected_backends))
    ]

    if selected_versions and backend_versions:
        filtered_df = filtered_df[
            filtered_df["backend_version"].isin(selected_versions)
        ]

    st.sidebar.markdown(f"### Results: {len(filtered_df)} benchmarks")

    # Main content
    tab1, tab2, tab3, tab4 = st.tabs(
        ["Overview", "Comparison", "Individual Runs", "Export"]
    )

    with tab1:
        st.header("Overview")

        # Key metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Runs", len(filtered_df))

        with col2:
            avg_ttft = filtered_df["ttft_ms"].mean()
            st.metric(
                "Avg TTFT", f"{avg_ttft:.1f} ms" if not pd.isna(avg_ttft) else "N/A"
            )

        with col3:
            avg_tpot = filtered_df["tpot_ms"].mean()
            st.metric(
                "Avg TPOT", f"{avg_tpot:.2f} ms" if not pd.isna(avg_tpot) else "N/A"
            )

        with col4:
            avg_throughput = filtered_df["throughput_toks_s"].mean()
            st.metric(
                "Avg Throughput",
                f"{avg_throughput:.2f} tok/s" if not pd.isna(avg_throughput) else "N/A",
            )

        # Data table
        st.subheader("Benchmark Results")
        columns_to_show = [
            "model_path",
            "backend_name",
        ]
        if "backend_version" in filtered_df.columns:
            columns_to_show.append("backend_version")
        columns_to_show.extend(
            [
                "ttft_ms",
                "tpot_ms",
                "throughput_toks_s",
                "peak_vram_mb",
            ]
        )
        st.dataframe(
            filtered_df[columns_to_show].head(50),
            use_container_width=True,
        )

    with tab2:
        st.header("Comparison Charts")

        # Get available variables
        all_variables = get_all_variable_names(filtered_df)

        col1, col2 = st.columns(2)

        with col1:
            x_variable = st.selectbox(
                "X-Axis Variable",
                options=all_variables,
                index=0 if all_variables else 0,
            )

        with col2:
            y_metric = st.selectbox(
                "Y-Axis Metric",
                options=["ttft_ms", "tpot_ms", "throughput_toks_s", "peak_vram_mb"],
                index=1,
            )

        # Create chart
        fig = create_comparison_chart(filtered_df, x_variable, y_metric)
        st.plotly_chart(fig, use_container_width=True)

        # Scatter plot
        st.subheader("Scatter Plot")
        col3, col4 = st.columns(2)

        with col3:
            x_metric = st.selectbox(
                "X-Metric", options=["ttft_ms", "tpot_ms", "throughput_toks_s"], index=2
            )

        with col4:
            y_metric_scatter = st.selectbox(
                "Y-Metric", options=["ttft_ms", "tpot_ms", "throughput_toks_s"], index=1
            )

        fig_scatter = create_scatter_chart(filtered_df, x_metric, y_metric_scatter)
        st.plotly_chart(fig_scatter, use_container_width=True)

    with tab3:
        st.header("Individual Run Details")

        # Select benchmark
        benchmark_ids = sorted(filtered_df["id"].unique(), reverse=True)
        selected_id = st.selectbox(
            "Select Benchmark", options=benchmark_ids, format_func=lambda x: f"#{x}"
        )

        # Get benchmark data
        benchmark = filtered_df[filtered_df["id"] == selected_id].iloc[0]

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Variables")
            variables = benchmark.get("variables", {})
            for var_name, var_value in variables.items():
                st.text(f"{var_name}: {var_value}")

        with col2:
            st.subheader("Metrics")
            st.text(f"TTFT: {benchmark.get('ttft_ms', 'N/A')} ms")
            st.text(f"TPOT: {benchmark.get('tpot_ms', 'N/A')} ms")
            st.text(f"Throughput: {benchmark.get('throughput_toks_s', 'N/A')} tok/s")
            st.text(f"Peak VRAM: {benchmark.get('peak_vram_mb', 'N/A')} MB")
            st.text(f"Peak RAM: {benchmark.get('peak_system_ram_mb', 'N/A')} MB")

        st.subheader("Rendered Command")
        st.code(benchmark.get("rendered_command", "N/A"))

    with tab4:
        st.header("Export Results")

        st.subheader("Download Options")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Export to CSV"):
                csv_data = filtered_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name="crossbench_results.csv",
                    mime="text/csv",
                )

        with col2:
            if st.button("Export to Markdown"):
                md_data = filtered_df.to_markdown()
                st.download_button(
                    label="Download Markdown",
                    data=md_data.encode("utf-8"),
                    file_name="crossbench_results.md",
                    mime="text/markdown",
                )

        st.subheader("Save Charts")

        # Save current chart
        chart_name = st.text_input("Chart name (without extension)")

        if st.button("Save Current Chart as PNG"):
            # Get current chart from session
            if "current_chart" in st.session_state:
                fig = st.session_state.current_chart
                png_data = fig.to_image(format="png", width=1200, height=600)
                st.download_button(
                    label="Download PNG",
                    data=png_data,
                    file_name=f"{chart_name}.png",
                    mime="image/png",
                )
