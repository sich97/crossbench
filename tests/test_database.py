"""
Tests for Database Module - SQLite storage and queries.
"""

import unittest
import tempfile
import os
import json
from storage.database import (
    init_database,
    hash_config_file,
    insert_benchmark,
    query_benchmarks,
    get_hardware_metadata,
)


class TestDatabaseModule(unittest.TestCase):
    def setUp(self):
        """Create temporary database."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()

        self.conn = init_database(self.temp_db.name)

    def tearDown(self):
        """Clean up database."""
        self.conn.close()
        os.unlink(self.temp_db.name)

    def test_init_database(self):
        """Test database initialization."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='benchmarks'"
        )

        result = cursor.fetchone()
        self.assertIsNotNone(result)

    def test_hash_config_file(self):
        """Test config file hashing."""
        # Create temp config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("variables:\n  --ctx-size: [4096]\n")
            temp_config = f.name

        try:
            hash1 = hash_config_file(temp_config)
            hash2 = hash_config_file(temp_config)

            # Same file should produce same hash
            self.assertEqual(hash1, hash2)
            self.assertEqual(len(hash1), 64)  # SHA-256 produces 64 hex characters
        finally:
            os.unlink(temp_config)

    def test_insert_benchmark(self):
        """Test inserting benchmark data."""
        run_data = {
            "config_hash": "abc123",
            "model_path": "/models/llama-2-7b.gguf",
            "model_group": "dense_models",
            "backend_name": "llama.cpp",
            "backend_version": "v0.36-cuda",
            "rendered_command": "llama-server --port 1234 --ctx-size 4096",
            "variables": {"--ctx-size": 4096, "--batch-size": 512},
            "config_yaml": "variables:\n  --ctx-size: [4096]",
            "ttft_ms": 150.5,
            "tpot_ms": 45.2,
            "throughput_toks_s": 22.1,
            "peak_vram_mb": 4096.0,
            "peak_system_ram_mb": 8192.0,
            "hardware_metadata": {"cpu_count": 8, "ram_total_mb": 16384},
        }

        benchmark_id = insert_benchmark(self.conn, run_data)

        self.assertIsInstance(benchmark_id, int)
        self.assertGreater(benchmark_id, 0)

    def test_query_benchmarks(self):
        """Test querying benchmark data."""
        # Insert test data
        run_data = {
            "config_hash": "test123",
            "model_path": "/models/test.gguf",
            "model_group": "dense_models",
            "backend_name": "llama.cpp",
            "rendered_command": "test command",
            "variables": {"--ctx-size": 4096},
            "config_yaml": "test",
            "ttft_ms": 100.0,
            "tpot_ms": 30.0,
            "throughput_toks_s": 33.3,
            "peak_vram_mb": 2048.0,
            "peak_system_ram_mb": 4096.0,
        }

        insert_benchmark(self.conn, run_data)

        # Query all
        results = query_benchmarks(self.conn)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["model_group"], "dense_models")

    def test_query_benchmarks_with_filters(self):
        """Test querying with filters."""
        # Insert test data
        run_data = {
            "config_hash": "test123",
            "model_path": "/models/test.gguf",
            "model_group": "dense_models",
            "backend_name": "llama.cpp",
            "rendered_command": "test command",
            "variables": {"--ctx-size": 4096},
            "config_yaml": "test",
            "ttft_ms": 100.0,
            "tpot_ms": 30.0,
            "throughput_toks_s": 33.3,
            "peak_vram_mb": 2048.0,
            "peak_system_ram_mb": 4096.0,
        }

        insert_benchmark(self.conn, run_data)

        # Query with filter
        results = query_benchmarks(self.conn, {"model_group": "dense_models"})

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["model_group"], "dense_models")

        # Query with non-matching filter
        results = query_benchmarks(self.conn, {"model_group": "moe_models"})

        self.assertEqual(len(results), 0)

    def test_hardware_metadata(self):
        """Test hardware metadata collection."""
        metadata = get_hardware_metadata()

        self.assertIn("cpu_count", metadata)
        self.assertIn("ram_total_mb", metadata)
        self.assertIn("platform", metadata)
        self.assertGreater(metadata["cpu_count"], 0)


if __name__ == "__main__":
    unittest.main()
