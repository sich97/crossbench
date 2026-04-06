"""
Tests for Cartesian Product Generator - Multi-value expansion.
"""

import unittest
from core.cartesian import (
    generate_combinations,
    group_static_variables,
    expand_all_variables,
)


class TestCartesianProduct(unittest.TestCase):
    def test_generate_combinations_single_dimension(self):
        """Test generation with single dimension variable."""
        dimensions = {"--ctx-size": [4096, 8192]}

        combinations = generate_combinations(dimensions)

        self.assertEqual(len(combinations), 2)
        self.assertIn({"--ctx-size": 4096}, combinations)
        self.assertIn({"--ctx-size": 8192}, combinations)

    def test_generate_combinations_multiple_dimensions(self):
        """Test generation with multiple dimension variables."""
        dimensions = {"--ctx-size": [4096, 8192], "--flash-attn": [True, False]}

        combinations = generate_combinations(dimensions)

        self.assertEqual(len(combinations), 4)
        self.assertIn({"--ctx-size": 4096, "--flash-attn": True}, combinations)
        self.assertIn({"--ctx-size": 4096, "--flash-attn": False}, combinations)
        self.assertIn({"--ctx-size": 8192, "--flash-attn": True}, combinations)
        self.assertIn({"--ctx-size": 8192, "--flash-attn": False}, combinations)

    def test_generate_combinations_empty(self):
        """Test generation with no dimensions."""
        dimensions = {}

        combinations = generate_combinations(dimensions)

        self.assertEqual(len(combinations), 1)
        self.assertEqual(combinations[0], {})

    def test_group_static_variables(self):
        """Test attaching static variables to combinations."""
        static = {"--batch-size": [512], "--n-predict": 128}

        combinations = [{"--ctx-size": 4096}, {"--ctx-size": 8192}]

        result = group_static_variables(static, combinations)

        self.assertEqual(len(result), 2)
        self.assertIn("--batch-size", result[0])
        self.assertEqual(result[0]["--batch-size"], 512)
        self.assertIn("--n-predict", result[0])
        self.assertEqual(result[0]["--n-predict"], 128)

    def test_expand_all_variables(self):
        """Test full variable expansion."""
        variables = {
            "--ctx-size": [4096, 8192],  # dimension
            "--batch-size": [512],  # static
            "--flash-attn": [True, False],  # dimension
            "--n-predict": 128,  # static
        }

        combinations = expand_all_variables(variables)

        # Should have 4 combinations (2 x 2)
        self.assertEqual(len(combinations), 4)

        # Each should have all variables
        for combo in combinations:
            self.assertIn("--ctx-size", combo)
            self.assertIn("--batch-size", combo)
            self.assertIn("--flash-attn", combo)
            self.assertIn("--n-predict", combo)

            # Static variables should be unwrapped
            self.assertEqual(combo["--batch-size"], 512)
            self.assertEqual(combo["--n-predict"], 128)


if __name__ == "__main__":
    unittest.main()
