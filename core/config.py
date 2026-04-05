"""
Configuration Module - YAML parsing and hierarchy resolution.

Implements the Override Cascade:
1. Backend Version (highest priority)
2. Backend Group
3. Model Group
4. Global (lowest priority)
"""

import yaml
from typing import Dict, Any, Optional, Tuple
from pathlib import Path


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load and parse the configuration YAML file.

    Args:
        config_path: Path to the config.yaml file

    Returns:
        Parsed configuration as dictionary
    """
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    return config


def deep_merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with override taking precedence.

    Args:
        base: Base dictionary
        override: Override dictionary (highest priority)

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dict(result[key], value)
        else:
            result[key] = value

    return result


def resolve_hierarchy(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve variable hierarchy from Global → Model Group → Backend Group → Backend Version.

    The most specific definition always wins.

    Args:
        config: Parsed configuration dictionary

    Returns:
        Resolved variable dictionary with all overrides applied
    """
    # Start with global variables (lowest priority)
    resolved = config.get("variables", {})

    # Apply model group variables
    model_groups = config.get("model_groups", {})
    for group_name, group_config in model_groups.items():
        group_vars = group_config.get("variables", {})
        resolved = deep_merge_dict(resolved, group_vars)

    # Apply backend group variables
    backends = config.get("backends", {})
    for backend_name, backend_config in backends.items():
        backend_vars = backend_config.get("variables", {})
        resolved = deep_merge_dict(resolved, backend_vars)

    # Apply backend version variables (highest priority)
    backend_versions = config.get("backend_versions", {})
    for version_name, version_config in backend_versions.items():
        version_vars = version_config.get("variables", {})
        resolved = deep_merge_dict(resolved, version_vars)

    return resolved


def get_backend_config(
    config: Dict[str, Any], backend_name: str
) -> Optional[Dict[str, Any]]:
    """
    Get configuration for a specific backend.

    Args:
        config: Parsed configuration dictionary
        backend_name: Name of the backend (e.g., 'llama.cpp')

    Returns:
        Backend configuration dictionary or None if not found
    """
    backends = config.get("backends", {})
    return backends.get(backend_name)


def get_model_group_config(
    config: Dict[str, Any], group_name: str
) -> Optional[Dict[str, Any]]:
    """
    Get configuration for a specific model group.

    Args:
        config: Parsed configuration dictionary
        group_name: Name of the model group

    Returns:
        Model group configuration dictionary or None if not found
    """
    model_groups = config.get("model_groups", {})
    return model_groups.get(group_name)


def get_all_backend_names(config: Dict[str, Any]) -> list:
    """
    Get list of all backend names from configuration.

    Args:
        config: Parsed configuration dictionary

    Returns:
        List of backend names
    """
    backends = config.get("backends", {})
    return list(backends.keys())


def get_all_model_groups(config: Dict[str, Any]) -> list:
    """
    Get list of all model group names from configuration.

    Args:
        config: Parsed configuration dictionary

    Returns:
        List of model group names
    """
    model_groups = config.get("model_groups", {})
    return list(model_groups.keys())
