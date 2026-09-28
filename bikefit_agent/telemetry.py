"""Observability, OpenTelemetry Tracing, Structured JSON Logging, and PII Redaction.

Implements structured RFC 3339 JSON logging, end-to-end OpenTelemetry span lifecycles,
and automated PII redaction for Google Cloud Trace and Cloud Logging compliance.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .security.pii import redact_pii_text, sanitize_payload

# Global in-flight OpenTelemetry spans keyed by (tool_name, thread_id/context)
_ACTIVE_SPANS: Dict[str, Any] = {}
_SPAN_START_TIMES: Dict[str, float] = {}

# OpenTelemetry Tracer initialization
try:
    from opentelemetry import trace
    from opentelemetry.trace import StatusCode, Status
    from opentelemetry.sdk.trace import TracerProvider

    # Only set provider if one doesn't exist
    if not isinstance(trace.get_tracer_provider(), TracerProvider):
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("bikefit_agent", "0.2.0")
    OTEL_AVAILABLE = True
except Exception:
    tracer = None
    OTEL_AVAILABLE = False


class StructuredJsonFormatter(logging.Formatter):
    """Custom logging formatter that produces structured, cloud-ready JSON records."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a structured JSON object with PII redaction."""
        now_iso = datetime.now(timezone.utc).isoformat()

        # Extract OpenTelemetry context if available
        trace_id = None
        span_id = None
        if OTEL_AVAILABLE:
            curr_span = trace.get_current_span()
            if curr_span and curr_span.get_span_context().is_valid:
                ctx = curr_span.get_span_context()
                trace_id = format(ctx.trace_id, "032x")
                span_id = format(ctx.span_id, "016x")

        # Sanitize message to strip any inadvertent PII
        clean_msg = redact_pii_text(record.getMessage())

        log_payload = {
            "timestamp": now_iso,
            "severity": record.levelname,
            "logger": record.name,
            "message": clean_msg,
            "event_type": getattr(record, "event_type", "GENERAL"),
            "trace_id": trace_id,
            "span_id": span_id,
        }

        # Include structured extra data if provided
        if hasattr(record, "structured_data") and isinstance(record.structured_data, dict):
            log_payload["data"] = sanitize_payload(record.structured_data)

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload)


# Configure structured logger
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(StructuredJsonFormatter())

logger = logging.getLogger("bikefit_agent")
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
logger.handlers = [handler]
logger.propagate = False


def trace_before_tool(tool: Any, args: Dict[str, Any], context: Any) -> Optional[Dict[str, Any]]:
    """ADK lifecycle callback invoked immediately before tool execution.

    Starts an OpenTelemetry span and writes a structured JSON log with sanitized arguments.
    """
    tool_name = getattr(tool, "name", str(tool))
    sanitized_args = sanitize_payload(args)
    span_key = f"{tool_name}_{id(context)}"
    _SPAN_START_TIMES[span_key] = time.time()

    span = None
    if OTEL_AVAILABLE and tracer:
        # Start OpenTelemetry span
        span = tracer.start_span(f"tool.{tool_name}")
        span.set_attribute("tool.name", tool_name)
        span.set_attribute("tool.args", json.dumps(sanitized_args))
        span.set_attribute("component", "bikefit_agent.tools")
        span.add_event("tool_started", {"timestamp": datetime.now(timezone.utc).isoformat()})
        _ACTIVE_SPANS[span_key] = span

    # Emit structured JSON log
    record = logger.makeRecord(
        logger.name, logging.INFO, "telemetry.py", 0,
        f"Invoking tool '{tool_name}'", (), None
    )
    record.event_type = "TOOL_START"
    record.structured_data = {
        "tool_name": tool_name,
        "arguments": sanitized_args,
    }
    logger.handle(record)
    return None


def trace_after_tool(tool: Any, args: Dict[str, Any], context: Any, tool_output: Any) -> Optional[Dict[str, Any]]:
    """ADK lifecycle callback invoked immediately after tool execution.

    Records span duration, success status, and writes a structured JSON log.
    """
    tool_name = getattr(tool, "name", str(tool))
    span_key = f"{tool_name}_{id(context)}"
    start_time = _SPAN_START_TIMES.pop(span_key, time.time())
    duration_ms = round((time.time() - start_time) * 1000, 2)

    # Sanitize tool output for logging
    sanitized_output = sanitize_payload(
        tool_output.model_dump() if hasattr(tool_output, "model_dump") else tool_output
    )

    # Finalize OpenTelemetry span
    span = _ACTIVE_SPANS.pop(span_key, None)
    if span:
        span.set_attribute("tool.duration_ms", duration_ms)
        span.set_attribute("tool.status", "SUCCESS")
        span.add_event("tool_finished", {
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        if hasattr(StatusCode, "OK"):
            span.set_status(Status(StatusCode.OK))
        span.end()

    # Emit structured JSON log
    record = logger.makeRecord(
        logger.name, logging.INFO, "telemetry.py", 0,
        f"Tool '{tool_name}' completed in {duration_ms}ms", (), None
    )
    record.event_type = "TOOL_SUCCESS"
    record.structured_data = {
        "tool_name": tool_name,
        "duration_ms": duration_ms,
        "result": sanitized_output,
    }
    logger.handle(record)
    return None


def trace_on_tool_error(tool: Any, args: Dict[str, Any], context: Any, error: Exception) -> Optional[Dict[str, Any]]:
    """ADK lifecycle callback invoked when a tool throws an error.

    Records the exception on the active OpenTelemetry span and writes an ERROR JSON log.
    """
    tool_name = getattr(tool, "name", str(tool))
    span_key = f"{tool_name}_{id(context)}"
    sanitized_args = sanitize_payload(args)

    span = _ACTIVE_SPANS.pop(span_key, None)
    if span:
        span.record_exception(error)
        if hasattr(StatusCode, "ERROR"):
            span.set_status(Status(StatusCode.ERROR, description=str(error)))
        span.add_event("tool_error", {
            "error_type": type(error).__name__,
            "error_message": str(error)
        })
        span.end()

    # Emit structured JSON log
    record = logger.makeRecord(
        logger.name, logging.ERROR, "telemetry.py", 0,
        f"Tool '{tool_name}' failed with error: {error}", (), None
    )
    record.event_type = "TOOL_ERROR"
    record.structured_data = {
        "tool_name": tool_name,
        "arguments": sanitized_args,
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    logger.handle(record)
    return None
