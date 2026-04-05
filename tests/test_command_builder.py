"""
Tests for Command Builder - Dynamic command construction.
"""

import unittest
from core.command_builder import variables_to_flags, render_command


class TestCommandBuilder(unittest.TestCase):
    def test_variables_to_flags_simple(self):
        """Test simple variable to flags conversion."""
        variables = {"--ctx-size": 4096, "--batch-size": 512}

        result = variables_to_flags(variables)

        self.assertIn("--ctx-size 4096", result)
        self.assertIn("--batch-size 512", result)

    def test_variables_to_flags_boolean_true(self):
        """Test boolean true values."""
        variables = {"--flash-attn": True}

        result = variables_to_flags(variables)

        self.assertEqual(result, "--flash-attn")

    def test_variables_to_flags_boolean_false(self):
        """Test boolean false values."""
        variables = {"--flash-attn": False}

        result = variables_to_flags(variables)

        self.assertEqual(result, "")

    def test_variables_to_flags_list_single(self):
        """Test single-element list."""
        variables = {"--ctx-size": [4096]}

        result = variables_to_flags(variables)

        self.assertIn("--ctx-size 4096", result)

    def test_render_command(self):
        """Test template rendering with placeholder."""
        template = (
            "llama-server --port 1234 -m /models/model.gguf {{ benchmark_params }}"
        )

        variables = {"--ctx-size": 8192, "--batch-size": 2048, "--flash-attn": True}

        result = render_command(template, variables)

        expected = "llama-server --port 1234 -m /models/model.gguf --ctx-size 8192 --batch-size 2048 --flash-attn"
        self.assertEqual(result, expected)

    def test_render_command_empty_variables(self):
        """Test rendering with no variables."""
        template = (
            "llama-server --port 1234 -m /models/model.gguf {{ benchmark_params }}"
        )

        variables = {}

        result = render_command(template, variables)

        self.assertEqual(result, template.replace("{{ benchmark_params }}", ""))


if __name__ == "__main__":
    unittest.main()
