#!/usr/bin/env python3
"""
Main CLI Entry Point - Orchestrate benchmark pipeline.

Single command to run entire benchmark suite or launch Web UI.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add core modules
sys.path.insert(0, str(Path(__file__).parent))

from core.config import (
    load_config,
    resolve_hierarchy,
    get_all_model_groups,
    get_backend_config,
)
from core.variable_engine import classify_variables
from core.cartesian import expand_all_variables
from core.command_builder import render_command
from core.model_discovery import discover_models, get_model_metadata
from storage.database import (
    init_database,
    hash_config_file,
    insert_benchmark,
    get_hardware_metadata,
)
from execution.docker_runner import (
    spawn_container,
    wait_for_container_ready,
    stop_container,
)
from execution.metrics_collector import run_inference_test
from core.memory_monitor import MemoryMonitor


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="CrossBench: LLM Benchmarking Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --config config.yaml --db results.db
  python main.py --config config.yaml --db results.db --model-group dense_models
  python main.py --ui --db results.db
        """,
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to configuration YAML file (default: config.yaml)",
    )

    parser.add_argument(
        "--db",
        type=str,
        default="results.db",
        help="Path to SQLite database file (default: results.db)",
    )

    parser.add_argument(
        "--model-group",
        type=str,
        default=None,
        help="Optional: Run only specific model group",
    )

    parser.add_argument(
        "--backend", type=str, default=None, help="Optional: Run only specific backend"
    )

    parser.add_argument(
        "--ui", action="store_true", help="Launch Web UI instead of running benchmarks"
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Print commands without executing"
    )

    return parser.parse_args()


def run_benchmark(config_path: str, db_path: str) -> None:
    """
    Run entire benchmark suite.

    Args:
        config_path: Path to config.yaml
        db_path: Path to SQLite database
    """
    print("=" * 60)
    print("CrossBench: LLM Benchmarking Framework")
    print("=" * 60)

    # Load configuration
    print(f"\n[1/7] Loading configuration: {config_path}")
    config = load_config(config_path)
    config_hash = hash_config_file(config_path)
    print(f"      Config hash: {config_hash}")

    # Get model groups
    print(f"\n[2/7] Discovering model groups...")
    model_groups = config.get("model_groups", {})

    all_groups = get_all_model_groups(config)

    if args.model_group and args.model_group not in all_groups:
        print(f"Error: Model group '{args.model_group}' not found")
        sys.exit(1)

    groups_to_run = [args.model_group] if args.model_group else all_groups

    print(f"      Found {len(all_groups)} model groups: {', '.join(all_groups)}")
    print(f"      Running: {', '.join(groups_to_run)}")

    # Initialize database
    print(f"\n[3/7] Initializing database: {db_path}")
    conn = init_database(db_path)
    hardware_metadata = get_hardware_metadata()
    print(
        f"      Hardware: {hardware_metadata.get('cpu_count')} CPU cores, "
        f"{hardware_metadata.get('ram_total_mb', 0):.0f} MB RAM"
    )

    # Read config YAML content
    with open(config_path, "r") as f:
        config_yaml_content = f.read()

    # Process each model group
    for group_name in groups_to_run:
        group_config = model_groups.get(group_name, {})
        group_path = group_config.get("path", "")

        print(f"\n[4/7] Processing model group: {group_name}")
        print(f"      Path: {group_path}")

        # Discover models
        models = discover_models(group_path)
        print(f"      Found {len(models)} models")

        # Resolve variables for this group
        group_variables = group_config.get("variables", {})
        resolved_variables = resolve_hierarchy(config)

        print(f"      Resolved variables: {len(resolved_variables)}")

        # Expand variables into combinations
        combinations = expand_all_variables(resolved_variables)
        print(f"      Generated {len(combinations)} test combinations")

        # Process each model
        for model in models:
            model_path = model["path"]
            model_name = model["name"]

            print(f"\n[5/7] Benchmarking model: {model_name}")
            print(f"      Path: {model_path}")

            # Get model metadata
            model_meta = get_model_metadata(model_path)

            for i, combo in enumerate(combinations):
                print(f"\n[6/7] Running test {i + 1}/{len(combinations)}...")

                # Get backend config
                backend_name = (
                    list(config.get("backends", {}).keys())[0]
                    if config.get("backends")
                    else "llama.cpp"
                )
                backend_config = get_backend_config(config, backend_name)

                if not backend_config:
                    print(
                        f"      Warning: Backend '{backend_name}' not found, using default"
                    )
                    template = "llama-server --port 1234 -m /models/model.gguf {{ benchmark_params }}"
                else:
                    template = backend_config.get(
                        "command_template",
                        "llama-server --port 1234 -m /models/model.gguf {{ benchmark_params }}",
                    )

                # Render command
                rendered_command = render_command(template, combo)
                print(f"      Command: {rendered_command[:100]}...")

               if args.dry_run:
                    print(f"      [DRY RUN] Skipping execution")
                    continue

                # Create run data
                run_data = {
                    "config_hash": config_hash,
                    "model_path": model_path,
                    "model_group": group_name,
                    "backend_name": backend_name,
                    "backend_version": None,
                    "rendered_command": rendered_command,
                    "variables": combo,
                    "config_yaml": config_yaml_content,
                    "hardware_metadata": hardware_metadata,
                }

                # Start memory monitor
                print(f"      Starting memory monitor...")
                memory_monitor = MemoryMonitor(sample_interval=1.0)
                memory_monitor.start()

                try:
                    # Spawn container
                    print(f"      Spawning Docker container...")
                    container, container_ip = spawn_container(
                        image="ghcr.io/ggerganov/llama.cpp:latest",
                        command=rendered_command,
                        model_path=model_path,
                    )

                    # Wait for server
                    print(f"      Waiting for server to be ready...")
                    if not wait_for_container_ready(
                        container_ip, port=1234, timeout=60
                    ):
                        print(f"      Error: Server not ready")
                        stop_container(container)
                        continue

                    # Run inference test
                    print(f"      Running inference test...")
                    metrics = run_inference_test(
                        container_ip=container_ip,
                        port=1234,
                        ctx_size=combo.get("--ctx-size", 4096),
                        output_tokens=128,
                    )

                    # Stop memory monitor
                    memory_monitor.stop()
                    memory_stats = memory_monitor.get_peak_values()

                    # Update run data with metrics
                    run_data.update(
                        {
                            "ttft_ms": metrics.get("ttft_ms"),
                            "tpot_ms": metrics.get("tpot_ms"),
                            "throughput_toks_s": metrics.get("throughput_toks_s"),
                            "peak_vram_mb": memory_stats.get("peak_vram_mb"),
                            "peak_system_ram_mb": memory_stats.get(
                                "peak_system_ram_mb"
                            ),
                        }
                    )

                    # Store in database
                    print(f"      Storing results in database...")
                    benchmark_id = insert_benchmark(conn, run_data)
                    print(f"      Benchmark ID: {benchmark_id}")

                    # Clean up container
                    print(f"      Stopping container...")
                    stop_container(container)

                    print(f"      Success!")

                except Exception as e:
                    print(f"      Error: {e}")
                    memory_monitor.stop()

                print(f"\n      Test {i + 1}/{len(combinations)} complete")

    # Close database connection
    conn.close()

    print("\n" + "=" * 60)
    print("Benchmark suite complete!")
    print(f"Results stored in: {db_path}")
    print("=" * 60)


def launch_ui(db_path: str) -> None:
    """
    Launch Web UI.

    Args:
        db_path: Path to SQLite database
    """
    import streamlit

    print(f"\n[1/2] Launching Web UI...")
    print(f"      Database: {db_path}")

    # Import and run Streamlit dashboard
    from ui.dashboard import run_dashboard

    run_dashboard(db_path)


def main():
    """Main entry point."""
    args = parse_args()

    # Check if config exists
    if not Path(args.config).exists():
        print(f"Error: Configuration file not found: {args.config}")
        sys.exit(1)

    if args.ui:
        # Launch Web UI
        if not Path(args.db).exists():
            print(f"Error: Database not found: {args.db}")
            print("Run benchmarks first to generate results.")
            sys.exit(1)

        launch_ui(args.db)
    else:
        # Run benchmarks
        run_benchmark(args.config, args.db)


if __name__ == "__main__":
    main()
