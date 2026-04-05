"""
Config Hasher - Generate SHA-256 hash of configuration files for reproducibility.

Ensures every benchmark run can be traced back to its exact configuration.
"""

import hashlib
from pathlib import Path
from typing import Optional


def hash_config_file(config_path: str) -> str:
    """
    Generate SHA-256 hash of a configuration YAML file.

    Args:
        config_path: Path to the config.yaml file

    Returns:
        Hexadecimal SHA-256 hash string
    """
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path, "rb") as f:
        file_content = f.read()

    hash_object = hashlib.sha256(file_content)
    return hash_object.hexdigest()


def hash_config_content(config_content: str) -> str:
    """
    Generate SHA-256 hash of configuration content (string).

    Args:
        config_content: YAML configuration as string

    Returns:
        Hexadecimal SHA-256 hash string
    """
    hash_object = hashlib.sha256(config_content.encode("utf-8"))
    return hash_object.hexdigest()


def verify_config_integrity(config_path: str, expected_hash: str) -> bool:
    """
    Verify that a configuration file matches an expected hash.

    Args:
        config_path: Path to the config.yaml file
        expected_hash: Expected SHA-256 hash

    Returns:
        True if hash matches, False otherwise
    """
    try:
        actual_hash = hash_config_file(config_path)
        return actual_hash == expected_hash
    except Exception:
        return False


def generate_run_identifier(config_hash: str, model_path: str, variables: dict) -> str:
    """
    Generate a unique run identifier from config hash and variables.

    Args:
        config_hash: SHA-256 hash of config file
        model_path: Path to model file
        variables: Dictionary of benchmark variables

    Returns:
        Unique run identifier string
    """
    import json

    # Create deterministic string from variables
    var_string = json.dumps(variables, sort_keys=True)

    # Combine and hash again for unique identifier
    combined = f"{config_hash}:{model_path}:{var_string}"
    run_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]

    return run_hash
