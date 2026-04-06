"""
Docker Runner - Container spawning, IP detection, and cleanup.

Spawns fresh Docker containers per test combination and detects container IP
for API requests.
"""

import docker
import subprocess
import time
import re
from typing import Optional, Dict, Any, Tuple
from pathlib import Path


def get_docker_client():
    """
    Get Docker client instance.

    Returns:
        Docker client object
    """
    return docker.from_env()


def spawn_container(
    image: str, command: str, model_path: str, container_name: Optional[str] = None
) -> Tuple[Any, str]:
    """
    Spawn a fresh Docker container for benchmark execution.

    Args:
        image: Docker image name (e.g., "llama.cpp:latest")
        command: Command to execute inside container
        model_path: Local path to model file (will be bind-mounted)
        container_name: Optional custom container name

    Returns:
        Tuple of (container_object, container_ip)
    """
    client = get_docker_client()

    # Get absolute path to model
    model_abs_path = Path(model_path).resolve()
    model_dir = str(model_abs_path.parent)
    model_file = model_abs_path.name

    # Generate container name if not provided
    if not container_name:
        container_name = f"crossbench-{int(time.time())}"

    # Bind mount model directory
    volumes = {
        model_dir: {
            "bind": "/models",
            "mode": "ro",  # Read-only
        }
    }

    # Create and start container
    try:
        container = client.containers.run(
            image,
            command=command,
            name=container_name,
            volumes=volumes,
            detach=True,
            remove=True,
            network_mode="host",  # Use host network for easy access
        )

        # Wait for container to start
        time.sleep(2)

        # Detect container IP
        container_ip = detect_container_ip(container)

        return container, container_ip

    except docker.errors.NotFound as e:
        raise RuntimeError(f"Docker image not found: {image}. Error: {e}")
    except docker.errors.ImageNotFound as e:
        raise RuntimeError(f"Docker image not found: {image}. Error: {e}")
    except docker.errors.APIError as e:
        raise RuntimeError(f"Docker API error: {e}")


def detect_container_ip(container) -> str:
    """
    Detect IP address of a running container.

    Args:
        container: Docker container object

    Returns:
        Container IP address string
    """
    try:
        # Use Docker inspect to get IP
        inspect_data = container.attrs
        networks = inspect_data.get("NetworkSettings", {}).get("Networks", {})

        # Try host network first
        if "host" in networks:
            return networks["host"].get("IPAddress", "127.0.0.1")

        # Fall back to first available network
        for network_name, network_config in networks.items():
            ip = network_config.get("IPAddress")
            if ip:
                return ip

        # Final fallback
        return "127.0.0.1"

    except Exception as e:
        print(f"Warning: Could not detect container IP: {e}")
        return "127.0.0.1"


def wait_for_container_ready(
    container_ip: str, port: int = 1234, timeout: int = 30, check_interval: float = 1.0
) -> bool:
    """
    Wait for container's API to be ready.

    Args:
        container_ip: Container IP address
        port: Port to check (default: 1234 for llama-server)
        timeout: Maximum time to wait in seconds
        check_interval: Time between checks in seconds

    Returns:
        True if container is ready, False if timeout
    """
    import urllib.request

    start_time = time.time()
    check_url = f"http://{container_ip}:{port}/health"

    while time.time() - start_time < timeout:
        try:
            # Try to connect to container's API
            request = urllib.request.Request(check_url, method="GET")
            response = urllib.request.urlopen(request, timeout=2)

            if response.status == 200:
                return True

        except Exception:
            pass  # Container not ready yet

        time.sleep(check_interval)

    return False


def stop_container(container) -> bool:
    """
    Stop and remove a container.

    Args:
        container: Docker container object

    Returns:
        True if successful, False if error
    """
    try:
        container.stop(timeout=10)
        container.remove()
        return True
    except Exception as e:
        print(f"Error stopping container: {e}")
        return False


def get_container_logs(container) -> str:
    """
    Get logs from a container.

    Args:
        container: Docker container object

    Returns:
        Container logs as string
    """
    try:
        return container.logs().decode("utf-8")
    except Exception as e:
        print(f"Error getting container logs: {e}")
        return ""


def run_command_in_container(container, command: str) -> Tuple[int, str, str]:
    """
    Run a command inside a running container.

    Args:
        container: Docker container object
        command: Command to execute

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    try:
        result = container.exec_run(command)
        return result.exit_code, result.output.decode("utf-8"), ""
    except Exception as e:
        return -1, "", str(e)


def get_docker_memory_stats(container) -> Dict[str, float]:
    """
    Get memory statistics from a container.

    Args:
        container: Docker container object

    Returns:
        Dictionary with memory stats
    """
    try:
        stats = container.stats(stream=False)
        mem_stats = stats.get("memory", {})

        return {
            "current_mb": mem_stats.get("usage", 0) / (1024 * 1024),
            "limit_mb": mem_stats.get("limit", 0) / (1024 * 1024),
            "percent": mem_stats.get("percent", 0),
        }
    except Exception as e:
        print(f"Error getting Docker memory stats: {e}")
        return {"current_mb": 0.0, "limit_mb": 0.0, "percent": 0.0}


def get_vram_usage_in_container(container) -> float:
    """
    Get VRAM usage by running rocm-smi inside container.

    Args:
        container: Docker container object

    Returns:
        VRAM usage in MB, or 0.0 if not available
    """
    exit_code, output, error = run_command_in_container(
        container, "rocm-smi --query-memory-used"
    )

    if exit_code == 0:
        # Parse output
        match = re.search(r"(\d+(?:\.\d+)?)\s*MB", output)
        if match:
            return float(match.group(1))

    return 0.0
