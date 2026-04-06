"""
Tests for Config Module - YAML parsing and hierarchy resolution.
"""

import unittest
import tempfile
import os
from core.config import load_config, deep_merge_dict, resolve_hierarchy


class TestConfigModule(unittest.TestCase):
    def setUp(self):
        """Create test config files."""
        self.test_configs = {
            "simple": """
variables:
  --ctx-size: [4096, 8192]
  --batch-size: [512]
""",
            "hierarchy": """
variables:
  --ctx-size: [4096]
  --batch-size: [256]

model_groups:
  dense_models:
    path: ./models/dense/
    variables:
      --batch-size: [512]
      --n-gpu-layers: [35]

backends:
  llama.cpp:
    command_template: llama-server {{ benchmark_params }}
    variables:
      --batch-size: [1024]
      --flash-attn: [true, false]
""",
        }

        self.temp_files = {}
        for name, content in self.test_configs.items():
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as f:
                f.write(content)
                self.temp_files[name] = f.name

    def tearDown(self):
        """Clean up temp files."""
        for path in self.temp_files.values():
            os.unlink(path)

    def test_load_config(self):
        """Test loading configuration from file."""
        config = load_config(self.temp_files["simple"])

        self.assertIn("variables", config)
        self.assertIn("--ctx-size", config["variables"])
        self.assertEqual(config["variables"]["--ctx-size"], [4096, 8192])

    def test_deep_merge_dict(self):
        """Test deep merge of dictionaries."""
        base = {"a": 1, "b": {"x": 10, "y": 20}, "c": [1, 2, 3]}

        override = {"b": {"y": 200, "z": 30}, "d": 4}

        result = deep_merge_dict(base, override)

        self.assertEqual(result["a"], 1)
        self.assertEqual(result["b"]["x"], 10)
        self.assertEqual(result["b"]["y"], 200)  # overridden
        self.assertEqual(result["b"]["z"], 30)  # new
        self.assertEqual(result["c"], [1, 2, 3])
        self.assertEqual(result["d"], 4)

    def test_resolve_hierarchy(self):
        """Test variable hierarchy resolution."""
        config = load_config(self.temp_files["hierarchy"])

        resolved = resolve_hierarchy(config)

        # Global variables
        self.assertIn("--ctx-size", resolved)
        self.assertEqual(resolved["--ctx-size"], [4096])

        # Model group overrides global
        self.assertIn("--batch-size", resolved)
        # Model group sets 512, but backend group sets 1024, so final should be 1024
        self.assertEqual(resolved["--batch-size"], [1024])

        # Backend group variables
        self.assertIn("--flash-attn", resolved)
        self.assertEqual(resolved["--flash-attn"], [true, false])


if __name__ == "__main__":
    unittest.main()
