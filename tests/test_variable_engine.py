"""
Tests for Variable Engine - Length-based branching logic.
"""

import unittest
from core.variable_engine import (
    is_static_variable,
    classify_variables,
    get_variable_type,
)


class TestVariableEngine(unittest.TestCase):
    def test_is_static_variable_single_element(self):
        """Test that single-element list is static."""
        self.assertTrue(is_static_variable([4096]))
        self.assertTrue(is_static_variable([True]))
        self.assertTrue(is_static_variable([512]))

    def test_is_static_variable_multi_element(self):
        """Test that multi-element list is a dimension."""
        self.assertFalse(is_static_variable([4096, 8192]))
        self.assertFalse(is_static_variable([True, False]))
        self.assertFalse(is_static_variable([1, 2, 3]))

    def test_is_static_variable_non_list(self):
        """Test that non-list values are static."""
        self.assertTrue(is_static_variable(4096))
        self.assertTrue(is_static_variable("string"))
        self.assertTrue(is_static_variable(True))

    def test_classify_variables(self):
        """Test variable classification into static and dimensions."""
        variables = {
            "--ctx-size": [4096, 8192],  # dimension
            "--batch-size": [512],  # static
            "--flash-attn": [True, False],  # dimension
            "--n-predict": 128,  # static (non-list)
        }

        static, dimensions = classify_variables(variables)

        # Check static variables
        self.assertIn("--batch-size", static)
        self.assertEqual(static["--batch-size"], [512])
        self.assertIn("--n-predict", static)
        self.assertEqual(static["--n-predict"], 128)

        # Check dimension variables
        self.assertIn("--ctx-size", dimensions)
        self.assertEqual(dimensions["--ctx-size"], [4096, 8192])
        self.assertIn("--flash-attn", dimensions)
        self.assertEqual(dimensions["--flash-attn"], [True, False])

        # Check lengths
        self.assertEqual(len(static), 2)
        self.assertEqual(len(dimensions), 2)


if __name__ == "__main__":
    unittest.main()
