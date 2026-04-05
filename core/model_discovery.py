"""
Model Discovery - Folder-based discovery of .gguf model files.

Discovers models via simple folder organization without regex or pattern matching.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import os


def discover_models(group_path: str) -> List[Dict[str, str]]:
    """
    Discover all .gguf model files in a given directory.

    Args:
        group_path: Path to model group directory (e.g., ./models/dense/)

    Returns:
        List of model dictionaries with 'path' and 'name' keys
    """
    models = []
    path = Path(group_path)

    if not path.exists():
        print(f"Warning: Model group path does not exist: {group_path}")
        return models

    if not path.is_dir():
        print(f"Warning: Model group path is not a directory: {group_path}")
        return models

    # Find all .gguf files (case-insensitive)
    for file_path in path.rglob("*.gguf"):
        if file_path.is_file():
            model_info = {
                "path": str(file_path.resolve()),
                "name": file_path.stem,  # Filename without extension
                "filename": file_path.name,
            }
            models.append(model_info)

    # Find all .GGUF files (uppercase)
    for file_path in path.rglob("*.GGUF"):
        if file_path.is_file():
            model_info = {
                "path": str(file_path.resolve()),
                "name": file_path.stem,
                "filename": file_path.name,
            }
            models.append(model_info)

    return models


def get_model_metadata(model_path: str) -> Optional[Dict[str, Any]]:
    """
    Get metadata for a model file.

    Args:
        model_path: Path to the .gguf model file

    Returns:
        Dictionary with model metadata or None if not available
    """
    metadata = {
        "path": model_path,
        "name": Path(model_path).stem,
        "size_bytes": 0,
        "exists": False,
    }

    path = Path(model_path)

    if not path.exists():
        return metadata

    metadata["exists"] = True
    metadata["size_bytes"] = path.stat().st_size
    metadata["size_mb"] = metadata["size_bytes"] / (1024 * 1024)

    # Try to extract architecture from filename
    name_lower = metadata["name"].lower()

    if "moe" in name_lower or "mixtral" in name_lower:
        metadata["architecture"] = "moe"
    elif "llama" in name_lower:
        metadata["architecture"] = "llama"
    elif "gpt" in name_lower:
        metadata["architecture"] = "gpt"
    elif "glm" in name_lower:
        metadata["architecture"] = "glm"
    elif "qwen" in name_lower:
        metadata["architecture"] = "qwen"
    else:
        metadata["architecture"] = "unknown"

    return metadata


def discover_all_models(
    model_groups: Dict[str, Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Discover models across all model groups.

    Args:
        model_groups: Dictionary of model group configurations

    Returns:
        Dictionary mapping group names to lists of models
    """
    all_models = {}

    for group_name, group_config in model_groups.items():
        group_path = group_config.get("path", "")

        if group_path:
            models = discover_models(group_path)
            all_models[group_name] = models
        else:
            all_models[group_name] = []

    return all_models


def validate_model_groups(
    model_groups: Dict[str, Dict[str, Any]],
) -> Dict[str, List[str]]:
    """
    Validate model group paths and report issues.

    Args:
        model_groups: Dictionary of model group configurations

    Returns:
        Dictionary with validation results
    """
    validation = {"valid_groups": [], "invalid_groups": [], "empty_groups": []}

    for group_name, group_config in model_groups.items():
        group_path = group_config.get("path", "")

        if not group_path:
            validation["invalid_groups"].append(group_name)
            continue

        path = Path(group_path)

        if not path.exists():
            validation["invalid_groups"].append(group_name)
            continue

        if not path.is_dir():
            validation["invalid_groups"].append(group_name)
            continue

        # Check for .gguf files
        gguf_files = list(path.rglob("*.gguf"))

        if len(gguf_files) == 0:
            validation["empty_groups"].append(group_name)
        else:
            validation["valid_groups"].append(group_name)

    return validation
