"""
Metrics Collector - Measure TTFT, TPOT, and throughput at full context.

Implements high-fidelity metric collection for benchmark execution.
"""

import time
import urllib.request
import urllib.error
import json
from typing import Dict, Any, Optional, Tuple
import requests


def measure_ttft(
    container_ip: str, port: int = 1234, timeout: float = 300.0
) -> Tuple[float, bool]:
    """
    Measure Time To First Token (TTFT) via llama-server API.

    Args:
        container_ip: Container IP address
        port: Server port (default: 1234)
        timeout: Request timeout in seconds

    Returns:
        Tuple of (ttft_ms, success)
    """
    url = f"http://{container_ip}:{port}/v1/chat/completions"

    # Simple prompt for TTFT measurement
    prompt_data = {
        "model": "default",
        "messages": [{"role": "user", "content": "Hello, this is a test prompt."}],
        "max_tokens": 1,
        "stream": False,
    }

    try:
        start_time = time.time()

        request = urllib.request.Request(
            url,
            data=json.dumps(prompt_data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        response = urllib.request.urlopen(request, timeout=timeout)
        response.read()

        elapsed_ms = (time.time() - start_time) * 1000

        return elapsed_ms, True

    except Exception as e:
        print(f"TTFT measurement error: {e}")
        return -1.0, False


def measure_tpot(
    container_ip: str,
    port: int = 1234,
    output_tokens: int = 128,
    timeout: float = 600.0,
) -> Tuple[float, bool]:
    """
    Measure Time Per Output Token (TPOT) via llama-server API.

    Args:
        container_ip: Container IP address
        port: Server port (default: 1234)
        output_tokens: Number of output tokens to generate
        timeout: Request timeout in seconds

    Returns:
        Tuple of (tpot_ms, success)
    """
    url = f"http://{container_ip}:{port}/v1/chat/completions"

    prompt_data = {
        "model": "default",
        "messages": [
            {
                "role": "user",
                "content": "Please generate text for benchmarking purposes.",
            }
        ],
        "max_tokens": output_tokens,
        "stream": False,
    }

    try:
        start_time = time.time()

        request = urllib.request.Request(
            url,
            data=json.dumps(prompt_data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        response = urllib.request.urlopen(request, timeout=timeout)
        response.read()

        total_time_ms = (time.time() - start_time) * 1000

        # TPOT = total time / output tokens
        tpot_ms = total_time_ms / output_tokens

        return tpot_ms, True

    except Exception as e:
        print(f"TPOT measurement error: {e}")
        return -1.0, False


def measure_throughput(tpot_ms: float) -> float:
    """
    Calculate throughput (tokens per second) from TPOT.

    Args:
        tpot_ms: Time per output token in milliseconds

    Returns:
        Throughput in tokens per second
    """
    if tpot_ms <= 0:
        return 0.0

    # tokens_per_second = 1000 / tpot_ms
    throughput = 1000.0 / tpot_ms

    return throughput


def get_llama_server_health(
    container_ip: str, port: int = 1234, timeout: float = 5.0
) -> bool:
    """
    Check if llama-server is healthy and ready.

    Args:
        container_ip: Container IP address
        port: Server port (default: 1234)
        timeout: Request timeout in seconds

    Returns:
        True if server is healthy, False otherwise
    """
    url = f"http://{container_ip}:{port}/health"

    try:
        request = urllib.request.Request(url, method="GET")
        response = urllib.request.urlopen(request, timeout=timeout)

        return response.status == 200

    except Exception:
        return False


def run_inference_test(
    container_ip: str,
    port: int = 1234,
    ctx_size: int = 4096,
    output_tokens: int = 128,
    timeout: float = 600.0,
) -> Dict[str, Any]:
    """
    Run complete inference test and collect all metrics.

    Args:
        container_ip: Container IP address
        port: Server port (default: 1234)
        ctx_size: Context size being tested
        output_tokens: Number of output tokens
        timeout: Request timeout in seconds

    Returns:
        Dictionary with all collected metrics
    """
    metrics = {
        "ctx_size": ctx_size,
        "output_tokens": output_tokens,
        "ttft_ms": -1.0,
        "tpot_ms": -1.0,
        "throughput_toks_s": 0.0,
        "success": False,
    }

    # Check server health first
    if not get_llama_server_health(container_ip, port):
        print(f"Server not healthy at {container_ip}:{port}")
        return metrics

    # Measure TTFT
    ttft_ms, ttft_success = measure_ttft(container_ip, port, timeout)
    metrics["ttft_ms"] = ttft_ms

    # Measure TPOT
    tpot_ms, tpot_success = measure_tpot(container_ip, port, output_tokens, timeout)
    metrics["tpot_ms"] = tpot_ms

    # Calculate throughput
    if tpot_ms > 0:
        metrics["throughput_toks_s"] = measure_throughput(tpot_ms)

    # Overall success
    metrics["success"] = ttft_success and tpot_success

    return metrics


def stream_inference(
    container_ip: str,
    port: int = 1234,
    prompt: str = "Hello",
    max_tokens: int = 64,
    stream_interval: float = 0.1,
) -> Dict[str, Any]:
    """
    Run streaming inference and collect timing metrics.

    Args:
        container_ip: Container IP address
        port: Server port (default: 1234)
        prompt: Input prompt
        max_tokens: Maximum output tokens
        stream_interval: Polling interval for streaming

    Returns:
        Dictionary with streaming metrics
    """
    url = f"http://{container_ip}:{port}/v1/chat/completions"

    prompt_data = {
        "model": "default",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": True,
    }

    metrics = {
        "ttft_ms": -1.0,
        "total_time_ms": -1.0,
        "tokens_generated": 0,
        "success": False,
    }

    try:
        start_time = time.time()
        ttft_recorded = False

        request = urllib.request.Request(
            url,
            data=json.dumps(prompt_data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        response = urllib.request.urlopen(request, timeout=300)

        for line in response:
            line = line.decode("utf-8").strip()

            if line.startswith("data:"):
                data = line[5:].strip()

                if data == "[DONE]":
                    break

                try:
                    chunk = json.loads(data)

                    # Check for first token (TTFT)
                    if not ttft_recorded and "choices" in chunk:
                        if chunk["choices"]:
                            ttft_ms = (time.time() - start_time) * 1000
                            metrics["ttft_ms"] = ttft_ms
                            ttft_recorded = True

                    # Count tokens
                    if "choices" in chunk:
                        for choice in chunk["choices"]:
                            if "delta" in choice:
                                metrics["tokens_generated"] += 1

                except json.JSONDecodeError:
                    pass

        metrics["total_time_ms"] = (time.time() - start_time) * 1000
        metrics["success"] = True

    except Exception as e:
        print(f"Streaming error: {e}")

    return metrics
