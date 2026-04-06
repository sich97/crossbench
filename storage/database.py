"""
Database Module - SQLite storage for benchmark results.

Implements extensible schema for results with metadata for reproducibility.
"""

import sqlite3
import json
import hashlib
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime


def init_database(db_path: str) -> sqlite3.Connection:
    """
    Initialize SQLite database with benchmarks table.

    Args:
        db_path: Path to SQLite database file

    Returns:
        Database connection
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create benchmarks table with extensible schema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS benchmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_hash TEXT NOT NULL,
            model_path TEXT NOT NULL,
            model_group TEXT NOT NULL,
            backend_name TEXT NOT NULL,
            backend_version TEXT,
            rendered_command TEXT NOT NULL,
            variables_json TEXT NOT NULL,
            config_yaml TEXT NOT NULL,
            ttft_ms REAL,
            tpot_ms REAL,
            throughput_toks_s REAL,
            peak_vram_mb REAL,
            peak_system_ram_mb REAL,
            hardware_metadata_json TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create index for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_model_group 
        ON benchmarks(model_group, backend_name)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_config_hash 
        ON benchmarks(config_hash)
    """)

    conn.commit()

    return conn


def hash_config(config_path: str) -> str:
    """
    Generate SHA-256 hash of configuration file.

    Args:
        config_path: Path to config.yaml file

    Returns:
        Hexadecimal hash string
    """
    with open(config_path, "r") as f:
        config_content = f.read()

    hash_object = hashlib.sha256(config_content.encode("utf-8"))
    return hash_object.hexdigest()


def insert_benchmark(conn: sqlite3.Connection, run_data: Dict[str, Any]) -> int:
    """
    Insert benchmark result into database.

    Args:
        conn: Database connection
        run_data: Dictionary with all benchmark data

    Returns:
        ID of inserted row
    """
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO benchmarks (
            config_hash,
            model_path,
            model_group,
            backend_name,
            backend_version,
            rendered_command,
            variables_json,
            config_yaml,
            ttft_ms,
            tpot_ms,
            throughput_toks_s,
            peak_vram_mb,
            peak_system_ram_mb,
            hardware_metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            run_data["config_hash"],
            run_data["model_path"],
            run_data["model_group"],
            run_data["backend_name"],
            run_data.get("backend_version"),
            run_data["rendered_command"],
            json.dumps(run_data["variables"]),
            run_data.get("config_yaml", ""),
            run_data.get("ttft_ms"),
            run_data.get("tpot_ms"),
            run_data.get("throughput_toks_s"),
            run_data.get("peak_vram_mb"),
            run_data.get("peak_system_ram_mb"),
            json.dumps(run_data.get("hardware_metadata", {})),
        ),
    )

    conn.commit()

    return cursor.lastrowid


def query_benchmarks(
    conn: sqlite3.Connection, filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Query benchmarks with optional filters.

    Args:
        conn: Database connection
        filters: Dictionary of filters (model_group, backend_name, etc.)

    Returns:
        List of benchmark result dictionaries
    """
    cursor = conn.cursor()

    base_query = "SELECT * FROM benchmarks"
    conditions = []
    params = []

    if filters:
        if "model_group" in filters:
            conditions.append("model_group = ?")
            params.append(filters["model_group"])

        if "backend_name" in filters:
            conditions.append("backend_name = ?")
            params.append(filters["backend_name"])

        if "config_hash" in filters:
            conditions.append("config_hash = ?")
            params.append(filters["config_hash"])

        if "min_ctx_size" in filters:
            conditions.append("variables_json LIKE ?")
            params.append(f'"--ctx-size": {filters["min_ctx_size"]}%')

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    base_query += " ORDER BY timestamp DESC"

    cursor.execute(base_query, params)

    columns = [description[0] for description in cursor.description]
    results = []

    for row in cursor.fetchall():
        row_dict = dict(zip(columns, row))

        # Parse JSON fields
        if row_dict.get("variables_json"):
            row_dict["variables"] = json.loads(row_dict["variables_json"])
            del row_dict["variables_json"]

        if row_dict.get("hardware_metadata_json"):
            row_dict["hardware_metadata"] = json.loads(
                row_dict["hardware_metadata_json"]
            )
            del row_dict["hardware_metadata_json"]

        results.append(row_dict)

    return results


def get_hardware_metadata() -> Dict[str, Any]:
    """
    Collect hardware metadata for benchmark runs.

    Returns:
        Dictionary with hardware information
    """
    import psutil

    metadata = {
        "timestamp": datetime.now().isoformat(),
        "cpu_count": psutil.cpu_count(logical=True),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "ram_total_mb": psutil.virtual_memory().total / (1024 * 1024),
        "gpu_detected": False,
        "gpu_type": None,
    }

    # Check for GPU (ROCm)
    try:
        result = __import__("subprocess").run(
            ["rocm-smi", "--query-gpu"], capture_output=True, text=True, timeout=5
        )

        if result.returncode == 0:
            metadata["gpu_detected"] = True
            metadata["gpu_type"] = "AMD ROCm"

            # Extract GPU count
            gpu_count = result.stdout.count("GPU")
            metadata["gpu_count"] = gpu_count

    except Exception:
        pass  # ROCm not available

    # Add platform info
    import platform

    metadata["platform"] = platform.platform()
    metadata["python_version"] = platform.python_version()

    return metadata


def get_all_model_groups(conn: sqlite3.Connection) -> List[str]:
    """
    Get list of all model groups from database.

    Args:
        conn: Database connection

    Returns:
        List of model group names
    """
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT model_group FROM benchmarks")
    return [row[0] for row in cursor.fetchall()]


def get_all_backends(conn: sqlite3.Connection) -> List[str]:
    """
    Get list of all backends from database.

    Args:
        conn: Database connection

    Returns:
        List of backend names
    """
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT backend_name FROM benchmarks")
    return [row[0] for row in cursor.fetchall()]


def get_benchmark_by_id(
    conn: sqlite3.Connection, benchmark_id: int
) -> Optional[Dict[str, Any]]:
    """
    Get a single benchmark by ID.

    Args:
        conn: Database connection
        benchmark_id: Benchmark ID

    Returns:
        Benchmark dictionary or None if not found
    """
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM benchmarks WHERE id = ?", (benchmark_id,))

    row = cursor.fetchone()
    if not row:
        return None

    columns = [description[0] for description in cursor.description]
    row_dict = dict(zip(columns, row))

    # Parse JSON fields
    if row_dict.get("variables_json"):
        row_dict["variables"] = json.loads(row_dict["variables_json"])
        del row_dict["variables_json"]

    if row_dict.get("hardware_metadata_json"):
        row_dict["hardware_metadata"] = json.loads(row_dict["hardware_metadata_json"])
        del row_dict["hardware_metadata_json"]

    return row_dict


def get_comparison_data(
    conn: sqlite3.Connection, model_group: str, variable_name: str
) -> List[Dict[str, Any]]:
    """
    Get data for comparing a variable across benchmarks.

    Args:
        conn: Database connection
        model_group: Model group to filter
        variable_name: Variable name to compare (e.g., "--ctx-size")

    Returns:
        List of comparison records
    """
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, model_path, backend_name, ttft_ms, tpot_ms, throughput_toks_s,
               variables_json
        FROM benchmarks
        WHERE model_group = ?
        ORDER BY model_path, backend_name
    """,
        (model_group,),
    )

    results = []
    for row in cursor.fetchall():
        variables = json.loads(row[6])

        # Extract variable value
        var_value = variables.get(variable_name, "N/A")

        results.append(
            {
                "id": row[0],
                "model_path": row[1],
                "backend_name": row[2],
                "variable_value": var_value,
                "ttft_ms": row[3],
                "tpot_ms": row[4],
                "throughput_toks_s": row[5],
            }
        )

    return results
