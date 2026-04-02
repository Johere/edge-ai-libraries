"""
Performance profiling utilities for video analysis pipeline.

Usage:
    # Environment variable control
    export ENABLE_PROFILING=true
    export PROFILE_OUTPUT=/tmp/profile_results.json

    # In code
    with ProfileTimer("operation_name", {"key": "value"}):
        # code to profile
        ...

    # Or as decorator
    @profile_function
    def my_function():
        ...

Features:
    - Context manager for timing code blocks
    - Decorator for function-level profiling
    - Nested timing support (tracks parent-child relationships)
    - JSON export for analysis
    - Zero overhead when disabled (checks env var once at startup)
"""

import json
import os
import time
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional

# Global profiling state
_PROFILING_ENABLED = os.getenv("ENABLE_PROFILING", "").lower() in ("true", "1", "yes")
_PROFILE_OUTPUT = os.getenv("PROFILE_OUTPUT", "/tmp/profile_results.json")
_profile_data: List[Dict[str, Any]] = []
_profile_lock = Lock()
_nesting_level = 0


class ProfileTimer:
    """Context manager for timing code blocks with metadata."""

    def __init__(self, operation: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize profiler for an operation.

        Args:
            operation: Name of the operation being timed
            metadata: Optional dictionary of metadata about the operation
        """
        self.operation = operation
        self.metadata = metadata or {}
        self.start_time = None
        self.end_time = None
        self.duration = None
        self.enabled = _PROFILING_ENABLED

    def __enter__(self):
        """Start timing."""
        if not self.enabled:
            return self

        global _nesting_level
        with _profile_lock:
            self.nesting_level = _nesting_level
            _nesting_level += 1

        self.start_time = time.monotonic()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record results."""
        if not self.enabled:
            return False

        self.end_time = time.monotonic()
        self.duration = self.end_time - self.start_time

        global _nesting_level
        with _profile_lock:
            _nesting_level -= 1

            # Record the profiling data
            record = {
                "operation": self.operation,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "duration_seconds": round(self.duration, 4),
                "nesting_level": self.nesting_level,
                "metadata": self.metadata,
                "success": exc_type is None,
            }

            if exc_type is not None:
                record["error"] = {
                    "type": exc_type.__name__,
                    "message": str(exc_val),
                }

            _profile_data.append(record)

        # Don't suppress exceptions
        return False


def profile_function(func: Callable) -> Callable:
    """
    Decorator to profile function execution time.

    Usage:
        @profile_function
        def my_function(arg1, arg2):
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        metadata = {
            "function": func.__name__,
            "module": func.__module__,
        }

        with ProfileTimer(f"function_{func.__name__}", metadata):
            return func(*args, **kwargs)

    return wrapper


def export_profile_data(output_path: Optional[str] = None) -> None:
    """
    Export collected profile data to JSON file.

    Args:
        output_path: Optional custom output path (overrides PROFILE_OUTPUT env var)
    """
    if not _PROFILING_ENABLED:
        return

    path = output_path or _PROFILE_OUTPUT

    with _profile_lock:
        data = {
            "profiling_enabled": _PROFILING_ENABLED,
            "output_path": path,
            "total_operations": len(_profile_data),
            "operations": _profile_data.copy(),
        }

        # Calculate summary statistics
        if _profile_data:
            total_time = sum(op["duration_seconds"] for op in _profile_data)
            data["summary"] = {
                "total_duration_seconds": round(total_time, 4),
                "operation_types": list(set(op["operation"] for op in _profile_data)),
            }

    # Ensure parent directory exists
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    # Write to file
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def clear_profile_data() -> None:
    """Clear all collected profile data."""
    global _profile_data
    with _profile_lock:
        _profile_data.clear()


def get_profile_summary() -> Dict[str, Any]:
    """
    Get summary statistics of collected profile data.

    Returns:
        Dictionary with summary statistics
    """
    if not _PROFILING_ENABLED:
        return {"profiling_enabled": False}

    with _profile_lock:
        if not _profile_data:
            return {
                "profiling_enabled": True,
                "total_operations": 0,
                "total_duration_seconds": 0,
            }

        total_time = sum(op["duration_seconds"] for op in _profile_data)
        operation_counts = {}
        for op in _profile_data:
            op_name = op["operation"]
            operation_counts[op_name] = operation_counts.get(op_name, 0) + 1

        return {
            "profiling_enabled": True,
            "total_operations": len(_profile_data),
            "total_duration_seconds": round(total_time, 4),
            "operation_counts": operation_counts,
            "longest_operation": max(_profile_data, key=lambda x: x["duration_seconds"]),
        }


# Utility function for easy timing
@contextmanager
def time_operation(operation: str, **metadata):
    """
    Convenience context manager for timing operations.

    Usage:
        with time_operation("video_download", url="http://example.com/video.mp4"):
            download_video()
    """
    with ProfileTimer(operation, metadata):
        yield
