"""
Performance logging module for the mining workflow.

Provides structured performance logs for timing data of every mining step and loop iteration.
Writes to a dedicated perf.log file when enabled via ENABLE_PERF_LOG environment variable.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Literal

from alphaagent.core.conf import RD_AGENT_SETTINGS

# Lazy initialization of the logger
_perf_logger: logging.Logger | None = None


def _get_perf_logger() -> logging.Logger:
    """
    Get or initialize the performance logger.

    Returns a logger that writes to perf.log in the current working directory.
    The logger is configured to not propagate to parent loggers to avoid
    interference with loguru/stderr logging.
    """
    global _perf_logger
    if _perf_logger is None:
        _perf_logger = logging.getLogger("alphaagent.perf")
        _perf_logger.setLevel(logging.INFO)
        _perf_logger.propagate = False  # Don't leak into loguru/stderr

        # Create file handler in append mode
        perf_log_path = Path.cwd() / "perf.log"
        handler = logging.FileHandler(perf_log_path, mode="a", encoding="utf-8")
        handler.setLevel(logging.INFO)

        # Simple format without logger name or level
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)

        _perf_logger.addHandler(handler)

    return _perf_logger


def log_step(
    timestamp: datetime,
    loop_idx: int,
    step_idx: int,
    step_name: str,
    duration_sec: float,
    status: Literal["success", "skipped", "error"],
) -> None:
    """
    Log timing data for a single workflow step.

    Args:
        timestamp: When the step completed (UTC)
        loop_idx: Loop iteration index
        step_idx: Step index within the loop
        step_name: Name of the step function
        duration_sec: Duration in seconds
        status: Step execution status (success/skipped/error)
    """
    if not RD_AGENT_SETTINGS.enable_perf_log:
        return

    logger = _get_perf_logger()

    # Format: ISO8601 timestamp | loop=X step=Y name=Z duration=Xs status=S
    iso_timestamp = timestamp.isoformat()
    message = (
        f"{iso_timestamp} | "
        f"loop={loop_idx} step={step_idx} name={step_name} "
        f"duration={duration_sec:.2f}s status={status}"
    )

    logger.info(message)


def log_loop_summary(
    timestamp: datetime,
    loop_idx: int,
    total_duration_sec: float,
    step_count: int,
) -> None:
    """
    Log summary for a completed loop iteration.

    Args:
        timestamp: When the loop completed (UTC)
        loop_idx: Loop iteration index
        total_duration_sec: Total duration of the loop in seconds
        step_count: Number of steps in the loop
    """
    if not RD_AGENT_SETTINGS.enable_perf_log:
        return

    logger = _get_perf_logger()

    # Format: ISO8601 timestamp | loop=X SUMMARY steps=Y total_duration=Zs
    iso_timestamp = timestamp.isoformat()
    message = (
        f"{iso_timestamp} | "
        f"loop={loop_idx} SUMMARY steps={step_count} "
        f"total_duration={total_duration_sec:.2f}s"
    )

    logger.info(message)
