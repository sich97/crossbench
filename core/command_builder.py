"""
Command Builder - Dynamic command construction with {{ benchmark_params }} placeholder injection.

Transforms resolved variables into CLI strings for llama-server execution.
"""

from typing import Dict, Any


def variables_to_flags(variables_dict: Dict[str, Any]) -> str:
    """
    Convert variable dictionary to space-separated CLI flags.

    Args:
        variables_dict: Dictionary of variables (e.g., {"--ctx-size": 4096})

    Returns:
        Space-separated string of flags (e.g., "--ctx-size 4096")
    """
    flags = []

    for key, value in variables_dict.items():
        # Handle boolean values
        if isinstance(value, bool):
            if value:
                flags.append(key)
        # Handle list values (unwrap single-element lists)
        elif isinstance(value, list):
            if len(value) == 1:
                flags.append(f"{key} {value[0]}")
            else:
                # For multi-element lists, use the first value or join them
                flags.append(f"{key} {value[0]}")
        # Handle other values
        else:
            flags.append(f"{key} {value}")

    return " ".join(flags)


def render_command(template: str, variables_dict: Dict[str, Any]) -> str:
    """
    Render benchmark command by injecting variables into template.

    Args:
        template: Command template with {{ benchmark_params }} placeholder
        variables_dict: Dictionary of resolved variables

    Returns:
        Fully rendered command string
    """
    benchmark_params = variables_to_flags(variables_dict)
    command = template.replace("{{ benchmark_params }}", benchmark_params)

    return command


def build_llama_server_command(
    template: str, model_path: str, variables_dict: Dict[str, Any]
) -> str:
    """
    Build complete llama-server command with model path and variables.

    Note: The model path is often hardcoded in templates because it's
    expected to be bind-mounted via Docker.

    Args:
        template: Command template (may or may not include -m flag)
        model_path: Path to model file (for reference, usually in template)
        variables_dict: Dictionary of resolved variables

    Returns:
        Complete executable command string
    """
    command = render_command(template, variables_dict)

    return command
