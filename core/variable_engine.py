"""
Variable Engine - Core logic for length-based branching and variable classification.

The variable engine implements the "One Field Rule":
- Single element list [value] = Static Parameter (no iteration)
- Multi element list [val1, val2] = Benchmark Dimension (triggers iteration)
"""

from typing import Dict, List, Tuple, Any


def is_static_variable(value: Any) -> bool:
    """
    Check if a variable is static (single element) or a dimension (multi-element).

    Args:
        value: The variable value to check

    Returns:
        True if static (len == 1), False if dimension (len > 1)
    """
    if not isinstance(value, list):
        return True  # Non-list values are treated as static

    return len(value) == 1


def classify_variables(
    variables_dict: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Classify all variables into static and dimension categories.

    Args:
        variables_dict: Dictionary of all variables

    Returns:
        Tuple of (static_variables, dimension_variables)
    """
    static_variables = {}
    dimension_variables = {}

    for key, value in variables_dict.items():
        if is_static_variable(value):
            static_variables[key] = value
        else:
            dimension_variables[key] = value

    return static_variables, dimension_variables


def get_variable_type(variables_dict: Dict[str, Any]) -> Dict[str, str]:
    """
    Get the type classification for each variable.

    Args:
        variables_dict: Dictionary of all variables

    Returns:
        Dictionary mapping variable names to their type ('static' or 'dimension')
    """
    variable_types = {}

    for key, value in variables_dict.items():
        if is_static_variable(value):
            variable_types[key] = "static"
        else:
            variable_types[key] = "dimension"

    return variable_types


def extract_unique_values(variables_dict: Dict[str, Any]) -> Dict[str, List[Any]]:
    """
    Extract unique values from dimension variables for UI display.

    Args:
        variables_dict: Dictionary of all variables

    Returns:
        Dictionary mapping dimension variable names to their unique values
    """
    unique_values = {}

    for key, value in variables_dict.items():
        if isinstance(value, list) and len(value) > 1:
            unique_values[key] = value

    return unique_values
