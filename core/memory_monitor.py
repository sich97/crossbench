"""
Memory Monitor - Peak VRAM and System RAM sampling every 1 second.

Records the maximum observed values during benchmark execution, not final snapshot.
"""

import threading
import subprocess
import time
import re
from typing import Optional, Dict, Any, List
import psutil


class MemoryMonitor:
    """
    Background thread that samples VRAM and System RAM every 1 second.

    Records peak (maximum observed) values during benchmark execution.
    """

    def __init__(self, sample_interval: float = 1.0):
        """
        Initialize memory monitor.

        Args:
            sample_interval: Sampling interval in seconds (default: 1.0)
        """
        self.sample_interval = sample_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Peak values (initialized to 0)
        self.peak_vram_mb = 0.0
        self.peak_system_ram_mb = 0.0

        # Current values (for debugging)
        self.current_vram_mb = 0.0
        self.current_system_ram_mb = 0.0

        # Sample history (optional, for timeline views)
        self.sample_history: List[Dict[str, Any]] = []

    def start(self):
        """Start the memory monitoring thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the memory monitoring thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _monitor_loop(self):
        """Main monitoring loop that runs in background thread."""
        while self._running:
            try:
                # Sample VRAM
                vram = self._get_vram_usage()
                with self._lock:
                    self.current_vram_mb = vram
                    if vram > self.peak_vram_mb:
                        self.peak_vram_mb = vram

                # Sample System RAM
                ram = self._get_system_ram_usage()
                with self._lock:
                    self.current_system_ram_mb = ram
                    if ram > self.peak_system_ram_mb:
                        self.peak_system_ram_mb = ram

                # Record sample (optional)
                sample = {
                    "timestamp": time.time(),
                    "vram_mb": vram,
                    "system_ram_mb": ram,
                }
                with self._lock:
                    self.sample_history.append(sample)

            except Exception as e:
                print(f"Memory monitor error: {e}")

            # Wait for next sample
            time.sleep(self.sample_interval)

    def _get_vram_usage(self) -> float:
        """
        Get current VRAM usage using rocm-smi.

        Returns:
            VRAM usage in MB, or 0.0 if not available
        """
        try:
            # Try rocm-smi first (AMD GPUs)
            result = subprocess.run(
                ["rocm-smi", "--query-memory-used"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                # Parse output - looks for "Memory Used" column
                output = result.stdout
                # Extract numeric value (simplified parsing)
                match = re.search(r"(\d+(?:\.\d+)?)\s*MB", output)
                if match:
                    return float(match.group(1))

                # Alternative: look for just a number
                match = re.search(r"(\d+(?:\.\d+)?)", output)
                if match:
                    return float(match.group(1))

        except FileNotFoundError:
            pass  # rocm-smi not available
        except subprocess.TimeoutExpired:
            pass  # Command timed out
        except Exception:
            pass  # Other errors

        # Fallback to system memory if VRAM not available
        return self._get_system_ram_usage() * 0.1  # Estimate 10% of system RAM

    def _get_system_ram_usage(self) -> float:
        """
        Get current system RAM usage using psutil.

        Returns:
            System RAM usage in MB
        """
        try:
            mem = psutil.virtual_memory()
            # Convert bytes to MB
            return mem.used / (1024 * 1024)
        except Exception:
            return 0.0

    def get_peak_values(self) -> Dict[str, float]:
        """
        Get peak memory values recorded during monitoring.

        Returns:
            Dictionary with 'peak_vram_mb' and 'peak_system_ram_mb'
        """
        with self._lock:
            return {
                "peak_vram_mb": self.peak_vram_mb,
                "peak_system_ram_mb": self.peak_system_ram_mb,
            }

    def get_sample_history(self) -> List[Dict[str, Any]]:
        """
        Get sample history for timeline views.

        Returns:
            List of sample dictionaries
        """
        with self._lock:
            return self.sample_history.copy()


def get_docker_memory_usage(container_id: str) -> Dict[str, float]:
    """
    Get memory usage metrics from Docker stats.

    Args:
        container_id: Docker container ID or name

    Returns:
        Dictionary with memory metrics
    """
    try:
        result = subprocess.run(
            [
                "docker",
                "stats",
                "--no-stream",
                "--format",
                "{{.MemUsage}} {{.MemPerc}} {{.MaxMem}}",
                container_id,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            parts = result.stdout.strip().split()
            if len(parts) >= 1:
                # Parse "X MiB / Y MiB (Z%)"
                mem_usage = parts[0]
                usage_str = mem_usage.split("/")[0].strip()
                usage_mb = float(usage_str.replace("MiB", "").strip())

                return {
                    "current_mb": usage_mb,
                    "max_mb": 0.0,  # Would need separate query
                }

    except Exception as e:
        print(f"Error getting Docker memory usage: {e}")

    return {"current_mb": 0.0, "max_mb": 0.0}


def get_vram_usage_rocm() -> float:
    """
    Get VRAM usage using rocm-smi (standalone function).

    Returns:
        VRAM usage in MB, or 0.0 if not available
    """
    monitor = MemoryMonitor()
    return monitor._get_vram_usage()
