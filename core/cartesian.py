"""
Cartesian Product Generator - Creates all test run combinations from benchmark dimensions.

For each model, the framework:
1. Collects variables from all hierarchy levels
2. Expands multi-element lists into all combinations
3. Attaches static variables to each combination
"""

from typing import Dict, List, Any
from itertools import product


def generate_combinations(
    dimension_variables: Dict[str, List[Any]],
) -> List[Dict[str, Any]]:
    """
    Generate all combinations from dimension variables using Cartesian product.

    Args:
        dimension_variables: Dictionary of dimension variables (multi-element lists)

    Returns:
        List of dictionaries, each representing one test run combination
    """
    if not dimension_variables:
        return [{}]

    # Get variable names and their values
    var_names = list(dimension_variables.keys())
    var_values = list(dimension_variables.values())

    # Generate Cartesian product
    combinations = []
    for combo in product(*var_values):
        combination = dict(zip(var_names, combo))
        combinations.append(combination)

    return combinations


def group_static_variables(
    static_variables: Dict[str, Any], combinations: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Attach static variables to each combination.

    Args:
        static_variables: Dictionary of static variables (single element or non-list)
        combinations: List of dimension combinations

    Returns:
        List of complete variable dictionaries with static variables attached
    """
    if not combinations:
        combinations = [{}]

    # If static_variables is empty, just return combinations
    if not static_variables:
        return combinations

    # Attach static variables to each combination
    for i in range(len(combinations)):
        for key, value in static_variables.items():
            # Unwrap single-element lists
            if isinstance(value, list) and len(value) == 1:
                combinations[i][key] = value[0]
            else:
                combinations[i][key] = value

    return combinations


def expand_all_variables(variables_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Expand all variables into complete test run combinations.

    This is the main entry point for variable expansion.

    Args:
        variables_dict: Dictionary of all variables (mixed static and dimensions)

    Returns:
        List of complete variable dictionaries for each test run
    """
    from .variable_engine import classify_variables

    # Classify variables into static and dimensions
    static_variables, dimension_variables = classify_variables(variables_dict)

    # Generate combinations for dimensions
    combinations = generate_combinations(dimension_variables)

    # Attach static variables to each combination
    complete_variables = group_static_variables(static_variables, combinations)

    return complete_variables
