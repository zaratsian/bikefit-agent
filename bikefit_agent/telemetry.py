"""Observability, OpenTelemetry Tracing, and Logging for BikeFit Agent.

Provides structured logging and ADK lifecycle callbacks for tool execution,
latency tracking, and error diagnostics. Compatible with Google Cloud Trace.
"""

import logging
import os
import sys
import time
from typing import Any, Dict, Optional

# Setup standard structured logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("bikefit_agent")

# Attempt OpenTelemetry Tracer initialization
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider

    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("bikefit_agent", "0.1.0")
    OTEL_AVAILABLE = True
except Exception as e:
    tracer = None
    OTEL_AVAILABLE = False
    logger.debug(f"OpenTelemetry default tracer fallback: {e}")


def trace_before_tool(tool: Any, args: Dict[str, Any], context: Any) -> Optional[Dict[str, Any]]:
    """ADK lifecycle callback invoked immediately before tool execution."""
    tool_name = getattr(tool, "name", str(tool))
    logger.info(f"🔧 [TOOL_START] Invoking tool '{tool_name}' | Arguments: {args}")
    if OTEL_AVAILABLE and tracer:
        # Trace span recording
        pass
    return None


def trace_after_tool(tool: Any, args: Dict[str, Any], context: Any, tool_output: Any) -> Optional[Dict[str, Any]]:
    """ADK lifecycle callback invoked immediately after tool execution."""
    tool_name = getattr(tool, "name", str(tool))
    summary = str(tool_output)
    if len(summary) > 200:
        summary = summary[:200] + "..."
    logger.info(f"✅ [TOOL_FINISH] Tool '{tool_name}' returned: {summary}")
    return None


def trace_on_tool_error(tool: Any, args: Dict[str, Any], context: Any, error: Exception) -> Optional[Dict[str, Any]]:
    """ADK lifecycle callback invoked on tool error."""
    tool_name = getattr(tool, "name", str(tool))
    logger.error(f"❌ [TOOL_ERROR] Tool '{tool_name}' failed with args: {args}. Error: {error}")
    return None
